"""Registered finite mechanical checks for default Host work and study bundles.

Never grades scientific truth, learning effectiveness, or unavailable native Hosts.
No provider request, raw credential return, or model action replay.
"""
import json,os,subprocess,sys,urllib.request
from pathlib import Path
from .util import Fault,canonical,file_hash,sha,now,atomic
from .state import object_new,request
from .fabric import vector
from .host_work import policy

TESTS=['tests.test_host_work','tests.test_host_work_hooks','tests.test_ecosystem','tests.test_project_workflow','tests.test_generic_budget_authorization','tests.test_command_ledger','tests.test_service_lifecycle','tests.test_archive_trigger','tests.test_work_verification']
PROPERTIES={'host_default_work_configured','study_bundle_source_integrity','unified_assets_source_integrity'}

def environment(state):
 repo=state.root/'repo';home=Path.home()
 paths=[repo/'uacf'/n for n in ['host_work.py','state.py','fabric.py','service.py','work_verification.py']]
 paths += [repo/'tests'/(n.split('.')[-1]+'.py') for n in TESTS]
 paths += [repo/'adapters'/n for n in ['codex/hook.py','claude_code/hook.py','dsh/index.js','dsh/continuity.js','pi/installed.mjs','pi/continuity.mjs']]
 paths += [repo/'ops/host_work_pi_probe.mjs',home/'.codex/AGENTS.md',home/'.codex/hooks.json',home/'.claude/settings.json',home/'.claude/CLAUDE.md',home/'.claude.json',home/'.pi/agent/settings.json',(Path(os.environ.get('UACF_PI_AGENT_HOME', str(Path.home()/'.pi/agent')))/'settings.json'),Path(os.environ.get('ProgramData','C:/ProgramData'))/'OpenAI/Codex/requirements.toml']
 paths += [repo/n for n in ['uacf/unified_assets.py','uacf/native_watch.py','uacf/learning_lifecycle.py','uacf/mcp.py','adapters/codex/public_read.py','apps/control-surface/catalog.js','ops/capture_native_history.py','tests/test_unified_assets.py']]
 p=policy(state);files={str(x):file_hash(x) if x.is_file() else None for x in paths}
 result=dict(files=files,policy_ref=p['ref'] if p else None,scope='loaded code/config identity, not model or domain acceptance')
 return dict(ok=True,environment_hash=sha(result),environment=result)

