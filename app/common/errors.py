from werkzeug.exceptions import HTTPException
from flask_wtf.csrf import CSRFError
from app.common.responses import error_response

def register_errors(app):
    @app.errorhandler(HTTPException)
    def http_error(error):
        return error_response(error.description, error.code)

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return error_response(error.description, 400)
