import copy,json,tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.fabric import vector
from uacf.util import Fault
from uacf import portable_assets as p

def card():
 return dict(slug='respect-required-work',kind='principle',title={'zh':'先核对必需工作','en':'Check required work'},principle={'zh':'按当前目标核对所有必需工序。','en':'Check each required step against the current objective.'},applicable={'zh':'目标与必需步骤已明确。','en':'The objective and required steps are explicit.'},excluded={'zh':'缺少必要授权时保留阻塞。','en':'Missing authorization remains a blocker.'},positive_example={'zh':'合成例：提交前发现缺项并补齐。','en':'Synthetic: find a missing step and complete it before delivery.'},negative_example={'zh':'合成例：用旁枝成果掩盖必需步骤缺失。','en':'Synthetic: replace a missing required step with unrelated output.'},topics=['work-intent'],confidence='provisional',limitations={'zh':'候选指导，不是任意工具的执行权限。','en':'Candidate guidance, not permission for arbitrary tools.'})

class PortableTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  init(Path(self.tmp.name));self.s=State(Path(self.tmp.name))
  self.src=self.s.put(request(object_new('Evidence',{'observation':{'fixture':'synthetic only'}})),'owner')['object']
 def tearDown(self):self.tmp.cleanup()
 def draft(self):return p.draft(self.s,'owner',{'card':card(),'source_refs':[vector(self.src)],'derivation_basis':'Synthetic contract test; not a private historical lesson.'})['module_ref']
 def reviewed(self):
  ref=self.draft();obj,_=p.read_module(self.s,'owner',ref)
  return p.review(self.s,'owner',{'module_ref':ref,'basis':'Review the exact synthetic public projection.','public_content_hash':obj['payload']['sha256']})['module_ref']
 def test_private_mapping_and_public_export_are_separate(self):
  ref=self.reviewed();result=p.export(self.s,'owner',{'module_refs':[ref]});body=json.dumps(result['bundle'])
  self.assertNotIn(self.src['object_id'],body);self.assertNotIn(ref['object_id'],body)
  self.assertEqual(p.links(self.s,'owner',{'module_ref':ref})['source_refs'],[vector(self.src)])
  self.assertFalse(result['upload_authorized']);self.assertFalse(result['bundle']['hard_rule_adoption'])
 def test_unreviewed_duplicate_and_nonowner_are_rejected(self):
  ref=self.draft()
  with self.assertRaises(Fault):p.export(self.s,'owner',{'module_refs':[ref]})
  with self.assertRaises(Fault):self.draft()
  with self.assertRaises(Fault):p.links(self.s,'codex',{'module_ref':ref})
 def test_source_change_blocks_export_without_reextracting(self):
  ref=self.reviewed();src=copy.deepcopy(self.src);src['payload']['observation']['updated']=True
  self.s.put(request(src,expected=src['revision']),'owner')
  with self.assertRaises(Fault):p.export(self.s,'owner',{'module_refs':[ref]})
 def test_revision_invalidates_review_and_preserves_old_snapshot(self):
  ref=self.reviewed();changed=card();changed['principle']['en']='Check required steps and preserve unresolved evidence.'
  result=p.revise(self.s,'owner',{'module_ref':ref,'card':changed,'source_refs':[vector(self.src)],'derivation_basis':'Synthetic correction.'})
  self.assertEqual(result['disclosure'],'draft');self.assertFalse(result['source_reextraction'])
  with self.assertRaises(Fault):p.export(self.s,'owner',{'module_refs':[result['module_ref']]})
  self.assertEqual(self.s.get(ref['object_id'],'owner',ref['revision'])['revision'],ref['revision'])
 def test_private_fields_and_identifiers_rejected(self):
  for text in ['F:\\Private\\chat.txt','user@example.com',self.src['object_id'],'Bearer '+'a'*32]:
   c=card();c['principle']['en']=text
   with self.assertRaises(Fault):p.validate(c)
  c=card();c['private_locator']='private'
  with self.assertRaises(Fault):p.validate(c)
 def test_authenticated_dispatch_and_opt_in_context(self):
  from uacf.service import dispatch,MUTATIONS
  ref=self.reviewed();self.assertIn('portable_review',MUTATIONS);self.assertIn('archive_trigger_check',MUTATIONS)
  self.assertEqual(len(dispatch(self.s,'owner','portable_overview',{})['rows']),1)
  task=self.s.put(request(object_new('TaskContract',{'goal':'Check required work steps','required_properties':[],'portable_lessons':True,'learning_capture_policy':{'mode':'adaptive'}},visibility='shared')),'owner')['object']
  capsule=self.s.context('codex',task['object_id'])
  self.assertEqual(capsule['status'],'ready');self.assertIn('archive_trigger_annotation',capsule['capsule'])
  lessons=capsule['capsule']['portable_lesson_candidates'];self.assertEqual(len(lessons['lessons']),1)
  self.assertNotIn(self.src['object_id'],json.dumps(lessons));self.assertLessEqual(lessons['assembled_bytes'],4000)
 def test_import_requires_local_review_and_preserves_public_origin(self):
  bundle=p.export(self.s,'owner',{'module_refs':[self.reviewed()]})['bundle']
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));other=State(Path(d));result=p.import_bundle(other,'owner',{'bundle':bundle,'license_basis':'Synthetic test permission only.'})
   ref=result['rows'][0]['module_ref'];obj,_=p.read_module(other,'owner',ref)
   self.assertEqual(obj['payload']['disclosure'],'draft');self.assertFalse(result['hard_rule_adoption'])
   with self.assertRaises(Fault):p.export(other,'owner',{'module_refs':[ref]})
   src=other.get(result['source_ref']['object_id'],'owner');self.assertIn('not this owner',src['payload']['origin'])
   self.assertEqual(p.import_bundle(other,'owner',{'bundle':bundle,'license_basis':'Synthetic test permission only.'})['rows'][0]['state'],'unchanged_existing')
 def test_conflicting_import_has_no_partial_modules(self):
  ref=self.reviewed();bundle=p.export(self.s,'owner',{'module_refs':[ref]})['bundle'];second=card();second['slug']='another-synthetic-principle';bundle['cards']=[second,card()];bundle['cards'][1]['principle']['en']='Conflicting replacement.'
  with self.assertRaises(Fault):p.import_bundle(self.s,'owner',{'bundle':bundle,'license_basis':'Synthetic.'})
  self.assertEqual(len(p.refs(self.s)),1)
 def test_original_conditions_only_resolve_exact_linked_source(self):
  ref=self.reviewed();detail=p.source_detail(self.s,'owner',{'module_ref':ref,'source_ref':vector(self.src)})
  self.assertIn('observation',detail['conditions'])
  with self.assertRaises(Fault):p.source_detail(self.s,'codex',{'module_ref':ref,'source_ref':vector(self.src)})
  unrelated=self.s.put(request(object_new('Evidence',{'observation':{'fixture':'not linked'}})),'owner')['object']
  with self.assertRaises(Fault):p.source_detail(self.s,'owner',{'module_ref':ref,'source_ref':vector(unrelated)})
