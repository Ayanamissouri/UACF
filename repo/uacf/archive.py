"""Bounded immutable GPT archive extension. Same State authority; no paid replay."""
import json,re,zipfile,time,html,hashlib
from collections import Counter
from pathlib import Path,PurePosixPath
from .util import Fault,canonical,sha,uid,now,atomic,file_hash
from .state import verify_backup,restore
from .fabric import owner,save,stable_id,vector

CONTRACT='batch4-1';PARSER='gpt-archive-1'
ACTIONS={'archive_inventory','archive_plan','archive_run','archive_coverage','archive_read','archive_materialize','archive_reindex','reading_plan'}
MUTATIONS=ACTIONS-{'archive_coverage'}
FACETS=['inventory','structure','branches','attachment_linkage','attachment_bodies','semantics','affiliations','discourse','failures','index','daily_handoff']

def migrate4(state,backup):
    verify_backup(backup)
    m=json.loads((Path(backup)/'manifest.json').read_text())
    if m['authority_id']!=state.authority:raise Fault('BACKUP_AUTHORITY','wrong authority')
    recovered=state.root/'backups'/('batch4-migration-recovery-'+uid())
    doctor=restore(backup,recovered)
    if not doctor['ok']:raise Fault('BACKUP_INCOMPLETE','recovery failed')
    with state.db() as c:
        if c.execute('PRAGMA user_version').fetchone()[0]!=3:raise Fault('SCHEMA_VERSION','E7 requires schema3')
        c.executescript((Path(__file__).resolve().parents[1]/'contracts/migrations/004-archive.sql').read_text())
    return {'ok':True,'database_version':3,'extension':CONTRACT,'authority':state.authority,'recovery':str(recovered),'doctor':doctor,'budget_limit_micro':45000000}

def safe_member(name):
    p=PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name and not any(x in name.lower() for x in ['api.txt','pika','学长'])

