"""Repair structure from known paid receipts; never infer missing semantics."""
import json,base64,collections
from .util import Fault

def existing_index(inp):
 rows=[]
 for k in inp['knowledge']:
  text=k.get('text','')+' '+' '.join(r.get('quote','') for r in k.get('refs',[]))
  tags=[x for x in inp.get('facets',{}).get('candidate_labels',[]) if x.casefold() in text.casefold()][:2]
  quote=next((r.get('quote','') for r in k.get('refs',[]) if r.get('quote')),None)
  tags.append((quote or k.get('text') or 'source candidate')[:80])
  rows.append(dict(index=k['index'],topics=tags[:3],index_method='reuse existing facets and literal source quotes; no model retagging'))
 return rows

def disposition(inp,raw):
 from .learning import MECHANISMS
 groups=collections.defaultdict(list)
 try:
  parsed=json.loads(raw['choices'][0]['message']['content'])
  for job in parsed.get('jobs',[]):
   for row in job.get('issues',[]):
    if isinstance(row,dict) and isinstance(row.get('case_id'),str):groups[row['case_id']].append(row)
 except (ValueError,KeyError,TypeError,AttributeError):pass
 issues=[];pending=[]
 for case in inp['issues']:
  ident=case['case_ref']['object_id'];rows=groups[ident]
  valid=[r for r in rows if r.get('mechanism') in MECHANISMS and r.get('relation') in ['related_candidate','condition_extension_candidate','unresolved','normal_boundary'] and isinstance(r.get('basis'),str) and 1<=len(r['basis'])<=1000]
  signatures={(r['mechanism'],r['relation'],r['basis']) for r in valid}
  if rows and len(valid)==len(rows) and len(signatures)==1:
   issues.append({k:valid[0][k] for k in ['case_id','mechanism','relation','basis']})
  else:
   pending.append(ident)
   issues.append(dict(case_id=ident,mechanism='normal_boundary',relation='unresolved',basis='程序未取得唯一有效比较；保留原候选待语义复核，不判定正常或故障'))
 return dict(issues=issues,knowledge=existing_index(inp),program_repair=dict(method='canonical case IDs and bounded enums; reuse settled output only',semantic_pending=pending,provider_calls=0))

def reconcile(state,args):
 from .learning import folder,candidate_input,receive,oid
 results=[];blocked=[]
 for path in sorted((folder(state)/'jobs').glob('*.json')):
  j=json.loads(path.read_text())
  if j['state']!='needs_review' or j['source_kind']=='native_work':continue
  receipt=folder(state)/'receipts'/(j['id']+'.json')
  r=json.loads(receipt.read_text()) if receipt.exists() else {}
  if r.get('state')!='settled':blocked.append(j['id']);continue
  try:
   try:
    artifact=state.get(oid(state,'Artifact',['result',j['id']]),'owner')
   except Fault as error:
    if error.code!='NOT_FOUND':raise
    result=disposition(candidate_input(state,j),r.get('raw',{}))
   else:
    result=json.loads(base64.b64decode(state.fetch_blob('owner',artifact['object_id'],artifact['revision'],1048576)['base64']))['comparison']
   done=receive(state,j,result)
   results.append(dict(job_id=j['id'],result_ref=done['result_ref'],pending=len(result.get('program_repair',{}).get('semantic_pending',[]))))
  except Fault as error:blocked.append(dict(job_id=j['id'],code=error.code))
 return dict(ok=True,repaired=results,blocked=blocked,provider_calls=0,semantic_acceptance=False)
