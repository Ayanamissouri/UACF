"""Isolated registered uninstall and real native Codex configuration parser, no model turn."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
from uacf.host import backup_config,complete
from uacf.util import atomic,canonical
class HostLifecycle(unittest.TestCase):
 def test_B3_08_config_drift_uninstall(self):
  root=Path(__file__).resolve().parents[2]
  with tempfile.TemporaryDirectory(dir=root/'backups') as tmp:
   isolated=Path(tmp);(isolated/'backups').mkdir();home=isolated/'codex-home';home.mkdir();config=home/'config.toml';original='model = "gpt-5.5"\n';config.write_text(original)
   dest,m=backup_config(isolated,'codex',[config]);installed=original+'\n[mcp_servers.uacf]\ncommand = "'+str(root/'repo/.venv/Scripts/python.exe').replace('\\','/')+'"\nargs = ["-m", "uacf", "--root", "'+str(root).replace('\\','/')+'", "mcp"]\n';config.write_text(installed);complete(dest,m)
   env=dict(os.environ,CODEX_HOME=str(home));native=subprocess.run(['cmd.exe','/d','/c','codex.cmd','mcp','get','uacf','--json'],env=env,capture_output=True,text=True,timeout=20);self.assertEqual(native.returncode,0,native.stderr)
   config.write_text(installed+'# synthetic later drift\n')
   cmd=[str(root/'repo/.venv/Scripts/python.exe'),'-X','utf8',str(root/'repo/ops/uninstall-batch3.py'),'--root',str(isolated),'--host-manifest',str(dest/'manifest.json')]
   rejected=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(json.loads(rejected.stdout)['code'],'HOST_DRIFT');self.assertIn('later drift',config.read_text())
   # Restore our synthetic stimulus, then perform the isolated destructive drill.
   config.write_text(installed);done=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(done.returncode,0,done.stderr);self.assertEqual(config.read_text(),original)
   basic=subprocess.run(['cmd.exe','/d','/c','codex.cmd','--version'],env=env,capture_output=True,text=True,timeout=20);self.assertEqual(basic.returncode,0)
   atomic(root/'logs/batch3-host-uninstall.json',canonical({'ok':True,'scope':'real native Codex parser with synthetic isolated config; no active desktop uninstall','registered_manifest':str(dest/'manifest.json'),'native_install':json.loads(native.stdout),'drift_rejection':json.loads(rejected.stdout),'uninstall':json.loads(done.stdout),'native_basic':basic.stdout.strip(),'model_calls':0,'V8_Governor_touched':False}))
if __name__=='__main__':unittest.main()
