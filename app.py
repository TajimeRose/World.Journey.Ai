# ใช้ factory function เพื่อสร้าง Flask app และตั้งค่า (เช่น CORS, services)
from world_journey_ai import create_app
import datetime

# สร้างแอปจาก factory (CORS ถูกตั้งค่าแล้วใน create_app)
app = create_app()



if __name__ == '__main__':
    # รันเซิร์ฟเวอร์แบบ development
    app.run(debug=True)