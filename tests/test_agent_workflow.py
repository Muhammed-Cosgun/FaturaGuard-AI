from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.services.agent_workflow import SourceBackedAgent
from faturaguard.services.hybrid_retrieval import RetrievedEvidence
from faturaguard.services.official_rag import RagChunk
from faturaguard.services.source_backed_explanation import (
    Citation,
    LLMUnavailableError,
    SourceBackedExplanation,
)


class FakeRetriever:
    def __init__(self, evidence):
        self.evidence = evidence

    def search(self, query, limit):
        return self.evidence


class FakeGenerator:
    def generate(self, finding, evidence):
        chunk = evidence[0].chunk
        return SourceBackedExplanation(
            summary="Resmî kaynakla desteklenen açıklama.",
            reasoning="Kanıt şema ve schematron kontrolünü açıklıyor.",
            recommendation="Kullanıcı belgeyi incelemelidir.",
            citations=[
                Citation(
                    source_id=chunk.source_id,
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    page=chunk.page,
                )
            ],
        )


class FailingGenerator:
    def generate(self, finding, evidence):
        raise LLMUnavailableError("Yerel model yanıt veremedi.")


def _finding() -> Finding:
    return Finding(
        code="xml-bicim",
        severity=Severity.ERROR,
        priority=Priority.CRITICAL,
        priority_reason="Doğrulama durur.",
        source="xml",
        message="XML iyi biçimli değil.",
    )


def test_agent_routes_to_human_review_when_official_evidence_exists() -> None:
    chunk = RagChunk(
        "gib-test", "GİB Test Planı", "https://ebelge.gib.gov.tr/test.pdf", 7, "Şema kontrolü"
    )
    evidence = RetrievedEvidence(chunk, 0.9, 1.0, 1.0, 0.95)
    result = SourceBackedAgent(FakeRetriever([evidence]), FakeGenerator()).explain(_finding())

    assert result["status"] == "awaiting_human_review"
    assert result["explanation"].citations[0].source_id == "gib-test"
    assert result["audit_events"][-1] == "await_human_review"


def test_agent_stops_when_no_official_evidence_exists() -> None:
    result = SourceBackedAgent(FakeRetriever([]), FakeGenerator()).explain(_finding())

    assert result["status"] == "insufficient_official_evidence"
    assert result["explanation"] is None


def test_agent_stops_when_only_weak_official_evidence_exists() -> None:
    chunk = RagChunk(
        "gib-test", "GİB Test Planı", "https://ebelge.gib.gov.tr/test.pdf", 3, "Versiyon geçmişi"
    )
    weak_evidence = RetrievedEvidence(chunk, 0.85, 0.20, 0.05, 0.55)

    result = SourceBackedAgent(FakeRetriever([weak_evidence]), FakeGenerator()).explain(_finding())

    assert result["status"] == "insufficient_official_evidence"
    assert result["explanation"] is None


def test_agent_preserves_official_evidence_when_generation_is_unavailable() -> None:
    chunk = RagChunk(
        "gib-test", "GİB Test Planı", "https://ebelge.gib.gov.tr/test.pdf", 7, "Şema kontrolü"
    )
    evidence = RetrievedEvidence(chunk, 0.9, 1.0, 1.0, 0.95)

    result = SourceBackedAgent(FakeRetriever([evidence]), FailingGenerator()).explain(_finding())

    assert result["status"] == "generation_unavailable"
    assert result["explanation"] is None
    assert result["evidence"] == [evidence]
    assert result["generation_error"] == "Yerel model yanıt veremedi."
    assert "source_generation_unavailable" in result["audit_events"]


def test_agent_warmup_runs_a_small_retrieval_query() -> None:
    class WarmupRetriever:
        def __init__(self) -> None:
            self.calls = []

        def search(self, query, limit):
            self.calls.append((query, limit))
            return []

    retriever = WarmupRetriever()
    SourceBackedAgent(retriever, FakeGenerator()).warmup()

    assert retriever.calls == [("UBL-TR e-Fatura doğrulama", 1)]
