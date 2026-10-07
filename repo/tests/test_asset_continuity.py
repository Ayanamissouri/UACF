import copy,tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.util import Fault,sha,canonical,atomic,uid
class AssetContinuity(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
 def tearDown(self):self.tmp.cleanup()
 def put(self,kind,payload,blob=None,visibility='shared'):
  if kind=='Artifact':payload={**payload,'locator':payload.get('source_locator','fixture'),'sha256':sha(blob)}
  return self.s.put(request(object_new(kind,payload,visibility=visibility),blob=blob),'owner')['object']
 def test_unrelated_commit_does_not_invalidate_preparation(self):
  task=self.put('TaskContract',{'goal':'focused work','required_properties':[]});key=self.s.context('pi',task['object_id'])['cache_key']
  self.put('Evidence',{'observation':{'unrelated':True}})
  self.assertEqual(self.s.context('pi',task['object_id'])['cache_key'],key)
  changed=copy.deepcopy(task);changed['payload']['goal']='actual correction';self.s.put(request(changed,1),'owner')
  self.assertNotEqual(self.s.context('pi',task['object_id'])['cache_key'],key)
 def test_body_requires_selection_acl_exact_revision_and_byte_limit(self):
  asset=self.put('Artifact',{'name':'work product','source_locator':'native tool output'},b'actual body')
  task=self.put('TaskContract',{'goal':'reuse asset','required_properties':[],'asset_refs':[{'object_id':asset['object_id'],'revision':1}]})
  args={'task_id':task['object_id'],'task_revision':1,'artifact_id':asset['object_id']}
  self.assertEqual(self.s.asset_read('pi',args)['bytes'],11)
  for change in [{'task_revision':2},{'max_bytes':1},{'artifact_id':'absent'}]:
   with self.assertRaises(Fault):self.s.asset_read('pi',{**args,**change})
  private=self.put('Artifact',{'name':'private'},b'private',visibility='private')
  other=self.put('TaskContract',{'goal':'private denial','required_properties':[],'asset_refs':[{'object_id':private['object_id'],'revision':1}]})
  with self.assertRaises(Fault):self.s.asset_read('pi',{'task_id':other['object_id'],'task_revision':1,'artifact_id':private['object_id']})
  changed=copy.deepcopy(asset);changed['payload']['name']='revised';self.s.put(request(changed,1),'owner')
  self.assertEqual(self.s.context('pi',task['object_id'])['status'],'missing')
  with self.assertRaises(Fault):self.s.asset_read('pi',args)
 def test_native_capture_is_scoped_idempotent_and_reusable(self):
  from uacf.artifact_capture import capture
  workspace=self.root/'workspace';workspace.mkdir();product=workspace/'result.json';product.write_text('{"verified":true}')
  task=self.put('TaskContract',{'goal':'capture native work','required_properties':[],
    'artifact_capture_roots':{'pi':[str(workspace)]},'artifact_capture_paths':{'pi':[str(product)]}})
  atomic(self.root/'data/host-bindings.json',canonical({'pi':{'exact-native':task['object_id']}}))
  args={'task_id':task['object_id'],'task_revision':1,'native_session_id':'exact-native'}
  a=capture(self.s,'pi',args);b=capture(self.s,'pi',args)
  self.assertFalse(a['artifacts'][0]['duplicate']);self.assertTrue(b['artifacts'][0]['duplicate'])
  self.assertEqual(a['artifacts'][0]['object_id'],b['artifacts'][0]['object_id'])
  self.assertEqual(len(self.s.list('owner','Artifact')),1)
  with self.assertRaises(Fault):capture(self.s,'codex',{**args,'host':'pi'})
  next_task=self.put('TaskContract',{'goal':'next task reuse','required_properties':[],'asset_refs':[{'object_id':a['artifacts'][0]['object_id'],'revision':1}]})
  self.assertEqual(self.s.asset_read('codex',{'task_id':next_task['object_id'],'task_revision':1,'artifact_id':a['artifacts'][0]['object_id']})['bytes'],17)
