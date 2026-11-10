from flask_wtf.csrf import generate_csrf


def csrf_token():
    return generate_csrf()


def init_csrf(app):
    @app.context_processor
    def expose_csrf_token():
        return {"csrf_token": csrf_token}
