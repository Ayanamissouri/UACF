"""Bounded exchange snapshots and fenced executors. Foreign data never owns local heads."""
import base64, json, re, time, zipfile
from pathlib import Path, PurePosixPath
from .util import Fault, atomic, canonical, file_hash, now, sha, uid
from .state import object_new, request, stale, verify_backup
from .fabric import owner, vector

ACTIONS={'exchange_export','exchange_import','exchange_status','exchange_context','lease_acquire','lease_check','lease_result','budget_open'}
MUTATIONS=ACTIONS-{'exchange_status','exchange_context','lease_check'}
MAX_BYTES=8*1024*1024

def assert_secret_bytes(state,body):
    # Blob membership/hash and object ACL do not themselves prove safe egress.
    auth=json.loads((state.data/'auth.json').read_text())
    for v in auth.values():
        if isinstance(v,str) and v and any(v.encode(e) in body for e in ['utf-8','utf-16-le','utf-16-be']):
            raise Fault('SECRET','runtime credential bytes found; package refused')
    for text in [body.decode('utf-8',errors='ignore'),body.decode('utf-16-le',errors='ignore'),body.decode('utf-16-be',errors='ignore')]:
        if re.search(r'(?i)sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}',text):
            raise Fault('SECRET','credential-like blob material refused')

def workspace_path(state,raw):
    p=Path(raw).resolve()
    if not p.is_relative_to(state.root): raise Fault('PATH_SCOPE','writes/reads of exchange files require selected UACF root')
    return p

def migrate3(state,backup):
    verify_backup(backup)
    m=json.loads((Path(backup)/'manifest.json').read_text())
    if m['authority_id']!=state.authority: raise Fault('BACKUP_AUTHORITY','backup not from current authority')
    # Recovery must be proven by the caller before this explicit migration.
    with state.db() as c:
        v=c.execute('PRAGMA user_version').fetchone()[0]
        if v not in [2,3]: raise Fault('SCHEMA_VERSION','batch3 migration requires database 2 or 3')
        c.executescript((Path(__file__).resolve().parents[1]/'contracts/migrations/003.sql').read_text())
    return {'ok':True,'database_version':3,'authority_id':state.authority,'budget_account':'batch3'}

def assert_no_secrets(state,value):
    text=canonical(value)
    auth=json.loads((state.data/'auth.json').read_text())
    if any(isinstance(v,str) and v and v in text for v in auth.values()): raise Fault('SECRET','runtime credential found; package refused')
    for pattern in [r'(?i)sk-[A-Za-z0-9_-]{16,}',r'(?i)Bearer\s+[A-Za-z0-9._-]{16,}']:
        if re.search(pattern,text): raise Fault('SECRET','credential-like material refused')
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if re.fullmatch(r'(?i)(api[_-]?key|password|secret|access[_-]?token|refresh[_-]?token|credential)',k) and v not in [None,'unknown','redacted']: raise Fault('SECRET','sensitive field refused')
                walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(value)

