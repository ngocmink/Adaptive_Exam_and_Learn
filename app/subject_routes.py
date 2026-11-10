from flask import Blueprint
from sqlalchemy import select, func
from app.models import Subject, Material, Assessment
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
