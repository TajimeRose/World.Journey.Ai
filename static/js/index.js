(() => {
  const form = document.getElementById('journey-form');
  const input = document.getElementById('destination-input');
  const micButton = document.getElementById('mic-button');
  const toast = document.getElementById('toast');
  const fileInput = document.getElementById('imageInput');
  const fileName = document.getElementById('imagePreview');

  const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
  const MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = SpeechRecognition ? new SpeechRecognition() : null;
  let isRecording = false;
  let toastTimer = null;

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

  function handleSubmit(event) {
    event.preventDefault();
    if (!input) return;
    const value = (input.value || '').trim();
    if (!value) {
      showToast('กรุณาพิมพ์ชื่อสถานที่ก่อนค้นหา');
      input.focus();
      return;
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

  resetFileInput();
})();


