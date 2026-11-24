from datetime import timedelta, timezone

from flask import Blueprint, g, redirect, render_template, request, url_for
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.common.decorators import login_required
from app.common.difficulty import parse_difficulty
from app.common.material_storage import StorageError, create_pdf_url, legacy_pdf_url, private_response
from app.common.model_registry import get_model
from app.common.pagination import get_page_args, pagination_data
from app.common.responses import error_response, success_response
from app.extensions import db
from app.models.schema import utcnow


library_bp = Blueprint("library", __name__)


def _ensure_utc(dt):
    if dt is None:
        return utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _assessment_active_questions(assessment):
    return sorted(
        [aq for aq in assessment.assessment_questions if aq.question and aq.question.is_active],
        key=lambda item: item.order_num,
    )


def _attempt_deadline(attempt, assessment):
    return _ensure_utc(attempt.start_time) + timedelta(minutes=assessment.duration_minutes)


def _grade_and_finalize_attempt(attempt, assessment, answers_payload=None, now=None):
    if attempt.status == "completed":
        return attempt

    AttemptAnswer = get_model("AttemptAnswer")
    aqs = _assessment_active_questions(assessment)
    existing_answers = db.session.scalars(
        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
    ).all()
    answer_map = {ans.question_id: ans for ans in existing_answers}

    if answers_payload:
        aq_by_qid = {aq.question.id: aq.question for aq in aqs}
        for qid, opt_id in answers_payload.items():
            q = aq_by_qid.get(qid)
            if q is None:
                continue
            valid_opt_id = None
            if opt_id is not None:
                matching = next((opt for opt in q.options if opt.id == opt_id), None)
                if matching is not None:
                    valid_opt_id = matching.id
            ans_row = answer_map.get(qid)
            if ans_row is None:
                ans_row = AttemptAnswer(
                    attempt_id=attempt.id,
                    question_id=qid,
                    selected_option_id=valid_opt_id,
                    is_correct=None,
                )
                db.session.add(ans_row)
                answer_map[qid] = ans_row
            else:
                ans_row.selected_option_id = valid_opt_id

    correct_count = 0
    total_points = sum(aq.points for aq in aqs) or float(len(aqs)) or 1.0
    earned_points = 0.0

    for aq in aqs:
        q = aq.question
        ans_row = answer_map.get(q.id)
        if ans_row is None:
            ans_row = AttemptAnswer(
                attempt_id=attempt.id,
                question_id=q.id,
                selected_option_id=None,
                is_correct=False,
            )
            db.session.add(ans_row)
            answer_map[q.id] = ans_row
        is_correct = False
        if ans_row.selected_option_id is not None:
            matching_opt = next(
                (opt for opt in q.options if opt.id == ans_row.selected_option_id), None
            )
            if matching_opt and matching_opt.is_correct:
                is_correct = True
        ans_row.is_correct = is_correct
        if is_correct:
            correct_count += 1
            earned_points += aq.points

    attempt.total_questions = len(aqs)
    attempt.correct_answers = correct_count
    attempt.score = round((earned_points / total_points) * 100, 1) if aqs else 0.0
    attempt.status = "completed"
    current_time = _ensure_utc(now or utcnow())
    start_utc = _ensure_utc(attempt.start_time)
    attempt.submit_time = current_time if current_time >= start_utc else start_utc
    db.session.commit()
    return attempt


def _finalize_expired_user_attempts(user_id):
    Attempt = get_model("Attempt")
    Assessment = get_model("Assessment")
    in_progress = db.session.scalars(
        select(Attempt).where(Attempt.user_id == user_id, Attempt.status == "in_progress")
    ).all()
    if not in_progress:
        return
    now = utcnow()
    for att in in_progress:
        assess = db.session.get(Assessment, att.assessment_id)
        if assess is None:
            continue
        deadline = _attempt_deadline(att, assess)
        if now >= deadline:
            _grade_and_finalize_attempt(att, assess, now=deadline)


