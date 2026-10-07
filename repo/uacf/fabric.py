"""E3/E4 contracts and projections over the same canonical authority."""
import json, uuid, zipfile, time
from pathlib import Path, PurePosixPath
from .util import Fault, canonical, sha, uid, now, atomic, file_hash
from .state import object_new, request, stale, verify_backup

POLICY='discourse-1'; PARSER='sources-1.2'
KINDS={'SourceSet':['roots','authorization','limits'],'Locator':['source_id','member','kind'],
 'Asset':['locator_id','identity'],'Affiliation':['asset_id','target_id','basis','lifecycle'],
 'Relation':['source_id','target_id','kind','basis'],'Dossier':['subject_id','cards','facets'],
 'Obligation':['failure_id','task_id','conditions','assessment'],'ProviderProfile':['host','provider','model','capabilities','pricing'],
 'RoleAssignment':['mode','roles','fallback'],'DiscourseState':['message_refs','branch','claims','relations','coverage','policy_version'],
 'Claim':['literal_content','speech_act','source_kind','branch','interpretation_basis','lifecycle'],
 'AdoptionDecision':['claim_id','claim_revision','basis','scope','lifecycle'],
 'ResponseContract':['task_id','request_ref','questions','evidence_refs','format','uncertainty'],
 'View':['name','layout','input_vector'],'Run':['task_id','route','state'],'Budget':['currency','limit_micro']}
KINDS.update(WorkUnit=['purpose','message_refs','branch','basis'],SemanticCard=['summary','evidence_map','facets','input_vector'],
 Contribution=['target_id','base_revision','write_set'],IntegrationDecision=['target_id','contribution_ids','conflicts','outcome'],
 LearningAttempt=['learner_actor','prompt_ref','answer','assessment','error_owner'])

def owner(actor):
 if actor!='owner':raise Fault('PERMISSION','owner required')
def vector(obj):return {'object_id':obj['object_id'],'revision':obj['revision']}
def save(state,kind,payload,visibility='private',oid=None,expected=0):
 obj=object_new(kind,payload,visibility=visibility)
 if oid:obj['object_id']=oid
 return state.put(request(obj,expected),'owner')['object']
def stable_id(*parts):return str(uuid.uuid5(uuid.NAMESPACE_URL,canonical(parts)))

def migrate(state,backup):
 verify_backup(backup)
 m=json.loads((Path(backup)/'manifest.json').read_text())
 if m['authority_id']!=state.authority:raise Fault('BACKUP_AUTHORITY','backup belongs to another authority')
 cfg=state.config; cfg.setdefault('revision',1)
 with state.db() as c:
  c.executescript((Path(__file__).resolve().parents[1]/'contracts/migrations/002.sql').read_text())
  c.execute("INSERT OR IGNORE INTO metadata VALUES('canonical_config',?)",(canonical(cfg),))
 # Legacy payload pin migration creates new revisions, retaining original evidence and receipts.
 fixed=[]
 for obj in state.list('owner'):
  p=obj['payload']
  if p.get('project_id') and not p.get('project_revision'):
   with state.db() as c:r=c.execute("SELECT target_revision FROM object_links WHERE object_id=? AND revision=? AND field='project_id'",(obj['object_id'],obj['revision'])).fetchone()
   if not r:raise Fault('MIGRATION_MISSING','legacy project pin has no durable relation')
   p['project_revision']=r[0];fixed.append(state.put(request(obj,obj['revision']),'owner',internal=True)['object']['object_id'])
 return {'ok':True,'database_version':2,'legacy_pins_revised':fixed,'authority_id':state.authority}

