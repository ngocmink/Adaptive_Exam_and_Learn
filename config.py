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

def normalize_database_url(uri):
    if uri and uri.startswith(('postgres://', 'postgresql://')):
        return 'postgresql+psycopg://' + uri.split('://', 1)[1]
    return uri

def environment_config():
    return {
        'TRUST_PROXY': os.getenv('TRUST_PROXY', 'false').lower() == 'true',
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'SQLALCHEMY_DATABASE_URI': normalize_database_url(os.getenv('DATABASE_URL')),
        'SESSION_COOKIE_SECURE': os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
    }
