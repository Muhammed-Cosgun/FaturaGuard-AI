from pathlib import Path

import pytest
from efatura_kontrol import kod, sematron
from efatura_kontrol.kontrol import kontrol_et
from lxml import etree

from faturaguard.services.validation_adapter import EfaturaKontrolAdapter

BASELINE = Path("resources/fixtures/baseline_invoice.xml").read_bytes()
INVALID_ENVELOPE = Path("resources/fixtures/invalid_envelope.xml").read_bytes()


def _mutate(old: bytes, new: bytes) -> bytes:
    assert old in BASELINE, f"Temel fixture içinde hedef metin yok: {old!r}"
    return BASELINE.replace(old, new, 1)


def _with_xml_signature(signature: bytes) -> bytes:
    """Temel faturaya imza denetimlerinin okuyabileceği bir ds:Signature ekler."""
    return _mutate(
        b'xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">\n  <ext:UBLExtensions>',
        b'xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" '
        b'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" '
        b'xmlns:xades="http://uri.etsi.org/01903/v1.3.2#">\n  <ext:UBLExtensions>',
    ).replace(b"<n4:auto-generated_for_wildcard/>", signature, 1)


COMPLETE_SIGNATURE = (
    b"<ds:Signature><ds:SignedInfo><ds:Reference URI=\"\"/></ds:SignedInfo>"
    b"<ds:SignatureValue>test</ds:SignatureValue><ds:KeyInfo><ds:X509Data>"
    b"<ds:X509Certificate>test</ds:X509Certificate></ds:X509Data></ds:KeyInfo><ds:Object>"
    b"<xades:QualifyingProperties><xades:SignedProperties><xades:SignedSignatureProperties>"
    b"<xades:SigningTime>2026-01-01T00:00:00Z</xades:SigningTime>"
    b"<xades:SigningCertificate/></xades:SignedSignatureProperties></xades:SignedProperties>"
    b"</xades:QualifyingProperties></ds:Object></ds:Signature>"
)


