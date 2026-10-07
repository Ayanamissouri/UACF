import unittest
from uacf.e7_library import library
from uacf.util import Fault
class FakeState:
 def list(self,actor,kind):
  if actor=='reader':return []
  return [{'object_id':'one','revision':1,'payload':{'semantic_contract':'e7-semantic-1','catalog_title':'德语翻译','summary':'继承目标语言','facets':{'candidate_labels':['机械'],'independent_review':'pending'},'coverage':{}}},{'object_id':'old','payload':{}}]
class E7LibraryTest(unittest.TestCase):
 def test_access_domain_and_candidate_state(self):
  self.assertEqual(library(FakeState(),'reader',{})['total_candidate_cards'],0)
  x=library(FakeState(),'owner',{'query':'目标语言'});self.assertEqual(x['shown'],1);self.assertFalse(x['whole_E7_acceptance']);self.assertEqual(x['independent_accepted'],0)
 def test_negative_query_and_bounded_mode(self):
  self.assertEqual(library(FakeState(),'owner',{'query':'热力学'})['shown'],0)
  with self.assertRaises(Fault):library(FakeState(),'owner',{'query':'x'*201})
  with self.assertRaises(Fault):library(FakeState(),'owner',{'mode':'write'})
