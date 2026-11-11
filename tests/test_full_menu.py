import unittest
from html import unescape
from georges_oasis import create_app
from georges_oasis.content import load_content, public_content, validate_content
from georges_oasis.models import db


class FullMenuTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        with self.app.app_context():
            db.create_all()
            self.content = load_content()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_complete_published_inventory_and_original_pages(self):
        html = unescape(self.client.get('/food-and-ice-cream').get_data(as_text=True))
        self.assertEqual(html.count('data-menu-item '), 212)
        self.assertEqual(len(self.content['menu_sources']), 7)
        self.assertEqual(validate_content(self.content), [])
        for category in self.content['menu_categories']:
            self.assertTrue(category['items'], category['id'])
            for item in category['items']:
                self.assertIn('<h4>'+item['name']+'</h4>', html)
            if category.get('photo'):
                with self.app.test_request_context():
                    context = {}
                    self.app.update_template_context(context)
                    photo = context['photo_url'](category['photo'])
                with self.client.get(photo) as response:
                    self.assertEqual(response.status_code, 200)
        self.assertIn('id="printed-menus"', html)
        for filename in ['Breakfast_Menu.pdf', 'Lunch_and_Dinner_Menu.pdf', 'Ice_Cream_and_Desserts_Menu.pdf']:
            self.assertIn(f'href="/static/menus/{filename}" target="_blank"', html)
            self.assertIn(f'download="{filename}"', html)
            with self.client.get(f'/static/menus/{filename}') as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'application/pdf')
                self.assertTrue(response.data.startswith(b'%PDF-'))
        self.assertNotIn('/static/images/menu/', html)
        for internal_copy in ['owner review', 'Source says', 'Eligibility requires', 'independently verified']:
            self.assertNotIn(internal_copy, html)

    def test_source_options_and_unpriced_items_remain_accurate(self):
        items = {item['name']:item for c in self.content['menu_categories'] for item in c['items']}
        self.assertEqual(items['Monte Cristo']['add_ons'], [])
        self.assertEqual(items['Eggs Benedict']['add_ons'][0]['price'], '3.00')
        self.assertEqual(items['Greek Omelet']['add_ons'], [])
        self.assertEqual(items['Carnitas Especial']['add_ons'][0]['price'], '2.50')
        self.assertEqual(items['Plain Burger']['add_ons'], [
            {'name':'Turkey or Garden burger substitution','price':'1.00'}, {'name':'Fries','price':'3.00'}])
        self.assertEqual(items['Hot Dog on a Roll']['add_ons'], [])
        self.assertEqual(items['Vegan Flatbread']['description'], 'Hummus, tomato, cucumber, arugula and olive oil.')
        self.assertIsNone(items['Homemade Baklava']['price'])
        with self.app.app_context():
            bakery = next(c for c in public_content()['menu_categories'] if c['id']=='bakery-and-custom-pies')
        self.assertNotIn('formatted_price', next(i for i in bakery['items'] if i['name']=='Homemade Baklava'))
        self.assertIn('For current prices', self.client.get('/food-and-ice-cream').get_data(as_text=True))

    def test_dessert_page_reuses_published_menu(self):
        html = self.client.get('/ice-cream').get_data(as_text=True)
        for name in ['Chocolate Sundae','Oasis Super Sundae','Homemade Baklava']:
            self.assertIn(name, html)
        self.assertNotIn('$5.75', html)
        self.assertNotIn('Moose Trail', html)
        self.assertIn('Ask at the counter for today’s flavors.', html)