def config_set(state,actor,args,operation_id):
 owner(actor)
 with state.db() as c:
  c.execute('BEGIN IMMEDIATE')
  old=c.execute('SELECT response FROM operations WHERE operation_id=?',(operation_id,)).fetchone()
  if old:return json.loads(old[0])
  cfg=state.config; revision=cfg.get('revision',1)
  if args.get('expected_revision')!=revision:raise Fault('REVISION_CONFLICT','configuration revision changed')
  host=args['host'];tokens=args['requested_tokens'];budget=args.get('capsule_max_bytes')
  if host not in ['dsh','codex'] or not(tokens=='auto' or type(tokens)==int and tokens>0):raise Fault('INPUT','host/tokens invalid')
  if budget is not None and (type(budget)!=int or budget<1):raise Fault('INPUT','positive capsule budget required')
  # Config preimage is hashed and verified before commit; canonical config and receipt are one transaction.
  backup=state.root/'backups'/('config-'+operation_id+'.json');atomic(backup,canonical(cfg))
  if file_hash(backup)!=sha(cfg):raise Fault('BACKUP_INCOMPLETE','config backup verification failed')
  cfg['context_profiles'][host]={'requested_tokens':tokens,'effective_tokens':'unknown','recorded_at':now()}
  if budget is not None:cfg['capsule_max_bytes']=budget
  cfg['revision']=revision+1
  response={'ok':True,'profiles':cfg['context_profiles'],'revision':cfg['revision'],'effective':'unknown','backup':str(backup)}
  c.execute("INSERT OR REPLACE INTO metadata VALUES('canonical_config',?)",(canonical(cfg),))
  c.execute('INSERT INTO operations VALUES(?,?,?,?)',(operation_id,sha(args),actor,canonical(response)))
 atomic(state.data/'config.json',canonical(cfg)) # Rebuildable file projection, never canonical authority.
 return response

def failure_obligations(state,actor,task):
 required=set(task['payload'].get('required_properties',[])); candidates=[]; effective=[]; excluded=[]
 environment=task['payload'].get('environment',{}); host=task['payload'].get('host','dsh')
 for f in state.list(actor,'FailureCase')+state.list(actor,'FailurePattern'):
  if not(required & set(f['payload'].get('properties',[]))):continue
  candidates.append(f); reasons=[]; cond=f['payload'].get('applicability',{})
  if f['status'] in ['retracted','superseded','rejected']:reasons.append('inactive lifecycle')
  for k,v in cond.items():
   actual=host if k=='host' else task['payload'].get(k,environment.get(k,'unknown'))
   if actual!=v:reasons.append(k+': mismatch or unknown')
  if stale(state,f):reasons.append('stale input dependency')
  if 'provisional' in f['payload'].get('source',{}).get('grading',''):reasons.append('provisional assessment is not a confirmed failure lesson')
  if reasons:excluded.append({'failure_id':f['object_id'],'reasons':reasons})
  else:effective.append({'failure_id':f['object_id'],'revision':f['revision'],'lesson':f['payload']['lesson'],'conditions':cond,'assessment':'applicable','mandatory':True})
 return {'candidates':candidates,'effective_obligations':effective,'excluded':excluded,'selection':'deterministic full applicable set, no top-k'}

def check_relation(state,c,obj,actor):
 p=obj['payload'];state._get(c,p['source_id'],actor);state._get(c,p['target_id'],actor)
 if p['kind'] not in ['supports','qualifies','contradicts','supersedes','hypothetical','quoted','depends_on','affiliated','contains']:raise Fault('SCHEMA','unknown relation semantics')
 if p['kind']=='depends_on':
  edges={}
  for r in c.execute("SELECT r.envelope FROM object_revisions r JOIN objects o ON r.object_id=o.id AND r.revision=o.head WHERE o.type='Relation'"):
   o=json.loads(r[0]);q=o['payload']
   if o['object_id']!=obj['object_id'] and q['kind']=='depends_on' and o['status'] not in ['retracted','superseded']:edges.setdefault(q['source_id'],[]).append(q['target_id'])
  todo=[p['target_id']];seen=set()
  while todo:
   x=todo.pop()
   if x==p['source_id']:raise Fault('DEPENDENCY_CYCLE','blocking dependency cycle')
   if x not in seen:seen.add(x);todo+=edges.get(x,[])

