from datetime import datetime, timezone, timedelta
import hmac
from functools import wraps
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
from .models import db, Promotion, DisplaySettings, Inquiry, LoginAttempt, StaffUser, NotificationOutbox, ContentRecord, utcnow
from .services.auth import require_roles, audit
from .services.abuse import take_limit
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
        now = utcnow()
        raw_username = request.form.get('username', '').strip().casefold()
        username = raw_username[:80]
        ip_allowed = take_limit('login-ip', request.remote_addr or 'unknown', 10)
        account_allowed = take_limit('login-account', username, 20)
        if not ip_allowed or not account_allowed:
            return render_template('admin/login.html', throttled=True), 429, {'Retry-After': '900'}
        user = db.session.scalar(db.select(StaffUser).where(StaffUser.username == username))
        has_users = db.session.scalar(db.select(db.func.count()).select_from(StaffUser))
        fallback = current_app.config.get('OWNER_PASSWORD_HASH') or DEMO_PASSWORD_HASH
        submitted_password = request.form.get('password', '')
        valid = check_password_hash(user.password_hash if user else fallback, submitted_password if len(submitted_password)<=256 else '') and len(submitted_password)<=256 and len(raw_username)<=80
        if valid and ((user and user.active) or (not has_users and username == current_app.config['OWNER_USERNAME'].casefold())):
            session.clear()
            session['owner'] = True
            session['staff_login_at'] = now.replace(tzinfo=timezone.utc).timestamp()
            session['staff_last_seen'] = session['staff_login_at']
            if user:
                session['staff_id'], session['staff_version'] = user.id, user.session_version
                user.last_login_at = now
                db.session.commit()
            session.permanent = True
            return redirect(url_for('admin.dashboard'))
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
    from flask import g
    if g.staff and g.staff.role == 'inquiry':
        return redirect(url_for('admin.inquiries'))
    settings = db.session.get(DisplaySettings, 1) or DisplaySettings(deals_enabled=True, coupons_enabled=True)
    page = db.paginate(db.select(Promotion).order_by(Promotion.id.desc()), per_page=25, error_out=False)
    promotions = page.items
    unread = db.session.scalar(db.select(db.func.count()).select_from(Inquiry).where(Inquiry.staff_state=='new', Inquiry.archived_at.is_(None)))
    notification_alerts = db.session.scalar(db.select(db.func.count()).select_from(Inquiry).where(Inquiry.notification_state.in_(['failed','pending','not_configured'])))
    overdue = db.session.scalar(db.select(db.func.count()).select_from(Inquiry).where(Inquiry.archived_at.is_(None), Inquiry.follow_up_at <= utcnow(), Inquiry.staff_state.notin_(['cancelled','spam','confirmed'])))
    drafts = db.session.scalar(db.select(db.func.count()).select_from(ContentRecord).where(db.or_(ContentRecord.published_id.is_(None), ContentRecord.draft_id != ContentRecord.published_id)))
    return render_template('admin/dashboard.html', settings=settings, promotions=promotions, unread=unread, notification_alerts=notification_alerts, overdue=overdue, drafts=drafts, page=page)


@admin_bp.post("/display")
@require_roles('owner', 'editor')
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
@require_roles('owner', 'editor')
def edit(promotion_id=None):
    promotion = db.get_or_404(Promotion, promotion_id) if promotion_id else Promotion(kind="deal", enabled=False)
    if request.method == "POST":
        try:
            if promotion.id:
                from .backend import expected
                expected(promotion)
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
            image_name = (promotion.draft_data or {}).get("image", promotion.image)
            upload = request.files.get("image")
            if upload and upload.filename:
                try:
                    upload.stream.seek(0, 2)
                    if upload.stream.tell() > 4 * 1024 * 1024:
                        raise ValueError('Choose an image smaller than 4 MiB.')
                    upload.stream.seek(0)
                    with Image.open(upload.stream) as picture:
                        if getattr(picture, "n_frames", 1) != 1 or picture.format not in ("JPEG", "PNG", "WEBP") or picture.width * picture.height > 20000000:
                            raise ValueError("Choose a JPG, PNG, or WebP image up to 20 megapixels.")
                        picture.load()
                        from PIL import ImageOps
                        picture = ImageOps.exif_transpose(picture)
                        picture.thumbnail((1600, 1600))
                        folder = Path(current_app.instance_path) / "uploads"
                        folder.mkdir(exist_ok=True)
                        image_name = uuid4().hex + ".webp"
                        picture.convert("RGB").save(folder / image_name, "WEBP", quality=85)
                except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                    raise ValueError("That image could not be read. Choose a JPG, PNG, or WebP image.") from exc
            elif "remove_image" in request.form:
                image_name = None
            action = request.form.get('action', 'draft')
            if action not in ('draft', 'publish'):
                abort(400)
            payload = dict(kind=kind, title=title, description=description, code=code, starts_at=start.isoformat() if start else None, ends_at=end.isoformat() if end else None, enabled='enabled' in request.form, image=image_name)
            if not promotion.id:
                promotion.title = title
            promotion.draft_data = payload
            if action == 'publish':
                for field in ('kind', 'title', 'description', 'code', 'enabled', 'image'):
                    setattr(promotion, field, payload[field])
                promotion.starts_at, promotion.ends_at = start, end
                promotion.approval_status = 'approved'
                promotion.reviewed_at = utcnow()
            promotion.version_id = (promotion.version_id or 1) + 1
            db.session.add(promotion)
            db.session.flush()
            audit('promotion.' + action, promotion.id)
            from .backend import commit
            commit()
            flash('Offer published.' if action == 'publish' else 'Offer draft saved. Published content is unchanged.')
            return redirect(url_for('admin.dashboard'))
        except ValueError as error:
            flash(str(error), "error")
    from types import SimpleNamespace
    display_promotion = promotion
    if promotion.draft_data:
        display_promotion = SimpleNamespace(**{column.name: getattr(promotion, column.name) for column in Promotion.__table__.columns})
        for field, value in promotion.draft_data.items():
            setattr(display_promotion, field, datetime.fromisoformat(value) if field in ('starts_at', 'ends_at') and value else value)
    return render_template('admin/edit.html', promotion=display_promotion)


