import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Subject, Material, Question, Lesson, LessonMaterial, QuestionLesson

@pytest.fixture
def hierarchy(app,demo):
    subject=db.session.scalar(select(Subject))
    lesson=Lesson(subject_id=subject.id,code='L1',title='Lesson 1')
    db.session.add(lesson);db.session.commit()
    return subject,lesson

def test_reusable_material_and_question(hierarchy):
    subject,lesson=hierarchy
    second=Lesson(subject_id=subject.id,code='L2',title='Lesson 2',order_num=2)
    db.session.add(second);db.session.flush()
    material=db.session.scalar(select(Material));question=db.session.scalar(select(Question))
    for item in (lesson,second):
        db.session.add(LessonMaterial.link(item,material))
        db.session.add(QuestionLesson.link(question,item))
    db.session.commit()
    assert len(subject.lessons)==2
    assert db.session.scalar(select(LessonMaterial)).material.id==material.id
    assert db.session.query(QuestionLesson).count()==2

@pytest.mark.parametrize('kind',['material','question'])
def test_cross_subject_link_rejected_by_database(hierarchy,kind):
    subject,lesson=hierarchy
    other=Subject(code='OTHER',name='Other subject');db.session.add(other);db.session.flush()
    if kind=='material':
        content=Material(subject_id=other.id,title='Other notes',file_url='pdf/GTC1.pdf')
        db.session.add(content);db.session.flush()
        link=LessonMaterial(lesson_id=lesson.id,material_id=content.id,subject_id=subject.id)
    else:
        content=Question(subject_id=other.id,content='Other question')
        db.session.add(content);db.session.flush()
        link=QuestionLesson(lesson_id=lesson.id,question_id=content.id,subject_id=subject.id)
    db.session.add(link)
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

def test_duplicate_lesson_code_within_subject_rejected(hierarchy):
    subject,lesson=hierarchy
    db.session.add(Lesson(subject_id=subject.id,code=lesson.code,title='Duplicate'))
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

def test_lesson_code_reusable_in_other_subject(hierarchy):
    subject,lesson=hierarchy
    other=Subject(code='OTHER',name='Other');db.session.add(other);db.session.flush()
    db.session.add(Lesson(subject_id=other.id,code=lesson.code,title='Other lesson'))
    db.session.commit()

def test_lesson_requires_existing_subject(hierarchy):
    db.session.add(Lesson(subject_id=999999,code='BAD',title='Bad'))
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

def test_material_api_excludes_author(login_as):
    client=login_as('teacher')
    subject=db.session.scalar(select(Subject))
    response=client.post('/api/admin/materials',json={
        'subject_id':subject.id,'title':'Shared notes',
        'file_url':'https://example.com/notes.pdf','difficulty':3})
    assert response.status_code==201
    material_id=response.json['data']['id']
    for path in (f'/api/materials/{material_id}','/api/admin/materials'):
        payload=client.get(path).json['data']
        rows=payload if isinstance(payload,list) else [payload]
        assert rows
        assert all('author_id' not in row and 'author_name' not in row for row in rows)

def test_duplicate_link_rejected(hierarchy):
    lesson=hierarchy[1];material=db.session.scalar(select(Material))
    db.session.add(LessonMaterial.link(lesson,material));db.session.commit()
    db.session.add(LessonMaterial.link(lesson,material))
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

@pytest.mark.parametrize('field,value',[('order_num',0),('status','unknown'),('title',' '),('code','')])
def test_invalid_lesson_metadata_rejected(hierarchy,field,value):
    lesson=hierarchy[1];setattr(lesson,field,value)
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

def test_delete_referenced_lesson_rejected(hierarchy):
    lesson=hierarchy[1];material=db.session.scalar(select(Material))
    db.session.add(LessonMaterial.link(lesson,material));db.session.commit()
    with pytest.raises(IntegrityError):
        db.session.execute(text('DELETE FROM lessons WHERE id=:id'),{'id':lesson.id})
        db.session.commit()
    db.session.rollback()
