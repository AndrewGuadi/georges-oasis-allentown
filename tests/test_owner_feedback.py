"""Owner feedback: retain menu choice without publishing outdated prices."""
import unittest
from copy import deepcopy
from georges_oasis import create_app
from georges_oasis.content import load_content, public_content, validate_content
from georges_oasis.models import db

APPROVED = {'status': 'approved', 'source': 'Owner test fixture', 'reviewed_at': '2026-10-26'}

class OwnerFeedbackTest(unittest.TestCase):
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

    def test_prices_and_old_downloads_are_absent_but_dishes_remain(self):
        for path in ['/food-and-ice-cream', '/ice-cream']:
            html = self.client.get(path).get_data(as_text=True)
            menu_html = html.split('id="desserts"', 1)[1] if path == '/ice-cream' else html
            self.assertNotIn('$', menu_html)
            self.assertNotIn('/static/images/menu/', html)
            self.assertNotIn('class="menu-addons"', html)
            self.assertEqual(html.count('id="sundae-toppings"'), 1)
            self.assertIn('Whipped cream · Malt', html)
        html = self.client.get('/food-and-ice-cream').get_data(as_text=True)
        self.assertEqual(html.count('data-menu-item '), 216)
        self.assertIn('Turkey or garden burger substitution available for the 4 oz burger.', html)
        self.assertIn('Check Ordering Menu', html)

    def test_price_switch_also_requires_current_approval(self):
        self.source['menu_pricing']['show_prices'] = True
        self.source['menu_categories'][0]['items'][0]['price'] = '10.95'
        self.app.config['SITE_CONTENT'] = self.source
        self.assertNotIn('$', self.client.get('/food-and-ice-cream').get_data(as_text=True))
        self.source['menu_pricing']['metadata'] = deepcopy(APPROVED)
        self.app.config['SITE_CONTENT'] = self.source
        self.assertIn('$10.95', self.client.get('/food-and-ice-cream').get_data(as_text=True))
        self.source['menu_pricing']['metadata']['valid_until'] = '2020-01-01'
        self.app.config['SITE_CONTENT'] = self.source
        self.assertNotIn('$', self.client.get('/food-and-ice-cream').get_data(as_text=True))

    def test_specials_require_menu_and_dish_approval_and_preserve_preview(self):
        menu = self.source['special_menus'][0]
        menu['title'] = 'Confirmed menu fixture'
        menu['metadata']['status'] = 'draft'
        menu['items'] = [{'name':'Confirmed dish fixture', 'description':'A test dish.', 'metadata':deepcopy(APPROVED)}]
        self.app.config['SITE_CONTENT'] = self.source
        self.assertNotIn('Confirmed dish fixture', self.client.get('/specials').get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(public_content(include_drafts=True)['special_menus'][0]['items'][0]['name'], 'Confirmed dish fixture')
        menu['metadata'] = deepcopy(APPROVED)
        self.app.config['SITE_CONTENT'] = self.source
        html = self.client.get('/specials').get_data(as_text=True)
        self.assertIn('Confirmed dish fixture', html)
        self.assertIn('View the Wednesday special menu', html)
        menu['items'][0]['metadata']['status'] = 'paused'
        self.app.config['SITE_CONTENT'] = self.source
        self.assertNotIn('Confirmed dish fixture', self.client.get('/specials').get_data(as_text=True))
        self.assertNotIn('images/specials/burger-night.webp', self.client.get('/specials').get_data(as_text=True))
        menu['weekday'] = 1
        self.assertTrue(validate_content(self.source))

    def test_weekly_specials_use_the_same_records_on_home_and_specials(self):
        home = self.client.get('/').get_data(as_text=True)
        specials = self.client.get('/specials').get_data(as_text=True)
        for day, title, flyer in (
            ('wednesday', 'Burger Night', 'burger-night'),
            ('thursday', 'Half-Price Appetizers', 'half-price-appetizers'),
            ('friday', 'Crabcake Fridays', 'crabcake-fridays'),
        ):
            self.assertIn(f'href="/specials#special-{day}"', home)
            self.assertIn(title, home)
            self.assertIn(f'id="special-{day}"', specials)
            self.assertIn(title, specials)
            with self.client.get(f'/static/images/specials/{flyer}.webp') as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'image/webp')
        self.assertNotIn('special-tuesday', specials)

    def test_home_hours_and_burgers_precede_experience_cards(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertLess(html.index('quick-hours'), html.index('class="features"'))
        self.assertLess(html.index('A burger worth slowing down for'), html.index('class="features"'))
        self.assertIn('Char-grilled burgers', html)
        self.assertIn('View week', html)
        self.assertIn('Dinner follows its own schedule', html)
