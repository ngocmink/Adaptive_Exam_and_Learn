from flask import Blueprint, request
from sqlalchemy import select, func
from app.models import Subject, Material, Assessment, Lesson
from app.common.pagination import paginate

subjects_bp = Blueprint('subjects_read', __name__)

@subjects_bp.get('/api/subjects')
def subjects():
    material_count = select(func.count(Material.id)).where(Material.subject_id == Subject.id, Material.is_active.is_(True)).correlate(Subject).scalar_subquery()
    assessment_count = select(func.count(Assessment.id)).where(Assessment.subject_id == Subject.id, Assessment.is_active.is_(True)).correlate(Subject).scalar_subquery()
    # Correlated counts avoid multiplying material and assessment rows.
    from app.extensions import db
    counts = {r.id: (r.material_count, r.assessment_count) for r in db.session.execute(
        select(Subject.id, material_count.label('material_count'), assessment_count.label('assessment_count')).where(Subject.is_active.is_(True)))}
    return paginate(select(Subject).where(Subject.is_active.is_(True)).order_by(Subject.id), lambda s: {
        'id': s.id, 'code': s.code, 'name': s.name, 'description': s.description,
        'material_count': counts[s.id][0], 'assessment_count': counts[s.id][1],
    })

@subjects_bp.get('/api/lessons')
def lessons():
    subject_id = request.args.get('subject_id')
    stmt = (
        select(Lesson)
        .join(Subject, Subject.id == Lesson.subject_id)
        .where(Subject.is_active.is_(True), Lesson.status == 'published')
    )
    if subject_id:
        try:
            stmt = stmt.where(Lesson.subject_id == int(subject_id))
        except (ValueError, TypeError):
            pass
    stmt = stmt.order_by(Subject.id, Lesson.order_num, Lesson.id)
    return paginate(stmt, lambda l: {
        'id': l.id,
        'code': l.code,
        'title': l.title,
        'subject_id': l.subject_id,
        'subject_code': l.subject.code if l.subject else '',
        'subject_name': l.subject.name if l.subject else '',
        'order_num': l.order_num,
    })
