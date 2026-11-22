"""Yerel otomasyon ayarını oluşturur; mevcut dosyayı ve sistem ayarlarını ezmez."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "data" / "automation" / "local.env"
target.parent.mkdir(parents=True, exist_ok=True)
if not target.exists():
    with target.open("x", encoding="utf-8") as stream:
        stream.write("N8N_WEBHOOK_URL=http://127.0.0.1:5678/webhook/faturaguard-correction\n")
        stream.write(f"FATURAGUARD_AUTOMATION_TOKEN={secrets.token_hex(32)}\n")
print("Yerel ayar hazır:", target)
print("Header Auth değerini bu dosyadan n8n'e aktarın; sohbete veya Git'e eklemeyin.")
