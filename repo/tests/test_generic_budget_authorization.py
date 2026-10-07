import tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.fabric import vector
from uacf.batch3 import dispatch_batch3 as dispatch
from uacf.util import Fault
class GenericBudgetTests(unittest.TestCase):
 def test_exact_new_account_and_stale_wrong_amount_refused(self):
  with tempfile.TemporaryDirectory() as d:
   init(Path(d));s=State(Path(d))
   from uacf.fabric import migrate
   s.backup(Path(d)/'before');migrate(s,Path(d)/'before')
   t=s.put(request(object_new('TaskContract',{'goal':'synthetic authorization','required_properties':[],'allow_provider':True,'budget_authorization':{'account':'synthetic-new-test','limit_micro':20000000,'authorization_source':'synthetic test fixture only'}})),'owner')['object'];args={'account':'synthetic-new-test','limit_micro':20000000,'currency':'CNY','task_ref':vector(t)}
   self.assertEqual(dispatch(s,'owner','budget_open',args)['limit_micro'],20000000)
   for patch in [{'limit_micro':21000000},{'account':'batch4'},{'task_ref':{'object_id':t['object_id'],'revision':2}}]:
    with self.assertRaises(Fault):dispatch(s,'owner','budget_open',dict(args,**patch))
   with self.assertRaises(Fault):dispatch(s,'codex','budget_open',args)
