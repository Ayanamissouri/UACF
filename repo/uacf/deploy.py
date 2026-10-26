"""Content addressed code releases. Rollback changes code only, never the database."""
import json,shutil,subprocess,sys
from pathlib import Path
from .util import Fault,atomic,canonical,file_hash,now,sha,uid
from .state import State,restore

FOLDERS=['uacf','contracts','adapters','apps','ops','vendor']
def build(root):
 root=Path(root).resolve();repo=root/'repo';files={}
 for folder in FOLDERS:
  for p in (repo/folder).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.log']:
    files[p.relative_to(repo).as_posix()]=file_hash(p)
 for name in ['requirements.lock','requirements.pinned.txt']:files[name]=file_hash(repo/name)
 identity=sha(files);dest=root/'data/releases'/identity/'repo'
 if not dest.exists():
  for name,h in files.items():
   target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,target)
  atomic(dest.parent/'manifest.json',canonical({'identity':identity,'files':files,'created_at':now(),'database_min':3,'database_max':3,'source_root':str(repo)}))
 verify(root,identity)
 return {'ok':True,'identity':identity,'installed_path':str(dest),'generated':True,'installed':True,'loaded':False}
def verify(root,identity):
 root=Path(root).resolve()
 if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):raise Fault('INPUT','release identity SHA256 required')
 dest=root/'data/releases'/identity;manifest=json.loads((dest/'manifest.json').read_text())
 if manifest['identity']!=identity or sha(manifest['files'])!=identity:raise Fault('HASH','release manifest identity mismatch')
 for name,h in manifest['files'].items():
  path=(dest/'repo'/name).resolve()
  if not path.is_relative_to(dest/'repo') or not path.is_file() or file_hash(path)!=h:raise Fault('HASH','installed release differs from manifest')
 return manifest
def apply(root,identity,expected=None,authorization=None):
 root=Path(root).resolve();m=verify(root,identity);s=State(root)
 with s.db() as c:v=c.execute('PRAGMA user_version').fetchone()[0]
 if not m['database_min']<=v<=m['database_max']:raise Fault('VERSION_INCOMPATIBLE','code cannot read current data; keep new history and choose compatible code')
 pointer=root/'data/deployment.json';old=json.loads(pointer.read_text()) if pointer.exists() else None
 if (old or {}).get('identity')!=expected:raise Fault('DEPLOY_CONFLICT','deployment pointer changed')
 backup=root/'backups'/('deploy-'+uid());restore_into=root/'backups'/('deploy-recovery-'+uid());s.backup(backup)
 recovery=restore(backup,restore_into)
 if not recovery['ok']:raise Fault('BACKUP_INCOMPLETE','recovery drill failed')
 # Reconstruct dependencies in installed copy with locked hashes before activating it.
 repo=root/'data/releases'/identity/'repo';runtime=repo/'.venv/Scripts/python.exe'
 if not runtime.exists():
  subprocess.run([sys.executable,'-m','venv',str(repo/'.venv')],check=True,capture_output=True)
  wheelhouse=repo/'vendor/wheels'
  source=['--no-index','--find-links',str(wheelhouse)] if wheelhouse.is_dir() else ['--index-url','https://pypi.org/simple']
  subprocess.run([str(runtime),'-m','pip','install',*source,'--require-hashes','-r',str(repo/'requirements.lock')],check=True,capture_output=True)
 # A populated archive verifies every referenced immutable blob. Keep the
 # integrity check intact; a large local store may exceed three minutes.
 result=subprocess.run([str(runtime),'-X','utf8','-m','uacf','--root',str(root),'--json','doctor'],cwd=repo,capture_output=True,text=True,encoding='utf-8',timeout=900)
 if result.returncode or not json.loads(result.stdout)['ok']:raise Fault('CANARY','installed CLI canary failed')
 scoped=None
 if authorization:
  from .service import call
  scoped=call(root,'lease_acquire',dict(authorization,ttl=30),operation_id=uid())
  call(root,'lease_check',{'scope':scoped['scope'],'holder':scoped['holder'],'fence':scoped['fence']})
 current=json.loads(pointer.read_text()) if pointer.exists() else None
 if (current or {}).get('identity')!=expected:raise Fault('DEPLOY_CONFLICT','deployment pointer changed during validation; prepared release preserved')
 receipt={'identity':identity,'previous_identity':(old or {}).get('identity'),'repo':str(repo),'runtime':str(runtime),'backup':str(backup),'restore':str(restore_into),'applied_at':now(),'loaded':'pending controlled restart','data_rollback':False,'doctor':json.loads(result.stdout),'scoped_authorization':scoped}
 atomic(root/'logs'/('deploy-'+identity+'.json'),canonical(receipt));atomic(pointer,canonical(receipt))
 return dict(receipt,ok=True)
