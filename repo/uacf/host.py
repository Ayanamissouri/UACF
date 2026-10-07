"""Bounded host configuration edits with compare-before-rollback backups."""
import json, os, shutil, subprocess, sys, tomllib
from pathlib import Path
import yaml
from .state import State
from .service import call
from .util import Fault, atomic, canonical, file_hash, now, uid

def homes(a):
    return Path(a.home or os.environ.get('DSH_HOME' if a.host=='dsh' else 'CODEX_HOME') or Path.home()/('.dsh-research' if a.host=='dsh' else '.codex')).resolve()
def backup_config(root,host,paths):
    dest=root/'backups'/('host-'+host+'-'+uid()); dest.mkdir(parents=True)
    rows=[]
    for i,p in enumerate(paths):
        p=Path(p); row={'path':str(p),'existed':p.exists(),'backup':str(dest/f'{i}.original')}
        if p.exists(): shutil.copyfile(p,row['backup']); row['before_hash']=file_hash(p)
        rows.append(row)
    manifest={'host':host,'created_at':now(),'files':rows,'status':'prepared'}
    atomic(dest/'manifest.json',canonical(manifest)); return dest,manifest
def complete(dest,manifest):
    for r in manifest['files']: r['after_hash']=file_hash(r['path']) if Path(r['path']).exists() else None
    manifest['status']='applied'; atomic(dest/'manifest.json',canonical(manifest))
