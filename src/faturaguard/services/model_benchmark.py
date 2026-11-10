"""Yerel LLM değerlendirme kayıtlarının ölçümlerini hesaplar."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ModelBenchmarkRecord:
    model: str
    case_id: str
    elapsed_seconds: float
    status: str
    generation_mode: str | None
    citation_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def aggregate_model_benchmark(
    records: Iterable[ModelBenchmarkRecord],
) -> list[dict[str, float | int | str]]:
    grouped: dict[str, list[ModelBenchmarkRecord]] = defaultdict(list)
    for record in records:
        grouped[record.model].append(record)
    summaries: list[dict[str, float | int | str]] = []
    for model, items in grouped.items():
        total = len(items)
        summaries.append(
            {
                "model": model,
                "case_count": total,
                "mean_seconds": round(sum(item.elapsed_seconds for item in items) / total, 2),
                "llm_success_rate": round(
                    sum(item.generation_mode == "llm" for item in items) / total, 3
                ),
                "fallback_rate": round(
                    sum(item.generation_mode == "deterministic_fallback" for item in items) / total,
                    3,
                ),
                "source_backed_rate": round(
                    sum(item.citation_count > 0 for item in items) / total,
                    3,
                ),
            }
        )
    return sorted(summaries, key=lambda item: str(item["model"]))
