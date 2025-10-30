# ใช้ factory function เพื่อสร้าง Flask app และตั้งค่า (เช่น CORS, services)
from world_journey_ai import create_app
import datetime

# สร้างแอปจาก factory (CORS ถูกตั้งค่าแล้วใน create_app)
app = create_app()


# ชั่วคราว: สร้าง document ตัวอย่างใน MongoDB เพื่อให้ฐานข้อมูล/collection ถูกสร้างอัตโนมัติ
@app.get("/mongo-test")
def mongo_test_root():
    events = app.extensions.get("mongo_events")
    if events is None:
        return {"ok": False, "error": "mongo not configured"}, 500

    try:
        events.insert_one({
            "uid": "test",
            "event": "test_event",
            "created_at": datetime.datetime.utcnow(),
        })
    except Exception as exc:
        return {"ok": False, "error": str(exc)}, 500

    return {"ok": True}


if __name__ == '__main__':
    # รันเซิร์ฟเวอร์แบบ development
    app.run(debug=True)

