from collections import Counter
import pytest
from sqlalchemy import select
from app.extensions import db
from app.models import Subject, Question
from config import normalize_database_url

def test_cloud_connection_url_normalization():
    for scheme in ('postgres','postgresql'):
        assert normalize_database_url(scheme + '://user:pass@db/exam_staging') == 'postgresql+psycopg://user:pass@db/exam_staging'
    assert normalize_database_url('postgresql+psycopg://host/db') == 'postgresql+psycopg://host/db'

def test_no_duplicate_route_handlers(app):
    routes = Counter((rule.rule, method) for rule in app.url_map.iter_rules()
        for method in rule.methods - {'HEAD','OPTIONS'})
    assert not [route for route,count in routes.items() if count > 1]

def test_public_pages_and_static_files(client):
    for path in ('/','/login','/register','/static/js/auth.js','/static/pdf/GTC1.pdf','/health'):
        assert client.get(path).status_code == 200, path
    for path in ('/static/.env','/static/app/models/schema.py','/static/asset/../.env','/static/asset/%2e%2e/.env'):
        assert client.get(path).status_code == 404, path

def test_auth_login_logout_and_admin_page(client, demo):
    response = client.post('/api/auth/login',json={'email':'teacher@example.test','password':'test-teacher-password-123'})
    assert response.status_code == 200
    assert response.json['data']['redirect_url'] == '/admin'
    assert client.get('/admin').status_code == 200
    assert client.get('/api/auth/me').json['data']['role'] == 'teacher'
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/auth/me').status_code == 401

def test_registration_does_not_grant_admin(client):
    response=client.post('/api/auth/register',json={'email':'NEW@example.test','password':'new-test-password','full_name':'Test student','role':'admin','study_type':'auditory'})
    assert response.status_code == 201
    assert response.json['data']['role'] == 'student'
    assert client.post('/api/auth/login',json={'email':'new@example.test','password':'new-test-password'}).status_code == 200
    assert client.get('/api/admin/questions').status_code == 403

def test_csrf_required_for_writes_and_token_works(app, demo):
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        client=app.test_client()
        body={'email':'admin@example.test','password':'test-admin-password-123'}
        assert client.post('/api/auth/login',json=body).status_code == 400
        token=client.get('/api/csrf').json['data']['csrf_token']
        response=client.post('/api/auth/login',json=body,headers={'X-CSRF-Token':token})
        assert response.status_code == 200
        token=client.get('/api/csrf').json['data']['csrf_token']
        assert client.post('/api/auth/logout',headers={'X-CSRF-Token':token}).status_code == 200
    finally:
        app.config['WTF_CSRF_ENABLED'] = False

def test_numeric_library_and_admin_create(login_as):
    client=login_as('teacher')
    subject=db.session.scalar(select(Subject))
    response=client.post('/api/admin/materials',json={'subject_id':subject.id,'title':'Cloud test notes','file_url':'/static/pdf/GTC1.pdf','difficulty':2.5})
    assert response.status_code == 201
    result=client.get('/api/materials?difficulty=2.5').json['data']
    assert any(m['title']=='Cloud test notes' and m['difficulty']==2.5 for m in result)
    assert client.get('/api/materials?difficulty=easy').status_code == 400
    response=client.post('/api/admin/questions',json={'subject_id':subject.id,'content':'Cloud test question','difficulty':7.5,'options':[
        {'content':str(i),'is_correct':i==0} for i in range(4)]})
    assert response.status_code == 201
    assert response.json['data']['difficulty'] == 7.5

def test_student_cannot_write_admin_content(login_as):
    client=login_as('student')
    assert client.post('/api/admin/materials',json={}).status_code == 403
    assert client.post('/api/admin/questions',json={}).status_code == 403
    assert client.post('/api/admin/assessments',json={}).status_code == 403
