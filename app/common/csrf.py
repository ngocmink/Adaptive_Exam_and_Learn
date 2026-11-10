import hmac
import secrets

from flask import abort, request, session


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def init_csrf(app):
    @app.context_processor
    def expose_csrf_token():
        return {"csrf_token": csrf_token}

    @app.before_request
    def protect_mutating_api_requests():
        if not request.path.startswith("/api/") or request.method in SAFE_METHODS:
            return None
        expected = session.get("_csrf_token")
        provided = request.headers.get("X-CSRF-Token", "")
        if not expected or not hmac.compare_digest(expected, provided):
            abort(403, description="CSRF token không hợp lệ hoặc đã hết hạn.")
        return None
