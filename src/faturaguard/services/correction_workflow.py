"""Onay/red kararını, çalışma kopyasını ve yeniden doğrulamayı yönetir."""

import difflib
from pathlib import Path

from faturaguard.domain.correction import CorrectionJob, CorrectionStatus
from faturaguard.services.correction_engine import SafeCorrectionEngine, store_working_copy
from faturaguard.services.document_storage import StoredDocument
from faturaguard.services.validation_adapter import EfaturaKontrolAdapter


class JsonCorrectionJobStore:
    def __init__(self, root: Path) -> None:
        self._root = root / "jobs"

    def save(self, job: CorrectionJob) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        target = self._root / f"{job.job_id}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(job.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(target)

    def load(self, job_id: str) -> CorrectionJob:
        return CorrectionJob.model_validate_json(
            (self._root / f"{job_id}.json").read_text(encoding="utf-8")
        )


class CorrectionWorkflow:
    def __init__(self, data_root: Path, validator: EfaturaKontrolAdapter) -> None:
        self._data_root = data_root
        self._validator = validator
        self._engine = SafeCorrectionEngine()
        self._store = JsonCorrectionJobStore(data_root)

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
        return job

    def decide(self, job_id: str, proposal_id: str, decision: str) -> CorrectionJob:
        job = self._store.load(job_id)
        proposal = next((item for item in job.proposals if item.proposal_id == proposal_id), None)
        if proposal is None or proposal.status is not CorrectionStatus.PROPOSED:
            raise ValueError("Bekleyen düzeltme teklifi bulunamadı.")
        if decision == "reject":
            proposal.status = CorrectionStatus.REJECTED
            self._store.save(job)
            return job
        if decision != "approve":
            raise ValueError("Geçersiz kullanıcı kararı.")
        proposal.status = CorrectionStatus.APPROVED
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
        proposal.status = CorrectionStatus.APPLIED
        self._store.save(job)
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
        }
        self._store.save(job)
        return job

    def record_automation_event(self, job_id: str, status: str, detail: str) -> CorrectionJob:
        job = self._store.load(job_id)
        job.automation_events.append({"status": status, "detail": detail})
        self._store.save(job)
        return job
