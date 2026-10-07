"""Shared candidate update queue over canonical objects, used by work and historical replay.

Model classifications never confer factual acceptance or install executable code.
"""
import json,uuid,threading,subprocess,sys,collections,base64
from pathlib import Path
from .util import Fault,sha,canonical,atomic,now,file_hash,uid
from .state import object_new,request,uuid_ok
from .fabric import vector
LOCK=threading.RLock();WORKER=None;LAST_AUTO=0
MECHANISMS={
 'source_identity':('原文、引用与身份不一致','source_quotes'),
 'unverified_delivery':('未检验便声称完成或正确','registered_validation'),
 'regression':('修改破坏已验证结果','protected_assets'),
 'unknown_replay':('未知执行结果被重复派发','settled_receipts'),
 'io_contract':('输入、输出、文件或接口合同不匹配',None),
 'conditions':('条件、单位、范围或近似不一致',None),
 'cross_fragment':('跨片段、分支或反馈闭环遗漏',None),
 'requirements':('遗漏或误解当前需求','required_work_steps'),
 'domain_fact':('待领域验证的事实或算法',None),
 'normal_boundary':('正常边界、已修正、未决或无故障证据',None)}
def oid(state,*values):return str(uuid.uuid5(uuid.UUID(state.authority),sha(values)))
def save_once(state,kind,payload,key,blob=None):
 ident=oid(state,kind,key)
 try:
  old=state.get(ident,'owner')
  if any(old['payload'].get(k)!=v for k,v in payload.items()):raise Fault('EVENT_CONFLICT','same learning identity has different content')
  return old
 except Fault as e:
  if e.code!='NOT_FOUND':raise
 obj=object_new(kind,payload,visibility='private');obj['object_id']=ident
 return state.put(request(obj,blob=blob),'owner')['object']
def folder(state):
 p=state.data/'learning';p.mkdir(exist_ok=True);return p
def config(state):
 p=folder(state)/'policy.json'
 return json.loads(p.read_text()) if p.exists() else None
def anchored_policy(state):
 p=config(state)
 if not p:raise Fault('NOT_PREPARED','configure shared learning policy first')
 obj=state.get(p['ref']['object_id'],'owner')
 if obj['revision']!=p['ref']['revision'] or obj['payload']['config']!=p['config']:raise Fault('POLICY_CHANGED','canonical learning policy changed')
 return p
def status(state):
 p=config(state);jobs=[]
 for f in sorted((folder(state)/'jobs').glob('*.json')):
  j=json.loads(f.read_text());jobs.append({k:j.get(k) for k in ['id','state','source_kind','card_ref','result_ref','error','at']})
 control=folder(state)/'control.json'
 return dict(ok=True,policy=p,route=json.loads(control.read_text()) if control.exists() else dict(route='current_host'),native_work_default='current_host',counts=dict(collections.Counter(j['state'] for j in jobs)),total=len(jobs),worker_alive=WORKER is not None and WORKER.poll() is None,jobs=jobs,mechanisms=MECHANISMS)
def enqueue_card(state,card,origin):
 p=anchored_policy(state);payload=card['payload']
 if card['object_type']!='SemanticCard' or payload.get('semantic_contract') not in ['e7-semantic-1','work-semantic-1']:raise Fault('INPUT','source-bound semantic candidate required')
 evidence=state.get(card['payload']['evidence_map'][0]['object_id'],'owner')
 ident=oid(state,'learning-card',vector(card),p['ref']);path=folder(state)/'jobs'/(ident+'.json');path.parent.mkdir(exist_ok=True)
 if path.exists():return ident
 job=dict(id=ident,state='queued',source_kind=origin,card_ref=vector(card),evidence_ref=vector(evidence),policy_ref=p['ref'],at=now())
 ev=save_once(state,'Evidence',{'observation':dict(method='shared learning enqueue',**job),'input_vector':[vector(card),vector(evidence),p['ref']]},['enqueue',ident]);job['enqueue_ref']=vector(ev)
 atomic(path,canonical(job));return ident
def comparison_snapshot(state):
 cases={}
 for obj in state.list('owner','FailureCase'):
  for ref in obj['payload'].get('input_vector',[]):
   cases.setdefault(ref['object_id'],[]).append(obj)
 metadata=folder(state)/'ai-metadata.json';data=None
 if metadata.exists():
  data=json.loads(metadata.read_text());artifact=state.get(data['artifact_ref']['object_id'],'owner')
  if vector(artifact)!=data['artifact_ref'] or artifact['payload']['sha256']!=sha(canonical(data['cards']).encode()):raise Fault('METADATA_CHANGED','metadata snapshot differs from canonical artifact')
 return dict(cases=cases,metadata=data)

