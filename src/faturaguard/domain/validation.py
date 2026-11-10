"""Doğrulama sağlayıcılarından bağımsız uygulama modelleri."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    ERROR = "hata"
    WARNING = "uyari"
    INFO = "bilgi"


class Priority(StrEnum):
    CRITICAL = "kritik"
    HIGH = "yuksek"
    MEDIUM = "orta"
    LOW = "dusuk"


class Finding(BaseModel):
    """Kütüphane bulgusunun kullanıcı arayüzüne uygun, kararlı şekli."""

    code: str
    severity: Severity
    priority: Priority
    priority_reason: str
    source: str
    message: str
    line: int | None = None
    explanation: str | None = None
    suggested_fix: str | None = None


class ValidationSummary(BaseModel):
    is_valid: bool
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    document_type: str | None = None
    profile: str | None = None
    invoice_type: str | None = None
    duration_ms: float = Field(ge=0)


class ValidationReport(BaseModel):
    original_filename: str
    summary: ValidationSummary
    findings: list[Finding]
    validator_package: dict[str, str] = Field(default_factory=dict)
