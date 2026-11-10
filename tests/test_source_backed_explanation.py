from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.services.hybrid_retrieval import RetrievedEvidence
from faturaguard.services.official_rag import RagChunk
from faturaguard.services.source_backed_explanation import (
    Citation,
    OllamaStructuredGenerator,
    SourceBackedExplanation,
)


def test_generator_removes_summary_sentence_repeated_in_reasoning() -> None:
    explanation = SourceBackedExplanation(
        summary="Toplam tutar satırlarla uyumlu olmalıdır.",
        reasoning="Toplam tutar satırlarla uyumlu olmalıdır. Resmî kılavuz ilgili alanları tanımlar.",
        recommendation="Satırları yeniden hesaplayın.",
        citations=[
            Citation(
                source_id="gib",
                source_title="GİB Kılavuzu",
                source_url="https://ebelge.gib.gov.tr/x",
                page=1,
            )
        ],
    )

    normalized = OllamaStructuredGenerator._remove_reasoning_repetition(explanation)

    assert normalized.reasoning == "Resmî kılavuz ilgili alanları tanımlar."


def test_generator_uses_deterministic_fallback_after_invalid_llm_json(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"message": {"content": "geçersiz json"}}

    monkeypatch.setattr(
        "faturaguard.services.source_backed_explanation.httpx.post",
        lambda *args, **kwargs: Response(),
    )
    finding = Finding(
        code="hesap-dip-satir",
        severity=Severity.WARNING,
        priority=Priority.HIGH,
        priority_reason="Toplam tutarsız.",
        source="hesap",
        message="Satır toplamı uyuşmuyor.",
        suggested_fix="Satırları yeniden hesaplayın.",
    )
    chunk = RagChunk("gib", "GİB Kılavuzu", "https://ebelge.gib.gov.tr/x", 35, "Kanıt")
    evidence = RetrievedEvidence(chunk, 0.9, 0.8, 0.5, 0.8)

    result = OllamaStructuredGenerator("test", retries=1).generate(finding, [evidence])

    assert result.generation_mode == "deterministic_fallback"
    assert result.recommendation == "Satırları yeniden hesaplayın."
    assert result.citations[0].page == 35
