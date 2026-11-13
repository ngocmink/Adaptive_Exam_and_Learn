from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKeyConstraint, Index, text
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.common.difficulty import parse_difficulty

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(40))
    role = db.Column(db.String(20), nullable=False, default='student', server_default='student')
    study_type = db.Column(db.String(30))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, server_default=db.func.now())
    __table_args__ = (
        CheckConstraint("role IN ('student','teacher','admin')", name='role'),
        CheckConstraint("email = lower(trim(email)) AND length(email) > 0", name='normalized_email'),
        CheckConstraint("study_type IS NULL OR study_type IN ('visual','auditory','reading','kinesthetic')", name='study_type'),
    )
    @validates('email')
    def normalize_email(self, key, value):
        return value.strip().lower()
    def set_password(self, value):
        self.password_hash = generate_password_hash(value)
    def check_password(self, value):
        return check_password_hash(self.password_hash, value)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=text('true'))

class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='RESTRICT'), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    file_url = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Numeric(), nullable=False, default=5.5, server_default='5.5')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=text('true'))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, server_default=db.func.now())
    subject = db.relationship('Subject')
    author = db.relationship('User')
    __table_args__ = (CheckConstraint('difficulty BETWEEN 1 AND 10', name='difficulty'),
        UniqueConstraint('id','subject_id',name='uq_materials_id_subject'),)

    @validates('difficulty')
    def validate_difficulty(self, key, value):
        return parse_difficulty(value)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='RESTRICT'), nullable=False, index=True)
    topic = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Numeric(), nullable=False, default=5.5, server_default='5.5')
    explanation = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=text('true'))
    subject = db.relationship('Subject')
    options = db.relationship('QuestionOption', back_populates='question', order_by='QuestionOption.id', cascade='all, delete-orphan', passive_deletes=True)
    __table_args__ = (
        CheckConstraint('difficulty BETWEEN 1 AND 10', name='difficulty'),
        Index('ix_questions_subject_difficulty_topic', 'subject_id', 'difficulty', 'topic'),
        UniqueConstraint('id','subject_id',name='uq_questions_id_subject'),
    )
    def validate_for_use(self):
        if len(self.options) != 4 or sum(bool(option.is_correct) for option in self.options) != 1:
            raise ValueError('Usable questions require four options and exactly one correct option.')

    @validates('difficulty')
    def validate_difficulty(self, key, value):
        return parse_difficulty(value)

class QuestionOption(db.Model):
    __tablename__ = 'question_options'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False, server_default=text('false'))
    question = db.relationship('Question', back_populates='options')
    __table_args__ = (
        UniqueConstraint('id', 'question_id', name='uq_question_options_id_question'),
        Index('uq_question_options_one_correct', 'question_id', unique=True, postgresql_where=text('is_correct')),
    )

class Assessment(db.Model):
    __tablename__ = 'assessments'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='RESTRICT'), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False, default='quiz', server_default='quiz')
    duration_minutes = db.Column(db.Integer, nullable=False)
    pass_score = db.Column(db.Integer, nullable=False, default=50, server_default='50')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=text('true'))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, server_default=db.func.now())
    subject = db.relationship('Subject')
    assessment_questions = db.relationship('AssessmentQuestion', order_by='AssessmentQuestion.order_num', cascade='all, delete-orphan', passive_deletes=True)
    __table_args__ = (
        CheckConstraint("type IN ('quiz','exam','practice')", name='type'),
        CheckConstraint('duration_minutes > 0', name='duration'),
        CheckConstraint('pass_score BETWEEN 0 AND 100', name='pass_score'),
    )

class AssessmentQuestion(db.Model):
    __tablename__ = 'assessment_questions'
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='RESTRICT'), nullable=False, index=True)
    order_num = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Float, nullable=False, default=1, server_default='1')
    question = db.relationship('Question')
    __table_args__ = (
        UniqueConstraint('assessment_id', 'question_id', name='uq_assessment_questions_question'), UniqueConstraint('assessment_id', 'order_num', name='uq_assessment_questions_order'),
        CheckConstraint('order_num > 0', name='order'), CheckConstraint("points > 0 AND points < 'Infinity'::float8", name='points'),
    )

class Attempt(db.Model):
    __tablename__ = 'attempts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='RESTRICT'), nullable=False, index=True)
    score = db.Column(db.Float)
    total_questions = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    correct_answers = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    start_time = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, server_default=db.func.now())
    submit_time = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(20), nullable=False, default='in_progress', server_default='in_progress')
    __table_args__ = (
        CheckConstraint("status IN ('in_progress','completed','abandoned')", name='status'),
        CheckConstraint('total_questions >= 0 AND correct_answers >= 0 AND correct_answers <= total_questions', name='counts'),
        CheckConstraint("score IS NULL OR (score >= 0 AND score < 'Infinity'::float8)", name='score'),
        CheckConstraint('submit_time IS NULL OR submit_time >= start_time', name='times'),
    )

class AttemptAnswer(db.Model):
    __tablename__ = 'attempt_answers'
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='RESTRICT'), nullable=False, index=True)
    selected_option_id = db.Column(db.Integer, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    __table_args__ = (
        UniqueConstraint('attempt_id', 'question_id'),
        ForeignKeyConstraint(['selected_option_id','question_id'], ['question_options.id','question_options.question_id'], ondelete='RESTRICT'),
        Index('ix_attempt_answers_selected_option_id', 'selected_option_id'),
    )

class LearningRule(db.Model):
    __tablename__ = 'learning_rules'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='RESTRICT'), nullable=False, index=True)
    trigger_condition = db.Column(db.String(300), nullable=False)
    recommended_action = db.Column(db.Text, nullable=False)
    target_material_id = db.Column(db.Integer, db.ForeignKey('materials.id', ondelete='RESTRICT'), index=True)
