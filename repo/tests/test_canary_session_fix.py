"""Synthetic verifier counterexamples; actual native receipts are recorded separately."""
import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from uacf.state import State,init,object_new,request
from uacf.service import verify_dsh
from uacf.util import file_hash

class SessionVerifier(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'backups')
  self.root=Path(self.tmp.name);init(self.root);self.state=State(self.root)
  self.task=self.state.put(request(object_new('TaskContract',{'goal':'synthetic canary verifier counterexample','constraints':[],'required_properties':['installed_loaded_called'],'execution_state':'pending'},'active','shared')),'owner')['object']
  # Identity checks need bytes, not an excluded private adapter implementation.
  target=self.root/'repo/adapters/dsh/index.js';target.parent.mkdir(parents=True);target.write_text('// Synthetic identity-only fixture; never loaded as a host adapter.\n',encoding='utf-8');self.target=target
 def tearDown(self):self.tmp.cleanup()
 def receipt(self,nonce,binding):
  return {'nonce':nonce,'plugin':{'file':str(self.target),'pid':123,'sha256':file_hash(self.target),'loaded_sha256':file_hash(self.target)},'session_binding':dict(binding,task_id=self.task['object_id'],task_revision=1),'tool_result':{'isError':False,'value':{'ok':True,'authority_id':self.state.authority,'nonce':nonce,'host_pid':123}},'context_result':{'isError':False,'value':{'body':json.dumps({'status':'ready','capsule':{'task_revision':1}})}}}
 def verify(self,binding):
  def response(req,**kw):
   nonce=json.loads(req.data)['nonce'];return io.BytesIO(json.dumps(self.receipt(nonce,binding)).encode())
  with patch('uacf.service.urllib.request.urlopen',side_effect=response):return verify_dsh(self.state,'owner',self.task['object_id'],1)
 def test_missing_agent_binding_cannot_pass(self):
  self.assertEqual(self.verify({})['result'],'fail')
 def test_registry_mismatch_cannot_pass(self):
  b={'agent_id':'synthetic-a','session_id':'synthetic-b','agent_registry_exact':True,'session_registry_exact':True,'factory':'ctx.agents.create','model_turns_requested':0,'turn_start_events':0}
  self.assertEqual(self.verify(b)['result'],'fail')
 def test_bound_receipt_and_unexpected_model_turn(self):
  b={'agent_id':'synthetic-a','session_id':'synthetic-a','agent_registry_exact':True,'session_registry_exact':True,'factory':'ctx.agents.create','model_turns_requested':0,'turn_start_events':0}
  self.assertEqual(self.verify(b)['result'],'pass');b['turn_start_events']=1
  self.assertEqual(self.verify(b)['result'],'fail')

if __name__=='__main__':unittest.main()
