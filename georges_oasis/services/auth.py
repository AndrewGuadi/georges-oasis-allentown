"""Named staff authorization, with explicit development/legacy bootstrap access."""
from datetime import datetime, timezone
from functools import wraps
from flask import abort, current_app, g, redirect, request, session, url_for
from ..models import db, StaffUser, AuditEvent


def actor():
    return g.staff.username if getattr(g, 'staff', None) else 'bootstrap-owner'


def audit(action, entity, summary=''):
    db.session.add(AuditEvent(actor=actor(), action=action, entity=str(entity), summary=summary[:300]))


def current_role():
    return g.staff.role if getattr(g, 'staff', None) else 'owner'


def require_roles(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get('owner'):
                return redirect(url_for('admin.login'))
            if current_role() not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate


def configure_auth(app):
    @app.before_request
    def staff_session():
        g.staff = None
        if not session.get('owner'):
            return
        now = datetime.now(timezone.utc).timestamp()
        if session.get('staff_id'):
            staff = db.session.get(StaffUser, session['staff_id'])
            if not staff or not staff.active or staff.session_version != session.get('staff_version'):
                session.clear()
                return
            g.staff = staff
        elif not app.config.get('TESTING') and db.session.scalar(db.select(db.func.count()).select_from(StaffUser)):
            session.clear()
            return
        if now - session.get('staff_last_seen', now) > app.config['STAFF_IDLE_SECONDS'] or now - session.get('staff_login_at', now) > 28800:
            session.clear()
            return
        session['staff_last_seen'] = now

    @app.context_processor
    def staff_context():
        return {'staff_role': current_role(), 'staff_actor': actor()}
