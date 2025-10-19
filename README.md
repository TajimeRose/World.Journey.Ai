1. ติดตั้ง Python (แนะนำ 3.10+) และเลือก "Add Python to PATH" ขณะติดตั้ง.

2. สร้างและเปิดใช้งาน virtual environment ในโฟลเดอร์โปรเจค:
สร้าง: python -m venv .venv
เปิดใช้งาน (PowerShell): .venv\Scripts\Activate

3. ติดตั้งไลบรารีที่โปรเจคต้องการ:
pip install flask requests unidecode python-dotenv openai
(ถ้าต้องการไฟล์ requirements.txt ให้สร้างและใช้ pip install -r requirements.txt)
pip install flask requests unidecode python-dotenv openai


4. ตั้งตัวแปรสภาพแวดล้อมที่จำเป็น (ถ้าใช้ OpenAI / Meili):
PowerShell (ชั่วคราว): $env:OPENAI_API_KEY="YOUR_KEY"
CMD (ชั่วคราว): set OPENAI_API_KEY=YOUR_KEY
ถา้ใช้ Meili: ตั้ง MEILI_URL และ MEILI_KEY ในลักษณะเดียวกัน

5. รันแอพในโฟลเดอร์ที่มี app.py:
python app.py