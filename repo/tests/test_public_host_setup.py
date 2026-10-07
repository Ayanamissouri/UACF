import json,pathlib,tempfile,unittest,importlib.util,tomllib
from uacf.state import init
from uacf.util import Fault
spec=importlib.util.spec_from_file_location('public_setup',pathlib.Path(__file__).resolve().parents[1]/'ops/install_host.py');setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
class PublicSetupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.tmp.name);self.root=self.base/'root';init(self.root)
  # This is a synthetic config fixture, never an executed/verified interpreter.
  runtime=self.root/'repo/.venv/Scripts/python.exe';runtime.parent.mkdir(parents=True);runtime.write_bytes(b'fixture only')
  self.home=self.base/'home';self.home.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def test_codex_named_merge_preserves_prior_text_and_is_idempotent(self):
  p=self.home/'config.toml';before='# keep this comment\nmodel = "existing-model"\n';p.write_text(before)
  r=setup.install(self.root,'codex',self.home,True);after=p.read_text();self.assertTrue(after.startswith(before));self.assertTrue(r['configured'])
  cfg=tomllib.loads(after);self.assertEqual(cfg['model'],'existing-model');self.assertNotIn('token',cfg['mcp_servers']['uacf'])
  self.assertTrue(setup.install(self.root,'codex',self.home,True)['already_configured']);self.assertEqual(after,p.read_text())
 def test_another_codex_root_is_not_overwritten(self):
  p=self.home/'config.toml';before='[mcp_servers.uacf]\ncommand="other"\n';p.write_text(before)
  with self.assertRaises(Fault):setup.install(self.root,'codex',self.home,True)
  self.assertEqual(p.read_text(),before)
 def test_pi_preserves_model_and_extensions_with_scoped_local_binding(self):
  p=self.home/'settings.json';p.write_text(json.dumps({'extensions':['existing'], 'model':'original','retry':{'enabled':True}}))
  setup.install(self.root,'pi',self.home,True);cfg=json.loads(p.read_text());self.assertEqual(cfg['extensions'][0],'existing');self.assertEqual(cfg['model'],'original');self.assertTrue(cfg['retry']['enabled'])
  auth=json.loads((self.root/'data/auth.json').read_text());binding=json.loads((self.home/'uacf-host.json').read_text());self.assertEqual(binding['token'],auth['pi']);self.assertNotEqual(binding['token'],auth['owner'])
 def test_plan_does_not_write_host_config(self):
  result=setup.install(self.root,'pi',self.home,False);self.assertFalse(result['configured']);self.assertEqual(list(self.home.iterdir()),[])
 def test_missing_dsh_profile_is_not_fabricated(self):
  with self.assertRaises(Fault):setup.install(self.root,'dsh',self.home,True)
  self.assertEqual(list(self.home.iterdir()),[])
