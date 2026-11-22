import json
from pathlib import Path

import pytest

from faturaguard.services.chat_quality import (
    INTERNAL_FIELDS,
    chat_quality_issues,
    prepare_user_answer,
)
from faturaguard.services.chat_quality_evaluation import evaluate_quality_cases, quality_scenario

CASES = json.loads((Path(__file__).resolve().parents[1] / "resources/evaluation/chat_answer_quality_cases.json")
                   .read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_quality_contract(case):
    assert chat_quality_issues(case["answer"], quality_scenario(case["scenario"])) == case["expected"]


@pytest.mark.parametrize("field", INTERNAL_FIELDS)
def test_internal_fields_are_not_allowed_in_final_user_prose(field):
    assert "technical_field_leak" in chat_quality_issues(f"{field}: false", quality_scenario("pending"))


def test_quality_report_records_both_good_and_bad_cases_without_answer_text():
    report = evaluate_quality_cases(CASES)
    assert report["passed"] == report["case_count"] == len(CASES)
    assert report["kind"] == "offline_guard_contract"
    assert "answer" not in report["results"][0]


@pytest.mark.parametrize("scenario,raw,expected", [
    ("applied", "approval_available: false", "onaylanabilir hazır teklif yok"),
    ("pending", '"approval_available": true', "sonuç ekranında onaylanabilir bir teklif var"),
    ("applied", "already_applied", "uygulandı"),
    ("pending", "awaiting_user_approval", "kullanıcı onayı bekliyor"),
    ("unready", "plan_not_ready", "plan henüz onaya hazır değil"),
])
def test_only_record_matching_state_values_get_human_readable_text(scenario, raw, expected):
    assert prepare_user_answer(raw, quality_scenario(scenario)) == expected


@pytest.mark.parametrize("scenario,raw", [
    ("applied", "approval_available: true"), ("pending", "approval_available: false"),
    ("pending", "already_applied"), ("applied", "awaiting_user_approval"),
    ("applied", "plan_not_ready"), ("applied", "workflow_state: unknown"),
])
def test_conflicting_or_unknown_fields_are_not_silently_sanitized(scenario, raw):
    job = quality_scenario(scenario)
    result = prepare_user_answer(raw, job)
    assert result == raw and "technical_field_leak" in chat_quality_issues(result, job)


def test_plain_text_normalization_preserves_xml_and_amount_tokens_without_rendering_html():
    raw = '**Bilgi** kaydı aynı. [VALUE_1] → [VALUE_2]. <script>örnek</script>'
    result = prepare_user_answer(raw, quality_scenario("applied"))
    assert result == 'Bilgi kaydı aynı. [VALUE_1] → [VALUE_2]. <script>örnek</script>'

@pytest.mark.parametrize('answer', [
    'Başka bir işlem yapmanız gerekmez.',
    'Herhangi bir işlem yapmanıza gerek yok.',
])
def test_remaining_information_prevents_blanket_completion_claim(answer):
    assert 'remaining_findings_completion_claim' in chat_quality_issues(answer, quality_scenario('applied'))


def test_no_new_approval_is_distinct_from_no_remaining_action():
    assert not chat_quality_issues('Yeniden onay gerekmiyor; kalan bilgi kaydını inceleyin.', quality_scenario('applied'))
