import unittest
from http.server import BaseHTTPRequestHandler
from uacf.service import LocalStateServer
class ListenerOwnership(unittest.TestCase):
 def test_browser_pairing_on_other_port_does_not_replace_session(self):
  import tempfile
  from pathlib import Path
  from uacf.state import init,State
  from uacf.browser_session import issue,authenticate,clear
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);init(root);state=State(root)
   first=issue(state,'owner',8766).split(';')[0];second=issue(state,'owner',8876).split(';')[0]
   combined=first+'; '+second
   self.assertEqual(authenticate(state,combined,8766),'owner');self.assertEqual(authenticate(state,combined,8876),'owner')
   self.assertTrue(clear(8766)[0].startswith('uacf_session_8766='))
 def test_second_listener_cannot_replace_loaded_identity(self):
  first=LocalStateServer(('127.0.0.1',0),BaseHTTPRequestHandler)
  try:
   with self.assertRaises(OSError):LocalStateServer(first.server_address,BaseHTTPRequestHandler)
  finally:first.server_close()
