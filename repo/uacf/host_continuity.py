"""Native observations have their own directory projection; never create Affiliation."""
import json
from .util import Fault

def observe(state,actor,args):
    host=args.get('host');session=args.get('native_session_id');after=args.get('after_rowid',0);limit=args.get('limit',50)
    if host not in ['dsh','codex','pi'] or type(after)!=int or after<0 or type(limit)!=int or not 1<=limit<=100:
        raise Fault('INPUT','explicit native host and bounded cursor required')
    if actor not in ['owner',host]:raise Fault('PERMISSION','private native archive is restricted to its host and owner')
    events=[];directory={};cursor=after
    with state.db() as c:
        for row in c.execute('SELECT rowid,payload FROM host_events WHERE source_host=? ORDER BY rowid',(host,)):
            e=json.loads(row['payload']);p=e['payload'];sid=p.get('native_session_id')
            if session and sid!=session:continue
            if p.get('kind')=='native_organization':
                directory.setdefault(sid,{}).update({k:v for k,v in p.items() if k.startswith('native_')})
                directory[sid].update(observed_at=e['observed_at'],source_version=p.get('source_version'),semantic_affiliation_changed=False)
            if row['rowid']>after and len(events)<limit:
                events.append({'rowid':row['rowid'],**e});cursor=row['rowid']
    return {'ok':True,'host':host,'events':events,'next_cursor':cursor,'native_directory':directory,'semantic_affiliation_modified':False,
            'coverage':'explicitly mapped sessions only; raw hook events are not semantic interpretation'}
