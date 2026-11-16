from flask import Blueprint, g, redirect, render_template, request, url_for
from sqlalchemy import func, or_, select

from app.common.decorators import login_required
from app.common.difficulty import parse_difficulty
from app.common.model_registry import get_model
from app.common.pagination import get_page_args, pagination_data
from app.common.responses import error_response, success_response
from app.extensions import db
from app.models.schema import utcnow
from app.common.material_storage import StorageError, create_pdf_url, legacy_pdf_url, private_response


library_bp = Blueprint("library", __name__)


@library_bp.get("/account")
@login_required
def learner_page():
    return render_template("account.html", user=g.current_user)


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


@library_bp.get("/api/materials/<int:material_id>/file")
@private_response
@login_required
def material_file(material_id):
    Material = get_model("Material")
    material = db.session.get(Material, material_id)
    # Current library policy: every signed-in role may read active content.
    if material is None or not material.is_active or not material.subject.is_active:
        return error_response("Material not found.", status=404)
    try:
        if material.storage_path:
            target = create_pdf_url(material.storage_bucket, material.storage_path)
        else:
            target = legacy_pdf_url(material.file_url)
    except StorageError as error:
        return error_response(str(error), status=error.status)
    except ValueError:
        return error_response("Invalid material storage location.", status=404)
    return redirect(target)


@library_bp.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz_page():
    try:
        assessment_id = int(request.args.get("id", ""))
        Assessment = get_model("Assessment")
        Attempt = get_model("Attempt")
        AttemptAnswer = get_model("AttemptAnswer")
    except (ValueError, TypeError):
        return error_response("Thiếu hoặc sai mã đề thi.", status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None or not assessment.is_active:
        return error_response("Không tìm thấy đề thi.", status=404)

    aqs = sorted(
        [aq for aq in assessment.assessment_questions if aq.question and aq.question.is_active],
        key=lambda item: item.order_num,
    )

    if request.method == "POST":
        now = utcnow()
        attempt = Attempt(
            user_id=g.current_user.id,
            assessment_id=assessment.id,
            total_questions=len(aqs),
            correct_answers=0,
            score=0.0,
            start_time=now,
            submit_time=now,
            status="completed",
        )
        db.session.add(attempt)
        db.session.flush()

        correct_count = 0
        total_points = sum(aq.points for aq in aqs) or float(len(aqs)) or 1.0
        earned_points = 0.0

        for aq in aqs:
            q = aq.question
            selected_str = request.form.get(f"question_{q.id}")
            selected_option_id = None
            is_correct = False
            if selected_str:
                try:
                    selected_val = int(selected_str)
                    matching_opt = next((opt for opt in q.options if opt.id == selected_val), None)
                    if matching_opt:
                        selected_option_id = matching_opt.id
                        is_correct = bool(matching_opt.is_correct)
                except (ValueError, TypeError):
                    pass

            if is_correct:
                correct_count += 1
                earned_points += aq.points

            db.session.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    question_id=q.id,
                    selected_option_id=selected_option_id,
                    is_correct=is_correct,
                )
            )

        attempt.correct_answers = correct_count
        score_percent = round((earned_points / total_points) * 100, 1)
        attempt.score = score_percent
        db.session.commit()

        return redirect(url_for("library.quiz_results", attempt_id=attempt.id))

    return render_template(
        "quiz.html",
        assessment=assessment,
        aqs=aqs,
        user=g.current_user,
    )


@library_bp.get("/quiz/results")
@login_required
def quiz_results():
    try:
        attempt_id = int(request.args.get("attempt_id", ""))
        Attempt = get_model("Attempt")
        Assessment = get_model("Assessment")
        AttemptAnswer = get_model("AttemptAnswer")
    except (ValueError, TypeError):
        return error_response("Thiếu hoặc sai mã kết quả làm bài.", status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    attempt = db.session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != g.current_user.id:
        return error_response("Không tìm thấy kết quả làm bài.", status=404)

    assessment = db.session.get(Assessment, attempt.assessment_id)
    if assessment is None:
        return error_response("Không tìm thấy đề thi tương ứng.", status=404)

    aqs = sorted(
        [aq for aq in assessment.assessment_questions if aq.question and aq.question.is_active],
        key=lambda item: item.order_num,
    )
    answers = db.session.scalars(
        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
    ).all()
    answer_map = {ans.question_id: ans for ans in answers}

    review_list = []
    for aq in aqs:
        q = aq.question
        user_ans = answer_map.get(q.id)
        selected_id = user_ans.selected_option_id if user_ans else None
        is_ans_correct = user_ans.is_correct if user_ans else False
        correct_option = next((opt for opt in q.options if opt.is_correct), None)
        selected_option = next((opt for opt in q.options if opt.id == selected_id), None)

        review_list.append({
            "order_num": aq.order_num,
            "question": q,
            "points": aq.points,
            "selected_option": selected_option,
            "correct_option": correct_option,
            "is_correct": is_ans_correct,
            "explanation": q.explanation,
        })

    is_passed = (attempt.score or 0.0) >= assessment.pass_score

    return render_template(
        "results.html",
        assessment=assessment,
        attempt=attempt,
        is_passed=is_passed,
        review_list=review_list,
        user=g.current_user,
    )


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
        "storage_bucket": material.storage_bucket,
        "storage_path": material.storage_path,
        "file_endpoint": url_for("library.material_file", material_id=material.id),
        "difficulty": float(material.difficulty),
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
            stmt = stmt.where(
                func.unaccent(Material.title).ilike(func.unaccent("%{}%".format(search)))
            )

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
                    func.unaccent(Assessment.title).ilike(
                        func.unaccent("%{}%".format(search))
                    ),
                    func.unaccent(func.coalesce(Assessment.description, "")).ilike(
                        func.unaccent("%{}%".format(search))
                    ),
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
