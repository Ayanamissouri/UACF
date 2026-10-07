"""Owner reconciliation of durable native observations; never replay Host work."""
import json,uuid
from .util import Fault,sha,canonical,now
from .state import object_new,request,uuid_ok
from .fabric import vector

def inventory(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','Owner native inventory required')
 if set(args)!={'task_id'}:raise Fault('INPUT','one explicitly mapped Task required')
 task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract':raise Fault('INPUT','Task required')
 bindings=json.loads((state.data/'host-bindings.json').read_text());results=[]
 with state.db() as c:
  pending=c.execute("select operation_id,actor,request_hash from command_operations where state='pending' and action='host_event' order by recorded_at limit 50").fetchall()
  events=c.execute('select payload from host_events order by rowid desc limit 512').fetchall()
 for row in pending:
  match=None
  for raw in events:
   event=json.loads(raw['payload']);p=event['payload']
   if bindings.get(event['source_host'],{}).get(p.get('native_session_id'))!=task['object_id']:continue
   original=dict(action='host_event',args=event,operation_id=row['operation_id'],actor=row['actor'],correlation_id=str(uuid.uuid5(uuid.UUID(row['operation_id']),'correlation')),schema_version='1.0',scope='action:host_event',expected_revision=0)
   if sha(original)==row['request_hash']:
    match={'native_operation':row['operation_id'],'event_id':event['event_id'],'native_type':p.get('native_type'),'task_ref':vector(task),'observed':True};break
  if match:results.append(match)
 return dict(ok=True,rows=results,scope='last512 durable events and first50 pending native commands; this exact mapped Task only',provider_calls=0,unmatched_pending=len(pending)-len(results),unmatched_reason='outside bounded inventory or another Task; not resolved')

def reconcile(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','Owner native reconciliation required')
 if set(args)!={'native_operation','event_id','task_id','task_revision'}:raise Fault('INPUT','exact operation, event and current Task required')
 for key in ['native_operation','event_id','task_id']:uuid_ok(args[key])
 task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract' or task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','reconciliation Task changed')
 with state.db() as c:
  row=c.execute('select * from command_operations where operation_id=?',(args['native_operation'],)).fetchone()
  saved=c.execute('select rowid,payload,request_hash from host_events where event_id=?',(args['event_id'],)).fetchone()
 if not row or row['action']!='host_event' or not saved:raise Fault('NOT_FOUND','original command and durable Host event required')
 if row['state']=='done':return dict(ok=True,already_recorded=True,operation=json.loads(row['response']),provider_calls=0,host_work_replayed=False)
 event=json.loads(saved['payload']);payload=event['payload'];sid=payload.get('native_session_id');host=event['source_host']
 bindings=json.loads((state.data/'host-bindings.json').read_text())
 if bindings.get(host,{}).get(sid)!=task['object_id']:raise Fault('MAPPING_CONFLICT','event is not this explicitly mapped Task')
 original=dict(action='host_event',args=event,operation_id=row['operation_id'],actor=row['actor'],correlation_id=str(uuid.uuid5(uuid.UUID(row['operation_id']),'correlation')),schema_version='1.0',scope='action:host_event',expected_revision=0)
 if sha(event)!=saved['request_hash'] or sha(original)!=row['request_hash']:raise Fault('OPERATION_CONFLICT','durable event does not match original authenticated command')
 from .learning import oid,after_work,folder
 source=None;canonical_event=None
 # Preserve legacy duplicate events, but reuse a source already captured from
 # the same actual native completion instead of generating another source.
 if payload.get('native_type')=='turn/end' and payload.get('observed_status')=='completed' and payload.get('completed_at') is not None:
  with state.db() as c:
   candidates=c.execute("select payload from host_events where rowid<=? and source_host=? and json_extract(payload,'$.payload.native_session_id')=? and json_extract(payload,'$.payload.native_turn_id')=? and json_extract(payload,'$.payload.native_type')='turn/end' and json_extract(payload,'$.payload.completed_at')=? order by rowid",(saved['rowid'],host,sid,payload.get('native_turn_id'),payload['completed_at'])).fetchall()
  for candidate in candidates:
   prior=json.loads(candidate['payload'])
   try:source=state.get(oid(state,'Artifact',['native-source',prior['event_id']]),actor)
   except Fault as error:
    if error.code!='NOT_FOUND':raise
    continue
   if source['payload'].get('native_session_id')!=sid:raise Fault('MAPPING_CONFLICT','captured source session differs')
   canonical_event=prior['event_id'];break
 capture={'state':'source_already_captured','source_ref':vector(source),'canonical_end_event_id':canonical_event,'duplicate_completion':canonical_event!=event['event_id']} if source else after_work(state,row['actor'],event)
 with state.db() as c:
  mark=c.execute('select contiguous from host_watermarks where source_host=? and host_epoch=?',(host,event['host_epoch'])).fetchone()
  maximum=c.execute('select max(source_seq) from host_events where source_host=? and host_epoch=?',(host,event['host_epoch'])).fetchone()[0]
 observation={'method':'authenticated pending Host observation reconciliation against durable envelope and source','original_operation_id':row['operation_id'],'event_id':event['event_id'],'capture':capture,'provider_calls':0,'host_work_replayed':False,'semantic_acceptance':False,'at':now()}
 evidence=state.put(request(object_new('Evidence',{'observation':observation,'input_vector':[vector(task)]})),actor)['object']
 response=dict(ok=True,contiguous=mark[0],max_seq=maximum,gap=mark[0]<maximum,duplicate=True,reconciled=True,capture=capture,evidence_ref=vector(evidence),operation_id=row['operation_id'],request_hash=row['request_hash'])
 with state.db() as c:
  c.execute('BEGIN IMMEDIATE')
  current=c.execute('select state,request_hash from command_operations where operation_id=?',(row['operation_id'],)).fetchone()
  if current['state']!='pending' or current['request_hash']!=row['request_hash']:raise Fault('REVISION_CONFLICT','original command changed during reconciliation')
  c.execute("update command_operations set state='done',response=? where operation_id=?",(canonical(response),row['operation_id']))
 return dict(ok=True,reconciled_operation_id=row['operation_id'],evidence_ref=vector(evidence),capture=capture,provider_calls=0,host_work_replayed=False,semantic_acceptance=False)
