import re
import unittest
from werkzeug.security import generate_password_hash
from georges_oasis import create_app
from georges_oasis.models import db, Promotion


class ProductionTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_expired_csrf_keeps_customer_details(self):
        response = self.client.post('/gatherings', data={'name': 'Saved Name', 'email': 'guest@example.test', 'contact_method': 'email', 'csrf_token': 'expired'})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Saved Name', response.data)
        self.assertIn(b'guest@example.test', response.data)
        self.assertIn(b'Your form session expired', response.data)
        self.assertIn(b'name="csrf_token"', response.data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_login_limit_persists_across_clients(self):
        self.app.config['WTF_CSRF_ENABLED'] = False
        for _ in range(10):
            self.assertEqual(self.app.test_client().post('/admin/login', data={'username': 'username', 'password': 'wrong'}).status_code, 200)
        response = self.app.test_client().post('/admin/login', data={'username': 'username', 'password': 'password'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '900')

    def test_headers_and_custom_not_found(self):
        response = self.client.get('/does-not-exist')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Back to Home', response.data)
        self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])

    def test_production_rejects_demo_and_missing_hosts(self):
        with self.assertRaises(RuntimeError):
            create_app({'PRODUCTION': True})
        with self.assertRaises(RuntimeError):
            create_app({'PRODUCTION': True, 'OWNER_USERNAME': 'owner', 'OWNER_PASSWORD_HASH': generate_password_hash('password'), 'TRUSTED_HOSTS': ['example.test']})
        with self.assertRaises(RuntimeError):
            create_app({'PRODUCTION': True, 'OWNER_USERNAME': 'owner', 'OWNER_PASSWORD_HASH': generate_password_hash('test-strong-secret')})

    def test_deals_are_visible_without_javascript(self):
        with self.app.app_context():
            db.session.add(Promotion(kind='deal', title='Approved test offer', approval_status='approved', enabled=True))
            db.session.commit()
        response = self.client.get('/')
        self.assertIn(b'Approved test offer', response.data)
        self.assertNotIn(b'<dialog', response.data)
        self.assertNotIn(b'js/deals.js', response.data)

    def test_production_hosts_and_secure_sessions(self):
        app = create_app({'TESTING': True, 'PRODUCTION': True,
                          'OWNER_USERNAME': 'staff',
                          'OWNER_PASSWORD_HASH': generate_password_hash('test-only-unique-secret'),
                          'TRUSTED_HOSTS': ['restaurant.example']})
        self.assertTrue(app.config['SESSION_COOKIE_SECURE'])
        response = app.test_client().get('/', base_url='https://untrusted.example')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_data(as_text=True), 'Invalid host.')
        response = app.test_client().get('/missing', base_url='https://restaurant.example')
        self.assertEqual(response.status_code, 404)
        self.assertIn('max-age=31536000', response.headers['Strict-Transport-Security'])
