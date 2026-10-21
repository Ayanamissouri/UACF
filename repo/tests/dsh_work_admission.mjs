// Isolated public-interface fixtures; not native DSH runtime receipts.
import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import assert from 'node:assert/strict';
import {continuity} from '../adapters/dsh/continuity.js';
const root=fs.mkdtempSync(path.join(os.tmpdir(),'uacf-work-'));
fs.mkdirSync(path.join(root,'data/host-work'),{recursive:true});fs.writeFileSync(path.join(root,'data/host-work/policy.json'),'{}');
const handlers={},disposers=[];let guard,result={allowed:true},calls=0;
const ctx={on:(n,f)=>handlers[n]=f,tools:{guard:f=>{guard=f;return()=>{}}},effect:f=>{const d=f();if(d)disposers.push(d)},workspaceRegistry:{list:()=>[]}};
continuity(ctx,root,async(action,args)=>{assert.equal(action,'work_admit');assert.equal(args.host,'dsh');calls++;if(result instanceof Error)throw result;return result;});
const exec=()=>({agent:{id:'fixture-session'},name:'bash',arguments:{command:'echo fixture'}});
try{
 let e=exec();assert.equal(guard(e),'UACF_ADMISSION_NOT_CHECKED');
 assert.equal((await handlers['tools/pre-execute'](e,async()=>({kind:'allow'}))).kind,'allow');assert.equal(guard(e),undefined);
 result={allowed:false,reason:'UACF_PROVIDER_BYPASS'};e=exec();assert.equal((await handlers['tools/pre-execute'](e,async()=>({kind:'allow'}))).kind,'deny');assert.equal(guard(e),'UACF_PROVIDER_BYPASS');
 result=Error('offline');e=exec();assert.equal((await handlers['tools/pre-execute'](e,async()=>({kind:'allow'}))).kind,'deny');assert.match(guard(e),/unavailable/);
 const unmapped={name:'bash',arguments:{}};assert.equal((await handlers['tools/pre-execute'](unmapped,async()=>({kind:'allow'}))).kind,'deny');assert.match(guard(unmapped),/unavailable/);
 assert.equal(calls,3);console.log(JSON.stringify({ok:true,coverage:'async refusal, monotonic refusal, skipped gate, outage, absent native ID; isolated fixtures',model_calls:0}));
}finally{disposers.forEach(f=>f());fs.rmSync(root,{recursive:true,force:true});}
