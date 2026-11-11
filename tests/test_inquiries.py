import re
import unittest
from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from georges_oasis import create_app
from georges_oasis.models import db, Inquiry
class InquiryTest(unittest.TestCase):
    def setUp(self):
        self.notifications=[]
        self.app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://','INQUIRY_NOTIFIER':lambda inquiry:self.notifications.append(inquiry.reference),'INQUIRY_RATE_LIMIT':20})
        with self.app.app_context():db.create_all()
        self.client=self.app.test_client()
    def tearDown(self):
        with self.app.app_context():db.session.remove();db.drop_all();db.engine.dispose()
    def form(self):
        html=self.client.get('/gatherings?interest=Mini+golf').get_data(as_text=True)
        return {'csrf_token':re.search(r'name="csrf_token" value="([^"]+)"',html).group(1),'submission_token':re.search(r'name="submission_token" value="([^"]+)"',html).group(1),'name':'Test Organizer','contact_method':'email','email':'organizer@example.test','phone':'','occasion':'Birthday','guest_count':'12','preferred_date':'','date_flexibility':'Not sure yet','interests':['Mini golf'],'notes':'Test fixture only.'}
    def test_received_duplicate_retry_private_receipt(self):
        form=self.form();first=self.client.post('/gatherings',data=form);second=self.client.post('/gatherings',data=form)
        self.assertEqual(first.status_code,303);self.assertEqual(second.location,first.location);self.assertEqual(len(self.notifications),1)
        with self.app.app_context():self.assertEqual(db.session.query(Inquiry).count(),1)
        receipt=self.client.get(first.location);self.assertEqual(receipt.status_code,200)
        self.assertIn('does not confirm a booking',receipt.get_data(as_text=True));self.assertNotIn('organizer@example.test',receipt.get_data(as_text=True))
        self.assertEqual(receipt.headers['X-Robots-Tag'],'noindex, nofollow')
        self.assertEqual(self.app.test_client().get(first.location).status_code,404)
    def test_validation_preservation_and_safe_rendering(self):
        form=self.form();form.update(name='<script>alert(1)</script>',email='invalid',guest_count='-3')
        response=self.client.post('/gatherings',data=form);self.assertEqual(response.status_code,400)
        html=response.get_data(as_text=True);self.assertIn('Enter a valid email',html);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('name="interests" value="Mini golf"',html);self.assertEqual(self.notifications,[])
    def test_phone_only_flexible_inquiry(self):
        form=self.form();form.update(contact_method='phone',email='',phone='610 555 0100',guest_count='',date_flexibility='Flexible date')
        self.assertEqual(self.client.post('/gatherings',data=form).status_code,303)
        with self.app.app_context():
            inquiry=db.session.execute(db.select(Inquiry)).scalar_one();self.assertEqual(inquiry.contact_detail,'610 555 0100');self.assertIsNone(inquiry.guest_count)
    def test_short_inquiry_accepts_either_contact_method_without_event_details(self):
        for method, contact in (('email', 'organizer@example.test'), ('phone', '610 555 0100')):
            with self.subTest(method=method):
                original = self.form()
                form = {key: original[key] for key in ('csrf_token', 'submission_token', 'name')}
                form[method] = contact
                response = self.client.post('/gatherings', data=form)
                self.assertEqual(response.status_code, 303)
                with self.app.app_context():
                    inquiry = db.session.execute(db.select(Inquiry).filter_by(contact_method=method)).scalar_one()
                    self.assertEqual(inquiry.contact_detail, contact)
                    self.assertEqual(inquiry.occasion, 'Not sure yet')
                    self.assertEqual(inquiry.date_flexibility, 'Not sure yet')
                    self.assertEqual(inquiry.notes, '')
                    self.assertEqual(inquiry.interests, [])

    def test_short_inquiry_requires_a_way_to_follow_up(self):
        original = self.form()
        form = {key: original[key] for key in ('csrf_token', 'submission_token', 'name')}
        response = self.client.post('/gatherings', data=form)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Enter an email address or phone number', response.get_data(as_text=True))
        self.assertEqual(self.notifications, [])
    def test_notification_outage_keeps_receipt_and_owner_alert(self):
        def fail(inquiry):raise RuntimeError('Test mail outage')
        self.app.config['INQUIRY_NOTIFIER']=fail
        with self.assertLogs(self.app.logger,level='ERROR'):response=self.client.post('/gatherings',data=self.form())
        self.assertEqual(response.status_code,303)
        with self.app.app_context():self.assertEqual(db.session.execute(db.select(Inquiry)).scalar_one().notification_state,'failed')
        with self.client.session_transaction() as session:session['owner']=True
        self.assertIn('direct dashboard review',self.client.get('/admin').get_data(as_text=True))
    def test_storage_failure_preserves_form_without_success(self):
        form=self.form()
        with patch('georges_oasis.inquiries.db.session.commit',side_effect=OperationalError('test',{},Exception('fixture'))):response=self.client.post('/gatherings',data=form)
        self.assertEqual(response.status_code,503);self.assertIn('couldn’t save your request',response.get_data(as_text=True));self.assertIn('Test Organizer',response.get_data(as_text=True));self.assertEqual(self.notifications,[])
    def test_csrf_honeypot_email_injection_rate_limit(self):
        self.assertEqual(self.client.post('/gatherings',data={}).status_code,400)
        form=self.form();form['website']='spam';self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        form=self.form();form['email']='x@example.test\r\nBcc: another@example.test';self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        self.app.config['INQUIRY_RATE_LIMIT']=2
        self.assertEqual(self.client.post('/gatherings',data=self.form()).status_code,429);self.assertEqual(self.notifications,[])
    def test_required_contact_and_date(self):
        form=self.form();form.update(date_flexibility='Preferred date',preferred_date='')
        self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        form.update(preferred_date='2000-01-01');self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
        form.update(date_flexibility='Not sure yet',preferred_date='',contact_method='phone',phone='123');self.assertEqual(self.client.post('/gatherings',data=form).status_code,400)
    def test_authenticated_owner_review(self):
        self.client.post('/gatherings',data=self.form());self.assertEqual(self.client.get('/admin/inquiries').status_code,302)
        with self.client.session_transaction() as session:session['owner']=True
        detail=self.client.get('/admin/inquiries/1').get_data(as_text=True)
        token=re.search(r'name="csrf_token" value="([^"]+)"',detail).group(1)
        self.assertIn('organizer@example.test',detail)
        self.assertEqual(self.client.post('/admin/inquiries/1',data={'csrf_token':token,'staff_state':'contacted'}).status_code,302)
        with self.app.app_context():self.assertEqual(db.session.get(Inquiry,1).staff_state,'contacted')
if __name__=='__main__':unittest.main()
