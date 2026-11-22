import asyncio
import json
import runpy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from faturaguard import main
from faturaguard.config import Settings
from faturaguard.domain.chat import ChatTurn
from faturaguard.domain.correction import CorrectionJob, CorrectionProposal
from faturaguard.domain.validation import Finding, Severity, ValidationReport, ValidationSummary
from faturaguard.services.conversational_chat import (
    ConversationalDocumentChat,
    ConversationAnswer,
    ConversationMask,
    ConversationModel,
    ConversationPlan,
    has_unresolved_chat_tokens,
    suggests_approval_action,
)
from faturaguard.services.source_backed_explanation import LLMUnavailableError

CODES = [case["code"] for case in json.loads(
    (Path(__file__).resolve().parents[1] / "resources/evaluation/error_coverage_matrix.json")
    .read_text(encoding="utf-8"))]


@pytest.fixture
def document(tmp_path):
    path = tmp_path / "private-invoice.xml"
    path.write_text('<Invoice><Name>Özel Müşteri AŞ</Name><ID>ABC2026000123</ID>'
                    '<StreetName>Gizli Sokak</StreetName><Amount>15.00</Amount></Invoice>',
                    encoding="utf-8")
    return CorrectionJob(
        job_id="one", original_filename=path.name, original_path=str(path),
        original_sha256=sha256(path.read_bytes()).hexdigest(),
        report=ValidationReport(original_filename=path.name,
            summary=ValidationSummary(is_valid=True, error_count=0, warning_count=1,
                                      info_count=0, duration_ms=1),
            findings=[Finding(code="hesap-dip-vergi-haric", source="hesap", severity="uyari",
                              priority="yuksek", priority_reason="İncele",
                              message="Özel Müşteri AŞ: vergi hariç tutar 15.00, beklenen 15.15")]),
        proposals=[CorrectionProposal(proposal_id="p", rule_id="recalculate-tax-exclusive-total",
            finding_code="hesap-dip-vergi-haric", title="Vergi hariç toplam",
            rationale="Dip toplamı yeniden hesapla", target_path="cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount",
            before="15.00", after="15.15", agent_plan={"decision": "propose"})],
    )


class Model:
    def __init__(self, tools=None, answer="Bu bulguyu sonuç ekranında inceleyebilirsiniz.",
                 citations=None, scope="document"):
        self.calls, self.attempted = [], []
        self.tools = tools or [{"name": "current_findings", "finding_code": ""}]
        self.answer, self.citations, self.scope = answer, citations or [], scope

    def generate(self, prompt, data, schema, **kwargs):
        self.attempted.append("fake")
        self.calls.append((prompt, data))
        if schema is ConversationPlan:
            return schema.model_validate({"scope": self.scope, "tools": self.tools})
        return schema(answer=self.answer, citation_ids=self.citations)


def test_model_interprets_free_question_and_follow_up_with_masked_history(document):
    document.chat_history = [ChatTurn(question="Özel Müşteri AŞ için ne oldu?",
                                     answer="Tutar 15.00 → 15.15", mode="llm_chat")]
    model = Model(answer="Vergi hariç toplam [VALUE_1] → [VALUE_2] olarak öneriliyor.")
    before = document.model_dump_json()
    turn = ConversationalDocumentChat(model).answer(document, "Peki bunun kaynağı ne olabilir?")
    assert turn.mode == "llm_chat" and "15.00 → 15.15" in turn.answer
    assert turn.tools_used == ["current_findings"]
    assert model.calls[0][1]["question"] == "Peki bunun kaynağı ne olabilir?"
    serialized = json.dumps(model.calls, ensure_ascii=False)
    for secret in ("Özel Müşteri AŞ", "15.00", "15.15", document.original_path,
                   document.original_filename, document.original_sha256):
        assert secret not in serialized
    assert model.calls[0][1]["history"][0]["answer"] == "Tutar [VALUE_1] → [VALUE_2]"
    assert document.model_dump_json() == before


