"""Tüm bulgu kodları ve izinli düzeltmeler için kayıt temelli açıklama katmanı.

Bu katman mevzuat üretmez ve sağlayıcı çağırmaz. Yerel, doğrulanmış bulguları
ve uygulanmış teklif kayıtlarını açıklar; bilinmeyen kodlarda da aynı sınır geçerlidir.
"""

from collections import Counter

from faturaguard.domain.correction import CorrectionJob
from faturaguard.domain.validation import Finding, Severity
from faturaguard.services.correction_engine import correction_rule_catalog


def finding_context(job: CorrectionJob, finding: Finding) -> str:
    severity = {Severity.ERROR: "Hata", Severity.WARNING: "Uyarı", Severity.INFO: "Bilgi"}
    lines = [
        f"Belgenizde tespit edilen ({severity[finding.severity]} · {finding.code}):",
        finding.message,
    ]
    if finding.line is not None:
        lines.append(
            f"Konum: yüklenen XML içinde satır {finding.line}. Bu, kaynak belgenin sayfası değildir."
        )
    if finding.explanation:
        lines += ["", "Doğrulayıcının kontrol ettiği kural: " + finding.explanation]
    proposals = [p for p in job.proposals if p.finding_code == finding.code]
    current = job.corrected_report or job.report
    if job.corrected_report and proposals:
        lines.append(
            "Bu bulgu yeniden doğrulamada hâlâ var; önceki teklif kaydı giderildiği anlamına gelmez."
        )
    pending = [p for p in proposals if p.status == "proposed"]
    if pending:
        for proposal in pending:
            lines.append(f"İzinli aday: {proposal.title}; {proposal.before} → {proposal.after}.")
            if (proposal.agent_plan or {}).get("decision") == "propose":
                lines.append("Geçerli plan var; uygulamak için sonuç ekranındaki onayınız gerekir.")
            else:
                lines.append("AI planı onaya hazır değil; şu anda bu aday uygulanamaz.")
    else:
        rules = correction_rule_catalog()
        matching = [m for m in rules.values() if m["finding_code"] == finding.code]
        blockers = sorted(
            {
                f.code
                for f in current.findings
                for meta in matching
                if f.code in meta["dependency_findings"]
            }
        )
        if blockers:
            lines.append(
                "Bu alanın bağlı olduğu kontrollerde de bulgu var: "
                + ", ".join(blockers)
                + ". Önce bu kontroller incelenmeli; bağımlı tutardan yeni değer önerilmiyor."
            )
        else:
            lines.append(
                "Bu bulgu için şu anda onaya hazır bir otomatik düzeltme teklifi yok. "
                "Bu, bulgunun giderildiği anlamına gelmez."
            )
    if finding.suggested_fix:
        lines.append("Doğrulayıcının önerdiği inceleme: " + finding.suggested_fix)
    elif finding.severity is Severity.ERROR:
        lines.append(
            "Sonraki adım: ilgili XML alanını kaynak sistemde inceleyin ve belgeyi yeniden doğrulayın."
        )
    else:
        lines.append(
            "Sonraki adım: bu bulguyu belgeyi oluşturan kaynak sistemde ve resmî kaynakla inceleyin."
        )
    return "\n".join(lines)


