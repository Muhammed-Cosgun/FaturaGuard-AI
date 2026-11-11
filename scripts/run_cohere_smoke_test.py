"""Cohere Command A+ erişimi ve kaynaklı JSON çıktısı için canlı smoke test."""

from pathlib import Path

from faturaguard.config import settings
from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.services.agent_workflow import SourceBackedAgent
from faturaguard.services.hybrid_retrieval import (
    Bm25LexicalRetriever,
    ChromaSemanticStore,
    HybridRetriever,
    SentenceTransformerEmbedder,
)
from faturaguard.services.official_rag import OfficialRagIndex
from faturaguard.services.source_backed_explanation import CohereStructuredGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if not settings.cohere_api_key:
        raise SystemExit("COHERE_API_KEY tanımlı değil; anahtarı bu CMD oturumunda ayarlayın.")
    chunks = OfficialRagIndex.load(
        PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"
    ).chunks
    retriever = HybridRetriever(
        ChromaSemanticStore(PROJECT_ROOT / "data" / "chroma", SentenceTransformerEmbedder()),
        Bm25LexicalRetriever(chunks),
    )
    finding = Finding(
        code="xsd-sema",
        severity=Severity.ERROR,
        priority=Priority.CRITICAL,
        priority_reason="Belge doğrulamasını durduran bir hata bulundu.",
        source="xsd",
        message="UBL-TR şema ve schematron kurallarına uyum doğrulanmalıdır.",
    )
    result = SourceBackedAgent(
        retriever,
        CohereStructuredGenerator(
            settings.cohere_api_key,
            settings.cohere_model,
            timeout_seconds=settings.cohere_timeout_seconds,
        ),
    ).explain(finding)
    print(f"model={settings.cohere_model}")
    print(f"status={result['status']}")
    if result["generation_error"]:
        print(f"generation_error={result['generation_error']}")
    if result["explanation"] is not None:
        print(result["explanation"].model_dump_json(indent=2))
    print("audit_events=" + ", ".join(result["audit_events"]))


if __name__ == "__main__":
    main()