def test_all_read_tools_use_actual_current_state_and_verified_citations(document):
    document.proposals[0].status = "applied"
    document.corrected_report = document.report.model_copy(deep=True)
    document.corrected_report.findings = []
    document.corrected_report.summary.warning_count = 0
    chunk = SimpleNamespace(source_title="Resmî kılavuz", source_url="https://ebelge.gib.gov.tr/guide.pdf",
                            page=47, text="Vergi hariç toplam alanı.")
    agent = SimpleNamespace(chat_evidence=lambda finding: [SimpleNamespace(chunk=chunk)])
    names = ["current_findings", "correction_proposals", "validation_comparison", "official_sources"]
    model = Model(tools=[{"name": n, "finding_code": "hesap-dip-vergi-haric" if n == "official_sources" else ""}
                         for n in names], answer="Toplam [VALUE_1] → [VALUE_2].", citations=["evidence_1"])
    turn = ConversationalDocumentChat(model, agent).answer(document, "Neler değişmiş, dayanağı nedir?")
    tools = model.calls[1][1]["TOOLS"]
    assert tools["current_findings"]["findings"] == []
    assert tools["validation_comparison"]["initial_counts"]["warnings"] == 1
    assert tools["validation_comparison"]["current_counts"]["warnings"] == 0
    assert tools["correction_proposals"][0]["status"] == "applied"
    assert "artık görülmeyen" in tools["validation_comparison"]["detail"]
    assert turn.tools_used == names and turn.citations[0].page == 47
    assert "15.00 → 15.15" in turn.answer


@pytest.mark.parametrize("tools", [
    [{"name": "apply_correction", "finding_code": ""}],
    [{"name": "current_findings", "finding_code": "other-job-code"}],
    [{"name": "current_findings", "finding_code": "", "job_id": "other"}],
    [{"name": "current_findings", "finding_code": ""}] * 2,
    [{"name": "current_findings", "finding_code": ""}] * 5,
])
def test_unapproved_tools_arguments_other_job_and_repeated_calls_fail_closed(document, tools):
    model = Model(tools=tools)
    original = document.model_dump_json()
    turn = ConversationalDocumentChat(model).answer(document, "Bu belgeyi incele")
    assert turn.mode == "local_fallback"
    assert len(model.calls) == 1
    assert original == document.model_dump_json()


@pytest.mark.parametrize("scope", ["mutation", "out_of_scope"])
def test_model_scope_decision_exposes_no_document_tool_results(document, scope):
    model = Model(scope=scope)
    turn = ConversationalDocumentChat(model).answer(document, "Talebimi değerlendir")
    assert model.calls[1][1]["TOOLS"] == {"scope": scope}
    assert not turn.tools_used and turn.mode == "llm_chat"


@pytest.mark.parametrize("answer,citations", [
    ("Bilinmeyen [VALUE_999]", []), ("Bakınız https://evil.test", []),
    ("Açıklama", ["unknown"]),
])
def test_unbound_values_links_and_citations_are_rejected(document, answer, citations):
    turn = ConversationalDocumentChat(Model(answer=answer, citations=citations)).answer(document, "Açıkla")
    assert turn.mode == "local_fallback" and "evil.test" not in turn.answer


def test_missing_original_fails_before_any_provider_request(document):
    document.original_path += ".missing"
    model = Model()
    turn = ConversationalDocumentChat(model).answer(document, "Özetle")
    assert turn.mode == "local_fallback" and not model.calls
    assert not turn.masked_conversation_sent


def test_masking_secrets_known_names_ids_numbers_and_history_window(document):
    mask = ConversationMask(document)
    text = mask.text("Gizli Sokak ABC2026000123 Özel Müşteri AŞ gsk_ABCDEFGH abc@test.com 12345678901 "
                     "<Invoice> 987.65 https://example.com C:\\private\\x.xml")
    for private in ("Gizli Sokak", "ABC2026000123", "Özel Müşteri AŞ", "ABCDEFGH", "abc@test.com",
                    "12345678901", "987.65", "<Invoice>", "example.com", "private"):
        assert private not in text
    document.chat_history = [ChatTurn(question=f"soru-{i}", answer="yanıt", mode="overview") for i in range(20)]
    model = Model()
    ConversationalDocumentChat(model).answer(document, "Devam edelim")
    history = model.calls[0][1]["history"]
    assert len(history) == 6 and history[0]["question"] == "soru-[NUMBER]"


def test_no_keys_uses_labeled_local_fallback_without_network(document, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: pytest.fail("Network forbidden"))
    turn = ConversationalDocumentChat(ConversationModel(Settings(gemini_api_key=None, groq_api_key=None))).answer(
        document, "Öncelikli sorunları özetle")
    assert turn.mode == "local_fallback" and not turn.masked_conversation_sent
    assert "Yerel kayıt özeti" in turn.answer


