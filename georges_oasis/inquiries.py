"""Server-side inquiry validation, durable receipts, and optional staff notifications."""
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from hashlib import sha256
from uuid import uuid4
import hmac
import re
import secrets
import smtplib
from flask import current_app, g, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .content import local_now, load_content
from .models import db, Inquiry, InquiryAttempt, InquiryHistory
from .services.abuse import take_limit
from .services.notifications import queue_notification

OCCASIONS = ["Birthday", "Family celebration", "Shower", "Company gathering", "School trip", "Fundraiser", "Other", "Not sure yet"]
INTERESTS = ["Dining", "Private space", "Mini golf", "Ice cream & desserts", "Not sure yet"]
FLEXIBILITY = ["Preferred date", "Flexible date", "Not sure yet"]
EMAIL = re.compile(r"^[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+$")

def signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="event-inquiry")

def new_submission_token():
    session.setdefault("inquiry_actor", secrets.token_hex(24))
    return signer().dumps({"actor":session["inquiry_actor"],"nonce":secrets.token_hex(24)})

def form_values():
    return {key:request.form.get(key, "").strip() for key in ["name","contact_method","email","phone","occasion","guest_count","preferred_date","date_flexibility","notes","submission_token","inquiry_type"]} | {"interests":request.form.getlist("interests")}

def deliver_notification(inquiry):
    """Worker-only delivery; database state is owned by the outbox service."""
    callback = current_app.config.get('INQUIRY_NOTIFIER')
    if callback:
        callback(inquiry)
        return
    recipient, sender = current_app.config.get('INQUIRY_RECIPIENT', ''), current_app.config.get('INQUIRY_SENDER', '')
    if not EMAIL.fullmatch(recipient or '') or not EMAIL.fullmatch(sender or ''):
        raise ValueError('Invalid staff mail configuration')
    message = EmailMessage()
    message['From'], message['To'] = sender, recipient
    message['Subject'] = f'Oasis inquiry {inquiry.reference}'
    base = current_app.config.get('STAFF_BASE_URL', '').rstrip('/')
    message.set_content(f'Reference: {inquiry.reference}\nA new inquiry is saved in the staff inbox.\n{base}/admin/inquiries/{inquiry.id}\nSign in to review it. This is not a confirmed booking.')
    with smtplib.SMTP(current_app.config.get('SMTP_HOST', 'localhost'), current_app.config.get('SMTP_PORT', 587), timeout=8) as smtp:
        if current_app.config.get('SMTP_TLS', True):
            smtp.starttls()
        if current_app.config.get('SMTP_USERNAME'):
            smtp.login(current_app.config['SMTP_USERNAME'], current_app.config['SMTP_PASSWORD'])
        smtp.send_message(message)


def notify(inquiry):
    """Compatibility entry point: enqueue only, never send within HTTP handlers."""
    queue_notification(inquiry)
    db.session.commit()


def authorize_receipt(inquiry):
    references = session.get("inquiry_receipts", [])
    if inquiry.reference not in references:
        session["inquiry_receipts"] = (references + [inquiry.reference])[-20:]


