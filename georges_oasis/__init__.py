from flask import Flask
from pathlib import Path
import os
import secrets
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from .models import db
from .external_links import EXTERNAL_LINKS


def create_app(test_config=None):
    """Create and configure the George's Oasis website application."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_file = Path(app.instance_path) / "session-key"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32))
        secret_file.chmod(0o600)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secret_file.read_text(),
        SQLALCHEMY_DATABASE_URI="sqlite:///oasis.sqlite",
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
    if os.environ.get("OASIS_ENV") == "production" and not app.config.get("OWNER_PASSWORD_HASH"):
        raise RuntimeError("Production requires OWNER_PASSWORD_HASH before enabling the owner dashboard.")

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

    db.init_app(app)
    Migrate(app, db)
    CSRFProtect(app)

    from .public import public_bp

    app.register_blueprint(public_bp)
    from .admin import admin_bp
    app.register_blueprint(admin_bp)
    return app
