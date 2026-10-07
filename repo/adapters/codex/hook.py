"""Trusted Codex command hook: stable public inputs only; no transcript reverse engineering."""
import json, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from uacf.service import call
from uacf.spool import enqueue, sync
from uacf.util import now, uid, sha, Fault, atomic, canonical

def run(root, event):
    host_id = event.get('session_id'); kind = event.get('hook_event_name')
    if not host_id or kind not in ['UserPromptSubmit','Stop','PostToolUse','SessionStart','SessionEnd','Interrupt']:
        raise Fault('INPUT','supported public hook and native session ID required')
    binding_path = root/'data/host-bindings.json'
    bindings = json.loads(binding_path.read_text()) if binding_path.exists() else {}
    task = bindings.get('codex',{}).get(host_id)
    # An unmapped session is not licensed for archive capture; keep other chats untouched.
    if not task: return {'continue':True}
    payload = {'kind':'native_hook','native_session_id':host_id,'native_turn_id':event.get('turn_id'),
               'native_type':kind,'source_version':bindings.get('codex_version','unknown')}
    for key in ['prompt','last_assistant_message','tool_name','tool_use_id','tool_input','tool_response']:
        if key in event: payload[key]=event[key]
    payload['content_hash']=sha(payload)
    # Public native locators deduplicate delivery, never execution. Missing locator stays explicit.
    locator=event.get('tool_use_id') if kind=='PostToolUse' else event.get('turn_id') if kind in ['UserPromptSubmit','Stop','Interrupt'] else None
    payload['deduplication']='native_locator' if locator else 'unavailable_no_native_event_locator'
    eid=str(uuid.uuid5(uuid.NAMESPACE_URL,'uacf:codex:'+host_id+':'+kind+':'+str(locator))) if locator else uid()
    observation={'event_id':eid,'source_host':'codex','host_epoch':eid,'source_seq':1,
        'type':'observation','occurred_at':now(),'observed_at':now(),'schema_version':'1.0','visibility':'private','payload':payload}
    for prior in [root/'data/host-spool'/eid,root/'data/host-spool-ack'/eid]:
        if prior.exists():
            saved=json.loads(prior.read_text());saved=saved.get('event',saved)
            if saved['payload']!=payload:raise Fault('EVENT_CONFLICT','native hook locator content changed')
            observation=saved;break
    if not (root/'data/host-spool-ack'/eid).exists():enqueue(root,observation)
    # End/Interrupt have a native <=3s deadline: durable queue first; next normal hook drains.
    try:
        if kind not in ['SessionEnd','Interrupt']:sync(root,lambda e:call(root,'host_event',e,'codex'),source_host='codex')
    except (Fault,OSError): pass
    if kind == 'Stop':
        try:
            turn=event.get('turn_id')
            if turn:
                prepared=json.loads((root/'data/codex-prepared'/(sha([host_id,turn])+'.json')).read_text())
                call(root,'artifact_capture',{'task_id':task,'task_revision':prepared['task_revision'],'native_session_id':host_id},'codex')
        except (Fault,OSError):pass # source product remains; failure never restarts a tool/model
    if kind != 'UserPromptSubmit': return {'continue':True}
    try: prepared=call(root,'context',{'task_id':task},'codex')
    except (Fault,OSError) as error: return {'decision':'block','reason':'UACF required context unavailable: '+type(error).__name__}
    if not prepared.get('ok') or prepared.get('status')!='ready':
        return {'decision':'block','reason':'UACF required context: '+str(prepared.get('status',prepared.get('code')))}
    if event.get('turn_id'):
        atomic(root/'data/codex-prepared'/(sha([host_id,event['turn_id']])+'.json'),canonical({'task_revision':prepared['capsule']['task_revision']}))
    return {'hookSpecificOutput':{'hookEventName':kind,'additionalContext':json.dumps(prepared['capsule'],ensure_ascii=False)}}

if __name__=='__main__':
    try: print(json.dumps(run(Path(sys.argv[1]).resolve(),json.load(sys.stdin)),ensure_ascii=False))
    except Exception as error:
        # Failure is explicit; never claim prepared/delivered or silently drop mandatory context.
        print(json.dumps({'decision':'block','reason':'UACF hook failed: '+type(error).__name__}));sys.exit(0)
