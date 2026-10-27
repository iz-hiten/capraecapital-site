/* Caprae Capital site assistant widget.
   Include once per page:  <script src="/assets/chat/chat.js" defer></script>
   Optional attributes: data-api="/api/chat"  data-turnstile-sitekey="..."
   Replies are always inserted as plain text. Long ones are shortened with a "Know more" toggle, and
   the one matching page (our own pages only) gets an "Open … page" link under the answer. */
(function () {
  'use strict';
  if (window.__ccChat) return;
  window.__ccChat = true;

  var script = document.currentScript || document.querySelector('script[src*="/assets/chat/chat.js"]');
  var API = (script && script.getAttribute('data-api')) || '/api/chat';
  var SITEKEY = script && script.getAttribute('data-turnstile-sitekey');
  var BASE = script ? script.src.replace(/chat\.js(\?.*)?$/, '') : '/assets/chat/';
  var MAX = 600;
  var SHORT_WORDS = 60;                                   // longer answers show this many words, then "Know more"
  var STORE = 'cc-chat-v1';
  var SITE = 'https://capraecapital.com';
  var ALLOWED = [SITE + '/', 'https://post.saasquatchleads.com', 'https://www.linkedin.com/company/caprae-capital',
    'https://www.linkedin.com/in/kevinhshong', 'https://capraecapitalpartners.substack.com',
    'https://capraecapitalpartners.com/#careers', 'https://www.instagram.com/capraeofficial', 'mailto:partners@capraecapital.com'];
  var SUGGESTIONS = ['What is Search as a Service?', 'How much do your services cost?',
    'Who do you work with?', 'How do I get started?'];

  var state = { sessionId: null, transcript: [], turnstileToken: null, busy: false };
  try { var saved = JSON.parse(sessionStorage.getItem(STORE) || 'null'); if (saved) state = Object.assign(state, saved); } catch (e) {}
  function save() {
    try { sessionStorage.setItem(STORE, JSON.stringify({ sessionId: state.sessionId, transcript: state.transcript.slice(-40) })); } catch (e) {}
  }

  var link = document.createElement('link');
  link.rel = 'stylesheet'; link.href = BASE + 'chat.css';
  document.head.appendChild(link);

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'on') for (var ev in attrs.on) n.addEventListener(ev, attrs.on[ev]);
      else n.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) { n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return n;
  }

  // Returns a safe href, or null. Our own pages become relative paths so links stay on the
  // current domain (live or dev mirror).
  function allowedHref(href) {
    if (href.charAt(0) === '/' && href.charAt(1) !== '/') href = SITE + href;
    for (var i = 0; i < ALLOWED.length; i++) {
      if (href === ALLOWED[i] || href.indexOf(ALLOWED[i]) === 0) {
        return href.indexOf(SITE + '/') === 0 ? href.slice(SITE.length) : href;
      }
    }
    return null;
  }

  // The first ~SHORT_WORDS words, ending on a sentence where possible, or null if the text is short.
  function shortVersion(text) {
    var re = /\S+/g, n = 0, m, endAt = -1;
    while ((m = re.exec(text))) { if (++n === SHORT_WORDS) endAt = m.index + m[0].length; }
    if (n <= SHORT_WORDS + 15) return null;               // not worth hiding just a few words
    var cut = text.slice(0, endAt);
    var stop = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('\n'));
    if (stop > cut.length / 2) cut = cut.slice(0, stop + 1);
    return cut.replace(/[\s,;:.]+$/, '') + '…';
  }

  var launch, panel, log, input, send, tsBox;

  function build() {
    var icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">' +
      '<path d="M4 5h16v11H8l-4 4V5z" stroke-linejoin="round"/><path d="M8 9.5h8M8 12.5h5" stroke-linecap="round"/></svg>';
    launch = el('button', { type: 'button', class: 'cc-launch', 'aria-haspopup': 'dialog', 'aria-expanded': 'false',
      'aria-controls': 'cc-panel', 'aria-label': 'Ask Caprae Capital', title: 'Ask Caprae Capital', on: { click: open } });
    launch.innerHTML = icon;

    log = el('div', { class: 'cc-log', role: 'log', 'aria-live': 'polite', 'aria-relevant': 'additions' });
    input = el('textarea', { class: 'cc-input', rows: '1', maxlength: String(MAX), id: 'cc-input',
      placeholder: 'Type your question…', 'aria-label': 'Your question',
      on: { keydown: onKey, input: onInput } });
    send = el('button', { type: 'submit', class: 'cc-send', text: 'Send' });
    tsBox = el('div', { class: 'cc-turnstile' });

    panel = el('div', { class: 'cc-panel', id: 'cc-panel', role: 'dialog', 'aria-modal': 'false',
      'aria-labelledby': 'cc-title', hidden: '' }, [
      el('div', { class: 'cc-head' }, [
        el('h2', { class: 'cc-title', id: 'cc-title', text: 'Caprae Capital Assistant' }),
        el('button', { type: 'button', class: 'cc-close', 'aria-label': 'Close chat', text: '×', on: { click: close } })]),
      log,
      tsBox,
      el('form', { class: 'cc-form', on: { submit: onSubmit } }, [el('label', { class: 'cc-sr', for: 'cc-input', text: 'Your question' }), input, send])
    ]);

    var root = el('div', { class: 'cc-chat' }, [launch, panel]);
    document.body.appendChild(root);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) close(); });

    if (state.transcript.length) state.transcript.forEach(function (m) { render(m, false); });
    else welcome();
  }

  function welcome() {
    var m = el('div', { class: 'cc-msg cc-bot' });
    m.textContent = 'Hi! I can answer questions about Caprae Capital: our services, pricing, process and team.';
    log.appendChild(m);
    var chips = el('div', { class: 'cc-chips', 'data-chips': '' });
    SUGGESTIONS.forEach(function (q) {
      chips.appendChild(el('button', { type: 'button', class: 'cc-chip', text: q, on: { click: function () { ask(q); } } }));
    });
    log.appendChild(chips);
  }

  function render(m, persist) {
    var node = el('div', { class: 'cc-msg ' + (m.role === 'user' ? 'cc-user' : 'cc-bot') });
    if (m.role === 'user') node.textContent = m.text;
    else {
      var body = el('div', { class: 'cc-text' }), short = shortVersion(m.text);
      body.textContent = short || m.text;
      node.appendChild(body);
      var actions = el('div', { class: 'cc-actions' });
      if (short) {
        var more = el('button', { type: 'button', class: 'cc-more', text: 'Know more', 'aria-expanded': 'false',
          on: { click: function () {
            var full = more.getAttribute('aria-expanded') === 'false';
            body.textContent = full ? m.text : short;
            more.textContent = full ? 'Show less' : 'Know more';
            more.setAttribute('aria-expanded', String(full));
          } } });
        actions.appendChild(more);
      }
      var src = (m.sources || [])[0], href = src && allowedHref(src.url || '');
      if (href) actions.appendChild(el('a', { class: 'cc-page', href: href, text: 'Open ' + (src.title || 'this') + ' page →' }));
      if (actions.childNodes.length) node.appendChild(actions);
    }
    log.appendChild(node);
    log.scrollTop = log.scrollHeight;
    if (persist) { state.transcript.push(m); save(); }
  }

  function open() {
    panel.hidden = false; launch.hidden = true; launch.setAttribute('aria-expanded', 'true');
    loadTurnstile();
    setTimeout(function () { input.focus(); log.scrollTop = log.scrollHeight; }, 30);
  }
  function close() {
    panel.hidden = true; launch.hidden = false; launch.setAttribute('aria-expanded', 'false'); launch.focus();
  }

  function onInput() {
    // Grow with the text; only show a scrollbar once the box reaches its maximum height.
    input.style.height = 'auto';
    var full = input.scrollHeight + 2;                     // + top/bottom border
    input.style.height = Math.min(full, 120) + 'px';
    input.style.overflowY = full > 120 ? 'auto' : 'hidden';
  }
  function onKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSubmit(e); } }
  function onSubmit(e) { e.preventDefault(); ask(input.value); }

  function ask(text) {
    text = (text || '').trim();
    if (!text || state.busy) return;
    if (text.length > MAX) text = text.slice(0, MAX);
    var chips = log.querySelector('[data-chips]'); if (chips) chips.remove();
    if (SITEKEY && !state.sessionId && !state.turnstileToken) {
      render({ role: 'bot', text: 'Please complete the quick check below, then send your question again.' }, false);
      return;
    }
    render({ role: 'user', text: text }, true);
    input.value = ''; onInput();
    state.busy = true; send.disabled = true;
    var typing = el('div', { class: 'cc-msg cc-bot', 'aria-label': 'Assistant is typing' },
      [el('span', { class: 'cc-typing' }, [el('span'), el('span'), el('span')])]);
    log.appendChild(typing); log.scrollTop = log.scrollHeight;

    fetch(API, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'omit',
      body: JSON.stringify({ session_id: state.sessionId, message: text, turnstile_token: state.turnstileToken })
    }).then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (data) {
        if (data.session_id) state.sessionId = data.session_id;
        render({ role: 'bot', text: data.reply || 'Sorry, something went wrong. Please try again.', sources: data.sources || [] }, true);
      })
      .catch(function () {
        render({ role: 'bot', text: 'Sorry, I can’t connect right now. Please email partners@capraecapital.com.' }, false);
      })
      .then(function () { typing.remove(); state.busy = false; send.disabled = false; input.focus(); });
  }

  // Optional Cloudflare Turnstile (bot check on the first message).
  var tsLoaded = false;
  function loadTurnstile() {
    if (!SITEKEY || tsLoaded || state.sessionId) return;
    tsLoaded = true;
    window.ccTurnstileReady = function () {
      window.turnstile.render(tsBox, { sitekey: SITEKEY, theme: 'dark', size: 'flexible',
        callback: function (t) { state.turnstileToken = t; } });
    };
    var s = document.createElement('script');
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=ccTurnstileReady';
    s.async = true; document.head.appendChild(s);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build); else build();
})();