def check_adoption(state,c,obj,actor):
 p=obj['payload'];claim=state._get(c,p['claim_id'],actor,p['claim_revision'])
 if state._get(c,p['claim_id'],actor)['revision']!=p['claim_revision']:raise Fault('DEPENDENCY_STALE','claim changed')
 if p['lifecycle']=='adopted':
  owner(actor);basis=p['basis']
  if basis.get('kind') not in ['current_direct_instruction','human_correction']:raise Fault('ADOPTION_BASIS','inferred claims remain candidates')
  source=state._get(c,basis['message_id'],actor,basis['message_revision'])
  sp=source['payload']
  if sp.get('source_kind')!='direct_user' or sp.get('role')!='user' or not sp.get('current',False):raise Fault('ADOPTION_SOURCE','historical/tool/quoted source cannot authorize current action')
  if claim['payload'].get('branch')!=sp.get('branch'):raise Fault('ADOPTION_BRANCH','different branch')
  if claim['payload'].get('speech_act') in ['quoted','hypothetical','discussion']:raise Fault('ADOPTION_BASIS','non-executable speech act remains candidate')
  # This attestation is a user correction/input; semantic truth is never claimed by schema.
  if not basis.get('explicit_attestation'):raise Fault('ADOPTION_BASIS','clear instruction attestation required')

def effective_intent(state,actor,task_id):
 result=[]
 for d in state.list(actor,'AdoptionDecision'):
  p=d['payload']
  if p['scope'].get('task_id')!=task_id or p['lifecycle']!='adopted' or stale(state,d):continue
  claim=state.get(p['claim_id'],actor)
  if claim['revision']==p['claim_revision']:result.append({'decision':d,'claim':claim})
 return result

def projection(state,actor,mode='table',focus=None):
 if mode not in ['table','graph','tree','nexus']:raise Fault('INPUT','unknown view')
 # One read transaction binds ACL, canonical heads and water level to the same snapshot.
 objects=[]
 with state.db() as c:
  c.execute('BEGIN')
  seq=c.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0]
  for row in c.execute('SELECT id FROM objects ORDER BY rowid').fetchall():
   try:objects.append(state._get(c,row[0],actor))
   except Fault as e:
    if e.code!='NOT_FOUND':raise
 byid={o['object_id']:o for o in objects};edges=[];invalid={}
 def is_stale(oid,seen=frozenset()):
  if oid in seen:return True
  if oid in invalid:return invalid[oid]
  obj=byid[oid];result=False
  for dep in obj['payload'].get('input_vector',[]):
   source=byid.get(dep['object_id'])
   if not source or source['revision']!=dep['revision'] or is_stale(dep['object_id'],seen|{oid}):result=True;break
  invalid[oid]=result;return result
 for o in objects:
  p=o['payload']
  for i,dep in enumerate(p.get('input_vector',[])):
   if dep['object_id'] in byid:edges.append({'id':o['object_id']+':input:'+str(i),'source':o['object_id'],'target':dep['object_id'],'kind':'input_revision','basis':dep,'stale':is_stale(o['object_id'])})
  if p.get('project_id') in byid:edges.append({'id':o['object_id']+':project','source':o['object_id'],'target':p['project_id'],'kind':'uses_project_contract','basis':p.get('project_revision'),'stale':is_stale(o['object_id'])})
  if o['object_type'] in ['Relation','Affiliation']:
   a=p.get('source_id',p.get('asset_id'));b=p.get('target_id')
   if a in byid and b in byid:edges.append({'id':o['object_id'],'source':a,'target':b,'kind':p.get('kind','affiliated'),'basis':p.get('basis'),'stale':is_stale(o['object_id'])})
 if mode=='nexus' and focus:
  if focus not in byid:raise Fault('NOT_FOUND','object not visible')
  selected={focus}
  for e in edges:
   if focus in [e['source'],e['target']]:selected.update([e['source'],e['target']])
  objects=[o for o in objects if o['object_id'] in selected];edges=[e for e in edges if e['source'] in selected and e['target'] in selected]
 return {'ok':True,'mode':mode,'authority_id':state.authority,'commit_seq':seq,'nodes':[dict(o,projection_stale=is_stale(o['object_id'])) for o in objects],
  'edges':edges,'unique_count':len(objects),'unique_assets':sum(o['object_type'] in ['Asset','Artifact','WorkUnit'] for o in objects),'memberships':sum(o['object_type']=='Affiliation' for o in objects),'source_files_moved':False}

