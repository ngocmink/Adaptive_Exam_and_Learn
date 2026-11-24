from datetime import datetime, timedelta, timezone
from flask import Blueprint, request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, NotFound

from app.common.difficulty import parse_difficulty
from app.common.pagination import boolean_arg, paginate, positive_int
from app.common.read_access import staff_required
from app.common.responses import success_response
from app.extensions import db
from app.models import (
    Assessment,
    AssessmentQuestion,
    Attempt,
    Lesson,
    LessonMaterial,
    Material,
    Question,
    QuestionLesson,
    Subject,
    User,
)

admin_read_bp = Blueprint("admin_read", __name__, url_prefix="/api/admin")


def _escape_like(value):
    return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def _unaccent_contains(column, search):
    escaped = _escape_like(search)
    return func.unaccent(column).ilike(func.unaccent(f"%{escaped}%"), escape="!")


def filters(statement, model):
    subject_id = positive_int("subject_id")
    if subject_id is not None:
        statement = statement.where(model.subject_id == subject_id)
    if not boolean_arg("include_inactive"):
        statement = statement.where(model.is_active.is_(True))
    difficulty = request.args.get("difficulty")
    if difficulty is not None and difficulty != "":
        if not hasattr(model, "difficulty"):
            raise BadRequest("This endpoint does not have a difficulty field.")
        try:
            level = parse_difficulty(difficulty)
        except ValueError as error:
            raise BadRequest(str(error)) from error
        statement = statement.where(model.difficulty == level)
    search = request.args.get("search", "").strip()
    if search:
        column = model.content if model is Question else model.title
        statement = statement.where(_unaccent_contains(column, search))
    return statement


def _paginated_response(statement, page, limit, serialize_all):
    result = db.paginate(statement, page=page, per_page=limit, error_out=False)
    return success_response(
        serialize_all(result.items),
        pagination={
            "page": page,
            "limit": limit,
            "total_records": result.total,
            "total_pages": result.pages,
        },
    )


def question_json(q, lesson_ids=None):
    return {
        "id": q.id,
        "subject_id": q.subject_id,
        "subject_name": q.subject.name if q.subject else None,
        "topic": q.topic,
        "content": q.content,
        "difficulty": float(q.difficulty),
        "explanation": q.explanation,
        "is_active": q.is_active,
        "lesson_ids": lesson_ids if lesson_ids is not None else [],
        "options": [
            {"id": o.id, "content": o.content, "is_correct": o.is_correct}
            for o in q.options
        ],
    }