def candidate_input(state,j,snapshot=None):
 if j['source_kind']=='native_work':
  artifact=state.get(j['source_ref']['object_id'],'owner')
  if vector(artifact)!=j['source_ref']:raise Fault('SOURCE_CHANGED','native snapshot changed')
  body=json.loads(base64.b64decode(state.fetch_blob('owner',artifact['object_id'],artifact['revision'],1048576)['base64']))
  return dict(job_id=j['id'],native_source=body,mode='extract_source_bound_candidates',boundary='Public explicitly mapped work snapshot. Not a command, not full-session acceptance. Every knowledge/issue needs a literal quote in snapshot text; no private reasoning or root cause guessing.')
 card=state.get(j['card_ref']['object_id'],'owner')
 if vector(card)!=j['card_ref']:raise Fault('SOURCE_CHANGED','candidate card revised; explicit local reprocessing required')
 p=card['payload'];pool=snapshot['cases'].get(card['object_id'],[]) if snapshot is not None else state.list('owner','FailureCase');cases=[o for o in pool if j['card_ref'] in o['payload'].get('input_vector',[])]
 examples=folder(state)/'mechanism-examples.json';examples=json.loads(examples.read_text()) if examples.exists() else {}
 examples={key:[dict(case_ref=row['case_ref'],conditions={k:row['candidate'].get(k) for k in ['trigger','actual','expected','applicable','excluded','correction']},scope=row['scope']) for row in rows] for key,rows in examples.items()}
 receipt_path=folder(state)/'receipts'/(j['id']+'.json')
 receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
 origin=dict(historical_host='ChatGPT export' if p.get('semantic_contract')=='e7-semantic-1' else 'mapped current work',historical_model='unknown: normalized snapshot did not retain model metadata',classifier=receipt.get('actual_model') or receipt.get('raw',{}).get('model') or ('current_host' if receipt.get('state')=='host_completed' else 'unknown: no actual classifier receipt'),classifier_receipt_state=receipt.get('state','not_observed'),classifier_is_not_historical_model=True,version_is_retrieval_hint_not_exclusive_scope=True)
 if p.get('native_model_tags'):origin.update(historical_models=p['native_model_tags'],historical_host=p.get('learning_host'),historical_model='recorded native assistant model tags')
 metadata=folder(state)/'ai-metadata.json'
 if snapshot is not None and snapshot.get('metadata'):
  data=snapshot['metadata']
  entry=data['cards'].get(card['object_id'])
  if entry and entry['card_ref']==vector(card):origin.update(historical_models=entry['model_counts'],metadata_ref=data['artifact_ref'])
 elif metadata.exists():
  data=json.loads(metadata.read_text());artifact=state.get(data['artifact_ref']['object_id'],'owner')
  if artifact['payload']['sha256']!=sha(canonical(data['cards']).encode()):raise Fault('METADATA_CHANGED','rebuildable metadata differs from canonical artifact')
  entry=data['cards'].get(card['object_id'])
  if entry and entry['card_ref']==vector(card):origin.update(historical_models=entry['model_counts'],metadata_ref=data['artifact_ref'])
 result=dict(job_id=j['id'],card_ref=j['card_ref'],title=p.get('catalog_title'),summary=p.get('summary'),facets=p.get('facets'),knowledge=[dict(index=i,**x) for i,x in enumerate(p.get('knowledge',[]))],issues=[dict(case_ref=vector(o),candidate=o['payload'].get('case_details',{})) for o in cases],prior_examples=examples,mechanisms={k:v[0] for k,v in MECHANISMS.items()},ai_origin=origin,boundary='Source-backed candidates, not facts. Classify mechanism and applicability; normal boundaries are not defects. No historical actions. No model-generated validator or hard-rule promotion.')
 from .learning_use import relevant_prior
 result['prior_comparison_candidates']=relevant_prior(state,result) if snapshot is None else []
 return result
