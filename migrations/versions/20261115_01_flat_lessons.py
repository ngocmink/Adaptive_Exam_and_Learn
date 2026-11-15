"""Put lessons directly under subjects and remove material account ownership.

Revision ID: 20261115_01
Revises: 20261114_01
"""
from alembic import op
import sqlalchemy as sa

revision = '20261115_01'
down_revision = '20261114_01'
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    # Prevent concurrent hierarchy writes while resolving ordering and codes.
    op.execute('LOCK TABLE chapters, lessons, materials IN ACCESS EXCLUSIVE MODE')
    rows = connection.execute(sa.text(
        'SELECT id, subject_id, code FROM lessons ORDER BY subject_id, id'
    )).mappings().all()
    reserved = {(row['subject_id'], row['code']) for row in rows}
    seen = set()
    for row in rows:
        key = (row['subject_id'], row['code'])
        if key in seen:
            number = 0
            while True:
                suffix = f"~{row['id']}" + (f'-{number}' if number else '')
                code = row['code'][:100-len(suffix)] + suffix
                if (row['subject_id'], code) not in reserved:
                    break
                number += 1
            connection.execute(sa.text('UPDATE lessons SET code=:code WHERE id=:id'),
                               {'code': code, 'id': row['id']})
            reserved.add((row['subject_id'], code))
        seen.add(key)
    op.execute('''WITH ordered AS (
        SELECT l.id, row_number() OVER (
            PARTITION BY l.subject_id
            ORDER BY c.order_num, c.id, l.order_num, l.id
        ) AS position
        FROM lessons l JOIN chapters c ON c.id=l.chapter_id
    ) UPDATE lessons SET order_num=ordered.position
      FROM ordered WHERE lessons.id=ordered.id''')
    op.create_foreign_key('fk_lessons_subject_id_subjects', 'lessons', 'subjects',
                          ['subject_id'], ['id'], ondelete='RESTRICT')
    op.create_unique_constraint('uq_lessons_subject_code','lessons',['subject_id','code'])
    op.drop_constraint('fk_lessons_chapter_id_chapters','lessons',type_='foreignkey')
    op.drop_constraint('uq_lessons_chapter_code','lessons',type_='unique')
    op.drop_index('ix_lessons_chapter_id',table_name='lessons')
    op.drop_column('lessons','chapter_id')
    op.drop_table('chapters')
    op.drop_constraint('fk_materials_author_id_users','materials',type_='foreignkey')
    op.drop_index('ix_materials_author_id',table_name='materials')
    op.drop_column('materials','author_id')

def downgrade():
    raise RuntimeError(
        'This migration removes chapter metadata and material ownership. '
        'Restore the pre-migration backup together with the previous code; '
        'an automatic downgrade cannot recover the original data.'
    )
