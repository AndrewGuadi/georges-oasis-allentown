from datetime import datetime, timezone
from flask import render_template

from . import public_bp
from .sitemap import PAGES
from ..models import homepage_promotions


@public_bp.context_processor
def site_context():
    return {"site_pages": PAGES, "current_year": datetime.now(timezone.utc).year}


@public_bp.get("/")
def home():
    return render_template("public/homepage.html", **homepage_promotions())


def page_view(page):
    """Bind only the explicitly declared sitemap pages, never a user-supplied template."""
    def view():
        return render_template(f"public/{page['key']}.html", page=page)
    return view


for page in PAGES:
    public_bp.add_url_rule(page["path"], endpoint=page["key"], view_func=page_view(page), methods=["GET"])
