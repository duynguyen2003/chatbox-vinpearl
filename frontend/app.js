'use strict';

const $ = (selector) => document.querySelector(selector);

const els = {
  messages: $('#messages'),
  form: $('#chatForm'),
  input: $('#messageInput'),
  send: $('#sendBtn'),
  newChat: $('#newChatBtn'),
  settings: $('#settingsBtn'),
  dialog: $('#settingsDialog'),
  apiUrl: $('#apiUrl'),
  userId: $('#userId'),
  save: $('#saveSettings'),
  error: $('#errorBanner'),
  errorText: $('#errorText'),
  closeError: $('#closeError'),
};

const SESSION_STORAGE_KEY = 'vp_session_id';

const state = {
  apiUrl:
    localStorage.getItem('vp_api_url') ||
    'http://127.0.0.1:8000/api/v1/chat',
  userId: localStorage.getItem('vp_user_id') || 'web-demo-user',

  // Reuse the backend session after page refresh.
  // null means the backend will create the session on the first request.
  sessionId: localStorage.getItem(SESSION_STORAGE_KEY) || null,
  sending: false,
};

els.apiUrl.value = state.apiUrl;
els.userId.value = state.userId;

function saveSession(sessionId) {
  if (!sessionId) return;

  state.sessionId = sessionId;
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  console.debug('[Vinpearl chat] active session_id:', sessionId);
}

function resetLocalSession() {
  state.sessionId = null;
  localStorage.removeItem(SESSION_STORAGE_KEY);
}

function esc(value) {
  const div = document.createElement('div');
  div.textContent = String(value ?? '');
  return div.innerHTML;
}

