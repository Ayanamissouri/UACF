import copy,json,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.util import Fault,uid,now,sha,atomic,canonical
from uacf.trial_budget import reserve,settle
from uacf.fabric import vector

class TrialBudget(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  from uacf.fabric import migrate
  self.s.backup(self.root/'before');migrate(self.s,self.root/'before')
  def put(kind,p):return self.s.put(request(object_new(kind,p,visibility='shared')),'owner')['object']
  self.profiles={h:put('ProviderProfile',{'host':h,'provider':'deepseek','model':'deepseek-flash','endpoint_kind':'official_deepseek','capabilities':{'generation':'callable'},'pricing':{'currency':'CNY','verified_at':now(),'worst_input_micro_per_token':2,'worst_output_micro_per_token':8,'worst_cache_micro_per_token':.04}}) for h in ['pi','dsh']}
  self.task=put('TaskContract',{'goal':'bounded paid fixture','required_properties':[],'allow_provider':True,'execution_state':'running','budget_account':'fixture','trial_budget':{'authorized':True,'authorization_source':'explicit test fixture, no external call','trial_id':uid(),'limit_micro':30000,'account':'fixture','max_output_tokens':100,'max_requests':10,'profiles':{h:vector(v) for h,v in self.profiles.items()}}})
  atomic(self.s.data/'host-bindings.json',canonical({h:{h+'-native':self.task['object_id']} for h in ['pi','dsh']}))
  self.preflights={h:put('Evidence',{'observation':{'method':'actual_owner_provider_inspection','task_id':self.task['object_id'],'task_revision':1,'profile':vector(p),'checked_at':now(),'provider':'deepseek','model':'deepseek-flash','pricing_hash':sha(p['payload']['pricing']),'capabilities_hash':sha(p['payload']['capabilities']),'source_locator':'test fixture: no model called','provider_checked':True,'price_checked':True,'capability_checked':True}}) for h,p in self.profiles.items()}
  with self.s.db() as c:c.execute('INSERT INTO budget_accounts VALUES(?,?,?,?,?)',('fixture','CNY',1000000,0,1))
 def tearDown(self):self.tmp.cleanup()
 def args(self,h='pi'):
  return {'task_id':self.task['object_id'],'task_revision':1,'native_session_id':h+'-native','provider_profile_id':self.profiles[h]['object_id'],'provider_profile_revision':1,'preflight_evidence_id':self.preflights[h]['object_id'],'input_upper_bound_bytes':100,'max_output_tokens':100,'dispatch_hash':'0'*64}
 def test_parallel_hosts_cannot_overrun_aggregate(self):
  def run(h):
   try:return reserve(self.s,h,self.args(h),uid())['amount_micro']
   except Fault as e:return e.code
  with ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(run,['pi','dsh']))
  self.assertEqual(results.count('BUDGET_EXCEEDED'),1);self.assertIn(17384,results)
 def test_unknown_prevents_continuation_and_other_host_settlement(self):
  r=reserve(self.s,'pi',self.args(),uid());args={'reservation_id':r['reservation_id'],'usage':None,'outcome':'unknown'}
  with self.assertRaises(Fault):settle(self.s,'dsh',args)
  self.assertEqual(settle(self.s,'pi',args)['state'],'unknown')
  with self.assertRaises(Fault) as e:reserve(self.s,'dsh',self.args('dsh'),uid())
  self.assertEqual(e.exception.code,'OUTCOME_UNKNOWN')
 def test_settlement_keeps_trial_tag_and_deduplicates(self):
  r=reserve(self.s,'pi',self.args(),uid());args={'reservation_id':r['reservation_id'],'outcome':'completed','usage':{'inputTokens':100,'outputTokens':10,'cacheReadTokens':0,'cacheWriteTokens':0}}
  self.assertEqual(settle(self.s,'pi',args)['actual_micro'],280);self.assertTrue(settle(self.s,'pi',args)['duplicate'])
  with self.s.db() as c:
   self.assertEqual(c.execute("SELECT spent_micro FROM budget_accounts WHERE id='fixture'").fetchone()[0],280)
   self.assertEqual(json.loads(c.execute('SELECT receipt FROM budget_reservations WHERE id=?',(r['reservation_id'],)).fetchone()[0])['trial_id'],self.task['payload']['trial_budget']['trial_id'])
  self.assertTrue(reserve(self.s,'dsh',self.args('dsh'),uid())['ok'])
 def test_host_crash_reservation_prevents_next_dispatch(self):
  reserve(self.s,'pi',self.args(),uid())
  with self.assertRaises(Fault) as e:reserve(self.s,'pi',self.args(),uid())
  self.assertEqual(e.exception.code,'OUTCOME_UNKNOWN')
 def test_stop_stale_identity_and_output_limits(self):
  for changes in [{'task_revision':2},{'native_session_id':'wrong'},{'max_output_tokens':101},{'provider_profile_revision':2}]:
   with self.assertRaises(Fault):reserve(self.s,'pi',{**self.args(),**changes},uid())
  task=copy.deepcopy(self.task);task['payload']['allow_provider']=False;self.s.put(request(task,1),'owner')
  with self.assertRaises(Fault):reserve(self.s,'pi',{**self.args(),'task_revision':2},uid())
if __name__=='__main__':unittest.main()