def test_provider_chain_validates_schema_and_does_not_leak_error_bodies(monkeypatch):
    calls = []
    def post(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        if "google" in endpoint:
            return httpx.Response(429, request=httpx.Request("POST", endpoint), text="SECRET_ERROR")
        return httpx.Response(200, request=httpx.Request("POST", endpoint), json={
            "choices": [{"message": {"content": '{"answer":"Güvenli yanıt","citation_ids":[]}'}}]})
    monkeypatch.setattr(httpx, "post", post)
    model = ConversationModel(Settings(gemini_api_key="fake-google", groq_api_key="fake-groq"))
    result = model.generate("SYSTEM", {"question": "Soru"}, ConversationAnswer)
    assert result.answer == "Güvenli yanıt" and model.attempted == ["gemini", "groq"]
    assert calls[0][1]["json"]["store"] is False
    assert calls[1][1]["json"]["response_format"]["json_schema"]["strict"] is True


def test_gemini_success_uses_existing_interactions_response_contract(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda endpoint, **kwargs: httpx.Response(
        200, request=httpx.Request("POST", endpoint), json={"steps": [
            {"type": "model_output", "content": [{"type": "text", "text":
                '{"scope":"document","tools":[{"name":"current_findings","finding_code":""}]}'}]}]}))
    model = ConversationModel(Settings(gemini_api_key="fake", groq_api_key=None))
    assert model.generate("system", {}, ConversationPlan).tools[0].name == "current_findings"


def test_provider_failures_are_bounded(monkeypatch):
    def post(*args, **kwargs):
        raise httpx.ReadTimeout("secret error")
    monkeypatch.setattr(httpx, "post", post)
    model = ConversationModel(Settings(gemini_api_key="fake", groq_api_key="fake"))
    with pytest.raises(LLMUnavailableError, match="geçerli yanıt"):
        model.generate("system", {}, ConversationAnswer)
    assert model.attempted == ["gemini", "groq"]


def test_http_route_uses_llm_chat_persists_only_chat_and_audits_metadata(document, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "settings", replace(main.settings, data_directory=tmp_path))
    model = Model(answer="Güncel bulgu vergi hariç toplamla ilgilidir.")
    monkeypatch.setattr(main, "create_conversational_chat",
                        lambda settings, agent: ConversationalDocumentChat(model))
    app = main.create_app()
    store = app.state.correction_workflow._store
    store.save(document)
    original = document.model_dump()

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/jobs/one/chat", data={"question": "Burada beni ne bekliyor?"},
                                         headers={"Accept": "application/json"})
            assert response.status_code == 200 and response.json()["turn"]["mode"] == "llm_chat"
            assert response.json()["turn"]["tools_used"] == ["current_findings"]
            html = (await client.get("/jobs/one/report")).text
            assert "AI sohbeti" in html and "son 6 soru-cevabın" in html
            assert "Sorularınız yerelde kalır" not in html
    asyncio.run(exercise())
    loaded = store.load("one")
    assert loaded.model_dump(exclude={"chat_history"}) == {k: v for k, v in original.items() if k != "chat_history"}
    assert sha256(Path(document.original_path).read_bytes()).hexdigest() == document.original_sha256
    assert loaded.chat_history[0].masked_conversation_sent
    events = app.state.correction_workflow.list_audit_events("one")
    assert "masked_conversation_sent" in str(events) and "Burada beni" not in str(events)


@pytest.mark.parametrize("code", [*CODES, "gelecekteki-bulgu"])
def test_all_catalog_findings_are_available_to_the_same_llm_tool(document, code):
    document.report.findings[0].code = code
    document.proposals = []
    model = Model()
    turn = ConversationalDocumentChat(model).answer(document, "Bu tespiti anlat", code)
    rows = model.calls[1][1]["TOOLS"]["current_findings"]["findings"]
    assert turn.mode == "llm_chat" and rows[0]["code"] == code
    assert "vergi hariç tutar" in rows[0]["detail"]
    assert "Özel Müşteri AŞ" not in rows[0]["detail"]


@pytest.mark.parametrize("rule_id", ["recalculate-line-extension-total", "recalculate-tax-exclusive-total",
                                    "recalculate-tax-inclusive-total", "recalculate-payable-total"])
