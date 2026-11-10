"""İşlem kanıtlarını XML içeriğini açığa çıkarmadan raporlar."""

from typing import Any

from faturaguard.domain.correction import CorrectionJob


def build_report_payload(job: CorrectionJob) -> dict[str, Any]:
    diff_line_count = len(job.diff.splitlines()) if job.diff else 0
    return {
        "report_type": "FaturaGuard AI işlem raporu",
        "job_id": job.job_id,
        "document": {
            "filename": job.original_filename,
            "original_sha256": job.original_sha256,
            "corrected_sha256": job.corrected_sha256,
        },
        "validation_before": job.report.model_dump(mode="json"),
        "correction_proposals": [item.model_dump(mode="json") for item in job.proposals],
        "validation_after": job.corrected_report.model_dump(mode="json")
        if job.corrected_report
        else None,
        "agent_outputs": job.agent_outputs,
        "automation_events": job.automation_events,
        "diff_summary": {
            "available": bool(job.diff),
            "line_count": diff_line_count,
            "detail": "Tam XML diff'i yalnızca uygulama içi işlem görünümünde gösterilir.",
        },
        "privacy_note": "Orijinal, düzeltilmiş XML ve tam XML diff'i bu rapora dahil edilmez.",
    }
