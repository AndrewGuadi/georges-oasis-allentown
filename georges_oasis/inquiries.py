"""Server-side inquiry validation, durable receipts, and optional staff notifications."""
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from hashlib import sha256
from uuid import uuid4
import hmac
import re
import secrets
import smtplib
from flask import current_app, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .content import local_now
from .models import db, Inquiry, InquiryAttempt

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
    return {key:request.form.get(key, "").strip() for key in ["name","contact_method","email","phone","occasion","guest_count","preferred_date","date_flexibility","notes","submission_token"]} | {"interests":request.form.getlist("interests")}

def notify(inquiry):
    """No delivery occurs unless a notifier or approved SMTP recipient is configured."""
    callback = current_app.config.get("INQUIRY_NOTIFIER")
    recipient = current_app.config.get("INQUIRY_RECIPIENT")
    if callback is None and not recipient:
        inquiry.notification_state = "not_configured"
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.error("Notification state update failed for saved inquiry %s; review the dashboard.", inquiry.reference)
        return
    try:
        if callback is not None:
            callback(inquiry)
        else:
            sender = current_app.config.get("INQUIRY_SENDER", "")
            if not EMAIL.fullmatch(recipient) or not EMAIL.fullmatch(sender):
                raise ValueError("Invalid staff mail configuration")
            message = EmailMessage()
            message["From"], message["To"] = sender, recipient
            message["Subject"] = f"Oasis event inquiry {inquiry.reference}"
            if inquiry.contact_method == "email":
                message["Reply-To"] = inquiry.contact_detail
            message.set_content(f"Reference: {inquiry.reference}\nName: {inquiry.name}\nContact: {inquiry.contact_method}: {inquiry.contact_detail}\nOccasion: {inquiry.occasion}\nGuests: {inquiry.guest_count or 'Not sure yet'}\nDate: {inquiry.preferred_date or inquiry.date_flexibility}\nInterests: {', '.join(inquiry.interests)}\nNotes: {inquiry.notes}\n\nThis is an inquiry, not a confirmed booking.")
            with smtplib.SMTP(current_app.config.get("SMTP_HOST", "localhost"),current_app.config.get("SMTP_PORT",587),timeout=8) as smtp:
                if current_app.config.get("SMTP_TLS",True):
                    smtp.starttls()
                if current_app.config.get("SMTP_USERNAME"):
                    smtp.login(current_app.config["SMTP_USERNAME"],current_app.config["SMTP_PASSWORD"])
                smtp.send_message(message)
        inquiry.notification_state = "sent"
    except Exception:
        inquiry.notification_state = "failed"
        current_app.logger.error("Staff notification failed for saved inquiry %s; review the owner dashboard.",inquiry.reference)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error("Could not update notification state for inquiry %s; receipt remains saved.",inquiry.reference)

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
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        client_key = hmac.new(current_app.secret_key.encode(), (request.remote_addr or "unknown").encode(), "sha256").hexdigest()
        count = db.session.scalar(db.select(db.func.count()).select_from(InquiryAttempt).where(InquiryAttempt.client_key==client_key,InquiryAttempt.attempted_at>=now-timedelta(minutes=15)))
        if count >= current_app.config.get("INQUIRY_RATE_LIMIT",10):
            return None,{"form":"Please wait a few minutes before sending again, or give us a call."},429
        db.session.add(InquiryAttempt(client_key=client_key,attempted_at=now))
        db.session.execute(db.delete(InquiryAttempt).where(InquiryAttempt.attempted_at<now-timedelta(days=1)))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
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
    inquiry = Inquiry(reference="GO-"+uuid4().hex[:12].upper(),submission_key=submission_key,name=values["name"],contact_method=values["contact_method"],contact_detail=contact,occasion=values["occasion"],guest_count=guest_count,preferred_date=preferred_date,date_flexibility=values["date_flexibility"],interests=list(dict.fromkeys(values["interests"])),notes=values["notes"])
    try:
        db.session.add(inquiry)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        inquiry = db.session.execute(db.select(Inquiry).filter_by(submission_key=submission_key)).scalar_one_or_none()
        if not inquiry:
            return None,{"form":"We couldn’t save your request. Please try again or call us."},503
    except SQLAlchemyError:
        db.session.rollback()
        return None,{"form":"We couldn’t save your request. Your details are still below. Try again or call us."},503
    else:
        notify(inquiry)
    authorize_receipt(inquiry)
    return inquiry,{},303
