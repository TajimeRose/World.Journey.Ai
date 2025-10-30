(() => {
  const elements = {
    messages: document.getElementById('messages'),
    emptyState: document.getElementById('empty-state'),
    composer: document.getElementById('composer'),
    chatInput: document.getElementById('chat-input'),
    sendButton: document.getElementById('send-button'),
    micButton: document.getElementById('mic-button'),
    fileInput: document.getElementById('chatImageInput'),
    fileName: document.getElementById('chatImagePreview'),
    toastRegion: document.getElementById('toast-region'),
    chatUserName: document.getElementById('chatUserName'),
  };

  const FILE_ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
  const MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024;

  const state = {
    userDisplayName: window.__USER_DISPLAY_NAME__ || 'ผู้ใช้งาน',
    typingNode: null,
    lastTimestamp: null,
    speech: {
      recognition: null,
      recording: false,
    },
    realtimeSeen: new Set(),
  };

  function showToast(message, variant = 'info') {
    if (!elements.toastRegion || !message) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${variant}`;
    toast.textContent = message;
    toast.classList.add('toast-hide');
    elements.toastRegion.appendChild(toast);
    requestAnimationFrame(() => {
      toast.classList.remove('toast-hide');
    });
    window.setTimeout(() => {
      toast.classList.add('toast-hide');
      window.setTimeout(() => toast.remove(), 260);
    }, 3200);
  }

  function updateUserIdentity(name) {
    const displayName = name && name.trim() ? name.trim() : 'ผู้ใช้งาน';
    state.userDisplayName = displayName;
    if (elements.chatUserName) {
      elements.chatUserName.textContent = displayName;
    }
    document.querySelectorAll('.message-author--user').forEach((node) => {
      node.textContent = displayName;
    });
  }

  function analyseMessageRole(role) {
    if (role === 'assistant') return 'AI น้องปลาทู';
    if (role === 'user') return state.userDisplayName;
    return 'ระบบ';
  }

  function createMessageNode(message) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-row';
    wrapper.classList.add(
      message.role === 'assistant'
        ? 'message-row--assistant'
        : message.role === 'user'
          ? 'message-row--user'
          : 'message-row--system'
    );

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.dataset.role = message.role;
    bubble.classList.add(
      message.role === 'assistant'
        ? 'message-bubble--assistant'
        : message.role === 'user'
          ? 'message-bubble--user'
          : 'message-bubble--system'
    );

    const meta = document.createElement('div');
    meta.className = 'message-meta';
    const author = document.createElement('span');
    author.className = 'message-author';
    if (message.role === 'assistant') {
      author.classList.add('message-author--assistant');
    } else if (message.role === 'user') {
      author.classList.add('message-author--user');
    }
    // Prefer an explicit author provided on the message; fall back to role-based label
    if (message.author && message.role === 'user') {
      author.textContent = message.author;
    } else {
      author.textContent = analyseMessageRole(message.role);
    }
    meta.appendChild(author);
    bubble.appendChild(meta);

    const body = document.createElement('div');
    body.className = 'message-body';
    if (message.html) {
      body.innerHTML = message.html;
    } else if (message.text) {
      const p = document.createElement('p');
      p.textContent = message.text;
      body.appendChild(p);
    }
    bubble.appendChild(body);

    wrapper.appendChild(bubble);
    return wrapper;
  }

  function appendMessage(message) {
    if (!elements.messages) return;
    const node = createMessageNode(message);
    elements.messages.appendChild(node);
    elements.messages.scrollTop = elements.messages.scrollHeight;
    if (elements.emptyState) {
      elements.emptyState.classList.add('hidden');
    }
  }

  function showTypingIndicator() {
    if (state.typingNode || !elements.messages) return;
    const indicator = document.createElement('div');
    indicator.className = 'message-row message-row--assistant typing-wrapper';
    indicator.innerHTML = '<div class="message-bubble message-bubble--assistant"><div class="message-meta"><span class="message-author message-author--assistant">AI น้องปลาทู</span></div><div class="message-body"><div class="typing-indicator"><span></span><span></span><span></span></div></div></div>';
    elements.messages.appendChild(indicator);
    elements.messages.scrollTop = elements.messages.scrollHeight;
    state.typingNode = indicator;
  }

  function removeTypingIndicator() {
    if (state.typingNode) {
      state.typingNode.remove();
      state.typingNode = null;
    }
  }

  function resetFilePreview(message = 'ยังไม่ได้เลือกไฟล์') {
    if (!elements.fileInput || !elements.fileName) return;
    elements.fileInput.value = '';
    elements.fileName.textContent = message;
  }

  function validateFile(file) {
    if (!file) {
      resetFilePreview();
      return;
    }
    if (!FILE_ACCEPTED_TYPES.includes(file.type)) {
      showToast('รองรับเฉพาะไฟล์ภาพ JPG, PNG หรือ WebP เท่านั้น', 'warning');
      resetFilePreview();
      return;
    }
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      showToast('ไฟล์มีขนาดใหญ่เกิน 4MB', 'warning');
      resetFilePreview();
      return;
    }
    if (elements.fileName) {
      elements.fileName.textContent = file.name;
    }
  }

  async function fetchMessages() {
    try {
      const params = state.lastTimestamp ? `?since=${encodeURIComponent(state.lastTimestamp)}` : '';
      const response = await fetch(`/api/messages${params}`);
      if (!response.ok) return;
      const data = await response.json();
      const messages = Array.isArray(data.messages) ? data.messages : [];
      messages.forEach((message) => {
        appendMessage(message);
        state.lastTimestamp = message.createdAt;
      });
    } catch (error) {
      console.warn('Unable to load messages', error);
    }
  }

  async function sendUserMessage() {
    if (!elements.chatInput || !elements.sendButton) return;
    const text = elements.chatInput.value.trim();
    if (!text) return;

    elements.chatInput.value = '';
    elements.sendButton.disabled = true;
    resetFilePreview();

    const userEntry = { role: 'user', text, createdAt: new Date().toISOString() };
    appendMessage(userEntry);
    showTypingIndicator();

    try {
      const response = await fetch('/api/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', text }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = await response.json();
      removeTypingIndicator();
      if (data.assistant) {
        appendMessage(data.assistant);
        state.lastTimestamp = data.assistant.createdAt;
      }
    } catch (error) {
      removeTypingIndicator();
      showToast('ไม่สามารถส่งข้อความได้ กรุณาลองใหม่', 'error');
      elements.chatInput.value = text;
    } finally {
      elements.sendButton.disabled = false;
      elements.chatInput.focus();
    }
  }

  // polling removed — realtime listener is used instead

  function ensureSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (elements.micButton) {
        elements.micButton.disabled = true;
        elements.micButton.setAttribute('aria-disabled', 'true');
      }
      return null;
    }
    return new SpeechRecognition();
  }

  function initialiseSpeechRecognition() {
    const recognition = ensureSpeechRecognition();
    if (!recognition) return;

    recognition.lang = 'th-TH';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.addEventListener('start', () => {
      state.speech.recording = true;
      elements.micButton?.classList.add('is-recording');
      elements.micButton?.setAttribute('aria-label', 'หยุดฟังเสียง');
    });

    recognition.addEventListener('end', () => {
      state.speech.recording = false;
      elements.micButton?.classList.remove('is-recording');
      elements.micButton?.setAttribute('aria-label', 'เริ่มฟังเสียง');
    });

    recognition.addEventListener('speechend', () => recognition.stop());
    recognition.addEventListener('result', (event) => {
      const transcript = event?.results?.[0]?.[0]?.transcript || '';
      if (elements.chatInput) {
        elements.chatInput.value = transcript;
        elements.chatInput.focus();
      }
    });
    recognition.addEventListener('error', () => {
      state.speech.recording = false;
      showToast('ไม่สามารถใช้งานไมโครโฟนได้', 'error');
    });

    state.speech.recognition = recognition;
  }

  // Realtime database listener for new messages (client-side writes)
  function listenForRealtimeMessages() {
    try {
      if (window.__FIREBASE__ && window.__FIREBASE__.dbApi && window.__FIREBASE__.dbApi.onValue) {
        window.__FIREBASE__.dbApi.onValue('messages', (snapshot) => {
          const data = snapshot.val();
          if (!data) return;
          Object.entries(data).forEach(([key, val]) => {
            if (state.realtimeSeen.has(key)) return;
            state.realtimeSeen.add(key);
            const text = val.text || val.message || '';
            const time = val.time || val.createdAt || new Date().toISOString();
            const author = val.user || val.author || null;
            // normalize to server message shape if possible
            appendMessage({ role: 'user', text, createdAt: time, author });
          });
        });
      }
    } catch (err) {
      console.warn('Realtime listener failed', err);
    }
  }

  function handleMicClick() {
    const recognition = state.speech.recognition;
    if (!recognition) {
      showToast('ไม่สามารถเริ่มต้นไมโครโฟนได้', 'warning');
      return;
    }
    if (state.speech.recording) {
      recognition.stop();
      return;
    }
    try {
      recognition.start();
    } catch (error) {
      recognition.stop();
      recognition.start();
    }
  }

  function handleQueryParameter() {
    const params = new URLSearchParams(window.location.search);
    const keyword = (params.get('q') || '').trim();
    if (!keyword) return;
    if (elements.chatInput) {
      elements.chatInput.value = keyword;
    }
    // store the redirected search query to Firebase
    try {
      if (window.__FIREBASE__ && window.__FIREBASE__.dbApi) {
        const dbApi = window.__FIREBASE__.dbApi;
        const key = `searches/${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        dbApi.set(dbApi.ref(key), {
          query: keyword,
          createdAt: new Date().toISOString(),
          source: 'index-redirect',
        });
      }
    } catch (err) {
      console.warn('Failed to write search to Firebase', err);
    }
    sendUserMessage();
    params.delete('q');
    const newQuery = params.toString();
    const newUrl = `${window.location.pathname}${newQuery ? `?${newQuery}` : ''}${window.location.hash}`;
    window.history.replaceState({}, '', newUrl);
  }

  function bindEvents() {
    elements.composer?.addEventListener('submit', (event) => {
      event.preventDefault();
      sendUserMessage();
    });

    elements.chatInput?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        sendUserMessage();
      }
    });

    elements.micButton?.addEventListener('click', handleMicClick);
    elements.fileInput?.addEventListener('change', (event) => {
      const file = event.target?.files?.[0];
      validateFile(file || null);
    });
  }

  window.addEventListener('wj-auth-changed', (event) => {
    updateUserIdentity(event?.detail?.displayName);
  });

  updateUserIdentity(state.userDisplayName);
  bindEvents();
  initialiseSpeechRecognition();
  resetFilePreview();
  fetchMessages().then(() => {
    // start realtime listener (non-blocking)
    listenForRealtimeMessages();
    handleQueryParameter();
  });
})();
