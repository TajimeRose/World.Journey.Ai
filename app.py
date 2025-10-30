from world_journey_ai import create_app


# ✅ สร้างตัวแปรหลักของแอป
app = Flask(__name__)
CORS(app)


if __name__ == '__main__':
    app.run(debug=True)

