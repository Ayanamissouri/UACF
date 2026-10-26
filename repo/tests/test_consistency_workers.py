import copy,json,math,tempfile,time,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.fabric import vector
from uacf.util import Fault,sha
from uacf.consistency import validate,fingerprint,gate,dispatch
from uacf.coding_workers import decide,spec_check,audit_guard

class WorkerRouting(unittest.TestCase):
 def limits(self,remaining,minutes):return {'rateLimits':{'primary':{'windowDurationMins':300,'usedPercent':100-remaining,'resetsAt':1000+minutes*60}}}
 def route(self,p,m,setup=None):return decide(self.limits(p,m),setup or {'configured':True,'luna_usable':True},1000)['route']
 def test_owner_thresholds_and_equalities(self):
  for p,m,expected in [(38,180,'deepseek'),(80,60,'luna'),(40,40,'luna'),(39,20,'deepseek'),(40,41,'deepseek'),(100,0,'deepseek')]:
   with self.subTest(p=p,m=m):self.assertEqual(self.route(p,m),expected)
 def test_no_setup_is_main_with_reminder_broken_setup_is_ds(self):
  self.assertEqual(decide(None,{'configured':False})['route'],'main');self.assertTrue(decide(None,{'configured':False})['notice'])
  self.assertEqual(self.route(80,60,{'configured':True,'luna_usable':False}),'deepseek')
  self.assertEqual(decide(None,{})['route'],'deepseek')
 def test_unknown_nan_wrong_window_and_disallowed(self):
  for limits in [None,{},self.limits(float('nan'),20),self.limits(80,-1),{'rateLimits':{'primary':{'windowDurationMins':10080}}}]:self.assertEqual(decide(limits,{'configured':True,'luna_usable':True},1000)['route'],'deepseek')
  v=self.limits(80,60);v['ordinaryUsageAllowed']=False;self.assertEqual(decide(v,{'configured':True,'luna_usable':True},1000)['route'],'deepseek')
 def test_complete_worker_contract_required(self):
  self.assertRaises(Fault,spec_check,{'interfaces':'only signature'})
 def test_reviewed_ds_candidate_rows_and_missing_equality(self):
  rows=json.loads((Path(__file__).parent/'fixtures/coding_worker_routes.json').read_text('utf8'))
  for row in rows:
   with self.subTest(row=row):self.assertEqual(self.route(row['remaining_percent'],row['reset_minutes']),row['expected_route'])

