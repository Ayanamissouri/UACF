"""Read two mapped public turns through the official API; never start a model turn.

This observes persisted public items and completedAt, not live hook delivery.
Reasoning items and opaque MCP result bodies are excluded before persistence.
"""
import argparse,json,queue,subprocess,threading,time,uuid,sys,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from uacf.util import Fault,canonical,now,sha,atomic
from uacf.service import call
from uacf.state import State
from uacf.batch3 import assert_no_secrets

def reconcile_event(root,event,operation):
 # A missing local receipt does not prove the authenticated command failed.
 # Query its stable ID before any dispatch; pending outcomes remain pending.
 try:record=call(root,'operation_get',{'operation_id':operation},'codex')['operation']
 except Fault as error:
  if error.code!='NOT_FOUND':raise
 else:
  if record['state']!='done':raise Fault('OUTCOME_UNKNOWN','observer command remains in flight; reconcile before dispatch')
  response=record['response']
  if not response.get('ok'):raise Fault(response.get('code','INTERNAL'),response.get('detail','recorded observer failure'))
  return response
 return call(root,'host_event',event,'codex',operation_id=operation)

def prior_completion(directory,sid,turn,completed_at):
 candidates=[]
 for path in directory.glob('*.json'):
  if path.name.endswith('-receipt.json'):continue
  value=json.loads(path.read_text());payload=value.get('payload',{})
  if payload.get('native_session_id')==sid and payload.get('native_turn_id')==turn and payload.get('native_type')=='turn/end' and payload.get('observed_status')=='completed' and payload.get('completed_at')==completed_at and (directory/(value['event_id']+'-receipt.json')).exists():
   candidates.append(value)
 return min(candidates,key=lambda x:x['observed_at'])['event_id'] if candidates else None

def public_item(item):
 kind=item.get('type');identity=item.get('id')
 if not identity:return None
 if kind=='userMessage':
  text='\n'.join(x['text'] for x in item.get('content',[]) if x.get('type')=='text' and isinstance(x.get('text'),str))
  return {'id':identity,'role':'user','content':text,'coverage':'public text only; attachments excluded'}
 if kind=='agentMessage':return {'id':identity,'role':'assistant','content':item.get('text',''),'phase':item.get('phase'),'coverage':'public agent message'}
 if kind=='commandExecution':return {'id':identity,'role':'tool','content':{k:item[k] for k in ['command','cwd','status','exitCode','durationMs','aggregatedOutput'] if k in item},'coverage':'public command and available native result'}
 if kind=='mcpToolCall':return {'id':identity,'role':'tool','content':{k:item[k] for k in ['server','tool','status','durationMs'] if k in item},'coverage':'metadata only; opaque result body not archived'}
 if kind=='fileChange':return {'id':identity,'role':'tool','content':{'status':item.get('status'),'paths':[x.get('path') for x in item.get('changes',[]) if x.get('path')]},'coverage':'public changed-path metadata; diffs excluded'}
 return None # reasoning, encrypted content, memory and unrecognized types

