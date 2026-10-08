"""Finite executable guard contracts. Textual lessons never become executable code."""
from pathlib import Path
from .util import Fault,file_hash,sha
CONTRACTS={
 'source_quotes':dict(property='learning_source_integrity',scope='source-bound machine-readable quote assertions',excludes='domain truth, unread images, semantic entailment'),
 'registered_validation':dict(property='learning_checked_delivery',scope='UACF project delivery and acceptance',excludes='unmapped host turns and arbitrary host tools'),
 'protected_assets':dict(property='learning_preserved_baseline',scope='explicitly declared protected paths at registered stage boundaries',excludes='undeclared files and arbitrary host writes'),
 'settled_receipts':dict(property='learning_no_unknown_replay',scope='shared update dispatcher',excludes='unregistered external calls'),
 'required_work_steps':dict(property='learning_no_missing_work_step',scope='explicit Task required_work_steps at registered delivery',excludes='undeclared semantic requirements and arbitrary host tools')}
def quotes(strings,claims):
 for claim in claims:
  refs=claim.get('refs',[])
  if not refs or any(not isinstance(r.get('quote'),str) or not r['quote'] or not any(r['quote'] in x for x in strings) for r in refs):raise Fault('SOURCE_QUOTE_INVALID','source-bound assertion lacks exact literal quotation')
 return True
def protected(task):
 roots=[Path(x).resolve() for values in task['payload'].get('artifact_capture_roots',{}).values() for x in values]
 entries=task['payload'].get('protected_paths',[])
 for entry in entries:
  path=Path(entry['path']).resolve()
  if not roots or not any(path.is_relative_to(root) for root in roots):raise Fault('PERMISSION','protected path must be explicitly within Task workspace')
  if not path.is_file() or file_hash(path)!=entry['sha256']:raise Fault('REGRESSION','protected baseline changed; do not deliver or auto overwrite it')
 return True
def delivery(state,task):
 from .retry_guard import check as retry_check
 retry_check(task)
 from .command_ledger import delivery as command_delivery
 command_delivery(task)
 protected(task)
 work_steps(state,task)
 required=task['payload'].get('required_properties',[]);environment=task['payload'].get('delivery_environment_hash')
 if not required or not isinstance(environment,str) or len(environment)!=64:raise Fault('VALIDATION_REQUIRED','delivery needs a frozen environment and registered checks; self-report is insufficient')
 from .state import stale
 with state.db() as c:
  for prop in required:
   row=c.execute('select id,result from validations where task_id=? and task_revision=? and property=? and environment_hash=? order by rowid desc limit 1',(task['object_id'],task['revision'],prop,environment)).fetchone()
   if not row or row['result']!='pass' or stale(state,state.get(row['id'],'owner')):raise Fault('VALIDATION_REQUIRED','current registered pass required: '+prop)
 return True
def work_steps(state,task):
 steps=task['payload'].get('required_work_steps',[])
 if not steps:return True
 if not isinstance(steps,list) or any(not isinstance(s,str) or not s or len(s)>80 for s in steps) or len(set(steps))!=len(steps):raise Fault('WORK_STEP_CONTRACT','explicit unique work step IDs required')
 properties=task['payload'].get('required_properties',[]);env=task['payload'].get('delivery_environment_hash')
 if any('work_step/'+step not in properties for step in steps) or not isinstance(env,str) or len(env)!=64:raise Fault('WORK_STEP_CONTRACT','each step needs an explicit registered validation obligation and frozen environment')
 with state.db() as c:
  for step in steps:
   row=c.execute('select id,result from validations where task_id=? and task_revision=? and property=? and environment_hash=? order by rowid desc limit 1',(task['object_id'],task['revision'],'work_step/'+step,env)).fetchone()
   if not row or row['result']!='pass':raise Fault('WORK_STEP_MISSING','required work step lacks registered pass: '+step)
   from .state import stale
   if stale(state,state.get(row['id'],'owner')):raise Fault('WORK_STEP_MISSING','work step evidence stale: '+step)
 return True
def fixture_checks():
 """Registered positive/negative tests of guard behavior, without reading production data."""
 import tempfile
 checks={}
 checks['literal_positive']=quotes(['verified source'],[{'refs':[{'quote':'source'}]}])
 try:quotes(['verified source'],[{'refs':[{'quote':'invented'}]}]);checks['invented_quote_rejected']=False
 except Fault:checks['invented_quote_rejected']=True
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)/'baseline';path.write_bytes(b'known correct')
  task={'payload':{'artifact_capture_roots':{'codex':[tmp]},'protected_paths':[dict(path=str(path),sha256=file_hash(path))]}}
  checks['protected_positive']=protected(task);path.write_bytes(b'accidental regression')
  try:protected(task);checks['regression_rejected']=False
  except Fault as error:checks['regression_rejected']=error.code=='REGRESSION'
 class MissingValidation:
  pass
 try:delivery(MissingValidation(),{'payload':{'required_properties':[]}});checks['unchecked_delivery_rejected']=False
 except Fault:checks['unchecked_delivery_rejected']=True
 try:work_steps(None,{'payload':{'required_work_steps':['answer_user_questions'],'required_properties':[]}});checks['undeclared_step_validation_rejected']=False
 except Fault as error:checks['undeclared_step_validation_rejected']=error.code=='WORK_STEP_CONTRACT'
 return checks