@pytest.mark.parametrize(
    ("case_id", "document", "expected_code"),
    [
        (
            "xml-root",
            _mutate(b"<Invoice xsi:schemaLocation", b"<Document xsi:schemaLocation").replace(
                b"</Invoice>", b"</Document>", 1
            ),
            "xml-kok",
        ),
        ("ubl-version", _mutate(b"<cbc:UBLVersionID>2.1", b"<cbc:UBLVersionID>2.0"), "sch-UBLVersionIDCheck-1"),
        ("customization", _mutate(b"<cbc:CustomizationID>TR1.2", b"<cbc:CustomizationID>TR9.9"), "sch-CustomizationIDCheck-1"),
        ("schema-location", _mutate(b"UBL-Invoice-2.1.xsd", b"Gecersiz-Invoice.xsd"), "sch-ProfileIDCheck-4"),
        ("invoice-id", _mutate(b"GIB2009000000001", b"HATALI"), "sch-InvoiceIDCheck-1"),
        ("profile", _mutate(b"<cbc:ProfileID>TEMELFATURA", b"<cbc:ProfileID>GECERSIZ"), "sch-ProfileIDCheck-1"),
        ("uuid", _mutate(b"F47AC10B-58CC-4372-A567-0E02B2C3D479", b"GECERSIZ-UUID"), "sch-UUIDCheck-1"),
        ("date", _mutate(b"2009-01-05", b"2009-02-30"), "sch-TarihBicimi-1"),
        ("future-date", _mutate(b"2009-01-05", b"2099-01-05"), "sch-TimeCheck-1"),
        ("legacy-date", _mutate(b"2009-01-05", b"2000-01-05"), "sch-TimeCheck-2"),
        ("currency", _mutate(b"<cbc:DocumentCurrencyCode>TRY", b"<cbc:DocumentCurrencyCode>ZZZ"), "sch-CurrencyCodeCheck-1"),
        (
            "exchange-rate-required",
            _mutate(b"<cbc:DocumentCurrencyCode>TRY", b"<cbc:DocumentCurrencyCode>USD"),
            "sch-CurrencyCodeCheck-6",
        ),
        ("amount-currency", _mutate(b'<cbc:TaxAmount currencyID="TRY">2.73', b'<cbc:TaxAmount currencyID="ZZZ">2.73'), "sch-GeneralCurrencyIDCheck-1"),
        ("decimal", _mutate(b'<cbc:TaxInclusiveAmount currencyID="TRY">17.88', b'<cbc:TaxInclusiveAmount currencyID="TRY">17.888'), "sch-decimalCheck-1"),
        ("unit", _mutate(b'unitCode="KWH"', b'unitCode="ADET"'), "sch-GeneralUnitCodeCheck-1"),
        ("unit-missing", _mutate(b' unitCode="KWH"', b""), "sch-InvoicedQuantityCheck-1"),
        ("copy-indicator", _mutate(b"<cbc:CopyIndicator>false", b"<cbc:CopyIndicator>true"), "sch-CopyIndicatorCheck-1"),
        ("invoice-type", _mutate(b"<cbc:InvoiceTypeCode>SATIS", b"<cbc:InvoiceTypeCode>HATALI"), "sch-InvoiceTypeCodeCheck-1"),
        ("tax-code", _mutate(b"<cbc:TaxTypeCode>0015", b"<cbc:TaxTypeCode>9999"), "sch-TaxTypeCheck-1"),
        ("party-scheme", _mutate(b' schemeID="TCKN">10000000146', b' schemeID="HATALI">10000000146'), "sch-PartyIdentificationSchemeIDCheck-1"),
        (
            "party-vkn",
            _mutate(
                b'<cac:AccountingSupplierParty><cac:Party><cbc:WebsiteURI>http://www.aaa.com.tr/</cbc:WebsiteURI><cac:PartyIdentification><cbc:ID schemeID="VKN">1288331521',
                b'<cac:AccountingSupplierParty><cac:Party><cbc:WebsiteURI>http://www.aaa.com.tr/</cbc:WebsiteURI><cac:PartyIdentification><cbc:ID schemeID="VKN">123',
            ),
            "sch-PartyIdentificationTCKNVKNCheck-1",
        ),
        ("party-tckn", _mutate(b' schemeID="TCKN">10000000146', b' schemeID="TCKN">123'), "sch-PartyIdentificationTCKNVKNCheck-2"),
        (
            "party-required-identity",
            _mutate(
                b'<cac:AccountingSupplierParty><cac:Party><cbc:WebsiteURI>http://www.aaa.com.tr/</cbc:WebsiteURI><cac:PartyIdentification><cbc:ID schemeID="VKN">1288331521',
                b'<cac:AccountingSupplierParty><cac:Party><cbc:WebsiteURI>http://www.aaa.com.tr/</cbc:WebsiteURI><cac:PartyIdentification><cbc:ID schemeID="MUSTERINO">1288331521',
            ),
            "sch-PartyIdentificationPartyNamePersonCheck-1",
        ),
        (
            "party-name-required",
            _mutate(
                "<cac:PartyName><cbc:Name>AAA Anonim Şirketi</cbc:Name></cac:PartyName>".encode(),
                b"",
            ),
            "sch-PartyIdentificationPartyNamePersonCheck-3",
        ),
        (
            "party-person-required",
            _mutate(
                b"<cac:Person><cbc:FirstName>Ali</cbc:FirstName><cbc:FamilyName>YILMAZ</cbc:FamilyName></cac:Person>",
                b"",
            ),
            "sch-PartyIdentificationPartyNamePersonCheck-5",
        ),
        (
            "party-person-name-required",
            _mutate(b"<cbc:FirstName>Ali</cbc:FirstName>", b"<cbc:FirstName></cbc:FirstName>"),
            "sch-PartyIdentificationPartyNamePersonCheck-6",
        ),
        ("return-reference", _mutate(b"<cbc:InvoiceTypeCode>SATIS", b"<cbc:InvoiceTypeCode>IADE"), "sch-IADEInvioceCheck-1"),
        ("signature-scheme", _mutate(b'<cac:Signature><cbc:ID schemeID="VKN_TCKN"', b'<cac:Signature><cbc:ID schemeID="HATALI"'), "sch-SignatureCheck-1"),
        (
            "line-calculation",
            _mutate(
                b'<cbc:InvoicedQuantity unitCode="KWH">101</cbc:InvoicedQuantity><cbc:LineExtensionAmount currencyID="TRY">15.15',
                b'<cbc:InvoicedQuantity unitCode="KWH">101</cbc:InvoicedQuantity><cbc:LineExtensionAmount currencyID="TRY">15.13',
            ),
            "hesap-satir",
        ),
        (
            "tax-calculation",
            _mutate(
                b'<cbc:TaxableAmount currencyID="TRY">15.15</cbc:TaxableAmount><cbc:TaxAmount currencyID="TRY">2.73</cbc:TaxAmount><cbc:Percent>18.0',
                b'<cbc:TaxableAmount currencyID="TRY">15.15</cbc:TaxableAmount><cbc:TaxAmount currencyID="TRY">2.00</cbc:TaxAmount><cbc:Percent>18.0',
            ),
            "hesap-vergi",
        ),
        (
            "zero-vat-exemption-reason",
            BASELINE.replace(b'<cbc:TaxAmount currencyID="TRY">2.73', b'<cbc:TaxAmount currencyID="TRY">0.00', 2),
            "sch-TaxExemptionReasonCheck-1",
        ),
        (
            "invalid-exemption-code",
            _mutate(
                b"<cac:TaxCategory><cac:TaxScheme>",
                b"<cac:TaxCategory><cbc:TaxExemptionReason>Exemption</cbc:TaxExemptionReason>"
                b"<cbc:TaxExemptionReasonCode>999</cbc:TaxExemptionReasonCode><cac:TaxScheme>",
            ),
            "sch-TaxExemptionReasonCodeCheck-2",
        ),
        (
            "incompatible-exemption-invoice-type",
            _mutate(
                b"<cac:TaxCategory><cac:TaxScheme>",
                b"<cac:TaxCategory><cbc:TaxExemptionReason>Exemption</cbc:TaxExemptionReason>"
                b"<cbc:TaxExemptionReasonCode>001</cbc:TaxExemptionReasonCode><cac:TaxScheme>",
            ),
            "sch-TaxExemptionReasonCodeCheck-3",
        ),
        (
            "withholding-type",
            _mutate(
                b"</cac:TaxTotal>\n  <cac:LegalMonetaryTotal>",
                b"</cac:TaxTotal>\n  <cac:WithholdingTaxTotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount></cac:WithholdingTaxTotal>\n  <cac:LegalMonetaryTotal>",
            ),
            "sch-GeneralWithholdingTaxTotalCheck-1",
        ),
        (
            "withholding-invalid-code",
            _mutate(
                b"</cac:TaxTotal>\n  <cac:LegalMonetaryTotal>",
                b"</cac:TaxTotal><cac:WithholdingTaxTotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount>"
                b"<cac:TaxSubtotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount><cbc:Percent>50</cbc:Percent>"
                b"<cac:TaxCategory><cac:TaxScheme><cbc:TaxTypeCode>999</cbc:TaxTypeCode></cac:TaxScheme>"
                b"</cac:TaxCategory></cac:TaxSubtotal></cac:WithholdingTaxTotal>\n  <cac:LegalMonetaryTotal>",
            ),
            "sch-WithholdingTaxTotalCheck-2",
        ),
        (
            "withholding-invalid-percent",
            _mutate(
                b"</cac:TaxTotal>\n  <cac:LegalMonetaryTotal>",
                b"</cac:TaxTotal><cac:WithholdingTaxTotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount>"
                b"<cac:TaxSubtotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount><cbc:Percent>99</cbc:Percent>"
                b"<cac:TaxCategory><cac:TaxScheme><cbc:TaxTypeCode>601</cbc:TaxTypeCode></cac:TaxScheme>"
                b"</cac:TaxCategory></cac:TaxSubtotal></cac:WithholdingTaxTotal>\n  <cac:LegalMonetaryTotal>",
            ),
            "sch-WithholdingTaxTotalCheck-3",
        ),
        (
            "payment-means-code",
            _mutate(
                b"  <cac:PaymentTerms>",
                b"  <cac:PaymentMeans><cbc:PaymentMeansCode>999</cbc:PaymentMeansCode></cac:PaymentMeans>\n  <cac:PaymentTerms>",
            ),
            "sch-PaymentMeansCodeCheck-1",
        ),
        (
            "public-invoice-iban",
            _mutate(b"<cbc:ProfileID>TEMELFATURA", b"<cbc:ProfileID>KAMU"),
            "sch-KamuFaturaCheck-1",
        ),
        (
            "withholding-calculation",
            _mutate(
                b"</cac:TaxTotal>\n  <cac:LegalMonetaryTotal>",
                b"</cac:TaxTotal><cac:WithholdingTaxTotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount>"
                b"<cac:TaxSubtotal><cbc:TaxAmount currencyID=\"TRY\">1.37</cbc:TaxAmount><cbc:Percent>50</cbc:Percent>"
                b"<cac:TaxCategory><cac:TaxScheme><cbc:TaxTypeCode>601</cbc:TaxTypeCode></cac:TaxScheme>"
                b"</cac:TaxCategory></cac:TaxSubtotal></cac:WithholdingTaxTotal>\n  <cac:LegalMonetaryTotal>",
            ),
            "hesap-tevkifat-toplam",
        ),
        (
            "withholding-subtotal-calculation",
            _mutate(
                b"</cac:TaxTotal>\n  <cac:LegalMonetaryTotal>",
                b"</cac:TaxTotal><cac:WithholdingTaxTotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount>"
                b"<cac:TaxSubtotal><cbc:TaxAmount currencyID=\"TRY\">1.00</cbc:TaxAmount><cbc:Percent>50</cbc:Percent>"
                b"<cac:TaxCategory><cac:TaxScheme><cbc:TaxTypeCode>601</cbc:TaxTypeCode></cac:TaxScheme>"
                b"</cac:TaxCategory></cac:TaxSubtotal></cac:WithholdingTaxTotal>\n  <cac:LegalMonetaryTotal>",
            ),
            "hesap-tevkifat",
        ),
        (
            "xades-structure",
            _with_xml_signature(b"<ds:Signature/>"),
            "sch-XadesSignatureCheckForInvoice-1",
        ),
        ("signature-structure", _with_xml_signature(b"<ds:Signature/>"), "imza-yapi"),
        ("xades-key-info", _with_xml_signature(b"<ds:Signature/>"), "sch-XadesSignatureCheckForInvoice-2"),
        (
            "xades-signing-time",
            _with_xml_signature(b"<ds:Signature><ds:Object/></ds:Signature>"),
            "sch-XadesSignatureCheckForInvoice-5",
        ),
        (
            "signature-reference",
            _with_xml_signature(COMPLETE_SIGNATURE.replace(b'URI=""', b'URI="#missing"')),
            "imza-referans",
        ),
        ("signature-present", _with_xml_signature(COMPLETE_SIGNATURE), "imza-var"),
        (
            "tax-inclusive",
            _mutate(
                b'<cbc:TaxInclusiveAmount currencyID="TRY">17.88',
                b'<cbc:TaxInclusiveAmount currencyID="TRY">17.00',
            ),
            "hesap-dip-vergi-dahil",
        ),
        ("payable", _mutate(b"<cbc:PayableAmount currencyID=\"TRY\">17.88", b"<cbc:PayableAmount currencyID=\"TRY\">17.00"), "hesap-dip-odenecek"),
        (
            "document-tax-total",
            _mutate(
                b'<cac:TaxTotal><cbc:TaxAmount currencyID="TRY">2.73',
                b'<cac:TaxTotal><cbc:TaxAmount currencyID="TRY">2.00',
            ),
            "hesap-vergi-toplam",
        ),
        (
            "amount-currency-mismatch",
            _mutate(
                b'<cbc:PriceAmount currencyID="TRY">0.15',
                b'<cbc:PriceAmount currencyID="USD">0.15',
            ),
            "hesap-para-birimi",
        ),
        (
            "document-charge-total",
            _mutate(
                b'  <cac:TaxTotal>',
                b'  <cac:AllowanceCharge><cbc:ChargeIndicator>true</cbc:ChargeIndicator>'
                b'<cbc:Amount currencyID="TRY">1.00</cbc:Amount></cac:AllowanceCharge>\n  <cac:TaxTotal>',
            ).replace(
                b'<cbc:TaxExclusiveAmount currencyID="TRY">15.15',
                b'<cbc:ChargeTotalAmount currencyID="TRY">0.00</cbc:ChargeTotalAmount>'
                b'<cbc:TaxExclusiveAmount currencyID="TRY">15.15',
                1,
            ),
            "hesap-dip-artirim",
        ),
    ],
)
def test_real_mutated_xml_fixture_produces_expected_validator_code(
    case_id: str, document: bytes, expected_code: str
) -> None:
    report = EfaturaKontrolAdapter().validate(document, f"{case_id}.xml")

    assert expected_code in {finding.code for finding in report.findings}


