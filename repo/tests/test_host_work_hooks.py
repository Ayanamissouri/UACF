import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(host):
 spec=importlib.util.spec_from_file_location('fixture_'+host,ROOT/'adapters'/host/'hook.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class HookTests(unittest.TestCase):
 def test_both_native_pretool_shapes_deny_unavailable_and_refused(self):
  for host in ['codex','claude_code']:
   m=module(host);event=dict(session_id='fixture-not-a-real-session',hook_event_name='PreToolUse',tool_name='Bash',tool_input={'command':'echo fixture'})
   with patch.object(m,'call',side_effect=OSError('offline')):
    r=m.run(ROOT,event)['hookSpecificOutput'];self.assertEqual(r['permissionDecision'],'deny');self.assertEqual(r['hookEventName'],'PreToolUse')
   with patch.object(m,'call',return_value={'allowed':False,'reason':'UACF_PROVIDER_BYPASS'}):self.assertEqual(m.run(ROOT,event)['hookSpecificOutput']['permissionDecision'],'deny')
 def test_native_id_required(self):
  for host in ['codex','claude_code']:
   with self.assertRaises(Exception):module(host).run(ROOT,{'hook_event_name':'PreToolUse'})
