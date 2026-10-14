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
    live = [p for p in db.session.execute(db.select(Promotion).order_by(Promotion.id.desc())).scalars() if p.status_at(now) == "Live"]
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
    staff_state = db.Column(db.String(20), nullable=False, default="new")
    notification_state = db.Column(db.String(20), nullable=False, default="pending")


class InquiryAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_key = db.Column(db.String(64), nullable=False, index=True)
    attempted_at = db.Column(db.DateTime, nullable=False, index=True)