def finalize_all_expired_attempts():
    Attempt = get_model("Attempt")
    Assessment = get_model("Assessment")
    in_progress = db.session.scalars(
        select(Attempt).where(Attempt.status == "in_progress")
    ).all()
    if not in_progress:
        return 0
    now = utcnow()
    finalized = 0
    for att in in_progress:
        assess = db.session.get(Assessment, att.assessment_id)
        if assess is None:
            continue
        deadline = _attempt_deadline(att, assess)
        if now >= deadline:
            _grade_and_finalize_attempt(att, assess, now=deadline)
            finalized += 1
    return finalized


@library_bp.get("/account")
@login_required
def learner_page():
    return render_template("account.html", user=g.current_user)


@library_bp.get("/history")
@login_required
def history_page():
    return render_template("history.html", user=g.current_user)


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
    if material is None or not material.is_active or not material.subject or not material.subject.is_active:
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
    if assessment is None or not assessment.is_active or not assessment.subject or not assessment.subject.is_active:
        return error_response("Không tìm thấy đề thi.", status=404)

    aqs = _assessment_active_questions(assessment)

    if request.method == "POST":
        form_attempt_id = request.form.get("attempt_id")
        attempt = None
        if form_attempt_id:
            try:
                candidate = db.session.get(Attempt, int(form_attempt_id))
                if (
                    candidate is not None
                    and candidate.user_id == g.current_user.id
                    and candidate.assessment_id == assessment.id
                ):
                    attempt = candidate
            except (ValueError, TypeError):
                attempt = None

        if attempt is None:
            attempt = db.session.scalar(
                select(Attempt)
                .where(
                    Attempt.user_id == g.current_user.id,
                    Attempt.assessment_id == assessment.id,
                    Attempt.status == "in_progress",
                )
                .order_by(Attempt.id.desc())
            )

        if attempt is not None and attempt.status == "completed":
            return redirect(url_for("library.quiz_results", attempt_id=attempt.id))

        now = utcnow()
        if attempt is None or attempt.status != "in_progress":
            attempt = Attempt(
                user_id=g.current_user.id,
                assessment_id=assessment.id,
                total_questions=len(aqs),
                correct_answers=0,
                score=None,
                start_time=now,
                status="in_progress",
            )
            db.session.add(attempt)
            db.session.flush()

        deadline = _attempt_deadline(attempt, assessment)
        if now > deadline:
            _grade_and_finalize_attempt(attempt, assessment, answers_payload=None, now=deadline)
            return redirect(url_for("library.quiz_results", attempt_id=attempt.id, auto_submitted=1))

        answers_payload = {}
        for aq in aqs:
            q = aq.question
            selected_str = request.form.get(f"question_{q.id}")
            if selected_str:
                try:
                    answers_payload[q.id] = int(selected_str)
                except (ValueError, TypeError):
                    pass

        _grade_and_finalize_attempt(attempt, assessment, answers_payload=answers_payload)
        return redirect(url_for("library.quiz_results", attempt_id=attempt.id))

    retake = request.args.get("retake") == "1"
    attempt = db.session.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == g.current_user.id,
            Attempt.assessment_id == assessment.id,
            Attempt.status == "in_progress",
        )
        .order_by(Attempt.id.desc())
    )

    now = utcnow()
    if attempt is not None:
        deadline = _attempt_deadline(attempt, assessment)
        if now >= deadline:
            _grade_and_finalize_attempt(attempt, assessment, now=deadline)
            if not retake:
                return redirect(
                    url_for("library.quiz_results", attempt_id=attempt.id, auto_submitted=1)
                )
            attempt = None
        elif retake:
            attempt.status = "abandoned"
            start_utc = _ensure_utc(attempt.start_time)
            attempt.submit_time = now if now >= start_utc else start_utc
            db.session.commit()
            attempt = None

    if attempt is None and aqs:
        attempt = Attempt(
            user_id=g.current_user.id,
            assessment_id=assessment.id,
            total_questions=len(aqs),
            correct_answers=0,
            score=None,
            start_time=now,
            status="in_progress",
        )
        db.session.add(attempt)
        db.session.commit()

    saved_answers = {}
    remaining_seconds = assessment.duration_minutes * 60
    deadline_iso = None
    if attempt is not None:
        rows = db.session.scalars(
            select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
        ).all()
        saved_answers = {
            row.question_id: row.selected_option_id
            for row in rows
            if row.selected_option_id is not None
        }
        deadline = _attempt_deadline(attempt, assessment)
        remaining_seconds = max(0, int((deadline - utcnow()).total_seconds()))
        deadline_iso = deadline.isoformat()

    return render_template(
        "quiz.html",
        assessment=assessment,
        aqs=aqs,
        user=g.current_user,
        attempt=attempt,
        saved_answers=saved_answers,
        remaining_seconds=remaining_seconds,
        deadline_iso=deadline_iso,
    )


