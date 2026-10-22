import copy,json,tempfile,unittest,uuid
from pathlib import Path
from uacf.state import State,init,object_new,request,restore,verify_backup
from uacf.storage_layout import allocated_path,configure,layout,resolve_bundle,task_paths,batch_path
from uacf.util import Fault

class StorageLayout(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
  self.root=self.base/'uacf';init(self.root);self.state=State(self.root)
  self.quant=self.base/'quant';self.quant.mkdir();self.task_id=str(uuid.uuid4())
 def tearDown(self):self.temp.cleanup()
 def configure(self):
  return configure(self.state,'owner',{'authorization':'Owner explicit test project','projects':{'uacf':{'root':str(self.root)},'quant':{'root':str(self.quant)}},'bundles':{'study':{'path':str(self.root/'artifacts/study'),'project_key':'uacf'}}})
 def test_explicit_project_routes_and_no_implicit_cross_project_default(self):
  self.configure()
  task={'object_id':self.task_id,'payload':{'output_contract':{'project_key':'quant','project_root':str(self.quant)}}}
  paths=task_paths(self.state,task)
  self.assertTrue(all(Path(x).is_relative_to(self.quant) for x in paths.values()))
  self.assertFalse(any(Path(x).exists() for x in paths.values()))
  with self.assertRaises(Fault):task_paths(self.state,{'object_id':self.task_id,'payload':{}})
  task['payload']['output_contract']['project_root']=str(self.root)
  with self.assertRaises(Fault):task_paths(self.state,task)
 def test_traversal_and_external_link_denied(self):
  for rel in ['../escape','C:/elsewhere','foo\\bar','/absolute']:
   with self.subTest(rel=rel),self.assertRaises(Fault):allocated_path(self.quant,self.task_id,'deliverable',rel)
  outside=self.base/'outside';outside.mkdir()
  link=self.quant/'deliverables'
  try:link.symlink_to(outside,target_is_directory=True)
  except OSError:return
  with self.assertRaises(Fault):allocated_path(self.quant,self.task_id,'deliverable','x')
 def test_owner_only_policy_and_immutable_projection(self):
  with self.assertRaises(Fault):configure(self.state,'codex',{'authorization':'external text'})
  self.configure();self.assertEqual(resolve_bundle(self.state,'study'),self.root/'artifacts/study')
  p=self.state.data/'storage-layout.json';body=json.loads(p.read_text());body['config']['projects']['quant']['root']=str(self.root);p.write_text(json.dumps(body))
  with self.assertRaises(Fault):layout(self.state)
 def test_cross_project_bundle_rejected(self):
  with self.assertRaises(Fault):configure(self.state,'owner',{'authorization':'Owner','projects':{'quant':{'root':str(self.quant)}},'bundles':{'bad':{'path':str(self.root/'secret'),'project_key':'quant'}}})
 def test_registered_stage_refuses_missing_contract(self):
  from uacf.project_workflow import dispatch
  self.configure()
  obj=object_new('TaskContract',{'goal':'fixture','required_properties':[]},visibility='shared')
  task=self.state.put(request(obj),'owner')['object']
  dispatch(self.state,'owner','workflow_project_configure',{'task_id':task['object_id'],'task_revision':1},str(uuid.uuid4()))
  with self.assertRaises(Fault) as failure:
   dispatch(self.state,'owner','workflow_project_record',{'task_id':task['object_id'],'task_revision':2,'stage_id':'s1','state':'started'},str(uuid.uuid4()))
  self.assertEqual(failure.exception.code,'OUTPUT_CONTRACT_REQUIRED')
 def test_registered_capture_rejects_cross_project_root_before_snapshot(self):
  from uacf.artifact_capture import capture
  self.configure()
  obj=object_new('TaskContract',{'goal':'fixture','required_properties':[],'output_contract':{'project_key':'quant','project_root':str(self.quant)},'artifact_capture_roots':{'codex':[str(self.root)]}},visibility='shared')
  task=self.state.put(request(obj),'owner')['object']
  (self.state.data/'host-bindings.json').write_text(json.dumps({'codex':{'native-fixture':task['object_id']}}))
  with self.assertRaises(Fault) as failure:capture(self.state,'owner',{'host':'codex','native_session_id':'native-fixture','task_id':task['object_id'],'task_revision':1})
  self.assertEqual(failure.exception.code,'STORAGE_ESCAPE')
 def test_backup_layout_integrity_restore_and_external_write_block(self):
  self.configure();backup=self.base/'backup';self.state.backup(backup)
  self.assertTrue(verify_backup(backup)['ok']);restore(backup,self.base/'restored')
  s=State(self.base/'restored')
  self.assertTrue((s.data/'storage-layout.json').is_file())
  with self.assertRaises(Fault):task_paths(s,{'object_id':self.task_id,'payload':{'output_contract':{'project_key':'quant','project_root':str(self.quant)}}})
  (backup/'storage-layout.json').write_text('{}')
  with self.assertRaises(Fault):verify_backup(backup)
 def test_legacy_batch_readable_but_no_new_execution_in_delivery_folder(self):
  self.configure();name='e7-workflow-test'
  self.assertEqual(batch_path(self.state,name),self.root/'deliverables'/name)
  with self.assertRaises(Fault) as failure:batch_path(self.state,name,write=True)
  self.assertEqual(failure.exception.code,'STORAGE_MIGRATION_REQUIRED')
  from uacf.workflow import dispatch
  out=self.root/'deliverables'/name;out.mkdir(parents=True)
  (self.state.data/'e7-active-batch.json').write_text(json.dumps({'directory':name}))
  with self.assertRaises(Fault) as failure:dispatch(self.state,'owner','workflow_start',{})
  self.assertEqual(failure.exception.code,'STORAGE_MIGRATION_REQUIRED')
  self.assertFalse((out/'control.json').exists())
 def test_registered_batch_project_boundary_and_restore(self):
  name='e7-workflow-test';target=self.root/'artifacts/archive-processing'/name
  configure(self.state,'owner',{'authorization':'fixture','projects':{'uacf':{'root':str(self.root)}},'bundles':{name:{'path':str(target),'project_key':'uacf'}}})
  self.assertEqual(batch_path(self.state,name,write=True),target)
  backup=self.base/'batch-backup';self.state.backup(backup)
  restore(backup,self.base/'batch-restored');isolated=State(self.base/'batch-restored')
  with self.assertRaises(Fault) as failure:batch_path(isolated,name,write=True)
  self.assertEqual(failure.exception.code,'STORAGE_REMAP_REQUIRED')
  for bad in ['../escape','e7-workflow-../../x']:
   with self.assertRaises(Fault):batch_path(self.state,bad)
 def test_registered_batch_cannot_designate_delivery_as_work(self):
  name='e7-workflow-test'
  configure(self.state,'owner',{'authorization':'fixture','projects':{'uacf':{'root':str(self.root)}},'bundles':{name:{'path':str(self.root/'deliverables'/name),'project_key':'uacf'}}})
  with self.assertRaises(Fault):batch_path(self.state,name,write=True)

if __name__=='__main__':unittest.main()
