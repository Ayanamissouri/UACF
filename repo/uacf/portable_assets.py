"""Separate reusable public lessons from private provenance; never export raw assets."""
import json,re
from .util import Fault,canonical,sha
from .state import object_new,request
from .fabric import vector

VERSION='uacf-portable-lessons-1'
FIELDS={'slug','kind','title','principle','applicable','excluded','positive_example','negative_example','topics','confidence','limitations'}
PRIVATE=re.compile(r'(?:[A-Z]:[\\/]|(?:sk-|Bearer\s+)[A-Za-z0-9_-]{16,}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://(?:127\.0\.0\.1|localhost)|\b\d{8,}\b)',re.I)
def language(value):
 if not isinstance(value,dict) or set(value)!={'zh','en'} or any(not isinstance(s,str) or not 1<=len(s)<=1200 for s in value.values()):raise Fault('INPUT','bounded Chinese/English prose required')
def validate(card):
 if not isinstance(card,dict) or set(card)!=FIELDS:raise Fault('INPUT','exact public fields; no private ref, locator, model or source quote')
 if not re.fullmatch(r'[a-z][a-z0-9-]{2,64}',card['slug']) or card['kind'] not in ['context','principle','registered_guard_description']:raise Fault('INPUT','public slug and asset kind')
 for k in ['title','principle','applicable','excluded','positive_example','negative_example','limitations']:language(card[k])
 if card['confidence'] not in ['provisional','host_reviewed','registered_finite_scope']:raise Fault('INPUT','bounded confidence, never universal truth')
 if not isinstance(card['topics'],list) or not 1<=len(card['topics'])<=8 or any(not isinstance(x,str) or not re.fullmatch('[a-z][a-z0-9-]{1,40}',x) for x in card['topics']):raise Fault('INPUT','generic public topics')
 if PRIVATE.search(canonical(card)):raise Fault('PRIVACY','public projection contains identifier, credential, local path or contact marker')
 return card
def current_sources(state,refs):
 if not isinstance(refs,list) or not 1<=len(refs)<=32:raise Fault('INPUT','bounded existing source refs')
 for ref in refs:
  if not isinstance(ref,dict) or set(ref)!={'object_id','revision'}:raise Fault('INPUT','exact source reference')
  obj=state.get(ref['object_id'],'owner')
  if vector(obj)!=ref:raise Fault('DEPENDENCY_STALE','source revised; no automatic re-extraction')
  if obj['object_type'] not in ['FailureCase','SemanticCard','FailurePattern','Evidence','Artifact','Relation']:raise Fault('INPUT','source-derived lesson required')
def refs(state):
 with state.db() as c:
  return [dict(object_id=x[0],revision=x[1]) for x in c.execute("select o.id,o.head from objects o join object_revisions v on v.object_id=o.id and v.revision=o.head where o.type='Artifact' and json_extract(v.envelope,'$.payload.portable_schema')=?",(VERSION,))]
def read_module(state,actor,ref):
 obj=state.get(ref['object_id'],actor)
 if obj['object_type']!='Artifact' or obj['payload'].get('portable_schema')!=VERSION or vector(obj)!=ref:raise Fault('REVISION_CONFLICT','exact current portable module')
 import base64
 body=base64.b64decode(state.fetch_blob(actor,obj['object_id'],obj['revision'],65536)['base64'])
 if sha(body)!=obj['payload']['sha256']:raise Fault('HASH','portable snapshot differs')
 card=json.loads(body);validate(card);return obj,card
