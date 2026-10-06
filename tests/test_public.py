import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit

from georges_oasis import create_app
from georges_oasis.models import db


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.anchors = []
        self.images = []
        self.ids = []
        self.current = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.anchors.append(attrs)
            self.links.append(attrs.get('href', ''))
            if attrs.get('aria-current') == 'page':
                self.current.append(attrs['href'])
        if tag == 'img':
            self.images.append(attrs['src'])


class PublicPagesTest(unittest.TestCase):
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

    def test_sitemap_pages_and_all_navigation_targets(self):
        paths = ['/', '/food-and-ice-cream', '/mini-golf', '/gatherings', '/specials', '/our-story', '/visit']
        documents = {}
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            html = response.get_data(as_text=True)
            self.assertEqual(html.count('<h1'), 1, path)
            self.assertIn('Order Delivery', html)
            documents[path] = Document(html)
        for path, doc in documents.items():
            self.assertEqual(len(doc.ids), len(set(doc.ids)), path)
            self.assertEqual(doc.current, [path, path])  # Desktop and mobile navigation.
            for link in doc.links:
                self.assertNotIn(link, ['', '#'], path)
                url = urlsplit(link)
                if url.scheme or url.netloc:
                    continue
                target = url.path or path
                self.assertIn(target, documents, link)
                if url.fragment:
                    self.assertIn(url.fragment, documents[target].ids, link)
        self.assertEqual(len(documents['/'].images), 8)
        for image in documents['/'].images:
            with self.client.get(image) as response:
                self.assertEqual(response.status_code, 200, image)
                self.assertTrue(response.mimetype.startswith('image/'))

    def test_external_actions_and_configuration_changes(self):
        actions = {
            'order-foodbooking': 'food_ordering',
            'order-grubhub': 'delivery',
            'reserve-google': 'table_reservation',
            'group-reservation-email': 'group_reservation',
            'hiring-facebook': 'hiring',
        }
        paths = ['/', '/food-and-ice-cream', '/mini-golf', '/gatherings', '/specials', '/our-story', '/visit']
        for override in [False, True]:
            if override:
                self.app.config['EXTERNAL_LINKS'] = {
                    key: ('mailto:groups@example.test' if key == 'group_reservation'
                          else 'https://provider.example.test/' + key)
                    for key in actions.values()
                }
            for path in paths:
                html = self.client.get(path).get_data(as_text=True)
                self.assertNotIn('<iframe', html)
                doc = Document(html)
                outbound = [a for a in doc.anchors if 'data-action' in a]
                self.assertEqual({a['data-action'] for a in outbound}, set(actions), path)
                for anchor in outbound:
                    key = actions[anchor['data-action']]
                    self.assertEqual(anchor['href'], self.app.config['EXTERNAL_LINKS'][key])
                    if key == 'group_reservation':
                        self.assertNotIn('target', anchor)
                    else:
                        self.assertEqual(anchor['target'], '_blank')
                        self.assertEqual(set(anchor['rel'].split()), {'noopener', 'noreferrer'})
                # Desktop and mobile headers offer the same two ordering actions.
                header = html.split('</header>')[0]
                self.assertIn('data-action="order-foodbooking"', header)
                self.assertIn('data-action="order-grubhub"', header)
                self.assertNotIn('>View Menu</a>', header)
                self.assertEqual(header.count('data-action="order-foodbooking"'), 2)
                self.assertEqual(header.count('data-action="order-grubhub"'), 2)
        with self.app.test_request_context('/'):
            context = {}
            self.app.update_template_context(context)
            self.assertEqual(context['external_links'], self.app.config['EXTERNAL_LINKS'])

    def test_retired_and_unknown_routes_are_not_exposed(self):
        for path in ['/menu', '/ice-cream', '/parties', '/about', '/order', '/missing', '/homepage.html']:
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.assertEqual(self.client.post('/gatherings').status_code, 405)


if __name__ == '__main__':
    unittest.main()
