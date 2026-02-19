# test_env.py
import os
from dotenv import load_dotenv

print("1. Loading .env file...")
load_dotenv()
print("2. Environment variables after loading:")
print(f"   SECRET_KEY: {os.getenv('SECRET_KEY')}")
print(f"   MYSQL_USER: {os.getenv('MYSQL_USER')}")
print(f"   MYSQL_PASSWORD: {'*' * len(os.getenv('MYSQL_PASSWORD', ''))}")
print(f"   MYSQL_DB: {os.getenv('MYSQL_DB')}")

print("\n3. Testing config.py import...")
try:
    from config import Config
    print(f"   Config.SECRET_KEY: {Config.SECRET_KEY[:10]}...")
    print(f"   Config.MYSQL_USER: {Config.MYSQL_USER}")
    print("✅ Config loaded successfully!")
except Exception as e:
    print(f"❌ Error loading config: {e}")