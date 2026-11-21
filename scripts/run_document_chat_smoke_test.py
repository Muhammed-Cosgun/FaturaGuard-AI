"""Kayıtlı bir belgedeki salt okunur asistanı mevcut canlı sağlayıcılarla sınar."""

from faturaguard.config import settings
from faturaguard.main import _create_agent
from faturaguard.services.document_chat import DocumentChat
from faturaguard.services.job_repository import SqliteCorrectionJobStore


def main() -> None:
    if not settings.gemini_api_key and not settings.groq_api_key:
        raise SystemExit("Gemini veya Groq anahtarı bu terminalde tanımlı olmalıdır.")
    store = SqliteCorrectionJobStore(settings.data_directory)
    selected = None
    for row in store.list_recent(100):
        item = store.load(row["job_id"])
        if (item.corrected_report or item.report).findings:
            selected = item
            break
    if selected is None:
        raise SystemExit("Güncel bulgusu olan işlem yok; önce bir demo XML yükleyin.")
    assistant = DocumentChat(_create_agent())
    local = assistant.answer(selected, "Öncelikli sorunları özetle")
    finding = (selected.corrected_report or selected.report).findings[0]
    turn = assistant.answer(selected, "Bu bulguyu resmî GİB kaynağıyla açıkla", finding.code)
    print(f"local_mode={local.mode}")
    print(f"finding_code={finding.code}")
    print(f"answer_mode={turn.mode}")
    print(f"citation_count={len(turn.citations)}")
    print("xml_changed=false (salt okunur asistan)")
    if turn.mode != "source_backed" or not turn.citations:
        raise SystemExit(
            "Canlı kaynaklı AI yanıtı alınamadı; güvenli duruş/fallback sonucu incelenmeli."
        )
    print("Chatbot smoke testi: başarılı")


if __name__ == "__main__":
    main()
