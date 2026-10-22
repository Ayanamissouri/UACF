"""Owner-scoped physical layout. Memory identity is independent of file placement.

This guards registered allocation/resolution, not arbitrary filesystem writes by
other programs. Frozen evidence keeps its original locator and hash.
"""
import json,re
from pathlib import Path
from .util import Fault,atomic,canonical,sha
from .state import object_new,request,uuid_ok
from .fabric import vector

KEY=re.compile(r'[a-z][a-z0-9_-]{0,63}\Z')
KINDS={'work':'.uacf/work','deliverable':'deliverables','archive':'.uacf/archives'}

def checked_root(raw):
    p=Path(raw)
    if not p.is_absolute() or not p.is_dir():raise Fault('STORAGE_ROOT','explicit existing absolute project root required')
    resolved=p.resolve(strict=True)
    if resolved==Path(resolved.anchor):raise Fault('STORAGE_ROOT','volume root is not a project')
    return resolved

def allocated_path(project_root,task_id,kind,relative=''):
    if kind not in KINDS:raise Fault('STORAGE_INPUT','known output kind required')
    uuid_ok(task_id)
    root=checked_root(project_root)
    rel=Path(relative)
    if rel.is_absolute() or '..' in rel.parts or ':' in relative or '\\' in relative:
        raise Fault('STORAGE_ESCAPE','relative POSIX output path required')
    base=root/KINDS[kind]/task_id
    target=(base/rel).resolve()
    if not target.is_relative_to(base.resolve()) or not target.is_relative_to(root):
        raise Fault('STORAGE_ESCAPE','output escapes project or follows external reparse point')
    return target

def layout(state):
    path=state.data/'storage-layout.json'
    if not path.exists():return None
    projection=json.loads(path.read_text(encoding='utf8'))
    obj=state.get(projection['ref']['object_id'],'owner')
    if vector(obj)!=projection['ref'] or obj['payload']['config']!=projection['config']:
        raise Fault('STORAGE_CHANGED','layout projection differs from canonical policy')
    return projection

def configure(state,actor,args):
    if actor!='owner' or not args.get('authorization'):raise Fault('PERMISSION','Owner output/storage authorization required')
    old=layout(state)
    if args.get('expected_layout_ref')!=(old['ref'] if old else None):raise Fault('REVISION_CONFLICT','layout changed')
    projects=args.get('projects',{});bundles=args.get('bundles',{})
    if not isinstance(projects,dict) or not projects:raise Fault('STORAGE_INPUT','explicit project map required')
    clean={}
    for key,entry in projects.items():
        if not KEY.fullmatch(key) or not isinstance(entry,dict):raise Fault('STORAGE_INPUT','project key required')
        root=checked_root(entry['root'])
        clean[key]={'root':str(root),'basis':entry.get('basis',args['authorization'])}
    roots=[x['root'] for x in clean.values()]
    if len(set(roots))!=len(roots):raise Fault('STORAGE_INPUT','project roots must be distinct')
    approved=[Path(x) for x in roots]
    mappings={}
    for key,entry in bundles.items():
        if not KEY.fullmatch(key):raise Fault('STORAGE_INPUT','bundle key required')
        dest=Path(entry['path']).resolve()
        if not any(dest.is_relative_to(root) for root in approved):raise Fault('STORAGE_ESCAPE','bundle target outside approved projects')
        if entry.get('project_key') not in clean or not dest.is_relative_to(Path(clean[entry['project_key']]['root'])):
            raise Fault('STORAGE_ESCAPE','bundle belongs to a different project')
        mappings[key]=dict(entry,path=str(dest))
    config={'version':1,'projects':clean,'bundles':mappings,'authorization':args['authorization'],
            'scope':'registered allocation, bundle resolution and task stage admission; not an OS filesystem sandbox'}
    body=canonical(config).encode()
    obj=object_new('Artifact',{'name':'Owner project storage layout','locator':'uacf:storage-layout','sha256':sha(body),'config':config},visibility='shared')
    saved=state.put(request(obj,blob=body),actor)['object']
    result={'ref':vector(saved),'config':config}
    atomic(state.data/'storage-layout.json',canonical(result))
    return {'ok':True,'layout':result,'filesystem_moved':False}

