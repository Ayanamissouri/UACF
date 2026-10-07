// Installed standalone Pi bridge. Only a Pi-scoped token, never Owner credentials.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import continuity from './continuity.mjs';
const sorted=x=>Array.isArray(x)?x.map(sorted):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,sorted(x[k])])):x;
const encode=x=>JSON.stringify(sorted(x));
export default function installed(pi) {
  const file=path.join(process.env.PI_CODING_AGENT_DIR||path.join(process.env.USERPROFILE,'.pi/agent'),'uacf-host.json');
  if(!fs.existsSync(file))return;
  const config=JSON.parse(fs.readFileSync(file,'utf8'));
  if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(config.url))throw Error('UACF_LOOPBACK_ONLY');
  let binding=null;
  const epoch=crypto.randomUUID();let seq=0,drainPromise=null;
  const queue=path.join(config.root,'data/pi-observation-queue');
  async function send(action,args) {
    const body={action,args};
    if(['host_event','artifact_capture'].includes(action)){
      const operation_id=action==='host_event'?args.event_id:crypto.randomUUID();
      Object.assign(body,{actor:'pi',operation_id,correlation_id:operation_id,scope:'action:'+action,expected_revision:0,schema_version:'1.0'});
      body.request_hash=crypto.createHash('sha256').update(encode(body)).digest('hex');
    }
    const response=await fetch(config.url+'/v1/action',{method:'POST',headers:{Authorization:'Bearer '+config.token,'Content-Type':'application/json'},body:encode(body),signal:AbortSignal.timeout(2000)});
    const result=await response.json();if(!result.ok)throw Error('UACF_'+result.code);return result;
  }
  function flush(){
    if(drainPromise)return drainPromise;
    if(!fs.existsSync(queue))return Promise.resolve();
    drainPromise=(async()=>{while(true){
      const names=fs.readdirSync(queue).filter(n=>n.endsWith('.json'));if(!names.length)break;
      for(const name of names){
      const p=path.join(queue,name),e=JSON.parse(fs.readFileSync(p,'utf8'));const r=await send('host_event',e);
      const ack=path.join(config.root,'data/pi-observation-ack');fs.mkdirSync(ack,{recursive:true});
      const temp=path.join(ack,name+'.tmp-'+crypto.randomUUID()),fd=fs.openSync(temp,'wx');
      try{fs.writeFileSync(fd,encode({event:e,ack:r}));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
      fs.renameSync(temp,path.join(ack,name));fs.unlinkSync(p);
    }}})().finally(()=>{drainPromise=null;});
    return drainPromise;
  }
  const bridge={get taskId(){return binding?.task;},active:()=>!!binding,
      prepare:()=>{if(!binding)throw Error('UACF_SESSION_UNMAPPED');return send('context',{task_id:binding.task});},flush,
      captureArtifacts:revision=>{if(!binding)return;return send('artifact_capture',{task_id:binding.task,task_revision:revision,native_session_id:binding.native});},
      observe:async payload=>{
        if(!binding)return;const {native,task}=binding;
        const fullPayload={...payload,native_session_id:native,source_version:'Pi 1.0.2 public ExtensionAPI'};
        const locator=payload.native_tool_call_id?encode([native,payload.kind,payload.native_tool_call_id]):null;
        const hex=locator?crypto.createHash('sha256').update(locator).digest('hex'):null;
        const eventId=hex?`${hex.slice(0,8)}-${hex.slice(8,12)}-5${hex.slice(13,16)}-a${hex.slice(17,20)}-${hex.slice(20,32)}`:crypto.randomUUID();
        const pending=path.join(queue,eventId+'.json'), acknowledged=path.join(config.root,'data/pi-observation-ack',eventId+'.json');
        const prior=fs.existsSync(pending)?JSON.parse(fs.readFileSync(pending)):fs.existsSync(acknowledged)?JSON.parse(fs.readFileSync(acknowledged)).event:null;
        if(prior){if(encode(prior.payload)!==encode(fullPayload))throw Error('UACF_EVENT_CONFLICT');void flush().catch(()=>{});return;}
        const e={event_id:eventId,source_host:'pi',host_epoch:epoch,source_seq:++seq,type:'observation',occurred_at:new Date().toISOString(),observed_at:new Date().toISOString(),schema_version:'1.0',visibility:'private',payload:fullPayload};
        fs.mkdirSync(queue,{recursive:true});const fd=fs.openSync(path.join(queue,e.event_id+'.json'),'wx');try{fs.writeFileSync(fd,encode(e));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
        pi.appendEntry('uacf-observation-locator',{event_id:e.event_id,task_id:task,task_revision:payload.task_revision,
          canonical_delivery:'pending observation acknowledgement; never replay a tool or model'});
        // Native action waits only for the fsynced local observation, not canonical delivery.
        // Settled/shutdown await the shared drain; outage keeps exact queued identities.
        void flush().catch(()=>{});
      }};
  continuity(pi,bridge);
  pi.on('session_start',async(_event,ctx)=>{
    binding=null;
    const native=ctx.sessionManager.getSessionId();
    const bindings=JSON.parse(fs.readFileSync(path.join(config.root,'data/host-bindings.json'),'utf8'));
    const task=bindings.pi?.[native];if(!task)return;
    binding={native,task};
    await bridge.observe({kind:'native_organization',native_title:ctx.sessionManager.getSessionName()||null,
      native_cwd:ctx.sessionManager.getCwd(),task_id:task,semantic_affiliation_modified:false});
  });
}
