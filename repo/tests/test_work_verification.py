import tempfile,unittest
from pathlib import Path
from uacf.state import State,init,request,object_new
from uacf.host_work import configure
from uacf.work_verification import dispatch,environment
from uacf.util import Fault,uid
class WorkVerificationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.sroot=Path(self.tmp.name);init(self.sroot);self.s=State(self.sroot)
  configure(self.s,'owner',{'authorization':'synthetic Owner policy fixture'},uid())
  self.t=self.s.put(request(object_new('TaskContract',{'goal':'synthetic frozen verification boundary','required_properties':['study_bundle_source_integrity'],'delivery_environment_hash':environment(self.s)['environment_hash']})),'owner')['object']
  self.a=dict(task_id=self.t['object_id'],task_revision=1,property='study_bundle_source_integrity')
 def tearDown(self):self.tmp.cleanup()
 def test_host_cannot_dispatch_verifier_or_freeze_environment(self):
  for action in ['work_environment','work_verify']:
   with self.assertRaises(Fault):dispatch(self.s,'codex',action,self.a)
 def test_unregistered_property_and_stale_task_rejected(self):
  for patch in [{'property':'scientific_truth'},{'task_revision':2}]:
   with self.assertRaises(Fault):dispatch(self.s,'owner','work_verify',dict(self.a,**patch))
 def test_changed_environment_cannot_receive_validation(self):
  self.t['payload']['delivery_environment_hash']='0'*64;self.s.put(request(self.t,1),'owner')
  with self.assertRaises(Fault) as e:dispatch(self.s,'owner','work_verify',dict(self.a,task_revision=2))
  self.assertEqual(e.exception.code,'ENVIRONMENT_CHANGED')
 def test_missing_study_contract_records_failed_validation_not_pass(self):
  r=dispatch(self.s,'owner','work_verify',self.a);self.assertEqual(r['result'],'fail');self.assertFalse(r['checks']['completed_without_error'])
  v=self.s.get(r['validation_ref']['object_id'],'owner');self.assertEqual(v['payload']['result'],'fail')
