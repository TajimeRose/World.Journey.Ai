(function () {
    const form = document.getElementById('journey-form');
    const input = document.getElementById('destination-input');
    const output = document.getElementById('output-text');
    const micButton = document.getElementById('mic-button');
    const toast = document.getElementById('toast');
    const tickerTrack = document.querySelector('.ticker-track');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const imageValidation = document.getElementById('image-validation');

    const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
    const MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024;
    const MAX_FUZZY_DISTANCE = 2;
    const THAI_TONE_MARKS_REGEX = /[\u0E31\u0E34-\u0E37\u0E47\u0E48-\u0E4C\u0E3A]/g;
    const WHITESPACE_REGEX = /\s+/g;

    let recognition = null;
    let isRecording = false;
    let toastTimer = null;

    const stripThaiToneMarks = (value = '') => value.replace(THAI_TONE_MARKS_REGEX, '');
    const normaliseKey = (value = '') => stripThaiToneMarks(value.toString().toLowerCase().normalize('NFC')).replace(WHITESPACE_REGEX, '');

    const PLACE_DATA = [
        {
            name: 'สมุทรสงคราม',
            keywords: ['สมุทรสงคราม', 'จังหวัดสมุทรสงคราม', 'samut songkhram'],
            attractions: [
                { name: 'ตลาดน้ำอัมพวา', popularity: 100 },
                { name: 'ตลาดร่มหุบ', popularity: 92 },
                { name: 'ดอนหอยหลอด', popularity: 88 },
                { name: 'วัดบางกุ้ง', popularity: 84 },
                { name: 'ตลาดน้ำท่าคา', popularity: 78 },
                { name: 'ศาลเจ้าแม่อัมพวา', popularity: 70 }
            ]
        },
        {
            name: 'กรุงเทพมหานคร',
            keywords: ['กรุงเทพ', 'bangkok', 'bangkok city', 'bkk'],
            attractions: [
                { name: 'พระบรมมหาราชวัง', popularity: 100 },
                { name: 'วัดพระเชตุพนวิมลมังคลาราม (วัดโพธิ์)', popularity: 95 },
                { name: 'วัดอรุณราชวราราม', popularity: 92 },
                { name: 'เยาวราช', popularity: 88 },
                { name: 'ไอคอนสยาม', popularity: 84 },
                { name: 'พิพิธภัณฑ์ศิลปะร่วมสมัย (MOCA)', popularity: 76 }
            ]
        },
        {
            name: 'พัทยา',
            keywords: ['เมืองพัทยา', 'pattaya'],
            attractions: [
                { name: 'ชายหาดพัทยา', popularity: 96 },
                { name: 'เกาะล้าน', popularity: 94 },
                { name: 'ปราสาทสัจธรรม', popularity: 90 },
                { name: 'สวนนงนุชพัทยา', popularity: 86 },
                { name: 'Walking Street พัทยา', popularity: 82 },
                { name: 'เขาพระตำหนัก', popularity: 78 }
            ]
        },
        {
            name: 'เชียงใหม่',
            keywords: ['จังหวัดเชียงใหม่', 'chiang mai'],
            attractions: [
                { name: 'วัดพระธาตุดอยสุเทพราชวรวิหาร', popularity: 98 },
                { name: 'อุทยานแห่งชาติดอยอินทนนท์', popularity: 94 },
                { name: 'ถนนนิมมานเหมินท์', popularity: 90 },
                { name: 'บ้านแม่กำปอง', popularity: 86 },
                { name: 'วัดพระสิงห์วรมหาวิหาร', popularity: 84 },
                { name: 'สวนสัตว์เชียงใหม่', popularity: 78 }
            ]
        },
        {
            name: 'ภูเก็ต',
            keywords: ['จังหวัดภูเก็ต', 'phuket'],
            attractions: [
                { name: 'หาดป่าตอง', popularity: 97 },
                { name: 'แหลมพรหมเทพ', popularity: 92 },
                { name: 'เมืองเก่าภูเก็ต', popularity: 90 },
                { name: 'เกาะพีพี', popularity: 88 },
                { name: 'หาดกะตะ', popularity: 84 },
                { name: 'จุดชมวิวกะรน', popularity: 80 }
            ]
        },
        {
            name: 'เกียวโต',
            keywords: ['kyoto', 'kyouto', 'เมืองเกียวโต'],
            attractions: [
                { name: 'วัดคิโยะมิสึเดระ', popularity: 98 },
                { name: 'ศาลเจ้าฟุชิมิ อินาริ', popularity: 96 },
                { name: 'ป่าไผ่อาราชิยามะ', popularity: 92 },
                { name: 'กิออน', popularity: 88 },
                { name: 'วัดคินคะคุจิ (ศาลาทอง)', popularity: 86 },
                { name: 'ปราสาทนิโจ', popularity: 82 }
            ]
        },
        {
            name: 'โซล',
            keywords: ['seoul', 'โซล เกาหลี', 'โซล เกาหลีใต้'],
            attractions: [
                { name: 'พระราชวังคย็องบกกุง', popularity: 97 },
                { name: 'ย่านมยองดง', popularity: 93 },
                { name: 'หอคอยเอ็นโซล', popularity: 90 },
                { name: 'คลองชองกเยชอน', popularity: 86 },
                { name: 'ย่านฮงแด', popularity: 84 },
                { name: 'หมู่บ้านบุกชอนฮันอก', popularity: 82 }
            ]
        },
        {
            name: 'ปารีส',
            keywords: ['paris', 'เมืองปารีส'],
            attractions: [
                { name: 'หอไอเฟล', popularity: 100 },
                { name: 'พิพิธภัณฑ์ลูฟวร์', popularity: 96 },
                { name: 'ประตูชัยอาร์กเดอทรียงฟ์', popularity: 92 },
                { name: 'ย่านมงมาร์ต', popularity: 88 },
                { name: 'มหาวิหารนอเทรอดาม', popularity: 86 },
                { name: 'ล่องเรือแม่น้ำแซน', popularity: 82 }
            ]
        },
        {
            name: 'ดูไบ',
            keywords: ['dubai', 'เมืองดูไบ'],
            attractions: [
                { name: 'ตึกเบิร์จคาลิฟา (Burj Khalifa)', popularity: 100 },
                { name: 'ดูไบมอลล์', popularity: 94 },
                { name: 'เดอะปาล์ม จูเมราห์', popularity: 92 },
                { name: 'น้ำพุดูไบ', popularity: 90 },
                { name: 'ดูไบมารีนา', popularity: 86 },
                { name: 'พิพิธภัณฑ์แห่งอนาคต', popularity: 84 }
            ]
        }
    ];

    const PLACE_DATA_INDEX = PLACE_DATA.map((entry) => {
        const keywords = Array.isArray(entry.keywords) ? entry.keywords : [];
        const normalizedKeywords = Array.from(new Set([entry.name, ...keywords].map(normaliseKey))).filter(Boolean);
        return {
            entry,
            normalizedName: normaliseKey(entry.name),
            normalizedKeywords
        };
    });

    const renderOutput = (text) => {
        if (!output) {
            return;
        }
        output.textContent = text;
    };

    const showImageValidation = (message = '') => {
        if (!imageValidation) {
            return;
        }
        imageValidation.textContent = message;
        imageValidation.classList.toggle('is-visible', Boolean(message));
    };

    const clearImageValidation = () => {
        showImageValidation('');
    };

    const resetImagePreview = () => {
        if (!imagePreview) {
            return;
        }
        const emptyLabel = imagePreview.dataset ? imagePreview.dataset.empty || '' : '';
        imagePreview.textContent = emptyLabel;
        imagePreview.title = emptyLabel;
        imagePreview.classList.remove('has-file');
    };

    const renderImagePreview = async (file) => {
        if (!imagePreview) {
            return;
        }
        resetImagePreview();
        const fileName = file && typeof file.name === 'string' ? file.name.trim() : '';
        if (!fileName) {
            return;
        }
        imagePreview.textContent = fileName;
        imagePreview.title = fileName;
        imagePreview.classList.add('has-file');
    };

    const computeLevenshtein = (a, b, maxDistance = MAX_FUZZY_DISTANCE) => {
        if (a === b) {
            return 0;
        }
        if (!a.length) {
            return b.length <= maxDistance ? b.length : maxDistance + 1;
        }
        if (!b.length) {
            return a.length <= maxDistance ? a.length : maxDistance + 1;
        }
        if (Math.abs(a.length - b.length) > maxDistance) {
            return maxDistance + 1;
        }
        const previous = new Array(b.length + 1);
        const current = new Array(b.length + 1);
        for (let j = 0; j <= b.length; j += 1) {
            previous[j] = j;
        }
        for (let i = 1; i <= a.length; i += 1) {
            current[0] = i;
            let smallest = current[0];
            const codeA = a.charCodeAt(i - 1);
            for (let j = 1; j <= b.length; j += 1) {
                const cost = codeA === b.charCodeAt(j - 1) ? 0 : 1;
                const deletion = previous[j] + 1;
                const insertion = current[j - 1] + 1;
                const substitution = previous[j - 1] + cost;
                const value = Math.min(deletion, insertion, substitution);
                current[j] = value;
                if (value < smallest) {
                    smallest = value;
                }
            }
            if (smallest > maxDistance) {
                return maxDistance + 1;
            }
            for (let j = 0; j <= b.length; j += 1) {
                previous[j] = current[j];
            }
        }
        const distance = previous[b.length];
        return distance > maxDistance ? maxDistance + 1 : distance;
    };

    const findBestDatasetMatch = (normalizedInput) => {
        if (!normalizedInput) {
            return null;
        }
        let bestEntry = null;
        let bestScore = Number.POSITIVE_INFINITY;

        for (const item of PLACE_DATA_INDEX) {
            for (const keyword of item.normalizedKeywords) {
                if (!keyword) {
                    continue;
                }
                if (normalizedInput === keyword || normalizedInput.includes(keyword) || keyword.includes(normalizedInput)) {
                    return item.entry;
                }
                const distance = computeLevenshtein(normalizedInput, keyword, MAX_FUZZY_DISTANCE);
                if (distance < bestScore) {
                    bestScore = distance;
                    bestEntry = item.entry;
                }
            }
        }

        if (bestScore <= MAX_FUZZY_DISTANCE) {
            return bestEntry;
        }
        return null;
    };

    const buildRankedAttractions = (entry) => {
        if (!entry || !Array.isArray(entry.attractions)) {
            return [];
        }
        return entry.attractions
            .slice()
            .sort((a, b) => {
                const popA = typeof a.popularity === 'number' ? a.popularity : 0;
                const popB = typeof b.popularity === 'number' ? b.popularity : 0;
                if (popA === popB) {
                    return (a.name || '').localeCompare(b.name || '', 'th');
                }
                return popB - popA;
            })
            .slice(0, 10)
            .map((item) => item.name);
    };

    const buildGenericAttractions = (placeName) => [
        `เดินเที่ยวสำรวจย่านโดดเด่นของ${placeName}`,
        `ลิ้มลองอาหารท้องถิ่นขึ้นชื่อใน${placeName}`,
        `ชมวิวมุมสูงหรือจุดชมพระอาทิตย์ตกใน${placeName}`,
        `แวะเยือนพิพิธภัณฑ์หรือแกลเลอรีศิลป์ใน${placeName}`,
        `พักผ่อนในสวนสาธารณะหรือริมแม่น้ำของ${placeName}`
    ];

    const formatOutput = (placeName, attractions) => {
        const list = Array.isArray(attractions) && attractions.length ? attractions : buildGenericAttractions(placeName);
        const numbered = list.map((name, index) => `${index + 1}) ${name}`);
        return [`สถานที่ท่องเที่ยวใน${placeName}`, ...numbered].join('\n');
    };

    const searchPlaceViaApi = async (query) => {
        if (typeof fetch !== 'function') {
            return null;
        }
        const controller = typeof AbortController === 'function' ? new AbortController() : null;
        const url = `/api/search?q=${encodeURIComponent(query)}`;
        let timeoutId = null;
        if (controller) {
            timeoutId = window.setTimeout(() => {
                controller.abort();
            }, 3500);
        }
        try {
            const response = await fetch(url, { signal: controller ? controller.signal : undefined });
            if (!response.ok) {
                return null;
            }
            const data = await response.json();
            if (!data) {
                return null;
            }
            if (Array.isArray(data)) {
                const candidate = data[0];
                if (candidate) {
                    if (typeof candidate === 'string') {
                        return candidate;
                    }
                    if (typeof candidate.name === 'string') {
                        return candidate.name;
                    }
                    if (typeof candidate.title === 'string') {
                        return candidate.title;
                    }
                }
                return null;
            }
            if (Array.isArray(data.results) && data.results[0]) {
                const first = data.results[0];
                if (typeof first === 'string') {
                    return first;
                }
                if (typeof first.name === 'string') {
                    return first.name;
                }
                if (typeof first.title === 'string') {
                    return first.title;
                }
            }
            if (typeof data.name === 'string') {
                return data.name;
            }
            if (data.top && typeof data.top === 'object') {
                if (typeof data.top.name === 'string') {
                    return data.top.name;
                }
                if (typeof data.top.title === 'string') {
                    return data.top.title;
                }
            }
            return null;
        } catch (error) {
            return null;
        } finally {
            if (timeoutId) {
                window.clearTimeout(timeoutId);
            }
        }
    };

    const resolveCanonicalPlace = async (rawInput) => {
        const trimmed = (rawInput || '').trim();
        if (!trimmed) {
            return { canonicalName: '', datasetEntry: null };
        }
        const normalizedInput = normaliseKey(trimmed);
        let canonicalName = trimmed;
        let datasetEntry = null;

        const apiName = await searchPlaceViaApi(trimmed);
        if (apiName) {
            canonicalName = apiName;
            datasetEntry = findBestDatasetMatch(normaliseKey(apiName)) || findBestDatasetMatch(normalizedInput);
        } else {
            datasetEntry = findBestDatasetMatch(normalizedInput);
            if (datasetEntry) {
                canonicalName = datasetEntry.name;
            }
        }

        if (!datasetEntry) {
            const fallbackMatch = findBestDatasetMatch(normaliseKey(canonicalName));
            if (fallbackMatch) {
                datasetEntry = fallbackMatch;
                canonicalName = fallbackMatch.name;
            }
        }

        return { canonicalName, datasetEntry };
    };

    const produceOutput = async (placeRaw = '') => {
        const trimmed = (placeRaw || '').trim();
        if (!trimmed) {
            renderOutput('');
            return;
        }
        try {
            const { canonicalName, datasetEntry } = await resolveCanonicalPlace(trimmed);
            const attractions = datasetEntry ? buildRankedAttractions(datasetEntry) : buildGenericAttractions(canonicalName);
            renderOutput(formatOutput(canonicalName, attractions));
        } catch (error) {
            renderOutput(formatOutput(trimmed, buildGenericAttractions(trimmed)));
        }
    };

    const onImageSelected = async (file) => {
        if (!file) {
            return;
        }
        clearImageValidation();

        if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
            showImageValidation('รองรับเฉพาะไฟล์ JPG, PNG หรือ WebP');
            resetImagePreview();
            if (imageInput) {
                imageInput.value = '';
            }
            return;
        }

        if (file.size > MAX_IMAGE_SIZE_BYTES) {
            showImageValidation('ไฟล์มีขนาดเกิน 4MB กรุณาเลือกไฟล์ที่เล็กกว่า');
            resetImagePreview();
            if (imageInput) {
                imageInput.value = '';
            }
            return;
        }

        await renderImagePreview(file);
        clearImageValidation();

        let placeFromImage = '';
        if (typeof window.searchPlaceFromImage === 'function') {
            try {
                const maybePlace = await Promise.resolve(window.searchPlaceFromImage(file));
                if (typeof maybePlace === 'string') {
                    placeFromImage = maybePlace.trim();
                }
            } catch (error) {
                placeFromImage = '';
            }
        }

        const typedValue = input ? input.value.trim() : '';
        const candidate = typedValue || placeFromImage;

        if (!candidate) {
            showImageValidation('อัปโหลดสำเร็จแล้ว ลองพิมพ์ชื่อสถานที่เพื่อรับคำแนะนำ');
            return;
        }

        await produceOutput(candidate);
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
        produceOutput(input.value);
    };

    const handleMicClick = () => {
        if (!recognition) {
            showToast('เบราว์เซอร์ของคุณไม่รองรับคำสั่งเสียง');
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

    renderOutput('');
    initialiseTicker();
    window.addEventListener('resize', initialiseTicker, { passive: true });

    if (form) {
        form.addEventListener('submit', handleSubmit);
    }

    if (micButton) {
        micButton.addEventListener('click', handleMicClick);
        setMicRecordingState(false);
    }

    if (imageInput) {
        imageInput.addEventListener('change', (event) => {
            const target = event.target;
            const file = target && target.files && target.files[0];
            if (!file) {
                resetImagePreview();
                clearImageValidation();
                return;
            }
            onImageSelected(file).catch(() => {
                resetImagePreview();
                showImageValidation('ไม่สามารถประมวลผลไฟล์ได้ กรุณาลองใหม่อีกครั้ง');
                if (imageInput) {
                    imageInput.value = '';
                }
            });
        });
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        if (micButton) {
            micButton.disabled = true;
            micButton.setAttribute('aria-disabled', 'true');
        }
        showToast('เบราว์เซอร์ของคุณไม่รองรับคำสั่งเสียง');
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
        const transcript = (event.results[0] && event.results[0][0] && event.results[0][0].transcript) || '';
        if (input) {
            input.value = transcript;
        }
        produceOutput(transcript);
    });

    recognition.addEventListener('error', () => {
        setMicRecordingState(false);
        showToast('เกิดข้อผิดพลาดในการใช้งานคำสั่งเสียง');
    });
})();

