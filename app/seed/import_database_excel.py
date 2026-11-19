"""Import normalized database Excel workbook (database_data.xlsx) into PostgreSQL models."""
import json
from pathlib import Path
import click
from flask.cli import with_appcontext
import openpyxl
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.common.difficulty import parse_difficulty
from app.models import (
    Subject, Lesson, Material, LessonMaterial,
    Question, QuestionOption, QuestionLesson,
    Assessment, AssessmentQuestion, User
)


def _get_sheet_rows(workbook, sheet_name):
    if sheet_name not in workbook.sheetnames:
        return []
    ws = workbook[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = rows[0]
    clean_h = [str(c).strip() for c in header if c is not None and str(c).strip()]
    results = []
    for row in rows[1:]:
        if any(c is not None for c in row[:len(clean_h)]):
            d = dict(zip(clean_h, row[:len(clean_h)]))
            results.append(d)
    return results


def _as_int(val, default=None):
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _as_str(val, default=None):
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _as_bool(val, default=False):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "t", "yes")


def import_database_excel(file_path):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    counts = {
        "subjects": 0,
        "lessons": 0,
        "materials": 0,
        "questions": 0,
        "question_options": 0,
        "question_lessons": 0,
        "assessments": 0,
        "assessment_questions": 0,
        "lesson_materials": 0,
    }

    try:
        # 1. SUBJECTS
        subject_map = {}
        for row in _get_sheet_rows(wb, "subjects"):
            sid = _as_int(row.get("id"))
            code = _as_str(row.get("code"))
            name = _as_str(row.get("name"))
            if not code or not name:
                continue
            desc = _as_str(row.get("description"))
            is_active = _as_bool(row.get("is_active"), True)

            subj = db.session.scalar(select(Subject).filter_by(code=code))
            if subj is None and sid:
                subj = db.session.get(Subject, sid)
            if subj is None:
                subj = Subject(id=sid, code=code, name=name, description=desc, is_active=is_active)
                db.session.add(subj)
            else:
                subj.name = name
                subj.description = desc
                subj.is_active = is_active
            db.session.flush()
            subject_map[subj.id] = subj
            counts["subjects"] += 1

        # 2. LESSONS
        lesson_map = {}
        for row in _get_sheet_rows(wb, "lessons"):
            lid = _as_int(row.get("id"))
            sid = _as_int(row.get("subject_id"))
            code = _as_str(row.get("code"))
            title = _as_str(row.get("title"))
            if not sid or not code or not title or sid not in subject_map:
                continue
            objectives = _as_str(row.get("objective") or row.get("objectives"))
            content = _as_str(row.get("content"))
            order_num = _as_int(row.get("ordernum") or row.get("order_num"), 1)
            status = _as_str(row.get("status"), "published")
            if status not in ("draft", "published", "archived"):
                status = "published"

            lesson = db.session.scalar(select(Lesson).filter_by(subject_id=sid, code=code))
            if lesson is None and lid:
                lesson = db.session.get(Lesson, lid)
            if lesson is None:
                lesson = Lesson(
                    id=lid,
                    subject_id=sid,
                    code=code,
                    title=title,
                    objectives=objectives,
                    content=content,
                    order_num=order_num,
                    status=status,
                )
                db.session.add(lesson)
            else:
                lesson.title = title
                lesson.objectives = objectives
                lesson.content = content
                lesson.order_num = order_num
                lesson.status = status
            db.session.flush()
            lesson_map[lesson.id] = lesson
            counts["lessons"] += 1

        # 3. MATERIALS
        material_map = {}
        for row in _get_sheet_rows(wb, "materials"):
            mid = _as_int(row.get("id"))
            sid = _as_int(row.get("subject_id"))
            file_url = _as_str(row.get("file_url"))
            storage_path = _as_str(row.get("storage_path"))
            storage_bucket = _as_str(row.get("storage_bucket"))

            if not sid or sid not in subject_map:
                continue
            if not file_url and not storage_path:
                continue
            # Skip draft placeholder notes like (chỗ này t sẽ tải slide lên...)
            if file_url and file_url.startswith("(") and file_url.endswith(")"):
                continue

            if storage_path and not storage_bucket:
                storage_bucket = "materials"

            desc = _as_str(row.get("description"))
            title = _as_str(row.get("title")) or desc or f"Tài liệu {mid or sid}"
            difficulty = 5.5
            try:
                if row.get("difficultly") is not None:
                    difficulty = parse_difficulty(row.get("difficultly"))
                elif row.get("difficulty") is not None:
                    difficulty = parse_difficulty(row.get("difficulty"))
            except ValueError:
                difficulty = 5.5
            is_active = _as_bool(row.get("is_active"), True)

            mat = db.session.get(Material, mid) if mid else None
            if mat is None:
                mat = Material(
                    id=mid,
                    subject_id=sid,
                    title=title,
                    description=desc,
                    file_url=file_url,
                    storage_bucket=storage_bucket if storage_path else None,
                    storage_path=storage_path,
                    difficulty=difficulty,
                    is_active=is_active,
                )
                db.session.add(mat)
            else:
                mat.title = title
                mat.description = desc
                mat.file_url = file_url
                mat.storage_bucket = storage_bucket if storage_path else None
                mat.storage_path = storage_path
                mat.difficulty = difficulty
                mat.is_active = is_active
            db.session.flush()
            material_map[mat.id] = mat
            counts["materials"] += 1

        # 4. QUESTIONS & QUESTION_LESSONS
        question_map = {}
        question_lesson_pairs = set()
        for row in _get_sheet_rows(wb, "questions"):
            qid = _as_int(row.get("id"))
            sid = _as_int(row.get("subject_id"))
            content = _as_str(row.get("content"))
            if not sid or not content or sid not in subject_map:
                continue
            lid = _as_int(row.get("lesson_id"))
            topic = _as_str(row.get("topic"))
            explanation = _as_str(row.get("explaintion") or row.get("explanation"))
            difficulty = 5.5
            try:
                if row.get("difficulty") is not None:
                    difficulty = parse_difficulty(row.get("difficulty"))
            except ValueError:
                difficulty = 5.5
            is_active = _as_bool(row.get("is_active"), True)

            q = db.session.get(Question, qid) if qid else None
            if q is None:
                q = Question(
                    id=qid,
                    subject_id=sid,
                    topic=topic,
                    content=content,
                    difficulty=difficulty,
                    explanation=explanation,
                    is_active=is_active,
                )
                db.session.add(q)
            else:
                q.subject_id = sid
                q.topic = topic
                q.content = content
                q.difficulty = difficulty
                q.explanation = explanation
                q.is_active = is_active
            db.session.flush()
            question_map[q.id] = q
            counts["questions"] += 1

            if lid and lid in lesson_map and (q.id, lid) not in question_lesson_pairs:
                question_lesson_pairs.add((q.id, lid))
                ql = db.session.scalar(
                    select(QuestionLesson).filter_by(question_id=q.id, lesson_id=lid)
                )
                if ql is None:
                    ql = QuestionLesson(question_id=q.id, lesson_id=lid, subject_id=sid)
                    db.session.add(ql)
                    counts["question_lessons"] += 1

        # 5. QUESTION_OPTIONS
        for row in _get_sheet_rows(wb, "question_options"):
            oid = _as_int(row.get("id"))
            qid = _as_int(row.get("question_id"))
            content = _as_str(row.get("content"))
            if not qid or content is None or qid not in question_map:
                continue
            is_correct = _as_bool(row.get("is_correct"), False)

            opt = db.session.get(QuestionOption, oid) if oid else None
            if opt is None:
                opt = QuestionOption(
                    id=oid,
                    question_id=qid,
                    content=content,
                    is_correct=is_correct,
                )
                db.session.add(opt)
            else:
                opt.question_id = qid
                opt.content = content
                opt.is_correct = is_correct
            db.session.flush()
            counts["question_options"] += 1

        # 6. ASSESSMENTS
        assess_map = {}
        for row in _get_sheet_rows(wb, "assessments"):
            aid = _as_int(row.get("id"))
            sid = _as_int(row.get("subject_id"))
            title = _as_str(row.get("title"))
            if not sid or not title or sid not in subject_map:
                continue
            desc = _as_str(row.get("description"))
            raw_type = _as_str(row.get("type"), "quiz").lower()
            if "exam" in raw_type or "thi" in raw_type:
                atype = "exam"
            elif "practice" in raw_type or "luyện" in raw_type or "on" in raw_type:
                atype = "practice"
            else:
                atype = "quiz"

            duration = _as_int(row.get("duration_minutes"), 30)
            if not duration or duration <= 0:
                duration = 30
            pass_score = _as_int(row.get("pass_value") or row.get("pass_score"), 50)
            if pass_score is None or pass_score < 0 or pass_score > 100:
                pass_score = 50
            is_active = _as_bool(row.get("is_active"), True)

            creator_id = _as_int(row.get("created_by"))
            if creator_id and db.session.get(User, creator_id) is None:
                creator_id = None

            assess = db.session.get(Assessment, aid) if aid else None
            if assess is None:
                assess = Assessment(
                    id=aid,
                    subject_id=sid,
                    title=title,
                    description=desc,
                    type=atype,
                    duration_minutes=duration,
                    pass_score=pass_score,
                    created_by=creator_id,
                    is_active=is_active,
                )
                db.session.add(assess)
            else:
                assess.subject_id = sid
                assess.title = title
                assess.description = desc
                assess.type = atype
                assess.duration_minutes = duration
                assess.pass_score = pass_score
                if creator_id:
                    assess.created_by = creator_id
                assess.is_active = is_active
            db.session.flush()
            assess_map[assess.id] = assess
            counts["assessments"] += 1

        # 7. ASSESSMENT_QUESTIONS
        for row in _get_sheet_rows(wb, "assessment_questions"):
            aqid = _as_int(row.get("id"))
            aid = _as_int(row.get("assessment_id"))
            qid = _as_int(row.get("question_id"))
            if not aid or not qid or aid not in assess_map or qid not in question_map:
                continue
            order_num = _as_int(row.get("order_num"), 1)
            points = float(row.get("points") or 1.0)
            if points <= 0:
                points = 1.0

            aq = db.session.scalar(
                select(AssessmentQuestion).filter_by(assessment_id=aid, question_id=qid)
            )
            if aq is None and aqid:
                aq = db.session.get(AssessmentQuestion, aqid)
            if aq is None:
                aq = AssessmentQuestion(
                    id=aqid,
                    assessment_id=aid,
                    question_id=qid,
                    order_num=order_num,
                    points=points,
                )
                db.session.add(aq)
            else:
                aq.order_num = order_num
                aq.points = points
            db.session.flush()
            counts["assessment_questions"] += 1

        # 8. QUESTION_LESSONS (if sheet exists with explicit rows)
        for row in _get_sheet_rows(wb, "question_lessons"):
            qlid = _as_int(row.get("id"))
            qid = _as_int(row.get("question_id"))
            lid = _as_int(row.get("lesson_id"))
            sid = _as_int(row.get("subject_id"))
            if not qid or not lid or qid not in question_map or lid not in lesson_map:
                continue
            if (qid, lid) in question_lesson_pairs:
                continue
            question_lesson_pairs.add((qid, lid))
            ql = db.session.scalar(
                select(QuestionLesson).filter_by(question_id=qid, lesson_id=lid)
            )
            if ql is None and qlid:
                ql = db.session.get(QuestionLesson, qlid)
            if ql is None:
                ql = QuestionLesson(
                    id=qlid,
                    question_id=qid,
                    lesson_id=lid,
                    subject_id=sid or lesson_map[lid].subject_id,
                )
                db.session.add(ql)
                counts["question_lessons"] += 1

        # 9. LESSON_MATERIALS (optional)
        for row in _get_sheet_rows(wb, "lesson_materials"):
            lmid = _as_int(row.get("id"))
            lid = _as_int(row.get("lesson_id"))
            mid = _as_int(row.get("material_id"))
            sid = _as_int(row.get("subject_id"))
            lesson_obj = lesson_map.get(lid) or (db.session.get(Lesson, lid) if lid else None)
            material_obj = material_map.get(mid) or (db.session.get(Material, mid) if mid else None)
            if not lid or not mid or not lesson_obj or not material_obj:
                continue
            order_num = _as_int(row.get("order_num"), 1)
            lm = db.session.scalar(
                select(LessonMaterial).filter_by(lesson_id=lid, material_id=mid)
            )
            if lm is None:
                lm = LessonMaterial(
                    id=lmid,
                    lesson_id=lid,
                    material_id=mid,
                    subject_id=sid or lesson_obj.subject_id,
                    order_num=order_num,
                )
                db.session.add(lm)
                counts["lesson_materials"] += 1

        # 10. RESET SEQUENCES FOR POSTGRESQL TABLES
        if db.engine.dialect.name == "postgresql":
            for table_name in [
                "subjects", "lessons", "materials", "questions",
                "question_options", "assessments", "assessment_questions",
                "question_lessons", "lesson_materials"
            ]:
                try:
                    db.session.execute(
                        text(
                            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM \"{table_name}\"), 0) + 1, false)"
                        )
                    )
                except Exception:
                    pass

        db.session.commit()
        return counts
    except Exception:
        db.session.rollback()
        raise
    finally:
        wb.close()