def test_all_correction_rules_reach_conversation_through_the_same_tool(document, rule_id):
    from faturaguard.services.correction_engine import correction_rule_catalog
    metadata = correction_rule_catalog()[rule_id]
    proposal = document.proposals[0]
    proposal.rule_id, proposal.finding_code = rule_id, metadata["finding_code"]
    model = Model(tools=[{"name": "correction_proposals", "finding_code": ""}])
    turn = ConversationalDocumentChat(model).answer(document, "Teklifin içeriği nedir?")
    data = model.calls[1][1]["TOOLS"]["correction_proposals"][0]
    assert turn.mode == "llm_chat" and data["rule"] == rule_id
    assert "15.00" not in str(data) and "[VALUE_1]" in data["detail"]


def test_chat_evidence_keeps_source_agents_threshold_and_trusted_query(document):
    from faturaguard.services.agent_workflow import SourceBackedAgent
    from faturaguard.services.hybrid_retrieval import RetrievedEvidence
    from faturaguard.services.official_rag import RagChunk
    queries = []
    evidence = RetrievedEvidence(chunk=RagChunk("gib", "Guide", "https://ebelge.gib.gov.tr/g.pdf", 1,
                                              "Resmî açıklama"),
                                 semantic_score=.9, lexical_score=.9, exact_term_score=.9, rerank_score=.9)
    def search(query, limit):
        queries.append(query)
        return [evidence]
    agent = SourceBackedAgent(SimpleNamespace(search=search), object())
    assert agent.chat_evidence(document.report.findings[0]) == [evidence]
    assert "Özel Müşteri" not in queries[0] and "15.00" not in queries[0]
    low = replace(evidence, rerank_score=.1)
    agent._retriever = SimpleNamespace(search=lambda query, limit: [low])
    assert agent.chat_evidence(document.report.findings[0]) == []


def test_provider_outputs_must_match_schema(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda endpoint, **kwargs: httpx.Response(
        200, request=httpx.Request("POST", endpoint), json={"choices": [{"message": {
            "content": '{"answer":"Yanıt","citation_ids":[],"extra":"not allowed"}'}}]}))
    model = ConversationModel(Settings(gemini_api_key=None, groq_api_key="fake"))
    with pytest.raises(LLMUnavailableError):
        model.generate("system", {}, ConversationAnswer)


def test_two_findings_can_request_separate_official_sources_in_one_question(document):
    second = document.report.findings[0].model_copy(update={"code": "imza-yok"})
    document.report.findings.append(second)
    chunk = SimpleNamespace(source_title="GİB", source_url="https://ebelge.gib.gov.tr/g.pdf",
                            page=7, text="Resmî kanıt")
    agent = SimpleNamespace(chat_evidence=lambda finding: [SimpleNamespace(chunk=chunk)])
    model = Model(tools=[{"name": "official_sources", "finding_code": f.code}
                         for f in document.report.findings], citations=["evidence_1", "evidence_2"])
    turn = ConversationalDocumentChat(model, agent).answer(document, "İki bulguyu da kaynaklarıyla karşılaştır")
    assert turn.mode == "llm_chat" and len(turn.citations) == 2
    assert set(model.calls[1][1]["TOOLS"]) == {"official_sources", "official_sources:imza-yok"}


def test_retrieved_evidence_requires_final_citation(document):
    chunk = SimpleNamespace(source_title="GİB", source_url="https://ebelge.gib.gov.tr/g.pdf",
                            page=7, text="Resmî kanıt")
    agent = SimpleNamespace(chat_evidence=lambda finding: [SimpleNamespace(chunk=chunk)])
    model = Model(tools=[{"name": "official_sources", "finding_code": "hesap-dip-vergi-haric"}])
    assert ConversationalDocumentChat(model, agent).answer(document, "Kaynakla açıkla").mode == "local_fallback"


def test_missing_evidence_is_explicit_in_model_context(document):
    agent = SimpleNamespace(chat_evidence=lambda finding: [])
    model = Model(tools=[{"name": "official_sources", "finding_code": "hesap-dip-vergi-haric"}],
                  answer="Bu bulgu için yeterli resmî kanıt bulunamadı; kesin yorum yapamıyorum.")
    turn = ConversationalDocumentChat(model, agent).answer(document, "GİB ne diyor?")
    assert model.calls[1][1]["TOOLS"]["official_sources"]["status"] == "insufficient_official_evidence"
    assert not turn.citations and "kesin yorum yapamıyorum" in turn.answer


