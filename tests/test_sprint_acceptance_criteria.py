from datetime import timedelta
from pathlib import Path

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


def test_ac_1_4_erd_models_and_relationships(app):
    expected_tables = {
        "users",
        "subjects",
        "materials",
        "questions",
        "question_options",
        "assessments",
        "assessment_questions",
        "attempts",
        "attempt_answers",
        "learning_rules",
        "lessons",
        "lesson_materials",
        "question_lessons",
    }
    assert set(db.metadata.tables.keys()) == expected_tables


def test_ac_1_6_auth_register_login_role_redirect_and_password_hash(client, demo):
    # Registration supports all 4 study_types including auditory and hashes password
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "newstudent@example.test",
            "password": "secure-password-123",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "study_type": "auditory",
        },
    )
    assert reg.status_code == 201
    created = db.session.scalar(select(User).where(User.email == "newstudent@example.test"))
    assert created is not None
    assert created.role == "student"
    assert created.study_type == "auditory"
    assert created.password_hash != "secure-password-123"
    assert created.check_password("secure-password-123")

    # Wrong credentials rejected with clear Vietnamese message
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "newstudent@example.test", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json["success"] is False

    # Student redirects to /account
    stu_login = client.post(
        "/api/auth/login",
        json={"email": "newstudent@example.test", "password": "secure-password-123"},
    )
    assert stu_login.status_code == 200
    assert stu_login.json["data"]["redirect_url"] == "/account"

    # Teacher & Admin redirect to /admin
    for role in ("teacher", "admin"):
        r = client.post(
            "/api/auth/login",
            json={
                "email": f"{role}@example.test",
                "password": f"test-{role}-password-123",
            },
        )
        assert r.status_code == 200
        assert r.json["data"]["redirect_url"] == "/admin"


def test_ac_1_7_library_search_subject_lesson_filter_metadata_and_pagination(login_as, demo):
    client = login_as("student")
    subj = db.session.scalar(select(Subject))
    lesson = Lesson(subject_id=subj.id, code="L-AC17", title="Giải tích sơ cấp", order_num=1, status="published")
    db.session.add(lesson)
    db.session.flush()

    mat = Material(
        subject_id=subj.id,
        title="Tài liệu AC 1.7",
        description="Mô tả tài liệu",
        file_url="pdf/GTC1.pdf",
        difficulty=3.5,
        is_active=True,
    )
    db.session.add(mat)
    db.session.flush()
    db.session.add(LessonMaterial(lesson_id=lesson.id, material_id=mat.id, subject_id=subj.id, order_num=1))
    db.session.commit()

    # Keyword search + lesson_id filter
    m_res = client.get(f"/api/materials?search=AC%201.7&lesson_id={lesson.id}&page=1&limit=5")
    assert m_res.status_code == 200
    assert m_res.json["pagination"]["total_records"] == 1
    assert m_res.json["data"][0]["lesson_code"] == "L-AC17"
    assert m_res.json["data"][0]["difficulty"] == 3.5

    # Assessments metadata includes author_name, duration_minutes, question_count, subject_name & pagination
    a_res = client.get(f"/api/assessments?subject_id={subj.id}&type=quiz&page=1&limit=1")
    assert a_res.status_code == 200
    assert a_res.json["pagination"]["limit"] == 1
    item = a_res.json["data"][0]
    assert item["question_count"] >= 1
    assert item["duration_minutes"] > 0
    assert item["subject_name"] == subj.name
    assert item["author_name"]


def test_ac_1_8_admin_teacher_crud_and_rbac(login_as, client):
    assert client.post("/api/admin/subjects", json={"code": "X", "name": "Y"}).status_code == 401
    assert login_as("student").post("/api/admin/subjects", json={"code": "X", "name": "Y"}).status_code == 403
    assert login_as("student").post("/api/admin/assessments", json={}).status_code == 403

    teacher = login_as("teacher")
    subj = db.session.scalar(select(Subject))
    c_res = teacher.post(
        "/api/admin/materials",
        json={"subject_id": subj.id, "title": "Teacher Mat", "file_url": "pdf/GTC1.pdf", "difficulty": 4},
    )
    assert c_res.status_code == 201
    mid = c_res.json["data"]["id"]
    assert teacher.put(f"/api/admin/materials/{mid}", json={"title": "Updated Mat"}).status_code == 200
    assert teacher.delete(f"/api/admin/materials/{mid}").status_code == 200
    assert db.session.get(Material, mid).is_active is False


