"""Doğrulama bulgularını kullanıcı aksiyonuna göre önceliklendirir."""

from dataclasses import dataclass

from faturaguard.domain.validation import Priority, Severity


@dataclass(frozen=True, slots=True)
class PriorityDecision:
    priority: Priority
    reason: str


def prioritize(code: str, severity: Severity, source: str) -> PriorityDecision:
    """Kesin bir iş kuralıyle öncelik üretir; model tahmini kullanmaz."""
    if severity is Severity.ERROR:
        return PriorityDecision(Priority.CRITICAL, "Belge doğrulamasını durduran bir hata bulundu.")
    if code == "imza-yok":
        return PriorityDecision(
            Priority.HIGH,
            "Taslak için normal olabilir; GİB'e gönderim öncesinde elektronik imza gerektirir.",
        )
    if source in {"hesap", "sematron"}:
        return PriorityDecision(
            Priority.HIGH,
            "Belgenin tutarlılığını veya GİB iş kuralına uyumunu etkileyebilir.",
        )
    if severity is Severity.WARNING:
        return PriorityDecision(Priority.MEDIUM, "Gönderim öncesinde gözden geçirilmesi önerilir.")
    return PriorityDecision(
        Priority.LOW, "Bilgilendirme niteliğindedir; tek başına doğrulamayı durdurmaz."
    )
