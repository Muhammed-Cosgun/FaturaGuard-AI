import json
from pathlib import Path

from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.services.agent_workflow import SourceBackedAgent

MATRIX_PATH = Path("resources/evaluation/error_coverage_matrix.json")


def test_error_coverage_matrix_has_real_cases_across_core_families() -> None:
    cases = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    real_families = {item["family"] for item in cases if item["status"] == "real_xml_verified"}

    assert {"XML", "XSD", "Aritmetik", "İmza"} <= real_families
    assert len([item for item in cases if item["status"] == "real_xml_verified"]) >= 18


def test_each_coverage_matrix_code_has_a_nonempty_safe_retrieval_query() -> None:
    cases = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    for item in cases:
        finding = Finding(
            code=item["code"], severity=Severity.ERROR, priority=Priority.CRITICAL,
            priority_reason="Test", source="sematron",
            message="Bu metin retrieval sorgusuna taşınmamalıdır.",
        )
        query = SourceBackedAgent._trusted_retrieval_query(finding)
        assert query.startswith("UBL-TR")
        assert "taşınmamalıdır" not in query