def submit_inquiry(values):
    errors = {}
    try:
        token = signer().loads(values["submission_token"],max_age=7200)
        if token.get("actor") != session.get("inquiry_actor") or not token.get("nonce"):
            raise BadSignature("Wrong session")
        submission_key = sha256(values["submission_token"].encode()).hexdigest()
    except (BadSignature, SignatureExpired):
        return None,{"form":"This form session has expired. Please review your details and send again."},400
    try:
        existing = db.session.execute(db.select(Inquiry).filter_by(submission_key=submission_key)).scalar_one_or_none()
        if existing:
            authorize_receipt(existing)
            return existing,{},303
        actor = session.get('inquiry_actor', 'unknown')
        ip_ok = take_limit('inquiry-ip', request.remote_addr or 'unknown', current_app.config.get('INQUIRY_RATE_LIMIT', 10))
        session_ok = take_limit('inquiry-session', actor, current_app.config.get('INQUIRY_SESSION_LIMIT', 5))
        if not ip_ok or not session_ok:
            return None, {'form': 'Please wait a few minutes before sending again, or give us a call.'}, 429
    except SQLAlchemyError:
        db.session.rollback()
        g.error_render = True
        return None,{"form":"We couldn’t save your request. Your details are still below. Try again or call us."},503
    if request.form.get("website"):
        errors["form"] = "We couldn’t accept this request. Please call us to discuss your event."
    if not 1 <= len(values["name"]) <= 100:
        errors["name"] = "Enter your name (up to 100 characters)."
    if values["contact_method"] not in ["email","phone"]:
        errors["contact_method"] = "Choose how you’d like us to contact you."
    contact = values.get(values["contact_method"], "") if values["contact_method"] in ["email","phone"] else ""
    if values["contact_method"] == "email" and (len(contact)>254 or not EMAIL.fullmatch(contact)):
        errors["email"] = "Enter a valid email address."
    if values["contact_method"] == "phone" and (not 7 <= len(re.sub(r"\D","",contact)) <= 15 or len(contact)>40 or any(c in contact for c in "\r\n")):
        errors["phone"] = "Enter a phone number we can reach you on."
    kind = values.get('inquiry_type') or 'event'
    if kind not in ('event', 'mini_golf_group', 'general', 'other'):
        errors['inquiry_type'] = 'Choose a request type.'
    if kind in ('general', 'other'):
        values['occasion'] = 'Other'
        values['date_flexibility'] = 'Not sure yet'
        values['interests'] = values['interests'] or ['Not sure yet']
        if not values['notes']:
            errors['notes'] = 'Tell us how we can help.'
    if values["occasion"] not in OCCASIONS:
        errors["occasion"] = "Choose an occasion, or select Not sure yet."
    guest_count = None
    if values["guest_count"]:
        try:
            guest_count = int(values["guest_count"])
            if not 1 <= guest_count <= 10000:
                raise ValueError()
        except ValueError:
            errors["guest_count"] = "Enter a positive approximate guest count, or leave it blank."
    preferred_date = None
    if values["preferred_date"]:
        try:
            preferred_date = date.fromisoformat(values["preferred_date"])
            if preferred_date < local_now().date():
                raise ValueError()
        except ValueError:
            errors["preferred_date"] = "Choose today or a future date."
    if values["date_flexibility"] not in FLEXIBILITY:
        errors["date_flexibility"] = "Choose a date preference."
    elif values["date_flexibility"] == "Preferred date" and not preferred_date:
        errors.setdefault("preferred_date","Enter a preferred date, or choose Flexible date / Not sure yet.")
    if not values["interests"] or any(value not in INTERESTS for value in values["interests"]):
        errors["interests"] = "Choose at least one interest, or Not sure yet."
    if len(values["notes"])>2000:
        errors["notes"] = "Keep your notes to 2,000 characters or fewer."
    if errors:
        return None,errors,400
    inquiry = Inquiry(reference="GO-"+uuid4().hex[:12].upper(),submission_key=submission_key,name=values["name"],contact_method=values["contact_method"],contact_detail=contact,occasion=values["occasion"],guest_count=guest_count,preferred_date=preferred_date,date_flexibility=values["date_flexibility"],interests=list(dict.fromkeys(values["interests"])),notes=values["notes"],inquiry_type=kind,source_route=request.path,contact_normalized=re.sub(r"\D", "", contact) if values["contact_method"] == "phone" else contact.casefold())
    try:
        db.session.add(inquiry)
        db.session.flush()
        db.session.add(InquiryHistory(inquiry_id=inquiry.id, new_state='new', actor='public-submission'))
        queue_notification(inquiry)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        inquiry = db.session.execute(db.select(Inquiry).filter_by(submission_key=submission_key)).scalar_one_or_none()
        if not inquiry:
            return None,{"form":"We couldn’t save your request. Please try again or call us."},503
    except SQLAlchemyError:
        db.session.rollback()
        g.error_render = True
        return None,{"form":"We couldn’t save your request. Your details are still below. Try again or call us."},503
    authorize_receipt(inquiry)
    return inquiry,{},303