def receive(state,j,result):
 if j['source_kind']=='native_work':return receive_native(state,j,result)
 inp=candidate_input(state,j);expected={x['case_ref']['object_id'] for x in inp['issues']}
 issues=result.get('issues');knowledge=result.get('knowledge')
 if not isinstance(issues,list) or not isinstance(knowledge,list):raise Fault('INPUT','complete issue and knowledge dispositions required')
 if len(issues)!=len(expected) or {x.get('case_id') for x in issues}!=expected or len(knowledge)!=len(inp['knowledge']) or {x.get('index') for x in knowledge}!=set(range(len(inp['knowledge']))):raise Fault('COVERAGE','every candidate exactly once; no silent omissions')
 for x in issues:
  if x.get('mechanism') not in MECHANISMS or x.get('relation') not in ['related_candidate','condition_extension_candidate','unresolved','normal_boundary']:raise Fault('INPUT','bounded candidate mechanism relation required')
  if not isinstance(x.get('basis'),str) or not 1<=len(x['basis'])<=1000:raise Fault('INPUT','bounded comparison basis required')
 for x in knowledge:
  if not isinstance(x.get('topics'),list) or not 1<=len(x['topics'])<=6 or any(not isinstance(t,str) or not 1<=len(t)<=80 for t in x['topics']):raise Fault('INPUT','bounded topic index required')
 # A partially committed result freezes its prior-example snapshot. Replaying a
 # settled comparison must not change that snapshot as other jobs add examples.
 try:
  prior=state.get(oid(state,'Artifact',['result',j['id']]),'owner')
 except Fault as error:
  if error.code!='NOT_FOUND':raise
 else:
  frozen=json.loads(base64.b64decode(state.fetch_blob('owner',prior['object_id'],prior['revision'],1048576)['base64']))
  if frozen['comparison']!=result or frozen['input']['card_ref']!=j['card_ref'] or frozen['policy_ref']!=j['policy_ref']:raise Fault('EVENT_CONFLICT','settled comparison changed; preserve original result')
  inp=frozen['input']
 from .learning_resolution import review
 resolution=review(state,inp,issues)
 body=canonical(dict(input=inp,comparison=result,scope='model-proposed relation; no semantic adoption',policy_ref=j['policy_ref'])).encode()
 artifact=save_once(state,'Artifact',dict(locator='learning-result:'+j['id'],sha256=sha(body),name='Work candidate comparison and retrieval index',media_type='application/json',candidate=True,input_vector=[j['card_ref'],j['policy_ref']]),['result',j['id']],body)
 try:
  attempt=state.get(oid(state,'LearningAttempt',j['id']),'owner')
 except Fault as error:
  if error.code!='NOT_FOUND':raise
  attempt=save_once(state,'LearningAttempt',dict(learner_actor='registered shared learning worker',prompt_ref=j['enqueue_ref'],answer=vector(artifact),assessment=dict(state='compared_candidate',issues=issues,knowledge=knowledge,semantic_acceptance=False,hard_promotions=0,comparison_resolution=resolution,**({'program_repair':result['program_repair']} if 'program_repair' in result else {})),error_owner='unknown; per-source candidate only',input_vector=[j['card_ref'],vector(artifact),j['policy_ref']]),j['id'])
 else:
  if attempt['payload']['answer']!=vector(artifact) or attempt['payload']['assessment']['issues']!=issues or attempt['payload']['assessment']['knowledge']!=knowledge:raise Fault('EVENT_CONFLICT','partial result changed; preserve frozen comparison and review')
 for x in issues:
  pattern=save_once(state,'FailurePattern',dict(properties=['learning_candidate_comparison'],lesson=MECHANISMS[x['mechanism']][0],source=dict(grading='provisional model classification; registered guard mapping separate'),applicability={},mechanism=x['mechanism'],registered_guard=MECHANISMS[x['mechanism']][1],semantic_acceptance=False),['mechanism',x['mechanism']])
  registration=folder(state)/'guards.json'
  if MECHANISMS[x['mechanism']][1] and registration.exists():
   registered=json.loads(registration.read_text())
   for ref in registered['pattern_refs']:
    guard=state.get(ref['object_id'],'owner')
    if guard['payload']['lesson']==MECHANISMS[x['mechanism']][1]:
     key=['guard-family',pattern['object_id'],ref]
     try:state.get(oid(state,'Relation',key),'owner')
     except Fault as error:
      if error.code!='NOT_FOUND':raise
      save_once(state,'Relation',dict(source_id=pattern['object_id'],target_id=guard['object_id'],kind='qualifies',basis='Family linkage to current registered mechanical guard scope; historical candidate is not thereby accepted'),key)
  save_once(state,'Relation',dict(source_id=x['case_id'],target_id=pattern['object_id'],kind='qualifies',basis=canonical(dict(candidate_relation=x['relation'],comparison_ref=vector(attempt),basis=x['basis'],confirmed_same_pattern=False))),['comparison-link',j['id'],x['case_id']])
 examples=folder(state)/'mechanism-examples.json';groups=json.loads(examples.read_text()) if examples.exists() else {};byid={x['case_ref']['object_id']:x for x in inp['issues']}
 for x in issues:
  if x['case_id'] in result.get('program_repair',{}).get('semantic_pending',[]):continue
  group=groups.setdefault(x['mechanism'],[])
  if len(group)<2:group.append(dict(case_ref=byid[x['case_id']]['case_ref'],candidate=byid[x['case_id']]['candidate'],scope='provisional representative; conditions must be compared, not automatically adopted'))
 atomic(examples,canonical(groups))
 j.update(state='compared',result_ref=vector(attempt),artifact_ref=vector(artifact),issue_count=len(issues),knowledge_count=len(knowledge),at=now());atomic(folder(state)/'jobs'/(j['id']+'.json'),canonical(j))
 index=folder(state)/'recall.json';entries=json.loads(index.read_text()) if index.exists() else {}
 entries[j['id']]=dict(card_ref=j['card_ref'],attempt_ref=vector(attempt),knowledge=[dict(index=x['index'],topics=x['topics'],candidate=inp['knowledge'][x['index']]) for x in knowledge]);atomic(index,canonical(entries))
 from .learning_use import update_issues
 update_issues(state,inp,vector(attempt))
 return j
