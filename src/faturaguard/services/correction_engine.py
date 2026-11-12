"""İzin listesine dayalı, düşük riskli XML düzeltme kuralları."""

import re
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from lxml import etree

from faturaguard.domain.correction import CorrectionProposal, CorrectionStatus
from faturaguard.domain.validation import ValidationReport

CAC = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
CBC = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
LINE_TOTAL_PATH = "cac:LegalMonetaryTotal/cbc:LineExtensionAmount"
TAX_EXCLUSIVE_PATH = "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount"
TAX_INCLUSIVE_PATH = "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"
PAYABLE_PATH = "cac:LegalMonetaryTotal/cbc:PayableAmount"

_LEGAL_TOTAL_ELEMENTS = {
    "recalculate-line-extension-total": (
        "LineExtensionAmount",
        LINE_TOTAL_PATH,
        "hesap-dip-satir",
        "Mal/hizmet dip toplamını satırlardan yeniden hesapla",
        "Yalnızca mevcut InvoiceLine tutarları toplanır; satır, taraf ve vergi bilgileri değiştirilmez.",
    ),
    "recalculate-tax-exclusive-total": (
        "TaxExclusiveAmount",
        TAX_EXCLUSIVE_PATH,
        "hesap-dip-vergi-haric",
        "Vergi hariç dip toplamı yeniden hesapla",
        "Yalnızca mevcut dip toplam, indirim ve artırım tutarları kullanılır; satır, taraf ve vergi bilgileri değiştirilmez.",
    ),
    "recalculate-tax-inclusive-total": (
        "TaxInclusiveAmount",
        TAX_INCLUSIVE_PATH,
        "hesap-dip-vergi-dahil",
        "Vergiler dahil dip toplamı yeniden hesapla",
        "Yalnızca mevcut vergi hariç dip toplam ve belge vergi tutarı kullanılır; vergi satırları değiştirilmez.",
    ),
    "recalculate-payable-total": (
        "PayableAmount",
        PAYABLE_PATH,
        "hesap-dip-odenecek",
        "Ödenecek tutarı yeniden hesapla",
        "Yalnızca mevcut vergiler dahil tutar, tevkifat ve yuvarlama tutarı kullanılır; ödeme bilgileri değiştirilmez.",
    ),
}

_DEPENDENCY_FINDINGS = {
    "recalculate-tax-exclusive-total": {
        "hesap-dip-satir",
        "hesap-dip-indirim",
        "hesap-dip-artirim",
    },
    "recalculate-tax-inclusive-total": {
        "hesap-dip-vergi-haric",
        "hesap-vergi",
        "hesap-vergi-toplam",
    },
    "recalculate-payable-total": {
        "hesap-dip-vergi-dahil",
        "hesap-tevkifat",
        "hesap-tevkifat-toplam",
    },
}


class CorrectionNotApplicableError(ValueError):
    """Teklif mevcut XML durumuna güvenle uygulanamadığında yükseltilir."""


