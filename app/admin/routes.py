from flask import Blueprint, g, render_template, request
from sqlalchemy import delete, select
from urllib.parse import urlparse

from app.common.decorators import role_required
from app.common.model_registry import get_model
from app.common.pagination import get_page_args, pagination_data
from app.common.responses import error_response, success_response
from app.extensions import db
from app.library.routes import _material_data


admin_bp = Blueprint("admin", __name__)
MANAGER_ROLES = ["admin", "teacher"]
from app.common.difficulty import parse_difficulty
ASSESSMENT_TYPES = {"quiz", "exam", "practice"}


@admin_bp.get("/admin")
@role_required(MANAGER_ROLES)
def admin_page():
    return render_template("admin_dashboard.html", user=g.current_user)


def _body():
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


def _required_text(body, key, max_length=None):
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} là trường bắt buộc.".format(key))
    value = value.strip()
    if max_length and len(value) > max_length:
        raise ValueError("{} không được dài quá {} ký tự.".format(key, max_length))
    return value


def _validate_file_url(value):
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    if not parsed.scheme and value.startswith("/static/"):
        return value
    raise ValueError("file_url phải là URL http(s) hoặc đường dẫn /static/ an toàn.")


def _validate_options(options):
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError("Câu hỏi phải có đúng 4 options.")
    if any(not isinstance(item, dict) or not str(item.get("content", "")).strip() for item in options):
        raise ValueError("Mỗi option phải có nội dung.")
    if sum(item.get("is_correct") is True for item in options) != 1:
        raise ValueError("Phải chọn chính xác một đáp án đúng.")


def _question_data(question, options):
    return {
        "id": question.id,
        "subject_id": question.subject_id,
        "topic": question.topic,
        "content": question.content,
        "difficulty": float(question.difficulty),
        "explanation": question.explanation,
        "is_active": question.is_active,
        "options": [
            {"id": item.id, "content": item.content, "is_correct": item.is_correct}
            for item in options
        ],
    }


def _assessment_question_ids(assessment_id, AssessmentQuestion):
    rows = db.session.scalars(
        select(AssessmentQuestion.question_id)
        .where(AssessmentQuestion.assessment_id == assessment_id)
        .order_by(AssessmentQuestion.order_num)
    ).all()
    return list(rows)




@admin_bp.post("/api/admin/materials")
@role_required(MANAGER_ROLES)
def create_material():
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Material = get_model("Material")
        title = _required_text(body, "title", 200)
        file_url = _validate_file_url(_required_text(body, "file_url", 500))
        difficulty = parse_difficulty(body.get("difficulty", 5.5))
        subject_id = int(body.get("subject_id"))
    except (ValueError, TypeError) as exc:
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    material = Material(
        subject_id=subject_id,
        title=title,
        description=body.get("description"),
        file_url=file_url,
        difficulty=difficulty,
        author_id=g.current_user.id,
        is_active=True,
    )
    try:
        db.session.add(material)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response("Không thể tạo tài liệu; hãy kiểm tra subject_id.", status=400)
    return success_response(_material_data(material), "Đã tạo tài liệu.", status=201)


