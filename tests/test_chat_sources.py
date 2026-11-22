import pytest
from pydantic import ValidationError

from faturaguard import main
from faturaguard.domain.chat import ChatCitation, ChatTurn
from faturaguard.services.chat_sources import source_excerpt


def test_excerpt_is_normalized_actual_retrieved_text_not_model_generated():
    text = "Vergi hariç toplam.\n\n  Kaynakta tanımlanan\talan."
    assert source_excerpt(text) == "Vergi hariç toplam. Kaynakta tanımlanan alan."


@pytest.mark.parametrize("text", ["Vergi hariç toplam " * 150, "A" * 2300])
def test_excerpt_is_bounded_and_only_uses_the_context_available_to_model(text):
    excerpt = source_excerpt(text)
    assert len(excerpt) <= 361 and excerpt.endswith("…")
    assert " ".join(text[:1800].split()).startswith(excerpt[:-1])


def test_empty_text_does_not_fabricate_quote():
    assert source_excerpt(" \n\t ") == ""


def test_excerpt_prefers_trusted_technical_term_without_quoting_outside_model_context():
    text = "Önceki bölüm " * 60 + "MonetaryTotal TaxExclusiveAmount parasal toplam alanıdır. " * 15
    excerpt = source_excerpt(text, "UBL-TR TaxExclusiveAmount LegalMonetaryTotal")
    assert "TaxExclusiveAmount" in excerpt and len(excerpt) <= 362
    assert excerpt.startswith("…")
    assert excerpt.strip("…") in " ".join(text[:1800].split())


def test_source_card_escapes_real_excerpt_and_preserves_official_link():
    citation = ChatCitation(source_title="<b>Resmî kaynak</b>",
        source_url="https://ebelge.gib.gov.tr/guide.pdf", page=47,
        excerpt='Alan <cbc:TaxExclusiveAmount> ile tanımlıdır. <script>alert(1)</script>')
    html = main.templates.get_template("chat_source_card.html").render(citation=citation)
    assert "Sayfa 47" in html and "Kaynaktan kısa alıntı" in html
    assert "&lt;cbc:TaxExclusiveAmount&gt;" in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert 'href="https://ebelge.gib.gov.tr/guide.pdf"' in html and 'rel="noopener"' in html


def test_legacy_citation_without_excerpt_shows_missing_quote_honestly():
    turn = ChatTurn.model_validate({"question": "Soru", "answer": "Yanıt", "mode": "source_backed",
        "citations": [{"source_title": "GİB", "source_url": "https://ebelge.gib.gov.tr/guide.pdf", "page": 7}]})
    html = main.templates.get_template("chat_basis.html").render(turn=turn)
    assert "Bu kayıtta kısa alıntı bulunmuyor" in html and "<blockquote>" not in html


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://third-party.test/g.pdf"])
def test_source_cards_still_require_official_https_citations(url):
    with pytest.raises(ValidationError):
        ChatCitation(source_title="Kaynak", source_url=url, page=7, excerpt="Özet")
