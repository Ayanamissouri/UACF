import json,tempfile,unittest
from pathlib import Path
from uacf.workflow import checkpoint_boundary
from uacf.util import file_hash,Fault

class CheckpointBoundary(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name)
  (self.out/'selection.json').write_text('{"packets":[]}')
  self.plan={'task_id':'fixture-task','task_revision':3,'architecture_checkpoints':[10,30,60,100]}
  self.objects={};self.accept={}
 def tearDown(self):self.tmp.cleanup()
 def accept_count(self,n):
  ref={'object_id':str(n),'revision':1};task={'object_id':'fixture-task','revision':3};h=file_hash(self.out/'selection.json')
  self.objects[str(n)]={'object_type':'Evidence','revision':1,'payload':{'observation':{'count':n,'task_ref':task,'selection_hash':h}}}
  self.accept[str(n)]={'evidence_ref':ref,'task_ref':task,'selection_hash':h}
  (self.out/'architecture-acceptance.json').write_text(json.dumps(self.accept))
 def test_partial_failure_resumes_only_permitted_segment(self):
  self.accept_count(10);self.accept_count(30)
  self.assertEqual(checkpoint_boundary(self.objects.get,self.out,self.plan,46,100),60)
  self.assertEqual(checkpoint_boundary(self.objects.get,self.out,self.plan,60,100),60)
 def test_file_cannot_replace_canonical_evidence(self):
  self.accept_count(10);self.objects['10']['payload']['observation']['task_ref']['revision']=2
  with self.assertRaises(Fault):checkpoint_boundary(self.objects.get,self.out,self.plan,10,100)
 def test_changed_source_manifest_blocks_next_segment(self):
  self.accept_count(10);(self.out/'selection.json').write_text('{"packets":[1]}')
  with self.assertRaises(Fault):checkpoint_boundary(self.objects.get,self.out,self.plan,10,100)
