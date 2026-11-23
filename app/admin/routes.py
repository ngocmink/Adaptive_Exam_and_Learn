from flask import Blueprint, g, render_template, request
from sqlalchemy import delete, func, select
from urllib.parse import urlparse

from app.common.decorators import role_required
from app.common.difficulty import parse_difficulty
from app.common.material_storage import material_source
from app.common.model_registry import get_model
from app.common.responses import error_response, success_response
from app.extensions import db
from app.library.routes import _material_data


admin_bp = Blueprint("admin", __name__)
MANAGER_ROLES = ["admin", "teacher"]
ASSESSMENT_TYPES = {"quiz", "exam", "practice"}
LESSON_STATUSES = {"draft", "published", "archived"}
USER_ROLES = {"student", "teacher", "admin"}


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


def _parse_int_list(raw, field_name):
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{field_name} phải là danh sách số nguyên.")
    seen = set()
    parsed = []
    for item in raw:
        try:
            val = int(item)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} chứa giá trị không hợp lệ.") from None
        if val not in seen:
            seen.add(val)
            parsed.append(val)
    return parsed


def _sync_material_lessons(material, lesson_ids):
    Lesson = get_model("Lesson")
    LessonMaterial = get_model("LessonMaterial")
    ids = _parse_int_list(lesson_ids, "lesson_ids")
    lessons = db.session.scalars(select(Lesson).where(Lesson.id.in_(ids))).all() if ids else []
    lesson_map = {l.id: l for l in lessons}
    if len(lesson_map) != len(ids):
        raise ValueError("Một hoặc nhiều lesson_id không tồn tại.")
    for lid in ids:
        if lesson_map[lid].subject_id != material.subject_id:
            raise ValueError("Bài học được gán phải thuộc cùng môn học với tài liệu.")
    db.session.execute(delete(LessonMaterial).where(LessonMaterial.material_id == material.id))
    for order_num, lid in enumerate(ids, start=1):
        db.session.add(
            LessonMaterial(
                lesson_id=lid,
                material_id=material.id,
                subject_id=material.subject_id,
                order_num=order_num,
            )
        )
    return ids


def _sync_question_lessons(question, lesson_ids):
    Lesson = get_model("Lesson")
    QuestionLesson = get_model("QuestionLesson")
    ids = _parse_int_list(lesson_ids, "lesson_ids")
    lessons = db.session.scalars(select(Lesson).where(Lesson.id.in_(ids))).all() if ids else []
    lesson_map = {l.id: l for l in lessons}
    if len(lesson_map) != len(ids):
        raise ValueError("Một hoặc nhiều lesson_id không tồn tại.")
    for lid in ids:
        if lesson_map[lid].subject_id != question.subject_id:
            raise ValueError("Bài học được gán phải thuộc cùng môn học với câu hỏi.")
    db.session.execute(delete(QuestionLesson).where(QuestionLesson.question_id == question.id))
    for lid in ids:
        db.session.add(
            QuestionLesson(
                question_id=question.id,
                lesson_id=lid,
                subject_id=question.subject_id,
            )
        )
    return ids


