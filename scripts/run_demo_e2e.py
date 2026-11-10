"""Gerçek XML ile doğrulama ve kullanıcı-onaylı düzeltme demosu çalıştırır."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from faturaguard.config import settings
from faturaguard.services.correction_workflow import CorrectionWorkflow
from faturaguard.services.document_storage import DocumentStorage
from faturaguard.services.reporting import build_report_payload
from faturaguard.services.validation_adapter import EfaturaKontrolAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FaturaGuard AI uçtan uca demo")
    parser.add_argument("xml_path", type=Path, help="Doğrulanacak XML dosyası")
    parser.add_argument(
        "--approve-first-proposal",
        action="store_true",
        help="Yalnızca demo amacıyla ilk izinli düzeltme teklifini onaylar.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = parse_args()
    source = args.xml_path.resolve()
    if not source.is_file():
        raise SystemExit(f"XML dosyası bulunamadı: {source}")
    if source.suffix.lower() != ".xml":
        raise SystemExit("Demo yalnızca .xml dosyası kabul eder.")

    original_hash_before = sha256(source)
    data_root = PROJECT_ROOT / "data"
    storage = DocumentStorage(data_root, settings.max_upload_bytes)
    validator = EfaturaKontrolAdapter()
    workflow = CorrectionWorkflow(data_root, validator)

    contents = source.read_bytes()
    stored = storage.store_original(contents, source.name)
    job = workflow.create(stored, validator.validate(contents, source.name))
    print(f"İşlem kimliği: {job.job_id}")
    print(
        f"İlk doğrulama: {job.report.summary.error_count} hata, "
        f"{job.report.summary.warning_count} uyarı"
    )
    print(f"Düzeltme teklifi: {len(job.proposals)}")

    if args.approve_first_proposal and job.proposals:
        job = workflow.decide(job.job_id, job.proposals[0].proposal_id, "approve")
        print("Karar: kullanıcı onayıyla ilk izinli düzeltme uygulandı.")
        print(
            f"Yeniden doğrulama: {job.corrected_report.summary.error_count} hata, "
            f"{job.corrected_report.summary.warning_count} uyarı"
        )
        print(f"Çalışma kopyası: {job.corrected_path}")
    elif job.proposals:
        print("Karar: onay verilmedi; orijinal XML ve çalışma kopyası değiştirilmedi.")

    if sha256(source) != original_hash_before:
        raise RuntimeError("Güvenlik ihlali: girişteki orijinal XML değişti.")

    report_path = data_root / "reports" / f"{job.job_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(build_report_payload(job), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Orijinal hash doğrulandı: {original_hash_before}")
    print(f"İşlem raporu: {report_path}")


if __name__ == "__main__":
    main()
