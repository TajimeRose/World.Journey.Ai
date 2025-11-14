// Guide page JavaScript functionality

document.addEventListener('DOMContentLoaded', function () {
    // Mobile menu toggle functionality
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileMenuBtn && navMenu) {
        mobileMenuBtn.addEventListener('click', function () {
            const isExpanded = this.getAttribute('aria-expanded') === 'true';

            // Toggle menu visibility
            navMenu.classList.toggle('active');

            // Update ARIA attributes
            this.setAttribute('aria-expanded', !isExpanded);

            // Animate hamburger menu
            this.classList.toggle('active');
        });
    }

    // Option card hover effects
    const optionCards = document.querySelectorAll('.option-card');
    optionCards.forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.style.transform = 'translateY(-4px)';
        });

        card.addEventListener('mouseleave', function () {
            this.style.transform = 'translateY(0)';
        });
    });
});

// Trip option selection function
function selectTripOption(optionType) {
    if (optionType === 'automatic') {
        showAutomaticForm();
    } else if (optionType === 'manual') {
        showManualAssistant();
    }
}

// Show manual assistant interface
function showManualAssistant() {
    const content = `
        <div class="manual-assistant">
            <h2>🗺️ วางแผนทริปแบบปรับแต่งเอง</h2>
            <p>บอกความต้องการของคุณ AI จะเป็นผู้ช่วยแนะนำและให้คำปรึกษา</p>
            
            <div class="chat-interface">
                <div id="guide-chat-log" class="guide-chat-log">
                    <div class="ai-message">
                        <div class="message-content">
                            <p>สวัสดีครับ! ผมพร้อมเป็นผู้ช่วยวางแผนทริปให้คุณ</p>
                            <p>อยากไปเที่ยวที่ไหน? มีงบประมาณเท่าไหร่? หรือมีความต้องการพิเศษอะไรไหม?</p>
                        </div>
                    </div>
                </div>
                
                <div class="guide-input-container">
                    <div class="input-wrapper">
                        <input type="text" id="guide-input" placeholder="พิมพ์ข้อความ..." maxlength="500">
                        <button id="guide-send-btn" onclick="sendGuideMessage()">ส่ง</button>
                    </div>
                </div>
            </div>
            
            <div class="quick-actions">
                <button onclick="sendQuickMessage('ช่วยแนะนำสถานที่ท่องเที่ยวยอดนิยม')" class="quick-btn">
                    📍 สถานที่ยอดนิยม
                </button>
                <button onclick="sendQuickMessage('ช่วยคำนวณงบประมาณการเดินทาง')" class="quick-btn">
                    💰 คำนวณงบ
                </button>
                <button onclick="sendQuickMessage('แนะนำเส้นทางการเดินทาง')" class="quick-btn">
                    🚗 เส้นทาง
                </button>
            </div>
            
            <div class="form-actions">
                <button type="button" onclick="goBackToOptions()" class="back-button">← กลับ</button>
            </div>
        </div>
    `;

    updateMainContent(content);

    // Add event listener for Enter key
    const guideInput = document.getElementById('guide-input');
    if (guideInput) {
        guideInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                sendGuideMessage();
            }
        });
        guideInput.focus();
    }
}

// Send message to guide AI
async function sendGuideMessage() {
    const input = document.getElementById('guide-input');
    const sendBtn = document.getElementById('guide-send-btn');
    const chatLog = document.getElementById('guide-chat-log');

    if (!input || !input.value.trim()) return;

    const message = input.value.trim();
    input.value = '';
    sendBtn.disabled = true;
    sendBtn.textContent = 'กำลังส่ง...';

    // Add user message to chat
    addMessageToChat(chatLog, message, 'user');

    // Add typing indicator
    addTypingIndicator(chatLog);

    try {
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: message, mode: 'guide' })
        });

        if (!response.ok) {
            throw new Error('Failed to send message');
        }

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(chatLog);

        if (data.assistant) {
            addMessageToChat(chatLog, data.assistant.text, 'ai', data.assistant.html);
        }

    } catch (error) {
        removeTypingIndicator(chatLog);
        addMessageToChat(chatLog, 'ขออภัย เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'ai');
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'ส่ง';
        input.focus();
    }
}

