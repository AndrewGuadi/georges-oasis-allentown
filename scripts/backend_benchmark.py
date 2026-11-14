import json
import statistics
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from flask_migrate import upgrade
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from georges_oasis import create_app
from georges_oasis.models import db, Inquiry, InquiryNote
from georges_oasis.content import load_content
from georges_oasis.services.catalog import import_catalog

with tempfile.TemporaryDirectory() as folder:
    app=create_app({'TESTING':True,'PRODUCTION':False,'SQLALCHEMY_DATABASE_URI':'sqlite:///'+folder+'/load.sqlite','WTF_CSRF_ENABLED':False})
    with app.app_context():
        upgrade();import_catalog(load_content())
        now=datetime.now()
        for start in range(0,50000,1000):
            db.session.execute(db.insert(Inquiry),[dict(reference=f'LOAD-{i:08}',submission_key=f'load-{i}',name=f'Synthetic guest {i}',contact_method='email',contact_detail=f'fixture{i}@example.test',contact_normalized=f'fixture{i}@example.test',occasion='Birthday',date_flexibility='Not sure yet',interests=['Mini golf'],notes='Synthetic message',received_at=now-timedelta(minutes=i),inquiry_type='event',staff_state='new',notification_state='not_configured') for i in range(start,start+1000)])
        db.session.commit()
        for start in range(1,50001,1000):
            db.session.execute(db.insert(InquiryNote),[dict(inquiry_id=i,actor='load-fixture',body=f'Private synthetic note {j} marker{i}') for i in range(start,start+1000) for j in range(3)])
        db.session.commit()
    def measure(path):
        client=app.test_client()
        if path.startswith('/admin'):
            with client.session_transaction() as s:s['owner']=True
        before=time.perf_counter();response=client.get(path);elapsed=(time.perf_counter()-before)*1000
        assert response.status_code==200,(path,response.status_code)
        return elapsed
    paths=['/admin/inquiries','/admin/inquiries?staff_state=new&inquiry_type=event','/admin/inquiries?q=marker49999','/admin/inquiries?q=doesnotexist','/food-and-ice-cream']
    results={}
    for path in paths:
        cold=measure(path)
        with ThreadPoolExecutor(max_workers=10) as pool:
            values=list(pool.map(measure,[path]*30))
        results[path]={'cold_ms':round(cold,1),'p95_ms':round(sorted(values)[28],1),'max_ms':round(max(values),1)}
    report={'database':'SQLite','inquiries':50000,'notes':150000,'concurrent_sessions':10,'results':results}
    from pathlib import Path
    Path('/tmp/oasis-stage-two-performance.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