@library_bp.post("/api/attempts/<int:attempt_id>/answers")
@login_required
def save_attempt_answers(attempt_id):
    try:
        Attempt = get_model("Attempt")
        Assessment = get_model("Assessment")
        AttemptAnswer = get_model("AttemptAnswer")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    attempt = db.session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != g.current_user.id:
        return error_response("Không tìm thấy phiên làm bài.", status=404)

    if attempt.status == "completed":
        return error_response(
            "Bài thi đã được nộp.",
            status=409,
            data={"redirect_url": url_for("library.quiz_results", attempt_id=attempt.id)},
        )
    if attempt.status != "in_progress":
        return error_response("Phiên làm bài không còn hiệu lực.", status=400)

    assessment = db.session.get(Assessment, attempt.assessment_id)
    if assessment is None:
        return error_response("Không tìm thấy đề thi tương ứng.", status=404)

    now = utcnow()
    deadline = _attempt_deadline(attempt, assessment)
    if now >= deadline:
        _grade_and_finalize_attempt(attempt, assessment, now=deadline)
        return success_response(
            {
                "expired": True,
                "redirect_url": url_for(
                    "library.quiz_results", attempt_id=attempt.id, auto_submitted=1
                ),
            },
            "Đã hết thời gian làm bài, hệ thống đã tự động nộp bài.",
        )

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error_response("Request body phải là JSON.", status=400)

    if "answers" in body and isinstance(body["answers"], list):
        raw_items = body["answers"]
    elif "question_id" in body:
        raw_items = [
            {
                "question_id": body.get("question_id"),
                "selected_option_id": body.get("selected_option_id"),
            }
        ]
    else:
        return error_response("Thiếu dữ liệu câu trả lời.", status=400)

    aqs = _assessment_active_questions(assessment)
    aq_by_qid = {aq.question.id: aq.question for aq in aqs}
    existing_map = {
        row.question_id: row
        for row in db.session.scalars(
            select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
        ).all()
    }

    for item in raw_items:
        if not isinstance(item, dict):
            return error_response("Định dạng đáp án không hợp lệ.", status=400)
        try:
            qid = int(item.get("question_id"))
        except (ValueError, TypeError):
            return error_response("question_id không hợp lệ.", status=400)
        q = aq_by_qid.get(qid)
        if q is None:
            return error_response("Câu hỏi không thuộc đề thi này.", status=400)

        raw_opt = item.get("selected_option_id")
        valid_opt_id = None
        if raw_opt is not None and raw_opt != "":
            try:
                opt_val = int(raw_opt)
            except (ValueError, TypeError):
                return error_response("selected_option_id không hợp lệ.", status=400)
            matching_opt = next((opt for opt in q.options if opt.id == opt_val), None)
            if matching_opt is None:
                return error_response("Đáp án không thuộc câu hỏi này.", status=400)
            valid_opt_id = matching_opt.id

        row = existing_map.get(qid)
        if row is None:
            row = AttemptAnswer(
                attempt_id=attempt.id,
                question_id=qid,
                selected_option_id=valid_opt_id,
                is_correct=None,
            )
            db.session.add(row)
            existing_map[qid] = row
        else:
            row.selected_option_id = valid_opt_id
            row.is_correct = None

    db.session.commit()
    saved_count = sum(1 for row in existing_map.values() if row.selected_option_id is not None)
    remaining_seconds = max(0, int((deadline - utcnow()).total_seconds()))
    return success_response(
        {
            "saved": True,
            "saved_count": saved_count,
            "remaining_seconds": remaining_seconds,
            "saved_at": utcnow().isoformat(),
        },
        "Đã lưu câu trả lời.",
    )


