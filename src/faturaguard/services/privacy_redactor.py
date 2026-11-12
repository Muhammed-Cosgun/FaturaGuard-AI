"""Bulut LLM sınırına giden bağlam için merkezi PII maskeleme katmanı.

Bu modül doğrulama sonucunu, özgün XML'i veya yerel raporu değiştirmez. Yalnızca
uzak bir LLM sağlayıcısına gönderilmeden hemen önce oluşturulan istemi temizler.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


class PrivacyRedactor:
    """Fatura bağlamında yaygın kişisel/ticari tanımlayıcıları maskeler."""

    _email = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    _iban = re.compile(r"\bTR(?:[ -]?[0-9A-Z]){24}\b", re.IGNORECASE)
    _phone = re.compile(
        r"(?<!\d)(?:\+?90[ .-]?)?(?:\(?0?5\d{2}\)?[ .-]?)?\d{3}[ .-]?\d{2}[ .-]?\d{2}(?!\d)"
    )
    _tax_or_identity = re.compile(r"(?<!\d)\d{10,11}(?!\d)")
    _account_number = re.compile(r"(?i)(hesap\s*no[: ]{0,8})[0-9]{6,}")

    # Bu anahtarların değeri, içerik hangi biçimde gelirse gelsin LLM sınırına taşınmaz.
    _sensitive_key_fragments = frozenset(
        {
            "xml",
            "iban",
            "vkn",
            "tckn",
            "tax_number",
            "identity_number",
            "email",
            "e_mail",
            "phone",
            "telefon",
            "address",
            "adres",
            "party_name",
            "person_name",
            "customer_name",
            "account_number",
            "bank_account",
        }
    )

    def redact_text(self, value: str) -> str:
        """Metindeki bilinen tanımlayıcıları sabit, denetlenebilir tokenlara dönüştürür."""

        redacted = self._email.sub("[MASKED_EMAIL]", value)
        redacted = self._iban.sub("[MASKED_IBAN]", redacted)
        redacted = self._phone.sub("[MASKED_PHONE]", redacted)
        redacted = self._account_number.sub(r"\1[MASKED_ACCOUNT]", redacted)
        return self._tax_or_identity.sub(self._mask_numeric_identifier, redacted)

    @staticmethod
    def _mask_numeric_identifier(match: re.Match[str]) -> str:
        return "[MASKED_TCKN]" if len(match.group(0)) == 11 else "[MASKED_VKN]"

    def redact_payload(self, value: Any) -> Any:
        """İç içe API payload'ını kopyalayarak hassas alan ve metinleri temizler."""

        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, item in value.items():
                normalized_key = str(key).casefold().replace("-", "_")
                if any(fragment in normalized_key for fragment in self._sensitive_key_fragments):
                    result[str(key)] = "[MASKED_FIELD]"
                else:
                    result[str(key)] = self.redact_payload(item)
            return result
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [self.redact_payload(item) for item in value]
        return value


privacy_redactor = PrivacyRedactor()