class SemanticConsistency(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.state=State(self.root)
  self.msg=self.put('Message',{'text':'不要只用五档。比如八成九成。Why did you choose 80%?','source_kind':'direct_user','current':True})
  text=self.msg['payload']['text'];a=text.index('比如');b=text.index('Why')
  self.task=self.put('TaskContract',{'goal':'density','required_properties':[],'output_contract':{'project_root':str(self.root)},'command_contract':{'source_ref':vector(self.msg)},'command_ledger':[dict(key='density',text='Compare density',kind='instruction',actionable=True,state='in_progress',source_ref=vector(self.msg))]})
  def clause(i,start,end,role,commands):return dict(id=i,source_id=self.msg['object_id'],start=start,end=end,quote=text[start:end],role=role,commands=commands,relation='none',scope='density question',interpretation='Source-bound public interpretation')
  self.contract={'sources':[vector(self.msg)],'clauses':[clause('a',0,a,'prohibition',['density']),clause('b',a,b,'example',[]),clause('c',b,len(text),'question',[])],'decisions':[]}
 def tearDown(self):self.tmp.cleanup()
 def put(self,kind,p):return self.state.put(request(object_new(kind,p,visibility='shared')),'owner')['object']
 def prepared(self):
  c=dict(contract=self.contract,contract_hash=validate(self.state,self.task,self.contract),requirements_hash=fingerprint(self.task),author='main')
  self.task['payload'].update(consistency_required=True,consistency=c);return c
 def test_source_coverage_and_quoted_question_not_command(self):
  validate(self.state,self.task,self.contract)
  bad=copy.deepcopy(self.contract);bad['clauses'][1]['start']+=1;self.assertRaises(Fault,validate,self.state,self.task,bad)
  bad=copy.deepcopy(self.contract);bad['clauses'][2]['commands']=['density'];self.assertRaises(Fault,validate,self.state,self.task,bad)
 def test_examples_and_unresolved_numbers_cannot_execute(self):
  for status in ['example','unresolved']:
   bad=copy.deepcopy(self.contract);bad['clauses'][1]['numbers']=[dict(literal='八成',status=status,used_for_execution=True)]
   with self.assertRaises(Fault):validate(self.state,self.task,bad)
 def test_numeric_referent_unit_and_denominator_required(self):
  bad=copy.deepcopy(self.contract);bad['clauses'][1]['numbers']=[dict(literal='八成',status='model_choice',used_for_execution=True,object='first rung')]
  self.assertRaises(Fault,validate,self.state,self.task,bad)
 def test_self_review_missing_review_and_requirement_change_rejected(self):
  c=self.prepared();self.assertRaises(Fault,gate,self.task)
  c['review']=dict(contract_hash=c['contract_hash'],verdict='pass',reviewer='main');self.assertRaises(Fault,gate,self.task)
  c['review']['reviewer']='independent-reviewer';gate(self.task)
  self.task['payload']['goal']='changed';self.assertRaises(Fault,gate,self.task)
 def test_delivery_requires_all_current_result_hashes(self):
  c=self.prepared();c['review']=dict(contract_hash=c['contract_hash'],verdict='pass',reviewer='other')
  self.assertRaises(Fault,gate,self.task,None,'deliver')
  f=self.root/'code.py';f.write_text('x=1')
  from uacf.util import file_hash
  c['delivery']=dict(contract_hash=c['contract_hash'],verdict='pass',trace=[dict(command='density',path=str(f),sha256=file_hash(f),check='actual regression',result='pass')])
  gate(self.task,None,'deliver');f.write_text('x=2');self.assertRaises(Fault,gate,self.task,None,'deliver')
 def test_publication_preflight_does_not_claim_final_delivery(self):
  c=self.prepared();c['review']=dict(contract_hash=c['contract_hash'],verdict='pass',reviewer='other')
  f=self.root/'publish-ready.py';f.write_text('x=1')
  from uacf.util import file_hash
  c['publication']=dict(contract_hash=c['contract_hash'],verdict='pass',trace=[dict(command='density',path=str(f),sha256=file_hash(f),check='publication preflight',result='pass')])
  gate(self.task,None,'publish');self.assertRaises(Fault,gate,self.task,None,'deliver')
 def test_registered_review_requires_exact_observed_review(self):
  c=self.prepared();self.task=self.state.put(request(self.task,self.task['revision']),'owner')['object']
  unrelated=self.put('Evidence',{'observation':{'tests':'pass'}})
  review=dict(contract_hash=c['contract_hash'],reviewer='other',verdict='pass',findings=['Original source checked'],evidence_ref=vector(unrelated))
  with self.assertRaises(Fault):dispatch(self.state,'owner','consistency_review',dict(task_id=self.task['object_id'],task_revision=self.task['revision'],review=review))
 def test_attaching_review_preserves_native_revision_without_invalidating_it(self):
  c=self.prepared();self.task=self.state.put(request(self.task,self.task['revision']),'owner')['object']
  review=dict(contract_hash=c['contract_hash'],reviewer='independent-native-review',verdict='pass',findings=['Compared original source and all clauses'])
  ev=self.put('Evidence',{'observation':{'consistency_review':review},'input_vector':[vector(self.task)]})
  review['evidence_ref']=vector(ev)
  out=dispatch(self.state,'owner','consistency_review',dict(task_id=self.task['object_id'],task_revision=self.task['revision'],review=review))
  self.task=self.state.get(out['task_ref']['object_id'],'owner');gate(self.task,self.state)
  self.task['payload']['goal']='different requirement';self.assertRaises(Fault,gate,self.task,self.state)

class CodeOnlyDeployment(unittest.TestCase):
 def test_dependencies_cas_and_rollback_pointer(self):
  from unittest.mock import patch
  from uacf.deploy import activate_code_only
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'data').mkdir();runtime=root/'python.exe';runtime.write_text('fixture')
   old={'identity':'old','runtime':str(runtime),'repo':'old-path'};pointer=root/'data/deployment.json';pointer.write_text(json.dumps(old))
   manifest={'files':{'requirements.lock':'same','requirements.pinned.txt':'same','contracts/migrations/001.sql':'same'}}
   with patch('uacf.deploy.verify',return_value=manifest):
    self.assertRaises(Fault,activate_code_only,root,'new','wrong')
    out=activate_code_only(root,'new','old');self.assertEqual(json.loads(Path(out['rollback_receipt']).read_text())['previous_pointer'],old)
    self.assertFalse((root/'data/core.sqlite').exists());self.assertEqual(json.loads(pointer.read_text())['runtime'],str(runtime))

class WorkerDefaultEnrollment(unittest.TestCase):
 def test_missing_configuration_reminds_and_configured_tasks_get_independent_budgets(self):
  from uacf.coding_workers import configure,inherit,notice
  from uacf.batch2 import budget_get
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'root';init(root);state=State(root)
   from uacf.fabric import migrate
   backup=Path(d)/'before';state.backup(backup);migrate(state,backup)
   def put(k,p):return state.put(request(object_new(k,p,visibility='shared')),'owner')['object']
   source=put('Message',dict(text='默认脏活使用DS，主模型审计',source_kind='direct_user',current=True))
   task=put('TaskContract',dict(goal='new work',required_properties=[]));self.assertTrue(notice(state,task))
   profile=put('ProviderProfile',dict(host='dsh',provider='deepseek-official',model='deepseek-flash',capabilities={'generation':'callable'},pricing={'currency':'CNY'}))
   configure(state,'owner',dict(source_ref=vector(source),config=dict(configured=True,luna_usable=False,profile_ref=vector(profile),budget_limit_micro=100000,max_calls=4,max_output_tokens=1024)))
   first=inherit(state,task);second=inherit(state,put('TaskContract',dict(goal='another work',required_properties=[])))
   self.assertNotEqual(first['payload']['budget_account'],second['payload']['budget_account'])
   self.assertEqual(budget_get(state,first['payload']['budget_account'])['available_micro'],100000)
   self.assertEqual(inherit(state,first)['revision'],first['revision'])

if __name__=='__main__':unittest.main()