@admin_read_bp.get("/overview")
@staff_required
def overview():
    from app.library.routes import finalize_all_expired_attempts

    finalize_all_expired_attempts()
    subjects_total = db.session.scalar(select(func.count(Subject.id))) or 0
    subjects_active = (
        db.session.scalar(select(func.count(Subject.id)).where(Subject.is_active.is_(True)))
        or 0
    )
    lessons_total = db.session.scalar(select(func.count(Lesson.id))) or 0
    lessons_published = (
        db.session.scalar(select(func.count(Lesson.id)).where(Lesson.status == "published"))
        or 0
    )
    materials_total = db.session.scalar(select(func.count(Material.id))) or 0
    materials_active = (
        db.session.scalar(select(func.count(Material.id)).where(Material.is_active.is_(True)))
        or 0
    )
    questions_total = db.session.scalar(select(func.count(Question.id))) or 0
    questions_active = (
        db.session.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True)))
        or 0
    )
    assessments_total = db.session.scalar(select(func.count(Assessment.id))) or 0
    assessments_active = (
        db.session.scalar(select(func.count(Assessment.id)).where(Assessment.is_active.is_(True)))
        or 0
    )
    users_total = db.session.scalar(select(func.count(User.id))) or 0
    students_total = (
        db.session.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
    )

    attempts_total = db.session.scalar(select(func.count(Attempt.id))) or 0
    completed_attempts = (
        db.session.scalar(select(func.count(Attempt.id)).where(Attempt.status == "completed"))
        or 0
    )
    in_progress_attempts = (
        db.session.scalar(select(func.count(Attempt.id)).where(Attempt.status == "in_progress"))
        or 0
    )
    avg_score_raw = db.session.scalar(
        select(func.avg(Attempt.score)).where(Attempt.status == "completed")
    )
    average_score = round(float(avg_score_raw), 1) if avg_score_raw is not None else 0.0

    passed_count = (
        db.session.scalar(
            select(func.count(Attempt.id))
            .join(Assessment, Assessment.id == Attempt.assessment_id)
            .where(
                Attempt.status == "completed",
                Attempt.score.is_not(None),
                Attempt.score >= Assessment.pass_score,
            )
        )
        or 0
    )
    failed_count = max(0, completed_attempts - passed_count)
    pass_rate = (
        round((passed_count / completed_attempts) * 100, 1)
        if completed_attempts > 0
        else 0.0
    )

    today_utc = datetime.now(timezone.utc).date()
    start_day = today_utc - timedelta(days=6)
    start_dt = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
    recent_rows = db.session.execute(
        select(Attempt.start_time, Attempt.score, Attempt.status).where(
            Attempt.start_time >= start_dt
        )
    ).all()

    daily_buckets = {}
    for offset in range(7):
        day = start_day + timedelta(days=offset)
        daily_buckets[day.isoformat()] = {
            "date": day.isoformat(),
            "label": day.strftime("%d/%m"),
            "count": 0,
            "scores": [],
        }
    for row in recent_rows:
        st = row.start_time
        if st is None:
            continue
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        else:
            st = st.astimezone(timezone.utc)
        key = st.date().isoformat()
        if key in daily_buckets:
            daily_buckets[key]["count"] += 1
            if row.status == "completed" and row.score is not None:
                daily_buckets[key]["scores"].append(float(row.score))

    attempts_by_day = []
    for key in sorted(daily_buckets):
        bucket = daily_buckets[key]
        scores = bucket["scores"]
        attempts_by_day.append(
            {
                "date": bucket["date"],
                "label": bucket["label"],
                "count": bucket["count"],
                "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            }
        )

    subjects_list = db.session.scalars(
        select(Subject).where(Subject.is_active.is_(True)).order_by(Subject.id)
    ).all()
    lesson_counts = dict(
        db.session.execute(select(Lesson.subject_id, func.count(Lesson.id)).group_by(Lesson.subject_id)).all()
    )
    material_counts = dict(
        db.session.execute(select(Material.subject_id, func.count(Material.id)).group_by(Material.subject_id)).all()
    )
    question_counts = dict(
        db.session.execute(select(Question.subject_id, func.count(Question.id)).group_by(Question.subject_id)).all()
    )
    assessment_counts = dict(
        db.session.execute(select(Assessment.subject_id, func.count(Assessment.id)).group_by(Assessment.subject_id)).all()
    )
    attempt_counts = dict(
        db.session.execute(
            select(Assessment.subject_id, func.count(Attempt.id))
            .join(Assessment, Assessment.id == Attempt.assessment_id)
            .group_by(Assessment.subject_id)
        ).all()
    )
    subject_breakdown = [
        {
            "id": subj.id,
            "code": subj.code,
            "name": subj.name,
            "lessons": lesson_counts.get(subj.id, 0),
            "materials": material_counts.get(subj.id, 0),
            "questions": question_counts.get(subj.id, 0),
            "assessments": assessment_counts.get(subj.id, 0),
            "attempts": attempt_counts.get(subj.id, 0),
        }
        for subj in subjects_list
    ]

    latest_attempts = db.session.execute(
        select(Attempt, User, Assessment, Subject)
        .join(User, User.id == Attempt.user_id)
        .join(Assessment, Assessment.id == Attempt.assessment_id)
        .join(Subject, Subject.id == Assessment.subject_id)
        .order_by(Attempt.start_time.desc(), Attempt.id.desc())
        .limit(8)
    ).all()
    recent_attempts = []
    for att, usr, assess, subj in latest_attempts:
        score_val = float(att.score) if att.score is not None else None
        is_passed = (
            score_val is not None
            and att.status == "completed"
            and score_val >= assess.pass_score
        )
        recent_attempts.append(
            {
                "id": att.id,
                "user_name": usr.full_name,
                "user_email": usr.email,
                "assessment_id": assess.id,
                "assessment_title": assess.title,
                "subject_name": subj.name,
                "score": score_val,
                "pass_score": assess.pass_score,
                "is_passed": is_passed,
                "correct_answers": att.correct_answers,
                "total_questions": att.total_questions,
                "status": att.status,
                "start_time": att.start_time.isoformat() if att.start_time else None,
                "submit_time": att.submit_time.isoformat() if att.submit_time else None,
            }
        )

    return success_response(
        {
            "kpis": {
                "subjects_total": subjects_total,
                "subjects_active": subjects_active,
                "lessons_total": lessons_total,
                "lessons_published": lessons_published,
                "materials_total": materials_total,
                "materials_active": materials_active,
                "questions_total": questions_total,
                "questions_active": questions_active,
                "assessments_total": assessments_total,
                "assessments_active": assessments_active,
                "users_total": users_total,
                "students_total": students_total,
                "attempts_total": attempts_total,
                "completed_attempts": completed_attempts,
                "in_progress_attempts": in_progress_attempts,
                "average_score": average_score,
                "pass_rate": pass_rate,
            },
            "attempts_by_day": attempts_by_day,
            "result_distribution": {
                "passed": passed_count,
                "failed": failed_count,
                "in_progress": in_progress_attempts,
            },
            "subject_breakdown": subject_breakdown,
            "recent_attempts": recent_attempts,
        }
    )


@admin_read_bp.get("/subjects")
@staff_required
def subjects():
    page = positive_int("page", 1)
    limit = positive_int("limit", 20, 100)
    statement = select(Subject)
    if not boolean_arg("include_inactive"):
        statement = statement.where(Subject.is_active.is_(True))
    search = request.args.get("search", "").strip()
    if search:
        statement = statement.where(
            or_(
                _unaccent_contains(Subject.name, search),
                _unaccent_contains(Subject.code, search),
            )
        )
    statement = statement.order_by(Subject.id.asc())

    def serialize_all(items):
        ids = [s.id for s in items]
        if not ids:
            return []
        lesson_map = dict(
            db.session.execute(
                select(Lesson.subject_id, func.count(Lesson.id))
                .where(Lesson.subject_id.in_(ids))
                .group_by(Lesson.subject_id)
            ).all()
        )
        mat_map = dict(
            db.session.execute(
                select(Material.subject_id, func.count(Material.id))
                .where(Material.subject_id.in_(ids))
                .group_by(Material.subject_id)
            ).all()
        )
        q_map = dict(
            db.session.execute(
                select(Question.subject_id, func.count(Question.id))
                .where(Question.subject_id.in_(ids))
                .group_by(Question.subject_id)
            ).all()
        )
        a_map = dict(
            db.session.execute(
                select(Assessment.subject_id, func.count(Assessment.id))
                .where(Assessment.subject_id.in_(ids))
                .group_by(Assessment.subject_id)
            ).all()
        )
        return [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "description": s.description,
                "is_active": s.is_active,
                "lesson_count": lesson_map.get(s.id, 0),
                "material_count": mat_map.get(s.id, 0),
                "question_count": q_map.get(s.id, 0),
                "assessment_count": a_map.get(s.id, 0),
            }
            for s in items
        ]

    return _paginated_response(statement, page, limit, serialize_all)


