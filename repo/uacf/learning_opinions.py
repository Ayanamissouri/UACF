"""Human-facing opinions derived only from explicit reviewed principle links."""
import collections,json
from .util import Fault,canonical
from .fabric import owner,vector
from .learning_use import issue_index
from .learning_semantic import records

def source(state,actor,args):
 owner(actor);case=state.get(args['case_ref']['object_id'],actor);card=state.get(args['card_ref']['object_id'],actor)
 if vector(case)!=args['case_ref'] or vector(card)!=args['card_ref']:raise Fault('SOURCE_CHANGED','exact instance/source revision required')
 row=issue_index(state).get(case['object_id'])
 if not row or row['card_ref']!=args['card_ref']:raise Fault('SOURCE_CHANGED','instance is not linked to this source')
 return dict(ok=True,case_ref=vector(case),original_conditions=case['payload'].get('case_details',{}),source_card_ref=vector(card),source_title=card['payload'].get('catalog_title') or card['payload'].get('summary'),evidence_map=card['payload'].get('evidence_map',[]),source_locator=card['payload'].get('source_locator'),source_ref=card['payload'].get('source_ref'),scope='private local candidate source/quotation linkage; raw attachments and historical domain truth not inferred')

def opinions(state,actor,args):
 owner(actor);query=args.get('query','');offset=args.get('offset',0);limit=args.get('limit',12)
 if not isinstance(query,str) or len(query)>200 or type(offset)!=int or offset<0 or type(limit)!=int or not 1<=limit<=25:raise Fault('INPUT','bounded human opinion page')
 idx=issue_index(state);reviews=records(state);groups={};covered=set();verdicts=collections.Counter()
 with state.db() as c:
  c.execute('BEGIN');cached={}
  def current(ref):
   ident=ref['object_id']
   if ident not in cached:cached[ident]=state._get(c,ident,actor)
   obj=cached[ident]
   if vector(obj)!=ref:raise Fault('SOURCE_CHANGED','reviewed opinion input changed; rebuild/review explicitly')
   return obj
  for r in reviews.values():
   ev=current(r['evidence_ref']);review=r['review']
   if ev['payload']['observation']['review']!=review:raise Fault('REVIEW_CHANGED','canonical comparison differs from cache')
   for k in ['left_ref','right_ref']:current(review['pair'][k]);covered.add(review['pair'][k]['object_id'])
   verdicts[review['verdict']]+=1
   if not r.get('group_ref'):continue
   group=current(r['group_ref']);ident=group['object_id'];g=groups.setdefault(ident,dict(principle_ref=vector(group),principle=group['payload']['lesson'],instances={},comparisons=[]))
   for k in ['left_ref','right_ref']:
    ref=review['pair'][k];case=current(ref);row=idx.get(ref['object_id'],{})
    g['instances'][ref['object_id']]=dict(case_ref=ref,card_ref=row.get('card_ref'),conditions=case['payload'].get('case_details',{}),source_kind='private source-bound candidate; expand locally')
   g['comparisons'].append(dict(verdict=review['verdict'],comparison=review['condition_comparison'],basis=review['basis'],evidence_ref=r['evidence_ref'],pair=review['pair']))
 rows=[dict(g,instances=list(g['instances'].values()),instance_count=len(g['instances']),rule_status='已审候选原则；不是已注册执行约束，领域真值未验') for g in groups.values() if query.casefold() in canonical(g).casefold()]
 rows.sort(key=lambda x:(-x['instance_count'],x['principle_ref']['object_id']))
 from .learning import folder
 p=folder(state)/'recall.json';recall=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {};knowledge=sum(len(x['knowledge']) for x in recall.values())
 return dict(ok=True,total_principles=len(groups),matching_principles=len(rows),offset=offset,rows=rows[offset:offset+limit],counts=dict(indexed_sources=len(recall),knowledge_candidates=knowledge,issue_instances=len(idx),reviewed_pairs=len(reviews),reviewed_instances=len(covered),unreviewed_instances=len(idx)-len(covered),verdict_counts=dict(verdicts)),meaning='一份已审原则链接多个原实例，各自条件保留。独立/未决对不并入原则。没有成对审查的知识或问题不会按字面或机制族自动去重。',knowledge_scope='知识候选逐条查询；尚未全部语义去重。索引来源数不等于详细提取总覆盖。',hard_rules_added=0)
