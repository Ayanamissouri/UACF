"""Finite registered read probe with persisted repeat-stop and actual reprepare.

Hashes identify an experiment/revision, never semantic equivalence. The gateway
does not intercept arbitrary Codex tools. Reprepare returns real bounded files.
"""
from pathlib import Path
from .util import Fault,sha,file_hash,now
from .state import request
from .fabric import owner,vector

def check(task):
 if task['payload'].get('retry_guard',{}).get('blocked'):raise Fault('REREAD_REQUIRED','registered attempts stopped; read current command lane and declared structure before another registered action')

def dispatch(state,actor,action,args):
 owner(actor);task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract':raise Fault('INPUT','registered Task required')
 if task['revision']!=args['expected_revision']:raise Fault('REVISION_CONFLICT','guard requires exact current Task')
 cfg=dict(task['payload'].get('retry_guard',{}));paths=cfg.get('read_paths',[])
 if not cfg.get('enabled') or not paths:raise Fault('GUARD_SCOPE','explicit enabled Task read-path scope required')
 limit=cfg.get('max_same_experiment',3)
 if type(limit)!=int or not 1<=limit<=10:raise Fault('GUARD_SCOPE','bounded repeat limit required')
 def read(path):
  p=Path(path).resolve()
  if str(p) not in [str(Path(x).resolve()) for x in paths]:raise Fault('PERMISSION','probe restricted to exact declared structure files')
  if not p.is_file() or p.stat().st_size>262144:raise Fault('GUARD_SCOPE','declared bounded file missing/too large')
  return dict(path=str(p),sha256=file_hash(p),text=p.read_text(encoding='utf-8')[:6000],truncated=p.stat().st_size>6000)
 history=list(cfg.get('events',[]));result={}
 if action=='guard_reprepare':
  if not args.get('correction_basis'):raise Fault('REREAD_BASIS','explain the changed hypothesis after structure/context re-read')
  structures=[read(x) for x in paths[:6]]
  from .command_ledger import capsule
  result=dict(structures=structures,mandatory_commands=capsule(task),host_understanding='not proven by hashes or file delivery',previous_block=cfg.get('blocked'),basis=args['correction_basis'])
  cfg.update(blocked=False,counts={},last_reprepare_at=now(),reprepare_identity=sha(result))
 else:
  check(task);path=str(Path(args['path']).resolve());ident=sha(['registered-read-probe-v1',path]);counts=dict(cfg.get('counts',{}));n=counts.get(ident,0)
  if n>=limit:cfg['blocked']=True;result=dict(allowed=False,code='REREAD_REQUIRED',experiment_hash=ident,observed_attempts=n)
  else:
   try:observation=read(path);result=dict(allowed=True,experiment_hash=ident,observation=observation);counts[ident]=n+1
   except Fault as e:
    if e.code=='PERMISSION':raise
    result=dict(allowed=False,experiment_hash=ident,observation_error=e.code,detail=str(e));counts[ident]=n+1
    if counts[ident]>=limit:cfg['blocked']=True;result['code']='REREAD_REQUIRED'
   cfg['counts']=counts
  # Descriptions/timeouts are deliberately absent from identity; distinct
  # file targets remain distinct, without claiming semantic inference.
 history.append(dict(action=action,at=now(),allowed=result.get('allowed'),experiment_hash=result.get('experiment_hash'),reprepare=action=='guard_reprepare'))
 cfg['events']=history[-100:];task['payload']['retry_guard']=cfg;obj={k:task[k] for k in ['object_id','object_type','status','visibility','payload']};new=state.put(request(obj,task['revision']),actor)['object']
 return dict(ok=True,task_ref=vector(new),**result,scope='actual registered bounded file-read gateway and registered delivery; arbitrary host tools not intercepted',new_model_calls=0)
