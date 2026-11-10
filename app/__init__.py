from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory

from app.common.csrf import init_csrf
from app.common.errors import register_error_handlers
from app.common.model_registry import load_available_models
from app.common.responses import success_response
from app.extensions import db, migrate


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder=None,
    )

    app.config.from_object("config.Config")

    db.init_app(app)
    load_available_models()
    migrate.init_app(app, db)
    init_csrf(app)
    register_error_handlers(app)

    # Importing the blueprints here keeps route registration in one place.
    from app.auth.routes import auth_bp
    from app.library.routes import library_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(admin_bp)

    @app.get("/")
    def home_page():
        return render_template("index.html")

    @app.get("/static/<path:filename>", endpoint="static")
    def static_files(filename):
        # The project keeps assets in root-level folders. Only expose those
        # folders, never source code, configuration, or the database file.
        allowed_roots = {"asset", "fonts", "images", "js", "vendor", "pdf"}
        parts = Path(filename).parts
        if not parts or parts[0] not in allowed_roots:
            abort(404)
        return send_from_directory(Path(app.root_path).parent, filename)

    @app.get("/health")
    def health_check():
        return success_response(
            data={"service": "adaptive-exam"},
            message="Ứng dụng đang hoạt động",
        )

    return app
