import re
import unittest
from unittest.mock import patch
from sqlalchemy.exc import OperationalError

from georges_oasis import create_app
from georges_oasis.models import db, Inquiry, CustomerAcknowledgment, NotificationOutbox, utcnow
from georges_oasis.services.notifications import drain
from georges_oasis.inquiries import deliver_customer_acknowledgment


class CustomerAcknowledgmentTest(unittest.TestCase):
    def setUp(self):
        self.staff = []
        self.customers = []
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'INQUIRY_NOTIFIER': lambda row: self.staff.append(row.reference),
            'CUSTOMER_NOTIFIER': lambda row: self.customers.append(row.reference)})
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def form(self, **changes):
        html = self.client.get('/gatherings').get_data(as_text=True)
        form = {key: re.search(r'name="' + key + r'" value="([^"]+)"', html).group(1)
                for key in ('csrf_token', 'submission_token')}
        form.update(name='Acknowledgment fixture', email='customer@example.test')
        form.update(changes)
        return form

    @staticmethod
    def fail(row):
        raise RuntimeError('Synthetic mail outage')

    def test_saved_inquiry_sends_two_independent_messages_and_duplicate_sends_none(self):
        form = self.form()
        response = self.client.post('/gatherings', data=form)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.post('/gatherings', data=form).location, response.location)
        self.assertEqual(len(self.staff), 1)
        self.assertEqual(self.staff, self.customers)
        with self.app.app_context():
            inquiry = db.session.scalar(db.select(Inquiry))
            self.assertEqual((inquiry.notification_state, inquiry.customer_notification_state), ('sent', 'sent'))
            self.assertEqual(db.session.scalar(db.select(CustomerAcknowledgment)).attempts, 1)
            self.assertEqual(drain(), 0)
        receipt = self.client.get(response.location).get_data(as_text=True)
        self.assertIn('sent an acknowledgment email', receipt)
        self.assertNotIn('customer@example.test', receipt)
        self.assertIn('does not confirm a booking', receipt)

    def test_staff_failure_does_not_prevent_customer_acknowledgment(self):
        self.app.config['INQUIRY_NOTIFIER'] = self.fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            response = self.client.post('/gatherings', data=self.form())
        self.assertEqual(response.status_code, 303)
        self.assertEqual(len(self.customers), 1)
        with self.app.app_context():
            inquiry = db.session.scalar(db.select(Inquiry))
            self.assertEqual((inquiry.notification_state, inquiry.customer_notification_state), ('failed', 'sent'))

    def test_customer_failure_preserves_staff_email_receipt_and_dashboard_retry(self):
        self.app.config['CUSTOMER_NOTIFIER'] = self.fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            response = self.client.post('/gatherings', data=self.form())
        self.assertEqual(response.status_code, 303)
        receipt = self.client.get(response.location).get_data(as_text=True)
        self.assertIn('couldn’t send your acknowledgment email', receipt)
        self.assertEqual(len(self.staff), 1)
        self.app.config['CUSTOMER_NOTIFIER'] = lambda row: self.customers.append(row.reference)
        with self.client.session_transaction() as session:
            session['owner'] = True
        detail = self.client.get('/admin/inquiries/1').get_data(as_text=True)
        self.assertIn('Retry customer acknowledgment', detail)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
        for _ in range(2):
            self.assertEqual(self.client.post('/admin/inquiries/1/notify', data={
                'csrf_token': csrf, 'audience': 'customer'}).status_code, 302)
        self.assertEqual(len(self.staff), 1)
        self.assertEqual(len(self.customers), 1)
        self.assertIn('sent an acknowledgment email', self.client.get(response.location).get_data(as_text=True))

    def test_phone_only_gets_no_email_acknowledgment(self):
        response = self.client.post('/gatherings', data=self.form(email='', phone='610 555 0100'))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.customers, [])
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(Inquiry)).customer_notification_state, 'not_requested')
            self.assertEqual(db.session.scalar(db.select(db.func.count(CustomerAcknowledgment.id))), 0)
        self.assertNotIn('sent an acknowledgment email', self.client.get(response.location).get_data(as_text=True))

    def test_valid_secondary_email_gets_acknowledgment(self):
        response = self.client.post('/gatherings', data=self.form(contact_method='phone', phone='610 555 0100'))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(len(self.customers), 1)

    def test_failed_storage_sends_neither_message(self):
        form = self.form()
        with patch('georges_oasis.inquiries.db.session.commit', side_effect=OperationalError('test', {}, Exception('fixture'))):
            response = self.client.post('/gatherings', data=form)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.staff, [])
        self.assertEqual(self.customers, [])

    def test_cli_retries_customer_without_resending_successful_staff_alert(self):
        self.app.config['CUSTOMER_NOTIFIER'] = self.fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.client.post('/gatherings', data=self.form())
        self.app.config['CUSTOMER_NOTIFIER'] = lambda row: self.customers.append(row.reference)
        with self.app.app_context():
            job = db.session.scalar(db.select(CustomerAcknowledgment))
            job.next_attempt_at = utcnow()
            db.session.commit()
        result = self.app.test_cli_runner().invoke(args=['process-notifications'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Processed 1 notification jobs.', result.output)
        self.assertEqual(len(self.staff), 1)
        self.assertEqual(len(self.customers), 1)

    def test_customer_message_is_branded_private_and_replyable(self):
        self.app.config.update(CUSTOMER_NOTIFIER=None, INQUIRY_SENDER='website@example.test')
        from types import SimpleNamespace
        inquiry = SimpleNamespace(email='customer@example.test', reference='GO-ACKTEST', name='Private name', notes='Sensitive fixture message')
        with self.app.app_context(), patch('georges_oasis.inquiries._send_email') as send:
            deliver_customer_acknowledgment(inquiry)
        message = send.call_args.args[0]
        self.assertEqual(str(message['To']), inquiry.email)
        self.assertIsNone(message['Cc'])
        self.assertIsNone(message['Bcc'])
        self.assertEqual(message['Reply-To'].addresses[0].addr_spec, 'georgesoasisrestaurant@gmail.com')
        self.assertEqual(message.get_content_type(), 'multipart/alternative')
        for kind in ('plain', 'html'):
            body = message.get_body(preferencelist=(kind,)).get_content()
            self.assertIn(inquiry.reference, body)
            self.assertNotIn('/admin', body)
            self.assertNotIn(inquiry.notes, body)
            self.assertNotIn(inquiry.name, body)
        html = message.get_body(preferencelist=('html',)).get_content()
        self.assertIn('What happens next?', html)
        self.assertIn('staff confirmation', html)
        self.assertNotIn('configured staff inbox', html)

    def test_customer_retries_stop_at_five_attempts(self):
        self.app.config['CUSTOMER_NOTIFIER'] = self.fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.client.post('/gatherings', data=self.form())
        with self.app.app_context():
            job = db.session.scalar(db.select(CustomerAcknowledgment))
            job.attempts, job.next_attempt_at = 4, utcnow()
            db.session.commit()
            with self.assertLogs(self.app.logger, level='ERROR'):
                self.assertEqual(drain(), 1)
            self.assertEqual(db.session.get(CustomerAcknowledgment, job.id).state, 'failed')
            self.assertEqual(db.session.get(CustomerAcknowledgment, job.id).attempts, 5)
            self.assertEqual(drain(), 0)
        self.assertEqual(len(self.staff), 1)

    def test_spam_suppresses_customer_retry(self):
        self.app.config['CUSTOMER_NOTIFIER'] = self.fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.client.post('/gatherings', data=self.form())
        self.app.config['CUSTOMER_NOTIFIER'] = lambda row: self.customers.append(row.reference)
        with self.app.app_context():
            db.session.scalar(db.select(Inquiry)).staff_state = 'spam'
            db.session.scalar(db.select(CustomerAcknowledgment)).next_attempt_at = utcnow()
            db.session.commit()
            drain()
            self.assertEqual(db.session.scalar(db.select(Inquiry)).customer_notification_state, 'suppressed')
            self.assertEqual(db.session.scalar(db.select(CustomerAcknowledgment)).state, 'suppressed')
        self.assertEqual(self.customers, [])
