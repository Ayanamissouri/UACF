"""Frozen bidirectional hard-contract examples; synthetic, never real-source proof."""
import copy,json,tempfile,unittest,zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uacf.state import init,State,object_new,request,restore,stale
from uacf.fabric import migrate,save,vector,config_set,projection,correct,ingest,build_workunit
from uacf.batch2 import reserve,settle,budget_get,route,integrate
from uacf.util import Fault,uid,canonical,file_hash

class Batch2Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.root=self.base/'root';init(self.root);self.s=State(self.root)
  self.backup=self.base/'before';self.s.backup(self.backup);restore(self.backup,self.base/'restore');migrate(self.s,self.backup)
 def tearDown(self):self.temp.cleanup()
 def fault(self,code,fn):
  with self.assertRaises(Fault) as r:fn()
  self.assertEqual(r.exception.code,code)
 def put(self,kind,payload,visibility='private'):
  if kind=='SemanticCard':payload=dict({'summary':'synthetic dependency case','evidence_map':[],'facets':{}},**payload)
  return save(self.s,kind,payload,visibility)
 def test_A01_unpinned_write_is_normalized_and_head_never_drifts(self):
  p=self.put('Project',{'name':'units','contracts':{'time':'s'}})
  t=self.put('TaskContract',{'goal':'fixed','required_properties':['x'],'project_id':p['object_id']})
  self.assertEqual(t['payload']['project_revision'],1);p['payload']['contracts']['time']='ms';self.s.put(request(p,1),'owner')
  self.assertEqual(self.s.context('owner',t['object_id'])['capsule']['project_contract']['payload']['contracts']['time'],'s')
 def test_A03_concurrent_config_CAS_and_durable_receipt(self):
  def writer(n):
   try:return config_set(self.s,'owner',{'host':'dsh','requested_tokens':n,'expected_revision':1},uid())['revision']
   except Fault as e:return e.code
  with ThreadPoolExecutor(2) as pool:result=list(pool.map(writer,[400000,500000]))
  self.assertCountEqual(result,[2,'REVISION_CONFLICT'])
  oid=uid();args={'host':'dsh','requested_tokens':700000,'expected_revision':2}
  with patch('uacf.fabric.atomic',side_effect=lambda p,b: (_ for _ in ()).throw(OSError('projection crash')) if p==self.s.data/'config.json' else __import__('uacf.util',fromlist=['atomic']).atomic(p,b)):
   with self.assertRaises(OSError):config_set(self.s,'owner',args,oid)
  self.assertEqual(self.s.config['revision'],3);self.assertEqual(config_set(self.s,'owner',args,oid)['revision'],3)
 def test_A04_nondefault_config_budget_restore_new_identity(self):
  config_set(self.s,'owner',{'host':'dsh','requested_tokens':600000,'capsule_max_bytes':12345,'expected_revision':1},uid())
  with self.s.db() as c:c.execute('INSERT INTO budget_accounts VALUES(?,?,?,?,?)',('batch2','CNY',30000000,123,1))
  backup=self.base/'changed';self.s.backup(backup);into=self.base/'recovered';restore(backup,into);s=State(into)
  self.assertEqual(s.config['capsule_max_bytes'],12345);self.assertEqual(s.config['context_profiles']['dsh']['requested_tokens'],600000)
  self.assertEqual(budget_get(s)['spent_micro'],123);self.assertNotEqual(s.authority,self.s.authority)
  self.assertNotEqual((s.data/'auth.json').read_bytes(),(self.s.data/'auth.json').read_bytes());self.assertIn('restore_mapping',s.config)
 def test_A05_body_mismatch_vs_preview(self):
  obj=object_new('Artifact',{'locator':'external','sha256':'a'*64})
  self.fault('ARTIFACT_HASH',lambda:self.s.put(request(obj,blob=b'actual'),'owner'))
  obj['payload']['blob_role']='preview';r=self.s.put(request(obj,blob=b'actual'),'owner')['object'];self.assertEqual(r['payload']['identity_verification'],'external_unverified')
 def test_A02_all_applicable_obligations_and_exclusions(self):
  t=self.put('TaskContract',{'goal':'g','required_properties':['x'],'host':'dsh'})
  for cond,status in [({},'proposed'),({'host':'pi'},'proposed'),({},'retracted')]:
   o=object_new('FailureCase',{'properties':['x'],'lesson':'L','source':{},'applicability':cond},status);self.s.put(request(o),'owner')
  a=self.s.context('owner',t['object_id'])['capsule']['failure_assessment'];self.assertEqual(len(a['effective_obligations']),1);self.assertEqual(len(a['excluded']),2)
 def message(self,kind='direct_user',current=True,text='Archive it. I am serious.',branch='main'):
  return self.put('Message',{'role':'user','source_kind':kind,'current':current,'text':text,'branch':branch})
 def claim(self,m,literal='archive'):
  return self.put('Claim',{'literal_content':literal,'speech_act':'request','source_kind':m['payload']['source_kind'],'branch':m['payload']['branch'],'interpretation_basis':[vector(m)],'lifecycle':'candidate','input_vector':[vector(m)]})
 def adoption(self,m,c,kind='current_direct_instruction'):
  return self.put('AdoptionDecision',{'claim_id':c['object_id'],'claim_revision':c['revision'],'basis':{'kind':kind,'message_id':m['object_id'],'message_revision':m['revision'],'explicit_attestation':True},'scope':{},'lifecycle':'adopted','input_vector':[vector(m),vector(c)]})
 def test_S02_T01_T02_T04_T05_T06_T13_candidate_vs_authorized_source(self):
  emotional=self.message(text='Never touching this again!');c=self.claim(emotional,'possible venting or abandonment');self.assertEqual(c['payload']['lifecycle'],'candidate');self.assertEqual(self.s.list('owner','AdoptionDecision'),[])
  explicit=self.message();self.assertEqual(self.adoption(explicit,self.claim(explicit))['payload']['lifecycle'],'adopted')
  for kind,current in [('tool',True),('quoted',True),('direct_user',False),('subagent',True)]:
   m=self.message(kind,current);c=self.claim(m);self.fault('ADOPTION_SOURCE',lambda:self.adoption(m,c))
  m=self.message();c=self.claim(m);self.fault('ADOPTION_BASIS',lambda:self.adoption(m,c,'model_inference'))
 def test_S02_T07_correction_invalidates_transitive_projection_and_stale_write(self):
  m=self.message();c=self.claim(m);card=self.put('SemanticCard',{'input_vector':[vector(c)]});d=self.put('Dossier',{'subject_id':c['object_id'],'cards':[vector(card)],'facets':{},'input_vector':[vector(card)]})
  r=correct(self.s,'owner',{'object_id':c['object_id'],'expected_revision':1,'changes':{'literal_content':'continue','lifecycle':'candidate'},'basis':'human correction'})
  self.assertIn(d['object_id'],r['invalidated_projection_ids']);self.assertTrue(stale(self.s,card));self.assertEqual(self.s.get(c['object_id'],'owner',1)['payload']['literal_content'],'archive')
  self.fault('REVISION_CONFLICT',lambda:correct(self.s,'owner',{'object_id':c['object_id'],'expected_revision':1,'changes':{},'basis':'stale'}))
 def test_S02_T12_permissions_tighten_transitive_no_existence_leak(self):
  m=self.put('Message',{'text':'secret'},'shared');card=self.put('SemanticCard',{'input_vector':[vector(m)]},'shared');d=self.put('Dossier',{'subject_id':m['object_id'],'cards':[vector(card)],'facets':{},'input_vector':[vector(card)]},'shared')
  m['visibility']='private';self.s.put(request(m,1),'owner');self.assertEqual(self.s.list('reader'),[]);self.fault('NOT_FOUND',lambda:self.s.get(d['object_id'],'reader'));self.assertEqual(projection(self.s,'reader')['nodes'],[])
 def test_T32_budget_parallel_total_and_unknown_lock(self):
  with self.s.db() as c:c.execute('INSERT INTO budget_accounts VALUES(?,?,?,?,?)',('batch2','CNY',100,0,1))
  def work(n):
   try:return reserve(self.s,'owner',{'amount_micro':60},uid())
   except Fault as e:return e.code
  with ThreadPoolExecutor(2) as pool:r=list(pool.map(work,[1,2]))
  self.assertEqual(sum(isinstance(x,dict) for x in r),1);self.assertIn('BUDGET_EXCEEDED',r)
  rid=next(x['reservation_id'] for x in r if isinstance(x,dict));settle(self.s,'owner',{'reservation_id':rid});self.assertEqual(budget_get(self.s)['available_micro'],40)
 def test_T30_T31_T33_modes_capability_no_silent_fallback(self):
  p=self.put('ProviderProfile',{'host':'dsh','provider':'x','model':'m','capabilities':{'generation':'unknown'},'pricing':{}})
  a=self.put('RoleAssignment',{'mode':'manual','roles':{'responder':[p['object_id']]},'fallback':None});args={'assignment_id':a['object_id']}
  self.fault('PROVIDER_UNAVAILABLE',lambda:route(self.s,'owner',args))
  p['payload']['capabilities']={'generation':'verified','reasoning_efforts':[]};self.s.put(request(p,1),'owner');self.fault('CAPABILITY_UNSUPPORTED',lambda:route(self.s,'owner',dict(args,reasoning_effort='magic')))
  for mode in ['manual','semi_auto','auto']:
   a['payload']['mode']=mode;a=self.s.put(request(a,a['revision']),'owner')['object'];self.assertEqual(route(self.s,'owner',args)['mode'],mode)
 def test_T37_conflicting_contributions_preserved(self):
  p=self.put('Project',{'name':'P','contracts':{}});cs=[self.put('Contribution',{'target_id':p['object_id'],'base_revision':1,'write_set':{'name':n}}) for n in ['A','B']]
  r=integrate(self.s,'owner',{'target_id':p['object_id'],'expected_revision':1,'contribution_ids':[c['object_id'] for c in cs]});self.assertEqual(r['status'],'conflict');self.assertEqual(self.s.get(p['object_id'],'owner')['revision'],1)
 def test_T40_relation_dependency_cycle_rejected(self):
  a=self.put('Attempt',{});b=self.put('Attempt',{});self.put('Relation',{'source_id':a['object_id'],'target_id':b['object_id'],'kind':'depends_on','basis':'test'})
  self.fault('DEPENDENCY_CYCLE',lambda:self.put('Relation',{'source_id':b['object_id'],'target_id':a['object_id'],'kind':'depends_on','basis':'test'}))
 def test_S02_T03_T06_versioned_qualifier_and_alternate_branch(self):
  a=self.message(text='A');b=self.message(text='B qualifies A');alt=self.message(text='opposite decision',branch='alternate')
  ca=self.claim(a,'A');cb=self.claim(b,'B');relation=self.put('Relation',{'source_id':ca['object_id'],'target_id':cb['object_id'],'kind':'qualifies','basis':'explicit relation, not newest-wins','input_vector':[vector(ca),vector(cb)]})
  self.assertEqual(relation['payload']['kind'],'qualifies')
  self.fault('BRANCH',lambda:build_workunit(self.s,'owner',{'message_ids':[a['object_id'],alt['object_id']],'purpose':'must not merge branches'}))
  c=self.claim(alt);c['payload']['branch']='main';c=self.s.put(request(c,1),'owner')['object'];self.fault('ADOPTION_BRANCH',lambda:self.adoption(alt,c))
 def test_S02_T05_T14_stopped_dispatch_and_advisory_capability(self):
  from uacf.batch2 import model_dispatch
  task=self.put('TaskContract',{'goal':'synthetic stop','required_properties':['x'],'execution_state':'stopped'})
  self.fault('STOPPED',lambda:model_dispatch(self.s,'owner',{'task_id':task['object_id'],'expected_revision':1},uid()))
  m=self.message();c=self.claim(m);c['payload']['speech_act']='hypothetical';c=self.s.put(request(c,1),'owner')['object'];self.fault('ADOPTION_BASIS',lambda:self.adoption(m,c))
 def test_S02_T08_T09_rebuild_mode_and_overflow(self):
  from uacf.fabric import rebuild
  m=self.message();c=self.claim(m);card=self.put('SemanticCard',{'input_vector':[vector(c)]})
  task=self.put('TaskContract',{'goal':'bounded','required_properties':['x'],'input_vector':[vector(card)]})
  correct(self.s,'owner',{'object_id':c['object_id'],'expected_revision':1,'changes':{'literal_content':'corrected'},'basis':'explicit engineering correction'})
  self.assertEqual(self.s.context('owner',task['object_id'])['status'],'missing')
  self.fault('LOCAL_FULL_REQUIRED',lambda:rebuild(self.s,'owner',{'object_id':c['object_id'],'mode':'REINDEX','basis':'wrong reuse label'}))
  rebuild(self.s,'owner',{'object_id':c['object_id'],'mode':'FULL','basis':'scoped correction'})
  self.assertEqual(self.s.context('owner',task['object_id'])['status'],'ready');self.assertEqual(self.s.context('owner',task['object_id'],1)['status'],'overflow')
 def test_actual_observation_kept_even_after_dependency_changes(self):
  t=self.put('TaskContract',{'goal':'source version','required_properties':['x']});old=vector(t);t['payload']['goal']='new';self.s.put(request(t,1),'owner')
  ev=self.put('Evidence',{'observation':{'actually_occurred':True},'input_vector':[old]});self.assertTrue(stale(self.s,ev));self.assertTrue(self.s.get(ev['object_id'],'owner')['payload']['observation']['actually_occurred'])
 def test_T19_T20_T43_T44_incremental_safe_roles_branches_REUSE_REINDEX(self):
  path=self.base/'synthetic.zip'
  rows=[{'seq':0,'type':'user/message','data':{'role':'user','content':[{'type':'text','text':'do'}],'source':{'kind':'user'}}},{'seq':0,'type':'tool/result','data':{'message':{'role':'user','content':[],'source':{'kind':'tool'}}}}]
  with zipfile.ZipFile(path,'w') as z:z.writestr('session.v3.jsonl','\n'.join(canonical(r) for r in rows))
  source=self.put('SourceSet',{'roots':[str(path)],'authorization':{'kind':'user_scope','sha256':file_hash(path)},'limits':{'max_bytes':10000,'max_records':64}})
  args={'source_id':source['object_id'],'member':'session.v3.jsonl','format':'dsh','interrupt_after':1}
  self.fault('INTERRUPTED',lambda:ingest(self.s,'owner',args));args.pop('interrupt_after');r=ingest(self.s,'owner',args);self.assertEqual(r['resumed_from'],1)
  messages=[self.s.get(i,'owner') for i in r['message_ids']];self.assertEqual([m['payload']['source_kind'] for m in messages],['direct_user','tool'])
  self.assertEqual(len(set(r['message_ids'])),2)
  from uacf.fabric import source_read
  self.assertTrue(source_read(self.s,'owner',{'message_id':r['message_ids'][1]})['original_identity_verified'])
  self.assertEqual(ingest(self.s,'owner',dict(args,mode='REUSE'))['source_bytes_read'],0);self.assertEqual(ingest(self.s,'owner',dict(args,mode='REINDEX'))['source_bytes_read'],0)
  p1=self.put('Project',{'name':'A','contracts':{}});p2=self.put('Project',{'name':'B','contracts':{}})
  w=build_workunit(self.s,'owner',{'message_ids':r['message_ids'],'purpose':'test','project_ids':[p1['object_id'],p2['object_id']]});self.assertEqual(len(w['affiliations']),2)
  self.fault('LOCATOR',lambda:ingest(self.s,'owner',dict(args,member='../escape')))

if __name__=='__main__':unittest.main(verbosity=2)
