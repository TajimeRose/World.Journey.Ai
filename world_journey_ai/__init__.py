
# world_journey_ai/__init__.py
from flask import Flask
from flask_cors import CORS

# ถ้ามี blueprint หรือ route แยกไฟล์
# from .routes.main import bp as main_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # register blueprint ตรงนี้ ถ้ามี
    # app.register_blueprint(main_bp)

    return app
