"""Durable host observations only. Never queue/replay dispatches or external actions."""
import json
from pathlib import Path
from .util import Fault,atomic,canonical,sha

def enqueue(root,event):
    required=['event_id','source_host','host_epoch','source_seq','type','occurred_at','observed_at','schema_version','visibility','payload']
    if any(k not in event for k in required):raise Fault('INPUT','complete HostEvent required')
    if event['type'] not in ['observation','tool_result','host_status']:raise Fault('PERMISSION','spool only observations; no commands or paid calls')
    from .state import State
    from .state import uuid_ok
    uuid_ok(event['event_id'])
    from .batch3 import assert_no_secrets
    assert_no_secrets(State(root),event)
    dest=Path(root)/'data/host-spool'/event['event_id'];dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and json.loads(dest.read_text())!=event:raise Fault('EVENT_CONFLICT','spooled event id differs')
    atomic(dest,canonical(event));return {'ok':True,'event_id':event['event_id'],'hash':sha(event),'sync':'pending'}

def sync(root,send,source_host=None):
    receipts=[]
    for p in sorted((Path(root)/'data/host-spool').glob('*')):
        event=json.loads(p.read_text())
        if source_host is not None and event['source_host']!=source_host: continue
        r=send(event) # caller may be offline: leave file on any exception
        if not r.get('ok'):raise Fault('SYNC','durable acknowledgement required')
        dest=Path(root)/'data/host-spool-ack'/p.name;dest.parent.mkdir(parents=True,exist_ok=True)
        atomic(dest,canonical({'event':event,'acknowledgement':r}));p.unlink(missing_ok=True)
        receipts.append(r)
    return {'ok':True,'receipts':receipts,'external_actions_replayed':False}
