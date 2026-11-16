import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.common import material_storage as storage
from app.extensions import db
from app.models import Material, Subject


@pytest.fixture
def stored(app, demo):
    app.config.update(SUPABASE_URL='https://example.supabase.co',
                      SUPABASE_SECRET_KEY='sb_secret_test_only',
                      SUPABASE_STORAGE_BUCKET='materials')
    subject=db.session.scalar(select(Subject))
    material=Material(subject_id=subject.id,title='Private notes',
                      storage_bucket='materials',storage_path='GT1/notes.pdf')
    db.session.add(material);db.session.commit()
    return material


def test_anonymous_cannot_sign(client, stored, monkeypatch):
    signer=Mock();monkeypatch.setattr('app.library.routes.create_pdf_url', signer)
    response=client.get(f'/api/materials/{stored.id}/file')
    assert response.status_code==401
    assert response.headers['Cache-Control']=='private, no-store'
    signer.assert_not_called()


@pytest.mark.parametrize('role',['admin','teacher','student'])
def test_active_content_available_to_authenticated_roles(login_as,stored,role,monkeypatch):
    signer=Mock(return_value='https://example.supabase.co/storage/v1/object/sign/materials/GT1/notes.pdf?token=test')
    monkeypatch.setattr('app.library.routes.create_pdf_url',signer)
    response=login_as(role).get(f'/api/materials/{stored.id}/file')
    assert response.status_code==302
    assert response.headers['Cache-Control']=='private, no-store'
    assert response.headers['Referrer-Policy']=='no-referrer'
    signer.assert_called_once_with('materials','GT1/notes.pdf')


@pytest.mark.parametrize('target',['material','subject','missing'])
def test_unavailable_content_never_signed(login_as,stored,target,monkeypatch):
    client=login_as('student');signer=Mock()
    monkeypatch.setattr('app.library.routes.create_pdf_url',signer)
    material_id=stored.id
    if target=='material':stored.is_active=False
    elif target=='subject':stored.subject.is_active=False
    else:material_id=999999
    db.session.commit()
    assert client.get(f'/api/materials/{material_id}/file').status_code==404
    signer.assert_not_called()


def test_reader_uses_authorized_endpoint(login_as,stored):
    response=login_as('student').get(f'/reading?id={stored.id}')
    assert response.status_code==200
    assert f'/api/materials/{stored.id}/file'.encode() in response.data
    assert b'sb_secret_' not in response.data and b'token=' not in response.data


def test_legacy_pdf_url_still_works(login_as,stored):
    stored.storage_bucket=None;stored.storage_path=None;stored.file_url='pdf/GTC1.pdf';db.session.commit()
    response=login_as('student').get(f'/api/materials/{stored.id}/file')
    assert response.status_code==302
    assert response.location.endswith('/static/pdf/GTC1.pdf')


def test_admin_can_attach_and_replace_storage_source(login_as,stored):
    client=login_as('teacher')
    response=client.post('/api/admin/materials',json={'title':'New PDF','subject_id':stored.subject_id,
                                                   'storage_path':'GT1/new.pdf'})
    assert response.status_code==201
    material_id=response.json['data']['id']
    assert response.json['data']['file_url'] is None
    assert response.json['data']['storage_bucket']=='materials'
    assert client.put(f'/api/admin/materials/{material_id}',json={'title':'Renamed'}).status_code==200
    material=db.session.get(Material,material_id)
    assert material.storage_path=='GT1/new.pdf'
    response=client.put(f'/api/admin/materials/{material_id}',json={'file_url':'https://example.com/notes.pdf'})
    assert response.status_code==200
    assert response.json['data']['storage_path'] is None
    assert client.get('/api/admin/materials').status_code==200


def test_student_cannot_attach_storage_source(login_as,stored):
    assert login_as('student').post('/api/admin/materials',json={
        'title':'Forbidden','subject_id':stored.subject_id,'storage_path':'GT1/new.pdf'}).status_code==403


