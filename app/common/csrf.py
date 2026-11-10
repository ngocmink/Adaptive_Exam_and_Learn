"""Use one CSRF implementation for both Jinja forms and JSON APIs."""
from flask import g, session
from flask_wtf.csrf import generate_csrf

def csrf_token():
    # A login rotates the session. Discard any token cached in the current
    # application context when its matching session token no longer exists.
    if not session.get('csrf_token'):
        g.pop('csrf_token', None)
    return generate_csrf()

def init_csrf(app):
    @app.context_processor
    def expose_csrf_token():
        return {'csrf_token': csrf_token}