def test_ac_1_9_end_to_end_admin_update_reflected_to_learner(login_as):
    subj = db.session.scalar(select(Subject))
    admin = login_as("admin")
    created = admin.post(
        "/api/admin/materials",
        json={"subject_id": subj.id, "title": "Tài liệu mới Sprint 1", "file_url": "pdf/GTC1.pdf", "difficulty": 6},
    )
    assert created.status_code == 201
    mid = created.json["data"]["id"]

    # Learner searches and opens detail
    student = login_as("student")
    found = student.get("/api/materials?search=Tài%20liệu%20mới%20Sprint%201").json["data"]
    assert len(found) == 1
    assert student.get(f"/reading?id={mid}").status_code == 200

    # Admin updates title -> learner immediately sees new title
    admin = login_as("admin")
    assert admin.put(f"/api/admin/materials/{mid}", json={"title": "Tài liệu đã cập nhật"}).status_code == 200
    student = login_as("student")
    assert student.get(f"/api/materials/{mid}").json["data"]["title"] == "Tài liệu đã cập nhật"

    # Admin disables entire subject -> learner library hides subject's materials and assessments
    admin = login_as("admin")
    assert admin.patch(f"/api/admin/subjects/{subj.id}/toggle-status").json["data"]["is_active"] is False
    student = login_as("student")
    assert student.get(f"/api/materials/{mid}").status_code == 404
    assert student.get("/api/materials").json["data"] == []
    assert student.get("/api/assessments").json["data"] == []


def test_ac_2_1_ux_states_present_in_templates_and_scripts(login_as):
    student = login_as("student")
    assess = db.session.scalar(select(Assessment))
    quiz_html = student.get(f"/quiz?id={assess.id}").data.decode("utf-8")
    assert 'id="autosave-status"' in quiz_html
    assert 'id="offline-banner"' in quiz_html
    assert 'id="submit-modal"' in quiz_html
    assert 'id="timeout-overlay"' in quiz_html

    hist_html = student.get("/history").data.decode("utf-8")
    assert "Chưa có lịch sử làm bài" in hist_html

    reg_html = student.get("/register").data.decode("utf-8")
    assert 'value="auditory"' in reg_html

    quiz_js = Path("js/quiz.js").read_text(encoding="utf-8")
    assert "flushDirtyAnswers" in quiz_js and "offline" in quiz_js


def test_ac_2_3_exam_ownership_reload_persistence_and_locked_after_submit_or_timeout(login_as, demo):
    assess = db.session.scalar(select(Assessment).order_by(Assessment.id))
    qs = db.session.scalars(select(Question).order_by(Question.id)).all()
    opt0 = next(o for o in qs[0].options if o.is_correct)

    # Student starts attempt and saves Q1
    student = login_as("student")
    assert student.get(f"/quiz?id={assess.id}").status_code == 200
    attempt = db.session.scalar(
        select(Attempt).where(Attempt.user_id == demo["student"].id, Attempt.status == "in_progress")
    )
    assert student.post(
        f"/api/attempts/{attempt.id}/answers",
        json={"question_id": qs[0].id, "selected_option_id": opt0.id},
    ).status_code == 200

    # Another user cannot save to or submit student's attempt
    other = login_as("teacher")
    assert other.post(
        f"/api/attempts/{attempt.id}/answers",
        json={"question_id": qs[0].id, "selected_option_id": opt0.id},
    ).status_code == 404
    assert other.post(f"/api/attempts/{attempt.id}/submit", json={}).status_code == 404

    # Reload /quiz keeps saved answer & remaining timer
    student = login_as("student")
    reloaded = student.get(f"/quiz?id={assess.id}").data.decode("utf-8")
    assert f"{qs[0].id}: {opt0.id}" in reloaded or f'"{qs[0].id}": {opt0.id}' in reloaded

    # Once submitted, answers cannot be edited (409)
    assert student.post(f"/api/attempts/{attempt.id}/submit", json={}).status_code == 200
    locked = student.post(
        f"/api/attempts/{attempt.id}/answers",
        json={"question_id": qs[0].id, "selected_option_id": opt0.id},
    )
    assert locked.status_code == 409

    # Strict timeout cutoff: 1 second past deadline refuses edits and auto-submits
    exp = Attempt(
        user_id=demo["student"].id,
        assessment_id=assess.id,
        total_questions=len(qs),
        start_time=utcnow() - timedelta(minutes=assess.duration_minutes, seconds=1),
        status="in_progress",
    )
    db.session.add(exp)
    db.session.commit()
    res_exp = student.post(
        f"/api/attempts/{exp.id}/answers",
        json={"question_id": qs[0].id, "selected_option_id": opt0.id},
    )
    assert res_exp.status_code == 200
    assert res_exp.json["data"]["expired"] is True
    db.session.refresh(exp)
    assert exp.status == "completed"
    # Answer sent AFTER deadline was NOT saved
    assert exp.correct_answers == 0