def export(state,actor,args):
    owner(actor)
    target=workspace_path(state,args['path'])
    if target.exists(): raise Fault('ALREADY_EXISTS','export never overwrites an existing package')
    task=state.get(args['task_id'],actor)
    if task['object_type']!='TaskContract': raise Fault('INPUT','TaskContract required')
    if args.get('task_revision')!=task['revision']: raise Fault('REVISION_CONFLICT','handoff target changed')
    destination=args.get('destination','local-isolated')
    if destination!='local-isolated': raise Fault('REMOTE_AUTH_MISSING','only authorized local isolated exchange; real remote requires explicit permission')
    capsule=state.context(actor,task['object_id'],args.get('max_bytes',200000))
    if capsule['status']!='ready': raise Fault('HANDOFF_INCOMPLETE','required dependencies missing/overflow; repair before exchange')
    private=args.get('include_private',False)
    selected={};pending=[(task['object_id'],task['revision']),*((i,None) for i in args.get('object_ids',[]))]
    # Include current intent, all applicable failures and ResponseContracts, not only task direct links.
    cap=capsule['capsule']
    for o in cap.get('response_contracts',[])+cap.get('failure_candidates',[])+cap.get('task_evidence',[]):
        if isinstance(o,dict) and 'object_id' in o: pending.append((o['object_id'],o['revision']))
    for intent in cap.get('selected_claims',[]):
        pending.extend([(intent['decision']['object_id'],intent['decision']['revision']),(intent['claim']['object_id'],intent['claim']['revision'])])
    missing=[]
    with state.db() as c:
        c.execute('BEGIN')
        commit=c.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0]
        while pending:
            oid,revision=pending.pop()
            o=state._get(c,oid,actor,revision)
            key=(oid,o['revision'])
            if key in selected: continue
            if o['visibility']=='private' and not private: raise Fault('EGRESS_PERMISSION','private closure requires explicit include_private for local isolated destination')
            if len(selected)>=256: raise Fault('LIMIT','bounded closure exceeds 256 objects')
            selected[key]=o
            pending.extend((i,None) for i in o.get('provenance_refs',[]))
            pending.extend((r[0],r[1]) for r in c.execute('SELECT target_id,target_revision FROM object_links WHERE object_id=? AND revision=?',(oid,o['revision'])))
        # Ensure the earlier Capsule snapshot still refers to this exact task and dependency heads.
        for o in selected.values():
            if o['authority_id']!=state.authority: raise Fault('AUTHORITY','foreign historical envelopes cannot be reissued as local authority; retain their external snapshot package')
            if o['object_type'] in ['TaskContract','ResponseContract','Claim','AdoptionDecision','SemanticCard','Dossier'] and stale(state,o): raise Fault('DEPENDENCY_STALE','exchange includes stale effective dependency; local rebuild required')
        if state._get(c,task['object_id'],actor)['revision']!=task['revision']: raise Fault('REVISION_CONFLICT','task changed during export')
        for o in cap.get('response_contracts',[])+cap.get('failure_candidates',[])+cap.get('task_evidence',[]):
            if state._get(c,o['object_id'],actor)['revision']!=o['revision']: raise Fault('REVISION_CONFLICT','capsule changed during export; refresh context')
    records=list(selected.values()); resources=[]; entries={}
    for o in records:
        name=f"objects/{o['object_id']}/{o['revision']}.json";entries[name]=canonical(o).encode()
        p=o['payload']
        if o['object_type']=='Artifact' and isinstance(p.get('locator'),str) and p['locator'].replace('\\','/').split('?',1)[0].rsplit('/',1)[-1].lower()=='api.txt':
            raise Fault('SECRET','API.txt artifacts are excluded from exchange')
        for attachment in p.get('attachments',[]): resources.append({'object_id':o['object_id'],'kind':'attachment','state':'referenced' if attachment.get('locator') else 'missing','body_included':False,'locator':attachment.get('locator'),'verified':False})
        if o['object_type'] in ['SourceSet','Locator']: resources.append({'object_id':o['object_id'],'kind':'original','state':'referenced','body_included':False,'original_read_only':True})
        if 'record' in p: resources.append({'object_id':o['object_id'],'kind':'raw_record','state':'included','body_included':True})
        # Required blobs are included only through object-scoped authorization and byte/hash checks.
        with state.db() as c: hashes=[r[0] for r in c.execute('SELECT hash FROM revision_blobs WHERE object_id=? AND revision=?',(o['object_id'],o['revision']))]
        for h in hashes:
            bp=state.data/'blobs'/h[:2]/h
            if not bp.is_file() or file_hash(bp)!=h: raise Fault('BLOB_MISSING','required exchange body missing')
            body=bp.read_bytes();assert_secret_bytes(state,body)
            entries['blobs/'+h]=body;resources.append({'object_id':o['object_id'],'kind':'blob','state':'included','sha256':h,'body_included':True})
    handoff={'capsule':cap,'next_action':args.get('next_action'),'task_state':task['payload'].get('execution_state','unknown'),'authority_boundary':'foreign snapshot is evidence only; local authorization must be re-established','body_and_attachments':resources,'source_paths':'references only; path mapping never moves originals'}
    if not handoff['next_action']: raise Fault('INPUT','explicit next_action required')
    entries['handoff.json']=canonical(handoff).encode()
    assert_no_secrets(state,{'records':records,'handoff':handoff})
    import hashlib
    manifest={'exchange_version':'1.0','payload_contract':'batch3-1','envelope_version':'1.0','source_authority':state.authority,'destination':destination,'commit_seq':commit,'task_id':task['object_id'],'task_revision':task['revision'],'base_vector':[vector(o) for o in records],'created_at':now(),'permissions':{'private_included':private,'canonical_write_authority_transferred':False},'resources':resources,'files':{k:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for k,v in entries.items()},'manifest_authenticity':'hash integrity only; trusted local authorized input, no remote signature'}
    if sum(map(len,entries.values()))>MAX_BYTES: raise Fault('LIMIT','exchange expanded bytes exceeded')
    import io
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',canonical(manifest))
        for k,v in entries.items(): z.writestr(k,v)
    atomic(target,buf.getvalue())
    return {'ok':True,'path':str(target),'package_hash':file_hash(target),'objects':len(records),'manifest':manifest,'next_action':handoff['next_action']}

