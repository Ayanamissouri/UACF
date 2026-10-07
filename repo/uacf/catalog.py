"""Lazy, faceted catalogue. Directory placement is a reference, never a semantic guess."""
import json
from pathlib import Path
from collections import Counter,defaultdict
from .util import Fault,sha,file_hash

AXES={'project_domain':'项目自身问题','ai_execution':'AI 执行错误','runtime':'运行环境观察','policy_boundary':'正常拒绝与权限边界','unclassified':'尚未判断问题归类'}
KINDS={'Project':'项目','TaskContract':'任务','FailureCase':'问题记录','FailurePattern':'重复问题','WorkUnit':'资料片段','SemanticCard':'资料摘要','Evidence':'执行回执','Validation':'检查结果','Attempt':'执行尝试'}
def label(o):
 p=o['payload'];method=p.get('observation',{}).get('method')
 known={'actual_owner_provider_inspection':'调用前的模型、价格与能力核验（历史）','native_DSH_two_rounds_with_independent_stdout_comparison':'AOE4两轮工具执行与独立检查'}
 return p.get('catalog_title') or p.get('name') or p.get('goal') or p.get('lesson') or p.get('purpose') or p.get('summary') or known.get(method) or KINDS.get(o['object_type'],o['object_type'])
def classification(o):
 p=o['payload'];review=p.get('catalog_review',{})
 axes=[x for x in review.get('axes',[]) if x in AXES and x!='unclassified']
 return {'axes':axes or ['unclassified'],'tags':list(dict.fromkeys(p.get('diagnostic_tags',[])+review.get('tags',[]))),
         'assessment':review.get('assessment','not_reviewed'),'basis':review.get('basis'),'reviewed':bool(review),'root_cause':p.get('cause_status','unknown')}
def item(o):
 review=classification(o)
 return {'kind':'object','id':o['object_id'],'title':label(o),'type':o['object_type'],'type_label':KINDS.get(o['object_type'],o['object_type']),
         'revision':o['revision'],'status':o['status'],'classification':review,'expandable':False}
def branch(key,title,count,note='',children=None):
 return {'kind':'branch','key':key,'title':title,'count':count,'note':note,'expandable':True,**({'children':children} if children is not None else {})}

