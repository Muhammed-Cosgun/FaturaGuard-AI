"""Teslimleri gösterir; yalnızca açıkça seçilen başarısız olayı tekrar kuyruğa alır."""

import argparse
import json
from pathlib import Path

from faturaguard.services.automation import AutomationStore

parser = argparse.ArgumentParser()
parser.add_argument("--retry", metavar="EVENT_ID")
args = parser.parse_args()
store = AutomationStore(Path(__file__).resolve().parents[1] / "data")
if args.retry and not store.retry_failed(args.retry):
    raise SystemExit("Başarısız durumda böyle bir olay yok; teslim edilmiş olay yeniden gönderilmedi.")
print(json.dumps({"deliveries": store.overview(), "reviews": store.reviews()}, ensure_ascii=False, indent=2))
