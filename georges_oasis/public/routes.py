from flask import render_template

from . import public_bp
from ..models import homepage_promotions


@public_bp.get("/")
def home():
    """Render the supplied homepage with links served by this application."""
    homepage = render_template("public/homepage.html", **homepage_promotions())
    local_links = {
        'href="#food"': 'href="/menu"',
        'href="#golf"': 'href="/mini-golf"',
        'href="#parties"': 'href="/parties"',
        'href="#visit"': 'href="/visit"',
        'href="https://www.georgesoasis.com/menus.html"': 'href="/menu"',
        'href="https://www.georgesoasis.com/mini-golf.html"': 'href="/mini-golf"',
        'href="https://www.georgesoasis.com/private-eventscatering.html"': 'href="/parties"',
        'href="https://www.georgesoasis.com/hours--info.html"': 'href="/visit"',
    }
    for original, replacement in local_links.items():
        homepage = homepage.replace(original, replacement)
    return homepage


PAGES = {
    "menu": ("Menu", "Browse George's Oasis food, dessert, and ice cream offerings."),
    "ice_cream": ("Ice Cream", "See seasonal ice cream offerings and plan a sweet stop."),
    "mini_golf": ("Mini Golf", "Find mini golf details, pricing, and seasonal availability."),
    "parties": ("Parties & Groups", "Plan a birthday, family gathering, or group outing."),
    "specials": ("Specials", "Explore current offers and recurring specials."),
    "visit": ("Visit", "Get directions, hours, and helpful information for your visit."),
    "about": ("Our Story", "Meet the family tradition behind George's Oasis."),
    "order": ("Order", "Choose a pickup or delivery option."),
}


def placeholder(page_key):
    title, description = PAGES[page_key]
    return render_template("public/placeholder.html", title=title, description=description)


@public_bp.get("/menu")
def menu():
    return placeholder("menu")


@public_bp.get("/ice-cream")
def ice_cream():
    return placeholder("ice_cream")


@public_bp.get("/mini-golf")
def mini_golf():
    return placeholder("mini_golf")


@public_bp.get("/parties")
def parties():
    return placeholder("parties")


@public_bp.get("/specials")
def specials():
    return placeholder("specials")


@public_bp.get("/visit")
def visit():
    return placeholder("visit")


@public_bp.get("/about")
def about():
    return placeholder("about")


@public_bp.get("/order")
def order():
    return placeholder("order")
