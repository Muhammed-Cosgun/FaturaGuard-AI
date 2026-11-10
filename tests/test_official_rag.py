from pathlib import Path

from faturaguard.services.official_rag import OfficialRagIndexer
from faturaguard.services.official_source_catalog import OfficialSourceCatalog


class FakePdfExtractor:
    def extract_pages(self, path: Path) -> list[str]:
        assert path.is_file()
        return ["Şema ve schematron kontrolü e-Fatura belgesi için gereklidir."]


class FakeArchiveExtractor:
    def extract_documents(self, path: Path) -> list[tuple[str, list[str]]]:
        assert path.is_file()
        return [("UBL-TR Fatura Kılavuzu", ["LegalMonetaryTotal parasal toplamları içerir."])]


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


def test_rag_indexes_verified_ubl_guide_archive(tmp_path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    archive = raw / "guides.zip"
    archive.write_bytes(b"official archive")
    import hashlib
    import json

    catalog_path = tmp_path / "sources.json"
    catalog_path.write_text(
        json.dumps(
            {
                "policy": {"allowed_domains": ["ebelge.gib.gov.tr"]},
                "sources": [
                    {
                        "id": "gib-ubl-guides",
                        "title": "GİB UBL-TR Kılavuzları",
                        "url": "https://ebelge.gib.gov.tr/guides.zip",
                        "status": "retrieved",
                        "local_file": "raw/guides.zip",
                        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    index = OfficialRagIndexer(
        OfficialSourceCatalog(catalog_path), FakePdfExtractor(), FakeArchiveExtractor()
    ).build()

    results = index.search("LegalMonetaryTotal")

    assert len(results) == 1
    assert results[0].source_id == "gib-ubl-guides"
    assert results[0].source_title.endswith("UBL-TR Fatura Kılavuzu")
