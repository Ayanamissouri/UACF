"""Feed real old candidate copies through the same receiver in an isolated authority."""
import tempfile,json,copy
from pathlib import Path
from .state import State,init,object_new,request
from .fabric import vector
from .util import Fault,canonical,atomic,now

def run(state,args):
 from .learning import dispatch,folder,enqueue_card,receive
 from .learning_use import rebuild_issues
 from .learning_verify import identity
 selected=[]
 for case in state.list('owner','FailureCase'):
  p=case['payload'].get('case_details',{})
  if p.get('category')=='ai_execution' and all(k in p for k in ['trigger','actual','expected','correction','applicable','excluded']):selected.append(case)
  if len(selected)==2:break
 if not selected:raise Fault('NOT_PREPARED','source-backed old cases required')
 production_heads=[vector(x) for x in selected]
 checks=[]
 with tempfile.TemporaryDirectory(prefix='uacf-condition-probe-') as tmp:
  init(tmp);isolated=State(tmp);dispatch(isolated,'owner','learning_configure',{'authorization':'explicit current user request for isolated duplicate and independence refeeding; no model dispatch'})
  def source(original,label,changed=None):
   evidence=isolated.put(request(object_new('Evidence',dict(observation=dict(method='controlled reuse of an existing structured candidate; no raw-log replay',original_case=vector(original),original_authority=state.authority,label=label)))),'owner')['object']
   card=isolated.put(request(object_new('SemanticCard',dict(summary=label,evidence_map=[vector(evidence)],facets={},knowledge=[],semantic_contract='work-semantic-1',input_vector=[vector(evidence)]))),'owner')['object']
   candidate=copy.deepcopy(original['payload']['case_details'])
   if changed:candidate.update(changed)
   case=isolated.put(request(object_new('FailureCase',dict(properties=['learning_candidate_comparison'],lesson='controlled candidate copy',source={'grading':'controlled test, not a new historical AI error'},case_details=candidate,input_vector=[vector(card)]))),'owner')['object']
   ident=enqueue_card(isolated,card,'controlled_learning_probe');job=json.loads((folder(isolated)/'jobs'/(ident+'.json')).read_text())
   return card,case,job
  for original in selected:
   card,case,job=source(original,'baseline existing candidate')
   result=dict(issues=[dict(case_id=case['object_id'],mechanism='requirements',relation='related_candidate',basis='controlled existing candidate')],knowledge=[])
   receive(isolated,job,result);rebuild_issues(isolated)
   duplicate,dup,dupjob=source(original,'different source ID, identical old candidate')
   same=dict(issues=[dict(case_id=dup['object_id'],mechanism='requirements',relation='related_candidate',basis='same explicit conditions')],knowledge=[])
   done=receive(isolated,dupjob,same);review=isolated.get(done['result_ref']['object_id'],'owner')['payload']['assessment']['comparison_resolution'][0]
   checks.append(dict(test='real_candidate_different_source_duplicate',original_case=vector(original),baseline_case=vector(case),duplicate_case=vector(dup),pass_=case['object_id'] in [x['object_id'] for x in review['equivalent_candidates']],review=review))
   again=enqueue_card(isolated,duplicate,'controlled_learning_probe');checks.append(dict(test='same_source_enqueue_idempotent',pass_=again==dupjob['id']))
   altered,negative,negjob=source(original,'same words, changed exclusions',dict(excluded='Controlled negative: applicability differs from the baseline; retain independently'))
   proposed=dict(issues=[dict(case_id=negative['object_id'],mechanism='requirements',relation='related_candidate',basis='deliberately invalid merge proposal',merge_target_case_ref=vector(case))],knowledge=[])
   try:receive(isolated,negjob,proposed);blocked=False
   except Fault as error:blocked=error.code=='FALSE_MERGE'
   checks.append(dict(test='false_merge_proposal_rejected',pass_=blocked))
   proposed['issues'][0].pop('merge_target_case_ref');done=receive(isolated,negjob,proposed);review=isolated.get(done['result_ref']['object_id'],'owner')['payload']['assessment']['comparison_resolution'][0]
   checks.append(dict(test='different_exclusion_stays_independent',pass_=review['state']=='independent_conditions' and not review['equivalent_candidates'],review=review))
   checks.append(dict(test='mandatory_review_recorded',pass_=review['review']['passed'] and not review['review']['root_cause_equivalence']))
 result=dict(at=now(),checks=checks,result='pass' if all(x['pass_'] for x in checks) else 'fail',code_identity=identity(),real_old_candidates=len(selected),model_calls=0,raw_archive_reads=0,production_queue_unchanged=True,original_heads_unchanged=production_heads==[vector(state.get(x['object_id'],'owner')) for x in selected],scope='different source IDs in isolated State, same receiver and registry, exact repeat and changed-condition controls; paraphrase/root-cause recognition not proven')
 ev=state.put(request(object_new('Evidence',dict(observation=result))),'owner')['object'];result['evidence_ref']=vector(ev)
 atomic(folder(state)/'protocol-probe.json',canonical(result));return result