def draft(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','owner-authorized private derivation only')
 if set(args)!={'card','source_refs','derivation_basis'} or not isinstance(args['derivation_basis'],str) or not 1<=len(args['derivation_basis'])<=2000:raise Fault('INPUT','public card, existing private refs and derivation basis required')
 card=validate(args['card']);current_sources(state,args['source_refs'])
 # Slug collision must be an explicit revision, never accidental merging.
 for ref in refs(state):
  obj,old=read_module(state,'owner',ref)
  if old['slug']==card['slug']:raise Fault('ALREADY_EXISTS','use explicit current module revision, do not duplicate principle')
 body=canonical(card).encode();obj=object_new('Artifact',{'locator':'portable-lesson:'+card['slug'],'sha256':sha(body),'media_type':'application/json','name':card['title']['zh'],'portable_schema':VERSION,'public_slug':card['slug'],'disclosure':'draft','private_source_refs':args['source_refs'],'derivation_basis':args['derivation_basis'],'input_vector':args['source_refs'],'examples':'synthetic, not private original quotations','semantic_adoption':False},visibility='private')
 saved=state.put(request(obj,blob=body),'owner')['object'];return {'ok':True,'module_ref':vector(saved),'disclosure':'draft','source_reextraction':False,'provider_calls':0}
def review(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','local review uses owner-authorized scope')
 if set(args)!={'module_ref','basis','public_content_hash'} or not isinstance(args['basis'],str) or not 1<=len(args['basis'])<=2000:raise Fault('INPUT','current module and explicit review basis required')
 obj,card=read_module(state,actor,args['module_ref']);current_sources(state,obj['payload']['private_source_refs'])
 if args['public_content_hash']!=obj['payload']['sha256']:raise Fault('HASH','review a concrete public snapshot')
 obj['payload'].update(disclosure='host_reviewed_candidate',disclosure_review_basis=args['basis'],human_release_approval=False)
 saved=state.put(request(obj,expected=obj['revision']),'owner')['object'];return {'ok':True,'module_ref':vector(saved),'upload_authorized':False,'semantic_adoption':False}
def revise(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','owner-authorized local revision only')
 if set(args)!={'module_ref','card','source_refs','derivation_basis'}:raise Fault('INPUT','explicit revision and new derivation required')
 obj,old=read_module(state,actor,args['module_ref']);card=validate(args['card']);current_sources(state,args['source_refs'])
 if card['slug']!=old['slug'] or not isinstance(args['derivation_basis'],str) or not 1<=len(args['derivation_basis'])<=2000:raise Fault('INPUT','preserve principle identity and bounded revision basis')
 body=canonical(card).encode();obj['payload'].update(sha256=sha(body),private_source_refs=args['source_refs'],input_vector=args['source_refs'],derivation_basis=args['derivation_basis'],disclosure='draft',human_release_approval=False)
 saved=state.put(request(obj,expected=obj['revision'],blob=body),actor)['object'];return {'ok':True,'module_ref':vector(saved),'disclosure':'draft','source_reextraction':False,'provider_calls':0}
def overview(state,actor,args):
 if actor not in ['owner','reader']:raise Fault('PERMISSION','private source mapping is not public host access')
 rows=[]
 for ref in refs(state):
  obj,card=read_module(state,actor,ref);rows.append({'module_ref':ref,'card':card,'disclosure':obj['payload']['disclosure'],'public_content_hash':obj['payload']['sha256'],'private_link_count':len(obj['payload']['private_source_refs'])})
 return {'ok':True,'rows':rows,'raw_assets_exported':False,'provider_calls':0,'automatic_privacy_guarantee':False}
def links(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','local private provenance only')
 obj,card=read_module(state,actor,args['module_ref']);current_sources(state,obj['payload']['private_source_refs'])
 return {'ok':True,'slug':card['slug'],'source_refs':obj['payload']['private_source_refs'],'basis':obj['payload']['derivation_basis'],'scope':'private local resolution; never include this response in public bundle'}

def source_detail(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','original conditions remain local and private')
 if set(args)!={'module_ref','source_ref'}:raise Fault('INPUT','select one exact linked source')
 obj,card=read_module(state,actor,args['module_ref']);current_sources(state,obj['payload']['private_source_refs'])
 if args['source_ref'] not in obj['payload']['private_source_refs']:raise Fault('PERMISSION','source is not linked to this module')
 source=state.get(args['source_ref']['object_id'],actor);payload=source['payload']
 selected={k:payload[k] for k in ['name','summary','catalog_title','case_details','source','lesson','conditions','applicable','excluded','observation','derivation_basis'] if k in payload}
 # Read one selected object, not the whole case corpus. Bounds are explicit.
 body=canonical(selected);truncated=len(body.encode())>24000
 if truncated:selected={'bounded_preview':body.encode()[:24000].decode('utf-8',errors='ignore'),'truncated':True}
 return {'ok':True,'source_ref':vector(source),'object_type':source['object_type'],'conditions':selected,'dependency_refs':payload.get('input_vector',[])[:32],'truncated':truncated,'scope':'private original conditions; never exported; candidate interpretation is not domain truth'}

def import_bundle(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','local owner selects imported guidance')
 if set(args)!={'bundle','license_basis'} or not isinstance(args['license_basis'],str) or not 1<=len(args['license_basis'])<=2000:raise Fault('INPUT','explicit public bundle and license basis required')
 bundle=args['bundle']
 keys={'schema','purpose','cards','source_links','hard_rule_adoption','privacy_review','license'}
 if not isinstance(bundle,dict) or set(bundle)!=keys or bundle['schema']!=VERSION or bundle['hard_rule_adoption'] is not False:raise Fault('INPUT','supported advisory bundle; no executable adoption')
 if not isinstance(bundle['cards'],list) or not 1<=len(bundle['cards'])<=64 or len(canonical(bundle).encode())>262144:raise Fault('LIMIT','bounded public bundle')
 if any(not isinstance(bundle[k],str) or len(bundle[k])>1000 for k in keys-{'schema','cards','hard_rule_adoption'}):raise Fault('INPUT','bounded disclosure and license strings')
 if PRIVATE.search(canonical(bundle)):raise Fault('PRIVACY','import must contain only a public projection')
 cards=[validate(x) for x in bundle['cards']]
 if len({x['slug'] for x in cards})!=len(cards):raise Fault('INPUT','duplicate imported slug')
 existing={}
 for ref in refs(state):
  obj,card=read_module(state,actor,ref);existing[card['slug']]=(obj,card)
 for card in cards:
  if card['slug'] in existing and existing[card['slug']][1]!=card:raise Fault('ALREADY_EXISTS','different existing principle requires explicit revision; nothing imported')
 from .learning import save_once
 body=canonical(bundle).encode();digest=sha(body)
 src=save_once(state,'Artifact',{'locator':'public-lesson-import:'+digest,'sha256':digest,'media_type':'application/json','name':'Selected public advisory bundle','license_basis':args['license_basis'],'origin':'imported public projection, not this owner private historical conversation','input_vector':[]},['portable-import',digest,args['license_basis']],body)
 rows=[]
 for card in cards:
  if card['slug'] in existing:rows.append({'module_ref':vector(existing[card['slug']][0]),'state':'unchanged_existing'});continue
  rows.append({**draft(state,actor,{'card':card,'source_refs':[vector(src)],'derivation_basis':'Imported advisory bundle. '+args['license_basis']}),'state':'draft_requires_local_review'})
 return {'ok':True,'rows':rows,'source_ref':vector(src),'provider_calls':0,'hard_rule_adoption':False,'local_review_required':True}
def export(state,actor,args):
 if actor!='owner':raise Fault('PERMISSION','explicit local review export only')
 selected=args.get('module_refs')
 if set(args)!={'module_refs'} or not isinstance(selected,list) or not 1<=len(selected)<=64:raise Fault('INPUT','select bounded current reviewed modules')
 cards=[]
 for ref in selected:
  obj,card=read_module(state,actor,ref);current_sources(state,obj['payload']['private_source_refs'])
  if obj['payload']['disclosure']!='host_reviewed_candidate':raise Fault('REVIEW_REQUIRED','unreviewed private derivation is not exportable')
  cards.append(card)
 if len({x['slug'] for x in cards})!=len(cards):raise Fault('INPUT','duplicate principle slug')
 license_file=state.root/'repo/LICENSE'
 selected_license=state.config.get('project_license','project owner choice pending')
 if selected_license=='project owner choice pending' and license_file.exists() and re.search(r'Apache License\s+Version 2\.0',license_file.read_text(encoding='utf-8')):selected_license='Apache-2.0'
 bundle={'schema':VERSION,'purpose':'reusable advisory lessons with synthetic examples','cards':cards,'source_links':'local private registry only; absent in distribution','hard_rule_adoption':False,'privacy_review':'host-reviewed candidate; human release scope approval pending','license':selected_license}
 return {'ok':True,'bundle':bundle,'sha256':sha(canonical(bundle).encode()),'upload_authorized':False}
def dispatch(state,actor,action,args):
 fn={'portable_draft':draft,'portable_revise':revise,'portable_review':review,'portable_overview':overview,'portable_links':links,'portable_source_detail':source_detail,'portable_import':import_bundle,'portable_export':export}.get(action)
 if not fn:raise Fault('INPUT','unknown portable operation')
 return fn(state,actor,args)
def context(state,task):
 """Bounded public advisory text; no private source locator or existence counts."""
 query=task['payload'].get('goal','').lower();rows=[];used=0
 for ref in refs(state):
  obj,card=read_module(state,'owner',ref)
  if obj['payload']['disclosure']!='host_reviewed_candidate':continue
  try:current_sources(state,obj['payload']['private_source_refs'])
  except Fault:continue
  text=canonical(card).lower();words=set(re.findall(r'[a-z][a-z0-9-]{2,}',query));words.update(query[i:i+2] for i in range(len(query)-1) if all('\u4e00'<=c<='\u9fff' for c in query[i:i+2]))
  if not any(w in text for w in words):continue
  entry={'slug':card['slug'],'principle':card['principle'],'applicable':card['applicable'],'excluded':card['excluded'],'limitations':card['limitations'],'adoption':'candidate guidance; validate conditions, not an executable permission'};size=len(canonical(entry).encode())
  if used+size>4000:continue
  rows.append(entry);used+=size
  if len(rows)==3:break
 return {'lessons':rows,'assembled_bytes':used,'actual_use':'not inferred from retrieval','private_links':'not delivered'}
