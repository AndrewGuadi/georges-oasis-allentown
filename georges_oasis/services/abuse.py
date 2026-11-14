"""Atomic fixed-window counters shared by workers on SQLite or PostgreSQL."""
import hashlib
import hmac
import time
from flask import current_app
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from ..models import db, RateBucket


def take_limit(namespace, identity, limit, seconds=900):
    secret = current_app.config.get('ABUSE_KEY') or current_app.secret_key
    digest = hmac.new(secret.encode(), identity.encode(), hashlib.sha256).hexdigest()
    window = int(time.time()) // seconds
    key = namespace + ':' + digest
    insert = pg_insert if db.engine.dialect.name == 'postgresql' else sqlite_insert
    statement = insert(RateBucket).values(key=key, window=window, count=1)
    statement = statement.on_conflict_do_update(index_elements=['key'], set_={
        'window': window,
        'count': db.case((RateBucket.window == window, RateBucket.count + 1), else_=1),
    })
    db.session.execute(statement)
    # The upsert holds the write lock until commit, so the read sees our count.
    count = db.session.execute(
        db.select(RateBucket.count).where(RateBucket.key == key)
    ).scalar_one()
    db.session.commit()
    return count <= limit
