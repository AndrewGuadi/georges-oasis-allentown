"""Homepage launch rules: shared offers, contact details and service boundaries."""
import unittest
import re
from copy import deepcopy
from datetime import datetime
from georges_oasis import create_app
from georges_oasis.content import load_content, service_status
from georges_oasis.models import db
from georges_oasis.public.sitemap import PAGES


class HomepageReviewTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        with self.app.app_context():
            db.create_all()
            self.source = load_content()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_shared_offers_exclude_tuesday_and_unapproved_details(self):
        source = deepcopy(self.source)
        source['offers'] = [dict(id=str(day), title=f'Approved offer {day}', weekday=day,
            start_time='15:00', end_time='20:00', price=None, terms='Dine in only.',
            metadata={'status':'approved','source':'Test fixture','reviewed_at':'2026-10-16'}) for day in [1,2,3,4]]
        self.app.config['SITE_CONTENT'] = source
        for route in ['/', '/specials']:
            html = self.client.get(route).get_data(as_text=True)
            self.assertNotIn('Approved offer 1', html)
            self.assertNotIn('$0', html)
            for day in [2,3,4]:
                self.assertIn(f'Approved offer {day}', html)
            self.assertIn('Dine in only.', html)
        source['offers'][1]['metadata']['status'] = 'paused'
        source['offers'][2]['metadata']['valid_until'] = '2020-01-01'
        self.app.config['SITE_CONTENT'] = source
        for route in ['/', '/specials']:
            html = self.client.get(route).get_data(as_text=True)
            self.assertNotIn('Approved offer 2', html)
            self.assertNotIn('Approved offer 3', html)

    def test_draft_specials_are_not_claimed_absent(self):
        for route in ['/', '/specials']:
            html = self.client.get(route).get_data(as_text=True)
            self.assertNotIn('no current specials', html)
            self.assertNotIn('Conflicting source prices', html)
            self.assertNotIn('Wednesday Burger Night', html)
            for day in ['Wednesday','Thursday','Friday']:
                self.assertIn(day, html)

    def test_contact_is_shared_and_preview_is_not_indexed(self):
        self.app.config['INQUIRY_RECIPIENT'] = 'restaurant@example.test'
        for route in ['/'] + [page['path'] for page in PAGES]:
            response = self.client.get(route)
            html = response.get_data(as_text=True)
            self.assertIn('mailto:georgesoasisrestaurant@gmail.com', html)
            self.assertEqual(set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', html)), {'georgesoasisrestaurant@gmail.com'})
            self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
        self.assertIn('Disallow: /\n', self.client.get('/robots.txt').get_data(as_text=True))

    def test_dinner_next_service_exceptions_and_unknown_golf(self):
        dinner = next(s for s in self.source['services'] if s['key'] == 'dinner')
        now = datetime.fromisoformat('2026-10-16T14:00:00-04:00')
        self.assertEqual(service_status(dinner, now)['note'], 'Dinner begins at 3 PM today.')
        dinner['exceptions'] = {'2026-10-16': []}
        self.assertEqual(service_status(dinner, now)['note'], 'View service hours.')
        golf = next(s for s in self.source['services'] if s['key'] == 'golf')
        self.assertEqual(service_status(golf, now)['state'], 'unknown')
        saturday = next(s for s in self.source['services'] if s['key'] == 'dinner')['weekly']['5']
        self.assertEqual(saturday, [['08:00', '21:00']])
