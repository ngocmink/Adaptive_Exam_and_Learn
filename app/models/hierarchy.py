"""Teaching hierarchy with subject-consistent reusable content links."""
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKeyConstraint, text
from app.extensions import db
from app.models.schema import utcnow

class Chapter(db.Model):
    __tablename__ = 'chapters'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='RESTRICT'), nullable=False, index=True)
    code = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    order_num = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    status = db.Column(db.String(20), nullable=False, default='draft', server_default='draft')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, server_default=db.func.now())
    subject = db.relationship('Subject', backref=db.backref('chapters', passive_deletes=True, order_by='Chapter.order_num, Chapter.id'))
    __table_args__ = (
        UniqueConstraint('subject_id','code',name='uq_chapters_subject_code'),
        UniqueConstraint('id','subject_id',name='uq_chapters_id_subject'),
        CheckConstraint('order_num > 0',name='order'),
        CheckConstraint("length(trim(code)) > 0 AND length(trim(title)) > 0",name='nonempty'),
        CheckConstraint("status IN ('draft','published','archived')",name='status'),
    )

class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, nullable=False, index=True)
    subject_id = db.Column(db.Integer, nullable=False, index=True)
    code = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    objectives = db.Column(db.Text)
    content = db.Column(db.Text)
    order_num = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    status = db.Column(db.String(20), nullable=False, default='draft', server_default='draft')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, server_default=db.func.now())
    chapter = db.relationship('Chapter', backref=db.backref('lessons',passive_deletes=True,order_by='Lesson.order_num, Lesson.id'))
    __table_args__ = (
        ForeignKeyConstraint(['chapter_id','subject_id'],['chapters.id','chapters.subject_id'],ondelete='RESTRICT'),
        UniqueConstraint('chapter_id','code',name='uq_lessons_chapter_code'),
        UniqueConstraint('id','subject_id',name='uq_lessons_id_subject'),
        CheckConstraint('order_num > 0',name='order'),
        CheckConstraint("length(trim(code)) > 0 AND length(trim(title)) > 0",name='nonempty'),
        CheckConstraint("status IN ('draft','published','archived')",name='status'),
    )

class LessonMaterial(db.Model):
    __tablename__ = 'lesson_materials'
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, nullable=False, index=True)
    material_id = db.Column(db.Integer, nullable=False, index=True)
    subject_id = db.Column(db.Integer, nullable=False)
    order_num = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    # Read-only navigation avoids ambiguous writes to the shared subject_id;
    # set all three IDs explicitly (or use the constructor helper).
    lesson = db.relationship('Lesson',viewonly=True)
    material = db.relationship('Material',viewonly=True)
    __table_args__ = (
        ForeignKeyConstraint(['lesson_id','subject_id'],['lessons.id','lessons.subject_id'],ondelete='RESTRICT'),
        ForeignKeyConstraint(['material_id','subject_id'],['materials.id','materials.subject_id'],ondelete='RESTRICT'),
        UniqueConstraint('lesson_id','material_id',name='uq_lesson_materials_pair'),
        CheckConstraint('order_num > 0',name='order'),
    )
    @classmethod
    def link(cls,lesson,material,order_num=1):
        if lesson.id is None or material.id is None:
            raise ValueError('Flush lesson and material before linking.')
        if lesson.subject_id != material.subject_id:
            raise ValueError('Lesson and material must belong to the same subject.')
        return cls(lesson_id=lesson.id,material_id=material.id,subject_id=lesson.subject_id,order_num=order_num)

class QuestionLesson(db.Model):
    __tablename__ = 'question_lessons'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, nullable=False, index=True)
    lesson_id = db.Column(db.Integer, nullable=False, index=True)
    subject_id = db.Column(db.Integer, nullable=False)
    question = db.relationship('Question',viewonly=True)
    lesson = db.relationship('Lesson',viewonly=True)
    __table_args__ = (
        ForeignKeyConstraint(['question_id','subject_id'],['questions.id','questions.subject_id'],ondelete='RESTRICT'),
        ForeignKeyConstraint(['lesson_id','subject_id'],['lessons.id','lessons.subject_id'],ondelete='RESTRICT'),
        UniqueConstraint('question_id','lesson_id',name='uq_question_lessons_pair'),
    )
    @classmethod
    def link(cls,question,lesson):
        if question.id is None or lesson.id is None:
            raise ValueError('Flush question and lesson before linking.')
        if question.subject_id != lesson.subject_id:
            raise ValueError('Question and lesson must belong to the same subject.')
        return cls(question_id=question.id,lesson_id=lesson.id,subject_id=lesson.subject_id)
