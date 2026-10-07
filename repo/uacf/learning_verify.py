"""Registered verifier for the shared learning chain; never executes candidate text."""
import json,collections
from pathlib import Path
from .util import sha,canonical,file_hash,Fault,now,atomic
from .state import object_new,request
from .fabric import vector
def identity():
 root=Path(__file__).resolve().parents[1]
 return {p:file_hash(root/p) for p in ['uacf/learning.py','uacf/learning_use.py','uacf/learning_resolution.py','uacf/learning_semantic.py','uacf/learning_inspect.py','uacf/learning_probe.py','uacf/learning_reconcile.py','uacf/learning_verify.py','uacf/learning_guards.py','uacf/project_workflow.py','uacf/artifact_capture.py','ops/learning_worker.py']}
def register(state,policy):
 from .learning import save_once,folder,MECHANISMS
 from .learning_guards import CONTRACTS,fixture_checks
 checks=fixture_checks()
 if not all(checks.values()):raise Fault('VALIDATION_REQUIRED','registered negative/positive guard tests failed')
 hashes=identity();ev=save_once(state,'Evidence',dict(observation=dict(method='loaded registered guard positive/negative fixture execution',checks=checks,loaded_files=hashes,scope=CONTRACTS),input_vector=[policy['ref']]),['guard-fixture',hashes])
 patterns=[]
 for key,contract in CONTRACTS.items():
  pattern=save_once(state,'FailurePattern',dict(properties=[contract['property']],lesson=key,source=dict(grading='registered executable guard; finite mechanical scope only'),applicability={},guard_contract=contract,code_identity=hashes,semantic_acceptance=False,input_vector=[vector(ev)]),['registered-guard',key,hashes]);patterns.append(vector(pattern))
 decision=save_once(state,'Decision',dict(outcome='activate registered mechanical guards only',basis='Current user requested hard enforcement; loaded registered positive/negative checks passed',rules=patterns,scope=CONTRACTS,input_vector=[vector(ev),policy['ref']]),['guard-decision',hashes])
 for old in state.list('owner','FailurePattern'):
  family=old['payload'].get('mechanism')
  if family in MECHANISMS and old['payload'].get('registered_guard')!=MECHANISMS[family][1]:
   old['payload']['registered_guard']=MECHANISMS[family][1]
   old=state.put(request(old,old['revision']),'owner')['object']
  if old['payload'].get('guard_contract') and old['payload'].get('code_identity')!=hashes and old['status']!='superseded':
   old['status']='superseded';state.put(request(old,old['revision']),'owner')
  name=old['payload'].get('registered_guard')
  if name:
   for ref in patterns:
    guard=state.get(ref['object_id'],'owner')
    if guard['payload']['lesson']==name:save_once(state,'Relation',dict(source_id=old['object_id'],target_id=guard['object_id'],kind='qualifies',basis='Family linkage to current registered mechanical guard scope; historical candidate is not thereby accepted'),['guard-family',old['object_id'],ref])
 result=dict(ok=True,checks=checks,code_identity=hashes,pattern_refs=patterns,decision_ref=vector(decision),evidence_ref=vector(ev));atomic(folder(state)/'guards.json',canonical(result));return result