def read_package(state,args):
    path=workspace_path(state,args['path'])
    if not path.is_file() or path.stat().st_size>MAX_BYTES: raise Fault('LIMIT','package missing or oversized')
    digest=file_hash(path)
    if digest!=args.get('package_hash'): raise Fault('HASH','explicit package hash mismatch')
    import hashlib
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)>1024: raise Fault('PACKAGE','duplicate/excessive members')
        for n in names:
            p=PurePosixPath(n)
            if p.is_absolute() or '..' in p.parts or '\\' in n or ':' in n: raise Fault('PACKAGE','unsafe member')
        if sum(i.file_size for i in z.infolist())>MAX_BYTES: raise Fault('LIMIT','expanded quota exceeded')
        m=json.loads(z.read('manifest.json'))
        if m.get('exchange_version')!='1.0' or m.get('envelope_version')!='1.0' or m.get('payload_contract')!='batch3-1': raise Fault('VERSION_INCOMPATIBLE','exchange contract unsupported')
        if set(names)!=set(m['files'])|{'manifest.json'}: raise Fault('PACKAGE','manifest membership mismatch')
        bodies={}
        for n,info in m['files'].items():
            body=z.read(n)
            if len(body)!=info['bytes'] or hashlib.sha256(body).hexdigest()!=info['sha256']: raise Fault('HASH','member hash mismatch')
            if n.startswith('blobs/'):
                if n!='blobs/'+info['sha256']: raise Fault('HASH','blob member name differs from content hash')
                assert_secret_bytes(state,body)
            bodies[n]=body
        objs=[]
        for name,body in bodies.items():
            if not name.startswith('objects/'): continue
            obj=json.loads(body)
            if name!=f"objects/{obj['object_id']}/{obj['revision']}.json": raise Fault('PACKAGE','object member identity/revision mismatch')
            objs.append(obj)
        if len(objs)>256: raise Fault('LIMIT','object count exceeded')
        for o in objs:
            state.validator.validate(o)
            if o['authority_id']!=m['source_authority']: raise Fault('AUTHORITY','object authority differs from manifest')
            locator=o['payload'].get('locator')
            if o['object_type']=='Artifact' and isinstance(locator,str) and locator.replace('\\','/').split('?',1)[0].rsplit('/',1)[-1].lower()=='api.txt': raise Fault('SECRET','API.txt artifacts excluded from import')
            h=o['payload'].get('blob_hash')
            if h and 'blobs/'+h not in bodies: raise Fault('BLOB_MISSING','object blob reference not included in package')
        if len({(o['object_id'],o['revision']) for o in objs})!=len(objs): raise Fault('PACKAGE','duplicate object revision')
        if sorted([vector(o) for o in objs],key=canonical)!=sorted(m['base_vector'],key=canonical): raise Fault('PACKAGE','base vector mismatch')
        h=json.loads(bodies['handoff.json']);assert_no_secrets(state,{'objects':objs,'handoff':h})
        tasks=[o for o in objs if o['object_type']=='TaskContract' and o['object_id']==m['task_id'] and o['revision']==m['task_revision']]
        if len(tasks)!=1 or h.get('capsule',{}).get('task')!=tasks[0] or h['capsule'].get('task_revision')!=m['task_revision']:
            raise Fault('PACKAGE','manifest, canonical task snapshot and capsule disagree')
    return digest,m,objs,h

