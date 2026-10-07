"""Host-scoped trial reservations: one parent account and an atomic aggregate cap."""
import json,math
from .util import Fault,canonical,now
from .state import uuid_ok

def reserve(state,actor,args,oid):
 if actor not in ['pi','dsh']:raise Fault('PERMISSION','trial Host principal required')
 if state.config.get('restore_mapping'):raise Fault('HOST_REMAP_REQUIRED','isolated recovery cannot dispatch')
 uuid_ok(oid)
 with state.db() as c:
  c.execute('BEGIN IMMEDIATE')
  task=state.get(args['task_id'],actor);p=task['payload'];trial=p.get('trial_budget',{})
  if task['object_type']!='TaskContract' or task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','exact current trial Task required')
  if p.get('execution_state')=='stopped' or p.get('allow_provider') is not True or trial.get('authorized') is not True:
   raise Fault('STOPPED','current Task does not authorize this paid trial')
  uuid_ok(trial.get('trial_id'));cap=trial.get('limit_micro');account=trial.get('account')
  if type(cap)!=int or cap<1 or account!=p.get('budget_account') or not trial.get('authorization_source'):
   raise Fault('BUDGET_ACCOUNT_MISMATCH','Owner trial authorization and parent account required')
  bindings=json.loads((state.data/'host-bindings.json').read_text())
  if bindings.get(actor,{}).get(args['native_session_id'])!=task['object_id']:raise Fault('PERMISSION','exact native trial mapping required')
  route=trial.get('profiles',{}).get(actor)
  if route!={'object_id':args['provider_profile_id'],'revision':args['provider_profile_revision']}:
   raise Fault('ROUTE_PERMISSION','Host profile is outside authorized trial roster')
  from .service import dispatch
  pre=dispatch(state,'owner','host_preflight',{'task_id':task['object_id'],'task_revision':task['revision'],'provider_profile_id':route['object_id'],'preflight_evidence_id':args['preflight_evidence_id'],'account':account})
  profile=pre['profile'];price=profile['payload']['pricing']
  if profile['revision']!=route['revision'] or profile['payload']['host']!=actor or profile['payload'].get('endpoint_kind')!='official_deepseek':
   raise Fault('ROUTE_PERMISSION','current exact official Host profile required')
  size=args['input_upper_bound_bytes'];output=args['max_output_tokens']
  if type(size)!=int or not 1<=size<=262144 or type(output)!=int or not 1<=output<=trial.get('max_output_tokens',4096):
   raise Fault('LIMIT','bounded native request and output required')
  digest=args['dispatch_hash']
  if not isinstance(digest,str) or len(digest)!=64 or any(x not in '0123456789abcdef' for x in digest):raise Fault('INPUT','native dispatch hash required')
  if price.get('currency')!='CNY' or not price.get('verified_at'):raise Fault('PRICE_UNKNOWN','timestamped CNY pricing required')
  rates=[price.get(k) for k in ['worst_input_micro_per_token','worst_output_micro_per_token','worst_cache_micro_per_token']]
  if any(type(v) not in [int,float] or not math.isfinite(v) or v<0 for v in rates) or min(rates[:2])<=0:raise Fault('PRICE_UNKNOWN','positive finite cost bounds required')
  amount=max(1,math.ceil((size+8192)*rates[0]+output*rates[1]))
  rows=c.execute('SELECT * FROM budget_reservations WHERE account=?',(account,)).fetchall()
  trial_rows=[(r,json.loads(r['receipt'])) for r in rows if json.loads(r['receipt']).get('trial_id')==trial['trial_id']]
  if any(r['state']=='unknown' for r,_ in trial_rows):raise Fault('OUTCOME_UNKNOWN','trial has an unresolved request; no automatic continuation')
  if any(r['state']=='reserved' and x.get('actor')==actor for r,x in trial_rows):raise Fault('OUTCOME_UNKNOWN','Host has an outstanding reservation; reconcile before another dispatch')
  old=next((r for r,x in trial_rows if r['id']==oid),None)
  if old:raise Fault('OUTCOME_UNKNOWN','reservation identity already used; never redispatch')
  if len(trial_rows)>=trial.get('max_requests',24):raise Fault('LIMIT','persistent aggregate request count reached')
  charged=sum((r['actual_micro'] or 0) if r['state']=='settled' else r['amount_micro'] if r['state'] in ['reserved','unknown'] else 0 for r,_ in trial_rows)
  if amount+charged>cap:raise Fault('BUDGET_EXCEEDED','atomic aggregate trial cap exceeded')
  account_row=c.execute('SELECT * FROM budget_accounts WHERE id=?',(account,)).fetchone()
  if not account_row:raise Fault('BUDGET_MISSING','explicit parent account required')
  locked=sum(r['amount_micro'] for r in rows if r['state'] in ['reserved','unknown'])
  if amount+account_row['spent_micro']+locked>account_row['limit_micro']:raise Fault('BUDGET_EXCEEDED','parent total limit exceeded')
  receipt={'reserved_at':now(),'usage':'not_called','trial_id':trial['trial_id'],'trial_cap_micro':cap,'actor':actor,'native_session_id':args['native_session_id'],'task_id':task['object_id'],'task_revision':task['revision'],'profile':route,'preflight_evidence_id':args['preflight_evidence_id'],'dispatch_hash':digest,'input_upper_bound_bytes':size,'max_output_tokens':output,'price':price,'basis':'native payload/context bytes plus8192 framing, capped total output, verified peak cost bound'}
  c.execute('INSERT INTO budget_reservations VALUES(?,?,?,?,?,?)',(oid,account,amount,'reserved',None,canonical(receipt)))
 return {'ok':True,'reservation_id':oid,'amount_micro':amount,'trial_id':trial['trial_id'],'remaining_trial_micro':cap-charged-amount,'price':price}

