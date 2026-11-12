"""LangGraph üzerinde kaynak açıklaması ve güvenli belge orkestrasyonu."""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from faturaguard.domain.correction import CorrectionProposal
from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.services.correction_workflow import CorrectionWorkflow
from faturaguard.services.document_storage import StoredDocument
from faturaguard.services.hybrid_retrieval import RetrievedEvidence
from faturaguard.services.source_backed_explanation import (
    AgentCorrectionPlan,
    CorrectionPlanGenerator,
    DeterministicCorrectionPlanGenerator,
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


class DocumentAgentState(TypedDict):
    """Belge verisini yalnızca yerel araçlar arasında taşıyan agent durumu."""

    stored: StoredDocument
    workflow: CorrectionWorkflow
    report: object | None
    job: object | None
    correction_sequence: list[dict[str, object]]
    status: str
    audit_events: list[str]


class DecisionAgentState(TypedDict):
    workflow: CorrectionWorkflow
    job_id: str
    proposal_id: str
    decision: str
    job: object | None
    status: str
    audit_events: list[str]


class SourceBackedAgent:
    """Araç allowlist'iyle sınırlı, koşullu yönlendirmeli bir LangGraph agent'ı."""

    def __init__(
        self,
        retriever,
        generator: ExplanationGenerator,
        correction_planner: CorrectionPlanGenerator | None = None,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._correction_planner = correction_planner or DeterministicCorrectionPlanGenerator()
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

    def plan_safe_correction(
        self, finding: Finding, proposal: CorrectionProposal
    ) -> AgentCorrectionPlan:
        """LLM'e yalnızca maskeli aday patch göndererek düzeltme planı alır."""
        query = self._trusted_retrieval_query(finding)
        evidence = [
            item
            for item in self._retriever.search(query, limit=3)
            if not self._is_version_history(item)
        ]
        if not self._has_sufficient_evidence(evidence):
            return AgentCorrectionPlan(
                decision="human_review",
                rationale="Yeterli resmî GİB kanıtı bulunamadı; insan incelemesi gerekir.",
                requires_user_approval=True,
                citations=[],
                generation_mode="insufficient_official_evidence",
            )
        candidates = [
            {
                "candidate_id": proposal.proposal_id,
                "finding_code": proposal.finding_code,
                "rule_id": proposal.rule_id,
                "operation": "replace_text",
                "target_token": "TARGET_FIELD_1",
                "before_token": "CURRENT_VALUE_1",
                "after_token": "RECALCULATED_VALUE_1",
                "risk": "low",
            }
        ]
        plan = self._correction_planner.generate(finding, candidates, evidence)
        return self._guard_correction_plan(plan, proposal)

    @staticmethod
    def _guard_correction_plan(
        plan: AgentCorrectionPlan, proposal: CorrectionProposal
    ) -> AgentCorrectionPlan:
        """LLM planını izinli adayla bire bir eşleştirmeden uygulatmaz."""
        if plan.decision == "human_review":
            return plan
        valid_patch = len(plan.patches) == 1 and plan.patches[0].model_dump() == {
            "operation": "replace_text",
            "target_token": "TARGET_FIELD_1",
            "before_token": "CURRENT_VALUE_1",
            "after_token": "RECALCULATED_VALUE_1",
        }
        if (
            plan.selected_candidate_id != proposal.proposal_id
            or not plan.requires_user_approval
            or not valid_patch
            or not plan.citations
        ):
            return AgentCorrectionPlan(
                decision="human_review",
                rationale="LLM planı güvenlik politikasıyla eşleşmedi; insan incelemesi gerekir.",
                requires_user_approval=True,
                citations=plan.citations,
                generation_mode="guard_rejected_correction_plan",
                provider_trace=plan.provider_trace,
            )
        return plan

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


class FaturaGuardAgent:
    """FaturaGuard'ın araç kullanan, insan onaylı iş akışı orkestratörü.

    Bu sınıf bir LLM'e XML vermez. LangGraph yalnızca yerel doğrulama/düzeltme
    araçlarının çağrılma sırasını ve insan kararına göre yönlendirmeyi yönetir.
    Kaynaklı doğal dil açıklaması gerektiğinde ``SourceBackedAgent`` alt aracını
    kullanır.
    """

    def __init__(self, source_agent: SourceBackedAgent | None = None) -> None:
        self._source_agent = source_agent
        self.intake_graph = self._build_intake_graph()
        self.decision_graph = self._build_decision_graph()

    def process_uploaded_document(
        self, stored: StoredDocument, workflow: CorrectionWorkflow
    ) -> DocumentAgentState:
        """Doğrula → güvenli teklif üret → insan incelemesine yönlendir."""
        return self.intake_graph.invoke(
            {
                "stored": stored,
                "workflow": workflow,
                "report": None,
                "job": None,
                "correction_sequence": [],
                "status": "started",
                "audit_events": [],
            }
        )

    def handle_correction_decision(
        self,
        workflow: CorrectionWorkflow,
        job_id: str,
        proposal_id: str,
        decision: str,
    ) -> DecisionAgentState:
        """İnsan kararından sonra yalnızca izinli düzeltme aracını çalıştırır."""
        return self.decision_graph.invoke(
            {
                "workflow": workflow,
                "job_id": job_id,
                "proposal_id": proposal_id,
                "decision": decision,
                "job": None,
                "status": "started",
                "audit_events": [],
            }
        )

    def explain_finding(self, job_id: str, finding_code: str, workflow: CorrectionWorkflow):
        if self._source_agent is None:
            raise RuntimeError("GİB RAG indeksi hazır değil; kaynaklı açıklama üretilemez.")
        return workflow.explain_finding(job_id, finding_code, self._source_agent)

    def _build_intake_graph(self):
        graph = StateGraph(DocumentAgentState)
        graph.add_node("validate_document", self._validate_document)
        graph.add_node("propose_safe_corrections", self._propose_safe_corrections)
        graph.add_node("plan_correction_sequence", self._plan_correction_sequence)
        graph.add_node("assess_document_risk", self._assess_document_risk)
        graph.add_node("await_human_review", self._await_human_review)
        graph.add_node("report_ready", self._report_ready)
        graph.add_edge(START, "validate_document")
        graph.add_edge("validate_document", "propose_safe_corrections")
        graph.add_conditional_edges(
            "assess_document_risk",
            self._route_after_intake,
            {"review": "await_human_review", "complete": "report_ready"},
        )
        graph.add_edge("propose_safe_corrections", "plan_correction_sequence")
        graph.add_edge("plan_correction_sequence", "assess_document_risk")
        graph.add_edge("await_human_review", END)
        graph.add_edge("report_ready", END)
        return graph.compile()

    @staticmethod
    def _validate_document(state: DocumentAgentState) -> dict[str, object]:
        report = state["workflow"].validate_stored(state["stored"])
        return {
            "report": report,
            "audit_events": [*state["audit_events"], "agent_tool_validate_document"],
        }

    @staticmethod
    def _plan_correction_sequence(state: DocumentAgentState) -> dict[str, object]:
        """İzinli tekliflerin bağımlılıklarını analiz eder; XML'e erişmez veya yazmaz."""
        job = state["job"]
        if job is None:
            raise RuntimeError("Agent düzeltme sıralaması için iş kaydı bulamadı.")

        rule_metadata = {
            "recalculate-line-extension-total": {
                "rank": 10,
                "depends_on": [],
                "expected_effect": "Satır toplamını temel dip toplam ile eşitler; sonraki vergi hariç toplam kontrolünü etkileyebilir.",
            },
            "recalculate-tax-exclusive-total": {
                "rank": 20,
                "depends_on": ["recalculate-line-extension-total"],
                "expected_effect": "Vergi hariç toplamı günceller; vergiler dahil ve ödenecek tutar kontrollerini etkileyebilir.",
            },
            "recalculate-tax-inclusive-total": {
                "rank": 30,
                "depends_on": ["recalculate-tax-exclusive-total"],
                "expected_effect": "Vergiler dahil toplamı günceller; ödenecek tutar kontrolünü etkileyebilir.",
            },
            "recalculate-payable-total": {
                "rank": 40,
                "depends_on": ["recalculate-tax-inclusive-total"],
                "expected_effect": "Yalnızca ödenecek tutarı günceller; ödeme bilgileri ve taraf verileri değişmez.",
            },
        }
        present_rules = {proposal.rule_id for proposal in job.proposals}
        sequence = []
        for proposal in sorted(
            job.proposals,
            key=lambda item: (rule_metadata.get(item.rule_id, {"rank": 99})["rank"], item.proposal_id),
        ):
            metadata = rule_metadata.get(
                proposal.rule_id,
                {
                    "depends_on": [],
                    "expected_effect": "Bu izinli düzeltmenin etkisi yeniden doğrulama ile denetlenmelidir.",
                },
            )
            dependencies = [rule for rule in metadata["depends_on"] if rule in present_rules]
            agent_plan = proposal.agent_plan or {}
            sequence.append(
                {
                    "order": len(sequence) + 1,
                    "proposal_id": proposal.proposal_id,
                    "finding_code": proposal.finding_code,
                    "title": proposal.title,
                    "rule_id": proposal.rule_id,
                    "depends_on": dependencies,
                    "approval_ready": agent_plan.get("decision") == "propose",
                    "expected_effect": metadata["expected_effect"],
                }
            )
        state["workflow"].record_agent_event(
            job.job_id,
            "agent_tool_plan_correction_sequence",
            {"sequence_count": len(sequence), "execution_scope": "metadata_only"},
        )
        return {
            "correction_sequence": sequence,
            "audit_events": [*state["audit_events"], "agent_tool_plan_correction_sequence"],
        }

    @staticmethod
    def _assess_document_risk(state: DocumentAgentState) -> dict[str, object]:
        """Agent'ın yerel bulgulardan sonraki işlem planını ve kalite kapısını üretir.

        Bu araç LLM'e veya ham XML'e erişmez. Böylece agent, riskli belgeleri
        önceliklendirirken gizlilik sınırını ve kararların tekrarlanabilirliğini korur.
        """
        job = state["job"]
        if job is None:
            raise RuntimeError("Agent işlem planı için iş kaydı bulamadı.")

        findings = list(job.report.findings)
        priority_findings = sorted(
            findings,
            key=lambda item: (
                item.priority is not Priority.CRITICAL,
                item.priority is not Priority.HIGH,
                item.code,
            ),
        )
        blocking = [
            item.code
            for item in priority_findings
            if item.severity is Severity.ERROR or item.priority is Priority.CRITICAL
        ]
        ready_proposals = sum(
            1
            for proposal in job.proposals
            if proposal.agent_plan and proposal.agent_plan.get("decision") == "propose"
        )
        sequence = state["correction_sequence"]
        human_review_questions = FaturaGuardAgent._human_review_questions(findings, sequence)

        if blocking:
            triage = {
                "route": "blocked",
                "priority_finding_codes": blocking[:3],
                "safe_correction_ready_count": 0,
                "recommended_next_actions": [
                    "Önce doğrulamayı durduran bulguları inceleyin.",
                    "Gerekliyse ilgili bulgu için resmî GİB kaynağıyla açıklama isteyin.",
                    "Belgeyi düzelttikten sonra yeniden doğrulayın.",
                ],
                "rationale": "Kritik veya hata seviyesindeki bulgular belgeyi gönderim için bloke eder.",
                "privacy_boundary": "ham_xml_local_only",
                "correction_sequence": sequence,
                "human_review_questions": human_review_questions,
            }
        elif findings:
            actions = ["Öncelikli bulguları resmî GİB kaynaklarıyla inceleyin."]
            if ready_proposals:
                actions.append("AI Agent'ın önerdiği düşük riskli düzeltmeyi onaylayın veya reddedin.")
            actions.append("Gönderimden önce yeniden doğrulama sonucunu inceleyin.")
            triage = {
                "route": "needs_human_review",
                "priority_finding_codes": [item.code for item in priority_findings[:3]],
                "safe_correction_ready_count": ready_proposals,
                "recommended_next_actions": actions,
                "rationale": "Belge teknik olarak okunabilir; ancak bulgular insan incelemesi gerektirir.",
                "privacy_boundary": "ham_xml_local_only",
                "correction_sequence": sequence,
                "human_review_questions": human_review_questions,
            }
        else:
            triage = {
                "route": "ready_for_manual_submission_review",
                "priority_finding_codes": [],
                "safe_correction_ready_count": 0,
                "recommended_next_actions": [
                    "Belge teknik doğrulamayı geçti.",
                    "Gönderim öncesi iş süreci ve yetkili imza kontrollerini tamamlayın.",
                ],
                "rationale": "Doğrulama bulgusu bulunmadı; GİB'e gönderim kararı yine kullanıcı/kurum sorumluluğundadır.",
                "privacy_boundary": "ham_xml_local_only",
                "correction_sequence": sequence,
                "human_review_questions": human_review_questions,
            }

        job.agent_triage = triage
        state["workflow"].save_agent_plan(job)
        state["workflow"].record_agent_event(
            job.job_id,
            "agent_tool_assess_document_risk",
            {
                "route": triage["route"],
                "priority_finding_codes": triage["priority_finding_codes"],
                "safe_correction_ready_count": ready_proposals,
                "correction_sequence_count": len(sequence),
                "human_review_question_count": len(human_review_questions),
                "privacy_boundary": "ham_xml_local_only",
            },
        )
        return {
            "job": job,
            "audit_events": [*state["audit_events"], "agent_tool_assess_document_risk"],
        }

    @staticmethod
    def _human_review_questions(
        findings: list[Finding], sequence: list[dict[str, object]]
    ) -> list[str]:
        """Agentın insan onayı öncesi istediği, ham veri içermeyen karar soruları."""
        codes = {finding.code for finding in findings}
        questions: list[str] = []
        if "imza-yok" in codes:
            questions.append("Belge taslak/test belgesi mi, yoksa GİB'e gönderilecek nihai belge mi?")
        if any("tevkifat" in code or "odenecek" in code for code in codes):
            questions.append("Tevkifat ve varsa yuvarlama tutarlarının iş süreci tarafından onaylandığı doğrulandı mı?")
        if any(item["depends_on"] for item in sequence):
            questions.append("Bağımlı dip toplam düzeltmeleri önerilen sırayla uygulanıp her adım sonrası yeniden doğrulanacak mı?")
        if not questions and findings:
            questions.append("Belgeyi oluşturan kaynak sistemde ilgili iş kuralı ve tutarlar doğrulandı mı?")
        return questions

    def _propose_safe_corrections(self, state: DocumentAgentState) -> dict[str, object]:
        report = state["report"]
        if report is None:
            raise RuntimeError("Agent doğrulama sonucu olmadan düzeltme teklifi üretemez.")
        workflow = state["workflow"]
        job = workflow.create(state["stored"], report)
        # İş kaydı doğrulamadan sonra oluşur; bu nedenle doğrulama aracının
        # gerçekleştiğini kayda oluşturulduktan hemen sonra açıkça ekleriz.
        workflow.record_agent_event(
            job.job_id,
            "agent_tool_validate_document",
            {"execution_scope": "local_only", "executed_before_job_creation": True},
        )
        workflow.record_agent_event(
            job.job_id,
            "agent_tool_propose_safe_corrections",
            {"proposal_count": len(job.proposals)},
        )
        plans_created = 0
        if self._source_agent is not None:
            for proposal in job.proposals:
                finding = next(
                    (item for item in job.report.findings if item.code == proposal.finding_code), None
                )
                if finding is None:
                    continue
                plan = self._source_agent.plan_safe_correction(finding, proposal)
                proposal.agent_plan = plan.model_dump(mode="json")
                plans_created += 1
                workflow.record_agent_event(
                    job.job_id,
                    "agent_llm_masked_patch_plan",
                    {
                        "proposal_id": proposal.proposal_id,
                        "decision": plan.decision,
                        "generation_mode": plan.generation_mode,
                        "provider_trace": plan.provider_trace,
                        "uses_masked_tokens": True,
                    },
                )
        if plans_created:
            workflow.save_agent_plan(job)
        return {
            "job": job,
            "audit_events": [
                *state["audit_events"],
                "agent_tool_propose_safe_corrections",
                *(["agent_llm_masked_patch_plan"] if plans_created else []),
            ],
        }

    @staticmethod
    def _route_after_intake(state: DocumentAgentState) -> Literal["review", "complete"]:
        job = state["job"]
        if job is None:
            raise RuntimeError("Agent işlem kaydı oluşturmadan rota belirleyemez.")
        triage = job.agent_triage or {}
        return (
            "complete"
            if triage.get("route") == "ready_for_manual_submission_review"
            else "review"
        )

    @staticmethod
    def _await_human_review(state: DocumentAgentState) -> dict[str, object]:
        job = state["job"]
        if job is not None:
            state["workflow"].record_agent_event(
                job.job_id, "agent_route_await_human_review", {"reason": "findings_or_proposals"}
            )
        return {
            "status": "awaiting_human_review",
            "audit_events": [*state["audit_events"], "agent_route_await_human_review"],
        }

    @staticmethod
    def _report_ready(state: DocumentAgentState) -> dict[str, object]:
        job = state["job"]
        if job is not None:
            state["workflow"].record_agent_event(
                job.job_id, "agent_route_report_ready", {"reason": "no_findings"}
            )
        return {
            "status": "report_ready",
            "audit_events": [*state["audit_events"], "agent_route_report_ready"],
        }

    def _build_decision_graph(self):
        graph = StateGraph(DecisionAgentState)
        graph.add_node("apply_safe_correction", self._apply_safe_correction)
        graph.add_node("record_rejection", self._record_rejection)
        graph.add_node("report_correction_result", self._report_correction_result)
        graph.add_edge(START, "apply_safe_correction")
        graph.add_conditional_edges(
            "apply_safe_correction",
            self._route_after_decision,
            {"approved": "report_correction_result", "rejected": "record_rejection"},
        )
        graph.add_edge("record_rejection", "report_correction_result")
        graph.add_edge("report_correction_result", END)
        return graph.compile()

    @staticmethod
    def _apply_safe_correction(state: DecisionAgentState) -> dict[str, object]:
        if state["decision"] != "approve":
            return {"status": "rejected", "audit_events": [*state["audit_events"], "agent_received_rejection"]}
        pending_job = state["workflow"].load_job(state["job_id"])
        pending_proposal = next(
            (item for item in pending_job.proposals if item.proposal_id == state["proposal_id"]), None
        )
        plan = pending_proposal.agent_plan if pending_proposal is not None else None
        if not plan or plan.get("decision") != "propose":
            raise ValueError("AI Agent tarafından onaylanmış güvenli patch planı bulunamadı.")
        job = state["workflow"].decide(state["job_id"], state["proposal_id"], "approve")
        proposal = next(p for p in job.proposals if p.proposal_id == state["proposal_id"])
        state["workflow"].record_agent_event(
            job.job_id,
            "agent_tool_apply_safe_correction",
            {"proposal_id": state["proposal_id"], "rule_id": proposal.rule_id},
        )
        state["workflow"].record_agent_event(
            job.job_id, "agent_tool_revalidate_corrected_copy", {"revalidated": job.corrected_report is not None}
        )
        return {
            "job": job,
            "status": "approved",
            "audit_events": [
                *state["audit_events"],
                "agent_tool_apply_safe_correction",
                "agent_tool_revalidate_corrected_copy",
            ],
        }

    @staticmethod
    def _route_after_decision(state: DecisionAgentState) -> Literal["approved", "rejected"]:
        return "approved" if state["status"] == "approved" else "rejected"

    @staticmethod
    def _record_rejection(state: DecisionAgentState) -> dict[str, object]:
        job = state["workflow"].decide(state["job_id"], state["proposal_id"], "reject")
        state["workflow"].record_agent_event(
            job.job_id, "agent_tool_record_rejection", {"proposal_id": state["proposal_id"]}
        )
        return {
            "job": job,
            "status": "rejected",
            "audit_events": [*state["audit_events"], "agent_tool_record_rejection"],
        }

    @staticmethod
    def _report_correction_result(state: DecisionAgentState) -> dict[str, object]:
        job = state["job"]
        if job is not None:
            state["workflow"].record_agent_event(
                job.job_id, "agent_tool_report_correction_result", {"status": state["status"]}
            )
        return {
            "audit_events": [*state["audit_events"], "agent_tool_report_correction_result"],
        }
