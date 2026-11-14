"""Render branded emails with fixture data, without sending or using credentials."""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from georges_oasis import create_app
from georges_oasis.inquiries import deliver_notification, deliver_customer_acknowledgment, send_staff_email


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='/tmp/oasis-email-review')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'INQUIRY_NOTIFIER': None, 'INQUIRY_SENDER': 'website@example.test',
        'INQUIRY_RECIPIENT': 'staff@example.test', 'STAFF_BASE_URL': 'https://restaurant.example',
        'SMTP_HOST': 'localhost', 'SMTP_PORT': 587, 'SMTP_SSL': False,
        'SMTP_USERNAME': None, 'SMTP_PASSWORD': None})
    with app.app_context(), patch('georges_oasis.inquiries.smtplib.SMTP') as transport:
        smtp = transport.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        for kind in ('inquiry', 'inquiry-no-link', 'test', 'customer'):
            if kind == 'customer':
                deliver_customer_acknowledgment(SimpleNamespace(email='customer@example.test', reference='GO-TEST1234ABCD'))
            elif kind == 'test':
                send_staff_email('George’s Oasis — email delivery test',
                    'This is a requested test of the George’s Oasis website email settings.\n\n'
                    'No customer request or booking was created.\n\n'
                    'If you received this message, the configured SMTP server accepted the test and delivered it to this mailbox.')
            else:
                app.config['STAFF_BASE_URL'] = '' if kind == 'inquiry-no-link' else 'https://restaurant.example'
                deliver_notification(SimpleNamespace(id=7, reference='GO-TEST1234ABCD'))
            message = smtp.send_message.call_args.args[0]
            (output / f'{kind}.html').write_text(message.get_body(preferencelist=('html',)).get_content())
            (output / f'{kind}.txt').write_text(message.get_body(preferencelist=('plain',)).get_content())
            (output / f'{kind}.eml').write_bytes(message.as_bytes())
    print(f'Email previews saved to {output}. No messages sent.')


if __name__ == '__main__':
    main()
