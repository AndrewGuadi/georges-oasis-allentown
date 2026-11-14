"""Track customer acknowledgment independently of staff alerts.

Revision ID: d830f25b012c
Revises: c720e14a901b
"""
from alembic import op
import sqlalchemy as sa

revision = 'd830f25b012c'
down_revision = 'c720e14a901b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('inquiry', sa.Column('customer_notification_state', sa.String(20), nullable=False, server_default='not_requested'))
    op.create_table('customer_acknowledgment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('inquiry_id', sa.Integer(), sa.ForeignKey('inquiry.id'), nullable=False, unique=True),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(), nullable=False),
        sa.Column('lease_until', sa.DateTime()),
        sa.Column('lease_token', sa.String(40)),
        sa.Column('last_error', sa.String(100)),
        sa.Column('sent_at', sa.DateTime()))
    op.create_index('ix_customer_ack_due', 'customer_acknowledgment', ['state', 'next_attempt_at'])


def downgrade():
    op.drop_table('customer_acknowledgment')
    op.drop_column('inquiry', 'customer_notification_state')
