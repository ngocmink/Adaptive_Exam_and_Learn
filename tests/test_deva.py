import json
import os
from pathlib import Path
import pytest
from openpyxl import Workbook
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import *
from app.seed.import_excel import seed_demo, import_legacy, reset_sequences
from conftest import validate_test_database

def counts():
    return {table.name: db.session.scalar(select(func.count()).select_from(table)) for table in db.metadata.tables.values()}

def test_seed_repeatable_and_passwords_hashed(app, demo):
    before = counts()
    seed_demo({role: f'another-{role}-password-123' for role in ('admin','teacher','student')})
    db.session.commit()
    assert counts() == before
    assert demo['admin'].check_password('test-admin-password-123')
    assert demo['admin'].password_hash != 'test-admin-password-123'

@pytest.mark.parametrize('role,status', [('admin',200),('teacher',200),('student',403)])
@pytest.mark.parametrize('path', ['/api/admin/questions','/api/admin/materials','/api/admin/assessments'])
def test_role_permissions(login_as, role, status, path):
    response = login_as(role).get(path)
    assert response.status_code == status
    assert response.json['success'] == (status == 200)

def test_anonymous_and_forged_role(client, demo):
    assert client.get('/api/admin/questions').status_code == 401
    with client.session_transaction() as session:
        session['user_id'] = demo['student'].id
        session['role'] = 'admin'
    assert client.get('/api/admin/questions').status_code == 403
    with client.session_transaction() as session:
        session['user_id'] = 999999
    assert client.get('/api/admin/questions').status_code == 401

def test_question_detail_and_flask_login_session(client, demo):
    with client.session_transaction() as session:
        session['_user_id'] = str(demo['teacher'].id)
        session['_fresh'] = True
    q = db.session.scalar(select(Question))
    response = client.get(f'/api/admin/questions/{q.id}')
    assert response.status_code == 200
    assert len(response.json['data']['options']) == 4
    assert sum(o['is_correct'] for o in response.json['data']['options']) == 1
    assert client.get('/api/admin/questions/999999').status_code == 404

def test_filters_pagination_and_stable_order(login_as):
    client = login_as('admin')
    subject = db.session.scalar(select(Subject))
    url = f'/api/admin/questions?subject_id={subject.id}&difficulty=2&topic=Addition'
    result = client.get(url).json
    assert result['pagination']['total_records'] == 1
    assert result['data'][0]['difficulty'] == 2
    first = client.get('/api/admin/questions?limit=2').json
    second = client.get('/api/admin/questions?limit=2&page=2').json
    assert first['pagination'] == {'page':1,'limit':2,'total_records':3,'total_pages':2}
    assert len(second['data']) == 1
    assert first['data'][0]['id'] > second['data'][0]['id']
    assert client.get('/api/admin/questions?page=99').json['data'] == []
    assert client.get('/api/admin/questions?subject_id=99999').json['pagination']['total_records'] == 0

@pytest.mark.parametrize('query', ['page=0','page=no','limit=101','limit=-1','subject_id=x','difficulty=unknown','include_inactive=maybe'])
def test_bad_filters(login_as, query):
    response = login_as('admin').get('/api/admin/questions?' + query)
    assert response.status_code == 400
    assert response.json['success'] is False

@pytest.mark.parametrize('path,model', [('materials',Material),('assessments',Assessment)])
def test_inactive_and_subject_counts(login_as, path, model):
    client = login_as('teacher')
    row = db.session.scalar(select(model))
    row.is_active = False
    db.session.commit()
    visible = client.get(f'/api/admin/{path}').json['pagination']['total_records']
    all_rows = client.get(f'/api/admin/{path}?include_inactive=true').json['pagination']['total_records']
    assert all_rows == visible + 1
    data = client.get('/api/subjects').json['data'][0]
    assert data['material_count'] == (0 if model is Material else 1)
    assert data['assessment_count'] == (1 if model is Assessment else 2)

