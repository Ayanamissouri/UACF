"""Claude Code public lifecycle adapter to the same canonical work admission.
No model dispatch; no transcript/private reasoning reads; unavailable gate denies tools.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from uacf.service import call
from uacf.util import now,uid

def run(root,event):
 sid=event.get('session_id');kind=event.get('hook_event_name');host='claude_code'
 if not sid:raise ValueError('real Claude Code session_id required')
 base=dict(host=host,native_session_id=sid)
 if kind=='SessionStart':
  return {'hookSpecificOutput':{'hookEventName':kind,'additionalContext':'是否继续使用 UACF 工作？默认继续；不等待回答，只有明确不使用才退出。使用既有任务、预算和派发链路。'}}
 if kind=='UserPromptSubmit':
  r=call(root,'work_enter',dict(base,goal=(event.get('prompt') or 'Claude Code work')[:2500],native_locator='claude-code:session:'+sid),host)
  if r['mode']=='external':return {}
  return {'hookSpecificOutput':{'hookEventName':kind,'additionalContext':json.dumps(dict(notice=r['notice'],task_ref=r['task_ref'],capsule=r['context']['capsule']),ensure_ascii=False)}}
 if kind=='PreToolUse':
  try:r=call(root,'work_admit',dict(base,tool_name=event.get('tool_name',''),tool_input=event.get('tool_input',{}),cwd=event.get('cwd',str(root))),host)
  except Exception as e:r=dict(allowed=False,reason='UACF admission unavailable: '+type(e).__name__)
  if not r.get('allowed'):return {'hookSpecificOutput':{'hookEventName':kind,'permissionDecision':'deny','permissionDecisionReason':r.get('reason','UACF admission refused')}}
  return {}
 if kind in ['PostToolUse','Stop','SessionEnd']:
  status=call(root,'work_status',base,host)
  if (status.get('session') or {}).get('mode')=='external':return {}
  eid=uid();payload=dict(kind='native_hook',native_type=kind,native_session_id=sid,native_tool_call_id=event.get('tool_use_id'))
  for key in ['tool_name','tool_input','tool_response','last_assistant_message']:
   if key in event:payload[key]=event[key]
  observation=dict(event_id=eid,source_host=host,host_epoch=eid,source_seq=1,type='observation',occurred_at=now(),observed_at=now(),schema_version='1.0',visibility='private',payload=payload)
  from uacf.spool import enqueue,sync
  enqueue(root,observation)
  if kind!='SessionEnd':
   try:sync(root,lambda e:call(root,'host_event',e,host),source_host=host)
   except Exception:pass
 return {}

if __name__=='__main__':
 try:print(json.dumps(run(Path(sys.argv[1]).resolve(),json.load(sys.stdin)),ensure_ascii=False))
 except Exception as e:
  print(json.dumps({'decision':'block','reason':'UACF Claude Code adapter failed: '+type(e).__name__}));sys.exit(2)
