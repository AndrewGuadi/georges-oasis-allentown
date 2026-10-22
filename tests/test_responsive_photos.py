import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

from flask import render_template_string
from PIL import Image

from georges_oasis import create_app
from georges_oasis.models import db
from georges_oasis.public.sitemap import PAGES


class ImageTags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.images = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))


class ResponsivePhotosTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.static = Path(self.app.static_folder)
        self.assets = json.loads((self.static / 'images/oasis/manifest.json').read_text())['assets']

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_packaged_variants_and_deduplicated_srcsets(self):
        with self.app.test_request_context():
            html = render_template_string(
                "{% from 'macros/oasis_image.html' import oasis_image with context %}"
                "{% for key in oasis_images %}{{ oasis_image(key) }}{% endfor %}"
            )
        images = ImageTags(html).images
        self.assertEqual(len(images), len(self.assets))
        for (key, asset), tag in zip(self.assets.items(), images):
            widths = []
            for variant in asset['variants'].values():
                path = self.static / variant['path']
                self.assertEqual(path.stat().st_size, variant['bytes'], key)
                with Image.open(path) as picture:
                    self.assertEqual(picture.size, (variant['width'], variant['height']), key)
                    self.assertNotIn('exif', picture.info, key)
                widths.append(variant['width'])
            descriptors = [int(source.rsplit(' ', 1)[1][:-1]) for source in tag['srcset'].split(', ')]
            self.assertEqual(descriptors, sorted(set(widths)), key)
            self.assertEqual(tag['alt'], asset['alt'])

    def test_public_pages_use_valid_responsive_sources_and_priority(self):
        for route in ['/'] + [p['path'] for p in PAGES]:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, route)
            images = ImageTags(response.get_data(as_text=True)).images
            priority = [i for i in images if i.get('fetchpriority') == 'high']
            self.assertLessEqual(len(priority), 1, route)
            for tag in images:
                if '/images/oasis/' not in tag['src']:
                    continue
                if 'golf-lightbox-image' in tag.get('class', ''):
                    # The lightbox swaps to the clicked link's full-size source.
                    self.assertEqual(tag['loading'], 'lazy', route)
                    continue
                self.assertTrue(tag.get('sizes'), route)
                self.assertTrue(tag.get('width') and tag.get('height'), route)
                self.assertEqual(tag['loading'], 'eager' if tag in priority else 'lazy', route)
                for candidate in tag['srcset'].split(', '):
                    source, width = candidate.rsplit(' ', 1)
                    with Image.open(self.static / source.removeprefix('/static/')) as picture:
                        self.assertEqual(picture.width, int(width[:-1]), route)
        home = self.client.get('/').get_data(as_text=True)
        self.assertNotIn('--hero-photo:', home)
        self.assertIn('Our Homemade Tomato Soup', home)
        self.assertIn('georges_history.webp', home)
        self.assertEqual(self.client.get('/static/images/oasis/SOURCE-MANIFEST.json').status_code, 404)
