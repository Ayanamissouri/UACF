"""Owner's permanent asset-use view, reading the same runtime indexes and evidence."""
import json,collections
from .learning_use import issue_index
from .learning_semantic import overview,annotations
from .learning_guards import CONTRACTS
from .fabric import vector
from .util import Fault,canonical
def inspect(state,args):
 from .learning import folder
 query=args.get('query','');offset=args.get('offset',0);limit=args.get('limit',20);kind=args.get('kind','issues')
 if not isinstance(query,str) or len(query)>200 or type(offset)!=int or offset<0 or type(limit)!=int or not 1<=limit<=50:raise Fault('INPUT','bounded inspect query and page')
 idx=issue_index(state);reviewed=annotations(state);rows=[]
 if kind=='knowledge':
  path=folder(state)/'recall.json';data=json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
  for entry in data.values():
   for item in entry['knowledge']:
    if query.lower() in canonical(item).lower():rows.append(dict(kind='knowledge',card_ref=entry['card_ref'],attempt_ref=entry['attempt_ref'],**item))
 else:
  for row in idx.values():
   if query.lower() in canonical(row).lower():rows.append(row)
 from .learning import candidate_input,comparison_snapshot
 job_map={}
 for path in (folder(state)/'jobs').glob('*.json'):
  job=json.loads(path.read_text());job_map[job.get('card_ref',{}).get('object_id')]=job
 snapshot=comparison_snapshot(state) if rows[offset:offset+limit] else None
 selected=[]
 for row in rows[offset:offset+limit]:
  card=state.get(row['card_ref']['object_id'],'owner');attempt=state.get(row['attempt_ref']['object_id'],'owner')
  if vector(card)!=row['card_ref'] or vector(attempt)!=row['attempt_ref']:raise Fault('SOURCE_CHANGED','asset use index stale; refresh index instead of hiding revision change')
  receipt_job=job_map.get(row['card_ref']['object_id'])
  ai_origin=candidate_input(state,receipt_job,snapshot)['ai_origin'] if receipt_job else dict(classifier='unknown: no source job receipt')
  item=dict(row,title=card['payload'].get('catalog_title') or card['payload'].get('summary',''),ai_origin=ai_origin,layer='上下文候选与来源入口；不自动成为硬规则')
  if row.get('case_ref'):
   case=state.get(row['case_ref']['object_id'],'owner')
   if vector(case)!=row['case_ref']:raise Fault('SOURCE_CHANGED','case revision changed')
   item.update(semantic_reviews=reviewed.get(case['object_id'],[]),classification=next((x for x in attempt['payload']['assessment']['issues'] if x['case_id']==case['object_id']),None))
  selected.append(item)
 guards=[];p=folder(state)/'guards.json';registered=json.loads(p.read_text(encoding='utf8')) if p.exists() else {}
 names={'source_quotes':('原文引用一致','检查输出中的引用是否确实存在；不能验证语义或未读图像'), 'registered_validation':('交付前验收','检查当前Task修订和冻结环境的注册Validation；不是模型自称正确'), 'protected_assets':('修改不破坏基线','检查Owner预声明受保护文件hash；不覆盖任意宿主写入'), 'settled_receipts':('未知结果不重跑','检查费用/派发状态；不是事后总结中的提醒'), 'required_work_steps':('必需工序不得遗漏','仅在已声明的逐工序合同上检查注册验收；未声明要求无法自动理解')}
 for ref in registered.get('pattern_refs',[]):
  obj=state.get(ref['object_id'],'owner');key=obj['payload']['lesson'];label,meaning=names[key]
  guards.append(dict(name=label,key=key,ref=ref,scope=CONTRACTS[key]['scope'],meaning=meaning,constrains_private_thinking=False,gate='已注册执行/交付边界',active=obj['status']!='superseded'))
 semantic=overview(state,dict(query=args.get('pair_query',''),limit=5,reviewed_only=True))
 metadata=folder(state)/'ai-metadata.json';ai={}
 if metadata.exists():
  m=json.loads(metadata.read_text(encoding='utf8'));ai=dict(recorded_sources=sum(bool(x['model_counts']) for x in m['cards'].values()),unknown_sources=sum(not x['model_counts'] for x in m['cards'].values()),origin='历史原AI元数据统计；实际分类模型逐条见回执与来源详情',model_counts=dict(collections.Counter(k for x in m['cards'].values() for k in x['model_counts'])))
 recall_path=folder(state)/'recall.json'
 recall=json.loads(recall_path.read_text(encoding='utf8')) if recall_path.exists() else {}
 source_ids={x['card_ref']['object_id'] for x in recall.values()} | {x['card_ref']['object_id'] for x in idx.values()}
 return dict(ok=True,overview=dict(sources=len(source_ids),issues=len(idx),knowledge=sum(len(x['knowledge']) for x in recall.values()),raw_extraction_repeated=False,semantic_complete=False,automation='有明确宿主映射和公开工作事件才可形成来源；重要纠错可先记录候选，短日常按工作节点聚合；自动结束送达须现场验证',effect='准备、送达、实际使用、正常结束回填和效率改善分别验收；未观察不报成功'),guards=guards,ai=ai,semantic=semantic,kind=kind,total=len(rows),offset=offset,rows=selected)