def comparison_details(job: CorrectionJob) -> str:
    if job.corrected_report is None:
        return "Henüz düzeltilmiş bir kopya ve yeniden doğrulama sonucu yok. İlk doğrulama sonucu gösteriliyor."
    before, after = job.report.summary, job.corrected_report.summary
    rules = correction_rule_catalog()
    applied = [p for p in job.proposals if p.status == "applied"]
    lines = ["Uygulanan değişiklikler:"]
    for proposal in applied:
        metadata = rules.get(proposal.rule_id)
        label = f"{metadata['title']} ({metadata['element']})" if metadata else proposal.title
        lines.append(f"• {label}: {proposal.before} → {proposal.after}.")
        lines.append(
            "  Kapsam: " + (str(metadata["rationale"]) if metadata else proposal.rationale)
        )
    if not applied:
        lines.append(
            "Yeniden doğrulama kaydı var; ancak uygulanmış alan değişikliği ayrıntısı "
            "kayıtlı değil. Hangi değerin değiştiğini varsaymıyorum."
        )
    initial = Counter(f.code for f in job.report.findings)
    current = Counter(f.code for f in job.corrected_report.findings)
    removed, added = initial - current, current - initial
    lines += [
        "",
        f"İlk doğrulama: {before.error_count} hata, {before.warning_count} uyarı, {before.info_count} bilgi.",
        f"Yeniden doğrulama: {after.error_count} hata, {after.warning_count} uyarı, {after.info_count} bilgi.",
    ]
    disappeared = sorted(code for code in removed if current[code] == 0)
    if disappeared:
        lines.append(
            "Yeniden doğrulamada artık görülmeyen bulgular: " + ", ".join(disappeared) + "."
        )
    for code in sorted(code for code in removed if current[code]):
        lines.append(
            f"• {code}: kayıt sayısı {initial[code]} → {current[code]}; bu kod tamamen giderilmiş değil."
        )
    if not removed:
        lines.append(
            "Bulgu sayısı azalmadı; uygulanmış teklif kaydı tek başına sorunun çözüldüğünü göstermez."
        )
    if added:
        lines += ["", "Yeni veya sayısı artan bulgular:"]
        lines += [f"• {code}: {initial[code]} → {current[code]} kayıt." for code in sorted(added)]
        lines.append(
            "Bu farkın nedenini yalnızca bu kayıtlardan kesinleştiremiyorum; yeni bulguları inceleyin."
        )

    # Herhangi bir izinli kuralın alt bulgusu, başka kuralın bağımlılığında ise
    # ilişki motor kataloğundan bulunur. Tek bir örneğe ait tutar/kod koşulu yoktur.
    if len(applied) == 1:
        change = applied[0]
        own = rules.get(change.rule_id)
        if own:
            related = sorted(
                {
                    str(meta["finding_code"])
                    for meta in rules.values()
                    if own["finding_code"] in meta["dependency_findings"]
                    and meta["finding_code"] in disappeared
                    and meta["finding_code"] != own["finding_code"]
                }
            )
            if related:
                lines += [
                    "",
                    "Bağımlı kontroller: " + ", ".join(related) + ".",
                    f"{own['element']} bu kontrollerin hesap girdilerindendir. Alan güncellendikten "
                    "sonraki doğrulamada bu bulgular da görülmedi; bunlar için ayrı bir alan "
                    "düzeltmesi kaydı yok. İlişki, izinli kural bağımlılığı ve doğrulama sonucuna dayanır.",
                ]
    elif len(applied) > 1 and disappeared:
        lines.append(
            "Birden fazla alan değiştiği için her giderilen bulguyu tek bir değişikliğe bağlamıyorum."
        )

    lines += ["", "Kalan durum:"]
    if job.corrected_report.findings:
        labels = {Severity.ERROR: "Hata", Severity.WARNING: "Uyarı", Severity.INFO: "Bilgi"}
        lines += [
            f"• {labels[f.severity]} · {f.code}: {f.message}" for f in job.corrected_report.findings
        ]
        if after.error_count:
            lines.append(
                "Hata seviyesinde bulgu sürüyor; belgeyi kaynak sistemde inceleyip yeniden doğrulayın."
            )
        elif after.warning_count:
            lines.append("Uyarılar sürüyor; ilgili bulguları ve varsa izinli teklifleri inceleyin.")
        else:
            lines.append("Hata/uyarı kalmadı; bilgi kayıtlarını belge bağlamında değerlendirin.")
        lines.append(
            "Bir bulguyu seçerek kayıttaki kuralı, varsa teklifini ve resmî kaynak açıklamasını inceleyebilirsiniz."
        )
    else:
        lines.append(
            "Teknik doğrulamada bulgu kalmadı. Gönderim öncesi yetkili iş süreci ve imza kontrollerini ayrıca tamamlayın."
        )
    lines += [
        "",
        "Bu aritmetik düzeltme imza eklemedi. Düzeltme ayrı çalışma kopyasına kaydedildi; "
        "orijinal XML üzerine yazılmadı.",
    ]
    return "\n".join(lines)