function fmt(value) {
  return esc(value)
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

function time() {
  return new Intl.DateTimeFormat('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date());
}

function scroll() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function showError(message) {
  els.errorText.textContent = message;
  els.error.hidden = false;
}

function hideError() {
  els.error.hidden = true;
  els.errorText.textContent = '';
}

function addUser(text) {
  const node = document.createElement('div');
  node.className = 'message user';
  node.innerHTML = `
    <div class="bubble-wrap">
      <div class="bubble">${fmt(text)}</div>
      <small>${time()}</small>
    </div>`;
  els.messages.appendChild(node);
  scroll();
}

function typing() {
  const node = document.createElement('div');
  node.className = 'message assistant';
  node.innerHTML = `
    <div class="avatar small">V</div>
    <div class="bubble-wrap">
      <div class="bubble typing"><i></i><i></i><i></i></div>
    </div>`;
  els.messages.appendChild(node);
  scroll();
  return node;
}

function sourcesHtml(sources) {
  if (!Array.isArray(sources) || !sources.length) return '';

  return `
    <details class="sources">
      <summary>Xem ${sources.length} nguồn dữ liệu</summary>
      ${sources
        .slice(0, 6)
        .map(
          (source) => `
            <div class="source">
              <strong>${esc(source.source_file || 'Unknown')}</strong>
              ${esc(source.category || 'unknown')}
              ${source.path ? ` · ${esc(source.path)}` : ''}
              ${
                typeof source.score === 'number'
                  ? ` · ${Math.round(source.score * 100)}%`
                  : ''
              }
            </div>`,
        )
        .join('')}
    </details>`;
}

function addAssistant(payload) {
  const node = document.createElement('div');
  node.className = 'message assistant';
  node.innerHTML = `
    <div class="avatar small">V</div>
    <div class="bubble-wrap">
      <div class="bubble">
        <p>${fmt(payload.answer || 'Không có nội dung phản hồi.')}</p>
        ${
          payload.ticket_id
            ? `<div class="ticket"><strong>Ticket:</strong> ${esc(payload.ticket_id)}</div>`
            : ''
        }
        ${sourcesHtml(payload.sources)}
        <div class="meta">
          <span>${esc(payload.route || 'unknown')}</span>
          <span>${esc(payload.language || 'unknown')}</span>
        </div>
      </div>
      <small>${time()}</small>
    </div>`;
  els.messages.appendChild(node);
  scroll();
}

function setSending(value) {
  state.sending = value;
  els.send.disabled = value;
  els.input.disabled = value;
}

async function parseResponse(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function callApi(message) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);

  const requestBody = {
    message,
    user_id: state.userId,
  };

  // Do not invent a session on the browser. Let the backend create the first
  // session, then persist and reuse the returned session_id.
  if (state.sessionId) {
    requestBody.session_id = state.sessionId;
  }

  try {
    const response = await fetch(state.apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    const payload = await parseResponse(response);

    if (!response.ok) {
      throw new Error(
        payload?.detail || `FastAPI trả về HTTP ${response.status}`,
      );
    }

    if (!payload?.session_id) {
      throw new Error(
        'Backend không trả về session_id nên không thể duy trì ngữ cảnh.',
      );
    }

    // This is the important memory step.
    saveSession(payload.session_id);
    return payload;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(
        'Yêu cầu quá thời gian chờ. Gemini hoặc FastAPI có thể đang bận.',
      );
    }

    if (error instanceof TypeError) {
      throw new Error(
        'Không thể kết nối FastAPI. Hãy kiểm tra server, API URL và CORS.',
      );
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function clearServerHistory(sessionId) {
  if (!sessionId) return;

  const historyUrl = `${state.apiUrl.replace(/\/+$/, '')}/${encodeURIComponent(
    sessionId,
  )}/history`;

  try {
    await fetch(historyUrl, { method: 'DELETE' });
  } catch (error) {
    // Starting a new session must still work even when history cleanup fails.
    console.warn('[Vinpearl chat] unable to clear old history:', error);
  }
}

async function send(raw) {
  const message = raw.trim();
  if (!message || state.sending) return;

  hideError();
  setSending(true);
  addUser(message);
  $('#suggestions')?.remove();
  els.input.value = '';
  els.input.style.height = 'auto';

  const wait = typing();

  try {
    const payload = await callApi(message);
    wait.remove();
    addAssistant(payload);
  } catch (error) {
    wait.remove();
    showError(error.message || 'Đã xảy ra lỗi.');
    addAssistant({
      answer:
        'Xin lỗi, hệ thống đang tạm thời không thể xử lý yêu cầu. Vui lòng thử lại sau.',
      language: 'vi',
      route: 'system_error',
      sources: [],
    });
  } finally {
    setSending(false);
    els.input.focus();
  }
}

els.form.addEventListener('submit', (event) => {
  event.preventDefault();
  send(els.input.value);
});

els.input.addEventListener('input', () => {
  els.input.style.height = 'auto';
  els.input.style.height = `${Math.min(els.input.scrollHeight, 140)}px`;
});

els.input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    els.form.requestSubmit();
  }
});

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-question]');
  if (button) send(button.dataset.question || '');
});

els.newChat.addEventListener('click', async () => {
  const previousSessionId = state.sessionId;

  // Remove it immediately so the next message cannot accidentally reuse it.
  resetLocalSession();
  await clearServerHistory(previousSessionId);

  hideError();
  els.messages.innerHTML = `
    <div class="message assistant">
      <div class="avatar small">V</div>
      <div class="bubble-wrap">
        <div class="bubble">
          Cuộc trò chuyện mới đã bắt đầu. Bạn muốn khám phá điểm đến
          hoặc trải nghiệm nào của Vinpearl?
        </div>
        <small>Vừa xong</small>
      </div>
    </div>`;
  els.input.focus();
});

els.settings.addEventListener('click', () => els.dialog.showModal());

els.save.addEventListener('click', (event) => {
  event.preventDefault();

  const url = els.apiUrl.value.trim();
  if (!url) {
    showError('API URL không được để trống.');
    return;
  }

  state.apiUrl = url;
  state.userId = els.userId.value.trim() || 'web-demo-user';
  localStorage.setItem('vp_api_url', state.apiUrl);
  localStorage.setItem('vp_user_id', state.userId);
  els.dialog.close();
  hideError();
});

els.closeError.addEventListener('click', hideError);
els.dialog.addEventListener('click', (event) => {
  if (event.target === els.dialog) els.dialog.close();
});