class Reader:
 def __init__(self,binary,cwd):
  self.p=subprocess.Popen([str(binary),'app-server','--stdio'],cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.q=queue.Queue();self.i=0
  def read():
   for line in self.p.stdout:
    try:self.q.put(json.loads(line))
    except ValueError:pass
  threading.Thread(target=read,daemon=True).start()
  self.rpc('initialize',{'clientInfo':{'name':'uacf-public-observer','version':'1.0'},'capabilities':{'experimentalApi':True}})
  self.p.stdin.write(b'{"method":"initialized"}\n');self.p.stdin.flush()
 def rpc(self,method,args):
  if method not in ['initialize','thread/read','thread/turns/list','thread/items/list']:raise Fault('PERMISSION','observer is read only')
  self.i+=1;self.p.stdin.write((canonical({'id':self.i,'method':method,'params':args})+'\n').encode());self.p.stdin.flush();end=time.monotonic()+30
  while time.monotonic()<end:
   try:r=self.q.get(timeout=.5)
   except queue.Empty:continue
   if r.get('id')!=self.i:continue
   if r.get('error'):raise Fault('CAPABILITY_GAP',canonical(r['error']))
   return r['result']
  raise Fault('CAPABILITY_GAP','public native read timeout')
 def close(self):
  self.p.stdin.close()
  try:self.p.wait(timeout=5)
  except subprocess.TimeoutExpired:self.p.terminate();self.p.wait(timeout=5)

def observe(root,binary,sid,task_id):
 root=Path(root).resolve();bindings=json.loads((root/'data/host-bindings.json').read_text())
 if bindings.get('codex',{}).get(sid)!=task_id:raise Fault('MAPPING_CONFLICT','explicit exact current Task required')
 task=call(root,'get',{'object_id':task_id})['object'];ready=call(root,'context',{'task_id':task_id},'codex')
 if ready.get('status')!='ready':raise Fault('NOT_PREPARED','mandatory context not ready')
 reader=Reader(binary,root);result=[];outdir=root/'data/codex-public-observer';outdir.mkdir(exist_ok=True)
 def deliver(turn,identity,payload,occurred):
  eid=str(uuid.uuid5(uuid.NAMESPACE_URL,'uacf-public-read-v2:'+sid+':'+turn+':'+identity));p=outdir/(eid+'.json');receipt=outdir/(eid+'-receipt.json')
  if receipt.exists():return eid
  if p.exists():event=json.loads(p.read_text())
  else:
   event={'event_id':eid,'source_host':'codex','host_epoch':eid,'source_seq':1,'type':'observation','occurred_at':occurred,'observed_at':now(),'schema_version':'1.0','visibility':'private','payload':dict(payload,native_session_id=sid,native_turn_id=turn,transport='official app-server public paginated read',native_locator='codex://threads/'+sid+'?turn='+turn,live_hook_delivery=False)}
   atomic(p,canonical(event))
  op=str(uuid.uuid5(uuid.UUID(eid),'observation-command'))
  # Unknown commands are reconciled by the service, never by rerunning work.
  response=reconcile_event(root,event,op);atomic(receipt,canonical(response));return eid
 try:
  thread=reader.rpc('thread/read',{'threadId':sid,'includeTurns':False})['thread']
  if thread['id']!=sid or Path(thread['cwd']).resolve()!=root:raise Fault('MAPPING_CONFLICT','actual native thread workspace mismatch')
  turns=reader.rpc('thread/turns/list',{'threadId':sid,'limit':2,'itemsView':'notLoaded','sortDirection':'desc'})['data']
  for turn in reversed(turns):
   occurred=datetime.datetime.fromtimestamp(turn['startedAt'],datetime.timezone.utc).isoformat();cursor=None;count=0;last=None;bounded=False;public_ids=[];has_work=False;has_final=False
   while count<256:
    # A long active turn can exceed the cap. Read the recent public tail so
    # the real final item is observable; earlier watcher receipts are retained.
    params={'threadId':sid,'turnId':turn['id'],'limit':64,'sortDirection':'desc'}
    if cursor:params['cursor']=cursor
    page=reader.rpc('thread/items/list',params)
    for entry in page['data']:
     item=entry.get('item',entry)
     public=public_item(item)
     if public is None:continue
     has_work=has_work or item.get('type') in ['commandExecution','fileChange'] and item.get('status')=='completed'
     has_final=has_final or item.get('type')=='agentMessage' and item.get('phase')=='final'
     try:assert_no_secrets(State(root),public)
     except Fault as error:
      if error.code!='SECRET':raise
      public={'id':public['id'],'role':public['role'],'content':'Public item body withheld by credential filter','withheld_hash':sha(public),'coverage':'identity only; original remains in native host'}
     if len(canonical(public).encode())>24000:public['content']={'bounded_preview':canonical(public['content']).encode()[:24000].decode('utf-8',errors='ignore'),'truncated':True};public['coverage']+='; body truncated'
     last=deliver(turn['id'],public['id'],{'kind':'native_message','native_type':'public/item','message':public},occurred);count+=1;public_ids.append(public['id'])
    cursor=page.get('nextCursor')
    if not cursor:break
   if cursor:bounded=True
   end=None
   if count and turn.get('status')=='completed' and turn.get('completedAt') is not None:
    features={'progress':bool(has_work and has_final)}
    policy=task['payload'].get('learning_capture_policy',{});request_event=policy.get('requested_capture_turns',{}).get(turn['id'])
    if request_event:
     # One exact Owner-recorded request on a real current public user event.
     # It is an annotation, not a new native end or user satisfaction claim.
     with State(root).db() as c:row=c.execute('select payload from host_events where event_id=?',(request_event,)).fetchone()
     if not row:raise Fault('CAPABILITY_GAP','capture request needs a real observed user event')
     ev=json.loads(row[0]);msg=ev['payload'].get('message',{})
     if ev['source_host']!='codex' or ev['payload'].get('native_session_id')!=sid or msg.get('role')!='user':raise Fault('MAPPING_CONFLICT','capture request is not this mapped public user event')
     features['explicit_request']=True
    end=prior_completion(outdir,sid,turn['id'],turn['completedAt'])
    if not end:end=deliver(turn['id'],'completed-public-native:'+str(turn['completedAt']),{'kind':'native_public_status','native_type':'turn/end','observed_status':'completed','completed_at':turn['completedAt'],'coverage':'persisted native completion; selected public items only','bounded_items':bounded,'observed_public_item_ids_hash':sha(public_ids),'learning_features':features,'capture_request_event_id':request_event,'signal_basis':'observable tool work and final output; Owner request is separate from native completion'},datetime.datetime.fromtimestamp(turn['completedAt'],datetime.timezone.utc).isoformat())
   result.append({'turn_id':turn['id'],'status':turn['status'],'public_items':count,'last_public_event_id':last,'normal_end_event_id':end,'bounded_items':bounded})
 finally:reader.close()
 return {'ok':True,'task_ref':{'object_id':task_id,'revision':task['revision']},'turns':result,'live_hook_delivery':False,'model_turns_started':0,'coverage':'two latest explicitly mapped public turns; no full-session acceptance'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--binary',required=True);p.add_argument('--session',required=True);p.add_argument('--task',required=True);p.add_argument('--watch',action='store_true');a=p.parse_args()
 while True:
  try:print(canonical(observe(a.root,a.binary,a.session,a.task)),flush=True)
  except (TimeoutError,Fault) as error:
   if not a.watch or isinstance(error,Fault) and error.code not in ['CORE_UNAVAILABLE','OUTCOME_UNKNOWN']:raise
   print(canonical({'ok':False,'state':'waiting_reconciliation','reason':type(error).__name__,'detail':str(error),'model_turns_started':0,'live_hook_delivery':False}),flush=True)
  if not a.watch:break
  time.sleep(60)
