from faturaguard.services.privacy_redactor import PrivacyRedactor


def test_redactor_masks_common_invoice_identifiers() -> None:
    text = (
        "VKN 1234567890, TCKN 12345678901, IBAN TR33 0006 1005 1978 6457 8413 26, "
        "e-posta kisi@example.com, telefon +90 532 123 45 67"
    )

    result = PrivacyRedactor().redact_text(text)

    assert "1234567890" not in result
    assert "12345678901" not in result
    assert "TR33" not in result
    assert "kisi@example.com" not in result
    assert "532 123" not in result
    assert "[MASKED_VKN]" in result
    assert "[MASKED_TCKN]" in result
    assert "[MASKED_IBAN]" in result
    assert "[MASKED_EMAIL]" in result
    assert "[MASKED_PHONE]" in result


def test_redactor_suppresses_sensitive_mapping_keys_recursively() -> None:
    payload = {
        "finding": {"code": "xsd-test", "address": "Atatürk Cd. 10"},
        "customer_name": "Ayşe Yılmaz",
        "evidence": [{"text": "VKN 1234567890", "page": 47}],
    }

    result = PrivacyRedactor().redact_payload(payload)

    assert result["customer_name"] == "[MASKED_FIELD]"
    assert result["finding"]["address"] == "[MASKED_FIELD]"
    assert result["evidence"][0]["text"] == "VKN [MASKED_VKN]"
