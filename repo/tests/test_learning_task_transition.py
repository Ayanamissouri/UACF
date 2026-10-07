"""Synthetic mappings only; no native work event or completion is fabricated."""
import unittest,tempfile,json
from pathlib import Path
from uacf.state import init,State,object_new,request
from uacf.learning_lifecycle import bind
from uacf.fabric import vector
from uacf.util import sha,Fault
from uacf.batch3 import lease
class Transition(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  self.old=self.s.put(request(object_new('TaskContract',{'goal':'synthetic previous','execution_state':'blocked','required_properties':[]},visibility='shared')),'owner')['object']
  self.new=self.s.put(request(object_new('TaskContract',{'goal':'synthetic next','required_properties':[]},visibility='shared')),'owner')['object']
  self.before={'codex':{'synthetic-session':self.old['object_id']}};(self.root/'data/host-bindings.json').write_text(json.dumps(self.before))
  self.args={'host':'codex','native_session_id':'synthetic-session','native_locator':'synthetic:test-only','authorization':'synthetic owner continuation test','task_id':self.new['object_id'],'task_revision':1,'expected_binding_hash':sha(self.before),'previous_task_ref':vector(self.old)}
 def tearDown(self):self.tmp.cleanup()
 def test_transition_preserves_previous_task_and_records_decision(self):
  r=bind(self.s,'owner',self.args);self.assertFalse(r['automatic_callback_verified']);self.assertEqual(self.s.get(self.old['object_id'],'owner'),self.old)
  d=self.s.get(r['decision_ref']['object_id'],'owner');self.assertEqual(d['payload']['previous_task_ref'],vector(self.old));self.assertEqual(json.loads((self.root/'data/host-bindings.json').read_text())['codex']['synthetic-session'],self.new['object_id'])
 def test_exact_previous_head_required(self):
  self.args['previous_task_ref']['revision']=2
  with self.assertRaises(Fault):bind(self.s,'owner',self.args)
 def test_running_previous_task_refused(self):
  o=self.old.copy();o['payload']=dict(o['payload'],execution_state='running');o=self.s.put(request(o,expected=1),'owner')['object'];self.args['previous_task_ref']=vector(o)
  with self.assertRaises(Fault):bind(self.s,'owner',self.args)
 def test_active_previous_lease_refused(self):
  from uacf.fabric import migrate
  from uacf.batch3 import migrate3
  self.s.backup(self.root/'b1');migrate(self.s,self.root/'b1');self.s.backup(self.root/'b2');migrate3(self.s,self.root/'b2')
  lease(self.s,'owner','lease_acquire',{'scope':'synthetic-old-work','holder':'other-window','task_id':self.old['object_id'],'task_revision':1,'ttl':100})
  with self.assertRaises(Fault):bind(self.s,'owner',self.args)
 def test_binding_hash_and_owner_scope_required(self):
  with self.assertRaises(Fault):bind(self.s,'codex',self.args)
  self.args['expected_binding_hash']='not-current'
  with self.assertRaises(Fault):bind(self.s,'owner',self.args)
