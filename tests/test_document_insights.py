import json
from pathlib import Path

import pytest

from faturaguard.domain.correction import CorrectionJob, CorrectionProposal
from faturaguard.domain.validation import (
    Finding,
    Priority,
    Severity,
    ValidationReport,
    ValidationSummary,
)
from faturaguard.services.correction_engine import correction_rule_catalog
from faturaguard.services.document_chat import DocumentChat
from faturaguard.services.document_insights import comparison_details, finding_context
from faturaguard.services.source_backed_explanation import Citation, SourceBackedExplanation

CODES = [
    case["code"]
    for case in json.loads(
        (
            Path(__file__).resolve().parents[1] / "resources/evaluation/error_coverage_matrix.json"
        ).read_text(encoding="utf-8")
    )
]


def finding(code, message="Kayıtta gözlenen gerçek bulgu", severity=Severity.WARNING):
    return Finding(
        code=code,
        message=message,
        severity=severity,
        priority=Priority.HIGH,
        priority_reason="İncelenmeli",
        source="test",
        line=12,
        explanation="Doğrulayıcının bildirdiği kural",
        suggested_fix="Kaynak sistemde inceleyin.",
    )


def job(findings):
    return CorrectionJob(
        job_id="job",
        original_filename="demo.xml",
        original_path="local.xml",
        original_sha256="hash",
        report=ValidationReport(
            original_filename="demo.xml",
            findings=findings,
            summary=ValidationSummary(
                is_valid=True,
                error_count=0,
                warning_count=len(findings),
                info_count=0,
                duration_ms=1,
            ),
        ),
    )


@pytest.mark.parametrize("code", [*CODES, "gelecekteki-bilinmeyen-kod"])
def test_every_catalog_code_gets_concrete_local_context_even_without_llm(code):
    item = job([finding(code, "Bu dosyada saptanan değer farkı 41 → 42")])
    before = item.model_dump_json()
    turn = DocumentChat().answer(item, "Bu bulguyu açıkla", code)
    assert code in turn.answer and "Bu dosyada saptanan değer farkı 41 → 42" in turn.answer
    assert "XML içinde satır 12" in turn.answer
    assert "Doğrulayıcının kontrol ettiği kural" in turn.answer
    assert "Kaynak sistemde inceleyin" in turn.answer
    assert turn.mode == "unavailable" and not turn.citations
    assert item.model_dump_json() == before


@pytest.mark.parametrize(
    "rule_id",
    [
        "recalculate-line-extension-total",
        "recalculate-tax-exclusive-total",
        "recalculate-tax-inclusive-total",
        "recalculate-payable-total",
    ],
)
def test_all_supported_corrections_report_real_fields_and_values(rule_id):
    meta = correction_rule_catalog()[rule_id]
    item = job([finding(meta["finding_code"])])
    item.corrected_report = item.report.model_copy(deep=True)
    item.corrected_report.findings = []
    item.corrected_report.summary.warning_count = 0
    item.proposals = [
        CorrectionProposal(
            proposal_id="p",
            rule_id=rule_id,
            finding_code=meta["finding_code"],
            title=meta["title"],
            rationale=meta["rationale"],
            target_path=meta["path"],
            before="98.10",
            after="97.25",
            status="applied",
        )
    ]
    answer = comparison_details(item)
    assert f"({meta['element']}): 98.10 → 97.25" in answer
    assert meta["rationale"] in answer
    assert meta["finding_code"] in answer
    assert "Teknik doğrulamada bulgu kalmadı" in answer


@pytest.mark.parametrize(
    ("rule_id", "dependent_code"),
    [
        ("recalculate-line-extension-total", "hesap-dip-vergi-haric"),
        ("recalculate-tax-exclusive-total", "hesap-dip-vergi-dahil"),
        ("recalculate-tax-inclusive-total", "hesap-dip-odenecek"),
    ],
)
def test_dependency_explanation_works_across_rule_chain(rule_id, dependent_code):
    meta = correction_rule_catalog()[rule_id]
    item = job([finding(meta["finding_code"]), finding(dependent_code)])
    item.corrected_report = item.report.model_copy(deep=True)
    item.corrected_report.findings = []
    item.corrected_report.summary.warning_count = 0
    item.proposals = [
        CorrectionProposal(
            proposal_id="p",
            rule_id=rule_id,
            finding_code=meta["finding_code"],
            title=meta["title"],
            rationale=meta["rationale"],
            target_path=meta["path"],
            before="100",
            after="90",
            status="applied",
        )
    ]
    assert "Bağımlı kontroller: " + dependent_code in comparison_details(item)


