import unittest,tempfile,copy
from pathlib import Path
from types import SimpleNamespace
from uacf.project_workflow import dispatch,defaults
from uacf.util import Fault

class ProjectWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.objects={};self.counter=0
        self.task={'object_id':'task','object_type':'TaskContract','revision':1,'payload':{'goal':'test','constraints':['preserve sources']}}
        self.objects['task']=copy.deepcopy(self.task)
        self.state=SimpleNamespace(root=Path(self.tmp.name),get=lambda oid,actor:copy.deepcopy(self.objects[oid]),put=self.put,context=lambda *a:{'status':'ready'})
        (self.state.root/'data').mkdir()
    def tearDown(self):self.tmp.cleanup()
    def put(self,req,actor):
        obj=copy.deepcopy(req['object']);self.counter+=1
        oid=obj['object_id'];obj['revision']=self.objects.get(oid,{}).get('revision',0)+1
        self.objects[oid]=obj;return {'object':copy.deepcopy(obj)}
    def configure(self,route='current_host'):
        return dispatch(self.state,'owner','workflow_project_configure',{'task_id':'task','task_revision':1,'stages':[dict(id='first',role='review',label='review',route=route,depends_on=[]),dict(id='second',role='deliver',label='deliver',route='current_host',depends_on=['first'])]},'op')['plan']
    def record(self,stage,state,**kw):return dispatch(self.state,'owner','workflow_project_record',dict(task_id='task',task_revision=2,stage_id=stage,state=state,**kw),'op')
    def test_nonowner_cannot_configure_or_observe_private_plan(self):
        with self.assertRaises(Fault):dispatch(self.state,'reader','workflow_project_status',{'task_id':'task'},None)
    def test_dependencies_and_actual_model_then_receipt(self):
        self.configure()
        with self.assertRaises(Fault):self.record('second','started')
        self.assertTrue(self.record('first','started')['continue_current_host'])
        with self.assertRaises(Fault):self.record('first','completed',result='work',actual_model='pretend',native_locator='file')
        self.record('first','completed',result='work',actual_model='current_host',native_locator='file')
        self.record('second','started')
        self.assertEqual(self.objects['task']['payload']['constraints'],['preserve sources'])
    def test_no_replay_or_false_external_success(self):
        self.configure('deepseek')
        with self.assertRaises(Fault) as f:self.record('first','started')
        self.assertEqual(f.exception.code,'ADAPTER_REQUIRED')
    def test_task_change_blocks_old_plan(self):
        self.configure();self.objects['task']['revision']=3
        with self.assertRaises(Fault) as f:dispatch(self.state,'owner','workflow_project_status',{'task_id':'task'},None)
        self.assertEqual(f.exception.code,'REVISION_CONFLICT')
    def test_context_overflow_cannot_start(self):
        self.configure();self.state.context=lambda *a:{'status':'overflow'}
        with self.assertRaises(Fault) as f:self.record('first','started')
        self.assertEqual(f.exception.code,'CAPSULE_OVERFLOW')
    def test_current_host_start_does_not_dispatch_inference_and_cannot_replay(self):
        self.configure();self.record('first','started')
        with self.assertRaises(Fault):self.record('first','started')
    def test_provider_disabled_still_allows_current_host_but_blocked_task_stops(self):
        self.objects['task']['payload']['allow_provider']=False
        self.configure();self.assertTrue(self.record('first','started')['continue_current_host'])
        self.record('first','completed',result='observed current host result',actual_model='current_host',native_locator='fixture')
        self.objects['task']['payload']['execution_state']='blocked'
        with self.assertRaises(Fault) as error:self.record('second','started')
        self.assertEqual(error.exception.code,'STOPPED')
    def test_forward_dependency_rejected(self):
        with self.assertRaises(Fault):dispatch(self.state,'owner','workflow_project_configure',{'task_id':'task','task_revision':1,'stages':[dict(id='first',role='review',label='review',route='current_host',depends_on=['second'])]},'op')
    def test_defaults_are_phase_routes_not_percentages(self):
        stages=defaults('assets','time')
        self.assertEqual([s['role'] for s in stages if s['route']=='deepseek'],[])
        self.assertTrue(all(s['route']=='current_host' for s in defaults('general','cost')))
        self.assertTrue(all(s['route']=='current_host' for s in defaults('general','quality')))
    def test_real_capsule_carries_policy_and_blocks_changed_revision(self):
        from uacf.state import State,init,object_new,request
        from uacf.util import uid
        root=self.state.root/'real';init(root);state=State(root)
        task=state.put(request(object_new('TaskContract',{'goal':'real context','required_properties':[],'constraints':['preserve']})),'owner')['object']
        plan=dispatch(state,'owner','workflow_project_configure',{'task_id':task['object_id'],'task_revision':1,'preset':'quality'},uid())['plan']
        context=state.context('owner',task['object_id'])
        self.assertEqual(context['status'],'ready')
        self.assertEqual(context['capsule']['execution_policy']['config'],plan['config'])
        artifact=state.get(plan['plan_ref']['object_id'],'owner');artifact['payload']['config']['preset']='changed'
        state.put(request(artifact,artifact['revision']),'owner')
        self.assertEqual(state.context('owner',task['object_id'])['status'],'missing')

if __name__=='__main__':unittest.main()
