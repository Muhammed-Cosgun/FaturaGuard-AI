"""Doğrulanmış resmî GİB PDF'lerinden yerel RAG indeksi üretir."""

from pathlib import Path

from faturaguard.services.official_rag import OfficialRagIndexer, PdfTextExtractor
from faturaguard.services.official_source_catalog import OfficialSourceCatalog

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "resources" / "gib" / "official_sources.json"
INDEX_PATH = PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"


def main() -> None:
    catalog = OfficialSourceCatalog(CATALOG_PATH)
    index = OfficialRagIndexer(catalog, PdfTextExtractor()).build()
    index.save(INDEX_PATH)
    print(f"{len(index.chunks)} resmî GİB kaynak parçası indekslendi: {INDEX_PATH}")


if __name__ == "__main__":
    main()
