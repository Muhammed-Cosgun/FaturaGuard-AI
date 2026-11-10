"""RAG retrieval kalitesini golden sorgularla ölçer."""

import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GoldenQuery:
    query_id: str
    query: str
    expected_source_id: str
    expected_page: int


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    strategy: str
    query_count: int
    recall_at_k: float
    mrr_at_k: float
    citation_coverage: float
    details: list[dict[str, object]]


def load_golden_queries(path: Path) -> list[GoldenQuery]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        GoldenQuery(item["id"], item["query"], item["expected_source_id"], item["expected_page"])
        for item in payload
    ]


def evaluate_retriever(
    strategy: str,
    queries: Sequence[GoldenQuery],
    retrieve: Callable[[str, int], Sequence[object]],
    source_id_of: Callable[[object], str],
    page_of: Callable[[object], int],
    url_of: Callable[[object], str],
    k: int = 3,
) -> EvaluationResult:
    reciprocal_ranks: list[float] = []
    recalls: list[float] = []
    citation_flags: list[float] = []
    details: list[dict[str, object]] = []
    for golden in queries:
        results = list(retrieve(golden.query, k))
        rank = next(
            (
                index
                for index, item in enumerate(results, 1)
                if source_id_of(item) == golden.expected_source_id
                and page_of(item) == golden.expected_page
            ),
            None,
        )
        recalls.append(float(rank is not None))
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        citation_flags.extend(
            float(url_of(item).startswith("https://ebelge.gib.gov.tr/")) for item in results
        )
        details.append({"query_id": golden.query_id, "matched_rank": rank})
    return EvaluationResult(
        strategy,
        len(queries),
        sum(recalls) / len(queries) if queries else 0.0,
        sum(reciprocal_ranks) / len(queries) if queries else 0.0,
        sum(citation_flags) / len(citation_flags) if citation_flags else 0.0,
        details,
    )


def save_results(path: Path, results: Sequence[EvaluationResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
