// Supplementary contract stimuli; real SDK/server receipts are separate.
import assert from 'node:assert/strict';import continuity from '../adapters/pi/continuity.mjs';
const handlers={},commands={};let active=true,key='revision1',offline=false,records=0;
continuity({on:(name,handler)=>{handlers[name]=handler;},registerCommand:(name,c)=>commands[name]=c},
 {taskId:'contract-fixture',active:()=>active,prepare:async()=>{if(offline)throw Error('offline');return {ok:true,status:'ready',cache_key:key,capsule:{task_revision:key},required_bytes:123};},observe:async()=>records++,flush:async()=>{}});
await commands['uacf-prepare'].handler();const initial=records;
await commands['uacf-prepare'].handler();assert.equal(records,initial,'same preparation does not archive twice');
assert.equal(await handlers.tool_call({toolName:'read',toolCallId:'a',input:{}}),undefined);
key='revision2';assert.equal((await handlers.tool_call({toolName:'read',toolCallId:'b',input:{}})).block,true);
await commands['uacf-prepare'].handler();offline=true;assert.equal((await handlers.tool_call({toolName:'read',toolCallId:'c',input:{}})).block,true);
active=false;assert.deepEqual(await handlers.input(),{action:'continue'});assert.equal(await handlers.tool_call({}),undefined);
const before=records;await handlers.tool_result({toolName:'read'});assert.equal(records,before,'unmapped result cannot enter old task archive');
active=true;assert.deepEqual(await handlers.input(),{action:'handled'});
console.log(JSON.stringify({ok:true,coverage:'supplementary mapped/unmapped, stale, unavailable, duplicate preparation; no native invocation claim'}));
