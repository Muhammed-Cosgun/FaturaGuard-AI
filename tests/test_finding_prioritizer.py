import pytest

from faturaguard.domain.validation import Priority, Severity
from faturaguard.services.finding_prioritizer import prioritize


@pytest.mark.parametrize(
    ("code", "severity", "source", "expected"),
    [
        ("xml-bicim", Severity.ERROR, "xml", Priority.CRITICAL),
        ("hesap-dip-satir", Severity.WARNING, "hesap", Priority.HIGH),
        ("imza-yok", Severity.INFO, "imza", Priority.HIGH),
        ("genel-bilgi", Severity.INFO, "xml", Priority.LOW),
    ],
)
def test_prioritizer_uses_deterministic_business_rules(code, severity, source, expected) -> None:
    assert prioritize(code, severity, source).priority is expected