def host_command(root,a):
    root=Path(root).resolve(); home=homes(a); state=State(root)
    if a.operation=='probe':
        if a.host=='dsh':
            profile=home/'profiles/web'; package=profile/'package.json'
            d=json.loads(package.read_text()) if package.exists() else {}
            return {'ok':home.exists(),'home':str(home),'profile':str(profile),'dependencies':d.get('dependencies',{}),'bundles':d.get('dsh',{}).get('profile',{}).get('bundles',[]),'loaded':'unknown; use authenticated verify','config_hashes':{p.name:file_hash(p) for p in [package,profile/'pnpm-lock.yaml',profile/'cordis.patch.yml'] if p.exists()},'legacy_installed_root':str(home/'_multi_ai'),'governor_source':d.get('dependencies',{}).get('dsh-workbench-governor')}
        config=home/'config.toml'; d=tomllib.loads(config.read_text(encoding='utf-8-sig')) if config.exists() else {}
        return {'ok':home.exists(),'home':str(home),'local_sessions_exist':(home/'sessions').is_dir(),'sqlite_exists':(home/'state_5.sqlite').is_file(),
         'model_context_window':d.get('model_context_window','auto'),'auto_compact':d.get('model_auto_compact_token_limit','model default'),
         'mcp_configured':'uacf' in d.get('mcp_servers',{}),'current_desktop_loaded':'unknown'}
    if a.operation=='verify':
        if a.host=='dsh': return call(root,'verify_dsh',{'task_id':a.task,'revision':a.revision})
        # Real native Codex CLI config parser, not a mock client.
        process=subprocess.run(['cmd.exe','/d','/c','codex.cmd','mcp','get','uacf','--json'],capture_output=True,text=True,encoding='utf-8',timeout=30)
        if process.returncode: raise Fault('HOST_CONFIG','native codex mcp get failed')
        d=json.loads(process.stdout)
        return {'ok':True,'native_config':d,'current_desktop_loaded':'unknown; next session/reload required','scope':'native CLI configuration only'}
    if a.operation=='rollback':
        candidates=sorted((root/'backups').glob('host-'+a.host+'-*/manifest.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        selected=None
        for p in candidates:
            m=json.loads(p.read_text())
            if m['status']=='applied': selected=(p,m); break
        if not selected: raise Fault('NOT_FOUND','no applied host configuration backup')
        p,m=selected
        for r in m['files']:
            f=Path(r['path'])
            current=file_hash(f) if f.exists() else None
            if current!=r['after_hash']: raise Fault('CONFIG_CONFLICT','host config changed after installation; rollback refuses overwrite')
        for r in m['files']:
            if r['existed']: atomic(r['path'],Path(r['backup']).read_bytes())
            elif Path(r['path']).exists():
                # Preserve newly created configuration as an inert backup rather than deleting it.
                Path(r['path']).rename(p.parent/(Path(r['path']).name+'.uninstalled'))
        m['status']='rolled_back'; atomic(p,canonical(m))
        return {'ok':True,'backup':str(p),'data_preserved':True,'reload_required':True}
    if a.operation=='reload':
        if a.host!='dsh': raise Fault('HOST_CAPABILITY','Codex active desktop reload is not a verified tool capability')
        p=home/'profiles/web/cordis.patch.yml'; rows=yaml.safe_load(p.read_text(encoding='utf-8-sig')) or []
        owned=[r for e in rows if isinstance(e,dict) for r in e.get('insert',[]) if isinstance(r,dict) and r.get('id')=='uacf-continuity-v1']
        if len(owned)!=1: raise Fault('HOST_CONFIG','exactly one owned UACF mount required')
        dest,m=backup_config(root,a.host,[p]); owned[0]['config']['reloadNonce']=uid()
        atomic(p,yaml.safe_dump(rows,sort_keys=False)); complete(dest,m)
        return {'ok':True,'live_reload_requested':True,'backup':str(dest),'verified':'pending authenticated canary'}
    if a.operation=='context':
        if not a.tokens or a.tokens<=0: raise Fault('INPUT','positive --tokens required')
        if a.host=='codex':
            p=home/'config.toml'; original=p.read_text(encoding='utf-8-sig'); lines=original.splitlines(); output=[]; replaced=False
            for line in lines:
                if line.strip().startswith('model_context_window') and '=' in line and not replaced:
                    output.append('model_context_window = '+str(a.tokens)); replaced=True
                else: output.append(line)
            if not replaced: output.insert(0,'model_context_window = '+str(a.tokens))
            text='\n'.join(output)+'\n'; tomllib.loads(text)
        else:
            p=home/'settings.yaml'; original=p.read_text(encoding='utf-8-sig'); d=yaml.safe_load(original)
            section=d.setdefault('llm-deepseek',{})
            # Public installed dsh-llm-deepseek Config declares defaultContextWindow and models[].contextWindow.
            section['defaultContextWindow']=a.tokens
            models=section.get('models')
            if models is None:
                # Read the exact currently resolved catalog through the authenticated public adapter seam.
                # No guessed model IDs or lost modality/capacity metadata.
                import urllib.request
                auth=json.loads((state.data/'auth.json').read_text())
                q=urllib.request.Request(state.config['dsh_url']+'/uacf/v1/canary',data=canonical({'nonce':uid()}).encode(),headers={'Authorization':'Bearer '+auth['owner'],'Content-Type':'application/json'})
                with urllib.request.urlopen(q,timeout=15) as response: probe=json.load(response)
                models=probe.get('context_profile',{}).get('catalog')
                if not models: raise Fault('HOST_CAPABILITY','resolved model catalog unavailable; no guessed entries')
                section['models']=models
            selected=d.get('agent-default-model',{}).get('model')
            found=False
            for model in models:
                if model.get('id')==selected: model['contextWindow']=a.tokens; found=True
            if not found: raise Fault('HOST_CAPABILITY','selected model missing from configured catalog; no guessed entry')
            text=yaml.safe_dump(d,allow_unicode=True,sort_keys=False)
        dest,m=backup_config(root,a.host,[p]); atomic(p,text); complete(dest,m)
        return {'ok':True,'backup':str(dest),'requested_tokens':a.tokens,'effective':'unknown until consumer reload/canary'}
    if a.operation!='install': raise Fault('UNSUPPORTED','unknown host operation')
    if a.host=='codex':
        p=home/'config.toml'; original=p.read_text(encoding='utf-8-sig') if p.exists() else ''
        d=tomllib.loads(original)
        if 'uacf' in d.get('mcp_servers',{}): return {'ok':True,'already_configured':True,'current_desktop_loaded':'unknown'}
        python=str(root/'repo/.venv/Scripts/python.exe'); repo=str(root/'repo')
        # JSON-quoted strings are valid TOML basic strings; no shell command interpolation.
        text=original+'\n[mcp_servers.uacf]\ncommand = '+json.dumps(python)+'\nargs = '+json.dumps(['-m','uacf','--root',str(root),'mcp','--host','codex'])+'\ncwd = '+json.dumps(repo)+'\nenabled = true\n'
        tomllib.loads(text); dest,m=backup_config(root,a.host,[p]); atomic(p,text); complete(dest,m)
        return {'ok':True,'configured':True,'backup':str(dest),'current_desktop_loaded':'unknown','reload_required':True}
    profile=home/'profiles/web'; p=profile/'package.json'; d=json.loads(p.read_text())
    target=root/'repo/adapters/dsh'; dependency='link:'+target.as_posix()
    existing_patch=yaml.safe_load((profile/'cordis.patch.yml').read_text(encoding='utf-8-sig')) or []
    mounted=any(any(r.get('id')=='uacf-continuity-v1' for r in e.get('insert',[]) if isinstance(r,dict)) for e in existing_patch if isinstance(e,dict))
    if d.get('dependencies',{}).get('dsh-uacf')==dependency and mounted:
        return {'ok':True,'already_configured':True,'loaded':'verify separately'}
    dest,m=backup_config(root,'dsh',[p,profile/'pnpm-lock.yaml',profile/'cordis.patch.yml'])
    d.setdefault('dependencies',{})['dsh-uacf']=dependency
    bundles=d['dsh']['profile']['bundles']
    # Mount once through the profile's live patch, never also as a bundle insertion.
    if 'dsh-uacf' in bundles: bundles.remove('dsh-uacf')
    # Plugin bundle root is generated from selected root, not a hardcoded data identity.
    patch=[{'insert':[{'id':'uacf-continuity-v1','name':'dsh-uacf','inject':['tools','webServer'],'config':{'root':root.as_posix()}}]}]
    atomic(target/'cordis.patch.yml',yaml.safe_dump(patch,sort_keys=False))
    atomic(p,json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    result=subprocess.run(['cmd.exe','/d','/c','pnpm.cmd','install','--offline'],cwd=profile,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    if result.returncode:
        # Restore only our prepared configuration; no asset or existing package removal.
        for r in m['files']:
            if r['existed']: atomic(r['path'],Path(r['backup']).read_bytes())
        m['status']='failed_restored'; atomic(dest/'manifest.json',canonical(m))
        atomic(root/'logs/dsh-install-failure.log',result.stdout+'\n'+result.stderr)
        raise Fault('INSTALL_FAILED','pnpm offline install failed; configs restored; local log retained')
    if not mounted:
        # Preserve the existing privacy overlay byte-for-byte; append our registered row.
        overlay=(profile/'cordis.patch.yml').read_text(encoding='utf-8-sig')
        atomic(profile/'cordis.patch.yml',overlay+'\n# UACF owned live mount; no bundle duplicate.\n'+yaml.safe_dump(patch,sort_keys=False))
    complete(dest,m)
    return {'ok':True,'installed_path':str(target),'backup':str(dest),'loaded':'unknown; live reload or managed restart then verify','plugin_hash':file_hash(target/'index.js')}
