"""Staff mail transport, provider password handling and safe CLI diagnostics."""
import smtplib
import ssl
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from georges_oasis import create_app
from georges_oasis.inquiries import send_staff_email, deliver_notification


class StaffEmailTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'INQUIRY_RECIPIENT': 'recipient@example.test', 'INQUIRY_SENDER': 'sender@example.test',
            'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': 587, 'SMTP_TLS': True, 'SMTP_SSL': False,
            'SMTP_USERNAME': 'sender@example.test', 'SMTP_PASSWORD': 'abcd efgh ijkl mnop'})

    def test_starttls_validates_certificate_and_accepts_formatted_google_password(self):
        with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as transport:
            smtp = transport.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            send_staff_email('Delivery test', 'Synthetic test body')
            context = smtp.starttls.call_args.kwargs['context']
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            smtp.login.assert_called_once_with('sender@example.test', 'abcdefghijklmnop')
            message = smtp.send_message.call_args.args[0]
            self.assertEqual(message['To'], 'recipient@example.test')
            self.assertEqual(message['From'].addresses[0].addr_spec, 'sender@example.test')
            self.assertEqual(message['From'].addresses[0].display_name, 'George’s Oasis')

    def test_implicit_tls_does_not_send_starttls(self):
        self.app.config.update(SMTP_PORT=465, SMTP_SSL=True)
        with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP_SSL') as transport:
            smtp = transport.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            send_staff_email('Delivery test', 'Synthetic test body')
            smtp.starttls.assert_not_called()
            self.assertTrue(transport.call_args.kwargs['context'].check_hostname)

    def test_other_provider_passwords_are_preserved(self):
        self.app.config['SMTP_HOST'] = 'smtp.example.test'
        with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as transport:
            smtp = transport.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            send_staff_email('Delivery test', 'Synthetic test body')
            smtp.login.assert_called_once_with('sender@example.test', 'abcd efgh ijkl mnop')

    def test_cli_failure_never_prints_provider_message_or_credentials(self):
        with patch('georges_oasis.inquiries.send_staff_email', side_effect=smtplib.SMTPAuthenticationError(535, b'SENSITIVE PROVIDER DETAIL')):
            result = self.app.test_cli_runner().invoke(args=['test-email'])
        self.assertEqual(result.exit_code, 1)
        self.assertIn('SMTP 535', result.output)
        self.assertNotIn('SENSITIVE PROVIDER DETAIL', result.output)
        self.assertNotIn(self.app.config['SMTP_PASSWORD'], result.output)

    def test_cli_success_reports_acceptance_without_claiming_inbox_delivery(self):
        with patch('georges_oasis.inquiries.send_staff_email') as send:
            result = self.app.test_cli_runner().invoke(args=['test-email'])
        self.assertEqual(result.exit_code, 0)
        send.assert_called_once()
        self.assertIn('Check the configured recipient inbox', result.output)

    def test_refused_recipient_is_a_failure(self):
        with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as transport:
            transport.return_value.__enter__.return_value.send_message.return_value = {'recipient@example.test': (550, b'refused')}
            with self.assertRaises(smtplib.SMTPRecipientsRefused):
                send_staff_email('Delivery test', 'Synthetic test body')

    def test_branded_email_has_html_and_plain_text_and_escapes_content(self):
        with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as transport:
            smtp = transport.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            send_staff_email('Test <script>unsafe</script>', 'Line one\nLine two\n\n<script>private</script>')
            message = smtp.send_message.call_args.args[0]
        self.assertEqual(message.get_content_type(), 'multipart/alternative')
        self.assertEqual([part.get_content_type() for part in message.iter_parts()], ['text/plain', 'text/html'])
        self.assertIn('Line one\nLine two', message.get_body(preferencelist=('plain',)).get_content())
        html = message.get_body(preferencelist=('html',)).get_content()
        self.assertIn('George’s Oasis', html)
        self.assertIn('GOOD FOOD. GREAT TIMES. FOR EVERYONE.', html)
        self.assertIn('&lt;script&gt;private&lt;/script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)

    def test_inquiry_email_has_safe_absolute_button_and_no_customer_details(self):
        inquiry = SimpleNamespace(id=7, reference='GO-TEST1234', name='Private Guest', email='private@example.test', notes='Private message')
        self.app.config['STAFF_BASE_URL'] = 'https://restaurant.example'
        with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as transport:
            smtp = transport.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            deliver_notification(inquiry)
            message = smtp.send_message.call_args.args[0]
        html = message.get_body(preferencelist=('html',)).get_content()
        self.assertIn('https://restaurant.example/admin/inquiries/7', html)
        self.assertIn('Review the inquiry', html)
        self.assertIn('GO-TEST1234', html)
        self.assertIn('does not confirm a booking', html)
        for value in (inquiry.name, inquiry.email, inquiry.notes):
            self.assertNotIn(value, message.as_string())

    def test_missing_or_unsafe_inbox_url_uses_signin_instructions(self):
        for base in ('', 'javascript:alert(1)', '/admin', 'https://restaurant.example?unexpected=1'):
            self.app.config['STAFF_BASE_URL'] = base
            with self.app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as transport:
                smtp = transport.return_value.__enter__.return_value
                smtp.send_message.return_value = {}
                deliver_notification(SimpleNamespace(id=7, reference='GO-TEST1234'))
                message = smtp.send_message.call_args.args[0]
            html = message.get_body(preferencelist=('html',)).get_content()
            self.assertNotIn('Review the inquiry', html)
            self.assertIn('sign in at', html)
            self.assertNotIn('javascript:', html)
