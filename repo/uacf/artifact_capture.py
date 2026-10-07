"""Publish explicitly authorized work products as candidate snapshots, never semantic adoption."""
import json,uuid
from pathlib import Path
from .state import object_new,request
from .util import Fault,sha,file_hash
def capture(state,actor,args):
 if set(args)-{'task_id','task_revision','native_session_id','host'} or any(not isinstance(args.get(k),str) or not args[k] or len(args[k])>256 for k in ['task_id','native_session_id']):
  raise Fault('INPUT','bounded Task/native session identifiers required')
 host=args.get('host',actor)
 if host not in ['codex','pi','dsh'] or actor not in ['owner',host]:raise Fault('PERMISSION','own Host capture only')
 task=state.get(args['task_id'],actor)
 if task['object_type']!='TaskContract' or type(args.get('task_revision'))!=int or task['revision']!=args['task_revision']:
  raise Fault('REVISION_CONFLICT','current exact Task revision required')
 sid=args['native_session_id'];bindings=json.loads((state.data/'host-bindings.json').read_text())
 from .learning import config
 if config(state):
  from .learning_guards import protected
  protected(task)
 if bindings.get(host,{}).get(sid)!=task['object_id']:raise Fault('PERMISSION','explicit native mapping required')
 paths=task['payload'].get('artifact_capture_paths',{}).get(host,[])
 roots=[Path(p).resolve() for p in task['payload'].get('artifact_capture_roots',{}).get(host,[])]
 if len(paths)>32 or len(roots)>8:raise Fault('LIMIT','capture path/root count exceeds quota')
 if any(not any(Path(raw).resolve().is_relative_to(r) for r in roots) for raw in paths):
  raise Fault('PERMISSION','capture path escapes authorized workspace')
 artifacts=[];missing=[]
 for raw in paths:
  p=Path(raw).resolve()
  if not any(p.is_relative_to(r) for r in roots):raise Fault('PERMISSION','capture path escapes authorized workspace')
  if not p.is_file():missing.append(str(p));continue
  if p.stat().st_size>1048576:raise Fault('LIMIT','work product exceeds snapshot quota')
  body=p.read_bytes();digest=sha(body)
  if len(body)>1048576 or file_hash(p)!=digest:raise Fault('SOURCE_CHANGED','capture source changed during snapshot')
  oid=str(uuid.uuid5(uuid.UUID(state.authority),sha([host,sid,task['object_id'],task['revision'],str(p),digest])))
  try:old=state.get(oid,actor)
  except Fault as e:
   if e.code!='NOT_FOUND':raise
   old=None
  if old:
   if old['object_type']!='Artifact' or old['payload'].get('sha256')!=digest:raise Fault('EVENT_CONFLICT','snapshot identity differs')
   artifacts.append({'object_id':oid,'revision':old['revision'],'duplicate':True,'sha256':digest});continue
  obj=object_new('Artifact',{'locator':str(p),'sha256':digest,'name':p.name,'media_type':'application/json' if p.suffix=='.json' else 'text/plain',
   'source_locator':{'path':str(p),'native_session_id':sid,'host':host,'task_id':task['object_id'],'task_revision':task['revision']},
   'origin_host':host,'task_id':task['object_id'],'task_revision':task['revision'],'candidate':True,'interpretation':'not performed','adoption':'not implied'},visibility=task['visibility'])
  obj['object_id']=oid;obj['provenance_refs']=[task['object_id']]
  saved=state.put(request(obj,blob=body,actor=actor),actor)['object']
  artifacts.append({'object_id':oid,'revision':saved['revision'],'duplicate':False,'sha256':digest})
 return {'ok':True,'artifacts':artifacts,'missing_paths':missing,'coverage':'explicit configured output files only; candidate snapshots; no semantic adoption'}
