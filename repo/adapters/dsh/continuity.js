// Public DSH lifecycle observations. No input injection, synthetic turns or Governor changes.
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
const sorted = x => Array.isArray(x) ? x.map(sorted) : x && typeof x === 'object' ? Object.fromEntries(Object.keys(x).sort().map(k => [k, sorted(x[k])])) : x
const digest = x => crypto.createHash('sha256').update(JSON.stringify(sorted(x))).digest('hex')
export function continuity(ctx, root, core) {
  const dir = path.join(root, 'data', 'dsh-observation-queue')
  fs.mkdirSync(dir, {recursive:true})
  const epoch = crypto.randomUUID(); let seq = 0; let draining = false
  const directoryHashes = new Map()
  const preparedRevisions = new Map()
  const externalSessions = new Set()
  const admissions = new WeakMap()
  const governed = () => fs.existsSync(path.join(root,'data/host-work/policy.json'))
  // Public async pre-execute gate plus monotonic native guard. Another listener
  // cannot turn a refusal (or a skipped gate) into permission later in the chain.
  ctx.on('tools/pre-execute', async (exec,next) => {
    if(!governed())return next()
    let decision
    try {
      if(!exec.agent?.id)throw Error('UACF_NATIVE_SESSION_REQUIRED')
      const r=await core('work_admit',{host:'dsh',native_session_id:exec.agent.id,
        tool_name:exec.name,tool_input:exec.arguments,cwd:exec.agent.session?.meta?.cwd||root})
      decision=r.allowed?{allowed:true}:{allowed:false,reason:r.reason||r.code||'UACF admission refused'}
    } catch(error) {decision={allowed:false,reason:'UACF admission unavailable: '+error.name}}
    admissions.set(exec,decision)
    if(!decision.allowed)return {kind:'deny',reason:decision.reason}
    return next()
  })
  if(ctx.tools?.guard)ctx.effect(()=>ctx.tools.guard(exec=>{
    if(!governed())return
    const d=admissions.get(exec)
    if(!d?.allowed)return d?.reason||'UACF_ADMISSION_NOT_CHECKED'
  }))
  const bindings = () => {
    const p = path.join(root, 'data', 'host-bindings.json')
    return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')).dsh || {} : {}
  }
  function record(payload, nativeTime) {
    const event = {event_id:crypto.randomUUID(), source_host:'dsh', host_epoch:epoch, source_seq:++seq,
      type:'observation', occurred_at:new Date(nativeTime || Date.now()).toISOString(), observed_at:new Date().toISOString(),
      schema_version:'1.0', visibility:'private', payload}
    const p = path.join(dir, event.event_id + '.json')
    const fd = fs.openSync(p, 'wx'); try {fs.writeFileSync(fd, JSON.stringify(event)); fs.fsyncSync(fd)} finally {fs.closeSync(fd)}
    void drain()
  }
  async function drain() {
    if (draining) return
    draining = true
    try {
      for (const name of fs.readdirSync(dir).filter(n => n.endsWith('.json'))) {
        const p = path.join(dir,name), event = JSON.parse(fs.readFileSync(p,'utf8'))
        const receipt = await core('host_event', event)
        if (!receipt.ok) break // Keep exact observation and id; never replay a model/tool action.
        fs.mkdirSync(path.join(root,'data','dsh-observation-ack'),{recursive:true})
        fs.renameSync(p,path.join(root,'data','dsh-observation-ack',name))
      }
    } catch { /* Offline retains the durable observation, not the external action. */ }
    finally {draining = false}
  }
  // Filter model reasoning/stream/private replay fields before any archival write.
  const publicMessage = m => m && ({id:m.id, role:m.role, toolCallId:m.toolCallId, isError:m.isError, source:m.source && {kind:m.source.kind,provider:m.source.provider,model:m.source.model,callId:m.source.callId},
    content:(m.content || []).filter(b => ['text','tool-result','tool-call'].includes(b.type)).map(b => {
      if (b.type === 'text') return {type:b.type,text:b.text}
      return {type:b.type,id:b.id,name:b.name,...(b.arguments === undefined ? {} : {arguments:b.arguments}),...(b.content === undefined ? {} : {content:b.content}),...(b.isError === undefined ? {} : {isError:b.isError})}
    })})
  ctx.on('session/event', (session,event) => {
    if(externalSessions.has(session.id))return
    if (!bindings()[session.id]) return // Explicit native ID mapping; no title/cwd guessed semantic affiliation.
    const base = {native_session_id:session.id,native_seq:event.seq,native_type:event.type,source_version:'DSH 0.1.5-rc.2'}
    if (['user/message','assistant/message','tool/result'].includes(event.type)) {
      const message = publicMessage(event.data.message || event.data)
      record({...base,kind:'native_message',message,usage:event.data.usage || null,content_hash:digest(message)},event.time)
    } else if (event.type === 'session/title') {
      record({...base,kind:'native_organization',native_title:event.data.title,semantic_affiliation_changed:false},event.time)
    } else if (['turn/start','turn/end','step/end'].includes(event.type)) {
      record({...base,kind:'native_lifecycle',data:event.data},event.time)
      if(event.type==='turn/end')void ctx.sessions.flush(session).then(participated=>record({...base,kind:'native_durability_checkpoint',participated})).catch(error=>record({...base,kind:'native_durability_checkpoint',status:'failed',error_type:error.name}))
      if(event.type==='turn/end')void (async()=>{
        const task_id=bindings()[session.id],task_revision=preparedRevisions.get(session.id)
        if(!task_revision)return
        const captured=await core('artifact_capture',{task_id,task_revision,native_session_id:session.id})
        record({...base,kind:'artifact_capture_receipt',receipt:captured})
      })().catch(error=>record({...base,kind:'artifact_capture_failed',error_type:error.name}))
    }
  })
  ctx.on('system-prompt/assemble', async (assembly, context, next) => {
    const id = context.agent?.id;let task = bindings()[id]
    let notice=''
    if(fs.existsSync(path.join(root,'data/host-work/policy.json'))){
      if(!id)throw new Error('UACF_NATIVE_SESSION_REQUIRED')
      const entered=await core('work_enter',{host:'dsh',native_session_id:id,goal:'DSH native work; preserve current Owner request before implementation',native_locator:'dsh:session:'+id})
      if(entered.mode==='external'){externalSessions.add(id);return next()}
      externalSessions.delete(id)
      task=entered.task_ref.object_id;notice=entered.notice
    }
    if (!task) return next()
    const prepared = await core('context',{task_id:task})
    record({kind:'round_preparation',native_session_id:id,task_id:task,status:prepared.status || prepared.code,
      cache_key:prepared.cache_key,required_bytes:prepared.required_bytes,learning_use:prepared.capsule?.learning_use_observation,delivery:'assembly contribution; request/context verifies actual delivery'})
    if (!prepared.ok || prepared.status !== 'ready') throw new Error('UACF_CONTEXT_' + (prepared.status || prepared.code))
    preparedRevisions.set(id,prepared.capsule.task_revision)
    const result = await next()
    return {...result,contexts:[...result.contexts,{name:'uacf:canonical-task',text:JSON.stringify({...prepared.capsule,default_work_notice:notice,notice_is_nonblocking:true})}]}
  })
  function observeDirectory() {
    const projects=ctx.workspaceRegistry.list()
    for(const id of Object.keys(bindings())) {
      const native_projects=projects.filter(p=>p.sessionIds.includes(id)).map(p=>({native_project_id:p.id,native_project_title:p.title,native_project_path:p.path}))
      const h=digest(native_projects)
      if(directoryHashes.get(id)!==h) {record({kind:'native_organization',native_session_id:id,native_projects,source_version:'DSH 0.1.5-rc.2 workspaceRegistry.list',semantic_affiliation_changed:false});directoryHashes.set(id,h)}
    }
  }
  const timer = setInterval(() => {observeDirectory();void drain()},10000); timer.unref()
  ctx.effect(() => () => clearInterval(timer))
  return {record,drain,bindings,observeDirectory}
}
