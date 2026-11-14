"""Server-side inquiry validation, durable receipts, and optional staff notifications."""
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.headerregistry import Address
from hashlib import sha256
from uuid import uuid4
import hmac
import re
import secrets
import smtplib
import ssl
from flask import current_app, g, request, session, render_template
from urllib.parse import urlsplit
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .content import local_now
from .models import db, Inquiry, InquiryHistory
from .services.abuse import take_limit
from .services.notifications import notification_recipient, queue_notification

OCCASIONS = ["Birthday", "Family celebration", "Shower", "Company gathering", "Mini golf outing", "School trip", "Fundraiser", "Other", "Not sure yet"]
INTERESTS = ["Dining", "Private space", "Mini golf", "Ice cream & desserts", "Not sure yet"]
FLEXIBILITY = ["Preferred date", "Flexible date", "Not sure yet"]
EMAIL = re.compile(r"^[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+$")

def signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="event-inquiry")

def new_submission_token():
    session.setdefault("inquiry_actor", secrets.token_hex(24))
    return signer().dumps({"actor":session["inquiry_actor"],"nonce":secrets.token_hex(24)})

def form_values():
    return {
        key: request.form.get(key, "").strip()
        for key in ("name", "contact_method", "email", "phone", "occasion",
                    "guest_count", "preferred_date", "date_flexibility", "notes", "submission_token", "inquiry_type")
    } | {"interests": request.form.getlist("interests")}

def send_staff_email(subject, body, *, reference=None, inbox_url=None):
    """Send one staff message using the same transport for tests and the worker."""
    recipient = notification_recipient()
    sender = current_app.config.get('INQUIRY_SENDER')
    if not EMAIL.fullmatch(recipient or '') or not EMAIL.fullmatch(sender or ''):
        raise ValueError('Invalid staff mail configuration')
    from .content import load_content
    business = load_content()['business']
    message = EmailMessage()
    message['From'] = Address(display_name=business['name'], addr_spec=sender)
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(body)
    message.add_alternative(render_template('emails/message.html',
        business=business, subject=subject,
        preheader=f'New saved inquiry {reference}. Sign in to review.' if reference else 'A message from the George’s Oasis website.',
        eyebrow='FROM YOUR WEBSITE' if reference else 'STAFF EMAIL CHECK',
        heading='A new inquiry is waiting.' if reference else subject,
        reference=reference, inbox_url=inbox_url,
        paragraphs=body.split('\n\n')), subtype='html')
    _send_email(message)


def _send_email(message):
    """Shared SMTP transport for independently addressed staff/customer mail."""
    host = current_app.config.get('SMTP_HOST', 'localhost')
    port = current_app.config.get('SMTP_PORT', 587)
    use_ssl = current_app.config.get('SMTP_SSL', port == 465)
    options = {'timeout': 15}
    if use_ssl:
        options['context'] = ssl.create_default_context()
    transport = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with transport(host, port, **options) as smtp:
        if not use_ssl and current_app.config.get('SMTP_TLS', True):
            smtp.starttls(context=ssl.create_default_context())
        if current_app.config.get('SMTP_USERNAME'):
            password = current_app.config.get('SMTP_PASSWORD') or ''
            # Google displays its generated app passwords in four groups.
            if host.casefold() == 'smtp.gmail.com' and re.fullmatch(r'[a-zA-Z]{4}( [a-zA-Z]{4}){3}', password):
                password = password.replace(' ', '')
            smtp.login(current_app.config['SMTP_USERNAME'], password)
        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def deliver_notification(inquiry):
    """Delivery after storage; database state is owned by the outbox service."""
    callback = current_app.config.get('INQUIRY_NOTIFIER')
    if callback:
        callback(inquiry)
        return
    base = current_app.config.get('STAFF_BASE_URL', '').rstrip('/')
    parsed = urlsplit(base)
    allowed_schemes = ('https',) if current_app.config.get('PRODUCTION') else ('https', 'http')
    inbox_url = f'{base}/admin/inquiries/{inquiry.id}' if parsed.scheme in allowed_schemes and parsed.netloc and not parsed.username and not parsed.query and not parsed.fragment else None
    inbox = (inbox_url if inbox_url else
             'Open the restaurant website and sign in at /admin to review this reference.')
    send_staff_email(f'Oasis inquiry {inquiry.reference}', f'Reference: {inquiry.reference}\nA new inquiry is saved in the staff inbox.\n{inbox}\nSign in to review it. This is not a confirmed booking.', reference=inquiry.reference, inbox_url=inbox_url)