// Send quick message
function sendQuickMessage(message) {
    const input = document.getElementById('guide-input');
    if (input) {
        input.value = message;
        sendGuideMessage();
    }
}

// Add message to chat log
function addMessageToChat(chatLog, message, type, html = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'user' ? 'user-message' : 'ai-message';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (html && type === 'ai') {
        contentDiv.innerHTML = html;
    } else {
        contentDiv.textContent = message;
    }

    messageDiv.appendChild(contentDiv);
    chatLog.appendChild(messageDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Add typing indicator
function addTypingIndicator(chatLog) {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'ai-message typing-indicator';
    typingDiv.innerHTML = '<div class="message-content"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
    chatLog.appendChild(typingDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator(chatLog) {
    const typingIndicator = chatLog.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Show trip planning form for automatic option
function showAutomaticForm() {
    const content = `
        <div class="planning-form">
            <h2>🤖 วางแผนทริปอัตโนมัติ</h2>
            <p>กรอกข้อมูลด้านล่าง AI จะวางแผนทริปที่เหมาะสมให้คุณ</p>
            
            <form id="automaticTripForm" class="trip-form">
                <div class="form-group">
                    <label for="destination">ปลายทางที่อยากไป:</label>
                    <input type="text" id="destination" name="destination" placeholder="เช่น กรุงเทพ, เชียงใหม่, ภูเก็ต" required>
                </div>
                
                <div class="form-group">
                    <label for="duration">ระยะเวลา (วัน):</label>
                    <select id="duration" name="duration" required>
                        <option value="">เลือกระยะเวลา</option>
                        <option value="1">1 วัน</option>
                        <option value="2">2 วัน 1 คืน</option>
                        <option value="3">3 วัน 2 คืน</option>
                        <option value="4">4 วัน 3 คืน</option>
                        <option value="5">5 วัน 4 คืน</option>
                        <option value="7">1 สัปดาห์</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="budget">งบประมาณ (บาท):</label>
                    <select id="budget" name="budget" required>
                        <option value="">เลือกงบประมาณ</option>
                        <option value="1000-3000">1,000 - 3,000 บาท</option>
                        <option value="3000-5000">3,000 - 5,000 บาท</option>
                        <option value="5000-10000">5,000 - 10,000 บาท</option>
                        <option value="10000-20000">10,000 - 20,000 บาท</option>
                        <option value="20000+">มากกว่า 20,000 บาท</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="interests">สิ่งที่สนใจ:</label>
                    <div class="checkbox-group">
                        <label><input type="checkbox" value="วัด"> วัดและสถานที่ศักดิ์สิทธิ์</label>
                        <label><input type="checkbox" value="ธรรมชาติ"> ธรรมชาติและภูเขา</label>
                        <label><input type="checkbox" value="ทะเล"> ทะเลและชายหาด</label>
                        <label><input type="checkbox" value="อาหาร"> อาหารและตลาด</label>
                        <label><input type="checkbox" value="วัฒนธรรม"> วัฒนธรรมและประวัติศาสตร์</label>
                        <label><input type="checkbox" value="ช้อปปิ้ง"> ช้อปปิ้งและไนท์ไลฟ์</label>
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="button" onclick="goBackToOptions()" class="back-button">← กลับ</button>
                    <button type="button" onclick="processAutomaticTrip()" class="generate-button">🚀 สร้างแผนทริป</button>
                </div>
            </form>
        </div>
    `;

    updateMainContent(content);
}

// Show trip planning form for manual option
function showManualForm() {
    const content = `
        <div class="planning-form">
            <h2>✋ วางแผนทริปด้วยตนเอง</h2>
            <p>เริ่มวางแผนทริปของคุณ AI จะคอยช่วยเหลือและแนะนำ</p>
            
            <div class="manual-options">
                <div class="manual-card" onclick="startManualPlanning('chat')">
                    <div class="manual-icon">💬</div>
                    <h3>สนทนากับ AI</h3>
                    <p>ถามคำถามและขอคำแนะนำจาก AI ได้ทันที</p>
                    <button class="manual-button">เริ่มสนทนา</button>
                </div>
                
                <div class="manual-card" onclick="startManualPlanning('planner')">
                    <div class="manual-icon">📋</div>
                    <h3>เครื่องมือวางแผน</h3>
                    <p>ใช้เครื่องมือวางแผนที่มี AI ช่วยเหลือ</p>
                    <button class="manual-button">เริ่มวางแผน</button>
                </div>
            </div>
            
            <div class="form-actions">
                <button type="button" onclick="goBackToOptions()" class="back-button">← กลับ</button>
            </div>
        </div>
    `;

    document.getElementById('guide-content').innerHTML = content;
}

// Process automatic trip form
async function processAutomaticTrip() {
    const form = document.getElementById('automaticTripForm');
    const formData = new FormData(form);

    const destination = formData.get('destination');
    const duration = formData.get('duration');
    const budget = formData.get('budget');

    const interests = [];
    document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
        interests.push(cb.value);
    });

    // Prompts removed per user request
    const prompt = '';

    // Show the result interface
    const resultContent = `
        <div class="trip-result">
            <h2>🗺️ แผนทริป${destination}</h2>
            <div id="trip-chat-log" class="guide-chat-log">
                <div class="user-message">
                    <div class="message-content">${prompt}</div>
                </div>
            </div>
            <div class="form-actions">
                <button type="button" onclick="goBackToOptions()" class="back-button">← เริ่มใหม่</button>
            </div>
        </div>
    `;

    updateMainContent(resultContent);

    // Send to guide API
    const chatLog = document.getElementById('trip-chat-log');
    addTypingIndicator(chatLog);

    try {
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: prompt, mode: 'guide' })
        });

        if (!response.ok) {
            throw new Error('Failed to send message');
        }

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(chatLog);

        if (data.assistant) {
            addMessageToChat(chatLog, data.assistant.text, 'ai', data.assistant.html);
        }

    } catch (error) {
        removeTypingIndicator(chatLog);
        addMessageToChat(chatLog, 'ขออภัย เกิดข้อผิดพลาดในการสร้างแผนทริป กรุณาลองใหม่อีกครั้ง', 'ai');
    }
}

