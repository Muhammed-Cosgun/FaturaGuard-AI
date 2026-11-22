"""Yerel ayarı yükleyip ana siteyi veya dar callback sunucusunu çalıştırır."""

import argparse
import os
from pathlib import Path

import uvicorn

parser = argparse.ArgumentParser()
parser.add_argument("component", choices=["site", "callback"])
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
os.chdir(root)
config = root / "data" / "automation" / "local.env"
if not config.is_file():
    raise SystemExit("Önce scripts/setup_local_automation.py çalıştırılmalı.")
allowed = {"N8N_WEBHOOK_URL", "FATURAGUARD_AUTOMATION_TOKEN"}
for line in config.read_text(encoding="utf-8").splitlines():
    key, separator, value = line.partition("=")
    if separator and key in allowed:
        os.environ[key] = value
if len(os.environ.get("FATURAGUARD_AUTOMATION_TOKEN", "")) < 32:
    raise SystemExit("Otomasyon token ayarı eksik veya kısa.")
uvicorn.run("faturaguard.main:app" if args.component == "site" else "faturaguard.automation_api:app",
            host="127.0.0.1" if args.component == "site" else "0.0.0.0",
            port=8011 if args.component == "site" else 8012)
