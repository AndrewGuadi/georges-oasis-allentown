import re
import unittest
import sqlite3
import tempfile
from contextlib import closing
from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from georges_oasis import create_app
from georges_oasis.models import db, Inquiry, NotificationOutbox
from georges_oasis.services.notifications import drain
class InquiryTest(unittest.TestCase):
    def setUp(self):
        self.notifications=[]
        self.app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://','INQUIRY_NOTIFIER':lambda inquiry:self.notifications.append(inquiry.reference),'INQUIRY_RATE_LIMIT':20})
        with self.app.app_context():db.create_all()
        self.client=self.app.test_client()
    def tearDown(self):
        with self.app.app_context():db.session.remove();db.drop_all();db.engine.dispose()
    def form(self):
        html=self.client.get('/gatherings?interest=Mini+golf').get_data(as_text=True)
        return {'csrf_token':re.search(r'name="csrf_token" value="([^"]+)"',html).group(1),'submission_token':re.search(r'name="submission_token" value="([^"]+)"',html).group(1),'name':'Test Organizer','contact_method':'email','email':'organizer@example.test','phone':'','occasion':'Birthday','guest_count':'12','preferred_date':'','date_flexibility':'Not sure yet','interests':['Mini golf'],'notes':'Test fixture only.'}
    def test_received_duplicate_retry_private_receipt(self):
        form=self.form();first=self.client.post('/gatherings',data=form);second=self.client.post('/gatherings',data=form)
        self.assertEqual(first.status_code,303);self.assertEqual(second.location,first.location);self.assertEqual(len(self.notifications),1)
        with self.app.app_context():
            self.assertEqual(drain(),0)
            self.assertEqual(drain(),0)
        self.assertEqual(len(self.notifications),1)
        with self.app.app_context():self.assertEqual(db.session.query(Inquiry).count(),1)
        receipt=self.client.get(first.location);self.assertEqual(receipt.status_code,200)
        self.assertIn('does not confirm a booking',receipt.get_data(as_text=True));self.assertNotIn('organizer@example.test',receipt.get_data(as_text=True))
        self.assertEqual(receipt.headers['X-Robots-Tag'],'noindex, nofollow')
        self.assertEqual(self.app.test_client().get(first.location).status_code,404)
    def test_validation_preservation_and_safe_rendering(self):
        form=self.form();form.update(name='<script>alert(1)</script>',email='invalid',guest_count='-3')
        response=self.client.post('/gatherings',data=form);self.assertEqual(response.status_code,400)
        html=response.get_data(as_text=True);self.assertIn('Enter a valid email',html);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('name="interests" value="Mini golf"',html);self.assertEqual(self.notifications,[])
    def test_phone_only_flexible_inquiry(self):
        form=self.form();form.update(contact_method='phone',email='',phone='610 555 0100',guest_count='',date_flexibility='Flexible date')
        self.assertEqual(self.client.post('/gatherings',data=form).status_code,303)
        with self.app.app_context():
            inquiry=db.session.execute(db.select(Inquiry)).scalar_one();self.assertEqual(inquiry.contact_detail,'610 555 0100');self.assertIsNone(inquiry.guest_count)
    def test_short_inquiry_accepts_either_contact_method_without_event_details(self):
        for method, contact in (('email', 'organizer@example.test'), ('phone', '610 555 0100')):
            with self.subTest(method=method):
                original = self.form()
                form = {key: original[key] for key in ('csrf_token', 'submission_token', 'name')}
                form[method] = contact
                response = self.client.post('/gatherings', data=form)
                self.assertEqual(response.status_code, 303)
                with self.app.app_context():
                    inquiry = db.session.execute(db.select(Inquiry).filter_by(contact_method=method)).scalar_one()
                    self.assertEqual(inquiry.contact_detail, contact)
                    self.assertEqual(inquiry.occasion, 'Not sure yet')
                    self.assertEqual(inquiry.date_flexibility, 'Not sure yet')
                    self.assertEqual(inquiry.notes, '')
                    self.assertEqual(inquiry.interests, [])

    def test_short_inquiry_requires_a_way_to_follow_up(self):
        original = self.form()
        form = {key: original[key] for key in ('csrf_token', 'submission_token', 'name')}
        response = self.client.post('/gatherings', data=form)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Enter an email address or phone number', response.get_data(as_text=True))
        self.assertEqual(self.notifications, [])
    def test_both_contacts_are_saved_and_visible_to_staff(self):
        form = self.form()
        form['phone'] = '610 555 0100'
        self.assertEqual(self.client.post('/gatherings', data=form).status_code, 303)
        with self.app.app_context():
            inquiry = db.session.scalar(db.select(Inquiry))
            self.assertEqual(inquiry.email, form['email'])
            self.assertEqual(inquiry.phone, form['phone'])
        with self.client.session_transaction() as session:
            session['owner'] = True
        detail = self.client.get('/admin/inquiries/1').get_data(as_text=True)
        self.assertIn('mailto:organizer@example.test', detail)
        self.assertIn('tel:610 555 0100', detail)

    def test_invalid_secondary_contact_is_not_silently_discarded(self):
        form = self.form()
        form['phone'] = '123'
        response = self.client.post('/gatherings', data=form)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Enter a phone number', response.get_data(as_text=True))

    def test_worker_mail_has_absolute_link_or_clear_inbox_instructions(self):
        self.client.post('/gatherings', data=self.form())
        self.app.config.update(INQUIRY_NOTIFIER=None, INQUIRY_RECIPIENT='staff@example.test', INQUIRY_SENDER='website@example.test')
        from georges_oasis.inquiries import deliver_notification
        with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as smtp:
            smtp.return_value.__enter__.return_value.send_message.return_value = {}
            inquiry = db.session.scalar(db.select(Inquiry))
            for base in ('', 'https://restaurant.example'):
                self.app.config['STAFF_BASE_URL'] = base
                deliver_notification(inquiry)
                message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
                body = message.get_body(preferencelist=('plain',)).get_content()
                self.assertNotIn('organizer@example.test', body)
                if base:
                    self.assertIn('https://restaurant.example/admin/inquiries/1', body)
                else:
                    self.assertIn('sign in at /admin', body)
                    self.assertNotIn('\n/admin/inquiries/', body)

    def test_notification_outage_keeps_receipt_and_owner_alert(self):
        def fail(inquiry):raise RuntimeError('Test mail outage')
        self.app.config['INQUIRY_NOTIFIER']=fail
        form = self.form()
        with self.assertLogs(self.app.logger,level='ERROR'):
            response=self.client.post('/gatherings',data=form)
        self.assertEqual(response.status_code,303)
        self.assertEqual(self.client.get(response.location).status_code,200)
        with self.app.app_context():self.assertEqual(db.session.execute(db.select(Inquiry)).scalar_one().notification_state,'failed')
        with self.client.session_transaction() as session:session['owner']=True
        self.assertIn('direct dashboard review',self.client.get('/admin').get_data(as_text=True))

    def test_notification_processing_database_error_keeps_successful_receipt(self):
        form = self.form()
        with patch('georges_oasis.services.notifications.drain', side_effect=OperationalError('test', {}, Exception('fixture'))), self.assertLogs(self.app.logger, level='ERROR'):
            response = self.client.post('/gatherings', data=form)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.get(response.location).status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(Inquiry)).notification_state, 'pending')
            self.assertEqual(db.session.scalar(db.select(NotificationOutbox)).state, 'pending')

    def test_inquiry_and_history_are_committed_before_email_attempt(self):
        observed = []
        with tempfile.TemporaryDirectory() as folder:
            path = folder + '/committed.sqlite'
            def inspect_saved_inquiry(inquiry):
                # A separate native connection cannot see uncommitted rows.
                with closing(sqlite3.connect(path)) as connection:
                    observed.append((
                        connection.execute('SELECT name FROM inquiry WHERE id=?', (inquiry.id,)).fetchone(),
                        connection.execute('SELECT count(*) FROM inquiry_history WHERE inquiry_id=?', (inquiry.id,)).fetchone()[0],
                        connection.execute('SELECT state FROM notification_outbox WHERE inquiry_id=?', (inquiry.id,)).fetchone(),
                    ))
                raise RuntimeError('Synthetic email outage after durable save')
            app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + path,
                              'INQUIRY_NOTIFIER': inspect_saved_inquiry})
            with app.app_context():
                db.create_all()
            client = app.test_client()
            html = client.get('/gatherings').get_data(as_text=True)
            form = {key: re.search(r'name="' + key + r'" value="([^"]+)"', html).group(1)
                    for key in ('csrf_token', 'submission_token')}
            form.update(name='Durable save fixture', email='fixture@example.test')
            with self.assertLogs(app.logger, level='ERROR'):
                response = client.post('/gatherings', data=form)
            self.assertEqual(observed, [(('Durable save fixture',), 1, ('sending',))])
            self.assertEqual(response.status_code, 303)
            self.assertEqual(client.get(response.location).status_code, 200)
            with app.app_context():
                self.assertEqual(db.session.scalar(db.select(Inquiry)).notification_state, 'failed')
                db.session.remove()
                db.engine.dispose()

    def test_new_submission_does_not_process_another_inquirys_queue(self):
        first_form = self.form()
        with patch('georges_oasis.services.notifications.drain', return_value=0):
            self.assertEqual(self.client.post('/gatherings', data=first_form).status_code, 303)
        self.assertEqual(self.client.post('/gatherings', data=self.form()).status_code, 303)
        self.assertEqual(len(self.notifications), 1)
        with self.app.app_context():
            inquiries = db.session.scalars(db.select(Inquiry).order_by(Inquiry.id)).all()
            self.assertEqual([i.notification_state for i in inquiries], ['pending', 'sent'])

    def test_email_status_commit_failure_does_not_fail_saved_request(self):
        form = self.form()
        commit = db.session.commit
        def fail_status_commit():
            if any(isinstance(row, NotificationOutbox) and row.state == 'sent' for row in db.session.dirty):
                raise OperationalError('test', {}, Exception('status write fixture'))
            return commit()
        with patch('georges_oasis.services.notifications.db.session.commit', side_effect=fail_status_commit), self.assertLogs(self.app.logger, level='ERROR'):
            response = self.client.post('/gatherings', data=form)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.get(response.location).status_code, 200)
        self.assertEqual(len(self.notifications), 1)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(Inquiry.id))), 1)
            self.assertEqual(db.session.scalar(db.select(NotificationOutbox)).state, 'sending')

    def test_staff_retry_sends_immediately_without_worker(self):
        def fail(inquiry):
            raise RuntimeError('Mail outage fixture')
        self.app.config['INQUIRY_NOTIFIER'] = fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.client.post('/gatherings', data=self.form())
        self.app.config['INQUIRY_NOTIFIER'] = lambda inquiry: self.notifications.append(inquiry.reference)
        with self.client.session_transaction() as session:
            session['owner'] = True
        detail = self.client.get('/admin/inquiries/1').get_data(as_text=True)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
        self.assertEqual(self.client.post('/admin/inquiries/1/notify', data={'csrf_token': csrf}).status_code, 302)
        self.assertEqual(len(self.notifications), 1)
        with self.app.app_context():
            self.assertEqual(db.session.get(Inquiry, 1).notification_state, 'sent')
    def test_storage_failure_preserves_form_without_success(self):
        form=self.form()
        with patch('georges_oasis.inquiries.db.session.commit',side_effect=OperationalError('test',{},Exception('fixture'))):response=self.client.post('/gatherings',data=form)
        self.assertEqual(response.status_code,503);self.assertIn('couldn’t save your request',response.get_data(as_text=True));self.assertIn('Test Organizer',response.get_data(as_text=True));self.assertEqual(self.notifications,[])
    def test_csrf_honeypot_email_injection_rate_limit(self):
        self.assertEqual(self.client.post('/gatherings',data={}).status_code,400)
        form=self.form();form['website']='spam';self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        form=self.form();form['email']='x@example.test\r\nBcc: another@example.test';self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        self.app.config['INQUIRY_RATE_LIMIT']=2
        self.assertEqual(self.client.post('/gatherings',data=self.form()).status_code,429);self.assertEqual(self.notifications,[])
    def test_required_contact_and_date(self):
        form=self.form();form.update(date_flexibility='Preferred date',preferred_date='')
        self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        form.update(preferred_date='2000-01-01');self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        form.update(date_flexibility='Not sure yet',preferred_date='',contact_method='phone',phone='123');self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
    def test_authenticated_owner_review(self):
        self.client.post('/gatherings',data=self.form());self.assertEqual(self.client.get('/admin/inquiries').status_code,302)
        with self.client.session_transaction() as session:session['owner']=True
        detail=self.client.get('/admin/inquiries/1').get_data(as_text=True)
        token=re.search(r'name="csrf_token" value="([^"]+)"',detail).group(1)
        self.assertIn('organizer@example.test',detail)
        self.assertEqual(self.client.post('/admin/inquiries/1',data={'csrf_token':token,'staff_state':'contacted','version_id':re.search(r'name="version_id" value="([^"]+)"',detail).group(1)}).status_code,302)
        with self.app.app_context():self.assertEqual(db.session.get(Inquiry,1).staff_state,'contacted')
if __name__=='__main__':unittest.main()