// Start manual planning
function startManualPlanning(type) {
    if (type === 'chat') {
        // Redirect to chat (no prompt query)
        window.location.href = `/chat`;
    } else if (type === 'planner') {
        // Redirect to chat/planner (no prompt query)
        window.location.href = `/chat`;
    }
}

// Go back to options
function goBackToOptions() {
    location.reload();
}

function handleCategorySelection(category) {
    const placeholder = document.getElementById('guide-placeholder');
    const sections = document.getElementById('guide-sections');

    // Hide placeholder and show content
    if (placeholder) placeholder.style.display = 'none';
    if (sections) {
        sections.style.display = 'block';
        sections.innerHTML = generateCategoryContent(category);
    }
}

function handleTipSelection(tip) {
    const placeholder = document.getElementById('guide-placeholder');
    const sections = document.getElementById('guide-sections');

    // Hide placeholder and show content
    if (placeholder) placeholder.style.display = 'none';
    if (sections) {
        sections.style.display = 'block';
        sections.innerHTML = generateTipContent(tip);
    }
}

function generateCategoryContent(category) {
    const content = {
        'แนะนำยอดนิยม': `
            <div class="content-section">
                <h2>สถานที่ท่องเที่ยวยอดนิยม</h2>
                <div class="places-grid">
                    <div class="place-card">
                        <h3>วัดอรุณราชวรารามราชวรมหาวิหาร</h3>
                        <p>วัดที่มีความสวยงามและเป็นสัญลักษณ์ของกรุงเทพฯ</p>
                    </div>
                    <div class="place-card">
                        <h3>ตลาดน้ำอัมพวา</h3>
                        <p>ตลาดน้ำที่มีชื่อเสียงในจังหวัดสมุทรสงคราม</p>
                    </div>
                    <div class="place-card">
                        <h3>เกาะเสม็ด</h3>
                        <p>เกาะสวยงามในจังหวัดระยอง เหมาะสำหรับการพักผ่อน</p>
                    </div>
                </div>
            </div>
        `,
        'เส้นทางท่องเที่ยว': `
            <div class="content-section">
                <h2>เส้นทางท่องเที่ยวแนะนำ</h2>
                <div class="routes-list">
                    <div class="route-item">
                        <h3>เส้นทางกรุงเทพ 1 วัน</h3>
                        <p>วัดพระแก้ว → พระบรมมหาราชวัง → วัดโพธิ์ → ตลาดโรงเกลือ</p>
                    </div>
                    <div class="route-item">
                        <h3>เส้นทางสมุทรสงคราม 2 วัน 1 คืน</h3>
                        <p>ตลาดน้ำอัมพวา → วัดบางกุ้ง → ชมหิ่งห้อย → วัดบ้านแหลม</p>
                    </div>
                </div>
            </div>
        `,
        'กิจกรรมพิเศษ': `
            <div class="content-section">
                <h2>กิจกรรมพิเศษ</h2>
                <div class="activities-list">
                    <div class="activity-item">
                        <h3>ชมหิ่งห้อยที่อัมพวา</h3>
                        <p>กิจกรรมยามค่ำคืนที่ไม่ควรพลาด ช่วงเวลา 19:30-21:00 น.</p>
                    </div>
                    <div class="activity-item">
                        <h3>ล่องเรือชมวิถีชีวิตริมน้ำ</h3>
                        <p>สัมผัสวิถีชีวิตของชาวบ้านริมคลองและชิมอาหารท้องถิ่น</p>
                    </div>
                </div>
            </div>
        `,
        'สถานที่ใหม่': `
            <div class="content-section">
                <h2>สถานที่ใหม่ที่น่าสนใจ</h2>
                <div class="new-places">
                    <div class="place-card">
                        <h3>Sky Garden Observatory</h3>
                        <p>จุดชมวิวใหม่ในกรุงเทพฯ ที่มีความสูง 314 เมตร</p>
                    </div>
                    <div class="place-card">
                        <h3>พิพิธภัณฑ์สยาม</h3>
                        <p>พิพิธภัณฑ์แห่งใหม่ที่เล่าเรื่องราวประวัติศาสตร์ไทย</p>
                    </div>
                </div>
            </div>
        `
    };

    return content[category] || `
        <div class="content-section">
            <h2>${category}</h2>
            <p>ข้อมูลสำหรับหมวดหมู่นี้กำลังจัดเตรียม กรุณาลองใหม่อีกครั้งในภายหลัง</p>
        </div>
    `;
}

