"""Yerel Ollama modellerini gerçek FaturaGuard RAG vakalarında karşılaştırır."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.services.agent_workflow import SourceBackedAgent
from faturaguard.services.hybrid_retrieval import (
    Bm25LexicalRetriever,
    ChromaSemanticStore,
    HybridRetriever,
    SentenceTransformerEmbedder,
)
from faturaguard.services.model_benchmark import (
    ModelBenchmarkRecord,
    aggregate_model_benchmark,
)
from faturaguard.services.official_rag import OfficialRagIndex
from faturaguard.services.source_backed_explanation import OllamaStructuredGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS = ("qwen2.5:3b-instruct", "qwen3:4b-instruct", "gemma3:4b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FaturaGuard AI yerel model benchmark")
    parser.add_argument(
        "--model", action="append", dest="models", help="Tekrar kullanılabilir model adı"
    )
    return parser.parse_args()


def load_cases() -> list[Finding]:
    payload = json.loads(
        (PROJECT_ROOT / "resources" / "evaluation" / "local_llm_cases.json").read_text(
            encoding="utf-8"
        )
    )
    return [
        Finding(
            code=item["code"],
            severity=Severity(item["severity"]),
            priority=Priority(item["priority"]),
            priority_reason=item["priority_reason"],
            source=item["source"],
            message=item["message"],
            explanation=item["explanation"],
            suggested_fix=item["suggested_fix"],
        )
        for item in payload
    ]


def main() -> None:
    args = parse_args()
    models = tuple(args.models or DEFAULT_MODELS)
    chunks = OfficialRagIndex.load(
        PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"
    ).chunks
    retriever = HybridRetriever(
        ChromaSemanticStore(PROJECT_ROOT / "data" / "chroma", SentenceTransformerEmbedder()),
        Bm25LexicalRetriever(chunks),
    )
    records: list[ModelBenchmarkRecord] = []
    for model in models:
        agent = SourceBackedAgent(retriever, OllamaStructuredGenerator(model))
        for finding in load_cases():
            started = perf_counter()
            result = agent.explain(finding)
            explanation = result["explanation"]
            records.append(
                ModelBenchmarkRecord(
                    model=model,
                    case_id=finding.code,
                    elapsed_seconds=round(perf_counter() - started, 3),
                    status=result["status"],
                    generation_mode=explanation.generation_mode if explanation else None,
                    citation_count=len(explanation.citations) if explanation else 0,
                )
            )
            print(
                f"{model} | {finding.code} | {records[-1].elapsed_seconds:.2f}s | "
                f"{records[-1].status} | {records[-1].generation_mode}"
            )
    output = PROJECT_ROOT / "data" / "evaluation" / "local_model_benchmark.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "records": [item.to_dict() for item in records],
                "summary": aggregate_model_benchmark(records),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nÖzet")
    for summary in aggregate_model_benchmark(records):
        print(summary)
    print(f"Rapor: {output}")


if __name__ == "__main__":
    main()