def snapshot(path):
    st=path.stat();return {'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}

def check_source(state,source):
    p=Path(source['payload']['roots'][0]);a=source['payload']['authorization']
    if not p.is_file():raise Fault('SOURCE_MISSING','original offline; cached coverage still available')
    if snapshot(p)!=a['snapshot']:raise Fault('SOURCE_CHANGED','snapshot changed; verify hash and register new revision, no relocation')
    return p

def plan_get(state,actor,pid):
    owner(actor)
    with state.db() as c:r=c.execute('SELECT * FROM archive_plans WHERE id=?',(pid,)).fetchone()
    if not r:raise Fault('NOT_FOUND','archive plan missing')
    plan=json.loads(r['plan']); source=state.get(r['source_id'],actor)
    if source['revision']!=plan['source_revision']:raise Fault('DEPENDENCY_STALE','source changed')
    return plan,source

def inventory(state,actor,args):
    owner(actor);path=Path(args['path']).resolve()
    if not path.is_file() or path.suffix.lower()!='.zip' or not safe_member(path.name):raise Fault('SOURCE_EXCLUDED','authorized ZIP required')
    before=snapshot(path);h=file_hash(path)
    if snapshot(path)!=before:raise Fault('SOURCE_CHANGED','source changed during identity read')
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>20000:raise Fault('SOURCE_LIMIT','directory quota 20000')
        names=Counter(i.filename for i in infos);entries=[]
        for i in infos:
            state_='duplicate' if names[i.filename]>1 else 'unsafe' if not safe_member(i.filename) else 'encrypted' if i.flag_bits&1 else 'oversize' if i.file_size>64*1024*1024 and i.filename.endswith('.json') else 'registered'
            entries.append({'member':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'crc32':f'{i.CRC:08x}','state':state_})
        mapping={};mapping_status='missing'
        name='conversation_asset_file_names.json'
        if names[name]==1:
            i=z.getinfo(name)
            if i.file_size<=4*1024*1024:
                mapping=json.loads(z.read(name));mapping_status='parsed'
                if not isinstance(mapping,dict):raise Fault('SOURCE_FORMAT','asset name mapping must be object')
    oid=stable_id('archive-source',str(path),h)
    try:source=state.get(oid,actor)
    except Fault as e:
        if e.code!='NOT_FOUND':raise
        source=save(state,'SourceSet',{'roots':[str(path)],'authorization':{'kind':'user_scope','basis':args['authorization_basis'],'sha256':h,'snapshot':before},'limits':{'max_bytes':2097152,'max_records':64,'member_max_bytes':67108864,'conversation_max_bytes':16777216,'records_per_run':32},'original_access':'read-only','archive_contract':CONTRACT},oid=oid)
    result={'source_id':oid,'source_revision':source['revision'],'source_hash':h,'snapshot':before,'entries':entries,'mapping':mapping,'mapping_status':mapping_status,'identity_bytes_read':before['bytes'],'mapping_bytes_read':sum(e['bytes'] for e in entries if e['member']==name),'semantic_cost':'not_run','observed_at':now()}
    dest=state.data/'archive'/oid/'inventory.json';atomic(dest,canonical(result))
    return {'ok':True,'source':source,'inventory':str(dest),'members':len(entries),'mapping_entries':len(mapping),'source_hash':h,'identity_bytes_read':before['bytes'],'excluded_members':sum(e['state']!='registered' for e in entries)}

def make_plan(state,actor,args):
    owner(actor);source=state.get(args['source_id'],actor);check_source(state,source)
    inv=json.loads((state.data/'archive'/source['object_id']/'inventory.json').read_text(encoding='utf-8'))
    shards=[e for e in inv['entries'] if re.fullmatch(r'conversations-\d+\.json',e['member']) and e['state']=='registered']
    scope=args.get('members') or [e['member'] for e in shards]
    if not scope or len(scope)!=len(set(scope)) or any(n not in {e['member'] for e in shards} for n in scope):raise Fault('INPUT','unique registered shard scope required')
    plan={'contract':CONTRACT,'parser':PARSER,'source_id':source['object_id'],'source_revision':source['revision'],'source_hash':inv['source_hash'],'members':sorted(scope),'member_limit':67108864,'conversation_limit':16777216,'attachment_sample_limit':24,'attachment_max_bytes':8388608,
      'facets':{'inventory':'whole ZIP directory + mapping','structure':'all conversations and nodes in selected shards','branches':'all parent/current-node edges; anomalies explicit','attachment_linkage':'exact refs only; missing/ambiguous/orphan scoped counts','attachment_bodies':'up to24 exact-linked <=8MiB each; no automatic visual acceptance','semantics':'12 frozen stratified candidates; independent review required','affiliations':'candidate or explicit source basis; no keyword adoption','discourse':'selected source-grounded candidates','failures':'selected evidence; historical learner errors separate','index':'local directory and canonical selected messages','daily_handoff':'one real daily source-linked task plus correction'},
      'semantic_egress':'no automatic dispatch','budget_account':'batch4','limit_micro':45000000,'thresholds':{'hard_counterexamples':'zero violations in scoped cases','exact_linking':'zero guesses; unresolved allowed','parse_integrity':'100% hashes/record checks for committed nodes','semantic':'human each>=1/2; missing remains partial','cost':'spent+locked<=45000000'},
      'stratified_sample_rules':{'count':12,'ordered_strata':['first_main_user','first_alternate_user','first_exact_linked_image','first_missing_attachment','literal_HDMR','literal_聚合物','literal_BOM','literal_crew cabin','first_tool','first_multi_attachment','last_shard_main_user','first_main_assistant'],'selection':'first in member/ordinal/node order satisfying each predicate; no substitutions without separate revision; lexical strata are retrieval candidates, never adopted project affiliation'},
      'counterexample_pairs':{'B4-T01':['exact opaque pointer resolves','similar name does not resolve'],'B4-T02':['durable interrupted parse resumes','unknown paid dispatch never resumes'],'B4-T03':['REINDEX zero raw reads','new meaning requires local FULL'],'B4-T04':['historical source stays current=false','current explicit correction updates scoped adoption'],'B4-T05':['normal capsule ready','mandatory overflow refuses'],'B4-T06':['body hash proves bytes','image meaning requires actual view and independent judgment'],'B4-T07':['budget atomic reserve succeeds within45','overlapping reserve exceeding45 rejects'],'B4-T08':['new isolated recovery preserves increment','old database never copied over authority']},
      'quality_denominators':'processed conversations/nodes/messages/main/alternate/null separately; semantic reviewed count separate; unknown never zero','cost_dimensions':['identity_bytes_read','parse_bytes_read','attachment_bytes_read','semantic_calls','actual_usage','spent_micro','locked_micro','elapsed_s'],'frozen_at':now()}
    pid=sha({k:v for k,v in plan.items() if k!='frozen_at'})
    with state.db() as c:
        c.execute('INSERT OR IGNORE INTO archive_plans VALUES(?,?,?,?,?)',(pid,source['object_id'],CONTRACT,canonical(plan),now()))
        for n in scope:c.execute('INSERT OR IGNORE INTO archive_progress VALUES(?,?,0,?,?)',(pid,n,'pending','{}'))
        for e in inv['entries']:
            detail=dict(e,original_name=inv['mapping'].get(e['member']),body='not_read')
            c.execute('INSERT OR IGNORE INTO archive_assets VALUES(?,?,?)',(pid,e['member'],canonical(detail)))
    atomic(state.root/'logs'/('batch4-plan-'+pid+'.json'),canonical(plan))
    return {'ok':True,'plan_id':pid,'plan':plan}

def conversations(stream,limit):
    """Streaming array decoder; bounded buffer per conversation, no shard-wide load."""
    import codecs
    decoder=codecs.getincrementaldecoder('utf-8')();buf='';started=False;eof=False;index=0;total=0;delimiter=False
    while True:
        if not started:
            if not buf.strip():
                raw=stream.read(65536);total+=len(raw);buf+=decoder.decode(raw,final=not raw);eof=not raw
                if eof:raise Fault('SOURCE_FORMAT','empty shard')
            buf=buf.lstrip()
            if not buf.startswith('['):raise Fault('SOURCE_FORMAT','GPT array required')
            buf=buf[1:];started=True
        buf=buf.lstrip()
        if not buf and not eof:
            raw=stream.read(65536);total+=len(raw);buf+=decoder.decode(raw,final=not raw);eof=not raw;continue
        if buf.startswith(']'):
            trailing=buf[1:]
            while not eof:
                raw=stream.read(65536);total+=len(raw);trailing+=decoder.decode(raw,final=not raw);eof=not raw
                if len(trailing)>65536:raise Fault('SOURCE_FORMAT','excess trailing data')
            if trailing.strip():raise Fault('SOURCE_FORMAT','trailing non-whitespace')
            return
        if delimiter:
            if not buf.startswith(','):raise Fault('SOURCE_FORMAT','missing array separator')
            buf=buf[1:].lstrip();delimiter=False
            if buf.startswith(']'):raise Fault('SOURCE_FORMAT','trailing comma')
            continue
        try:
            obj,end=json.JSONDecoder().raw_decode(buf)
            if not isinstance(obj,dict):raise Fault('SOURCE_FORMAT','conversation object required')
            consumed=len(buf[:end].encode())
            if consumed>limit:raise Fault('SOURCE_LIMIT','conversation quota exceeded')
            yield index,obj,total;index+=1;buf=buf[end:];delimiter=True
        except json.JSONDecodeError:
            if eof:raise Fault('SOURCE_FORMAT','truncated or malformed shard')
            if len(buf.encode())>limit+65536:raise Fault('SOURCE_LIMIT','conversation quota exceeded')
            raw=stream.read(65536);total+=len(raw);buf+=decoder.decode(raw,final=not raw);eof=not raw

def pointers(value):
    out=[]
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ['asset_pointer','file_id','attachment_id'] and isinstance(v,str):out.append(v)
                elif k=='attachments' and isinstance(v,list):
                    for a in v:
                        if isinstance(a,dict) and isinstance(a.get('id'),str):out.append(a['id'])
                    walk(v)
                else:walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(value);return list(dict.fromkeys(out))

def resolve(pointer,assets):
    token=pointer.split('://',1)[-1]
    # exact archive name or exact opaque file id + .dat. No basename/fuzzy guesses.
    candidates=[n for n in [token,token+'.dat'] if n in assets]
    candidates=list(dict.fromkeys(candidates))
    valid=[n for n in candidates if assets[n].get('state')=='registered']
    status='resolved' if len(valid)==1 else 'ambiguous' if len(valid)>1 else 'missing'
    return {'status':status,'candidates':candidates,'members':valid,'basis':'exact pointer token or token+.dat; original-name mapping is descriptive only','body':'not_read','semantic':'not_verified'}

def run(state,actor,args):
    plan,source=plan_get(state,actor,args['plan_id']);path=check_source(state,source)
    maximum=args.get('max_conversations',32)
    if type(maximum)!=int or not 1<=maximum<=64:raise Fault('INPUT','1..64 conversations per bounded run')
    with state.db() as c:
        progress=[dict(r) for r in c.execute("SELECT * FROM archive_progress WHERE plan_id=? AND state!='done' ORDER BY member",(args['plan_id'],))]
        assets={r['member']:json.loads(r['detail']) for r in c.execute('SELECT * FROM archive_assets WHERE plan_id=?',(args['plan_id'],))}
    if not progress:return dict(coverage(state,actor,args),mode='REUSE',parse_bytes_read=0)
    selected=args.get('member')
    if selected:
        matching=[p for p in progress if p['member']==selected]
        if not matching:raise Fault('INPUT','member must be a frozen unfinished shard')
        p=matching[0]
    else:p=progress[0]
    member=p['member'];cursor=p['cursor'];began=time.monotonic();written=0;readbytes=0;done=False
    try:
        with zipfile.ZipFile(path) as z:
            info=z.getinfo(member)
            if not safe_member(member) or info.file_size>plan['member_limit']:raise Fault('SOURCE_LIMIT','unsafe/oversize member')
            with z.open(member) as f:
                for ordinal,conv,readbytes in conversations(f,plan['conversation_limit']):
                    if ordinal<cursor:continue
                    mapping=conv.get('mapping')
                    if not isinstance(mapping,dict):raise Fault('SOURCE_FORMAT','mapping missing/non-object')
                    main=set();current=conv.get('current_node');seen=set()
                    while current in mapping and current not in seen:
                        seen.add(current);main.add(current);current=mapping[current].get('parent')
                    stats={'nodes':len(mapping),'messages':0,'main_messages':0,'alternate_messages':0,'null_messages':0,'attachment_refs':0,'missing_parents':sum(bool(n.get('parent')) and n['parent'] not in mapping for n in mapping.values()),'current_node_missing':conv.get('current_node') not in mapping,'main_cycle':current in seen,'roles':{},'semantic':'not_run'}
                    rows=[];refs=[];roles=Counter()
                    for nodeid,node in mapping.items():
                        m=node.get('message');role=(m.get('author') or {}).get('role','unknown') if m else 'null';roles[role]+=1
                        branch='main' if nodeid in main else 'alternate:'+nodeid
                        if m:stats['messages']+=1;stats['main_messages' if nodeid in main else 'alternate_messages']+=1
                        else:stats['null_messages']+=1
                        content=(m or {}).get('content',{});rp=pointers(m or {})
                        kind='direct_user' if role=='user' else 'assistant' if role=='assistant' else 'tool' if role=='tool' else 'unknown'
                        detail={'conversation_id':conv.get('id',conv.get('conversation_id')),'branch':branch,'parent':node.get('parent'),'children':node.get('children'),'role':role,'source_kind':kind,'content_type':content.get('content_type'),'current':False,'attachments':rp,'text_preview':canonical(content)[:360],'body_cached':True,'semantic':'not_run'}
                        rows.append((args['plan_id'],member,ordinal,nodeid,sha(node),canonical(node),canonical(detail)))
                        for i,ptr in enumerate(rp):refs.append((args['plan_id'],member,ordinal,nodeid,i,ptr,canonical(resolve(ptr,assets))))
                    stats['roles']=dict(roles);stats['attachment_refs']=len(refs)
                    with state.db() as c:
                        c.execute('BEGIN IMMEDIATE')
                        actual=c.execute('SELECT cursor FROM archive_progress WHERE plan_id=? AND member=?',(args['plan_id'],member)).fetchone()[0]
                        if actual!=ordinal:raise Fault('REVISION_CONFLICT','archive cursor advanced; inspect then resume')
                        c.execute('INSERT INTO archive_conversations VALUES(?,?,?,?,?,?,?)',(args['plan_id'],member,ordinal,conv.get('id',conv.get('conversation_id')),conv.get('title'),sha(conv),canonical(stats)))
                        c.executemany('INSERT INTO archive_messages VALUES(?,?,?,?,?,?,?)',rows)
                        c.executemany('INSERT INTO archive_refs VALUES(?,?,?,?,?,?,?)',refs)
                        c.execute("UPDATE archive_progress SET cursor=?,state='running',receipt=? WHERE plan_id=? AND member=?",(ordinal+1,canonical({'last_conversation_hash':sha(conv),'parse_bytes_read':readbytes,'parser':PARSER}),args['plan_id'],member))
                    written+=1
                    if args.get('interrupt_after')==written:raise Fault('INTERRUPTED','explicit interruption after durable conversation; inspect cursor and resume with new operation')
                    if written>=maximum:break
                else:done=True
    except (zipfile.BadZipFile,UnicodeError,json.JSONDecodeError) as e:raise Fault('SOURCE_CORRUPT',type(e).__name__)
    if done:
        with state.db() as c:c.execute("UPDATE archive_progress SET state='done' WHERE plan_id=? AND member=?",(args['plan_id'],member))
    # original never written; cheap snapshot check rejects drift on each batch, full SHA used at registration.
    check_source(state,source)
    return {'ok':True,'plan_id':args['plan_id'],'member':member,'resumed_from':cursor,'conversations_committed':written,'member_done':done,'parse_bytes_read':readbytes,'identity_bytes_read':0,'identity_assurance':'registration full SHA256 + current stat guard; re-inventory for cryptographic refresh','semantic_calls':0,'elapsed_s':time.monotonic()-began}

def coverage(state,actor,args):
    plan,source=plan_get(state,actor,args['plan_id']);pid=args['plan_id'];totals=Counter();anomalies=Counter()
    with state.db() as c:
        progress=[dict(r) for r in c.execute('SELECT member,cursor,state FROM archive_progress WHERE plan_id=? ORDER BY member',(pid,))]
        for r in c.execute('SELECT stats FROM archive_conversations WHERE plan_id=?',(pid,)):
            q=json.loads(r[0]);totals['conversations']+=1
            for k in ['nodes','messages','main_messages','alternate_messages','null_messages','attachment_refs']:totals[k]+=q[k]
            for k in ['missing_parents','current_node_missing','main_cycle']:anomalies[k]+=q[k]
        refs=[json.loads(r[0]) for r in c.execute('SELECT resolution FROM archive_refs WHERE plan_id=?',(pid,))]
        used={n for r in refs for n in r['members']};linked=Counter(r['status'] for r in refs)
        assets=[dict(r) for r in c.execute('SELECT member,detail FROM archive_assets WHERE plan_id=?',(pid,))]
        dat={r['member'] for r in assets if r['member'].endswith('.dat')};mapping={r['member'] for r in assets if json.loads(r['detail']).get('original_name')}
        reads=[json.loads(r[0]) for r in c.execute('SELECT detail FROM archive_reads WHERE plan_id=?',(pid,))]
    all_done=all(r['state']=='done' for r in progress)
    return {'ok':True,'plan_id':pid,'authority_id':state.authority,'source_id':source['object_id'],'counts':dict(totals),'anomalies':dict(anomalies),'progress':progress,'scope':plan['facets'],'attachment_linkage':dict(linked),'unique_referenced_members':len(used),'unreferenced_dat_count':len(dat-used),'orphan_status':'full_scope_unreferenced' if all_done else 'scoped_not_yet_referenced','mapped_assets':len(mapping),'unmapped_dat_count':len(dat-mapping),'body_reads':len(reads),'attachment_bytes_read':sum(r['bytes'] for r in reads),'facets':{'inventory':'verified_directory','structure':'verified_scoped' if all_done else 'partial','branches':'verified_scoped_with_anomalies' if all_done else 'partial','attachment_linkage':'verified_exact_with_unresolved' if all_done else 'partial','attachment_bodies':'partial' if reads else 'not_read','semantics':'not_accepted','affiliations':'partial','discourse':'partial','failures':'partial','index':'available_directory_and_selected_canonical','daily_handoff':'see batch4 daily receipt'},'semantic_acceptance':False,'paid_calls':0,'budget':__import__('uacf.batch2',fromlist=['budget_get']).budget_get(state,'batch4')}

def read_asset(state,actor,args):
    plan,source=plan_get(state,actor,args['plan_id']);pid=args['plan_id'];member=args['member']
    with state.db() as c:
        old=c.execute('SELECT detail FROM archive_reads WHERE plan_id=? AND member=?',(pid,member)).fetchone()
        if old:
            detail=json.loads(old[0]);dest=state.data/'archive'/pid/'assets'/Path(detail['derived_path']).name
            if not dest.exists():
                artifact=state.get(detail['artifact_id'],actor)
                h=artifact['payload']['blob_hash'];body=state.data/'blobs'/h[:2]/h
                raw=body.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=detail['sha256']:raise Fault('HASH','restored artifact body mismatch')
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
            if file_hash(dest)!=detail['sha256']:raise Fault('HASH','derived asset mismatch; preserve evidence before repair')
            detail['derived_path']=str(dest)
            return {'ok':True,'read':detail,'mode':'REUSE','attachment_bytes_read':0,'cache_bytes_verified':detail['bytes']}
        rows=[json.loads(r[0]) for r in c.execute('SELECT resolution FROM archive_refs WHERE plan_id=?',(pid,))]
        if not any(r['status']=='resolved' and r['members']==[member] for r in rows):raise Fault('ATTACHMENT_UNRESOLVED','exact resolved real message reference required')
        if c.execute('SELECT COUNT(*) FROM archive_reads WHERE plan_id=?',(pid,)).fetchone()[0]>=plan['attachment_sample_limit']:raise Fault('SOURCE_LIMIT','frozen attachment body sample cap')
    path=check_source(state,source)
    with zipfile.ZipFile(path) as z:
        info=z.getinfo(member)
        if not safe_member(member) or info.file_size>plan['attachment_max_bytes']:raise Fault('SOURCE_LIMIT','attachment quota')
        body=z.read(member)
    check_source(state,source);h=hashlib.sha256(body).hexdigest();header=body[:16].hex()
    detected='image/png' if body.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if body.startswith(b'\xff\xd8\xff') else 'application/pdf' if body.startswith(b'%PDF') else 'image/webp' if body[:4]==b'RIFF' and body[8:12]==b'WEBP' else 'application/zip' if body[:4]==b'PK\x03\x04' else 'unknown'
    from .batch3 import assert_secret_bytes
    assert_secret_bytes(state,body)
    dest=state.data/'archive'/pid/'assets'/(h+{'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}.get(detected,'.bin'))
    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
    # Canonical Artifact + blob registration makes selected bodies part of normal backup/recovery.
    from .state import object_new,request
    asset_id=stable_id(pid,member,'body',h)
    try:asset=state.get(asset_id,actor)
    except Fault as e:
        if e.code!='NOT_FOUND':raise
        obj=object_new('Artifact',{'name':member,'sha256':h,'media_type':detected,'locator':canonical({'source_id':source['object_id'],'member':member}),'source_locator':{'source_id':source['object_id'],'member':member},'input_vector':[vector(source)],'visual_semantics':'not_verified'})
        obj['object_id']=asset_id
        asset=state.put(request(obj,blob=body),actor)['object']
    detail={'member':member,'sha256':h,'bytes':len(body),'header_hex':header,'detected_media':detected,'derived_path':str(dest),'artifact_id':asset_id,'original_body':'verified_hash','visual_semantics':'not_verified','read_at':now()}
    with state.db() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT COUNT(*) FROM archive_reads WHERE plan_id=?',(pid,)).fetchone()[0]>=plan['attachment_sample_limit']:raise Fault('SOURCE_LIMIT','concurrent attachment sample cap')
        c.execute('INSERT INTO archive_reads VALUES(?,?,?,?)',(pid,member,h,canonical(detail)))
    return {'ok':True,'read':detail,'attachment_bytes_read':len(body),'semantic_calls':0}

def materialize(state,actor,args):
    plan,source=plan_get(state,actor,args['plan_id'])
    with state.db() as c:r=c.execute('SELECT * FROM archive_messages WHERE plan_id=? AND member=? AND ordinal=? AND node=?',(args['plan_id'],args['member'],args['ordinal'],args['node'])).fetchone()
    if not r:raise Fault('SOURCE_MISSING','parsed node required')
    node=json.loads(r['record']);detail=json.loads(r['detail']);m=node.get('message')
    if not m:raise Fault('INPUT','null node is structural evidence, not Message')
    loc={'member':r['member'],'ordinal':r['ordinal'],'node':r['node'],'conversation_id':detail['conversation_id'],'archive_plan':args['plan_id']}
    oid=stable_id(source['object_id'],PARSER,loc,r['raw_hash'])
    try:obj=state.get(oid,actor)
    except Fault as e:
        if e.code!='NOT_FOUND':raise
        locator=save(state,'Locator',{'source_id':source['object_id'],'member':r['member'],'kind':'gpt_archive_node','location':loc,'input_vector':[vector(source)]},oid=stable_id(oid,'locator'))
        obj=save(state,'Message',dict(detail,source_id=source['object_id'],locator_id=locator['object_id'],locator=loc,record=node,text=m.get('content',{}),raw_hash=r['raw_hash'],input_vector=[vector(source)]),oid=oid)
    return {'ok':True,'message':obj,'original_body_included':True,'attachments_body_included':False,'source_bytes_read':0,'parse_reused':True}

def reread(state,actor,message):
    p=message['payload'];loc=p['locator'];plan,source=plan_get(state,actor,loc['archive_plan']);path=check_source(state,source)
    with zipfile.ZipFile(path) as z:
        info=z.getinfo(loc['member'])
        if loc['member'] not in plan['members'] or info.file_size>plan['member_limit']:raise Fault('SOURCE_LIMIT','outside frozen scope')
        with z.open(loc['member']) as f:
            for ordinal,conv,count in conversations(f,plan['conversation_limit']):
                if ordinal!=loc['ordinal']:continue
                record=conv.get('mapping',{}).get(loc['node'])
                if record is None or sha(record)!=p['raw_hash']:raise Fault('SOURCE_CHANGED','exact node/hash mismatch')
                check_source(state,source)
                return {'ok':True,'message_id':message['object_id'],'locator':loc,'raw_hash':p['raw_hash'],'record':record,'source_bytes_read':count,'identity_bytes_read':0,'identity_assurance':'registered full hash and unchanged stat; exact node content hash verified','scope':'bounded original node; no attachment or semantic validation'}
    raise Fault('SOURCE_MISSING','exact ordinal absent')

def directory(state,actor,args):
    from .human_directory import render_directory
    plan,source=plan_get(state,actor,args['plan_id'])
    return render_directory(state,actor,plan,coverage(state,actor,args))

def legacy_directory(state,actor,args):
    plan,source=plan_get(state,actor,args['plan_id']);pid=args['plan_id'];cov=coverage(state,actor,args)
    dest=state.data/'archive'/pid/'directory';dest.mkdir(parents=True,exist_ok=True)
    with state.db() as c:
        rows=[dict(r) for r in c.execute('SELECT member,ordinal,native_id,title,stats FROM archive_conversations WHERE plan_id=? ORDER BY member,ordinal',(pid,))]
    def page(title,body):return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+html.escape(title)+'</title><style>body{max-width:1150px;margin:30px auto;font:16px/1.8 system-ui}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd;padding:8px}pre{white-space:pre-wrap}</style><h1>'+html.escape(title)+'</h1>'+body+'</html>'
    links=[]
    for member in plan['members']:
        name=member+'.html';selected=[r for r in rows if r['member']==member];links.append(f'<li><a href="{name}">{member}</a>：{len(selected)} 对话</li>')
        body='<p>目录标题来自原文；没有自动确认项目归属或语义。原始 ZIP 原位只读。null／主分支／其他分支分别统计。</p><table><tr><th>序号／来源</th><th>原始标题</th><th>覆盖</th></tr>'
        for r in selected:body+='<tr><td>'+html.escape(str(r['ordinal'])+' / '+str(r['native_id']))+'</td><td>'+html.escape(str(r['title']))+'</td><td>'+html.escape(r['stats'])+'</td></tr>'
        atomic(dest/name,page(member,body+'</table>'))
    atomic(dest/'index.html',page('UACF E7 旧库人可读目录','<p>单一 authority '+state.authority+'；正文、附件与语义状态分别报告。未参考的附件只表示本范围没有引用。</p><ul>'+''.join(links)+'</ul><pre>'+html.escape(json.dumps(cov,ensure_ascii=False,indent=2))+'</pre>'))
    atomic(state.root/'logs/batch4-coverage.json',canonical(cov))
    return {'ok':True,'path':str(dest/'index.html'),'conversations':len(rows),'mode':'REINDEX','source_bytes_read':0,'semantic_calls':0,'coverage':cov}

def dispatch_archive(state,actor,action,args,oid):
    owner(actor)
    from jsonschema import Draft202012Validator
    schema=json.loads((Path(__file__).resolve().parents[1]/'contracts/actions-batch4.schema.json').read_text())['actions'][action]
    errors=list(Draft202012Validator(schema).iter_errors(args))
    if errors:raise Fault('INPUT','archive typed contract: '+errors[0].message)
    if action=='reading_plan':
        from .reading import reading_plan
        return reading_plan(state,actor,args)
    if action=='archive_inventory':return inventory(state,actor,args)
    if action=='archive_plan':return make_plan(state,actor,args)
    if action=='archive_run':return run(state,actor,args)
    if action=='archive_coverage':return coverage(state,actor,args)
    if action=='archive_read':return read_asset(state,actor,args)
    if action=='archive_materialize':return materialize(state,actor,args)
    if action=='archive_reindex':return directory(state,actor,args)
    raise Fault('UNSUPPORTED','unknown archive action')
