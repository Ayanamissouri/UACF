import importlib.util,unittest
from unittest.mock import patch
import tempfile,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('public_read',Path(__file__).resolve().parents[1]/'adapters/codex/public_read.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PublicReadTests(unittest.TestCase):
 def test_native_end_reuses_first_receipted_completion_across_observation_ranges(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   for identity,stamp,receipt in [('synthetic-old','2026-01-01T00:00:00Z',True),('synthetic-new','2026-01-02T00:00:00Z',True),('synthetic-unknown','2025-01-01T00:00:00Z',False)]:
    event={'event_id':identity,'observed_at':stamp,'payload':{'native_session_id':'synthetic-session','native_turn_id':'synthetic-turn','native_type':'turn/end','observed_status':'completed','completed_at':123}}
    (root/(identity+'.json')).write_text(json.dumps(event))
    if receipt:(root/(identity+'-receipt.json')).write_text('{"ok":true}')
   self.assertEqual(m.prior_completion(root,'synthetic-session','synthetic-turn',123),'synthetic-old')
   self.assertIsNone(m.prior_completion(root,'synthetic-session','synthetic-turn',456))
 def test_unknown_delivery_is_reconciled_without_redispatch(self):
  with patch.object(m,'call',return_value={'operation':{'state':'done','response':{'ok':True}}}) as call:
   self.assertEqual(m.reconcile_event('synthetic',{},'synthetic-operation'),{'ok':True});self.assertEqual(call.call_count,1)
  with patch.object(m,'call',return_value={'operation':{'state':'pending','response':None}}) as call:
   with self.assertRaises(m.Fault):m.reconcile_event('synthetic',{},'synthetic-operation')
   self.assertEqual(call.call_count,1)
 def test_private_reasoning_and_opaque_tool_results_excluded(self):
  self.assertIsNone(m.public_item({'id':'synthetic','type':'reasoning','content':['never persist']}))
  x=m.public_item({'id':'synthetic','type':'mcpToolCall','tool':'bounded','result':{'reasoning':'never persist'},'arguments':{'secret':'not projected'}})
  self.assertNotIn('never persist',str(x));self.assertNotIn('secret',str(x))
 def test_public_inputs_outputs_and_real_tool_metadata(self):
  for x in [{'id':'synthetic-user','type':'userMessage','content':[{'type':'text','text':'test input'},{'type':'image','url':'not copied'}]},{'id':'synthetic-output','type':'agentMessage','text':'test output','phase':'final'},{'id':'synthetic-tool','type':'commandExecution','command':'synthetic check','exitCode':1,'aggregatedOutput':'test failure'}]:
   self.assertIsNotNone(m.public_item(x))
  self.assertNotIn('not copied',str(m.public_item({'id':'u','type':'userMessage','content':[{'type':'image','url':'not copied'}]})))
