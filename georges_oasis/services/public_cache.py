"""One-second anonymous menu-page cache with authoritative DB version checks.

Never use for forms, receipts, previews or sessions. A database outage fails
closed through the normal error handler rather than resurrecting cached prices.
"""
import time
from flask import current_app, make_response, request, session
from ..models import db, ContentRecord, ContentRevision


def menu_response(render):
    if session or current_app.config.get('SITE_CONTENT') is not None:
        return render()
    from ..content import DATA_PATH, local_now
    generation = tuple(db.session.execute(db.select(db.func.count(ContentRecord.id), db.func.sum(ContentRecord.version_id))).one()) + (db.session.scalar(db.select(db.func.max(ContentRevision.id))),)
    key = (request.url_root, request.path, generation, DATA_PATH.stat().st_mtime_ns,
           local_now().replace(microsecond=0).isoformat())
    cache = current_app.extensions.setdefault('anonymous_menu_pages', {})
    now = time.time()
    cached = cache.get(request.path)
    if cached and cached[0] == key and now < cached[1]:
        return make_response(cached[2])
    response = render()
    if response.status_code == 200 and not session and not response.headers.get('Set-Cookie'):
        # All staff-entered service times have second precision or coarser. Also
        # bound subsecond editorial validity windows explicitly below.
        deadline = int(time.time()) + 1
        from .catalog import apply_catalog
        from ..content import load_content, boundary
        def boundaries(value):
            if isinstance(value, dict):
                for field, item in value.items():
                    if field in ('valid_from', 'valid_until') and item:
                        try:
                            yield boundary(item).timestamp()
                        except (ValueError, TypeError):
                            pass
                    else:
                        yield from boundaries(item)
            elif isinstance(value, list):
                for item in value:
                    yield from boundaries(item)
        for instant in boundaries(apply_catalog(load_content())):
            if now < instant < deadline:
                deadline = instant
        cache[request.path] = (key, deadline, response.get_data())
    return response