def ingest(state,actor,args):
 owner(actor);source=state.get(args['source_id'],actor);p=source['payload']; member=args['member'];fmt=args['format']; mode=args.get('mode','FULL')
 if source['object_type']!='SourceSet' or p['authorization'].get('kind')!='user_scope':raise Fault('PERMISSION','registered user-authorized SourceSet required')
 if mode not in ['REUSE','REINDEX','FULL']:raise Fault('INPUT','unknown processing mode')
 path=Path(p['roots'][0]); declared=p['authorization'].get('sha256')
 if not path.is_file():raise Fault('SOURCE_MISSING','original source offline; cached objects remain queryable')
 identity_bytes=path.stat().st_size
 if file_hash(path)!=declared:raise Fault('SOURCE_CHANGED','source identity changed; register new source revision')
 pp=PurePosixPath(member)
 if pp.is_absolute() or '..' in pp.parts or '\\' in member:raise Fault('LOCATOR','unsafe archive member')
 limits=p['limits'];maxbytes=min(int(limits['max_bytes']),2097152);nrecords=min(int(limits['max_records']),64)
 key=sha([source['object_id'],source['revision'],declared,member,PARSER]);started=time.monotonic()
 with state.db() as c:old=c.execute('SELECT * FROM ingest_runs WHERE key=?',(key,)).fetchone()
 if old and old['status']=='done' and mode in ['REUSE','REINDEX']:
  result=json.loads(old['receipt']);result.update(mode=mode,source_bytes_read=0,identity_bytes_read=identity_bytes,semantic_cost='not_run',elapsed_s=time.monotonic()-started);return result
 if mode=='REINDEX':raise Fault('MISSING_PARSE','REINDEX requires existing parsed structure; reinterpretation is FULL')
 requested_mode=mode
 if mode=='REUSE':mode='FULL' # Cache miss is actual parse work, never reported as a reuse hit.
 cursor=old['cursor'] if old else 0; records=[];missing=[];coverage={};readbytes=0
 with zipfile.ZipFile(path) as z:
  if member not in z.namelist():raise Fault('SOURCE_MISSING','member missing')
  with z.open(member) as f:
   if fmt=='dsh':
    for i in range(nrecords):
     raw=f.readline(maxbytes-readbytes+1)
     if not raw:break
     readbytes+=len(raw)
     if readbytes>maxbytes:missing.append('byte quota; next record not parsed');break
     r=json.loads(raw);d=r.get('data',{});m=d.get('message',d) if isinstance(d,dict) else {};typ=r.get('type','unknown')
     origin=m.get('source',{});origin_kind=origin.get('kind',origin.get('type','unknown')) if isinstance(origin,dict) else 'unknown'
     role=m.get('role','unknown');kind='tool' if typ=='tool/result' else 'subagent' if typ.startswith('agent/') else 'direct_user' if typ=='user/message' and origin_kind in ['user','human'] else 'assistant' if role=='assistant' else 'unknown'
     blocks=m.get('content',[]);refs=[{'kind':b['type'],'locator':b.get('attachment'),'availability':'unknown'} for b in blocks if isinstance(b,dict) and b.get('type') in ['file','image']] if isinstance(blocks,list) else []
     records.append({'record':r,'text':blocks,'role':role,'source_kind':kind,'branch':'main' if not member.startswith('subagents/') else 'subagent:'+member.split('/')[1],'parent':None,'seq':r.get('seq',i),'attachments':refs,'origin':origin,'locator':{'line':i+1,'member':member}})
    coverage={'records':len(records),'branch':'main sample only','all_subagents':'not_read','attachments':'directory registered, bodies not read','full_session':'partial'}
   elif fmt=='gpt':
    raw=f.read(maxbytes);readbytes=len(raw);text=raw.decode('utf-8');text=text.lstrip()
    if not text.startswith('['):raise Fault('SOURCE_FORMAT','GPT shard must be JSON array')
    try:conv,end=json.JSONDecoder().raw_decode(text[1:].lstrip())
    except json.JSONDecodeError:raise Fault('SOURCE_LIMIT','first conversation exceeds prefix quota or malformed; no guessed continuation')
    mapping=conv.get('mapping',{});main=set();current=conv.get('current_node');seen=set()
    while current in mapping and current not in seen:
     seen.add(current);main.add(current);current=mapping[current].get('parent')
    for nodeid,node in list(mapping.items())[:nrecords]:
     m=node.get('message');
     if not m:continue
     role=m.get('author',{}).get('role','unknown');content=m.get('content',{});meta=m.get('metadata',{})
     refs=[]
     for part in content.get('parts',[]):
      if isinstance(part,dict):refs.append({'kind':part.get('content_type','unknown'),'locator':part.get('asset_pointer'),'availability':'unknown'})
     refs+= [{'kind':'attachment','locator':a.get('id',a.get('file_id')),'availability':'unknown'} for a in meta.get('attachments',[]) if isinstance(a,dict)]
     records.append({'record':node,'text':content,'role':role,'source_kind':'direct_user' if role=='user' else 'tool' if role=='tool' else 'assistant' if role=='assistant' else 'unknown',
       'branch':'main' if nodeid in main else 'alternate:'+nodeid,'parent':node.get('parent'),'seq':nodeid,'attachments':refs,'origin':m.get('author'),
       'locator':{'conversation_id':conv.get('id',conv.get('conversation_id')),'node':nodeid,'member':member}})
    coverage={'conversation_nodes':len(mapping),'messages':len(records),'main_messages':sum(r['branch']=='main' for r in records),'alternate_messages':sum(r['branch']!='main' for r in records),'all_shards':'not_read','full_export':'unknown','orphan_attachments':'not_enumerated','missing_nodes':len(mapping)>nrecords}
   else:raise Fault('SOURCE_FORMAT','supported formats gpt/dsh only')
 locid=stable_id(key,'locator');sessionid=stable_id(key,'session')
 def once(kind,payload,oid):
  try:return state.get(oid,actor)
  except Fault as e:
   if e.code!='NOT_FOUND':raise
  return save(state,kind,payload,source['visibility'],oid)
 loc=once('Locator',{'source_id':source['object_id'],'member':member,'kind':'zip_member','input_vector':[vector(source)],'content_identity':declared},locid)
 session=once('Session',{'source_id':source['object_id'],'format':fmt,'coverage':coverage,'current':False,'input_vector':[vector(source)]},sessionid)
 ids=[]
 for i,r in enumerate(records):
  oid=stable_id(key,r['locator'],r['seq']);ids.append(oid)
  if i>=cursor:
   once('Message',dict(r,source_id=source['object_id'],session_id=sessionid,locator_id=locid,current=False,raw_hash=sha(r['record']),input_vector=[vector(source)]),oid)
   with state.db() as c:c.execute('INSERT INTO ingest_runs VALUES(?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET cursor=excluded.cursor,status=excluded.status,receipt=excluded.receipt',(key,source['object_id'],PARSER,i+1,'running',canonical({'processed':i+1})))
   if args.get('interrupt_after')==i+1:raise Fault('INTERRUPTED','explicit drill after committed record; resume retains stable identity')
 result={'ok':True,'key':key,'source_id':source['object_id'],'session_id':sessionid,'locator_id':locid,'message_ids':ids,'mode':mode,'requested_mode':requested_mode,'parser':PARSER,'source_bytes_read':readbytes,'identity_bytes_read':identity_bytes,'coverage':coverage,'missing':missing,'semantic_cost':'not_run','elapsed_s':time.monotonic()-started,'resumed_from':cursor}
 with state.db() as c:c.execute('INSERT INTO ingest_runs VALUES(?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET cursor=excluded.cursor,status=excluded.status,receipt=excluded.receipt',(key,source['object_id'],PARSER,len(records),'done',canonical(result)))
 return result

