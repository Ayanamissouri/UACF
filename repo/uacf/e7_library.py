"""Read-only source-bound first-round library over the existing authority and ACL."""
from .util import Fault
def library(state,actor,args):
 query=args.get('query','');mode=args.get('mode','summary')
 if not isinstance(query,str) or len(query)>200 or mode not in ['summary','body','issues','recall']:raise Fault('INPUT','bounded summary/body/issues/recall query required')
 if mode=='recall':
  applicable=[];excluded=[]
  for f in state.list(actor,'FailureCase'):
   criteria=f['payload'].get('retrieval_criteria')
   if not criteria:continue
   reasons=[k+': mismatch or unknown' for k,v in criteria.items() if args.get('task',{}).get(k)!=v]
   item={'failure_id':f['object_id'],'revision':f['revision'],'criteria':criteria,'mandatory':False,'assessment':'source-backed candidate; not an accepted failure obligation'}
   (excluded if reasons else applicable).append(dict(item,reasons=reasons) if reasons else item)
  return {'ok':True,'applicable':applicable,'excluded':excluded,'selection':'explicit Task nature and constraints, no title/keyword scoring','validation_pass':False}
 cards=[o for o in state.list(actor,'SemanticCard') if o['payload'].get('semantic_contract')=='e7-semantic-1']
 if mode=='issues':
  cases=[o for o in state.list(actor,'FailureCase') if o['payload'].get('semantic_contract')=='e7-semantic-1']
  return {'ok':True,'items':[{'id':o['object_id'],'title':o['payload'].get('catalog_title','待复核问题'),'assessment':'provisional','axes':o['payload'].get('catalog_review',{}).get('axes',[])} for o in cases], 'total':len(cases),'independent_confirmed':0}
 if mode=='body':
  from .catalog import catalog
  result=catalog(state,actor,{'mode':'children','key':'archive:all','scope':'body','query':query,'limit':50,'offset':args.get('offset',0)})
  result['semantic_scope']='正文词语命中；不等于语义适用或验收';return result
 rows=[]
 for o in cards:
  p=o['payload'];title=p.get('catalog_title','');summary=p.get('summary','');labels=p['facets'].get('candidate_labels',[])
  if query and query.casefold() not in (title+' '+summary+' '+' '.join(labels)).casefold():continue
  rows.append({'id':o['object_id'],'revision':o['revision'],'title':title,'summary':summary,'labels':labels,'knowledge':p.get('knowledge',[]),'coverage':p.get('coverage',{}),'source_locator':p.get('source_locator'), 'review':p['facets'].get('independent_review'),'source_span_coverage':p['facets'].get('source_span_coverage'),'summary_omissions':p.get('summary_omissions',[]),'evidence_map':p.get('evidence_map',[])})
 return {'ok':True,'total_candidate_cards':len(cards),'shown':len(rows),'rows':rows,'whole_E7_acceptance':False,'independent_accepted':0,'semantics':'来源绑定候选；未经独立语义确认','model_calls':0,'source_bytes_read':0}
