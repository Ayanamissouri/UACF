"""Owner-authorized bounded candidate projection into exact mapped host Tasks.

This never changes source ACLs or allows hosts to fetch the private archive.
"""
import json,re,collections
from .util import Fault,canonical,atomic,now,sha
from .fabric import vector

def enable(state,args):
 from .learning import folder,anchored_policy,save_once
 hosts=args.get('hosts',['dsh','codex'])
 if not isinstance(hosts,list) or not hosts or any(x not in ['dsh','codex','pi'] for x in hosts):raise Fault('INPUT','explicit native hosts')
 if not args.get('authorization'):raise Fault('INPUT','direct owner authorization required')
 policy=anchored_policy(state)
 cfg=dict(hosts=sorted(set(hosts)),policy_ref=policy['ref'],scope='bounded source candidate excerpts for exact explicitly mapped host Task; no raw archive access',knowledge_limit=4,issue_limit=3,total_optional_bytes=10000,automatic_hard_adoption=False)
 decision=save_once(state,'Decision',dict(outcome='enable task-scoped candidate projection',basis=args['authorization'],learning_use_contract=cfg,input_vector=[policy['ref']]),['learning-use',cfg,args['authorization']])
 atomic(folder(state)/'use-contract.json',canonical(dict(decision_ref=vector(decision),config=cfg)))
 return dict(ok=True,decision_ref=vector(decision),config=cfg,source_acls_changed=False)

def authorized(state,actor,task):
 if actor=='owner':return True
 if actor not in ['dsh','codex','pi']:return False
 from .learning import folder
 path=folder(state)/'use-contract.json'
 if not path.exists():return False
 contract=json.loads(path.read_text());obj=state.get(contract['decision_ref']['object_id'],'owner')
 if vector(obj)!=contract['decision_ref'] or obj['payload'].get('learning_use_contract')!=contract['config']:raise Fault('USE_CONTRACT_CHANGED','canonical use contract changed')
 bindings=json.loads((state.data/'host-bindings.json').read_text())
 return actor in contract['config']['hosts'] and task['object_id'] in bindings.get(actor,{}).values()

def issue_index(state):
 from .learning import folder
 path=folder(state)/'issue-index.json'
 if path.exists():return json.loads(path.read_text())
 return {}

def rebuild_issues(state):
 from .learning import folder
 jobs=[json.loads(p.read_text()) for p in (folder(state)/'jobs').glob('*.json')]
 bycard={j.get('card_ref',{}).get('object_id'):j for j in jobs if j['state']=='compared'}
 result={}
 for case in state.list('owner','FailureCase'):
  job=next((bycard[r['object_id']] for r in case['payload'].get('input_vector',[]) if r['object_id'] in bycard),None)
  if not job:continue
  result[case['object_id']]=dict(case_ref=vector(case),card_ref=job['card_ref'],attempt_ref=job['result_ref'],candidate={k:v for k,v in case['payload'].get('case_details',{}).items() if k!='refs'})
 atomic(folder(state)/'issue-index.json',canonical(result))
 return dict(ok=True,issues=len(result),source_data_changed=False)

