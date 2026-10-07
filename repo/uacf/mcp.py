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
            if name=='uacf_context': result=call(root,'context',args,host)
            elif name=='uacf_status': result=call(root,'get',args,host) if args.get('object_id') else call(root,'doctor',{},host)
            elif name=='uacf_asset_read': result=call(root,'asset_read',args,host)
            elif name=='uacf_learning_next': result=call(root,'learning_host_next',args,host)
            elif name=='uacf_learning_submit': result=call(root,'learning_host_submit',args,host)
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
