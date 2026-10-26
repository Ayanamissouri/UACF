"""Minimal negotiated stdio tools facade through 2025-11-25; no stdout diagnostics."""
import json, sys
from jsonschema import Draft202012Validator
from .service import call
from .util import Fault, canonical

TOOLS=[{'name':'uacf_context','description':'Get TaskContract revision, applicable historical failure candidates and validation obligations. Overflow never truncates mandatory constraints.',
 'inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'max_bytes':{'type':'integer','minimum':1}},'required':['task_id'],'additionalProperties':False}},
 {'name':'uacf_status','description':'Read canonical state and capability gaps; shared visibility only.',
 'inputSchema':{'type':'object','properties':{'object_id':{'type':'string'}},'required':[],'additionalProperties':False}},
 {'name':'uacf_asset_read','description':'Read the bounded immutable body of an Artifact explicitly selected by the current Task. Candidate data is not authority or adoption.',
 'inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'task_revision':{'type':'integer','minimum':1},'artifact_id':{'type':'string'},'max_bytes':{'type':'integer','minimum':1,'maximum':8388608}},'required':['task_id','task_revision','artifact_id'],'additionalProperties':False}}]
TOOLS += [{'name':'uacf_learning_next','description':'Read only this host\'s explicitly mapped public work awaiting source-bound learning. Continue in the existing host; no external model dependency.', 'inputSchema':{'type':'object','properties':{'task_id':{'type':'string'}},'required':['task_id'],'additionalProperties':False}},
 {'name':'uacf_learning_submit','description':'Return current-host source-bound knowledge/issues or candidate comparisons to the same shared queue. Literal quotes and complete indexes are enforced; no factual acceptance or generated rule execution.', 'inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'job_id':{'type':'string'},'result':{'type':'object'}},'required':['task_id','job_id','result'],'additionalProperties':False}}]
TOOLS += [{'name':'uacf_search','description':'Search ALL indexed UACF sources: historical GPT exports, Codex/DSH/Pi public work and current source-bound assets. Requires an Owner-authorized mapped Task; returns bounded candidates with source coverage, never authority.',
 'inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'task_revision':{'type':'integer'},'query':{'type':'string','maxLength':200},'host':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':20}},'required':['task_id','task_revision','query'],'additionalProperties':False}}]

TOOLS += [{'name':'uacf_checkpoint','description':'Capture a meaningful current-work correction/milestone from an already observed real event in this exact mapped session. Never synthesizes a native event; use critical correction for explicit severe rejection with a concrete correction, not emotion alone.',
 'inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'task_revision':{'type':'integer'},'native_session_id':{'type':'string'},'native_event_id':{'type':'string'},'signal':{'enum':['correction','requirement_change','milestone','owner_satisfied','completion']},'basis':{'type':'string','maxLength':1000},'features':{'type':'object'}},'required':['task_id','task_revision','native_session_id','native_event_id','signal'],'additionalProperties':False}}]

TOOLS += [{'name':'uacf_work_brief','description':'Read the current Task requirements, unresolved work and Owner project output. Derived recovery view only; no completion or permission grant.',
 'inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'task_revision':{'type':'integer','minimum':1}},'required':['task_id'],'additionalProperties':False}},
 {'name':'uacf_capabilities','description':'Read separate generated, installed, loaded, called and verified evidence for a host capability. Unobserved never means unavailable; records do not authorize tools.',
 'inputSchema':{'type':'object','properties':{k:{'type':'string'} for k in ['host','machine','host_version','profile','capability','source_identity','native_session_id']},'additionalProperties':False}}]

for _action,_extra in {
 'coding_worker_status':{},
 'coding_worker_prepare':{'spec':{'type':'object'},'unit':{'type':'string'},'limits':{'type':'object'},'limits_observed_at':{'type':'number'}},
 'coding_worker_run':{'ticket_ref':{'type':'object'}},
 'coding_worker_fallback':{'ticket_ref':{'type':'object'},'observation':{'type':'object'}},
 'coding_worker_native_result':{'ticket_ref':{'type':'object'},'observation':{'type':'object'}},
 'coding_worker_audit':{'ticket_ref':{'type':'object'},'review':{'type':'object'}},
 'consistency_status':{'phase':{'enum':['implement','publish','deliver']}},
}.items():
 TOOLS.append(dict(name='uacf_'+_action,description='Registered '+_action+'; frozen source contract, task budget and main-model audit; no universal native interception claim.',inputSchema=dict(type='object',properties=dict(task_id={'type':'string'},task_revision={'type':'integer'},**_extra),required=['task_id']+(['task_revision'] if _action not in ['coding_worker_status'] else [])+([k for k in _extra if k not in ['limits','limits_observed_at','phase']]),additionalProperties=False)))

def handle(root,host,msg):
    method=msg.get('method'); params=msg.get('params',{})
    if method=='initialize': return {'protocolVersion':params.get('protocolVersion') if params.get('protocolVersion') in ['2024-11-05','2025-03-26','2025-06-18','2025-11-25'] else '2025-11-25','capabilities':{'tools':{}},'serverInfo':{'name':'uacf','version':'0.1.1'}}
    if method=='ping': return {}
    if method=='tools/list': return {'tools':TOOLS}
    if method=='tools/call':
        name=params.get('name'); args=params.get('arguments',{})
        try:
            tool=next((t for t in TOOLS if t['name']==name),None)
            if tool is None:raise Fault('UNSUPPORTED','unknown tool')
            errors=list(Draft202012Validator(tool['inputSchema']).iter_errors(args))
            if errors:raise Fault('INPUT','MCP tool arguments do not match declared schema')
            if name=='uacf_checkpoint': result=call(root,'learning_checkpoint',dict(args,host=host),host)
            elif name=='uacf_search': result=call(root,'unified_search',args,host)
            elif name=='uacf_context': result=call(root,'context',args,host)
            elif name=='uacf_work_brief': result=call(root,'work_brief',args,host)
            elif name=='uacf_capabilities': result=call(root,'capability_status',args,host)
            elif name=='uacf_status': result=call(root,'get',args,host) if args.get('object_id') else call(root,'doctor',{},host)
            elif name=='uacf_asset_read': result=call(root,'asset_read',args,host)
            elif name=='uacf_learning_next': result=call(root,'learning_host_next',args,host)
            elif name=='uacf_learning_submit': result=call(root,'learning_host_submit',args,host)
            elif name.startswith('uacf_coding_worker_') or name=='uacf_consistency_status': result=call(root,name[5:],args,host)
            else: raise Fault('UNSUPPORTED','unknown tool')
            return {'content':[{'type':'text','text':canonical(result)}],'isError':not result.get('ok',False)}
        except Fault as e: return {'content':[{'type':'text','text':canonical(e.result())}],'isError':True}
    raise Fault('METHOD_NOT_FOUND','unknown MCP method')
def run(root,host):
    for raw in sys.stdin.buffer:
        if len(raw)>1024*1024: continue
        msg={}
        try:
            msg=json.loads(raw)
            if 'id' not in msg: continue
            reply={'jsonrpc':'2.0','id':msg['id'],'result':handle(root,host,msg)}
        except Fault as e: reply={'jsonrpc':'2.0','id':msg.get('id'),'error':{'code':-32601,'message':e.detail}}
        except Exception: reply={'jsonrpc':'2.0','id':msg.get('id'),'error':{'code':-32602,'message':'invalid request'}}
        sys.stdout.buffer.write((canonical(reply)+'\n').encode('utf-8')); sys.stdout.buffer.flush()
