"""efatura-kontrol ile FaturaGuard'ın iş modelini birbirinden ayırır."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from faturaguard.domain.validation import (
    Finding,
    Severity,
    ValidationReport,
    ValidationSummary,
)
from faturaguard.services.finding_prioritizer import prioritize

ValidatorFunction = Callable[[str | Path | bytes], Any]


class ValidatorUnavailableError(RuntimeError):
    """Doğrulama sağlayıcısı uygulama ortamında hazır olmadığında yükseltilir."""


class EfaturaKontrolAdapter:
    """Harici kütüphane raporunu uygulamanın kararlı sözleşmesine dönüştürür."""

    def __init__(self, validator: ValidatorFunction | None = None) -> None:
        self._validator = validator

    def validate(self, document: bytes, original_filename: str) -> ValidationReport:
        report = self._get_validator()(document)
        findings = [self._to_finding(item) for item in report.bulgular]
        return ValidationReport(
            original_filename=original_filename,
            summary=ValidationSummary(
                is_valid=report.gecerli,
                error_count=report.sayim("hata"),
                warning_count=report.sayim("uyari"),
                info_count=report.sayim("bilgi"),
                document_type=report.tur,
                profile=report.profil,
                invoice_type=report.tip,
                duration_ms=round(report.sure_ms, 1),
            ),
            findings=findings,
            validator_package=dict(report.paket),
        )

    def _get_validator(self) -> ValidatorFunction:
        if self._validator is not None:
            return self._validator
        try:
            from efatura_kontrol.kontrol import kontrol_et
        except ImportError as error:
            raise ValidatorUnavailableError(
                "efatura-kontrol kurulamadı; doğrulama hizmeti başlatılamıyor."
            ) from error
        return kontrol_et

    @staticmethod
    def _to_finding(finding: Any) -> Finding:
        severity = Severity(finding.seviye)
        decision = prioritize(finding.kod, severity, finding.kaynak)
        return Finding(
            code=finding.kod,
            severity=severity,
            priority=decision.priority,
            priority_reason=decision.reason,
            source=finding.kaynak,
            message=finding.mesaj,
            line=finding.satir,
            explanation=finding.aciklama,
            suggested_fix=finding.duzeltme,
        )
