import json,tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.catalog import catalog
from uacf.util import canonical,now,Fault,file_hash

class CatalogueContracts(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  with self.s.db() as c:
   for n in ['002.sql','003.sql','004-archive.sql']:c.executescript((Path(__file__).resolve().parents[1]/'contracts/migrations'/n).read_text())
  self.source=object_new('Project',{'name':'private source','contracts':{}},visibility='private');self.s.put(request(self.source),'owner')
  with self.s.db() as c:
   c.execute('insert into archive_plans values(?,?,?,?,?)',('p',self.source['object_id'],'fixture','{}',now()))
   for i in range(65):
    c.execute('insert into archive_conversations values(?,?,?,?,?,?,?)',('p','one',i,str(i),'title '+str(i),'hash','{}'))
    c.execute('insert into archive_messages values(?,?,?,?,?,?,?)',('p','one',i,'node','hash',canonical({'message':{'content':{'parts':['buried keyword-secret-'+str(i)]}}}),canonical({'role':'user','text_preview':'buried keyword-secret-'+str(i)})))
 def tearDown(self):self.tmp.cleanup()
 def test_default_has_counts_and_branches_no_source_bodies(self):
  r=catalog(self.s,'owner',{});self.assertEqual(r['counts']['archive_conversations'],65);self.assertFalse(r['body_loaded']);self.assertNotIn('keyword-secret',canonical(r));self.assertEqual([x['key'] for x in r['roots']],['projects','issues','tags','archive'])
 def test_private_plan_cannot_be_searched_or_expanded(self):
  self.assertEqual(catalog(self.s,'codex',{})['counts']['archive_conversations'],0)
  self.assertEqual(catalog(self.s,'codex',{'mode':'children','scope':'body','query':'secret'})['total'],0)
  for mode in ['messages','message']:
   with self.assertRaises(Fault):catalog(self.s,'codex',{'mode':mode,'locator':{'plan_id':'p','member':'one','ordinal':0,'node':'node'}})
 def test_archive_completion_is_not_selected_span_or_semantic_acceptance(self):
  with self.s.db() as c:
   c.execute('update archive_plans set plan=? where id=?',(canonical({'members':['one','two']}),'p'))
   c.execute('insert into archive_progress values(?,?,?,?,?)',('p','one',65,'done','{}'))
  r=catalog(self.s,'owner',{});self.assertEqual(r['archive_coverage']['structure_status'],'partial')
  with self.s.db() as c:c.execute('insert into archive_progress values(?,?,?,?,?)',('p','two',0,'done','{}'))
  r=catalog(self.s,'owner',{});coverage=r['archive_coverage']
  self.assertEqual(coverage['structure_status'],'complete_for_frozen_shards');self.assertEqual(coverage['nodes'],65)
  self.assertEqual(r['counts']['selected_conversations'],0);self.assertEqual(coverage['full_semantic_acceptance'],'not_recorded')
  self.assertNotIn('尚未整理',canonical(r));self.assertEqual(catalog(self.s,'owner',{'mode':'children','key':'archive:all'})['total'],65)
  self.assertEqual(catalog(self.s,'codex',{})['archive_coverage']['nodes'],0)
 def test_body_keyword_search_and_body_loading_are_explicit(self):
  self.assertEqual(catalog(self.s,'owner',{'mode':'children','query':'keyword-secret'})['total'],0)
  r=catalog(self.s,'owner',{'mode':'children','scope':'body','query':'keyword-secret-64'});self.assertEqual(r['total'],1);self.assertFalse(r['body_loaded'])
  loc=r['items'][0]['locator'];nodes=catalog(self.s,'owner',{'mode':'messages','locator':loc});self.assertNotIn('keyword-secret',canonical(nodes))
  read=catalog(self.s,'owner',{'mode':'message','locator':dict(loc,node='node')});self.assertTrue(read['body_loaded']);self.assertIn('keyword-secret-64',canonical(read))
 def test_multitag_is_one_record_and_refusal_not_ai_bug(self):
  def case(title,axes,tags,assessment):
   o=object_new('FailureCase',{'lesson':title,'properties':[],'applicability':{},'source':{'kind':'test fixture'},'catalog_review':{'axes':axes,'tags':tags,'assessment':assessment,'basis':'fixture explicit review'}},visibility='shared');self.s.put(request(o),'owner');return o
  o=case('f',['ai_execution'],['a','b'],'observed');case('refusal',['policy_boundary'],['wall-clock'],'boundary')
  r=catalog(self.s,'owner',{});self.assertEqual(r['counts']['issue_records'],2);self.assertEqual(r['counts']['ai_issue_records'],1);self.assertEqual(r['counts']['project_issue_records'],0)
  for tag in ['a','b']:self.assertEqual(catalog(self.s,'owner',{'mode':'children','key':'tag:'+tag})['items'][0]['id'],o['object_id'])
 def test_search_pagination_does_not_skip_mixed_records(self):
  for i in range(3):self.s.put(request(object_new('Project',{'name':'title project '+str(i),'contracts':{}},visibility='shared')),'owner')
  r=catalog(self.s,'owner',{'mode':'children','query':'title','limit':10,'offset':1});self.assertEqual(len(r['items']),10);self.assertEqual(r['total'],68)
  with self.assertRaises(Fault):catalog(self.s,'owner',{'query':5})
 def test_native_return_is_lazy_private_and_hash_checked(self):
  path=self.root/'logs/native-fixture.json';path.write_text(canonical({'tool_results':[{'seq':16,'isError':False,'result':{'stdout':'private return sentinel'}}]}))
  ev=object_new('Evidence',{'observation':{'method':'native_DSH_two_rounds_with_independent_stdout_comparison','source_locator':str(path),'source_sha256':file_hash(path)}},visibility='shared');self.s.put(request(ev),'owner')
  args={'mode':'native-return','key':ev['object_id'],'seq':16}
  with self.assertRaises(Fault):catalog(self.s,'codex',args)
  self.assertIn('private return sentinel',canonical(catalog(self.s,'owner',args)))
  path.write_text('{}')
  with self.assertRaises(Fault):catalog(self.s,'owner',args)
 def test_project_issue_reference_follows_evidence_not_keyword_or_new_affiliation(self):
  project=self.s.put(request(object_new('Project',{'name':'actual project','contracts':{}},visibility='shared')),'owner')['object']
  task=self.s.put(request(object_new('TaskContract',{'goal':'task','project_id':project['object_id'],'project_revision':1,'required_properties':[],'constraints':[]},visibility='shared')),'owner')['object']
  evidence=self.s.put(request(object_new('Evidence',{'observation':{'task_id':task['object_id']}},visibility='shared')),'owner')['object']
  case=self.s.put(request(object_new('FailureCase',{'lesson':'actual case','properties':[],'applicability':{},'source':{'evidence_id':evidence['object_id']}},visibility='shared')),'owner')['object']
  r=catalog(self.s,'owner',{'mode':'children','key':'project:'+project['object_id']})
  self.assertIn(case['object_id'],[o['id'] for o in r['items']]);self.assertEqual(self.s.list('owner','Affiliation'),[])
