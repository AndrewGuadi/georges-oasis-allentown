"""SQLite substring index, transactionally maintained by database triggers.

install_search_v1 is frozen for the migration that uses it. FTS is a private
copy of inquiry PII and must be included in record deletion/retention handling.
"""
from sqlalchemy import text


def install_search_v1(connection):
    if connection.dialect.name != 'sqlite':
        return
    connection.exec_driver_sql("CREATE VIRTUAL TABLE IF NOT EXISTS inquiry_search USING fts5(reference, name, contact, phone, message, internal_notes, tokenize='trigram')")
    connection.exec_driver_sql('DELETE FROM inquiry_search')
    connection.exec_driver_sql("""INSERT INTO inquiry_search(rowid, reference, name, contact, phone, message, internal_notes)
        SELECT i.id, i.reference, i.name, i.contact_detail, i.contact_normalized, i.notes,
        COALESCE((SELECT group_concat(n.body, ' ') FROM inquiry_note n WHERE n.inquiry_id=i.id), '') FROM inquiry i""")
    connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS inquiry_search_insert AFTER INSERT ON inquiry BEGIN
        INSERT INTO inquiry_search(rowid, reference, name, contact, phone, message, internal_notes)
        VALUES(new.id, new.reference, new.name, new.contact_detail, new.contact_normalized, new.notes, ''); END""")
    connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS inquiry_search_update AFTER UPDATE OF reference,name,contact_detail,contact_normalized,notes ON inquiry BEGIN
        UPDATE inquiry_search SET reference=new.reference, name=new.name, contact=new.contact_detail,
        phone=new.contact_normalized, message=new.notes WHERE rowid=new.id; END""")
    connection.exec_driver_sql('CREATE TRIGGER IF NOT EXISTS inquiry_search_delete AFTER DELETE ON inquiry BEGIN DELETE FROM inquiry_search WHERE rowid=old.id; END')
    for action in ('INSERT', 'UPDATE', 'DELETE'):
        identity = 'old' if action == 'DELETE' else 'new'
        connection.exec_driver_sql(f"""CREATE TRIGGER IF NOT EXISTS inquiry_note_search_{action.lower()} AFTER {action} ON inquiry_note BEGIN
            UPDATE inquiry_search SET internal_notes=COALESCE((SELECT group_concat(body, ' ') FROM inquiry_note WHERE inquiry_id={identity}.inquiry_id),'') WHERE rowid={identity}.inquiry_id; END""")


def indexed_ids(query):
    """Return literal substring matches for >=3 characters; shorter uses SQL."""
    import re
    from ..models import db
    if db.engine.dialect.name != 'sqlite' or len(query) < 3:
        return None
    terms = ['"' + query.replace('"', '""') + '"']
    if re.fullmatch(r'[+()\d\s.\-]+', query):
        digits = re.sub(r'\D', '', query)
        if len(digits) >= 3:
            terms.append('"' + digits + '"')
    return db.select(db.literal_column('rowid')).select_from(db.table('inquiry_search')).where(text('inquiry_search MATCH :inquiry_search_term')).params(inquiry_search_term=' OR '.join(terms))
