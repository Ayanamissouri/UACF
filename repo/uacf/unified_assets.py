"""Rebuildable, source-labelled search across the existing canonical authority.

No provider calls, native session synthesis, source ACL changes or semantic adoption.
Owner may search all local sources; hosts get only an explicitly authorized,
mapped Task projection. Private reasoning and credential-like fields are excluded.
"""
import json,re,sqlite3,threading
from contextlib import contextmanager
from pathlib import Path
from .util import Fault,canonical,sha,now,atomic
LOCK=threading.RLock()
SCHEMA='unified-public-assets-1'

def public_text(value):
 if isinstance(value,str):return value
 if isinstance(value,list):return '\n'.join(filter(None,(public_text(v) for v in value)))
 if not isinstance(value,dict):return ''
 if value.get('channel') in ['analysis','reasoning'] or value.get('type') in ['reasoning','thinking','analysis'] or value.get('content_type') in ['thoughts','reasoning','reasoning_recap']:return ''
 # Read semantic text/content fields, never arbitrary opaque tool internals.
 if 'message' in value:return public_text(value['message'])
 if 'content' in value:return public_text(value['content'])
 if 'parts' in value:return public_text(value['parts'])
 return value.get('text','') if isinstance(value.get('text'),str) else ''

def clean(text):
 return re.sub(r'(?i)(?:sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,})','[REDACTED]',text)

@contextmanager
def db(state):
 path=state.data/'unified-assets.sqlite';c=sqlite3.connect(path,timeout=30);c.row_factory=sqlite3.Row
 c.execute('pragma journal_mode=WAL')
 c.execute('create table if not exists docs(id text primary key,host text,session text,project text,title text,body text,locator text,scope text)')
 c.execute('create table if not exists marks(id text primary key,value text)')
 try:
  yield c
  c.commit()
 finally:c.close()

def refresh(state):
 with LOCK,state.db() as src,db(state) as out:
  def mark(k):
   r=out.execute('select value from marks where id=?',(k,)).fetchone();return r[0] if r else None
  def setmark(k,v):out.execute('insert or replace into marks values(?,?)',(k,str(v)))
  def put(ident,host,sid,project,title,body,loc,scope):
   if not body:return
   out.execute('insert or replace into docs values(?,?,?,?,?,?,?,?)',(ident,host,sid,project or '',title,clean(body),canonical(loc),scope))
  tables={r[0] for r in src.execute("select name from sqlite_master where type='table'")}
  signature=sha([src.execute('select coalesce(max(seq),0) from events').fetchone()[0],src.execute('select coalesce(max(rowid),0) from host_events').fetchone()[0],src.execute('select coalesce(max(rowid),0) from archive_messages').fetchone()[0] if 'archive_messages' in tables else 0])
  if mark('source_signature')==signature:return inventory(state)
  if 'archive_messages' in tables:
   for r in src.execute('select a.*,c.native_id,c.title from archive_messages a join archive_conversations c on a.plan_id=c.plan_id and a.member=c.member and a.ordinal=c.ordinal where a.rowid>?',(int(mark('gpt_row') or 0),)):
    # Per-plan/node identity survives pagination and index rebuilds.
    loc=dict(plan_id=r['plan_id'],member=r['member'],ordinal=r['ordinal'],node=r['node'])
    put('gpt:'+sha(loc),'gpt_export',r['native_id'],None,r['title'] or '旧GPT导出',public_text(json.loads(r['record'])),loc,'archived public text; semantic acceptance separate')
   setmark('gpt_row',src.execute('select coalesce(max(rowid),0) from archive_messages').fetchone()[0])
  if 'host_events' in tables:
   for r in src.execute('select rowid,payload from host_events where rowid>?',(int(mark('event_row') or 0),)):
    ev=json.loads(r['payload']);p=ev['payload'];message=p.get('message',{});body=public_text(message)
    if p.get('kind')=='native_hook':body='\n'.join(str(p[k]) for k in ['prompt','last_assistant_message'] if isinstance(p.get(k),str))
    sid=p.get('native_session_id') or 'unknown';loc=dict(event_id=ev['event_id'],native_session_id=sid,native_turn_id=p.get('native_turn_id'),native_locator=p.get('native_locator'))
    put('event:'+ev['event_id'],ev['source_host'],sid,None,sid,body,loc,'observed public item; not entire account or session coverage')
   setmark('event_row',src.execute('select coalesce(max(rowid),0) from host_events').fetchone()[0])
  for row in src.execute("select v.envelope from objects o join object_revisions v on o.id=v.object_id and o.head=v.revision where o.type in ('Artifact','SemanticCard','TaskContract','FailureCase','Project')"):
   obj=json.loads(row[0]);p=obj['payload'];key='object:'+obj['object_id'];rev=str(obj['revision'])
   if mark(key)==rev:continue
   # Indexed prefix range: LIKE otherwise scans the entire archive per object.
   out.execute('delete from docs where id=? or (id>=? and id<?)',(key,key+':',key+';'));setmark(key,rev)
   title=p.get('catalog_title') or p.get('name') or p.get('goal') or p.get('summary') or p.get('lesson') or obj['object_type']
   meta='\n'.join(str(p[k]) for k in ['summary','goal','lesson'] if isinstance(p.get(k),str))
   loc=dict(object_id=obj['object_id'],revision=obj['revision'])
   put(key,'canonical',obj['object_id'],p.get('project_id'),title,meta,loc,'canonical object metadata; candidate is not authority')
   if obj['object_type']=='SemanticCard':
    put(key+':knowledge','current_work' if p.get('semantic_contract')=='work-semantic-1' else 'gpt_candidate',p.get('native_session_id') or obj['object_id'],p.get('project_id'),title,'\n'.join(k.get('text','') for k in p.get('knowledge',[]) if isinstance(k,dict)),loc,'source-bound candidate knowledge; not automatically adopted')
   if obj['object_type']!='Artifact' or p.get('source_kind')!='native_history_snapshot' or not p.get('blob_hash'):continue
   path=state.data/'blobs'/p['blob_hash'][:2]/p['blob_hash']
   if not path.is_file():continue
   body=json.loads(path.read_text(encoding='utf8'))
   for i,record in enumerate(body.get('records',[])):
    rl=dict(loc,node=record.get('id',record.get('node',str(i))),native_locator=record.get('native_locator'))
    put(key+':'+str(i),p['native_host'],p['native_session_id'],p.get('native_project') or p.get('native_cwd'),title,public_text(record),rl,body.get('coverage','native persisted public snapshot'))
  setmark('refreshed',now())
  setmark('source_signature',signature)
 return inventory(state)

