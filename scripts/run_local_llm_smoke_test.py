"""Gerçek GİB RAG kanıtı + yerel Ollama modeli için canlı smoke test."""

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
from faturaguard.services.source_backed_explanation import OllamaStructuredGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    chunks = OfficialRagIndex.load(
        PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"
    ).chunks
    retriever = HybridRetriever(
        ChromaSemanticStore(PROJECT_ROOT / "data" / "chroma", SentenceTransformerEmbedder()),
        Bm25LexicalRetriever(chunks),
    )
    agent = SourceBackedAgent(
        retriever,
        OllamaStructuredGenerator(settings.ollama_model, settings.ollama_base_url),
    )
    finding = Finding(
        code="xsd-sema",
        severity=Severity.ERROR,
        priority=Priority.CRITICAL,
        priority_reason="Belge doğrulamasını durduran bir hata bulundu.",
        source="xsd",
        message="UBL-TR şema ve schematron kurallarına uyum doğrulanmalıdır.",
    )
    result = agent.explain(finding)
    print(f"model={settings.ollama_model}")
    print(f"status={result['status']}")
    if result["explanation"] is not None:
        print(result["explanation"].model_dump_json(indent=2))
    print("audit_events=" + ", ".join(result["audit_events"]))


if __name__ == "__main__":
    main()
