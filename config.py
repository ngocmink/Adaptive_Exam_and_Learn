import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024

def environment_config():
    return {
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL'),
        'SESSION_COOKIE_SECURE': os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
    }
