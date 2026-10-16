from datetime import datetime, timezone, timedelta
import hmac
from functools import wraps
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
from .models import db, Promotion, DisplaySettings, Inquiry, LoginAttempt
from .content import load_content, public_content
from .public.sitemap import PAGES
from .inquiries import notify, OCCASIONS, INTERESTS, FLEXIBILITY, new_submission_token

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
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        key = hmac.new(current_app.secret_key.encode(), (request.remote_addr or "unknown").encode(), "sha256").hexdigest()
        recent = LoginAttempt.attempted_at >= now - timedelta(minutes=15)
        count = db.session.scalar(db.select(db.func.count()).select_from(LoginAttempt).where(LoginAttempt.client_key == key, recent))
        if count >= 10:
            return render_template("admin/login.html", throttled=True), 429, {"Retry-After": "900"}
        db.session.execute(db.delete(LoginAttempt).where(LoginAttempt.attempted_at < now - timedelta(days=1)))
        db.session.add(LoginAttempt(client_key=key, attempted_at=now))
        db.session.commit()
        password_valid = check_password_hash(current_app.config.get("OWNER_PASSWORD_HASH") or DEMO_PASSWORD_HASH, request.form.get("password", ""))
        if request.form.get("username") == current_app.config["OWNER_USERNAME"] and password_valid:
            session.clear()
            session["owner"] = True
            session.permanent = True
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
    unread = db.session.scalar(db.select(db.func.count()).select_from(Inquiry).where(Inquiry.staff_state=='new'))
    notification_alerts = db.session.scalar(db.select(db.func.count()).select_from(Inquiry).where(Inquiry.notification_state.in_(['failed','pending','not_configured'])))
    return render_template("admin/dashboard.html", settings=settings, promotions=promotions,unread=unread,notification_alerts=notification_alerts)


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
    aware = local.replace(tzinfo=LOCAL_TIME)
    round_trip = aware.astimezone(timezone.utc).astimezone(LOCAL_TIME).replace(tzinfo=None)
    if round_trip != local or aware.utcoffset() != local.replace(tzinfo=LOCAL_TIME,fold=1).utcoffset():
        raise ValueError("Choose a time outside the skipped or repeated daylight-saving hour.")
    return aware.astimezone(timezone.utc).replace(tzinfo=None)


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
            if promotion.enabled:
                promotion.approval_status = "approved"
                promotion.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
    if promotion.approval_status != 'approved':
        flash('Review this draft and approve it in the offer editor before publishing.', 'error')
        return redirect(url_for('admin.edit',promotion_id=promotion.id))
    promotion.enabled = not promotion.enabled
    db.session.commit()
    flash("Offer visibility updated.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.get("/images/<filename>")
def uploaded_image(filename):
    if not filename.endswith(".webp"):
        abort(404)
    return send_from_directory(Path(current_app.instance_path) / "uploads", filename)


@admin_bp.after_request
def private_owner_responses(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@admin_bp.get('/inquiries')
@login_required
def inquiries():
    records = db.session.execute(db.select(Inquiry).order_by(Inquiry.received_at.desc())).scalars().all()
    return render_template('admin/inquiries.html',inquiries=records)


@admin_bp.route('/inquiries/<int:inquiry_id>',methods=['GET','POST'])
@login_required
def inquiry_detail(inquiry_id):
    inquiry = db.get_or_404(Inquiry,inquiry_id)
    if request.method == 'POST':
        state = request.form.get('staff_state')
        if state not in ('new','contacted','closed'):
            abort(400)
        inquiry.staff_state=state
        db.session.commit()
        flash('Inquiry status saved.')
        return redirect(url_for('admin.inquiry_detail',inquiry_id=inquiry.id))
    return render_template('admin/inquiry.html',inquiry=inquiry)


@admin_bp.post('/inquiries/<int:inquiry_id>/notify')
@login_required
def retry_notification(inquiry_id):
    inquiry=db.get_or_404(Inquiry,inquiry_id)
    if inquiry.notification_state != 'sent':
        notify(inquiry)
    flash('Staff notification state: '+inquiry.notification_state)
    return redirect(url_for('admin.inquiry_detail',inquiry_id=inquiry.id))


@admin_bp.get('/content-review')
@login_required
def content_review():
    data=load_content()
    return render_template('admin/content_review.html',data=data,pages=PAGES)


@admin_bp.get('/preview/<key>')
@login_required
def preview(key):
    page=next((p for p in PAGES if p['key']==key),None)
    if page is None:
        abort(404)
    return render_template('public/'+key+'.html',page=page,review_mode=True,site_pages=PAGES,current_year=datetime.now().year,**public_content(include_drafts=True),deals=[],coupons=[],values={'submission_token':new_submission_token(),'contact_method':'email','date_flexibility':'Not sure yet','interests':[]},errors={},occasions=OCCASIONS,interests=INTERESTS,flexibilities=FLEXIBILITY)


@admin_bp.get('/source-menu/<filename>')
@login_required
def source_menu(filename):
    folder=Path(__file__).resolve().parent.parent / 'build_docs' / 'source_menu_images'
    return send_from_directory(folder,filename)
