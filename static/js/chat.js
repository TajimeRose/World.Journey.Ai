(() => {
  // Mobile menu functionality
  function initMobileMenu() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileMenuBtn && navMenu) {
      mobileMenuBtn.addEventListener('click', () => {
        const isActive = navMenu.classList.contains('active');

        if (isActive) {
          navMenu.classList.remove('active');
          mobileMenuBtn.classList.remove('active');
          mobileMenuBtn.setAttribute('aria-expanded', 'false');
        } else {
          navMenu.classList.add('active');
          mobileMenuBtn.classList.add('active');
          mobileMenuBtn.setAttribute('aria-expanded', 'true');
        }
      });

      // Close menu when clicking outside
      document.addEventListener('click', (e) => {
        if (!mobileMenuBtn.contains(e.target) && !navMenu.contains(e.target)) {
          navMenu.classList.remove('active');
          mobileMenuBtn.classList.remove('active');
          mobileMenuBtn.setAttribute('aria-expanded', 'false');
        }
      });

      // Close menu when clicking on nav links
      const navLinks = navMenu.querySelectorAll('.nav-link');
      navLinks.forEach(link => {
        link.addEventListener('click', () => {
          navMenu.classList.remove('active');
          mobileMenuBtn.classList.remove('active');
          mobileMenuBtn.setAttribute('aria-expanded', 'false');
        });
      });
    }
  }

  const elements = {
    messages: document.getElementById('messages'),
    chatLog: document.getElementById('chat-log'),
    emptyState: document.getElementById('empty-state'),
    composer: document.getElementById('composer'),
    chatInput: document.getElementById('chat-input'),
    sendButton: document.getElementById('send-button'),
    micButton: document.getElementById('mic-button'),
    fileInput: document.getElementById('chatImageInput'),
    fileName: document.getElementById('chatImagePreview'),
    toastRegion: document.getElementById('toast-region'),
    chatUserName: document.getElementById('chatUserName'),
    scrollToBottomBtn: document.getElementById('scroll-to-bottom'),
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
    abortController: null,
    isAIThinking: false,
    shouldAutoScroll: true, // Track if we should auto-scroll
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

  function sanitizeAssistantText(message) {
    if (
      message.role !== 'assistant' ||
      !message.structured_data ||
      !Array.isArray(message.structured_data) ||
      message.structured_data.length === 0 ||
      !message.text
    ) {
      return message.text || '';
    }

    const paragraphs = message.text.split('\n').filter(Boolean);
    if (paragraphs.length === 0) return message.text;

    const overviewLines = [];
    for (const line of paragraphs) {
      if (line.includes('**') || line.trim().startsWith('- ')) break;
      overviewLines.push(line);
    }

    const baseText =
      overviewLines.length > 0 ? overviewLines.join(' ') : paragraphs[0];

    const lowerPlaceNames = message.structured_data
      .map((place) => (place.place_name || place.name || '').toLowerCase())
      .filter(Boolean);

    const sentences = baseText
      .split(/(?<=[.!?])\s+|(?<=[。！？])/)
      .map((sentence) => sentence.trim())
      .filter(Boolean);

    const filteredSentences = [];
    for (const sentence of sentences) {
      const lowerSentence = sentence.toLowerCase();
      const mentionsPlace = lowerPlaceNames.some((name) =>
        name ? lowerSentence.includes(name) : false
      );
      if (mentionsPlace) continue;
      filteredSentences.push(sentence);
      if (filteredSentences.length >= 3) break;
    }

    if (filteredSentences.length > 0) {
      return filteredSentences.join(' ');
    }
    return sentences.length > 0 ? sentences[0] : baseText;
  }

  function createPlaceCard(place) {
    const card = document.createElement('div');
    card.className = 'place-card';

    const title = document.createElement('h4');
    title.className = 'place-card-title';
    title.textContent = place.place_name || place.name || 'ไม่ระบุชื่อ';
    card.appendChild(title);

    const typeText = place.type
      || place.category
      || (place.place_information && place.place_information.category_description)
      || '';
    if (typeText) {
      const typeLabel = document.createElement('div');
      typeLabel.className = 'place-card-type';
      typeLabel.innerHTML = `<strong>ประเภทสถานที่:</strong> ${typeText}`;
      card.appendChild(typeLabel);
    }

    const locationText = (() => {
      if (typeof place.location === 'string') {
        return place.location;
      } else if (typeof place.location === 'object' && place.location !== null) {
        const district = place.location.district || '';
        const province = place.location.province || '';
        return [district, province].filter(Boolean).join(', ');
      } else if (place.address) {
        return typeof place.address === 'string' ? place.address : '';
      }
      return '';
    })();

    if (locationText) {
      const location = document.createElement('div');
      location.className = 'place-card-location';
      location.innerHTML = `<strong>ที่ตั้ง:</strong> ${locationText}`;
      card.appendChild(location);
    }

    const descriptionText = (() => {
      if (typeof place.description === 'string') {
        return place.description;
      } else if (typeof place.place_information === 'object' && place.place_information !== null) {
        return place.place_information.detail || '';
      } else if (typeof place.place_information === 'string') {
        return place.place_information;
      }
      return '';
    })();

    const shortDescription = (() => {
      const candidate =
        place.short_description ||
        place.summary ||
        (Array.isArray(place.highlights) ? place.highlights.join(', ') : '') ||
        descriptionText;
      if (!candidate) return '';
      if (candidate.length > 320) {
        return `${candidate.slice(0, 317)}...`;
      }
      return candidate;
    })();

    if (shortDescription) {
      const summary = document.createElement('p');
      summary.className = 'place-card-summary';
      summary.innerHTML = `<strong>คำอธิบายย่อ:</strong> ${shortDescription}`;
      card.appendChild(summary);
    }

    const fullDescription =
      place.full_description ||
      (place.place_information && place.place_information.full_detail) ||
      place.long_description ||
      descriptionText;

    if (fullDescription) {
      const detailsWrapper = document.createElement('div');
      detailsWrapper.className = 'place-card-details-wrapper';

      const detailsToggle = document.createElement('button');
      detailsToggle.className = 'place-card-details-btn';
      detailsToggle.type = 'button';
      detailsToggle.setAttribute('aria-expanded', 'false');
      detailsToggle.textContent = 'กดเพื่อดูรายละเอียดเพิ่มเติม';

      const detailsContent = document.createElement('div');
      detailsContent.className = 'place-card-details hidden';
      detailsContent.textContent = fullDescription;

      detailsToggle.addEventListener('click', () => {
        const isHidden = detailsContent.classList.contains('hidden');
        detailsContent.classList.toggle('hidden');
        detailsToggle.setAttribute('aria-expanded', String(isHidden));
        detailsToggle.textContent = isHidden
          ? 'ย่อรายละเอียด'
          : 'กดเพื่อดูรายละเอียดเพิ่มเติม';
      });

      detailsWrapper.appendChild(detailsToggle);
      detailsWrapper.appendChild(detailsContent);
      card.appendChild(detailsWrapper);
    }

    if (place.opening_hours) {
      const hours = document.createElement('div');
      hours.className = 'place-card-hours';
      hours.innerHTML = `🕐 ${place.opening_hours}`;
      card.appendChild(hours);
    }

    if (place.contact || place.mobile_phone) {
      const contact = document.createElement('div');
      contact.className = 'place-card-contact';
      contact.innerHTML = `📞 ${place.contact || place.mobile_phone}`;
      card.appendChild(contact);
    }

    return card;
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
    bubble.dataset.messageId = message.id || message.createdAt; // Use ID or fallback to timestamp
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
    let displayText = message.text;
    if (message.role === 'assistant') {
      displayText = sanitizeAssistantText(message);
    }

    if (message.html) {
      body.innerHTML = message.html;
    } else if (displayText) {
      const p = document.createElement('p');
      p.textContent = displayText;
      body.appendChild(p);
    }
    bubble.appendChild(body);

    // Add structured data (place cards) if available
    if (message.structured_data && Array.isArray(message.structured_data) && message.structured_data.length > 0) {
      const placesContainer = document.createElement('div');
      placesContainer.className = 'places-container';

      message.structured_data.forEach(place => {
        const placeCard = createPlaceCard(place);
        placesContainer.appendChild(placeCard);
      });

      bubble.appendChild(placesContainer);
    }

    wrapper.appendChild(bubble);
    return wrapper;
  }

  function smoothScrollToBottom() {
    if (!elements.chatLog) return;

    // Only auto-scroll if the user hasn't manually scrolled up
    if (!state.shouldAutoScroll) return;

    // Use smooth scrolling for better UX
    elements.chatLog.scrollTo({
      top: elements.chatLog.scrollHeight,
      behavior: 'smooth'
    });
  }

  function isScrolledToBottom() {
    if (!elements.chatLog) return true;
    const threshold = 150; // pixels from bottom
    const position = elements.chatLog.scrollTop + elements.chatLog.clientHeight;
    const height = elements.chatLog.scrollHeight;
    return height - position < threshold;
  } function handleScroll() {
    // Check if user has scrolled away from bottom
    state.shouldAutoScroll = isScrolledToBottom();

    // Show/hide scroll-to-bottom button
    if (elements.scrollToBottomBtn) {
      if (state.shouldAutoScroll) {
        elements.scrollToBottomBtn.classList.add('hidden');
      } else {
        elements.scrollToBottomBtn.classList.remove('hidden');
      }
    }
  }

  function scrollToBottomClick() {
    // Force scroll to bottom and re-enable auto-scroll
    state.shouldAutoScroll = true;
    if (elements.chatLog) {
      elements.chatLog.scrollTo({
        top: elements.chatLog.scrollHeight,
        behavior: 'smooth'
      });
    }
    if (elements.scrollToBottomBtn) {
      elements.scrollToBottomBtn.classList.add('hidden');
    }
  }

  function appendMessage(message) {
    if (!elements.messages) return;
    const node = createMessageNode(message);
    elements.messages.appendChild(node);

    // Smooth scroll to bottom after message is appended
    requestAnimationFrame(() => {
      smoothScrollToBottom();
    });

    if (elements.emptyState) {
      elements.emptyState.classList.add('hidden');
    }
  }

  function showTypingIndicator() {
    if (state.typingNode || !elements.messages) return;
    const indicator = document.createElement('div');
    indicator.className = 'message-row message-row--assistant typing-wrapper';
    indicator.innerHTML = '<div class="message-bubble message-bubble--assistant"><div class="message-meta"><span class="message-author message-author--assistant">AI น้องปลาทู</span></div><div class="message-body"><div class="typing-indicator"><span></span><span></span><span></span></div><div class="ai-thinking-text">กำลังคิด...</div></div></div>';
    elements.messages.appendChild(indicator);

    // Smooth scroll when typing indicator appears
    requestAnimationFrame(() => {
      smoothScrollToBottom();
    });

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

  function setInputsDisabled(disabled) {
    if (elements.chatInput) {
      elements.chatInput.disabled = disabled;
      if (disabled) {
        elements.chatInput.placeholder = 'กรุณารอสักครู่...';
      } else {
        elements.chatInput.placeholder = 'พิมพ์ข้อความของคุณ...';
      }
    }
    if (elements.sendButton) {
      elements.sendButton.disabled = disabled;
    }
    if (elements.micButton) {
      elements.micButton.disabled = disabled;
    }
  }

  function showCancelButton() {
    if (!elements.composer || !elements.sendButton) return;

    let cancelBtn = document.getElementById('cancel-ai-button');
    if (!cancelBtn) {
      cancelBtn = document.createElement('button');
      cancelBtn.id = 'cancel-ai-button';
      cancelBtn.type = 'button';
      cancelBtn.className = 'cancel-ai-btn';
      cancelBtn.innerHTML = '✕ ยกเลิก';
      cancelBtn.addEventListener('click', cancelAIRequest);
      // Insert cancel button right after send button
      elements.sendButton.parentNode.insertBefore(cancelBtn, elements.sendButton.nextSibling);
    }

    // Hide send button and show cancel button
    elements.sendButton.style.display = 'none';
    cancelBtn.classList.add('show');
  }

  function hideCancelButton() {
    const cancelBtn = document.getElementById('cancel-ai-button');
    if (cancelBtn) {
      cancelBtn.classList.remove('show');
    }
    // Show send button again
    if (elements.sendButton) {
      elements.sendButton.style.display = 'inline-flex';
    }
  }

  function cancelAIRequest() {
    if (state.abortController) {
      state.abortController.abort();
      state.abortController = null;
    }
    state.isAIThinking = false;
    removeTypingIndicator();
    setInputsDisabled(false);
    hideCancelButton();
    showToast('ยกเลิกคำขอแล้ว', 'info');
  }

  async function sendUserMessage() {
    if (!elements.chatInput || !elements.sendButton) return;

    const text = elements.chatInput.value.trim();
    if (!text || state.isAIThinking) return;

    // Re-enable auto-scroll when user sends a message
    state.shouldAutoScroll = true;

    elements.chatInput.value = '';
    setInputsDisabled(true);
    resetFilePreview();

    const userEntry = { role: 'user', text, createdAt: new Date().toISOString() };
    appendMessage(userEntry);
    showTypingIndicator();
    showCancelButton();

    state.isAIThinking = true;
    state.abortController = new AbortController();

    try {
      const response = await fetch('/api/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', text, mode: 'chat' }),
        signal: state.abortController.signal,
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
      if (error.name === 'AbortError') {
        // Request was cancelled by user
        elements.chatInput.value = text;
      } else {
        showToast('ไม่สามารถส่งข้อความได้ กรุณาลองใหม่', 'error');
        elements.chatInput.value = text;
      }
    } finally {
      state.isAIThinking = false;
      state.abortController = null;
      setInputsDisabled(false);
      hideCancelButton();
      elements.chatInput.focus();
    }
  }

  // polling removed — realtime listener is used instead

  function updateMicRecordingState(recording) {
    state.speech.recording = recording;
    if (!elements.micButton) return;
    elements.micButton.classList.toggle('is-recording', recording);
    elements.micButton.setAttribute('aria-label', recording ? 'หยุดฟังเสียง' : 'เริ่มฟังเสียง');
    elements.micButton.setAttribute('aria-pressed', recording ? 'true' : 'false');
  }

  function ensureSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (elements.micButton) {
        elements.micButton.disabled = true;
        elements.micButton.setAttribute('aria-disabled', 'true');
        elements.micButton.setAttribute('aria-pressed', 'false');
      }
      return null;
    }
    try {
      const instance = new SpeechRecognition();
      if (elements.micButton) {
        elements.micButton.disabled = false;
        elements.micButton.removeAttribute('aria-disabled');
        elements.micButton.setAttribute('aria-pressed', 'false');
      }
      return instance;
    } catch (error) {
      console.warn('SpeechRecognition initialisation failed', error);
      if (elements.micButton) {
        elements.micButton.disabled = true;
        elements.micButton.setAttribute('aria-disabled', 'true');
      }
      return null;
    }
  }

  function initialiseSpeechRecognition() {
    const recognition = ensureSpeechRecognition();
    if (!recognition) return;

    recognition.lang = 'th-TH';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.addEventListener('start', () => updateMicRecordingState(true));

    recognition.addEventListener('end', () => updateMicRecordingState(false));

    recognition.addEventListener('speechend', () => recognition.stop());
    recognition.addEventListener('result', (event) => {
      const transcript = event?.results?.[0]?.[0]?.transcript || '';
      if (elements.chatInput) {
        elements.chatInput.value = transcript;
        elements.chatInput.focus();
      }
    });
    recognition.addEventListener('error', (event) => {
      const errorType = event?.error || '';
      updateMicRecordingState(false);
      if (errorType === 'not-allowed' || errorType === 'service-not-allowed') {
        state.speech.recognition = null;
      }
      const message = errorType === 'not-allowed'
        ? 'กรุณาอนุญาตให้เบราว์เซอร์เข้าถึงไมโครโฟน'
        : 'ไม่สามารถใช้งานไมโครโฟนได้';
      showToast(message, 'error');
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
    let recognition = state.speech.recognition;
    if (!recognition) {
      recognition = ensureSpeechRecognition();
      state.speech.recognition = recognition;
    }
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

    // Add scroll event listener to detect when user manually scrolls
    elements.chatLog?.addEventListener('scroll', handleScroll);

    // Add click handler for scroll-to-bottom button
    elements.scrollToBottomBtn?.addEventListener('click', scrollToBottomClick);
  }  // Check authentication status and clear chat data if user is not logged in
  function checkAuthAndInitialize() {
    const isAuthenticated = window.__FIREBASE__ && window.__FIREBASE__.auth && window.__FIREBASE__.auth.currentUser;

    if (!isAuthenticated) {
      // Clear all messages from display for unauthenticated users
      if (elements.messages) {
        elements.messages.innerHTML = '';
      }
      // Show a small notice about logging in to save history
      if (elements.emptyState) {
        elements.emptyState.classList.remove('hidden');
        const loginPrompt = elements.emptyState.querySelector('p') || elements.emptyState;
        if (loginPrompt) {
          loginPrompt.textContent = 'กรุณาเข้าสู่ระบบเพื่อเก็บประวัติการสนทนา';
          loginPrompt.style.fontSize = '0.9rem';
          loginPrompt.style.color = '#666';
        }
      }
      // Allow sending messages (don't disable)
      if (elements.sendButton) {
        elements.sendButton.disabled = false;
      }
      if (elements.chatInput) {
        elements.chatInput.placeholder = 'พิมพ์ข้อความของคุณ...';
      }
      // Don't load saved messages for unauthenticated users
      return false;
    }
    return true;
  }

  window.addEventListener('wj-auth-changed', (event) => {
    updateUserIdentity(event?.detail?.displayName);
    // Re-check auth status when auth state changes
    const isAuth = checkAuthAndInitialize();
    if (isAuth) {
      // Load saved messages when user logs in
      fetchMessages().then(() => {
        listenForRealtimeMessages();
      });
    }
  });

  updateUserIdentity(state.userDisplayName);
  bindEvents();
  initialiseSpeechRecognition();
  resetFilePreview();
  initMobileMenu(); // Initialize mobile menu

  // Check auth before loading messages
  const canProceed = checkAuthAndInitialize();
  if (canProceed) {
    fetchMessages().then(() => {
      // start realtime listener (non-blocking)
      listenForRealtimeMessages();
      handleQueryParameter();
    });
  } else {
    // For unauthenticated users, just handle query param (allow chatting)
    handleQueryParameter();
  }
})();
