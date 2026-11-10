from types import SimpleNamespace

from faturaguard.domain.validation import Priority, Severity
from faturaguard.services.validation_adapter import EfaturaKontrolAdapter


def test_adapter_maps_validator_report_to_application_contract() -> None:
    source_report = SimpleNamespace(
        gecerli=False,
        tur="fatura",
        profil="TEMELFATURA",
        tip="SATIS",
        sure_ms=4.54,
        paket={"surum": "0.1.0"},
        bulgular=[
            SimpleNamespace(
                kod="hesap-dip-satir",
                seviye="uyari",
                kaynak="hesap",
                mesaj="Satır toplamı uyuşmuyor.",
                satir=131,
                aciklama="Toplam satırlardan hesaplanır.",
                duzeltme="Toplamı yeniden hesaplayın.",
            )
        ],
        sayim=lambda level: {"hata": 1, "uyari": 1, "bilgi": 0}[level],
    )
    adapter = EfaturaKontrolAdapter(validator=lambda _: source_report)

    result = adapter.validate(b"<Invoice />", "ornek.xml")

    assert result.original_filename == "ornek.xml"
    assert result.summary.error_count == 1
    assert result.summary.duration_ms == 4.5
    assert result.findings[0].severity is Severity.WARNING
    assert result.findings[0].priority is Priority.HIGH
    assert result.findings[0].suggested_fix == "Toplamı yeniden hesaplayın."
