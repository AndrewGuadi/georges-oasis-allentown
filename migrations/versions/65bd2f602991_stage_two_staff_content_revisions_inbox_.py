"""Stage two staff content revisions inbox and durable notification queue

Revision ID: 65bd2f602991
Revises: 3a72d189c401
Create Date: 2026-11-11 19:46:16.043960

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import re


# revision identifiers, used by Alembic.
revision = '65bd2f602991'
down_revision = '3a72d189c401'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    legacy = connection.execute(sa.text('SELECT id, staff_state FROM inquiry')).mappings().all()
    if any(row['staff_state'] not in {'new','contacted','closed'} for row in legacy):
        raise RuntimeError('Unknown legacy inquiry state: resolve explicitly before upgrading.')
    connection.execute(sa.text("UPDATE inquiry SET staff_state='other' WHERE staff_state='closed'"))
    with op.batch_alter_table('promotion') as batch_op:
        batch_op.add_column(sa.Column('draft_data', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('version_id', sa.Integer(), nullable=False, server_default='1'))
    op.create_table('audit_event',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('actor', sa.String(length=100), nullable=False),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('entity', sa.String(length=120), nullable=False),
    sa.Column('summary', sa.String(length=300), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('backend_setting',
    sa.Column('key', sa.String(length=60), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('content_record',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('parent_key', sa.String(length=100), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('draft_id', sa.Integer(), nullable=True),
    sa.Column('published_id', sa.Integer(), nullable=True),
    sa.Column('archived', sa.Boolean(), nullable=False),
    sa.Column('unavailable', sa.Boolean(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False, server_default='1'),
    sa.CheckConstraint("kind IN ('category','item','weekly','recurring','settings')", name='ck_content_kind'),
    sa.ForeignKeyConstraint(['draft_id'], ['content_revision.id'], name='fk_content_draft', use_alter=True),
    sa.ForeignKeyConstraint(['parent_key'], ['content_record.key'], ),
    sa.ForeignKeyConstraint(['published_id'], ['content_revision.id'], name='fk_content_published', use_alter=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    with op.batch_alter_table('content_record', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_content_record_kind'), ['kind'], unique=False)

    op.create_table('media_asset',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('alt', sa.String(length=300), nullable=False),
    sa.Column('caption', sa.String(length=500), nullable=False),
    sa.Column('source', sa.String(length=300), nullable=False),
    sa.Column('variants', sa.JSON(), nullable=False),
    sa.Column('public', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rate_bucket',
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('window', sa.Integer(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('staff_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('display_name', sa.String(length=100), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('session_version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("role IN ('owner','editor','inquiry')", name='ck_staff_role'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('content_revision',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('record_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('actor', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['record_id'], ['content_record.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('content_revision', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_content_revision_record_id'), ['record_id'], unique=False)

    op.create_table('inquiry_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('inquiry_id', sa.Integer(), nullable=False),
    sa.Column('old_state', sa.String(length=32), nullable=True),
    sa.Column('new_state', sa.String(length=32), nullable=False),
    sa.Column('actor', sa.String(length=100), nullable=False),
    sa.Column('reason', sa.String(length=1000), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['inquiry_id'], ['inquiry.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('inquiry_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_inquiry_history_inquiry_id'), ['inquiry_id'], unique=False)

    op.create_table('inquiry_note',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('inquiry_id', sa.Integer(), nullable=False),
    sa.Column('actor', sa.String(length=100), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['inquiry_id'], ['inquiry.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('inquiry_note', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_inquiry_note_inquiry_id'), ['inquiry_id'], unique=False)

    op.create_table('notification_outbox',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('inquiry_id', sa.Integer(), nullable=False),
    sa.Column('state', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', sa.DateTime(), nullable=False),
    sa.Column('lease_until', sa.DateTime(), nullable=True),
    sa.Column('lease_token', sa.String(length=40), nullable=True),
    sa.Column('last_error', sa.String(length=100), nullable=True),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['inquiry_id'], ['inquiry.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('inquiry_id')
    )
    with op.batch_alter_table('notification_outbox', schema=None) as batch_op:
        batch_op.create_index('ix_outbox_due', ['state', 'next_attempt_at'], unique=False)

    with op.batch_alter_table('inquiry', schema=None) as batch_op:
        batch_op.add_column(sa.Column('inquiry_type', sa.String(length=24), nullable=False, server_default='event'))
        batch_op.add_column(sa.Column('source_route', sa.String(length=100), nullable=False, server_default='/gatherings'))
        batch_op.add_column(sa.Column('assigned_user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('follow_up_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()))
        batch_op.add_column(sa.Column('contact_normalized', sa.String(length=254), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('version_id', sa.Integer(), nullable=False, server_default='1'))
        batch_op.alter_column('staff_state',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.String(length=32),
               existing_nullable=False)
        batch_op.create_index('ix_inquiry_contact_normalized', ['contact_normalized'], unique=False)
        batch_op.create_index('ix_inquiry_follow_up', ['assigned_user_id', 'follow_up_at'], unique=False)
        batch_op.create_index('ix_inquiry_preferred_date', ['preferred_date'], unique=False)
        batch_op.create_index('ix_inquiry_state_received', ['staff_state', 'received_at', 'id'], unique=False)
        batch_op.create_index('ix_inquiry_type_received', ['inquiry_type', 'received_at', 'id'], unique=False)
        batch_op.create_foreign_key('fk_inquiry_assigned_staff', 'staff_user', ['assigned_user_id'], ['id'])
        batch_op.create_check_constraint('ck_inquiry_state', "staff_state IN ('new','contacted','tentative_reservation','confirmed','cancelled','spam','other')")
        batch_op.create_check_constraint('ck_inquiry_type', "inquiry_type IN ('event','mini_golf_group','general','other')")

    connection = op.get_bind()
    legacy_states = {row['id']: row['staff_state'] for row in legacy}
    known = {'new', 'contacted', 'other'}
    records = connection.execute(sa.text('SELECT id, staff_state, contact_method, contact_detail, received_at FROM inquiry')).mappings().all()
    if any(row['staff_state'] not in known for row in records):
        raise RuntimeError('Unknown legacy inquiry state: resolve explicitly before upgrading.')
    for row in records:
        contact = re.sub(r'\D', '', row['contact_detail']) if row['contact_method'] == 'phone' else row['contact_detail'].casefold()
        state = row['staff_state']
        connection.execute(sa.text('UPDATE inquiry SET contact_normalized=:contact, staff_state=:state, updated_at=received_at WHERE id=:id'), {'contact': contact, 'state': state, 'id': row['id']})
        connection.execute(sa.text('INSERT INTO inquiry_history (inquiry_id, old_state, new_state, actor, reason, created_at) VALUES (:id, :old, :state, :actor, :reason, :at)'), {'id': row['id'], 'old': legacy_states[row['id']], 'state': state, 'actor': 'stage-two-migration', 'reason': 'Legacy closed mapped to Other; outcome requires staff review.' if state == 'other' else 'Existing inquiry preserved during migration.', 'at': datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None)})


    if connection.dialect.name == 'postgresql':
        op.create_foreign_key('fk_content_draft', 'content_record', 'content_revision', ['draft_id'], ['id'])
        op.create_foreign_key('fk_content_published', 'content_record', 'content_revision', ['published_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    raise RuntimeError('Stage two contains staff revisions and inquiry history. Roll back the application with the expanded schema, or restore a rehearsed pre-upgrade backup with writes stopped; automatic schema downgrade would discard staff data.')
