"""Tarayıcı demosu için tekil aritmetik hata XML'leri üretir.

Kaynak fatura değişmez; çıktılar ``data/demo-fixtures`` altında çalışma örneği
olarak oluşturulur. Her mutasyon, yazılmadan önce gerçek doğrulayıcıyla kontrol
edilir. Böylece sunumda doğru agent düzeltme rotası gösterilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faturaguard.services.validation_adapter import EfaturaKontrolAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE = PROJECT_ROOT / "resources" / "fixtures" / "baseline_invoice.xml"
OUTPUT_DIR = PROJECT_ROOT / "data" / "demo-fixtures"


@dataclass(frozen=True)
class ArithmeticDemoCase:
    filename: str
    old: bytes
    new: bytes
    expected_finding: str


CASES = (
    ArithmeticDemoCase(
        "demo_tax_exclusive_error.xml",
        b'<cbc:TaxExclusiveAmount currencyID="TRY">15.15',
        b'<cbc:TaxExclusiveAmount currencyID="TRY">15.00',
        "hesap-dip-vergi-haric",
    ),
    ArithmeticDemoCase(
        "demo_tax_inclusive_error.xml",
        b'<cbc:TaxInclusiveAmount currencyID="TRY">17.88',
        b'<cbc:TaxInclusiveAmount currencyID="TRY">17.00',
        "hesap-dip-vergi-dahil",
    ),
    ArithmeticDemoCase(
        "demo_payable_error.xml",
        b'<cbc:PayableAmount currencyID="TRY">17.88',
        b'<cbc:PayableAmount currencyID="TRY">17.00',
        "hesap-dip-odenecek",
    ),
)


def generate(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    validator = EfaturaKontrolAdapter()
    try:
        return _generate(output_dir, validator)
    finally:
        validator.close()


def _generate(output_dir: Path, validator) -> list[Path]:
    baseline = BASELINE.read_bytes()
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for case in CASES:
        if case.old not in baseline:
            raise RuntimeError(f"Baseline target missing for {case.filename}")
        document = baseline.replace(case.old, case.new, 1)
        findings = {item.code for item in validator.validate(document, case.filename).findings}
        if case.expected_finding not in findings:
            raise RuntimeError(
                f"Fixture validation failed: expected {case.expected_finding}, got {sorted(findings)}"
            )
        destination = output_dir / case.filename
        temporary = destination.with_suffix(".uploading")
        temporary.write_bytes(document)
        temporary.replace(destination)
        generated.append(destination)
    return generated


def main() -> None:
    for fixture in generate():
        print(f"Generated and validated: {fixture.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