class SafeCorrectionEngine:
    """Yalnızca açıkça tanımlanmış kuralları teklif eder ve uygular."""

    def propose(self, xml_bytes: bytes, report: ValidationReport) -> list[CorrectionProposal]:
        finding_codes = {finding.code for finding in report.findings}
        proposals: list[CorrectionProposal] = []
        for rule_id, (_element, path, finding_code, title, rationale) in _LEGAL_TOTAL_ELEMENTS.items():
            if finding_code not in finding_codes:
                continue
            # Alt toplam bozuksa üst toplamı mevcut, hatalı değerden hesaplamayız.
            # Agent bu belgeyi önce düşük seviyeli düzeltmeye ve yeniden doğrulamaya yönlendirir.
            if finding_codes.intersection(_DEPENDENCY_FINDINGS.get(rule_id, set())):
                continue
            try:
                before, after = self._values_for_rule(xml_bytes, rule_id)
            except CorrectionNotApplicableError:
                continue
            if before == after:
                continue
            proposals.append(
                CorrectionProposal(
                    proposal_id=uuid4().hex,
                    rule_id=rule_id,
                    finding_code=finding_code,
                    title=title,
                    rationale=rationale,
                    target_path=path,
                    before=before,
                    after=after,
                )
            )
        return proposals

    def apply(self, xml_bytes: bytes, proposal: CorrectionProposal) -> bytes:
        if proposal.status is not CorrectionStatus.APPROVED:
            raise CorrectionNotApplicableError("Kullanıcı onayı olmayan düzeltme uygulanamaz.")
        if proposal.rule_id not in _LEGAL_TOTAL_ELEMENTS:
            raise CorrectionNotApplicableError("İzin listesinde olmayan düzeltme kuralı istendi.")
        element, _, _, _, _ = _LEGAL_TOTAL_ELEMENTS[proposal.rule_id]
        before, after = self._values_for_rule(xml_bytes, proposal.rule_id)
        if before != proposal.before or after != proposal.after:
            raise CorrectionNotApplicableError(
                "Belge teklifi oluşturulduktan sonra değişmiş görünüyor."
            )
        return self._replace_legal_total_value(xml_bytes, element, before, after)

    @staticmethod
    def _replace_line_total_value(xml_bytes: bytes, before: str, after: str) -> bytes:
        """Geriye dönük uyumluluk için LineExtensionAmount alanını değiştirir."""
        return SafeCorrectionEngine._replace_legal_total_value(
            xml_bytes, "LineExtensionAmount", before, after
        )

    @staticmethod
    def _replace_legal_total_value(
        xml_bytes: bytes, element: str, before: str, after: str
    ) -> bytes:
        """Yalnızca onaylanan dip toplam metnini değiştirir; XML'i yeniden yazmaz."""

        if element not in {item[0] for item in _LEGAL_TOTAL_ELEMENTS.values()}:
            raise CorrectionNotApplicableError("Düzeltilecek alan izin listesinde değil.")
        pattern = re.compile(
            rb"(?P<head>"
            rb"<(?:[A-Za-z_][\w.-]*:)?LegalMonetaryTotal\b[^>]*>"
            rb".*?"
            + rb"<(?P<tag>(?:[A-Za-z_][\w.-]*:)?"
            + element.encode("ascii")
            + rb")\b[^>]*>"
            + rb")"
            + rb"(?P<value>[^<]*)"
            + rb"(?P<tail></(?P=tag)\s*>)",
            re.DOTALL,
        )

        match = pattern.search(xml_bytes)
        if match is None:
            raise CorrectionNotApplicableError("Düzeltilecek dip toplam alanı bulunamadı.")
        try:
            current = match.group("value").decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise CorrectionNotApplicableError(
                "Dip toplam alanı güvenle değiştirilemedi."
            ) from error
        if current != before:
            raise CorrectionNotApplicableError(
                "Düzeltilecek dip toplam alanı teklif oluşturulduktan sonra değişmiş görünüyor."
            )
        leading = match.group("value")[
            : len(match.group("value")) - len(match.group("value").lstrip())
        ]
        trailing = match.group("value")[len(match.group("value").rstrip()) :]
        replacement = (
            match.group("head") + leading + after.encode("ascii") + trailing + match.group("tail")
        )
        return xml_bytes[: match.start()] + replacement + xml_bytes[match.end() :]

    @staticmethod
    def _line_extension_values(xml_bytes: bytes) -> tuple[str, str]:
        return SafeCorrectionEngine._values_for_rule(xml_bytes, "recalculate-line-extension-total")

    @staticmethod
    def _values_for_rule(xml_bytes: bytes, rule_id: str) -> tuple[str, str]:
        try:
            root = etree.fromstring(
                xml_bytes, parser=etree.XMLParser(resolve_entities=False, no_network=True)
            )
        except etree.XMLSyntaxError as error:
            raise CorrectionNotApplicableError(
                "İyi biçimli olmayan XML için bu düzeltme uygulanamaz."
            ) from error
        element, _, _, _, _ = _LEGAL_TOTAL_ELEMENTS[rule_id]
        target = root.find(f"{CAC}LegalMonetaryTotal/{CBC}{element}")
        if target is None or not target.text:
            raise CorrectionNotApplicableError("Düzeltilecek dip toplam alanı bulunamadı.")
        try:
            if rule_id == "recalculate-line-extension-total":
                line_amounts = root.findall(f"{CAC}InvoiceLine/{CBC}LineExtensionAmount")
                if not line_amounts:
                    raise CorrectionNotApplicableError("Fatura satırları bulunamadı.")
                total = sum((_decimal(item) for item in line_amounts), Decimal("0"))
            elif rule_id == "recalculate-tax-exclusive-total":
                line_total = _decimal_required(
                    root.find(f"{CAC}LegalMonetaryTotal/{CBC}LineExtensionAmount")
                )
                allowance, charge = _allowance_charge_totals(root)
                total = line_total - allowance + charge
            elif rule_id == "recalculate-tax-inclusive-total":
                tax_exclusive = _decimal_required(
                    root.find(f"{CAC}LegalMonetaryTotal/{CBC}TaxExclusiveAmount")
                )
                tax_amounts = root.findall(f"{CAC}TaxTotal/{CBC}TaxAmount")
                if not tax_amounts:
                    raise CorrectionNotApplicableError("Belge vergi toplamı bulunamadı.")
                total = tax_exclusive + sum((_decimal(item) for item in tax_amounts), Decimal("0"))
            elif rule_id == "recalculate-payable-total":
                tax_inclusive = _decimal_required(
                    root.find(f"{CAC}LegalMonetaryTotal/{CBC}TaxInclusiveAmount")
                )
                withholding = sum(
                    (_decimal(item) for item in root.findall(f"{CAC}WithholdingTaxTotal/{CBC}TaxAmount")),
                    Decimal("0"),
                )
                rounding = _decimal_optional(
                    root.find(f"{CAC}LegalMonetaryTotal/{CBC}PayableRoundingAmount")
                )
                total = tax_inclusive - withholding + rounding
            else:  # pragma: no cover - allowlist kontrolü yukarıda yapılır.
                raise CorrectionNotApplicableError("İzin listesinde olmayan düzeltme kuralı istendi.")
        except (InvalidOperation, ValueError) as error:
            raise CorrectionNotApplicableError("Dip toplamdan güvenli hesaplama yapılamadı.") from error
        return target.text.strip(), format(total.quantize(Decimal("0.01")), "f")


