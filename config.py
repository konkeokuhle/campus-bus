# config.py
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    # Database configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root123')
    MYSQL_DB = os.getenv('MYSQL_DB', 'campus_bus_db')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_CURSORCLASS = 'DictCursor'
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-do-not-use-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Session configuration - ADD THESE LINES
    SESSION_TYPE = 'filesystem'  # This tells Flask how to store sessions
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True  # Sign the session cookie for security
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    @classmethod
    def print_config(cls):
        """Print configuration for debugging"""
        print("\n" + "="*60)
        print("🔧 CAMPUS BUS CONFIGURATION")
        print("="*60)
        print(f"SECRET_KEY: {'✅ SET' if cls.SECRET_KEY else '❌ NOT SET'}")
        print(f"  └─ Value: {cls.SECRET_KEY[:10]}...")
        print(f"\n📊 SESSION:")
        print(f"  ├─ SESSION_TYPE: {cls.SESSION_TYPE}")
        print(f"  ├─ SESSION_PERMANENT: {cls.SESSION_PERMANENT}")
        print(f"  └─ SESSION_USE_SIGNER: {cls.SESSION_USE_SIGNER}")
        
        print(f"\n🗄️  DATABASE:")
        print(f"  ├─ Host: {cls.MYSQL_HOST}")
        print(f"  ├─ User: {cls.MYSQL_USER}")
        print(f"  ├─ Database: {cls.MYSQL_DB}")
        print(f"  └─ Port: {cls.MYSQL_PORT}")
        print("="*60 + "\n")