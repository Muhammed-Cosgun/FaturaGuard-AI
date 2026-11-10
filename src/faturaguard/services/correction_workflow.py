"""Onay/red kararını, çalışma kopyasını ve yeniden doğrulamayı yönetir."""

import difflib
from pathlib import Path

from faturaguard.domain.correction import CorrectionJob, CorrectionStatus
from faturaguard.services.correction_engine import SafeCorrectionEngine, store_working_copy
from faturaguard.services.document_storage import StoredDocument
from faturaguard.services.job_repository import SqliteCorrectionJobStore
from faturaguard.services.validation_adapter import EfaturaKontrolAdapter


class CorrectionWorkflow:
    def __init__(self, data_root: Path, validator: EfaturaKontrolAdapter) -> None:
        self._data_root = data_root
        self._validator = validator
        self._engine = SafeCorrectionEngine()
        self._store = SqliteCorrectionJobStore(data_root)

    def create(self, stored: StoredDocument, report) -> CorrectionJob:
        proposals = self._engine.propose(stored.path.read_bytes(), report)
        job = CorrectionJob(
            job_id=stored.job_id,
            original_filename=stored.original_filename,
            original_path=str(stored.path),
            original_sha256=stored.sha256,
            report=report,
            proposals=proposals,
        )
        self._store.save(job)
        self._store.append_event(
            job.job_id,
            "job_created",
            {"filename": job.original_filename, "original_sha256": job.original_sha256},
        )
        return job

    def decide(self, job_id: str, proposal_id: str, decision: str) -> CorrectionJob:
        job = self._store.load(job_id)
        proposal = next((item for item in job.proposals if item.proposal_id == proposal_id), None)
        if proposal is None or proposal.status is not CorrectionStatus.PROPOSED:
            raise ValueError("Bekleyen düzeltme teklifi bulunamadı.")
        if decision == "reject":
            proposal.status = CorrectionStatus.REJECTED
            self._store.save(job)
            self._store.append_event(
                job.job_id,
                "correction_rejected",
                {"proposal_id": proposal.proposal_id, "rule_id": proposal.rule_id},
            )
            return job
        if decision != "approve":
            raise ValueError("Geçersiz kullanıcı kararı.")
        proposal.status = CorrectionStatus.APPROVED
        self._store.append_event(
            job.job_id,
            "correction_approved",
            {"proposal_id": proposal.proposal_id, "rule_id": proposal.rule_id},
        )
        original = Path(job.original_path).read_bytes()
        corrected = self._engine.apply(original, proposal)
        corrected_path, corrected_hash = store_working_copy(self._data_root, job.job_id, corrected)
        job.corrected_path = str(corrected_path)
        job.corrected_sha256 = corrected_hash
        job.corrected_report = self._validator.validate(corrected, job.original_filename)
        job.diff = "\n".join(
            difflib.unified_diff(
                original.decode("utf-8", errors="replace").splitlines(),
                corrected.decode("utf-8", errors="replace").splitlines(),
                fromfile="original.xml",
                tofile="corrected.xml",
                lineterm="",
            )
        )
        job.diff_path = str(self._store.store_diff(job.job_id, job.diff))
        proposal.status = CorrectionStatus.APPLIED
        self._store.save(job)
        self._store.append_event(
            job.job_id,
            "correction_applied",
            {"proposal_id": proposal.proposal_id, "corrected_sha256": corrected_hash},
        )
        return job

    def explain_finding(self, job_id: str, finding_code: str, agent) -> CorrectionJob:
        """Agent çıktısını işlem kaydına yazar; XML üzerinde değişiklik yapmaz."""
        job = self._store.load(job_id)
        finding = next((item for item in job.report.findings if item.code == finding_code), None)
        if finding is None:
            raise ValueError("Açıklanacak doğrulama bulgusu bulunamadı.")
        result = agent.explain(finding)
        job.agent_outputs[finding_code] = {
            "status": result["status"],
            "audit_events": result["audit_events"],
            "explanation": result["explanation"].model_dump() if result["explanation"] else None,
            "evidence": [
                {
                    "source_title": item.chunk.source_title,
                    "source_url": item.chunk.source_url,
                    "page": item.chunk.page,
                }
                for item in result.get("evidence", [])
            ],
            "failure_reason": result.get("generation_error"),
        }
        self._store.save(job)
        self._store.append_event(
            job.job_id,
            "source_explanation_requested",
            {
                "finding_code": finding_code,
                "status": result["status"],
                "failure_reason": result.get("generation_error"),
            },
        )
        return job

    def record_automation_event(self, job_id: str, status: str, detail: str) -> CorrectionJob:
        job = self._store.load(job_id)
        job.automation_events.append({"status": status, "detail": detail})
        self._store.save(job)
        self._store.append_event(
            job.job_id,
            "automation_notification",
            {"status": status, "detail": detail},
        )
        return job

    def list_recent_jobs(self, limit: int = 20) -> list[dict[str, object]]:
        return self._store.list_recent(limit)

    def list_audit_events(self, job_id: str) -> list[dict[str, object]]:
        return self._store.list_events(job_id)
