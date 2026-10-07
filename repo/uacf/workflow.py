"""Authenticated workflow controls; one worker, immutable route evidence."""
import json,threading,subprocess,os
from pathlib import Path
from .util import Fault,canonical,atomic,now,uid,sha,file_hash
from .state import object_new,request
LOCK=threading.Lock();WORKER=None

def checkpoint_boundary(get_object,out,plan,completed_count,total):
 checkpoints=plan.get('architecture_checkpoints',[])
 if not checkpoints:return total
 projection=out/'architecture-acceptance.json'
 accepted=json.loads(projection.read_text()) if projection.exists() else {}
 task={'object_id':plan['task_id'],'revision':plan['task_revision']}
 selection_hash=file_hash(out/'selection.json')
 for count in checkpoints:
  if count>completed_count:return count
  entry=accepted.get(str(count))
  if not entry:return completed_count
  ref=entry.get('evidence_ref',{});obj=get_object(ref.get('object_id'))
  observation=obj.get('payload',{}).get('observation',{})
  if obj.get('object_type')!='Evidence' or obj.get('revision')!=ref.get('revision') or observation.get('count')!=count or observation.get('task_ref')!=task or observation.get('selection_hash')!=selection_hash or entry.get('task_ref')!=task or entry.get('selection_hash')!=selection_hash:
   raise Fault('CHECKPOINT_TAMPERED','checkpoint projection must match canonical evidence, Task revision and frozen source set')
 return total

def anchored_packet(state,p,actor):
 obj=state.get(p['artifact_ref']['object_id'],actor)
 if obj['revision']!=p['artifact_ref']['revision'] or obj['payload'].get('sha256')!=sha(canonical({k:v for k,v in p.items() if k!='artifact_ref'}).encode()):raise Fault('SOURCE_CHANGED','source projection differs from canonical Artifact')
def worker_busy(out):
 if WORKER is not None and WORKER.poll() is None:return True
 import msvcrt
 try:
  with open(out/'worker.lock','a+b') as handle:
   handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
  return False
 except OSError:return True
