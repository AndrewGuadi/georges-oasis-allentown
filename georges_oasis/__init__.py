from dotenv import load_dotenv
from flask import Flask
from pathlib import Path
import os
import secrets
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from .models import db
from .external_links import EXTERNAL_LINKS
from datetime import timedelta


def create_app(test_config=None):
    """Create and configure the George's Oasis website application."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_file = Path(app.instance_path) / "session-key"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32))
        secret_file.chmod(0o600)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secret_file.read_text(),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///oasis.sqlite"),
        PRODUCTION=os.environ.get("OASIS_ENV") == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=False,
        TRUSTED_HOSTS=[h.strip() for h in os.environ.get("TRUSTED_HOSTS", "").split(",") if h.strip()] or None,
        EXTERNAL_LINKS=EXTERNAL_LINKS.copy(),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        INQUIRY_RECIPIENT=os.environ.get("INQUIRY_RECIPIENT"),
        INQUIRY_SENDER=os.environ.get("INQUIRY_SENDER"),
        SMTP_HOST=os.environ.get("SMTP_HOST", "localhost"),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_TLS=os.environ.get("SMTP_TLS", "true").lower() == "true",
        SMTP_USERNAME=os.environ.get("SMTP_USERNAME"),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD"),
        OWNER_USERNAME=os.environ.get("OWNER_USERNAME", "username"),
        OWNER_PASSWORD_HASH=os.environ.get("OWNER_PASSWORD_HASH"),
        SESSION_COOKIE_SECURE=os.environ.get("OASIS_ENV") == "production",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)
    from .oasis_images import init_oasis_images
    init_oasis_images(app)
    if app.config["PRODUCTION"]:
        app.config["SESSION_COOKIE_SECURE"] = True
        if not app.config.get("OWNER_PASSWORD_HASH") or app.config["OWNER_USERNAME"] == "username":
            raise RuntimeError("Production requires OWNER_USERNAME and OWNER_PASSWORD_HASH.")
        if not app.config.get("TRUSTED_HOSTS"):
            raise RuntimeError("Production requires TRUSTED_HOSTS (comma-separated public host names).")
        from werkzeug.security import check_password_hash
        if check_password_hash(app.config["OWNER_PASSWORD_HASH"], "password"):
            raise RuntimeError("The demo password cannot be used in production.")

    @app.cli.command("check-content")
    def check_content():
        import click
        from .content import load_content, validate_content
        issues = validate_content(load_content())
        if issues:
            raise click.ClickException("\n".join(issues))
        click.echo("Content structure is valid. Draft records remain unpublished.")

    @app.context_processor
    def inject_external_links():
        return {"external_links": app.config["EXTERNAL_LINKS"]}

    @app.template_filter("optimized_image")
    def optimized_image(filename):
        return Path(filename).stem + ".webp"

    db.init_app(app)
    Migrate(app, db)
    CSRFProtect(app)

    from .public import public_bp

    app.register_blueprint(public_bp)
    from .admin import admin_bp
    app.register_blueprint(admin_bp)
    from .security import configure_security
    configure_security(app)
    return app
