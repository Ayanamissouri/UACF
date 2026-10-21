"""Managed zero-model catch-up for mapped Codex sessions via official public read.
This is polling, not a hook. It captures sources only; current host interprets them.
"""
import importlib.util,json,threading,time
from pathlib import Path
from .util import Fault,canonical,atomic,now

def configure(state,actor,args):
 if actor!='owner' or not args.get('authorization'):raise Fault('PERMISSION','current Owner archive authorization required')
 interval=args.get('interval_seconds',60)
 if type(interval)!=int or not 30<=interval<=3600:raise Fault('INPUT','bounded polling cadence required')
 config=dict(enabled=args.get('enabled',True) is True,interval_seconds=interval,max_sessions=4,preferred_session=args.get('native_session_id'),authorization=args['authorization'],coverage='currently mapped active Codex sessions, official persisted public read, no model turns or fake hooks')
 atomic(state.data/'native-watch.json',canonical(config));return dict(ok=True,config=config,model_calls=0)

def start(state,stop):
 def run():
  active={}
  while not stop.is_set():
   config_path=state.data/'native-watch.json';delay=60
   try:
    cfg=json.loads(config_path.read_text()) if config_path.exists() else {}
    delay=cfg.get('interval_seconds',60)
    if cfg.get('enabled'):
     bindings=json.loads((state.data/'host-bindings.json').read_text()).get('codex',{})
     rows=sorted(bindings.items(),key=lambda p:p[0]!=cfg.get('preferred_session'));selected=[]
     for sid,tid in rows:
      t=state.get(tid,'owner')
      if t['payload'].get('execution_state') not in ['stopped','blocked','completed']:selected.append((sid,tid))
     spec=importlib.util.spec_from_file_location('uacf_managed_native_public',Path(__file__).resolve().parents[1]/'adapters/codex/public_read.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
     binaries=list((Path.home()/'AppData/Local/OpenAI/Codex/bin').glob('*/codex.exe'))
     if not binaries:raise Fault('CAPABILITY_GAP','native Codex binary unavailable')
     binary=max(binaries,key=lambda p:p.stat().st_mtime);results=[]
     for sid,tid in selected[:cfg.get('max_sessions',4)]:
      if stop.is_set():break
      try:
       observed=module.observe(state.root,binary,sid,tid);results.append(dict(session_id=sid,**observed))
       for turn in observed['turns']:
        key=(sid,turn['turn_id']);previous=active.setdefault(key,{'at':time.monotonic(),'event':None});event=turn.get('last_public_event_id')
        if turn['status']!='completed' and event and event!=previous['event'] and time.monotonic()-previous['at']>=900:
         from .service import call
         task=state.get(tid,'owner')
         capture=call(state.root,'learning_checkpoint',dict(task_id=tid,task_revision=task['revision'],host='codex',native_session_id=sid,native_event_id=event,signal='milestone',basis='15-minute active-work public polling checkpoint; no synthetic turn completion',features={'progress':True,'periodic_checkpoint':True,'cue':'Periodic public work checkpoint; interpretation remains candidate.'}))
         previous.update(at=time.monotonic(),event=event);results[-1]['periodic_checkpoint']=capture
      except Exception as e:results.append(dict(session_id=sid,ok=False,error=str(e)[:400]))
     atomic(state.data/'native-watch-status.json',canonical(dict(at=now(),transport='managed official public polling; not live hooks',results=results,model_calls=0)))
   except Exception as e:atomic(state.data/'native-watch-status.json',canonical(dict(at=now(),ok=False,error=str(e)[:500],model_calls=0)))
   stop.wait(delay)
 thread=threading.Thread(target=run,daemon=True,name='uacf-native-public-watch');thread.start();return thread