def after_work(state,actor,event,checkpoint=False):
 """Continue only the existing explicitly mapped, public, authorized host observations."""
 if not config(state):return
 p=event['payload'];host=event['source_host'];sid=p.get('native_session_id');kind=p.get('native_type')
 if not sid or not checkpoint and kind not in ['Stop','turn/end']:return
 bindings=json.loads((state.data/'host-bindings.json').read_text())
 tid=bindings.get(host,{}).get(sid)
 if not tid:return
 task=state.get(tid,'owner')
 if task['payload'].get('execution_state')=='stopped':return
 from .learning_lifecycle import capture_gate
 if task['payload'].get('learning_capture_policy',{}).get('mode')=='adaptive':
  from .archive_trigger import check
  features=dict(p.get('learning_features') or {})
  signal=p.get('learning_signal')
  if signal in ['correction','requirement_change','owner_satisfied','completion']:features[signal]=True
  if signal=='milestone':features['progress']=True
  features['observed_event_id']=event['event_id']
  gate=check(state,actor,{'task_id':task['object_id'],'task_revision':task['revision'],'features':features})
  if gate['action']!='prepare_incremental':return dict(state='deferred',trigger=gate,reason='coalesce public events; no extra model request')
 elif capture_gate(task,event)=='defer':return dict(state='deferred',reason='public events retained; await meaningful work checkpoint, no per-utterance extraction')
 records=[]
 previous_source=None;previous_boundary=0
 with state.db() as c:
  boundary=c.execute('select rowid from host_events where event_id=?',(event['event_id'],)).fetchone()
  if not boundary:return dict(state='blocked',reason='event not durably observed; cannot synthesize a work source')
  # Reuse prior real capture boundaries. Meaningful checkpoints within one
  # turn must not re-extract the whole earlier working snapshot every time.
  prior=c.execute("select o.id,o.head,h.rowid from objects o join object_revisions v on v.object_id=o.id and v.revision=o.head join host_events h on h.event_id=coalesce(json_extract(v.envelope,'$.payload.native_event_id'),substr(json_extract(v.envelope,'$.payload.locator'),17)) where o.type='Artifact' and json_extract(v.envelope,'$.payload.learning_task_ref.object_id')=? and json_extract(v.envelope,'$.payload.native_session_id')=? and h.rowid<? and json_extract(h.payload,'$.payload.native_turn_id') is ? order by h.rowid desc limit 1",(tid,sid,boundary[0],p.get('native_turn_id'))).fetchone()
  if prior:previous_source={'object_id':prior[0],'revision':prior[1]};previous_boundary=prior[2]
  rows=c.execute('select payload from host_events where source_host=? and rowid>? and rowid<=? order by rowid desc limit 1000',(host,previous_boundary,boundary[0])).fetchall()
  for row in reversed(rows):
   value=json.loads(row[0]);q=value['payload']
   if q.get('native_session_id')!=sid:continue
   if p.get('native_turn_id') and q.get('native_turn_id')!=p['native_turn_id']:continue
   if not p.get('native_turn_id') and q.get('native_type') in ['turn/start','UserPromptSubmit']:records=[]
   if q.get('kind')=='native_message':
    message=q.get('message') or {}
    content=message.get('content')
    if message.get('channel') in ['analysis','reasoning'] or isinstance(content,dict) and content.get('content_type') in ['thoughts','reasoning','reasoning_recap']:continue
    records.append(dict(event_id=value['event_id'],message={k:message[k] for k in ['id','role','content','source','toolCallId','isError'] if k in message}))
   elif q.get('kind')=='native_hook' and q.get('native_type') in ['UserPromptSubmit','Stop','PostToolUse']:
    records.append(dict(event_id=value['event_id'],**{k:q[k] for k in ['prompt','last_assistant_message','tool_name','tool_use_id','tool_input','tool_response'] if k in q}))
 if not records:return dict(state='blocked',reason='no observed public input/output/tool body; event alone is not normal work')
 # Explicit bounded observation snapshot; source limits never masquerade as full conversation.
 body=canonical(dict(host=host,native_session_id=sid,task_ref=vector(task),native_event_id=event['event_id'],previous_source_ref=previous_source,records=records,coverage='incremental mapped observed public work since previous capture; historical attachments and unobserved turns excluded')).encode()
 if len(body)>1048576:
  ident=oid(state,'learning-native',event['event_id']);path=folder(state)/'jobs'/(ident+'.json');path.parent.mkdir(exist_ok=True)
  atomic(path,canonical(dict(id=ident,state='needs_review',source_kind='native_work',native_event_id=event['event_id'],error='Observed snapshot exceeds 1MB; original host events preserved, explicit split required',at=now())));return
 source=save_once(state,'Artifact',dict(locator='native-learning:'+event['event_id'],sha256=sha(body),name='Mapped public work learning source',media_type='application/json',candidate=True,learning_host=host,learning_task_ref=vector(task),native_session_id=sid,native_event_id=event['event_id'],previous_source_ref=previous_source,input_vector=[vector(task)]+([previous_source] if previous_source else [])),['native-source',event['event_id']],body)
 ident=oid(state,'learning-native',event['event_id']);path=folder(state)/'jobs'/(ident+'.json');path.parent.mkdir(exist_ok=True)
 if path.exists():return
 pol=anchored_policy(state);job=dict(id=ident,state='queued',source_kind='native_work',source_ref=vector(source),policy_ref=pol['ref'],at=now())
 ev=save_once(state,'Evidence',dict(observation=dict(method='existing host work lifecycle to shared learning queue',**job),input_vector=[vector(source)]),['enqueue',ident]);job['enqueue_ref']=vector(ev);atomic(path,canonical(job))
 return dict(state='queued',job_id=ident,source_ref=vector(source),normal_end_observed=kind in ['Stop','turn/end'])
