"""Initialize only the cloud staging DB configured by the hosting provider."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flask_migrate import upgrade
from app import create_app
from app.extensions import db
from app.seed.import_excel import seed_demo

app = create_app()
with app.app_context():
    upgrade(directory='migrations')
    if os.getenv('SEED_DEMO', 'false').lower() == 'true':
        try:
            seed_demo({role: os.getenv(f'DEMO_{role.upper()}_PASSWORD') for role in ('admin','teacher','student')})
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