@admin_bp.put("/api/admin/materials/<int:material_id>")
@role_required(MANAGER_ROLES)
def update_material(material_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Material = get_model("Material")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    material = db.session.get(Material, material_id)
    if material is None:
        return error_response("Không tìm thấy tài liệu.", status=404)

    try:
        if "title" in body:
            material.title = _required_text(body, "title", 200)
        if "file_url" in body:
            material.file_url = _validate_file_url(_required_text(body, "file_url", 500))
        if "description" in body:
            material.description = body["description"]
        if "subject_id" in body:
            material.subject_id = int(body["subject_id"])
        if "difficulty" in body:
            difficulty = parse_difficulty(body["difficulty"])
            material.difficulty = difficulty
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể cập nhật tài liệu.", status=400)
    return success_response(_material_data(material), "Đã cập nhật tài liệu.")


@admin_bp.delete("/api/admin/materials/<int:material_id>")
@role_required(MANAGER_ROLES)
def disable_material(material_id):
    try:
        Material = get_model("Material")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    material = db.session.get(Material, material_id)
    if material is None:
        return error_response("Không tìm thấy tài liệu.", status=404)
    material.is_active = False
    db.session.commit()
    return success_response({"id": material.id, "is_active": False}, "Đã ẩn tài liệu.")






@admin_bp.post("/api/admin/questions")
@role_required(MANAGER_ROLES)
def create_question():
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Question = get_model("Question")
        QuestionOption = get_model("QuestionOption")
        content = _required_text(body, "content")
        difficulty = parse_difficulty(body.get("difficulty", 5.5))
        _validate_options(body.get("options"))
        question = Question(
            subject_id=int(body.get("subject_id")),
            topic=str(body.get("topic", "")).strip() or None,
            content=content,
            difficulty=difficulty,
            explanation=body.get("explanation"),
            is_active=True,
        )
        db.session.add(question)
        db.session.flush()
        options = [
            QuestionOption(
                question_id=question.id,
                content=item["content"].strip(),
                is_correct=item.get("is_correct") is True,
            )
            for item in body["options"]
        ]
        db.session.add_all(options)
        db.session.commit()
    except (ValueError, TypeError, KeyError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        db.session.rollback()
        return error_response(str(exc), status=503)
    except Exception:
        db.session.rollback()
        return error_response("Không thể tạo câu hỏi; hãy kiểm tra subject_id.", status=400)
    return success_response(_question_data(question, options), "Đã tạo câu hỏi.", status=201)


@admin_bp.put("/api/admin/questions/<int:question_id>")
@role_required(MANAGER_ROLES)
def update_question(question_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Question = get_model("Question")
        QuestionOption = get_model("QuestionOption")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    question = db.session.get(Question, question_id)
    if question is None:
        return error_response("Không tìm thấy câu hỏi.", status=404)

    try:
        if "content" in body:
            question.content = _required_text(body, "content")
        for key in ("topic", "explanation"):
            if key in body:
                setattr(question, key, body[key])
        if "subject_id" in body:
            question.subject_id = int(body["subject_id"])
        if "difficulty" in body:
            question.difficulty = parse_difficulty(body["difficulty"])
        if "options" in body:
            _validate_options(body["options"])
            db.session.execute(delete(QuestionOption).where(QuestionOption.question_id == question.id))
            db.session.add_all([
                QuestionOption(
                    question_id=question.id,
                    content=item["content"].strip(),
                    is_correct=item.get("is_correct") is True,
                )
                for item in body["options"]
            ])
        db.session.commit()
    except (ValueError, TypeError, KeyError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể cập nhật câu hỏi.", status=400)

    options = db.session.scalars(
        select(QuestionOption).where(QuestionOption.question_id == question.id)
    ).all()
    return success_response(_question_data(question, options), "Đã cập nhật câu hỏi.")


@admin_bp.delete("/api/admin/questions/<int:question_id>")
@role_required(MANAGER_ROLES)
def disable_question(question_id):
    try:
        Question = get_model("Question")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    question = db.session.get(Question, question_id)
    if question is None:
        return error_response("Không tìm thấy câu hỏi.", status=404)
    question.is_active = False
    db.session.commit()
    return success_response({"id": question.id, "is_active": False}, "Đã ẩn câu hỏi.")


@admin_bp.post("/api/admin/assessments")
@role_required(MANAGER_ROLES)
def create_assessment():
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Assessment = get_model("Assessment")
        AssessmentQuestion = get_model("AssessmentQuestion")
        title = _required_text(body, "title", 200)
        assessment_type = str(body.get("type", "quiz")).lower()
        if assessment_type not in ASSESSMENT_TYPES:
            raise ValueError("type chỉ nhận quiz, exam hoặc practice.")
        question_ids = body.get("question_ids", [])
        if not isinstance(question_ids, list) or len(set(question_ids)) != len(question_ids):
            raise ValueError("question_ids phải là danh sách không trùng.")
        assessment = Assessment(
            subject_id=int(body.get("subject_id")),
            title=title,
            description=body.get("description"),
            type=assessment_type,
            duration_minutes=int(body.get("duration_minutes", 30)),
            pass_score=int(body.get("pass_score", 50)),
            created_by=g.current_user.id,
            is_active=True,
        )
        db.session.add(assessment)
        db.session.flush()
        db.session.add_all([
            AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=int(question_id),
                order_num=index,
                points=1,
            )
            for index, question_id in enumerate(question_ids, start=1)
        ])
        db.session.commit()
    except (ValueError, TypeError, KeyError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        db.session.rollback()
        return error_response(str(exc), status=503)
    except Exception:
        db.session.rollback()
        return error_response("Không thể tạo đề thi; hãy kiểm tra môn học và câu hỏi.", status=400)
    return success_response({"id": assessment.id, "title": assessment.title}, "Đã tạo đề thi.", status=201)


@admin_bp.put("/api/admin/assessments/<int:assessment_id>")
@role_required(MANAGER_ROLES)
def update_assessment(assessment_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Assessment = get_model("Assessment")
        AssessmentQuestion = get_model("AssessmentQuestion")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None:
        return error_response("Không tìm thấy đề thi.", status=404)
    try:
        if "title" in body:
            assessment.title = _required_text(body, "title", 200)
        if "description" in body:
            assessment.description = body["description"]
        for key in ("duration_minutes", "pass_score", "subject_id"):
            if key in body:
                setattr(assessment, key, int(body[key]))
        if "type" in body:
            if body["type"] not in ASSESSMENT_TYPES:
                raise ValueError("type chỉ nhận quiz, exam hoặc practice.")
            assessment.type = body["type"]
        if "question_ids" in body:
            question_ids = body["question_ids"]
            if not isinstance(question_ids, list) or len(set(question_ids)) != len(question_ids):
                raise ValueError("question_ids phải là danh sách không trùng.")
            db.session.execute(
                delete(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment.id)
            )
            db.session.add_all([
                AssessmentQuestion(
                    assessment_id=assessment.id,
                    question_id=int(question_id),
                    order_num=index,
                    points=1,
                )
                for index, question_id in enumerate(question_ids, start=1)
            ])
        db.session.commit()
    except (ValueError, TypeError, KeyError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể cập nhật đề thi.", status=400)
    return success_response({"id": assessment.id, "title": assessment.title}, "Đã cập nhật đề thi.")


@admin_bp.patch("/api/admin/assessments/<int:assessment_id>/toggle-status")
@role_required(MANAGER_ROLES)
def toggle_assessment(assessment_id):
    try:
        Assessment = get_model("Assessment")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None:
        return error_response("Không tìm thấy đề thi.", status=404)
    assessment.is_active = not assessment.is_active
    db.session.commit()
    return success_response(
        {"id": assessment.id, "is_active": assessment.is_active},
        "Đã cập nhật trạng thái đề thi.",
    )
