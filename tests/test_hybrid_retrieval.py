from faturaguard.services.hybrid_retrieval import HybridRetriever, ScoredChunk
from faturaguard.services.official_rag import RagChunk


class FakeSemanticStore:
    def __init__(self, results):
        self.results = results

    def search(self, query, limit, where=None):
        return self.results


class FakeLexicalRetriever:
    def __init__(self, results):
        self.results = results

    def search(self, query, limit):
        return self.results


def test_hybrid_rerank_prioritizes_semantic_and_exact_technical_evidence() -> None:
    correct = RagChunk(
        "gib-test",
        "GİB Test Planı",
        "https://ebelge.gib.gov.tr/test.pdf",
        7,
        "UBL-TR formatına uygun e-fatura şema XSD ve schematron kontrolünden geçirilmelidir.",
    )
    weaker = RagChunk(
        "gib-guide",
        "GİB Kılavuzu",
        "https://ebelge.gib.gov.tr/guide.pdf",
        2,
        "Elektronik fatura uygulamasında mesajlaşma altyapısı bulunur.",
    )
    retriever = HybridRetriever(
        FakeSemanticStore([ScoredChunk(weaker, 0.95), ScoredChunk(correct, 0.80)]),
        FakeLexicalRetriever([ScoredChunk(correct, 8.0)]),
    )

    results = retriever.search("e-fatura şema schematron kontrolü")

    assert results[0].chunk == correct
    assert results[0].lexical_score == 1.0
    assert results[0].exact_term_score > 0
