"use strict";
function clearBrowserView(){
 if(typeof flowState!=='undefined')flowState=null;for(const id of ['hostSource','hostResult','flowEvents','flowApplied','flowProgress','hostReviewStatus']){const n=$(id);if(n){n.textContent='';if('value' in n)n.value=''}}$('hostReview').hidden=true;$('flowStatus').textContent='等待配对';if(typeof portableReset==='function'){portableReset();$('triggerCue').value='';$('triggerTask').value=''}browserAuthenticated=false;browserGeneration++;snapshot=null;selected=null;observeSnapshot=null;catalogSnapshot=null;catalogSelection=null;catalogSequence++;workspaceSnapshot=null;
 for(const id of ['portableRows','portablePrivateLinks','portableSourceRows','triggerResult','portableFeedback','assetUseRows','assetUseDetail','assetSemanticReviews','identity','view','detail','catalogTree','catalogSummary','catalogResults','catalogDetail','observeWork','observeHistory','observeSystem','workspaceWorkflow','workspaceAffiliation','workspaceSources','workspaceLessons','workspaceRoute']){const n=$(id);if(n)n.replaceChildren()}
 show('observeState','尚未配对此浏览器。资料已保存在本机，配对后自动显示目录。');
 show('observeHint','使用安装目录的资料库启动入口；也可以展开上方手动配对。');
}
async function resumeBrowser(){
 try{
  const params=new URLSearchParams(location.hash.slice(1)),ticket=params.get('pair');
  if(ticket){history.replaceState(null,'',location.pathname);const r=await fetch('/browser/launch',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticket})});const v=await r.json();if(!v.ok)throw Error(v.detail||v.code)}
  const r=await fetch('/browser/session',{credentials:'same-origin'});if(!r.ok)throw Error('本机登录状态读取失败');const v=await r.json();
  browserAuthenticated=v.authenticated===true;browserActor=v.actor||'owner';
  if(!browserAuthenticated){clearBrowserView();show('authstate','未配对：请双击本机“打开UACF资料库.cmd”。资料无需重新导入。');return}
  $('manualPair').open=false;show('authstate','本浏览器已配对；正在加载本机资料库。');
 }catch(e){clearBrowserView();show('authstate','登录未完成：'+e.message+'。请重新打开本机启动入口。');return}
 try{await refresh();show('authstate','已加载本机资料库；同一浏览器重开网址可续用30天。')}catch(e){show('authstate','已登录，但目录读取失败：'+e.message+'。点击“刷新事实”重试。')}
}
$('authfile').onchange=guarded(async()=>{
 const file=$('authfile').files[0];if(!file)return;
 try{const obj=JSON.parse(await file.text());const r=await fetch('/browser/session',{method:'POST',credentials:'same-origin',headers:{Authorization:'Bearer '+obj.owner}});const v=await r.json();if(!v.ok)throw Error(v.code+': '+v.detail);browserAuthenticated=true;browserActor=v.actor;$('manualPair').open=false;await refresh();show('authstate','已配对并加载本机资料库；以后可直接重开网址。')}finally{$('authfile').value=''}
});
$('logout').onclick=guarded(async()=>{
 clearBrowserView();const r=await fetch('/browser/logout',{method:'POST',credentials:'same-origin'});if(!r.ok)throw Error('退出失败，请关闭浏览器并重试');show('authstate','已退出并清除本页显示；其他浏览器不受影响。');
});
resumeBrowser();
