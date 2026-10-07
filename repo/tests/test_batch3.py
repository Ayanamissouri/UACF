"""Frozen batch3 contract/fault drills; synthetic inputs, real SQLite/ZIP transactions."""
import json,time,unittest,zipfile,tempfile
from pathlib import Path
from uacf.state import State,init,restore,object_new,request
from uacf.fabric import migrate
from uacf.batch3 import migrate3,export,import_package,exchange_context,lease
from uacf.util import Fault,file_hash,uid

class Batch3(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'backups');self.root=Path(self.tmp.name)
  init(self.root);self.s=State(self.root);self.s.backup(self.root/'b1');migrate(self.s,self.root/'b1');self.s.backup(self.root/'b2');restore(self.root/'b2',self.root/'recovery');migrate3(self.s,self.root/'b2')
  self.t=self.s.put(request(object_new('TaskContract',{'goal':'synthetic handoff','required_properties':[],'constraints':['preserve history'],'execution_state':'pending'},'active','shared')),'owner')['object']
 def tearDown(self):self.tmp.cleanup()
 def bundle(self):
  out=export(self.s,'owner',{'task_id':self.t['object_id'],'task_revision':1,'path':str(self.root/'exchange.zip'),'next_action':'inspect pending task'})
  return {'path':out['path'],'package_hash':out['package_hash'],'accept_as':'external_snapshot','path_map':{}}
 def denied(self,code,fn):
  with self.assertRaises(Fault) as e:fn()
  self.assertEqual(e.exception.code,code)
 def test_B3_01_context_and_body(self):
  a=self.bundle();r=import_package(self.s,'owner',a);c=exchange_context(self.s,'owner',a)
  self.assertEqual(c['handoff']['capsule']['mandatory_constraints'],['preserve history']);self.assertFalse(r['canonical_heads_modified']);self.assertFalse(c['canonical_write'])
 def test_B3_02_duplicate_and_interruption(self):
  a=self.bundle();self.denied('INTERRUPTED',lambda:import_package(self.s,'owner',dict(a,interrupt_after=1)));self.assertIsNone(exchange_context(self.s,'owner',a)['handoff'])
  import_package(self.s,'owner',a);self.assertTrue(import_package(self.s,'owner',a)['duplicate'])
  self.denied('HASH',lambda:import_package(self.s,'owner',dict(a,package_hash='0'*64)))
 def test_B3_03_conflict_no_overwrite(self):
  a=self.bundle();o=self.s.get(self.t['object_id'],'owner');o['payload']['goal']='new current goal';self.s.put(request(o,1),'owner')
  import_package(self.s,'owner',a);self.assertEqual(self.s.get(o['object_id'],'owner')['payload']['goal'],'new current goal')
 def test_B3_04_fence_and_late_evidence(self):
  a={'scope':'task-execution','task_id':self.t['object_id'],'task_revision':1,'holder':'old','ttl':1};r=lease(self.s,'owner','lease_acquire',a)
  self.assertTrue(lease(self.s,'owner','lease_check',dict(a,fence=r['fence']))['authorized']);time.sleep(1.1)
  new=lease(self.s,'owner','lease_acquire',dict(a,holder='new'));self.assertGreater(new['fence'],r['fence']);self.denied('FENCED',lambda:lease(self.s,'owner','lease_check',dict(a,fence=r['fence'])))
  ev=lease(self.s,'owner','lease_result',dict(a,fence=r['fence'],observation={'actual':'late result'},outcome='unknown'));self.assertFalse(ev['executor_current']);self.assertFalse(ev['plan_modified'])
 def test_B3_05_permission_and_credentials(self):
  self.denied('PERMISSION',lambda:export(self.s,'reader',{}));a=self.bundle();self.denied('PERMISSION',lambda:import_package(self.s,'reader',a))
  task=self.s.get(self.t['object_id'],'owner');task['payload']['goal']='Bearer '+json.loads((self.s.data/'auth.json').read_text())['owner'];self.s.put(request(task,1),'owner')
  self.denied('SECRET',lambda:export(self.s,'owner',{'task_id':task['object_id'],'task_revision':2,'path':str(self.root/'bad.zip'),'next_action':'none'}))
 def test_B3_09_corrected_task_fences(self):
  a={'scope':'s','task_id':self.t['object_id'],'task_revision':1,'holder':'a'};r=lease(self.s,'owner','lease_acquire',a)
  task=self.s.get(self.t['object_id'],'owner');task['payload']['constraints'].append('new direct restriction');self.s.put(request(task,1),'owner')
  self.denied('FENCED',lambda:lease(self.s,'owner','lease_check',dict(a,fence=r['fence'])))
 def test_B3_version_and_tamper(self):
  a=self.bundle();p=Path(a['path'])
  with zipfile.ZipFile(p) as z:entries={n:z.read(n) for n in z.namelist()}
  m=json.loads(entries['manifest.json']);m['exchange_version']='99';entries['manifest.json']=json.dumps(m).encode()
  with zipfile.ZipFile(p,'w') as z:
   for n,b in entries.items():z.writestr(n,b)
  self.denied('VERSION_INCOMPATIBLE',lambda:import_package(self.s,'owner',dict(a,package_hash=file_hash(p))))
 def test_B3_12_budget_independent(self):
  from uacf.batch2 import reserve,settle,budget_get
  with self.s.db() as c:c.execute("INSERT INTO budget_accounts VALUES('batch2','CNY',30000000,0,1)")
  before=budget_get(self.s,'batch2');oid=uid();reserve(self.s,'owner',{'account':'batch3','amount_micro':25000000},oid)
  self.denied('BUDGET_EXCEEDED',lambda:reserve(self.s,'owner',{'account':'batch3','amount_micro':6000000},uid()))
  settle(self.s,'owner',{'reservation_id':oid});self.assertEqual(budget_get(self.s,'batch3')['locked_micro'],25000000);self.assertEqual(budget_get(self.s,'batch2'),before)
 def test_B3_03_actual_concurrent_CAS_and_import(self):
  from concurrent.futures import ThreadPoolExecutor
  def write_goal(goal):
   obj=self.s.get(self.t['object_id'],'owner',1);obj['payload']['goal']=goal
   try:return self.s.put(request(obj,1),'owner')['ok']
   except Fault as e:return e.code
  with ThreadPoolExecutor(2) as pool:results=list(pool.map(write_goal,['concurrent A','concurrent B']))
  self.assertEqual(results.count(True),1);self.assertEqual(results.count('REVISION_CONFLICT'),1)
  current=self.s.get(self.t['object_id'],'owner');out=export(self.s,'owner',{'task_id':current['object_id'],'task_revision':2,'path':str(self.root/'concurrent.zip'),'next_action':'preserve chosen current head'})
  args={'path':out['path'],'package_hash':out['package_hash'],'accept_as':'external_snapshot','path_map':{}}
  with ThreadPoolExecutor(2) as pool:list(pool.map(lambda _:import_package(self.s,'owner',args),[1,2]))
  with self.s.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM exchange_records WHERE package_hash=?',(out['package_hash'],)).fetchone()[0],out['objects'])
  self.assertEqual(self.s.get(current['object_id'],'owner')['payload']['goal'],current['payload']['goal'])
 def test_B3_05_blob_credentials_and_hash_binding(self):
  import hashlib
  from uacf.util import canonical
  token=json.loads((self.s.data/'auth.json').read_text())['owner']
  for i,encoding in enumerate(['utf-8','utf-16-le','utf-16-be']):
   body=token.encode(encoding);obj=self.s.put(request(object_new('Artifact',{'locator':'synthetic.txt','sha256':hashlib.sha256(body).hexdigest()},visibility='shared'),blob=body),'owner')['object']
   self.denied('SECRET',lambda:export(self.s,'owner',{'task_id':self.t['object_id'],'task_revision':1,'path':str(self.root/('secret'+str(i)+'.zip')),'next_action':'negative','object_ids':[obj['object_id']]}))
  body=b'allowed synthetic blob';obj=self.s.put(request(object_new('Artifact',{'locator':'synthetic.txt','sha256':hashlib.sha256(body).hexdigest()},visibility='shared'),blob=body),'owner')['object']
  result=export(self.s,'owner',{'task_id':self.t['object_id'],'task_revision':1,'path':str(self.root/'safe.zip'),'next_action':'verify bytes','object_ids':[obj['object_id']]})
  args={'path':result['path'],'package_hash':result['package_hash'],'accept_as':'external_snapshot','path_map':{}};self.assertTrue(import_package(self.s,'owner',args)['ok'])
  with zipfile.ZipFile(args['path']) as z:entries={n:z.read(n) for n in z.namelist()}
  manifest=json.loads(entries['manifest.json']);old='blobs/'+hashlib.sha256(body).hexdigest();newbody=token.encode();new='blobs/'+hashlib.sha256(newbody).hexdigest();entries.pop(old);manifest['files'].pop(old);entries[new]=newbody;manifest['files'][new]={'sha256':hashlib.sha256(newbody).hexdigest(),'bytes':len(newbody)};entries['manifest.json']=canonical(manifest).encode()
  malicious=self.root/'malicious.zip'
  with zipfile.ZipFile(malicious,'w') as z:
   for name,data in entries.items():z.writestr(name,data)
  self.denied('SECRET',lambda:import_package(self.s,'owner',dict(args,path=str(malicious),package_hash=file_hash(malicious))))
if __name__=='__main__':unittest.main()
