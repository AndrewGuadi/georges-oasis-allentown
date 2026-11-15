"""Shared response protections and customer-friendly failure recovery."""
from flask import g, make_response, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import SecurityError
from .content import public_content
from .public.sitemap import PAGES
from .services.turnstile import ORIGIN as TURNSTILE_ORIGIN
from datetime import datetime, timezone


ANALYTICS_ENDPOINTS = {"public.home", "public.inquiry_received"} | {
    f"public.{page['key']}" for page in PAGES
}


def configure_security(app):
    @app.context_processor
    def site_analytics():
        measurement_id = app.config["GA4_MEASUREMENT_ID"]
        if not measurement_id or request.endpoint not in ANALYTICS_ENDPOINTS or g.get("skip_analytics"):
            return {}
        return {"analytics_id": measurement_id, "inquiry_form_result": g.get("inquiry_form_result", "")}

    @app.after_request
    def response_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        scripts = ["'self'"]
        frames = ["'self'"]
        images = ["'self'", "data:"]
        connections = ["'self'"]
        if app.config["GA4_MEASUREMENT_ID"] and request.endpoint in ANALYTICS_ENDPOINTS and not g.get("skip_analytics"):
            # Also allow the tag on cached public menu HTML.
            tag = "https://www.googletagmanager.com"
            analytics = "https://*.google-analytics.com"
            scripts.append(tag)
            images.extend((tag, analytics))
            connections.extend((tag, analytics, "https://*.google.com"))
        if request.endpoint == "public.gatherings" and app.config["TURNSTILE_SITE_KEY"]:
            scripts.append(TURNSTILE_ORIGIN)
            frames.append(TURNSTILE_ORIGIN)
        response.headers.setdefault("Content-Security-Policy", "; ".join((
            "default-src 'self'",
            "script-src " + " ".join(scripts),
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src " + " ".join(images),
            "connect-src " + " ".join(connections),
            "frame-src " + " ".join(frames),
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        )))
        if not app.config["PRODUCTION"]:
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        if app.config["PRODUCTION"]:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response

    def error_page(code, title, message):
        g.error_render = True
        g.skip_analytics = True
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
            g.inquiry_form_result = "session_expired"
            response = make_response(render_template(
                "public/gatherings.html", page=next(p for p in PAGES if p["key"] == "gatherings"),
                values=values, errors={"form": "Your form session expired. Your details are still below. Please review them and send again."},
                occasions=OCCASIONS, interests=INTERESTS, flexibilities=FLEXIBILITY), 400)
            response.headers["Cache-Control"] = "no-store"
            return response
        return error_page(400, "Let’s try that again.", "Your form session expired. Go back, refresh the page, and try again.")

    @app.errorhandler(409)
    @app.errorhandler(503)
    def conflict(error):
        response = make_response(render_template('admin/conflict.html',
            message=error.description, title='This record changed' if error.code==409 else 'Changes were not saved',
            submitted={key: value for key, value in request.form.items() if key not in ('csrf_token', 'password', 'current_password', 'confirm_password')}), error.code)
        response.headers['Cache-Control'] = 'no-store'
        return response

    for code, title, message in [
        (403, 'Access is restricted.', 'Your staff account does not have permission for this action.'),
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
