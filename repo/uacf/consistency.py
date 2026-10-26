"""Source-bound semantic review gates; structural checks do not prove language truth.

The host supplies an interpretation, a separately identified reviewer challenges it,
and implementation/delivery remain bound to the same source and decisions.
"""
from pathlib import Path
import json
from .util import Fault, sha, file_hash
from .state import request, stale
from .fabric import vector
import re

ROLES={'directive','prohibition','goal','question','quotation','example','rhetoric','context','uncertain'}
RELATIONS={'and','contrast','condition','progression','explanation','reference','none'}

def tool_gate(state,task,args):
    """Known native edit/publish tools only; never claim a shell sandbox."""
    name=args.get('tool_name','').lower();body=str(args.get('tool_input',{}))
    publish=bool(re.search(r'\bgit\s+push\b',body))
    edit=any(x in name for x in ['apply_patch','write_file','edit_file','multiedit'])
    if not edit and not publish:return
    gate(task,state,'publish' if publish else 'implement')
    if publish:
        from .coding_workers import audit_guard
        audit_guard(state,task)

def fingerprint(task):
    p=task['payload']
    return sha({k:p.get(k) for k in ['goal','command_contract','constraints','output_contract','research_contract']} | {
        'commands':[{k:r.get(k) for k in ['key','text','kind','source_ref','source_quote','interpretation_basis']}
                    for r in p.get('command_ledger',[]) if r.get('state') not in ['cancelled','superseded']]})

def review_evidence(state,ref,task,seen=None):
    """Attaching a review versions the Task, not the interpreted requirements.

    Preserve exact native execution revision while allowing that one Task edge
    only when its original semantic fingerprint still equals the current one.
    Every other dependency must retain its exact recorded revision.
    """
    seen=set() if seen is None else seen
    key=(ref['object_id'],ref['revision'])
    if key in seen:raise Fault('CONSISTENCY_STALE','cyclic review dependencies')
    seen=seen|{key};obj=state.get(ref['object_id'],'owner')
    if obj['object_id']==task['object_id']:
        original=state.get(ref['object_id'],'owner',ref['revision'])
        if fingerprint(original)!=fingerprint(task):raise Fault('CONSISTENCY_STALE','native review covers different requirements')
        return obj
    if vector(obj)!=ref:raise Fault('CONSISTENCY_STALE','review dependency revision changed')
    for dep in obj['payload'].get('input_vector',[]):review_evidence(state,dep,task,seen)
    return obj

def validate(state,task,contract):
    sources=contract.get('sources',[]);clauses=contract.get('clauses',[])
    if not sources or not clauses:raise Fault('CONSISTENCY_SOURCE','complete source segmentation required')
    texts={}
    for ref in sources:
        source=state.get(ref['object_id'],'owner')
        if vector(source)!=ref or stale(state,source):raise Fault('CONSISTENCY_STALE','source revision changed')
        if source['object_type']!='Message' or source['payload'].get('source_kind')!='direct_user':raise Fault('CONSISTENCY_SOURCE','native user source required')
        texts[source['object_id']]=source['payload']['text']
    active={r['key']:r for r in task['payload'].get('command_ledger',[]) if r.get('actionable') and r.get('state') not in ['cancelled','superseded'] and (r.get('state')!='satisfied' or r.get('source_ref',{}).get('object_id') in texts)}
    covered=set();ids=set()
    for sid,text in texts.items():
        position=0
        for row in sorted([r for r in clauses if r.get('source_id')==sid],key=lambda r:r['start']):
            start,end=row['start'],row['end'];key=row.get('id')
            if type(start)!=int or type(end)!=int or start!=position or not start<end<=len(text) or row.get('quote')!=text[start:end]:raise Fault('CONSISTENCY_COVERAGE','source spans must cover full text exactly without gaps/overlap')
            position=end
            if not key or key in ids or row.get('role') not in ROLES or row.get('relation') not in RELATIONS or not row.get('scope') or not row.get('interpretation'):raise Fault('CONSISTENCY_STRUCTURE','unique clause, role, scope, relation and interpretation required')
            ids.add(key)
            actions=row.get('commands',[])
            if actions and row['role'] not in ['directive','prohibition','goal']:raise Fault('CONSISTENCY_AUTHORITY','questions, examples, rhetoric and quotations cannot directly become commands')
            for action in actions:
                if action not in active or active[action]['source_ref']['object_id']!=sid:raise Fault('CONSISTENCY_COMMAND','clause must bind a current same-source command')
                covered.add(action)
            for number in row.get('numbers',[]):
                if not number.get('literal') or number['literal'] not in row['quote'] or number.get('status') not in ['example','unresolved','explicit','model_choice']:raise Fault('CONSISTENCY_NUMBER','numeric provenance required')
                if number.get('used_for_execution'):
                    if number['status'] in ['example','unresolved'] or any(not number.get(k) for k in ['object','metric_denominator','unit','basis']):raise Fault('CONSISTENCY_NUMBER','execution numbers require resolved referent, denominator, unit and basis')
            # Reviewer must also challenge omitted numeric expressions: this is
            # intentionally not a regex claiming to understand Chinese/English.
        if position!=len(text):raise Fault('CONSISTENCY_COVERAGE','uninterpreted source tail')
    if any(r.get('source_id') not in texts for r in clauses) or covered!=set(active):raise Fault('CONSISTENCY_COMMAND','all active commands must have source-bound coverage')
    for decision in contract.get('decisions',[]):
        if decision.get('kind') not in ['explicit_requirement','model_choice','unresolved'] or not decision.get('basis') or not set(decision.get('clauses',[]))<=ids or not decision.get('clauses'):raise Fault('CONSISTENCY_DECISION','implementation choices need explicit classification and source context')
        if decision['kind']=='unresolved' and decision.get('used_for_execution'):raise Fault('CONSISTENCY_DECISION','unresolved consequential choices cannot execute')
    return sha(contract)