def verify(state,policy,args):
 from .learning import folder,status,save_once,candidate_input,comparison_snapshot
 from .learning_guards import fixture_checks
 jobs=[json.loads(f.read_text()) for f in (folder(state)/'jobs').glob('*.json')]
 task=state.get(args.get('task_id',policy['task_ref']['object_id']),'owner')
 if args.get('task_revision',task['revision'])!=task['revision']:raise Fault('REVISION_CONFLICT','learning Task changed')
 acceptance=task['payload'].get('learning_acceptance',{})
 baseline=acceptance.get('baseline_count',0);added=acceptance.get('new_count',0)
 expected=args.get('expected',baseline+added)
 if type(expected)!=int or expected<0 or expected>100000:raise Fault('INPUT','nonnegative actual frozen source count required')
 refs=acceptance.get('source_refs')
 if refs is not None and (len(refs)!=expected or expected!=baseline+added):raise Fault('INPUT','frozen source refs must match baseline plus new count')
 selected={x['object_id'] for x in refs} if refs is not None else None
 done=[j for j in jobs if j['source_kind']!='native_work' and j['state']=='compared' and (selected is None or j.get('card_ref',{}).get('object_id') in selected)]
 original={x['object_id']:x['revision'] for x in refs} if refs is not None else {j['card_ref']['object_id']:state.get(j['card_ref']['object_id'],'owner')['revision'] for j in done}
 guards=folder(state)/'guards.json';registered=json.loads(guards.read_text()) if guards.exists() else None
 probe=folder(state)/'protocol-probe.json';protocol=json.loads(probe.read_text()) if probe.exists() else {}
 checks=dict(comparison_protocol=protocol.get('result')=='pass' and protocol.get('code_identity')==identity(),registered_identity=bool(registered and registered['code_identity']==identity()),guard_fixtures=all(fixture_checks().values()),source_count=len(done)==expected,unique_sources=len({j['card_ref']['object_id'] for j in done})==expected,known_results=True,complete_candidate_coverage=True,canonical_source_revisions=True)
 knowledge=issues=pending=repairs=0;receipts={};relations=collections.Counter();mechanisms=collections.Counter()
 snapshot=comparison_snapshot(state)
 for j in done:
  inp=candidate_input(state,j,snapshot);attempt=state.get(j['result_ref']['object_id'],'owner');assessment=attempt['payload']['assessment'];knowledge+=len(assessment['knowledge']);issues+=len(assessment['issues'])
  pending+=len(assessment.get('program_repair',{}).get('semantic_pending',[]));repairs+=int('program_repair' in assessment)
  checks['canonical_source_revisions'] &= original.get(j['card_ref']['object_id'])==j['card_ref']['revision']
  checks['complete_candidate_coverage'] &= len(assessment['knowledge'])==len(inp['knowledge']) and {x['case_id'] for x in assessment['issues']}=={x['case_ref']['object_id'] for x in inp['issues']}
  path=folder(state)/'receipts'/(j['id']+'.json');r=json.loads(path.read_text()) if path.exists() else {};checks['known_results'] &= r.get('state') in ['settled','host_completed']
  if r.get('state')=='settled':receipts[r['reservation_id']]=r
  for x in assessment['issues']:relations[x['relation']]+=1;mechanisms[x['mechanism']]+=1
 checks['no_unknown_or_dispatched']=not any(j['state']=='dispatched' for j in jobs) and not any(json.loads(f.read_text()).get('state') in ['unknown','reserved','response_known'] for f in (folder(state)/'receipts').glob('*.json'))
 stats=dict(program_repaired_sources=repairs,program_semantic_pending_cases=pending,sources=len(done),knowledge=knowledge,issues=issues,relations=dict(relations),candidate_mechanisms=dict(mechanisms),requests=len(receipts),peak_CNY=sum(r['peak_micro'] for r in receipts.values())/1e6,offpeak_CNY=sum(r['offpeak_CNY'] for r in receipts.values()))
 ev=state.put(request(object_new('Evidence',dict(observation=dict(method='registered canonical queue coverage and receipt readback',checks=checks,statistics=stats,code_identity=identity(),expected=expected,semantic_truth_verified=False),input_vector=[policy['ref']]))),'owner')['object']
 result=dict(ok=True,result='pass' if all(checks.values()) else 'fail',checks=checks,statistics=stats,evidence_ref=vector(ev),environment_hash=sha(dict(identity=identity(),policy=policy['ref'],expected=expected,results=[j['result_ref'] for j in sorted(done,key=lambda j:j['id'])])))
 # Only explicitly frozen mechanical properties may receive machine Validation.
 # Semantic application and normal lifecycle completion require separate evidence.
 if refs is not None:
  result['validations']=[]
  for prop in acceptance.get('machine_properties',[]):
   if prop not in ['learning_source_coverage','learning_classifier_receipts','learning_registered_guards'] or prop not in task['payload']['required_properties']:raise Fault('INPUT','explicit registered mechanical property required')
   val=object_new('Validation',dict(task_id=task['object_id'],task_revision=task['revision'],property=prop,result=result['result'],environment_hash=result['environment_hash'],method='Registered shared learner mechanical coverage/receipt/guard verifier',evidence_id=ev['object_id'],input_vector=[vector(task),vector(ev)],execution_status='ran',coverage=[prop],expiry='source, policy, queue or loaded-code identity changes'))
   result['validations'].append(vector(state.put(request(val),'owner',internal=True)['object']))
 atomic(folder(state)/('slice-'+str(expected)+'.json'),canonical(dict(at=now(),**result,status=status(state))));return result
