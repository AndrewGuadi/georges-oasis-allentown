from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
from .models import db, Promotion, DisplaySettings

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
DEMO_PASSWORD_HASH = generate_password_hash("password")
LOCAL_TIME = ZoneInfo("America/New_York")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("owner"):
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "username" and check_password_hash(DEMO_PASSWORD_HASH, request.form.get("password", "")):
            session.clear()
            session["owner"] = True
            return redirect(url_for("admin.dashboard"))
        flash("The username or password is incorrect.", "error")
    return render_template("admin/login.html")


@admin_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.get("")
@admin_bp.get("/")
@login_required
def dashboard():
    settings = db.session.get(DisplaySettings, 1) or DisplaySettings(deals_enabled=True, coupons_enabled=True)
    promotions = db.session.execute(db.select(Promotion).order_by(Promotion.id.desc())).scalars().all()
    return render_template("admin/dashboard.html", settings=settings, promotions=promotions)


@admin_bp.post("/display")
@login_required
def display():
    settings = db.session.get(DisplaySettings, 1)
    if settings is None:
        settings = DisplaySettings(id=1)
        db.session.add(settings)
    settings.deals_enabled = "deals_enabled" in request.form
    settings.coupons_enabled = "coupons_enabled" in request.form
    db.session.commit()
    flash("Homepage visibility saved.")
    return redirect(url_for("admin.dashboard"))


def parse_time(value):
    if not value:
        return None
    local = datetime.fromisoformat(value)
    if local.tzinfo is not None:
        raise ValueError("Use a local date and time.")
    return local.replace(tzinfo=LOCAL_TIME).astimezone(timezone.utc).replace(tzinfo=None)


@admin_bp.app_template_filter("local_input")
def local_input(value):
    return value.replace(tzinfo=timezone.utc).astimezone(LOCAL_TIME).strftime("%Y-%m-%dT%H:%M") if value else ""


@admin_bp.route("/promotions/new", methods=["GET", "POST"])
@admin_bp.route("/promotions/<int:promotion_id>/edit", methods=["GET", "POST"])
@login_required
def edit(promotion_id=None):
    promotion = db.get_or_404(Promotion, promotion_id) if promotion_id else Promotion(kind="deal", enabled=False)
    if request.method == "POST":
        try:
            kind = request.form.get("kind")
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            code = request.form.get("code", "").strip()
            start = parse_time(request.form.get("starts_at"))
            end = parse_time(request.form.get("ends_at"))
            if kind not in ("deal", "coupon") or not title or len(title) > 120 or len(description) > 4000 or len(code) > 60:
                raise ValueError("Enter a title (up to 120 characters), description (up to 4,000), and optional code (up to 60).")
            if start and end and end <= start:
                raise ValueError("The end must be later than the start.")
            image_name = promotion.image
            upload = request.files.get("image")
            if upload and upload.filename:
                try:
                    with Image.open(upload.stream) as picture:
                        if picture.format not in ("JPEG", "PNG", "WEBP") or picture.width * picture.height > 20000000:
                            raise ValueError("Choose a JPG, PNG, or WebP image up to 20 megapixels.")
                        picture.load()
                        picture.thumbnail((1600, 1600))
                        folder = Path(current_app.instance_path) / "uploads"
                        folder.mkdir(exist_ok=True)
                        image_name = uuid4().hex + ".webp"
                        picture.convert("RGB").save(folder / image_name, "WEBP", quality=85)
                except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                    raise ValueError("That image could not be read. Choose a JPG, PNG, or WebP image.") from exc
            elif "remove_image" in request.form:
                image_name = None
            promotion.kind, promotion.title, promotion.description = kind, title, description
            promotion.code, promotion.starts_at, promotion.ends_at = code, start, end
            promotion.enabled, promotion.image = "enabled" in request.form, image_name
            db.session.add(promotion)
            db.session.commit()
            flash("Offer saved. Live offers now appear on the homepage.")
            return redirect(url_for("admin.dashboard"))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("admin/edit.html", promotion=promotion)


@admin_bp.post("/promotions/<int:promotion_id>/toggle")
@login_required
def toggle(promotion_id):
    promotion = db.get_or_404(Promotion, promotion_id)
    promotion.enabled = not promotion.enabled
    db.session.commit()
    flash("Offer visibility updated.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.get("/images/<filename>")
def uploaded_image(filename):
    if not filename.endswith(".webp"):
        abort(404)
    return send_from_directory(Path(current_app.instance_path) / "uploads", filename)
