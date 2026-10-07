"""Uninstall one selected UACF release/config manifest. Never walk historical backups."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from uacf.deploy import uninstall_release
from uacf.util import Fault,atomic,canonical,file_hash,uid
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--identity');p.add_argument('--host-manifest');a=p.parse_args();root=Path(a.root).resolve()
try:
 result={'ok':True,'data_preserved':True,'original_assets_preserved':True,'shared_packages_preserved':True}
 if a.host_manifest:
  path=Path(a.host_manifest).resolve()
  if not path.is_relative_to(root/'backups'):raise Fault('PATH_SCOPE','registered backup manifest required')
  m=json.loads(path.read_text())
  if m['status']!='applied':raise Fault('INPUT','applied host manifest required')
  for f in m['files']:
   target=Path(f['path']);current=file_hash(target) if target.exists() else None
   if current!=f['after_hash']:raise Fault('HOST_DRIFT','preserve later host modifications; manual reconciliation required')
   backup=Path(f['backup']).resolve()
   if not backup.is_relative_to(path.parent):raise Fault('PATH_SCOPE','invalid registered backup')
   if f['existed'] and file_hash(backup)!=f['before_hash']:raise Fault('HASH','original configuration backup differs')
  # After all checks, preserve current state and restore only exact registered files.
  for f in m['files']:
   target=Path(f['path'])
   if target.exists():atomic(root/'backups'/('uninstall-current-'+uid()),target.read_bytes())
   if f['existed']:atomic(target,Path(f['backup']).read_bytes())
   elif target.exists():target.rename(root/'backups'/('uninstalled-config-'+uid()))
  m['status']='rolled_back';atomic(path,canonical(m));result['host_manifest_restored']=str(path)
 if a.identity:result['release']=uninstall_release(root,a.identity)
 print(canonical(result))
except Fault as e:print(canonical(e.result()));sys.exit(6)