def rollback(root,identity,expected):
 # Same compatibility, backup and CAS as upgrades. No old DB is ever copied back.
 return apply(root,identity,expected)

def activate_code_only(root,identity,expected):
 """CAS a verified code release without migrating or restoring application data.

 Reuse an identical locked Python environment. Preserve the complete old pointer
 for code rollback; do not turn a code-only fix into an archive backup/replay.
 """
 root=Path(root).resolve();manifest=verify(root,identity)
 pointer=root/'data/deployment.json';old=json.loads(pointer.read_text())
 if old['identity']!=expected:raise Fault('DEPLOY_CONFLICT','deployment changed')
 previous=verify(root,expected)
 for name in ['requirements.lock','requirements.pinned.txt']:
  if manifest['files'][name]!=previous['files'][name]:raise Fault('DEPENDENCY_CHANGED','code-only activation requires identical dependency locks')
 old_migrations={k:v for k,v in previous['files'].items() if k.startswith('contracts/migrations/')}
 new_migrations={k:v for k,v in manifest['files'].items() if k.startswith('contracts/migrations/')}
 if old_migrations!=new_migrations:raise Fault('VERSION_INCOMPATIBLE','schema migration requires normal backup/deploy')
 runtime=Path(old['runtime'])
 if not runtime.is_file():raise Fault('RUNTIME_MISSING','existing locked runtime unavailable')
 receipt=dict(identity=identity,previous_identity=expected,repo=str(root/'data/releases'/identity/'repo'),runtime=str(runtime),applied_at=now(),loaded='pending controlled restart',data_rollback=False,mode='code_only_identical_dependencies_no_migration')
 journal=root/'logs'/('code-only-'+identity+'.json')
 atomic(journal,canonical(dict(previous_pointer=old,new_pointer=receipt)))
 if json.loads(pointer.read_text())['identity']!=expected:raise Fault('DEPLOY_CONFLICT','deployment changed before activation')
 atomic(pointer,canonical(receipt));return dict(ok=True,**receipt,rollback_receipt=str(journal))
def uninstall_release(root,expected):
 root=Path(root).resolve();p=root/'data/deployment.json'
 if not p.exists():return {'ok':True,'already_uninstalled':True,'data_preserved':True}
 d=json.loads(p.read_text())
 if d['identity']!=expected:raise Fault('DEPLOY_CONFLICT','installed pointer changed')
 verify(root,expected)
 atomic(root/'backups'/('deployment-uninstalled-'+uid()+'.json'),canonical(d))
 # Preserve all code as recoverable inert release. Stop owned service using manage before this command.
 p.rename(root/'backups'/('deployment-pointer-'+uid()+'.json'))
 s=State(root)
 with s.db() as c:
  pending=[dict(r) for r in c.execute("SELECT operation_id,action,state FROM command_operations WHERE state='pending'")]
  events=[dict(r) for r in c.execute('SELECT * FROM host_watermarks')]
 return {'ok':True,'code_preserved':True,'data_preserved':True,'pending_operations':pending,'host_watermarks':events,'external_actions_replayed':False,'scope':'registered UACF deployment pointer only; host plugin config via compare-before-rollback'}
