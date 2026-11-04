"""Task-bound action authority, separate from semantic interpretation and telemetry.

Only a current Owner source can configure authority. Host checks use the same
canonical revision as consistency review; their response proves no host effect.
"""
import json,re
from pathlib import Path
from .action_classifier import classify
from .state import request
from .fabric import vector
from .util import Fault,canonical,atomic,now

MODES={'answer','review','monitor','change'}

def status(task):
 return dict(task_ref=vector(task),contract=task['payload'].get('action_contract'),
  semantic_review='required independently; action classification cannot resolve numeric meaning',
  scope='covered native tool admission; no OS/network sandbox',host_effect='unobserved')

def configure(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','Owner source interpretation configures action authority')
 task=state.get(args['task_id'],actor)
 if task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','configure exact current Task')
 ref=args['source_ref'];source=state.get(ref['object_id'],actor)
 if vector(source)!=ref or source['object_type']!='Message' or source['payload'].get('source_kind')!='direct_user' or not source['payload'].get('current'):raise Fault('ACTION_SOURCE','current Owner source required')
 sources=task['payload'].get('consistency',{}).get('contract',{}).get('sources',[])
 if ref not in sources and ref!=task['payload'].get('command_contract',{}).get('source_ref'):raise Fault('ACTION_SOURCE','source must belong to this Task current command or interpretation')
 quote=args.get('source_quote','');basis=args.get('interpretation_basis','');contract=args.get('contract',{})
 if not quote or quote not in source['payload']['text'] or not basis:raise Fault('ACTION_SOURCE','quoted source and interpretation basis required')
 if set(contract)-{'mode','allowed_paths','dependencies','hashing'} or contract.get('mode') not in MODES:raise Fault('ACTION_CONTRACT','explicit supported mode and fields required')
 for key in ['dependencies','hashing']:
  if contract.get(key,'allow') not in ['allow','deny']:raise Fault('ACTION_CONTRACT','policy is explicit allow or deny')
 paths=contract.get('allowed_paths')
 if paths is not None:
  if not isinstance(paths,list) or not paths or len(paths)>100:raise Fault('ACTION_CONTRACT','bounded explicit file boundary required')
  root=Path(task['payload']['output_contract']['project_root']).resolve()
  for raw in paths:
   if not isinstance(raw,str) or not raw or '\\' in raw or ':' in raw or '..' in Path(raw).parts or Path(raw).is_absolute() or '*' in raw.removesuffix('/**'):raise Fault('ACTION_CONTRACT','relative exact paths or directory/** required')
   if not (root/raw.removesuffix('/**')).resolve().is_relative_to(root):raise Fault('ACTION_CONTRACT','file boundary escapes selected project')
 task['payload']['action_contract']=dict(contract,source_ref=ref,source_quote=quote,interpretation_basis=basis)
 out=state.put(request(task,task['revision']),actor)['object']
 return dict(ok=True,**status(out),review_invalidated=True)

def affected_paths(name,inp):
 if isinstance(inp,dict):
  if name.lower() in {'write','edit','write_file','edit_file'}:return [inp.get('file_path') or inp.get('path')] if inp.get('file_path') or inp.get('path') else []
  text=inp.get('patch') or inp.get('input') or ''
 else:text=inp if isinstance(inp,str) else ''
 if name.lower()!='apply_patch':return []
 return re.findall(r'^\*\*\* (?:Add File|Update File|Delete File|Move to):\s*(.+)$',text,re.M)

def check(task,args):
 name=args.get('tool_name','').removeprefix('functions.').removeprefix('tools.');inp=args.get('tool_input',{})
 effect=classify(name,inp);policy=task['payload'].get('action_contract')
 if not policy:return effect
 if policy.get('mode') not in MODES:raise Fault('ACTION_CONTRACT','invalid canonical action mode; repair current source interpretation')
 if policy['mode']!='change' and effect!='read':raise Fault('ACTION_MODE','Current '+policy['mode']+' authorizes only proven read actions; report findings or use a concrete read tool')
 if effect!='read' and task['payload'].get('retry_guard',{}).get('blocked'):raise Fault('REREAD_REQUIRED','registered retry guard stopped work; reprepare the declared hypothesis first')
 paths=policy.get('allowed_paths')
 if effect!='read' and paths is not None:
  root=Path(task['payload']['output_contract']['project_root']).resolve();targets=affected_paths(name,inp)
  if not targets:raise Fault('ACTION_PATH_UNPROVEN','write targets are opaque under the explicit file boundary; use a supported edit tool')
  for raw in targets:
   p=Path(raw);target=(p if p.is_absolute() else Path(args.get('cwd') or root)/p).resolve()
   if not target.is_relative_to(root):raise Fault('ACTION_PATH','write outside the selected project')
   if not any(target==(root/a.removesuffix('/**')).resolve() or a.endswith('/**') and target.is_relative_to((root/a[:-3]).resolve()) for a in paths):raise Fault('ACTION_PATH','write outside explicit task file boundary')
 # Optional defenses are not banned by keyword. Only an explicitly adopted
 # policy denies these high-confidence *executions*. UACF integrity consumers
 # keep their existing hashes; source/code mentions are not execution facts.
 if name.lower() in {'exec_command','bash','shell','shell_command','powershell'}:
  text=inp if isinstance(inp,str) else str(inp.get('command') or inp.get('cmd') or '')
  if policy.get('hashing')=='deny' and re.match(r'\s*(?:Get-FileHash|sha256sum|shasum|certutil\s+-hashfile)\b',text,re.I):raise Fault('ACTION_HASH','hash execution forbidden by current explicit task policy')
  if policy.get('dependencies')=='deny' and re.match(r'\s*(?:(?:npm|pnpm|yarn)\s+(?:add|install)|pip\s+install)\b',text,re.I):raise Fault('ACTION_DEPENDENCY','dependency addition forbidden by current explicit task policy')
 return effect

def record(state,args,result):
 """Disposable metadata projection. Telemetry failure cannot change admission."""
 ref=result.get('task_ref')
 if not ref:return
 path=state.data/'host-work/admissions'/(ref['object_id']+'.json')
 old=json.loads(path.read_text('utf8')) if path.exists() else {'checked':0,'allowed':0,'denied':0}
 key='allowed' if result.get('allowed') else 'denied'
 old.update(checked=old['checked']+1,**{key:old[key]+1},task_ref=ref,at=now(),last_code=result.get('code','ALLOWED'),tool_name=args.get('tool_name'),host_effect='unobserved',coverage='returned decisions only; counters are rebuildable telemetry, never authority')
 atomic(path,canonical(old))
