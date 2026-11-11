from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Promotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    code = db.Column(db.String(60), nullable=False, default="")
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    image = db.Column(db.String(100), nullable=True)

    approval_status = db.Column(db.String(20), nullable=False, default="draft")
    source = db.Column(db.String(300), nullable=False, default="Owner dashboard")
    reviewed_at = db.Column(db.DateTime, nullable=True)
    draft_data = db.Column(db.JSON)
    version_id = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {'version_id_col': version_id}


    @property
    def status(self):
        return self.status_at()

    def status_at(self, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is not None:
            now = now.astimezone(timezone.utc).replace(tzinfo=None)
        if self.approval_status != "approved":
            return "Draft"
        if not self.enabled:
            return "Hidden"
        if self.starts_at and now < self.starts_at:
            return "Scheduled"
        if self.ends_at and now >= self.ends_at:
            return "Expired"
        return "Live"


class DisplaySettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deals_enabled = db.Column(db.Boolean, nullable=False, default=True)
    coupons_enabled = db.Column(db.Boolean, nullable=False, default=True)


def current_promotions(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    live = db.session.scalars(db.select(Promotion).where(
        Promotion.approval_status == 'approved', Promotion.enabled.is_(True),
        db.or_(Promotion.starts_at.is_(None), Promotion.starts_at <= now),
        db.or_(Promotion.ends_at.is_(None), Promotion.ends_at > now),
    ).order_by(Promotion.id.desc())).all()
    return {"deals":[p for p in live if p.kind == "deal"],"coupons":[p for p in live if p.kind == "coupon"]}


def homepage_promotions():
    settings = db.session.get(DisplaySettings, 1)
    visible = current_promotions()
    return {
        "deals": visible["deals"] if not settings or settings.deals_enabled else [],
        "coupons": visible["coupons"] if not settings or settings.coupons_enabled else [],
    }


class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(24), nullable=False, unique=True)
    submission_key = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    contact_method = db.Column(db.String(10), nullable=False)
    contact_detail = db.Column(db.String(254), nullable=False)
    occasion = db.Column(db.String(60), nullable=False)
    guest_count = db.Column(db.Integer, nullable=True)
    preferred_date = db.Column(db.Date, nullable=True)
    date_flexibility = db.Column(db.String(100), nullable=False)
    interests = db.Column(db.JSON, nullable=False)
    notes = db.Column(db.Text, nullable=False, default="")
    received_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    staff_state = db.Column(db.String(32), nullable=False, default="new")
    notification_state = db.Column(db.String(20), nullable=False, default="pending")
    inquiry_type = db.Column(db.String(24), nullable=False, default='event')
    source_route = db.Column(db.String(100), nullable=False, default='/gatherings')
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('staff_user.id'))
    follow_up_at = db.Column(db.DateTime)
    archived_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    contact_normalized = db.Column(db.String(254), nullable=False, default='')
    version_id = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {'version_id_col': version_id}
    __table_args__ = (
        db.CheckConstraint("staff_state IN ('new','contacted','tentative_reservation','confirmed','cancelled','spam','other')", name='ck_inquiry_state'),
        db.CheckConstraint("inquiry_type IN ('event','mini_golf_group','general','other')", name='ck_inquiry_type'),
        db.Index('ix_inquiry_state_received', 'staff_state', 'received_at', 'id'),
        db.Index('ix_inquiry_type_received', 'inquiry_type', 'received_at', 'id'),
        db.Index('ix_inquiry_follow_up', 'assigned_user_id', 'follow_up_at'),
        db.Index('ix_inquiry_preferred_date', 'preferred_date'),
        db.Index('ix_inquiry_contact_normalized', 'contact_normalized'),
        db.Index('ix_inquiry_active_type_state', 'archived_at', 'inquiry_type', 'staff_state'),
    )



class InquiryAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_key = db.Column(db.String(64), nullable=False, index=True)
    attempted_at = db.Column(db.DateTime, nullable=False, index=True)