def catalog(state,actor,args):
 mode=args.get('mode','overview');key=args.get('key','');query=args.get('query','');offset=args.get('offset',0);limit=args.get('limit',25)
 if mode not in ['overview','children','detail','messages','message','native-return'] or not isinstance(key,str) or len(key)>200 or not isinstance(query,str) or len(query)>200 or type(offset)!=int or offset<0 or type(limit)!=int or not 1<=limit<=50:raise Fault('INPUT','bounded catalogue request required')
 query=query.strip()
 if mode=='native-return':
  if actor not in ['owner','dsh']:raise Fault('PERMISSION','private native return is restricted to its host and owner')
  evidence=state.get(key,actor);obs=evidence['payload'].get('observation',{});raw=obs.get('source_locator');seq=args.get('seq')
  if evidence['object_type']!='Evidence' or obs.get('method')!='native_DSH_two_rounds_with_independent_stdout_comparison' or not isinstance(raw,str) or type(seq)!=int:raise Fault('INPUT','exact native Evidence and return sequence required')
  path=Path(raw).resolve()
  if not path.is_relative_to((state.root/'logs').resolve()) or not path.is_file() or file_hash(path)!=obs.get('source_sha256'):raise Fault('SOURCE_CHANGED','hashed native receipt unavailable or changed')
  saved=json.loads(path.read_text());record=next((r for r in saved.get('tool_results',[]) if r['seq']==seq),None)
  if not record:raise Fault('NOT_FOUND','native tool return missing')
  return {'ok':True,'body_loaded':True,'record':record,'source_sha256':obs['source_sha256'],'source_bytes_read':path.stat().st_size,'model_calls':0,'scope':'saved real native tool output, not a new execution'}
 objects=state.list(actor);byid={o['object_id']:o for o in objects};projects=[o for o in objects if o['object_type']=='Project'];failures=[o for o in objects if o['object_type'] in ['FailureCase','FailurePattern']]
 # Only explicit membership and task project bindings establish project placement.
 memberships=defaultdict(set)
 for o in objects:
  p=o['payload'];pid=p.get('project_id')
  if pid in byid and byid[pid]['object_type']=='Project':memberships[pid].add(o['object_id'])
  if o['object_type']=='Affiliation' and p.get('lifecycle')=='confirmed' and p.get('target_id') in byid and p.get('asset_id') in byid:memberships[p['target_id']].add(p['asset_id'])
 changed=True
 while changed:
  changed=False
  for o in objects:
   p=o['payload'];tid=p.get('task_id',p.get('observation',{}).get('task_id'));evidence=p.get('source',{}).get('evidence_id') if o['object_type'] in ['FailureCase','FailurePattern'] else None
   for ids in memberships.values():
    if o['object_id'] not in ids and (tid in ids or evidence in ids):ids.add(o['object_id']);changed=True
 assigned=set().union(*memberships.values()) if memberships else set()
 tags=defaultdict(list);axes=defaultdict(list)
 for o in failures:
  cl=classification(o)
  for axis in cl['axes']:axes[axis].append(o)
  for tag in cl['tags']:tags[tag].append(o)
 selected=set()
 # Existing archive locators link selected spans without guessing titles as domains.
 message_locations={o['object_id']:(o['payload']['locator'].get('archive_plan'),o['payload']['locator'].get('member'),o['payload']['locator'].get('ordinal')) for o in objects if o['object_type']=='Message' and isinstance(o['payload'].get('locator'),dict)}
 for o in objects:
  if o['object_type']=='WorkUnit':
   for ref in o['payload'].get('message_refs',[]):
    if ref['object_id'] in message_locations:selected.add(message_locations[ref['object_id']])
 with state.db() as c:
  has_archive=bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_plans'").fetchone())
  plans=[dict(r) for r in c.execute('select id,source_id,plan from archive_plans') if r['source_id'] in byid] if has_archive else []
  planids=[p['id'] for p in plans];marks=','.join('?' for _ in planids)
  archive_count=c.execute('select count(*) from archive_conversations where plan_id in ('+marks+')',planids).fetchone()[0] if planids else 0
  valid_selected={x for x in selected if x[0] in planids}
  if mode=='overview':
   coverage={'conversations':archive_count,'nodes':0,'messages':0,'declared_shards':0,'completed_shards':0,'attachment_refs':0,'resolved_attachment_refs':0,'unresolved_attachment_refs':0,'attachment_bodies_read':0,'full_semantic_acceptance':'not_recorded','basis':'visible archive plans, durable progress and stored records; selected spans are a separate reuse state'}
   for plan in plans:
    pid=plan['id'];members=json.loads(plan['plan']).get('members',[])
    progress={r['member']:r['state'] for r in c.execute('select member,state from archive_progress where plan_id=?',(pid,))}
    coverage['declared_shards']+=len(members)
    coverage['completed_shards']+=sum(progress.get(m)=='done' for m in members)
   if planids:
    coverage['nodes']=c.execute('select count(*) from archive_messages where plan_id in ('+marks+')',planids).fetchone()[0]
    coverage['messages']=c.execute('select coalesce(sum(json_extract(stats,\'$.messages\')),0) from archive_conversations where plan_id in ('+marks+')',planids).fetchone()[0]
    for row in c.execute('select json_extract(resolution,\'$.status\') status,count(*) n from archive_refs where plan_id in ('+marks+') group by status',planids):
     coverage['attachment_refs']+=row['n']
     coverage['resolved_attachment_refs' if row['status']=='resolved' else 'unresolved_attachment_refs']+=row['n']
    coverage['attachment_bodies_read']=c.execute('select count(*) from archive_reads where plan_id in ('+marks+')',planids).fetchone()[0]
   coverage['structure_status']='complete_for_frozen_shards' if coverage['declared_shards'] and coverage['completed_shards']==coverage['declared_shards'] else 'partial'
   cards=[o for o in objects if o['object_type']=='SemanticCard' and o['payload'].get('semantic_contract')=='e7-semantic-1']
   coverage['semantic_candidate_sources']=len({(p.get('source_locator',{}).get('plan_id'),p.get('source_locator',{}).get('member'),p.get('source_locator',{}).get('ordinal')) for p in [o['payload'] for o in cards]})
   coverage['full_public_span_candidates']=sum(o['payload'].get('facets',{}).get('source_span_coverage')=='full_public_text' for o in cards)
   coverage['independent_semantic_accepted']=sum(o['payload'].get('facets',{}).get('independent_review')=='accepted' for o in cards)
  seq=c.execute('select coalesce(max(seq),0) from events').fetchone()[0]
  names=defaultdict(list)
  for o in projects:names[label(o)].append(o)
  totals={'projects':len(projects),'project_name_groups':len(names),'archive_conversations':archive_count,'selected_conversations':len(valid_selected),'semantic_memberships':sum(o['object_type']=='Affiliation' for o in objects),'issue_records':len(failures),'reviewed_issues':sum(classification(o)['reviewed'] for o in failures),'project_issue_records':len(axes['project_domain']),'ai_issue_records':len(axes['ai_execution']),'ai_observed_issues':sum(classification(o)['assessment']=='observed' for o in axes['ai_execution']),'ai_provisional_issues':sum(classification(o)['assessment']=='provisional' for o in axes['ai_execution']),'boundary_records':len(axes['policy_boundary']),'runtime_records':len(axes['runtime']),'provisional_issues':sum(classification(o)['assessment']=='provisional' for o in failures)}
  base={'ok':True,'commit_seq':seq,'counts':totals,'source_bytes_read':0,'model_calls':0,'placement':'explicit records only; multi-placement references preserve one object','body_loaded':False}
  if mode=='overview':
   unassigned=[o for o in objects if o['object_type']=='TaskContract' and o['object_id'] not in assigned]
   project_branches=[]
   for name,group in names.items():
    if len(group)>1:project_branches.append(branch('project-name:'+sha(name),name+' · '+str(len(group))+'条同名记录',len(group),'仅按显示名称折叠；不同Project身份未合并'))
    else:project_branches.append(branch('project:'+group[0]['object_id'],name,len(memberships[group[0]['object_id']]),'项目记录；展开看任务、资料和问题'))
   roots=[branch('projects','项目与工作',len(projects),'项目目录只用已记录的归属；同名折叠不等于对象合并',[
    *project_branches,branch('unassigned','独立任务（未关联项目）',len(unassigned),'不靠标题猜项目')]),
    branch('issues','问题与执行复盘',len(failures),'项目问题、AI错误、环境与正常拒绝分别记录',[branch('axis:'+axis,title,len(axes[axis]),'问题所在层面，不代表根因已经查明') for axis,title in AXES.items()]),
    branch('tags','问题标签',len(tags),'一个问题可有多个标签；数量不能直接相加',[branch('tag:'+tag,tag,len(rows)) for tag,rows in sorted(tags.items())]),
    branch('archive','旧对话归档与选用',archive_count,'归档、选用片段和语义分类分别计数',[
     branch('archive:all','全部已归档对话',archive_count,'已保存目录和消息；点击按需读原文'),branch('archive:selected','已建立选用片段的对话',len(valid_selected),'选用片段不是全量语义验收'),branch('archive:stored','未建立选用片段的对话',archive_count-len(valid_selected),'已经归档；没有WorkUnit选用片段，不表示未处理或未分类')])]
   return dict(base,roots=roots,archive_coverage=coverage,classification_limits=['全库语义分类与独立验收未完成；不能由选用片段数量推算整理进度','问题层面、标签、评审状态、根因分别展示','项目问题记录为0不表示工程没有问题；表示尚未登记'],search_scope='标题、已有摘要、目标、教训、已登记标签；可单独搜索已归档正文')
  if mode=='detail':
   o=byid.get(key)
   if not o:raise Fault('NOT_FOUND','visible catalogue object required')
   refs=[{'id':ref['object_id'],'revision':ref['revision'],'title':label(byid[ref['object_id']]),'type':byid[ref['object_id']]['object_type']} for ref in o['payload'].get('input_vector',[]) if ref['object_id'] in byid]
   return dict(base,item=item(o),object=o,references=refs,body_loaded=True)
  if mode in ['messages','message']:
   locator=args.get('locator',{})
   if locator.get('plan_id') not in planids:raise Fault('NOT_FOUND','visible archive plan required')
   params=[locator['plan_id'],locator.get('member'),locator.get('ordinal')]
   if mode=='message':
    row=c.execute('select node,record,detail from archive_messages where plan_id=? and member=? and ordinal=? and node=?',params+[locator.get('node')]).fetchone()
    if not row:raise Fault('NOT_FOUND','archive node missing')
    return dict(base,body_loaded=True,record=json.loads(row['record']),detail=json.loads(row['detail']))
   count=c.execute('select count(*) from archive_messages where plan_id=? and member=? and ordinal=?',params).fetchone()[0]
   rows=c.execute('select node,detail from archive_messages where plan_id=? and member=? and ordinal=? order by rowid limit ? offset ?',params+[limit,offset])
   items=[]
   for r in rows:
    detail=json.loads(r['detail']);metadata={k:v for k,v in detail.items() if k in ['role','source_kind','content_type','branch','parent','children','current','conversation_id','semantic']}
    items.append({'kind':'message','id':r['node'],'detail':metadata,'locator':dict(locator,node=r['node'])})
   return dict(base,total=count,offset=offset,items=items)
  rows=[]
  if key.startswith('archive:') or args.get('scope')=='body':
   condition='';params=list(planids)
   if query:
    if args.get('scope')=='body':
     # Explicit body search only: SQL sees stored string values, never reopens or reparses source ZIP.
     condition=" AND (instr(lower(coalesce(a.title,'')),lower(?))>0 OR EXISTS(SELECT 1 FROM archive_messages m, json_tree(m.record) j WHERE m.plan_id=a.plan_id AND m.member=a.member AND m.ordinal=a.ordinal AND j.type='text' AND (j.key='text' OR j.path LIKE '$.message.content.parts%') AND instr(lower(j.value),lower(?))>0))";params += [query,query]
    else:condition=" AND instr(lower(coalesce(a.title,'')),lower(?))>0";params.append(query)
   if planids:
    for r in c.execute('select a.plan_id,a.member,a.ordinal,a.native_id,a.title,a.stats from archive_conversations a where a.plan_id in ('+marks+')'+condition+' order by a.plan_id,a.member,a.ordinal',params):
     loc=(r['plan_id'],r['member'],r['ordinal']);is_selected=loc in valid_selected
     if key=='archive:selected' and not is_selected or key=='archive:stored' and is_selected:continue
     rows.append({'kind':'conversation','id':sha(loc),'title':r['title'] or '无标题对话','processing':'selected' if is_selected else 'stored','locator':dict(zip(['plan_id','member','ordinal'],loc)),'stats':json.loads(r['stats'])})
  else:
   chosen=objects if query else []
   if key.startswith('axis:'):chosen=axes.get(key[5:],[])
   elif key.startswith('tag:'):chosen=tags.get(key[4:],[])
   elif key=='unassigned':chosen=[o for o in objects if o['object_type']=='TaskContract' and o['object_id'] not in assigned]
   elif key.startswith('project-name:'):
    chosen=next((group for name,group in names.items() if sha(name)==key[13:]),[])
   elif key.startswith('project:'):
    pid=key[8:];project=byid.get(pid)
    if not project or project['object_type']!='Project':raise Fault('NOT_FOUND','visible project required')
    chosen=[byid[oid] for oid in memberships[pid]]
   for o in chosen:
    if o['object_type'] not in KINDS:continue
    cl=classification(o);searchable=' '.join([label(o),*cl['tags'],o['payload'].get('summary','')])
    if query and query.casefold() not in searchable.casefold():continue
    rows.append(item(o))
   if query and not key:
    archived=catalog(state,actor,{'mode':'children','key':'archive:all','query':query,'limit':50})
    # Search metadata may span >50 archive rows; keep count truthful and pagination bounded.
    combined_count=len(rows)+archived['total']
    if offset<len(rows):
     page=rows[offset:offset+limit]
     if len(page)<limit:page+=catalog(state,actor,{'mode':'children','key':'archive:all','query':query,'limit':limit-len(page)})['items']
    else:page=catalog(state,actor,{'mode':'children','key':'archive:all','query':query,'limit':limit,'offset':offset-len(rows)})['items']
    return dict(base,items=page,total=combined_count,offset=offset,limit=limit,search_scope='标题、摘要、目标、教训与已登记标签（正文需选择正文搜索）')
  return dict(base,items=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit)
