from datetime import timedelta

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import (
    Assessment,
    Attempt,
    AttemptAnswer,
    Lesson,
    LessonMaterial,
    Material,
    Question,
    Subject,
    User,
)
from app.models.schema import utcnow


def test_admin_pages_and_overview_access(login_as, client):
    assert client.get("/admin").status_code == 302
    assert client.get("/api/admin/overview").status_code == 401
    assert login_as("student").get("/api/admin/overview").status_code == 403
    assert login_as("student").get("/admin").status_code == 302

    res = login_as("admin").get("/admin")
    assert res.status_code == 200
    assert b"VISE ADMIN" in res.data

    ov = login_as("teacher").get("/api/admin/overview")
    assert ov.status_code == 200
    data = ov.json["data"]
    assert data["kpis"]["subjects_total"] >= 1
    assert len(data["attempts_by_day"]) == 7
    assert "result_distribution" in data


def test_admin_subject_and_lesson_crud(login_as):
    client = login_as("admin")
    res = client.post(
        "/api/admin/subjects",
        json={"code": "PHYS101", "name": "Vật lý đại cương", "description": "Môn cơ bản"},
    )
    assert res.status_code == 201
    sid = res.json["data"]["id"]

    assert client.post("/api/admin/subjects", json={"code": "PHYS101", "name": "Dup"}).status_code == 409
    assert client.put(f"/api/admin/subjects/{sid}", json={"name": "Vật lý 1"}).status_code == 200
    assert client.patch(f"/api/admin/subjects/{sid}/toggle-status").json["data"]["is_active"] is False
    assert client.patch(f"/api/admin/subjects/{sid}/toggle-status").json["data"]["is_active"] is True

    lres = client.post(
        "/api/admin/lessons",
        json={"subject_id": sid, "code": "PH-C01", "title": "Động học", "order_num": 1, "status": "published"},
    )
    assert lres.status_code == 201
    lid = lres.json["data"]["id"]

    assert client.get(f"/api/admin/lessons?subject_id={sid}").json["pagination"]["total_records"] == 1
    assert client.put(f"/api/admin/lessons/{lid}", json={"title": "Động học chất điểm"}).status_code == 200

    # Unused lesson hard-deletes
    del_res = client.delete(f"/api/admin/lessons/{lid}")
    assert del_res.status_code == 200
    assert del_res.json["data"]["deleted"] is True


def test_admin_material_lesson_link_and_toggle(login_as):
    client = login_as("teacher")
    subj = db.session.scalar(select(Subject))
    lesson = Lesson(subject_id=subj.id, code="DEMO-L1", title="Bài 1", order_num=1, status="published")
    db.session.add(lesson)
    db.session.commit()

    res = client.post(
        "/api/admin/materials",
        json={
            "subject_id": subj.id,
            "title": "Slide chương 1",
            "file_url": "pdf/GTC1.pdf",
            "difficulty": 4.0,
            "lesson_ids": [lesson.id],
        },
    )
    assert res.status_code == 201
    mid = res.json["data"]["id"]
    assert res.json["data"]["lesson_ids"] == [lesson.id]

    mats = client.get("/api/admin/materials?include_inactive=true").json["data"]
    found = next(m for m in mats if m["id"] == mid)
    assert found["lesson_codes"] == ["DEMO-L1"]

    assert client.patch(f"/api/admin/materials/{mid}/toggle-status").json["data"]["is_active"] is False
    assert client.patch(f"/api/admin/materials/{mid}/toggle-status").json["data"]["is_active"] is True

    # Linked lesson archives instead of hard-delete
    del_res = client.delete(f"/api/admin/lessons/{lesson.id}")
    assert del_res.status_code == 200
    assert del_res.json["data"]["deleted"] is False
    assert del_res.json["data"]["status"] == "archived"


def test_admin_question_inplace_option_update_with_attempt_answer(login_as, demo):
    client = login_as("admin")
    q = db.session.scalar(select(Question))
    assess = db.session.scalar(select(Assessment))

    attempt = Attempt(user_id=demo["student"].id, assessment_id=assess.id, total_questions=1, status="completed")
    db.session.add(attempt)
    db.session.flush()
    db.session.add(AttemptAnswer(attempt_id=attempt.id, question_id=q.id, selected_option_id=q.options[0].id, is_correct=True))
    db.session.commit()

    # Updating options in-place must preserve option IDs so AttemptAnswer FK stays valid
    res = client.put(
        f"/api/admin/questions/{q.id}",
        json={
            "content": "Demo updated content?",
            "options": [
                {"content": "New A", "is_correct": False},
                {"content": "New B", "is_correct": True},
                {"content": "New C", "is_correct": False},
                {"content": "New D", "is_correct": False},
            ],
        },
    )
    assert res.status_code == 200
    opts = res.json["data"]["options"]
    assert len(opts) == 4
    assert sum(1 for o in opts if o["is_correct"]) == 1
    assert opts[1]["content"] == "New B" and opts[1]["is_correct"] is True


