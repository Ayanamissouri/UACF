import unittest,io,json
from uacf.archive import conversations,resolve,safe_member
from uacf.util import Fault

class ArchiveContracts(unittest.TestCase):
 def test_stream_preserves_conversations_and_unicode(self):
  source=[{'id':'a','mapping':{'n':{'message':{'content':'中'*90000}}}},{'id':'b','mapping':{}}]
  rows=list(conversations(io.BytesIO(json.dumps(source,ensure_ascii=False).encode()),1000000))
  self.assertEqual([r[1] for r in rows],source)
 def test_stream_refuses_corruption_and_quota(self):
  for source in [b'[{} {}]',b'[{},]',b'[{}] junk',b'[{}',b'{}']:
   with self.subTest(source=source),self.assertRaises(Fault):list(conversations(io.BytesIO(source),1000))
  with self.assertRaises(Fault):list(conversations(io.BytesIO(json.dumps([{'x':'z'*10000}]).encode()),100))
 def test_exact_mapping_never_guesses_name(self):
  assets={'file-real.dat':{'state':'registered'},'file-real':{'state':'registered'},'file-other.dat':{'state':'duplicate'}}
  self.assertEqual(resolve('sediment://file-real',assets)['status'],'ambiguous')
  self.assertEqual(resolve('file-rea',assets)['status'],'missing')
  self.assertEqual(resolve('file-other',assets)['status'],'missing')
  self.assertEqual(resolve('sediment://file-real',{'file-real.dat':{'state':'registered'}})['members'],['file-real.dat'])
 def test_unsafe_names_and_excluded_inputs(self):
  for name in ['../x','/root','C:/x','a\\b','API.txt','pika/a','学长/a']:
   self.assertFalse(safe_member(name))
  self.assertTrue(safe_member('file-real.dat'))

if __name__=='__main__':unittest.main()
