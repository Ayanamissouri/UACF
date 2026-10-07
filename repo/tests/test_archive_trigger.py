import tempfile,unittest
from pathlib import Path
from uacf.archive_trigger import decide,check,POLICY,maintain,status,previous_state
from uacf.state import State,init,object_new,request
from uacf.util import Fault

class TriggerTests(unittest.TestCase):
 def test_emotion_and_text_volume_do_not_trigger_extraction(self):
  self.assertEqual(decide({'dissatisfaction':True},{},100)['action'],'defer')
  with self.assertRaises(Fault):decide({'cue':'x'*1025},{},100)
 def test_daily_and_overdue_work_are_metadata_only(self):
  self.assertEqual(decide({'short_daily':True},{'last_work_at':1},2)['action'],'defer')
  self.assertEqual(decide({'short_daily':True},{'last_work_at':1},POLICY['idle_check_seconds']+2)['action'],'metadata_check')
 def test_explicit_request_and_critical_correction_do_not_wait(self):
  for f in [{'explicit_request':True},{'correction':True,'severity':'critical'}]:
   r=decide(f,{'last_capture_at':99},100)
   self.assertEqual(r['action'],'prepare_incremental');self.assertEqual(r['model_calls'],0);self.assertFalse(r['automatic_archive_completed'])
 def test_coalescing_and_cooldown(self):
  self.assertEqual(decide({'requirement_change':True},{'last_capture_at':99},100)['action'],'aggregate')
  self.assertEqual(decide({'progress':True},{'pending_signal_count':2},1000)['action'],'prepare_incremental')
 def test_overdue_metadata_not_suppressed_by_capture_cooldown(self):
  r=decide({}, {'last_capture_at':POLICY['idle_check_seconds']+1,'last_work_at':0},POLICY['idle_check_seconds']+2)
  self.assertEqual(r['action'],'metadata_check')
 def test_periodic_sweep_is_opt_in_and_does_not_claim_capture(self):
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));s=State(Path(d))
   opted=s.put(request(object_new('TaskContract',{'goal':'synthetic adaptive','required_properties':[],'learning_capture_policy':{'mode':'adaptive'}})),'owner')['object']
   plain=s.put(request(object_new('TaskContract',{'goal':'synthetic ordinary','required_properties':[]})),'owner')['object']
   maintain(s);first=status(s,'owner',{'task_id':opted['object_id']})['latest'];self.assertIsNotNone(first)
   self.assertEqual(first['decision']['model_calls'],0);self.assertFalse(first['decision']['automatic_archive_completed'])
   self.assertIsNone(status(s,'owner',{'task_id':plain['object_id']})['latest']);maintain(s)
   self.assertEqual(status(s,'owner',{'task_id':opted['object_id']})['latest'],first)
 def test_actual_source_timestamp_not_preparation_marks_capture(self):
  from uacf.util import sha
  from uacf.fabric import vector
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));s=State(Path(d));t=s.put(request(object_new('TaskContract',{'goal':'synthetic','required_properties':[]})),'owner')['object']
   self.assertNotIn('last_capture_at',previous_state(s,t,None))
   s.put(request(object_new('Artifact',{'locator':'native-learning:synthetic-contract-only','sha256':sha(b'{}'),'learning_task_ref':vector(t)}),blob=b'{}'),'owner')
   self.assertIn('last_capture_at',previous_state(s,t,None))
 def test_sweep_rotates_past_first64_tasks(self):
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));s=State(Path(d));ids=[]
   for i in range(70):ids.append(s.put(request(object_new('TaskContract',{'goal':'synthetic '+str(i),'required_properties':[],'learning_capture_policy':{'mode':'adaptive'}})),'owner')['object']['object_id'])
   maintain(s);s._archive_trigger_sweep=-60;maintain(s)
   self.assertTrue(all(status(s,'owner',{'task_id':ident})['latest'] is not None for ident in ids))
 def test_annotation_not_native_delivery_and_missing_event_fails(self):
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));s=State(Path(d));t=s.put(request(object_new('TaskContract',{'goal':'synthetic task','required_properties':[]})),'owner')['object']
   a={'task_id':t['object_id'],'task_revision':1,'features':{'explicit_request':True}}
   r=check(s,'owner',a);self.assertIn('partial',r['source_delivery']);self.assertTrue(check(s,'owner',a)['duplicate'])
   a['features']={'explicit_request':True,'observed_event_id':'does-not-exist'}
   with self.assertRaises(Fault):check(s,'owner',a)
