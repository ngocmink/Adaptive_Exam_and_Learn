from pathlib import Path
from flask import Flask, abort, render_template, send_from_directory
from sqlalchemy import text
from sqlalchemy.engine import make_url
from werkzeug.middleware.proxy_fix import ProxyFix
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
        raise RuntimeError('Set SECRET_KEY; no insecure default is supplied.')
    if app.config.get('TRUST_PROXY'):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
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
    from app.common.csrf import init_csrf
    from app.subject_routes import subjects_bp
    from app.admin.read_routes import admin_read_bp
    from app.auth.routes import auth_bp
    from app.library.routes import library_bp
    from app.admin.routes import admin_bp
    from app.seed.import_excel import seed_command, import_command
    register_errors(app)
    init_csrf(app)
    for blueprint in (subjects_bp, admin_read_bp, auth_bp, library_bp, admin_bp):
        app.register_blueprint(blueprint)
    app.cli.add_command(seed_command)
    app.cli.add_command(import_command)

    @app.get('/')
    def home_page():
        return render_template('index.html')

    @app.get('/static/<path:filename>', endpoint='static')
    def static_files(filename):
        parts = Path(filename).parts
        if len(parts) < 2 or '..' in parts or chr(92) in filename or parts[0] not in {'asset','fonts','images','js','vendor','pdf'}:
            abort(404)
        return send_from_directory(ROOT / parts[0], '/'.join(parts[1:]))

    @app.get('/health')
    def health():
        try:
            db.session.execute(text('SELECT 1'))
        except Exception:
            db.session.rollback()
            return {'status': 'unavailable'}, 503
        return {'status': 'ok'}, 200
    return app
