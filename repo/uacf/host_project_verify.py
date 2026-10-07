"""Registered, local-only verification of a finite native AOE trial, not a general success-rate claim."""
import json,subprocess,shutil,base64
from datetime import datetime
from pathlib import Path
from .state import object_new,request
from .util import Fault,sha,file_hash,now

def verify(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','Owner dispatches independent project verification')
 task=state.get(args['task_id'],actor)
 if task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','exact current verification revision required')
 root=state.root;plan=json.loads((state.data/'host-project-paid-plan.json').read_text());bench=json.loads((state.data/'host-project-benchmark.json').read_text())
 if plan['task_id']!=task['object_id'] or plan['task_revision']!=task['revision'] or task['payload']['allow_provider'] is not False:raise Fault('INPUT','finished frozen trial required')
 if bench['code_path']!='tools/uacf-acceptance-report.mjs' or bench['report_path']!='reports/uacf-acceptance.json':raise Fault('CONFIG','unexpected output contract')
 for h,w in plan['workspaces'].items():
  if Path(w).resolve() not in [Path(r).resolve() for r in task['payload']['artifact_capture_roots'].get(h,[])]:raise Fault('PERMISSION','verifier workspace is not an authorized Task root')
 checks={};hosts={};node=shutil.which('node');stage=json.loads((state.data/'host-project-stage-1.json').read_text());selected=[]
 if not node:raise Fault('CAPABILITY','actual Node runtime unavailable')
 from .service import verify_dsh
 loaded=verify_dsh(state,actor,task['object_id'],task['revision'])
 codex_context=json.loads((root/f'logs/host-project-codex-native-context-rev{task["revision"]}-20261005.json').read_text())
 def parsed_arguments(b):
  v=b.get('arguments',{});return json.loads(v) if isinstance(v,str) else v
 with state.db() as c:
  native=[json.loads(r['payload']) for r in c.execute('SELECT payload FROM host_events')]
  rows=[dict(r) for r in c.execute('SELECT * FROM budget_reservations') if json.loads(r['receipt']).get('trial_id')==plan['trial_id']]
 protected=lambda w:all(file_hash(Path(w)/n)==h and file_hash(Path(bench['source'])/n)==h for n,h in bench['source_protected_hashes'].items())
 expected=bench['expected']
 def report_ok(v):
  return v.get('schema_version')==2 and all(all(v.get(k,{}).get(a)==b for a,b in expected[k].items()) for k in ['baseline','invariants','undo','provenance']) and v.get('unsupported')==expected['unsupported'] and v.get('original_project_modified') is False
 for host,w in plan['workspaces'].items():
  report=Path(w)/bench['report_path'];code=Path(w)/bench['code_path'];conditions={'protected_111_files':protected(w)};metrics={}
  if host in ['pi','dsh']:
   script="import {runProject} from './ops/host_project_runner.mjs'; console.log(JSON.stringify(await runProject("+json.dumps(str(root))+","+json.dumps(host)+")));"
   ran=subprocess.run([node,'--input-type=module','-e',script],cwd=root/'repo',capture_output=True,text=True,encoding='utf-8',timeout=100)
   value=json.loads(ran.stdout) if ran.returncode==0 else {};conditions.update(fresh_runner=ran.returncode==0 and value.get('ok') is True,dynamic_input_check=value.get('dynamic_input_check') is True)
   metrics['fresh_runner_ms']=value.get('elapsed_ms');chosen=next(x for x in stage['captured'][host]['artifacts'] if state.get(x['object_id'],'owner')['payload']['name'].endswith('.mjs'));selected.append({'object_id':chosen['object_id'],'revision':chosen['revision']})
   conditions['selected_code_pinned']=selected[-1] in task['payload']['asset_refs']
   conditions['restored_bytes_match_asset']=file_hash(code)==chosen['sha256']==file_hash(Path(w)/'tools/uacf-acceptance-report.schema2-retained.mjs')
   events=[e['payload'] for e in native if e['source_host']==host and e['payload'].get('native_session_id')==plan['native_sessions'][host]]
   if host=='pi':
    calls=[e for e in events if e.get('kind')=='native_tool_call' and e.get('input',{}).get('artifact_id')==chosen['object_id'] and e.get('task_revision')==10]
    ids={e['native_tool_call_id'] for e in calls};conditions['actual_asset_read']=bool(ids) and any(e.get('kind')=='native_tool_result' and e.get('native_tool_call_id') in ids and e.get('isError') is False for e in events)
    receipt=json.loads((root/'logs/host-project-pi-round-2-20261005.json').read_text());conditions['native_model_round']=receipt['model_calls']>0 and not receipt['error'] and not receipt['unknown']
   else:
    calls=[b for e in events if e.get('kind')=='native_message' for b in (e.get('message') or {}).get('content',[]) if b.get('type')=='tool-call' and b.get('name')=='uacf_asset_read' and parsed_arguments(b).get('artifact_id')==chosen['object_id'] and parsed_arguments(b).get('task_revision')==10]
    ids={b['id'] for b in calls};conditions['actual_asset_read']=bool(ids) and any(e.get('native_type')=='tool/result' and ((e.get('message') or {}).get('source') or {}).get('callId') in ids and any(b.get('type')=='tool-result' and b.get('isError') is False for b in (e.get('message') or {}).get('content',[])) for e in events)
    conditions['native_model_round']=any(e.get('native_type')=='turn/end' and (e.get('data') or {}).get('reason',{}).get('kind')=='completed' for e in events)
   conditions['automatic_candidate_capture']=any(e.get('kind')=='artifact_capture_receipt' and e.get('receipt',{}).get('ok') is True and any(state.get(v['object_id'],'owner')['payload'].get('task_revision')==10 for v in e['receipt'].get('artifacts',[])) for e in events)
  else:
   reuse=json.loads((root/'logs/host-project-codex-reuse-read-20261005.json').read_text());ref={'object_id':reuse['read']['object_id'],'revision':reuse['read']['revision']};selected.append(ref)
   body=state.fetch_blob('owner',ref['object_id'],ref['revision'])
   conditions.update(selected_code_pinned=ref in task['payload']['asset_refs'],restored_bytes_match_asset=file_hash(Path(reuse['reconstructed']))==sha(base64.b64decode(body['base64'])),actual_asset_read=reuse['read'].get('ok') is True and reuse['read']['blob_hash']==body['blob_hash'])
   started=datetime.now();ran=subprocess.run([node,str(Path(reuse['reconstructed']))],cwd=w,capture_output=True,text=True,encoding='utf-8',timeout=100)
   conditions['fresh_runner']=ran.returncode==0 and report_ok(json.loads(ran.stdout)) if ran.returncode==0 else False
   metrics.update(fresh_runner_ms=(datetime.now()-started).total_seconds()*1000,model_latency='unavailable in current desktop chat',provider_usage='unavailable; no DeepSeek charge attributed to Codex',archive='explicit native-locator CLI fallback; automatic Stop receipt not proven')
  conditions['schema2_report']=report_ok(json.loads(report.read_text()));hosts[host]={'checks':conditions,'metrics':metrics,'report_sha256':file_hash(report),'code_sha256':file_hash(code)}
 checks['all_reports']=all(h['checks'].get('schema2_report') and h['checks'].get('fresh_runner') and h['checks'].get('protected_111_files') for h in hosts.values())
 checks['all_reuse']=all(all(h['checks'].get(k) for k in ['actual_asset_read','selected_code_pinned','restored_bytes_match_asset']) for h in hosts.values())
 checks['native_pi_dsh']=all(all(v for k,v in hosts[h]['checks'].items()) for h in ['pi','dsh'])
 checks['known_bounded_paid_calls']=len(rows)==26 and all(r['state']=='settled' for r in rows) and sum(r['actual_micro'] for r in rows)<=plan['authorized_limit_micro']
 checks['frozen']=task['payload']['allow_provider'] is False
 checks['installed_loaded_called']=loaded['result']=='pass' and checks['native_pi_dsh'] and codex_context.get('status')=='ready' and codex_context.get('capsule',{}).get('task_revision')==task['revision']
 metrics={}
 for h in ['pi','dsh']:
  rs=[r for r in rows if json.loads(r['receipt'])['actor']==h];times=[]
  for r in rs:
   x=json.loads(r['receipt']);times.append((datetime.fromisoformat(x['settled_at'])-datetime.fromisoformat(x['reserved_at'])).total_seconds()*1000)
  metrics[h]={'paid_model_requests':len(rs),'cost_upper_bound_micro':sum(r['actual_micro'] for r in rs),'request_ms':times,'request_mean_ms':sum(times)/len(times),'max_request_context_bytes':max(json.loads(r['receipt'])['input_upper_bound_bytes'] for r in rs),'native_rounds':3,'broad_success_rate':'not established','causal_performance_improvement':'not established'}
 observation={'at':now(),'checks':checks,'hosts':hosts,'metrics':metrics,'scope':'finite AOE report implementation/correction/asset body reuse; no general Host/model reliability or complete original AOE acceptance','automatic_codex_stop':'unproven; supported explicit archive fallback','invoice':'unknown; ledger is conservative peak-price usage upper bound'}
 environment_hash=sha({'deployment':json.loads((state.data/'deployment.json').read_text())['identity'],'hosts':{h:{k:v for k,v in p.items() if k.endswith('_sha256')} for h,p in hosts.items()},'loaded_environment':loaded['environment_hash'],'authority':state.authority})
 evidence=state.put(request(object_new('Evidence',{'observation':observation,'task_id':task['object_id'],'target_revision':task['revision']},visibility=task['visibility'])),'owner')['object'];validations=[]
 verdicts={'installed_loaded_called':checks['installed_loaded_called'],'source_grounded_aoe_report_all_hosts':checks['all_reports'],'artifact_reuse_all_hosts':checks['all_reuse'],'bounded_real_host_performance':checks['known_bounded_paid_calls'] and checks['native_pi_dsh']}
 for prop,passed in verdicts.items():
  v=object_new('Validation',{'task_id':task['object_id'],'task_revision':task['revision'],'property':prop,'result':'pass' if passed else 'fail','environment_hash':environment_hash,'method':'registered independent local report/byte identity/native public call and budget verifier','evidence_id':evidence['object_id'],'input_vector':[{'object_id':task['object_id'],'revision':task['revision']},*selected,{'object_id':evidence['object_id'],'revision':evidence['revision']}],'execution_status':'ran','coverage':[prop,observation['scope']],'expiry':'environment or dependency change'},visibility=task['visibility']);v['provenance_refs']=[evidence['object_id']];validations.append(state.put(request(v),'system',internal=True)['object'])
 return {'ok':True,'checks':checks,'evidence':evidence,'validations':validations,'environment_hash':environment_hash}
