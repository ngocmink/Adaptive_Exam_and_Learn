"""Dev A read-route guard; Dev B's decorators.py remains untouched."""
from functools import wraps
from flask import session
from flask_login import current_user
from app.extensions import db
from app.models import User
from app.common.responses import error_response

def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        # Re-read the database role; never trust session['role'].
        user_id = current_user.get_id() if current_user.is_authenticated else session.get('user_id')
        try:
            user = db.session.get(User, int(user_id)) if user_id is not None else None
        except (ValueError, TypeError):
            user = None
        if user is None:
            return error_response('Authentication required.', 401)
        if user.role not in ('admin', 'teacher'):
            return error_response('Admin or teacher permission required.', 403)
        return view(*args, **kwargs)
    return wrapped
