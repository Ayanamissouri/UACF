"""Zero-model metadata gate: meaningful progress, bounded cues, debounce and overdue check."""
import datetime,json,time
from .util import Fault,sha,now
from .state import object_new,request
from .fabric import vector

POLICY={'schema':'uacf-archive-trigger-1','min_interval_seconds':900,'idle_check_seconds':7*86400,'periodic_check_seconds':86400,'aggregate_signal_count':3,'max_cue_bytes':1024,'model_calls':0}
PROMPT='Use only the current public work node. Return explicit_request, correction, requirement_change, progress, owner_satisfied, completion, dissatisfaction, severity, short_daily. Do not infer personality or factual failure from tone. No full-history reread. Unknown stays unknown; this annotation is not native delivery proof.'
def stamp(s):
 try:
  d=datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
  if d.tzinfo is None:raise ValueError()
  return d.timestamp()
 except (ValueError,AttributeError):raise Fault('INPUT','timezone-aware timestamp required')
def decide(features,previous,timestamp):
 if set(features)-{'explicit_request','correction','requirement_change','progress','owner_satisfied','completion','dissatisfaction','severity','short_daily','cue','observed_event_id','last_work_at'}:raise Fault('INPUT','bounded trigger feature schema')
 for k in ['explicit_request','correction','requirement_change','progress','owner_satisfied','completion','dissatisfaction','short_daily']:
  if k in features and type(features[k]) is not bool:raise Fault('INPUT','boolean signals required')
 if features.get('severity','ordinary') not in ['ordinary','critical']:raise Fault('INPUT','severity scope')
 cue=features.get('cue','')
 if not isinstance(cue,str) or len(cue.encode())>POLICY['max_cue_bytes']:raise Fault('LIMIT','do not send full context for a trigger check')
 # Emotion alone never cancels work or proves an error. Explicit intent prevails.
 elapsed=timestamp-previous['last_capture_at'] if 'last_capture_at' in previous else float('inf');lastwork=stamp(features['last_work_at']) if features.get('last_work_at') else previous.get('last_work_at',timestamp)
 if lastwork>timestamp:raise Fault('INPUT','future work timestamp')
 urgent=features.get('explicit_request') or features.get('correction') and features.get('severity')=='critical'
 important=any(features.get(k) for k in ['correction','requirement_change','progress']) or features.get('dissatisfaction') and features.get('correction')
 pending=previous.get('pending_signal_count',0)+(1 if important else 0)
 due=timestamp-lastwork>=POLICY['idle_check_seconds'] or timestamp-previous.get('last_check_at',timestamp)>=POLICY['periodic_check_seconds']
 if urgent:action='prepare_incremental';reason='explicit request or critical correction, current node only'
 elif features.get('short_daily'):action='metadata_check' if due else 'defer';reason='daily work stays lightweight; overdue metadata still checked'
 elif due and not (features.get('completion') or features.get('owner_satisfied')):action='metadata_check';reason='mandatory overdue metadata inspection precedes extraction cooldown'
 elif elapsed<POLICY['min_interval_seconds']:action='aggregate';reason='debounce: retain meaningful signals without another extraction'
 elif features.get('completion') or features.get('owner_satisfied'):action='prepare_incremental';reason='explicit completion/satisfaction; not mere assistant reply end'
 elif pending>=POLICY['aggregate_signal_count']:action='prepare_incremental';reason='meaningful accumulated work changes'
 elif due:action='metadata_check';reason='mandatory overdue metadata check; not permission to replay or paid extraction'
 else:action='aggregate' if important else 'defer';reason='wait for meaningful work node'
 return {'action':action,'reason':reason,'pending_signal_count':pending,'model_calls':0,'max_cue_bytes':POLICY['max_cue_bytes'],'normal_end_observed':False,'automatic_archive_completed':False}
def observations(state,tid):
 with state.db() as c:
  rows=c.execute("select v.envelope from objects o join object_revisions v on v.object_id=o.id and v.revision=o.head where o.type='Evidence' and json_extract(v.envelope,'$.payload.trigger_contract')=? and json_extract(v.envelope,'$.payload.task_id')=? order by v.recorded_at desc limit 1",(POLICY['schema'],tid)).fetchall()
 return json.loads(rows[0][0]) if rows else None

def previous_state(state,task,old):
 previous=dict(old['payload']['observation']['next_state']) if old else {'last_work_at':stamp(task['recorded_at'])}
 with state.db() as c:
  row=c.execute("select max(v.recorded_at) from objects o join object_revisions v on v.object_id=o.id and v.revision=o.head where o.type='Artifact' and json_extract(v.envelope,'$.payload.learning_task_ref.object_id')=? and json_extract(v.envelope,'$.payload.locator') like 'native-learning:%'",(task['object_id'],)).fetchone()
 if row and row[0]:
  captured=stamp(row[0])
  if captured>previous.get('last_capture_at',0):previous.update(last_capture_at=captured,pending_signal_count=0)
 return previous
