from faturaguard.domain.correction import CorrectionJob
from faturaguard.domain.validation import ValidationReport, ValidationSummary
from faturaguard.services.reporting import build_report_payload


def _job() -> CorrectionJob:
    report = ValidationReport(
        original_filename="fatura.xml",
        summary=ValidationSummary(
            is_valid=True, error_count=0, warning_count=0, info_count=0, duration_ms=1
        ),
        findings=[],
    )
    return CorrectionJob(
        job_id="job-1",
        original_filename="fatura.xml",
        original_path="private/original.xml",
        original_sha256="original-hash",
        report=report,
        diff="--- original.xml\n+++ corrected.xml\n-<Invoice/>\n+<Invoice><ID>1</ID></Invoice>",
    )


def test_report_excludes_xml_contents_and_private_path() -> None:
    job = _job()
    job.agent_triage = {
        "route": "needs_human_review",
        "priority_finding_codes": ["hesap-dip-satir"],
        "safe_correction_ready_count": 1,
        "recommended_next_actions": ["İnceleyin."],
        "rationale": "İnsan incelemesi gerekir.",
        "privacy_boundary": "ham_xml_local_only",
    }
    payload = build_report_payload(job)

    assert payload["document"]["original_sha256"] == "original-hash"
    assert "original_path" not in str(payload)
    assert "<Invoice" not in str(payload)
    assert payload["diff_summary"] == {
        "available": True,
        "line_count": 4,
        "detail": "Tam XML diff'i yalnızca uygulama içi işlem görünümünde gösterilir.",
    }
    assert payload["agent_triage"]["route"] == "needs_human_review"
    assert "private/original.xml" not in str(payload["agent_triage"])
