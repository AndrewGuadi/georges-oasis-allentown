"""Preserve both customer contact details and install the inquiry search index.

Revision ID: c720e14a901b
Revises: baf73d71c469
"""
from alembic import op
import sqlalchemy as sa
from georges_oasis.services.search import install_search_v1

revision = 'c720e14a901b'
down_revision = 'baf73d71c469'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('inquiry') as batch:
        batch.add_column(sa.Column('email', sa.String(254), nullable=False, server_default=''))
        batch.add_column(sa.Column('phone', sa.String(40), nullable=False, server_default=''))
    op.execute("UPDATE inquiry SET email=contact_detail WHERE contact_method='email'")
    op.execute("UPDATE inquiry SET phone=contact_detail WHERE contact_method='phone'")
    install_search_v1(op.get_bind())


def downgrade():
    connection = op.get_bind()
    if connection.dialect.name == 'sqlite':
        for name in ('inquiry_search_insert', 'inquiry_search_update', 'inquiry_search_delete',
                     'inquiry_note_search_insert', 'inquiry_note_search_update', 'inquiry_note_search_delete'):
            connection.exec_driver_sql(f'DROP TRIGGER IF EXISTS {name}')
        connection.exec_driver_sql('DROP TABLE IF EXISTS inquiry_search')
    with op.batch_alter_table('inquiry') as batch:
        batch.drop_column('phone')
        batch.drop_column('email')
