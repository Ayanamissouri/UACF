// Synthetic declaration test; not a native Host lifecycle receipt.
import assert from 'node:assert/strict'
import os from 'node:os'
import fs from 'node:fs'
import path from 'node:path'
import {apply} from '../adapters/dsh/public.js'
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'uacf-public-'))
const tools = [], effects = [], handlers = {}
apply({on:(n,h)=>handlers[n]=h,effect:f=>{const d=f();if(typeof d==='function')effects.push(d)},tools:{register:t=>tools.push(t)},workspaceRegistry:{list:()=>[]},sessions:{flush:async()=>true}}, {root})
assert.deepEqual(tools.map(x=>x.name), ['uacf_context','uacf_status','uacf_asset_read','uacf_learning_next','uacf_learning_submit'])
assert.equal(Object.keys(handlers).length, 2)
let continued = false
await handlers['system-prompt/assemble']({}, {agent:{id:'unmapped'}}, async()=>{continued=true;return {contexts:[]}})
assert.equal(continued, true)
effects.forEach(f=>f())
console.log('pass: five declarations, import graph, unmapped passthrough; native lifecycle remains unverified')
