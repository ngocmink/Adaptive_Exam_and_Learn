from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory
from sqlalchemy.engine import make_url

from config import Config, ROOT, environment_config
from app.extensions import csrf, db, login_manager, migrate


def create_app(test_config=None):
    app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=None)
    app.config.from_object(Config)
    app.config.update(environment_config())
    if test_config:
        app.config.update(test_config)

    database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not database_url or make_url(database_url).get_backend_name() != "postgresql":
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL.")
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Set SECRET_KEY in .env; no insecure default is supplied.")

    db.init_app(app)
    from app import models

    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(models.User, int(user_id))
        except (TypeError, ValueError):
            return None

    from app.common.csrf import init_csrf
    from app.common.errors import register_errors
    from app.auth.routes import auth_bp
    from app.library.routes import library_bp
    from app.admin.routes import admin_bp
    from app.subject_routes import subjects_bp
    from app.admin.read_routes import admin_read_bp
    from app.seed.import_excel import seed_command, import_command

    init_csrf(app)
    register_errors(app)
    app.register_blueprint(subjects_bp)
    app.register_blueprint(admin_read_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(admin_bp)
    app.cli.add_command(seed_command)
    app.cli.add_command(import_command)

    @app.get("/")
    def home_page():
        return render_template("index.html")

    @app.get("/static/<path:filename>", endpoint="static")
    def static_files(filename):
        allowed_roots = {"asset", "fonts", "images", "js", "vendor", "pdf"}
        parts = Path(filename).parts
        if not parts or parts[0] not in allowed_roots:
            abort(404)
        return send_from_directory(ROOT, filename)

    @app.get("/health")
    def health_check():
        from app.common.responses import success_response

        return success_response(
            data={"service": "adaptive-exam"},
            message="Ứng dụng đang hoạt động",
        )

    return app
