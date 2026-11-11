"""LangGraph üzerinde kaynaklı açıklama üreten tek-agent iş akışı."""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from faturaguard.domain.validation import Finding
from faturaguard.services.hybrid_retrieval import RetrievedEvidence
from faturaguard.services.source_backed_explanation import (
    ExplanationGenerator,
    LLMUnavailableError,
    SourceBackedExplanation,
)


class AgentState(TypedDict):
    finding: Finding
    query: str
    evidence: list[RetrievedEvidence]
    explanation: SourceBackedExplanation | None
    status: str
    generation_error: str | None
    audit_events: list[str]


class SourceBackedAgent:
    """Araç allowlist'iyle sınırlı, koşullu yönlendirmeli bir LangGraph agent'ı."""

    def __init__(self, retriever, generator: ExplanationGenerator) -> None:
        self._retriever = retriever
        self._generator = generator
        self.graph = self._build_graph()

    def explain(self, finding: Finding) -> AgentState:
        query = self._trusted_retrieval_query(finding)
        return self.graph.invoke(
            {
                "finding": finding,
                "query": query,
                "evidence": [],
                "explanation": None,
                "status": "started",
                "generation_error": None,
                "audit_events": [],
            }
        )

    def warmup(self) -> None:
        """Semantic retrieval ve varsa yerel LLM hattını belleğe alır."""

        self._retriever.search("UBL-TR e-Fatura doğrulama", limit=1)
        generator_warmup = getattr(self._generator, "warmup", None)
        if callable(generator_warmup):
            generator_warmup()

    @staticmethod
    def _trusted_retrieval_query(finding: Finding) -> str:
        """Bulguya ait ham metni RAG sorgusuna taşımadan teknik kanıt arar.

        XML hata mesajı, kullanıcı girdisi ya da dış kütüphanenin açıklaması gibi
        veriler talimat içerebilir. Retrieval için bunlara ihtiyaç yoktur: her
        desteklenen bulgu kodu, ilgili GİB terimlerini içeren sabit bir sözlüğe
        eşlenir. Tanınmayan kodda ise yalnızca kısa kimlik alanları kullanılır.
        """

        vocabulary = {
            "xml-bicim": "UBL-TR XML iyi biçimli XSD şema doğrulama",
            "hesap-dip-satir": "UBL-TR LegalMonetaryTotal LineExtensionAmount InvoiceLine",
            "hesap-dip-vergi-haric": (
                "UBL-TR TaxExclusiveAmount LegalMonetaryTotal "
                "AllowanceTotalAmount ChargeTotalAmount"
            ),
            "imza-yok": "UBL-TR XAdES UBLExtensions ExtensionContent ds Signature",
        }
        if finding.code in vocabulary:
            return vocabulary[finding.code]

        code = finding.code.casefold()
        if code.startswith("xsd-"):
            return "UBL-TR XSD XML eleman sırası zorunlu alan schema doğrulama"
        if code.startswith("hesap-satir"):
            return "UBL-TR InvoiceLine LineExtensionAmount InvoicedQuantity Price AllowanceCharge"
        if code.startswith("hesap-vergi"):
            return "UBL-TR TaxSubtotal TaxAmount TaxableAmount Percent vergi hesaplama"
        if code.startswith("hesap-tevkifat"):
            return "UBL-TR WithholdingTaxTotal TaxAmount TaxTypeCode Percent tevkifat"
        if code == "hesap-dip-indirim":
            return "UBL-TR AllowanceTotalAmount AllowanceCharge ChargeIndicator indirim"
        if code == "hesap-dip-artirim":
            return "UBL-TR ChargeTotalAmount AllowanceCharge ChargeIndicator artırım"
        if code == "hesap-dip-vergi-dahil":
            return "UBL-TR TaxInclusiveAmount TaxExclusiveAmount TaxTotal vergi dahil tutar"
        if code == "hesap-dip-odenecek":
            return "UBL-TR PayableAmount PayableRoundingAmount WithholdingTaxTotal"
        if code == "hesap-para-birimi":
            return "UBL-TR DocumentCurrencyCode currencyID para birimi"
        if "invoiceid" in code:
            return "UBL-TR Invoice cbc ID fatura numarası formatı"
        if "uuid" in code:
            return "UBL-TR cbc UUID fatura tekil kimlik formatı"
        if "tarihbicimi" in code or "timecheck" in code:
            return "UBL-TR IssueDate IssueTime düzenleme tarihi saat formatı"
        if any(term in code for term in ("profileid", "invoicetypecode", "customizationid", "ublversionid")):
            return "UBL-TR ProfileID InvoiceTypeCode CustomizationID UBLVersionID senaryo fatura tipi"
        if "currency" in code:
            return "UBL-TR DocumentCurrencyCode currencyID PricingExchangeRate döviz kuru"
        if "unitcode" in code or "invoicedquantity" in code:
            return "UBL-TR InvoicedQuantity unitCode UN ECE ölçü birimi"
        if "partyidentification" in code:
            return "UBL-TR PartyIdentification VKN TCKN schemeID PartyName Person"
        if "taxexemption" in code or "taxtype" in code:
            return "UBL-TR TaxCategory TaxScheme TaxTypeCode TaxExemptionReasonCode"
        if "withholdingtax" in code or "generalwithholding" in code:
            return "UBL-TR WithholdingTaxTotal TaxTypeCode Percent tevkifat"
        if "xades" in code or "signature" in code:
            return "UBL-TR XAdES UBLExtensions ExtensionContent ds Signature KeyInfo SigningTime"
        if "iade" in code or "billingreference" in code:
            return "UBL-TR IADE BillingReference InvoiceDocumentReference InvoiceTypeCode"
        if "paymentmeans" in code or "kamufatura" in code:
            return "UBL-TR PaymentMeans PaymentMeansCode PayeeFinancialAccount IBAN"
        return f"UBL-TR {finding.code} {finding.source}"

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("retrieve_official_sources", self._retrieve_official_sources)
        workflow.add_node(
            "generate_source_backed_explanation", self._generate_source_backed_explanation
        )
        workflow.add_node("await_human_review", self._await_human_review)
        workflow.add_node("insufficient_evidence", self._insufficient_evidence)
        workflow.add_edge(START, "retrieve_official_sources")
        workflow.add_conditional_edges(
            "retrieve_official_sources",
            self._route_after_retrieval,
            {"generate": "generate_source_backed_explanation", "missing": "insufficient_evidence"},
        )
        workflow.add_edge("generate_source_backed_explanation", "await_human_review")
        workflow.add_edge("await_human_review", END)
        workflow.add_edge("insufficient_evidence", END)
        return workflow.compile()

    def _retrieve_official_sources(self, state: AgentState) -> dict[str, object]:
        candidates = self._retriever.search(state["query"], limit=3)
        evidence = [item for item in candidates if not self._is_version_history(item)]
        return {
            "evidence": evidence,
            "audit_events": [*state["audit_events"], f"retrieve_official_sources:{len(evidence)}"],
        }

    @staticmethod
    def _route_after_retrieval(state: AgentState) -> Literal["generate", "missing"]:
        return (
            "generate"
            if SourceBackedAgent._has_sufficient_evidence(state["evidence"])
            else "missing"
        )

    @staticmethod
    def _has_sufficient_evidence(evidence: list[RetrievedEvidence]) -> bool:
        """Genel başlık/versiyon metinleriyle kesin GİB iddiası kurulmasını engeller."""

        return any(item.rerank_score >= 0.50 and item.exact_term_score >= 0.12 for item in evidence)

    @staticmethod
    def _is_version_history(item: RetrievedEvidence) -> bool:
        text = item.chunk.text.lower()
        return "versiyon yayım tarihi" in text or "eklenen/silinen/değişen bölüm" in text

    def _generate_source_backed_explanation(self, state: AgentState) -> dict[str, object]:
        try:
            explanation = self._generator.generate(state["finding"], state["evidence"])
        except LLMUnavailableError as error:
            return {
                "explanation": None,
                "status": "generation_unavailable",
                "generation_error": str(error),
                "audit_events": [*state["audit_events"], "source_generation_unavailable"],
            }
        return {
            "explanation": explanation,
            "generation_error": explanation.provider_trace,
            "audit_events": [
                *state["audit_events"],
                *( ["api_provider_fallback"] if explanation.provider_trace else [] ),
                "deterministic_source_fallback"
                if explanation.generation_mode == "deterministic_fallback"
                else "generate_source_backed_explanation",
            ],
        }

    @staticmethod
    def _await_human_review(state: AgentState) -> dict[str, object]:
        return {
            "status": state["status"]
            if state["status"] == "generation_unavailable"
            else "awaiting_human_review",
            "audit_events": [*state["audit_events"], "await_human_review"],
        }

    @staticmethod
    def _insufficient_evidence(state: AgentState) -> dict[str, object]:
        return {
            "status": "insufficient_official_evidence",
            "audit_events": [*state["audit_events"], "insufficient_evidence"],
        }
