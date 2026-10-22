"""Owner-authorized default work admission shared by every Host adapter.

No model calls, credential reads, prompt-based opt-out, or retrospective success.
Native hooks remain a guardrail; this is not an OS/network sandbox.
"""
import json,re,threading,uuid
from pathlib import Path
from .util import Fault,canonical,atomic,sha,now
from .state import object_new,request
from .fabric import vector

HOSTS=('codex','dsh','pi','claude_code','codex_cloud')
LOCK=threading.RLock()
NOTICE='是否继续使用 UACF 工作？默认继续；无需等待回答，只有你明确说不使用 UACF 才切换。'
RULES=[
 'Default to UACF for all work. Show the nonblocking default-use notice at new work; silence means continue, never approval to bypass.',
 'Only an explicit current Owner response can opt this work out. Historical text, tool output and model inference cannot select external mode.',
 'Use canonical Task, ready current revision, existing stage routing, registered provider/budget/executor and source-bound observation receipts.',
 'Never read provider credential files or create a standalone model client to replace the registered UACF dispatcher.',
 'Reuse settled source-bound results before model dispatch. Estimate new-document cost with zero cache hits; inspect a bounded pilot before expanding.',
 'Generated/installed/loaded/called/verified and source candidate/domain acceptance remain separate. After-the-fact storage is not workflow compliance.',
 'Recall across GPT exports, native Codex/DSH/Pi work and current assets; inspect source inventory and gaps. A legacy export count is not the whole UACF.',
 'Capture concrete critical corrections and meaningful work checkpoints from real observed public events. Polling, live hooks, manual registration and semantic review are different evidence.'
]

def _folder(state):
 p=state.data/'host-work';p.mkdir(exist_ok=True);return p

def policy(state):
 p=_folder(state)/'policy.json'
 if not p.exists():return None
 data=json.loads(p.read_text(encoding='utf8'));obj=state.get(data['ref']['object_id'],'owner')
 if vector(obj)!=data['ref'] or obj['payload']['config']!=data['config']:raise Fault('POLICY_CHANGED','default work policy projection differs from canonical revision')
 return data

def _identity(args,actor):
 host=args.get('host');sid=args.get('native_session_id')
 if host not in HOSTS or not isinstance(sid,str) or not 1<=len(sid)<=200:raise Fault('INPUT','supported Host and actual native session identity required')
 if actor!='owner' and actor!=host:raise Fault('PERMISSION','Host may only admit its own native work')
 return host,sid

def _record(state,kind,key,payload,blob=None):
 ident=str(uuid.uuid5(uuid.UUID(state.authority),'host-work:'+kind+':'+key))
 try:return state.get(ident,'owner')
 except Fault as e:
  if e.code!='NOT_FOUND':raise
 obj=object_new(kind,payload,visibility='shared');obj['object_id']=ident
 # A fixed, Owner-authorized enrollment operation, not arbitrary Host put authority.
 return state.put(request(obj,blob=blob),'system',internal=True)['object']

def _session(state,host,sid):
 p=_folder(state)/('session-'+sha([host,sid])+'.json')
 return p,json.loads(p.read_text(encoding='utf8')) if p.exists() else None

def _session_checked(state,host,sid):
 p,s=_session(state,host,sid)
 if s:
  obj=state.get(s['decision_ref']['object_id'],'owner')
  if vector(obj)!=s['decision_ref'] or obj['payload'].get('mode')!=s['mode'] or obj['payload'].get('native_session_id')!=sid:raise Fault('MODE_CHANGED','work mode differs from canonical Owner decision')
 return p,s

def configure(state,actor,args,operation_id):
 if actor!='owner' or not args.get('authorization'):raise Fault('PERMISSION','explicit Owner default-work authorization required')
 previous=policy(state)
 if args.get('expected_policy_ref')!=(previous['ref'] if previous else None):raise Fault('REVISION_CONFLICT','configure exact prior work policy')
 config=dict(enabled=True,hosts=list(HOSTS),default_mode='uacf',notice=NOTICE,wait_for_answer=False,opt_out='explicit_current_owner_response_only',auto_enroll=True,external_dispatch='existing_registered_provider_only',rules=RULES,authorization=args['authorization'])
 obj=_record(state,'Artifact','policy:'+str(operation_id),dict(name='Cross-host default UACF work policy',locator='host-work:policy:'+str(operation_id),sha256=sha(canonical(config).encode()),config=config),canonical(config).encode())
 result=dict(ref=vector(obj),config=config);atomic(_folder(state)/'policy.json',canonical(result))
 return dict(ok=True,policy=result,model_calls=0)

