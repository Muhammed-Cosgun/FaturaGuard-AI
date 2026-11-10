from faturaguard.domain.validation import (
    Finding,
    Priority,
    Severity,
    ValidationReport,
    ValidationSummary,
)
from faturaguard.services.correction_workflow import CorrectionWorkflow
from faturaguard.services.document_storage import StoredDocument


class FakeValidator:
    def validate(self, document, original_filename):
        return _report()


class FakeAgent:
    def explain(self, finding):
        return {
            "status": "awaiting_human_review",
            "audit_events": ["retrieve_official_sources:1", "await_human_review"],
            "explanation": FakeExplanation(),
        }


class FakeExplanation:
    def model_dump(self):
        return {"summary": "Kaynaklı açıklama", "citations": []}


def _report() -> ValidationReport:
    return ValidationReport(
        original_filename="test.xml",
        summary=ValidationSummary(
            is_valid=False, error_count=1, warning_count=0, info_count=0, duration_ms=1
        ),
        findings=[
            Finding(
                code="xml-bicim",
                severity=Severity.ERROR,
                priority=Priority.CRITICAL,
                priority_reason="Hata",
                source="xml",
                message="Geçersiz XML",
            )
        ],
    )


def test_workflow_persists_source_backed_agent_audit_output(tmp_path) -> None:
    source = tmp_path / "original.xml"
    source.write_bytes(b"<Invoice />")
    stored = StoredDocument("job-1", "test.xml", source, "hash", 11)
    workflow = CorrectionWorkflow(tmp_path, FakeValidator())
    workflow.create(stored, _report())

    job = workflow.explain_finding("job-1", "xml-bicim", FakeAgent())

    assert job.agent_outputs["xml-bicim"]["status"] == "awaiting_human_review"
    persisted = workflow._store.load("job-1")
    assert persisted.agent_outputs["xml-bicim"]["explanation"]["summary"] == "Kaynaklı açıklama"