def issue_recall(state,actor,task):
 if not authorized(state,actor,task):return dict(candidates=[],access='not authorized for private candidate projection')
 query=task['payload'].get('goal','');tokens=set(re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}',query.lower()));tokens.update(query[i:i+2] for i in range(len(query)-1) if all('\u4e00'<=c<='\u9fff' for c in query[i:i+2]))
 selected=[];size=0;ranked=[]
 from .learning_semantic import annotations
 semantic=annotations(state);selected_principles=set()
 for item in issue_index(state).values():
  text=canonical(list(item['candidate'].values())).lower();score=sum(t in text for t in tokens)
  if score:ranked.append((score,item))
 for score,item in sorted(ranked,key=lambda x:-x[0]):
  try:
   if any(vector(state.get(item[k]['object_id'],'owner'))!=item[k] for k in ['case_ref','card_ref','attempt_ref']):continue
  except Fault:continue
  case=state.get(item['case_ref']['object_id'],'owner')
  if {k:v for k,v in case['payload'].get('case_details',{}).items() if k!='refs'}!=item['candidate']:continue
  attempt=state.get(item['attempt_ref']['object_id'],'owner')
  if not any(x['case_id']==case['object_id'] for x in attempt['payload']['assessment']['issues']):continue
  reviewed=semantic.get(item['case_ref']['object_id'],[])
  principle=reviewed[0]['principle'] if reviewed else None
  if principle and principle in selected_principles:continue
  row=dict(item,acceptance='candidate conditions and correction only; not mandatory rule or confirmed root cause',score=score,semantic_reviews=reviewed[:2])
  amount=len(canonical(row).encode())
  if size+amount>4000:continue
  selected.append(row);size+=amount
  if principle:selected_principles.add(principle)
  if len(selected)==3:break
 return dict(candidates=selected,selection='bounded task-goal lexical recall with source conditions; applicability must be checked')

def usage(state,actor,task,knowledge,issues):
 from .learning import folder
 directory=folder(state)/'usage';directory.mkdir(exist_ok=True)
 row=dict(at=now(),actor=actor,task_ref=vector(task),knowledge=[dict(card_ref=x['card_ref'],index=x['index']) for x in knowledge],issues=[x['case_ref'] for x in issues],phase='prepared capsule; actual host delivery and use require native receipt',source_semantic_acceptance=False)
 # A repeat of the same prepared selection does not inflate usage counts.
 key=sha({k:v for k,v in row.items() if k!='at'});atomic(directory/(key+'.json'),canonical(row))
 return dict(prepared_selection_id=key,knowledge_count=len(knowledge),issue_count=len(issues),actual_use='not inferred from preparation')

def relevant_prior(state,inp):
 query=canonical([list(x['candidate'].values()) for x in inp['issues']]).lower();tokens=set(re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}',query));tokens.update(query[i:i+3] for i in range(len(query)-2) if all('\u4e00'<=c<='\u9fff' for c in query[i:i+3]))
 ranked=[]
 for row in issue_index(state).values():
  if row['card_ref']==inp['card_ref']:continue
  text=canonical(list(row['candidate'].values())).lower();score=sum(t in text for t in tokens)
  if score:ranked.append((score,row))
 chosen=[];size=0
 for score,row in sorted(ranked,key=lambda x:-x[0]):
  case=state.get(row['case_ref']['object_id'],'owner')
  if vector(case)!=row['case_ref']:continue
  candidate={k:v for k,v in case['payload'].get('case_details',{}).items() if k!='refs'}
  if candidate!=row['candidate']:continue
  entry=dict(case_ref=row['case_ref'],card_ref=row['card_ref'],comparison_ref=row['attempt_ref'],conditions={k:candidate.get(k) for k in ['trigger','actual','expected','correction','applicable','excluded']},scope='related comparison candidate only; check applicability/exclusions before proposing equivalence')
  amount=len(canonical(entry).encode())
  if size+amount>6000:continue
  chosen.append(entry);size+=amount
  if len(chosen)==3:break
 return chosen

def equivalent(a,b):
 keys=['trigger','actual','expected','correction','applicable','excluded']
 return all(k in a and k in b and a[k] is not None and b[k] is not None for k in keys) and {k:a[k] for k in keys}=={k:b[k] for k in keys}

def update_issues(state,inp,attempt_ref):
 from .learning import folder
 entries=issue_index(state)
 for item in inp['issues']:
  entries[item['case_ref']['object_id']]=dict(case_ref=item['case_ref'],card_ref=inp['card_ref'],attempt_ref=attempt_ref,candidate={k:v for k,v in item['candidate'].items() if k!='refs'})
 atomic(folder(state)/'issue-index.json',canonical(entries))
 from .learning_semantic import build
 build(state) # index-only proposals; the current host must perform semantic judgments
