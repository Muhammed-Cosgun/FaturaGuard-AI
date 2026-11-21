document.querySelectorAll('[data-document-chat]').forEach((panel) => {
  const form = panel.querySelector('form');
  const input = form.elements.question;
  const log = panel.querySelector('[role="log"]');
  const status = panel.querySelector('.chat-status');
  let busy = false;
  const addText = (parent, tag, text, className) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
  };
  panel.querySelectorAll('[data-chat-prompt]').forEach((button) => {
    button.addEventListener('click', () => {
      if (busy) return;
      form.elements.finding_code.value = '';
      input.value = button.dataset.chatPrompt;
      form.requestSubmit();
    });
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy || !input.value.trim()) return;
    busy = true;
    const data = new FormData(form);
    const buttons = form.querySelectorAll('button');
    buttons.forEach((button) => { button.disabled = true; });
    status.textContent = 'Yanıt hazırlanıyor…';
    log.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: data, headers: { Accept: 'application/json' },
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Soru gönderilemedi. Tekrar deneyin.');
      const turn = result.turn;
      panel.querySelector('.chat-empty').hidden = true;
      const article = addText(log, 'article', '', 'chat-turn');
      const question = addText(article, 'p', '', 'chat-question');
      addText(question, 'strong', 'Siz');
      addText(question, 'span', turn.question);
      const answer = addText(article, 'div', '', 'chat-answer');
      const label = turn.mode === 'llm_chat' ? 'AI sohbeti'
        : turn.mode === 'local_fallback' ? 'Yerel yedek yanıt'
        : turn.mode === 'source_backed' ? 'Kaynaklı AI açıklaması'
        : turn.mode === 'source_summary' ? 'Güvenli kaynak özeti' : 'İşlem rehberi';
      addText(answer, 'strong', 'Asistan · ' + label);
      addText(answer, 'p', turn.answer);
      if (turn.citations.length) {
        const list = addText(answer, 'ul', '', 'chat-citations');
        turn.citations.forEach((citation) => {
          const item = addText(list, 'li', '');
          const link = addText(item, 'a', citation.source_title + ', s. ' + citation.page);
          link.href = citation.source_url;
          link.target = '_blank';
          link.rel = 'noopener';
        });
      }
      while (log.querySelectorAll('.chat-turn').length > 20) {
        log.querySelector('.chat-turn').remove();
      }
      // Yanıt beklerken yeni yazılan metni silme.
      if (input.value === data.get('question')) input.value = '';
      log.scrollTop = log.scrollHeight;
      status.textContent = 'Yanıt hazır.';
    } catch (error) {
      status.textContent = error.message || 'Bağlantı kurulamadı. Tekrar deneyin.';
    } finally {
      busy = false;
      buttons.forEach((button) => { button.disabled = false; });
      log.setAttribute('aria-busy', 'false');
    }
  });
});
