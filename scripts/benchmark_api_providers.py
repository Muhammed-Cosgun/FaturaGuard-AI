"""Gemini ve Groq için aynı kaynaklı açıklama vakasında kısa gecikme ölçümü yapar.

Çıktı yalnızca model adı, süre ve başarı durumunu içerir; API anahtarı, ham XML veya
fatura verisi yazılmaz. Ölçüm, sağlayıcı başına varsayılan üç tekrar çalıştırır.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

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
from faturaguard.services.source_backed_explanation import (
    GeminiStructuredGenerator,
    GroqStructuredGenerator,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kaynaklı API açıklama gecikmesini ölçer")
    parser.add_argument("--provider", choices=("gemini", "groq"), required=True)
    parser.add_argument("--runs", type=int, default=3)
    return parser.parse_args()


def build_agent(provider: str) -> tuple[SourceBackedAgent, str]:
    chunks = OfficialRagIndex.load(
        PROJECT_ROOT / "data" / "rag" / "official_gib_chunks.json"
    ).chunks
    retriever = HybridRetriever(
        ChromaSemanticStore(PROJECT_ROOT / "data" / "chroma", SentenceTransformerEmbedder()),
        Bm25LexicalRetriever(chunks),
    )
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise SystemExit("GEMINI_API_KEY tanımlı değil")
        return (
            SourceBackedAgent(
                retriever,
                GeminiStructuredGenerator(settings.gemini_api_key, settings.gemini_model),
            ),
            settings.gemini_model,
        )
    if not settings.groq_api_key:
        raise SystemExit("GROQ_API_KEY tanımlı değil")
    return (
        SourceBackedAgent(
            retriever,
            GroqStructuredGenerator(
                settings.groq_api_key,
                settings.groq_model,
                timeout_seconds=settings.groq_timeout_seconds,
            ),
        ),
        settings.groq_model,
    )


def main() -> None:
    args = parse_args()
    if args.runs < 1:
        raise SystemExit("--runs en az 1 olmalı")
    agent, model = build_agent(args.provider)
    finding = Finding(
        code="hesap-dip-vergi-haric",
        severity=Severity.WARNING,
        priority=Priority.HIGH,
        priority_reason="Belgenin tutarlılığını etkileyebilir.",
        source="hesap",
        message="Vergi hariç tutar dip toplam kuralıyla uyuşmuyor.",
        explanation="cbc:TaxExclusiveAmount = mal/hizmet toplamı − indirim + artırım.",
        remediation="Dip toplamı yeniden hesaplayın.",
    )
    samples: list[dict[str, object]] = []
    for run_number in range(1, args.runs + 1):
        started = perf_counter()
        result = agent.explain(finding)
        seconds = round(perf_counter() - started, 3)
        success = result["status"] == "awaiting_human_review" and result["explanation"] is not None
        sample = {
            "run": run_number,
            "seconds": seconds,
            "success": success,
            "status": result["status"],
            "generation_error": result["generation_error"],
        }
        samples.append(sample)
        print(f"{args.provider} run={run_number} seconds={seconds} success={success}")

    result_summary = {
        "provider": args.provider,
        "model": model,
        "run_count": args.runs,
        "successful_runs": sum(sample["success"] for sample in samples),
        "mean_seconds": round(sum(sample["seconds"] for sample in samples) / len(samples), 3),
        "samples": samples,
    }
    output_path = PROJECT_ROOT / "data" / "evaluation" / "api_provider_benchmark.json"
    previous: dict[str, object] = {}
    if output_path.is_file():
        try:
            loaded = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                previous = loaded
        except json.JSONDecodeError:
            previous = {}
    previous[args.provider] = result_summary
    output_path.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Kanıt: {output_path}")


if __name__ == "__main__":
    main()
