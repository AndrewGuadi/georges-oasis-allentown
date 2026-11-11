import io
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from PIL import Image
from flask_migrate import upgrade
from georges_oasis import create_app
from georges_oasis.models import db, Promotion


class OwnerWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + self.folder.name + "/test.sqlite"})
        self.app.instance_path = self.folder.name
        with self.app.app_context():
            upgrade()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.folder.cleanup()

    def token(self, path):
        html = self.client.get(path).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    def login(self):
        return self.client.post('/admin/login', data={"csrf_token": self.token('/admin/login'), "username": "username", "password": "password"})

    def test_login_and_csrf(self):
        self.assertEqual(self.client.get('/admin').status_code, 302)
        self.assertEqual(self.client.post('/admin/display').status_code, 400)
        response = self.client.post('/admin/login', data={"csrf_token": self.token('/admin/login'), "username": "username", "password": "wrong"})
        self.assertIn(b'incorrect', response.data)
        self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.client.get('/admin').status_code, 200)

    def test_offer_upload_schedule_and_visibility(self):
        self.login()
        picture = io.BytesIO()
        Image.new('RGB', (30, 30), 'green').save(picture, 'PNG')
        picture.seek(0)
        response = self.client.post('/admin/promotions/new', data={"csrf_token": self.token('/admin/promotions/new'), "kind": "coupon", "title": "Test family coupon", "description": "Test terms", "code": "FAMILY", "enabled": "on", "action":"publish", "image": (picture, 'photo.png')})
        self.assertEqual(response.status_code, 302)
        self.assertIn(b'Test family coupon', self.client.get('/').data)
        with self.app.app_context():
            offer = db.session.execute(db.select(Promotion)).scalar_one()
            offer_id, filename = offer.id, offer.image
        with self.client.get('/admin/images/' + filename) as image_response:
            self.assertEqual(image_response.status_code, 200)
        self.client.post('/admin/display', data={"csrf_token": self.token('/admin'), "deals_enabled": "on"})
        self.assertNotIn(b'Test family coupon', self.client.get('/').data)
        self.client.post('/admin/display', data={"csrf_token": self.token('/admin'), "coupons_enabled": "on", "deals_enabled": "on"})
        with self.app.app_context():
            offer = db.session.get(Promotion, offer_id)
            offer.kind = 'deal'
            offer.starts_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
            db.session.commit()
        self.assertNotIn(b'id="current-offers"', self.client.get('/').data)
        with self.app.app_context():
            offer = db.session.get(Promotion, offer_id)
            offer.starts_at = None
            db.session.commit()
        self.assertIn(b'id="current-offers"', self.client.get('/').data)
        with self.app.app_context():
            offer = db.session.get(Promotion, offer_id)
            offer.ends_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
            db.session.commit()
        self.assertNotIn(b'id="current-offers"', self.client.get('/').data)
        invalid = self.client.post('/admin/promotions/new', data={"csrf_token": self.token('/admin'), "kind": "coupon", "title": "Bad dates", "starts_at": "2026-09-23T12:00", "ends_at": "2026-09-22T12:00"})
        self.assertIn(b'end must be later', invalid.data)
        with self.app.app_context():
            self.assertEqual(db.session.query(Promotion).count(), 1)


if __name__ == '__main__':
    unittest.main()
