"""Project/task view joins front controls to canonical assets and obligations."""
from .util import Fault,file_hash
import json
from pathlib import Path
from .fabric import projection,failure_obligations

def workspace(state,actor,args):
 view=projection(state,actor);objects=view['nodes'];byid={o['object_id']:o for o in objects};tid=args.get('task_id');task=byid.get(tid) if tid else None
 if tid and (not task or task['object_type']!='TaskContract'):raise Fault('NOT_FOUND','visible TaskContract required')
 roster=[{'id':o['object_id'],'revision':o['revision'],'provider':o['payload']['provider'],'model':o['payload']['model'],'host':o['payload']['host'],'capabilities':o['payload']['capabilities'],'verification':'declared_or_historical; current paid preflight still required'} for o in objects if o['object_type']=='ProviderProfile']
 tasks=[{'id':o['object_id'],'revision':o['revision'],'goal':o['payload'].get('goal',''),'project_id':o['payload'].get('project_id'),'status':o['status'],'stale':o.get('projection_stale',False),'execution_state':o['payload'].get('execution_state','unknown')} for o in objects if o['object_type']=='TaskContract']
 result={'ok':True,'commit_seq':view['commit_seq'],'authority_id':view['authority_id'],'projects':[o for o in objects if o['object_type']=='Project'],'tasks':tasks,'providers':roster,'affiliations':[o for o in objects if o['object_type']=='Affiliation'],'relations':[o for o in objects if o['object_type']=='Relation'],'edges':view['edges'],'selected_task':task,'paid_calls':0,'phase_routing':'interpreter/responder/reviewer RoleAssignment; stage-specific provider choice is a draft until explicitly recorded and validated','full_semantic_domain_map':'not inferred from titles'}
 result['affiliation_labels']={o['object_id']:o['payload'].get('purpose',o['payload'].get('name',o['object_type'])) for o in objects if any(a['payload'].get('asset_id')==o['object_id'] for a in result['affiliations'])}
 if task:
  closure=[];missing=[];queue=list(task['payload'].get('input_vector',[]));seen=set()
  while queue and len(seen)<256:
   ref=queue.pop(0);key=(ref['object_id'],ref['revision'])
   if key in seen:continue
   seen.add(key)
   try:o=state.get(ref['object_id'],actor,ref['revision'])
   except Fault as e:
    if e.code in ['NOT_FOUND','PERMISSION']:missing.append({'id':ref['object_id'],'reason':'not available in access domain'});continue
    raise
   head=byid.get(o['object_id']);closure.append({'object':o,'current_revision':(head or {}).get('revision'),'stale':not head or head['revision']!=o['revision'] or head.get('projection_stale',False)});queue+=o['payload'].get('input_vector',[])
  failure=failure_obligations(state,actor,task)
  results=[o for o in objects if o['object_type'] in ['Evidence','Validation','Attempt'] and (o['payload'].get('task_id',o['payload'].get('observation',{}).get('task_id'))==tid or o['object_id']==task['payload'].get('completion_evidence_id'))]
  contracts=[o for o in objects if o['object_type']=='ResponseContract' and o['payload'].get('task_id')==tid]
  trace=[]
  if actor in ['owner','dsh']:
   for evidence in results:
    obs=evidence['payload'].get('observation',{});raw=obs.get('source_locator')
    if not isinstance(raw,str) or obs.get('method')!='native_DSH_two_rounds_with_independent_stdout_comparison':continue
    path=Path(raw).resolve()
    if not path.is_relative_to((state.root/'logs').resolve()) or not path.is_file() or file_hash(path)!=obs.get('source_sha256'):continue
    saved=json.loads(path.read_text());checks={r['seq']:r for r in saved.get('independent_comparison',[])}
    calls=saved.get('calls',[]);returns=saved.get('tool_results',[])
    for call in calls:
     returned=next((r for r in returns if r['seq']==call['seq']+1),None)
     trace.append({'turn':call['turn'],'step':call['step'],'call_id':call['callId'],'tool':call['name'],'arguments':json.loads(call['arguments']),'call_seq':call['seq'],'return_seq':returned['seq'] if returned else None,'is_error':returned['isError'] if returned else None,'independent_stdout_match':checks.get((returned or {}).get('seq'),{}).get('exact_normalized_stdout_match'),'evidence_id':evidence['object_id'],'task_revision':obs['task_revision']})
  for entry in closure:
   if entry['object']['object_type']=='Message':
    o=entry['object'];entry['object']=dict(o,payload={k:v for k,v in o['payload'].items() if k in ['locator','source_id','source_kind','role','raw_hash','input_vector','branch','conversation_id']})
  context=state.context(actor,tid,32000);context={k:v for k,v in context.items() if k!='capsule'}
  result.update(source_closure=closure,source_bodies_included=False,missing_sources=missing,closure_limit=256,closure_remaining=bool(queue),failure_assessment=failure,results=results,response_contracts=contracts,context=context,execution_trace=trace,trace_scope='exact saved native calls/returns linked to hashed Evidence; not generic inferred workflow')
 return result
