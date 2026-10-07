"""Persistent human observability of canonical assets, use and revision evidence."""
import json,re
from .util import Fault,sha

def scripts(text):
 han=bool(re.search(r'[\u3400-\u9fff]',text));latin=bool(re.search(r'[A-Za-z]',text))
 return {'observed_scripts':(['Han'] if han else [])+(['Latin'] if latin else []),'language':'unknown','basis':'title character scripts only; not confirmed body language','declared':False}

def observe(state,actor,args):
 limit=args.get('limit',20);offset=args.get('offset',0);query=args.get('query','');after=args.get('after_cursor')
 if type(limit)!=int or not 1<=limit<=50 or type(offset)!=int or offset<0 or not isinstance(query,str) or len(query)>200 or (after is not None and (not isinstance(after,str) or len(after)!=64)):raise Fault('INPUT','limit1..50, nonnegative offset, cursor64 and query<=200 required')
 deployment=json.loads((state.data/'deployment.json').read_text()) if (state.data/'deployment.json').is_file() else {}
 with state.db() as c:
  c.execute('BEGIN');seq=c.execute('select coalesce(max(seq),0) from events').fetchone()[0]
  has_archive=bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_plans'").fetchone())
  progress=[tuple(r) for r in c.execute('select plan_id,member,cursor,state from archive_progress order by plan_id,member')] if has_archive else []
  read_count=c.execute('select count(*) from archive_reads').fetchone()[0] if has_archive else 0
  cursor=sha([seq,progress,read_count,deployment.get('identity'),actor,offset,limit,query])
  if after==cursor:return {'ok':True,'unchanged':True,'commit_seq':seq,'cursor':cursor,'source_bytes_read':0,'model_calls':0}
  objects=[]
  for r in c.execute('select id from objects'):
   try:objects.append(state._get(c,r['id'],actor))
   except Fault as e:
    if e.code not in ['NOT_FOUND','PERMISSION']:raise
  byid={o['object_id']:o for o in objects};plans=[dict(r) for r in c.execute('select id,source_id,created from archive_plans') if r['source_id'] in byid] if has_archive else []
  planids=[r['id'] for r in plans];assets=[];total=0;messages=0;selected=set();cards={};usage={};links={}
  for o in objects:
   p=o['payload']
   for d in p.get('input_vector',[]):links.setdefault(d['object_id'],[]).append({'id':o['object_id'],'type':o['object_type'],'revision':o['revision']})
   if o['object_type']=='Message':
    loc=p.get('locator',{})
    if isinstance(loc,dict) and loc.get('archive_plan') in planids:usage[o['object_id']]=(loc['archive_plan'],loc['member'],loc['ordinal'])
  for card in objects:
   if card['object_type']!='SemanticCard':continue
   unit=byid.get(card['payload'].get('work_unit_id'))
   if not unit:continue
   for d in unit['payload'].get('message_refs',[]):
    key=usage.get(d['object_id'])
    if key:selected.add(key);cards.setdefault(key,[]).append({'card':card['object_id'],'revision':card['revision'],'summary':card['payload'].get('summary'),'purpose':unit['payload'].get('purpose'),'input_message':d['object_id'],'reuse_refs':links.get(card['object_id'],[])})
  if planids:
   marks=','.join('?' for _ in planids);params=[*planids,query]
   total=c.execute('select count(*) from archive_conversations where plan_id in ('+marks+') and instr(lower(coalesce(title,\'\')),lower(?))>0',params).fetchone()[0]
   messages=c.execute('select count(*) from archive_messages where plan_id in ('+marks+')',planids).fetchone()[0]
   rows=c.execute('select plan_id,member,ordinal,native_id,title,raw_hash,stats from archive_conversations where plan_id in ('+marks+') and instr(lower(coalesce(title,\'\')),lower(?))>0 order by plan_id,member,ordinal limit ? offset ?',params+[limit,offset])
   for r in rows:
    key=(r['plan_id'],r['member'],r['ordinal']);item=dict(r);item['stats']=json.loads(r['stats']);item.update(processing='selected_pending' if key in selected else 'stored_uninterpreted',domain_judgment='unknown',failure_judgment='not_assessed',reuse_policy='source_lookup_only',source_language=scripts(r['title'] or ''),cards=cards.get(key,[]));assets.append(item)
  history=[]
  for r in c.execute('select object_id,revision from object_revisions order by recorded_at desc limit 200'):
   try:o=state._get(c,r['object_id'],actor,r['revision'])
   except Fault as e:
    if e.code in ['NOT_FOUND','PERMISSION']:continue
    raise
   history.append({'id':o['object_id'],'type':o['object_type'],'revision':o['revision'],'status':o['status'],'at':o['recorded_at'],'current_revision':byid.get(o['object_id'],{}).get('revision'),'previous_available':o['revision']>1})
   if len(history)>=30:break
 failures=[{'id':o['object_id'],'revision':o['revision'],'status':o['status'],'lesson':o['payload'].get('lesson'),'properties':o['payload'].get('properties',[]),'applicability':o['payload'].get('applicability',{}),'source':o['payload'].get('source',{}),'input_vector':o['payload'].get('input_vector',[]),'evidence_kind':'synthetic_prompt_provisional' if 'synthetic' in o['payload'].get('reproduction','') else 'runtime_observation','root_cause':o['payload'].get('cause_status','unknown'),'diagnostic_tags':o['payload'].get('diagnostic_tags',[])} for o in objects if o['object_type'] in ['FailureCase','FailurePattern']]
 def dependency_state(o,seen=frozenset()):
  if o['object_id'] in seen:return 'stale_or_unavailable'
  for d in o['payload'].get('input_vector',[]):
   target=byid.get(d['object_id'])
   if not target or target['revision']!=d['revision'] or dependency_state(target,seen|{o['object_id']})!='current':return 'stale_or_unavailable'
  return 'current'
 scopes=[{'id':o['object_id'],'revision':o['revision'],'type':o['object_type'],'status':o['status'],'dependency_state':dependency_state(o),'payload':o['payload'],'dependencies':o['payload'].get('input_vector',[])} for o in objects if o['object_type'] in ['TaskContract','AdoptionDecision','ResponseContract','Affiliation','RetrievalReceipt']]
 source_counts={'plans':len(plans),'matching_conversations':total,'stored_nodes':messages,'selected_conversations':len(selected),'canonical_objects':len(objects),'failure_cases':len(failures)}
 updates=[]
 if actor=='owner':
  for path in sorted((state.root/'logs').glob('deploy-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:20]:
   try:d=json.loads(path.read_text());updates.append({k:d.get(k) for k in ['identity','previous_identity','applied_at','loaded','data_rollback']})
   except (OSError,ValueError):continue
 snapshot={'ok':True,'unchanged':False,'cursor':cursor,'commit_seq':seq,'authority_id':state.authority,'counts':source_counts,'assets':assets,'offset':offset,'limit':limit,'query':query,'failures':failures,'work_and_use':scopes,'history':history,'deployment':{'identity':deployment.get('identity'),'applied_at':deployment.get('applied_at'),'previous_identity':deployment.get('previous_identity')},'system_updates':updates,'history_scope':'latest200 revision rows filtered by actor, up to30 visible rows','refresh_policy':'poll event sequence + archive checkpoints + deployment identity; unchanged returns no rescan','source_bytes_read':0,'model_calls':0,'coverage_limits':['not a semantic classifier','direct recorded dependencies prove recorded use only, not model attention or external success','title script observation is not confirmed original language','missing diagnostic tags remain unknown','plain host chats are not automatically captured without a connected writer']}
 return snapshot