@library_bp.post("/api/attempts/<int:attempt_id>/submit")
@login_required
def submit_attempt(attempt_id):
    try:
        Attempt = get_model("Attempt")
        Assessment = get_model("Assessment")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    attempt = db.session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != g.current_user.id:
        return error_response("Không tìm thấy phiên làm bài.", status=404)

    assessment = db.session.get(Assessment, attempt.assessment_id)
    if assessment is None:
        return error_response("Không tìm thấy đề thi tương ứng.", status=404)

    body = request.get_json(silent=True) or {}
    auto_submitted = bool(body.get("auto_submitted")) if isinstance(body, dict) else False

    if attempt.status == "completed":
        return success_response(
            {
                "attempt_id": attempt.id,
                "score": float(attempt.score or 0.0),
                "correct_answers": attempt.correct_answers,
                "total_questions": attempt.total_questions,
                "is_passed": (attempt.score or 0.0) >= assessment.pass_score,
                "redirect_url": url_for("library.quiz_results", attempt_id=attempt.id),
            },
            "Bài thi đã được nộp trước đó.",
        )
    if attempt.status != "in_progress":
        return error_response("Không thể nộp phiên làm bài này.", status=400)

    now = utcnow()
    deadline = _attempt_deadline(attempt, assessment)
    is_expired = now > deadline

    answers_payload = {}
    if not is_expired and isinstance(body, dict) and isinstance(body.get("answers"), dict):
        for k, v in body["answers"].items():
            try:
                qid = int(k)
                opt_id = int(v) if v is not None and v != "" else None
                answers_payload[qid] = opt_id
            except (ValueError, TypeError):
                pass

    _grade_and_finalize_attempt(
        attempt,
        assessment,
        answers_payload=answers_payload if not is_expired else None,
        now=deadline if is_expired else now,
    )
    redirect_params = {"attempt_id": attempt.id}
    if auto_submitted or is_expired:
        redirect_params["auto_submitted"] = 1

    return success_response(
        {
            "attempt_id": attempt.id,
            "score": float(attempt.score or 0.0),
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "is_passed": (attempt.score or 0.0) >= assessment.pass_score,
            "redirect_url": url_for("library.quiz_results", **redirect_params),
        },
        "Đã nộp bài và chấm điểm thành công.",
    )


