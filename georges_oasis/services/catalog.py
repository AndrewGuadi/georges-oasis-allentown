"""Revisioned content storage and compatibility adapter for existing templates."""
from copy import deepcopy
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from flask import current_app
from sqlalchemy.orm import joinedload
from ..models import db, ContentRecord, ContentRevision, BackendSetting, MediaAsset
from .auth import actor, audit

KINDS = {'category': 'Menu category', 'item': 'Menu item', 'weekly': 'Weekly menu', 'recurring': 'Recurring offer', 'settings': 'Publication settings'}


def cents(value):
    if value in (None, ''):
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal('100000') or number != number.quantize(Decimal('.01')):
            raise ValueError()
        return int(number * 100)
    except (ValueError, InvalidOperation):
        raise ValueError('Enter an exact price between 0 and 100,000 with at most two decimal places.') from None


def to_storage(data):
    data = deepcopy(data)
    if 'price' in data:
        data['price_cents'] = cents(data.pop('price'))
    for key in ('variants', 'add_ons', 'items'):
        if key in data:
            data[key] = [to_storage(item) for item in data[key]]
    return data


def to_public(data):
    data = deepcopy(data)
    if 'price_cents' in data:
        amount = data.pop('price_cents')
        data['price'] = f'{Decimal(amount) / 100:.2f}' if amount is not None else None
    for key in ('variants', 'add_ons', 'items'):
        if key in data:
            data[key] = [to_public(item) for item in data[key]]
    return data


def import_catalog(raw, dry_run=False):
    """One-time atomic import. Refuse changed sources rather than overwrite edits."""
    checksum = sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    prior = db.session.get(BackendSetting, 'catalog_source')
    if prior:
        if prior.value != checksum:
            raise ValueError('Catalog already imported from a different source. Reconcile changes explicitly; staff edits were preserved.')
        return {'created': 0, 'items': sum(len(c['items']) for c in raw['menu_categories'])}
    if db.session.scalar(db.select(db.func.count()).select_from(ContentRecord)):
        raise ValueError('Content records already exist without an import marker; inspect before importing.')
    entries = []
    for index, category in enumerate(raw['menu_categories']):
        data = deepcopy(category)
        items = data.pop('items')
        entries.append(('category', category['id'], None, index, data))
        entries += [('item', i['id'], category['id'], n, i) for n, i in enumerate(items)]
    entries += [('weekly', 'weekly:' + v['id'], None, n, v) for n, v in enumerate(raw.get('special_menus', []))]
    entries += [('recurring', 'recurring:' + v['id'], None, n, v) for n, v in enumerate(raw.get('offers', []))]
    entries.append(('settings', 'catalog-settings', None, 0, {'menu_pricing': raw['menu_pricing'], 'weekly_special_days': raw['weekly_special_days']}))
    if dry_run:
        return {'created': len(entries), 'items': sum(len(c['items']) for c in raw['menu_categories'])}
    for kind, key, parent, position, data in entries:
        record = ContentRecord(kind=kind, key=key, parent_key=parent, position=position)
        db.session.add(record)
        db.session.flush()
        revision = ContentRevision(record_id=record.id, data=to_storage(data), actor='source-import')
        db.session.add(revision)
        db.session.flush()
        record.draft_id = revision.id
        # Keep original draft/approval metadata; public selectors still enforce it.
        record.published_id = revision.id
    db.session.add(BackendSetting(key='catalog_source', value=checksum))
    db.session.add(BackendSetting(key='catalog_enabled', value='true'))
    audit('catalog.import', 'catalog', f'{len(entries)} records; source {checksum}')
    db.session.commit()
    return {'created': len(entries), 'items': sum(len(c['items']) for c in raw['menu_categories'])}


def apply_catalog(raw, include_drafts=False):
    if current_app.config.get('SITE_CONTENT') is not None:
        return raw
    if not (setting := db.session.get(BackendSetting, 'catalog_enabled')) or setting.value != 'true':
        return raw
    signature = tuple(db.session.execute(db.select(db.func.count(ContentRecord.id), db.func.sum(ContentRecord.version_id))).one()) + (db.session.scalar(db.select(db.func.max(ContentRevision.id))),)
    snapshots = current_app.extensions.setdefault('catalog_snapshots', {})
    cached = snapshots.get(include_drafts)
    if cached and cached[0] == signature:
        raw.update(deepcopy(cached[1]))
        return raw
    records = db.session.scalars(db.select(ContentRecord).options(joinedload(ContentRecord.draft), joinedload(ContentRecord.published)).order_by(ContentRecord.position, ContentRecord.id)).all()
    groups = {kind: [] for kind in KINDS}
    for record in records:
        revision = record.draft if include_drafts else record.published
        if revision is None or record.archived or (record.unavailable and not include_drafts):
            continue
        data = to_public(revision.data)
        if record.kind == 'item' and not include_drafts and not data.get('prices_reviewed', False):
            # Leave descriptions live while withholding every stale price surface.
            data['price'] = None
            data.pop('price_note', None)
            for option in data.get('variants', []) + data.get('add_ons', []):
                option['price'] = None
        groups[record.kind].append((record, data))
    categories = []
    for record, data in groups['category']:
        data['items'] = [v for r, v in groups['item'] if r.parent_key == record.key]
        categories.append(data)
    payload = {'menu_categories': categories, 'special_menus': [v for r,v in sorted(groups['weekly'], key=lambda entry: entry[0].draft_id if include_drafts else entry[0].published_id, reverse=True)], 'offers': [v for r,v in groups['recurring']]}
    if groups['settings']:
        payload.update(groups['settings'][0][1])
        payload['special_menus'] = [menu for menu in payload['special_menus'] if menu['weekday'] in payload.get('weekly_special_days', [2,3,4])]
    ids = set(media_keys(payload))
    payload['uploaded_images'] = {'upload:' + asset.id: {'id': asset.id, 'alt': asset.alt, 'variants': asset.variants} for asset in db.session.scalars(db.select(MediaAsset).where(MediaAsset.id.in_(ids)))} if ids else {}
    snapshots[include_drafts] = (signature, deepcopy(payload))
    raw.update(payload)
    return raw