def settle(state,actor,args):
 if actor not in ['pi','dsh','owner']:raise Fault('PERMISSION','trial Host principal required')
 rid=args['reservation_id'];uuid_ok(rid)
 with state.db() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM budget_reservations WHERE id=?',(rid,)).fetchone()
  if not r:raise Fault('NOT_FOUND','reservation missing')
  receipt=json.loads(r['receipt'])
  if not receipt.get('trial_id') or actor not in ['owner',receipt.get('actor')]:raise Fault('PERMISSION','own trial reservation only')
  usage=args.get('usage');known=isinstance(usage,dict) and args.get('outcome')=='completed'
  if known:
   for k in ['inputTokens','outputTokens','cacheReadTokens','cacheWriteTokens']:
    if type(usage.get(k,0))!=int or usage.get(k,0)<0:raise Fault('USAGE_UNKNOWN','nonnegative integer usage required')
   if 'inputTokens' not in usage or 'outputTokens' not in usage:raise Fault('USAGE_UNKNOWN','explicit input/output usage required')
   price=receipt['price'];actual=math.ceil((usage['inputTokens']+usage.get('cacheWriteTokens',0))*price['worst_input_micro_per_token']+usage.get('cacheReadTokens',0)*price['worst_cache_micro_per_token']+usage['outputTokens']*price['worst_output_micro_per_token'])
   if actual>r['amount_micro']:raise Fault('COST_BOUND_BREACH','retain reservation for reconciliation')
  else:actual=None
  status='settled' if known else 'unknown'
  if r['state']=='settled':
   if receipt.get('usage')!=usage or r['actual_micro']!=actual:raise Fault('OPERATION_CONFLICT','settlement changed')
   return {'ok':True,'state':'settled','duplicate':True,'actual_micro':actual}
  if r['state']=='unknown' and actor!='owner':raise Fault('OUTCOME_UNKNOWN','Owner reconciliation required; no Host retry')
  if r['state']=='released':raise Fault('OPERATION_CONFLICT','released reservation cannot be billed by Host')
  if known:c.execute('UPDATE budget_accounts SET spent_micro=spent_micro+?,revision=revision+1 WHERE id=?',(actual,r['account']))
  receipt.update(usage=usage or 'unknown',actual_micro=actual,settled_at=now(),charge_kind='usage-based peak-price upper bound; invoice unknown')
  c.execute('UPDATE budget_reservations SET state=?,actual_micro=?,receipt=? WHERE id=?',(status,actual,canonical(receipt),rid))
 return {'ok':True,'reservation_id':rid,'state':status,'actual_micro':actual,'account':r['account']}
