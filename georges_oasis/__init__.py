from flask import Flask
from pathlib import Path
import os
import secrets
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from .models import db


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
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    Migrate(app, db)
    CSRFProtect(app)

    from .public import public_bp

    app.register_blueprint(public_bp)
    from .admin import admin_bp
    app.register_blueprint(admin_bp)
    return app
