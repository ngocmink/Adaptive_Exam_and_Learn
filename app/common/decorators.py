from functools import wraps

from flask import g, redirect, request, session, url_for

from app.common.responses import error_response
from app.extensions import db
from app.models.user import User


def get_current_user():
    """Load the signed-in user from the database for this request."""
    user_id = session.get("user_id")
    if user_id is None:
        return None

    if getattr(g, "current_user_loaded", False):
        return g.current_user

    g.current_user = db.session.get(User, user_id)
    g.current_user_loaded = True
    return g.current_user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            if not request.path.startswith("/api/"):
                return redirect(url_for("auth.login_page"))
            return error_response("Vui lòng đăng nhập.", status=401)
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def role_required(allowed_roles):
    allowed_roles = set(allowed_roles)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if user is None:
                if not request.path.startswith("/api/"):
                    return redirect(url_for("auth.login_page"))
                return error_response("Vui lòng đăng nhập.", status=401)
            if user.role not in allowed_roles:
                if not request.path.startswith("/api/"):
                    return redirect(url_for("library.learner_page"))
                return error_response("Bạn không có quyền thực hiện thao tác này.", status=403)
            g.current_user = user
            return view(*args, **kwargs)

        return wrapped

    return decorator
