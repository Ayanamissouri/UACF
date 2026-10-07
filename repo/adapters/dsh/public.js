// Public adapter: existing Host owns reasoning; no historical experiment runner.
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { continuity } from './continuity.js'
export const name = 'dsh-uacf-public'
export const inject = ['tools', 'agents', 'sessions', 'systemPrompt', 'sessionTitle', 'workspaceRegistry']
const sorted = x => Array.isArray(x) ? x.map(sorted) : x && typeof x === 'object' ? Object.fromEntries(Object.keys(x).sort().map(k => [k, sorted(x[k])])) : x
export function apply(ctx, config = {}) {
  const root = path.resolve(config.root)
  async function core(action, args) {
    const c = JSON.parse(fs.readFileSync(path.join(root, 'data/config.json')))
    const token = JSON.parse(fs.readFileSync(path.join(root, 'data/auth.json'))).dsh
    const command = { action, args }
    if (['host_event', 'artifact_capture', 'learning_host_submit'].includes(action)) {
      const operation_id = action === 'host_event' ? args.event_id : crypto.randomUUID()
      Object.assign(command, {operation_id, actor:'dsh', schema_version:'1.0', correlation_id:operation_id, scope:'action:'+action, expected_revision:0})
      command.request_hash = crypto.createHash('sha256').update(JSON.stringify(sorted(command))).digest('hex')
    }
    const response = await fetch(`http://127.0.0.1:${c.port}/v1/action`, {method:'POST', headers:{Authorization:'Bearer '+token, 'Content-Type':'application/json'}, body:JSON.stringify(command), signal:AbortSignal.timeout(10000)})
    const result = await response.json()
    if (!result.ok) throw new Error('UACF_'+result.code)
    return result
  }
  continuity(ctx, root, core)
  for (const [name, action, properties, required] of [
    ['uacf_context','context',{task_id:{type:'string'},max_bytes:{type:'integer',minimum:1}},['task_id']],
    ['uacf_status','doctor',{},[]],
    ['uacf_asset_read','asset_read',{task_id:{type:'string'},task_revision:{type:'integer',minimum:1},artifact_id:{type:'string'},max_bytes:{type:'integer',minimum:1,maximum:8388608}},['task_id','task_revision','artifact_id']],
    ['uacf_learning_next','learning_host_next',{task_id:{type:'string'}},['task_id']],
    ['uacf_learning_submit','learning_host_submit',{task_id:{type:'string'},job_id:{type:'string'},result:{type:'object'}},['task_id','job_id','result']]
  ]) ctx.effect(() => ctx.tools.register({name,description:'Explicit source-bound UACF access; current Host owns work, candidates do not imply adoption.',parameters:{type:'object',properties,required,additionalProperties:false},output:{schema:{type:'object',properties:{body:{type:'string'}},required:['body'],additionalProperties:false},render:(_a,v)=>[{type:'text',text:v.body}]},execute:async args=>({body:JSON.stringify(await core(action,args))})}))
}
