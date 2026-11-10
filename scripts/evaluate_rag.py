"""Semantic, BM25 ve hybrid rerank retrieval kalitesini karşılaştırır."""

from pathlib import Path

from faturaguard.services.hybrid_retrieval import (
    Bm25LexicalRetriever,
    ChromaSemanticStore,
    HybridRetriever,
    SentenceTransformerEmbedder,
)
from faturaguard.services.official_rag import OfficialRagIndex
from faturaguard.services.rag_evaluation import (
    evaluate_retriever,
    load_golden_queries,
    save_results,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    chunks = OfficialRagIndex.load(
        PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"
    ).chunks
    queries = load_golden_queries(PROJECT_ROOT / "resources" / "evaluation" / "golden_queries.json")
    semantic = ChromaSemanticStore(PROJECT_ROOT / "data" / "chroma", SentenceTransformerEmbedder())
    lexical = Bm25LexicalRetriever(chunks)
    hybrid = HybridRetriever(semantic, lexical)
    variants = [
        ("semantic", semantic.search),
        ("lexical_bm25", lexical.search),
        ("hybrid_rerank", hybrid.search),
    ]
    results = []
    for name, search in variants:
        results.append(
            evaluate_retriever(
                name,
                queries,
                search,
                lambda item: item.chunk.source_id,
                lambda item: item.chunk.page,
                lambda item: item.chunk.source_url,
            )
        )
    output = PROJECT_ROOT / "data" / "evaluation" / "retrieval_metrics.json"
    save_results(output, results)
    for result in results:
        print(
            f"{result.strategy}: Recall@3={result.recall_at_k:.2f}, MRR@3={result.mrr_at_k:.2f}, CitationCoverage={result.citation_coverage:.2f}"
        )
    print(f"Rapor: {output}")


if __name__ == "__main__":
    main()
