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

  const form = document.getElementById('journey-form');
  const input = document.getElementById('destination-input');
  const micButton = document.getElementById('mic-button');
  const toast = document.getElementById('toast');
  const fileInput = document.getElementById('imageInput');
  const fileName = document.getElementById('imagePreview');
  const faceContainer = document.getElementById('face-detector');
  const faceVideo = document.getElementById('fd-video');
  const faceCanvas = document.getElementById('fd-canvas');
  const faceStatus = document.getElementById('faceStatus');
  const faceStatusLabel = document.getElementById('faceStatusLabel');
  const mascotRoot = document.getElementById('mascot');
  const mascotSpeech = document.getElementById('speech');

  const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
  const MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = SpeechRecognition ? new SpeechRecognition() : null;
  let isRecording = false;
  let toastTimer = null;
  const FACE_CAPTURE_INTERVAL = 2000;
  let faceStream = null;
  let faceTimer = null;
  let faceInFlight = false;
  let faceActivated = false;
  let lastFaceStatus = null;
  const MASCOT_MESSAGES = [
    'สวัสดีค่ะ มีอะไรให้น้องปลาทูช่วยไหมคะ?',
    'วันนี้อยากเที่ยวที่ไหนบ้างน่ะ?',
    'มีอะไรให้น้องปลาทูช่วยค้นหาหรือเปล่าคะ?',
  ];
  const MASCOT_HIDE_DELAY = 10000;
  let mascotTimer = null;

  function setMascotGreeting(force = false) {
    if (!mascotSpeech || !MASCOT_MESSAGES.length) {
      return;
    }
    mascotSpeech.classList.remove('is-hidden');
    const current = mascotSpeech.textContent?.trim() || '';
    let nextMessage = current;
    if (MASCOT_MESSAGES.length === 1) {
      nextMessage = MASCOT_MESSAGES[0];
    } else {
      const shuffled = [...MASCOT_MESSAGES];
      for (let i = shuffled.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }
      nextMessage = shuffled.find((msg) => msg !== current) || shuffled[0];
    }

    if (force || nextMessage !== current) {
      mascotSpeech.textContent = nextMessage;
    }

    window.clearTimeout(mascotTimer);
    mascotTimer = window.setTimeout(() => {
      mascotSpeech?.classList.add('is-hidden');
    }, MASCOT_HIDE_DELAY);
  }

  function showToast(message) {
    if (!toast || !message) return;
    toast.textContent = message;
    toast.classList.add('is-visible');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.classList.remove('is-visible');
    }, 2800);
  }

  function resetFileInput(message) {
    if (!fileInput || !fileName) return;
    fileInput.value = '';
    fileName.textContent = message || 'ยังไม่ได้เลือกไฟล์';
  }

  function validateFile(file) {
    if (!file) {
      resetFileInput();
      return;
    }
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      showToast('รองรับเฉพาะไฟล์ภาพ JPG, PNG หรือ WebP เท่านั้น');
      resetFileInput();
      return;
    }
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      showToast('ไฟล์มีขนาดใหญ่เกิน 4MB');
      resetFileInput();
      return;
    }
    if (fileName) {
      fileName.textContent = file.name;
    }
  }

  function setMicState(recording) {
    if (!micButton) return;
    isRecording = recording;
    micButton.classList.toggle('is-recording', recording);
    micButton.setAttribute('aria-pressed', recording ? 'true' : 'false');
    micButton.setAttribute('aria-label', recording ? 'หยุดฟังเสียง' : 'เริ่มฟังเสียง');
  }

  function stopFaceDetection() {
    if (faceTimer) {
      window.clearInterval(faceTimer);
      faceTimer = null;
    }
    faceInFlight = false;
    if (faceStream) {
      faceStream.getTracks().forEach((track) => track.stop());
      faceStream = null;
    }
    if (faceVideo) {
      faceVideo.srcObject = null;
    }
    if (faceContainer) {
      faceContainer.hidden = true;
    }
    faceActivated = false;
    lastFaceStatus = null;
    updateFaceIndicator('idle');
    window.clearTimeout(mascotTimer);
    if (mascotSpeech) {
      mascotSpeech.classList.add('is-hidden');
    }
  }

  function updateFaceIndicator(statusKey, detail) {
    if (!faceStatus || !faceStatusLabel) {
      return;
    }
    const status = statusKey || 'idle';
    faceStatus.dataset.status = status;

    let label = 'กล้องพร้อมตรวจจับ';
    if (status === 'scanning') {
      label = 'กำลังตรวจจับใบหน้า...';
    } else if (status === 'detected') {
      const count = detail?.count ?? detail?.faces?.length ?? 0;
      label = count > 1 ? `พบใบหน้าจำนวน ${count} คน` : 'พบใบหน้าแล้ว';
    } else if (status === 'none') {
      label = 'ยังไม่พบใบหน้า';
    } else if (status === 'error') {
      label = detail?.error ? String(detail.error) : 'ไม่สามารถใช้งานกล้องได้';
    }

    faceStatusLabel.textContent = label;
  }

  function dispatchFaceEvent(detail) {
    if (typeof window.CustomEvent === 'function') {
      window.dispatchEvent(new CustomEvent('npt-face-detect', { detail }));
    }
    window.__NPT_FACE_STATE__ = detail;
    notifyFaceStatus(detail);
  }

  function notifyFaceStatus(detail) {
    if (!detail) {
      return;
    }
    let statusKey = 'idle';
    if (!detail.success) {
      statusKey = 'error';
    } else if ((detail.count || 0) > 0) {
      statusKey = 'detected';
    } else {
      statusKey = 'none';
    }

    updateFaceIndicator(statusKey, detail);

    if (lastFaceStatus === statusKey) {
      return;
    }
    lastFaceStatus = statusKey;

    if (statusKey === 'detected') {
      setMascotGreeting(true);
    } else {
      if (mascotSpeech) {
        window.clearTimeout(mascotTimer);
        mascotSpeech.classList.add('is-hidden');
      }
    }
  }

  async function captureFaceFrame() {
    if (!faceVideo || !faceCanvas || !faceStream || faceInFlight) {
      return;
    }
    if (faceVideo.readyState < 2) {
      return;
    }

    const width = faceVideo.videoWidth;
    const height = faceVideo.videoHeight;
    if (!width || !height) {
      return;
    }

    const ctx = faceCanvas.getContext('2d');
    if (!ctx) {
      return;
    }

    faceInFlight = true;
    try {
      faceCanvas.width = width;
      faceCanvas.height = height;
      ctx.drawImage(faceVideo, 0, 0, width, height);
      const dataUrl = faceCanvas.toDataURL('image/jpeg', 0.5);

      const response = await fetch('/api/face-detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: dataUrl }),
      });

      const payload = await response.json();
      if (!payload?.success) {
        dispatchFaceEvent({ success: false, error: payload?.error });
        return;
      }
      dispatchFaceEvent({ success: true, faces: payload.faces, count: payload.count });
    } catch (error) {
      console.warn('Face detection request failed', error);
      dispatchFaceEvent({ success: false, error: 'การตรวจจับใบหน้าล้มเหลว' });
    } finally {
      faceInFlight = false;
    }
  }

  function scheduleFaceDetection() {
    if (faceTimer) {
      window.clearInterval(faceTimer);
    }
    captureFaceFrame();
    faceTimer = window.setInterval(captureFaceFrame, FACE_CAPTURE_INTERVAL);
  }

  async function startFaceDetection() {
    if (faceActivated || !faceVideo || !faceCanvas) {
      return;
    }
    faceActivated = true;

    if (!navigator.mediaDevices?.getUserMedia) {
      dispatchFaceEvent({ success: false, error: 'อุปกรณ์นี้ไม่รองรับการใช้งานกล้อง' });
      faceActivated = false;
      updateFaceIndicator('error', { error: 'อุปกรณ์นี้ไม่รองรับกล้อง' });
      return;
    }

    updateFaceIndicator('scanning');

    try {
      faceStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      faceVideo.srcObject = faceStream;
      await faceVideo.play().catch(() => undefined);
      if (faceContainer) {
        faceContainer.hidden = true;
      }
      scheduleFaceDetection();
    } catch (error) {
      console.warn('Unable to start face detection', error);
      dispatchFaceEvent({ success: false, error: 'ไม่ได้รับอนุญาตให้เปิดกล้อง' });
      stopFaceDetection();
      updateFaceIndicator('error', { error: 'ไม่สามารถเปิดกล้องได้' });
    }
  }

  function requestFaceDetection() {
    if (faceActivated) {
      return;
    }
    startFaceDetection();
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      stopFaceDetection();
      faceActivated = false;
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!input) return;
    const value = (input.value || '').trim();
    if (!value) {
      showToast('กรุณาพิมพ์ชื่อสถานที่ก่อนค้นหา');
      input.focus();
      return;
    }
    // store search query to Firebase Realtime Database (non-blocking)
    try {
      if (window.__FIREBASE__ && window.__FIREBASE__.dbApi) {
        const dbApi = window.__FIREBASE__.dbApi;
        const key = `searches/${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        dbApi.set(dbApi.ref(key), {
          query: value,
          createdAt: new Date().toISOString(),
          source: 'index',
        });
      }
    } catch (err) {
      // ignore errors writing to DB so UX is unaffected
      console.warn('Failed to write search to Firebase', err);
    }
    const params = new URLSearchParams({ q: value });
    window.location.href = `/chat?${params.toString()}`;
  }

  function handleMicClick() {
    if (!recognition) {
      showToast('อุปกรณ์นี้ไม่รองรับการจดจำเสียง');
      return;
    }
    if (isRecording) {
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

  if (recognition) {
    recognition.lang = 'th-TH';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.addEventListener('start', () => setMicState(true));
    recognition.addEventListener('end', () => setMicState(false));
    recognition.addEventListener('speechend', () => recognition.stop());
    recognition.addEventListener('result', (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript || '';
      if (input) {
        input.value = transcript;
        input.focus();
      }
    });
    recognition.addEventListener('error', () => {
      setMicState(false);
      showToast('ไม่สามารถใช้งานไมโครโฟนได้');
    });
  } else if (micButton) {
    micButton.disabled = true;
    micButton.setAttribute('aria-disabled', 'true');
  }

  form?.addEventListener('submit', handleSubmit);
  micButton?.addEventListener('click', handleMicClick);
  fileInput?.addEventListener('change', (event) => {
    const file = event.target?.files?.[0];
    validateFile(file || null);
  });

  if (faceVideo && faceCanvas) {
    updateFaceIndicator('idle');

    const activateDetection = () => {
      document.removeEventListener('click', activateDetection);
      document.removeEventListener('touchstart', activateDetection);
      requestFaceDetection();
    };
    document.addEventListener('click', activateDetection, { once: true });
    document.addEventListener('touchstart', activateDetection, { once: true });
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', stopFaceDetection);
    window.addEventListener('pagehide', stopFaceDetection);

    window.NPTFaceDetector = {
      start: requestFaceDetection,
      stop: stopFaceDetection,
    };
  }

  resetFileInput();
  initMobileMenu(); // Initialize mobile menu
})();


