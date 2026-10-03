"""Eight meaningful fake/source-interface cases; all UNRUN by source author."""
import unittest
from types import SimpleNamespace as NS
import avatar_carrier_trial as trial

class FakeCheckpoint:
    def __init__(self,fail=None): self.fail=fail; self.rows=[]; self.primary=RuntimeError('original checkpoint failure')
    def __call__(self,state,label):
        self.rows.append((state,label))
        if label==self.fail: raise self.primary
        return {'fake':True,'phase':label,'runtime_authority':False}

class TrialInterface(unittest.TestCase):
    def options(self):
        return {'attempt_id':'0123456789abcdef','config_path':'C:/generic/config.json',
          'blend_path':'C:/generic/output/0123456789abcdef/carrier.blend',
          'record_path':'C:/generic/output/0123456789abcdef/BUILD-RECORD.json',
          'output_root':'C:/generic/output','acknowledge_generic_inactive':True}
    def test_01_closed_options_refuse_hidden_person_or_seed(self):
        value=self.options(); value['persona']='Robert'
        with self.assertRaisesRegex(ValueError,'closed inactive'): trial.fixed_paths(value)
    def test_02_old_or_other_saved_carrier_path_refuses(self):
        value=self.options(); value['blend_path']='C:/generic/output/old/carrier.blend'
        with self.assertRaisesRegex(ValueError,'fixed new outputs'): trial.fixed_paths(value)
    def test_03_profile_wrong_source_refuses_without_native_call(self):
        with self.assertRaisesRegex(ValueError,'generic rig profile'):
            trial.source_guard(dict(trial.REQUIRED_SOURCE_PINS),b'unselected profile')
    def test_04_callback_return_is_retained_before_original_checkpoint_error(self):
        state=trial.state_for('fake'); checkpoint=FakeCheckpoint('allocated'); owner=object()
        with self.assertRaises(RuntimeError) as caught:
            trial.call(state,checkpoint,'allocated',lambda:owner)
        self.assertIs(caught.exception,checkpoint.primary)
        self.assertIs(state['returns'][0]['value'],owner)
    def test_05_cold_in_process_flag_cannot_replace_actual_writer_exit(self):
        value={'attempt_id':'0123456789abcdef','exit_code':False,'normal_exit_observed':True,
          'complete_original_envelope_qualified':True,'record_sha256':'a'*64,
          'genuine_tool_identity':{'tool':'exec_command','chunk_id':'fake123'},'full_review_sha256':'b'*64}
        with self.assertRaisesRegex(ValueError,'separate actual'): trial.writer_return_guard(value,value['attempt_id'])
        value['exit_code']=0; value['genuine_tool_identity']['chunk_id']=''
        with self.assertRaisesRegex(ValueError,'genuine writer'): trial.writer_return_guard(value,value['attempt_id'])
    def test_06_geometric_feedback_never_claims_force_or_brain_delivery(self):
        event=trial.sensor_observation(((0.0,0.0,-0.003),(0.0,0.0,0.01)),(0,1),
          attempt='0123456789abcdef',probe='fake',bone='foot.L',angles=(-35.0,0.0,0.0))
        self.assertTrue(event['penetration_observed']); self.assertTrue(event['geometric_contact_observed'])
        self.assertIsNone(event['force_newtons']); self.assertFalse(event['brain_input_delivered'])
        self.assertFalse(event['physiology_or_sensation_claim'])
    def test_07_failed_evaluated_mesh_count_retains_owner_without_clear_retry(self):
        class Evaluated:
            def __init__(self): self.mesh=NS(vertices=[]); self.clears=0
            def to_mesh(self): return self.mesh
            def to_mesh_clear(self): self.clears+=1
        evaluated=Evaluated(); body=NS(evaluated_get=lambda _graph:evaluated)
        bpy=NS(context=NS(evaluated_depsgraph_get=lambda:object()))
        state=trial.state_for('fake')
        with self.assertRaisesRegex(ValueError,'vertex identity count'):
            trial.evaluate_points(state,FakeCheckpoint(),bpy,body,'fake')
        self.assertIs(state['objects']['evaluated_owners'][0]['mesh'],evaluated.mesh)
        self.assertFalse(state['objects']['evaluated_owners'][0]['clear_entered'])
        self.assertEqual(evaluated.clears,0)
    def test_08_whole_static_fingerprint_detects_rest_or_weights_changes(self):
        before={'weights_sha256':'a'*64,'attached_bones':{'root':{'matrix_local_sha256':'b'*64}}}
        after={'weights_sha256':'a'*64,'attached_bones':{'root':{'matrix_local_sha256':'c'*64}}}
        self.assertNotEqual(trial.static_fingerprint(before),trial.static_fingerprint(after))
