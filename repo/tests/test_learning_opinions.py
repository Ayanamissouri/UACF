import unittest,tempfile
from pathlib import Path
from uacf.state import State,init
from uacf.learning_opinions import opinions
from uacf.util import Fault
class OpinionTests(unittest.TestCase):
 def test_empty_store_has_no_inherited900_or_principles(self):
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));r=opinions(State(Path(d)),'owner',{});self.assertEqual(r['total_principles'],0);self.assertEqual(r['counts']['knowledge_candidates'],0);self.assertEqual(r['counts']['issue_instances'],0);self.assertEqual(r['rows'],[])
 def test_host_cannot_read_owner_private_opinions(self):
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));self.assertRaises(Fault,opinions,State(Path(d)),'codex',{})
 def test_bounded_pages(self):
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));self.assertRaises(Fault,opinions,State(Path(d)),'owner',{'limit':1000})
