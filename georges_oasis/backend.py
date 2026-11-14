"""Stage-two staff tools, using shared content and inquiry services."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import csv
import io
import re
from uuid import uuid4
from flask import Blueprint, abort, current_app, flash, g, make_response, redirect, render_template, request, send_from_directory, session, url_for
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from .models import (db, ContentRecord, ContentRevision, Inquiry, InquiryNote, InquiryHistory,
                     StaffUser, MediaAsset, NotificationOutbox, utcnow)
from .services.auth import require_roles, actor, audit
from .services.catalog import KINDS, to_public, to_storage, save_revision
from .services.media import upload_image

backend_bp = Blueprint('backend', __name__)
STATES = {'new': 'New', 'contacted': 'Contacted', 'tentative_reservation': 'Tentative reservation', 'confirmed': 'Confirmed', 'cancelled': 'Cancelled', 'spam': 'Fake / spam', 'other': 'Other'}
TYPES = {'event': 'Event', 'mini_golf_group': 'Mini golf group', 'general': 'General', 'other': 'Other'}
ALL = ('owner', 'editor', 'inquiry')
FILTER_KEYS = {'q','staff_state','inquiry_type','notification_state','occasion','interest','due','include_spam','archived','assigned_user_id','received_from','received_until','event_from','event_until','page','sort'}


def expected(record):
    if request.form.get('version_id') != str(record.version_id):
        abort(409, description='Another staff member saved this record. Copy your changes, reload, and review the current version before saving.')


def commit():
    try:
        db.session.commit()
    except StaleDataError:
        db.session.rollback()
        abort(409, description='This record changed while you were editing. Reload and review before saving.')
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error('Staff database save failed; no success response was issued.')
        abort(503, description='Your changes could not be saved. Copy the submitted values below and retry.')


@backend_bp.after_request
def private(response):
    if request.path.startswith('/admin'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@backend_bp.get('/admin/settings')
@require_roles('owner')
def settings():
    record = db.session.scalar(db.select(ContentRecord).where(ContentRecord.key == 'catalog-settings'))
    if not record:
        abort(404, description='Import the catalog before editing publication settings.')
    return redirect(url_for('backend.content_edit', record_id=record.id))


@backend_bp.get('/admin/menu', defaults={'specials': False})
@backend_bp.get('/admin/specials', endpoint='specials_catalog', defaults={'specials': True})
@require_roles('owner', 'editor')
def catalog(specials):
    kinds = ['weekly', 'recurring'] if specials else ['category', 'item', 'settings']
    query = db.select(ContentRecord).options(joinedload(ContentRecord.draft), joinedload(ContentRecord.published)).where(ContentRecord.kind.in_(kinds))
    category = request.args.get('category', '')
    if category:
        query = query.where(ContentRecord.parent_key == category)
    state = request.args.get('state', '')
    if state == 'archived':
        query = query.where(ContentRecord.archived.is_(True))
    elif state == 'unavailable':
        query = query.where(ContentRecord.unavailable.is_(True))
    elif state == 'draft':
        query = query.where(db.or_(ContentRecord.published_id.is_(None), ContentRecord.draft_id != ContentRecord.published_id))
    elif state == 'unreviewed':
        query = query.where(ContentRecord.kind == 'item', ContentRecord.draft.has(ContentRevision.data['prices_reviewed'].as_boolean().is_not(True)))
    q = request.args.get('q', '').strip()[:120]
    if q:
        escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.where(ContentRecord.draft.has(db.or_(ContentRevision.data['name'].as_string().ilike('%' + escaped + '%', escape='\\'), ContentRevision.data['title'].as_string().ilike('%' + escaped + '%', escape='\\'))))
    page = db.paginate(query.order_by(ContentRecord.kind, ContentRecord.parent_key, ContentRecord.position, ContentRecord.id), per_page=25, max_per_page=100, error_out=False)
    categories = db.session.scalars(db.select(ContentRecord).options(joinedload(ContentRecord.draft)).where(ContentRecord.kind == 'category').order_by(ContentRecord.position)).all()
    return render_template('admin/catalog.html', page=page, specials=specials, kinds=KINDS, categories=categories)


def options(text, label):
    result = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split('|')
        if len(parts) != 2 or not parts[0].strip() or len(parts[0]) > 160:
            raise ValueError('Enter each option as label | price. Leave the price blank if it should be omitted.')
        result.append({label: parts[0].strip(), 'price': parts[1].strip()})
    if len(result) > 50:
        raise ValueError('Use at most 50 options.')
    return result


def form_data(record):
    data = to_public(record.draft.data) if record.draft else {}
    form = request.form
    if record.kind == 'settings':
        data['weekly_special_days'] = [int(v) for v in form.getlist('weekdays')]
        data['menu_pricing'] = {'show_prices': 'show_prices' in form, 'note': 'For current prices, check the ordering menu or ask the restaurant.', 'metadata': data.get('menu_pricing', {}).get('metadata', {})}
        return to_storage(data)
    for field in ('name', 'title', 'description', 'intro', 'group', 'inclusions', 'price_note', 'terms', 'note', 'summary', 'photo', 'photo_alt', 'photo_caption'):
        if field in form:
            data[field] = form[field].strip()
    data['id'] = data.get('id', record.key.split(':')[-1])
    data['metadata'] = data.get('metadata', {}) | {'source': form.get('source', '').strip(), 'valid_from': form.get('valid_from') or None, 'valid_until': form.get('valid_until') or None}
    if record.kind in ('item', 'recurring'):
        data['price'] = form.get('price') or None
    if record.kind == 'item':
        data['variants'] = options(form.get('variants', ''), 'label')
        data['add_ons'] = options(form.get('add_ons', ''), 'name')
    if record.kind in ('weekly', 'recurring'):
        data['weekday'] = int(form.get('weekday', '-1'))
    if record.kind == 'recurring':
        data['start_time'], data['end_time'] = form.get('start_time'), form.get('end_time')
    if record.kind == 'weekly':
        items = []
        for line in form.get('dishes', '').splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) > 3 or not parts[0] or len(parts[0]) > 160:
                raise ValueError('Each dish: Name | Description | Optional price.')
            items.append({'name': parts[0], 'description': parts[1] if len(parts) > 1 else '', 'price': parts[2] if len(parts) > 2 else None})
        if len(items) > 100:
            raise ValueError('Use at most 100 dishes.')
        data['items'] = items
    data = to_storage(data)
    # Review applies to this exact submitted set of prices, not a previous version.
    data['prices_reviewed'] = 'prices_reviewed' in form
    if record.kind in ('weekly', 'recurring'):
        setting = db.session.scalar(db.select(ContentRecord).where(ContentRecord.key == 'catalog-settings'))
        if setting and data['weekday'] not in setting.draft.data['weekly_special_days']:
            raise ValueError('Enable this weekday in publication settings first.')
    photo = data.get('photo')
    if photo:
        if photo.startswith('upload:'):
            if not db.session.get(MediaAsset, photo[7:]):
                raise ValueError('Choose an existing image.')
        elif photo not in current_app.extensions['oasis_assets']:
            legacy = Path(current_app.static_folder) / 'images' / 'optimized' / (Path(photo).stem + '.webp')
            if not legacy.is_file():
                raise ValueError('Choose an image from the media library.')
    return data


@backend_bp.route('/admin/content/new/<kind>', methods=['GET', 'POST'])
@backend_bp.route('/admin/content/<int:record_id>', methods=['GET', 'POST'])
@require_roles('owner', 'editor')
def content_edit(record_id=None, kind=None):
    record = db.get_or_404(ContentRecord, record_id) if record_id else None
    if not record and kind not in ('category', 'item', 'weekly', 'recurring'):
        abort(404)
    error, status = None, 200
    if record and record.kind == 'settings' and g.staff and g.staff.role != 'owner':
        abort(403)
    if request.method == 'POST':
        try:
            if record:
                expected(record)
            else:
                record = ContentRecord(key=kind + '-' + uuid4().hex[:12], kind=kind)
                db.session.add(record)
                db.session.flush()
            action = request.form.get('action', 'draft')
            if action not in ('draft', 'publish', 'pause', 'archive', 'restore', 'duplicate'):
                abort(400)
            if action in ('pause', 'archive'):
                record.published_id = None
                record.archived = action == 'archive'
                record.version_id += 1
                audit('content.' + action, record.key)
            elif action == 'restore':
                revision = db.get_or_404(ContentRevision, request.form.get('revision_id', type=int))
                if revision.record_id != record.id:
                    abort(404)
                save_revision(record, revision.data, 'draft')
            elif action == 'duplicate':
                duplicate = ContentRecord(key=record.kind + '-' + uuid4().hex[:12], kind=record.kind, parent_key=record.parent_key, position=record.position + 1)
                db.session.add(duplicate)
                db.session.flush()
                data = deepcopy(record.draft.data)
                data['id'] = duplicate.key
                data['metadata'] = data.get('metadata', {}) | {'status': 'draft'}
                save_revision(duplicate, data, 'draft')
                record = duplicate
            else:
                data = form_data(record)
                position = int(request.form.get('position', '0'))
                if not 0 <= position <= 10000:
                    raise ValueError('Order must be between 0 and 10,000.')
                data["_position"] = position
                if record.kind == 'item':
                    parent = db.session.scalar(db.select(ContentRecord).where(ContentRecord.key == request.form.get('parent_key'), ContentRecord.kind == 'category'))
                    if not parent:
                        raise ValueError('Choose a menu category.')
                    data["_parent_key"] = parent.key
                record.unavailable = 'unavailable' in request.form
                if record.kind == 'settings' and session.get('staff_id') and g.staff.role != 'owner':
                    abort(403)
                save_revision(record, data, action)
            commit()
            flash('Content saved.' + (' Published changes are now live.' if action == 'publish' else ''))
            return redirect(url_for('backend.content_edit', record_id=record.id))
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            error, status = str(exc), 400
            if record and record.id and db.session.get(ContentRecord, record.id) is None:
                record = None
    kind = record.kind if record else kind
    data = to_public(record.draft.data) if record and record.draft else {}
    categories = db.session.scalars(db.select(ContentRecord).options(joinedload(ContentRecord.draft)).where(ContentRecord.kind == 'category').order_by(ContentRecord.position)).all()
    revisions = db.session.scalars(db.select(ContentRevision).where(ContentRevision.record_id == record.id).order_by(ContentRevision.id.desc()).limit(30)).all() if record else []
    photos = [(key, value.get('alt', key)) for key, value in current_app.extensions['oasis_assets'].items()]
    photos += [('upload:' + m.id, m.alt) for m in db.session.scalars(db.select(MediaAsset).order_by(MediaAsset.created_at.desc()).limit(200))]
    comparison = []
    previous = to_public(record.published.data) if record and record.published else {}
    for field, label in [('name','Name'),('title','Title'),('description','Description'),('intro','Introduction'),('group','Group'),('inclusions','Inclusions'),('price','Base price (USD)'),('price_note','Price note'),('variants','Variants'),('add_ons','Additions'),('items','Dishes'),('terms','Terms'),('summary','Public summary'),('note','Note'),('weekday','Weekday'),('start_time','Starts'),('end_time','Ends'),('prices_reviewed','Prices reviewed'),('photo_alt','Image description'),('menu_pricing','Public prices'),('weekly_special_days','Specials days')]:
        def display(value):
            if isinstance(value, list):
                return '\n'.join(' | '.join(str(v) for k,v in entry.items() if k != 'metadata' and v is not None) if isinstance(entry, dict) else str(entry) for entry in value)
            if isinstance(value, dict):
                return 'On' if value.get('show_prices') else 'Off'
            return str(value) if value is not None else '—'
        if field in data or field in previous:
            comparison.append((label, display(previous.get(field)), display(data.get(field))))
    return render_template('admin/content_edit.html', comparison=comparison, record=record, kind=kind, data=data, categories=categories, revisions=revisions, photos=photos, kinds=KINDS, error=error), status


@backend_bp.route('/admin/media', methods=['GET', 'POST'])
@require_roles('owner', 'editor')
def media():
    error = None
    if request.method == 'POST':
        try:
            upload = request.files.get('image')
            if not upload or not upload.filename:
                raise ValueError('Choose an image.')
            asset = upload_image(upload, request.form.get('alt', '').strip(), request.form.get('caption', '').strip(), request.form.get('source', 'Staff upload').strip())
            audit('media.upload', asset.id)
            commit()
            flash('Image ready. Choose it in a menu or special editor to publish it.')
            return redirect(url_for('backend.media'))
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
    page = db.paginate(db.select(MediaAsset).order_by(MediaAsset.created_at.desc()), per_page=24, error_out=False)
    library_page = max(1, request.args.get('library_page',1,type=int))
    packaged = list(current_app.extensions['oasis_assets'].items())
    return render_template('admin/media.html', page=page, error=error, packaged=packaged[(library_page-1)*24:library_page*24], library_page=library_page, library_more=len(packaged)>library_page*24), 400 if error else 200


@backend_bp.get('/media/<media_id>/<size>.webp')
def media_file(media_id, size):
    asset = db.get_or_404(MediaAsset, media_id)
    if size not in ('400', '800', '1600') or (not asset.public and not session.get('owner')):
        abort(404)
    response = send_from_directory(Path(current_app.instance_path) / 'media', asset.variants[size]['filename'])
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable' if asset.public else 'no-store'
    return response


def inquiry_query():
    query = db.select(Inquiry)
    for field in ('staff_state', 'inquiry_type', 'notification_state', 'occasion'):
        value = request.args.get(field)
        if value:
            if (field == 'staff_state' and value not in STATES) or (field == 'inquiry_type' and value not in TYPES):
                abort(400)
            query = query.where(getattr(Inquiry, field) == value)
    if not request.args.get('staff_state') and request.args.get('include_spam') != '1':
        query = query.where(Inquiry.staff_state != 'spam')
    if request.args.get('archived') != '1':
        query = query.where(Inquiry.archived_at.is_(None))
    if request.args.get('assigned_user_id'):
        value = request.args.get('assigned_user_id', type=int)
        if value is None:
            abort(400)
        query = query.where(Inquiry.assigned_user_id == value)
    if request.args.get('due') == '1':
        query = query.where(Inquiry.follow_up_at <= utcnow(), Inquiry.staff_state.notin_(['cancelled', 'spam', 'confirmed']))
    for parameter, column, ending in [('received_from', Inquiry.received_at, False), ('received_until', Inquiry.received_at, True), ('event_from', Inquiry.preferred_date, False), ('event_until', Inquiry.preferred_date, True)]:
        value = request.args.get(parameter)
        if value:
            try:
                parsed = date.fromisoformat(value)
                if column is Inquiry.received_at:
                    parsed = datetime.combine(parsed + timedelta(days=1) if ending else parsed, datetime.min.time(), tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).replace(tzinfo=None)
                    query = query.where(column < parsed if ending else column >= parsed)
                else:
                    query = query.where(column <= parsed if ending else column >= parsed)
            except ValueError:
                abort(400)
    interest = request.args.get('interest')
    if interest:
        from .inquiries import INTERESTS
        if interest not in INTERESTS:
            abort(400)
        # JSON membership is checked without substring collisions.
        if db.engine.dialect.name == 'sqlite':
            members = db.func.json_each(Inquiry.interests).table_valued('value').alias('interest_values')
            query = query.where(db.select(1).select_from(members).where(members.c.value == interest).exists())
        else:
            query = query.where(db.cast(Inquiry.interests, db.Text).contains('"' + interest + '"'))
    q = request.args.get('q', '').strip()
    if len(q) > 120:
        abort(400)
    if q:
        from .services.search import indexed_ids
        indexed = indexed_ids(q)
        if indexed is not None:
            return query.where(Inquiry.id.in_(indexed))
        escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = '%' + escaped + '%'
        expressions = [field.ilike(pattern, escape='\\') for field in (Inquiry.reference, Inquiry.name, Inquiry.contact_detail, Inquiry.notes)]
        if re.fullmatch(r'[+()\d\s.\-]+', q) and (digits := re.sub(r'\D', '', q)):
            expressions.append(Inquiry.contact_normalized.contains(digits))
        expressions.append(db.select(InquiryNote.id).where(InquiryNote.inquiry_id == Inquiry.id, InquiryNote.body.ilike(pattern, escape='\\')).exists())
        query = query.where(db.or_(*expressions))
    return query


@backend_bp.get('/admin/inbox')
@require_roles(*ALL)
def inbox():
    return redirect(url_for('admin.inquiries', **request.args))


def render_inbox():
    sort = request.args.get('sort', 'received')
    if sort not in ('received', 'event', 'follow_up'):
        abort(400)
    order = Inquiry.preferred_date.asc().nulls_last() if sort=='event' else Inquiry.follow_up_at.asc().nulls_last() if sort=='follow_up' else Inquiry.received_at.desc()
    page = db.paginate(inquiry_query().order_by(order, Inquiry.id.desc()), per_page=25, max_per_page=100, error_out=False)
    staff = db.session.scalars(db.select(StaffUser).where(StaffUser.active.is_(True), StaffUser.role.in_(['owner', 'inquiry'])).order_by(StaffUser.display_name)).all()
    counts = dict(db.session.execute(db.select(Inquiry.inquiry_type, db.func.count()).where(Inquiry.archived_at.is_(None), Inquiry.staff_state != 'spam').group_by(Inquiry.inquiry_type)).all())
    return render_template('admin/inquiries.html', page=page, inquiries=page.items, states=STATES, types=TYPES, staff=staff, counts=counts, filter_args={k:v for k,v in request.args.items() if k in FILTER_KEYS})


def inquiry_view(inquiry_id):
    inquiry = db.get_or_404(Inquiry, inquiry_id)
    error, status = None, 200
    if request.method == 'POST':
        try:
            expected(inquiry)
            action = request.form.get('action', 'update')
            note = request.form.get('note', '').strip()
            if len(note) > 4000:
                raise ValueError('Keep internal notes under 4,000 characters.')
            if action == 'note':
                if not note:
                    raise ValueError('Enter an internal note.')
                db.session.add(InquiryNote(inquiry_id=inquiry.id, actor=actor(), body=note))
            elif action == 'archive':
                inquiry.archived_at = None if inquiry.archived_at else utcnow()
            elif action == 'update':
                state = request.form.get('staff_state', inquiry.staff_state)
                kind = request.form.get('inquiry_type', inquiry.inquiry_type)
                if state not in STATES or kind not in TYPES:
                    abort(400)
                if state in ('tentative_reservation', 'confirmed') and kind not in ('event', 'mini_golf_group'):
                    raise ValueError('Only event and golf-group requests can be marked as reservations.')
                reason = request.form.get('reason', '').strip()
                if len(reason) > 1000:
                    raise ValueError('Keep the reason under 1,000 characters.')
                if state != inquiry.staff_state:
                    if (state in ('cancelled', 'other') or inquiry.staff_state in ('cancelled', 'spam', 'confirmed') or state == 'tentative_reservation' and inquiry.staff_state == 'confirmed') and not reason:
                        raise ValueError('Explain this status change in the reason field.')
                    db.session.add(InquiryHistory(inquiry_id=inquiry.id, old_state=inquiry.staff_state, new_state=state, actor=actor(), reason=reason))
                inquiry.staff_state, inquiry.inquiry_type = state, kind
                assigned = request.form.get('assigned_user_id', '')
                if assigned:
                    user = db.session.get(StaffUser, int(assigned))
                    if not user or not user.active or user.role not in ('owner', 'inquiry'):
                        raise ValueError('Choose active inquiry staff.')
                    inquiry.assigned_user_id = user.id
                elif 'assigned_user_id' in request.form:
                    inquiry.assigned_user_id = None
                if 'follow_up_at' in request.form:
                    from .admin import parse_time
                    inquiry.follow_up_at = parse_time(request.form.get('follow_up_at'))
            else:
                abort(400)
            inquiry.updated_at, inquiry.version_id = utcnow(), inquiry.version_id + 1
            audit('inquiry.' + action, inquiry.reference)
            commit()
            flash('Inquiry saved. No customer confirmation was sent.')
            return redirect(url_for('admin.inquiry_detail', inquiry_id=inquiry.id))
        except ValueError as exc:
            db.session.rollback()
            error, status = str(exc), 400
    notes = db.session.scalars(db.select(InquiryNote).where(InquiryNote.inquiry_id == inquiry.id).order_by(InquiryNote.created_at, InquiryNote.id)).all()
    history = db.session.scalars(db.select(InquiryHistory).where(InquiryHistory.inquiry_id == inquiry.id).order_by(InquiryHistory.created_at, InquiryHistory.id)).all()
    staff = db.session.scalars(db.select(StaffUser).where(StaffUser.active.is_(True), StaffUser.role.in_(['owner', 'inquiry']))).all()
    return render_template('admin/inquiry.html', inquiry=inquiry, notes=notes, history=history, staff=staff, states=STATES, types=TYPES, error=error, filter_args={k:v for k,v in request.args.items() if k in FILTER_KEYS}), status


@backend_bp.route('/admin/password', methods=['GET', 'POST'])
@require_roles(*ALL)
def password():
    error = None
    if request.method == 'POST':
        if not g.staff:
            error = 'Provision a named account with the staff-user command before changing passwords here.'
        elif not check_password_hash(g.staff.password_hash, request.form.get('current_password', '')):
            error = 'The current password is incorrect.'
        elif not 15 <= len(request.form.get('password', '')) <= 256 or request.form.get('password') != request.form.get('confirm_password'):
            error = 'Use a matching passphrase between 15 and 256 characters.'
        else:
            g.staff.password_hash = generate_password_hash(request.form['password'])
            g.staff.session_version += 1
            audit('staff.password', g.staff.id)
            commit()
            session.clear()
            flash('Password changed. Sign in again.')
            return redirect(url_for('admin.login'))
    return render_template('admin/password.html', error=error), 400 if error else 200


@backend_bp.get('/admin/staff')
@require_roles('owner')
def staff():
    users = db.session.scalars(db.select(StaffUser).order_by(StaffUser.username)).all()
    return render_template('admin/staff.html', users=users)


@backend_bp.post('/admin/staff/<int:user_id>/access')
@require_roles('owner')
def staff_access(user_id):
    if not g.staff or not check_password_hash(g.staff.password_hash, request.form.get('current_password', '')):
        abort(403)
    user = db.get_or_404(StaffUser, user_id)
    role = request.form.get('role')
    if role not in ('owner', 'editor', 'inquiry') or user.id == g.staff.id:
        abort(400)
    user.role, user.active = role, 'active' in request.form
    user.session_version += 1
    audit('staff.access', user.id)
    commit()
    return redirect(url_for('backend.staff'))


@backend_bp.post('/admin/inquiries/export')
@require_roles('owner')
def export():
    if not g.staff or not check_password_hash(g.staff.password_hash, request.form.get('current_password', '')):
        abort(403)
    rows = db.session.scalars(inquiry_query().order_by(Inquiry.received_at.desc(), Inquiry.id.desc()).limit(10001)).all()
    if len(rows) > 10000:
        abort(400, description='Narrow the filters to at most 10,000 inquiries before exporting.')
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Reference', 'Type', 'Status', 'Name', 'Contact', 'Received', 'Preferred date'])
    for row in rows:
        values = [row.reference, row.inquiry_type, row.staff_state, row.name, row.contact_detail, str(row.received_at), str(row.preferred_date or '')]
        writer.writerow(["'" + v if v.startswith(('\t','\r','\n')) or v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
    audit('inquiry.export', 'inquiries', f'{len(rows)} rows')
    commit()
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=inquiries.csv'
    return response
