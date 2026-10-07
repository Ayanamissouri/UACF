"""Explicit public work mapping and checkpoint policy; no synthetic native events."""
import json, threading
from .util import Fault, sha, canonical, atomic
from .fabric import vector
LOCK=threading.RLock()
SIGNALS=['correction','requirement_change','milestone','owner_satisfied','completion']
def bind(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','Owner maps an actual native session')
 host=args.get('host');sid=args.get('native_session_id')
 if host not in ['codex','pi','dsh'] or not isinstance(sid,str) or not 1<=len(sid)<=200 or not args.get('native_locator') or not args.get('authorization'):raise Fault('INPUT','real native identity and explicit authorization required')
 task=state.get(args['task_id'],'owner')
 if task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','map current Task revision')
 # Verify the host can read the whole mandatory dependency chain before mapping.
 state.get(task['object_id'],host)
 with LOCK:
  path=state.data/'host-bindings.json';before=json.loads(path.read_text()) if path.exists() else {}
  if sha(before)!=args.get('expected_binding_hash'):raise Fault('REVISION_CONFLICT','native mappings changed')
  current=before.get(host,{}).get(sid)
  previous_ref=None
  if current and current!=task['object_id']:
   # Same native conversation can continue a new explicitly authorized task.
   # Exact previous head and binding hash prevent accidental window takeover.
   previous_ref=args.get('previous_task_ref')
   previous=state.get(current,'owner')
   if previous_ref!=vector(previous):raise Fault('MAPPING_CONFLICT','explicit exact previous Task revision required for continuation')
   if previous['payload'].get('execution_state') not in ['blocked','stopped','complete']:
    raise Fault('MAPPING_CONFLICT','previous Task is still runnable; preserve its mapping')
   import time
   with state.db() as c:
    has_leases=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='executor_leases'").fetchone()
    if has_leases and c.execute('SELECT 1 FROM executor_leases WHERE task_id=? AND expires>?',(current,time.time())).fetchone():
     raise Fault('LEASE_BUSY','previous Task still has execution authority; preserve mapping')
  from .learning import save_once
  after=json.loads(canonical(before));after.setdefault(host,{})[sid]=task['object_id']
  decision=save_once(state,'Decision',dict(outcome='map explicit current public work',basis=args['authorization'],native_locator=args['native_locator'],host=host,native_session_id=sid,task_ref=vector(task),previous_task_ref=previous_ref,previous_task_preserved=True,before_hash=sha(before),after_hash=sha(after),automatic_callback_verified=False,input_vector=[vector(task)]+([previous_ref] if previous_ref else [])),['host-binding',host,sid,vector(task),sha(before)])
  atomic(path,canonical(after))
  return dict(ok=True,decision_ref=vector(decision),task_ref=vector(task),binding_hash=sha(after),automatic_callback_verified=False)
def capture_gate(task,event):
 policy=task['payload'].get('learning_capture_policy')
 if not policy:policy={'mode':'milestones'}
 mode=policy.get('mode','milestones')
 if mode=='lightweight':return 'defer'
 signal=event['payload'].get('learning_signal')
 if signal in SIGNALS:return 'capture'
 if mode=='work_end' and event['payload'].get('native_type') in ['Stop','turn/end']:return 'capture'
 return 'defer' # keep raw public events; no length/emotion-as-verdict heuristic
def checkpoint(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','explicit Owner checkpoint required')
 if args.get('signal') not in SIGNALS:raise Fault('INPUT','meaningful checkpoint signal required')
 task=state.get(args['task_id'],'owner')
 if task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','checkpoint current Task')
 bindings=json.loads((state.data/'host-bindings.json').read_text())
 host=args['host'];sid=args['native_session_id']
 if bindings.get(host,{}).get(sid)!=task['object_id']:raise Fault('MAPPING_CONFLICT','exact native Task required')
 with state.db() as c:
  row=c.execute('select payload from host_events where event_id=?',(args['native_event_id'],)).fetchone()
 if not row:raise Fault('CAPABILITY_GAP','no real observed native event to checkpoint')
 event=json.loads(row[0])
 if event['source_host']!=host or event['payload'].get('native_session_id')!=sid:raise Fault('MAPPING_CONFLICT','event from another native session')
 from .learning import save_once,after_work
 ev=save_once(state,'Evidence',dict(observation=dict(method='Owner meaningful checkpoint on existing public native event',signal=args['signal'],native_event_id=event['event_id'],basis=args.get('basis',''),synthetic_native_event=False),input_vector=[vector(task)]),['work-checkpoint',args])
 # The checkpoint annotation is an interpretation of an existing event, not a
 # fabricated Stop/turn-end or rewritten host history.
 annotated=json.loads(canonical(event));annotated['payload']['learning_signal']=args['signal']
 if 'features' in args:
  # Owner interpretation remains an annotation on a real source event.
  # archive_trigger validates the finite feature schema and byte budget.
  annotated['payload']['learning_features']=args['features']
 result=after_work(state,host,annotated,checkpoint=True)
 return dict(ok=True,evidence_ref=vector(ev),capture=result,normal_end_observed=event['payload'].get('native_type') in ['Stop','turn/end'])
