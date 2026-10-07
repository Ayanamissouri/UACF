"""Read only whitelisted model metadata from the already registered export."""
import json,zipfile,collections
from pathlib import Path
from .util import Fault,file_hash,canonical,atomic,sha
from .fabric import vector
def extract(state,policy):
 from .learning import folder,save_once
 cards=[c for c in state.list('owner','SemanticCard') if c['payload'].get('semantic_contract')=='e7-semantic-1']
 sources=state.list('owner','SourceSet');groups=collections.defaultdict(list)
 for card in cards:groups[card['payload']['source_locator']['member']].append(card)
 source=next(s for s in sources if any('exports' in x for x in s['payload']['roots']));path=Path(source['payload']['roots'][0])
 if file_hash(path)!=source['payload']['authorization']['sha256']:raise Fault('SOURCE_CHANGED','registered model metadata archive changed')
 data={};counts=collections.Counter()
 with zipfile.ZipFile(path) as z:
  for member,rows in groups.items():
   if z.getinfo(member).file_size>64000000:raise Fault('LIMIT','metadata member too large')
   records=json.loads(z.read(member))
   for card in rows:
    locator=card['payload']['source_locator'];record=records[locator['ordinal']]
    if record.get('id')!=locator['native_id'] and record.get('conversation_id')!=locator['native_id']:raise Fault('SOURCE_CHANGED','metadata conversation identity mismatch')
    models=collections.Counter();nodes=[]
    for node_id,node in record.get('mapping',{}).items():
     m=node.get('message') or {};metadata=m.get('metadata') or {}
     if m.get('author',{}).get('role')!='assistant':continue
     model=metadata.get('model_slug') or metadata.get('resolved_model_slug') or record.get('default_model_slug')
     if isinstance(model,str) and 0<len(model)<=160:models[model]+=1;nodes.append(dict(node=node_id,model=model))
    row=dict(card_ref=vector(card),origin='ChatGPT export',model_counts=dict(models),node_model_tags=nodes,unrecorded_model='unknown',version_is_hint_not_exclusive_scope=True,source_ref=vector(source),source_locator=locator)
    data[card['object_id']]=row;counts.update(models)
 obj=save_once(state,'Artifact',dict(locator='learning-ai-metadata:'+sha(data),name='Historical AI metadata only; not inferred from classifier',media_type='application/json',sha256=sha(canonical(data).encode()),candidate=True,input_vector=[vector(source),policy['ref']]),['ai-metadata',sha(data)],canonical(data).encode())
 atomic(folder(state)/'ai-metadata.json',canonical(dict(artifact_ref=vector(obj),cards=data)))
 return dict(ok=True,sources=len(data),with_recorded_models=sum(bool(x['model_counts']) for x in data.values()),model_message_counts=dict(counts),artifact_ref=vector(obj),unknown_not_inferred=True)
