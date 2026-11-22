"""Bilinen dil/durum hataları için çevrimdışı kalite denetimi; API çağrısı yapmaz."""

import json
from pathlib import Path

from faturaguard.services.chat_quality_evaluation import evaluate_quality_cases


def main():
    cases = json.loads(Path("resources/evaluation/chat_answer_quality_cases.json").read_text(encoding="utf-8"))
    report = evaluate_quality_cases(cases)
    target = Path("data/evaluation/chat_answer_quality.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Kalite denetimi: {report['passed']}/{report['case_count']} vaka geçti.")
    print("Ölçüm: yerel denetim sözleşmesi; canlı LLM doğruluğu veya sıfır halüsinasyon ölçümü değildir.")
    print(f"Kanıt: {target}")
    if report["passed"] != report["case_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