def validate_revision(kind, data, publishing=False):
    from ..content import boundary
    if kind == 'settings':
        days = data.get('weekly_special_days', [])
        if not days or any(type(day) is not int or day not in range(7) for day in days) or len(set(days)) != len(days):
            raise ValueError('Select at least one distinct weekday.')
        return
    title = data.get('name') if kind in ('item', 'category') else data.get('title')
    if not title or len(title) > 160:
        raise ValueError('A name or title up to 160 characters is required.')
    if len(data.get('group', '')) > 160:
        raise ValueError('Keep group names under 160 characters.')
    if kind == 'item':
        options = data.get('variants', []) + data.get('add_ons', [])
        amounts = [option.get('price_cents') for option in options]
        if any(value is not None and (type(value) is not int or value < 0) for value in amounts):
            raise ValueError('Option prices must be exact amounts or left blank.')
    for field in ('description', 'inclusions', 'intro', 'terms', 'note', 'summary', 'price_note'):
        if len(data.get(field, '')) > 4000:
            raise ValueError('Keep each description or note under 4,000 characters.')
    metadata = data.get('metadata', {})
    if len(metadata.get('source', '')) > 300:
        raise ValueError('Source must be at most 300 characters.')
    try:
        start, end = boundary(metadata.get('valid_from')), boundary(metadata.get('valid_until'))
        if start and end and end <= start:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Use valid publication dates with end later than start.') from None
    if publishing and not metadata.get('source'):
        raise ValueError('Record the source or owner review before publishing.')
    if kind in ('weekly', 'recurring'):
        if type(data.get('weekday')) is not int or data['weekday'] not in range(7):
            raise ValueError('Choose a weekday.')
    if publishing and kind == 'weekly' and (not data.get('items') or not data.get('photo')):
        raise ValueError('A weekly menu needs dishes and a photo before publication.')
    if publishing and kind == 'recurring':
        try:
            if not time.fromisoformat(data['start_time']) < time.fromisoformat(data['end_time']) or not data.get('terms'):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ValueError('Recurring offers need same-day start/end times and terms.') from None
    if publishing and kind in ('weekly', 'recurring') and any(x.get('price_cents') is not None for x in [data, *data.get('items', [])]) and not data.get('prices_reviewed'):
        raise ValueError('Review the special prices before publishing.')


def save_revision(record, data, action):
    validate_revision(record.kind, data, publishing=action == 'publish')
    data = deepcopy(data)
    if action == 'publish':
        data['metadata'] = data.get('metadata', {}) | {'status': 'approved', 'reviewed_at': date.today().isoformat()}
        if record.kind == 'settings':
            data['menu_pricing']['metadata'] = {'status': 'approved', 'source': 'Owner dashboard', 'reviewed_at': date.today().isoformat()}
        for item in data.get('items', []):
            item['metadata'] = dict(data['metadata'])
        for key in media_keys(data):
            media = db.session.get(MediaAsset, key)
            if media:
                media.public = True
        record.archived = False
        if record.kind == 'weekly':
            peers = db.session.scalars(db.select(ContentRecord).options(joinedload(ContentRecord.published)).where(ContentRecord.kind == 'weekly', ContentRecord.id != record.id)).all()
            for peer in peers:
                if peer.published and peer.published.data.get('weekday') == data['weekday']:
                    peer.published_id = None
                    peer.version_id += 1
                    audit('weekly.replaced', peer.key, 'Replaced by ' + record.key)
    revision = ContentRevision(record_id=record.id, data=data, actor=actor())
    db.session.add(revision)
    db.session.flush()
    record.draft_id = revision.id
    if action == 'publish':
        record.published_id = revision.id
        record.position = data.get('_position', record.position)
        if record.kind == 'item':
            record.parent_key = data.get('_parent_key', record.parent_key)
    record.version_id += 1
    audit('content.' + action, record.key, f'Revision {revision.id}')


def media_keys(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'photo' and isinstance(value, str) and value.startswith('upload:'):
                yield value[7:]
            else:
                yield from media_keys(value)
    elif isinstance(data, list):
        for value in data:
            yield from media_keys(value)
