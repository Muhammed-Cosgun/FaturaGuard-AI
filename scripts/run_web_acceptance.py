"""Üç aritmetik fixture için FastAPI form akışını uçtan uca kabul eder.

Bu komut gerçek uygulama rotalarını, LLM destekli maskeli patch planını, kullanıcı
onayı formunu, yeniden doğrulamayı ve HTML raporu sınar. Görsel piksel denetimi
değil, teslim öncesi tekrarlanabilir işlevsel web kabul kanıtıdır.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from faturaguard.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_NAMES = (
    "demo_tax_exclusive_error.xml",
    "demo_tax_inclusive_error.xml",
    "demo_payable_error.xml",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FastAPI kabul senaryolarını çalıştırır")
    parser.add_argument(
        "--fixture",
        choices=FIXTURE_NAMES,
        help="Yalnızca bir fixture çalıştırır; API gecikmesi olan ortamlarda kullanışlıdır.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = create_app()
    results: list[dict[str, object]] = []
    with TestClient(app) as client:
        fixture_names = (args.fixture,) if args.fixture else FIXTURE_NAMES
        for fixture_name in fixture_names:
            fixture = PROJECT_ROOT / "data" / "demo-fixtures" / fixture_name
            if not fixture.is_file():
                raise SystemExit(f"Fixture bulunamadı: {fixture}")
            original_sha256 = sha256(fixture)
            response = client.post(
                "/documents/validate",
                files={"file": (fixture.name, fixture.read_bytes(), "application/xml")},
            )
            if response.status_code != 200:
                raise RuntimeError(f"{fixture_name}: yükleme HTTP {response.status_code}")
            match = re.search(r"İşlem kimliği:\s*<code>([a-f0-9]{32})</code>", response.text)
            if match is None:
                raise RuntimeError(f"{fixture_name}: yükleme yanıtında işlem kimliği bulunamadı")
            job = app.state.correction_workflow._store.load(match.group(1))
            if not job.proposals:
                raise RuntimeError(f"{fixture_name}: güvenli düzeltme teklifi üretilmedi")
            proposal = job.proposals[0]
            agent_plan = proposal.agent_plan or {}
            if agent_plan.get("decision") != "propose":
                raise RuntimeError(f"{fixture_name}: AI Agent planı propose üretmedi: {agent_plan}")
            decision_response = client.post(
                f"/jobs/{job.job_id}/proposals/{proposal.proposal_id}",
                data={"decision": "approve"},
            )
            if decision_response.status_code != 200:
                raise RuntimeError(f"{fixture_name}: onay HTTP {decision_response.status_code}")
            corrected_job = app.state.correction_workflow._store.load(job.job_id)
            report_response = client.get(f"/jobs/{job.job_id}/report")
            if report_response.status_code != 200:
                raise RuntimeError(f"{fixture_name}: rapor HTTP {report_response.status_code}")
            if sha256(fixture) != original_sha256:
                raise RuntimeError(f"{fixture_name}: orijinal fixture değiştirildi")
            if corrected_job.corrected_report is None or corrected_job.corrected_report.summary.warning_count:
                raise RuntimeError(f"{fixture_name}: yeniden doğrulamada uyarı kaldı")
            results.append(
                {
                    "fixture": fixture_name,
                    "job_id": job.job_id,
                    "rule_id": proposal.rule_id,
                    "provider": agent_plan.get("generation_mode"),
                    "original_sha256": original_sha256,
                    "corrected_sha256": corrected_job.corrected_sha256,
                    "remaining_warnings": corrected_job.corrected_report.summary.warning_count,
                    "report_http_status": report_response.status_code,
                }
            )

    output_path = PROJECT_ROOT / "data" / "evaluation" / "web_acceptance.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    previous_results: dict[str, dict[str, object]] = {}
    if output_path.is_file():
        try:
            saved_results = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(saved_results, list):
                previous_results = {
                    item["fixture"]: item
                    for item in saved_results
                    if isinstance(item, dict) and isinstance(item.get("fixture"), str)
                }
        except json.JSONDecodeError:
            # Bozuk eski kanıt dosyası kabul testini engellemez; yeni sonuçlar yazılır.
            previous_results = {}
    previous_results.update({item["fixture"]: item for item in results})
    merged_results = [
        previous_results[fixture_name]
        for fixture_name in FIXTURE_NAMES
        if fixture_name in previous_results
    ]
    output_path.write_text(json.dumps(merged_results, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in results:
        print(
            f"{item['fixture']} | {item['rule_id']} | {item['provider']} | "
            f"kalan_uyari={item['remaining_warnings']}"
        )
    print(f"Kanıt: {output_path}")


if __name__ == "__main__":
    main()
