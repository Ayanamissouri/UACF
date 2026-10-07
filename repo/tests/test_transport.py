"""Real local HTTP server and MCP subprocess, never a mock Host."""
import json, os, subprocess, sys, tempfile, time, unittest, urllib.request, urllib.error
from pathlib import Path
from uacf.state import State, init, object_new, request
from uacf.service import call
from uacf.util import Fault, atomic, canonical, sha, uid

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='uacf-http-'); self.root=Path(self.temp.name)/'中文 root'; init(self.root); self.state=State(self.root)
        import socket
        with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
        cfg=self.state.config; cfg['port']=port; atomic(self.state.data/'config.json',canonical(cfg)); self.port=port
        self.proc=subprocess.Popen([sys.executable,'-X','utf8','-m','uacf','--root',str(self.root),'serve'],cwd=Path(__file__).resolve().parents[1],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=.2) as r: self.health=json.load(r)
                break
            except (OSError,urllib.error.URLError): time.sleep(.05)
        else: self.fail('real service did not start')
    def tearDown(self):
        if os.name=='nt':
            # The venv launcher and its exact child both belong to this fixture.
            subprocess.run(['taskkill','/PID',str(self.proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:self.proc.terminate()
        self.proc.communicate(timeout=5); self.temp.cleanup()
    def test_http_auth_acl_conflict_and_html(self):
        auth=json.loads((self.state.data/'auth.json').read_text())
        task=call(self.root,'put',request(object_new('TaskContract',{'goal':'HTTP test','required_properties':['property']},visibility='shared')))['object']
        self.assertEqual(call(self.root,'get',{'object_id':task['object_id']},'reader')['object'],task)
        req=request(object_new('Attempt',{}),actor='reader')
        with self.assertRaises(Fault) as c: call(self.root,'put',req,'reader')
        self.assertEqual(c.exception.code,'PERMISSION')
        q=urllib.request.Request(f'http://127.0.0.1:{self.port}/v1/action',data=b'{"action":"doctor"}',headers={'Authorization':'Bearer wrong'})
        with self.assertRaises(urllib.error.HTTPError) as c: urllib.request.urlopen(q)
        self.assertEqual(c.exception.code,401)
        with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/') as r: self.assertIn('UACF 连续性控制面',r.read().decode('utf-8'))
        self.assertIn('loaded_source_identity',self.health)
    def test_mcp_stdio_live_core_and_access_denial(self):
        shared=call(self.root,'put',request(object_new('TaskContract',{'goal':'MCP test','required_properties':['property']},visibility='shared')))['object']
        private=call(self.root,'put',request(object_new('TaskContract',{'goal':'private','required_properties':['property']})))['object']
        messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
          {'jsonrpc':'2.0','method':'notifications/initialized'}, {'jsonrpc':'2.0','id':2,'method':'tools/list'},
          {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'uacf_context','arguments':{'task_id':shared['object_id']}}},
          {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'uacf_context','arguments':{'task_id':private['object_id']}}}]
        wire=''.join(canonical(m)+'\n' for m in messages)
        p=subprocess.run([sys.executable,'-X','utf8','-m','uacf','--root',str(self.root),'mcp'],input=wire.encode(),capture_output=True,cwd=Path(__file__).resolve().parents[1],timeout=15)
        self.assertEqual(p.returncode,0,p.stderr); result=[json.loads(s) for s in p.stdout.splitlines()]
        self.assertEqual(len(result),4); self.assertEqual(result[0]['result']['protocolVersion'],'2025-06-18')
        self.assertFalse(result[2]['result']['isError']); self.assertTrue(result[3]['result']['isError'])
        self.assertEqual(json.loads(result[3]['result']['content'][0]['text'])['code'],'NOT_FOUND')
    def test_command_idempotency_profile_write_and_collision(self):
        oid=uid(); args={'host':'dsh','requested_tokens':1000000,'expected_revision':1}
        a=call(self.root,'profile_set',args,operation_id=oid)
        b=call(self.root,'profile_set',args,operation_id=oid)
        self.assertEqual(a,b); self.assertEqual(len(list((self.root/'backups').glob('config-*'))),1)
        with self.assertRaises(Fault) as c: call(self.root,'profile_set',{'host':'dsh','requested_tokens':500000},operation_id=oid)
        self.assertEqual(c.exception.code,'OPERATION_CONFLICT')
    def test_pending_command_reconciles_canonical_put_without_replay(self):
        req=request(object_new('Attempt',{'observation':'durable'})); oid=req['operation_id']
        initial=call(self.root,'put',req)
        with self.state.db() as c: c.execute("UPDATE command_operations SET state='pending',response=NULL WHERE operation_id=?",(oid,))
        recovered=call(self.root,'put',req); self.assertEqual(initial,recovered)
        self.assertEqual(len(self.state.list('owner')),1)

if __name__=='__main__': unittest.main(verbosity=2)
