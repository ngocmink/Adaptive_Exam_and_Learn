import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Subject, Material, Question, Chapter, Lesson, LessonMaterial, QuestionLesson

@pytest.fixture
def hierarchy(app,demo):
    subject=db.session.scalar(select(Subject))
    chapter=Chapter(subject_id=subject.id,code='C1',title='Chapter 1')
    db.session.add(chapter);db.session.flush()
    lesson=Lesson(chapter_id=chapter.id,subject_id=subject.id,code='L1',title='Lesson 1')
    db.session.add(lesson);db.session.commit()
    return subject,chapter,lesson

def test_reusable_material_and_question(hierarchy):
    subject,chapter,lesson=hierarchy
    second=Lesson(chapter_id=chapter.id,subject_id=subject.id,code='L2',title='Lesson 2',order_num=2)
    db.session.add(second);db.session.flush()
    material=db.session.scalar(select(Material));question=db.session.scalar(select(Question))
    for item in (lesson,second):
        db.session.add(LessonMaterial.link(item,material))
        db.session.add(QuestionLesson.link(question,item))
    db.session.commit()
    assert len(subject.chapters)==1 and len(chapter.lessons)==2
    assert db.session.scalar(select(LessonMaterial)).material.id==material.id
    assert db.session.query(QuestionLesson).count()==2

@pytest.mark.parametrize('kind',['material','question'])
def test_cross_subject_link_rejected_by_database(hierarchy,kind):
    subject,chapter,lesson=hierarchy
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

def test_wrong_chapter_subject_rejected(hierarchy):
    subject,chapter,lesson=hierarchy
    other=Subject(code='OTHER',name='Other');db.session.add(other);db.session.flush()
    db.session.add(Lesson(chapter_id=chapter.id,subject_id=other.id,code='BAD',title='Bad'))
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

def test_duplicate_link_rejected(hierarchy):
    lesson=hierarchy[2];material=db.session.scalar(select(Material))
    db.session.add(LessonMaterial.link(lesson,material));db.session.commit()
    db.session.add(LessonMaterial.link(lesson,material))
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

@pytest.mark.parametrize('field,value',[('order_num',0),('status','unknown'),('title',' '),('code','')])
def test_invalid_lesson_metadata_rejected(hierarchy,field,value):
    lesson=hierarchy[2];setattr(lesson,field,value)
    with pytest.raises(IntegrityError):db.session.commit()
    db.session.rollback()

def test_delete_referenced_lesson_rejected(hierarchy):
    lesson=hierarchy[2];material=db.session.scalar(select(Material))
    db.session.add(LessonMaterial.link(lesson,material));db.session.commit()
    with pytest.raises(IntegrityError):
        db.session.execute(text('DELETE FROM lessons WHERE id=:id'),{'id':lesson.id})
        db.session.commit()
    db.session.rollback()
