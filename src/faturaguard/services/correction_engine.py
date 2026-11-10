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

# Hedef alanı çalışma kopyasında yeniden-serileştirmeden değiştirmek için kullanılır.
# Böylece XML bildirimi, stylesheet processing instruction'ı, girintiler ve öznitelik sırası korunur.
_LINE_TOTAL_BYTES = re.compile(
    rb"(?P<head>"
    rb"<(?:[A-Za-z_][\w.-]*:)?LegalMonetaryTotal\b[^>]*>"
    rb".*?"
    rb"<(?P<tag>(?:[A-Za-z_][\w.-]*:)?LineExtensionAmount)\b[^>]*>"
    rb")"
    rb"(?P<value>[^<]*)"
    rb"(?P<tail></(?P=tag)\s*>)",
    re.DOTALL,
)


class CorrectionNotApplicableError(ValueError):
    """Teklif mevcut XML durumuna güvenle uygulanamadığında yükseltilir."""


class SafeCorrectionEngine:
    """Yalnızca açıkça tanımlanmış kuralları teklif eder ve uygular."""

    def propose(self, xml_bytes: bytes, report: ValidationReport) -> list[CorrectionProposal]:
        if not any(finding.code == "hesap-dip-satir" for finding in report.findings):
            return []
        before, after = self._line_extension_values(xml_bytes)
        if before == after:
            return []
        return [
            CorrectionProposal(
                proposal_id=uuid4().hex,
                rule_id="recalculate-line-extension-total",
                finding_code="hesap-dip-satir",
                title="Mal/hizmet dip toplamını satırlardan yeniden hesapla",
                rationale="Yalnızca mevcut InvoiceLine tutarları toplanır; satır, taraf ve vergi bilgileri değiştirilmez.",
                target_path=LINE_TOTAL_PATH,
                before=before,
                after=after,
            )
        ]

    def apply(self, xml_bytes: bytes, proposal: CorrectionProposal) -> bytes:
        if proposal.status is not CorrectionStatus.APPROVED:
            raise CorrectionNotApplicableError("Kullanıcı onayı olmayan düzeltme uygulanamaz.")
        if proposal.rule_id != "recalculate-line-extension-total":
            raise CorrectionNotApplicableError("İzin listesinde olmayan düzeltme kuralı istendi.")
        before, after = self._line_extension_values(xml_bytes)
        if before != proposal.before or after != proposal.after:
            raise CorrectionNotApplicableError(
                "Belge teklifi oluşturulduktan sonra değişmiş görünüyor."
            )
        return self._replace_line_total_value(xml_bytes, before, after)

    @staticmethod
    def _replace_line_total_value(xml_bytes: bytes, before: str, after: str) -> bytes:
        """Sadece onaylanan sayısal metni değiştirir; XML'i yeniden yazmaz."""

        match = _LINE_TOTAL_BYTES.search(xml_bytes)
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
        try:
            root = etree.fromstring(
                xml_bytes, parser=etree.XMLParser(resolve_entities=False, no_network=True)
            )
        except etree.XMLSyntaxError as error:
            raise CorrectionNotApplicableError(
                "İyi biçimli olmayan XML için bu düzeltme uygulanamaz."
            ) from error
        target = root.find(f"{CAC}LegalMonetaryTotal/{CBC}LineExtensionAmount")
        line_amounts = root.findall(f"{CAC}InvoiceLine/{CBC}LineExtensionAmount")
        if target is None or not target.text or not line_amounts:
            raise CorrectionNotApplicableError("Dip toplam veya fatura satırları bulunamadı.")
        try:
            total = sum((Decimal((item.text or "").strip()) for item in line_amounts), Decimal("0"))
        except InvalidOperation as error:
            raise CorrectionNotApplicableError(
                "Satır tutarlarından güvenli hesaplama yapılamadı."
            ) from error
        return target.text.strip(), format(total.quantize(Decimal("0.01")), "f")


def store_working_copy(root: Path, job_id: str, contents: bytes) -> tuple[Path, str]:
    """Düzeltmeyi orijinalden ayrı, işlem kimliğine ait çalışma kopyasına yazar."""
    directory = root / "working" / job_id
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "corrected.xml"
    temporary = directory / ".corrected.uploading"
    temporary.write_bytes(contents)
    temporary.replace(destination)
    return destination, sha256(contents).hexdigest()
