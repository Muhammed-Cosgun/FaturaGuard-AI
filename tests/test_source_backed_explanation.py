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
