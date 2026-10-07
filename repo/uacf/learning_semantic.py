"""Source-bound semantic review queue. Retrieval scores are never verdicts."""
import json,re,math,collections
from .util import Fault,canonical,atomic,sha,now
from .fabric import vector
from .learning_use import issue_index
FIELDS=['trigger','actual','expected','correction','applicable','excluded']
VERDICTS=['same_principle','equivalent_conditions','different_conditions','independent','insufficient_evidence']
def directory(state):
 from .learning import folder
 p=folder(state)/'semantic';p.mkdir(exist_ok=True);return p
def load(p,default):return json.loads(p.read_text(encoding='utf8')) if p.exists() else default
def records(state):return load(directory(state)/'reviews.json',{})
def build(state):
 rows=issue_index(state);docs={};df=collections.Counter();inv=collections.defaultdict(list)
 for ident,row in rows.items():
  c=row['candidate'];t=' '.join(str(c.get(k,'')) for k in FIELDS[:4]).lower()
  tokens=set(re.findall(r'[a-z][a-z0-9_-]{2,}',t))
  tokens.update(t[i:i+2] for i in range(len(t)-1) if all('\u4e00'<=x<='\u9fff' for x in t[i:i+2]))
  docs[ident]=tokens;df.update(tokens)
 n=len(rows);weights={t:math.log(1+n/(1+v)) for t,v in df.items()};norm={i:math.sqrt(sum(weights[t]**2 for t in ts)) for i,ts in docs.items()}
 for i,ts in docs.items():
  for t in ts:
   if df[t]<=max(10,n//3):inv[t].append(i)
 pairs={}
 for i,ts in docs.items():
  score=collections.Counter()
  for t in ts:
   for j in inv.get(t,[]):
    if i!=j and rows[i]['card_ref']!=rows[j]['card_ref']:score[j]+=weights[t]**2
  ranked=sorted(((v/(norm[i]*norm[j] or 1),j) for j,v in score.items()),reverse=True)[:3]
  for sim,j in ranked:
   if sim<.22:continue
   a,b=sorted([i,j]);key=sha([rows[a]['case_ref'],rows[b]['case_ref']]);pairs[key]=dict(pair_id=key,left_ref=rows[a]['case_ref'],right_ref=rows[b]['case_ref'],retrieval_score=round(sim,4),review_state='unreviewed',retrieval_is_semantic_verdict=False)
 queue=dict(at=now(),source_case_count=n,index_identity=sha(rows),pairs=sorted(pairs.values(),key=lambda x:-x['retrieval_score']),method='weighted Chinese bigram/English retrieval across different source cards; 3 neighbors, score>=0.22; only proposes pairs, misses paraphrases without lexical overlap')
 atomic(directory(state)/'queue.json',canonical(queue));return dict(ok=True,cases=n,pairs=len(pairs),semantic_reviews=len(records(state)),provider_calls=0)
def current(state,ref):
 case=state.get(ref['object_id'],'owner')
 if vector(case)!=ref:raise Fault('REVISION_CONFLICT','semantic review source changed')
 return case
def submit(state,args):
 from .learning import save_once
 items=args.get('items',[])
 if not isinstance(items,list) or not 1<=len(items)<=30:raise Fault('INPUT','1..30 explicit semantic pair reviews')
 queue=load(directory(state)/'queue.json',{});pairs={x['pair_id']:x for x in queue.get('pairs',[])};saved=records(state);refs=[]
 for item in items:
  pair=pairs.get(item.get('pair_id'))
  if not pair:raise Fault('INPUT','review a proposed source-bound pair')
  a=current(state,pair['left_ref']);b=current(state,pair['right_ref'])
  if item.get('verdict') not in VERDICTS:raise Fault('INPUT','explicit semantic verdict required')
  for k in ['principle','basis','condition_comparison']:
   if not isinstance(item.get(k),str) or not 6<=len(item[k])<=1600:raise Fault('INPUT','semantic meaning, evidence and conditions must be written')
  if not item.get('reviewer_locator'):raise Fault('INPUT','public review locator required; not a model/tool probe')
  # These are semantic judgments about existing candidates, not domain truth or executable rules.
  review=dict(pair=pair,verdict=item['verdict'],principle=item['principle'],basis=item['basis'],condition_comparison=item['condition_comparison'],reviewer_locator=item['reviewer_locator'],source_condition_hashes=[sha(a['payload']['case_details']),sha(b['payload']['case_details'])],candidate_semantic_review=True,domain_truth_accepted=False,hard_rule_adopted=False,source_instances_deleted=False)
  ev=save_once(state,'Evidence',dict(observation=dict(method='explicit current-host semantic comparison',review=review),input_vector=[pair['left_ref'],pair['right_ref']]),['semantic-review',review])
  group_ref=None
  if item['verdict'] in ['same_principle','equivalent_conditions','different_conditions']:
   group=save_once(state,'FailurePattern',dict(properties=['learning_semantic_comparison'],lesson=item['principle'],source=dict(grading='reviewed reusable principle, not verified historical failure or executable rule'),applicability={},semantic_group=True,hard_rule_adopted=False),['semantic-principle',item['principle']]);group_ref=vector(group)
   for ref in [pair['left_ref'],pair['right_ref']]:
    save_once(state,'Relation',dict(source_id=ref['object_id'],target_id=group['object_id'],kind='qualifies',basis=canonical(dict(semantic_review=vector(ev),verdict=item['verdict'],conditions_preserved=True))),['semantic-group-link',ref,group_ref,vector(ev)])
  saved[pair['pair_id']]=dict(review=review,evidence_ref=vector(ev),group_ref=group_ref);refs.append(vector(ev))
 atomic(directory(state)/'reviews.json',canonical(saved));return dict(ok=True,reviewed=len(items),evidence_refs=refs,provider_calls=0)
def overview(state,args):
 rows=issue_index(state);queue=load(directory(state)/'queue.json',{});reviews=records(state)
 for x in reviews.values():
  ev=state.get(x['evidence_ref']['object_id'],'owner')
  if vector(ev)!=x['evidence_ref'] or ev['payload']['observation']['review']!=x['review']:raise Fault('REVIEW_CHANGED','semantic review cache mismatch')
  for k in ['left_ref','right_ref']:current(state,x['review']['pair'][k])
 query=args.get('query','');offset=args.get('offset',0);limit=args.get('limit',20)
 if not isinstance(query,str) or len(query)>200 or type(offset)!=int or offset<0 or type(limit)!=int or not 1<=limit<=50:raise Fault('INPUT','bounded query/page')
 def detail(ref):
  row=rows.get(ref['object_id']);case=current(state,ref);return dict(case_ref=ref,card_ref=row.get('card_ref') if row else None,conditions=case['payload'].get('case_details',{}))
 pairs=[]
 for p in queue.get('pairs',[]):
  r=reviews.get(p['pair_id']);text=canonical(r or p)
  if args.get('unreviewed_only') and r:continue
  if args.get('reviewed_only') and not r:continue
  if query and query.lower() not in text.lower() and not any(query.lower() in canonical(rows.get(p[k]['object_id'],{})).lower() for k in ['left_ref','right_ref']):continue
  pairs.append((p,r))
 page=[dict(p,review=r,**{k:detail(p[k+'_ref']) for k in ['left','right']}) for p,r in pairs[offset:offset+limit]]
 counts=dict(collections.Counter(x['review']['verdict'] for x in reviews.values()));covered={x['review']['pair'][k]['object_id'] for x in reviews.values() for k in ['left_ref','right_ref']}
 return dict(ok=True,cases=len(rows),proposed_pairs=len(queue.get('pairs',[])),reviewed_pairs=len(reviews),reviewed_cases=len(covered),unreviewed_cases=len(rows)-len(covered),verdict_counts=counts,pair_total=len(pairs),offset=offset,rows=page,all_900_semantic_review_complete=False,method=queue.get('method'),meaning='same_principle shares a reusable lesson with separate conditions; equivalent_conditions may link same conditional pattern; neither confirms historical/model/domain truth or installs a hard guard')

def annotations(state):
 result={}
 for row in records(state).values():
  ev=state.get(row['evidence_ref']['object_id'],'owner')
  if vector(ev)!=row['evidence_ref'] or ev['payload']['observation']['review']!=row['review']:raise Fault('REVIEW_CHANGED','semantic annotations mismatch canonical review')
  for key in ['left_ref','right_ref']:current(state,row['review']['pair'][key])
  if row['review']['verdict'] not in ['same_principle','equivalent_conditions','different_conditions']:continue
  for key in ['left_ref','right_ref']:
   ident=row['review']['pair'][key]['object_id'];result.setdefault(ident,[]).append(dict(principle=row['review']['principle'],verdict=row['review']['verdict'],evidence_ref=row['evidence_ref'],group_ref=row.get('group_ref'),condition_comparison=row['review']['condition_comparison']))
 return result
