"""Isolated customer → inbox → SMTP check; --serve leaves a manual-test preview.

No production database, credentials, or mail server is used.
PLAYWRIGHT_BROWSERS_PATH=/tmp/oasis-browsers .venv/bin/python scripts/contact_check.py --serve
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import socketserver
import sys
import tempfile
import threading
from email import policy
from email.parser import BytesParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flask_migrate import upgrade
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from georges_oasis import create_app
from georges_oasis.models import db, Inquiry, InquiryNote
from georges_oasis.services.notifications import drain


class CaptureSMTP(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b'220 localhost test mail capture\r\n')
        while line := self.rfile.readline():
            command = line.split(b' ', 1)[0].strip().upper()
            if command == b'DATA':
                self.wfile.write(b'354 End with dot\r\n')
                lines = []
                while (line := self.rfile.readline()) not in (b'.\r\n', b''):
                    lines.append(line[1:] if line.startswith(b'..') else line)
                self.server.messages.append(b''.join(lines))
                self.wfile.write(b'250 Captured\r\n')
            elif command == b'QUIT':
                self.wfile.write(b'221 Bye\r\n')
                return
            else:
                self.wfile.write(b'250 OK\r\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--pages', action='store_true', help='Also run all public page/viewport checks')
    args = parser.parse_args()
    output = Path('/tmp/oasis-contact-review')
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='oasis-contact-') as folder, socketserver.TCPServer(('127.0.0.1', 0), CaptureSMTP) as smtp:
        smtp.messages = []
        threading.Thread(target=smtp.serve_forever, daemon=True).start()
        preview_host = (os.environ['CODESPACE_NAME'] + '-5013.app.github.dev') if os.environ.get('CODESPACE_NAME') else None
        app = create_app({'TESTING': True, 'PRODUCTION': False, 'SESSION_COOKIE_SECURE': False,
            'OWNER_USERNAME': 'username', 'OWNER_PASSWORD_HASH': None, 'TRUSTED_HOSTS': ['127.0.0.1', 'localhost'] + ([preview_host] if preview_host else []),
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + folder + '/review.sqlite',
            'INQUIRY_RECIPIENT': 'staff@example.test', 'INQUIRY_SENDER': 'website@example.test',
            'SMTP_HOST': '127.0.0.1', 'SMTP_PORT': smtp.server_address[1], 'SMTP_TLS': False,
            'SMTP_USERNAME': None, 'SMTP_PASSWORD': None, 'STAFF_BASE_URL': 'http://127.0.0.1:5013'})
        app.instance_path = folder
        with app.app_context():
            upgrade()
        server = make_server('0.0.0.0' if args.serve else '127.0.0.1', 5013, app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:5013'
        errors = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 390, 'height': 844})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/gatherings?interest=Mini+golf')
            page.locator('#inquiry-form button[type=submit]').click()
            expect(page.locator('#form-errors')).to_be_focused()
            page.locator('#name').fill('CONTACT TEST — safe to remove')
            page.locator('#email').fill('fixture@example.test')
            page.locator('#phone').fill('610 555 0100')
            page.locator('#notes').fill('Synthetic inquiry for contact verification.')
            page.locator('#inquiry-form button[type=submit]').click()
            page.wait_for_url('**/inquiry-received/*')
            receipt = page.url
            assert 'fixture@example.test' not in page.content()
            page.reload()
            with browser.new_context() as stranger:
                assert stranger.new_page().goto(receipt).status == 404
            with app.app_context():
                assert db.session.scalar(db.select(db.func.count(Inquiry.id))) == 1
                inquiry = db.session.scalar(db.select(Inquiry))
                assert (inquiry.email, inquiry.phone, inquiry.inquiry_type) == ('fixture@example.test', '610 555 0100', 'mini_golf_group')
                assert drain() == 0
                assert drain() == 0
                assert db.session.get(Inquiry, inquiry.id).notification_state == 'sent'
                assert db.session.get(Inquiry, inquiry.id).customer_notification_state == 'sent'
            assert len(smtp.messages) == 2
            mail = BytesParser(policy=policy.default).parsebytes(smtp.messages[0])
            assert base + '/admin/inquiries/1' in mail.get_body(preferencelist=('plain',)).get_content()
            assert 'fixture@example.test' not in mail.get_body(preferencelist=('plain',)).get_content()
            acknowledgment = BytesParser(policy=policy.default).parsebytes(smtp.messages[1])
            assert acknowledgment['To'] == 'fixture@example.test'
            assert '/admin' not in acknowledgment.get_body(preferencelist=('html',)).get_content()
            assert 'staff confirmation' in acknowledgment.get_body(preferencelist=('html',)).get_content()
            assert 'sent an acknowledgment email' in page.content()
            for width in (320, 390, 768):
                page.set_viewport_size({'width': width, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(output / 'receipt-mobile.png'), full_page=True)
            page.goto(base + '/admin/login')
            page.locator('[name=username]').fill('username')
            page.locator('[name=password]').fill('password')
            page.locator('button[type=submit], button.primary').click()
            page.wait_for_url('**/admin/')
            page.goto(base + '/admin/inquiries?q=610+555')
            page.get_by_role('link', name='Review request').click()
            expect(page.locator('a[href="mailto:fixture@example.test"]')).to_be_visible()
            expect(page.locator('a[href="tel:610 555 0100"]')).to_be_visible()
            page.locator('textarea[name=note]').fill('Contact verification staff followup marker')
            page.get_by_role('button', name='Add note', exact=True).click()
            page.locator('select[name=staff_state]').select_option('contacted')
            page.get_by_role('button', name='Save workflow').click()
            page.goto(base + '/admin/inquiries?q=followup+marker')
            page.get_by_role('link', name='Review request').click()
            expect(page.locator('select[name=staff_state]')).to_have_value('contacted')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / 'inquiry-mobile.png'), full_page=True)
            with app.app_context():
                assert db.session.scalar(db.select(InquiryNote)).body == 'Contact verification staff followup marker'
            assert not errors, errors
            browser.close()
        if args.pages:
            os.environ['OASIS_TEST_BASE_URL'] = base
            runpy.run_path(str(Path(__file__).with_name('browser_check.py')))
        result = {'result': 'passed', 'flows': ['validation and focus', 'both contacts saved', 'golf classification',
            'private receipt and reload', 'independent staff and customer SMTP delivery without worker', 'staff login', 'secondary contact search',
            'private notes and search', 'status persistence', 'mobile layout'], 'javascript_errors': errors}
        (output / 'results.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
        if args.serve:
            print('Manual test preview: http://localhost:5013 — staff username / password. Mail is captured locally. Ctrl-C stops and removes test data.', flush=True)
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                pass
        server.shutdown()
        smtp.shutdown()


if __name__ == '__main__':
    main()
