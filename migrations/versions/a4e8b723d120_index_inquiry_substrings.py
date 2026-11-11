"""Index inquiry substring search without asynchronous copies.

Revision ID: a4e8b723d120
Revises: 65bd2f602991
"""
from alembic import op
import sqlalchemy as sa

revision = 'a4e8b723d120'
down_revision = '65bd2f602991'
branch_labels = None
depends_on = None


def upgrade():
    from georges_oasis.services.search import install_search_v1
    connection = op.get_bind()
    install_search_v1(connection)
    op.create_index('ix_inquiry_active_type_state', 'inquiry', ['archived_at','inquiry_type','staff_state'])


def downgrade():
    op.drop_index('ix_inquiry_active_type_state', table_name='inquiry')
    if op.get_bind().dialect.name == 'sqlite':
        for name in ['inquiry_search_insert', 'inquiry_search_update', 'inquiry_search_delete', 'inquiry_note_search_insert', 'inquiry_note_search_update', 'inquiry_note_search_delete']:
            op.execute('DROP TRIGGER IF EXISTS ' + name)
        op.execute('DROP TABLE IF EXISTS inquiry_search')
