"""Versioned editorial data and conservative publication / service-time rules."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
import json
from flask import current_app

LOCAL = ZoneInfo("America/New_York")
DATA_PATH = Path(__file__).with_name("content") / "site.json"

def load_content():
    override = current_app.config.get("SITE_CONTENT")
    return deepcopy(override) if override is not None else json.loads(DATA_PATH.read_text())

def local_now(now=None):
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL)

def boundary(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=LOCAL) if parsed.tzinfo is None else parsed.astimezone(LOCAL)

def publishable(record, now=None):
    metadata = record.get("metadata", {})
    if metadata.get("status") != "approved" or not metadata.get("source") or not metadata.get("reviewed_at"):
        return False
    current = local_now(now)
    try:
        start, end = boundary(metadata.get("valid_from")), boundary(metadata.get("valid_until"))
        return (start is None or end is None or start < end) and (start is None or start <= current) and (end is None or current < end)
    except (ValueError, TypeError):
        return False

def money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal("0.01")):
            raise ValueError("Currency must be a nonnegative exact value with at most two decimals.")
        return f"${amount:.2f}"
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid currency value") from exc


def pie_campaign_dates(record):
    deadline = date.fromisoformat(record["order_deadline"])
    pickups = [date.fromisoformat(value) for value in record["pickup_dates"]]
    if not pickups or deadline >= pickups[0] or pickups != sorted(set(pickups)):
        raise ValueError("Pickup dates must be distinct, in order, and after the order deadline.")
    return deadline, pickups


def current_pie_campaign(record, now=None):
    if not publishable(record, now):
        return None
    try:
        deadline, pickups = pie_campaign_dates(record)
    except (KeyError, TypeError, ValueError):
        return None
    today = local_now(now).date()
    if today > pickups[-1]:
        return None
    return record | {"deadline": deadline, "pickups": pickups, "accepting_orders": today <= deadline}

def service_boundary(day, clock, closing=False):
    """Open on the first repeated clock time; close on the second. Spring gaps move forward."""
    wall = datetime.combine(day, time.fromisoformat(clock))
    value = wall.replace(tzinfo=LOCAL, fold=1 if closing else 0)
    first = wall.replace(tzinfo=LOCAL, fold=0)
    if first.astimezone(timezone.utc).astimezone(LOCAL).replace(tzinfo=None) != wall:
        value = first.astimezone(timezone.utc).astimezone(LOCAL)
    return value


def service_status(service, now=None):
    current = local_now(now)
    utc_now = current.astimezone(timezone.utc)
    result = {"key":service["key"], "name":service["name"], "label":"Check hours", "state":"unknown", "note":service.get("note", "Call for the current schedule."), "schedule":[], "cutoff":None, "breakfast":None, "exception_note":None}
    if not publishable(service, now):
        return result
    if service.get("season") == "closed":
        return result | {"state":"seasonal_closed", "label":"Closed for the season", "note":service.get("season_note", "Call for future season information.")}
    override = service.get("override")
    if override and publishable(override, now):
        return result | {"state":"temporary_closed", "label":"Temporarily closed", "note":override.get("note", "Call before visiting.")}
    weekly = service.get("weekly", {})
    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    result["schedule"] = [{"day":day,"windows":weekly.get(str(i), []),"known":str(i) in weekly} for i,day in enumerate(days)]
    result["breakfast"] = service.get("breakfast_cutoff")
    today_key = current.date().isoformat()
    exceptions = service.get("exceptions", {})
    windows = exceptions.get(today_key, weekly.get(str(current.weekday())))
    if today_key in exceptions:
        result["exception_note"] = "Today follows a special schedule." if windows else "Closed today: special schedule."
    if windows is None:
        return result
    dated = [(current.date(), windows)]
    if today_key not in exceptions:
        previous = current.date() - timedelta(days=1)
        dated.append((previous, exceptions.get(previous.isoformat(),weekly.get(str(previous.weekday()),[]))))
    try:
        for day, intervals in dated:
            for opens, closes in intervals:
                start = service_boundary(day,opens)
                close_day = day + timedelta(days=1) if time.fromisoformat(closes) <= time.fromisoformat(opens) else day
                end = service_boundary(close_day,closes,closing=True)
                utc_end = end.astimezone(timezone.utc)
                if start.astimezone(timezone.utc) <= utc_now < utc_end:
                    cutoff = utc_end - timedelta(minutes=service.get("cutoff_minutes") or 0)
                    state,label = "open","Open now"
                    if service.get("cutoff_minutes") and utc_now >= cutoff:
                        state,label = "cutoff_passed", "Last start has passed" if service["key"] == "golf" else "Kitchen closed"
                    return result | {"state":state,"label":label,"note":f"Until {end.strftime('%-I:%M %p')} Eastern","cutoff":cutoff.astimezone(LOCAL).strftime('%-I:%M %p') if service.get("cutoff_minutes") else None}
        future_starts = [service_boundary(current.date(), opens) for opens, closes in windows
                         if service_boundary(current.date(), opens).astimezone(timezone.utc) > utc_now]
        note = "View service hours."
        if future_starts:
            next_start = min(future_starts).strftime('%-I:%M %p').replace(':00', '')
            note = f"{'Dinner begins' if service['key'] == 'dinner' else 'Opens'} at {next_start} today."
        return result | {"state":"closed","label":"Closed now","note":note}
    except (ValueError,TypeError,OverflowError):
        return result | {"state":"unknown","label":"Check hours","schedule":[]}


def offer_state(offer, now=None):
    if not publishable(offer, now):
        return "hidden"
    current = local_now(now)
    if offer.get("weekday") is None or not offer.get("start_time") or not offer.get("end_time"):
        return "hidden"  # Incomplete recurring offers never become current by default.
    try:
        start, end = time.fromisoformat(offer["start_time"]), time.fromisoformat(offer["end_time"])
        if not start < end:
            return "hidden"
        if current.weekday() != offer["weekday"]:
            return "upcoming"
        clock = current.time().replace(tzinfo=None)
        return "later_today" if clock < start else "available_now" if clock < end else "upcoming"
    except ValueError:
        return "hidden"

def public_content(now=None, include_drafts=False):
    now = local_now(now)
    data = load_content()
    pricing = data.get("menu_pricing", {})
    show_menu_prices = pricing.get("show_prices") is True and publishable(pricing, now)
    categories = deepcopy(data["menu_categories"])
    for category in categories:
        category["items"] = [item for item in category["items"] if include_drafts or publishable(item,now)]
        for item in category["items"]:
            if show_menu_prices and item.get("price") is not None:
                item["formatted_price"] = money(item["price"])
            for variant in item.get("variants", []):
                if show_menu_prices:
                    variant["formatted_price"] = money(variant["price"])
            if not show_menu_prices:
                # Free-text price notes can also contain stale dollar amounts.
                item.pop("price_note", None)
    service_facts = [service_status(s, now) for s in data["services"]]
    offers = []
    for offer in data.get("offers", []):
        state = offer_state(offer,now)
        if state != "hidden" and offer.get("weekday") in data.get("weekly_special_days", [2, 3, 4]):
            offers.append(offer | {"state":state,"formatted_price":money(offer["price"]) if offer.get("price") is not None else None})
    offers.sort(key=lambda offer: offer['weekday'])
    special_menus = []
    today_special = None
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for weekday in data.get("weekly_special_days", [2, 3, 4]):
        record = next((m for m in data.get("special_menus", []) if m.get("weekday") == weekday), {})
        approved = include_drafts or publishable(record, now)
        items = record.get("items", [])
        visible_items = [
            item | {"formatted_price": money(item["price"]).removesuffix(".00") if item.get("price") is not None else None}
            for item in items if approved and (include_drafts or publishable(item, now))
        ]
        flyer = record.get("flyer") if visible_items and len(visible_items) == len(items) else None
        menu = {
            "id": day_names[weekday].lower(), "day": day_names[weekday],
            "title": record.get("title") if approved else day_names[weekday] + " specials",
            "photo": record.get("photo") if approved else {2: "george-oasis-menu-food-spread", 3: "george-oasis-menu-food-spread-02", 4: "george-oasis-menu-food-spread-04"}.get(weekday, "george-oasis-menu-food-spread"),
            "photo_alt": record.get("photo_alt", "Food from the Oasis kitchen") if approved else "A selection of food from the Oasis kitchen",
            "items": visible_items,
            "summary": record.get("summary", "") if visible_items else "",
            "note": record.get("note", "") if approved else "",
            "flyer": flyer,
            "flyer_cover": flyer and record.get("flyer_cover", False),
        }
        special_menus.append(menu)
        if weekday == now.weekday() and visible_items and not include_drafts:
            next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            today_special = menu | {"date": now.date().isoformat(), "expires_ms": int(next_day.timestamp() * 1000)}
    business = data['business']
    items_by_id = {item['id']: item | {'category_id': category['id']}
                   for category in categories for item in category['items']}
    def features(key):
        return [items_by_id[feature['item_id']] | feature
                for feature in data.get(key, []) if feature['item_id'] in items_by_id]
    return {"show_menu_prices":show_menu_prices, "special_menus":special_menus, "featured_menu_items":features('menu_features'), "featured_desserts":features('dessert_features'),
            "today_special": today_special,
            "pie_campaign": current_pie_campaign(data.get("pie_campaign", {}), now),
            "visit_details":data.get('visit_details', {}), "ice_cream_experience":data.get('ice_cream_experience', {}),
            "ordering_details":data.get('ordering_details', {}), "photo_placements":data.get("photo_placements", {}), "menu_sources":data.get("menu_sources", []) if show_menu_prices else [], "menu_item_count":sum(len(c["items"]) for c in categories), "weekly_special_days": data.get("weekly_special_days", [2, 3, 4]), "has_menu_items":any(c["items"] for c in categories),"consumer_advisory":data.get("consumer_advisory",{}).get("text"),"dessert_flavors":data.get("dessert_flavors") if include_drafts or publishable(data.get("dessert_flavors",{}),now) else None,"menu_download_url":data.get("menu_download",{}).get("url") if show_menu_prices and publishable(data.get("menu_download",{}),now) else None,"business":business,"menu_categories":categories,"service_facts":service_facts,"dining_services":[s for s in service_facts if s["key"] in ("restaurant", "dinner")],"editorial_offers":offers,"golf_rates":data["golf"] if include_drafts or publishable(data["golf"],now) else None,"story_record":data["story"] if include_drafts or publishable(data["story"],now) else None,"media":data["media"]}


def clock_time(value):
    return time.fromisoformat(value).strftime("%-I:%M %p")


def validate_content(data):
    """Validate the editable file before review or deployment; never infer approval."""
    issues = []
    def metadata(record, label):
        meta = record.get('metadata', {})
        if meta.get('status') not in ('draft','approved','paused','archived'):
            issues.append(f'{label}: use draft, approved, paused or archived status.')
        if meta.get('status') == 'approved' and (not meta.get('source') or not meta.get('reviewed_at')):
            issues.append(f'{label}: approved records need a source and review date.')
        try:
            if meta.get('reviewed_at'):date.fromisoformat(meta['reviewed_at'])
            start,end=boundary(meta.get('valid_from')),boundary(meta.get('valid_until'))
            if start and end and end <= start:raise ValueError()
        except (ValueError,TypeError):issues.append(f'{label}: invalid review date or validity window.')
    for category in data.get('menu_categories',[]):
        for item in category.get('items',[]):
            label=item.get('id','Menu item');metadata(item,label)
            if not item.get('name'):issues.append(f'{label}: a name is required.')
            if item.get('price') is None and not item.get('variants') and not item.get('price_note'):issues.append(f'{label}: a price, priced variants or explicit price note is required.')
            for value in ([item['price']] if item.get('price') is not None else [])+[v.get('price') for v in item.get('variants',[])]+[v.get('price') for v in item.get('add_ons',[])]:
                try:money(value)
                except ValueError:issues.append(f'{label}: invalid currency value.')
    for service in data.get('services',[]):
        label=service['name'];metadata(service,label)
        try:
            if any(key not in [str(i) for i in range(7)] for key in service.get('weekly',{})):raise ValueError()
            for key in service.get('exceptions',{}):date.fromisoformat(key)
            for intervals in list(service.get('weekly',{}).values())+list(service.get('exceptions',{}).values()):
                for opens,closes in intervals:time.fromisoformat(opens);time.fromisoformat(closes)
            cutoff=service.get('cutoff_minutes')
            if cutoff is not None and (not isinstance(cutoff,int) or not 0 <= cutoff <= 1440):raise ValueError()
            if service.get('breakfast_cutoff'):time.fromisoformat(service['breakfast_cutoff'])
        except (ValueError,TypeError):issues.append(f'{label}: invalid schedule or service cutoff.')
        if service.get('override'):metadata(service['override'],label+' override')
    for offer in data.get('offers',[]):
        metadata(offer,offer['title'])
        if offer['metadata']['status']=='approved':
            try:
                if offer.get('weekday') not in range(7) or not offer.get('terms'):raise ValueError()
                if time.fromisoformat(offer['start_time']) >= time.fromisoformat(offer['end_time']):raise ValueError()
            except (ValueError,TypeError,KeyError):issues.append(f'{offer["title"]}: complete the day, times and terms before approval.')
    if "menu_pricing" in data:
        metadata(data["menu_pricing"], "Menu pricing")
        if not isinstance(data["menu_pricing"].get("show_prices"), bool):
            issues.append("Menu pricing: show_prices must be true or false.")
    seen_days = set()
    for menu in data.get("special_menus", []):
        label = menu.get("id", "Specials menu")
        metadata(menu, label)
        weekday = menu.get("weekday")
        if weekday not in data.get("weekly_special_days", [2, 3, 4]) or weekday in seen_days:
            issues.append(f"{label}: use one menu per confirmed specials day.")
        seen_days.add(weekday)
        if menu.get("metadata", {}).get("status") == "approved" and (not menu.get("title") or not menu.get("photo") or not menu.get("items")):
            issues.append(f"{label}: approved specials menus need a title, photo and dishes.")
        for item in menu.get("items", []):
            metadata(item, label + " dish")
            if not item.get("name"):
                issues.append(f"{label}: each dish needs a name.")
            if item.get("price") is not None:
                try:
                    money(item["price"])
                except ValueError:
                    issues.append(f"{label}: invalid dish price.")
    for name in ['golf','story','dessert_flavors','consumer_advisory','pie_campaign']:
        if name in data:metadata(data[name],name)
    campaign = data.get("pie_campaign", {})
    if campaign.get("metadata", {}).get("status") == "approved":
        try:
            pie_campaign_dates(campaign)
        except (KeyError, TypeError, ValueError):
            issues.append("Holiday pie orders: set a deadline and distinct pickup dates after it.")
        pies = campaign.get("pies", [])
        if not pies:
            issues.append("Holiday pie orders: add at least one pie.")
        for pie in pies:
            try:
                if not pie.get("name"):
                    raise ValueError("Missing pie name.")
                money(pie["price"])
            except (KeyError, ValueError):
                issues.append("Holiday pie orders: every pie needs a name and valid price.")
    return issues