def deliver_customer_acknowledgment(inquiry):
    callback = current_app.config.get('CUSTOMER_NOTIFIER')
    if callback:
        callback(inquiry)
        return
    from .content import load_content
    business = load_content()['business']
    sender = current_app.config.get('INQUIRY_SENDER')
    if not EMAIL.fullmatch(sender or '') or not EMAIL.fullmatch(inquiry.email or ''):
        raise ValueError('Invalid acknowledgment mail configuration')
    reply_to = business.get('email') or sender
    if not EMAIL.fullmatch(reply_to):
        reply_to = sender
    subject = f'We received your inquiry | {business["name"]} | {inquiry.reference}'
    body = (f'Thanks for reaching out to {business["name"]}.\n\n'
            f'We received your inquiry. Your reference is {inquiry.reference}.\n\n'
            'Our team will review your message and contact you using the details you provided. '
            'This acknowledges receipt only; availability, pricing and any booking still need staff confirmation.\n\n'
            f'For a question or an update, reply to this email or call {business["phone"]}. '
            'Please mention your reference. There is no need to submit the form again.\n\n'
            'Please do not email payment details or sensitive personal information.')
    message = EmailMessage()
    message['From'] = Address(display_name=business['name'], addr_spec=sender)
    message['To'] = inquiry.email
    message['Reply-To'] = Address(display_name=business['name'], addr_spec=reply_to)
    message['Subject'] = subject
    message.set_content(body)
    message.add_alternative(render_template('emails/customer_acknowledgment.html',
        business=business, subject=subject, reference=inquiry.reference,
        preheader='Your inquiry is saved. Here’s what happens next.',
        recipient_notice='You received this email because this address was entered on an inquiry to ' + business['name'] + '.'), subtype='html')
    _send_email(message)


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
    email, phone = values["email"], values["phone"]
    valid_email = len(email) <= 254 and bool(EMAIL.fullmatch(email))
    valid_phone = 7 <= len(re.sub(r"\D", "", phone)) <= 15 and len(phone) <= 40 and not any(c in phone for c in "\r\n")
    contact_method = values["contact_method"]
    if not contact_method:
        contact_method = "email" if valid_email or not phone else "phone"
    if contact_method not in ("email", "phone"):
        errors["contact_method"] = "Choose how you’d like us to contact you."
    elif not email and not phone:
        errors["email"] = "Enter an email address or phone number so we can reach you."
    elif contact_method == "email" and not valid_email:
        errors["email"] = "Enter a valid email address."
    elif contact_method == "phone" and not valid_phone:
        errors["phone"] = "Enter a phone number we can reach you on."
    if email and not valid_email:
        errors["email"] = "Enter a valid email address."
    if phone and not valid_phone:
        errors["phone"] = "Enter a phone number we can reach you on."
    occasion = values["occasion"] or "Not sure yet"
    kind = values.get("inquiry_type") or (
        "mini_golf_group" if occasion == "Mini golf outing" or "Mini golf" in values["interests"] else "event"
    )
    if kind not in ("event", "mini_golf_group", "general", "other"):
        errors["inquiry_type"] = "Choose a request type."
    if kind in ("general", "other"):
        occasion = "Other"
        values["date_flexibility"] = "Not sure yet"
        values["interests"] = values["interests"] or ["Not sure yet"]
        if not values["notes"]:
            errors["notes"] = "Tell us how we can help."
    if occasion not in OCCASIONS:
        errors["occasion"] = "The event type wasn’t recognized. Review your request and send it again."
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
    date_flexibility = values["date_flexibility"] or "Not sure yet"
    if date_flexibility not in FLEXIBILITY:
        errors["date_flexibility"] = "Choose a date preference."
    elif date_flexibility == "Preferred date" and not preferred_date:
        errors.setdefault("preferred_date","Enter a preferred date, or choose Flexible date / Not sure yet.")
    if any(value not in INTERESTS for value in values["interests"]):
        errors["interests"] = "The package interest wasn’t recognized. Review your request and send it again."
    if len(values["notes"])>2000:
        errors["notes"] = "Keep your notes to 2,000 characters or fewer."
    if errors:
        return None,errors,400
    contact = values[contact_method]
    inquiry = Inquiry(
        reference="GO-" + uuid4().hex[:12].upper(),
        submission_key=submission_key,
        name=values["name"],
        contact_method=contact_method,
        contact_detail=contact,
        email=email,
        phone=phone,
        occasion=occasion,
        guest_count=guest_count,
        preferred_date=preferred_date,
        date_flexibility=date_flexibility,
        interests=list(dict.fromkeys(values["interests"])),
        notes=values["notes"],
        inquiry_type=kind,
        source_route=request.path,
        contact_normalized=re.sub(r"\D", "", contact) if contact_method == "phone" else contact.casefold(),
    )
    saved_new = False
    try:
        db.session.add(inquiry)
        db.session.flush()
        db.session.add(InquiryHistory(inquiry_id=inquiry.id, new_state='new', actor='public-submission'))
        queue_notification(inquiry)
        db.session.commit()
        saved_new = True
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
    if saved_new:
        from .services.notifications import attempt_notification
        # Receipt data stays available even if notification status updates fail.
        # authorize_receipt has loaded the committed row before detaching it.
        db.session.expunge(inquiry)
        attempt_notification(inquiry.id)
    return inquiry,{},303
