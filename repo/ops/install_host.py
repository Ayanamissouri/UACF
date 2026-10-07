"""User-invoked preserving setup. Never silently replace another root's named binding."""
import argparse,json,pathlib,sys,os,tomllib,shutil,subprocess
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import yaml
from uacf.host import backup_config,complete
from uacf.util import Fault,atomic,canonical

def install(root,host,home,apply=False):
 root=pathlib.Path(root).resolve();home=pathlib.Path(home).resolve();repo=root/'repo';python=repo/'.venv/Scripts/python.exe'
 if not python.is_file():raise Fault('RUNTIME','prepare local runtime first')
 paths=[home/'config.toml'] if host=='codex' else [home/'settings.json',home/'uacf-host.json'] if host=='pi' else [home/'profiles/web/package.json',home/'profiles/web/cordis.patch.yml',home/'profiles/web/pnpm-lock.yaml']
 if not apply:return {'ok':True,'plan_files':[str(p) for p in paths],'root':str(root),'host':host,'configured':False,'loaded':'unknown','provider_calls':0}
 texts={};plugin=None
 if host=='codex':
  p=paths[0];original=p.read_text(encoding='utf-8-sig') if p.exists() else '';cfg=tomllib.loads(original)
  entry={'command':str(python),'args':['-m','uacf','--root',str(root),'mcp','--host','codex'],'cwd':str(repo),'enabled':True}
  old=cfg.get('mcp_servers',{}).get('uacf')
  if old:
   if any(old.get(k)!=v for k,v in entry.items() if k!='enabled'):raise Fault('CONFIG_CONFLICT','uacf already belongs to another command/root; preserve it')
   return {'ok':True,'already_configured':True,'loaded':'unknown; verify native tools separately'}
  text=original+'\n[mcp_servers.uacf]\n'+'\n'.join(k+' = '+('true' if v is True else json.dumps(v)) for k,v in entry.items())+'\n';tomllib.loads(text);texts[p]=text
 elif host=='pi':
  p,bind=paths;cfg=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {};extensions=cfg.setdefault('extensions',[])
  if not isinstance(extensions,list):raise Fault('CONFIG','preserve unsupported Pi extensions shape')
  extension=str(repo/'adapters/pi/installed.mjs')
  if extension not in extensions:extensions.append(extension)
  auth=json.loads((root/'data/auth.json').read_text(encoding='utf-8'));port=json.loads((root/'data/config.json').read_text(encoding='utf-8'))['port']
  binding={'root':str(root),'url':f'http://127.0.0.1:{port}','token':auth['pi']}
  if bind.exists() and json.loads(bind.read_text(encoding='utf-8')).get('root')!=str(root):raise Fault('CONFIG_CONFLICT','Pi binding belongs to another root')
  texts[p]=json.dumps(cfg,ensure_ascii=False,indent=2);texts[bind]=canonical(binding)
 else:
  p,patch=paths[:2]
  if not p.exists():raise Fault('HOST_CONFIG','existing DSH web profile required; do not fabricate a host')
  cfg=json.loads(p.read_text(encoding='utf-8-sig'));overlay=patch.read_text(encoding='utf-8-sig') if patch.exists() else '';rows=yaml.safe_load(overlay) or []
  if not isinstance(rows,list):raise Fault('HOST_CONFIG','unsupported Cordis overlay; preserve it')
  for row in rows:
   for value in row.get('insert',[]) if isinstance(row,dict) else []:
    if isinstance(value,dict) and value.get('id')=='uacf-public-v1':raise Fault('CONFIG_CONFLICT','public mount already exists; verify instead of duplicate/overwrite')
  plugin=root/'data/host-adapters/dsh-uacf-public'
  if plugin.exists():raise Fault('CONFIG_CONFLICT','owned plugin directory exists; review its identity')
  manager=shutil.which('pnpm.cmd' if os.name=='nt' else 'pnpm')
  if not manager:raise Fault('HOST_CONFIG','DSH native pnpm is unavailable; profile preserved')
  dependency='link:'+plugin.as_posix();old=cfg.setdefault('dependencies',{}).get('dsh-uacf-public')
  if old and old!=dependency:raise Fault('CONFIG_CONFLICT','dependency belongs to another root')
  cfg['dependencies']['dsh-uacf-public']=dependency
  mount=[{'insert':[{'id':'uacf-public-v1','name':'dsh-uacf-public','config':{'root':str(root)}}]}]
  texts[p]=json.dumps(cfg,ensure_ascii=False,indent=2);texts[patch]=overlay+'\n# UACF public owned mount; all prior bytes preserved.\n'+yaml.safe_dump(mount,sort_keys=False)
 backup,manifest=backup_config(root,host,paths)
 if plugin:
  plugin.mkdir(parents=True)
  for name in ['public.js','continuity.js']:shutil.copyfile(repo/'adapters/dsh'/name,plugin/name)
  atomic(plugin/'package.json',canonical({'name':'dsh-uacf-public','version':'0.3.0','type':'module','exports':{'.':'./public.js'},'private':True}))
 for path,text in texts.items():atomic(path,text)
 complete(backup,manifest)
 if plugin:
  args=([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',manager] if os.name=='nt' else [manager])+['install','--offline','--ignore-scripts']
  try:
   process=subprocess.run(args,cwd=paths[0].parent,capture_output=True,timeout=120)
   if process.returncode:raise Fault('INSTALL_FAILED','native offline package resolution failed; inspect the preserving receipt')
  except Exception:
   from uacf.util import file_hash
   for path in texts:
    if file_hash(path)!=manifest['files'][paths.index(path)]['after_hash']:raise Fault('CONFIG_CONFLICT','profile changed during install; no overwrite')
   for row in manifest['files']:
    if row['existed']:atomic(pathlib.Path(row['path']),pathlib.Path(row['backup']).read_bytes())
   manifest['status']='failed; prior configuration restored, new files/plugin kept for inspection';atomic(backup/'manifest.json',canonical(manifest));raise
  complete(backup,manifest)
 return {'ok':True,'configured':True,'backup':str(backup),'loaded':'unknown; host reload and actual event verification required','provider_calls':0,'dsh_package_resolution':'native offline link installed without package scripts' if host=='dsh' else 'not applicable','data_preserved':True,'private_tokens_in_source_package':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--host',choices=['codex','pi','dsh'],required=True);p.add_argument('--home');p.add_argument('--install',action='store_true');a=p.parse_args()
 home=a.home or (os.environ.get('CODEX_HOME') or str(pathlib.Path.home()/'.codex')) if a.host=='codex' else a.home or (os.environ.get('PI_CODING_AGENT_DIR') or str(pathlib.Path.home()/'.pi/agent')) if a.host=='pi' else a.home or os.environ.get('DSH_HOME') or str(pathlib.Path.home()/'.dsh-research')
 try:print(canonical(install(a.root,a.host,home,a.install)))
 except Fault as e:print(canonical(e.result()));sys.exit(6)
if __name__=='__main__':main()
