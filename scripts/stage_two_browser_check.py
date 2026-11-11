import json
import os
from pathlib import Path
import tempfile
import threading
from werkzeug.serving import make_server
from flask_migrate import upgrade
from playwright.sync_api import sync_playwright
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from georges_oasis import create_app
from georges_oasis.content import load_content
from georges_oasis.services.catalog import import_catalog
from georges_oasis.models import db, Inquiry, InquiryNote

with tempfile.TemporaryDirectory() as folder:
    app=create_app({'PRODUCTION':False,'OWNER_USERNAME':'username','OWNER_PASSWORD_HASH':None,'TRUSTED_HOSTS':['127.0.0.1'],'SQLALCHEMY_DATABASE_URI':'sqlite:///'+folder+'/browser.sqlite', 'INQUIRY_RECIPIENT':None, 'INQUIRY_SENDER':None})
    app.instance_path=folder
    with app.app_context():
        upgrade()
        import_catalog(load_content())
    server=make_server('127.0.0.1',5012,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    output=Path('/tmp/oasis-stage-two-review');output.mkdir(exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':390,'height':844})
        page=context.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:5012/gatherings')
        page.locator('#name').fill('Browser workflow fixture')
        page.locator('#email').fill('fixture@example.test')
        page.locator('#occasion').select_option('Birthday')
        page.locator('#guest_count').fill('15')
        page.locator('input[name=interests][value="Mini golf"]').check()
        page.locator('#notes').fill('Synthetic customer message; no real inquiry.')
        page.get_by_role('button',name='Send Event Inquiry').click()
        page.wait_for_url('**/inquiry-received/*')
        assert 'fixture@example.test' not in page.content()
        page.goto('http://127.0.0.1:5012/admin/login')
        page.locator('input[name=username]').fill('username')
        page.locator('input[name=password]').fill('password')
        page.locator('button').click()
        page.wait_for_url('**/admin/')
        page.goto('http://127.0.0.1:5012/admin/inquiries?q=Browser')
        page.get_by_role('link',name='Review request').click()
        page.locator('textarea[name=note]').fill('Browser staff followup marker')
        page.get_by_role('button',name='Add note',exact=True).click()
        page.locator('select[name=staff_state]').select_option('tentative_reservation')
        page.get_by_role('button',name='Save workflow').click()
        assert page.locator('select[name=staff_state]').input_value()=='tentative_reservation'
        page.screenshot(path=str(output/'inquiry-mobile.png'),full_page=True)
        for path in ['/admin/menu','/admin/specials','/admin/media','/admin/inquiries?q=followup','/admin/content/2']:
            response=page.goto('http://127.0.0.1:5012'+path)
            assert response.status==200,(path,response.status)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),path
        page.locator('input[name=name]').fill('Browser draft breakfast')
        page.get_by_role('button',name='Save draft',exact=True).click()
        page.goto('http://127.0.0.1:5012/food-and-ice-cream')
        assert 'Browser draft breakfast' not in page.content()
        page.goto('http://127.0.0.1:5012/admin/preview/food')
        assert 'Browser draft breakfast' in page.content()
        page.set_viewport_size({'width':1440,'height':1000})
        page.goto('http://127.0.0.1:5012/admin/menu')
        page.screenshot(path=str(output/'menu-desktop.png'),full_page=True)
        with app.app_context():
            inquiry=db.session.scalar(db.select(Inquiry))
            assert inquiry.staff_state=='tentative_reservation'
            assert db.session.scalar(db.select(InquiryNote)).body=='Browser staff followup marker'
            assert inquiry.notification_state=='not_configured'
        assert not errors,errors
        browser.close()
    server.shutdown()
    print(json.dumps({'result':'passed','flows':['customer save/private receipt','staff login/CSRF','note/status persistence','note search','mobile screens without overflow','draft/public separation'],'screenshots':str(output)}))
