"""Leased, bounded notification worker. Never called from a customer request."""
from datetime import timedelta
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError
from ..models import db, Inquiry, NotificationOutbox, utcnow


def configured():
    from flask import current_app
    return bool(current_app.config.get('INQUIRY_NOTIFIER') or current_app.config.get('INQUIRY_RECIPIENT'))


def queue_notification(inquiry):
    if not configured():
        inquiry.notification_state = 'not_configured'
        return
    inquiry.notification_state = 'pending'
    db.session.add(NotificationOutbox(inquiry_id=inquiry.id))


def drain(limit=25):
    from ..inquiries import deliver_notification
    # Exhausted workers may have crashed after the final send. Surface the job
    # for staff review instead of leaving an expired Sending state forever.
    exhausted = db.session.scalars(db.select(NotificationOutbox).where(
        NotificationOutbox.state == 'sending', NotificationOutbox.lease_until < utcnow(), NotificationOutbox.attempts >= 5)).all()
    for job in exhausted:
        job.state, job.last_error = 'failed', 'LeaseExpiredAfterFinalAttempt'
        inquiry = db.session.get(Inquiry, job.inquiry_id)
        inquiry.notification_state = 'failed'
    db.session.commit()
    processed = 0
    for _ in range(limit):
        now = utcnow()
        row_id = db.session.scalar(db.select(NotificationOutbox.id).where(
            NotificationOutbox.attempts < 5,
            db.or_(db.and_(NotificationOutbox.state.in_(['pending', 'retry']), NotificationOutbox.next_attempt_at <= now),
                   db.and_(NotificationOutbox.state == 'sending', NotificationOutbox.lease_until < now)),
        ).order_by(NotificationOutbox.next_attempt_at, NotificationOutbox.id).limit(1))
        if row_id is None:
            break
        token = uuid4().hex
        changed = db.session.execute(db.update(NotificationOutbox).where(
            NotificationOutbox.id == row_id,
            db.or_(NotificationOutbox.state.in_(['pending', 'retry']), db.and_(NotificationOutbox.state == 'sending', NotificationOutbox.lease_until < now)),
        ).values(state='sending', lease_token=token, lease_until=now + timedelta(seconds=60), attempts=NotificationOutbox.attempts + 1)).rowcount
        db.session.commit()
        if not changed:
            continue
        row = db.session.get(NotificationOutbox, row_id, populate_existing=True)
        inquiry = db.session.get(Inquiry, row.inquiry_id)
        if inquiry.staff_state == 'spam':
            row.state, inquiry.notification_state = 'suppressed', 'suppressed'
            db.session.commit()
            continue
        # Carry a detached snapshot so network I/O holds no database transaction.
        db.session.expunge(inquiry)
        db.session.commit()
        try:
            deliver_notification(inquiry)
            outcome, error = 'sent', None
        except Exception as exc:
            from flask import current_app
            current_app.logger.error('Staff notification failed for saved inquiry %s; review the owner dashboard.', inquiry.reference)
            outcome, error = 'retry', type(exc).__name__[:100]
        row = db.session.get(NotificationOutbox, row_id, populate_existing=True)
        if row.lease_token != token:
            db.session.rollback()
            continue
        inquiry = db.session.get(Inquiry, row.inquiry_id, populate_existing=True)
        row.last_error = error
        row.lease_until = None
        if outcome == 'sent':
            row.state, row.sent_at, inquiry.notification_state = 'sent', utcnow(), 'sent'
        else:
            row.state = 'failed' if row.attempts >= 5 else 'retry'
            row.next_attempt_at = utcnow() + timedelta(minutes=[1, 5, 15, 60, 240][row.attempts - 1])
            inquiry.notification_state = 'failed'
        db.session.commit()
        processed += 1
    from ..models import BackendSetting
    heartbeat = db.session.get(BackendSetting, 'worker_heartbeat')
    if not heartbeat:
        heartbeat = BackendSetting(key='worker_heartbeat', value='')
        db.session.add(heartbeat)
    heartbeat.value = utcnow().isoformat()
    db.session.commit()
    return processed
