import json
from pathlib import Path

import pytest

from faturaguard.services.chat_quality import INTERNAL_FIELDS, chat_quality_issues
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
