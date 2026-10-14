import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit
from georges_oasis import create_app
from georges_oasis.models import db
from georges_oasis.public.sitemap import PAGES, LEGACY

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.links=[]; self.anchors=[]; self.images=[]; self.ids=[]; self.current=[]; self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if tag=='a':
            self.anchors.append(attrs); self.links.append(attrs.get('href',''))
            if attrs.get('aria-current')=='page':self.current.append(attrs['href'])
        if tag=='img':self.images.append(attrs['src'])

class PublicPagesTest(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
        with self.app.app_context():db.create_all()
        self.client=self.app.test_client()
    def tearDown(self):
        with self.app.app_context():db.session.remove(); db.drop_all(); db.engine.dispose()
    def test_all_routes_navigation_anchors_and_assets(self):
        documents={}
        for path in ['/']+[p['path'] for p in PAGES]:
            response=self.client.get(path); self.assertEqual(response.status_code,200,path)
            html=response.get_data(as_text=True)
            self.assertEqual(html.count('<h1'),1,path)
            self.assertNotIn('cdn.tailwindcss.com',html)
            self.assertNotIn('coming soon',html.lower())
            documents[path]=Document(html)
        for path,doc in documents.items():
            self.assertEqual(len(doc.ids),len(set(doc.ids)),path)
            self.assertEqual(doc.current,[path,path],path)
            for link in doc.links:
                self.assertNotIn(link,['','#'],path)
                url=urlsplit(link)
                if url.scheme or url.netloc:continue
                target=url.path or path
                if target.startswith('/static/'):
                    with self.client.get(target) as response:self.assertEqual(response.status_code,200,target)
                    continue
                self.assertIn(target,documents,link)
                if url.fragment:self.assertIn(url.fragment,documents[target].ids,link)
        self.assertEqual(len(documents['/'].images),8)
    def test_providers_are_configurable_and_missing_provider_has_fallback(self):
        actions={'order-foodbooking':'food_ordering','order-grubhub':'delivery','reserve-google':'table_reservation','hiring-facebook':'hiring'}
        for key in actions.values():self.app.config['EXTERNAL_LINKS'][key]='https://provider.example.test/'+key
        for path in ['/']+[p['path'] for p in PAGES]:
            for anchor in Document(self.client.get(path).get_data(as_text=True)).anchors:
                action=anchor.get('data-action')
                if action in actions:
                    self.assertEqual(anchor['href'],self.app.config['EXTERNAL_LINKS'][actions[action]])
                    self.assertEqual(anchor['target'],'_blank')
                    self.assertEqual(set(anchor['rel'].split()),{'noopener','noreferrer'})
                    self.assertIn('opens in a new tab',anchor['aria-label'])
        self.app.config['EXTERNAL_LINKS']['food_ordering']=None
        html=self.client.get('/order').get_data(as_text=True)
        self.assertIn('Call Us for Ordering',html)
        self.assertNotIn('href="None"',html)
    def test_legacy_redirects_preserve_query(self):
        for path in LEGACY:
            response=self.client.get(path+'?source=old-menu')
            self.assertEqual(response.status_code,301,path)
            self.assertIn('source=old-menu',response.location)
            self.assertEqual(self.client.get(response.location).status_code,200)
        for path in ['/about','/missing','/homepage.html','/pies']:
            self.assertEqual(self.client.get(path).status_code,404)
    def test_drafts_hidden_and_owner_preview_authenticated(self):
        self.assertNotIn('Monte Cristo',self.client.get('/food-and-ice-cream').get_data(as_text=True))
        self.assertNotIn('Burger Night',self.client.get('/specials').get_data(as_text=True))
        self.assertNotIn('18 holes',self.client.get('/').get_data(as_text=True))
        self.assertEqual(self.client.get('/admin/preview/food').status_code,302)
        with self.client.session_transaction() as session:session['owner']=True
        preview=self.client.get('/admin/preview/food')
        self.assertEqual(preview.status_code,200)
        self.assertIn('Monte Cristo',preview.get_data(as_text=True))
        self.assertIn('Owner preview',preview.get_data(as_text=True))
        self.assertEqual(preview.headers['X-Robots-Tag'],'noindex, nofollow')
        self.assertIn('no-store',preview.headers['Cache-Control'])
    def test_sitemap_and_review_source_protection(self):
        response=self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('/admin',response.get_data(as_text=True))
        self.assertNotIn('inquiry-received',response.get_data(as_text=True))
        self.assertEqual(self.client.get('/admin/source-menu/sources.json').status_code,302)

if __name__=='__main__':unittest.main()
