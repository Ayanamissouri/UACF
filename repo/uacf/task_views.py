"""Read-only Task-derived work brief and explicitly refreshed disposable projection."""
import json,threading
from pathlib import Path
from .util import Fault,canonical,atomic,file_hash,sha
from .fabric import vector
LOCK=threading.RLock()

def brief(state,actor,args):
 task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract':raise Fault('INPUT','TaskContract required')
 if args.get('task_revision') is not None and task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','prepare the current Task revision')
 p=task['payload'];rows=p.get('command_ledger',[])
 active=[x for x in rows if x.get('actionable') and x['state'] not in ['cancelled','superseded']]
 from .command_ledger import preparation
 try:preparation(task);prepared=True;gap=None
 except Fault as e:prepared=False;gap={'code':e.code,'detail':e.detail}
 result=dict(schema='uacf-task-view-1',authority_id=state.authority,task_ref=vector(task),goal=p.get('goal',''),output_contract=p.get('output_contract'),requirements_ready=prepared,preparation_gap=gap,open_requirements=[dict(key=x['key'],text=x['text'],state=x['state'],source_ref=x['source_ref']) for x in active if x['state']!='satisfied'],satisfied_keys=[x['key'] for x in active if x['state']=='satisfied'],required_properties=p.get('required_properties',[]),execution_state=p.get('execution_state'),next_action='Complete open requirements, verify actual outputs, and update evidence through canonical actions; this view cannot mark work complete.',authority='Derived reading/recovery view only; edits never update the canonical Task.',model_calls=0)
 if p.get('output_contract'):
  from .storage_layout import task_paths
  result['paths']=task_paths(state,task)
 return dict(ok=True,brief=result)

def refresh(state,actor,args):
 with LOCK:return _refresh(state,actor,args)

def _refresh(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','Owner explicitly refreshes project work views')
 if state.config.get('restore_mapping'):raise Fault('STORAGE_REMAP_REQUIRED','isolated restore cannot write to original projects')
 result=brief(state,actor,args);view=result['brief']
 if 'paths' not in view:raise Fault('OUTPUT_CONTRACT_REQUIRED','Owner project output contract required')
 from .storage_layout import allocated_path
 path=allocated_path(view['output_contract']['project_root'],args['task_id'],'work','views/current-task.json')
 before=file_hash(path) if path.exists() else None
 if args.get('expected_file_hash')!=before:raise Fault('VIEW_CONFLICT','work view changed; compare before refresh')
 body=canonical(view)
 if path.exists() and path.read_text(encoding='utf8')!=body:
  old=json.loads(path.read_text(encoding='utf8'))
  if old.get('schema')!='uacf-task-view-1' or old.get('authority_id')!=state.authority or old.get('task_ref',{}).get('object_id')!=args['task_id']:raise Fault('VIEW_CONFLICT','unrecognized local file; preserve it')
  atomic(path.parent/'history'/('view-'+before+'.json'),path.read_bytes())
 atomic(path,body)
 return dict(ok=True,path=str(path),sha256=file_hash(path),task_ref=view['task_ref'],canonical_state_changed=False,model_calls=0)