def _decimal(element: etree._Element) -> Decimal:
    return Decimal((element.text or "").strip())


def _decimal_required(element: etree._Element | None) -> Decimal:
    if element is None or not element.text:
        raise CorrectionNotApplicableError("Düzeltme için gerekli dip toplam alanı bulunamadı.")
    return _decimal(element)


def _decimal_optional(element: etree._Element | None) -> Decimal:
    return Decimal("0") if element is None or not element.text else _decimal(element)


def _allowance_charge_totals(root: etree._Element) -> tuple[Decimal, Decimal]:
    """Kütüphanedeki dip toplam hesabıyla uyumlu belge indirim/artırımını döndürür."""

    allowance = Decimal("0")
    charge = Decimal("0")
    for item in root.findall(f"{CAC}AllowanceCharge"):
        indicator = (item.findtext(f"{CBC}ChargeIndicator") or "").strip().casefold()
        amount = item.find(f"{CBC}Amount")
        if indicator not in {"true", "false"} or amount is None:
            raise CorrectionNotApplicableError("Belge indirimi veya artırımından güvenli hesaplama yapılamadı.")
        if indicator == "true":
            charge += _decimal(amount)
        else:
            allowance += _decimal(amount)
    return allowance, charge


def store_working_copy(root: Path, job_id: str, contents: bytes) -> tuple[Path, str]:
    """Düzeltmeyi orijinalden ayrı, işlem kimliğine ait çalışma kopyasına yazar."""
    directory = root / "working" / job_id
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "corrected.xml"
    temporary = directory / ".corrected.uploading"
    temporary.write_bytes(contents)
    temporary.replace(destination)
    return destination, sha256(contents).hexdigest()