@pytest.mark.parametrize("before,after", [
    ("15.00", "15.15"), ("1000000.00", "1000001.25"),
    ("1234567890.12", "1234567891.12"), ("-15.00", "-15.15"), ("15,00", "15,15"),
])
@pytest.mark.parametrize("ending", [".", ", sonraki adım", ";", ")", "!", "?"])
def test_amount_tokens_survive_sentence_punctuation_and_pii_filters(document, before, after, ending):
    document.proposals[0].before, document.proposals[0].after = before, after
    mask = ConversationMask(document)
    text = f"Dip toplam: {before} → {after}{ending}"
    encoded = mask.text(text, values=True)
    assert "[VALUE_1]" in encoded and "[VALUE_2]" in encoded
    assert before not in encoded and after not in encoded
    assert mask.restore(encoded) == text


def test_amount_substrings_of_larger_numbers_and_ids_are_not_bound(document):
    mask = ConversationMask(document)
    assert "[VALUE_" not in mask.text("115.00 15.150 ABC15.15 15.15X", values=True)


def test_comparison_sends_bound_counts_and_both_applied_amounts(document):
    document.proposals[0].status = "applied"
    document.corrected_report = document.report.model_copy(deep=True)
    document.corrected_report.findings = []
    document.corrected_report.summary.warning_count = 0
    model = Model(tools=[{"name": "validation_comparison", "finding_code": ""}],
                  answer="İlk kontrol [COUNT_2] uyarı; son kontrol [COUNT_1] uyarı. Tutar [VALUE_1] → [VALUE_2].")
    turn = ConversationalDocumentChat(model).answer(document, "İlk ve son kontrolü karşılaştır")
    data = model.calls[1][1]["TOOLS"]["validation_comparison"]
    assert "[COUNT_1] hata, [COUNT_2] uyarı, [COUNT_1] bilgi" in data["detail"]
    assert "[VALUE_1] → [VALUE_2]." in data["detail"]
    assert "[NUMBER]" not in data["detail"]
    assert turn.mode == "llm_chat" and "1 uyarı; son kontrol 0 uyarı" in turn.answer
    assert "15.00 → 15.15." in turn.answer and "[" not in turn.answer
    assert model.calls[1][1]["workflow_state"]["approval_available"] is False


@pytest.mark.parametrize("token", ["[NUMBER]", "[number]", "[MASKED_PHONE]", "[MASKED]", "[COUNT_999]", "[COUNT_1", "[VALUE_999]"])
def test_unresolved_placeholders_never_reach_user_even_on_free_wording(document, token):
    model = Model(tools=[{"name": "validation_comparison", "finding_code": ""}],
                  answer=f"Dip toplam {token} olarak değişti.")
    turn = ConversationalDocumentChat(model).answer(document, "İlk kontrolle en son kontrolü karşılaştır")
    assert turn.mode == "local_fallback" and not has_unresolved_chat_tokens(turn.answer)
    assert "Henüz düzeltilmiş bir kopya" in turn.answer


@pytest.mark.parametrize("status,ready", [("applied", False), ("rejected", False), ("proposed", True)])
def test_next_step_is_bound_to_current_approval_availability(document, status, ready):
    document.proposals[0].status = status
    model = Model(answer="Sonuç ekranındaki onay sürecine geçebilirsiniz.")
    turn = ConversationalDocumentChat(model).answer(document, "Şimdi ne yapmalıyım?")
    assert model.calls[1][1]["workflow_state"]["approval_available"] is ready
    assert turn.mode == ("llm_chat" if ready else "local_fallback")
    if not ready:
        assert "onay sürecine geçebilirsiniz" not in turn.answer


@pytest.mark.parametrize("answer", [
    "İlk kontrol [NUMBER] uyarı; toplam 15.00 → [NUMBER].",
    "İlk kontrol 1 uyarı; toplam değişti.",
])
def test_live_smoke_does_not_accept_missing_values_or_masks(document, answer):
    document.proposals[0].status = "applied"
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/run_document_chat_smoke_test.py"))
    turn = ChatTurn(question="Karşılaştır", answer=answer, mode="llm_chat",
                    tools_used=["validation_comparison"])
    with pytest.raises(SystemExit):
        namespace["validate_turn"](turn, 3, document)


def test_live_smoke_accepts_complete_comparison_with_local_amounts(document):
    document.proposals[0].status = "applied"
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/run_document_chat_smoke_test.py"))
    turn = ChatTurn(question="Karşılaştır", answer="İlk kontrol 1 uyarı; toplam 15,00 → 15,15.",
                    mode="llm_chat", tools_used=["validation_comparison"])
    namespace["validate_turn"](turn, 3, document)


