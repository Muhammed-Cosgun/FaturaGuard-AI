"""Sohbet için yerel, sayısal doğrulama ve teklif durumu gerçekleri."""

from collections import Counter

from faturaguard.domain.correction import CorrectionJob, CorrectionProposal


def proposal_approval(proposal: CorrectionProposal) -> dict[str, object]:
    """Yeniden onay gerekmemesi ile planın hazır olmamasını ayırır."""
    if proposal.status == "applied":
        return {"available": False, "reason": "already_applied",
                "description": "Uygulandı; yeniden onay gerekmez."}
    if proposal.status == "rejected":
        return {"available": False, "reason": "rejected",
                "description": "Kullanıcı reddetti; uygulanmadı."}
    if proposal.status == "approved":
        return {"available": False, "reason": "already_approved",
                "description": "Onay kaydedildi; uygulandığı ayrıca doğrulanmalıdır."}
    ready = proposal.status == "proposed" and (proposal.agent_plan or {}).get("decision") == "propose"
    return {"available": ready, "reason": "awaiting_user_approval" if ready else "plan_not_ready",
            "description": "Sonuç ekranında kullanıcı onayı bekliyor." if ready else
            "Teklif henüz uygulanmadı; AI planı onaya hazır değil."}


def validation_transitions(job: CorrectionJob) -> dict[str, object]:
    """Özetin net değişimini ve kod/seviye bazındaki adet farklarını ayırır.

    Net adet aynı kaldığında farklı kodlar giderilip yenileri oluşmuş olabilir;
    bu yüzden net azalma, giderilen bulgu adedi olarak adlandırılmaz.
    """
    current = job.corrected_report or job.report
    severity_changes = {}
    for key, attribute in (("errors", "error_count"), ("warnings", "warning_count"),
                           ("information", "info_count")):
        before, after = getattr(job.report.summary, attribute), getattr(current.summary, attribute)
        severity_changes[key] = {
            "initial": before, "current": after,
            "change": "decreased" if after < before else "increased" if after > before else "unchanged",
            "net_decrease": max(before - after, 0), "net_increase": max(after - before, 0),
        }
    initial = Counter((f.code, f.severity.value) for f in job.report.findings)
    final = Counter((f.code, f.severity.value) for f in current.findings)
    labels = {"hata": "Hata", "uyari": "Uyarı", "bilgi": "Bilgi"}
    return {
        "severity_changes": severity_changes,
        "finding_changes": [{"code": code, "severity": severity,
                             "severity_label": labels[severity],
                             "initial_count": initial[(code, severity)],
                             "current_count": final[(code, severity)],
                             "removed_count": max(initial[(code, severity)] - final[(code, severity)], 0),
                             "added_count": max(final[(code, severity)] - initial[(code, severity)], 0)}
                            for code, severity in sorted(initial.keys() | final.keys())],
    }
