"""Human archive view of canonical facts, never title-derived semantic grading."""
import html,json
from collections import defaultdict
from .util import atomic,canonical

def render_directory(state,actor,plan,cov):
 pid=cov['plan_id'];dest=state.data/'archive'/pid/'directory';dest.mkdir(parents=True,exist_ok=True)
 with state.db() as c:
  rows=[dict(r) for r in c.execute('SELECT member,ordinal,native_id,title,stats FROM archive_conversations WHERE plan_id=? ORDER BY member,ordinal',(pid,))]
 objects=state.list(actor);byid={o['object_id']:o for o in objects};selected=defaultdict(list)
 for card in objects:
  if card['object_type']!='SemanticCard':continue
  unit=byid.get(card['payload'].get('work_unit_id'))
  if not unit:continue
  for ref in unit['payload'].get('message_refs',[]):
   message=byid.get(ref['object_id']);loc=(message or {}).get('payload',{}).get('locator',{})
   if isinstance(loc,dict) and loc.get('archive_plan')==pid:
    selected[(loc['member'],loc['ordinal'])].append((card,unit,message))
 def esc(x):return html.escape(str(x))
 style='body{max-width:1100px;margin:30px auto;padding:20px;font:17px/1.8 system-ui;color:#183c4b;background:#f3f6f8}article,section{background:white;padding:22px;margin:18px 0;border-radius:10px}h2{font-size:22px}.badge{background:#e6edf2;border-radius:5px;padding:3px 8px;font-size:14px}details{margin-top:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}input,select{font:inherit;padding:8px}a{color:#156075}'
 def page(title,body):return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>'+style+'</style><h1>'+esc(title)+'</h1>'+body+'</html>'
 links=[]
 for member in plan['members']:
  subset=[r for r in rows if r['member']==member];name=member+'.html';n=sum(bool(selected[(r['member'],r['ordinal'])]) for r in subset)
  links.append('<li><a href="'+esc(name)+'">第 '+str(len(links)+1)+' 页 · '+str(len(subset))+' 个对话</a>，其中 '+str(n)+' 个有选中片段（仍未完成整段理解）</li>')
  body='<p><a href="index.html">返回总览</a></p><p>这是一份保存与处理进度目录。标题不是领域标签；“没有错误判断”不等于“没有错误”。历史素材不能直接成为当前命令。</p><label>搜索标题 <input id="query" placeholder="例如：数学、代码、crew cabin"></label> <label>处理进度 <select id="filter"><option value="all">全部</option><option value="selected">有选中片段</option><option value="stored">只完成保存</option></select></label><p id="count"></p>'
  for r in subset:
   cards=selected[(r['member'],r['ordinal'])];status='selected' if cards else 'stored';title=r['title'] or '原件未提供标题'
   body+='<article data-stage="'+status+'" data-title="'+esc(title).lower()+'"><h2>'+esc(title)+'</h2><span class="badge">'+('有来源卡片，待理解与核验' if cards else '原文已保存，尚未分析')+'</span><p><b>它讲了哪些领域？</b> 尚未完成多领域判断。可以同时属于数学、物理、金融等；本目录不按标题硬分。</p><p><b>哪些内容进入错题本？</b> 尚未完成本对话逐段错误判断；不能判定代码、理解、执行、表达或输入转录中的哪一类有问题。</p><p><b>以后怎么用？</b> 可定位并查阅原文。尚不能把本对话当作已验证知识、可靠摘要或当前动作授权。</p>'
   if cards:
    seen=set()
    for card,unit,message in cards:
     if card['object_id'] in seen:continue
     seen.add(card['object_id']);text=message['payload'].get('text','');text=text if isinstance(text,str) else canonical(text)
     body+='<details><summary>已选中的片段：'+esc(unit['payload']['purpose'])+'</summary><p>来源卡现有说明：'+esc(card['payload']['summary'])+'</p><p>原文预览（最多600字符，不是摘要）：</p><pre>'+esc(text[:600])+'</pre><p>该片段有正文定位；附件是否包含与图像理解仍需分别核验。</p><p>卡片修订 '+str(card['revision'])+'，对象 '+esc(card['object_id'])+'</p></details>'
   body+='<details><summary>查看来源定位与结构证据</summary><p>'+esc(member)+'，对话序号 '+str(r['ordinal'])+'，原始 ID '+esc(r['native_id'])+'</p><pre>'+esc(r['stats'])+'</pre></details></article>'
  body+='<script>function filter(){const q=document.getElementById("query").value.toLowerCase(),f=document.getElementById("filter").value;let n=0;document.querySelectorAll("article").forEach(a=>{a.hidden=!(a.dataset.title.includes(q)&&(f==="all"||a.dataset.stage===f));if(!a.hidden)n++});document.getElementById("count").textContent="当前显示 "+n+" 个对话"}document.getElementById("query").addEventListener("input",filter);document.getElementById("filter").addEventListener("change",filter);filter();</script>'
  atomic(dest/name,page('旧库阅读目录 · 第 '+str(len(links))+' 页',body))
 picked=sum(bool(selected[(r['member'],r['ordinal'])]) for r in rows)
 overview='<section><h2>先看：现在到底处理到哪一步</h2><p>'+str(len(rows))+' 个对话已完成结构保存与定位；'+str(picked)+' 个对话含有被选中的来源片段。选中不代表整段已理解。全量跨领域标签、逐段错题判断和语义摘要尚未完成。</p><p>因此本目录不会显示虚构的“数学已归类”“代码已入错题本”或“适合直接采纳”。保存层与理解层的差距是真实未完成的工作。</p><p><a href="../../../../../deliverables/UACF_实际架构与日常使用说明.html">系统怎样处理知识、错误与后续工作</a></p></section><section><h2>阅读每个对话时可以直接看到</h2><p>①它是否只完成保存；②是否有选中片段；③领域判断和错题判断是否已做；④能否作可靠知识或当前授权使用；⑤需要时才展开机器定位和hash。</p><p>领域、工作目标、错误类别和证据状态应是并列维度，不是把整个对话锁进一个数字分类。细标签必须绑定具体原文及判断依据。</p></section><section><h2>分页浏览</h2><ul>'+''.join(links)+'</ul></section><section><h2>附件与收费工作</h2><p>24 个精确关联附件正文已经读取并核对内容身份；大部分附件正文和独立语义判断尚未完成。未解析引用保留未知，不凭文件名猜图。</p><p>新增收费调用0；第四批预算45元。没有当次实际价格能力核验，就不能收费派发。</p><details><summary>展开技术覆盖回执</summary><pre>'+esc(json.dumps(cov,ensure_ascii=False,indent=2))+'</pre></details></section>'
 overview=overview.replace('../../../../../deliverables/','../../../../deliverables/')
 atomic(dest/'index.html',page('UACF 旧库：保存进度与理解进度',overview));atomic(state.root/'logs/batch4-coverage.json',canonical(cov))
 return {'ok':True,'path':str(dest/'index.html'),'conversations':len(rows),'conversations_with_selected_spans':picked,'mode':'REINDEX','source_bytes_read':0,'semantic_calls':0,'coverage':cov,'semantic_labels_inferred_from_titles':False}