@pytest.mark.parametrize("answer", [
    "Onay sürecine geçmeniz gerekmiyor.", "Onay sürecine geçmeyin.",
    "Onay aşamasına geçmenize gerek yok.", "Düzeltmeyi onaylamanız gerekmiyor.",
    "Teklifi onaylamayın, daha önce uygulandı.", "Bekleyen teklif yok; bu site imza atmaz.",
])
def test_negated_or_absent_approval_step_is_not_a_positive_recommendation(document, answer):
    assert not suggests_approval_action(answer)
    document.proposals[0].status = "applied"
    model = Model(answer=answer)
    turn = ConversationalDocumentChat(model).answer(document, "Ne yapmalıyım?")
    assert turn.mode == "llm_chat" and not turn.repair_attempted and not turn.validation_issues


@pytest.mark.parametrize("answer", [
    "Onay sürecine geçebilirsiniz.", "Onay aşamasına geçiniz.",
    "Onay sürecine ilerleyin.", "Düzeltmeyi onaylayın.",
    "Teklifi onaylayabilirsiniz.", "Düzeltmeleri onaylamanız gerekir.",
])
def test_affirmative_approval_recommendation_remains_detected(answer):
    assert suggests_approval_action(answer)


def test_rejected_answer_gets_one_masked_repair_without_echoing_rejected_text(document):
    class RepairModel(Model):
        def generate(self, prompt, data, schema, **kwargs):
            result = super().generate(prompt, data, schema, **kwargs)
            if kwargs.get("fallback_first"):
                assert data["rejection_code"] == "unresolved_mask"
                return schema(answer="Kayıtlı teklifin durumunu sonuç ekranında inceleyebilirsiniz.",
                              citation_ids=[])
            return result
    model = RepairModel(answer="REJECTED_PROVIDER_SECRET [NUMBER]")
    turn = ConversationalDocumentChat(model).answer(document, "Durum nedir?")
    assert turn.mode == "llm_chat" and turn.repair_attempted and turn.failure_code is None
    assert turn.validation_issues == ["unresolved_mask"] and len(model.calls) == 3
    assert "REJECTED_PROVIDER_SECRET" not in json.dumps(model.calls, ensure_ascii=False)
    assert "Özel Müşteri AŞ" not in json.dumps(model.calls, ensure_ascii=False)
    assert "REJECTED_PROVIDER_SECRET" not in turn.model_dump_json()


def test_second_rejection_stops_with_safe_diagnostics(document):
    model = Model(answer="REJECTED_PROVIDER_SECRET", citations=["not-retrieved"])
    turn = ConversationalDocumentChat(model).answer(document, "Durum nedir?")
    assert len(model.calls) == 3 and turn.mode == "local_fallback"
    assert turn.failure_code == "unbound_citation" and turn.repair_attempted
    assert turn.validation_issues == ["unbound_citation", "unbound_citation"]
    assert "REJECTED_PROVIDER_SECRET" not in turn.model_dump_json()


def test_semantically_rejected_gemini_answer_is_repaired_with_groq(document, monkeypatch):
    requests = []
    def post(endpoint, **kwargs):
        requests.append((endpoint, kwargs))
        if len(requests) == 1:
            content = '{"scope":"document","tools":[{"name":"correction_proposals","finding_code":""}]}'
        elif len(requests) == 2:
            content = '{"answer":"REJECTED_PROVIDER_SECRET","citation_ids":["old-evidence"]}'
        else:
            content = '{"answer":"Kayıtlı düzeltme teklifi onay bekliyor.","citation_ids":[]}'
        body = ({"steps": [{"type": "model_output", "content": [{"type": "text", "text": content}]}]}
                if "google" in endpoint else {"choices": [{"message": {"content": content}}]})
        return httpx.Response(200, request=httpx.Request("POST", endpoint), json=body)
    monkeypatch.setattr(httpx, "post", post)
    model = ConversationModel(Settings(gemini_api_key="fake-gemini", groq_api_key="fake-groq"))
    turn = ConversationalDocumentChat(model).answer(document, "Teklif var mı?")
    assert turn.mode == "llm_chat" and turn.providers == ["gemini", "groq"]
    assert turn.generated_by == "groq" and turn.producer_label == "Groq tarafından üretildi"
    assert turn.validation_issues == ["unbound_citation"] and turn.repair_attempted
    assert len(requests) == 3 and "groq" in requests[-1][0]
    repair_data = requests[-1][1]["json"]
    assert "REJECTED_PROVIDER_SECRET" not in json.dumps(repair_data)
    assert "Özel Müşteri AŞ" not in json.dumps(repair_data, ensure_ascii=False)
    assert "15.00" not in json.dumps(repair_data)


