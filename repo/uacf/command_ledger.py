"""Revisioned task instructions, kept separate from optional retrieved knowledge.

The current host interprets speech. This module checks provenance and transitions;
it never claims a lexical or hash check understands metaphor or user intent.
"""
from .util import Fault,canonical,sha,now
from .state import request,stale
from .fabric import owner,vector

STATES={'pending','in_progress','satisfied','unresolved','superseded','cancelled'}
KINDS={'instruction','correction','quoted_ai','discussion','ambiguous','duplicate'}

def summary(state,actor,args):
 task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract':raise Fault('INPUT','Task required')
 rows=task['payload'].get('command_ledger',[])
 return dict(ok=True,task_ref=vector(task),entries=rows,revision=task['revision'],unresolved=sum(x['state'] in ['pending','in_progress','unresolved'] for x in rows),mandatory=True,interpretation='host semantic judgment with quoted basis; no automatic NLP or hash semantics',scope='registered Task context and delivery; arbitrary host tools remain outside admission')

def update(state,actor,args):
 owner(actor);task=state.get(args['task_id'],actor)
 if task['revision']!=args['expected_revision']:raise Fault('REVISION_CONFLICT','read current Task before appending instructions')
 rows=[dict(x) for x in task['payload'].get('command_ledger',[])];bykey={x['key']:x for x in rows}
 entries=args.get('entries',[])
 if not isinstance(entries,list) or not 1<=len(entries)<=30:raise Fault('INPUT','bounded instruction group required')
 for e in entries:
  key=e.get('key');text=e.get('text');kind=e.get('kind','instruction');status=e.get('state','pending')
  if not isinstance(key,str) or not key or len(key)>80 or not isinstance(text,str) or not 0<len(text)<=1200 or kind not in KINDS or status not in STATES:raise Fault('INPUT','explicit bounded instruction, interpretation and lifecycle required')
  ref=e['source_ref'];source=state.get(ref['object_id'],actor)
  if vector(source)!=ref:raise Fault('SOURCE_CHANGED','instruction source revision changed')
  quote=e.get('source_quote','');raw=source['payload'].get('text')
  if not isinstance(raw,str):raw=canonical(source['payload'])
  if not quote or quote not in raw or not e.get('interpretation_basis'):raise Fault('COMMAND_BASIS','exact quoted basis and semantic explanation required')
  direct=source['object_type']=='Message' and source['payload'].get('source_kind')=='direct_user' and source['payload'].get('current') is True
  actionable=kind in ['instruction','correction']
  if actionable and not direct:raise Fault('COMMAND_AUTHORITY','historical, tool or AI text cannot authorize a live command')
  if actionable and not e.get('explicit_attestation'):raise Fault('COMMAND_AUTHORITY','current human directive attestation required')
  if not actionable and status in ['in_progress','satisfied']:raise Fault('COMMAND_AUTHORITY','ambiguous/quoted/discussion entries stay non-executable')
  if key in bykey:
   old=bykey[key]
   if text!=old['text'] and kind!='correction':raise Fault('COMMAND_REPLACE','changed requirement needs explicit correction; append does not replace earlier work')
   if status in ['superseded','cancelled'] and kind!='correction':raise Fault('COMMAND_REPLACE','only an explicit current correction cancels prior work')
   if text!=old['text']:e=dict(e,previous_text=old['text'],previous_source_ref=old['source_ref'])
  if kind=='duplicate':
   if e.get('duplicate_of') not in bykey:raise Fault('COMMAND_DUPLICATE','explicit previously reviewed target required; text equality is not semantic equivalence')
  if status=='satisfied':
   evidence=e.get('evidence_refs',[])
   if not evidence:raise Fault('COMMAND_EVIDENCE','completed instruction needs result evidence, not a claim')
   for r in evidence:
    actual=state.get(r['object_id'],actor)
    if vector(actual)!=r or stale(state,actual):raise Fault('COMMAND_EVIDENCE','result evidence changed or stale')
  item=dict(e,key=key,text=text,kind=kind,state=status,actionable=actionable,source_ref=ref,recorded_at=now(),semantic_judgment='current host; independent semantic truth not established')
  if key in bykey:rows[rows.index(bykey[key])]=item
  else:rows.append(item)
  bykey[key]=item
 if len(rows)>100:raise Fault('COMMAND_OVERFLOW','more than100 explicit entries requires bounded Task split; never silently drop earlier commands')
 task['payload']['command_ledger']=rows
 obj={k:task[k] for k in ['object_id','object_type','status','visibility','payload']}
 return dict(ok=True,task_ref=vector(state.put(request(obj,task['revision']),actor)['object']),entries=len(rows),older_commands_preserved=True)

def capsule(task):
 return [dict(key=x['key'],text=x['text'],kind=x['kind'],state=x['state'],actionable=x['actionable'],source_ref=x['source_ref'],interpretation_basis=x['interpretation_basis'],duplicate_of=x.get('duplicate_of')) for x in task['payload'].get('command_ledger',[]) if x['state'] not in ['superseded','cancelled']]

def delivery(task):
 remaining=[x['key'] for x in task['payload'].get('command_ledger',[]) if x.get('actionable') and x['state']!='satisfied']
 if remaining:raise Fault('COMMAND_INCOMPLETE','undelivered explicit instructions: '+', '.join(remaining))

def dispatch(state,actor,action,args):return (summary if action=='command_status' else update)(state,actor,args)
