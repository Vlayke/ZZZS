import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import BadZipFile
from openpyxl import Workbook

os.environ['NO_WORKER'] = '1'
_temp = tempfile.TemporaryDirectory()
os.environ['DATA_DIR'] = _temp.name
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as a


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.client = a.app.test_client()
        with a.db() as c:
            for t in ['users', 'invites', 'events']:
                c.execute('DELETE FROM ' + t)
        a.put('bot_username', 'example_bot')
        self.headers = {'X-ZZZS-Request': '1'}
        self.rows = [dict(id='a', name='A', location='LJ', service='GP', source='gp', accepting='DA', provider='P', address='S'),
                     dict(id='b', name='B', location='KR', service='Dentist', source='dentistry', accepting='DA', provider='P', address='S')]

    def post(self, p, data):
        return self.client.post('/api/' + p, json=data, headers=self.headers)

    def test_lan_and_csrf_and_dns_rebinding(self):
        self.assertEqual(self.client.get('/api/state', environ_base={'REMOTE_ADDR': '8.8.8.8'}).status_code, 403)
        self.assertEqual(self.client.get('/api/state', headers={'Host':'evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/users', json={'chat_id':'1'}).status_code, 403)
        self.assertEqual(self.client.post('/api/users', json={'chat_id':'1'}, headers={**self.headers, 'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/health').status_code,200)

    def test_filter_isolation(self):
        self.assertEqual([r['id'] for r in a.matching(self.rows, {'locations':['LJ']})], ['a'])
        self.assertEqual([r['id'] for r in a.matching(self.rows, {'sources':['dentistry']})], ['b'])
        self.assertEqual(a.matching(self.rows, {'services':['Paediatrician']}), [])

    def test_invite_one_use_and_stop(self):
        r = self.post('invites', {'alias':'Ana', 'filters':{'locations':['LJ']}, 'mode':'daily'})
        self.assertEqual(r.status_code,200)
        token = r.json['url'].split('=')[-1]
        update={'message':{'chat':{'id':123,'type':'private'},'text':'/start '+token,'from':{'username':'ana'}}}
        with patch.object(a,'send') as sender:
            a.handle_update(update)
            a.handle_update(update)
            self.assertEqual(sender.call_count,1)
        u=self.client.get('/api/state').json['users'][0]
        self.assertEqual(u['alias'],'Ana');self.assertEqual(u['mode'],'daily');self.assertEqual(u['filters']['locations'],['LJ'])
        with patch.object(a,'send'):
            a.handle_update({'message':{'chat':{'id':123,'type':'private'},'text':'/stop'}})
        self.assertEqual(self.client.get('/api/state').json['users'],[])

    def test_delivery_baselines_and_failures(self):
        for uid, loc in [('1','LJ'),('2','KR')]:
            self.assertEqual(self.post('users',{'chat_id':uid,'alias':uid,'filters':{'locations':[loc]}}).status_code,200)
        data={'doctors':self.rows,'dates':{'gp':'09.11.2026'}}
        with patch.object(a,'download_data',return_value=data),patch.object(a,'send') as sender:
            self.assertTrue(a.check());sender.assert_not_called()  # initial baseline
            self.assertTrue(a.check());sender.assert_not_called()  # unchanged
            extra=dict(self.rows[0],id='c',name='New GP')
            data['doctors']=self.rows+[extra]
            self.assertTrue(a.check());self.assertEqual(sender.call_args.args[0],'1');self.assertEqual(sender.call_count,1)
            data['doctors']=self.rows
            sender.side_effect=RuntimeError('Telegram rejected request: 403')
            self.assertTrue(a.check())
            with a.db() as c:
                baseline=json.loads(c.execute("SELECT baseline FROM users WHERE chat_id='1'").fetchone()[0])
            self.assertIn('c',baseline)  # retry delivery without losing the change
            sender.side_effect=None
            a.check();self.assertIn('Odstranjeni',sender.call_args.args[1])

    def test_validation_and_secret_not_returned(self):
        self.assertEqual(self.post('users',{'chat_id':'bad'}).status_code,400)
        self.assertEqual(self.post('users',{'chat_id':'1','filters':{'locations':'LJ'}}).status_code,400)
        a.put('bot_token','supersecret')
        self.assertNotIn('supersecret',self.client.get('/api/state').text)
        a.put('bot_token','')

    def test_refresh_does_not_consume_daily_schedule(self):
        self.post('users',{'chat_id':'1','mode':'daily','filters':{'locations':['LJ']}})
        a.put('last_scheduled_day','yesterday')
        data={'doctors':self.rows,'dates':{'gp':'09.11.2026'}}
        with patch.object(a,'download_data',return_value=data),patch.object(a,'send') as sender:
            a.check(notify=False)
            self.assertEqual(a.setting('last_scheduled_day'),'yesterday')
            sender.assert_not_called()
            a.check();self.assertEqual(sender.call_count,1)
            a.check();self.assertEqual(sender.call_count,1)  # no duplicate daily summary

    def test_alias_edit_preserves_baseline_but_filters_reset_it(self):
        b={'chat_id':'1','alias':'Before','filters':{'locations':['LJ']}}
        self.post('users',b)
        with a.db() as c:
            c.execute("UPDATE users SET baseline='{}' WHERE chat_id='1'")
        b['alias']='After';self.post('users',b)
        with a.db() as c:
            self.assertEqual(c.execute("SELECT baseline FROM users WHERE chat_id='1'").fetchone()[0],'{}')
        b['filters']['locations']=['KR'];self.post('users',b)
        with a.db() as c:
            self.assertIsNone(c.execute("SELECT baseline FROM users WHERE chat_id='1'").fetchone()[0])

    def test_parser_header_and_date(self):
        w=Workbook();s=w.active;s.append(['Report']);s.append(['Date','09.11.2026']);s.append([])
        s.append(['Kraj','Priimek in ime zdravnika','Naziv ZZZS dejavnosti','Zdravnik še sprejema zavarovane osebe'])
        s.append(['LJ','Doctor','GP','DA']);b=io.BytesIO();w.save(b)
        result=a.parse_workbook(b.getvalue(),'gp')
        self.assertEqual(result['date'],'09.11.2026');self.assertEqual(len(result['doctors']),1)
        with self.assertRaises(BadZipFile):a.parse_workbook(io.BytesIO().getvalue(),'gp')

    def test_token_saved_pending_on_timeout_but_invalid_rejected(self):
        import requests
        token='1234567890:'+('A'*35)
        with patch.object(a.requests,'post',side_effect=requests.Timeout()):
            r=self.post('settings',{'bot_token':token})
        self.assertEqual(r.status_code,200);self.assertTrue(r.json['warning'])
        self.assertEqual(a.setting('bot_token'),token)
        with patch.object(a.requests,'post') as req:
            req.return_value.json.return_value={'ok':False,'error_code':401}
            r=self.post('settings',{'bot_token':'9876543210:'+('B'*35)})
        self.assertEqual(r.status_code,400);self.assertEqual(a.setting('bot_token'),token)
        a.put('bot_token','')


if __name__=='__main__':
    unittest.main()
