import unittest,tempfile,json,uuid
from pathlib import Path
from unittest.mock import patch
from uacf.state import init,State,object_new,request
from uacf.unified_assets import refresh,search,read,public_text,matches
from uacf.util import canonical,sha,now,Fault

class UnifiedAssets(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init(self.root);self.s=State(self.root)
  with self.s.db() as c:
   for name in ['002.sql','003.sql','004-archive.sql']:c.executescript((Path(__file__).resolve().parents[1]/'contracts/migrations'/name).read_text())
  src=self.s.put(request(object_new('Project',{'name':'synthetic archive','contracts':{}},visibility='private')),'owner')['object']
  with self.s.db() as c:
   c.execute('insert into archive_plans values(?,?,?,?,?)',('p',src['object_id'],'fixture','{}',now()))
   c.execute('insert into archive_conversations values(?,?,?,?,?,?,?)',('p','one',0,'gpt-id','old Plus','hash','{}'))
   c.execute('insert into archive_messages values(?,?,?,?,?,?,?)',('p','one',0,'node','hash',canonical({'message':{'content':{'parts':['Plus archived source']}}}),'{}'))
  body=canonical({'records':[{'id':'n','role':'user','content':'Plus UACF一期 subscription cost'},{'id':'r','channel':'analysis','content':'hidden private marker'}]})
  a=object_new('Artifact',{'name':'phase1','locator':'synthetic:codex','sha256':sha(body.encode()),'source_kind':'native_history_snapshot','native_host':'codex','native_session_id':'c','native_cwd':'workspace'},visibility='private')
  self.old_hash=sha(body.encode());self.asset=self.s.put(request(a,blob=body.encode()),'owner')['object'];refresh(self.s)
 def tearDown(self):self.tmp.cleanup()
 def test_all_sources_and_native_locator(self):
  r=search(self.s,'owner',{'query':'Plus'});self.assertEqual(r['source_counts'],{'codex':1,'gpt_export':1})
  native=next(x for x in r['items'] if x['host']=='codex');self.assertEqual(read(self.s,'owner',{'id':native['id']})['locator']['node'],'n')
 def test_reasoning_never_indexed(self):self.assertEqual(search(self.s,'owner',{'query':'hidden private marker'})['total'],0)
 def test_projection_requires_owner_authorized_task(self):
  t=self.s.put(request(object_new('TaskContract',{'goal':'synthetic','required_properties':[]},visibility='shared')),'owner')['object']
  with self.assertRaises(Fault):search(self.s,'codex',{'task_id':t['object_id'],'task_revision':1,'query':'Plus'})
 def test_incremental_refresh_does_not_duplicate(self):
  refresh(self.s);self.assertEqual(search(self.s,'owner',{'query':'Plus'})['total'],2)
 def test_native_revision_replaces_index_not_canonical_history(self):
  a=self.asset;a['payload']['sha256']=sha(b'{"records":[{"id":"n","content":"new phrase"}]}')
  self.s.put(request(a,1,blob=b'{"records":[{"id":"n","content":"new phrase"}]}'),'owner')
  self.assertEqual(search(self.s,'owner',{'query':'Plus','host':'codex'})['total'],0)
  self.assertEqual(self.s.get(a['object_id'],'owner',1)['payload']['sha256'],self.old_hash)
 def test_ascii_boundary_and_credential_redaction(self):
  self.assertFalse(matches('program project provide','Pro'));self.assertTrue(matches('Pro的费用','Pro'))
  self.assertEqual(public_text({'channel':'analysis','content':'secret'}),'')
 def test_host_event_available_outside_gpt_tables(self):
  event={'event_id':str(uuid.uuid4()),'source_host':'dsh','host_epoch':'synthetic-epoch','source_seq':1,'type':'observation','occurred_at':now(),'observed_at':now(),'schema_version':'1.0','visibility':'private','payload':{'native_session_id':'dsh-session','kind':'native_message','message':{'role':'user','content':'Plus DSH workflow'}}}
  self.s.host_event(event,'dsh');self.assertEqual(search(self.s,'owner',{'query':'Plus','host':'dsh'})['total'],1)
 def test_periodic_work_checkpoint_has_cooldown(self):
  from uacf.archive_trigger import decide
  f={'progress':True,'periodic_checkpoint':True}
  self.assertEqual(decide(f,{'last_capture_at':0},901)['action'],'prepare_incremental')
  self.assertNotEqual(decide(f,{'last_capture_at':0},100)['action'],'prepare_incremental')
 def test_mapped_host_checkpoint_cannot_forge_event(self):
  from uacf.learning_lifecycle import checkpoint
  task=self.s.put(request(object_new('TaskContract',{'goal':'synthetic checkpoint','required_properties':[]},visibility='shared')),'owner')['object']
  (self.root/'data/host-bindings.json').write_text(json.dumps({'codex':{'synthetic-session':task['object_id']}}))
  a=dict(task_id=task['object_id'],task_revision=1,host='codex',native_session_id='synthetic-session',native_event_id=str(uuid.uuid4()),signal='correction')
  with self.assertRaises(Fault):checkpoint(self.s,'codex',a)
  with self.assertRaises(Fault):checkpoint(self.s,'dsh',a)

if __name__=='__main__':unittest.main()
