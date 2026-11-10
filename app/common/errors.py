from flask import current_app, request
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.common.model_registry import DatabaseModelsPending
from app.common.responses import error_response


def register_errors(app):
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return error_response(error.description, status=400)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            return error_response(error.description, status=error.code or 500)
        return error

    @app.errorhandler(DatabaseModelsPending)
    def handle_pending_models(error):
        return error_response(str(error), status=503)

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        current_app.logger.exception("Database request failed", exc_info=error)
        message = 'Database chưa sẵn sàng. Hãy kiểm tra DATABASE_URL, khởi động database và chạy migration.'
        if request.path.startswith("/api/"):
            return error_response(message, status=503)
        return message, 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        current_app.logger.exception("Unhandled request error", exc_info=error)
        if request.path.startswith("/api/"):
            return error_response('Lỗi máy chủ.', status=500)
        return 'Đã xảy ra lỗi máy chủ.', 500
