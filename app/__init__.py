from flask import Flask
from sqlalchemy.engine import make_url
from config import Config, ROOT, environment_config
from app.extensions import db, migrate, login_manager, csrf

def create_app(test_config=None):
    app = Flask(__name__, template_folder=str(ROOT / 'templates'), static_folder=None)
    app.config.from_object(Config)
    app.config.update(environment_config())
    if test_config:
        app.config.update(test_config)
    uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if not uri or make_url(uri).get_backend_name() != 'postgresql':
        raise RuntimeError('Set DATABASE_URL to a PostgreSQL connection URL.')
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError('Set SECRET_KEY in .env; no insecure default is supplied.')
    db.init_app(app)
    from app import models
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(models.User, int(user_id))
        except (ValueError, TypeError):
            return None

    from app.common.errors import register_errors
    from app.subject_routes import subjects_bp
    from app.admin.read_routes import admin_read_bp
    from app.seed.import_excel import seed_command, import_command
    register_errors(app)
    app.register_blueprint(subjects_bp)
    app.register_blueprint(admin_read_bp)
    app.cli.add_command(seed_command)
    app.cli.add_command(import_command)
    return app
