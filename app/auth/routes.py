import re

from flask import Blueprint, g, render_template, request, session
from sqlalchemy import select

from app.common.decorators import login_required
from app.common.responses import error_response, success_response
from app.extensions import db
from app.models.user import User


auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
STUDY_TYPES = {"visual", "auditory", "reading", "kinesthetic"}


@auth_bp.get("/login")
def login_page():
    return render_template("login.html")


@auth_bp.get("/register")
def register_page():
    return render_template("register.html")


@auth_bp.get("/api/csrf")
def csrf_token_api():
    from app.common.csrf import csrf_token

    return success_response({"csrf_token": csrf_token()})


def _json_body():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _user_data(user):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "study_type": user.study_type,
    }


@auth_bp.post("/api/auth/register")
def register():
    payload = _json_body()
    if payload is None:
        return error_response("Request body phải là JSON.", status=400)

    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    full_name = str(payload.get("full_name", "")).strip()
    phone = str(payload.get("phone", "")).strip() or None
    study_type = str(payload.get("study_type", "")).strip().lower() or None

    if not EMAIL_RE.fullmatch(email):
        return error_response("Email không hợp lệ.", status=400)
    if len(password) < 6:
        return error_response("Mật khẩu cần có ít nhất 6 ký tự.", status=400)
    if not full_name:
        return error_response("Vui lòng nhập họ tên.", status=400)
    if study_type and study_type not in STUDY_TYPES:
        return error_response("Phong cách học tập không hợp lệ.", status=400)

    existing = db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return error_response("Email đã được sử dụng.", status=409)

    user = User(email=email, full_name=full_name, phone=phone, study_type=study_type, role="student")
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response("Không thể tạo tài khoản lúc này.", status=500)

    return success_response(_user_data(user), "Đăng ký thành công.", status=201)


@auth_bp.post("/api/auth/login")
def login():
    payload = _json_body()
    if payload is None:
        return error_response("Request body phải là JSON.", status=400)

    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None or not user.check_password(password):
        return error_response("Email hoặc mật khẩu không đúng.", status=401)

    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role

    redirect_url = "/admin" if user.role in {"admin", "teacher"} else "/account"
    return success_response(
        {"user": _user_data(user), "redirect_url": redirect_url},
        "Đăng nhập thành công.",
    )


@auth_bp.post("/api/auth/logout")
def logout():
    session.clear()
    return success_response(message="Đăng xuất thành công.")


@auth_bp.get("/api/auth/me")
@login_required
def me():
    return success_response(_user_data(g.current_user))
