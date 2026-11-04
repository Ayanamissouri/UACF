"""Finite registered checks for action admission and archive projection boundaries."""
import json,os,platform,subprocess,sys
from pathlib import Path
from .util import file_hash,sha,Fault

MODULES=['uacf/action_classifier.py','uacf/action_guard.py','uacf/consistency.py','uacf/coding_workers.py','uacf/host_work.py','uacf/state.py','uacf/service.py','uacf/unified_assets.py','uacf/mcp.py','uacf/action_verification.py','uacf/work_verification.py']
TESTS=['tests.test_action_guard','tests.test_host_work','tests.test_host_work_hooks','tests.test_consistency_workers','tests.test_unified_assets','tests.test_transport']

def environment(state,task):
 from importlib.util import find_spec
 if find_spec(__package__+'.storage_layout'):
  from .storage_layout import task_paths
  work=Path(task_paths(state,task)['work'])
 else:
  root=task['payload'].get('output_contract',{}).get('project_root')
  if not root:raise Fault('OUTPUT_CONTRACT_REQUIRED','Owner-selected project root required')
  work=Path(root).resolve()/'.uacf'/'work'/task['object_id']
 if task['payload'].get('action_acceptance',{}).get('work_dir')!=str(work):raise Fault('OUTPUT_CONTRACT_REQUIRED','action acceptance must use the current allocated work directory')
 files=[state.root/'repo'/p for p in MODULES]
 files += [state.root/'repo/tests'/(p.split('.')[-1]+'.py') for p in TESTS]
 files += [work/n for n in ['micro-before.json','micro-after.json','historical-incident-source.json']]
 loaded=json.loads((state.data/'service-identity.json').read_text('utf8'))
 body=dict(files={str(p):file_hash(p) if p.is_file() else None for p in files},loaded={p:loaded['loaded_files'].get(p) for p in MODULES},scope='code identity, isolated regression behavior and declared small-command receipts; no general model effectiveness claim')
 return dict(ok=True,environment=body,environment_hash=sha(body))

def check(state,task,checks,details):
 work=Path(task['payload']['action_acceptance']['work_dir']);repo=state.root/'repo'
 loaded=json.loads((state.data/'service-identity.json').read_text('utf8'))
 checks['loaded_action_modules_match_source']=all(loaded['loaded_files'].get(p)==file_hash(repo/p) for p in MODULES)
 env=dict(os.environ,PYTHONPATH=str(repo))
 run=subprocess.run([sys.executable,'-X','utf8','-m','unittest',*TESTS,'-q'],cwd=repo,env=env,capture_output=True,text=True,encoding='utf8',timeout=90)
 checks['action_boundary_regressions']=run.returncode==0
 details['tests']=dict(exit_code=run.returncode,output=(run.stdout+run.stderr)[-4500:])
 before=json.loads((work/'micro-before.json').read_text('utf8'));after=json.loads((work/'micro-after.json').read_text('utf8'))
 source=json.loads((work/'historical-incident-source.json').read_text('utf8'))
 checks['real_historical_source']=before.get('source_event_id')==source.get('locator',{}).get('event_id') and before['question'] in source['body']
 checks['bounded_distinct_commands']=before.get('models_called')==after.get('models_called')==0 and before['proposed_tool']!=after['proposed_tool']
 checks['posttest_denied_and_file_preserved']=after.get('allowed') is False and after.get('target_unchanged') is True and after.get('read_recovery_allowed') is True
 details['comparison_scope']='Deterministic action-boundary replay with disposable files. Native hook diagnostic is explicitly identified in its receipt; no model-response A/B or universal host callback claim.'
 details['before']=dict(uacf_allowed=before['uacf_before']['allowed'],sts_outcome=before['sts']['decision']['outcome'])
 details['after']=after
 if checks and all(checks.values()):
  deployment=json.loads((state.data/'deployment.json').read_text('utf8'))
  details['capability_proofs']=[dict(machine=platform.node(),host='uacf',host_version='action-admission-20261104',profile='local-service',capability='action-control',source_identity=deployment['identity'],native_session_id=None,stages=['generated','installed','loaded','called','verified'],scope='Registered finite action-admission verifier: loaded code identity, isolated regressions and two bounded command receipts; no general model or automatic host-hook guarantee.')]