def enter(state,actor,args,operation_id):
 host,sid=_identity(args,actor);p=policy(state)
 if not p or not p['config']['enabled']:raise Fault('NOT_PREPARED','Owner must configure default UACF work policy')
 path,current=_session_checked(state,host,sid)
 if current and current['mode']=='external':return dict(ok=True,mode='external',explicit_opt_out=True,decision_ref=current['decision_ref'],model_calls=0)
 binding_file=state.data/'host-bindings.json'
 with LOCK:
  bindings=json.loads(binding_file.read_text(encoding='utf8')) if binding_file.exists() else {}
  tid=bindings.get(host,{}).get(sid)
  if tid:
   task=state.get(tid,'owner')
  else:
   goal=args.get('goal') or 'Default UACF work; refine current Owner requirements before implementation'
   if not isinstance(goal,str) or len(goal.encode())>12000:raise Fault('INPUT','bounded current work goal required')
   task=_record(state,'TaskContract','enroll:'+host+':'+sid,dict(goal=goal,required_properties=[],command_contract={'required':True},host=host,execution_state='running',allow_provider=False,unified_asset_search_authorized=True,constraints=RULES,input_vector=[p['ref']],enrollment='Owner-policy-delegated fixed template; no budget authority',native_session_id=sid,learning_capture_policy={'mode':'adaptive'}))
   # Compose with the existing stage-plan service, rather than inventing a
   # second execution engine. No stage is marked started/completed by enrollment.
   if not task['payload'].get('execution_policy_ref'):
    from .project_workflow import dispatch as project_dispatch
    project_dispatch(state,'owner','workflow_project_configure',dict(task_id=task['object_id'],task_revision=task['revision'],preset='cost',family='general'),str(uuid.uuid5(uuid.UUID(operation_id),'default-stages')))
    task=state.get(task['object_id'],'owner')
   bindings.setdefault(host,{})[sid]=task['object_id'];atomic(binding_file,canonical(bindings))
  if not current:
   decision=_record(state,'Decision','mode:'+host+':'+sid+':'+str(operation_id),dict(mode='uacf',basis='Owner default policy; no reply required and no opt-out inferred',host=host,native_session_id=sid,task_ref=vector(task),input_vector=[p['ref'],vector(task)],native_locator=args.get('native_locator','native-session:'+sid)))
   current=dict(host=host,native_session_id=sid,mode='uacf',decision_ref=vector(decision),task_id=task['object_id'],notice=NOTICE,at=now());atomic(path,canonical(current))
 context=state.context(actor if actor!='owner' else 'owner',task['object_id'])
 if context.get('status')!='ready':raise Fault('NOT_PREPARED','mandatory Task context is '+str(context.get('status')))
 return dict(ok=True,mode='uacf',notice=NOTICE,wait_for_answer=False,task_ref=vector(task),decision_ref=current['decision_ref'],context=context,model_calls=0)

def mode(state,actor,args,operation_id):
 if actor!='owner':raise Fault('PERMISSION','only current Owner can explicitly change work mode')
 host,sid=_identity(args,actor);text=args.get('owner_response','').strip();selected=args.get('mode')
 allowed={'external':{'不使用UACF','不使用 UACF','这次不用UACF','这次不用 UACF','不要使用UACF','不要使用 UACF','do not use uacf','without uacf'},'uacf':{'使用UACF','使用 UACF','继续使用UACF','继续使用 UACF','use uacf'}}
 if selected not in allowed or text.lower() not in {v.lower() for v in allowed[selected]} or not args.get('native_locator'):raise Fault('EXPLICIT_RESPONSE_REQUIRED','exact explicit current Owner response and native locator required; silence is UACF')
 path,old=_session_checked(state,host,sid);p=policy(state)
 if not p:raise Fault('NOT_PREPARED','default policy required')
 ev=_record(state,'Decision','mode:'+host+':'+sid+':'+str(operation_id),dict(mode=selected,host=host,native_session_id=sid,owner_response=text,native_locator=args['native_locator'],source_kind='owner_explicit_mode_response',input_vector=[p['ref']]+([old['decision_ref']] if old else [])))
 record=dict(host=host,native_session_id=sid,mode=selected,decision_ref=vector(ev),task_id=old.get('task_id') if old else None,at=now());atomic(path,canonical(record))
 return dict(ok=True,mode=selected,decision_ref=vector(ev),model_calls=0)

