"""Saved notifications with immediate attempts and optional CLI retries."""
from datetime import timedelta
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError
from ..models import db, Inquiry, NotificationOutbox, CustomerAcknowledgment, utcnow


def notification_recipient():
    from flask import current_app
    from ..content import load_content
    recipient = current_app.config.get('INQUIRY_RECIPIENT')
    if not recipient and current_app.config.get('INQUIRY_SENDER'):
        recipient = load_content()['business'].get('email')
    return recipient


def configured():
    from flask import current_app
    return bool(current_app.config.get('INQUIRY_NOTIFIER') or notification_recipient())


def customer_configured():
    from flask import current_app
    return bool(current_app.config.get('CUSTOMER_NOTIFIER') or current_app.config.get('INQUIRY_SENDER'))


def queue_notification(inquiry):
    if configured():
        inquiry.notification_state = 'pending'
        db.session.add(NotificationOutbox(inquiry_id=inquiry.id))
    else:
        inquiry.notification_state = 'not_configured'
    if inquiry.email:
        if customer_configured():
            inquiry.customer_notification_state = 'pending'
            db.session.add(CustomerAcknowledgment(inquiry_id=inquiry.id))
        else:
            inquiry.customer_notification_state = 'not_configured'
    else:
        inquiry.customer_notification_state = 'not_requested'


def attempt_notification(inquiry_id, *, audience=None):
    """Attempt each recipient independently after storage, preserving receipts."""
    from flask import current_app
    processed = 0
    for kind in ((audience,) if audience else ('staff', 'customer')):
        try:
            processed += drain(limit=1, inquiry_id=inquiry_id, audience=kind)
        except Exception:
            db.session.rollback()
            current_app.logger.error('%s notification processing failed for saved inquiry ID %s; review the staff inbox.', kind, inquiry_id)
    return processed


def drain(limit=25, *, inquiry_id=None, audience=None):
    from ..inquiries import deliver_notification, deliver_customer_acknowledgment
    if audience is None:
        processed = drain(limit, inquiry_id=inquiry_id, audience='staff')
        if processed < limit:
            processed += drain(limit - processed, inquiry_id=inquiry_id, audience='customer')
        return processed
    if audience not in ('staff', 'customer'):
        raise ValueError('Unknown notification audience')
    job_model = NotificationOutbox if audience == 'staff' else CustomerAcknowledgment
    state_field = 'notification_state' if audience == 'staff' else 'customer_notification_state'
    deliver = deliver_notification if audience == 'staff' else deliver_customer_acknowledgment
    # Exhausted workers may have crashed after the final send. Surface the job
    # for staff review instead of leaving an expired Sending state forever.
    exhausted_query = db.select(job_model).where(
        job_model.state == 'sending', job_model.lease_until < utcnow(), job_model.attempts >= 5)
    if inquiry_id is not None:
        exhausted_query = exhausted_query.where(job_model.inquiry_id == inquiry_id)
    exhausted = db.session.scalars(exhausted_query).all()
    for job in exhausted:
        job.state, job.last_error = 'failed', 'LeaseExpiredAfterFinalAttempt'
        inquiry = db.session.get(Inquiry, job.inquiry_id)
        setattr(inquiry, state_field, 'failed')
    db.session.commit()
    processed = 0
    for _ in range(limit):
        now = utcnow()
        eligible = db.select(job_model.id).where(
            job_model.attempts < 5,
            db.or_(db.and_(job_model.state.in_(['pending', 'retry']), job_model.next_attempt_at <= now),
                   db.and_(job_model.state == 'sending', job_model.lease_until < now)),
        )
        if inquiry_id is not None:
            eligible = eligible.where(job_model.inquiry_id == inquiry_id)
        row_id = db.session.scalar(eligible.order_by(job_model.next_attempt_at, job_model.id).limit(1))
        if row_id is None:
            break
        token = uuid4().hex
        changed = db.session.execute(db.update(job_model).where(
            job_model.id == row_id,
            db.or_(job_model.state.in_(['pending', 'retry']), db.and_(job_model.state == 'sending', job_model.lease_until < now)),
        ).values(state='sending', lease_token=token, lease_until=now + timedelta(seconds=60), attempts=job_model.attempts + 1)).rowcount
        db.session.commit()
        if not changed:
            continue
        row = db.session.get(job_model, row_id, populate_existing=True)
        inquiry = db.session.get(Inquiry, row.inquiry_id)
        if inquiry.staff_state == 'spam':
            row.state = 'suppressed'
            setattr(inquiry, state_field, 'suppressed')
            db.session.commit()
            continue
        # Carry a detached snapshot so network I/O holds no database transaction.
        db.session.expunge(inquiry)
        db.session.commit()
        try:
            deliver(inquiry)
            outcome, error = 'sent', None
        except Exception as exc:
            from flask import current_app
            current_app.logger.error('%s notification failed for saved inquiry %s; review the staff inbox.', audience, inquiry.reference)
            outcome, error = 'retry', type(exc).__name__[:100]
        row = db.session.get(job_model, row_id, populate_existing=True)
        if row.lease_token != token:
            db.session.rollback()
            continue
        inquiry = db.session.get(Inquiry, row.inquiry_id, populate_existing=True)
        row.last_error = error
        row.lease_until = None
        if outcome == 'sent':
            row.state, row.sent_at = 'sent', utcnow()
            setattr(inquiry, state_field, 'sent')
        else:
            row.state = 'failed' if row.attempts >= 5 else 'retry'
            row.next_attempt_at = utcnow() + timedelta(minutes=[1, 5, 15, 60, 240][row.attempts - 1])
            setattr(inquiry, state_field, 'failed')
        db.session.commit()
        processed += 1
    if inquiry_id is not None or audience == 'customer':
        return processed
    from ..models import BackendSetting
    heartbeat = db.session.get(BackendSetting, 'worker_heartbeat')
    if not heartbeat:
        heartbeat = BackendSetting(key='worker_heartbeat', value='')
        db.session.add(heartbeat)
    heartbeat.value = utcnow().isoformat()
    db.session.commit()
    return processed
