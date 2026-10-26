"""Photo placement, accuracy boundaries and progressive menu enhancement."""
import json
import unittest
from pathlib import Path
from html.parser import HTMLParser
from georges_oasis import create_app
from georges_oasis.content import load_content
from georges_oasis.models import db

class MenuPhotosTest(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
        with self.app.app_context():
            db.create_all()
            self.data=load_content()
        self.client=self.app.test_client()
        self.items={i['id']:i for c in self.data['menu_categories'] for i in c['items']}
    def tearDown(self):
        with self.app.app_context():
            db.session.remove();db.drop_all();db.engine.dispose()
    def test_specific_mismatches_are_not_used_to_fill_menu(self):
        self.assertNotIn('photo',self.items['breakfast-37'])  # Cream-filled toast is not plain toast.
        for id in ['lunch-and-dinner-27','lunch-and-dinner-32','lunch-and-dinner-35','children-3','bakery-vegan-baklava']:
            self.assertNotIn('photo',self.items[id])
        self.assertEqual(self.items['breakfast-35']['photo'],'george-oasis-strawberry-nutella-pancakes')
        self.assertEqual(self.items['lunch-and-dinner-21']['photo'],'george-oasis-greek-salad-wrap-and-fries')
        self.assertIn('separate sandwich',self.items['lunch-and-dinner-21']['photo_caption'])
    def test_reviewed_dish_photos_have_assets_and_descriptive_captions(self):
        manifest=json.loads((Path(self.app.static_folder)/'images/oasis/manifest.json').read_text())['assets']
        reviewed=[i for i in self.items.values() if i.get('photo_review')]
        self.assertEqual(len(reviewed),9)
        for item in reviewed:
            self.assertTrue(item['photo_alt']);self.assertTrue(item['photo_caption'])
            self.assertIn(item['photo'],manifest)
            for variant in manifest[item['photo']]['variants'].values():
                self.assertTrue((Path(self.app.static_folder)/variant['path']).is_file())
    def test_all_dishes_and_price_policy_survive_photo_enhancement(self):
        html=self.client.get('/food-and-ice-cream').get_data(as_text=True)
        self.assertEqual(html.count('data-menu-item '),212)
        self.assertNotIn('$',html)
        self.assertEqual(html.count('class="menu-item menu-item--pictured"'),13)
        self.assertIn('data-menu-group-photos',html)
        self.assertIn('id="menu-photo-viewer"',html)
        self.assertIn('js/photo-viewer.js',html)
        self.assertIn('href="/static/images/oasis/george-oasis-strawberry-nutella-pancakes-desktop.webp"',html)
        self.assertNotIn('george-oasis-chicken-and-waffles',html)
    def test_draft_dish_does_not_leave_its_new_photo_in_public_menu(self):
        self.items['breakfast-35']['metadata']['status']='draft'
        self.app.config['SITE_CONTENT']=self.data
        html=self.client.get('/food-and-ice-cream').get_data(as_text=True)
        self.assertNotIn('george-oasis-strawberry-nutella-pancakes',html)