def test_ac_2_4_submit_autosubmit_closed_page_server_grading_and_idempotency(login_as, demo):
    assess = db.session.scalar(select(Assessment).order_by(Assessment.id))
    qs = db.session.scalars(select(Question).order_by(Question.id)).all()
    q1_right = next(o for o in qs[0].options if o.is_correct)
    q2_right = next(o for o in qs[1].options if o.is_correct)

    # Expired attempt where student closed tab -> Admin viewing overview auto-finalizes it!
    closed_att = Attempt(
        user_id=demo["student"].id,
        assessment_id=assess.id,
        total_questions=len(qs),
        start_time=utcnow() - timedelta(minutes=assess.duration_minutes + 10),
        status="in_progress",
    )
    db.session.add(closed_att)
    db.session.flush()
    db.session.add(AttemptAnswer(attempt_id=closed_att.id, question_id=qs[0].id, selected_option_id=q1_right.id))
    db.session.commit()

    # Even if client tries submitting extra answers AFTER deadline, server ignores late payload
    student = login_as("student")
    late_sub = student.post(
        f"/api/attempts/{closed_att.id}/submit",
        json={"answers": {str(qs[1].id): q2_right.id}},
    )
    assert late_sub.status_code == 200
    assert late_sub.json["data"]["correct_answers"] == 1  # only Q1 saved before deadline counted!
    assert "auto_submitted=1" in late_sub.json["data"]["redirect_url"]

    # Repeated submit does NOT create duplicate Attempt rows
    before_count = db.session.query(Attempt).filter_by(user_id=demo["student"].id).count()
    repeat_sub = student.post(f"/api/attempts/{closed_att.id}/submit", json={})
    assert repeat_sub.status_code == 200
    assert db.session.query(Attempt).filter_by(user_id=demo["student"].id).count() == before_count

    # Also test closed-tab auto-finalization triggered from Admin overview
    abandoned_tab = Attempt(
        user_id=demo["student"].id,
        assessment_id=assess.id,
        total_questions=len(qs),
        start_time=utcnow() - timedelta(minutes=assess.duration_minutes + 3),
        status="in_progress",
    )
    db.session.add(abandoned_tab)
    db.session.commit()
    assert login_as("admin").get("/api/admin/overview").status_code == 200
    db.session.refresh(abandoned_tab)
    assert abandoned_tab.status == "completed"


def test_ac_2_5_results_metrics_explanations_and_privacy(login_as, demo):
    assess = db.session.scalar(select(Assessment).order_by(Assessment.id))
    qs = db.session.scalars(select(Question).order_by(Question.id)).all()
    q1_right = next(o for o in qs[0].options if o.is_correct)

    # Create another student to verify strict privacy
    other_student = User(email="otherstudent@example.test", full_name="Other Student", role="student")
    other_student.set_password("other-student-pw-123")
    db.session.add(other_student)
    db.session.flush()

    att = Attempt(
        user_id=demo["student"].id,
        assessment_id=assess.id,
        total_questions=len(qs),
        start_time=utcnow() - timedelta(minutes=5),
        status="in_progress",
    )
    db.session.add(att)
    db.session.flush()
    db.session.add(AttemptAnswer(attempt_id=att.id, question_id=qs[0].id, selected_option_id=q1_right.id))
    db.session.commit()

    # In-progress attempt cannot show answers prematurely -> redirects back to /quiz
    student = login_as("student")
    premature = student.get(f"/quiz/results?attempt_id={att.id}")
    assert premature.status_code == 302
    assert "/quiz" in premature.location

    # Submit & check results page content
    assert student.post(f"/api/attempts/{att.id}/submit", json={}).status_code == 200
    res_html = student.get(f"/quiz/results?attempt_id={att.id}").data.decode("utf-8")
    assert "Tỷ lệ đúng / sai" in res_html
    assert "Số câu bỏ trống" in res_html
    assert "Thời gian làm bài" in res_html
    assert qs[0].explanation in res_html

    # Another student cannot view this result (404)
    with student.session_transaction() as sess:
        sess.clear()
        sess["user_id"] = other_student.id
    assert student.get(f"/quiz/results?attempt_id={att.id}").status_code == 404


def test_ac_2_7_batch_resync_after_offline_and_history_accuracy(login_as, demo):
    assess = db.session.scalar(select(Assessment).order_by(Assessment.id))
    qs = db.session.scalars(select(Question).order_by(Question.id)).all()
    opts = [next(o for o in q.options if o.is_correct) for q in qs]

    student = login_as("student")
    assert student.get(f"/quiz?id={assess.id}").status_code == 200
    att = db.session.scalar(
        select(Attempt).where(Attempt.user_id == demo["student"].id, Attempt.status == "in_progress")
    )

    # Batch sync answers after reconnecting from offline
    batch = student.post(
        f"/api/attempts/{att.id}/answers",
        json={
            "answers": [
                {"question_id": qs[0].id, "selected_option_id": opts[0].id},
                {"question_id": qs[1].id, "selected_option_id": opts[1].id},
                {"question_id": qs[2].id, "selected_option_id": opts[2].id},
            ]
        },
    )
    assert batch.status_code == 200
    assert batch.json["data"]["saved_count"] == 3

    sub = student.post(f"/api/attempts/{att.id}/submit", json={})
    assert sub.status_code == 200 and sub.json["data"]["score"] == 100.0

    hist = student.get("/api/attempts").json
    assert hist["pagination"]["total_records"] == 1
    assert hist["data"][0]["is_passed"] is True
    assert hist["data"][0]["score"] == 100.0
