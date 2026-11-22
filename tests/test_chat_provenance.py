from dataclasses import replace

import pytest

from faturaguard import main
from faturaguard.domain.chat import ChatCitation, ChatTurn
from faturaguard.services.correction_workflow import CorrectionWorkflow


@pytest.mark.parametrize("provider,label", [("gemini", "Gemini tarafından üretildi"),
                                           ("groq", "Groq tarafından üretildi"),
                                           ("local", "Yerel kayıt özeti")])
def test_author_label_comes_from_recorded_author(provider, label):
    turn = ChatTurn(question="Soru", answer="Yanıt", mode="llm_chat", generated_by=provider)
    assert turn.producer_label == label and turn.model_dump()["producer_label"] == label


def test_legacy_attempt_trace_does_not_fabricate_reply_author():
    turn = ChatTurn.model_validate({"question": "Soru", "answer": "Yanıt", "mode": "llm_chat",
                                    "providers": ["gemini", "groq"]})
    assert turn.generated_by == "unknown" and "Sağlayıcı kaydı yok" in turn.producer_label
    html = main.templates.get_template("chat_basis.html").render(turn=turn)
    assert "Bu eski yanıt için" in html and "Gemini tarafından" not in html


def test_provenance_template_escapes_findings_and_sources():
    turn = ChatTurn(question="Soru", answer="Yanıt", mode="llm_chat", generated_by="gemini",
                    basis_recorded=True, basis_findings=["<script>bulgu</script>"],
                    basis_records=["Güncel doğrulama sonuçları"], citations=[ChatCitation(
                        source_title="<img>Kaynak", source_url="https://ebelge.gib.gov.tr/guide.pdf", page=47)])
    html = main.templates.get_template("chat_basis.html").render(turn=turn)
    assert "Gemini tarafından üretildi" in html and "Dayanaklar" in html
    assert "&lt;script&gt;bulgu&lt;/script&gt;" in html and "<script>bulgu" not in html
    assert "&lt;img&gt;Kaynak" in html and "Sayfa 47" in html


def test_no_document_evidence_is_explicit_in_new_reply():
    turn = ChatTurn(question="Merhaba", answer="Belgeyi inceleyebilirim.", mode="llm_chat", basis_recorded=True)
    html = main.templates.get_template("chat_basis.html").render(turn=turn)
    assert "belge bulgusu veya resmî kaynak kullanılmadı" in html


def test_author_and_basis_survive_sqlite_and_only_safe_author_is_audited(tmp_path, monkeypatch):
    from faturaguard.domain.correction import CorrectionJob
    from faturaguard.domain.validation import ValidationReport, ValidationSummary
    monkeypatch.setattr(main, "settings", replace(main.settings, data_directory=tmp_path))
    workflow = CorrectionWorkflow(tmp_path, object())
    job = CorrectionJob(job_id="one", original_filename="demo.xml", original_path="local.xml",
                        original_sha256="hash", report=ValidationReport(original_filename="demo.xml", findings=[],
                            summary=ValidationSummary(is_valid=True, error_count=0, warning_count=0,
                                                      info_count=0, duration_ms=1)))
    workflow._store.save(job)
    turn = ChatTurn(question="Yerel soru", answer="Yanıt", mode="llm_chat", generated_by="groq",
                    basis_recorded=True, basis_findings=["imza-yok"], basis_records=["Güncel doğrulama sonuçları"])
    workflow._store.append_chat_turn("one", turn)
    saved = workflow._store.load("one").chat_history[-1]
    assert saved.generated_by == "groq" and saved.basis_findings == ["imza-yok"]
    assert saved.producer_label == "Groq tarafından üretildi"
    events = str(workflow.list_audit_events("one"))
    assert "generated_by" in events and "Yerel soru" not in events
