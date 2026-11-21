document.querySelectorAll('[data-document-chat]').forEach((panel) => {
  const workspace = panel.closest('.document-workspace');
  const form = panel.querySelector('form');
  const input = form.elements.question;
  const log = panel.querySelector('[role="log"]');
  const status = panel.querySelector('.chat-status');
  const launcher = workspace.querySelector('[data-chat-open]');
  const closeButton = panel.querySelector('[data-chat-close]');
  const backdrop = workspace.querySelector('[data-chat-backdrop]');
  const mobile = window.matchMedia('(max-width: 1099px)');
  const protectedRegions = document.querySelectorAll('.document-content, .topbar, .site-footer');
  const previousInert = new Map();
  let busy = false;
  let followResponse = true;
  workspace.classList.add('chat-enhanced');

  const syncViewport = () => {
    const viewport = window.visualViewport;
    if (mobile.matches && panel.dataset.open === 'true' && viewport) {
      panel.style.setProperty('--chat-viewport-height', viewport.height + 'px');
      panel.style.setProperty('--chat-viewport-top', viewport.offsetTop + 'px');
    } else {
      panel.style.removeProperty('--chat-viewport-height');
      panel.style.removeProperty('--chat-viewport-top');
    }
  };
  window.visualViewport?.addEventListener('resize', syncViewport);
  window.visualViewport?.addEventListener('scroll', syncViewport);

  const setOpen = (open, restoreFocus = true) => {
    const isDialog = open && mobile.matches;
    panel.dataset.open = String(isDialog);
    launcher.hidden = !mobile.matches || isDialog;
    closeButton.hidden = !mobile.matches;
    launcher.setAttribute('aria-expanded', String(isDialog));
    backdrop.hidden = !isDialog;
    syncViewport();
    document.body.classList.toggle('chat-overlay-open', isDialog);
    if (isDialog) {
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      protectedRegions.forEach((region) => {
        if (!previousInert.has(region)) previousInert.set(region, region.inert);
        region.inert = true;
      });
      closeButton.focus();
      log.scrollTop = log.scrollHeight;
    } else {
      panel.removeAttribute('role');
      panel.removeAttribute('aria-modal');
      previousInert.forEach((wasInert, region) => { region.inert = wasInert; });
      previousInert.clear();
      if (mobile.matches && restoreFocus) launcher.focus();
    }
  };
  launcher.addEventListener('click', () => { setOpen(true); });
  closeButton.addEventListener('click', () => { setOpen(false); });
  backdrop.addEventListener('click', () => { setOpen(false); });
  mobile.addEventListener('change', () => {
    const wasInside = panel.contains(document.activeElement);
    setOpen(false, wasInside);
    if (!mobile.matches && wasInside) input.focus({ preventScroll: true });
  });
  panel.addEventListener('keydown', (event) => {
    if (!mobile.matches || panel.dataset.open !== 'true') return;
    if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false);
    }
    if (event.key === 'Tab') {
      const items = Array.from(panel.querySelectorAll('button:not([disabled]), a[href], textarea, select, summary, [tabindex="0"]'))
        .filter((element) => !element.hidden && element.getClientRects().length > 0);
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }
  });
  setOpen(false, false);
  log.scrollTop = log.scrollHeight;

  const resizeInput = () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    panel.querySelector('[data-chat-count]').textContent = input.value.length + ' / 600';
  };
  input.addEventListener('input', resizeInput);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!busy) form.requestSubmit();
    }
  });
  log.addEventListener('scroll', () => {
    if (busy) followResponse = log.scrollHeight - log.scrollTop - log.clientHeight < 100;
  });
  const addText = (parent, tag, text, className) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
  };
  const questionBubble = (article, text) => {
    const question = addText(article, 'p', '', 'chat-question');
    addText(question, 'strong', 'Siz');
    addText(question, 'span', text);
  };
  const answerBubble = (article, turn) => {
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
  };
  panel.querySelectorAll('[data-chat-prompt]').forEach((button) => {
    button.addEventListener('click', () => {
      if (busy) return;
      form.elements.finding_code.value = '';
      input.value = button.dataset.chatPrompt;
      resizeInput();
      form.requestSubmit();
    });
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy || !input.value.trim()) return;
    busy = true;
    followResponse = true;
    const data = new FormData(form);
    const buttons = form.querySelectorAll('button');
    buttons.forEach((button) => { button.disabled = true; });
    status.classList.remove('is-error');
    status.textContent = 'Yanıt hazırlanıyor…';
    log.setAttribute('aria-busy', 'true');
    panel.querySelector('.chat-empty').hidden = true;
    const pending = addText(log, 'article', '', 'chat-turn is-pending');
    questionBubble(pending, data.get('question'));
    const pendingAnswer = addText(pending, 'div', '', 'chat-answer');
    const dots = addText(pendingAnswer, 'span', '', 'chat-typing');
    dots.setAttribute('aria-hidden', 'true');
    for (let i = 0; i < 3; i++) addText(dots, 'i', '');
    addText(pendingAnswer, 'span', 'Belgeniz inceleniyor…', 'chat-pending-label');
    log.scrollTop = log.scrollHeight;
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: data, headers: { Accept: 'application/json' },
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.error === 'string' ? result.error : 'Soru gönderilemedi. Tekrar deneyin.');
      const turn = result.turn;
      pending.querySelector('.chat-question span').textContent = turn.question;
      pendingAnswer.remove();
      pending.classList.remove('is-pending');
      answerBubble(pending, turn);
      while (log.querySelectorAll('.chat-turn').length > 20) log.querySelector('.chat-turn').remove();
      // Yanıt beklenirken yazılan yeni taslağı koru.
      if (input.value === data.get('question')) input.value = '';
      if (followResponse) log.scrollTop = log.scrollHeight;
      status.textContent = 'Yanıt hazır.';
    } catch (error) {
      pending.remove();
      panel.querySelector('.chat-empty').hidden = log.querySelectorAll('.chat-turn').length > 0;
      status.classList.add('is-error');
      status.textContent = error.message || 'Bağlantı kurulamadı. Tekrar deneyin.';
    } finally {
      busy = false;
      buttons.forEach((button) => { button.disabled = false; });
      log.setAttribute('aria-busy', 'false');
      resizeInput();
    }
  });
});
