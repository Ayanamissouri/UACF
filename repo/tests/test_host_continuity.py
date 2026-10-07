import json,tempfile,unittest
from pathlib import Path
from uacf.state import State,init
from uacf.fabric import migrate
from uacf.batch3 import migrate3,dispatch_batch3
from uacf.batch2 import reserve,settle,budget_get
from uacf.util import uid,now,Fault

class ContinuityContract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  self.s.backup(self.root/'b1');migrate(self.s,self.root/'b1');self.s.backup(self.root/'b2');migrate3(self.s,self.root/'b2')
 def tearDown(self):self.tmp.cleanup()
 def event(self):return {'event_id':uid(),'source_host':'dsh','host_epoch':uid(),'source_seq':1,'type':'observation','occurred_at':now(),'observed_at':now(),'schema_version':'1.0','visibility':'private','payload':{'kind':'native_organization','native_session_id':'native-1','native_title':'renamed','native_project_id':'client-project-2','semantic_affiliation_changed':False}}
 def test_native_directory_observation_never_creates_semantics(self):
  e=self.event();self.s.host_event(e,'dsh');self.assertTrue(self.s.host_event(e,'dsh')['duplicate'])
  self.assertEqual(self.s.list('owner','Affiliation'),[])
  e['payload']['native_title']='different'
  with self.assertRaises(Fault):self.s.host_event(e,'dsh')
 def test_cross_host_and_credential_capture_rejected(self):
  e=self.event()
  with self.assertRaises(Fault):self.s.host_event(e,'codex')
  e['payload']['text']=json.loads((self.root/'data/auth.json').read_text())['owner']
  with self.assertRaises(Fault):self.s.host_event(e,'dsh')
 def test_projection_is_private_and_keeps_native_directory(self):
  from uacf.host_continuity import observe
  self.s.host_event(self.event(),'dsh')
  result=observe(self.s,'owner',{'host':'dsh','native_session_id':'native-1'})
  self.assertEqual(result['native_directory']['native-1']['native_title'],'renamed')
  self.assertFalse(result['semantic_affiliation_modified'])
  self.assertEqual(self.s.list('owner','Affiliation'),[])
  self.assertEqual(observe(self.s,'dsh',{'host':'dsh','after_rowid':result['next_cursor']})['events'],[])
  for actor in ['codex','reader']:
   with self.assertRaises(Fault):observe(self.s,actor,{'host':'dsh'})
 def test_independent_20_total_unknown_stays_locked(self):
  args={'account':'aoe4-20261004','limit_micro':20000000,'currency':'CNY'}
  dispatch_batch3(self.s,'owner','budget_open',args,uid());dispatch_batch3(self.s,'owner','budget_open',args,uid())
  rid=uid();reserve(self.s,'owner',{'account':args['account'],'amount_micro':12000000},rid)
  settle(self.s,'owner',{'reservation_id':rid,'usage':'unknown'})
  b=budget_get(self.s,args['account']);self.assertEqual(b['locked_micro'],12000000)
  with self.assertRaises(Fault):reserve(self.s,'owner',{'account':args['account'],'amount_micro':9000000},uid())
  self.assertEqual(budget_get(self.s,'batch3')['limit_micro'],30000000)
 def test_unknown_account_or_increased_limit_rejected(self):
  for account,amount in [('aoe4-20261004',21000000),('aoe4-other',20000000)]:
   with self.assertRaises(Fault):dispatch_batch3(self.s,'owner','budget_open',{'account':account,'limit_micro':amount,'currency':'CNY'},uid())