def test_partial_resolution_and_new_findings_are_not_reported_as_all_fixed():
    item = job([finding("xsd-example"), finding("xsd-example")])
    item.corrected_report = item.report.model_copy(deep=True)
    item.corrected_report.findings = [
        finding("xsd-example"),
        finding("new-error", severity=Severity.ERROR),
    ]
    item.corrected_report.summary.error_count = 1
    item.corrected_report.summary.warning_count = 1
    answer = comparison_details(item)
    assert "kayıt sayısı 2 → 1" in answer
    assert "bu kod tamamen giderilmiş değil" in answer
    assert "new-error: 0 → 1" in answer
    assert "Hata seviyesinde bulgu sürüyor" in answer
    assert "artık görülmeyen bulgular: xsd-example" not in answer


def test_unrelated_resolved_code_has_no_invented_dependency_and_blockers_are_specific():
    item = job([finding("hesap-dip-satir"), finding("xsd-unrelated")])
    item.corrected_report = item.report.model_copy(deep=True)
    item.corrected_report.findings = []
    item.corrected_report.summary.warning_count = 0
    meta = correction_rule_catalog()["recalculate-line-extension-total"]
    item.proposals = [
        CorrectionProposal(
            proposal_id="p",
            rule_id="recalculate-line-extension-total",
            finding_code=meta["finding_code"],
            title=meta["title"],
            rationale=meta["rationale"],
            target_path=meta["path"],
            before="10",
            after="9",
            status="applied",
        )
    ]
    assert "Bağımlı kontroller:" not in comparison_details(item)
    pending = job([finding("hesap-dip-satir"), finding("hesap-dip-vergi-haric")])
    explanation = finding_context(pending, pending.report.findings[1])
    assert "bağlı olduğu kontrollerde de bulgu var: hesap-dip-satir" in explanation


def test_source_answer_keeps_actual_finding_separate_from_model_interpretation():
    item = job([finding("xsd-example", "Yerelde doğrulanan özel bulgu mesajı")])

    class SourceAgent:
        def explain(self, selected):
            assert selected == item.report.findings[0]
            return {
                "explanation": SourceBackedExplanation(
                    summary="Modelin belgeye dair doğrulanmamış tahmini",
                    reasoning="Resmî kaynak genel şema kontrolünü açıklar.",
                    recommendation="Kaynak sistemde şemayı kontrol edin.",
                    citations=[
                        Citation(
                            source_id="gib",
                            source_title="GİB Kılavuzu",
                            source_url="https://ebelge.gib.gov.tr/guide.pdf",
                            page=7,
                        )
                    ],
                )
            }

    turn = DocumentChat(SourceAgent()).answer(item, "PII içerebilen serbest soru", "xsd-example")
    assert turn.mode == "source_backed" and len(turn.citations) == 1
    assert "Yerelde doğrulanan özel bulgu mesajı" in turn.answer
    assert "Modelin belgeye dair doğrulanmamış tahmini" not in turn.answer
    assert "Resmî kaynaklı açıklama:" in turn.answer


def test_explicit_question_about_resolved_finding_uses_comparison_not_stale_explanation():
    item = job([finding("hesap-dip-satir")])
    item.corrected_report = item.report.model_copy(deep=True)
    item.corrected_report.findings = []
    item.corrected_report.summary.warning_count = 0
    turn = DocumentChat().answer(item, "hesap-dip-satir ne oldu?")
    assert turn.mode == "comparison" and "güncel doğrulamada artık görülmüyor" in turn.answer
    assert DocumentChat().answer(item, "Açıkla", "hesap-dip-satir").mode == "comparison"
