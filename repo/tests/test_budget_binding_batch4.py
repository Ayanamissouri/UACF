import unittest
from uacf.batch2 import dispatch_account
from uacf.util import Fault
class BudgetBinding(unittest.TestCase):
 def test_same_batch_and_legacy(self):
  self.assertEqual(dispatch_account({'payload':{'budget_account':'batch4'}},{'payload':{'budget_account':'batch4'}}),'batch4')
  self.assertEqual(dispatch_account({'payload':{}},{'payload':{'budget_account':'batch3'}}),'batch3')
 def test_task_and_control_surface_cannot_inherit(self):
  for task,required in [({'payload':{'budget_account':'batch4'}},None),({'payload':{}},'batch4')]:
   with self.assertRaises(Fault) as caught:dispatch_account(task,{'payload':{'budget_account':'batch3'}},required)
   self.assertEqual(caught.exception.code,'BUDGET_ACCOUNT_MISMATCH')
if __name__=='__main__':unittest.main()
