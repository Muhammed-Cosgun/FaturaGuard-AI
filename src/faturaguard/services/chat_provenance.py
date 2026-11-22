"""Modelin kendi beyanından bağımsız, yerel yanıt dayanağı kaydı."""

TOOL_LABELS = {
    "current_findings": "Güncel doğrulama sonuçları",
    "correction_proposals": "Kayıtlı düzeltme teklifleri",
    "validation_comparison": "İlk ve güncel doğrulama karşılaştırması",
    "official_sources": "Resmî GİB kaynak araması",
}


def tool_finding_codes(job, call, result):
    if call.name == "current_findings":
        return [row["code"] for row in result["findings"]]
    if call.name == "correction_proposals":
        return [row["finding_code"] for row in result]
    if call.name == "validation_comparison":
        return [row["code"] for row in result["finding_changes"]]
    return [call.finding_code] if call.finding_code else []


def local_basis(job, turn, comparison_used=False):
    if comparison_used or turn.mode == "comparison":
        reports = [job.report, job.corrected_report or job.report]
        return [f.code for report in reports for f in report.findings], ["İlk ve güncel doğrulama karşılaştırması"]
    if turn.finding_code:
        return [turn.finding_code], ["Yerel doğrulama kaydı"]
    if turn.mode == "overview":
        return [f.code for f in (job.corrected_report or job.report).findings], ["Güncel doğrulama sonuçları"]
    if turn.mode == "proposal":
        return [p.finding_code for p in job.proposals], ["Kayıtlı düzeltme teklifleri"]
    return [], []
