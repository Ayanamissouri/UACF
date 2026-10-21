import json,tempfile,unittest
from pathlib import Path
from uacf.state import State,init,request,object_new
from uacf.host_work import configure,enter,mode,admit,policy,NOTICE
from uacf.util import Fault,uid

class HostWorkTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  configure(self.s,'owner',{'authorization':'Owner: default all work to UACF; silence continues'},uid())
 def tearDown(self):self.tmp.cleanup()
 def args(self,host='codex',sid='actual-native-fixture'):return dict(host=host,native_session_id=sid,goal='Read public course sources',native_locator='synthetic test fixture only')
 def test_silence_enters_without_paid_authority(self):
  r=enter(self.s,'codex',self.args(),uid());self.assertEqual(r['mode'],'uacf');self.assertFalse(r['wait_for_answer']);self.assertEqual(r['context']['status'],'ready')
  task=self.s.get(r['task_ref']['object_id'],'owner');self.assertFalse(task['payload']['allow_provider']);self.assertNotIn('budget_account',task['payload'])
  again=enter(self.s,'codex',self.args(),uid());self.assertEqual(again['task_ref'],r['task_ref'])
 def test_all_host_families_use_same_default(self):
  for host in ['codex','dsh','pi','claude_code','codex_cloud']:
   r=enter(self.s,host,self.args(host,host+'-native'),uid());self.assertEqual(r['mode'],'uacf')
 def test_unmapped_tool_denied(self):self.assertFalse(admit(self.s,'codex',dict(self.args(),tool_name='Bash',tool_input={'command':'echo test'}))['allowed'])
 def test_current_revision_required(self):
  r=enter(self.s,'codex',self.args(),uid());task=self.s.get(r['task_ref']['object_id'],'owner');task['payload']['goal']='amended';self.s.put(request(task,task['revision']),'owner')
  a=admit(self.s,'codex',dict(self.args(),task_revision=r['task_ref']['revision'],tool_name='Bash',tool_input={'command':'echo test'}));self.assertFalse(a['allowed']);self.assertEqual(a['code'],'REVISION_CONFLICT')
 def test_direct_provider_and_credential_route_denied(self):
  enter(self.s,'codex',self.args(),uid())
  for cmd in ['python -c "urllib.request.urlopen(\"https://api.deepseek.com/chat/completions\")"','Get-Content C:/Users/user/.dsh-research/.credentials.yaml']:
   r=admit(self.s,'codex',dict(self.args(),tool_name='Bash',tool_input={'command':cmd}));self.assertFalse(r['allowed'])
 def test_separate_provider_script_execution_denied(self):
  enter(self.s,'codex',self.args(),uid());p=self.root/'bypass.py';p.write_text('endpoint="https://api.deepseek.com/chat/completions"')
  r=admit(self.s,'codex',dict(self.args(),cwd=str(self.root),tool_name='Bash',tool_input={'command':'python bypass.py'}));self.assertEqual(r['code'],'UACF_PROVIDER_BYPASS')
 def test_explicit_owner_opt_out_is_only_exception(self):
  enter(self.s,'codex',self.args(),uid())
  for text in ['',NOTICE,'我没有说不使用UACF','以前说过不使用UACF']:
   with self.assertRaises(Fault):mode(self.s,'owner',dict(self.args(),mode='external',owner_response=text),uid())
  with self.assertRaises(Fault):mode(self.s,'codex',dict(self.args(),mode='external',owner_response='不使用UACF'),uid())
  mode(self.s,'owner',dict(self.args(),mode='external',owner_response='不使用UACF'),uid())
  r=admit(self.s,'codex',dict(self.args(),tool_name='Bash',tool_input={'command':'curl https://api.deepseek.com/chat/completions'}));self.assertTrue(r['allowed']);self.assertTrue(r['explicit_opt_out'])
 def test_host_cannot_choose_other_host_or_policy(self):
  with self.assertRaises(Fault):enter(self.s,'pi',self.args(),uid())
  with self.assertRaises(Fault):configure(self.s,'codex',{'authorization':'claim'},uid())
 def test_policy_projection_tamper_rejected(self):
  p=self.root/'data/host-work/policy.json';x=json.loads(p.read_text());x['config']['default_mode']='external';p.write_text(json.dumps(x))
  with self.assertRaises(Fault):policy(self.s)
 def test_new_hosts_can_record_own_observations_not_owner_objects(self):
  from uacf.util import now
  for host in ['claude_code','codex_cloud']:
   e=dict(event_id=uid(),source_host=host,host_epoch=uid(),source_seq=1,type='observation',occurred_at=now(),observed_at=now(),schema_version='1.0',visibility='private',payload={'kind':'fixture'})
   self.assertTrue(self.s.host_event(e,host)['ok'])
   obj=object_new('Evidence',{'observation':{'fixture':'synthetic'}})
   self.s.put(request(obj,actor=host),host)
   with self.assertRaises(Fault):self.s.put(request(object_new('Decision',{'mode':'external'}),actor=host),host)
   with self.assertRaises(Fault):self.s.host_event(dict(e,event_id=uid(),source_host='codex'),host)
 def test_default_policy_is_mandatory_in_existing_task_capsule(self):
  task=self.s.put(request(object_new('TaskContract',{'goal':'existing work','required_properties':[]},visibility='shared')),'owner')['object']
  r=self.s.context('codex',task['object_id']);self.assertEqual(r['status'],'ready');self.assertEqual(r['capsule']['mandatory_default_work_policy']['notice'],NOTICE)
  self.assertEqual(self.s.context('codex',task['object_id'],1)['status'],'overflow')

if __name__=='__main__':unittest.main()
