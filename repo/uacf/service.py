import json, os, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .state import State, object_new, request, uuid_ok
from .util import Fault, atomic, canonical, file_hash, now, sha, uid

def verify_dsh(state,actor,task_id,revision):
    if actor!='owner': raise Fault('PERMISSION','only owner dispatches verifier')
    task=state.get(task_id,actor)
    if task['revision']!=revision: raise Fault('REVISION_CONFLICT','verification target changed')
    if 'installed_loaded_called' not in task['payload']['required_properties']: raise Fault('INPUT','task does not request this property')
    cfg=state.config; nonce=uid(); observation={}; verdict='inconclusive'
    auth=json.loads((state.data/'auth.json').read_text())
    try:
        url=cfg['dsh_url']+'/uacf/v1/canary'
        if not url.startswith('http://127.0.0.1:'): raise Fault('CONFIG','DSH verifier only permits loopback')
        payload=canonical({'nonce':nonce,'task_id':task_id,'task_revision':revision}).encode()
        r=urllib.request.Request(url,data=payload,headers={'Authorization':'Bearer '+auth['owner'],'Content-Type':'application/json'})
        with urllib.request.urlopen(r,timeout=15) as response: observation=json.load(response)
        plugin=observation.get('plugin',{})
        allowed=(state.root/'repo/adapters/dsh/index.js').resolve()
        disk=PathSafe(plugin.get('file',''),allowed)
        result=observation.get('tool_result',{})
        value=result.get('value',{})
        context_result=observation.get('context_result',{}) or {}
        capsule=json.loads(context_result.get('value',{}).get('body','{}'))
        binding=observation.get('session_binding',{})
        conditions={'nonce':observation.get('nonce')==nonce,'pid':type(plugin.get('pid'))==int and plugin['pid']>0,
           'disk_hash':plugin.get('sha256')==file_hash(disk),'loaded_hash':plugin.get('loaded_sha256')==file_hash(disk),
           'tool_pipeline':result.get('isError') is False,'tool_result':value.get('ok') is True,
           'authority':value.get('authority_id')==state.authority,'tool_nonce':value.get('nonce')==nonce,
           'tool_pid':value.get('host_pid')==plugin.get('pid'),
           'context_tool':context_result.get('isError') is False,
           'task_revision':(capsule.get('capsule') or {}).get('task_revision')==revision,
           'capsule_ready':capsule.get('status')=='ready',
           'real_session_binding':bool(binding.get('agent_id')) and binding.get('agent_id')==binding.get('session_id') and binding.get('agent_registry_exact') is True and binding.get('session_registry_exact') is True and binding.get('factory')=='ctx.agents.create',
           'binding_task':binding.get('task_id')==task_id and binding.get('task_revision')==revision,
           'no_model_turn':binding.get('model_turns_requested')==0 and binding.get('turn_start_events')==0}
        observation['verification_conditions']=conditions; verdict='pass' if all(conditions.values()) else 'fail'
    except (urllib.error.URLError,TimeoutError,OSError,ValueError,Fault) as e:
        observation={'error_type':type(e).__name__,'reason':str(e),'nonce':nonce,'host':'dsh'}
    environment_hash=sha({'host':cfg['dsh_url'],'plugin':observation.get('plugin',{}),'context_profile':observation.get('context_profile'),'authority':state.authority})
    evidence=object_new('Evidence',{'observation':observation,'task_id':task_id,'target_revision':revision},visibility=task['visibility'])
    ev=state.put(request(evidence),actor)['object']
    val=object_new('Validation',{'task_id':task_id,'task_revision':revision,'property':'installed_loaded_called','result':verdict,
       'environment_hash':environment_hash,'method':'DSH authenticated route → actual ctx.tools.execute pipeline → independent disk/loaded identity checks', 'evidence_id':ev['object_id'],
       'input_vector':[{'object_id':task_id,'revision':revision},{'object_id':ev['object_id'],'revision':ev['revision']}],
       'execution_status':'ran','coverage':['installed_loaded_called'],'expiry':'environment or dependency change'},status='proposed',visibility=task['visibility'])
    val['provenance_refs']=[ev['object_id']]
    v=state.put(request(val),'system',internal=True)['object']
    return {'ok':True,'result':verdict,'validation':v,'evidence':ev,'environment_hash':environment_hash}

def PathSafe(raw,allowed):
    from pathlib import Path
    if Path(raw).resolve()!=allowed: raise Fault('EVIDENCE_PATH','unexpected installed plugin path')
    return allowed

