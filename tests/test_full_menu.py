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
        self.assertEqual(html.count('data-menu-item '), 216)
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
        self.assertNotIn('/static/images/menu/', html)
        for internal_copy in ['owner review', 'Source says', 'Eligibility requires', 'independently verified']:
            self.assertNotIn(internal_copy, html)

    def test_pdf_menu_is_a_secondary_action_above_the_online_menu(self):
        html = self.client.get('/food-and-ice-cream').get_data(as_text=True)
        self.assertEqual(html.count('Open/Download PDF Menu'), 1)
        self.assertIn('aria-haspopup="dialog" aria-controls="printed-menus"', html)
        self.assertIn('<dialog class="menu-pdf-dialog" id="printed-menus"', html)
        self.assertLess(html.index('id="menu-pdf-trigger"'), html.index('class="page-shell menu-layout"'))
        for filename in ['Breakfast_Menu.pdf', 'Lunch_and_Dinner_Menu.pdf', 'Ice_Cream_and_Desserts_Menu.pdf']:
            self.assertEqual(html.count(f'href="/static/menus/{filename}"'), 1)
            self.assertIn(f'href="/static/menus/{filename}" target="_blank" rel="noopener"', html)
        self.assertNotRegex(html, r'<a\b[^>]*\bdownload(?:[\s=>])')

    def test_source_options_and_unpriced_items_remain_accurate(self):
        items = {item['name']:item for c in self.content['menu_categories'] for item in c['items']}
        for name in [
            'NY Steak and Eggs', 'Greek Goodness Burrito', 'Brotherly Love Burrito',
            'Apple Cinnamon Pancakes', 'Bang Bang Shrimp', 'Build Your Own Rice Bowl',
            'Pizza Burger', 'Chesapeake Burger', 'Southwest Chicken Sandwich',
            'Grilled Salmon Teriyaki', 'Crispy Buffalo Chicken Cobb Salad',
            'Honey Dipped Fried Chicken',
        ]:
            self.assertIn(name, items)
            self.assertIsNone(items[name]['price'])
        for name in [
            'John’s Greek Wrap', 'Cheesesteak Egg Rolls', 'Buffalo Chicken Quesadilla',
            'Mushroom Swiss Burger', 'Mushroom Swiss Steak', 'Hot Dog on a Roll',
            'Cajun Chicken Sandwich', 'Char-Grilled Teriyaki Chicken',
        ]:
            self.assertNotIn(name, items)
        self.assertIn('pulled pork or smoked salmon', items['Eggs Benedict']['description'].lower())
        self.assertIn('Avocado available', items['Carnitas Especial']['description'])
        self.assertIn('Fries available', items['Plain Burger']['inclusions'])
        self.assertEqual(items['Vegan Flatbread']['description'], 'Hummus, tomato, cucumber, arugula and olives.')
        self.assertEqual(
            items['Apple Cinnamon Pancakes']['variants'],
            [{'label': '2 pancakes', 'price': None}, {'label': '3 pancakes', 'price': None}],
        )
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

