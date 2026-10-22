"""Persist owner sign-in throttling across workers."""
from alembic import op
import sqlalchemy as sa

revision = '3a72d189c401'
down_revision = '1e8469c0a112'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('login_attempt', sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('client_key', sa.String(64), nullable=False),
                    sa.Column('attempted_at', sa.DateTime(), nullable=False))
    op.create_index('ix_login_attempt_client_key', 'login_attempt', ['client_key'])
    op.create_index('ix_login_attempt_attempted_at', 'login_attempt', ['attempted_at'])


def downgrade():
    op.drop_table('login_attempt')
