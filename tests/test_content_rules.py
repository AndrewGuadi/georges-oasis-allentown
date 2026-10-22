import unittest
from copy import deepcopy
from datetime import datetime
from georges_oasis import create_app
from georges_oasis.content import publishable, service_status, offer_state, money, load_content, public_content
from georges_oasis.admin import parse_time
META={'status':'approved','source':'Owner-approved test fixture','reviewed_at':'2026-10-07','valid_from':None,'valid_until':None}
def instant(value):return datetime.fromisoformat(value)
def service(**changes):
    value={'key':'golf','name':'Golf','metadata':deepcopy(META),'season':'open','weekly':{str(i):[['09:00','20:00']] for i in range(7)},'exceptions':{},'cutoff_minutes':45}
    value.update(changes);return value
class ContentRulesTest(unittest.TestCase):
    def test_approval_and_validity_boundaries(self):
        record={'metadata':META|{'valid_from':'2026-10-07T15:00:00-04:00','valid_until':'2026-10-07T20:00:00-04:00'}}
        self.assertFalse(publishable(record,instant('2026-10-07T18:59:59+00:00')))
        self.assertTrue(publishable(record,instant('2026-10-07T19:00:00+00:00')))
        self.assertFalse(publishable(record,instant('2026-10-08T00:00:00+00:00')))
        record['metadata']['status']='paused';self.assertFalse(publishable(record,instant('2026-10-07T19:30:00+00:00')))
    def test_service_open_cutoff_close(self):
        for timestamp,expected in [('08:59:00','closed'),('09:00:00','open'),('19:15:00','cutoff_passed'),('20:00:00','closed')]:
            self.assertEqual(service_status(service(),instant('2026-10-07T'+timestamp+'-04:00'))['state'],expected)
    def test_holiday_season_and_temporary_override(self):
        now=instant('2026-10-07T12:00:00-04:00')
        self.assertEqual(service_status(service(exceptions={'2026-10-07':[]}),now)['state'],'closed')
        self.assertEqual(service_status(service(season='closed'),now)['state'],'seasonal_closed')
        self.assertEqual(service_status(service(override={'metadata':META,'note':'Weather closure'}),now)['state'],'temporary_closed')
        self.assertEqual(service_status(service(metadata=META|{'status':'draft'}),now)['state'],'unknown')
    def test_overnight_and_dst(self):
        overnight=service(weekly={str(i):[['22:00','02:00']] for i in range(7)},cutoff_minutes=None)
        self.assertEqual(service_status(overnight,instant('2026-10-08T01:30:00-04:00'))['state'],'open')
        repeated=service(weekly={'6':[['00:30','01:30']]},cutoff_minutes=None)
        for stamp,state in [('05:45','open'),('06:15','open'),('06:30','closed')]:
            self.assertEqual(service_status(repeated,instant('2026-11-01T'+stamp+':00+00:00'))['state'],state)
        skipped=service(weekly={'6':[['02:30','05:00']]},cutoff_minutes=None)
        self.assertEqual(service_status(skipped,instant('2026-03-08T07:29:00+00:00'))['state'],'closed')
        self.assertEqual(service_status(skipped,instant('2026-03-08T07:30:00+00:00'))['state'],'open')
    def test_admin_dst_validation(self):
        with self.assertRaises(ValueError):parse_time('2026-11-01T01:30')
        with self.assertRaises(ValueError):parse_time('2026-03-08T02:30')
        self.assertEqual(parse_time('2026-07-01T12:00').hour,16)
        self.assertEqual(parse_time('2026-12-01T12:00').hour,17)
    def test_recurring_offer_state(self):
        offer={'metadata':deepcopy(META),'weekday':2,'start_time':'15:00','end_time':'20:00'}
        for stamp,state in [('14:59:59','later_today'),('15:00:00','available_now'),('20:00:00','upcoming')]:
            self.assertEqual(offer_state(offer,instant('2026-10-07T'+stamp+'-04:00')),state)
        self.assertEqual(offer_state(offer|{'start_time':'bad'},instant('2026-10-08T12:00:00-04:00')),'hidden')
        self.assertEqual(offer_state(offer|{'metadata':META|{'status':'paused'}},instant('2026-10-07T16:00:00-04:00')),'hidden')
    def test_money_and_menu_publication(self):
        self.assertEqual(money('8.5'),'$8.50')
        for value in ['NaN','Infinity','-1','2.345']:
            with self.assertRaises(ValueError):money(value)
        app=create_app({'TESTING':True})
        with app.app_context():
            source=load_content(); category=next(c for c in source['menu_categories'] if c['id']=='ice-cream-and-desserts')
            for item in category['items']:item['metadata']['status']='draft'
            category['items'][0]['metadata']=deepcopy(META);app.config['SITE_CONTENT']=source
            dessert=next(c for c in public_content()['menu_categories'] if c['id']=='ice-cream-and-desserts')
            self.assertEqual(len(dessert['items']),1)
            self.assertEqual(dessert['items'][0]['formatted_price'],'$5.75')
if __name__=='__main__':unittest.main()
