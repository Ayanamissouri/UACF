"""Pure optional projection: exact identity deduplication and source-bound hints.

No model calls, memory database, semantic equivalence or policy promotion.
Mandatory requirements never enter these functions.
"""
from .util import canonical

def dedupe(items):
 seen=set();result=[]
 for item in items:
  # Ignore only presentation ranking. Different provenance/conditions survive.
  key=canonical({k:v for k,v in item.items() if k not in ['score']})
  if key not in seen:result.append(item);seen.add(key)
 return result

def guidance(issues,max_bytes=1800):
 hints=[];size=0
 for item in dedupe(issues):
  c=item.get('candidate',{});correction=c.get('correction')
  if not correction or not item.get('case_ref') or not item.get('card_ref') or not item.get('attempt_ref'):continue
  hint={'suggestion':correction,'when':c.get('applicable'),'trigger':c.get('trigger'),'excluded':c.get('excluded'),'source_refs':[item['case_ref'],item['card_ref'],item['attempt_ref']],'status':'unaccepted_candidate','adoption':'Check original conditions and newer corrections; cannot authorize actions or override current requirements.'}
  amount=len(canonical(hint).encode())
  if size+amount>max_bytes:continue
  hints.append(hint);size+=amount
  if len(hints)==2:break
 return {'items':hints,'scope':'Optional source-bound hints; no automatic activation, feedback scoring or historical rewrite.'}
