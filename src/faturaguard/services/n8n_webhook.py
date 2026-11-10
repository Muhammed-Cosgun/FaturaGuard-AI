"""Opsiyonel n8n webhook bildirimi; belge içeriğini asla iletmez."""

from dataclasses import dataclass

import httpx

from faturaguard.domain.correction import CorrectionJob


@dataclass(frozen=True, slots=True)
class NotificationResult:
    status: str
    detail: str


class N8nWebhookNotifier:
    def __init__(self, webhook_url: str | None) -> None:
        self._webhook_url = webhook_url

    def notify(self, job: CorrectionJob) -> NotificationResult:
        if not self._webhook_url:
            return NotificationResult("disabled", "N8N_WEBHOOK_URL yapılandırılmadı.")
        payload = {
            "event": "faturaguard.correction_decision",
            "job_id": job.job_id,
            "filename": job.original_filename,
            "original_sha256": job.original_sha256,
            "corrected_sha256": job.corrected_sha256,
            "proposal_statuses": {item.proposal_id: item.status.value for item in job.proposals},
            "validation_after": job.corrected_report.summary.model_dump(mode="json")
            if job.corrected_report
            else None,
        }
        try:
            response = httpx.post(self._webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as error:
            return NotificationResult("failed", str(error))
        return NotificationResult("sent", f"HTTP {response.status_code}")
