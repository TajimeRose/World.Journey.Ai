# World Journey AI

สามหน้าหลักสำหรับวางแผนการเดินทางด้วย AI น้องปลาทู พร้อม Firebase Authentication

## การติดตั้ง
1. ติดตั้ง Python 3.10 ขึ้นไป และสร้าง virtual environment
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. ติดตั้งไลบรารีที่จำเป็น
   ```bash
   pip install flask flask-cors
   ```
3. ตั้งค่าตัวแปรสภาพแวดล้อมสำหรับ Firebase ตามไฟล์ `firebase_config.js`
   ```text
   FIREBASE_API_KEY
   FIREBASE_AUTH_DOMAIN
   FIREBASE_PROJECT_ID
   FIREBASE_APP_ID
   FIREBASE_MESSAGING_SENDER_ID (ถ้ามี)
   FIREBASE_DATABASE_URL (ถ้ามี)
   FIREBASE_STORAGE_BUCKET (ถ้ามี)
   ```
4. รันเซิร์ฟเวอร์
   ```bash
   python app.py
   ```
5. เปิดเว็บเบราว์เซอร์ไปที่ http://127.0.0.1:5000

## โครงสร้างโปรเจกต์
```
project_root/
├── app.py
├── firebase_config.js
├── requirements.txt (optional)
├── static/
│   ├── css/
│   │   ├── chat.css
│   │   ├── index.css
│   │   └── login.css
│   ├── img/
│   │   ├── globe.png
│   │   └── favicon.ico
│   └── js/
│       ├── auth-state.js
│       ├── chat.js
│       ├── firebase-init.js
│       ├── index.js
│       └── login.js
└── templates/
    ├── chat.html
    ├── index.html
    └── login.html
```

## ฟังก์ชันหลัก
- `/login` ลงชื่อเข้าใช้/สมัครสมาชิกผ่าน Firebase พร้อมบันทึก Display Name ลง Realtime Database
- `/` หน้า Landing มีโลกหมุน ฟังก์ชันพูด-พิมพ์-แนบรูป และส่งต่อไปยังห้องแชต
- `/chat` ห้องสนทนา AI แสดงชื่อผู้ใช้/AI, แถบพิมพ์พร้อมไมค์และไฟล์ และการพิมพ์ตอบแบบ typing animation
- `/api/search` คืนข้อมูลสถานที่ (กรุงเทพ, สมุทรสงคราม, โซล ฯลฯ) ในรูปแบบ JSON
- `/api/messages` จัดเก็บบทสนทนาในหน่วยความจำ และตอบเที่ยวกรุงเทพแบบละเอียด 510 จุดพร้อมลิงก์ Google Maps

## หมายเหตุ
- ระบบเก็บบทสนทนาในหน่วยความจำชั่วคราว (จะรีเซ็ตเมื่อรีสตาร์ทเซิร์ฟเวอร์)
- ปรับแต่งค่าธีม สี และสำเนาตามดีไซน์เพิ่มเติมได้จากไฟล์ CSS/JS ตามหน้าที่
- หากต้องการเชื่อมต่อ OpenAI สามารถต่อยอดใน `app.py` ภายหลังได้