def test_subject_visibility_and_assessment_metadata(client, login_as):
    client = login_as('admin')
    data = client.get('/api/admin/assessments?type=practice').json['data']
    assert len(data) == 1 and data[0]['question_count'] == 3
    assert 'questions' not in data[0]
    assert client.get('/api/admin/assessments?type=wrong').status_code == 400
    subject = db.session.scalar(select(Subject))
    subject.is_active = False
    db.session.commit()
    assert client.get('/api/subjects').json['data'] == []

def test_accent_insensitive_search_and_literal_wildcard(login_as):
    client = login_as('admin')
    material = db.session.scalar(select(Material))
    material.title = 'Giải tích 100%'
    db.session.commit()
    assert len(client.get('/api/admin/materials?search=giai%20tich').json['data']) == 1
    assert len(client.get('/api/admin/materials?search=%25').json['data']) == 1
    assert client.get('/api/admin/questions?search=%25').json['data'] == []

def test_unique_correct_and_required_correct(app, demo):
    q = db.session.scalar(select(Question))
    db.session.add(QuestionOption(question_id=q.id, content='Other answer', is_correct=True))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    q = db.session.scalar(select(Question))
    next(o for o in q.options if o.is_correct).is_correct = False
    db.session.flush()
    with pytest.raises(ValueError, match='exactly one'):
        q.validate_for_use()

