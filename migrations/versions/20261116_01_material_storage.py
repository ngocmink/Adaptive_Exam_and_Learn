"""Add private object-storage locations while preserving legacy material URLs.

Revision ID: 20261116_01
Revises: 20261115_01
"""
from alembic import op
import sqlalchemy as sa

revision = '20261116_01'
down_revision = '20261115_01'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('materials',sa.Column('storage_bucket',sa.String(100),nullable=True))
    op.add_column('materials',sa.Column('storage_path',sa.Text(),nullable=True))
    op.alter_column('materials','file_url',existing_type=sa.Text(),nullable=True)
    op.create_check_constraint('storage_pair','materials',
        '(storage_bucket IS NULL AND storage_path IS NULL) OR '
        '(storage_bucket IS NOT NULL AND storage_path IS NOT NULL '
        'AND length(trim(storage_bucket)) > 0 AND length(trim(storage_path)) > 0)')
    op.create_check_constraint('file_source','materials',
        '(file_url IS NOT NULL AND length(trim(file_url)) > 0) OR '
        '(storage_bucket IS NOT NULL AND storage_path IS NOT NULL)')

def downgrade():
    connection=op.get_bind()
    if connection.scalar(sa.text('SELECT count(*) FROM materials WHERE file_url IS NULL')):
        raise RuntimeError('Export or convert storage-only materials before downgrading.')
    op.drop_constraint('ck_materials_file_source','materials',type_='check')
    op.drop_constraint('ck_materials_storage_pair','materials',type_='check')
    op.alter_column('materials','file_url',existing_type=sa.Text(),nullable=False)
    op.drop_column('materials','storage_path')
    op.drop_column('materials','storage_bucket')
