// Isolated adapter timeout stimuli. No native SDK or real network/model claim.
import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import installed from '../adapters/pi/installed.mjs';
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'uacf-pi-timeout-')),oldDir=process.env.PI_CODING_AGENT_DIR,oldFetch=globalThis.fetch;
try{
 const root=path.join(temp,'root');fs.mkdirSync(path.join(root,'data'),{recursive:true});fs.mkdirSync(path.join(root,'data/host-work'));fs.writeFileSync(path.join(root,'data/host-work/policy.json'),'{}');fs.writeFileSync(path.join(root,'data/host-bindings.json'),'{}');
 fs.writeFileSync(path.join(temp,'uacf-host.json'),JSON.stringify({root,url:'http://127.0.0.1:9999',token:'synthetic-fixture-only'}));process.env.PI_CODING_AGENT_DIR=temp;
 for(const settled of [true,false]){
  const handlers={},calls=[];let original;
  globalThis.fetch=async(_url,opts)=>{
   const m=JSON.parse(opts.body);calls.push(m);
   if(m.action==='work_enter'){original=m.operation_id;throw Error('synthetic request timeout');}
   if(m.action==='operation_get'){assert.equal(m.args.operation_id,original);return {json:async()=>({ok:true,operation:{state:settled?'done':'pending',response:settled?{ok:true,mode:'uacf',task_ref:{object_id:'fixture-task',revision:1},notice:'fixture'}:null}})};}
   return {json:async()=>({ok:true})};
  };
  installed({on:(n,h)=>handlers[n]=h,registerCommand:()=>{},appendEntry:()=>{}});
  const ctx={hasUI:false,sessionManager:{getSessionId:()=>settled?'settled-session':'pending-session',getCwd:()=>temp,getSessionName:()=>null}};
  if(settled){await handlers.session_start({},ctx);await handlers.session_shutdown();}
  else await assert.rejects(()=>handlers.session_start({},ctx),/UACF_OUTCOME_UNKNOWN/);
  assert.equal(calls.filter(x=>x.action==='work_enter').length,1,'unknown mutation must never be resent');
 }
 console.log(JSON.stringify({ok:true,model_calls:0,coverage:'Isolated Pi adapter timeout reconciliation: reads original operation; unknown enrollment is not replayed.'}));
}finally{
 globalThis.fetch=oldFetch;if(oldDir===undefined)delete process.env.PI_CODING_AGENT_DIR;else process.env.PI_CODING_AGENT_DIR=oldDir;
 if(path.dirname(path.resolve(temp))!==path.resolve(os.tmpdir())||!path.basename(temp).startsWith('uacf-pi-timeout-'))throw Error('Unsafe fixture cleanup');
 fs.rmSync(temp,{recursive:true,force:true});
}
