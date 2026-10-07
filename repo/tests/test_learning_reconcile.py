import unittest,json
from uacf.learning_reconcile import disposition

class StructureTests(unittest.TestCase):
 def test_cross_job_duplicate_and_missing_are_source_bound(self):
  inp=dict(issues=[dict(case_ref=dict(object_id=x)) for x in ['a','b','c']],knowledge=[])
  row=dict(case_id='a',mechanism='conditions',relation='related_candidate',basis='source condition')
  raw=dict(choices=[dict(message=dict(content=json.dumps(dict(jobs=[dict(job_id='foreign',issues=[row,row,dict(case_id='b',mechanism='invalid',relation='unresolved',basis='invalid'),dict(case_id='foreign',mechanism='conditions',relation='unresolved',basis='foreign')])]))))])
  result=disposition(inp,raw)
  self.assertEqual([x['case_id'] for x in result['issues']],['a','b','c'])
  self.assertEqual(result['issues'][0]['mechanism'],'conditions')
  self.assertEqual(result['program_repair']['semantic_pending'],['b','c'])
  self.assertTrue(all(x['relation']=='unresolved' for x in result['issues'][1:]))
 def test_conflicting_classifications_not_chosen(self):
  inp=dict(issues=[dict(case_ref=dict(object_id='a'))],knowledge=[])
  rows=[dict(case_id='a',mechanism=m,relation='related_candidate',basis='different') for m in ['conditions','requirements']]
  raw=dict(choices=[dict(message=dict(content=json.dumps(dict(jobs=[dict(issues=rows)]))))])
  self.assertEqual(disposition(inp,raw)['program_repair']['semantic_pending'],['a'])
 def test_unparseable_keeps_every_candidate_pending(self):
  inp=dict(issues=[dict(case_ref=dict(object_id='a'))],knowledge=[dict(index=0,text='existing literal')])
  result=disposition(inp,{})
  self.assertEqual(result['knowledge'][0]['topics'],['existing literal'])
  self.assertEqual(result['program_repair']['semantic_pending'],['a'])

class EquivalenceTests(unittest.TestCase):
 def test_same_conditions_merge_but_exclusions_remain_independent(self):
  from uacf.learning_use import equivalent
  a={k:'explicit' for k in ['trigger','actual','expected','correction','applicable','excluded']}
  self.assertTrue(equivalent(a,dict(a)))
  self.assertFalse(equivalent(a,dict(a,excluded='different boundary')))
  self.assertFalse(equivalent(a,{'trigger':'explicit'}))
