"""User-invoked preserving setup. Never silently replace another root's named binding."""
import argparse,json,pathlib,sys,os,tomllib,shutil,subprocess
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import yaml
from uacf.host import backup_config,complete
from uacf.util import Fault,atomic,canonical

def install_defaults(root):
 """Owner-invoked cross-host extension of the existing preserving installer.
 No hook trust-store edits and no native/model turns. All existing settings kept.
 """
 root=pathlib.Path(root).resolve();repo=root/'repo';home=pathlib.Path.home()
 instructions=(repo/'adapters/templates/DEFAULT_WORK.md').read_text(encoding='utf8')
 start='<!-- UACF DEFAULT WORK START -->';end='<!-- UACF DEFAULT WORK END -->'
 texts={}
 for p in [home/'.codex/AGENTS.md',home/'.claude/CLAUDE.md',home/'.pi/agent/AGENTS.md',(pathlib.Path(os.environ.get('UACF_PI_AGENT_HOME', str(home/'.pi/agent')))/'AGENTS.md'),home/'.dsh-research/AGENTS.md',repo/'AGENTS.md']:
  old=p.read_text(encoding='utf-8-sig') if p.exists() else ''
  if start in old:
   if end not in old:raise Fault('CONFIG_CONFLICT','unfinished managed instruction block')
   old=old[:old.index(start)]+instructions+old[old.index(end)+len(end):]
  else:old=old.rstrip()+'\n\n'+instructions
  texts[p]=old
 # Keep all unrelated native hook entries. The handler's real default-work scope
 # is separate from trust, which only the native application can report/grant.
 py=repo/'.venv/Scripts/python.exe'
 for host,p,events in [('codex',home/'.codex/hooks.json',['SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','Stop','SessionEnd','Interrupt']),('claude_code',home/'.claude/settings.json',['SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','Stop','SessionEnd'])]:
  cfg=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
  hooks=cfg.setdefault('hooks',{})
  script=repo/'adapters'/host/'hook.py'
  command=f'"{py}" -X utf8 "{script}" "{root}"'
  for event in events:
   rows=hooks.setdefault(event,[])
   for row in rows:
    row['hooks']=[h for h in row.get('hooks',[]) if str(script).lower() not in h.get('command','').lower()]
   rows[:]=[r for r in rows if r.get('hooks')]
   handler={'type':'command','command':command,'timeout':15}
   if host=='claude_code':handler.update(command='& '+command,shell='powershell')
   else:handler['statusMessage']='UACF archive and required context'
   rows.append({'hooks':[handler]})
  if host=='codex':cfg['description']='Owner default UACF work; explicit opt-out only; public native lifecycle and tool admission; no paid replay.'
  texts[p]=json.dumps(cfg,ensure_ascii=False,indent=2)+'\n'
 # Explicitly enable the existing Codex hook feature without rebuilding TOML.
 p=home/'.codex/config.toml';old=p.read_text(encoding='utf-8-sig') if p.exists() else '';cfg=tomllib.loads(old)
 if cfg.get('features',{}).get('hooks') is not True:
  import re
  if re.search(r'^\[features\]\s*$',old,re.M):
   match=re.search(r'(^\[features\]\s*\n)(.*?)(?=^\[|\Z)',old,re.M|re.S)
   body=match[2];body=re.sub(r'^hooks\s*=.*$', 'hooks = true',body,flags=re.M) if re.search(r'^hooks\s*=',body,re.M) else 'hooks = true\n'+body
   old=old[:match.start()]+match[1]+body+old[match.end():]
  else:old+='\n[features]\nhooks = true\n'
  tomllib.loads(old);texts[p]=old
 # Existing authorities gain only missing Host-scoped credentials; never print
 # them or reuse the Owner token in a Host configuration.
 authpath=root/'data/auth.json';auth=json.loads(authpath.read_text(encoding='utf8'))
 for host in ['claude_code','codex_cloud']:auth.setdefault(host,os.urandom(32).hex())
 texts[authpath]=canonical(auth)
 # Both actual custom Pi profile and standard global profile use same installer.
 backup,manifest=backup_config(root,'default-work',list(texts))
 for p,text in texts.items():atomic(p,text)
 complete(backup,manifest)
 pi=[install(root,'pi',p,True) for p in [home/'.pi/agent',pathlib.Path(os.environ.get('UACF_PI_AGENT_HOME', str(home/'.pi/agent')))]]
 # Claude Code reads per-user stdio MCP entries from ~/.claude.json.
 p=home/'.claude.json';cfg=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
 entry={'type':'stdio','command':str(py),'args':['-m','uacf','--root',str(root),'mcp','--host','claude_code'],'cwd':str(repo)}
 old=cfg.setdefault('mcpServers',{}).get('uacf')
 if old and old!=entry:raise Fault('CONFIG_CONFLICT','existing Claude UACF MCP belongs to another configuration')
 cfg['mcpServers']['uacf']=entry;b,m=backup_config(root,'claude-code-mcp',[p]);atomic(p,json.dumps(cfg,ensure_ascii=False,indent=2)+'\n');complete(b,m)
 return dict(ok=True,backup=str(backup),files=[str(p) for p in texts],pi=pi,claude_mcp_backup=str(b),native_trust_modified=False,model_calls=0,loaded='must verify each native runtime separately')