@library_bp.get("/quiz/results")
@login_required
def quiz_results():
    try:
        attempt_id = int(request.args.get("attempt_id", ""))
        Attempt = get_model("Attempt")
        Assessment = get_model("Assessment")
        AttemptAnswer = get_model("AttemptAnswer")
        User = get_model("User")
    except (ValueError, TypeError):
        return error_response("Thiếu hoặc sai mã kết quả làm bài.", status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    attempt = db.session.get(Attempt, attempt_id)
    is_staff = g.current_user.role in {"admin", "teacher"}
    if attempt is None or (attempt.user_id != g.current_user.id and not is_staff):
        return error_response("Không tìm thấy kết quả làm bài.", status=404)

    assessment = db.session.get(Assessment, attempt.assessment_id)
    if assessment is None:
        return error_response("Không tìm thấy đề thi tương ứng.", status=404)

    if attempt.status == "in_progress":
        deadline = _attempt_deadline(attempt, assessment)
        if utcnow() >= deadline:
            _grade_and_finalize_attempt(attempt, assessment, now=deadline)
        elif attempt.user_id == g.current_user.id:
            return redirect(url_for("library.quiz_page", id=attempt.assessment_id))

    aqs = _assessment_active_questions(assessment)
    answers = db.session.scalars(
        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
    ).all()
    answer_map = {ans.question_id: ans for ans in answers}

    review_list = []
    unanswered_count = 0
    for aq in aqs:
        q = aq.question
        user_ans = answer_map.get(q.id)
        selected_id = user_ans.selected_option_id if user_ans else None
        is_ans_correct = bool(user_ans.is_correct) if user_ans else False
        is_unanswered = selected_id is None
        if is_unanswered:
            unanswered_count += 1
        correct_option = next((opt for opt in q.options if opt.is_correct), None)
        selected_option = next((opt for opt in q.options if opt.id == selected_id), None)

        review_list.append(
            {
                "order_num": aq.order_num,
                "question": q,
                "options": list(q.options),
                "points": aq.points,
                "selected_option_id": selected_id,
                "selected_option": selected_option,
                "correct_option": correct_option,
                "is_correct": is_ans_correct,
                "is_unanswered": is_unanswered,
                "explanation": q.explanation,
            }
        )

    wrong_count = max(0, len(review_list) - (attempt.correct_answers or 0) - unanswered_count)
    elapsed_seconds = None
    if attempt.start_time and attempt.submit_time:
        elapsed_seconds = max(
            0, int((_ensure_utc(attempt.submit_time) - _ensure_utc(attempt.start_time)).total_seconds())
        )

    is_passed = (attempt.score or 0.0) >= assessment.pass_score
    attempt_user = db.session.get(User, attempt.user_id) or g.current_user

    return render_template(
        "results.html",
        assessment=assessment,
        attempt=attempt,
        attempt_user=attempt_user,
        is_staff_view=(attempt.user_id != g.current_user.id),
        is_passed=is_passed,
        review_list=review_list,
        unanswered_count=unanswered_count,
        wrong_count=wrong_count,
        elapsed_seconds=elapsed_seconds,
        auto_submitted=(request.args.get("auto_submitted") == "1"),
        user=g.current_user,
    )


@library_bp.get("/api/attempts/summary")
@login_required
def my_attempts_summary():
    try:
        Attempt = get_model("Attempt")
        Assessment = get_model("Assessment")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    _finalize_expired_user_attempts(g.current_user.id)

    rows = db.session.execute(
        select(Attempt, Assessment)
        .join(Assessment, Assessment.id == Attempt.assessment_id)
        .where(Attempt.user_id == g.current_user.id)
    ).all()

    total_attempts = len(rows)
    completed = [(a, assess) for a, assess in rows if a.status == "completed"]
    in_progress = sum(1 for a, _ in rows if a.status == "in_progress")
    scores = [float(a.score) for a, _ in completed if a.score is not None]
    average_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    best_score = round(max(scores), 1) if scores else 0.0
    passed_count = sum(
        1 for a, assess in completed if a.score is not None and a.score >= assess.pass_score
    )
    pass_rate = round((passed_count / len(completed)) * 100, 1) if completed else 0.0

    return success_response(
        {
            "total_attempts": total_attempts,
            "completed_attempts": len(completed),
            "in_progress_attempts": in_progress,
            "average_score": average_score,
            "best_score": best_score,
            "passed_count": passed_count,
            "pass_rate": pass_rate,
        }
    )


@library_bp.get("/api/attempts")
@login_required
def list_my_attempts():
    try:
        Attempt = get_model("Attempt")
        Assessment = get_model("Assessment")
        Subject = get_model("Subject")
        _finalize_expired_user_attempts(g.current_user.id)
        page, limit = get_page_args()

        stmt = (
            select(Attempt)
            .join(Assessment, Assessment.id == Attempt.assessment_id)
            .join(Subject, Subject.id == Assessment.subject_id)
            .where(Attempt.user_id == g.current_user.id)
        )

        subject_id = request.args.get("subject_id")
        if subject_id:
            stmt = stmt.where(Assessment.subject_id == _as_int(subject_id, "subject_id"))

        assessment_id = request.args.get("assessment_id")
        if assessment_id:
            stmt = stmt.where(Attempt.assessment_id == _as_int(assessment_id, "assessment_id"))

        status = request.args.get("status", "").strip().lower()
        if status:
            if status not in {"in_progress", "completed", "abandoned"}:
                return error_response("status không hợp lệ.", status=400)
            stmt = stmt.where(Attempt.status == status)

        stmt = stmt.order_by(Attempt.start_time.desc(), Attempt.id.desc())
        result = db.paginate(stmt, page=page, per_page=limit, error_out=False)

        assess_ids = {att.assessment_id for att in result.items}
        assess_map = (
            {
                a.id: a
                for a in db.session.scalars(
                    select(Assessment)
                    .options(selectinload(Assessment.subject))
                    .where(Assessment.id.in_(assess_ids))
                ).all()
            }
            if assess_ids
            else {}
        )

        now = utcnow()
        data = []
        for att in result.items:
            assess = assess_map.get(att.assessment_id)
            subj = assess.subject if assess else None
            if assess is None or subj is None:
                continue
            score_val = float(att.score) if att.score is not None else None
            is_passed = (
                score_val is not None
                and att.status == "completed"
                and score_val >= assess.pass_score
            )
            duration_seconds = None
            if att.start_time and att.submit_time:
                duration_seconds = max(
                    0,
                    int((_ensure_utc(att.submit_time) - _ensure_utc(att.start_time)).total_seconds()),
                )
            remaining_seconds = None
            if att.status == "in_progress":
                remaining_seconds = max(0, int((_attempt_deadline(att, assess) - now).total_seconds()))

            data.append(
                {
                    "id": att.id,
                    "assessment_id": assess.id,
                    "assessment_title": assess.title,
                    "assessment_type": assess.type,
                    "subject_id": subj.id,
                    "subject_name": subj.name,
                    "score": score_val,
                    "pass_score": assess.pass_score,
                    "is_passed": is_passed,
                    "correct_answers": att.correct_answers,
                    "total_questions": att.total_questions,
                    "status": att.status,
                    "start_time": att.start_time.isoformat() if att.start_time else None,
                    "submit_time": att.submit_time.isoformat() if att.submit_time else None,
                    "duration_seconds": duration_seconds,
                    "remaining_seconds": remaining_seconds,
                    "results_url": url_for("library.quiz_results", attempt_id=att.id),
                    "quiz_url": url_for("library.quiz_page", id=assess.id),
                }
            )
    except ValueError as exc:
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    return success_response(data, pagination=pagination_data(result))


def _as_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("{} phải là số nguyên.".format(field_name)) from None


def _material_data(material):
    subject = getattr(material, "subject", None)
    from app.models.hierarchy import Lesson, LessonMaterial

    lms = db.session.scalars(
        select(Lesson)
        .join(LessonMaterial, LessonMaterial.lesson_id == Lesson.id)
        .where(LessonMaterial.material_id == material.id)
        .order_by(Lesson.order_num)
    ).all()

    if material.title and material.title.strip():
        display_title = material.title.strip()
    elif lms:
        if len(lms) == 1:
            display_title = f"{lms[0].code}: {lms[0].title}"
        else:
            codes = " & ".join(
                l.code.split("-")[-1] if idx > 0 else l.code for idx, l in enumerate(lms)
            )
            titles = " & ".join(l.title for l in lms)
            display_title = f"{codes}: {titles}"
    else:
        display_title = "Tài liệu"

    lesson_code = (
        (
            lms[0].code
            if len(lms) == 1
            else " & ".join(
                l.code.split("-")[-1] if idx > 0 else l.code for idx, l in enumerate(lms)
            )
        )
        if lms
        else None
    )

    lesson_title = (
        (lms[0].title if len(lms) == 1 else " & ".join(l.title for l in lms)) if lms else None
    )

    return {
        "id": material.id,
        "subject_id": material.subject_id,
        "subject_name": getattr(subject, "name", None),
        "lesson_code": lesson_code,
        "lesson_title": lesson_title,
        "title": display_title,
        "description": material.description,
        "file_url": material.file_url,
        "storage_bucket": material.storage_bucket,
        "storage_path": material.storage_path,
        "file_endpoint": url_for("library.material_file", material_id=material.id),
        "difficulty": float(material.difficulty),
        "is_active": material.is_active,
    }


def _assessment_data(assessment, question_count, author_name=None):
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
        "author_name": author_name or "Giảng viên VISE",
    }


