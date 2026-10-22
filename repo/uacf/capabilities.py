"""Evidence-indexed capability observations, never installation or permission grants."""
import json,re,threading
from .util import Fault,atomic,canonical,sha,now
from .state import object_new,request,stale
from .fabric import vector
LOCK=threading.RLock()
STAGES=('generated','installed','loaded','called','verified')
HOSTS=('codex','pi','dsh','claude_code','codex_cloud','uacf')
FIELDS=('machine','host','host_version','profile','capability','source_identity')

def registry(state):
 p=state.data/'capability-registry.json'
 if not p.exists():
  # The canonical backup already contains immutable Artifact bodies/blobs.
  # Loss of this disposable projection must not erase visibility or start a
  # new empty authority. Reads recover without mutating the restore workspace.
  candidates=[x for x in state.list('owner','Artifact') if x['payload'].get('locator')=='uacf:capability-registry']
  if not candidates:return None
  obj=max(candidates,key=lambda x:(x['recorded_at'],x['object_id']))
  config=obj['payload']['config']
  if obj['payload'].get('sha256')!=sha(canonical(config).encode()):raise Fault('CAPABILITY_CHANGED','canonical capability body digest mismatch')
  return {'ref':vector(obj),'config':config}
 data=json.loads(p.read_text(encoding='utf8'));obj=state.get(data['ref']['object_id'],'owner')
 if vector(obj)!=data['ref'] or obj['payload'].get('config')!=data['config']:raise Fault('CAPABILITY_CHANGED','capability projection differs from canonical revision')
 return data

def _evidence(state,observation):
 ref=observation['evidence_ref'];obj=state.get(ref['object_id'],'owner')
 if vector(obj)!=ref or stale(state,obj):raise Fault('CAPABILITY_EVIDENCE','capability evidence is stale')
 if obj['object_type'] not in ['Evidence','Validation','Artifact']:raise Fault('CAPABILITY_EVIDENCE','capability observation requires evidence, not a task or message')
 if observation['stage']=='verified' and (obj['object_type']!='Validation' or obj['payload'].get('result')!='pass'):raise Fault('CAPABILITY_EVIDENCE','verified requires a registered passing Validation; self-report is insufficient')
 payload=obj['payload']
 if obj['object_type']=='Validation':
  evidence=state.get(payload['evidence_id'],'owner')
  if stale(state,evidence):raise Fault('CAPABILITY_EVIDENCE','underlying verification evidence became stale')
  payload=evidence['payload']
 body=payload.get('observation',payload.get('config',{}))
 proofs=body.get('capability_proofs',body.get('details',{}).get('capability_proofs',[]))
 matched=any(all(proof.get(k)==observation.get(k) for k in FIELDS) and proof.get('native_session_id')==observation.get('native_session_id') and observation['stage'] in proof.get('stages',[]) and proof.get('scope')==observation.get('scope') for proof in proofs)
 if not matched:raise Fault('CAPABILITY_EVIDENCE','evidence does not bind this machine/version/profile/source/session/stage and scope')
 return obj

def record(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','Owner records scoped capability observations; hosts cannot self-certify')
 with LOCK:
  old=registry(state)
  if args.get('expected_registry_ref')!=(old['ref'] if old else None):raise Fault('REVISION_CONFLICT','capability registry changed')
  item={k:args.get(k) for k in FIELDS}
  if any(not isinstance(v,str) or not 1<=len(v)<=200 for v in item.values()) or item['host'] not in HOSTS or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',item['capability']):raise Fault('CAPABILITY_INPUT','bounded machine, host/version/profile, capability and code identity required')
  if args.get('stage') not in STAGES or not isinstance(args.get('scope'),str) or not 1<=len(args['scope'])<=1200:raise Fault('CAPABILITY_INPUT','explicit observed stage and finite scope required')
  item.update(stage=args['stage'],scope=args['scope'],evidence_ref=args['evidence_ref'],native_session_id=args.get('native_session_id'),at=now())
  if item['native_session_id'] is not None and (not isinstance(item['native_session_id'],str) or not 1<=len(item['native_session_id'])<=200):raise Fault('CAPABILITY_INPUT','bounded actual native session identity required')
  _evidence(state,item)
  # Different versions, profiles, source bytes and sessions never inherit proof.
  key=sha([item[k] for k in FIELDS]+[item['native_session_id']])
  entries=dict(old['config']['entries'] if old else {})
  entry=dict(entries.get(key,dict(identity={k:item[k] for k in FIELDS},native_session_id=item['native_session_id'],observations={})))
  entry['observations']=dict(entry['observations'],**{item['stage']:item});entries[key]=entry
  if len(entries)>500:raise Fault('CAPABILITY_LIMIT','bounded current registry; archive observations through canonical history')
  config={'version':1,'entries':entries,'scope':'Observed installation/lifecycle evidence only; not tool authorization, model quality or a universal sandbox.'}
  body=canonical(config).encode();obj=object_new('Artifact',dict(name='Shared host capability evidence',locator='uacf:capability-registry',sha256=sha(body),config=config),visibility='shared')
  saved=state.put(request(obj,blob=body),actor)['object'];data={'ref':vector(saved),'config':config};atomic(state.data/'capability-registry.json',canonical(data))
  return dict(ok=True,registry_ref=data['ref'],key=key,stage=item['stage'],model_calls=0)

def status(state,actor,args):
 data=registry(state);items=[]
 for key,entry in (data['config']['entries'] if data else {}).items():
  identity=entry['identity']
  if any(args.get(k) is not None and args[k]!=identity[k] for k in FIELDS):continue
  if args.get('native_session_id') is not None and args['native_session_id']!=entry['native_session_id']:continue
  stages={};gaps={}
  for stage in STAGES:
   observation=entry['observations'].get(stage)
   if observation is None:stages[stage]='unobserved';continue
   try:_evidence(state,observation);stages[stage]='observed'
   except Fault as e:stages[stage]='stale';gaps[stage]=e.code
  items.append(dict(key=key,identity=identity,native_session_id=entry['native_session_id'],stages=stages,observations=entry['observations'],gaps=gaps))
 return dict(ok=True,registry_ref=data['ref'] if data else None,items=items,scope='Each stage independent and scoped to exact machine/version/profile/source/session; unobserved is not absent.',model_calls=0)
