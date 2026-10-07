import json,tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.learning import dispatch
from uacf.learning_inspect import inspect
from uacf.learning_lifecycle import capture_gate,bind,checkpoint
from uacf.util import Fault,sha,atomic,canonical
class GeneralLearningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
 def tearDown(self):self.tmp.cleanup()
 def task(self):return self.s.put(request(object_new('TaskContract',dict(goal='ordinary task',required_properties=[],learning_capture_policy={'mode':'milestones'}),visibility='shared')),'owner')['object']
 def test_empty_store_and_default_host_need_no_old_account(self):
  from uacf.catalog import catalog
  from uacf.observatory import observe
  from uacf.workflow import dispatch as workflow
  self.assertEqual(catalog(self.s,'owner',{})['counts']['archive_conversations'],0)
  self.assertEqual(observe(self.s,'owner',{})['counts']['matching_conversations'],0)
  self.assertIsNone(workflow(self.s,'owner','workflow_status',{})['batch_directory'])
  with self.assertRaises(Fault):workflow(self.s,'owner','workflow_start',{})
  self.assertEqual(inspect(self.s,{})['overview']['sources'],0)
  p=dispatch(self.s,'owner','learning_configure',{'authorization':'ordinary work'})['policy']
  self.assertIsNone(p['config']['account']);self.assertFalse(self.s.get(p['task_ref']['object_id'],'owner')['payload']['allow_provider'])
  self.assertTrue(dispatch(self.s,'owner','learning_start',{'count':1001})['no_model_spawn'])
  v=dispatch(self.s,'owner','learning_verify',{'expected':0})
  self.assertTrue(v['checks']['source_count']);self.assertNotIn('validations',v)
 def test_current_empty_install_has_schema_without_old_budget(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);init(root,current_schema=True);state=State(root)
   with state.db() as c:
    self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],3)
    self.assertEqual(c.execute('select count(*) from archive_conversations').fetchone()[0],0)
    self.assertEqual(c.execute('select count(*) from budget_accounts').fetchone()[0],0)
   self.assertEqual(inspect(state,{})['overview']['sources'],0)
   from uacf.workflow import dispatch as workflow
   self.assertIsNone(workflow(state,'owner','workflow_status',{})['batch_directory'])
   dispatch(state,'owner','learning_configure',{'authorization':'synthetic ordinary current-host path'})
   self.assertTrue(dispatch(state,'owner','learning_start',{'count':1001})['no_model_spawn'])
   with self.assertRaises(Fault):init(root,current_schema=True)
 def test_important_signals_not_text_length_or_emotion(self):
  t=self.task();e={'payload':{'native_type':'Stop','last_assistant_message':'x'*50000}}
  self.assertEqual(capture_gate(t,e),'defer')
  e['payload']['learning_signal']='correction';self.assertEqual(capture_gate(t,e),'capture')
  t['payload']['learning_capture_policy']['mode']='lightweight';self.assertEqual(capture_gate(t,e),'defer')
  self.assertEqual(capture_gate({'payload':{}},{'payload':{'native_type':'Stop'}}),'defer')
 def test_mapping_cas_and_missing_real_event_fail(self):
  t=self.task();args=dict(host='codex',native_session_id='fixture-session',task_id=t['object_id'],task_revision=1,native_locator='fixture only',authorization='fixture',expected_binding_hash=sha({}))
  r=bind(self.s,'owner',args);self.assertFalse(r['automatic_callback_verified'])
  with self.assertRaises(Fault):bind(self.s,'owner',args)
  with self.assertRaises(Fault):checkpoint(self.s,'owner',dict(host='codex',native_session_id='fixture-session',task_id=t['object_id'],task_revision=1,signal='correction',native_event_id='absent'))
