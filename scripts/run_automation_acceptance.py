"""Canlı n8n + yerel Mailpit kabulü; sadece sentetik kayıt ve demo e-postası üretir."""

import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

from faturaguard.domain.correction import CorrectionJob, CorrectionProposal
from faturaguard.domain.validation import ValidationReport, ValidationSummary
from faturaguard.services.automation import AutomationDispatcher, AutomationStore, correction_event
from faturaguard.services.job_repository import SqliteCorrectionJobStore

root = Path(__file__).resolve().parents[1]
config = root / "data/automation/local.env"
if not config.exists():
    raise SystemExit("Önce setup_local_automation.py çalıştırın.")
values = dict(line.split("=", 1) for line in config.read_text(encoding="utf-8").splitlines() if "=" in line)
url = values.get("N8N_WEBHOOK_URL", "")
if url != "http://127.0.0.1:5678/webhook/faturaguard-correction":
    raise SystemExit("Kabul testi yalnızca yerel demo webhook'una gönderir.")
report = ValidationReport(original_filename="SENTETIK-OTOMASYON-TESTI.xml", findings=[],
    summary=ValidationSummary(is_valid=True, error_count=0, warning_count=0, info_count=0, duration_ms=0))
job = CorrectionJob(job_id="automation-demo-" + uuid4().hex, original_filename=report.original_filename,
    original_path="", original_sha256="synthetic", corrected_sha256="synthetic",
    report=report, corrected_report=report, proposals=[CorrectionProposal(proposal_id="synthetic",
        rule_id="synthetic", finding_code="synthetic", title="Sentetik otomasyon kabulü",
        rationale="Gerçek fatura veya doğrulama sonucu değildir.", target_path="synthetic",
        before="0", after="1", status="applied")])
event = correction_event(job)
store = AutomationStore(root / "data")
SqliteCorrectionJobStore(root / "data").save(job, automation_event=event)
dispatcher = AutomationDispatcher(store, url, values.get("FATURAGUARD_AUTOMATION_TOKEN"))
deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    dispatcher.deliver_one()
    row = next(r for r in store.overview() if r["event_id"] == event["event_id"])
    if row["status"] in ("delivered", "failed"):
        break
    time.sleep(1)
if row["status"] != "delivered":
    raise SystemExit(f"Teslim tamamlanmadı: {row['status']} / {row['last_error']}. automation_status.py ile inceleyin.")
response = httpx.post(url, json=event,
    headers={"X-FaturaGuard-Token": values["FATURAGUARD_AUTOMATION_TOKEN"]}, timeout=25)
response.raise_for_status()
if response.json().get("status") != "duplicate":
    raise SystemExit("Yinelenen olay kontrolü geçmedi.")
mailbox = httpx.get("http://127.0.0.1:8025/api/v1/messages", timeout=10)
mailbox.raise_for_status()
matches = 0
for message in mailbox.json().get("messages", []):
    mail = httpx.get("http://127.0.0.1:8025/api/v1/message/" + message["ID"], timeout=10)
    mail.raise_for_status()
    if event["event_id"] in mail.json().get("Text", ""):
        matches += 1
if matches != 1:
    raise SystemExit(f"Tekil demo e-postası bekleniyordu, bulunan: {matches}")
proof = {"kind": "live_n8n_mailpit_synthetic_acceptance", "event_id": event["event_id"],
         "delivered": True, "duplicate_ack": True, "mail_count": matches,
         "real_invoice_validation": False, "external_email_sent": False}
target = root / "data/evaluation/automation_acceptance.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(proof, indent=2), encoding="utf-8")
print("Canlı n8n / inceleme kaydı / tekil yerel e-posta kabulü: başarılı.")
print("Kanıt:", target)