def resolve_bundle(state,key,legacy=None):
    current=layout(state)
    if current and key in current['config']['bundles']:
        return Path(current['config']['bundles'][key]['path'])
    if legacy is not None:return Path(legacy)
    raise Fault('STORAGE_UNCONFIGURED','bundle has no registered location')

def batch_path(state,name,write=False):
    """Read historical batches; require registered non-delivery storage for work.

    Legacy reads/pause remain possible while old consumers are retired. A new
    provider run or prepare cannot silently resume writing into deliverables.
    """
    if not isinstance(name,str) or not re.fullmatch(r'e7-workflow-[a-zA-Z0-9-]{1,60}',name):
        raise Fault('STORAGE_INPUT','safe prepared batch name required')
    legacy=state.root/'deliverables'/name
    current=layout(state) if (getattr(state,'data',state.root/'data')/'storage-layout.json').exists() else None
    if not current:return legacy
    entry=current['config']['bundles'].get(name)
    if not entry:
        if write:raise Fault('STORAGE_MIGRATION_REQUIRED','register batch work storage before prepare or execution; legacy status remains readable')
        return legacy
    root=checked_root(current['config']['projects'][entry['project_key']]['root'])
    target=Path(entry['path']).resolve()
    if not target.is_relative_to(root):raise Fault('STORAGE_ESCAPE','batch location escaped its registered project')
    if write and target.is_relative_to((state.root/'deliverables').resolve()):
        raise Fault('STORAGE_MIGRATION_REQUIRED','deliverables is an export surface, not a batch work directory')
    if write and state.config.get('restore_mapping'):raise Fault('STORAGE_REMAP_REQUIRED','isolated restore cannot resume original batch writes')
    return target

def task_paths(state,task):
    if state.config.get('restore_mapping'):raise Fault('STORAGE_REMAP_REQUIRED','isolated restore cannot allocate into original project roots')
    contract=task['payload'].get('output_contract')
    if not contract:raise Fault('OUTPUT_CONTRACT_REQUIRED','select actual Owner project/folder before outputs')
    current=layout(state)
    if not current:raise Fault('STORAGE_UNCONFIGURED','Owner storage layout not configured')
    key=contract.get('project_key');project=current['config']['projects'].get(key)
    if not project:raise Fault('STORAGE_PROJECT','output project is not Owner registered')
    if contract.get('project_root')!=project['root']:raise Fault('STORAGE_CHANGED','Task output root differs from Owner layout')
    return {kind:str(allocated_path(project['root'],task['object_id'],kind)) for kind in KINDS}

def dispatch(state,actor,action,args,operation_id=None):
    if action=='storage_layout_configure':return configure(state,actor,args)
    if action=='storage_layout_status':return {'ok':True,'layout':layout(state)}
    if action=='storage_bundle_resolve':
        path=resolve_bundle(state,args['bundle_key'])
        return {'ok':True,'path':str(path),'exists':path.exists(),'identity':'original object IDs/hash/locators are not rewritten'}
    if action=='storage_allocate':
        task=state.get(args['task_id'],actor)
        if task['revision']!=args['task_revision']:raise Fault('REVISION_CONFLICT','allocate for current Task revision')
        paths=task_paths(state,task);kind=args['kind']
        if kind not in paths:raise Fault('STORAGE_INPUT','unknown output kind')
        root=task['payload']['output_contract']['project_root']
        target=allocated_path(root,task['object_id'],kind,args.get('relative',''))
        return {'ok':True,'task_ref':vector(task),'path':str(target),'kind':kind,'created':False}
    raise Fault('NOT_FOUND','unknown storage action')