@pytest.mark.parametrize(
    "expected_code",
    ["sch-DocumentCheck-3", "sch-TypeVersionCheck-1", "sch-ContactCheck-3"],
)
def test_real_envelope_fixture_produces_expected_header_code(expected_code: str) -> None:
    report = kontrol_et(INVALID_ENVELOPE)

    assert expected_code in {finding.kod for finding in report.bulgular}


def test_earsiv_profile_rule_is_checked_with_the_librarys_earsiv_mode() -> None:
    report = kontrol_et(BASELINE, tur="earsiv")

    assert "sch-ProfileIDCheck-2" in {finding.kod for finding in report.bulgular}


def test_generic_xsd_and_evaluation_failure_handlers_are_covered() -> None:
    """Bazı katalog kodları kural değil, hata/eşleme katmanının güvenli yollarıdır."""
    assert kod.acikla("xsd") is not None

    evaluation_error = etree.fromstring(
        b'<svrl:error xmlns:svrl="http://purl.oclc.org/dsdl/svrl" code="FORG0001">invalid value</svrl:error>'
    )
    application_response_assert = etree.fromstring(
        b'<svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" id="ARSignatureCheck-1">'
        b"<svrl:text>Uygulama yaniti imzasi zorunludur.</svrl:text></svrl:failed-assert>"
    )

    assert sematron._degerlendirme_hatasi(evaluation_error).kod == "sch-degerlendirme"
    assert sematron._bulgu(None, application_response_assert, "hata").kod == "sch-ARSignatureCheck-1"
