from flask import Blueprint, request
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, NotFound
from app.extensions import db
from app.common.difficulty import parse_difficulty
from app.models import Subject, User, Question, Material, Assessment, AssessmentQuestion
from app.common.read_access import staff_required
from app.common.pagination import paginate, positive_int, boolean_arg
from app.common.responses import success_response

admin_read_bp = Blueprint('admin_read', __name__, url_prefix='/api/admin')

def filters(statement, model):
    subject_id = positive_int('subject_id')
    if subject_id is not None:
        statement = statement.where(model.subject_id == subject_id)
    if not boolean_arg('include_inactive'):
        statement = statement.where(model.is_active.is_(True))
    difficulty = request.args.get('difficulty')
    if difficulty is not None:
        if not hasattr(model, 'difficulty'):
            raise BadRequest('This endpoint does not have a difficulty field.')
        try:
            level = parse_difficulty(difficulty)
        except ValueError as error:
            raise BadRequest(str(error)) from error
        statement = statement.where(model.difficulty == level)
    search = request.args.get('search', '').strip()
    if search:
        column = model.content if model is Question else model.title
        # Escape LIKE metacharacters; user text is a literal substring.
        search = search.replace('!', '!!').replace('%', '!%').replace('_', '!_')
        statement = statement.where(func.unaccent(column).ilike(func.unaccent(f'%{search}%'), escape='!'))
    return statement

def question_json(q):
    return {'id': q.id, 'subject_id': q.subject_id, 'topic': q.topic,
        'content': q.content, 'difficulty': float(q.difficulty), 'explanation': q.explanation,
        'is_active': q.is_active, 'options': [
            {'id': o.id, 'content': o.content, 'is_correct': o.is_correct} for o in q.options]}

@admin_read_bp.get('/questions')
@staff_required
def questions():
    statement = filters(select(Question).options(selectinload(Question.options)), Question)
    topic = request.args.get('topic')
    if topic is not None:
        statement = statement.where(Question.topic == topic)
    return paginate(statement.order_by(Question.id.desc()), question_json)

@admin_read_bp.get('/questions/<int:question_id>')
@staff_required
def question_detail(question_id):
    q = db.session.get(Question, question_id)
    if q is None:
        raise NotFound('Question not found.')
    return success_response(question_json(q))

@admin_read_bp.get('/materials')
@staff_required
def materials():
    statement = filters(select(Material).options(selectinload(Material.subject), selectinload(Material.author)), Material)
    return paginate(statement.order_by(Material.id.desc()), lambda m: {
        'id': m.id, 'subject_id': m.subject_id, 'subject_name': m.subject.name,
        'title': m.title, 'description': m.description, 'file_url': m.file_url,
        'difficulty': float(m.difficulty), 'author_id': m.author_id,
        'author_name': m.author.full_name if m.author else None, 'is_active': m.is_active,
        'created_at': m.created_at.isoformat(),
    })

@admin_read_bp.get('/assessments')
@staff_required
def assessments():
    statement = filters(select(Assessment).options(selectinload(Assessment.subject), selectinload(Assessment.assessment_questions).load_only(AssessmentQuestion.id)), Assessment)
    kind = request.args.get('type')
    if kind is not None:
        if kind not in ('quiz','exam','practice'):
            raise BadRequest('type must be quiz, exam or practice.')
        statement = statement.where(Assessment.type == kind)
    def serialize(a):
        count = len(a.assessment_questions)
        return {'id': a.id, 'subject_id': a.subject_id, 'subject_name': a.subject.name,
            'title': a.title, 'description': a.description, 'type': a.type,
            'duration_minutes': a.duration_minutes, 'pass_score': a.pass_score,
            'created_by': a.created_by, 'is_active': a.is_active, 'question_count': count,
            'created_at': a.created_at.isoformat()}
    return paginate(statement.order_by(Assessment.id.desc()), serialize)