@pytest.mark.parametrize('body',[
    {'storage_path':'../notes.pdf'}, {'storage_path':'https://evil.test/notes.pdf'},
    {'storage_path':'GT1/notes.pdf','storage_bucket':'other'},
    {'storage_path':'GT1/notes.pdf','file_url':'https://example.com/notes.pdf'},
    {'storage_path':'notes.txt'}, {'storage_bucket':'materials'}, {},
])
def test_admin_rejects_invalid_source(login_as,stored,body):
    response=login_as('admin').post('/api/admin/materials',json={
        'title':'Invalid','subject_id':stored.subject_id,**body})
    assert response.status_code==400


@pytest.mark.parametrize('changes',[
    {'storage_bucket':None}, {'storage_path':None}, {'storage_path':''},
    {'storage_bucket':None,'storage_path':None},
])
def test_database_enforces_complete_file_location(stored,changes):
    for key,value in changes.items():setattr(stored,key,value)
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()


def test_signer_encodes_path_and_uses_bounded_expiry(stored,monkeypatch):
    call=Mock(return_value={'signedURL':'/object/sign/materials/GT1/notes%20%231.pdf?token=test'})
    monkeypatch.setattr(storage,'storage_json',call)
    assert storage.create_pdf_url('materials','GT1/notes #1.pdf').endswith('notes%20%231.pdf?token=test')
    call.assert_called_once_with('POST','object/sign/materials/GT1/notes%20%231.pdf',{'expiresIn':3600})


@pytest.mark.parametrize('signed',[
    'https://evil.test/storage/v1/object/sign/materials/GT1/notes.pdf?token=x',
    '//evil.test/object/sign/materials/GT1/notes.pdf?token=x',
    '/object/sign/other/notes.pdf?token=x', '', None,
])
def test_signer_rejects_invalid_upstream_urls(stored,monkeypatch,signed):
    monkeypatch.setattr(storage,'storage_json',lambda *a: {'signedURL':signed})
    with pytest.raises(storage.StorageError):storage.create_pdf_url('materials','GT1/notes.pdf')


def test_transport_uses_server_key_only_in_apikey_header(stored,monkeypatch):
    response=io.BytesIO(b'{"signedURL":"example"}')
    opener=Mock();opener.open.return_value=response
    monkeypatch.setattr(storage,'build_opener',lambda *args:opener)
    assert storage.storage_json('POST','object/sign/materials/notes.pdf',{'expiresIn':3600})
    request=opener.open.call_args.args[0]
    assert request.get_header('Apikey')=='sb_secret_test_only'
    assert request.get_header('Authorization') is None
    assert 'sb_secret_' not in request.full_url
    assert isinstance(opener.open.call_args.kwargs['timeout'],int)


@pytest.mark.parametrize('failure',[
    URLError('sensitive upstream detail'),
    HTTPError('https://example.test',403,'private',{},io.BytesIO(b'sensitive key detail')),
])
def test_upstream_failure_does_not_leak_details(login_as,stored,monkeypatch,failure):
    opener=Mock();opener.open.side_effect=failure
    monkeypatch.setattr(storage,'build_opener',lambda *args:opener)
    response=login_as('student').get(f'/api/materials/{stored.id}/file')
    assert response.status_code==502
    assert b'sensitive' not in response.data and b'sb_secret_' not in response.data


def test_missing_storage_configuration(login_as,stored):
    from flask import current_app
    current_app.config['SUPABASE_SECRET_KEY']=''
    assert login_as('student').get(f'/api/materials/{stored.id}/file').status_code==503


def test_static_route_cannot_escape_asset_root(client):
    assert client.get('/static/asset/../config.py').status_code==404
    assert client.get('/static/pdf/../../config.py').status_code==404


def test_render_connection_url_uses_installed_driver():
    from config import normalize_database_url
    assert normalize_database_url('postgresql://host/db')=='postgresql+psycopg://host/db'