def test_selected_option_must_belong_to_question(app, demo):
    q1, q2 = db.session.scalars(select(Question).order_by(Question.id)).all()[:2]
    assessment = db.session.scalar(select(Assessment))
    attempt = Attempt(user_id=demo['student'].id, assessment_id=assessment.id, total_questions=3)
    db.session.add(attempt)
    db.session.flush()
    db.session.add(AttemptAnswer(attempt_id=attempt.id, question_id=q1.id, selected_option_id=q2.options[0].id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

def test_invalid_role_and_email_case(app, demo):
    user = User(email='ADMIN@EXAMPLE.TEST', full_name='Duplicate', role='student', password_hash='unused')
    db.session.add(user)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    demo['student'].role = 'superuser'
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

def write_sheet(path, headers, rows):
    book = Workbook()
    book.active.append(headers)
    for row in rows:
        book.active.append(row)
    book.save(path)
    book.close()

def legacy_files(directory):
    write_sheet(directory/'tailieu.xlsx', ['Type','Subject','Doc'], [[0,'Algebra','pdf/GTC1.pdf']])
    write_sheet(directory/'quiz.xlsx', ['Type','Question','Option 1','Option 2','Option 3','Option 4','Correct Answer','Difficulty'],
        [[0,'1+1?','2','3','4','5','2',2.5]])

def test_import_repeatability_and_sequences(app, tmp_path):
    legacy_files(tmp_path)
    import_legacy(tmp_path)
    db.session.commit()
    before = counts()
    import_legacy(tmp_path)
    reset_sequences()
    db.session.commit()
    assert counts() == before
    subject = Subject(code='AFTER-IMPORT', name='After import')
    db.session.add(subject)
    db.session.commit()
    assert subject.id > 1

def test_import_rejects_invalid_difficulty_atomically(app, tmp_path):
    legacy_files(tmp_path)
    before = counts()
    book = __import__('openpyxl').load_workbook(tmp_path/'quiz.xlsx')
    book.active.cell(2, 8).value = 11
    book.save(tmp_path/'quiz.xlsx')
    book.close()
    with pytest.raises(ValueError, match='difficulty'):
        import_legacy(tmp_path)
    db.session.rollback()
    assert counts() == before

def test_import_plaintext_rejected_and_private_users_opt_in(app, tmp_path):
    legacy_files(tmp_path)
    write_sheet(tmp_path/'users.xlsx', ['email','name','password'], [['private@example.test','Private user','plain-password']])
    import_legacy(tmp_path)
    db.session.commit()
    assert db.session.scalar(select(func.count(User.id))) == 0
    before = counts()
    with pytest.raises(ValueError, match='plaintext'):
        import_legacy(tmp_path, include_users=True)
    db.session.rollback()
    assert counts() == before

def test_import_conflict_does_not_overwrite(app, tmp_path):
    legacy_files(tmp_path)
    import_legacy(tmp_path)
    db.session.commit()
    book = __import__('openpyxl').load_workbook(tmp_path/'quiz.xlsx')
    book.active.cell(2, 8).value = 9
    book.save(tmp_path/'quiz.xlsx')
    book.close()
    with pytest.raises(ValueError, match='conflicts'):
        import_legacy(tmp_path)
    db.session.rollback()
    assert db.session.scalar(select(Question)).difficulty == 2.5

def test_seed_cli_requires_passwords_and_repeats(app, monkeypatch):
    runner = app.test_cli_runner()
    for role in ('admin','teacher','student'):
        monkeypatch.delenv(f'DEMO_{role.upper()}_PASSWORD', raising=False)
    assert runner.invoke(args=['seed']).exit_code != 0
    for role in ('admin','teacher','student'):
        monkeypatch.setenv(f'DEMO_{role.upper()}_PASSWORD', f'demo-{role}-password-123')
    assert runner.invoke(args=['seed']).exit_code == 0
    before = counts()
    assert runner.invoke(args=['seed']).exit_code == 0
    assert counts() == before

def test_extensions_and_ten_models(app):
    assert len(db.metadata.tables) == 10
    extensions = set(db.session.scalars(text("SELECT extname FROM pg_extension")))
    assert {'unaccent','pg_trgm'} <= extensions

@pytest.mark.parametrize('test_uri,dev_uri', [
    ('postgresql+psycopg://localhost/exam_dev','postgresql+psycopg://localhost/exam_dev'),
    ('postgresql+psycopg://localhost/exam_test','postgresql+psycopg://localhost/exam_test'),
    ('sqlite:///exam_test','postgresql+psycopg://localhost/exam_dev'),
])
def test_database_reset_guard(test_uri, dev_uri, monkeypatch):
    monkeypatch.setenv('ALLOW_TEST_DB_RESET','yes')
    with pytest.raises(RuntimeError):
        validate_test_database(test_uri, dev_uri)

@pytest.mark.parametrize('value', ['0','11','NaN','Infinity','easy','true'])
def test_numeric_difficulty_rejects_invalid_filter(login_as, value):
    assert login_as('admin').get('/api/admin/questions?difficulty=' + value).status_code == 400

def test_numeric_difficulty_fractional_filter_and_bounds(login_as):
    client = login_as('admin')
    q = db.session.scalar(select(Question))
    q.difficulty = '2.5'
    db.session.commit()
    response = client.get('/api/admin/questions?difficulty=2.5')
    assert response.status_code == 200
    assert response.json['data'][0]['difficulty'] == 2.5
    for value in (1,10):
        q.difficulty = value
        db.session.commit()
    with pytest.raises(ValueError):
        q.difficulty = 10.1
    with pytest.raises(IntegrityError):
        db.session.execute(text('UPDATE questions SET difficulty=0 WHERE id=:id'), {'id':q.id})
        db.session.commit()
    db.session.rollback()

def test_test_reset_requires_acknowledgement(monkeypatch):
    monkeypatch.delenv('ALLOW_TEST_DB_RESET', raising=False)
    with pytest.raises(RuntimeError, match='ALLOW_TEST_DB_RESET'):
        validate_test_database('postgresql+psycopg://localhost/exam_test','postgresql+psycopg://localhost/exam_dev')

def test_successful_hash_import_and_sequence_after_explicit_id(app, tmp_path):
    from werkzeug.security import generate_password_hash
    legacy_files(tmp_path)
    write_sheet(tmp_path/'users.xlsx', ['email','name','password'], [
        ['IMPORTED@EXAMPLE.TEST','Imported student',generate_password_hash('private-test-password')]])
    import_legacy(tmp_path, include_users=True)
    db.session.commit()
    user = db.session.scalar(select(User))
    assert user.email == 'imported@example.test' and user.role == 'student'
    assert user.check_password('private-test-password')
    db.session.add(Subject(id=100, code='EXPLICIT-ID', name='Sequence test'))
    db.session.commit()
    reset_sequences()
    db.session.commit()
    subject = Subject(code='NEXT-ID', name='Next allocated ID')
    db.session.add(subject)
    db.session.commit()
    assert subject.id > 100
