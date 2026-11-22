"""Bilinen kusurlar için sınırlı kayıt denetimi; genel anlam doğruluk ispatı değildir."""

import re

from faturaguard.services.document_chat import normalize

INTERNAL_FIELDS = (
    "approval_available", "workflow_state", "initial_counts", "current_counts",
    "severity_changes", "finding_changes", "requires_user_review", "requires_user_approval",
    "generation_mode", "provider_trace", "failure_code", "validation_issues", "repair_attempted",
    "awaiting_human_review", "awaiting_user_approval", "already_applied", "plan_not_ready",
    "tools_used", "basis_findings", "basis_records", "generated_by", "producer_label",
    "net_decrease", "net_increase", "initial_count", "current_count", "removed_count", "added_count",
)
FIELD_PATTERN = re.compile(r"\b(?:" + "|".join(INTERNAL_FIELDS) + r")\b", re.IGNORECASE)


def prepare_user_answer(answer, job):
    """Yalnızca kayıtla doğrulanan durumları sadeleştirir; çelişkiyi gizlemez.

    HTML/Markdown çalıştırılmaz. Sayısal tokenlar ve kaynak atıfları değiştirilmez.
    Diğer iç anahtarlar kalite denetiminde reddedilmeye devam eder.
    """
    ready = any(p.status == "proposed" and (p.agent_plan or {}).get("decision") == "propose"
                for p in job.proposals)
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", answer)

    def approval(match):
        claimed = match[1].lower() == "true"
        if claimed != ready:
            return match[0]
        return "sonuç ekranında onaylanabilir bir teklif var" if ready else "onaylanabilir hazır teklif yok"

    text = re.sub(r"[\"`]?approval_available[\"`]?\s*[:=]\s*(true|false)\b", approval, text, flags=re.IGNORECASE)
    replacements = {}
    if any(p.status == "applied" for p in job.proposals):
        replacements["already_applied"] = "uygulandı"
    if ready:
        replacements["awaiting_user_approval"] = "kullanıcı onayı bekliyor"
    if any(p.status == "proposed" and (p.agent_plan or {}).get("decision") != "propose" for p in job.proposals):
        replacements["plan_not_ready"] = "plan henüz onaya hazır değil"
    for key, value in replacements.items():
        text = re.sub(r"\b" + key + r"\b", value, text, flags=re.IGNORECASE)
    return text


def chat_quality_issues(answer, job):
    issues = []
    if FIELD_PATTERN.search(answer):
        issues.append("technical_field_leak")
    text = normalize(answer).translate(str.maketrans("‐‑‒–—", "-----"))
    reports = [job.report, job.corrected_report or job.report]
    levels = {}
    for report in reports:
        for finding in report.findings:
            levels.setdefault(normalize(finding.code), set()).add(finding.severity.value)
    # Tarihî ve güncel seviye farklıysa yorum bağlamını otomatik varsayma.
    for code, severities in levels.items():
        if len(severities) != 1:
            continue
        expected = next(iter(severities))
        pattern = (r"(?<![\w-])" + re.escape(code) +
                   r"(?:['\"`])?\s+(?:bir\s+)?(uyari(?:si|sidir|dir)|hata(?:si|sidir|dir)|bilgi(?:si|sidir|dir))\b")
        for match in re.finditer(pattern, text):
            stated = "uyari" if match[1].startswith("uyari") else "hata" if match[1].startswith("hata") else "bilgi"
            if stated != expected:
                issues.append("finding_severity_mismatch")
    ready = any(p.status == "proposed" and (p.agent_plan or {}).get("decision") == "propose"
                for p in job.proposals)
    if not ready and re.search(
        r"\b(?:teklif(?:i)?|duzeltme(?: teklifi)?)[^.!?;\n]{0,110}\b(?:kullanici )?onayi? bekl(?:iyor|emektedir)\b", text
    ):
        issues.append("proposal_state_mismatch")
    if not any(p.status == "applied" for p in job.proposals) and re.search(
        r"\b(?:teklif|duzeltme)(?:\s+basariyla)?\s+uygulan(?:di|mistir)\b", text
    ):
        issues.append("proposal_state_mismatch")
    before = job.report.summary
    if before.error_count == 0 and re.search(
        r"\b0 hata(?:\s+ve\s+\d+\s+(?:uyari|bilgi))?\s+(?:ortadan kalk|gideril)", text
    ):
        issues.append("zero_error_resolution_claim")
    if job.corrected_report is not None:
        after = job.corrected_report.summary
        old = (before.error_count, before.warning_count, before.info_count)
        new = (after.error_count, after.warning_count, after.info_count)
        if old != new:
            counts = rf"{old[0]}\s+hata\s*,?\s*{old[1]}\s+uyari\s*(?:,|ve)?\s*{old[2]}\s+bilgi"
            if re.search(r"\b(?:duzeltme(?:den)? sonra(?:sinda)?|guncel durumda)\s+(?:belgede\s+)?" + counts, text):
                issues.append("validation_phase_mismatch")
    return list(dict.fromkeys(issues))
