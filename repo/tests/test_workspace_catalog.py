import tempfile,unittest
from pathlib import Path
from uacf.state import State,init,object_new,request
from uacf.workspace import workspace

class WorkspaceEvidenceLink(unittest.TestCase):
 def test_nested_task_reference_and_historical_revision_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   init(tmp);s=State(tmp)
   with s.db() as c:
    for n in ['002.sql','003.sql','004-archive.sql']:c.executescript((Path(__file__).resolve().parents[1]/'contracts/migrations'/n).read_text())
   task=object_new('TaskContract',{'goal':'fixture','required_properties':[],'constraints':[],'execution_state':'stopped','allow_provider':False},visibility='shared');task=s.put(request(task),'owner')['object']
   evidence=object_new('Evidence',{'observation':{'task_id':task['object_id'],'task_revision':task['revision'],'method':'fixture'}},visibility='shared');evidence=s.put(request(evidence),'owner')['object']
   task['payload']['goal']='revised fixture';task=s.put(request(task,task['revision']),'owner')['object']
   w=workspace(s,'owner',{'task_id':task['object_id']})
   self.assertEqual(w['results'][0]['object_id'],evidence['object_id']);self.assertEqual(w['results'][0]['payload']['observation']['task_revision'],1);self.assertEqual(w['selected_task']['revision'],2);self.assertEqual(w['execution_trace'],[]);self.assertEqual(w['paid_calls'],0)