def gate(task,state=None,phase='implement'):
    p=task['payload']
    if not p.get('consistency_required'):return
    c=p.get('consistency',{})
    if c.get('requirements_hash')!=fingerprint(task):raise Fault('CONSISTENCY_STALE','requirements changed; re-interpret and re-review')
    if sha(c.get('contract'))!=c.get('contract_hash'):raise Fault('CONSISTENCY_STALE','interpretation changed')
    review=c.get('review',{})
    if review.get('contract_hash')!=c.get('contract_hash') or review.get('verdict')!='pass' or review.get('reviewer')==c.get('author'):raise Fault('CONSISTENCY_REVIEW','separate source-to-contract review required')
    if state:
        validate(state,task,c['contract'])
        review_evidence(state,review['evidence_ref'],task)
    if phase in ['deliver','publish']:
        final=c.get('publication' if phase=='publish' else 'delivery',{})
        if final.get('contract_hash')!=c['contract_hash'] or final.get('verdict')!='pass':raise Fault('CONSISTENCY_DELIVERY','source-to-result review missing')
        if state:
            review_evidence(state,final['evidence_ref'],task)
        root=Path(p['output_contract']['project_root']).resolve()
        traced=set()
        for row in final.get('trace',[]):
            path=Path(row['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file() or file_hash(path)!=row['sha256'] or not row.get('check') or not row.get('result'):raise Fault('CONSISTENCY_DELIVERY','current implementation and test evidence required')
            traced.add(row['command'])
        expected={k for r in c['contract']['clauses'] for k in r.get('commands',[])}
        if traced!=expected:raise Fault('CONSISTENCY_DELIVERY','every command needs implementation/result trace')

def dispatch(state,actor,action,args):
    task=state.get(args['task_id'],actor)
    if task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','prepare exact current revision')
    if action=='consistency_status':
        try:gate(task,state,args.get('phase','implement'));return dict(ok=True,allowed=True,review=task['payload'].get('consistency'))
        except Fault as e:return dict(ok=True,allowed=False,code=e.code,reason=e.detail)
    if actor!='owner':raise Fault('PERMISSION','main host uses authenticated Owner action; workers cannot self-accept')
    c=task['payload'].get('consistency',{})
    if action=='consistency_prepare':
        contract=args['contract'];digest=validate(state,task,contract)
        if not args.get('author'):raise Fault('CONSISTENCY_REVIEW','interpretation author identity required')
        c=dict(contract=contract,contract_hash=digest,requirements_hash=fingerprint(task),author=args['author'])
        task['payload']['consistency_required']=True
    else:
        if c.get('requirements_hash')!=fingerprint(task):raise Fault('CONSISTENCY_STALE','requirements changed')
        review=args['review'];ev=review_evidence(state,review['evidence_ref'],task)
        if ev['object_type']!='Evidence':raise Fault('CONSISTENCY_REVIEW','current recorded review evidence required')
        observation=ev['payload'].get('observation',{})
        # Exact recorded public review, not an unrelated successful model call.
        if observation.get('consistency_review')!={k:v for k,v in review.items() if k!='evidence_ref'}:
            try:actual=json.loads(observation['answer'].strip().removeprefix('```json').removesuffix('```').strip())
            except (KeyError,ValueError,TypeError):raise Fault('CONSISTENCY_REVIEW','review must exactly match source-bound public observation')
            if observation.get('ok') is not True or observation.get('finish',{}).get('kind')!='stop' or review.get('reviewer')!='deepseek:'+str(observation.get('run_id')) or any(actual.get(k)!=review.get(k) for k in ['contract_hash','verdict','findings']):raise Fault('CONSISTENCY_REVIEW','native reviewer result is incomplete or does not match submission')
        if review.get('contract_hash')!=c.get('contract_hash') or not review.get('findings') or not review.get('reviewer') or review.get('reviewer')==c.get('author'):raise Fault('CONSISTENCY_REVIEW','separate reviewer must compare original source and interpretation')
        if review.get('verdict') not in ['pass','fail']:raise Fault('CONSISTENCY_REVIEW','explicit review verdict required')
        if action=='consistency_review':c['review']=review;c.pop('delivery',None)
        elif action=='consistency_publish':gate(task,state);c['publication']=review
        elif action=='consistency_deliver':gate(task,state);c['delivery']=review
        else:raise Fault('INPUT','unknown consistency action')
    task['payload']['consistency']=c
    out=state.put(request(task,task['revision']),actor)['object']
    return dict(ok=True,task_ref=vector(out),contract_hash=c['contract_hash'],scope='registered gates; semantic judgment is recorded and challengeable, not guaranteed correct')
