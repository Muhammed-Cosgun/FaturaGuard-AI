from pathlib import Path

import pytest

from faturaguard.services.validation_adapter import EfaturaKontrolAdapter

BASELINE = Path("resources/fixtures/baseline_invoice.xml").read_bytes()


def _mutate(old: bytes, new: bytes) -> bytes:
    assert old in BASELINE, f"Temel fixture içinde hedef metin yok: {old!r}"
    return BASELINE.replace(old, new, 1)


@pytest.mark.parametrize(
    ("case_id", "document", "expected_code"),
    [
        ("uuid", _mutate(b"F47AC10B-58CC-4372-A567-0E02B2C3D479", b"GECERSIZ-UUID"), "sch-UUIDCheck-1"),
        ("date", _mutate(b"2009-01-05", b"2009-02-30"), "sch-TarihBicimi-1"),
        ("currency", _mutate(b"<cbc:DocumentCurrencyCode>TRY", b"<cbc:DocumentCurrencyCode>ZZZ"), "sch-CurrencyCodeCheck-1"),
        ("unit", _mutate(b'unitCode="KWH"', b'unitCode="ADET"'), "sch-GeneralUnitCodeCheck-1"),
        ("tax-code", _mutate(b"<cbc:TaxTypeCode>0015", b"<cbc:TaxTypeCode>9999"), "sch-TaxTypeCheck-1"),
        ("payable", _mutate(b"<cbc:PayableAmount currencyID=\"TRY\">17.88", b"<cbc:PayableAmount currencyID=\"TRY\">17.00"), "hesap-dip-odenecek"),
    ],
)
def test_real_mutated_xml_fixture_produces_expected_validator_code(
    case_id: str, document: bytes, expected_code: str
) -> None:
    report = EfaturaKontrolAdapter().validate(document, f"{case_id}.xml")

    assert expected_code in {finding.code for finding in report.findings}
