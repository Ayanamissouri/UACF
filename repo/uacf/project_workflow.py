"""Task-bound stage plans. The running host continues; plans never spawn it again."""
import json, re, threading
from .util import Fault, canonical, atomic, sha, now
from .state import object_new, request
from .fabric import vector

ROLES={'plan','extract','implement','validate','review','deliver'}
LOCK=threading.Lock()
def defaults(family, preset):
    items=[('plan','理解目标与约束'),('extract','读取来源与结构化')]
    if family!='assets':items.append(('implement','实施与修订'))
    items += [('validate','程序与来源核验'),('review','条件、矛盾与结果复核'),('deliver','交付与接续')]
    return [dict(id='s'+str(i+1),role=role,label=label,route='current_host',depends_on=[] if i==0 else ['s'+str(i)]) for i,(role,label) in enumerate(items)]

def dispatch(state,actor,action,args,operation_id):
    with LOCK:return _dispatch(state,actor,action,args,operation_id)

def _dispatch(state,actor,action,args,operation_id):
    if actor!='owner':raise Fault('PERMISSION','project execution policy requires owner')
    task=state.get(args.get('task_id',''),actor)
    if task['object_type']!='TaskContract':raise Fault('INPUT','TaskContract required')
    folder=state.root/'data/project-workflows';folder.mkdir(exist_ok=True)
    path=folder/(task['object_id']+'.json')
    old=json.loads(path.read_text()) if path.exists() else None
    def anchored():
        if not old:raise Fault('NOT_PREPARED','save task stage plan first')
        obj=state.get(old['plan_ref']['object_id'],actor)
        if obj['revision']!=old['plan_ref']['revision'] or obj['payload']['config']!=old['config']:raise Fault('ROUTE_TAMPERED','stage plan differs from canonical')
        if task['revision']!=old['task_ref']['revision'] or task['payload'].get('execution_policy_ref')!=old['plan_ref']:raise Fault('REVISION_CONFLICT','task changed; reprepare stage plan')
    if action=='workflow_project_status':
        if old:anchored()
        return {'ok':True,'task_ref':vector(task),'goal':task['payload'].get('goal',''),'required_work_steps':task['payload'].get('required_work_steps',[]),'plan':old,'defaults':defaults('general','time')}
    if args.get('task_revision')!=task['revision']:raise Fault('REVISION_CONFLICT','task changed')
    if action=='workflow_project_configure':
        preset=args.get('preset','time');family=args.get('family','general')
        if preset not in ['time','cost','quality'] or family not in ['general','assets','code','report']:raise Fault('INPUT','unsupported preset/family')
        if old and any(e['state']=='started' and not any(x['stage_id']==e['stage_id'] and x['state']=='completed' for x in old['events']) for e in old['events']):raise Fault('BUSY','complete active stage before replanning')
        stages=args.get('stages') or defaults(family,preset)
        if not isinstance(stages,list) or not 1<=len(stages)<=30:raise Fault('INPUT','1..30 stages required')
        seen=set()
        for s in stages:
            if not isinstance(s,dict) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',str(s.get('id',''))) or s['id'] in seen or s.get('role') not in ROLES or s.get('route') not in ['current_host','deepseek'] or not isinstance(s.get('label'),str) or not 1<=len(s['label'])<=120 or not isinstance(s.get('depends_on'),list) or any(x not in seen for x in s['depends_on']):raise Fault('INPUT','invalid stage or dependency; feedback uses a new revision')
            seen.add(s['id'])
        config=dict(planning_task_ref=vector(task),preset=preset,family=family,stages=stages,
                    current_host_mode='continue_existing_turn',external_dispatch='existing registered provider tools; not automatic from this plan',human_override='optional',at=now())
        obj=state.put(request(object_new('Artifact',dict(locator='project-workflow:'+str(operation_id),name='Task stage defaults and overrides',media_type='application/json',sha256=sha(canonical(config)),config=config),visibility=task.get('visibility','private')),operation_id=operation_id),actor)['object']
        task['payload']['execution_policy_ref']=vector(obj)
        task=state.put(request(task,task['revision']),actor)['object']
        plan=dict(plan_ref=vector(obj),task_ref=vector(task),config=config,events=[],previous_plan_ref=old['plan_ref'] if old else None)
        atomic(path,canonical(plan))
        return {'ok':True,'plan':plan,'task_ref':vector(task)}
    if action!='workflow_project_record':raise Fault('NOT_FOUND','unknown project stage action')
    anchored()
    step=next((x for x in old['config']['stages'] if x['id']==args.get('stage_id')),None)
    status=args.get('state')
    if not step or status not in ['started','completed']:raise Fault('INPUT','known stage and lifecycle required')
    if status=='started':
        if any(e['stage_id']==step['id'] for e in old['events']):raise Fault('REVISION_CONFLICT','stage already started; no replay')
        complete={e['stage_id'] for e in old['events'] if e['state']=='completed'}
        if any(x not in complete for x in step['depends_on']):raise Fault('DEPENDENCY','finish dependencies first')
        if state.context(actor,task['object_id'])['status']!='ready':raise Fault('CAPSULE_OVERFLOW','mandatory context must be ready')
        if step['route']=='deepseek':raise Fault('ADAPTER_REQUIRED','use registered E7 provider runner; general stage dispatcher not installed')
        if task['payload'].get('execution_state') in ['stopped','blocked']:raise Fault('STOPPED','task execution stopped or blocked')
    else:
        if not any(e['stage_id']==step['id'] and e['state']=='started' for e in old['events']) or any(e['stage_id']==step['id'] and e['state']=='completed' for e in old['events']):raise Fault('REVISION_CONFLICT','stage not active')
        if not isinstance(args.get('result'),str) or not args['result'].strip() or len(args['result'])>12000:raise Fault('INPUT','bounded public result required')
        if step['route']=='deepseek':raise Fault('ADAPTER_REQUIRED','generic DS completion needs a registered task-specific receipt verifier; do not claim success')
        if args.get('actual_model') not in ['current_host','gpt-6.1-sol']:raise Fault('MODEL_MISMATCH','current host receipt or explicitly observed model required')
        if not isinstance(args.get('native_locator'),str) or not args['native_locator'].strip():raise Fault('INPUT','public native call/file locator required')
        from .learning import config
        if getattr(state,'data',None) is not None and config(state):
            from .learning_guards import protected,delivery
            protected(task)
            if step['role']=='deliver':delivery(state,task)
    event=dict(stage_id=step['id'],state=status,route=step['route'],at=now(),result=args.get('result'),native_locator=args.get('native_locator'),actual_model=args.get('actual_model'),coverage='host-reported stage lifecycle; not independent semantic acceptance',plan_ref=old['plan_ref'],task_ref=vector(task))
    ev=state.put(request(object_new('Evidence',{'observation':event}),operation_id=operation_id),actor)['object']
    event['evidence_ref']=vector(ev);old['events'].append(event);atomic(path,canonical(old))
    return {'ok':True,'plan':old,'continue_current_host':step['route']=='current_host','external_dispatch_required':step['route']=='deepseek'}