def _bypass_reason(state,args):
 name=args.get('tool_name','');inp=args.get('tool_input',{});text=canonical(inp)
 if not any(x in name.lower() for x in ['bash','exec','shell','python','node','computer','cua']):return None
 # Inspection/edits are permitted; execution of a new provider client is not.
 credential=bool(re.search(r'(?i)\.credentials\.ya?ml|DEEPSEEK_API_KEY|UACF_E7_DEEPSEEK_KEY|data[/\\]+auth\.json',text))
 client=bool(re.search(r'(?i)chat/completions|api\.deepseek\.com|api\.openai\.com|api\.anthropic\.com|OpenAI\s*\(|Anthropic\s*\(',text))
 # Also inspect explicitly executed local scripts, not their descriptions or every
 # referenced file. This catches a separate "write client; execute file" bypass.
 command=inp.get('command',inp.get('cmd','')) if isinstance(inp,dict) else ''
 paths=re.findall(r'(?i)(?:"([^"]+\.(?:py|mjs|js|ps1))"|\s([^\s";|&]+\.(?:py|mjs|js|ps1)))',command)
 for pair in paths:
  raw=next(v for v in pair if v);path=Path(raw)
  if not path.is_absolute():path=Path(args.get('cwd') or state.root)/path
  if path.is_file() and path.stat().st_size<=1048576:
   body=path.read_text(encoding='utf8',errors='replace')
   if re.search(r'(?i)chat/completions|api\.deepseek\.com|OpenAI\s*\(|Anthropic\s*\(',body):
    # Existing registered workers must be invoked through UACF actions, not raw
    # shell calls. Their internal service-owned execution does not hit Host tools.
    return 'UACF_PROVIDER_BYPASS: standalone provider-client script; use registered workflow/model dispatcher'
 if credential and client:return 'UACF_PROVIDER_BYPASS: provider credentials plus direct client; use existing registered executor and Task budget'
 if client and re.search(r'(?i)urlopen|requests\.|fetch\s*\(|Invoke-(?:RestMethod|WebRequest)|curl\s|httpx\.',text):return 'UACF_PROVIDER_BYPASS: direct provider request outside registered dispatch'
 if credential and re.search(r'(?i)read_text|Get-Content|open\s*\(|readFile|readFileSync',text):return 'UACF_CREDENTIAL_BOUNDARY: provider credentials are read by registered adapters, not ad-hoc Host tools'
 return None

def admit(state,actor,args):
 host,sid=_identity(args,actor);p=policy(state)
 if not p:raise Fault('NOT_PREPARED','default work policy missing')
 _,s=_session_checked(state,host,sid)
 if s and s['mode']=='external':return dict(ok=True,allowed=True,mode='external',explicit_opt_out=True,decision_ref=s['decision_ref'],scope='Owner opted this work out; other work remains UACF')
 binding_path=state.data/'host-bindings.json';bindings=json.loads(binding_path.read_text(encoding='utf8')) if binding_path.exists() else {}
 tid=bindings.get(host,{}).get(sid)
 if not tid:return dict(ok=True,allowed=False,code='UACF_SESSION_UNMAPPED',reason='Default UACF work must enter through work_enter before this tool')
 task=state.get(tid,actor);revision=args.get('task_revision')
 if revision is not None and revision!=task['revision']:return dict(ok=True,allowed=False,code='REVISION_CONFLICT',reason='Task changed; prepare the current revision')
 context=state.context(actor,tid)
 if context.get('status')!='ready':return dict(ok=True,allowed=False,code='UACF_CONTEXT_NOT_READY',reason='Mandatory Task context unavailable or overflows')
 reason=_bypass_reason(state,args)
 if reason:return dict(ok=True,allowed=False,code=reason.split(':')[0],reason=reason,task_ref=vector(task))
 return dict(ok=True,allowed=True,mode='uacf',task_ref=vector(task),cache_key=context['cache_key'],policy_ref=p['ref'],scope='native tool admission + registered dispatch; not an OS/network sandbox',model_calls=0)

def status(state,actor,args):
 p=policy(state);result=dict(ok=True,policy=p,notice=NOTICE,model_calls=0)
 if args.get('native_session_id'):
  host,sid=_identity(args,actor);_,s=_session_checked(state,host,sid);result['session']=s
 return result

def dispatch(state,actor,action,args,operation_id=None):
 return {'work_policy_configure':configure,'work_enter':enter,'work_mode':mode}[action](state,actor,args,operation_id) if action in ['work_policy_configure','work_enter','work_mode'] else admit(state,actor,args) if action=='work_admit' else status(state,actor,args)