@admin_read_bp.get("/lessons")
@staff_required
def lessons():
    page = positive_int("page", 1)
    limit = positive_int("limit", 20, 100)
    statement = select(Lesson).options(selectinload(Lesson.subject))
    subject_id = positive_int("subject_id")
    if subject_id is not None:
        statement = statement.where(Lesson.subject_id == subject_id)
    status = request.args.get("status", "").strip().lower()
    if status:
        if status not in ("draft", "published", "archived"):
            raise BadRequest("status must be draft, published or archived.")
        statement = statement.where(Lesson.status == status)
    search = request.args.get("search", "").strip()
    if search:
        statement = statement.where(
            or_(
                _unaccent_contains(Lesson.title, search),
                _unaccent_contains(Lesson.code, search),
            )
        )
    statement = statement.order_by(Lesson.subject_id.asc(), Lesson.order_num.asc(), Lesson.id.asc())

    def serialize_all(items):
        ids = [l.id for l in items]
        if not ids:
            return []
        lm_map = dict(
            db.session.execute(
                select(LessonMaterial.lesson_id, func.count(LessonMaterial.id))
                .where(LessonMaterial.lesson_id.in_(ids))
                .group_by(LessonMaterial.lesson_id)
            ).all()
        )
        ql_map = dict(
            db.session.execute(
                select(QuestionLesson.lesson_id, func.count(QuestionLesson.id))
                .where(QuestionLesson.lesson_id.in_(ids))
                .group_by(QuestionLesson.lesson_id)
            ).all()
        )
        return [
            {
                "id": l.id,
                "subject_id": l.subject_id,
                "subject_name": l.subject.name if l.subject else None,
                "code": l.code,
                "title": l.title,
                "objectives": l.objectives,
                "content": l.content,
                "order_num": l.order_num,
                "status": l.status,
                "material_count": lm_map.get(l.id, 0),
                "question_count": ql_map.get(l.id, 0),
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in items
        ]

    return _paginated_response(statement, page, limit, serialize_all)


@admin_read_bp.get("/questions")
@staff_required
def questions():
    page = positive_int("page", 1)
    limit = positive_int("limit", 9, 100)
    statement = filters(
        select(Question).options(
            selectinload(Question.options), selectinload(Question.subject)
        ),
        Question,
    )
    topic = request.args.get("topic")
    if topic is not None and topic != "":
        statement = statement.where(Question.topic == topic)
    statement = statement.order_by(Question.id.desc())

    def serialize_all(items):
        q_ids = [q.id for q in items]
        ql_map = {qid: [] for qid in q_ids}
        if q_ids:
            for row in db.session.execute(
                select(QuestionLesson.question_id, QuestionLesson.lesson_id).where(
                    QuestionLesson.question_id.in_(q_ids)
                )
            ).all():
                ql_map[row.question_id].append(row.lesson_id)
        return [question_json(q, ql_map.get(q.id, [])) for q in items]

    return _paginated_response(statement, page, limit, serialize_all)


@admin_read_bp.get("/questions/<int:question_id>")
@staff_required
def question_detail(question_id):
    q = db.session.scalar(
        select(Question)
        .options(selectinload(Question.options), selectinload(Question.subject))
        .where(Question.id == question_id)
    )
    if q is None:
        raise NotFound("Question not found.")
    lesson_ids = list(
        db.session.scalars(
            select(QuestionLesson.lesson_id).where(QuestionLesson.question_id == q.id)
        ).all()
    )
    return success_response(question_json(q, lesson_ids))


@admin_read_bp.get("/materials")
@staff_required
def materials():
    page = positive_int("page", 1)
    limit = positive_int("limit", 9, 100)
    statement = filters(
        select(Material).options(selectinload(Material.subject)), Material
    ).order_by(Material.id.desc())

    def serialize_all(items):
        m_ids = [m.id for m in items]
        lesson_ids_map = {mid: [] for mid in m_ids}
        lesson_codes_map = {mid: [] for mid in m_ids}
        if m_ids:
            rows = db.session.execute(
                select(LessonMaterial.material_id, Lesson.id, Lesson.code)
                .join(Lesson, Lesson.id == LessonMaterial.lesson_id)
                .where(LessonMaterial.material_id.in_(m_ids))
                .order_by(Lesson.order_num, Lesson.id)
            ).all()
            for row in rows:
                lesson_ids_map[row.material_id].append(row.id)
                lesson_codes_map[row.material_id].append(row.code)
        return [
            {
                "id": m.id,
                "subject_id": m.subject_id,
                "subject_name": m.subject.name,
                "title": m.title,
                "description": m.description,
                "file_url": m.file_url,
                "storage_bucket": m.storage_bucket,
                "storage_path": m.storage_path,
                "difficulty": float(m.difficulty),
                "is_active": m.is_active,
                "lesson_ids": lesson_ids_map.get(m.id, []),
                "lesson_codes": lesson_codes_map.get(m.id, []),
                "created_at": m.created_at.isoformat(),
            }
            for m in items
        ]

    return _paginated_response(statement, page, limit, serialize_all)


@admin_read_bp.get("/assessments")
@staff_required
def assessments():
    page = positive_int("page", 1)
    limit = positive_int("limit", 9, 100)
    statement = filters(
        select(Assessment).options(
            selectinload(Assessment.subject),
            selectinload(Assessment.assessment_questions).load_only(AssessmentQuestion.id),
        ),
        Assessment,
    )
    kind = request.args.get("type")
    if kind is not None and kind != "":
        if kind not in ("quiz", "exam", "practice"):
            raise BadRequest("type must be quiz, exam or practice.")
        statement = statement.where(Assessment.type == kind)
    statement = statement.order_by(Assessment.id.desc())

    def serialize_all(items):
        a_ids = [a.id for a in items]
        attempt_map = {}
        if a_ids:
            attempt_map = dict(
                db.session.execute(
                    select(Attempt.assessment_id, func.count(Attempt.id))
                    .where(Attempt.assessment_id.in_(a_ids))
                    .group_by(Attempt.assessment_id)
                ).all()
            )
        return [
            {
                "id": a.id,
                "subject_id": a.subject_id,
                "subject_name": a.subject.name,
                "title": a.title,
                "description": a.description,
                "type": a.type,
                "duration_minutes": a.duration_minutes,
                "pass_score": a.pass_score,
                "created_by": a.created_by,
                "is_active": a.is_active,
                "question_count": len(a.assessment_questions),
                "attempt_count": attempt_map.get(a.id, 0),
                "created_at": a.created_at.isoformat(),
            }
            for a in items
        ]

    return _paginated_response(statement, page, limit, serialize_all)


@admin_read_bp.get("/assessments/<int:assessment_id>")
@staff_required
def assessment_detail(assessment_id):
    assessment = db.session.scalar(
        select(Assessment)
        .options(
            selectinload(Assessment.subject),
            selectinload(Assessment.assessment_questions).selectinload(
                AssessmentQuestion.question
            ),
        )
        .where(Assessment.id == assessment_id)
    )
    if assessment is None:
        raise NotFound("Assessment not found.")

    ordered = sorted(assessment.assessment_questions, key=lambda item: item.order_num)
    return success_response(
        {
            "id": assessment.id,
            "subject_id": assessment.subject_id,
            "subject_name": assessment.subject.name if assessment.subject else None,
            "title": assessment.title,
            "description": assessment.description,
            "type": assessment.type,
            "duration_minutes": assessment.duration_minutes,
            "pass_score": assessment.pass_score,
            "created_by": assessment.created_by,
            "is_active": assessment.is_active,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
            "question_ids": [aq.question_id for aq in ordered],
            "questions": [
                {
                    "id": aq.question_id,
                    "order_num": aq.order_num,
                    "points": float(aq.points),
                    "content": aq.question.content if aq.question else "",
                    "topic": aq.question.topic if aq.question else None,
                    "difficulty": float(aq.question.difficulty) if aq.question else 5.5,
                    "is_active": aq.question.is_active if aq.question else False,
                }
                for aq in ordered
            ],
        }
    )


@admin_read_bp.get("/attempts")
@staff_required
def attempts():
    from app.library.routes import finalize_all_expired_attempts

    finalize_all_expired_attempts()
    page = positive_int("page", 1)
    limit = positive_int("limit", 15, 100)
    statement = (
        select(Attempt)
        .join(User, User.id == Attempt.user_id)
        .join(Assessment, Assessment.id == Attempt.assessment_id)
        .join(Subject, Subject.id == Assessment.subject_id)
    )
    subject_id = positive_int("subject_id")
    if subject_id is not None:
        statement = statement.where(Assessment.subject_id == subject_id)
    assessment_id = positive_int("assessment_id")
    if assessment_id is not None:
        statement = statement.where(Attempt.assessment_id == assessment_id)
    status = request.args.get("status", "").strip().lower()
    if status:
        if status not in ("in_progress", "completed", "abandoned"):
            raise BadRequest("status must be in_progress, completed or abandoned.")
        statement = statement.where(Attempt.status == status)
    search = request.args.get("search", "").strip()
    if search:
        statement = statement.where(
            or_(
                _unaccent_contains(User.full_name, search),
                _unaccent_contains(User.email, search),
                _unaccent_contains(Assessment.title, search),
            )
        )
    statement = statement.order_by(Attempt.start_time.desc(), Attempt.id.desc())

    result = db.paginate(statement, page=page, per_page=limit, error_out=False)
    user_ids = {att.user_id for att in result.items}
    assess_ids = {att.assessment_id for att in result.items}
    user_map = (
        {u.id: u for u in db.session.scalars(select(User).where(User.id.in_(user_ids))).all()}
        if user_ids
        else {}
    )
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
    items = []
    for att in result.items:
        usr = user_map.get(att.user_id)
        assess = assess_map.get(att.assessment_id)
        subj = assess.subject if assess else None
        if usr is None or assess is None or subj is None:
            continue
        score_val = float(att.score) if att.score is not None else None
        is_passed = (
            score_val is not None
            and att.status == "completed"
            and score_val >= assess.pass_score
        )
        duration_seconds = None
        if att.start_time and att.submit_time:
            st = att.start_time if att.start_time.tzinfo else att.start_time.replace(tzinfo=timezone.utc)
            et = att.submit_time if att.submit_time.tzinfo else att.submit_time.replace(tzinfo=timezone.utc)
            duration_seconds = max(0, int((et - st).total_seconds()))
        items.append(
            {
                "id": att.id,
                "user_id": usr.id,
                "user_name": usr.full_name,
                "user_email": usr.email,
                "assessment_id": assess.id,
                "assessment_title": assess.title,
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
            }
        )

    return success_response(
        items,
        pagination={
            "page": page,
            "limit": limit,
            "total_records": result.total,
            "total_pages": result.pages,
        },
    )


@admin_read_bp.get("/users")
@staff_required
def users():
    page = positive_int("page", 1)
    limit = positive_int("limit", 15, 100)
    statement = select(User)
    role = request.args.get("role", "").strip().lower()
    if role:
        if role not in ("student", "teacher", "admin"):
            raise BadRequest("role must be student, teacher or admin.")
        statement = statement.where(User.role == role)
    search = request.args.get("search", "").strip()
    if search:
        statement = statement.where(
            or_(
                _unaccent_contains(User.full_name, search),
                _unaccent_contains(User.email, search),
            )
        )
    statement = statement.order_by(User.id.asc())

    def serialize_all(items):
        ids = [u.id for u in items]
        att_map = {}
        if ids:
            att_map = dict(
                db.session.execute(
                    select(Attempt.user_id, func.count(Attempt.id))
                    .where(Attempt.user_id.in_(ids))
                    .group_by(Attempt.user_id)
                ).all()
            )
        return [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "phone": u.phone,
                "role": u.role,
                "study_type": u.study_type,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "attempt_count": att_map.get(u.id, 0),
            }
            for u in items
        ]

    return _paginated_response(statement, page, limit, serialize_all)
