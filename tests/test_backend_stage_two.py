"""End-to-end stage-two invariants using real migrations and isolated storage."""
from copy import deepcopy
from datetime import timedelta
import io
import re
import tempfile
import unittest
from PIL import Image
from flask_migrate import upgrade
from werkzeug.security import generate_password_hash
from georges_oasis import create_app
from georges_oasis.content import load_content, public_content
from georges_oasis.models import (db, ContentRecord, ContentRevision, Inquiry, InquiryHistory,
    InquiryNote, StaffUser, MediaAsset, NotificationOutbox, utcnow)
from georges_oasis.services.catalog import import_catalog, to_public
from georges_oasis.services.notifications import drain


class BackendStageTwoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = generate_password_hash('fixture-long-passphrase')

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.sent = []
        self.app = create_app({'TESTING':True, 'WTF_CSRF_ENABLED':False,
            'SQLALCHEMY_DATABASE_URI':'sqlite:///' + self.folder.name + '/test.sqlite',
            'INQUIRY_NOTIFIER':lambda inquiry:self.sent.append(inquiry.reference)})
        self.app.instance_path = self.folder.name
        self.client = self.app.test_client()
        with self.app.app_context():
            upgrade()
            self.source = load_content()
            import_catalog(self.source)
        with self.client.session_transaction() as session:
            session['owner'] = True

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.folder.cleanup()

    def record(self, key='breakfast-1'):
        with self.app.app_context():
            row = db.session.scalar(db.select(ContentRecord).where(ContentRecord.key==key))
            return row.id, row.version_id

    def item_form(self, **changes):
        rid, version = self.record()
        with self.app.app_context():
            row = db.session.get(ContentRecord,rid)
            data = to_public(row.draft.data)
        form = {'version_id':str(version),'action':'draft','name':data['name'],'parent_key':'breakfast',
            'position':'0','group':data['group'],'description':data['description'],'price':'12.34',
            'price_note':'','source':'Owner reviewed fixture','variants':'','add_ons':''}
        form.update(changes)
        return rid, form

    def submit(self, **changes):
        html = self.client.get('/gatherings').get_data(as_text=True)
        form = {'submission_token':re.search(r'name="submission_token" value="([^"]+)"',html).group(1),
            'name':'Fixture Guest','contact_method':'phone','phone':'610 555 0100','occasion':'Birthday',
            'guest_count':'12','date_flexibility':'Not sure yet','interests':['Mini golf'],'notes':'Customer message'}
        form.update(changes)
        return self.client.post('/gatherings',data=form), form

    def workflow(self, **changes):
        with self.app.app_context():
            row=db.session.scalar(db.select(Inquiry))
            form={'version_id':str(row.version_id),'staff_state':row.staff_state,'inquiry_type':row.inquiry_type}
            inquiry_id=row.id
        form.update(changes)
        return self.client.post(f'/admin/inquiries/{inquiry_id}',data=form)

    def test_import_reconciles_cents_and_is_idempotent(self):
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(ContentRecord).where(ContentRecord.kind=='item')),212)
            for category in self.source['menu_categories']:
                for item in category['items']:
                    row=db.session.scalar(db.select(ContentRecord).where(ContentRecord.key==item['id']))
                    restored=to_public(row.draft.data)
                    self.assertEqual(restored,item)
            self.assertEqual(import_catalog(self.source)['created'],0)
            changed=deepcopy(self.source);changed['menu_categories'][0]['items'][0]['name']='Conflict'
            with self.assertRaises(ValueError):import_catalog(changed)
            self.assertFalse(public_content()['show_menu_prices'])
            self.assertEqual(db.session.execute(db.text('PRAGMA foreign_keys')).scalar(),1)

    def test_draft_publish_and_stale_write(self):
        rid,form=self.item_form(name='Reviewed breakfast fixture')
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data=form).status_code,302)
        self.assertNotIn(b'Reviewed breakfast fixture',self.client.get('/food-and-ice-cream').data)
        self.assertIn(b'Reviewed breakfast fixture',self.client.get('/admin/preview/food').data)
        stale=self.client.post(f'/admin/content/{rid}',data=form)
        self.assertEqual(stale.status_code,409)
        self.assertIn(b'Reviewed breakfast fixture',stale.data)
        _,form=self.item_form(name='Reviewed breakfast fixture',action='publish',prices_reviewed='on')
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data=form).status_code,302)
        self.assertIn(b'Reviewed breakfast fixture',self.client.get('/food-and-ice-cream').data)
        self.assertNotIn(b'$12.34',self.client.get('/food-and-ice-cream').data)

    def test_price_switch_only_publishes_reviewed_prices(self):
        rid,form=self.item_form(action='publish',prices_reviewed='on')
        self.client.post(f'/admin/content/{rid}',data=form)
        sid,version=self.record('catalog-settings')
        response=self.client.post(f'/admin/content/{sid}',data={'version_id':version,'action':'publish','show_prices':'on','weekdays':['2','3','4']})
        self.assertEqual(response.status_code,302)
        html=self.client.get('/food-and-ice-cream').get_data(as_text=True)
        self.assertIn('$12.34',html)
        self.assertNotIn('$10.95',html)
        self.assertNotIn('$3.00',html)

    def test_bad_price_rejected_and_draft_retained(self):
        for price in ['NaN','-1','1.234','Infinity','1e99999999']:
            rid,form=self.item_form(price=price)
            self.assertEqual(self.client.post(f'/admin/content/{rid}',data=form).status_code,400,price)
        with self.app.app_context():
            row=db.session.get(ContentRecord,rid)
            self.assertEqual(row.draft.data['price_cents'],1095)

    def test_pause_archive_restore_and_duplicate(self):
        rid,version=self.record()
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data={'version_id':version,'action':'pause'}).status_code,302)
        self.assertNotIn(b'<h4>Monte Cristo</h4>',self.client.get('/food-and-ice-cream').data)
        rid,version=self.record()
        with self.app.app_context():
            revision=db.session.get(ContentRecord,rid).draft_id
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data={'version_id':version,'action':'restore','revision_id':revision}).status_code,302)
        rid,version=self.record()
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data={'version_id':version,'action':'duplicate'}).status_code,302)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(ContentRecord).where(ContentRecord.kind=='item')),213)

    def test_general_request_private_notes_search_and_conflict(self):
        result,_=self.submit(inquiry_type='general',occasion='',interests=[],notes='Question about access')
        self.assertEqual(result.status_code,303)
        self.assertEqual(self.workflow(action='note',note='Staff-only followup marker').status_code,302)
        listing=self.client.get('/admin/inquiries?q=followup+marker&inquiry_type=general')
        self.assertIn(b'Fixture Guest',listing.data)
        self.assertIn(b'Fixture Guest',self.client.get('/admin/inquiries?q=6105550100').data)
        self.assertNotIn(b'Fixture Guest',self.client.get('/admin/inquiries?q=missing').data)
        self.assertNotIn(b'Staff-only',self.client.get(result.location).data)
        self.assertEqual(self.workflow(staff_state='confirmed').status_code,400)
        self.assertEqual(self.client.post('/admin/inquiries/1',data={'version_id':'1','action':'note','note':'Stale note'}).status_code,409)

    def test_all_statuses_and_required_reasons(self):
        self.submit()
        for state in ['contacted','tentative_reservation','confirmed']:
            self.assertEqual(self.workflow(staff_state=state).status_code,302)
        self.assertEqual(self.workflow(staff_state='cancelled').status_code,400)
        self.assertEqual(self.workflow(staff_state='cancelled',reason='Customer cancelled').status_code,302)
        self.assertEqual(self.workflow(staff_state='new',reason='Reopened by customer').status_code,302)
        self.assertEqual(self.workflow(staff_state='other',reason='Need more details').status_code,302)
        self.assertEqual(self.workflow(staff_state='spam').status_code,302)
        self.assertNotIn(b'Fixture Guest',self.client.get('/admin/inquiries').data)
        self.assertIn(b'Fixture Guest',self.client.get('/admin/inquiries?staff_state=spam').data)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(InquiryHistory)),8)
        self.assertEqual(self.sent,[])

    def test_queue_commit_duplicate_retry_and_recovery(self):
        response,form=self.submit()
        self.assertEqual(response.status_code,303)
        self.assertEqual(self.client.post('/gatherings',data=form).location,response.location)
        self.assertEqual(self.sent,[])
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(NotificationOutbox)),1)
            row=db.session.scalar(db.select(NotificationOutbox))
            row.state='sending';row.lease_until=utcnow()-timedelta(seconds=1);db.session.commit()
            self.assertEqual(drain(),1)
            self.assertEqual(drain(),0)
            self.assertEqual(db.session.scalar(db.select(Inquiry)).notification_state,'sent')
        self.assertEqual(len(self.sent),1)

    def test_role_permissions_disable_and_session_revocation(self):
        with self.app.app_context():
            user=StaffUser(username='fixture',display_name='Inquiry staff',role='inquiry',password_hash=self.password_hash)
            db.session.add(user);db.session.commit();uid=user.id
        self.client.post('/admin/logout')
        self.assertEqual(self.client.post('/admin/login',data={'username':'fixture','password':'fixture-long-passphrase'}).status_code,302)
        self.assertEqual(self.client.get('/admin/inquiries').status_code,200)
        for path in ['/admin/menu','/admin/specials','/admin/media','/admin/staff','/admin/preview/food']:
            self.assertEqual(self.client.get(path).status_code,403,path)
        with self.app.app_context():
            user=db.session.get(StaffUser,uid);user.active=False;user.session_version+=1;db.session.commit()
        self.assertEqual(self.client.get('/admin/inquiries').status_code,302)

    def test_media_private_then_published_and_reencoded(self):
        image=io.BytesIO();Image.new('RGB',(40,30),'green').save(image,'PNG');image.seek(0)
        response=self.client.post('/admin/media',data={'image':(image,'../../untrusted.png'),'alt':'Fixture image','source':'Fixture rights'})
        self.assertEqual(response.status_code,302)
        with self.app.app_context():asset=db.session.scalar(db.select(MediaAsset));key=asset.id
        path=f'/media/{key}/400.webp'
        with self.client.get(path) as response:
            self.assertEqual(response.status_code,200)
        self.assertEqual(self.app.test_client().get(path).status_code,404)
        rid,form=self.item_form(action='publish',photo='upload:'+key)
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data=form).status_code,302)
        public=self.app.test_client().get(path)
        self.assertEqual(public.status_code,200)
        self.assertIn('immutable',public.headers['Cache-Control'])
        self.assertEqual(public.mimetype,'image/webp')
        public.close()
        bad=self.client.post('/admin/media',data={'image':(io.BytesIO(b'not image'),'fake.png'),'alt':'Bad image'})
        self.assertEqual(bad.status_code,400)

    def test_weekly_publication_and_incomplete_recurring(self):
        rid,version=self.record('weekly:wednesday')
        form={'version_id':version,'title':'Fixture Wednesday','weekday':'2','position':'0','photo':'george-oasis-menu-food-spread','source':'Fixture owner','dishes':'Special dish | Fixture description | 9.99','prices_reviewed':'on','action':'publish'}
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data=form).status_code,302)
        html=self.client.get('/specials').data
        self.assertIn(b'Special dish',html);self.assertIn(b'$9.99',html)
        rid,version=self.record('recurring:burger-night')
        response=self.client.post(f'/admin/content/{rid}',data={'version_id':version,'title':'Incomplete','weekday':'2','source':'Owner','action':'publish'})
        self.assertEqual(response.status_code,400)

    def test_pagination_and_literal_search(self):
        self.submit(name='Literal % underscore_ name')
        self.assertIn(b'Literal',self.client.get('/admin/inquiries?q=%25').data)
        self.assertNotIn(b'Literal',self.client.get('/admin/inquiries?q=absent%25').data)
        self.assertEqual(self.client.get('/admin/inquiries?received_from=invalid').status_code,400)
        self.assertIn(b'Literal',self.client.get('/admin/inquiries?interest=Mini+golf').data)
        self.assertNotIn(b'Literal',self.client.get('/admin/inquiries?interest=Dining').data)
        self.assertEqual(self.client.get('/admin/menu?state=unreviewed').status_code,200)
        self.assertEqual(self.client.get('/admin/menu?page=2&q=').status_code,200)

    def test_anonymous_menu_cache_invalidates_on_publish_and_excludes_staff(self):
        public=self.app.test_client()
        self.assertEqual(public.get('/food-and-ice-cream').status_code,200)
        self.assertEqual(public.get('/food-and-ice-cream').status_code,200)
        cache=self.app.extensions['anonymous_menu_pages']
        self.assertIn('/food-and-ice-cream',cache)
        self.assertNotIn('Set-Cookie',public.get('/food-and-ice-cream').headers)
        rid,form=self.item_form(name='Immediate publication fixture',action='publish')
        self.assertEqual(self.client.post(f'/admin/content/{rid}',data=form).status_code,302)
        self.assertIn(b'Immediate publication fixture',public.get('/food-and-ice-cream').data)
        self.assertEqual(self.client.get('/admin/preview/food').headers['Cache-Control'],'no-store')

    def test_search_index_updates_transactionally_and_handles_literal_quotes(self):
        self.submit(name='Fixture "quoted" guest')
        self.assertIn(b'Fixture', self.client.get('/admin/inquiries?q=quoted').data)
        self.assertIn(b'Fixture', self.client.get('/admin/inquiries?q=%22quoted%22').data)
        self.workflow(action='note',note='Transactional internal phrase')
        self.assertIn(b'Fixture',self.client.get('/admin/inquiries?q=Transactional').data)
        with self.app.app_context():
            note=InquiryNote(inquiry_id=1,actor='rollback-test',body='Never committed marker')
            db.session.add(note);db.session.flush();db.session.rollback()
        self.assertNotIn(b'Fixture',self.client.get('/admin/inquiries?q=Never+committed').data)

    def test_replacing_weekly_menu_publishes_newest_without_duplicate_day(self):
        rid,version=self.record('weekly:wednesday')
        response=self.client.post(f'/admin/content/{rid}',data={'version_id':version,'action':'duplicate'})
        location=response.location
        self.assertEqual(response.status_code,302)
        with self.app.app_context():
            newest=db.session.scalar(db.select(ContentRecord).where(ContentRecord.kind=='weekly').order_by(ContentRecord.id.desc()))
            new_id,version=newest.id,newest.version_id
        response=self.client.post(f'/admin/content/{new_id}',data={'version_id':version,'action':'publish','title':'Replacement Wednesday fixture','weekday':'2','source':'Fixture owner','photo':'george-oasis-menu-food-spread','dishes':'Replacement dish | Description |','position':'0'})
        self.assertEqual(response.status_code,302)
        html=self.client.get('/specials').get_data(as_text=True)
        self.assertIn('Replacement Wednesday fixture',html)
        self.assertEqual(html.count('<h4>Replacement dish</h4>'),1)

    def test_parallel_rate_limit_is_atomic(self):
        from concurrent.futures import ThreadPoolExecutor
        from georges_oasis.services.abuse import take_limit
        def attempt(_):
            with self.app.app_context():
                return take_limit('parallel-fixture', 'same-client', 10)
        with ThreadPoolExecutor(max_workers=10) as pool:
            results=list(pool.map(attempt,range(20)))
        self.assertEqual(sum(results),10)

    def test_exhausted_worker_lease_surfaces_failure(self):
        self.submit()
        with self.app.app_context():
            row=db.session.scalar(db.select(NotificationOutbox))
            row.state='sending';row.attempts=5;row.lease_until=utcnow()-timedelta(minutes=1)
            db.session.commit()
            self.assertEqual(drain(),0)
            self.assertEqual(db.session.get(NotificationOutbox,row.id).state,'failed')
            self.assertEqual(db.session.scalar(db.select(Inquiry)).notification_state,'failed')
        self.assertEqual(self.sent,[])

    def test_submission_body_limit_precedes_csrf_parsing(self):
        self.assertEqual(self.client.post('/gatherings',data={'notes':'x'*40000}).status_code,413)

    def test_staff_export_requires_password_and_escapes_formulas(self):
        self.submit(name='=Untrusted spreadsheet name')
        with self.app.app_context():
            user=StaffUser(username='export-owner',display_name='Owner',role='owner',password_hash=self.password_hash)
            db.session.add(user);db.session.commit();uid=user.id
        with self.client.session_transaction() as session:
            session['staff_id']=uid;session['staff_version']=1
        self.assertEqual(self.client.post('/admin/inquiries/export',data={'current_password':'wrong'}).status_code,403)
        response=self.client.post('/admin/inquiries/export',data={'current_password':'fixture-long-passphrase'})
        self.assertEqual(response.status_code,200)
        self.assertIn(b"'=Untrusted",response.data)
        self.assertEqual(response.headers['Cache-Control'],'no-store')

    def test_dated_offer_draft_does_not_mutate_public(self):
        response=self.client.post('/admin/promotions/new',data={'title':'Published fixture','kind':'deal','enabled':'on','action':'publish'})
        self.assertEqual(response.status_code,302)
        from georges_oasis.models import Promotion
        with self.app.app_context():row=db.session.scalar(db.select(Promotion));version=row.version_id;rid=row.id
        response=self.client.post(f'/admin/promotions/{rid}/edit',data={'title':'Unpublished replacement','kind':'deal','enabled':'on','action':'draft','version_id':version})
        self.assertEqual(response.status_code,302)
        self.assertIn(b'Published fixture',self.client.get('/').data)
        self.assertNotIn(b'Unpublished replacement',self.client.get('/').data)
        self.assertIn(b'Unpublished replacement',self.client.get(f'/admin/promotions/{rid}/edit').data)