def build_workunit(state,actor,args):
 owner(actor);messages=[state.get(i,actor) for i in args['message_ids']]
 if not messages:raise Fault('INPUT','nonempty source span required')
 if len({m['payload']['branch'] for m in messages})!=1:raise Fault('BRANCH','WorkUnit must not merge alternate branches into one decision')
 inputs=[vector(m) for m in messages];visibility='shared' if all(m['visibility']=='shared' for m in messages) else 'private'
 unit=save(state,'WorkUnit',{'purpose':args['purpose'],'message_refs':inputs,'input_vector':inputs,'branch':messages[0]['payload']['branch'],'basis':args.get('basis','explicit bounded selection'),'classification':'human_defined'},visibility)
 card=save(state,'SemanticCard',{'work_unit_id':unit['object_id'],'summary':args.get('summary','uninterpreted bounded source span'),'evidence_map':inputs,'facets':{'source':'covered','premises':'uninterpreted','failure':'unknown','decisions':'not_adopted','artifacts':'unknown'},'input_vector':[vector(unit),*inputs],'inference':True,'current_decision':False},visibility)
 dossier=save(state,'Dossier',{'subject_id':unit['object_id'],'cards':[vector(card)],'facets':card['payload']['facets'],'input_vector':[vector(card)]},visibility)
 affiliations=[]
 for project_id in args.get('project_ids',[]):
  project=state.get(project_id,actor)
  affiliations.append(save(state,'Affiliation',{'asset_id':unit['object_id'],'target_id':project_id,'basis':args.get('basis','human selection'),'lifecycle':'confirmed','input_vector':[vector(unit),vector(project)]},visibility))
 return {'ok':True,'work_unit':unit,'card':card,'dossier':dossier,'affiliations':affiliations}

