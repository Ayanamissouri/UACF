import tempfile,unittest
from pathlib import Path
from uacf.state import init,State,object_new,request
from uacf.archive import migrate4
from uacf.observatory import observe
from uacf.util import canonical,now

class ObservatoryACLAndIncrement(unittest.TestCase):
 def test_private_archive_and_archive_only_refresh(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);init(root);s=State(root)
   # An isolated fixture checks read ACL and cursor semantics, not real archive acceptance.
   with s.db() as c:
    for name in ['002.sql','003.sql','004-archive.sql']:c.executescript((Path(__file__).resolve().parents[1]/'contracts/migrations'/name).read_text())
   source=object_new('Project',{'name':'private fixture','contracts':{}},visibility='private');s.put(request(source),'owner')
   with s.db() as c:
    c.execute('insert into archive_plans values(?,?,?,?,?)',('fixture',source['object_id'],'batch4-1',canonical({}),now()))
    c.execute('insert into archive_progress values(?,?,?,?,?)',('fixture','one',0,'partial','{}'))
    c.execute('insert into archive_conversations values(?,?,?,?,?,?,?)',('fixture','one',0,'id','private 标题','hash','{}'))
   reader=observe(s,'codex',{});self.assertEqual(reader['counts']['matching_conversations'],0)
   first=observe(s,'owner',{});self.assertEqual(first['counts']['matching_conversations'],1)
   self.assertTrue(observe(s,'owner',{'after_cursor':first['cursor']})['unchanged'])
   with s.db() as c:c.execute('update archive_progress set cursor=1')
   self.assertFalse(observe(s,'owner',{'after_cursor':first['cursor']})['unchanged'])
   self.assertEqual(first['assets'][0]['domain_judgment'],'unknown')
   self.assertFalse(observe(s,'owner',{'after_cursor':first['cursor'],'query':'absent'})['unchanged'])

if __name__=='__main__':unittest.main()
