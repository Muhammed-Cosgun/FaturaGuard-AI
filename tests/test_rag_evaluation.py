from pathlib import Path

from faturaguard.services.rag_evaluation import GoldenQuery, evaluate_retriever, load_golden_queries


class Result:
    def __init__(self, source_id, page, url):
        self.source_id, self.page, self.url = source_id, page, url


def test_evaluation_calculates_metrics() -> None:
    golden = [
        GoldenQuery("first", "ilk", "gib-test", 7),
        GoldenQuery("second", "ikinci", "gib-guide", 3),
    ]
    responses = {
        "ilk": [Result("gib-test", 7, "https://ebelge.gib.gov.tr/test.pdf")],
        "ikinci": [
            Result("other", 1, "https://ebelge.gib.gov.tr/other.pdf"),
            Result("gib-guide", 3, "https://ebelge.gib.gov.tr/guide.pdf"),
        ],
    }
    result = evaluate_retriever(
        "test",
        golden,
        lambda query, limit: responses[query][:limit],
        lambda item: item.source_id,
        lambda item: item.page,
        lambda item: item.url,
    )
    assert result.recall_at_k == 1.0
    assert result.mrr_at_k == 0.75
    assert result.citation_coverage == 1.0


def test_project_golden_queries_are_unique_and_cover_core_validation_topics() -> None:
    project_root = Path(__file__).resolve().parents[1]
    queries = load_golden_queries(project_root / "resources" / "evaluation" / "golden_queries.json")

    assert len(queries) >= 10
    assert len({query.query_id for query in queries}) == len(queries)
    assert {"schema-schematron", "tax-exclusive-total", "xades-extension-content"} <= {
        query.query_id for query in queries
    }
