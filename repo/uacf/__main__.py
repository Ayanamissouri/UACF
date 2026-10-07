import argparse, json, sys
from pathlib import Path
from .state import State, init, object_new, request, restore, verify_backup
from .service import call, dispatch, serve
from .util import Fault, canonical

def main():
    # Accept the baseline's conventional `uacf doctor --json` / `init --root PATH` order.
    argv=sys.argv[1:]; global_args=[]
    for flag in ['--json','--root','--actor']:
        if flag in argv:
            i=argv.index(flag); count=1 if flag=='--json' else 2
            global_args.extend(argv[i:i+count]); del argv[i:i+count]
    p=argparse.ArgumentParser(prog='uacf',description='UACF E0-E2 canonical continuity service; no automatic external write replay')
    p.add_argument('--root',default=str(Path(__file__).resolve().parents[2])); p.add_argument('--json',action='store_true'); p.add_argument('--actor',choices=['owner','reader','dsh','codex','pi'],default='owner')
    sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('init');x.add_argument('--current-schema',action='store_true');sub.add_parser('doctor')
    x=sub.add_parser('migrate');x.add_argument('--backup',required=True)
    x.add_argument('--batch',type=int,choices=[2,3,4],default=2)
    x=sub.add_parser('serve'); x.add_argument('--bind',default='127.0.0.1'); x.add_argument('--port',type=int)
    x=sub.add_parser('worker'); x.add_argument('--once',action='store_true',required=True)
    x=sub.add_parser('object'); x.add_argument('operation',choices=['put','get','list']); x.add_argument('--file'); x.add_argument('--id'); x.add_argument('--type'); x.add_argument('--offline',action='store_true')
    x=sub.add_parser('task'); x.add_argument('operation',choices=['open','status','verify','accept']); x.add_argument('--goal'); x.add_argument('--id'); x.add_argument('--revision',type=int); x.add_argument('--property',action='append',default=[])
    x=sub.add_parser('context'); x.add_argument('operation',choices=['prepare']); x.add_argument('--task',required=True); x.add_argument('--max-bytes',type=int)
    x=sub.add_parser('profile'); x.add_argument('operation',choices=['get','set']); x.add_argument('--host',choices=['dsh','codex']); x.add_argument('--tokens'); x.add_argument('--capsule-max-bytes',type=int); x.add_argument('--expected-revision',type=int)
    x=sub.add_parser('action'); x.add_argument('name'); x.add_argument('--file',required=True)
    x=sub.add_parser('archive');x.add_argument('operation',choices=['inventory','plan','run','coverage','read','materialize','reindex']);x.add_argument('--file',required=True)
    x=sub.add_parser('backup'); x.add_argument('operation',choices=['create','verify']); x.add_argument('--path',required=True)
    x=sub.add_parser('evidence'); x.add_argument('operation',choices=['fetch']); x.add_argument('--id',required=True); x.add_argument('--revision',type=int); x.add_argument('--max-bytes',type=int,default=65536)
    x=sub.add_parser('operation'); x.add_argument('operation',choices=['status']); x.add_argument('--id',required=True)
    x=sub.add_parser('restore'); x.add_argument('--backup',required=True); x.add_argument('--into',required=True)
    x=sub.add_parser('host'); x.add_argument('operation',choices=['probe','install','verify','rollback','reload','context']); x.add_argument('--host',choices=['dsh','codex'],required=True); x.add_argument('--home'); x.add_argument('--task'); x.add_argument('--revision',type=int); x.add_argument('--tokens',type=int)
    x=sub.add_parser('mcp'); x.add_argument('--host',default='codex',choices=['dsh','codex','pi'])
    x=sub.add_parser('ui')
    a=p.parse_args(global_args+argv)
    try:
        root=Path(a.root).resolve()
        if a.command=='init': result=init(root,current_schema=a.current_schema)
        elif a.command=='serve': serve(root,a.bind,a.port); return
        elif a.command=='mcp':
            from .mcp import run
            run(root,a.host); return
        elif a.command=='doctor': result=State(root).doctor()
        elif a.command=='worker': result=State(root).worker_once()
        elif a.command=='backup': result=State(root).backup(a.path) if a.operation=='create' else verify_backup(a.path)
        elif a.command=='evidence': result=call(root,'blob',{'object_id':a.id,'revision':a.revision,'max_bytes':a.max_bytes},a.actor)
        elif a.command=='operation': result=call(root,'operation_get',{'operation_id':a.id},a.actor)
        elif a.command=='restore': result=restore(a.backup,a.into)
        elif a.command=='migrate':
            if a.batch==4:
                from .archive import migrate4 as migrate
            elif a.batch==3:
                from .batch3 import migrate3 as migrate
            else:
                from .fabric import migrate
            result=migrate(State(root),a.backup)
        elif a.command=='object':
            action={'put':'put','get':'get','list':'list'}[a.operation]
            args=json.loads(Path(a.file).read_text(encoding='utf-8-sig')) if action=='put' else {'object_id':a.id} if action=='get' else {'type':a.type}
            if a.offline:
                state=State(root)
                if action=='put': result=state.put(args,a.actor)
                else: result=dispatch(state,a.actor,action,args)
            else: result=call(root,action,args,a.actor)
        elif a.command=='task':
            if a.operation=='open':
                if not a.goal: raise Fault('INPUT','goal required')
                result=call(root,'put',request(object_new('TaskContract',{'goal':a.goal,'required_properties':a.property},'active','shared')),a.actor)
            elif a.operation=='status': result=call(root,'get',{'object_id':a.id},a.actor)
            else: result=call(root,'verify_dsh' if a.operation=='verify' else 'promote',{'task_id':a.id,'revision':a.revision},a.actor)
        elif a.command=='context': result=call(root,'context',{'task_id':a.task,'max_bytes':a.max_bytes},a.actor)
        elif a.command=='action': result=call(root,a.name,json.loads(Path(a.file).read_text(encoding='utf-8-sig')),a.actor)
        elif a.command=='archive': result=call(root,'archive_'+a.operation,json.loads(Path(a.file).read_text(encoding='utf-8-sig')),a.actor)
        elif a.command=='profile':
            args={} if a.operation=='get' else {'host':a.host,'requested_tokens':'auto' if a.tokens=='auto' else int(a.tokens),'capsule_max_bytes':a.capsule_max_bytes,'expected_revision':a.expected_revision}
            result=call(root,'profile_'+a.operation,args,a.actor)
        elif a.command=='host':
            from .host import host_command
            result=host_command(root,a)
        elif a.command=='ui':
            import webbrowser
            cfg=State(root).config; url=f"http://127.0.0.1:{cfg['port']}/"; webbrowser.open(url); result={'ok':True,'url':url}
        print(canonical(result) if a.json else json.dumps(result,ensure_ascii=False,indent=2))
        if not result.get('ok',True): sys.exit(6)
    except Fault as e:
        print(canonical(e.result())); sys.exit({'INPUT':2,'SCHEMA':2,'PERMISSION':3,'AUTHENTICATION':3,'REVISION_CONFLICT':4,'OPERATION_CONFLICT':4,'CORE_UNAVAILABLE':7}.get(e.code,6))
    except (ValueError,TypeError,KeyError) as e: print(canonical(Fault('INPUT',str(e)).result())); sys.exit(2)

if __name__=='__main__': main()
