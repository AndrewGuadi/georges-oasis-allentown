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

    @property
    def status(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
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


def homepage_promotions():
    settings = db.session.get(DisplaySettings, 1)
    live = [p for p in db.session.execute(db.select(Promotion).order_by(Promotion.id.desc())).scalars() if p.status == "Live"]
    return {
        "deals": [p for p in live if p.kind == "deal"] if not settings or settings.deals_enabled else [],
        "coupons": [p for p in live if p.kind == "coupon"] if not settings or settings.coupons_enabled else [],
    }