def install_trusted_codex(root,authorization):
 """Explicit Owner default-trust deployment using documented system requirements.
 Only UACF handlers are managed; no trust DB, broad trust bypass, or unrelated
 permission/approval settings are changed. Other hooks stay in native config.
 """
 if authorization!='Current Owner response: 默认信任':raise Fault('PERMISSION','explicit current Owner default-trust instruction required')
 root=pathlib.Path(root).resolve();repo=root/'repo';home=pathlib.Path.home()
 p=pathlib.Path(os.environ.get('ProgramData','C:/ProgramData'))/'OpenAI/Codex/requirements.toml'
 hooksfile=home/'.codex/hooks.json';old=p.read_text(encoding='utf-8-sig') if p.exists() else ''
 start='# UACF OWNER DEFAULT TRUST START';end='# UACF OWNER DEFAULT TRUST END'
 if start in old:
  if end not in old:raise Fault('CONFIG_CONFLICT','incomplete managed UACF block')
  old=old[:old.index(start)]+old[old.index(end)+len(end):]
 cfg=tomllib.loads(old)
 if 'hooks' in cfg:raise Fault('CONFIG_CONFLICT','existing system hooks require preserving merge review')
 if 'features' in cfg:raise Fault('CONFIG_CONFLICT','existing system feature table requires preserving merge review')
 command=f'"{repo / ".venv/Scripts/python.exe"}" -X utf8 "{repo / "adapters/codex/hook.py"}" "{root}"'
 lines=[start,'# Owner explicitly instructed default trust for UACF only.','[features]','hooks = true','[hooks]',"windows_managed_dir = '"+str(repo/'adapters/codex')+"'"]
 for event in ['SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','Stop','SessionEnd','Interrupt']:
  lines += ['[[hooks.'+event+']]','[[hooks.'+event+'.hooks]]','type = "command"','command = '+json.dumps(command),'command_windows = '+json.dumps(command),'timeout = 15','statusMessage = "UACF Owner-authorized default work"']
 text=old.rstrip()+'\n\n'+'\n'.join(lines+[end])+'\n';tomllib.loads(text)
 backup,manifest=backup_config(root,'codex-managed-default-trust',[p,hooksfile])
 atomic(p,text)
 # Remove only our duplicate user entries. Native trust of other hooks remains.
 user=json.loads(hooksfile.read_text(encoding='utf8'))
 for event,rows in list(user.get('hooks',{}).items()):
  for row in rows:row['hooks']=[h for h in row.get('hooks',[]) if str(repo/'adapters/codex/hook.py').lower() not in h.get('command','').lower()]
  user['hooks'][event]=[r for r in rows if r.get('hooks')]
  if not user['hooks'][event]:del user['hooks'][event]
 atomic(hooksfile,json.dumps(user,ensure_ascii=False,indent=2)+'\n');complete(backup,manifest)
 return dict(ok=True,authorization=authorization,backup=str(backup),system_policy=str(p),scope='Only seven UACF native hooks; existing other hooks and all sandbox/approval/network settings preserved',native_trust_database_modified=False,model_calls=0,loaded='verify through native hooks/list; running desktop reload separately observed')

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
