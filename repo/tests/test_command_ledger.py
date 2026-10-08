import unittest,tempfile
from pathlib import Path
from uacf.state import init,State,object_new,request
from uacf.command_ledger import update,summary,capsule,delivery
from uacf.retry_guard import dispatch,check
from uacf.util import Fault
class CommandLedgerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);init(self.root);self.s=State(self.root)
  self.msg=self.put('Message',{'role':'user','source_kind':'direct_user','current':True,'branch':'main','text':'请写中文手册，也写完整英文手册；德语，不，改为英文。先读旧版本。'})
  self.task=self.put('TaskContract',{'goal':'synthetic instruction continuity','required_properties':[]})
 def tearDown(self):self.temp.cleanup()
 def put(self,k,p):return self.s.put(request(object_new(k,p)),'owner')['object']
 def entry(self,key,text='写中文手册',**kwargs):return dict(key=key,text=text,source_ref={'object_id':self.msg['object_id'],'revision':1},source_quote='请写中文手册',interpretation_basis='current-host interpretation of explicit synthetic user directive',explicit_attestation=True,**kwargs)
 def append(self,entries):
  r=update(self.s,'owner',{'task_id':self.task['object_id'],'expected_revision':self.task['revision'],'entries':entries});self.task=self.s.get(self.task['object_id'],'owner');return r
 def test_supplement_preserves_original_after_reprepare(self):
  self.append([self.entry('chinese')]);self.append([self.entry('english','完整英文手册')]);c=self.s.context('owner',self.task['object_id']);self.assertEqual(c['status'],'ready');self.assertEqual([x['key'] for x in c['capsule']['mandatory_command_lane']],['chinese','english']);self.assertEqual(len(summary(self.s,'owner',{'task_id':self.task['object_id']})['entries']),2)
 def test_history_and_ai_quote_cannot_authorize(self):
  for source in [dict(role='user',source_kind='direct_user',current=False,branch='main',text='请写中文手册'),dict(role='assistant',source_kind='assistant',current=True,branch='main',text='请写中文手册')]:
   m=self.put('Message',source);e=self.entry('bad');e['source_ref']={'object_id':m['object_id'],'revision':1}
   with self.assertRaisesRegex(Fault,'historical'):self.append([e])
 def test_explicit_correction_required_and_prior_text_retained(self):
  self.append([self.entry('language')])
  with self.assertRaisesRegex(Fault,'explicit correction'):self.append([self.entry('language','改为英文')])
  self.append([self.entry('language','改为英文',kind='correction')]);self.assertEqual(self.task['payload']['command_ledger'][0]['previous_text'],'写中文手册')
 def test_repetition_and_ambiguity_do_not_become_extra_actions(self):
  self.append([self.entry('a')]);self.append([self.entry('duplicate',kind='duplicate',duplicate_of='a'),self.entry('unclear',kind='ambiguous',state='unresolved')]);self.assertEqual(sum(x['actionable'] for x in capsule(self.task)),1)
 def test_self_report_cannot_close_or_deliver(self):
  with self.assertRaisesRegex(Fault,'evidence'):self.append([self.entry('a',state='satisfied')])
  self.append([self.entry('a')]);self.assertRaises(Fault,delivery,self.task)
 def test_stale_revision_and_missing_source_basis_rejected(self):
  self.append([self.entry('a')])
  with self.assertRaises(Fault):update(self.s,'owner',{'task_id':self.task['object_id'],'expected_revision':1,'entries':[self.entry('b')]})
  e=self.entry('b');e['source_quote']='用户从没说过的内容';self.assertRaises(Fault,self.append,[e])
 def test_repeat_guard_is_real_and_reprepare_reads_structure(self):
  p=self.root/'structure.md';p.write_text('Synthetic architecture: verify original conditions',encoding='utf-8');self.task['payload']['retry_guard']={'enabled':True,'max_same_experiment':2,'read_paths':[str(p)]};self.task=self.s.put(request(self.task,self.task['revision']),'owner')['object']
  def act(name,**extra):
   r=dispatch(self.s,'owner',name,dict(task_id=self.task['object_id'],expected_revision=self.task['revision'],**extra));self.task=self.s.get(self.task['object_id'],'owner');return r
  self.assertTrue(act('guard_probe',path=str(p),description='one')['allowed']);self.assertTrue(act('guard_probe',path=str(p),description='two')['allowed']);self.assertFalse(act('guard_probe',path=str(p),description='three')['allowed']);self.assertRaises(Fault,check,self.task)
  r=act('guard_reprepare',correction_basis='check structure before changing hypothesis');self.assertIn('Synthetic architecture',r['structures'][0]['text']);self.assertFalse(self.task['payload']['retry_guard']['blocked']);self.assertTrue(act('guard_probe',path=str(p))['allowed']);self.assertEqual(r['new_model_calls'],0)