def dispatch(state,actor,action,args,operation_id=None):
    if action.startswith('portable_'):
        from .portable_assets import dispatch as portable_dispatch
        return portable_dispatch(state,actor,action,args)
    if action in ['archive_trigger_check','archive_trigger_status']:
        from .archive_trigger import check,status
        return (check if action=='archive_trigger_check' else status)(state,actor,args)
    if action in ['learning_bind_host','learning_checkpoint']:
        from .learning_lifecycle import bind,checkpoint
        return (bind if action=='learning_bind_host' else checkpoint)(state,actor,args)
    if action.startswith('learning_'):
        from .learning import dispatch as learning_dispatch
        return learning_dispatch(state,actor,action,args,operation_id)
    if action.startswith('workflow_'):
        from .workflow import dispatch as workflow_dispatch
        return workflow_dispatch(state,actor,action,args,operation_id)
    if action=='e7_library':
        from .e7_library import library
        return library(state,actor,args)
    if action=='verify_host_project':
        from .host_project_verify import verify
        return verify(state,actor,args)
    if action=='promote_host_project':
        from .host_project_verify import verify
        v=verify(state,actor,args)
        promoted=state.promote(actor,args['task_id'],args['task_revision'],v['environment_hash'],operation_id,complete_execution=True)
        return {'ok':True,'verification':v,'promotion':promoted}
    if action in ['trial_reserve','trial_settle']:
        from .trial_budget import reserve,settle
        return reserve(state,actor,args,operation_id) if action=='trial_reserve' else settle(state,actor,args)
    if action=='catalog':
        from .catalog import catalog
        return catalog(state,actor,args)
    if action=='host_observations':
        from .host_continuity import observe
        return observe(state,actor,args)
    if action=='host_preflight':
        from .fabric import owner, stale
        from .batch2 import batch4_preflight, budget_get
        owner(actor)
        if state.config.get('restore_mapping'): raise Fault('HOST_REMAP_REQUIRED','isolated restore cannot dispatch')
        task=state.get(args['task_id'],actor); profile=state.get(args['provider_profile_id'],actor)
        if task['object_type']!='TaskContract' or profile['object_type']!='ProviderProfile' or stale(state,task) or stale(state,profile): raise Fault('DEPENDENCY_STALE','current Task/Profile required')
        if task['revision']!=args['task_revision'] or task['payload'].get('budget_account')!=args['account']: raise Fault('BUDGET_ACCOUNT_MISMATCH','exact Task revision and independent account required')
        if task['payload'].get('execution_state')=='stopped' or not task['payload'].get('allow_provider'): raise Fault('STOPPED','current task does not authorize Provider execution')
        batch4_preflight(state,actor,args,task,profile)
        context=state.context(actor,task['object_id'])
        if context['status']!='ready': raise Fault('CAPSULE_OVERFLOW','mandatory context must be ready')
        return {'ok':True,'profile':profile,'budget':budget_get(state,args['account']),'context_status':context['status']}
    if action=='observatory':
        from .observatory import observe
        return observe(state,actor,args)
    if action=='workspace':
        from .workspace import workspace
        return workspace(state,actor,args)
    from .archive import ACTIONS as ARCHIVE_ACTIONS, dispatch_archive
    if action in ARCHIVE_ACTIONS: return dispatch_archive(state,actor,action,args,operation_id)
    from .batch3 import ACTIONS, dispatch_batch3
    if action in ACTIONS: return dispatch_batch3(state,actor,action,args,operation_id)
    if action in ['interpret','source_read','ingest','workunit','projection','correct','integrate','rebuild','route','budget_get','budget_reserve','budget_settle','model_dispatch','review_response','source_register']:
        from .batch2 import dispatch_batch2
        return dispatch_batch2(state,actor,action,args,operation_id)
    if action=='doctor': return state.doctor()
    if action=='list': return {'ok':True,'objects':state.list(actor,args.get('type'))}
    if action=='get': return {'ok':True,'object':state.get(args['object_id'],actor,args.get('revision'))}
    if action=='blob': return state.fetch_blob(actor,args['object_id'],args.get('revision'),args.get('max_bytes',65536))
    if action=='put':
        if args.get('actor')!=actor: raise Fault('PERMISSION','actor must match authenticated principal')
        return state.put(args,actor)
    if action=='search': return state.search(actor,args.get('text',''),args.get('min_commit_seq',0))
    if action=='context': return state.context(actor,args['task_id'],args.get('max_bytes'))
    if action=='asset_read': return state.asset_read(actor,args)
    if action=='artifact_capture':
        from .artifact_capture import capture
        return capture(state,actor,args)
    if action=='host_event': return state.host_event(args,actor)
    if action=='operation_get':
        with state.db() as c:
            row=c.execute('SELECT * FROM command_operations WHERE operation_id=?',(args['operation_id'],)).fetchone()
            if not row or actor!='owner' and row['actor']!=actor: raise Fault('NOT_FOUND','operation unavailable in access domain')
            result=dict(row)
            result['response']=json.loads(result['response']) if result['response'] else None
            return {'ok':True,'operation':result,'outcome':'unknown or in flight' if result['state']=='pending' else 'recorded'}
    if action=='verify_dsh': return verify_dsh(state,actor,args['task_id'],args['revision'])
    if action=='promote':
        # Re-probe environment before accepting; no stale loaded process validation reuse.
        v=verify_dsh(state,actor,args['task_id'],args['revision'])
        return state.promote(actor,args['task_id'],args['revision'],v['environment_hash'],operation_id)
    if action=='profile_get': return {'ok':True,'profiles':state.config['context_profiles'],'capsule_max_bytes':state.config['capsule_max_bytes'],'revision':state.config.get('revision',1)}
    if action=='profile_set':
        from .fabric import config_set
        return config_set(state,actor,args,operation_id or uid())
    raise Fault('UNSUPPORTED',f'unknown action {action}')

