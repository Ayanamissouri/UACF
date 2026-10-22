import json,tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.util import Fault,uid,file_hash
from uacf.capabilities import record,status
from uacf.command_ledger import preparation,delivery,capsule
from uacf.task_views import brief,refresh
from uacf.storage_layout import configure
from uacf.candidate_guidance import dedupe,guidance
from uacf.project_workflow import dispatch as workflow

class UpgradeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);init(self.root);self.s=State(self.root)
 def tearDown(self):self.temp.cleanup()
 def put(self,kind,payload):return self.s.put(request(object_new(kind,payload,visibility='shared')),'owner')['object']
 def identity(self,**patch):return dict(machine='fixture-machine',host='pi',host_version='fixture-v1',profile='fixture-profile',capability='task-prepare',source_identity='a'*64,**patch)
 def evidence(self,identity=None,stage='loaded',scope='fixture SDK preparation only'):
  identity=identity or self.identity();return self.put('Evidence',{'observation':{'capability_proofs':[dict(identity,stages=[stage],native_session_id='session-a',scope=scope)]}})
 def cap(self,e,**patch):return dict(self.identity(),expected_registry_ref=None,stage='loaded',scope='fixture SDK preparation only',evidence_ref={'object_id':e['object_id'],'revision':e['revision']},native_session_id='session-a',**patch)
 def test_capability_proof_does_not_inherit_installed_or_verified(self):
  record(self.s,'owner',self.cap(self.evidence()));item=status(self.s,'owner',{})['items'][0]
  self.assertEqual(item['stages']['loaded'],'observed');self.assertEqual(item['stages']['installed'],'unobserved');self.assertEqual(item['stages']['verified'],'unobserved')
 def test_capability_unrelated_evidence_and_false_verification_rejected(self):
  unrelated=self.put('Evidence',{'observation':{'ok':True}})
  for args in [self.cap(unrelated),dict(self.cap(self.evidence()),stage='verified')]:
   with self.assertRaises(Fault) as e:record(self.s,'owner',args)
   self.assertEqual(e.exception.code,'CAPABILITY_EVIDENCE')
 def test_capability_cross_session_version_and_scope_rejected(self):
  e=self.evidence()
  for patch in [{'native_session_id':'session-b'},{'host_version':'new-version'},{'source_identity':'b'*64},{'scope':'all tools sandboxed'}]:
   with self.assertRaises(Fault):record(self.s,'owner',dict(self.cap(e),**patch))
 def test_capability_acl_cas_and_tamper(self):
  args=self.cap(self.evidence())
  with self.assertRaises(Fault):record(self.s,'pi',args)
  r=record(self.s,'owner',args)
  with self.assertRaises(Fault):record(self.s,'owner',args)
  path=self.s.data/'capability-registry.json';data=json.loads(path.read_text());data['config']['entries']={};path.write_text(json.dumps(data))
  with self.assertRaises(Fault):status(self.s,'owner',{})
 def test_changed_evidence_expires_observed_capability(self):
  e=self.evidence();record(self.s,'owner',self.cap(e));e['payload']['observation']['changed']=True;self.s.put(request(e,1),'owner')
  self.assertEqual(status(self.s,'owner',{})['items'][0]['stages']['loaded'],'stale')
 def test_lost_projection_recovers_from_canonical_without_resetting_records(self):
  r=record(self.s,'owner',self.cap(self.evidence()));path=self.s.data/'capability-registry.json';path.rename(path.with_suffix('.preserved'))
  restored=status(self.s,'owner',{});self.assertEqual(restored['registry_ref'],r['registry_ref']);self.assertEqual(restored['items'][0]['stages']['loaded'],'observed');self.assertFalse(path.exists())
 def test_verified_requires_pass_and_exact_underlying_proof(self):
  t=self.put('TaskContract',{'goal':'fixture','required_properties':[]});e=self.evidence(stage='verified')
  v=object_new('Validation',dict(task_id=t['object_id'],task_revision=1,property='fixture',result='pass',environment_hash='a'*64,method='fixture only',evidence_id=e['object_id']),visibility='shared')
  v=self.s.put(request(v),'system',internal=True)['object']
  r=record(self.s,'owner',dict(self.cap(v),stage='verified'));self.assertTrue(r['ok'])
  self.assertEqual(status(self.s,'owner',{})['items'][0]['stages']['verified'],'observed')
 def test_required_contract_empty_ledger_and_old_source_cannot_pass(self):
  t={'payload':{'command_contract':{'required':True,'source_ref':{'object_id':'new','revision':1}},'command_ledger':[]}}
  with self.assertRaises(Fault):preparation(t)
  t['payload']['command_ledger']=[dict(key='old',actionable=True,state='satisfied',source_ref={'object_id':'old','revision':1})]
  with self.assertRaises(Fault) as e:preparation(t)
  self.assertEqual(e.exception.code,'COMMAND_SOURCE_REQUIRED')
 def test_legacy_tasks_not_rewritten_and_explicit_cancelled_rows_not_blocking(self):
  delivery({'payload':{'command_ledger':[dict(key='cancelled',actionable=True,state='cancelled')]}})
  preparation({'payload':{}})
 def test_completed_ledger_preserved_without_duplicate_projection(self):
  row=dict(key='work',text='fixture requirement',kind='instruction',state='satisfied',actionable=True,source_ref={'object_id':'fixture','revision':1},interpretation_basis='fixture only')
  task={'payload':{'command_contract':{'required':True},'command_ledger':[row,dict(row,key='open',state='pending')]}}
  self.assertEqual([x['key'] for x in capsule(task)],['open']);self.assertEqual(len(task['payload']['command_ledger']),2)
 def test_delivery_rechecks_changed_evidence(self):
  e=self.put('Evidence',{'observation':{'result':'fixture'}});ref={'object_id':e['object_id'],'revision':1}
  t={'payload':{'command_ledger':[dict(key='work',actionable=True,state='satisfied',evidence_refs=[ref])]}}
  delivery(t,self.s);e['payload']['observation']['result']='changed';self.s.put(request(e,1),'owner')
  with self.assertRaises(Fault):delivery(t,self.s)
 def configured_task(self):
  configure(self.s,'owner',dict(authorization='fixture output root',expected_layout_ref=None,projects={'fixture':{'root':str(self.root)}},bundles={}))
  return self.put('TaskContract',dict(goal='fixture recovery',required_properties=[],command_contract={'required':True},output_contract={'project_key':'fixture','project_root':str(self.root)}))
 def test_task_view_is_canonical_derived_cas_and_archive_safe(self):
  t=self.configured_task();args=dict(task_id=t['object_id'],task_revision=1,expected_file_hash=None)
  self.assertFalse(brief(self.s,'owner',args)['brief']['requirements_ready']);result=refresh(self.s,'owner',args)
  p=Path(result['path']);self.assertTrue(p.is_relative_to(self.root/'.uacf/work'/t['object_id']));self.assertEqual(self.s.get(t['object_id'],'owner')['revision'],1)
  p.write_text('user work')
  with self.assertRaises(Fault):refresh(self.s,'owner',args)
  self.assertEqual(p.read_text(),'user work')
 def test_task_view_stale_task_wrong_actor_and_restore_refused(self):
  t=self.configured_task();args=dict(task_id=t['object_id'],task_revision=2)
  with self.assertRaises(Fault):brief(self.s,'owner',args)
  with self.assertRaises(Fault):refresh(self.s,'pi',dict(args,task_revision=1))
  config=self.s.config;config['restore_mapping']={"fixture":"isolated"};(self.s.data/'config.json').write_text(json.dumps(config))
  with self.assertRaises(Fault):refresh(self.s,'owner',dict(args,task_revision=1))
 def test_exact_optional_dedup_keeps_distinct_sources_and_corrections(self):
  row={'id':'a','candidate':{'correction':'x','applicable':'a'},'score':1}
  rows=[row,dict(row,score=2),dict(row,id='b'),dict(row,candidate={'correction':'new','applicable':'a'})]
  self.assertEqual(len(dedupe(rows)),3);self.assertEqual(len(rows),4)
 def test_guidance_preserves_conditions_and_never_mutates_sources(self):
  row=dict(candidate=dict(correction='check source',applicable='fixture only',excluded='newer correction'),case_ref={'object_id':'a','revision':1},card_ref={'object_id':'b','revision':1},attempt_ref={'object_id':'c','revision':1})
  before=json.dumps(row,sort_keys=True);r=guidance([row,row]);self.assertEqual(len(r['items']),1);self.assertEqual(r['items'][0]['status'],'unaccepted_candidate');self.assertEqual(r['items'][0]['excluded'],'newer correction');self.assertEqual(json.dumps(row,sort_keys=True),before)
  self.assertEqual(guidance([row],max_bytes=1)['items'],[])
 def test_implementation_rejects_empty_requirements_before_side_effects(self):
  t=self.put('TaskContract',{'goal':'fixture','required_properties':[],'command_contract':{'required':True}})
  r=workflow(self.s,'owner','workflow_project_configure',dict(task_id=t['object_id'],task_revision=1,stages=[dict(id='impl',role='implement',label='implement',route='current_host',depends_on=[])]),uid())
  with self.assertRaises(Fault) as e:workflow(self.s,'owner','workflow_project_record',dict(task_id=t['object_id'],task_revision=r['task_ref']['revision'],stage_id='impl',state='started'),uid())
  self.assertEqual(e.exception.code,'COMMAND_CONTRACT_REQUIRED');self.assertEqual(r['plan']['events'],[])

if __name__=='__main__':unittest.main()
