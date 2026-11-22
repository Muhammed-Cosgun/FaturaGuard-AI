"""Canlı modele gitmeden, bilinen kalite denetimlerinin pozitif/negatif vakaları."""

from faturaguard.domain.correction import CorrectionJob, CorrectionProposal
from faturaguard.domain.validation import Finding, ValidationReport, ValidationSummary
from faturaguard.services.chat_quality import chat_quality_issues


def quality_scenario(name):
    def finding(code, severity):
        return Finding(code=code, severity=severity, priority="yuksek", priority_reason="İnceleme",
                       source="evaluation", message="Örnek tespit")
    findings = ([finding("xml-bicim", "hata")] if name == "error" else [
        finding("hesap-dip-vergi-haric", "uyari"), finding("hesap-dip-vergi-dahil", "uyari"),
        finding("imza-yok", "bilgi")])
    summary = ValidationSummary(is_valid=name != "error", error_count=int(name == "error"),
                                warning_count=0 if name == "error" else 2,
                                info_count=0 if name == "error" else 1, duration_ms=1)
    report = ValidationReport(original_filename="quality-demo.xml", findings=findings, summary=summary)
    job = CorrectionJob(job_id="quality", original_filename="quality-demo.xml", original_path="unused.xml",
                        original_sha256="not-a-real-document", report=report)
    if name in {"applied", "pending", "rejected", "unready"}:
        job.proposals = [CorrectionProposal(proposal_id="p", rule_id="recalculate-tax-exclusive-total",
            finding_code="hesap-dip-vergi-haric", title="Vergi hariç toplam", rationale="Yerel hesap",
            target_path="cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount", before="15.00", after="15.15",
            status={"applied": "applied", "rejected": "rejected"}.get(name, "proposed"),
            agent_plan={"decision": "human_review" if name == "unready" else "propose"})]
    if name == "applied":
        job.corrected_report = report.model_copy(deep=True)
        job.corrected_report.findings = [findings[-1]]
        job.corrected_report.summary.warning_count = 0
    return job


def evaluate_quality_cases(cases):
    results = []
    for case in cases:
        issues = chat_quality_issues(case["answer"], quality_scenario(case["scenario"]))
        results.append({"id": case["id"], "expected": case["expected"], "actual": issues,
                        "passed": set(issues) == set(case["expected"])})
    return {"kind": "offline_guard_contract", "case_count": len(results),
            "passed": sum(row["passed"] for row in results), "results": results}
