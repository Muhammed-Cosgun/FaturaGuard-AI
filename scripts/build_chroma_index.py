"""Doğrulanmış GİB RAG chunks'larını embedding ile yerel Chroma'ya yazar."""

from pathlib import Path

from faturaguard.services.hybrid_retrieval import ChromaSemanticStore, SentenceTransformerEmbedder
from faturaguard.services.official_rag import OfficialRagIndex

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma"


def main() -> None:
    chunks = OfficialRagIndex.load(CHUNKS_PATH).chunks
    store = ChromaSemanticStore(CHROMA_PATH, SentenceTransformerEmbedder(allow_model_download=True))
    count = store.rebuild(chunks)
    print(f"{count} GİB chunk'ı kalıcı Chroma koleksiyonuna yazıldı.")


if __name__ == "__main__":
    main()
