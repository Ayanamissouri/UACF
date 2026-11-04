"""Main-host acceptance checks; fixtures are not native interception receipts."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from uacf.action_classifier import classify
from uacf.action_guard import check,configure,record
from uacf.consistency import tool_gate,fingerprint
from uacf.state import State,init,object_new,request
from uacf.fabric import vector
from uacf.util import Fault

class ActionBoundary(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.task=dict(object_id='fixture',revision=1,payload=dict(action_contract={'mode':'answer'},output_contract={'project_root':str(self.root)}))
 def tearDown(self):self.tmp.cleanup()
 def args(self,name,inp):return dict(tool_name=name,tool_input=inp,cwd=str(self.root))
 def test_cmd_and_command_and_opaque_code(self):
  for field in ['cmd','command']:
   self.assertEqual(classify('exec_command',{field:'Get-Content a.py'}),'read')
   self.assertEqual(classify('exec_command',{field:'Set-Content a.py 0.8'}),'write')
  for cmd in ['Get-Content x; Set-Content y z','git diff --output=x','rg --pre=foo x','rg --hostname-bin=foo x','python -c "write()"','Get-Content $(write)']:
   self.assertEqual(classify('exec_command',{'cmd':cmd}),'unknown',cmd)
  self.assertEqual(classify('mcp__untrusted__get',{}),'unknown')
  self.assertEqual(classify('exec_command',{'cmd':'Get-Content x','command':'Set-Content x y'}),'unknown')
 def test_readonly_modes_allow_reads_and_reject_writes_and_opaque_tools(self):
  for mode in ['answer','review','monitor']:
   self.task['payload']['action_contract']['mode']=mode
   self.assertEqual(check(self.task,self.args('exec_command',{'cmd':'Get-Content a.py'})),'read')
   for name,inp in [('exec_command',{'cmd':'Set-Content a.py 0.8'}),('functions.exec',{'code':'unknown()'}),('apply_patch','*** Delete File: a.py')]:
    with self.assertRaises(Fault) as e:check(self.task,self.args(name,inp))
    self.assertEqual(e.exception.code,'ACTION_MODE')
 def test_shell_cannot_skip_source_review_even_without_new_policy(self):
  self.task['payload']={'consistency_required':True}
  with self.assertRaises(Fault) as e:tool_gate(None,self.task,self.args('exec_command',{'cmd':'Set-Content a.py 0.8'}))
  self.assertEqual(e.exception.code,'CONSISTENCY_STALE')
  tool_gate(None,self.task,self.args('exec_command',{'cmd':'Get-Content a.py'}))
 def test_new_tasks_require_action_authority_before_mutation(self):
  self.task['payload']={'consistency_required':True,'action_contract_required':True}
  with self.assertRaises(Fault) as e:tool_gate(None,self.task,self.args('Write',{'path':'a.py'}))
  self.assertEqual(e.exception.code,'ACTION_CONTRACT_REQUIRED')
 def test_change_file_boundary_and_move_destination(self):
  self.task['payload']['action_contract']={'mode':'change','allowed_paths':['a.py','sub/**']}
  for p in ['a.py','sub/b.py','sub/../a.py']:
   self.assertEqual(check(self.task,self.args('Write',{'path':p})),'write')
  for p in ['b.py','../a.py','submarine/b.py']:
   with self.assertRaises(Fault) as e:check(self.task,self.args('Write',{'file_path':p}))
   self.assertEqual(e.exception.code,'ACTION_PATH')
  with self.assertRaises(Fault) as e:check(self.task,self.args('apply_patch','*** Begin Patch\n*** Update File: a.py\n*** Move to: forbidden.py\n*** End Patch'))
  self.assertEqual(e.exception.code,'ACTION_PATH')
  with self.assertRaises(Fault) as e:check(self.task,self.args('exec_command',{'cmd':'Set-Content a.py z'}))
  self.assertEqual(e.exception.code,'ACTION_PATH_UNPROVEN')
 def test_existing_integrity_hashes_allowed_until_explicit_deny(self):
  self.task['payload']['action_contract']={'mode':'change'}
  self.assertEqual(check(self.task,self.args('exec_command',{'cmd':'Get-FileHash a.py'})),'unknown')
  self.task['payload']['action_contract']['hashing']='deny'
  with self.assertRaises(Fault) as e:check(self.task,self.args('exec_command',{'cmd':'Get-FileHash a.py'}))
  self.assertEqual(e.exception.code,'ACTION_HASH')
 def test_authority_change_invalidates_semantic_review(self):
  old=fingerprint(self.task);self.task['payload']['action_contract']['mode']='change'
  self.assertNotEqual(fingerprint(self.task),old)
 def test_repeat_stop_keeps_read_recovery_available(self):
  self.task['payload'].update(action_contract={'mode':'change'},retry_guard={'blocked':True})
  self.assertEqual(check(self.task,self.args('read_file',{})),'read')
  with self.assertRaises(Fault) as e:check(self.task,self.args('Write',{'path':'a.py'}))
  self.assertEqual(e.exception.code,'REREAD_REQUIRED')

class CanonicalActionAuthority(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  self.source=self.put('Message',dict(text='只回答依据，不改代码。',source_kind='direct_user',current=True))
  self.task=self.put('TaskContract',dict(goal='answer basis',required_properties=[],output_contract={'project_root':str(self.root)},consistency={'contract':{'sources':[vector(self.source)]}}))
 def tearDown(self):self.tmp.cleanup()
 def put(self,kind,p):return self.s.put(request(object_new(kind,p,visibility='shared')),'owner')['object']
 def args(self):return dict(task_id=self.task['object_id'],task_revision=self.task['revision'],source_ref=vector(self.source),source_quote='只回答依据',interpretation_basis='Current explicit read-only request',contract={'mode':'answer'})
 def test_only_current_owner_source_and_revision_configure_authority(self):
  with self.assertRaises(Fault):configure(self.s,'codex',self.args())
  args=self.args();args['source_quote']='invented'
  with self.assertRaises(Fault):configure(self.s,'owner',args)
  args=self.args();args['task_revision']+=1
  with self.assertRaises(Fault):configure(self.s,'owner',args)
  out=configure(self.s,'owner',self.args());self.assertTrue(out['review_invalidated'])
  self.assertEqual(out['contract']['mode'],'answer')
 def test_admission_defers_optional_archive_work_but_preserves_requirements(self):
  task=self.task;task['payload'].update(unified_asset_search_authorized=True,constraints=['keep this mandatory'])
  self.s.put(request(task,task['revision']),'owner')
  with patch('uacf.unified_assets.inventory',side_effect=AssertionError('optional I/O on admission')):
   c=self.s.context('owner',task['object_id'],include_optional_recall=False)
  self.assertEqual(c['status'],'ready');self.assertEqual(c['capsule']['mandatory_constraints'],['keep this mandatory'])
  self.assertIn('optional_recall_deferred',c['capsule'])
 def test_decision_counts_do_not_claim_execution(self):
  args={'tool_name':'exec_command'};ref=vector(self.task)
  record(self.s,args,dict(task_ref=ref,allowed=True));record(self.s,args,dict(task_ref=ref,allowed=False,code='ACTION_MODE'))
  p=json.loads((self.s.data/'host-work/admissions'/(self.task['object_id']+'.json')).read_text('utf8'))
  self.assertEqual((p['checked'],p['allowed'],p['denied']),(2,1,1));self.assertEqual(p['host_effect'],'unobserved')

if __name__=='__main__':unittest.main()
