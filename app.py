"""
NFC Student Attendance System - Flask Backend
Main application entry point
"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv

from routes.auth import auth_bp
from routes.students import students_bp
from routes.attendance import attendance_bp
from routes.nfc import nfc_bp
from routes.dashboard import dashboard_bp
from models.db import init_db

load_dotenv()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nfc-attendance-secret-2026')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-nfc-secret-key-2026')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 hours

    # Database config
    app.config['DB_HOST'] = os.getenv('DB_HOST', 'localhost')
    app.config['DB_PORT'] = int(os.getenv('DB_PORT', 3306))
    app.config['DB_USER'] = os.getenv('DB_USER', 'root')
    app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD', '')
    app.config['DB_NAME'] = os.getenv('DB_NAME', 'nfc_attendance')

    # Extensions
    CORS(app, origins=["http://localhost:3000", "http://localhost:5000"])
    JWTManager(app)

    # Init DB
    init_db(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(students_bp, url_prefix='/api/students')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    app.register_blueprint(nfc_bp, url_prefix='/api/nfc')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

    # Serve frontend
    @app.route('/')
    @app.route('/<path:path>')
    def serve_frontend(path=''):
        from flask import send_from_directory
        return send_from_directory('../frontend', 'index.html')

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"🚀 NFC Attendance System running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