@library_bp.get("/api/materials")
def list_materials():
    try:
        Material = get_model("Material")
        Subject = get_model("Subject")
        page, limit = get_page_args()
        stmt = (
            select(Material)
            .join(Subject, Subject.id == Material.subject_id)
            .where(Material.is_active.is_(True), Subject.is_active.is_(True))
        )

        search = request.args.get("search", "").strip()
        if search:
            stmt = stmt.where(
                func.unaccent(Material.title).ilike(func.unaccent("%{}%".format(search)))
            )

        subject_id = request.args.get("subject_id")
        if subject_id:
            stmt = stmt.where(Material.subject_id == _as_int(subject_id, "subject_id"))

        lesson_id = request.args.get("lesson_id")
        if lesson_id:
            from app.models.hierarchy import LessonMaterial

            lid = _as_int(lesson_id, "lesson_id")
            stmt = stmt.where(
                Material.id.in_(
                    select(LessonMaterial.material_id).where(LessonMaterial.lesson_id == lid)
                )
            )

        difficulty = request.args.get("difficulty", "").strip().lower()
        if difficulty:
            stmt = stmt.where(Material.difficulty == parse_difficulty(difficulty))

        from app.models.hierarchy import Lesson, LessonMaterial

        stmt = (
            stmt.outerjoin(LessonMaterial, LessonMaterial.material_id == Material.id)
            .outerjoin(Lesson, Lesson.id == LessonMaterial.lesson_id)
            .group_by(Material.id)
            .order_by(func.min(func.coalesce(Lesson.order_num, 9999)).asc(), Material.id.asc())
        )
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
    if material is None or not material.is_active or not material.subject or not material.subject.is_active:
        return error_response("Không tìm thấy tài liệu.", status=404)
    return success_response(_material_data(material))