def _host(state,args,checks,details):
 root=state.root;repo=root/'repo';p=policy(state)
 checks['canonical_default_policy']=bool(p and p['config']['default_mode']=='uacf' and p['config']['wait_for_answer'] is False)
 loaded=json.loads((state.data/'service-identity.json').read_text())
 names=['uacf/host_work.py','uacf/state.py','uacf/fabric.py','uacf/service.py','uacf/work_verification.py']
 checks['loaded_core_matches_tested_source']=all(loaded['loaded_files'].get(n)==file_hash(repo/n) for n in names)
 env=dict(os.environ,PYTHONPATH=str(repo))
 result=subprocess.run([sys.executable,'-X','utf8','-m','unittest',*TESTS,'-q'],cwd=repo,env=env,capture_output=True,text=True,encoding='utf8',timeout=60)
 checks['registered_boundary_tests']=result.returncode==0;details['boundary_tests']={'exit_code':result.returncode,'output':(result.stdout+result.stderr)[-3500:]}
 for host,file in [('pi',(Path(os.environ.get('UACF_PI_AGENT_HOME', str(Path.home()/'.pi/agent')))/'settings.json')),('claude_code',Path.home()/'.claude/settings.json')]:
  cfg=json.loads(file.read_text(encoding='utf8'))
  checks[host+'_configured']=str(repo/'adapters/pi/installed.mjs') in cfg.get('extensions',[]) if host=='pi' else all(event in cfg.get('hooks',{}) for event in ['SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','Stop','SessionEnd'])
 # Native binary reports managed policy; this is discovery, not a fabricated
 # callback from the current Desktop thread.
 native=subprocess.run([sys.executable,'-X','utf8',str(repo/'ops/probe_codex_hooks.py')],cwd=repo,capture_output=True,text=True,encoding='utf8',timeout=45)
 rows=[json.loads(line) for line in native.stdout.splitlines() if line.startswith('{')]
 checks['codex_managed_hooks']=native.returncode==0 and len(rows)==7 and all(x.get('isManaged') is True and x.get('enabled') is True and x.get('trustStatus')=='managed' for x in rows)
 details['codex_native_discovery']=rows
 if args.get('run_native') is not True:raise Fault('INPUT','explicit zero-model native diagnostic authorization required')
 auth=json.loads((state.data/'auth.json').read_text())
 req=urllib.request.Request(state.config['dsh_url']+'/uacf/v1/work-probe',data=b'{}',headers={'Authorization':'Bearer '+auth['owner'],'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as r:dsh=json.load(r)
 plugin=dsh.get('plugin',{})
 checks['dsh_native_gate']=dsh.get('ok') is True and dsh.get('registered') is True and dsh.get('model_calls')==0 and dsh.get('turn_start_events')==0
 checks['dsh_loaded_identity']=plugin.get('loaded_sha256')==file_hash(repo/'adapters/dsh/index.js') and all(plugin.get('loaded_modules',{}).get(n)==file_hash(repo/'adapters/dsh'/n) for n in ['continuity.js','experiment.js','project_trial.js'])
 details['dsh']=dsh
 node='C:/Program Files/nodejs/node.exe'
 pi=subprocess.run([node,str(repo/'ops/host_work_pi_probe.mjs'),str(root)],cwd=repo,capture_output=True,text=True,encoding='utf8',timeout=60)
 details['pi_diagnostic_process']={'exit_code':pi.returncode,'output':(pi.stdout+pi.stderr)[-3500:]}
 receipt=root/'artifacts/host-governance-rewrite-20261019/pi-native-receipt.json'
 data=json.loads(receipt.read_text()) if pi.returncode==0 and receipt.exists() else {}
 checks['pi_native_gate']=pi.returncode==0 and data.get('ok') is True and data.get('model_calls')==0 and not data.get('extension_errors')
 details['pi']=data
 details['native_limitations']=['Codex native discovery proves managed configuration; actual current-thread callback coverage is reported separately.','Pi and DSH use deterministic public native SDK/tool diagnostics, not model-generated turns.','Claude Code is configured for future startup; no installed native CLI session is asserted.','No OS/network sandbox or learning-effectiveness guarantee.']

def _study(state,task,checks,details):
 folder=(state.root/'deliverables/study-priority-20261019').resolve()
 acceptance=task['payload'].get('study_acceptance')
 if not acceptance:raise Fault('INPUT','explicit frozen study source counts/artifact refs required')
 read=lambda name:json.loads((folder/name).read_text(encoding='utf8'))
 reg=read('canonical-registration.json');rows=read('conversation-register.json');included=[x for x in rows if x['scope'] in ['core','extended']]
 checks['gpt_count_identity']=len(included)==acceptance['gpt_count']==len({x['native_id'] for x in included})
 keys={f'gpt-{x["index"]:04}' for x in included}
 checks['canonical_gpt_coverage']=keys=={x['key'] for x in reg['cards'] if x['key'].startswith('gpt-')}
 checks['all_canonical_sources']=len(reg['cards'])==acceptance['canonical_source_count']==len({x['key'] for x in reg['cards']})
 nodes={f'gpt-{r["index"]:04}':{n['node']:n for n in read(f'packets/{r["index"]:04}.json')['nodes']} for r in rows}
 for s in read('dsh-selected-snapshots.json'):nodes['dsh-'+s['session_id']]={n['node']:n for n in s['nodes']}
 quotes=0
 for row in rows:
  source=nodes[f'gpt-{row["index"]:04}']
  for kind in ['activities','questions','preferences','resources']:
   for item in row[kind]:
    if not item.get('refs'):raise Fault('SOURCE_QUOTE_INVALID','missing original source ref')
    for e in item['refs']:
     if e['quote'] not in source[e['node']]['text']:raise Fault('SOURCE_QUOTE_INVALID','quote changed')
     quotes+=1
    if kind in ['questions','preferences'] and not any(source[e['node']]['role']=='user' for e in item['refs']):raise Fault('SOURCE_QUOTE_INVALID','user feedback requires user source')
 synthesis=read('learning-synthesis.json');sq=0
 for values in synthesis.values():
  if not isinstance(values,list):continue
  for item in values:
   if not isinstance(item,dict):continue
   for e in item.get('evidence',[]):
    if e['quote'] not in nodes[e['source_id']][e['node']]['text']:raise Fault('SOURCE_QUOTE_INVALID','synthesis quote changed')
    sq+=1
 checks['literal_quotes_and_roles']=True
 for name,ref in acceptance['artifacts'].items():
  obj=state.get(ref['object_id'],'owner')
  if vector(obj)!=ref or obj['payload']['sha256']!=file_hash(folder/name):raise Fault('HASH','study delivery file differs from frozen canonical Artifact: '+name)
  result=state.fetch_blob('owner',ref['object_id'],ref['revision'],8388608)
  if result['blob_hash']!=obj['payload']['sha256']:raise Fault('HASH','canonical study blob mismatch')
 checks['frozen_artifacts']=True
 validation=read('validation.json');spans={}
 for path in (folder/'inputs').glob('analysis-*.json'):
  part=json.loads(path.read_text(encoding='utf8'));body=json.loads(part['prompt'].rsplit('\n',1)[-1]);index=int(path.name.split('-')[1])
  for n in body['nodes']:
   if n['end']-n['start']!=len(n['text']):raise Fault('SOURCE_COVERAGE','input span length mismatch')
   spans.setdefault((index,n['node']),[]).append((n['start'],n['end']))
 covered=chars=0
 for item in read('analysis-manifest.json'):
  for node in nodes[f'gpt-{item["index"]:04}'].values():
   if not node['text']:continue
   pos=0
   for a,b in sorted(spans[item['index'],node['node']]):
    if a!=pos:raise Fault('SOURCE_COVERAGE','gap or duplicate public span')
    pos=b
   if pos!=len(node['text']):raise Fault('SOURCE_COVERAGE','public node not fully covered')
   covered+=1;chars+=pos
 checks['full_public_text_coverage']=validation.get('ok') is True and len(read('analysis-manifest.json'))==acceptance['read_conversations'] and chars==validation['full_public_text_coverage']['chars']
 details['recomputed_public_coverage']={'nodes':covered,'chars':chars,'lossless':True}
 checks['old_handoff_preserved']=read('prior-progress.json')['handoff']==json.loads((state.root/'deliverables/e7-current-handoff.json').read_text(encoding='utf8'))
 checks['settled_model_outcomes']=read('statistics.json')['api_unresolved']==0
 details.update(gpt_count=len(included),canonical_sources=len(reg['cards']),literal_quotes=quotes,synthesis_quotes=sq,coverage='identity, file/blob integrity, literal quotation/user-role checks, observed public-span coverage and settled receipts; not semantic entailment, scientific truth or measured learning effect')

def _unified(state,task,checks,details):
 from .unified_assets import refresh,search
 result=refresh(state);sources={r['host']:r for r in result['sources']};native=result['native_inventory'] or {}
 checks['legacy_export_retained']=sources.get('gpt_export',{}).get('conversations')==2531
 checks['native_history_registered']=native.get('codex',{}).get('known_sessions',0)>=43 and native.get('dsh',{}).get('known_sessions',0)>=103 and not native['codex']['errors'] and not native['dsh']['errors']
 checks['cross_source_search']=search(state,'owner',{'query':'思考走订阅','host':'dsh'})['total']>0 and search(state,'owner',{'query':'不同流程用不同的AI','host':'codex'})['total']>0
 watch=json.loads((state.data/'native-watch-status.json').read_text())
 sid=task['payload'].get('verification_native_session_id')
 current=next((r for r in watch.get('results',[]) if r.get('session_id')==sid),{})
 checks['managed_public_observer_actual_read']=current.get('ok') is True and current.get('model_turns_started')==0 and bool(current.get('turns'))
 checks['capture_boundary_declared']=task['payload'].get('learning_capture_policy',{}).get('mode')=='adaptive'
 repo=state.root/'repo';env=dict(os.environ,PYTHONPATH=str(repo));r=subprocess.run([sys.executable,'-X','utf8','-m','unittest','tests.test_unified_assets','tests.test_checkpoint_boundary','tests.test_archive_trigger','tests.test_catalog','tests.test_learning_task_transition','tests.test_host_work','tests.test_codex_public_read','-q'],cwd=repo,env=env,capture_output=True,text=True,encoding='utf8',timeout=90)
 checks['source_acl_and_trigger_tests']=r.returncode==0
 details.update(source_inventory=result,observer=current,boundary_tests={'exit_code':r.returncode,'output':(r.stdout+r.stderr)[-1200:]},scope='public source identity, bounded search, registered ACL/trigger tests and actual zero-model polling; no private reasoning, semantic project acceptance or live-hook claim')

def dispatch(state,actor,action,args,operation_id=None):
 if actor!='owner':raise Fault('PERMISSION','Owner dispatches registered work verification')
 if action=='work_environment':return environment(state)
 task=state.get(args['task_id'],actor);prop=args.get('property')
 if task['revision']!=args.get('task_revision'):raise Fault('REVISION_CONFLICT','verify exact current Task')
 if prop not in PROPERTIES or prop not in task['payload']['required_properties']:raise Fault('INPUT','explicit registered work property required')
 before=environment(state)
 if task['payload'].get('delivery_environment_hash')!=before['environment_hash']:raise Fault('ENVIRONMENT_CHANGED','freeze this current environment before verification')
 checks={};details={'at':now(),'property':prop,'model_calls':0}
 try:
  (_host(state,args,checks,details) if prop=='host_default_work_configured' else _unified(state,task,checks,details) if prop=='unified_assets_source_integrity' else _study(state,task,checks,details))
 except Exception as e:checks['completed_without_error']=False;details['error']={'type':type(e).__name__,'detail':str(e)[:1500]}
 checks['environment_unchanged']=environment(state)['environment_hash']==before['environment_hash']
 result='pass' if checks and all(checks.values()) else 'fail'
 ev=state.put(request(object_new('Evidence',dict(task_id=task['object_id'],task_revision=task['revision'],observation={'checks':checks,'details':details,'environment':before}),visibility=task['visibility'])),'owner')['object']
 val=object_new('Validation',dict(task_id=task['object_id'],task_revision=task['revision'],property=prop,result=result,environment_hash=before['environment_hash'],method='Registered finite UACF work verifier; code/config/native diagnostics or frozen study source integrity only',evidence_id=ev['object_id'],input_vector=[vector(task),vector(ev)],execution_status='ran',coverage=[prop],expiry='Task revision, files, source refs, code, native installation or environment changes'),visibility=task['visibility'])
 obj=state.put(request(val),'owner',internal=True)['object']
 out=dict(ok=True,result=result,checks=checks,details=details,evidence_ref=vector(ev),validation_ref=vector(obj),environment_hash=before['environment_hash'])
 atomic(state.root/'artifacts/host-governance-rewrite-20261019'/('verified-'+prop+'.json'),canonical(out));return out
