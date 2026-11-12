from pathlib import Path

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
from faturaguard.services.validation_adapter import EfaturaKontrolAdapter

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cac:InvoiceLine><cbc:LineExtensionAmount>10.00</cbc:LineExtensionAmount></cac:InvoiceLine>
 <cac:InvoiceLine><cbc:LineExtensionAmount>5.15</cbc:LineExtensionAmount></cac:InvoiceLine>
 <cac:LegalMonetaryTotal><cbc:LineExtensionAmount>25.15</cbc:LineExtensionAmount></cac:LegalMonetaryTotal>
</Invoice>"""

TOTALS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cac:InvoiceLine><cbc:LineExtensionAmount>10.00</cbc:LineExtensionAmount></cac:InvoiceLine>
 <cac:InvoiceLine><cbc:LineExtensionAmount>5.15</cbc:LineExtensionAmount></cac:InvoiceLine>
 <cac:TaxTotal><cbc:TaxAmount>2.73</cbc:TaxAmount></cac:TaxTotal>
 <cac:LegalMonetaryTotal>
  <cbc:LineExtensionAmount>15.15</cbc:LineExtensionAmount>
  <cbc:TaxExclusiveAmount>15.15</cbc:TaxExclusiveAmount>
  <cbc:TaxInclusiveAmount>17.88</cbc:TaxInclusiveAmount>
  <cbc:PayableAmount>17.88</cbc:PayableAmount>
 </cac:LegalMonetaryTotal>
</Invoice>"""


def _report(*codes: str) -> ValidationReport:
    return ValidationReport(
        original_filename="test.xml",
        summary=ValidationSummary(
            is_valid=False, error_count=0, warning_count=len(codes), info_count=0, duration_ms=1
        ),
        findings=[
            Finding(
                code=code,
                severity=Severity.WARNING,
                priority=Priority.HIGH,
                priority_reason="Toplam tutarsız.",
                source="hesap",
                message="Dip toplam uyuşmuyor.",
            )
            for code in codes
        ],
    )


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


@pytest.mark.parametrize(
    ("finding_code", "rule_id", "old", "new"),
    [
        (
            "hesap-dip-vergi-haric",
            "recalculate-tax-exclusive-total",
            b"<cbc:TaxExclusiveAmount>15.15</cbc:TaxExclusiveAmount>",
            b"<cbc:TaxExclusiveAmount>10.00</cbc:TaxExclusiveAmount>",
        ),
        (
            "hesap-dip-vergi-dahil",
            "recalculate-tax-inclusive-total",
            b"<cbc:TaxInclusiveAmount>17.88</cbc:TaxInclusiveAmount>",
            b"<cbc:TaxInclusiveAmount>17.00</cbc:TaxInclusiveAmount>",
        ),
        (
            "hesap-dip-odenecek",
            "recalculate-payable-total",
            b"<cbc:PayableAmount>17.88</cbc:PayableAmount>",
            b"<cbc:PayableAmount>17.00</cbc:PayableAmount>",
        ),
    ],
)
def test_arithmetic_total_catalog_proposes_and_applies_one_allowed_rule(
    finding_code: str, rule_id: str, old: bytes, new: bytes
) -> None:
    document = TOTALS_XML.replace(old, new, 1)
    engine = SafeCorrectionEngine()

    proposals = engine.propose(document, _report(finding_code))

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.rule_id == rule_id
    assert proposal.before in new.decode()
    proposal.status = CorrectionStatus.APPROVED
    corrected = engine.apply(document, proposal)

    assert corrected != document
    assert proposal.after.encode() in corrected


def test_catalog_defers_dependent_totals_until_lower_level_finding_is_resolved() -> None:
    document = TOTALS_XML.replace(b"15.15", b"25.15", 1)
    engine = SafeCorrectionEngine()

    proposals = engine.propose(
        document, _report("hesap-dip-satir", "hesap-dip-vergi-haric")
    )

    assert [proposal.rule_id for proposal in proposals] == ["recalculate-line-extension-total"]


@pytest.mark.parametrize(
    ("finding_code", "old", "new"),
    [
        (
            "hesap-dip-vergi-haric",
            b'<cbc:TaxExclusiveAmount currencyID="TRY">15.15',
            b'<cbc:TaxExclusiveAmount currencyID="TRY">15.00',
        ),
        (
            "hesap-dip-vergi-dahil",
            b'<cbc:TaxInclusiveAmount currencyID="TRY">17.88',
            b'<cbc:TaxInclusiveAmount currencyID="TRY">17.00',
        ),
        (
            "hesap-dip-odenecek",
            b'<cbc:PayableAmount currencyID="TRY">17.88',
            b'<cbc:PayableAmount currencyID="TRY">17.00',
        ),
    ],
)
def test_catalog_aligns_with_real_validator_after_single_approved_patch(
    finding_code: str, old: bytes, new: bytes
) -> None:
    baseline = Path("resources/fixtures/baseline_invoice.xml").read_bytes()
    document = baseline.replace(old, new, 1)
    validator = EfaturaKontrolAdapter()
    report = validator.validate(document, "case.xml")
    engine = SafeCorrectionEngine()
    proposal = next(item for item in engine.propose(document, report) if item.finding_code == finding_code)
    proposal.status = CorrectionStatus.APPROVED

    corrected = engine.apply(document, proposal)
    corrected_codes = {item.code for item in validator.validate(corrected, "case.xml").findings}

    assert finding_code not in corrected_codes
