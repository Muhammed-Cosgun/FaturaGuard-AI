from types import SimpleNamespace

import pytest

from faturaguard.domain.validation import Finding, ValidationReport, ValidationSummary
from faturaguard.services.chat_facts import proposal_approval, validation_transitions


def report(*entries):
    findings = [Finding(code=code, severity=severity, source="test", message="Tespit",
                        priority="yuksek", priority_reason="İnceleme")
                for code, severity in entries]
    return ValidationReport(original_filename="demo.xml", findings=findings,
                            summary=ValidationSummary(is_valid=not any(f.severity == "hata" for f in findings),
                                error_count=sum(f.severity == "hata" for f in findings),
                                warning_count=sum(f.severity == "uyari" for f in findings),
                                info_count=sum(f.severity == "bilgi" for f in findings), duration_ms=1))


def test_zero_errors_were_not_resolved_and_remaining_information_is_not_a_warning():
    job = SimpleNamespace(report=report(("hesap-dip-vergi-haric", "uyari"),
                                       ("hesap-dip-vergi-dahil", "uyari"), ("imza-yok", "bilgi")),
                          corrected_report=report(("imza-yok", "bilgi")))
    facts = validation_transitions(job)
    changes = facts["severity_changes"]
    assert changes["errors"] == {"initial": 0, "current": 0, "change": "unchanged",
                                  "net_decrease": 0, "net_increase": 0}
    assert changes["warnings"]["net_decrease"] == 2
    assert changes["information"]["change"] == "unchanged"
    remaining = [f for f in facts["finding_changes"] if f["current_count"]]
    assert remaining == [{"code": "imza-yok", "severity": "bilgi", "severity_label": "Bilgi",
                          "initial_count": 1, "current_count": 1, "removed_count": 0, "added_count": 0}]


def test_equal_net_counts_do_not_hide_removed_and_new_finding_codes():
    job = SimpleNamespace(report=report(("old", "uyari")), corrected_report=report(("new", "uyari")))
    facts = validation_transitions(job)
    assert facts["severity_changes"]["warnings"]["change"] == "unchanged"
    by_code = {f["code"]: f for f in facts["finding_changes"]}
    assert by_code["old"]["removed_count"] == 1 and by_code["new"]["added_count"] == 1


def test_partial_removal_and_new_information_keep_distinct_counts():
    job = SimpleNamespace(report=report(("same", "uyari"), ("same", "uyari")),
                          corrected_report=report(("same", "uyari"), ("new", "bilgi")))
    facts = validation_transitions(job)
    by_code = {f["code"]: f for f in facts["finding_changes"]}
    assert by_code["same"]["removed_count"] == 1 and by_code["same"]["current_count"] == 1
    assert by_code["new"]["added_count"] == 1 and by_code["new"]["severity_label"] == "Bilgi"


def test_without_revalidation_no_removals_are_inferred():
    facts = validation_transitions(SimpleNamespace(report=report(("still-open", "hata")), corrected_report=None))
    assert facts["severity_changes"]["errors"]["change"] == "unchanged"
    assert facts["finding_changes"][0]["removed_count"] == 0


@pytest.mark.parametrize("severity,label", [("hata", "Hata"), ("uyari", "Uyarı"), ("bilgi", "Bilgi")])
def test_severity_is_preserved_for_any_code(severity, label):
    job = SimpleNamespace(report=report(("unknown-future-code", severity)), corrected_report=None)
    row = validation_transitions(job)["finding_changes"][0]
    assert row["severity"] == severity and row["severity_label"] == label


@pytest.mark.parametrize("status,decision,available,reason", [
    ("applied", "propose", False, "already_applied"),
    ("approved", "propose", False, "already_approved"),
    ("rejected", "propose", False, "rejected"),
    ("proposed", "propose", True, "awaiting_user_approval"),
    ("proposed", "human_review", False, "plan_not_ready"),
])
def test_approval_reason_distinguishes_completed_rejected_pending_and_unready(status, decision, available, reason):
    facts = proposal_approval(SimpleNamespace(status=status, agent_plan={"decision": decision}))
    assert facts["available"] is available and facts["reason"] == reason
    if status == "applied":
        assert facts["description"] == "Uygulandı; yeniden onay gerekmez."