def clean_curriculum_database(clean_users=False, keep_subjects=False):
    """Safely wipe academic, assessment and attempt data to resolve foreign key constraints."""
    dialect = db.engine.dialect.name
    tables = [
        "attempt_answers",
        "attempts",
        "assessment_questions",
        "assessments",
        "question_options",
        "question_lessons",
        "questions",
        "lesson_materials",
        "learning_rules",
        "materials",
        "lessons",
    ]
    if not keep_subjects:
        tables.append("subjects")
    if clean_users:
        tables.append("users")

    if dialect == "postgresql":
        table_str = ", ".join(f'"{t}"' for t in tables)
        db.session.execute(text(f"TRUNCATE TABLE {table_str} RESTART IDENTITY CASCADE;"))
        db.session.commit()
    else:
        db.session.execute(text("PRAGMA foreign_keys = OFF;"))
        for t in tables:
            db.session.execute(text(f'DELETE FROM "{t}";'))
        db.session.execute(text("PRAGMA foreign_keys = ON;"))
        db.session.commit()


@click.command("clean-db")
@click.option(
    "--clean-users",
    is_flag=True,
    default=False,
    help="Xóa toàn bộ người dùng trong bảng users (mặc định giữ lại tài khoản người dùng).",
)
@click.option(
    "--keep-subjects",
    is_flag=True,
    default=False,
    help="Giữ lại bảng môn học subjects (chỉ xóa bài học, tài liệu, câu hỏi, bài thi).",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Bỏ qua hỏi xác nhận (dùng cho automation script).",
)
@with_appcontext
def clean_db_command(clean_users, keep_subjects, yes):
    """Xóa sạch các bảng dữ liệu học tập/đề thi cũ để giải phóng ràng buộc foreign key."""
    if not yes:
        msg = "⚠️ CẢNH BÁO: Thao tác này sẽ XÓA SẠCH toàn bộ môn học, bài học, tài liệu, câu hỏi, bài thi và lịch sử làm bài!"
        if clean_users:
            msg += "\n⚠️ VÀ CẢ TOÀN BỘ TÀI KHOẢN NGƯỜI DÙNG TRONG BẢNG USERS!"
        if not click.confirm(f"{msg}\nBạn có chắc chắn muốn thực hiện?"):
            click.echo("Đã hủy thao tác.")
            return

    try:
        click.echo("🧹 Đang dọn dẹp cơ sở dữ liệu...")
        clean_curriculum_database(clean_users=clean_users, keep_subjects=keep_subjects)
        click.echo("✅ Đã dọn sạch cơ sở dữ liệu thành công.")
    except Exception as err:
        db.session.rollback()
        raise click.ClickException(f"Lỗi khi dọn dẹp database: {err}") from err