def test_failure_diagnostics_are_persisted_as_metadata_without_rejected_model_text(document, tmp_path):
    from faturaguard.services.correction_workflow import CorrectionWorkflow
    workflow = CorrectionWorkflow(tmp_path, object())
    workflow._store.save(document)
    model = Model(answer="REJECTED_PROVIDER_SECRET [NUMBER]")
    saved, turn = workflow.chat(document.job_id, "Durum nedir?", "", ConversationalDocumentChat(model))
    assert saved.chat_history[-1].failure_code == "unresolved_mask"
    assert saved.chat_history[-1].repair_attempted
    events = workflow.list_audit_events(document.job_id)
    assert "unresolved_mask" in str(events) and "repair_attempted" in str(events)
    assert "REJECTED_PROVIDER_SECRET" not in str(events)
    assert "REJECTED_PROVIDER_SECRET" not in saved.model_dump_json()


def test_failed_live_attempt_replaces_stale_success_evidence(tmp_path):
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/run_document_chat_smoke_test.py"))
    write = namespace["write_evidence"]
    path = tmp_path / "evaluation" / "document_conversation_acceptance.json"
    write(tmp_path, [], "automated_checks_passed", False)
    assert json.loads(path.read_text(encoding="utf-8"))["no_unresolved_tokens"]
    write(tmp_path, [], "running")
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "running"
    write(tmp_path, [{"turn": 2, "failure_code": "unbound_citation"}], "failed", False)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed" and not payload["no_unresolved_tokens"]
    assert payload["turns"] == [{"turn": 2, "failure_code": "unbound_citation"}]


def test_model_receives_completed_approval_and_explicit_severity_transitions(document):
    document.proposals[0].status = "applied"
    info = document.report.findings[0].model_copy(update={"code": "imza-yok", "severity": Severity.INFO})
    document.report.findings.append(info)
    document.report.summary.info_count = 1
    document.corrected_report = document.report.model_copy(deep=True)
    document.corrected_report.findings = [info]
    document.corrected_report.summary.warning_count = 0
    model = Model(tools=[{"name": "correction_proposals", "finding_code": ""},
                         {"name": "validation_comparison", "finding_code": ""}],
                  answer="Teklif uygulandı; yeniden onay gerekmiyor. Hata sayısı sıfır kaldı; bilgi kaydı sürüyor.")
    turn = ConversationalDocumentChat(model).answer(document, "Teklif ve önce/sonra durumu nedir?")
    tools = model.calls[1][1]["TOOLS"]
    assert turn.mode == "llm_chat" and not turn.repair_attempted
    assert tools["correction_proposals"][0]["approval"]["reason"] == "already_applied"
    changes = tools["validation_comparison"]["severity_changes"]
    assert changes["errors"]["change"] == "unchanged" and changes["warnings"]["net_decrease"] == 1
    rows = tools["validation_comparison"]["finding_changes"]
    assert next(row for row in rows if row["code"] == "imza-yok")["severity_label"] == "Bilgi"
    assert "Özel Müşteri AŞ" not in json.dumps(model.calls, ensure_ascii=False)
    assert "15.00" not in json.dumps(model.calls)


def test_basis_contains_only_the_findings_read_by_selected_tools(document):
    second = document.report.findings[0].model_copy(update={"code": "imza-yok"})
    document.report.findings.append(second)
    model = Model(tools=[{"name": "current_findings", "finding_code": "imza-yok"}])
    model.last_provider = "gemini"
    turn = ConversationalDocumentChat(model).answer(document, "İmzayı açıkla", "imza-yok")
    assert turn.generated_by == "gemini" and turn.basis_recorded
    assert turn.basis_findings == ["imza-yok"]
    assert turn.basis_records == ["Güncel doğrulama sonuçları"]


def test_failed_provider_attempt_is_not_presented_as_the_reply_author(document):
    model = Model(answer="Geçersiz [NUMBER]")
    model.last_provider = "gemini"
    turn = ConversationalDocumentChat(model).answer(document, "Öncelikli sorunları özetle")
    assert turn.generated_by == "local" and turn.producer_label == "Yerel kayıt özeti"
    assert turn.basis_findings == ["hesap-dip-vergi-haric"]
    assert turn.basis_records == ["Güncel doğrulama sonuçları"]