MUTATIONS={'put','verify_dsh','promote','profile_set','host_event','artifact_capture','source_register','ingest','workunit','correct','integrate','rebuild','budget_reserve','budget_settle','model_dispatch','review_response','interpret','exchange_export','exchange_import','lease_acquire','lease_result','budget_open'}
MUTATIONS.update(['portable_draft','portable_revise','portable_review','archive_trigger_check'])
MUTATIONS.update(['trial_reserve','trial_settle','verify_host_project','promote_host_project'])
from .archive import MUTATIONS as ARCHIVE_MUTATIONS
MUTATIONS.update(ARCHIVE_MUTATIONS)
MUTATIONS.update(['workflow_select_batch','workflow_configure','workflow_start','workflow_pause','workflow_resolve_rejection','workflow_review_submit'])
MUTATIONS.update(['workflow_project_configure','workflow_project_record'])
MUTATIONS.update(['learning_configure','learning_enqueue','learning_mark','learning_start','learning_pause','learning_register_guards','learning_verify'])
MUTATIONS.update(['learning_metadata','learning_recall'])
MUTATIONS.add('learning_review')
MUTATIONS.update(['learning_route','learning_fallback'])
MUTATIONS.add('learning_host_submit')
def execute_command(state,actor,message):
    action=message['action']; args=message.get('args',{})
    if action not in MUTATIONS: return dispatch(state,actor,action,args)
    if actor=='reader' or action in ['verify_dsh','promote','profile_set'] and actor!='owner': raise Fault('PERMISSION','actor cannot perform this mutation')
    uuid_ok(message.get('operation_id'))
    if message.get('actor')!=actor or message.get('schema_version')!='1.0' or not message.get('correlation_id') or message.get('scope')!='action:'+action:
        raise Fault('INPUT','mutation command envelope missing or mismatched')
    if type(message.get('expected_revision'))!=int or message['expected_revision']<0: raise Fault('INPUT','command expected_revision required')
    digest=sha({k:v for k,v in message.items() if k!='request_hash'})
    if message.get('request_hash')!=digest: raise Fault('REQUEST_HASH','command request hash mismatch')
    oid=message['operation_id']
    with state.db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM command_operations WHERE operation_id=?',(oid,)).fetchone()
        if row:
            if row['request_hash']!=digest or row['actor']!=actor: raise Fault('OPERATION_CONFLICT','command operation changed')
            if row['state']=='done':
                response=json.loads(row['response'])
                if not response.get('ok'): raise Fault(response['code'],response['detail'])
                return response
            # Recover only a canonical single-transaction receipt that is definitely durable.
            persisted=c.execute('SELECT response,actor FROM operations WHERE operation_id=?',(oid,)).fetchone() if action in ['put','promote','profile_set'] else None
            if persisted and persisted['actor']==actor:
                response=json.loads(persisted['response']); response.update(operation_id=oid,request_hash=digest)
                c.execute("UPDATE command_operations SET state='done',response=? WHERE operation_id=?",(canonical(response),oid))
                return response
            # Do not blindly replay a mutation after an interrupted/uncertain command.
            raise Fault('OUTCOME_UNKNOWN','command interrupted or still running; inspect operation and evidence before an explicit new action')
        c.execute('INSERT INTO command_operations VALUES(?,?,?,?,?,?,?)',(oid,digest,actor,action,'pending',None,now()))
    try:
        try: result=dispatch(state,actor,action,args,oid)
        except (KeyError,ValueError,TypeError) as e: raise Fault('INPUT',str(e))
        result.update(operation_id=oid,request_hash=digest)
    except Fault as e:
        result=e.result(); result.update(operation_id=oid,request_hash=digest)
        with state.db() as c: c.execute("UPDATE command_operations SET state='done',response=? WHERE operation_id=?",(canonical(result),oid))
        raise
    with state.db() as c: c.execute("UPDATE command_operations SET state='done',response=? WHERE operation_id=?",(canonical(result),oid))
    return result

class LocalStateServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR permits another listener to steal this port. A loaded
    # identity is meaningful only when the authority owns its single listener.
    allow_reuse_address=False
    def server_bind(self):
        import socket
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

def serve(root,bind='127.0.0.1',port=None):
    if bind!='127.0.0.1': raise Fault('CONFIG','first batch only permits authenticated loopback')
    state=State(root); stop=threading.Event(); started=now(); epoch=uid()
    atomic(state.data/'config.json',canonical(state.config))
    from pathlib import Path
    repo=Path(__file__).resolve().parents[1]
    loaded_files={p.relative_to(repo).as_posix():file_hash(p) for folder in ['uacf','contracts'] for p in (repo/folder).rglob('*') if p.suffix in ['.py','.json','.sql']}
    loaded_identity=sha(loaded_files)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,value,html=False,cookie=None):
            b=value.encode() if html else canonical(value).encode()
            self.send_response(status); self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
            if cookie:
                for value in cookie if isinstance(cookie,list) else [cookie]:self.send_header('Set-Cookie',value)
            self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            if self.headers.get('Host','') not in [f'127.0.0.1:{server.server_port}',f'localhost:{server.server_port}']:
                self.send(403,{'ok':False,'code':'HOST'});return
            if self.path=='/browser/session':
                from .browser_session import authenticate
                try:
                    actor=authenticate(state,self.headers.get('Cookie',''),server.server_port)
                    from .browser_session import issue
                    self.send(200,{'ok':True,'authenticated':True,'actor':actor,'authority_id':state.authority},cookie=issue(state,actor,server.server_port))
                except Fault:self.send(200,{'ok':True,'authenticated':False})
                return
            if self.path in ['/observatory.js','/catalog.js','/workspace.js','/auth.js','/e7.js','/workflow.js','/learning.js','/portable.js']:
                from pathlib import Path
                b=(Path(__file__).resolve().parents[1]/'apps/control-surface'/self.path[1:]).read_bytes()
                self.send_response(200); self.send_header('Content-Type','application/javascript; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(b); return
            if self.path=='/':
                from pathlib import Path
                self.send(200,(Path(__file__).resolve().parents[1]/'apps/control-surface/index.html').read_text(encoding='utf-8'),True); return
            if self.path=='/e7':
                from pathlib import Path
                self.send(200,(Path(__file__).resolve().parents[1]/'apps/control-surface/e7.html').read_text(encoding='utf-8'),True); return
            if self.path=='/health':
                self.send(200,{'ok':True,'schema_version':'1.0','version':'0.2.0','authority_id':state.authority,'pid':os.getpid(),'epoch':epoch,'started_at':started,'loaded_source_identity':loaded_identity}); return
            self.send(404,{'ok':False,'code':'NOT_FOUND'})
        def do_POST(self):
            try:
                from .browser_session import authenticate,origin_allowed,issue,clear,consume_launch_ticket
                if self.headers.get('Host','') not in [f'127.0.0.1:{server.server_port}',f'localhost:{server.server_port}']:raise Fault('PERMISSION','unexpected loopback Host')
                bearer=self.headers.get('Authorization','').removeprefix('Bearer ')
                if self.path=='/browser/launch':
                    if not origin_allowed(self.headers,server.server_port):raise Fault('PERMISSION','same-origin local launch required')
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=4096:raise Fault('LIMIT','launch request size invalid')
                    actor=consume_launch_ticket(state,json.loads(self.rfile.read(length))['ticket'],server.server_port)
                    self.send(200,{'ok':True,'authenticated':True,'actor':actor,'authority_id':state.authority},cookie=issue(state,actor,server.server_port));return
                if self.path in ['/browser/session','/browser/logout']:
                    if not origin_allowed(self.headers,server.server_port):raise Fault('PERMISSION','same-origin browser pairing required')
                    if self.path=='/browser/logout':self.send(200,{'ok':True},cookie=clear(server.server_port));return
                    actor=state.authenticate(bearer)
                    self.send(200,{'ok':True,'authenticated':True,'actor':actor,'authority_id':state.authority},cookie=issue(state,actor,server.server_port));return
                if bearer:actor=state.authenticate(bearer)
                else:
                    if not origin_allowed(self.headers,server.server_port):raise Fault('PERMISSION','same-origin browser action required')
                    actor=authenticate(state,self.headers.get('Cookie',''),server.server_port)
                if self.path!='/v1/action': raise Fault('NOT_FOUND','unknown route')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=12*1024*1024: raise Fault('LIMIT','request body size invalid')
                message=json.loads(self.rfile.read(length)); result=execute_command(state,actor,message)
                self.send(200,result)
            except Fault as e: self.send({'AUTHENTICATION':401,'PERMISSION':403,'NOT_FOUND':404,'REVISION_CONFLICT':409,'OPERATION_CONFLICT':409}.get(e.code,400),e.result())
            except (KeyError,ValueError,TypeError) as e: self.send(400,Fault('INPUT',str(e)).result())
            except Exception:
                self.send(500,Fault('INTERNAL','service error; see local logs').result())
                import traceback
                with (state.root/'logs/service-errors.log').open('a',encoding='utf-8') as f: traceback.print_exc(file=f)
    server=LocalStateServer((bind,port or state.config['port']),Handler)
    def worker():
        while not stop.wait(.25):
            try:
                state.worker_once()
                from .learning import maintain
                maintain(state)
                from .archive_trigger import maintain as archive_maintain
                archive_maintain(state)
            except Exception:
                import traceback
                with (state.root/'logs/worker-errors.log').open('a',encoding='utf-8') as f: traceback.print_exc(file=f)
    thread=threading.Thread(target=worker,daemon=True); thread.start()
    atomic(state.data/'service-identity.json',canonical({'pid':os.getpid(),'epoch':epoch,'started_at':started,'port':server.server_port,'authority_id':state.authority,'loaded_source_identity':loaded_identity,'loaded_files':loaded_files}))
    try: server.serve_forever()
    finally: stop.set(); server.server_close(); thread.join(2)

def call(root,action,args,actor='owner',operation_id=None):
    state=State(root); auth=json.loads((state.data/'auth.json').read_text()); args=args.copy()
    if action=='put':
        args.pop('request_hash',None); args['actor']=actor; args['request_hash']=sha(args)
    cfg=state.config
    message={'action':action,'args':args}
    if action in MUTATIONS:
        import uuid
        oid=operation_id or (args['operation_id'] if action=='put' else uid())
        message.update(operation_id=oid,actor=actor,correlation_id=str(uuid.uuid5(uuid.UUID(oid),'correlation')),schema_version='1.0',scope='action:'+action,
            expected_revision=args.get('expected_revision',args.get('revision',0)))
        message['request_hash']=sha(message)
    r=urllib.request.Request(f"http://{cfg['bind']}:{cfg['port']}/v1/action",data=canonical(message).encode(),headers={'Authorization':'Bearer '+auth[actor],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(r,timeout=110 if action in ['model_dispatch','review_response','interpret','archive_inventory','archive_run','archive_reindex'] else 30) as response: return json.load(response)
    except urllib.error.HTTPError as e:
        result=json.load(e); raise Fault(result['code'],result['detail'])
    except urllib.error.URLError: raise Fault('CORE_UNAVAILABLE','service unavailable; no automatic mutation retry')

MUTATIONS.add('learning_reconcile')

MUTATIONS.update(['learning_enable_use','learning_rebuild_use'])

MUTATIONS.add('learning_probe')
MUTATIONS.update(['learning_semantic_build','learning_semantic_submit'])
MUTATIONS.update(['learning_bind_host','learning_checkpoint','portable_import'])
