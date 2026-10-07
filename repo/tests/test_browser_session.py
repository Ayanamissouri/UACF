import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from uacf.state import init,State
from uacf.browser_session import issue,authenticate,origin_allowed,COOKIE,launch_ticket,consume_launch_ticket
from uacf.util import Fault

class BrowserSessionBoundary(unittest.TestCase):
 def test_local_launch_single_use_expiry_rotation_and_port(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);init(root);s=State(root);ticket=launch_ticket(s,8766)
   with self.assertRaises(Fault):consume_launch_ticket(s,ticket,8767)
   with self.assertRaises(Fault):consume_launch_ticket(s,ticket+'x',8766)
   self.assertEqual(consume_launch_ticket(s,ticket,8766),'owner')
   with self.assertRaises(Fault):consume_launch_ticket(s,ticket,8766)
   ticket=launch_ticket(s,8766)
   with patch('uacf.browser_session.time.time',return_value=999999999999):
    with self.assertRaises(Fault):consume_launch_ticket(s,ticket,8766)
   auth=json.loads((s.data/'auth.json').read_text());auth['owner']='rotated-test';(s.data/'auth.json').write_text(json.dumps(auth))
   with self.assertRaises(Fault):consume_launch_ticket(s,ticket,8766)
 def test_restart_tamper_rotation_and_actor(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);init(root);s=State(root)
   cookie=issue(s,'owner',8766).split(';')[0]
   self.assertEqual(authenticate(State(root),cookie,8766),'owner')
   self.assertIn('HttpOnly',issue(s,'reader',8766))
   self.assertEqual(authenticate(s,issue(s,'reader',8766).split(';')[0],8766),'reader')
   with self.assertRaises(Fault):authenticate(s,cookie+'x',8766)
   with self.assertRaises(Fault):authenticate(s,cookie,8767)
   with patch('uacf.browser_session.time.time',return_value=999999999999):
    with self.assertRaises(Fault):authenticate(s,cookie,8766)
   auth=json.loads((s.data/'auth.json').read_text());auth['owner']='rotated-test-credential';(s.data/'auth.json').write_text(json.dumps(auth))
   with self.assertRaises(Fault):authenticate(s,cookie,8766)
 def test_origin_boundary(self):
  self.assertTrue(origin_allowed({'Host':'127.0.0.1:8766','Origin':'http://127.0.0.1:8766'},8766))
  self.assertFalse(origin_allowed({'Host':'127.0.0.1:8766','Origin':'https://example.org'},8766))
  self.assertFalse(origin_allowed({'Host':'example.org:8766','Origin':'http://example.org:8766'},8766))
  self.assertFalse(origin_allowed({'Host':'localhost:8766','Origin':'http://localhost:8766','Sec-Fetch-Site':'cross-site'},8766))
