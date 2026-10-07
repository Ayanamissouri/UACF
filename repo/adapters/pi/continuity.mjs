// Thin public lifecycle bridge. Tool connections remain in Pi's native MCP extension.
export default function continuity(pi, bridge) {
  let prepared = null;
  const record = async payload => {
    try { await bridge.observe(payload); } catch { /* bridge durably queues before sending */ }
  };
  async function prepare() {
    if (bridge.active && !bridge.active()) throw Error('UACF_SESSION_UNMAPPED');
    const previous = prepared;
    prepared = null;
    const result = await bridge.prepare();
    if (!result.ok || result.status !== 'ready') throw Error('UACF_CONTEXT_' + (result.status || result.code));
    prepared = result;
    if (previous?.cache_key !== result.cache_key) await record({kind:'round_preparation',task_id:bridge.taskId,task_revision:result.capsule.task_revision,
      required_bytes:result.required_bytes,cache_key:result.cache_key,delivery:'public extension contribution; model delivery separately verified'});
    return result;
  }
  pi.registerCommand('uacf-prepare',{description:'Prepare current canonical Task without a model request',handler:prepare});
  pi.on('before_agent_start',async()=>{
    if (bridge.active && !bridge.active()) return;
    const result=await prepare();
    return {message:{customType:'uacf-continuity',content:JSON.stringify(result.capsule),display:false}};
  });
  // Explicit admission: unsupported/overflow inputs are consumed before the agent starts.
  // This governs mapped user input, not arbitrary provider calls by other extensions.
  pi.on('input',async()=>{
    if (bridge.active && !bridge.active()) return {action:'continue'};
    try { await prepare(); return {action:'continue'}; }
    catch { await record({kind:'preparation_refused',task_id:bridge.taskId}); return {action:'handled'}; }
  });
  pi.on('tool_call',async event=>{
    if (bridge.active && !bridge.active()) return;
    let current;
    try { current=await bridge.prepare(); }
    catch { return {block:true,reason:'UACF State Service unavailable; mapped tool admission refused'}; }
    if (!prepared || current.status!=='ready' || current.cache_key!==prepared.cache_key)
      return {block:true,reason:'UACF current Task changed or mandatory context unavailable; prepare again'};
    if (bridge.allowedTools && !bridge.allowedTools.includes(event.toolName))
      return {block:true,reason:'UACF mapped Task does not authorize this tool'};
    await record({kind:'native_tool_call',native_tool_call_id:event.toolCallId,tool:event.toolName,input:event.input,
      task_revision:prepared.capsule.task_revision});
  });
  pi.on('tool_result',async event=>{
    if (bridge.active && !bridge.active()) return;
    await record({kind:'native_tool_result',native_tool_call_id:event.toolCallId,
      tool:event.toolName,isError:event.isError,content:event.content,task_revision:prepared?.capsule.task_revision});
  });
  pi.on('message_end',async event=>{
    if (bridge.active && !bridge.active()) return;
    const m=event.message;
    if (!['user','assistant','toolResult'].includes(m?.role)) return;
    // Reasoning/private provider replay is never archived.
    const content=Array.isArray(m.content)?m.content.filter(b=>['text','toolCall'].includes(b.type)):m.content;
    await record({kind:'native_message',role:m.role,content,usage:m.usage||null,native_message_timestamp:m.timestamp,
      task_revision:prepared?.capsule.task_revision});
  });
  pi.on('agent_settled',async()=>{
    if (bridge.active && !bridge.active()) return;
    await record({kind:'native_lifecycle',native_type:'agent_settled'});await bridge.flush();
    if(bridge.captureArtifacts && prepared){
      try{const receipt=await bridge.captureArtifacts(prepared.capsule.task_revision);await record({kind:'artifact_capture_receipt',task_revision:prepared.capsule.task_revision,receipt});}
      catch(error){await record({kind:'artifact_capture_failed',task_revision:prepared.capsule.task_revision,error_type:error.name});}
    }
  });
  pi.on('session_shutdown',async()=>bridge.flush());
  return {prepare};
}