def check(state,actor,args):
 if actor not in ['owner','codex','dsh','pi']:raise Fault('PERMISSION','authorized trigger annotation only')
 if set(args)!={'task_id','task_revision','features'}:raise Fault('INPUT','exact Task and bounded features')
 task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract' or task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','current Task revision')
 old=observations(state,task['object_id']);previous=previous_state(state,task,old)
 timestamp=stamp(now());features=args['features'];fingerprint=sha([vector(task),features])
 if actor!='owner' and not features.get('observed_event_id'):raise Fault('CAPABILITY_GAP','host trigger requires a real mapped event')
 if old and old['payload']['observation']['fingerprint']==fingerprint and previous==old['payload']['observation']['next_state'] and (features.get('observed_event_id') or timestamp-previous.get('last_check_at',0)<POLICY['periodic_check_seconds']):return {'ok':True,'evidence_ref':vector(old),'duplicate':True,**old['payload']['observation']['decision']}
 decision=decide(features,previous,timestamp);event=features.get('observed_event_id')
 observed=False
 if event:
  with state.db() as c:row=c.execute('select payload from host_events where event_id=?',(event,)).fetchone()
  if not row:raise Fault('CAPABILITY_GAP','cannot invent a native event for trigger activation')
  ev=json.loads(row[0]);sid=ev['payload'].get('native_session_id');bindings=json.loads((state.data/'host-bindings.json').read_text());observed=bindings.get(ev['source_host'],{}).get(sid)==task['object_id']
  if actor!='owner' and ev['source_host']!=actor:raise Fault('PERMISSION','another host event cannot authorize this annotation')
  if not observed:raise Fault('MAPPING_CONFLICT','trigger event belongs to another Task')
 decision['source_delivery']='real mapped event observed' if observed else 'host annotation only; native event delivery partial'
 nextstate=dict(previous,last_check_at=timestamp,pending_signal_count=decision['pending_signal_count'])
 if features.get('progress') or features.get('correction') or features.get('requirement_change'):nextstate['last_work_at']=timestamp
 if features.get('completion') or features.get('owner_satisfied'):nextstate['last_completion_at']=timestamp
 # Only real source enqueue marks capture. Merely requesting it does not.
 obj=object_new('Evidence',{'trigger_contract':POLICY['schema'],'task_id':task['object_id'],'observation':{'fingerprint':fingerprint,'features':features,'decision':decision,'next_state':nextstate},'input_vector':[vector(task)]},visibility='private');saved=state.put(request(obj,actor=actor),actor)['object']
 return {'ok':True,'evidence_ref':vector(saved),'duplicate':False,**decision}
def status(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','local private trigger status')
 task=state.get(args['task_id'],actor);o=observations(state,task['object_id'])
 return {'ok':True,'policy':POLICY,'structured_prompt':PROMPT,'latest':o['payload']['observation'] if o else None,'periodic_worker':'service scans opted-in adaptive Tasks; metadata only, no provider calls','native_automatic_delivery':'partial unless real mapped events received'}

def maintain(state):
 # Cache belongs to this State instance, so another root cannot suppress its sweep.
 clock=time.monotonic()
 if clock-getattr(state,'_archive_trigger_sweep',-60)<60:return
 state._archive_trigger_sweep=clock
 with state.db() as c:
  query="select o.id,v.envelope from objects o join object_revisions v on v.object_id=o.id and v.revision=o.head where o.type='TaskContract' and json_extract(v.envelope,'$.payload.learning_capture_policy.mode')='adaptive' and coalesce(json_extract(v.envelope,'$.payload.execution_state'),'running') not in ('stopped','review_pending')"
  cursor=getattr(state,'_archive_trigger_cursor','')
  rows=c.execute(query+' and o.id>? order by o.id limit 64',(cursor,)).fetchall()
  if not rows:rows=c.execute(query+' order by o.id limit 64').fetchall()
 if rows:state._archive_trigger_cursor=rows[-1][0]
 for row in rows:
  task=json.loads(row[1]);old=observations(state,task['object_id']);previous=previous_state(state,task,old);timestamp=stamp(now())
  if timestamp-previous.get('last_check_at',0)<POLICY['periodic_check_seconds']:continue
  check(state,'owner',{'task_id':task['object_id'],'task_revision':task['revision'],'features':{'last_work_at':datetime.datetime.fromtimestamp(previous['last_work_at'],datetime.timezone.utc).isoformat()}})