def import_package(state,actor,args):
    owner(actor)
    if args.get('accept_as')!='external_snapshot': raise Fault('PERMISSION','only external_snapshot import; no automatic adoption')
    digest,m,objs,h=read_package(state,args)
    mapping=args.get('path_map',{})
    if not isinstance(mapping,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in mapping.items()): raise Fault('INPUT','explicit string path map required')
    with state.db() as c:
        c.execute('BEGIN IMMEDIATE')
        prior=c.execute('SELECT * FROM exchange_imports WHERE package_hash=?',(digest,)).fetchone()
        if not prior: c.execute('INSERT INTO exchange_imports VALUES(?,?,?,?,?,?)',(digest,m['source_authority'],0,len(objs),'importing',canonical({'manifest':m,'handoff':h,'path_map':mapping,'mapping_applied_to_originals':False})))
        elif json.loads(prior['manifest'])['path_map']!=mapping: raise Fault('IMPORT_CONFLICT','resume mapping changed')
    for i,o in enumerate(objs):
        with state.db() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR IGNORE INTO exchange_records VALUES(?,?,?,?)',(digest,o['object_id'],o['revision'],canonical(o)))
            c.execute('UPDATE exchange_imports SET cursor=MAX(cursor,?) WHERE package_hash=?',(i+1,digest))
        if args.get('interrupt_after')==i+1: raise Fault('INTERRUPTED','committed snapshot checkpoint; explicit resume same package')
    with state.db() as c: c.execute("UPDATE exchange_imports SET state='ready' WHERE package_hash=?",(digest,))
    return {'ok':True,'package_hash':digest,'objects':len(objs),'duplicate':bool(prior and prior['state']=='ready'),'source_authority':m['source_authority'],'local_authority':state.authority,'canonical_heads_modified':False,'adopted':False,'body_blobs':'validated inside immutable exchange ZIP; not registered as local Artifact','status':'ready'}

def exchange_context(state,actor,args):
    owner(actor)
    with state.db() as c:
        row=c.execute('SELECT * FROM exchange_imports WHERE package_hash=?',(args['package_hash'],)).fetchone()
        if not row: raise Fault('NOT_FOUND','import absent')
        result=dict(row);meta=json.loads(result.pop('manifest'));result.update(meta)
        conflicts=[]
        for record in c.execute('SELECT body FROM exchange_records WHERE package_hash=?',(args['package_hash'],)):
            obj=json.loads(record['body']);head=c.execute('SELECT head FROM objects WHERE id=?',(obj['object_id'],)).fetchone()
            if head and (obj['authority_id']!=state.authority or head[0]!=obj['revision']):
                conflicts.append({'object_id':obj['object_id'],'imported_revision':obj['revision'],'local_revision':head[0],'resolution':'preserve local head; explicit Contribution and IntegrationDecision required'})
        result['conflicts']=conflicts
        if row['state']!='ready': result['handoff']=None
        result.update(ok=True,local_authority=state.authority,canonical_write=False,authorization='foreign authorization is historical evidence only')
        return result

