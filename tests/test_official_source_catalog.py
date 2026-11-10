import json
from hashlib import sha256

import pytest

from faturaguard.services.official_source_catalog import OfficialSourceCatalog, SourcePolicyError


def _write_catalog(tmp_path, source_url: str, local_file: str = "raw/source.txt"):
    source_path = tmp_path / local_file
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"GIB official content")
    payload = {
        "policy": {"allowed_domains": ["ebelge.gib.gov.tr"]},
        "sources": [
            {
                "id": "official-source",
                "title": "Resmi kaynak",
                "url": source_url,
                "status": "retrieved",
                "local_file": local_file,
                "sha256": sha256(source_path.read_bytes()).hexdigest(),
            }
        ],
    }
    catalog_path = tmp_path / "official_sources.json"
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")
    return catalog_path


def test_catalog_accepts_and_verifies_official_gib_source(tmp_path) -> None:
    catalog = OfficialSourceCatalog(
        _write_catalog(tmp_path, "https://ebelge.gib.gov.tr/kilavuz.pdf")
    )

    verified = catalog.verified_local_sources()

    assert len(verified) == 1
    assert verified[0].source_id == "official-source"


def test_catalog_rejects_non_gib_source(tmp_path) -> None:
    catalog_path = _write_catalog(tmp_path, "https://example.com/kilavuz.pdf")

    with pytest.raises(SourcePolicyError):
        OfficialSourceCatalog(catalog_path)
