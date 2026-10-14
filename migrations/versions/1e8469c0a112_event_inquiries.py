"""Durable event inquiries and database-backed submission rate limits.
Revision ID: 1e8469c0a112
Revises: 0df58c369367
"""
from alembic import op
import sqlalchemy as sa
revision = '1e8469c0a112'
down_revision = '0df58c369367'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('promotion') as batch:
        batch.add_column(sa.Column('approval_status',sa.String(20),nullable=False,server_default='draft'))
        batch.add_column(sa.Column('source',sa.String(300),nullable=False,server_default='Owner dashboard'))
        batch.add_column(sa.Column('reviewed_at',sa.DateTime(),nullable=True))
    # Preserve offers previously published by the owner as approved records.
    op.execute("UPDATE promotion SET approval_status = 'approved', reviewed_at = CURRENT_TIMESTAMP WHERE enabled = 1")
    op.create_table('inquiry',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('reference',sa.String(24),nullable=False,unique=True),
        sa.Column('submission_key',sa.String(64),nullable=False,unique=True),
        sa.Column('name',sa.String(100),nullable=False),
        sa.Column('contact_method',sa.String(10),nullable=False),
        sa.Column('contact_detail',sa.String(254),nullable=False),
        sa.Column('occasion',sa.String(60),nullable=False),
        sa.Column('guest_count',sa.Integer(),nullable=True),
        sa.Column('preferred_date',sa.Date(),nullable=True),
        sa.Column('date_flexibility',sa.String(100),nullable=False),
        sa.Column('interests',sa.JSON(),nullable=False),
        sa.Column('notes',sa.Text(),nullable=False),
        sa.Column('received_at',sa.DateTime(),nullable=False),
        sa.Column('staff_state',sa.String(20),nullable=False),
        sa.Column('notification_state',sa.String(20),nullable=False))
    op.create_table('inquiry_attempt',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('client_key',sa.String(64),nullable=False),sa.Column('attempted_at',sa.DateTime(),nullable=False))
    op.create_index('ix_inquiry_attempt_client_key','inquiry_attempt',['client_key'])
    op.create_index('ix_inquiry_attempt_attempted_at','inquiry_attempt',['attempted_at'])

def downgrade():
    with op.batch_alter_table('promotion') as batch:
        batch.drop_column('reviewed_at')
        batch.drop_column('source')
        batch.drop_column('approval_status')
    op.drop_table('inquiry_attempt')
    op.drop_table('inquiry')