@admin_bp.post("/promotions/<int:promotion_id>/toggle")
@require_roles('owner', 'editor')
def toggle(promotion_id):
    promotion = db.get_or_404(Promotion, promotion_id)
    from .backend import expected
    expected(promotion)
    if promotion.approval_status != 'approved':
        flash('Review this draft and approve it in the offer editor before publishing.', 'error')
        return redirect(url_for('admin.edit',promotion_id=promotion.id))
    promotion.enabled = not promotion.enabled
    audit('promotion.toggle', promotion.id)
    from .backend import commit
    commit()
    flash("Offer visibility updated.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.get("/images/<filename>")
def uploaded_image(filename):
    if not filename.endswith(".webp"):
        abort(404)
    published = db.session.scalar(db.select(Promotion.id).where(Promotion.image == filename, Promotion.approval_status == 'approved').limit(1))
    if not published and not session.get('owner'):
        abort(404)
    return send_from_directory(Path(current_app.instance_path) / "uploads", filename)


@admin_bp.after_request
def private_owner_responses(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@admin_bp.get('/inquiries')
@require_roles('owner', 'inquiry')
def inquiries():
    from .backend import render_inbox
    return render_inbox()


@admin_bp.route('/inquiries/<int:inquiry_id>',methods=['GET','POST'])
@require_roles('owner', 'inquiry')
def inquiry_detail(inquiry_id):
    from .backend import inquiry_view
    return inquiry_view(inquiry_id)


@admin_bp.post('/inquiries/<int:inquiry_id>/notify')
@require_roles('owner', 'inquiry')
def retry_notification(inquiry_id):
    inquiry=db.get_or_404(Inquiry,inquiry_id)
    from .services.notifications import configured
    if inquiry.staff_state == 'spam':
        flash('Restore this request from spam before queuing a notification.', 'error')
    elif configured() and inquiry.notification_state != 'sent':
        row = db.session.scalar(db.select(NotificationOutbox).where(NotificationOutbox.inquiry_id == inquiry.id))
        if row and row.state == 'sending' and row.lease_until and row.lease_until > utcnow():
            flash('A worker is already sending this notification.')
            return redirect(url_for('admin.inquiry_detail', inquiry_id=inquiry.id))
        if row:
            row.state, row.attempts, row.next_attempt_at = 'pending', 0, utcnow()
        else:
            db.session.add(NotificationOutbox(inquiry_id=inquiry.id))
        inquiry.notification_state = 'pending'
        audit('notification.retry', inquiry.reference)
        db.session.commit()
        flash('Staff notification queued.')
    else:
        flash('Notification already sent or delivery is not configured.')
    return redirect(url_for('admin.inquiry_detail',inquiry_id=inquiry.id))


@admin_bp.get('/content-review')
@require_roles('owner', 'editor')
def content_review():
    data=load_content()
    return render_template('admin/content_review.html',data=data,pages=PAGES)


@admin_bp.get('/preview/<key>')
@require_roles('owner', 'editor')
def preview(key):
    page=next((p for p in PAGES if p['key']==key),None)
    if page is None:
        abort(404)
    return render_template('public/'+key+'.html',page=page,review_mode=True,site_pages=PAGES,current_year=datetime.now().year,**public_content(include_drafts=True),deals=[],coupons=[],values={'submission_token':new_submission_token(),'contact_method':'email','date_flexibility':'Not sure yet','interests':[]},errors={},occasions=OCCASIONS,interests=INTERESTS,flexibilities=FLEXIBILITY)


@admin_bp.get('/source-menu/<filename>')
@require_roles('owner', 'editor')
def source_menu(filename):
    folder=Path(__file__).resolve().parent.parent / 'build_docs' / 'source_menu_images'
    return send_from_directory(folder,filename)


@admin_bp.get('/promotions/<int:promotion_id>/preview')
@require_roles('owner', 'editor')
def promotion_preview(promotion_id):
    from types import SimpleNamespace
    promotion = db.get_or_404(Promotion, promotion_id)
    offer = SimpleNamespace(**{column.name: getattr(promotion, column.name) for column in Promotion.__table__.columns})
    for field, value in (promotion.draft_data or {}).items():
        setattr(offer, field, datetime.fromisoformat(value) if field in ('starts_at', 'ends_at') and value else value)
    return render_template('admin/offer_preview.html', offer=offer)