def test_admin_assessment_detail_and_user_role_management(login_as, demo):
    client = login_as("admin")
    assess = db.session.scalar(select(Assessment))
    qs = db.session.scalars(select(Question).order_by(Question.id)).all()

    detail = client.get(f"/api/admin/assessments/{assess.id}")
    assert detail.status_code == 200
    assert len(detail.json["data"]["questions"]) == len(qs)

    res = client.put(
        f"/api/admin/assessments/{assess.id}",
        json={"question_items": [{"question_id": qs[0].id, "points": 2.5}]},
    )
    assert res.status_code == 200
    detail2 = client.get(f"/api/admin/assessments/{assess.id}").json["data"]
    assert len(detail2["questions"]) == 1
    assert detail2["questions"][0]["points"] == 2.5

    # Role management: admin only, cannot self-change
    student_id = demo["student"].id
    admin_id = demo["admin"].id
    assert client.patch(f"/api/admin/users/{admin_id}/role", json={"role": "student"}).status_code == 400
    assert client.patch(f"/api/admin/users/{student_id}/role", json={"role": "teacher"}).status_code == 200
    assert db.session.get(User, student_id).role == "teacher"

    assert login_as("teacher").patch(f"/api/admin/users/{student_id}/role", json={"role": "student"}).status_code == 403


def test_exam_autosave_resume_submit_and_history(login_as, demo):
    client = login_as("student")
    assess = db.session.scalar(select(Assessment).order_by(Assessment.id))
    questions = db.session.scalars(select(Question).order_by(Question.id)).all()

    # 1. Opening /quiz creates an in_progress Attempt
    res = client.get(f"/quiz?id={assess.id}")
    assert res.status_code == 200
    attempt = db.session.scalar(
        select(Attempt).where(Attempt.user_id == demo["student"].id, Attempt.assessment_id == assess.id)
    )
    assert attempt is not None and attempt.status == "in_progress"

    # 2. Auto-save answers one by one (Q1 correct, Q2 wrong, Q3 skipped)
    q1_correct_opt = next(o for o in questions[0].options if o.is_correct)
    q2_wrong_opt = next(o for o in questions[1].options if not o.is_correct)

    save1 = client.post(
        f"/api/attempts/{attempt.id}/answers",
        json={"question_id": questions[0].id, "selected_option_id": q1_correct_opt.id},
    )
    assert save1.status_code == 200
    assert save1.json["data"]["saved_count"] == 1

    save2 = client.post(
        f"/api/attempts/{attempt.id}/answers",
        json={"question_id": questions[1].id, "selected_option_id": q2_wrong_opt.id},
    )
    assert save2.status_code == 200
    assert save2.json["data"]["saved_count"] == 2

    # 3. Reloading /quiz resumes the SAME attempt with saved answers rendered
    res_resume = client.get(f"/quiz?id={assess.id}")
    assert res_resume.status_code == 200
    assert f'value="{attempt.id}"'.encode() in res_resume.data
    assert db.session.query(Attempt).filter_by(user_id=demo["student"].id).count() == 1

    # 4. Submit grades accurately (1 of 3 correct = 33.3%) and is idempotent
    sub = client.post(f"/api/attempts/{attempt.id}/submit", json={"answers": {}})
    assert sub.status_code == 200
    assert sub.json["data"]["correct_answers"] == 1
    assert sub.json["data"]["score"] == 33.3
    assert sub.json["data"]["is_passed"] is False

    sub_again = client.post(f"/api/attempts/{attempt.id}/submit", json={})
    assert sub_again.status_code == 200
    assert sub_again.json["data"]["score"] == 33.3

    # 5. Results page shows breakdown & staff can also inspect it
    results_page = client.get(f"/quiz/results?attempt_id={attempt.id}")
    assert results_page.status_code == 200
    assert b"33.3" in results_page.data

    assert login_as("teacher").get(f"/quiz/results?attempt_id={attempt.id}").status_code == 200

    # 6. History API and page work
    client = login_as("student")
    hist_api = client.get("/api/attempts").json
    assert hist_api["pagination"]["total_records"] == 1
    assert hist_api["data"][0]["score"] == 33.3

    summary = client.get("/api/attempts/summary").json["data"]
    assert summary["completed_attempts"] == 1
    assert summary["average_score"] == 33.3
    assert client.get("/history").status_code == 200


def test_expired_attempt_auto_submits(login_as, demo):
    client = login_as("student")
    assess = db.session.scalar(select(Assessment).order_by(Assessment.id))
    q1 = db.session.scalar(select(Question).order_by(Question.id))
    correct_opt = next(o for o in q1.options if o.is_correct)

    expired_attempt = Attempt(
        user_id=demo["student"].id,
        assessment_id=assess.id,
        total_questions=3,
        start_time=utcnow() - timedelta(minutes=assess.duration_minutes + 5),
        status="in_progress",
    )
    db.session.add(expired_attempt)
    db.session.flush()
    db.session.add(AttemptAnswer(attempt_id=expired_attempt.id, question_id=q1.id, selected_option_id=correct_opt.id))
    db.session.commit()

    # Auto-save attempt after expiry triggers auto-submit
    res = client.post(
        f"/api/attempts/{expired_attempt.id}/answers",
        json={"question_id": q1.id, "selected_option_id": correct_opt.id},
    )
    assert res.status_code == 200
    assert res.json["data"]["expired"] is True
    db.session.refresh(expired_attempt)
    assert expired_attempt.status == "completed"
    assert expired_attempt.correct_answers == 1
