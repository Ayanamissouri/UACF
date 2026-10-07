"""Mandatory structural equivalence review; never equate family with root cause."""
from .util import sha,Fault
from .learning_use import equivalent,issue_index

KEYS=['trigger','actual','expected','correction','applicable','excluded']
def review(state,inp,issues):
 registry=issue_index(state);result=[]
 for item in inp['issues']:
  candidate=item['candidate'];ident=item['case_ref']['object_id'];matches=[];independent=[]
  for old in registry.values():
   if old['case_ref']['object_id']==ident or old['card_ref']==inp['card_ref']:continue
   possible=equivalent(candidate,old['candidate']) or all(candidate.get(k)==old['candidate'].get(k) and candidate.get(k) is not None for k in ['trigger','actual','expected'])
   if not possible:continue
   from .fabric import vector
   canonical_case=state.get(old['case_ref']['object_id'],'owner')
   if vector(canonical_case)!=old['case_ref'] or {k:v for k,v in canonical_case['payload'].get('case_details',{}).items() if k!='refs'}!=old['candidate']:continue
   if equivalent(candidate,old['candidate']):matches.append(old['case_ref'])
   elif all(candidate.get(k)==old['candidate'].get(k) and candidate.get(k) is not None for k in ['trigger','actual','expected']):
    independent.append(dict(case_ref=old['case_ref'],different_fields=[k for k in KEYS if candidate.get(k)!=old['candidate'].get(k)]))
  proposed=next(x for x in issues if x['case_id']==ident).get('merge_target_case_ref')
  if proposed and proposed not in matches:raise Fault('FALSE_MERGE','merge target must have identical explicit behavior, correction and applicability/exclusions; same family or similar wording is insufficient')
  complete=all(k in candidate and candidate[k] is not None for k in KEYS)
  result.append(dict(case_ref=item['case_ref'],state='equivalent_existing_candidate' if matches else 'independent_conditions' if independent else 'unresolved_incomplete_conditions' if not complete else 'no_exact_match_not_proof_of_novelty',equivalent_candidates=matches,independence_candidates=independent[:3],review=dict(method='registered exact behavior and condition equivalence, freshness checked',passed=True,root_cause_equivalence=False,semantic_truth_accepted=False)))
 return result
