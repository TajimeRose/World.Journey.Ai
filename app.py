# ...existing code...
from world_journey_ai import create_app

# สร้างแอปจาก factory (CORS ถูกตั้งค่าแล้วใน create_app)
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
# ...existing code...