class PopulatedMigrationTest(unittest.TestCase):
    def test_legacy_closed_preserves_submission_and_maps_to_other(self):
        with tempfile.TemporaryDirectory() as folder:
            app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite:///'+folder+'/legacy.sqlite'})
            with app.app_context():
                upgrade(revision='3a72d189c401')
                db.session.execute(db.text("INSERT INTO inquiry (reference,submission_key,name,contact_method,contact_detail,occasion,date_flexibility,interests,notes,received_at,staff_state,notification_state) VALUES ('GO-LEGACY','legacy-key','Legacy fixture','phone','610 555 0100','Birthday','Flexible date','[\"Mini golf\"]','Original customer note',CURRENT_TIMESTAMP,'closed','sent')"))
                db.session.commit()
                upgrade()
                inquiry=db.session.scalar(db.select(Inquiry))
                self.assertEqual(inquiry.staff_state,'other')
                self.assertEqual(inquiry.contact_normalized,'6105550100')
                self.assertEqual(inquiry.inquiry_type,'event')
                self.assertEqual(inquiry.notes,'Original customer note')
                history=db.session.scalar(db.select(InquiryHistory))
                self.assertEqual(history.old_state,'closed')
                self.assertIn('Legacy closed',history.reason)
                self.assertEqual(db.session.execute(db.text('PRAGMA foreign_key_check')).all(),[])
                db.session.remove();db.engine.dispose()


if __name__=='__main__':unittest.main()