def lease(state,actor,action,args):
    owner(actor);scope=args['scope']
    if not isinstance(scope,str) or not scope or len(scope)>200: raise Fault('INPUT','bounded lease scope required')
    with state.db() as c:
        c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM executor_leases WHERE scope=?',(scope,)).fetchone()
        if action=='lease_acquire':
            task=state._get(c,args['task_id'],actor)
            if task['revision']!=args['task_revision'] or stale(state,task): raise Fault('DEPENDENCY_STALE','current task revision required')
            ttl=args.get('ttl',30)
            if not isinstance(ttl,(int,float)) or not .1<=ttl<=300: raise Fault('INPUT','lease TTL .1..300 seconds')
            if r and r['expires']>time.time(): raise Fault('LEASE_BUSY','live executor already owns scope')
            fence=(r['fence'] if r else 0)+1
            c.execute('INSERT OR REPLACE INTO executor_leases VALUES(?,?,?,?,?,?)',(scope,args['holder'],fence,time.time()+ttl,task['object_id'],task['revision']))
            return {'ok':True,'scope':scope,'holder':args['holder'],'fence':fence,'ttl':ttl,'guarantee':'UACF scoped execution authorization; cannot cancel an already external action'}
        valid=bool(r and r['holder']==args['holder'] and r['fence']==args['fence'] and r['expires']>time.time())
        if valid:
            task=state._get(c,r['task_id'],actor)
            valid=task['revision']==r['task_revision'] and not stale(state,task) and task['payload'].get('execution_state')!='stopped'
    if action=='lease_check':
        if not valid: raise Fault('FENCED','lease expired/replaced or task dependency changed')
        return {'ok':True,'authorized':True,'lease':dict(r)}
    # Late observations are durable history, but never renew authority or change plans.
    o=object_new('Evidence',{'observation':args['observation'],'scope':scope,'holder':args['holder'],'fence':args['fence'],'executor_current':valid,'outcome':args.get('outcome','unknown'),'recorded_at':now(),'plan_modified':False})
    ev=state.put(request(o),actor)['object']
    return {'ok':True,'evidence':ev,'executor_current':valid,'plan_modified':False,'retry':'never automatic'}

def dispatch_batch3(state,actor,action,args,oid=None):
    from jsonschema import Draft202012Validator,FormatChecker
    contract=json.loads((Path(__file__).resolve().parents[1]/'contracts/actions-batch3.schema.json').read_text())
    errors=list(Draft202012Validator(contract['actions'][action],format_checker=FormatChecker()).iter_errors(args))
    if errors: raise Fault('INPUT','batch3 typed action contract: '+errors[0].message)
    if action=='exchange_export': return export(state,actor,args)
    if action=='exchange_import': return import_package(state,actor,args)
    if action in ['exchange_status','exchange_context']: return exchange_context(state,actor,args)
    if action.startswith('lease_'): return lease(state,actor,action,args)
    if action=='budget_open':
        owner(actor)
        authorized={'batch3':30000000,'aoe4-20261004':20000000}
        account=args.get('account')
        if 'task_ref' in args:
            if set(args)!={'account','limit_micro','currency','task_ref'}:raise Fault('INPUT','exact new account authorization')
            task=state.get(args['task_ref']['object_id'],actor)
            if vector(task)!=args['task_ref']:raise Fault('REVISION_CONFLICT','current budget authorization Task required')
            auth=task['payload'].get('budget_authorization') or task['payload'].get('new100_authorization',{})
            limit=auth.get('limit_micro',auth.get('ceiling_CNY',0)*1000000)
            if not isinstance(account,str) or not re.fullmatch('[a-z][a-z0-9-]{2,80}',account) or account in ['batch2','batch3','batch4','aoe4-20261004'] or auth.get('account')!=account or type(limit)!=int or limit<1 or args['limit_micro']!=limit or args['currency']!='CNY' or not auth.get('authorization_source',auth.get('basis')) or task['payload'].get('allow_provider') is not True:raise Fault('PERMISSION','explicit independent current Task amount authorization required')
            authorized[account]=limit
        elif account not in authorized or args!={'account':account,'limit_micro':authorized[account],'currency':'CNY'}:raise Fault('PERMISSION','fixed legacy account or explicit new Task authorization required')
        with state.db() as c:
            old=c.execute('SELECT currency,limit_micro FROM budget_accounts WHERE id=?',(account,)).fetchone()
            if old and (old[0]!='CNY' or old[1]!=authorized[account]):raise Fault('BUDGET_ACCOUNT_MISMATCH','never expand or replace an existing account')
            c.execute('INSERT OR IGNORE INTO budget_accounts VALUES(?,?,?,0,1)',(account,'CNY',authorized[account]))
        from .batch2 import budget_get
        return budget_get(state,account)
    raise Fault('UNSUPPORTED','unknown batch3 action')