def dispatch(state,actor,action,args,operation_id=None):
 global WORKER
 if action.startswith('workflow_project_'):
  from .project_workflow import dispatch as project_dispatch
  return project_dispatch(state,actor,action,args,operation_id)
 pointer=state.root/'data/e7-active-batch.json'
 batch=json.loads(pointer.read_text()) if pointer.exists() else {'directory':None}
 out=state.root/'deliverables'/(batch['directory'] or '__unprepared__')
 if actor!='owner' and action!='workflow_status':raise Fault('PERMISSION','workflow mutation requires owner')
 if not batch['directory'] and action not in ['workflow_status','workflow_select_batch']:raise Fault('NOT_PREPARED','select an explicitly frozen batch first; ordinary tasks use workflow_project')
 def read(name,default=None):return json.loads((out/name).read_text(encoding='utf-8')) if (out/name).exists() else default
 if action=='workflow_select_batch':
  if actor!='owner':raise Fault('PERMISSION','batch switch requires owner')
  with LOCK:
   if (out.exists() and worker_busy(out)) or read('status.json',{}).get('state') in ['queued','running','waiting_host_review']:raise Fault('BUSY','finish or pause current batch')
   name=args.get('directory','')
   import re
   if not re.fullmatch(r'e7-workflow-[a-zA-Z0-9-]{1,60}',name):raise Fault('INPUT','safe prepared batch directory required')
   target=state.root/'deliverables'/name
   if not (target/'plan.json').is_file():raise Fault('NOT_PREPARED','prepare immutable source selection first')
   plan=json.loads((target/'plan.json').read_text());task=state.get(plan['task_id'],actor)
   if task['revision']!=plan['task_revision']:raise Fault('REVISION_CONFLICT','batch Task changed')
   approved=state.get(task['payload']['processing_manifest_ref']['object_id'],actor)['payload']
   from .util import file_hash
   if approved['selection_hash']!=file_hash(target/'selection.json') or approved['audit_schedule_hash']!=file_hash(target/'audit-schedule.json'):raise Fault('SOURCE_CHANGED','manifest changed')
   evidence=state.put(request(object_new('Artifact',dict(locator='workflow-batch:'+str(operation_id),name='UI selected E7 batch',media_type='application/json',sha256=sha(name),directory=name,task_ref={'object_id':task['object_id'],'revision':task['revision']}),visibility='private'),operation_id=operation_id),actor)['object']
   atomic(pointer,canonical({'directory':name,'ref':{'object_id':evidence['object_id'],'revision':evidence['revision']}}))
   return {'ok':True,'directory':name}
 if action=='workflow_status':
  result={'ok':True,'batch_directory':batch['directory'],'selection':read('selection.json',{}),'status':read('status.json',{'state':'unprepared'}),'config':read('active-config.json',{}),'worker_alive':worker_busy(out) if out.exists() else False}
  if actor!='owner':result.pop('selection',None)
  if actor=='owner':result['host_request']=read('host-review-request.json',{})
  return result
 if action=='workflow_review_request':
  if actor!='owner':raise Fault('PERMISSION','source review requires owner')
  r=read('host-review-request.json')
  if not r:raise Fault('NOT_FOUND','no pending host request')
  p=read(f'packet-{r["index"]:02}.json')
  anchored_packet(state,p,actor)
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops'));import e7_semantics as base
  chunks=base.segments(p,20000);unit=chunks[r.get('part',0)]
  candidates=[read(f.name).get('parsed') for f in sorted(out.glob(f'call-{r["index"]:02}-*.json')) if any(x['node'] in {n['node'] for n in unit} for x in read(f.name).get('unit_spans',[]))]
  return {'ok':True,'request':r,'source':dict(p,nodes=unit),'candidates':candidates,'partial_source':len(chunks)>1,'cross_fragment_review':'pending; retain parent/branch/offsets and per-part candidates'}
 if actor!='owner':raise Fault('PERMISSION','workflow execution requires owner')
 with LOCK:
  alive=worker_busy(out)
  if action=='workflow_pause':
   evidence=state.put(request(object_new('Artifact',dict(locator='workflow-pause:'+str(operation_id),name='Pause new workflow calls',sha256=sha('pause'),media_type='application/json',control='pause',pending_request=read('host-review-request.json',{}),at=now()),visibility='private'),operation_id=operation_id),actor)['object']
   atomic(out/'control.json',canonical({'pause':True,'evidence_id':evidence['object_id']}));st=read('status.json',{});
   if st.get('state')=='waiting_host_review':st.update(state='paused',stage='已暂停宿主审核请求');atomic(out/'status.json',canonical(st))
   return {'ok':True,'pause_at_next_boundary':True}
  if alive:raise Fault('BUSY','worker active; pause and wait before changing route')
  if action=='workflow_resolve_rejection':
   s=read('status.json',{});error=s.get('error','')
   if "model is not supported when using Codex with a ChatGPT account" not in error:raise Fault('OUTCOME_UNKNOWN','only proven model rejection may be resolved here')
   proof=state.put(request(object_new('Evidence',{'observation':{'method':'actual CLI model rejection','error':error,'replacement':'current desktop host review queue','usage':'no successful generation receipt; accounting unknown'}}),operation_id=operation_id),actor)['object']
   s.update(state='idle',error=None,rejection_evidence={'object_id':proof['object_id'],'revision':proof['revision']});atomic(out/'status.json',canonical(s));return {'ok':True,'evidence':proof['object_id']}
  if action=='workflow_review_submit':
   r=read('host-review-request.json');s=read('status.json',{})
   if not r or args.get('request_id')!=r['request_id'] or s.get('state')!='waiting_host_review':raise Fault('REVISION_CONFLICT','review request changed')
   p=read(f'packet-{r["index"]:02}.json')
   anchored_packet(state,p,actor)
   if sha((out/f'packet-{r["index"]:02}.json').read_bytes())!=r['source_hash']:raise Fault('SOURCE_CHANGED','review source hash changed')
   import sys
   sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops'))
   import e7_semantics as base
   chunks=base.segments(p,20000);unit=chunks[r.get('part',0)];parsed=args.get('result')
   if not isinstance(parsed,dict) or not parsed.get('summary'):raise Fault('INPUT','complete semantic JSON required')
   for key in ['knowledge','issues']:
    if not isinstance(parsed.get(key,[]),list) or any(not isinstance(item,dict) or not item.get('refs') or any(not isinstance(ref,dict) or not ref.get('node') or not ref.get('quote') for ref in item['refs']) for item in parsed.get(key,[])):raise Fault('INPUT','every knowledge/issue needs literal node+quote references')
   check=base.check_refs(parsed,unit)
   if check['invalid']:raise Fault('SOURCE_QUOTE_INVALID','host response has nonliteral or wrong-node references')
   result=dict(state='settled',parsed=parsed,part=0,raw={'model':'gpt-6.1-sol','reasoning_effort':'medium','adapter':'current desktop host UI queue','usage':'shared current conversation; separate public native accounting','answer':canonical(parsed)},unit_spans=[{k:n[k] for k in ['node','start','end','raw_hash']} for n in unit],source_check=check,independent_semantic_acceptance=False,elapsed_seconds=None,request=r,at=now())
   evidence=state.put(request(object_new('Evidence',{'observation':{'method':'actual frontend host review submission','request':r,'source_check':check,'result_hash':sha(canonical(result)),'current_host_model':'self-reported; verify public native turn configuration','independent_acceptance':False}}),operation_id=operation_id),actor)['object']
   result['evidence_ref']={'object_id':evidence['object_id'],'revision':evidence['revision']};atomic(out/r['result_name'],canonical(result));atomic(out/'host-review-request.json',canonical({}));s.update(state='idle',stage='宿主审核回填完成');atomic(out/'status.json',canonical(s));return {'ok':True,'source_check':check,'evidence_id':evidence['object_id']}
  if action=='workflow_configure':
   if read('status.json',{}).get('state')=='waiting_host_review':raise Fault('BUSY','complete or pause current host review before changing route')
   if not (out/'plan.json').exists():raise Fault('NOT_PREPARED','frozen selection required')
   model=args.get('extract');host=args.get('host');ratio=args.get('review_percent');concurrency=args.get('concurrency',1)
   if model not in ['deepseek-flash','gpt-6.1-sol'] or host not in ['codex_deepseek','dsh_deepseek','pi_deepseek'] or type(ratio)!=int or not 0<=ratio<=100 or args.get('review_policy','risk') not in ['risk','balanced'] or type(concurrency)!=int or not 1<=concurrency<=3:raise Fault('INPUT','unsupported route, ratio or concurrency')
   old=read('active-config.json',{});revision=old.get('revision',0)
   if args.get('expected_revision')!=revision:raise Fault('REVISION_CONFLICT','route changed; refresh')
   config=dict(extract=model,host=host,review_percent=ratio,concurrency=concurrency,review_policy=args.get('review_policy','risk'),preset=args.get('preset','manual'),gpt_adapter='desktop_queue',revision=revision+1,at=now(),operation_id=operation_id,source_integrity='full public source; no lossy compression',calibration='asset ratio pilot10; other task families uncalibrated',review_model='gpt-6.1-sol',review_effort='medium')
   evidence=state.put(request(object_new('Artifact',dict(locator='workflow-route:'+str(operation_id),name='Applied E7 workflow route',media_type='application/json',sha256=sha(canonical(config).encode()),config=config),visibility='private'),operation_id=operation_id),actor)['object']
   config['canonical_ref']={'object_id':evidence['object_id'],'revision':evidence['revision']};atomic(out/'active-config.json',canonical(config));return {'ok':True,'config':config}
  if action=='workflow_start':
   config=read('active-config.json');scope=args.get('scope')
   if not config or scope not in ['pilot','review','production','publish','probe','repair']:raise Fault('INPUT','apply route then select execution scope')
   if scope=='probe' and config['extract']!='deepseek-flash':raise Fault('INPUT','provider connection probe requires DeepSeek extraction route')
   if args.get('expected_revision')!=config['revision']:raise Fault('REVISION_CONFLICT','route changed; refresh')
   s=read('status.json',{});
   if s.get('state')=='published':raise Fault('ALREADY_PUBLISHED','published batch cannot be restarted')
   if s.get('state')=='waiting_host_review':raise Fault('BUSY','current host review pending; complete or pause it first')
   if scope=='repair':
    invalid=[read(f.name) for f in out.glob('call-*.json') if not isinstance(read(f.name).get('parsed'),dict)]
    if s.get('error')!='INVALID_JSON_REQUIRES_EXPLICIT_CORRECTION' or not invalid or any(x.get('state')!='settled' for x in invalid) or config['extract']!='deepseek-flash':raise Fault('OUTCOME_UNKNOWN','repair only settled, proven invalid JSON; unknown calls are never replayed')
   elif s.get('state')=='blocked':raise Fault('OUTCOME_UNKNOWN','inspect receipts and explicitly resolve blocked step; no blind replay')
   if scope=='publish':
    expected={p['index'] for p in read('selection.json',{}).get('packets',[])}
    if not expected or set(s.get('completed',[]))!=expected:raise Fault('INPUT','complete exact frozen source set before publication')
    plan=read('plan.json',{})
    if plan.get('architecture_checkpoints'):
     checkpoint_boundary(lambda oid:state.get(oid,actor),out,plan,len(expected),len(expected))
     if str(len(expected)) not in read('architecture-acceptance.json',{}):raise Fault('CHECKPOINT_REQUIRED','accept final architecture checkpoint before publication')
   approved=state.get(config['canonical_ref']['object_id'],actor)
   if approved['revision']!=config['canonical_ref']['revision'] or approved['payload'].get('config')!={k:v for k,v in config.items() if k!='canonical_ref'}:raise Fault('ROUTE_TAMPERED','local route projection differs from canonical approved route')
   run=state.put(request(object_new('Artifact',dict(locator='workflow-run:'+str(operation_id),name='UI authorized workflow execution',media_type='application/json',sha256=sha(canonical({'scope':scope,'config':config}).encode()),scope=scope,applied_config=config,started_at=now()),visibility='private'),operation_id=operation_id),actor)['object']
   s.update(state='queued',pause=False,run_ref={'object_id':run['object_id'],'revision':run['revision']});atomic(out/'status.json',canonical(s))
   atomic(out/'control.json',canonical({'pause':False,'run_ref':s['run_ref']}))
   repo=Path(__file__).resolve().parents[1];env=dict(os.environ,UACF_WORKFLOW_ROOT=str(state.root),UACF_WORKFLOW_DIRECTORY=batch['directory']);log=open(out/'worker-public.log','a',encoding='utf-8')
   WORKER=subprocess.Popen([str(repo/'.venv/Scripts/python.exe'),'-X','utf8',str(repo/'ops/e7_workflow.py'),'run',scope],cwd=repo,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));log.close()
   return {'ok':True,'run_ref':s['run_ref'],'scope':scope,'worker_pid':WORKER.pid}
 raise Fault('UNSUPPORTED','unknown workflow action')
