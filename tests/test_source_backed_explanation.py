from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.services.hybrid_retrieval import RetrievedEvidence
from faturaguard.services.official_rag import RagChunk
from faturaguard.services.source_backed_explanation import (
    Citation,
    FallbackExplanationGenerator,
    GeminiStructuredGenerator,
    GroqStructuredGenerator,
    LLMUnavailableError,
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


def test_gemini_generator_uses_structured_output_and_marks_api_mode(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "steps": [
                    {
                        "type": "model_output",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    '{"summary":"Satır toplamı uyumsuz.",'
                                    '"reasoning":"GİB kaynağı ilgili alanı tanımlar.",'
                                    '"recommendation":"Satırları yeniden hesaplayın.",'
                                    '"requires_user_review":true,'
                                    '"citations":[{"source_id":"gib","source_title":'
                                    '"GİB Kılavuzu","source_url":'
                                    '"https://ebelge.gib.gov.tr/x","page":35}]}'
                                ),
                            }
                        ],
                    }
                ]
            }

    observed: dict[str, object] = {}

    def fake_post(*args, **kwargs):
        observed.update(kwargs)
        return Response()

    monkeypatch.setattr("faturaguard.services.source_backed_explanation.httpx.post", fake_post)
    finding = Finding(
        code="hesap-dip-satir",
        severity=Severity.WARNING,
        priority=Priority.HIGH,
        priority_reason="Toplam tutarsız.",
        source="hesap",
        message="Satır toplamı uyuşmuyor.",
        suggested_fix="Satırları yeniden hesaplayın.",
    )
    evidence = [
        RetrievedEvidence(
            RagChunk("gib", "GİB Kılavuzu", "https://ebelge.gib.gov.tr/x", 35, "Kanıt"),
            0.9,
            0.8,
            0.5,
            0.8,
        )
    ]

    result = GeminiStructuredGenerator("secret", "gemini-test").generate(finding, evidence)

    assert result.generation_mode == "gemini_api"
    assert observed["headers"]["x-goog-api-key"] == "secret"
    assert "response_format" in observed["json"]
    assert "original_filename" not in observed["json"]["input"]
    assert finding.message not in observed["json"]["input"]


def test_fallback_generator_uses_local_generator_after_api_failure() -> None:
    class FailingPrimary:
        def generate(self, finding, evidence):
            raise LLMUnavailableError("API timeout")

    class LocalFallback:
        def generate(self, finding, evidence):
            return SourceBackedExplanation(
                summary="Yerel açıklama.",
                reasoning="Yerel kanıt özeti.",
                recommendation="İnceleyin.",
                citations=[Citation(source_id="gib", source_title="GİB", source_url="https://gib", page=1)],
            )

    result = FallbackExplanationGenerator(FailingPrimary(), LocalFallback()).generate(
        _finding_for_fallback(), []
    )

    assert result.summary == "Yerel açıklama."
    assert result.provider_trace == "API fallback: API timeout"


def test_groq_generator_uses_strict_schema_and_marks_api_mode(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"summary":"Satır toplamı uyumsuz.",'
                                '"reasoning":"GİB kaynağı ilgili alanı tanımlar.",'
                                '"recommendation":"Satırları yeniden hesaplayın.",'
                                '"requires_user_review":true,'
                                '"citations":[{"source_id":"gib","source_title":'
                                '"GİB Kılavuzu","source_url":'
                                '"https://ebelge.gib.gov.tr/x","page":35}]}'
                            )
                        }
                    }
                ]
            }

    observed: dict[str, object] = {}

    def fake_post(*args, **kwargs):
        observed.update(kwargs)
        return Response()

    monkeypatch.setattr("faturaguard.services.source_backed_explanation.httpx.post", fake_post)
    finding = Finding(
        code="hesap-dip-satir",
        severity=Severity.WARNING,
        priority=Priority.HIGH,
        priority_reason="Toplam tutarsız.",
        source="hesap",
        message="Satır toplamı uyuşmuyor.",
        suggested_fix="Satırları yeniden hesaplayın.",
    )
    evidence = [
        RetrievedEvidence(
            RagChunk("gib", "GİB Kılavuzu", "https://ebelge.gib.gov.tr/x", 35, "Kanıt"),
            0.9,
            0.8,
            0.5,
            0.8,
        )
    ]

    result = GroqStructuredGenerator("secret", "openai/gpt-oss-20b").generate(finding, evidence)

    assert result.generation_mode == "groq_api"
    assert observed["headers"]["Authorization"] == "Bearer secret"
    schema = observed["json"]["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False


def test_groq_qwen_uses_json_schema_best_effort_and_keeps_client_side_validation() -> None:
    response_format = GroqStructuredGenerator._response_format(False, True)

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is False


def test_groq_generator_records_http_status_without_response_body(monkeypatch) -> None:
    import httpx

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(400, request=request, text="hassas hata gövdesi")

    class FailingResponse:
        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError("bad request", request=request, response=response)

    monkeypatch.setattr(
        "faturaguard.services.source_backed_explanation.httpx.post",
        lambda *args, **kwargs: FailingResponse(),
    )
    finding = _finding_for_fallback()
    evidence = [
        RetrievedEvidence(
            RagChunk("gib", "GİB Kılavuzu", "https://ebelge.gib.gov.tr/x", 7, "Kanıt"),
            0.9,
            0.8,
            0.5,
            0.8,
        )
    ]

    try:
        GroqStructuredGenerator("secret", "qwen/qwen3.8-27b").generate(finding, evidence)
    except LLMUnavailableError as error:
        assert "HTTP 400" in str(error)
        assert "hassas hata gövdesi" not in str(error)
    else:
        raise AssertionError("HTTP durum hatasının LLMUnavailableError'a dönüşmesi bekleniyordu.")


def _finding_for_fallback() -> Finding:
    return Finding(
        code="xml-bicim",
        severity=Severity.ERROR,
        priority=Priority.CRITICAL,
        priority_reason="Biçim hatası.",
        source="xml",
        message="XML hatası.",
    )
