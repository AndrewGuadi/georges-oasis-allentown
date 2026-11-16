"""Homepage launch rules: shared offers, contact details and service boundaries."""
import unittest
import re
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch
from georges_oasis import create_app
from georges_oasis.content import load_content, public_content, service_status
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
        source['special_menus'] = []
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
        for menu in self.source['special_menus']:
            menu['metadata']['status'] = 'draft'
        self.app.config['SITE_CONTENT'] = self.source
        for route in ['/', '/specials']:
            html = self.client.get(route).get_data(as_text=True)
            self.assertNotIn('no current specials', html)
            self.assertNotIn('Conflicting source prices', html)
            self.assertNotIn('Burger Night', html)
            for day in ['Wednesday','Thursday','Friday']:
                self.assertIn(day, html)

    def test_homepage_special_follows_the_restaurants_day(self):
        cases = [
            ('2026-11-11T04:59:00+00:00', None, None),
            ('2026-11-11T05:00:00+00:00', 'wednesday', 'Burger Night'),
            ('2026-11-12T05:00:00+00:00', 'thursday', 'Half-Price Appetizers'),
            ('2026-11-13T05:00:00+00:00', 'friday', 'Crabcake Fridays'),
            ('2026-11-14T05:00:00+00:00', None, None),
        ]
        for timestamp, day, title in cases:
            with self.subTest(timestamp=timestamp):
                now = datetime.fromisoformat(timestamp)
                with patch('georges_oasis.public.routes.public_content', lambda: public_content(now=now)):
                    html = self.client.get('/').get_data(as_text=True)
                if day is None:
                    self.assertNotIn('id="today-special-dialog"', html)
                    continue
                dialog = html.split('id="today-special-dialog"', 1)[1].split('</dialog>', 1)[0]
                self.assertIn(f'id="today-special-title">{title}</h2>', dialog)
                self.assertIn(f'href="/specials#special-{day}"', dialog)
                self.assertIn('Today from 3 PM', dialog)

        for item in self.source['special_menus'][0]['items']:
            item['metadata']['status'] = 'draft'
        self.app.config['SITE_CONTENT'] = self.source
        wednesday = datetime.fromisoformat('2026-11-11T20:00:00+00:00')
        with patch('georges_oasis.public.routes.public_content', lambda: public_content(now=wednesday)):
            self.assertNotIn('id="today-special-dialog"', self.client.get('/').get_data(as_text=True))

    def test_contact_is_shared_and_preview_is_not_indexed(self):
        self.app.config['INQUIRY_RECIPIENT'] = 'restaurant@example.test'
        for route in ['/'] + [page['path'] for page in PAGES]:
            response = self.client.get(route)
            html = response.get_data(as_text=True)
            self.assertIn('mailto:georgesoasisrestaurant@gmail.com', html)
            self.assertEqual(set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', html)), {'georgesoasisrestaurant@gmail.com'})
            self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
        self.assertIn('Disallow: /\n', self.client.get('/robots.txt').get_data(as_text=True))

    def test_restaurant_next_service_exceptions_and_unknown_golf(self):
        restaurant = next(s for s in self.source['services'] if s['key'] == 'restaurant')
        now = datetime.fromisoformat('2026-10-16T06:00:00-04:00')
        self.assertEqual(service_status(restaurant, now)['note'], 'Opens at 7 AM today.')
        restaurant['exceptions'] = {'2026-10-16': []}
        self.assertEqual(service_status(restaurant, now)['exception_note'], 'Closed today: special schedule.')
        golf = next(s for s in self.source['services'] if s['key'] == 'golf')
        self.assertEqual(service_status(golf, now)['state'], 'unknown')

    def test_restaurant_hours_and_weekend_kitchen_cutoff(self):
        restaurant = next(s for s in self.source['services'] if s['key'] == 'restaurant')
        self.assertNotIn('dinner', [service['key'] for service in self.source['services']])
        self.assertEqual(restaurant['weekly'], {
            '0': [['07:00', '15:00']],
            '1': [['07:00', '19:30']],
            '2': [['07:00', '19:30']],
            '3': [['07:00', '19:30']],
            '4': [['07:00', '20:00']],
            '5': [['08:00', '20:00']],
            '6': [],
        })
        for date in ('2026-11-13', '2026-11-14'):
            with self.subTest(date=date):
                after_cutoff = datetime.fromisoformat(f'{date}T19:30:00-05:00')
                closing = datetime.fromisoformat(f'{date}T20:00:00-05:00')
                self.assertEqual(service_status(restaurant, after_cutoff)['state'], 'open')
                self.assertEqual(service_status(restaurant, closing)['state'], 'closed')
        for path, hours_markup in (('/', 'quick-hours-panel'), ('/visit', 'dining-hours-table'), ('/order', 'dining-hours-table')):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn(restaurant['schedule_note'], html.split(hours_markup, 1)[1])
                self.assertNotIn('dinner-hours', html)
        menu = self.client.get('/food-and-ice-cream').get_data(as_text=True)
        self.assertNotIn('restaurant and dinner hours separately', menu)
