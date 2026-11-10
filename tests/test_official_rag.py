from pathlib import Path

from faturaguard.services.official_rag import OfficialRagIndexer
from faturaguard.services.official_source_catalog import OfficialSourceCatalog


class FakePdfExtractor:
    def extract_pages(self, path: Path) -> list[str]:
        assert path.is_file()
        return ["Şema ve schematron kontrolü e-Fatura belgesi için gereklidir."]


def test_rag_indexes_only_verified_pdf_sources(tmp_path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    pdf = raw / "guide.pdf"
    pdf.write_bytes(b"official content")
    import hashlib
    import json

    catalog_path = tmp_path / "sources.json"
    catalog_path.write_text(
        json.dumps(
            {
                "policy": {"allowed_domains": ["ebelge.gib.gov.tr"]},
                "sources": [
                    {
                        "id": "gib-guide",
                        "title": "GİB Kılavuzu",
                        "url": "https://ebelge.gib.gov.tr/guide.pdf",
                        "status": "retrieved",
                        "local_file": "raw/guide.pdf",
                        "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    index = OfficialRagIndexer(OfficialSourceCatalog(catalog_path), FakePdfExtractor()).build()

    results = index.search("schematron kontrolü")

    assert len(results) == 1
    assert results[0].source_id == "gib-guide"
    assert results[0].page == 1
