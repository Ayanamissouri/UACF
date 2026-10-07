import unittest,tempfile,json
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.learning import dispatch,enqueue_card,receive,folder
from uacf.util import Fault
from uacf.fabric import vector
class LearningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  dispatch(self.s,'owner','learning_configure',{'authorization':'test user scope'})
 def tearDown(self):self.tmp.cleanup()
 def put(self,kind,p):return self.s.put(request(object_new(kind,p)),'owner')['object']
 def source(self):
  e=self.put('Evidence',{'observation':{'fixture':True}})
  c=self.put('SemanticCard',dict(summary='fixture',evidence_map=[vector(e)],facets={},knowledge=[dict(text='conditional',refs=[])],semantic_contract='e7-semantic-1',input_vector=[vector(e)]))
  f=self.put('FailureCase',dict(properties=['e7_candidate_source_review'],lesson='fixture',source={'grading':'provisional'},case_details={'trigger':'reported completion without check'},input_vector=[vector(c)]))
  return c,f
 def test_program_repair_requires_settled_receipt(self):
  from uacf.util import atomic,canonical
  c,f=self.source();ident=enqueue_card(self.s,c,'work')
  dispatch(self.s,'owner','learning_mark',dict(job_id=ident,state='failed',error='fixture'))
  receipts=folder(self.s)/'receipts';receipts.mkdir(exist_ok=True)
  path=receipts/(ident+'.json');atomic(path,canonical(dict(state='unknown')))
  result=dispatch(self.s,'owner','learning_reconcile',{})
  self.assertEqual(result['blocked'],[ident]);self.assertEqual(len(self.s.list('owner','LearningAttempt')),0)
  atomic(path,canonical(dict(state='settled',raw={})))
  result=dispatch(self.s,'owner','learning_reconcile',{})
  self.assertEqual(result['provider_calls'],0);self.assertEqual(result['repaired'][0]['pending'],1)
  attempt=self.s.list('owner','LearningAttempt')[0]
  self.assertFalse(attempt['payload']['assessment']['semantic_acceptance'])
  self.assertEqual(self.s.get(f['object_id'],'owner')['revision'],1)
 def test_final_registered_verifier_writes_private_evidence_without_acl_expansion(self):
  dispatch(self.s,'owner','learning_register_guards',{})
  result=dispatch(self.s,'owner','learning_verify',{'expected':900})
  self.assertEqual(result['result'],'fail')
  self.assertNotIn('validations',result) # a count alone cannot freeze a Task contract
  with self.assertRaises(Fault):self.s.get(result['evidence_ref']['object_id'],'reader')
 def test_bulk_snapshot_preserves_current_source_coverage(self):
  from uacf.learning import candidate_input,comparison_snapshot
  c,f=self.source();ident=enqueue_card(self.s,c,'work');j=json.loads((folder(self.s)/'jobs'/(ident+'.json')).read_text())
  self.assertEqual(candidate_input(self.s,j),candidate_input(self.s,j,comparison_snapshot(self.s)))
 def test_host_projection_needs_owner_contract_and_exact_mapping(self):
  from uacf.learning import recall
  from uacf.util import atomic,canonical
  c,f=self.source();ident=enqueue_card(self.s,c,'work');j=json.loads((folder(self.s)/'jobs'/(ident+'.json')).read_text())
  receive(self.s,j,dict(issues=[dict(case_id=f['object_id'],mechanism='requirements',relation='unresolved',basis='fixture')],knowledge=[dict(index=0,topics=['verification'])]))
  task=object_new('TaskContract',dict(goal='verification',required_properties=[]),visibility='shared');task=self.s.put(request(task),'owner')['object']
  atomic(self.s.data/'host-bindings.json',canonical({'dsh':{'real-fixture-session':task['object_id']}}))
  self.assertEqual(recall(self.s,'dsh',dict(task_id=task['object_id']))['candidates'],[])
  dispatch(self.s,'owner','learning_enable_use',{'hosts':['dsh'],'authorization':'explicit fixture owner authority'})
  self.assertEqual(len(recall(self.s,'dsh',dict(task_id=task['object_id']))['candidates']),1)
  self.assertEqual(recall(self.s,'reader',dict(task_id=task['object_id']))['candidates'],[])
  with self.assertRaises(Fault):self.s.get(c['object_id'],'dsh')
  atomic(self.s.data/'host-bindings.json',canonical({'dsh':{}}))
  self.assertEqual(recall(self.s,'dsh',dict(task_id=task['object_id']))['candidates'],[])
 def test_real_old_candidate_replay_uses_same_protocol(self):
  c,f=self.source();f['payload']['case_details']={k:'existing explicit condition' for k in ['trigger','actual','expected','correction','applicable','excluded']};f['payload']['case_details']['category']='ai_execution';self.s.put(request(f,1),'owner')
  result=dispatch(self.s,'owner','learning_probe',{})
  self.assertEqual(result['result'],'pass');self.assertEqual(result['model_calls'],0);self.assertTrue(result['production_queue_unchanged'])
 def test_duplicate_source_and_no_automatic_promotion(self):
  c,f=self.source();a=enqueue_card(self.s,c,'work');b=enqueue_card(self.s,c,'history');self.assertEqual(a,b)
  j=json.loads((folder(self.s)/'jobs'/(a+'.json')).read_text());receive(self.s,j,dict(issues=[dict(case_id=f['object_id'],mechanism='unverified_delivery',relation='related_candidate',basis='fixture source')],knowledge=[dict(index=0,topics=['testing'])]))
  self.assertEqual(len(self.s.list('owner','LearningAttempt')),1);self.assertEqual(len(self.s.list('owner','FailurePattern')),1)
  self.assertEqual(len(self.s.list('owner','Validation')),0);self.assertEqual(self.s.get(f['object_id'],'owner')['revision'],1)
 def test_classifier_uses_actual_receipt_not_policy_or_historical_model(self):
  from uacf.learning import candidate_input
  from uacf.util import atomic,canonical
  c,f=self.source();ident=enqueue_card(self.s,c,'work');job=json.loads((folder(self.s)/'jobs'/(ident+'.json')).read_text())
  self.assertTrue(candidate_input(self.s,job)['ai_origin']['classifier'].startswith('unknown'))
  p=folder(self.s)/'receipts';p.mkdir(exist_ok=True)
  atomic(p/(ident+'.json'),canonical(dict(state='host_completed',actual_model='current_host')))
  self.assertEqual(candidate_input(self.s,job)['ai_origin']['classifier'],'current_host')
  atomic(p/(ident+'.json'),canonical(dict(state='settled',raw={'model':'provider-model-observed'})))
  self.assertEqual(candidate_input(self.s,job)['ai_origin']['classifier'],'provider-model-observed')
 def test_omissions_duplicate_indexes_and_unknown_rule_rejected(self):
  c,f=self.source();i=enqueue_card(self.s,c,'work');j=json.loads((folder(self.s)/'jobs'/(i+'.json')).read_text())
  for result in [dict(issues=[],knowledge=[]),dict(issues=[dict(case_id=f['object_id'],mechanism='execute_generated_python',relation='related_candidate',basis='x')],knowledge=[dict(index=0,topics=['x'])])]:
   with self.assertRaises(Fault):receive(self.s,j,result)
  self.assertFalse(self.s.list('owner','LearningAttempt'))
 def test_old_card_revision_and_nonowner_rejected(self):
  c,f=self.source();i=enqueue_card(self.s,c,'work');c['payload']['summary']='correction';self.s.put(request(c,1),'owner')
  with self.assertRaises(Fault):dispatch(self.s,'owner','learning_next',{})
  with self.assertRaises(Fault):dispatch(self.s,'reader','learning_configure',{'authorization':'x'})
 def test_unknown_dispatch_is_not_selected_again(self):
  c,f=self.source();i=enqueue_card(self.s,c,'work');dispatch(self.s,'owner','learning_mark',dict(job_id=i,state='dispatched',reservation_id='fixture'))
  self.assertIsNone(dispatch(self.s,'owner','learning_next',{})['job'])
  with self.assertRaises(Fault):dispatch(self.s,'owner','learning_mark',dict(job_id=i,state='dispatched',reservation_id='retry'))
 def test_registered_guards_and_acl_safe_recall(self):
  from uacf.learning import recall
  r=dispatch(self.s,'owner','learning_register_guards',{});self.assertTrue(all(r['checks'].values()))
  c,f=self.source();i=enqueue_card(self.s,c,'work');j=json.loads((folder(self.s)/'jobs'/(i+'.json')).read_text())
  receive(self.s,j,dict(issues=[dict(case_id=f['object_id'],mechanism='unverified_delivery',relation='unresolved',basis='conditions unknown')],knowledge=[dict(index=0,topics=['testing'])]))
  tid=dispatch(self.s,'owner','learning_status',{})['policy']['task_ref']['object_id']
  self.assertEqual(len(recall(self.s,'owner',dict(task_id=tid,query='testing'))['candidates']),1)
  with self.assertRaises(Fault):recall(self.s,'reader',dict(task_id=tid,query='testing'))
  c['payload']['summary']='changed';self.s.put(request(c,1),'owner')
  self.assertEqual(recall(self.s,'owner',dict(task_id=tid,query='testing'))['candidates'],[])
 def test_registered_family_link_and_partial_commit_recovery(self):
  from uacf.learning import candidate_input,save_once
  from uacf.util import canonical,sha
  dispatch(self.s,'owner','learning_register_guards',{})
  c,f=self.source();i=enqueue_card(self.s,c,'work');j=json.loads((folder(self.s)/'jobs'/(i+'.json')).read_text())
  result=dict(issues=[dict(case_id=f['object_id'],mechanism='unverified_delivery',relation='unresolved',basis='source lacks verification')],knowledge=[dict(index=0,topics=['testing'])])
  receive(self.s,j,result)
  dispatch(self.s,'owner','learning_register_guards',{})
  c,f=self.source();i=enqueue_card(self.s,c,'work');j=json.loads((folder(self.s)/'jobs'/(i+'.json')).read_text())
  result=dict(issues=[dict(case_id=f['object_id'],mechanism='unverified_delivery',relation='unresolved',basis='second source lacks verification')],knowledge=[dict(index=0,topics=['testing'])])
  inp=candidate_input(self.s,j);body=canonical(dict(input=inp,comparison=result,scope='model-proposed relation; no semantic adoption',policy_ref=j['policy_ref'])).encode()
  save_once(self.s,'Artifact',dict(locator='learning-result:'+i,sha256=sha(body),name='Work candidate comparison and retrieval index',media_type='application/json',candidate=True,input_vector=[j['card_ref'],j['policy_ref']]),['result',i],body)
  (folder(self.s)/'mechanism-examples.json').write_text('{}')
  receive(self.s,j,result)
  self.assertEqual(j['state'],'compared')
  self.assertEqual(len(self.s.list('owner','LearningAttempt')),2)
 def test_batch_input_and_manual_unknown_result_gate(self):
  for _ in range(6):c,f=self.source();enqueue_card(self.s,c,'work')
  batch=dispatch(self.s,'owner','learning_batch_input',{'limit':5})
  self.assertEqual(len(batch['jobs']),5);self.assertEqual(len({x['job']['id'] for x in batch['jobs']}),5)
  j=batch['jobs'][0]['job'];dispatch(self.s,'owner','learning_mark',dict(job_id=j['id'],state='failed',error='unknown'))
  with self.assertRaises(Fault):dispatch(self.s,'owner','learning_mark',dict(job_id=j['id'],state='received',result={}))
 def test_learning_receipts_restore_paused_and_verified(self):
  from uacf.state import restore,verify_backup
  from uacf.util import canonical
  (folder(self.s)/'receipts').mkdir();(folder(self.s)/'receipts/fixture.json').write_text(canonical(dict(state='settled',cost=0)))
  backup=self.root/'snapshot';self.s.backup(backup);restored=self.root/'restored';self.assertTrue(restore(backup,restored)['ok'])
  self.assertTrue(json.loads((restored/'data/learning/control.json').read_text())['pause'])
  (backup/'learning/receipts/fixture.json').write_text('{}')
  with self.assertRaises(Fault):verify_backup(backup)
 def test_frontend_registered_mutation_envelopes(self):
  # Real regression: frontend actions were rejected before their operation envelope existed.
  from uacf.service import MUTATIONS
  import re
  html=(Path(__file__).resolve().parents[1]/'apps/control-surface/index.html').read_text(encoding='utf8')
  actions=set(re.findall(r"'([^']+)'",re.search(r'const mutations=\[(.*?)\]',html).group(1)))
  for action in ['learning_configure','learning_enqueue','learning_mark','learning_start','learning_register_guards','learning_verify','learning_metadata']:self.assertIn(action,actions);self.assertIn(action,MUTATIONS)
 def test_provider_outage_returns_same_queue_to_current_host(self):
  c,f=self.source();i=enqueue_card(self.s,c,'work');r=dispatch(self.s,'owner','learning_fallback',dict(reason='fixture outage before dispatch'));self.assertEqual(r['route']['route'],'current_host')
  self.assertTrue(dispatch(self.s,'owner','learning_start',dict(count=100))['current_host_pending']);self.assertEqual(dispatch(self.s,'owner','learning_next',{})['job']['id'],i)
  result=dict(issues=[dict(case_id=f['object_id'],mechanism='unverified_delivery',relation='unresolved',basis='source lacks verification')],knowledge=[dict(index=0,topics=['testing'])])
  dispatch(self.s,'owner','learning_mark',dict(job_id=i,state='received',result=result,actual_model='current_desktop_gpt',native_locator='fixture public host output'))
  self.assertEqual(json.loads((folder(self.s)/'receipts'/(i+'.json')).read_text())['provider_calls'],0)
 def test_normal_host_round_is_private_scoped_and_source_checked(self):
  from uacf.fabric import migrate
  from uacf.batch3 import migrate3
  from uacf.util import uid,now
  from uacf.learning import after_work
  self.s.backup(self.root/'b1');migrate(self.s,self.root/'b1');self.s.backup(self.root/'b2');migrate3(self.s,self.root/'b2')
  task=object_new('TaskContract',dict(goal='fixture public work',required_properties=['source'],learning_capture_policy={'mode':'work_end'}),visibility='shared');task=self.s.put(request(task),'owner')['object']
  (self.s.data/'host-bindings.json').write_text(json.dumps(dict(codex={'public-fixture':task['object_id']})))
  event=dict(event_id=uid(),source_host='codex',host_epoch=uid(),source_seq=1,type='observation',occurred_at=now(),observed_at=now(),schema_version='1.0',visibility='private',payload=dict(kind='native_hook',native_session_id='public-fixture',native_type='Stop',last_assistant_message='Public completed output.'))
  self.s.host_event(event,'codex');self.s.host_event(event,'codex')
  nxt=dispatch(self.s,'codex','learning_host_next',dict(task_id=task['object_id']));self.assertIsNotNone(nxt['job_id'])
  self.assertEqual(self.s.context('codex',task['object_id'])['capsule']['current_host_learning_pending'][0]['job_id'],nxt['job_id'])
  self.assertIsNone(dispatch(self.s,'dsh','learning_host_next',dict(task_id=task['object_id']))['job_id'])
  with self.assertRaises(Fault):dispatch(self.s,'codex','learning_host_submit',dict(task_id=task['object_id'],job_id=nxt['job_id'],result=dict(knowledge=[dict(text='bad',refs=[dict(quote='invented')])],issues=[])))
  dispatch(self.s,'codex','learning_host_submit',dict(task_id=task['object_id'],job_id=nxt['job_id'],result=dict(summary='public fixture',knowledge=[dict(text='output',refs=[dict(quote='Public completed output.')])],issues=[])))
  nxt=dispatch(self.s,'codex','learning_host_next',dict(task_id=task['object_id']));self.assertEqual(nxt['input']['knowledge'][0]['text'],'output')