def test_final_provider_is_the_validated_response_not_the_first_attempt(monkeypatch):
    def post(endpoint, **kwargs):
        if "groq" in endpoint:
            return httpx.Response(429, request=httpx.Request("POST", endpoint))
        return httpx.Response(200, request=httpx.Request("POST", endpoint), json={"steps": [
            {"type": "model_output", "content": [{"type": "text", "text":
                '{"answer":"Yanıt","citation_ids":[]}'}]}]})
    monkeypatch.setattr(httpx, "post", post)
    model = ConversationModel(Settings(gemini_api_key="fake", groq_api_key="fake"))
    model.generate("system", {}, ConversationAnswer, fallback_first=True)
    assert model.attempted == ["groq", "gemini"] and model.last_provider == "gemini"


def test_technical_field_leak_is_repaired_before_it_reaches_the_user(document):
    class RepairModel(Model):
        def generate(self, prompt, data, schema, **kwargs):
            result = super().generate(prompt, data, schema, **kwargs)
            if kwargs.get("fallback_first"):
                assert data["rejection_code"] == "technical_field_leak"
                return schema(answer="Teklif sonuç ekranında kullanıcı onayı bekliyor.", citation_ids=[])
            return result
    model = RepairModel(answer="approval_available: false")
    turn = ConversationalDocumentChat(model).answer(document, "Teklifin durumu ne?")
    assert turn.mode == "llm_chat" and "approval_available" not in turn.answer
    assert turn.validation_issues == ["technical_field_leak"] and turn.repair_attempted


def test_repeated_technical_leak_uses_safe_local_summary_and_audits_only_reason(document):
    model = Model(answer="approval_available: false")
    turn = ConversationalDocumentChat(model).answer(document, "Düzeltme teklifini açıkla")
    assert turn.mode == "local_fallback" and turn.generated_by == "local"
    assert "approval_available" not in turn.answer and turn.failure_code == "technical_field_leak"
    assert turn.validation_issues == ["technical_field_leak", "technical_field_leak"]


def test_record_matching_technical_state_is_humanized_without_losing_ai_authorship(document):
    document.proposals[0].status = "applied"
    model = Model(tools=[{"name": "correction_proposals", "finding_code": ""}],
                  answer="Teklif **already_applied** durumunda (approval_available: false).")
    model.last_provider = "groq"
    turn = ConversationalDocumentChat(model).answer(document, "Teklifin durumu nedir?")
    assert turn.mode == "llm_chat" and turn.generated_by == "groq" and not turn.repair_attempted
    assert "uygulandı" in turn.answer and "onaylanabilir hazır teklif yok" in turn.answer
    assert "already_applied" not in turn.answer and "approval_available" not in turn.answer
    assert "**" not in turn.answer


def test_source_excerpt_is_bound_to_retrieved_evidence_and_survives_reload(document, tmp_path):
    from faturaguard.services.correction_workflow import CorrectionWorkflow
    chunk = SimpleNamespace(source_title="Resmî GİB kılavuzu", source_url="https://ebelge.gib.gov.tr/guide.pdf",
                            page=47, text="Gerçek kaynak metni.\nVergi hariç toplam alanı tanımlanır.")
    agent = SimpleNamespace(chat_evidence=lambda finding: [SimpleNamespace(chunk=chunk)])
    model = Model(tools=[{"name": "official_sources", "finding_code": "hesap-dip-vergi-haric"}],
                  answer="Bu alanı kaynakla inceleyin.", citations=["evidence_1"])
    model.last_provider = "gemini"
    turn = ConversationalDocumentChat(model, agent).answer(document, "Bu bulgunun kaynağı nedir?")
    assert turn.mode == "llm_chat"
    assert turn.citations[0].excerpt == "Gerçek kaynak metni. Vergi hariç toplam alanı tanımlanır."
    assert turn.basis_findings == ["hesap-dip-vergi-haric"]
    workflow = CorrectionWorkflow(tmp_path, object())
    workflow._store.save(document)
    workflow._store.append_chat_turn(document.job_id, turn)
    saved = workflow._store.load(document.job_id).chat_history[-1]
    assert saved.citations[0].excerpt == turn.citations[0].excerpt
