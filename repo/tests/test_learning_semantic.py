import unittest,tempfile,json
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.learning import dispatch,folder
from uacf.learning_semantic import build,submit,overview,annotations
from uacf.learning_use import rebuild_issues
from uacf.fabric import vector
from uacf.util import atomic,canonical,Fault
class SemanticTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();init(self.tmp.name);self.s=State(self.tmp.name);dispatch(self.s,'owner','learning_configure',{'authorization':'fixture'})
  rows={}
  for actual in ['要求德语邮件，首答中文','用户要求德语但得到中文首答']:
   evidence=self.put('Evidence',{'observation':{'fixture':True}})
   card=self.put('SemanticCard',dict(summary='fixture',evidence_map=[vector(evidence)],facets={},knowledge=[],semantic_contract='work-semantic-1',input_vector=[vector(evidence)]))
   case=self.put('FailureCase',dict(properties=['learning_candidate_comparison'],lesson='fixture',source={'grading':'candidate'},case_details=dict(trigger='用户要求德语邮件',actual=actual,expected='输出德语邮件',correction='按指定语言输出',applicable='德语邮件',excluded='其他语言任务'),input_vector=[vector(card)]))
   attempt=self.put('LearningAttempt',dict(learner_actor='fixture',prompt_ref=vector(evidence),answer=vector(evidence),assessment={'issues':[]},error_owner='fixture',input_vector=[vector(card)]))
   rows[case['object_id']]=dict(case_ref=vector(case),card_ref=vector(card),attempt_ref=vector(attempt),candidate=case['payload']['case_details'])
  atomic(folder(self.s)/'issue-index.json',canonical(rows));build(self.s)
 def tearDown(self):self.tmp.cleanup()
 def put(self,k,p):return self.s.put(request(object_new(k,p)),'owner')['object']
 def item(self):
  pair=overview(self.s,{'limit':1})['rows'][0]
  return dict(pair_id=pair['pair_id'],verdict='equivalent_conditions',principle='明确德语要求不得以中文首答',basis='两例明确相同语言合同，中文首答不满足德语输出',condition_comparison='相同德语邮件条件，排除其他语言任务；保留来源',reviewer_locator='controlled fixture reviewer, not a model turn')
 def test_retrieval_never_counts_as_review(self):
  v=overview(self.s,{});self.assertEqual(v['reviewed_pairs'],0);self.assertFalse(v['all_900_semantic_review_complete']);self.assertEqual(v['unreviewed_cases'],2)
 def test_review_keeps_sources_and_links_shared_principle(self):
  r=submit(self.s,{'items':[self.item()]});v=overview(self.s,{})
  self.assertEqual(v['verdict_counts'],{'equivalent_conditions':1});self.assertEqual(v['reviewed_cases'],2);self.assertEqual(len(annotations(self.s)),2)
  self.assertTrue(all(x['revision']==1 for x in self.s.list('owner','FailureCase')));self.assertTrue(all(not x['payload'].get('hard_rule_adopted') for x in self.s.list('owner','FailurePattern')))
 def test_stale_review_rejected(self):
  item=self.item();p=overview(self.s,{'limit':1})['rows'][0];case=self.s.get(p['left_ref']['object_id'],'owner');case['payload']['case_details']['excluded']='new exclusion';self.s.put(request(case,1),'owner')
  with self.assertRaises(Fault):submit(self.s,{'items':[item]})
 def test_corrupted_cache_is_not_semantic_evidence(self):
  submit(self.s,{'items':[self.item()]});p=folder(self.s)/'semantic/reviews.json';data=json.loads(p.read_text());next(iter(data.values()))['review']['verdict']='independent';atomic(p,canonical(data))
  with self.assertRaises(Fault):annotations(self.s)
 def test_nonowner_cannot_review_or_inspect(self):
  with self.assertRaises(Fault):dispatch(self.s,'reader','learning_semantic_submit',{'items':[self.item()]})
  with self.assertRaises(Fault):dispatch(self.s,'reader','learning_inspect',{})