function generateTipContent(tip) {
    const tips = {
        'การเตรียมตัวก่อนเดินทาง': `
            <div class="content-section">
                <h2>การเตรียมตัวก่อนเดินทาง</h2>
                <div class="tips-content">
                    <h3>สิ่งที่ควรเตรียม:</h3>
                    <ul>
                        <li>ตรวจสอบสภาพอากาศของปลายทาง</li>
                        <li>เตรียมเอกสารการเดินทาง (บัตรประชาชน, พาสปอร์ต)</li>
                        <li>จองที่พักล่วงหน้า</li>
                        <li>เตรียมเงินสำรองและบัตรเครดิต</li>
                        <li>ดาวน์โหลดแอปแปลภาษาและแผนที่</li>
                    </ul>
                </div>
            </div>
        `,
        'การใช้งบประมาณอย่างฉลาด': `
            <div class="content-section">
                <h2>การใช้งบประมาณอย่างฉลาด</h2>
                <div class="tips-content">
                    <h3>เคล็ดลับประหยัดเงิน:</h3>
                    <ul>
                        <li>จองล่วงหน้าเพื่อได้ราคาที่ดีกว่า</li>
                        <li>เลือกเดินทางในช่วง Low Season</li>
                        <li>ใช้บัตรนักเรียนหรือบัตรผู้สูงอายุ (ถ้ามี)</li>
                        <li>หาข้อมูลโปรโมชั่นพิเศษจากเว็บไซต์ต่างๆ</li>
                        <li>ทานอาหารท้องถิ่นแทนร้านอาหารแพง</li>
                    </ul>
                </div>
            </div>
        `
    };

    return tips[tip] || `
        <div class="content-section">
            <h2>${tip}</h2>
            <p>เคล็ดลับสำหรับหัวข้อนี้กำลังจัดเตรียม กรุณาลองใหม่อีกครั้งในภายหลัง</p>
        </div>
    `;
}

// Helper function to update main content
function updateMainContent(content) {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.innerHTML = content;
    }
}

// Go back to trip options
function goBackToOptions() {
    location.reload(); // Simple way to go back to the original options
}