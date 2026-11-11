import pytest

from faturaguard.domain.correction import CorrectionStatus
from faturaguard.domain.validation import (
    Finding,
    Priority,
    Severity,
    ValidationReport,
    ValidationSummary,
)
from faturaguard.services.correction_engine import (
    CorrectionNotApplicableError,
    SafeCorrectionEngine,
)

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cac:InvoiceLine><cbc:LineExtensionAmount>10.00</cbc:LineExtensionAmount></cac:InvoiceLine>
 <cac:InvoiceLine><cbc:LineExtensionAmount>5.15</cbc:LineExtensionAmount></cac:InvoiceLine>
 <cac:LegalMonetaryTotal><cbc:LineExtensionAmount>25.15</cbc:LineExtensionAmount></cac:LegalMonetaryTotal>
</Invoice>"""


def test_line_total_correction_changes_only_approved_working_copy() -> None:
    report = ValidationReport(
        original_filename="test.xml",
        summary=ValidationSummary(
            is_valid=False, error_count=0, warning_count=1, info_count=0, duration_ms=1
        ),
        findings=[
            Finding(
                code="hesap-dip-satir",
                severity=Severity.WARNING,
                priority=Priority.HIGH,
                priority_reason="Toplam tutarsız.",
                source="hesap",
                message="Dip toplam uyuşmuyor.",
            )
        ],
    )
    engine = SafeCorrectionEngine()
    proposal = engine.propose(XML, report)[0]

    assert proposal.before == "25.15"
    assert proposal.after == "15.15"
    proposal.status = CorrectionStatus.APPROVED
    corrected = engine.apply(XML, proposal)

    assert b">15.15<" in corrected
    assert corrected == XML.replace(b">25.15<", b">15.15<", 1)
    assert XML in XML  # Original bytes remain unchanged in memory.


def test_correction_engine_rejects_unapproved_or_unknown_rule() -> None:
    report = ValidationReport(
        original_filename="test.xml",
        summary=ValidationSummary(
            is_valid=False, error_count=0, warning_count=1, info_count=0, duration_ms=1
        ),
        findings=[
            Finding(
                code="hesap-dip-satir",
                severity=Severity.WARNING,
                priority=Priority.HIGH,
                priority_reason="Toplam tutarsız.",
                source="hesap",
                message="Dip toplam uyuşmuyor.",
            )
        ],
    )
    engine = SafeCorrectionEngine()
    proposal = engine.propose(XML, report)[0]

    with pytest.raises(CorrectionNotApplicableError, match="onayı olmayan"):
        engine.apply(XML, proposal)

    unknown_rule = proposal.model_copy(
        update={"status": CorrectionStatus.APPROVED, "rule_id": "change-invoice-number"}
    )
    with pytest.raises(CorrectionNotApplicableError, match="İzin listesinde olmayan"):
        engine.apply(XML, unknown_rule)

    assert XML.count(b"25.15") == 1