def correct(state,actor,args):
 owner(actor);obj=state.get(args['object_id'],actor)
 if args['expected_revision']!=obj['revision']:raise Fault('REVISION_CONFLICT','correction based on stale interpretation')
 if obj['object_type'] not in ['Claim','DiscourseState','Affiliation','SemanticCard','AdoptionDecision']:raise Fault('INPUT','correction supports semantic objects only')
 obj['payload'].update(args['changes']);obj['payload']['correction_basis']=args['basis'];obj['payload']['policy_version']=POLICY
 if obj['object_type']=='Affiliation':
  asset=state.get(obj['payload']['asset_id'],actor);target=state.get(obj['payload']['target_id'],actor)
  if target['object_type'] not in ['Project','Subgoal']:raise Fault('INPUT','affiliation target must be Project or Subgoal')
  obj['payload']['input_vector']=[vector(asset),vector(target)]
 updated=state.put(request(obj,obj['revision']),'owner')['object']
 affected=[o['object_id'] for o in state.list(actor) if stale(state,o)]
 return {'ok':True,'object':updated,'invalidated_projection_ids':affected,'raw_evidence_preserved':True,'rebuild_mode':'local FULL when reinterpretation is required'}

def integrate(state,actor,args):
 owner(actor);target=state.get(args['target_id'],actor); contributions=[state.get(i,actor) for i in args['contribution_ids']]
 if args['expected_revision']!=target['revision']:raise Fault('REVISION_CONFLICT','target changed')
 writes={};conflicts=[]
 for contribution in contributions:
  p=contribution['payload']
  if p['base_revision']!=target['revision'] or p['target_id']!=target['object_id']:conflicts.append({'id':contribution['object_id'],'reason':'stale base'})
  for key,value in p['write_set'].items():
   if key in writes and writes[key]!=value:conflicts.append({'field':key,'reason':'incompatible write sets'})
   writes[key]=value
 decision=save(state,'IntegrationDecision',{'target_id':target['object_id'],'target_revision':target['revision'],'contribution_ids':args['contribution_ids'],'conflicts':conflicts,'outcome':'conflict' if conflicts else 'integrated','input_vector':[vector(c) for c in contributions]})
 if conflicts:return {'ok':True,'status':'conflict','decision':decision,'target_unchanged':True}
 target['payload'].update(writes);updated=state.put(request(target,target['revision']),actor)['object']
 return {'ok':True,'status':'integrated','decision':decision,'object':updated}