def receive_native(state,j,result):
 inp=candidate_input(state,j)
 def strings(value):
  if isinstance(value,str):return [value]
  if isinstance(value,list):return [s for v in value for s in strings(v)]
  if isinstance(value,dict):return [s for v in value.values() for s in strings(v)]
  return []
 literal=strings(inp['native_source']['records'])
 knowledge=result.get('knowledge',[]);issues=result.get('issues',[])
 if not isinstance(knowledge,list) or not isinstance(issues,list) or len(knowledge)>12 or len(issues)>12:raise Fault('COVERAGE','bounded native source candidates')
 from .learning_guards import quotes
 quotes(literal,knowledge+issues)
 ev=save_once(state,'Evidence',dict(observation=dict(method='native work candidate extraction, literal source checks',independent_semantic_acceptance=False,source_ref=j['source_ref'],result=result),input_vector=[j['source_ref'],j['policy_ref']]),['native-result',j['id']])
 source=state.get(j['source_ref']['object_id'],'owner')['payload']
 native_models=sorted({(r.get('message') or {}).get('source',{}).get('model') for r in inp['native_source']['records'] if (r.get('message') or {}).get('role')=='assistant' and isinstance((r.get('message') or {}).get('source'),dict) and (r.get('message') or {})['source'].get('model')})
 card=save_once(state,'SemanticCard',dict(native_model_tags=native_models,summary=str(result.get('summary','')),evidence_map=[vector(ev),j['source_ref']],facets={'semantics':'candidate','independent_review':'pending'},knowledge=knowledge,semantic_contract='work-semantic-1',learning_host=source.get('learning_host'),learning_task_ref=source.get('learning_task_ref'),native_session_id=source.get('native_session_id'),input_vector=[vector(ev),j['source_ref']]),['native-card',j['id']])
 for i,x in enumerate(issues):save_once(state,'FailureCase',dict(properties=['learning_candidate_comparison'],lesson=str(x.get('correction','待复核')),source=dict(grading='provisional native work candidate',refs=x['refs']),case_details=x,semantic_contract='work-semantic-1',input_vector=[vector(card),vector(ev)]),['native-case',j['id'],i])
 nextid=enqueue_card(state,card,'current_work_candidate')
 j.update(state='extracted',card_ref=vector(card),comparison_job=nextid,result_ref=vector(ev),at=now());atomic(folder(state)/'jobs'/(j['id']+'.json'),canonical(j));return j
