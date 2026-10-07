import tempfile,unittest,json,uuid
from pathlib import Path
from unittest.mock import patch
from uacf.state import State,init,request,object_new
from uacf.service import execute_command
from uacf.learning import dispatch,folder
from uacf.native_reconcile import reconcile,inventory
from uacf.util import uid,sha,canonical,now,Fault,atomic

class NativeReconciliationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  dispatch(self.s,'owner','learning_configure',{'authorization':'synthetic current work fixture'})
  self.task=self.s.put(request(object_new('TaskContract',{'goal':'synthetic mapped work','required_properties':[],'learning_capture_policy':{'mode':'work_end'}},visibility='shared')),'owner')['object']
  atomic(self.s.data/'host-bindings.json',canonical({'codex':{'synthetic-session':self.task['object_id']}}))
  message=self.event({'native_type':'public/item','kind':'native_message','message':{'id':'synthetic-message','role':'user','content':'Complete the synthetic required steps.'}})
  execute_command(self.s,'codex',self.command(message))
 def tearDown(self):self.tmp.cleanup()
 def event(self,payload):
  identity=uid();return dict(event_id=identity,source_host='codex',host_epoch=identity,source_seq=1,type='observation',occurred_at=now(),observed_at=now(),schema_version='1.0',visibility='private',payload=dict(payload,native_session_id='synthetic-session',native_turn_id='synthetic-turn'))
 def command(self,event):
  operation=uid();cmd=dict(action='host_event',args=event,operation_id=operation,actor='codex',correlation_id=str(uuid.uuid5(uuid.UUID(operation),'correlation')),schema_version='1.0',scope='action:host_event',expected_revision=0);cmd['request_hash']=sha(cmd);return cmd
 def pending(self):
  event=self.event({'native_type':'turn/end','kind':'native_public_status','observed_status':'completed','completed_at':123})
  cmd=self.command(event)
  with patch('uacf.learning.after_work',side_effect=RuntimeError('synthetic interruption after event commit')):
   with self.assertRaises(RuntimeError):execute_command(self.s,'codex',cmd)
  return cmd,dict(native_operation=cmd['operation_id'],event_id=event['event_id'],task_id=self.task['object_id'],task_revision=self.task['revision'])
 def test_durable_event_recovers_source_without_host_or_model_replay(self):
  cmd,args=self.pending();view=inventory(self.s,'owner',{'task_id':self.task['object_id']});self.assertEqual(view['rows'][0]['event_id'],args['event_id']);r=reconcile(self.s,'owner',args)
  self.assertEqual(r['provider_calls'],0);self.assertFalse(r['host_work_replayed']);self.assertEqual(r['capture']['state'],'queued')
  with self.s.db() as c:record=c.execute('select state,response from command_operations where operation_id=?',(cmd['operation_id'],)).fetchone()
  self.assertEqual(record['state'],'done');self.assertTrue(json.loads(record['response'])['reconciled'])
  self.assertTrue(reconcile(self.s,'owner',args)['already_recorded']);self.assertEqual(len(list((folder(self.s)/'jobs').glob('*.json'))),1)
 def test_duplicate_native_completion_reuses_previous_source(self):
  first=self.event({'native_type':'turn/end','kind':'native_public_status','observed_status':'completed','completed_at':123})
  execute_command(self.s,'codex',self.command(first));before=len(self.s.list('owner','Artifact'))
  cmd,args=self.pending();r=reconcile(self.s,'owner',args)
  self.assertTrue(r['capture']['duplicate_completion']);self.assertEqual(r['capture']['canonical_end_event_id'],first['event_id']);self.assertEqual(len(self.s.list('owner','Artifact')),before)
 def test_permissions_revision_and_original_digest_required(self):
  cmd,args=self.pending()
  with self.assertRaises(Fault):reconcile(self.s,'codex',args)
  with self.assertRaises(Fault):reconcile(self.s,'owner',dict(args,task_revision=2))
  unrelated=self.event({'kind':'native_message','native_type':'public/item','message':{'id':'other','role':'user','content':'Other synthetic work.'}})
  execute_command(self.s,'codex',self.command(unrelated))
  with self.assertRaises(Fault):reconcile(self.s,'owner',dict(args,event_id=unrelated['event_id']))
 def test_same_turn_capture_only_adds_new_public_work(self):
  import base64
  from uacf.learning import after_work
  first=self.event({'native_type':'turn/end','kind':'native_public_status','observed_status':'completed','completed_at':123})
  execute_command(self.s,'codex',self.command(first))
  earlier=dispatch(self.s,'codex','learning_host_next',{'task_id':self.task['object_id']})
  self.assertIn('Complete the synthetic required steps.',canonical(earlier['input']))
  second_message=self.event({'native_type':'public/item','kind':'native_message','message':{'id':'new','role':'user','content':'New synthetic correction.'}})
  execute_command(self.s,'codex',self.command(second_message))
  second=self.event({'native_type':'public/item','kind':'native_message','message':{'id':'result','role':'assistant','content':'New synthetic result.'}})
  execute_command(self.s,'codex',self.command(second))
  result=after_work(self.s,'owner',dict(second,payload=dict(second['payload'],learning_signal='milestone')),checkpoint=True)
  source=json.loads(base64.b64decode(self.s.fetch_blob('owner',result['source_ref']['object_id'],1,1048576)['base64']))
  self.assertIsNotNone(source['previous_source_ref']);self.assertEqual(len(source['records']),2)
  self.assertNotIn('Complete the synthetic required steps.',canonical(source));self.assertIn('New synthetic correction.',canonical(source))
