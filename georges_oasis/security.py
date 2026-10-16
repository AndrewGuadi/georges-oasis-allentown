"""Shared response protections and customer-friendly failure recovery."""
from flask import make_response, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import SecurityError
from .content import public_content
from .public.sitemap import PAGES
from datetime import datetime, timezone


def configure_security(app):
    @app.after_request
    def response_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        if app.config["PRODUCTION"]:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response

    def error_page(code, title, message):
        response = make_response(render_template(
            "public/error.html", error_code=code, error_title=title, error_message=message,
            site_pages=PAGES, current_year=datetime.now(timezone.utc).year, **public_content()), code)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    @app.errorhandler(CSRFError)
    def expired_form(error):
        if request.endpoint == "public.gatherings":
            from .inquiries import form_values, new_submission_token, OCCASIONS, INTERESTS, FLEXIBILITY
            values = form_values()
            values["submission_token"] = new_submission_token()
            response = make_response(render_template(
                "public/gatherings.html", page=next(p for p in PAGES if p["key"] == "gatherings"),
                values=values, errors={"form": "Your form session expired. Your details are still below. Please review them and send again."},
                occasions=OCCASIONS, interests=INTERESTS, flexibilities=FLEXIBILITY), 400)
            response.headers["Cache-Control"] = "no-store"
            return response
        return error_page(400, "Let’s try that again.", "Your form session expired. Go back, refresh the page, and try again.")

    for code, title, message in [
        (400, "We couldn’t open that request.", "Please check the address or return to the homepage."),
        (404, "A little off the beaten path.", "That page isn’t here. Find your way back to a good meal, a round of golf, or your next visit."),
        (413, "That upload is a little too large.", "Go back and choose a file smaller than 5 MB, then try again."),
        (429, "Please try again shortly.", "There have been too many attempts. Wait a few minutes, or call the restaurant for help."),
        (500, "We hit a small bump.", "Please try again in a moment. You can also call the restaurant for help planning your visit."),
    ]:
        app.register_error_handler(code, lambda error, c=code, t=title, m=message: error_page(c, t, m))

    @app.errorhandler(SecurityError)
    def untrusted_host(error):
        return "Invalid host.", 400, {"Content-Type": "text/plain", "Cache-Control": "no-store"}
