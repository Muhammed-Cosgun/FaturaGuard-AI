from faturaguard.services.model_benchmark import ModelBenchmarkRecord, aggregate_model_benchmark


def test_benchmark_summary_calculates_speed_and_generation_rates() -> None:
    records = [
        ModelBenchmarkRecord("model-a", "case-1", 2.0, "awaiting_human_review", "llm", 1),
        ModelBenchmarkRecord(
            "model-a", "case-2", 4.0, "awaiting_human_review", "deterministic_fallback", 2
        ),
        ModelBenchmarkRecord("model-b", "case-1", 1.0, "insufficient_official_evidence", None, 0),
    ]

    summary = aggregate_model_benchmark(records)

    assert summary[0]["mean_seconds"] == 3.0
    assert summary[0]["llm_success_rate"] == 0.5
    assert summary[0]["fallback_rate"] == 0.5
    assert summary[1]["source_backed_rate"] == 0.0