def _question_data(question, options, lesson_ids=None):
    data = {
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
    if lesson_ids is not None:
        data["lesson_ids"] = lesson_ids
    return data


def _subject_data(subject):
    return {
        "id": subject.id,
        "code": subject.code,
        "name": subject.name,
        "description": subject.description,
        "is_active": subject.is_active,
    }


def _lesson_data(lesson):
    return {
        "id": lesson.id,
        "subject_id": lesson.subject_id,
        "code": lesson.code,
        "title": lesson.title,
        "objectives": lesson.objectives,
        "content": lesson.content,
        "order_num": lesson.order_num,
        "status": lesson.status,
    }


# ---------------- SUBJECTS ----------------

@admin_bp.post("/api/admin/subjects")
@role_required(MANAGER_ROLES)
def create_subject():
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Subject = get_model("Subject")
        code = _required_text(body, "code", 100)
        name = _required_text(body, "name", 200)
        existing = db.session.scalar(select(Subject).where(Subject.code == code))
        if existing is not None:
            return error_response("Mã môn học đã tồn tại.", status=409)
        subject = Subject(
            code=code,
            name=name,
            description=body.get("description"),
            is_active=bool(body.get("is_active", True)),
        )
        db.session.add(subject)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    except Exception:
        db.session.rollback()
        return error_response("Không thể tạo môn học.", status=400)
    return success_response(_subject_data(subject), "Đã tạo môn học.", status=201)


@admin_bp.put("/api/admin/subjects/<int:subject_id>")
@role_required(MANAGER_ROLES)
def update_subject(subject_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Subject = get_model("Subject")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return error_response("Không tìm thấy môn học.", status=404)
    try:
        if "code" in body:
            code = _required_text(body, "code", 100)
            dup = db.session.scalar(
                select(Subject).where(Subject.code == code, Subject.id != subject.id)
            )
            if dup is not None:
                return error_response("Mã môn học đã tồn tại.", status=409)
            subject.code = code
        if "name" in body:
            subject.name = _required_text(body, "name", 200)
        if "description" in body:
            subject.description = body["description"]
        if "is_active" in body:
            subject.is_active = bool(body["is_active"])
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể cập nhật môn học.", status=400)
    return success_response(_subject_data(subject), "Đã cập nhật môn học.")


@admin_bp.patch("/api/admin/subjects/<int:subject_id>/toggle-status")
@role_required(MANAGER_ROLES)
def toggle_subject(subject_id):
    try:
        Subject = get_model("Subject")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return error_response("Không tìm thấy môn học.", status=404)
    subject.is_active = not subject.is_active
    db.session.commit()
    return success_response(
        {"id": subject.id, "is_active": subject.is_active},
        "Đã cập nhật trạng thái môn học.",
    )


# ---------------- LESSONS ----------------

@admin_bp.post("/api/admin/lessons")
@role_required(MANAGER_ROLES)
def create_lesson():
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Lesson = get_model("Lesson")
        Subject = get_model("Subject")
        subject_id = int(body.get("subject_id"))
        if db.session.get(Subject, subject_id) is None:
            raise ValueError("Môn học không tồn tại.")
        code = _required_text(body, "code", 100)
        title = _required_text(body, "title", 300)
        order_num = int(body.get("order_num", 1))
        if order_num <= 0:
            raise ValueError("order_num phải lớn hơn 0.")
        status = str(body.get("status", "published")).lower()
        if status not in LESSON_STATUSES:
            raise ValueError("status chỉ nhận draft, published hoặc archived.")
        dup = db.session.scalar(
            select(Lesson).where(Lesson.subject_id == subject_id, Lesson.code == code)
        )
        if dup is not None:
            return error_response("Mã bài học đã tồn tại trong môn học này.", status=409)
        lesson = Lesson(
            subject_id=subject_id,
            code=code,
            title=title,
            objectives=body.get("objectives"),
            content=body.get("content"),
            order_num=order_num,
            status=status,
        )
        db.session.add(lesson)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    except Exception:
        db.session.rollback()
        return error_response("Không thể tạo bài học.", status=400)
    return success_response(_lesson_data(lesson), "Đã tạo bài học.", status=201)


@admin_bp.put("/api/admin/lessons/<int:lesson_id>")
@role_required(MANAGER_ROLES)
def update_lesson(lesson_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Lesson = get_model("Lesson")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        return error_response("Không tìm thấy bài học.", status=404)
    try:
        new_code = _required_text(body, "code", 100) if "code" in body else lesson.code
        new_subject_id = int(body["subject_id"]) if "subject_id" in body else lesson.subject_id
        dup = db.session.scalar(
            select(Lesson).where(
                Lesson.subject_id == new_subject_id,
                Lesson.code == new_code,
                Lesson.id != lesson.id,
            )
        )
        if dup is not None:
            return error_response("Mã bài học đã tồn tại trong môn học này.", status=409)
        lesson.subject_id = new_subject_id
        lesson.code = new_code
        if "title" in body:
            lesson.title = _required_text(body, "title", 300)
        if "objectives" in body:
            lesson.objectives = body["objectives"]
        if "content" in body:
            lesson.content = body["content"]
        if "order_num" in body:
            order_num = int(body["order_num"])
            if order_num <= 0:
                raise ValueError("order_num phải lớn hơn 0.")
            lesson.order_num = order_num
        if "status" in body:
            status = str(body["status"]).lower()
            if status not in LESSON_STATUSES:
                raise ValueError("status chỉ nhận draft, published hoặc archived.")
            lesson.status = status
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể cập nhật bài học.", status=400)
    return success_response(_lesson_data(lesson), "Đã cập nhật bài học.")


@admin_bp.delete("/api/admin/lessons/<int:lesson_id>")
@role_required(MANAGER_ROLES)
def delete_lesson(lesson_id):
    try:
        Lesson = get_model("Lesson")
        LessonMaterial = get_model("LessonMaterial")
        QuestionLesson = get_model("QuestionLesson")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        return error_response("Không tìm thấy bài học.", status=404)
    lm_refs = (
        db.session.scalar(
            select(func.count(LessonMaterial.id)).where(LessonMaterial.lesson_id == lesson.id)
        )
        or 0
    )
    ql_refs = (
        db.session.scalar(
            select(func.count(QuestionLesson.id)).where(QuestionLesson.lesson_id == lesson.id)
        )
        or 0
    )
    if lm_refs == 0 and ql_refs == 0:
        db.session.delete(lesson)
        db.session.commit()
        return success_response({"id": lesson_id, "deleted": True}, "Đã xóa bài học.")
    lesson.status = "archived"
    db.session.commit()
    return success_response(
        {"id": lesson.id, "status": "archived", "deleted": False},
        "Bài học đang có tài liệu hoặc câu hỏi liên kết nên đã chuyển sang lưu trữ (archived).",
    )


# ---------------- MATERIALS ----------------

@admin_bp.post("/api/admin/materials")
@role_required(MANAGER_ROLES)
def create_material():
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Material = get_model("Material")
        title = _required_text(body, "title", 300)
        source = material_source(body)
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
        **source,
        difficulty=difficulty,
        is_active=True,
    )
    try:
        db.session.add(material)
        db.session.flush()
        lesson_ids = None
        if "lesson_ids" in body:
            lesson_ids = _sync_material_lessons(material, body.get("lesson_ids"))
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể tạo tài liệu; hãy kiểm tra subject_id.", status=400)
    data = _material_data(material)
    if lesson_ids is not None:
        data["lesson_ids"] = lesson_ids
    return success_response(data, "Đã tạo tài liệu.", status=201)


@admin_bp.put("/api/admin/materials/<int:material_id>")
@role_required(MANAGER_ROLES)
def update_material(material_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Material = get_model("Material")
        LessonMaterial = get_model("LessonMaterial")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    material = db.session.get(Material, material_id)
    if material is None:
        return error_response("Không tìm thấy tài liệu.", status=404)

    try:
        if "title" in body:
            material.title = _required_text(body, "title", 300)
        for key, value in material_source(body, material).items():
            setattr(material, key, value)
        if "description" in body:
            material.description = body["description"]
        if "subject_id" in body:
            new_subject_id = int(body["subject_id"])
            if new_subject_id != material.subject_id:
                db.session.execute(
                    delete(LessonMaterial).where(LessonMaterial.material_id == material.id)
                )
                material.subject_id = new_subject_id
        if "difficulty" in body:
            material.difficulty = parse_difficulty(body["difficulty"])
        if "is_active" in body:
            material.is_active = bool(body["is_active"])
        db.session.flush()
        lesson_ids = None
        if "lesson_ids" in body:
            lesson_ids = _sync_material_lessons(material, body.get("lesson_ids"))
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể cập nhật tài liệu.", status=400)
    data = _material_data(material)
    if lesson_ids is not None:
        data["lesson_ids"] = lesson_ids
    return success_response(data, "Đã cập nhật tài liệu.")


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


@admin_bp.patch("/api/admin/materials/<int:material_id>/toggle-status")
@role_required(MANAGER_ROLES)
def toggle_material(material_id):
    try:
        Material = get_model("Material")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    material = db.session.get(Material, material_id)
    if material is None:
        return error_response("Không tìm thấy tài liệu.", status=404)
    material.is_active = not material.is_active
    db.session.commit()
    return success_response(
        {"id": material.id, "is_active": material.is_active},
        "Đã cập nhật trạng thái tài liệu.",
    )


# ---------------- QUESTIONS ----------------

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
        lesson_ids = None
        if "lesson_ids" in body:
            lesson_ids = _sync_question_lessons(question, body.get("lesson_ids"))
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
    return success_response(_question_data(question, options, lesson_ids), "Đã tạo câu hỏi.", status=201)


@admin_bp.put("/api/admin/questions/<int:question_id>")
@role_required(MANAGER_ROLES)
def update_question(question_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Question = get_model("Question")
        QuestionOption = get_model("QuestionOption")
        QuestionLesson = get_model("QuestionLesson")
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
                val = body[key]
                if key == "topic" and isinstance(val, str):
                    val = val.strip() or None
                setattr(question, key, val)
        if "subject_id" in body:
            new_subject_id = int(body["subject_id"])
            if new_subject_id != question.subject_id:
                db.session.execute(
                    delete(QuestionLesson).where(QuestionLesson.question_id == question.id)
                )
                question.subject_id = new_subject_id
        if "difficulty" in body:
            question.difficulty = parse_difficulty(body["difficulty"])
        if "is_active" in body:
            question.is_active = bool(body["is_active"])
        if "options" in body:
            _validate_options(body["options"])
            existing_opts = db.session.scalars(
                select(QuestionOption)
                .where(QuestionOption.question_id == question.id)
                .order_by(QuestionOption.id.asc())
            ).all()
            if len(existing_opts) == 4:
                # Clear existing correct flag before reassigning to satisfy uq_question_options_one_correct
                for opt in existing_opts:
                    opt.is_correct = False
                db.session.flush()
                for opt, item in zip(existing_opts, body["options"]):
                    opt.content = item["content"].strip()
                    opt.is_correct = item.get("is_correct") is True
            else:
                db.session.execute(
                    delete(QuestionOption).where(QuestionOption.question_id == question.id)
                )
                db.session.flush()
                db.session.add_all([
                    QuestionOption(
                        question_id=question.id,
                        content=item["content"].strip(),
                        is_correct=item.get("is_correct") is True,
                    )
                    for item in body["options"]
                ])
        db.session.flush()
        lesson_ids = None
        if "lesson_ids" in body:
            lesson_ids = _sync_question_lessons(question, body.get("lesson_ids"))
        db.session.commit()
    except (ValueError, TypeError, KeyError) as exc:
        db.session.rollback()
        return error_response(str(exc), status=400)
    except Exception:
        db.session.rollback()
        return error_response("Không thể cập nhật câu hỏi.", status=400)

    options = db.session.scalars(
        select(QuestionOption)
        .where(QuestionOption.question_id == question.id)
        .order_by(QuestionOption.id.asc())
    ).all()
    if lesson_ids is None:
        lesson_ids = list(
            db.session.scalars(
                select(QuestionLesson.lesson_id).where(QuestionLesson.question_id == question.id)
            ).all()
        )
    return success_response(_question_data(question, options, lesson_ids), "Đã cập nhật câu hỏi.")


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


@admin_bp.patch("/api/admin/questions/<int:question_id>/toggle-status")
@role_required(MANAGER_ROLES)
def toggle_question(question_id):
    try:
        Question = get_model("Question")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    question = db.session.get(Question, question_id)
    if question is None:
        return error_response("Không tìm thấy câu hỏi.", status=404)
    question.is_active = not question.is_active
    db.session.commit()
    return success_response(
        {"id": question.id, "is_active": question.is_active},
        "Đã cập nhật trạng thái câu hỏi.",
    )


# ---------------- ASSESSMENTS ----------------

def _parse_assessment_questions(body):
    if "question_items" in body:
        items = body.get("question_items")
        if not isinstance(items, list):
            raise ValueError("question_items phải là danh sách.")
        parsed = []
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Mỗi phần tử trong question_items phải là object.")
            qid = int(item.get("question_id"))
            points = float(item.get("points", 1.0))
            if points <= 0:
                raise ValueError("Điểm mỗi câu hỏi phải lớn hơn 0.")
            if qid in seen:
                raise ValueError("question_items không được chứa câu hỏi trùng lặp.")
            seen.add(qid)
            parsed.append((qid, points))
        return parsed

    question_ids = body.get("question_ids", [])
    if not isinstance(question_ids, list) or len(set(question_ids)) != len(question_ids):
        raise ValueError("question_ids phải là danh sách không trùng.")
    return [(int(qid), 1.0) for qid in question_ids]


@admin_bp.post("/api/admin/assessments")
@role_required(MANAGER_ROLES)
def create_assessment():
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        Assessment = get_model("Assessment")
        AssessmentQuestion = get_model("AssessmentQuestion")
        title = _required_text(body, "title", 300)
        assessment_type = str(body.get("type", "quiz")).lower()
        if assessment_type not in ASSESSMENT_TYPES:
            raise ValueError("type chỉ nhận quiz, exam hoặc practice.")
        q_items = _parse_assessment_questions(body)
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
                question_id=qid,
                order_num=index,
                points=pts,
            )
            for index, (qid, pts) in enumerate(q_items, start=1)
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
            assessment.title = _required_text(body, "title", 300)
        if "description" in body:
            assessment.description = body["description"]
        for key in ("duration_minutes", "pass_score", "subject_id"):
            if key in body:
                setattr(assessment, key, int(body[key]))
        if "type" in body:
            atype = str(body["type"]).lower()
            if atype not in ASSESSMENT_TYPES:
                raise ValueError("type chỉ nhận quiz, exam hoặc practice.")
            assessment.type = atype
        if "is_active" in body:
            assessment.is_active = bool(body["is_active"])
        if "question_ids" in body or "question_items" in body:
            q_items = _parse_assessment_questions(body)
            db.session.execute(
                delete(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment.id)
            )
            db.session.add_all([
                AssessmentQuestion(
                    assessment_id=assessment.id,
                    question_id=qid,
                    order_num=index,
                    points=pts,
                )
                for index, (qid, pts) in enumerate(q_items, start=1)
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


# ---------------- USERS ----------------

@admin_bp.patch("/api/admin/users/<int:user_id>/role")
@role_required(["admin"])
def update_user_role(user_id):
    body = _body()
    if body is None:
        return error_response("Request body phải là JSON.", status=400)
    try:
        User = get_model("User")
    except RuntimeError as exc:
        return error_response(str(exc), status=503)
    target = db.session.get(User, user_id)
    if target is None:
        return error_response("Không tìm thấy người dùng.", status=404)
    if target.id == g.current_user.id:
        return error_response("Không thể tự thay đổi vai trò của chính mình.", status=400)
    role = str(body.get("role", "")).strip().lower()
    if role not in USER_ROLES:
        return error_response("Vai trò chỉ nhận student, teacher hoặc admin.", status=400)
    target.role = role
    db.session.commit()
    return success_response(
        {"id": target.id, "role": target.role},
        "Đã cập nhật vai trò người dùng.",
    )
