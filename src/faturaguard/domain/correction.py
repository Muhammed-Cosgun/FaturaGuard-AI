"""Kullanıcı onaylı, sınırlı XML düzeltme modelleri."""

from enum import StrEnum

from pydantic import BaseModel, Field

from faturaguard.domain.validation import ValidationReport


class CorrectionStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class CorrectionProposal(BaseModel):
    proposal_id: str
    rule_id: str
    finding_code: str
    title: str
    rationale: str
    target_path: str
    before: str
    after: str
    status: CorrectionStatus = CorrectionStatus.PROPOSED


class CorrectionJob(BaseModel):
    job_id: str
    original_filename: str
    original_path: str
    original_sha256: str
    report: ValidationReport
    proposals: list[CorrectionProposal] = Field(default_factory=list)
    corrected_path: str | None = None
    corrected_sha256: str | None = None
    corrected_report: ValidationReport | None = None
    diff: str | None = None
    diff_path: str | None = None
    agent_outputs: dict[str, dict[str, object]] = Field(default_factory=dict)
    automation_events: list[dict[str, object]] = Field(default_factory=list)
