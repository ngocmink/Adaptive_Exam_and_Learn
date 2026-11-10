from flask import Blueprint, g, render_template, request
from sqlalchemy import func, or_, select

from app.common.decorators import login_required
from app.common.difficulty import parse_difficulty
from app.common.model_registry import get_model
from app.common.pagination import get_page_args, pagination_data
from app.common.responses import error_response, success_response
from app.extensions import db


library_bp = Blueprint("library", __name__)


@library_bp.get("/account")
@login_required
def learner_page():
    return render_template("library.html", user=g.current_user)


@library_bp.get("/reading")
@login_required
def reading_page():
    try:
        material_id = int(request.args.get("id", ""))
        Material = get_model("Material")
    except ValueError:
        return error_response("Thiếu hoặc sai mã tài liệu.", status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    material = db.session.get(Material, material_id)
    if material is None or not material.is_active:
        return error_response("Không tìm thấy tài liệu.", status=404)
    return render_template("material_reader.html", material=material, user=g.current_user)


def _as_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("{} phải là số nguyên.".format(field_name)) from None


def _material_data(material):
    subject = getattr(material, "subject", None)
    return {
        "id": material.id,
        "subject_id": material.subject_id,
        "subject_name": getattr(subject, "name", None),
        "title": material.title,
        "description": material.description,
        "file_url": material.file_url,
        "difficulty": float(material.difficulty),
        "author_id": material.author_id,
        "is_active": material.is_active,
    }


def _assessment_data(assessment, question_count):
    subject = getattr(assessment, "subject", None)
    return {
        "id": assessment.id,
        "subject_id": assessment.subject_id,
        "subject_name": getattr(subject, "name", None),
        "title": assessment.title,
        "description": assessment.description,
        "type": assessment.type,
        "duration_minutes": assessment.duration_minutes,
        "pass_score": assessment.pass_score,
        "question_count": question_count,
    }


@library_bp.get("/api/materials")
def list_materials():
    try:
        Material = get_model("Material")
        page, limit = get_page_args()
        stmt = select(Material).where(Material.is_active.is_(True))

        search = request.args.get("search", "").strip()
        if search:
            stmt = stmt.where(Material.title.ilike("%{}%".format(search)))

        subject_id = request.args.get("subject_id")
        if subject_id:
            stmt = stmt.where(Material.subject_id == _as_int(subject_id, "subject_id"))

        difficulty = request.args.get("difficulty", "").strip().lower()
        if difficulty:
            stmt = stmt.where(Material.difficulty == parse_difficulty(difficulty))

        stmt = stmt.order_by(Material.id.desc())
        result = db.paginate(stmt, page=page, per_page=limit, error_out=False)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    return success_response(
        [_material_data(item) for item in result.items],
        pagination=pagination_data(result),
    )


@library_bp.get("/api/materials/<int:material_id>")
def material_detail(material_id):
    try:
        Material = get_model("Material")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    material = db.session.get(Material, material_id)
    if material is None or not material.is_active:
        return error_response("Không tìm thấy tài liệu.", status=404)
    return success_response(_material_data(material))


@library_bp.get("/api/assessments")
def list_assessments():
    try:
        Assessment = get_model("Assessment")
        AssessmentQuestion = get_model("AssessmentQuestion")
        page, limit = get_page_args()
        stmt = select(Assessment).where(Assessment.is_active.is_(True))

        search = request.args.get("search", "").strip()
        if search:
            stmt = stmt.where(
                or_(
                    Assessment.title.ilike("%{}%".format(search)),
                    Assessment.description.ilike("%{}%".format(search)),
                )
            )

        subject_id = request.args.get("subject_id")
        if subject_id:
            stmt = stmt.where(Assessment.subject_id == _as_int(subject_id, "subject_id"))

        assessment_type = request.args.get("type", "").strip().lower()
        if assessment_type:
            if assessment_type not in {"quiz", "exam", "practice"}:
                return error_response("type không hợp lệ.", status=400)
            stmt = stmt.where(Assessment.type == assessment_type)

        stmt = stmt.order_by(Assessment.id.desc())
        result = db.paginate(stmt, page=page, per_page=limit, error_out=False)
        data = []
        for assessment in result.items:
            count = db.session.scalar(
                select(func.count(AssessmentQuestion.id)).where(
                    AssessmentQuestion.assessment_id == assessment.id
                )
            )
            data.append(_assessment_data(assessment, count or 0))
    except ValueError as exc:
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    return success_response(data, pagination=pagination_data(result))


@library_bp.get("/api/assessments/<int:assessment_id>")
def assessment_detail(assessment_id):
    try:
        Assessment = get_model("Assessment")
        AssessmentQuestion = get_model("AssessmentQuestion")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None or not assessment.is_active:
        return error_response("Không tìm thấy đề thi.", status=404)

    question_count = db.session.scalar(
        select(func.count(AssessmentQuestion.id)).where(
            AssessmentQuestion.assessment_id == assessment.id
        )
    )
    # Public detail deliberately excludes question text and correct answers.
    return success_response(_assessment_data(assessment, question_count or 0))
