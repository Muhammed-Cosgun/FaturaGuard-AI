"""Yerel soru yönlendirmesi ve mevcut kaynaklı agent ile salt okunur asistan.

Serbest kullanıcı sorusu/sohbet geçmişi uzak modele gönderilmez. Kaynaklı açıklama
isteğinde yalnızca bu işin güncel, doğrulanmış Finding nesnesi agent'a verilir.
Bu servis hiçbir doğrulama, düzeltme veya karar aracını çağırmaz.
"""

import re

from faturaguard.domain.chat import ChatCitation, ChatTurn
from faturaguard.domain.correction import CorrectionJob
from faturaguard.domain.validation import Priority
from faturaguard.services.source_backed_explanation import LLMUnavailableError


def normalize(text: str) -> str:
    return text.casefold().translate(str.maketrans("çğıöşü", "cgiosu"))


class DocumentChat:
    def __init__(self, source_agent=None):
        self._source_agent = source_agent

    def answer(self, job: CorrectionJob, question: str, finding_code: str = "") -> ChatTurn:
        question = question.strip()
        if not question or len(question) > 600:
            raise ValueError("Sorunuz 1–600 karakter arasında olmalıdır.")
        text = normalize(question)

        def reply(answer, mode, **kwargs):
            return ChatTurn(question=question, answer=answer, mode=mode, **kwargs)

        if re.search(r"\b(duzelt|onayla|reddet|sil|imzala|gonder|degistir)\b", text):
            return reply(
                "Sohbet üzerinden XML değişikliği, onay, silme veya gönderim yapamam. "
                "Düzeltme teklifini inceleyip sonuç ekranındaki onay düğmesini kullanın. "
                "Burada teklifin ne yaptığını sorabilirsiniz.",
                "safety_boundary",
            )

        report = job.corrected_report or job.report
        findings = report.findings
        selected = next((f for f in findings if f.code == finding_code), None)
        if finding_code and selected is None:
            return reply(
                "Seçilen bulgu bu belgenin güncel doğrulamasında bulunmuyor. "
                "Güncel listeden bir bulgu seçin.",
                "clarification",
            )
        if selected is None:
            selected = next((f for f in findings if normalize(f.code) in text), None)
        if selected is None:
            aliases = {
                "vergi haric": "hesap-dip-vergi-haric",
                "vergi dahil": "hesap-dip-vergi-dahil",
                "odenecek": "hesap-dip-odenecek",
                "satir toplami": "hesap-dip-satir",
                "imza": "imza-yok",
            }
            selected = next(
                (
                    f
                    for key, code in aliases.items()
                    if key in text
                    for f in findings
                    if f.code == code
                ),
                None,
            )

        if any(
            term in text
            for term in (
                "sonra ne",
                "sonuc ne",
                "ne degisti",
                "neler degisti",
                "hangi alan degisti",
                "ne duzeltildi",
                "karsilastir",
                "duzeltildi mi",
            )
        ):
            if job.corrected_report is None:
                return reply(
                    "Henüz düzeltilmiş bir kopya ve yeniden doğrulama sonucu yok. "
                    "İlk doğrulama sonucu gösteriliyor.",
                    "comparison",
                )
            before, after = job.report.summary, job.corrected_report.summary
            applied = [proposal for proposal in job.proposals if proposal.status == "applied"]
            field_labels = {
                "recalculate-line-extension-total": "Mal/hizmet toplamı (LineExtensionAmount)",
                "recalculate-tax-exclusive-total": "Vergi hariç toplam (TaxExclusiveAmount)",
                "recalculate-tax-inclusive-total": "Vergiler dahil toplam (TaxInclusiveAmount)",
                "recalculate-payable-total": "Ödenecek tutar (PayableAmount)",
            }
            lines = ["Uygulanan değişiklik:"]
            if applied:
                lines += [
                    f"• {field_labels.get(p.rule_id, p.title)}: {p.before} → {p.after}."
                    for p in applied
                ]
            else:
                lines.append(
                    "Yeniden doğrulama kaydı var; ancak uygulanmış alan değişikliği "
                    "ayrıntısı bu işlemde kayıtlı değil. Hangi değerin değiştiğini varsaymıyorum."
                )
            old_codes = {f.code for f in job.report.findings}
            remaining_codes = {f.code for f in job.corrected_report.findings}
            resolved = sorted(old_codes - remaining_codes)
            lines += [
                "",
                f"İlk doğrulama: {before.error_count} hata, {before.warning_count} uyarı, {before.info_count} bilgi.",
                f"Yeniden doğrulama: {after.error_count} hata, {after.warning_count} uyarı, {after.info_count} bilgi.",
            ]
            if resolved:
                lines.append(
                    "Yeniden doğrulamada artık görülmeyen bulgular: " + ", ".join(resolved) + "."
                )
            applied_rules = {p.rule_id for p in applied}
            if (
                len(applied) == 1
                and before.warning_count - after.warning_count == 2
                and "recalculate-tax-exclusive-total" in applied_rules
                and "hesap-dip-vergi-haric" in resolved
                and "hesap-dip-vergi-dahil" in resolved
                and "recalculate-tax-inclusive-total" not in applied_rules
            ):
                lines += [
                    "Vergi hariç toplam düzeltildikten sonra, ona bağlı vergi dahil toplam "
                    "kontrolü de geçti. Vergi dahil toplam için ayrı bir düzeltme kaydı yok; "
                    "bu nedenle tek alan değişikliğiyle iki uyarı kalktı.",
                ]
            lines += ["", "Kalan durum:"]
            if job.corrected_report.findings:
                lines += [f"• {f.code}: {f.message}" for f in job.corrected_report.findings]
                if remaining_codes == {"imza-yok"}:
                    lines.append(
                        "Aritmetik uyarı kalmadı; imza eksikliği bilgi kaydı olarak sürüyor. "
                        "Bu işlem imza eklemedi. Belgenin taslak/test veya gönderim "
                        "aşamasına göre imza kontrolünü ayrıca değerlendirin."
                    )
                else:
                    lines.append(
                        "Sonraki adım: kalan bulguları inceleyin; gerekirse birini seçip "
                        "resmî kaynaklı açıklama isteyin."
                    )
            else:
                lines.append(
                    "Teknik doğrulamada bulgu kalmadı. Gönderim öncesi yetkili "
                    "iş süreci ve imza kontrollerini ayrıca tamamlayın."
                )
            lines += [
                "",
                "Düzeltme ayrı çalışma kopyasına kaydedildi; orijinal XML üzerine yazılmadı.",
            ]
            return reply(
                "\n".join(lines),
                "comparison",
            )
        if (
            any(term in text for term in ("duzeltme", "dugme", "teklif", "neden acil"))
            and selected is None
        ):
            if not job.proposals:
                return reply(
                    "Bu işlemde izinli bir aritmetik düzeltme teklifi yok. "
                    "Her bulgu otomatik düzeltilemez; ilgili bulguyu inceleyin.",
                    "proposal",
                )
            lines = []
            for proposal in job.proposals:
                plan = proposal.agent_plan or {}
                status = {
                    "proposed": "Bekliyor",
                    "applied": "Uygulandı",
                    "rejected": "Reddedildi",
                    "approved": "Onaylandı",
                }.get(proposal.status, "İncelenmeli")
                line = f"{proposal.title}: {status}. {proposal.rationale}"
                if proposal.status == "proposed" and plan.get("decision") != "propose":
                    line += " AI planı onaya hazır değil. " + str(
                        plan.get("rationale")
                        or "Kaynak veya model planı hazır olmadığından insan incelemesi gerekir."
                    )
                lines.append(line)
            return reply(
                "\n\n".join(lines) + "\n\nBu sohbet teklifleri onaylamaz ve XML değiştirmez.",
                "proposal",
            )
        if any(term in text for term in ("nasil kullan", "yardim", "nasil calis")):
            return reply(
                "1. XML yükleyin.\n2. Güncel hata ve uyarıları inceleyin.\n"
                "3. Bulgu seçerek resmî kaynaklı açıklama isteyin.\n"
                "4. Geçerli plan varsa teklifi sonuç ekranında onaylayın veya reddedin.\n"
                "5. Yeniden doğrulama ve raporu kontrol edin. "
                "Uygulama e-imza üretmez veya GİB'e gönderim yapmaz.",
                "guidance",
            )
        if selected is None and any(
            term in text
            for term in ("ozet", "oncelik", "once", "ne yap", "sorun", "incelemeliyim", "nereden")
        ):
            summary = report.summary
            rank = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
            ordered = sorted(findings, key=lambda f: rank[f.priority])
            lines = [
                f"Güncel doğrulama: {summary.error_count} hata, {summary.warning_count} uyarı, "
                f"{summary.info_count} bilgi."
            ]
            lines += [f"• {f.code}: {f.message}" for f in ordered[:5]]
            if len(findings) > 5:
                lines.append(f"Diğer {len(findings) - 5} bulgu için güncel listeyi inceleyin.")
            lines.append(
                "Bir bulguyu seçip ne anlama geldiğini sorabilirsiniz."
                if findings
                else "Teknik bulgu kalmadı. Gönderim öncesi yetkili iş süreci ve imza kontrollerini tamamlayın."
            )
            return reply("\n".join(lines), "overview")

        if selected is None and any(term in text for term in ("bunu", "bu hata", "bu bulgu")):
            previous = next(
                (t.finding_code for t in reversed(job.chat_history) if t.finding_code), None
            )
            selected = next((f for f in findings if f.code == previous), None)
        if selected is None:
            return reply(
                "Bu belge için bulgu açıklaması, öncelik özeti, düzeltme teklifi ve "
                "önce/sonra sonucu hakkında yardımcı olabilirim. Teknik açıklama için "
                "aşağıdaki listeden bir bulgu seçin; başka belgelere veya genel sohbet "
                "bilgisine erişmiyorum.",
                "clarification",
            )
        if self._source_agent is None:
            return reply(
                "GİB kaynaklı açıklama hattı hazır değil. Bulgu sonuç ekranında korunuyor; "
                "kaynak indeksi ve model bağlantısı kontrol edilmeli.",
                "unavailable",
                finding_code=selected.code,
            )
        try:
            result = self._source_agent.explain(selected)
        except (LLMUnavailableError, RuntimeError):
            return reply(
                "Kaynaklı açıklama şu anda hazırlanamadı. Daha sonra tekrar deneyin; "
                "belgede hiçbir değişiklik yapılmadı.",
                "unavailable",
                finding_code=selected.code,
            )
        explanation = result.get("explanation")
        if explanation is None:
            return reply(
                "Bu bulgu için yeterli resmî kanıt veya geçerli model açıklaması "
                "hazırlanamadı. Kesin bir teknik yorum yapmadan insan incelemesine "
                "yönlendiriyorum.",
                "unavailable",
                finding_code=selected.code,
            )
        citations = [
            ChatCitation(source_title=c.source_title, source_url=c.source_url, page=c.page)
            for c in explanation.citations
        ]
        return reply(
            "\n\n".join(
                (
                    explanation.summary,
                    explanation.reasoning,
                    "Sonraki adım: " + explanation.recommendation,
                )
            ),
            "source_summary"
            if explanation.generation_mode == "deterministic_fallback"
            else "source_backed",
            finding_code=selected.code,
            citations=citations,
        )
