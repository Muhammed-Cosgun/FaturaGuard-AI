"""Aktif LLM zincirinin maskeli düzeltme planı üretebildiğini anahtar göstermeden denetler."""

from faturaguard.domain.correction import CorrectionProposal
from faturaguard.domain.validation import Finding, Priority, Severity
from faturaguard.main import _create_agent


def main() -> None:
    agent = _create_agent()
    if agent is None:
        raise SystemExit("RAG indeksi hazır değil; önce build_gib_index.py ve build_chroma_index.py çalıştırın.")
    finding = Finding(
        code="hesap-dip-odenecek",
        severity=Severity.WARNING,
        priority=Priority.HIGH,
        priority_reason="Demo smoke testi.",
        source="hesap",
        message="Bu metin LLM'e gönderilmez.",
    )
    proposal = CorrectionProposal(
        proposal_id="smoke-payable-candidate",
        rule_id="recalculate-payable-total",
        finding_code="hesap-dip-odenecek",
        title="Smoke test",
        rationale="Yerel test adayı.",
        target_path="cac:LegalMonetaryTotal/cbc:PayableAmount",
        before="MASKED",
        after="MASKED",
    )
    plan = agent.plan_safe_correction(finding, proposal)
    print(f"decision={plan.decision}")
    print(f"generation_mode={plan.generation_mode}")
    print(f"citation_count={len(plan.citations)}")
    print(f"provider_trace={plan.provider_trace or 'none'}")
    if plan.decision != "propose":
        raise SystemExit("Correction-plan smoke testi güvenli plan üretemedi.")


if __name__ == "__main__":
    main()