def inventory(state):
 with LOCK,db(state) as c:
  rows=[dict(r) for r in c.execute('select host,count(*) text_records,count(distinct session) conversations,count(distinct nullif(project,\'\')) project_locators from docs group by host')]
  at=c.execute("select value from marks where id='refreshed'").fetchone()
 meta=state.data/'native-history-inventory.json'
 with state.db() as src:
  observed=[dict(r) for r in src.execute('select source_host,count(*) events,count(distinct json_extract(payload,\'$.payload.native_session_id\')) sessions from host_events group by source_host')]
 return dict(ok=True,index_schema=SCHEMA,sources=rows,observed_events=observed,refreshed_at=at[0] if at else None,native_inventory=json.loads(meta.read_text()) if meta.exists() else None,coverage='indexed public text/metadata only; project locators do not create semantic Affiliation; missing sources stay explicit',model_calls=0)

def authorize(state,actor,args):
 if actor=='owner':return
 from .learning_use import authorized
 task=state.get(args.get('task_id',''),actor)
 if task['revision']!=args.get('task_revision'):raise Fault('REVISION_CONFLICT','current exact Task needed')
 if not task['payload'].get('unified_asset_search_authorized') or not authorized(state,actor,task):raise Fault('PERMISSION','Owner-authorized mapped Task projection required; no raw archive ACL grant')

def matches(body,term):
 if re.fullmatch('[A-Za-z0-9_-]+',term):return bool(re.search(r'(?<![A-Za-z0-9_])'+re.escape(term)+r'(?![A-Za-z0-9_])',body,re.I))
 return term.casefold() in body.casefold()

def search(state,actor,args):
 authorize(state,actor,args);q=args.get('query','').strip();limit=args.get('limit',8);offset=args.get('offset',0)
 if not 1<=len(q)<=200 or type(limit)!=int or not 1<=limit<=20 or type(offset)!=int or offset<0:raise Fault('INPUT','bounded query/page required')
 refresh(state);terms=q.split();host=args.get('host');found=[];title_only_seen=set()
 with LOCK,db(state) as c:
  sql='select * from docs'+(' where host=?' if host else '')
  for r in c.execute(sql,([host] if host else [])):
   body=r['body'];text=r['title']+'\n'+body
   if not all(matches(text,t) for t in terms):continue
   body_match=all(matches(body,t) for t in terms)
   if not body_match:
    group=(r['host'],r['session'])
    if group in title_only_seen:continue
    title_only_seen.add(group)
   pos=body.casefold().find(terms[0].casefold());start=max(0,pos-100)
   found.append(dict(id=r['id'],host=r['host'],session_id=r['session'],project_locator=r['project'],title=r['title'],excerpt=body[start:start+500],locator=json.loads(r['locator']),scope=r['scope'],score=sum(matches(r['title'],t) for t in terms)+2*sum(matches(body,t) for t in terms)))
 found.sort(key=lambda r:(-r['score'],r['host']=='gpt_export',r['id']))
 # Host projection stays smaller than the existing private candidate use contract.
 budget=8000 if actor!='owner' else 30000;page=[];size=0
 for row in found[offset:offset+limit]:
  n=len(canonical(row).encode())
  if size+n>budget:break
  page.append(row);size+=n
 return dict(ok=True,items=page,total=len(found),offset=offset,query=q,source_counts={h:sum(r['host']==h for r in found) for h in sorted({r['host'] for r in found})},scope='all indexed sources by default; bounded source candidate excerpts, not adoption',model_calls=0)

def read(state,actor,args):
 authorize(state,actor,args)
 with LOCK,db(state) as c:r=c.execute('select * from docs where id=?',(args['id'],)).fetchone()
 if not r:raise Fault('NOT_FOUND','refresh/search first')
 return dict(ok=True,id=r['id'],host=r['host'],title=r['title'],body=r['body'][:8000 if actor=='owner' else 4000],truncated=len(r['body'])>(8000 if actor=='owner' else 4000),locator=json.loads(r['locator']),scope=r['scope'],model_calls=0)

def dispatch(state,actor,action,args):
 if action=='unified_search':return search(state,actor,args)
 if action=='unified_read':return read(state,actor,args)
 if actor!='owner':raise Fault('PERMISSION','Owner index inventory')
 return refresh(state) if action=='unified_refresh' else inventory(state)
