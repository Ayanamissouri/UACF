"""Traceable reading units. Lexical boundaries are candidates, never semantic acceptance."""
import re
from .util import Fault,sha
from .fabric import owner,save,vector,stable_id
POLICY='reading-batch4-2'

def units(text,max_chars):
    result=[]
    # Preserve every character and exact offsets, including punctuation and whitespace.
    for match in re.finditer(r'.+?(?:[。！？；\n]|$)',text,re.S):
        start,end=match.span()
        while start<end:
            stop=min(end,start+max_chars);literal=text[start:stop]
            cues=[m.group() for m in re.finditer(r'但是|不过|而且|另一点|比如|如果|有时|因此|所以|甚至|并且',literal)]
            result.append({'id':f'u:{start}:{stop}:{sha(literal)[:12]}','start':start,'end':stop,'literal':literal,'sha256':sha(literal),'boundary':'lexical_candidate','cues':cues,'semantic_verified':False})
            start=stop
    return result

def reading_plan(state,actor,args):
    owner(actor);message=state.get(args['message_id'],actor)
    if message['object_type']!='Message':raise Fault('INPUT','Message required')
    text=message['payload'].get('text')
    if not isinstance(text,str):
        content=message['payload'].get('record',{}).get('message',{}).get('content',{})
        parts=content.get('parts',[])
        if not all(isinstance(p,str) for p in parts):raise Fault('BODY_INCOMPLETE','mixed or attachment content requires explicit body selection')
        text='\n'.join(parts)
    if not isinstance(text,str) or not text:raise Fault('BODY_INCOMPLETE','literal text unavailable')
    for ambiguity in args.get('ambiguities',[]):
        if ambiguity['literal'] not in text:raise Fault('INPUT','ambiguity must point to literal source text')
        if ambiguity['status']!='unresolved':raise Fault('INPUT','confirmation requires a separately sourced current AdoptionDecision; reading plan cannot grant it')
    limit=args['max_chars'];mapped=units(text,limit);selected=args.get('unit_ids')
    if args['scope']=='whole' and selected:raise Fault('INPUT','whole scope must retain every unit')
    if args['scope']=='local' and not selected:raise Fault('INPUT','local scope requires explicit affected unit ids')
    ids={u['id'] for u in mapped}
    if selected and not set(selected)<=ids:raise Fault('INPUT','unknown affected unit')
    chosen=[u for u in mapped if not selected or u['id'] in selected]
    batches=[];group=[];size=0
    for u in chosen:
        if size+len(u['literal'])>limit and group:batches.append(group);group=[];size=0
        group.append(u['id']);size+=len(u['literal'])
    if group:batches.append(group)
    payload={'message_refs':[vector(message)],'branch':message['payload'].get('branch','main'),'claims':[],'relations':[],
        'coverage':{'logic_markers':'lexical_candidates_only','semantic_acceptance':False,'body':'literal_complete','attachments':'not_included'},
        'policy_version':POLICY,'units':mapped,'scope':args['scope'],'selected_unit_ids':[u['id'] for u in chosen],
        'reading_batches':batches,'max_chars':limit,'budget_unit':'characters; not provider tokens or capsule bytes',
        'strategy':'read_complete' if len(batches)==1 else 'segmented_original_with_traceable_summary_needed',
        'summary_status':'not_generated','summary_rule':'any future summary must name covered unit ids, omissions and unresolved interpretations',
        'ambiguities':args.get('ambiguities',[]),'ambiguity_policy':'literal unchanged; proposed interpretations are not adopted; consequential ambiguity blocks only affected action',
        'input_vector':[vector(message)]}
    oid=stable_id(POLICY,vector(message),args)
    try:obj=state.get(oid,actor)
    except Fault as e:
        if e.code!='NOT_FOUND':raise
        obj=save(state,'DiscourseState',payload,visibility=message['visibility'],oid=oid)
    return {'ok':True,'reading_plan':obj,'paid_calls':0,'source_bytes_read':0,'semantic_validation':'not_performed'}