@click.command("import-db")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, dir_okay=False),
    default="seed_data/database_data.xlsx",
    show_default=True,
    help="Path to the database Excel workbook.",
)
@click.option(
    "--clean",
    is_flag=True,
    default=False,
    help="Xóa sạch dữ liệu học tập/đề thi cũ trước khi import (giữ nguyên bảng users).",
)
@click.option(
    "--clean-all",
    is_flag=True,
    default=False,
    help="Xóa sạch toàn bộ dữ liệu bao gồm cả users trước khi import.",
)
@with_appcontext
def import_db_command(file, clean, clean_all):
    """Import normalized database Excel workbook into PostgreSQL models."""
    try:
        if clean or clean_all:
            click.echo("🧹 Đang dọn dẹp dữ liệu học tập và bài thi cũ trước khi import...")
            clean_curriculum_database(clean_users=clean_all, keep_subjects=False)
            click.echo("✨ Dọn dẹp hoàn tất! Bắt đầu import dữ liệu mới từ Excel...")

        click.echo(f"Đang đọc và import dữ liệu từ: {file}...")
        results = import_database_excel(file)
        click.echo("✅ Import thành công:")
        click.echo(json.dumps(results, indent=2, ensure_ascii=False))
    except SQLAlchemyError as err:
        db.session.rollback()
        raise click.ClickException(f"Lỗi cơ sở dữ liệu khi import: {err}") from err
    except Exception as err:
        db.session.rollback()
        raise click.ClickException(f"Lỗi: {err}") from err