def dispatch(state,actor,action,args,operation_id=None):
 global WORKER
 if action in ['learning_host_next','learning_host_submit']:
  if actor not in ['dsh','codex','pi']:raise Fault('PERMISSION','mapped host token required')
  task=state.get(args['task_id'],actor);bindings=json.loads((state.data/'host-bindings.json').read_text())
  from .learning_use import authorized
  if action=='learning_host_submit' and str(args.get('job_id','')).startswith('semantic:'):
   if not authorized(state,actor,task):raise Fault('PERMISSION','semantic excerpt projection needs owner contract and exact mapped Task')
   from .learning_semantic import submit
   item=dict(args['result']);item['pair_id']=args['job_id'].split(':',1)[1];item['reviewer_locator']=actor+':mapped-task:'+task['object_id']+':semantic-tool-result'
   return submit(state,{'items':[item]})
  for path in sorted((folder(state)/'jobs').glob('*.json')):
   job=json.loads(path.read_text())
   if job['state']!='queued' or job['source_kind'] not in ['native_work','current_work_candidate']:continue
   source=state.get((job.get('source_ref') or job['card_ref'])['object_id'],'owner')['payload']
   if source.get('learning_host')!=actor or source.get('learning_task_ref',{}).get('object_id')!=task['object_id'] or bindings.get(actor,{}).get(source.get('native_session_id'))!=task['object_id']:continue
   if action=='learning_host_next':
    inp=candidate_input(state,job)
    from .learning_use import authorized
    if not authorized(state,actor,task):
     inp['prior_examples']={};inp['prior_comparison_candidates']=[]
    return dict(ok=True,job_id=job['id'],input=inp,source_scope='own explicitly mapped observed public work; old candidate projection requires owner use contract')
   if job['id']==args.get('job_id'):return dispatch(state,'owner','learning_mark',dict(job_id=job['id'],state='received',result=args['result'],actual_model='current_host',native_locator=source['native_session_id']+':public-host-learning-result'))
  if action=='learning_host_next':
   if authorized(state,actor,task):
    from .learning_semantic import overview
    page=overview(state,{'limit':1,'unreviewed_only':True})
    pending=next((x for x in page['rows'] if not x['review']),None)
    if pending and len(canonical(pending).encode())>10000:return dict(ok=True,job_id=None,manual_exception='semantic pair exceeds authorized bounded projection; no raw excerpt disclosed')
    if pending:return dict(ok=True,job_id='semantic:'+pending['pair_id'],input=dict(mode='semantic_pair_review',pair=pending,verdicts=['same_principle','equivalent_conditions','different_conditions','independent','insufficient_evidence'],required=['verdict','principle','basis','condition_comparison'],boundary='Interpret meanings and applicability, not exact string equality. Similarity only proposes pairs. Do not certify source truth or generate executable rules.'),source_scope='bounded owner-authorized candidate excerpts, same current-host queue')
   return dict(ok=True,job_id=None)
  raise Fault('PERMISSION','no queued work in this exact host Task scope')
 if action=='learning_recall':return recall(state,actor,args)
 if actor!='owner':raise Fault('PERMISSION','Owner controls learning policy and canonical updates')
 if action=='learning_inspect':
  from .learning_inspect import inspect
  return inspect(state,args)
 if action=='learning_sources':
  return dict(ok=True,rows=[dict(ref=vector(o),source_kind=o['payload'].get('semantic_contract'),title=o['payload'].get('catalog_title',o['payload'].get('summary',''))) for o in state.list('owner','SemanticCard') if o['payload'].get('semantic_contract') in ['e7-semantic-1','work-semantic-1']])
 if action in ['learning_semantic_build','learning_semantic_submit','learning_semantic_overview']:
  from . import learning_semantic
  return {'learning_semantic_build':learning_semantic.build,'learning_semantic_submit':learning_semantic.submit,'learning_semantic_overview':learning_semantic.overview}[action](state,args) if action!='learning_semantic_build' else learning_semantic.build(state)
 if action=='learning_metadata':
  from .learning_metadata import extract
  return extract(state,anchored_policy(state))
 with LOCK:
  if action=='learning_native_operations':
   from .native_reconcile import inventory
   return inventory(state,actor,args)
  if action=='learning_status':return status(state)
  if action=='learning_probe':
   from .learning_probe import run
   return run(state,args)
  if action=='learning_enable_use':
   from .learning_use import enable
   return enable(state,args)
  if action=='learning_rebuild_use':
   from .learning_use import rebuild_issues
   return rebuild_issues(state)
  if action=='learning_reconcile':
   if 'native_operation' in args:
    from .native_reconcile import reconcile as reconcile_native
    return reconcile_native(state,actor,args)
   from .learning_reconcile import reconcile
   return reconcile(state,args)
  if action=='learning_configure':
   if config(state):return dict(ok=True,policy=anchored_policy(state))
   message=save_once(state,'Message',dict(role='user',source_kind='direct_user',current=True,branch='learning',text=args.get('authorization',''),attachments=[]),['learning-authorization',args.get('authorization')])
   cfg=dict(version=2,automatic_capture=True,automatic_processing=False,account=None,classifier='current_host',thinking=False,hard_rule_adoption='registered verifier only; model proposals remain provisional',source_scope='explicitly mapped work and canonical source-bound candidates',manual_exceptions=True)
   obj=save_once(state,'Artifact',dict(locator='learning-policy:1',sha256=sha(cfg),name='Shared work candidate update policy',media_type='application/json',config=cfg,input_vector=[vector(message)]),['policy',1])
   task=save_once(state,'TaskContract',dict(goal='Task-scoped shared work learning; preserve conditions and separate candidate review from acceptance',required_properties=['learning_source_coverage','learning_classifier_receipts','learning_registered_guards'],host='codex',allow_provider=False,execution_state='running',constraints=['Preserve original candidates and archive. No historical actions. Model proposals do not adopt hard rules.'],input_vector=[vector(message),vector(obj)]),['learning-task',1])
   p=dict(ref=vector(obj),config=cfg,task_ref=vector(task));atomic(folder(state)/'policy.json',canonical(p));atomic(folder(state)/'control.json',canonical(dict(route='current_host',pause=False)));return dict(ok=True,policy=p)
  p=anchored_policy(state)
  if action in ['learning_route','learning_fallback']:
   route=args.get('route','current_host') if action=='learning_route' else 'current_host'
   if route not in ['auto','current_host']:raise Fault('INPUT','auto or current_host route')
   jobs=[json.loads(f.read_text()) for f in (folder(state)/'jobs').glob('*.json')]
   if any(j['state']=='dispatched' for j in jobs):raise Fault('OUTCOME_UNKNOWN','finish or reconcile dispatched work before route changes')
   if any(json.loads(f.read_text()).get('state') in ['unknown','reserved','response_known'] for f in (folder(state)/'receipts').glob('*.json')):raise Fault('OUTCOME_UNKNOWN','reconcile paid receipts before fallback')
   cfg=dict(route=route,reason=args.get('reason','Current user selects same-queue current host fallback'),pause=False)
   ev=save_once(state,'Evidence',dict(observation=dict(method='shared learner route selection before dispatch',**cfg),input_vector=[p['ref']]),['route',cfg])
   cfg['evidence_ref']=vector(ev);atomic(folder(state)/'control.json',canonical(cfg));return dict(ok=True,route=cfg,no_model_spawn=True)
  if action=='learning_review':
   items=args.get('items',[])
   if not isinstance(items,list) or not 1<=len(items)<=20:raise Fault('INPUT','1..20 explicit comparison reviews')
   results=[]
   for item in items:
    uuid_ok(item['job_id']);j=json.loads((folder(state)/'jobs'/(item['job_id']+'.json')).read_text())
    if j['state']!='compared' or item['result_ref']!=j['result_ref']:raise Fault('REVISION_CONFLICT','review current completed comparison only')
    if not isinstance(item.get('basis'),str) or not 1<=len(item['basis'])<=1000:raise Fault('INPUT','bounded observed review basis')
    for flag in item.get('knowledge_flags',[]):
     if type(flag.get('index'))!=int or not 0<=flag['index']<j['knowledge_count'] or flag.get('state')!='needs_semantic_review':raise Fault('INPUT','explicit source knowledge index and review state')
    ev=save_once(state,'Evidence',dict(observation=dict(method='current desktop GPT candidate comparison review; not source-wide semantic acceptance',review=item),input_vector=[j['result_ref'],j['card_ref']]),['review',item])
    directory=folder(state)/'reviews';directory.mkdir(exist_ok=True);atomic(directory/(j['id']+'.json'),canonical(dict(review=item,evidence_ref=vector(ev))));results.append(vector(ev))
   return dict(ok=True,reviews=results)
  if action=='learning_register_guards':
   from .learning_verify import register
   return register(state,p)
  if action=='learning_verify':
   from .learning_verify import verify
   return verify(state,p,args)
  if action=='learning_enqueue':
   refs=args.get('card_refs',[])
   if not isinstance(refs,list) or not 1<=len(refs)<=200:raise Fault('INPUT','1..200 canonical candidate refs')
   for ref in refs:
    card=state.get(ref['object_id'],'owner')
    if vector(card)!=ref:raise Fault('REVISION_CONFLICT','candidate changed')
    enqueue_card(state,card,'historical_candidate_replay' if card['payload'].get('semantic_contract')=='e7-semantic-1' else 'current_work_candidate')
   return dict(ok=True,queued=len(refs),total=status(state)['total'])
  if action=='learning_next':
   for f in sorted((folder(state)/'jobs').glob('*.json')):
    j=json.loads(f.read_text())
    if j['state']=='queued' and (not args.get('native_only') or j['source_kind'] in ['native_work','current_work_candidate']):return dict(ok=True,job=j,input=candidate_input(state,j),task_ref=p['task_ref'])
   return dict(ok=True,job=None)
  if action=='learning_batch_input':
   limit=args.get('limit',5)
   if type(limit)!=int or not 1<=limit<=5:raise Fault('INPUT','1..5 source batch')
   jobs=[]
   for f in sorted((folder(state)/'jobs').glob('*.json')):
    j=json.loads(f.read_text())
    if j['state']!='queued' or args.get('native_only') and j['source_kind'] not in ['native_work','current_work_candidate']:continue
    if j['source_kind']=='native_work':
     if not jobs:jobs.append(j)
     break
    jobs.append(j)
    if len(jobs)>=limit:break
   return dict(ok=True,jobs=[dict(job=j,input=candidate_input(state,j)) for j in jobs],task_ref=p['task_ref'])
  if action=='learning_mark':
   uuid_ok(args.get('job_id'))
   path=folder(state)/'jobs'/(args['job_id']+'.json');j=json.loads(path.read_text())
   if args.get('state')=='dispatched':
    if j['state']!='queued':raise Fault('OUTCOME_UNKNOWN','no automatic retry of dispatched job')
    j.update(state='dispatched',reservation_id=args['reservation_id'],at=now());atomic(path,canonical(j));return dict(ok=True)
   if args.get('state')=='failed':j.update(state='needs_review',error=args.get('error'),at=now());atomic(path,canonical(j));return dict(ok=True)
   if j['state']=='needs_review':
    receipt=folder(state)/'receipts'/(j['id']+'.json')
    if not receipt.exists() or json.loads(receipt.read_text())['state']!='settled':raise Fault('OUTCOME_UNKNOWN','manual correction requires known settled receipt')
   elif j['state'] not in ['dispatched','queued']:raise Fault('REVISION_CONFLICT','job no longer awaiting comparison')
   if j['state']=='queued':
    if args.get('actual_model') not in ['current_desktop_gpt','current_host','registered_program'] or not isinstance(args.get('native_locator'),str) or not args['native_locator']:raise Fault('INPUT','non-provider result needs explicit public locator; exact host model version remains unknown')
    receipt=folder(state)/'receipts';receipt.mkdir(exist_ok=True);atomic(receipt/(j['id']+'.json'),canonical(dict(state='host_completed',job_id=j['id'],actual_model=args['actual_model'],native_locator=args['native_locator'],input_sha256=sha(candidate_input(state,j)),provider_calls=0,at=now())))
   return dict(ok=True,job=receive(state,j,args['result']))
  if action=='learning_start':
   if not args.get('external_provider'):
    return dict(ok=True,current_host_pending=True,no_model_spawn=True,instruction='Read learning_batch_input and submit in this existing host; external execution requires explicit scoped Task and budget')
   external=state.get(args.get('task_id'),'owner')
   if vector(external)!=args.get('task_ref') or not external['payload'].get('allow_provider') or not external['payload'].get('budget_account'):
    raise Fault('BUDGET_REQUIRED','explicit current external Task and separately authorized budget required')
   if vector(external)!=p['task_ref'] or external['payload']['budget_account']!=p['config'].get('account'):
    raise Fault('BUDGET_ACCOUNT_MISMATCH','external execution must match configured Task and account')
   control=folder(state)/'control.json'
   if control.exists() and json.loads(control.read_text()).get('route')=='current_host':return dict(ok=True,current_host_pending=True,no_model_spawn=True,instruction='Read learning_batch_input and return source-bound dispositions through learning_mark with actual_model=current_desktop_gpt and public native_locator')
   if WORKER is not None and WORKER.poll() is None:raise Fault('BUSY','learning worker already running')
   import msvcrt
   try:
    with (folder(state)/'worker.lock').open('a+b') as handle:
     handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
   except OSError:raise Fault('BUSY','durable learning worker lock held')
   if any(json.loads(f.read_text()).get('state') in ['unknown','reserved','response_known'] for f in (folder(state)/'receipts').glob('*.json')):raise Fault('OUTCOME_UNKNOWN','reconcile unsettled paid result before new learning dispatch')
   count=args.get('count',100)
   if type(count)!=int or not 1<=count<=10000:raise Fault('INPUT','bounded worker count 1..10000')
   atomic(folder(state)/'control.json',canonical(dict(pause=False,route='auto')))
   log=(folder(state)/'worker.log').open('ab');repo=Path(__file__).resolve().parents[1]
   WORKER=subprocess.Popen([sys.executable,'-X','utf8',str(repo/'ops/learning_worker.py'),str(state.root),str(count),'native' if args.get('native_only') else 'all'],cwd=repo,stdout=log,stderr=log);log.close();return dict(ok=True,started=True,count=count)
  if action=='learning_pause':atomic(folder(state)/'control.json',canonical(dict(pause=True)));return dict(ok=True,pause_at_next_boundary=True)
  raise Fault('UNSUPPORTED','unknown shared learning action')
