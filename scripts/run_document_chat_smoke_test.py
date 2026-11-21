"""Demo belgesinde gerçek LLM sohbeti, araç seçimi ve takip bağlamı kabulü."""

import json
from hashlib import sha256
from pathlib import Path

from faturaguard.config import settings
from faturaguard.main import _create_agent
from faturaguard.services.conversational_chat import create_conversational_chat
from faturaguard.services.job_repository import SqliteCorrectionJobStore


def main() -> None:
    if not settings.gemini_api_key and not settings.groq_api_key:
        raise SystemExit("Gemini veya Groq anahtarı bu terminalde tanımlı olmalıdır.")
    store = SqliteCorrectionJobStore(settings.data_directory)
    selected = None
    for row in store.list_recent(100):
        item = store.load(row["job_id"])
        if item.original_filename.startswith("demo_") and (item.corrected_report or item.report).findings:
            selected = item
            break
    if selected is None:
        raise SystemExit("Güncel bulgusu olan demo işlemi yok; önce demo_tax_exclusive_error.xml yükleyin.")
    selected.chat_history = []  # Canlı kullanıcı konuşmalarını smoke testine taşımayız.
    paths = [Path(p) for p in (selected.original_path, selected.corrected_path) if p]
    before = {str(p): sha256(p.read_bytes()).hexdigest() for p in paths}
    assistant = create_conversational_chat(settings, _create_agent())
    finding = (selected.corrected_report or selected.report).findings[0]
    questions = [
        ("Bu bulgunun bu belgedeki anlamını resmî kaynağına dayanarak anlatır mısın?", finding.code),
        ("Peki bunun için şu anda uygulanabilir bir teklif var mı, ben ne yapmalıyım?", ""),
        ("İlk kontrolle en son kontrolü karşılaştır; neyin değiştiği kayıtlı, ne hâlâ duruyor?", ""),
    ]
    evidence = []
    for index, (question, code) in enumerate(questions, 1):
        turn = assistant.answer(selected, question, code)
        print(f"turn={index} mode={turn.mode} providers={','.join(turn.providers)}")
        print(f"tools={','.join(turn.tools_used)} citations={len(turn.citations)}")
        print(turn.answer)
        print()
        if turn.mode != "llm_chat":
            raise SystemExit("Gerçek LLM sohbeti alınamadı; yerel yedek sonucu başarı sayılmadı.")
        required_tool = ["official_sources", "correction_proposals", "validation_comparison"][index - 1]
        if required_tool not in turn.tools_used or (index == 1 and not turn.citations):
            raise SystemExit("Sorunun gerektirdiği araç/kaynak kullanılmadı; canlı çıktı incelenmeli.")
        selected.chat_history.append(turn)
        evidence.append({"turn": index, "mode": turn.mode, "providers": turn.providers,
                         "tools": turn.tools_used, "citations": len(turn.citations)})
    unchanged = before == {str(p): sha256(p.read_bytes()).hexdigest() for p in paths}
    if not unchanged:
        raise SystemExit("XML bütünlük kontrolü başarısız.")
    target = settings.data_directory / "evaluation" / "document_conversation_acceptance.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"turns": evidence, "xml_changed": False,
                                 "semantic_review": "Kullanıcı üç yanıtın anlamını ayrıca değerlendirmeli."},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    print("xml_changed=false (orijinal ve varsa düzeltilmiş kopya hash kontrolü)")
    print("AI sohbet araç/bağlam smoke testi: başarılı; yanıtların anlamını ayrıca inceleyin.")


if __name__ == "__main__":
    main()
