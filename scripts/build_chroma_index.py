"""Doğrulanmış GİB RAG chunks'larını embedding ile yerel Chroma'ya yazar."""

import argparse
from pathlib import Path

from faturaguard.services.hybrid_retrieval import ChromaSemanticStore, SentenceTransformerEmbedder
from faturaguard.services.official_rag import OfficialRagIndex

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resume-batches",
        type=int,
        default=None,
        help="Yalnızca belirtilen sayıda eksik batch yazar; kesintili yerel kurulum için kullanılır.",
    )
    args = parser.parse_args()
    chunks = OfficialRagIndex.load(CHUNKS_PATH).chunks
    # Model daha önce proje içi data/models önbelleğine indirildi. Yeniden kurulumda
    # ağ erişimi gerektirmemesi için yalnızca yerel kopya kullanılır.
    store = ChromaSemanticStore(CHROMA_PATH, SentenceTransformerEmbedder())
    count, target = store.sync(chunks, max_batches=args.resume_batches)
    print(f"Chroma koleksiyonu: {count}/{target} GİB chunk'ı.")


if __name__ == "__main__":
    main()