def rebuild(state,actor,args):
 owner(actor);root=state.get(args['object_id'],actor);mode=args.get('mode','FULL')
 if mode not in ['FULL','REINDEX']:raise Fault('INPUT','semantic rebuild mode FULL or REINDEX')
 eligible={'SemanticCard','Dossier','DiscourseState','TaskContract','ResponseContract'};changed=[]
 pending=[o for o in state.list(actor) if o['object_type'] in eligible and stale(state,o)]
 # Scope transitive dependencies of the selected interpretation, never historical Actions/Evidence.
 affected={root['object_id']};scope=[]
 while pending:
  found=[o for o in pending if any(d['object_id'] in affected for d in o['payload'].get('input_vector',[]))]
  if not found:break
  for o in found:pending.remove(o);affected.add(o['object_id']);scope.append(o)
 if scope and mode=='REINDEX':raise Fault('LOCAL_FULL_REQUIRED','changed semantic dependency is not a layout-only REINDEX')
 while scope:
  ready=[o for o in scope if all(d['object_id'] not in {s['object_id'] for s in scope} for d in o['payload'].get('input_vector',[]))]
  if not ready:raise Fault('DEPENDENCY_CYCLE','cannot topologically rebuild projections')
  for obj in ready:
   scope.remove(obj);p=obj['payload']
   for dep in p.get('input_vector',[]):dep['revision']=state.get(dep['object_id'],actor)['revision']
   for field in ['cards','claims','interpretation_refs','message_refs','evidence_refs']:
    for dep in p.get(field,[]):
     if isinstance(dep,dict) and 'object_id' in dep:dep['revision']=state.get(dep['object_id'],actor)['revision']
   if p.get('request_ref'):p['request_ref']['revision']=state.get(p['request_ref']['object_id'],actor)['revision']
   if p.get('task_id'):p['task_revision']=state.get(p['task_id'],actor)['revision']
   if obj['object_type']=='SemanticCard' and p.get('interpretation_refs'):
    p['summary']='\n'.join(state.get(dep['object_id'],actor)['payload']['literal_content'] for dep in p['interpretation_refs'])
   p['reprocessing']={'mode':mode,'basis':args['basis'],'policy_version':POLICY,'semantic_cost':'human correction already recorded; deterministic composition; model_calls=0','source_bytes_read':0}
   changed.append(state.put(request(obj,obj['revision']),actor)['object'])
 return {'ok':True,'mode':mode,'objects':[vector(o) for o in changed],'source_bytes_read':0,'historical_observations_rewritten':False,'semantic_cost':'recorded human/engineering correction; no new model call'}

def source_read(state,actor,args):
 """Re-resolve one registered span against unchanged original, with fixed quotas."""
 message=state.get(args['message_id'],actor)
 if message['object_type']!='Message':raise Fault('INPUT','Message locator required')
 p=message['payload'];source=state.get(p['source_id'],actor);path=Path(source['payload']['roots'][0])
 if p.get('locator',{}).get('archive_plan'):
  from .archive import reread
  return reread(state,actor,message)
 if not path.is_file():raise Fault('SOURCE_MISSING','original unavailable; canonical historical representation retained')
 if file_hash(path)!=source['payload']['authorization']['sha256']:raise Fault('SOURCE_CHANGED','original identity changed; no guessed relocation')
 loc=p['locator'];maxbytes=source['payload']['limits']['max_bytes'];count=0
 with zipfile.ZipFile(path) as archive:
  member=loc['member'];safe=PurePosixPath(member)
  if safe.is_absolute() or '..' in safe.parts or member not in archive.namelist():raise Fault('SOURCE_MISSING','unsafe or absent member')
  with archive.open(member) as stream:
   if 'line' in loc:
    if not 1<=loc['line']<=source['payload']['limits']['max_records']:raise Fault('SOURCE_LIMIT','line outside registered sample')
    for _ in range(loc['line']):
     raw=stream.readline(maxbytes-count+1);count+=len(raw)
     if not raw or count>maxbytes:raise Fault('SOURCE_LIMIT','line exceeds byte quota')
    record=json.loads(raw)
   else:
    raw=stream.read(maxbytes);count=len(raw)
    try:conversation,_=json.JSONDecoder().raw_decode(raw.decode('utf-8').lstrip()[1:].lstrip())
    except (ValueError,UnicodeError):raise Fault('SOURCE_LIMIT','conversation not resolvable within registered prefix')
    record=conversation.get('mapping',{}).get(loc['node'])
    if record is None:raise Fault('SOURCE_MISSING','node absent; no guessed branch merge')
 if sha(record)!=p['raw_hash']:raise Fault('SOURCE_CHANGED','exact source record differs')
 return {'ok':True,'message_id':message['object_id'],'locator':loc,'raw_hash':p['raw_hash'],'original_identity_verified':True,'record':record,'source_bytes_read':count,'identity_bytes_read':path.stat().st_size,'scope':'one original record; no image or semantic validation'}