def maintain(state):
 import time
 global LAST_AUTO
 if time.monotonic()-LAST_AUTO<5:return
 LAST_AUTO=time.monotonic()
 if not config(state) or not config(state)['config'].get('automatic_processing') or (WORKER is not None and WORKER.poll() is None):return
 control=folder(state)/'control.json'
 if control.exists() and (json.loads(control.read_text()).get('pause') or json.loads(control.read_text()).get('route')=='current_host'):return
 # Ordinary work always returns to the existing host. No hidden paid provider or new GPT turn.
 return
def recall(state,actor,args):
 """Bounded optional knowledge recall; ACL and current canonical revisions are checked."""
 import re
 task=state.get(args['task_id'],actor)
 from .learning_use import authorized
 projection=authorized(state,actor,task)
 reader='owner' if projection else actor
 query=args.get('query') or task['payload'].get('goal','')
 if not isinstance(query,str) or len(query)>12000:raise Fault('INPUT','bounded recall query')
 tokens=set(re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}|[\u4e00-\u9fff]{2,}',query.lower()))
 tokens.update(query[i:i+2] for i in range(len(query)-1) if all('\u4e00'<=x<='\u9fff' for x in query[i:i+2]))
 path=folder(state)/'recall.json';entries=json.loads(path.read_text()) if path.exists() else {};ranked=[]
 for job_id,entry in entries.items():
  entry=dict(entry,job_id=job_id)
  for item in entry['knowledge']:
   topics=' '.join(item['topics']).lower();score=sum(t in topics for t in tokens)
   if score:ranked.append((score,entry,item))
 selected=[];size=0
 for score,entry,item in sorted(ranked,key=lambda x:-x[0]):
  try:
   card=state.get(entry['card_ref']['object_id'],reader);attempt=state.get(entry['attempt_ref']['object_id'],reader)
   if vector(card)!=entry['card_ref'] or vector(attempt)!=entry['attempt_ref']:continue
  except Fault as e:
   if e.code=='NOT_FOUND':continue
   raise
  review=folder(state)/'reviews'/(entry['job_id']+'.json')
  if review.exists():
   reviewed=json.loads(review.read_text());ev=state.get(reviewed['evidence_ref']['object_id'],reader)
   if ev['payload']['observation']['review']!=reviewed['review']:raise Fault('REVIEW_CHANGED','review cache differs from canonical evidence')
   if reviewed['review']['result_ref']==entry['attempt_ref'] and any(f['index']==item['index'] for f in reviewed['review'].get('knowledge_flags',[])):continue
  row=dict(card_ref=entry['card_ref'],attempt_ref=entry['attempt_ref'],index=item['index'],topics=item['topics'],candidate=item['candidate'],score=score,acceptance='source candidate; verify applicability and facts before use')
  amount=len(canonical(row).encode())
  if size+amount>6000:continue
  selected.append(row);size+=amount
  if len(selected)>=4:break
 result=dict(ok=True,task_ref=vector(task),query=query,selection='deterministic lexical topic recall; bounded optional candidates, not mandatory proof',candidates=selected)
 if args.get('record') and actor=='owner':
  receipt=state.put(request(object_new('RetrievalReceipt',dict(query=query,selected=[x['card_ref'] for x in selected],task_ref=vector(task),scope='optional knowledge candidates',input_vector=[vector(task)]+[x['attempt_ref'] for x in selected]))),actor)['object'];result['receipt_ref']=vector(receipt)
 return result