@library_bp.get("/api/assessments")
def list_assessments():
    try:
        Assessment = get_model("Assessment")
        AssessmentQuestion = get_model("AssessmentQuestion")
        Subject = get_model("Subject")
        User = get_model("User")
        page, limit = get_page_args()
        stmt = (
            select(Assessment)
            .join(Subject, Subject.id == Assessment.subject_id)
            .where(Assessment.is_active.is_(True), Subject.is_active.is_(True))
        )

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

        lesson_id = request.args.get("lesson_id")
        if lesson_id:
            from app.models.hierarchy import QuestionLesson

            lid = _as_int(lesson_id, "lesson_id")
            stmt = stmt.where(
                Assessment.id.in_(
                    select(AssessmentQuestion.assessment_id)
                    .join(QuestionLesson, QuestionLesson.question_id == AssessmentQuestion.question_id)
                    .where(QuestionLesson.lesson_id == lid)
                )
            )

        assessment_type = request.args.get("type", "").strip().lower()
        if assessment_type:
            if assessment_type not in {"quiz", "exam", "practice"}:
                return error_response("type không hợp lệ.", status=400)
            stmt = stmt.where(Assessment.type == assessment_type)

        stmt = stmt.order_by(Assessment.id.asc())
        result = db.paginate(stmt, page=page, per_page=limit, error_out=False)
        creator_ids = {a.created_by for a in result.items if a.created_by is not None}
        author_map = (
            {
                u.id: u.full_name
                for u in db.session.scalars(select(User).where(User.id.in_(creator_ids))).all()
            }
            if creator_ids
            else {}
        )
        data = []
        for assessment in result.items:
            count = db.session.scalar(
                select(func.count(AssessmentQuestion.id)).where(
                    AssessmentQuestion.assessment_id == assessment.id
                )
            )
            data.append(
                _assessment_data(
                    assessment,
                    count or 0,
                    author_map.get(assessment.created_by),
                )
            )
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
        User = get_model("User")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)

    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None or not assessment.is_active or not assessment.subject or not assessment.subject.is_active:
        return error_response("Không tìm thấy đề thi.", status=404)

    question_count = db.session.scalar(
        select(func.count(AssessmentQuestion.id)).where(
            AssessmentQuestion.assessment_id == assessment.id
        )
    )
    author = db.session.get(User, assessment.created_by) if assessment.created_by else None
    # Public detail deliberately excludes question text and correct answers.
    return success_response(
        _assessment_data(assessment, question_count or 0, author.full_name if author else None)
    )
