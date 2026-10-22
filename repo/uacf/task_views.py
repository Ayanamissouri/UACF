"""Read-only Task-derived recovery brief. It never mutates canonical task state."""
from .util import Fault
from .fabric import vector

def brief(state,actor,args):
 task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract':raise Fault('INPUT','TaskContract required')
 if args.get('task_revision') is not None and task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','prepare the current Task revision')
 p=task['payload'];rows=p.get('command_ledger',[])
 active=[x for x in rows if x.get('actionable') and x['state'] not in ['cancelled','superseded']]
 from .command_ledger import preparation
 try:preparation(task);prepared=True;gap=None
 except Fault as e:prepared=False;gap={'code':e.code,'detail':e.detail}
 result=dict(schema='uacf-task-view-1',authority_id=state.authority,task_ref=vector(task),goal=p.get('goal',''),output_contract=p.get('output_contract'),requirements_ready=prepared,preparation_gap=gap,open_requirements=[dict(key=x['key'],text=x['text'],state=x['state'],source_ref=x['source_ref']) for x in active if x['state']!='satisfied'],satisfied_keys=[x['key'] for x in active if x['state']=='satisfied'],required_properties=p.get('required_properties',[]),execution_state=p.get('execution_state'),next_action='Complete open requirements, verify actual outputs, and update evidence through canonical actions; this view cannot mark work complete.',authority='Derived read-only recovery view; edits never update the canonical Task.',model_calls=0)
 return dict(ok=True,brief=result)