class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_key = db.Column(db.String(64), nullable=False, index=True)
    attempted_at = db.Column(db.DateTime, nullable=False, index=True)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class StaffUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='inquiry')
    active = db.Column(db.Boolean, nullable=False, default=True)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime)
    __table_args__ = (db.CheckConstraint("role IN ('owner','editor','inquiry')", name='ck_staff_role'),)


class ContentRecord(db.Model):
    """Stable identity with independent draft and published revision pointers.

    Revision JSON retains the existing public content contract; prices are stored
    in integer cents. Identity, order, parent and versions remain relational.
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    kind = db.Column(db.String(20), nullable=False, index=True)
    parent_key = db.Column(db.String(100), db.ForeignKey('content_record.key'))
    position = db.Column(db.Integer, nullable=False, default=0)
    draft_id = db.Column(db.Integer, db.ForeignKey('content_revision.id', use_alter=True, name='fk_content_draft'))
    published_id = db.Column(db.Integer, db.ForeignKey('content_revision.id', use_alter=True, name='fk_content_published'))
    archived = db.Column(db.Boolean, nullable=False, default=False)
    unavailable = db.Column(db.Boolean, nullable=False, default=False)
    version_id = db.Column(db.Integer, nullable=False, default=1)
    draft = db.relationship('ContentRevision', foreign_keys=[draft_id], post_update=True)
    published = db.relationship('ContentRevision', foreign_keys=[published_id], post_update=True)
    __mapper_args__ = {'version_id_col': version_id}
    __table_args__ = (db.CheckConstraint("kind IN ('category','item','weekly','recurring','settings')", name='ck_content_kind'),)


class ContentRevision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('content_record.id'), nullable=False, index=True)
    data = db.Column(db.JSON, nullable=False)
    actor = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(60), nullable=False)
    entity = db.Column(db.String(120), nullable=False)
    summary = db.Column(db.String(300), nullable=False, default='')
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class InquiryNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False, index=True)
    actor = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class InquiryHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False, index=True)
    old_state = db.Column(db.String(32))
    new_state = db.Column(db.String(32), nullable=False)
    actor = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.String(1000), nullable=False, default='')
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class NotificationOutbox(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False, unique=True)
    state = db.Column(db.String(20), nullable=False, default='pending')
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    lease_until = db.Column(db.DateTime)
    lease_token = db.Column(db.String(40))
    last_error = db.Column(db.String(100))
    sent_at = db.Column(db.DateTime)
    __table_args__ = (db.Index('ix_outbox_due', 'state', 'next_attempt_at'),)


class RateBucket(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    window = db.Column(db.Integer, nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)


class MediaAsset(db.Model):
    id = db.Column(db.String(32), primary_key=True)
    alt = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.String(500), nullable=False, default='')
    source = db.Column(db.String(300), nullable=False, default='Staff upload')
    variants = db.Column(db.JSON, nullable=False)
    public = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class BackendSetting(db.Model):
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text, nullable=False)


# db.create_all() test fixtures receive the same transactional search index as
# migrated SQLite installations. Alembic's table objects use their own metadata.
from sqlalchemy import event


@event.listens_for(InquiryNote.__table__, 'after_create')
def create_inquiry_search(target, connection, **kwargs):
    from .services.search import install_search_v1
    install_search_v1(connection)


@event.listens_for(InquiryNote.__table__, 'before_drop')
def drop_inquiry_search(target, connection, **kwargs):
    if connection.dialect.name == 'sqlite':
        for name in ['inquiry_search_insert', 'inquiry_search_update', 'inquiry_search_delete', 'inquiry_note_search_insert', 'inquiry_note_search_update', 'inquiry_note_search_delete']:
            connection.exec_driver_sql('DROP TRIGGER IF EXISTS ' + name)
        connection.exec_driver_sql('DROP TABLE IF EXISTS inquiry_search')
