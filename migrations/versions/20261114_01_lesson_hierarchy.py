"""Add chapters, lessons and subject-consistent content links.

Revision ID: 20261114_01
Revises: 8c3d02867120
"""
from alembic import op
import sqlalchemy as sa

revision='20261114_01'
down_revision='8c3d02867120'
branch_labels=None
depends_on=None

def upgrade():
    op.create_unique_constraint('uq_materials_id_subject','materials',['id','subject_id'])
    op.create_unique_constraint('uq_questions_id_subject','questions',['id','subject_id'])
    op.create_table('chapters',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('subject_id',sa.Integer(),nullable=False),
        sa.Column('code',sa.String(100),nullable=False),
        sa.Column('title',sa.String(300),nullable=False),
        sa.Column('description',sa.Text()),
        sa.Column('order_num',sa.Integer(),nullable=False,server_default='1'),
        sa.Column('status',sa.String(20),nullable=False,server_default='draft'),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['subject_id'],['subjects.id'],ondelete='RESTRICT'),
        sa.UniqueConstraint('subject_id','code',name='uq_chapters_subject_code'),
        sa.UniqueConstraint('id','subject_id',name='uq_chapters_id_subject'),
        sa.CheckConstraint('order_num > 0',name='order'),
        sa.CheckConstraint('length(trim(code)) > 0 AND length(trim(title)) > 0',name='nonempty'),
        sa.CheckConstraint("status IN ('draft','published','archived')",name='status'))
    op.create_index('ix_chapters_subject_id','chapters',['subject_id'])
    op.create_table('lessons',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('chapter_id',sa.Integer(),nullable=False),
        sa.Column('subject_id',sa.Integer(),nullable=False),
        sa.Column('code',sa.String(100),nullable=False),
        sa.Column('title',sa.String(300),nullable=False),
        sa.Column('objectives',sa.Text()),sa.Column('content',sa.Text()),
        sa.Column('order_num',sa.Integer(),nullable=False,server_default='1'),
        sa.Column('status',sa.String(20),nullable=False,server_default='draft'),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['chapter_id','subject_id'],['chapters.id','chapters.subject_id'],ondelete='RESTRICT'),
        sa.UniqueConstraint('chapter_id','code',name='uq_lessons_chapter_code'),
        sa.UniqueConstraint('id','subject_id',name='uq_lessons_id_subject'),
        sa.CheckConstraint('order_num > 0',name='order'),
        sa.CheckConstraint('length(trim(code)) > 0 AND length(trim(title)) > 0',name='nonempty'),
        sa.CheckConstraint("status IN ('draft','published','archived')",name='status'))
    for col in ('chapter_id','subject_id'):
        op.create_index(f'ix_lessons_{col}','lessons',[col])
    op.create_table('lesson_materials',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('lesson_id',sa.Integer(),nullable=False),
        sa.Column('material_id',sa.Integer(),nullable=False),
        sa.Column('subject_id',sa.Integer(),nullable=False),
        sa.Column('order_num',sa.Integer(),nullable=False,server_default='1'),
        sa.ForeignKeyConstraint(['lesson_id','subject_id'],['lessons.id','lessons.subject_id'],ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['material_id','subject_id'],['materials.id','materials.subject_id'],ondelete='RESTRICT'),
        sa.UniqueConstraint('lesson_id','material_id',name='uq_lesson_materials_pair'),
        sa.CheckConstraint('order_num > 0',name='order'))
    for col in ('lesson_id','material_id'):
        op.create_index(f'ix_lesson_materials_{col}','lesson_materials',[col])
    op.create_table('question_lessons',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('question_id',sa.Integer(),nullable=False),
        sa.Column('lesson_id',sa.Integer(),nullable=False),
        sa.Column('subject_id',sa.Integer(),nullable=False),
        sa.ForeignKeyConstraint(['question_id','subject_id'],['questions.id','questions.subject_id'],ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['lesson_id','subject_id'],['lessons.id','lessons.subject_id'],ondelete='RESTRICT'),
        sa.UniqueConstraint('question_id','lesson_id',name='uq_question_lessons_pair'))
    for col in ('question_id','lesson_id'):
        op.create_index(f'ix_question_lessons_{col}','question_lessons',[col])

def downgrade():
    # Destructive for the NEW hierarchy only. Never downgrade shared content
    # without a backup and an explicit rollback plan.
    for table in ('question_lessons','lesson_materials','lessons','chapters'):
        op.drop_table(table)
    op.drop_constraint('uq_questions_id_subject','questions',type_='unique')
    op.drop_constraint('uq_materials_id_subject','materials',type_='unique')
