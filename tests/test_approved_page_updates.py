"""Publication and customer-path checks for the approved page refinements."""
import unittest
from datetime import datetime, timedelta, timezone
from html import unescape

from georges_oasis import create_app
from georges_oasis.content import load_content, public_content
from georges_oasis.models import db, Promotion


class ApprovedPageUpdatesTest(unittest.TestCase):
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

    def test_featured_food_hides_outdated_prices_and_draft_dishes(self):
        toast = next(i for c in self.source['menu_categories'] for i in c['items'] if i['id']=='breakfast-35')
        toast['variants'][0]['price'] = '7.10'
        self.app.config['SITE_CONTENT'] = self.source
        html = self.client.get('/food-and-ice-cream').get_data(as_text=True)
        self.assertNotIn('$7.10', html)
        self.assertIn('href="/food-and-ice-cream#menu-item-breakfast-35"', html)
        toast['metadata']['status'] = 'draft'
        self.app.config['SITE_CONTENT'] = self.source
        with self.app.app_context():
            featured = public_content()['featured_menu_items']
        self.assertNotIn('breakfast-35', [i['id'] for i in featured])
        self.assertNotIn('$7.10', self.client.get('/food-and-ice-cream').get_data(as_text=True))

    def test_coupons_are_absent_unless_live(self):
        self.assertNotIn('coupons-offers', self.client.get('/specials').get_data(as_text=True))
        with self.app.app_context():
            offer = Promotion(kind='coupon', title='Approved coupon fixture', enabled=True, approval_status='approved',
                              starts_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(days=1))
            db.session.add(offer)
            db.session.commit()
            offer_id = offer.id
        self.assertNotIn('coupons-offers', self.client.get('/specials').get_data(as_text=True))
        with self.app.app_context():
            offer = db.session.get(Promotion, offer_id)
            offer.starts_at = None
            db.session.commit()
        self.assertIn('id="coupons-offers"', self.client.get('/specials').get_data(as_text=True))
        with self.app.app_context():
            db.session.get(Promotion, offer_id).ends_at = datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(seconds=1)
            db.session.commit()
        self.assertNotIn('coupons-offers', self.client.get('/specials').get_data(as_text=True))

    def test_ordering_hours_share_the_confirmed_restaurant_schedule(self):
        restaurant = next(s for s in self.source['services'] if s['key']=='restaurant')
        restaurant['weekly']['0'] = [['10:15','18:45']]
        self.app.config['SITE_CONTENT'] = self.source
        for path in ['/visit','/order']:
            html = unescape(self.client.get(path).get_data(as_text=True))
            self.assertIn('10:15 AM–6:45 PM', html)
        self.assertIn('View Ordering Hours', self.client.get('/order').get_data(as_text=True))

    def test_pending_facts_stay_unpublished_and_course_hours_stay_blank(self):
        self.assertEqual(next(s for s in self.source['services'] if s['key']=='golf')['weekly'], {})
        self.assertNotIn('Homemade Tomato Soup', self.client.get('/').get_data(as_text=True))
        for route in ['/ice-cream','/food-and-ice-cream']:
            self.assertNotIn('Moose Trail', self.client.get(route).get_data(as_text=True))
        self.assertIn('Hours not yet posted', self.client.get('/mini-golf').get_data(as_text=True))
        self.assertNotIn('George Sitaras', self.client.get('/our-story').get_data(as_text=True))
        self.assertEqual(self.client.get('/admin/content-review').status_code, 302)

    def test_corporate_inquiry_prefill_is_allowlisted_and_visit_facts_are_visible(self):
        html = self.client.get('/gatherings?occasion=Company+gathering').get_data(as_text=True)
        self.assertIn('name="occasion" value="Company gathering"', html)
        html = self.client.get('/gatherings?occasion=Unapproved+occasion').get_data(as_text=True)
        self.assertNotIn('name="occasion" value="Unapproved occasion"', html)
        for path in ['/visit','/gatherings']:
            self.assertIn('restaurant is wheelchair accessible', self.client.get(path).get_data(as_text=True))
        html = self.client.get('/ice-cream').get_data(as_text=True)
        self.assertIn('Order at the counter', html)
        self.assertIn('settle into a seat', html)
        self.assertIn('just for ice cream', html)

