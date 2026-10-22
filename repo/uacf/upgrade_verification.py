"""Finite code and archive-preservation checks for the organizing upgrade."""
import json,os,platform,subprocess,sys
from pathlib import Path
from .util import Fault,file_hash,sha

MODULES=['uacf/command_ledger.py','uacf/host_work.py','uacf/project_workflow.py','uacf/learning_guards.py','uacf/state.py','uacf/service.py','uacf/mcp.py','uacf/task_views.py','uacf/capabilities.py','uacf/candidate_guidance.py','uacf/learning_use.py','uacf/upgrade_verification.py','uacf/work_verification.py']
FILES=MODULES+['tests/test_organizing_upgrade.py','tests/pi_installed_contract.mjs','adapters/pi/continuity.mjs','adapters/pi/installed.mjs','apps/control-surface/host-work.js','apps/control-surface/auth.js']
TESTS=['tests.test_organizing_upgrade','tests.test_command_ledger','tests.test_project_workflow','tests.test_host_work','tests.test_host_work_hooks','tests.test_learning_semantic','tests.test_storage_layout','tests.test_work_verification','tests.test_transport']

def environment(state,task):
 config=task['payload'].get('upgrade_acceptance')
 if not config:raise Fault('INPUT','explicit upgrade acceptance contract required')
 repo=state.root/'repo';paths=[repo/p for p in FILES]
 paths += [repo/'tests'/(name.split('.')[-1]+'.py') for name in TESTS]
 paths+=list((repo/'adapters/skills/uacf-continuity').rglob('*.md'))
 paths += [Path(config['canonical_baseline'])]+[Path(p) for p in config.get('installed_skill_files',[])]+[Path(p) for p in config.get('native_receipts',[])]
 files={str(p):file_hash(p) if p.is_file() else None for p in paths}
 loaded=json.loads((state.data/'service-identity.json').read_text(encoding='utf8'))
 current={p:loaded['loaded_files'].get(p) for p in MODULES}
 result={'files':files,'loaded_modules':current,'scope':'Scoped upgrade modules, shared skill projections, zero-model diagnostics and immutable baseline; not full historical asset interpretation.'}
 if task['payload'].get('storage_acceptance'):
  from .storage_verification import environment as storage_environment
  result['prior_storage_environment']=storage_environment(state,task)['environment_hash']
 return {'ok':True,'environment_hash':sha(result),'environment':result}

def check(state,task,checks,details):
 config=task['payload']['upgrade_acceptance'];repo=state.root/'repo'
 loaded=json.loads((state.data/'service-identity.json').read_text(encoding='utf8'))
 checks['loaded_upgrade_modules_match_source']=all(loaded['loaded_files'].get(p)==file_hash(repo/p) for p in MODULES)
 baseline=json.loads(Path(config['canonical_baseline']).read_text(encoding='utf8'))['rows'];bad=[]
 with state.db() as c:
  for item in baseline:
   row=c.execute('select envelope from object_revisions where object_id=? and revision=?',(item['object_id'],item['revision'])).fetchone()
   if not row or sha(row[0])!=item['sha256']:bad.append([item['object_id'],item['revision']])
 checks['prior_immutable_revisions_preserved']=not bad
 details['canonical_preservation']={'existing_revisions_checked':len(baseline),'changed_or_missing':bad[:20]}
 skill=repo/'adapters/skills/uacf-continuity'
 skill_files={p.relative_to(skill).as_posix():file_hash(p) for p in skill.rglob('*.md')}
 expected=config.get('skill_projection_roots',[])
 checks['shared_skill_projections_match']=bool(expected) and all((Path(root)/name).is_file() and file_hash(Path(root)/name)==digest for root in expected for name,digest in skill_files.items())
 env=dict(os.environ,PYTHONPATH=str(repo))
 result=subprocess.run([sys.executable,'-X','utf8','-m','unittest',*TESTS,'-q'],cwd=repo,env=env,capture_output=True,text=True,encoding='utf8',timeout=90)
 checks['focused_upgrade_regressions']=result.returncode==0
 details['regressions']={'exit_code':result.returncode,'output':(result.stdout+result.stderr)[-4500:],'scope':'Isolated temporary fixture states, no production archive reprocessing or model requests.'}
 receipts=[]
 for p in config.get('native_receipts',[]):
  value=json.loads(Path(p).read_text(encoding='utf8'));receipts.append({'path':p,'ok':value.get('ok') is True,'model_calls':value.get('model_calls')})
 checks['zero_model_diagnostics']=bool(receipts) and all(x['ok'] and x['model_calls']==0 for x in receipts)
 details['native_receipts']=receipts
 details['scope']='Mechanical behavior, loaded code identity, shared files and preserved prior revision envelopes; no claim that all semantic misunderstandings are solved.'
 if checks and all(checks.values()):
  deployment=json.loads((state.data/'deployment.json').read_text(encoding='utf8'))
  details['capability_proofs']=[dict(machine=platform.node(),host='uacf',host_version='organizing-upgrade-20261022',profile='local-service',capability='task-workflow',source_identity=deployment['identity'],native_session_id=None,stages=['installed','loaded','called','verified'],scope='Registered finite organizing-upgrade verifier: code identity, isolated regressions, shared skill bytes and prior revision preservation; no semantic-quality guarantee.')]
