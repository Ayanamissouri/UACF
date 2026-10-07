import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from uacf.workflow import dispatch,anchored_packet
from uacf.util import Fault,sha,canonical
class WorkflowControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.out=self.root/'deliverables/e7-workflow-20261005';self.out.mkdir(parents=True)
  self.state=SimpleNamespace(root=self.root)
  (self.root/'data').mkdir();(self.root/'data/e7-active-batch.json').write_text(json.dumps({'directory':self.out.name}))
  (self.out/'plan.json').write_text('{}');(self.out/'status.json').write_text('{"state":"ready","completed":[]}')
 def tearDown(self):self.tmp.cleanup()
 def test_reader_cannot_launch_or_change_routes(self):
  for action in ['workflow_start','workflow_configure','workflow_pause','workflow_resolve_rejection','workflow_review_submit']:
   with self.assertRaises(Fault) as f:dispatch(self.state,'reader',action,{})
   self.assertEqual(f.exception.code,'PERMISSION')
 def test_reader_cannot_switch_batches(self):
  with self.assertRaises(Fault) as f:dispatch(self.state,'reader','workflow_select_batch',{'directory':'e7-workflow-next'})
  self.assertEqual(f.exception.code,'PERMISSION')
 def test_batch_switch_rejects_traversal(self):
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_select_batch',{'directory':'../../data'})
  self.assertEqual(f.exception.code,'INPUT')
 def test_batch_switch_does_not_abandon_pending_host_review(self):
  (self.out/'status.json').write_text('{"state":"waiting_host_review"}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_select_batch',{'directory':'e7-workflow-next'})
  self.assertEqual(f.exception.code,'BUSY')
 def test_unsupported_model_does_not_silently_substitute(self):
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_configure',{'extract':'unregistered','host':'codex_deepseek','review_percent':5,'expected_revision':0})
  self.assertEqual(f.exception.code,'INPUT');self.assertFalse((self.out/'active-config.json').exists())
 def test_stale_route_is_rejected_before_write(self):
  (self.out/'active-config.json').write_text('{"revision":2}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_configure',{'extract':'deepseek-flash','host':'codex_deepseek','review_percent':5,'expected_revision':1})
  self.assertEqual(f.exception.code,'REVISION_CONFLICT')
 def test_unknown_external_outcome_not_released(self):
  (self.out/'status.json').write_text('{"state":"blocked","error":"unknown external outcome"}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_resolve_rejection',{})
  self.assertEqual(f.exception.code,'OUTCOME_UNKNOWN')
 def test_publication_requires_all_150(self):
  (self.out/'active-config.json').write_text('{"revision":2}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_start',{'scope':'publish','expected_revision':2})
  self.assertEqual(f.exception.code,'INPUT')
 def test_publication_rejects_wrong_indices_even_at_same_count(self):
  (self.out/'active-config.json').write_text('{"revision":2}')
  (self.out/'selection.json').write_text('{"packets":[{"index":0},{"index":1}]}')
  (self.out/'status.json').write_text('{"state":"idle","completed":[0,2]}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_start',{'scope':'publish','expected_revision':2})
  self.assertEqual(f.exception.code,'INPUT')
 def test_published_batch_cannot_restart(self):
  (self.out/'active-config.json').write_text('{"revision":2}')
  (self.out/'status.json').write_text('{"state":"published"}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_start',{'scope':'production','expected_revision':2})
  self.assertEqual(f.exception.code,'ALREADY_PUBLISHED')
 def test_unknown_receipt_cannot_enter_format_repair(self):
  (self.out/'active-config.json').write_text('{"revision":2,"extract":"deepseek-flash"}')
  (self.out/'status.json').write_text('{"state":"blocked","error":"INVALID_JSON_REQUIRES_EXPLICIT_CORRECTION"}')
  (self.out/'call-01-000.json').write_text('{"state":"unknown","parsed":null}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_start',{'scope':'repair','expected_revision':2})
  self.assertEqual(f.exception.code,'OUTCOME_UNKNOWN')
 def test_provider_probe_cannot_substitute_gpt(self):
  (self.out/'active-config.json').write_text('{"revision":2,"extract":"gpt-6.1-sol"}')
  with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_start',{'scope':'probe','expected_revision':2})
  self.assertEqual(f.exception.code,'INPUT')
 def test_source_projection_tamper_is_rejected(self):
  p={'nodes':[{'text':'altered'}],'artifact_ref':{'object_id':'source','revision':1}}
  self.state.get=lambda *_:{'revision':1,'payload':{'sha256':sha(canonical({'nodes':[{'text':'original'}]}).encode())}}
  with self.assertRaises(Fault) as f:anchored_packet(self.state,p,'owner')
  self.assertEqual(f.exception.code,'SOURCE_CHANGED')
 def test_source_projection_revision_must_match(self):
  p={'nodes':[],'artifact_ref':{'object_id':'source','revision':1}}
  self.state.get=lambda *_:{'revision':2,'payload':{'sha256':sha(canonical({'nodes':[]}).encode())}}
  with self.assertRaises(Fault) as f:anchored_packet(self.state,p,'owner')
  self.assertEqual(f.exception.code,'SOURCE_CHANGED')
if __name__=='__main__':unittest.main()
