(function () {
    const form = document.getElementById('journey-form');
    const input = document.getElementById('destination-input');
    const output = document.getElementById('output-text');
    const micButton = document.getElementById('mic-button');
    const toast = document.getElementById('toast');
    const tickerTrack = document.querySelector('.ticker-track');

    let recognition = null;
    let isRecording = false;
    let toastTimer = null;

    const buildOutputText = (raw = '') => {
        const trimmed = raw.trim();
        return trimmed ? `สถานที่ท่องเที่ยวใน${trimmed}` : '';
    };

    const updateOutput = (value) => {
        if (!output) {
            return;
        }
        output.textContent = buildOutputText(value);
    };

    const showToast = (message) => {
        if (!message) {
            return;
        }
        if (!toast) {
            window.alert(message);
            return;
        }
        toast.textContent = message;
        toast.classList.add('is-visible');
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => {
            toast.classList.remove('is-visible');
        }, 3200);
    };

    const setMicRecordingState = (recording) => {
        if (!micButton) {
            return;
        }
        isRecording = recording;
        micButton.classList.toggle('is-recording', recording);
        micButton.setAttribute('aria-pressed', recording ? 'true' : 'false');
        const stateLabel = recording ? 'หยุด' : 'พูด';
        micButton.setAttribute('aria-label', stateLabel);
        const labelNode = micButton.querySelector('.button-label');
        if (labelNode) {
            labelNode.textContent = stateLabel;
        }
    };

    const initialiseTicker = () => {
        if (!tickerTrack) {
            return;
        }
        if (tickerTrack.dataset.duplicated !== 'true') {
            tickerTrack.innerHTML = `${tickerTrack.innerHTML}${tickerTrack.innerHTML}`;
            tickerTrack.dataset.duplicated = 'true';
        }
        window.requestAnimationFrame(() => {
            const halfWidth = tickerTrack.scrollWidth / 2;
            if (!halfWidth) {
                return;
            }
            const durationSeconds = Math.min(Math.max(halfWidth / 45, 16), 36);
            tickerTrack.style.setProperty('--ticker-duration', `${durationSeconds.toFixed(2)}s`);
        });
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        if (!input) {
            return;
        }
        updateOutput(input.value);
    };

    const handleMicClick = () => {
        if (!recognition) {
            showToast('เบราว์เซอร์ไม่รองรับไมค์ให้พิมพ์แทน');
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
    };

    updateOutput('');
    initialiseTicker();
    window.addEventListener('resize', initialiseTicker, { passive: true });

    if (form) {
        form.addEventListener('submit', handleSubmit);
    }

    if (micButton) {
        micButton.addEventListener('click', handleMicClick);
        setMicRecordingState(false);
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        if (micButton) {
            micButton.disabled = true;
            micButton.setAttribute('aria-disabled', 'true');
        }
        showToast('เบราว์เซอร์ไม่รองรับไมค์ให้พิมพ์แทน');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'th-TH';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.addEventListener('start', () => {
        setMicRecordingState(true);
    });

    recognition.addEventListener('speechend', () => {
        recognition.stop();
    });

    recognition.addEventListener('end', () => {
        setMicRecordingState(false);
    });

    recognition.addEventListener('result', (event) => {
        const transcript = event.results[0][0]?.transcript || '';
        if (input) {
            input.value = transcript;
        }
        updateOutput(transcript);
    });

    recognition.addEventListener('error', () => {
        setMicRecordingState(false);
        showToast('เบราว์เซอร์ไม่รองรับไมค์ให้พิมพ์แทน');
    });
})();
