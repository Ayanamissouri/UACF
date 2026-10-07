import importlib.util,json,tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.spool import enqueue,sync
from uacf.mcp import handle
from uacf.util import Fault,uid,now,atomic,canonical

class EcosystemTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
 def tearDown(self):self.tmp.cleanup()
 def event(self,host):return dict(event_id=uid(),source_host=host,host_epoch=uid(),source_seq=1,type='observation',occurred_at=now(),observed_at=now(),schema_version='1.0',visibility='private',payload={'kind':'probe'})
 def test_pi_host_has_no_contract_or_other_host_authority(self):
  e=self.event('pi');self.s.host_event(e,'pi');self.assertTrue(self.s.host_event(e,'pi')['duplicate'])
  with self.assertRaises(Fault):self.s.host_event(self.event('codex'),'pi')
  with self.assertRaises(Fault):self.s.put(request(object_new('TaskContract',{'goal':'unauthorized','required_properties':[]}),actor='pi'),'pi')
  from uacf.host_continuity import observe
  self.assertEqual(len(observe(self.s,'pi',{'host':'pi'})['events']),1)
  with self.assertRaises(Fault):observe(self.s,'codex',{'host':'pi'})
 def test_spool_scoped_sync_cannot_impersonate_another_host(self):
  p=self.event('pi');c=self.event('codex');enqueue(self.root,p);enqueue(self.root,c)
  result=sync(self.root,lambda e:self.s.host_event(e,'codex'),source_host='codex')
  self.assertEqual(len(result['receipts']),1);self.assertTrue((self.root/'data/host-spool'/p['event_id']).exists())
 def test_mcp_declared_schema_and_versions_are_enforced(self):
  self.assertEqual(handle(self.root,'pi',{'method':'initialize','params':{'protocolVersion':'2025-11-25'}})['protocolVersion'],'2025-11-25')
  for args in [{'task_id':42},{'task_id':'x','max_bytes':0},{'task_id':'x','extra':'write'}]:
   result=handle(self.root,'pi',{'method':'tools/call','params':{'name':'uacf_context','arguments':args}})
   self.assertTrue(result['isError']);self.assertEqual(json.loads(result['content'][0]['text'])['code'],'INPUT')
 def test_codex_locator_redelivery_dedup_and_conflict(self):
  spec=importlib.util.spec_from_file_location('hook',Path(__file__).resolve().parents[1]/'adapters/codex/hook.py');hook=importlib.util.module_from_spec(spec);spec.loader.exec_module(hook)
  atomic(self.root/'data/host-bindings.json',canonical({'codex':{'native-test':'mapped-task'}}))
  event={'session_id':'native-test','hook_event_name':'PostToolUse','tool_use_id':'exact-tool-call','tool_name':'read','tool_response':'actual-result'}
  # Offline enqueue only; no fake native Host invocation is claimed.
  original=hook.call;hook.call=lambda *a,**kw:(_ for _ in ()).throw(OSError('offline'))
  try:
   hook.run(self.root,event);hook.run(self.root,event);self.assertEqual(len(list((self.root/'data/host-spool').glob('*'))),1)
   with self.assertRaises(Fault):hook.run(self.root,{**event,'tool_response':'changed'})
  finally:hook.call=original
