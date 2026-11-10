import os
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy import text
from flask_migrate import upgrade
from app import create_app
from config import ROOT
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
from app.extensions import db
from app.models import User
from app.seed.import_excel import seed_demo

def validate_test_database(test_uri, dev_uri):
    if not test_uri or not dev_uri:
        raise RuntimeError('Set TEST_DATABASE_URL and DATABASE_URL explicitly.')
    test = make_url(test_uri)
    dev = make_url(dev_uri)
    if test.get_backend_name() != 'postgresql' or test.database != 'exam_test':
        raise RuntimeError('Tests may reset only the PostgreSQL database named exam_test.')
    if (test.host, test.port or 5432, test.database) == (dev.host, dev.port or 5432, dev.database):
        raise RuntimeError('Test and development database targets must be different.')
    if dev.database == 'exam_test':
        raise RuntimeError('DATABASE_URL must not point at exam_test.')
    if os.getenv('ALLOW_TEST_DB_RESET') != 'yes':
        raise RuntimeError('Set ALLOW_TEST_DB_RESET=yes to permit truncating the isolated test database.')
    return test_uri

@pytest.fixture(scope='session')
def application():
    uri = validate_test_database(os.getenv('TEST_DATABASE_URL'), os.getenv('DATABASE_URL'))
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret',
        'SQLALCHEMY_DATABASE_URI': uri, 'WTF_CSRF_ENABLED': False})
    with app.app_context():
        upgrade(directory='migrations')
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()

@pytest.fixture
def app(application):
    with application.app_context():
        # Check the LIVE connection before executing any destructive test cleanup.
        validate_test_database(str(db.engine.url.render_as_string(hide_password=False)), os.getenv('DATABASE_URL'))
        if db.session.scalar(text('SELECT current_database()')) != 'exam_test':
            raise RuntimeError('Refusing to truncate a non-test database.')
        names = ', '.join('"' + table.name + '"' for table in db.metadata.tables.values())
        db.session.execute(text(f'TRUNCATE {names} RESTART IDENTITY CASCADE'))
        db.session.commit()
        yield application
        db.session.rollback()
        db.session.remove()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def database(app):
    return db

@pytest.fixture
def demo(app):
    seed_demo({role: f'test-{role}-password-123' for role in ('admin','teacher','student')})
    db.session.commit()
    return {user.role: user for user in db.session.query(User).all()}

@pytest.fixture
def login_as(client, demo):
    def login(role):
        with client.session_transaction() as session:
            session.clear()
            session['user_id'] = demo[role].id
        return client
    return login

@pytest.fixture(name='db')
def db_fixture(database):
    return database

@pytest.fixture
def users(demo):
    return demo

@pytest.fixture
def admin_user(demo):
    return demo['admin']

@pytest.fixture
def teacher_user(demo):
    return demo['teacher']

@pytest.fixture
def student_user(demo):
    return demo['student']
