"""Authored, UNRUN control-flow fixtures; no Blender/native anatomy qualification.

Fake producers and fake compiler/consumer test lane selection, ordering,
no-downstream authoring, flags, source guards and partial ownership. The real
compiler's separate 22 fixtures remain a distinct required root-admitted run.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import unittest

import avatar_pre_surface_rest_lane as integration
import optional_rest_lane_controller as controller

PROFILE_RAW = None
SKELETON_RAW = None


class FixturePath(PurePosixPath):
    def read_bytes(self):
        if str(self) != '/fixture/data/rigs/default.mhskel':
            raise AssertionError('fixture_unexpected_file_request')
        return SKELETON_RAW


class FakeCollection(list):
    def __init__(self, owner, kind):
        super().__init__()
        self.owner, self.kind = owner, kind

    def new(self, name, *args):
        self.owner.calls.append('allocate:' + self.kind)
        if self.owner.fail == 'allocate:' + self.kind:
            raise self.owner.primary
        value = FakeMesh(name) if self.kind == 'mesh' else FakeBody(name, args[0]) if self.kind == 'body' else SimpleNamespace(name=name)
        self.append(value)
        return value

    def remove(self, *args, **kwargs):
        self.owner.calls.append('forbidden_remove')
        raise AssertionError('test_lane_must_not_delete')


class FakeMesh:
    def __init__(self, name):
        self.name = name
        self.polygons = []
        self.vertices = []

    def from_pydata(self, vertices, edges, faces):
        self.vertices = list(vertices)
        self.polygons = [SimpleNamespace(use_smooth=False) for _face in faces]

    def update(self, *, calc_edges):
        if calc_edges is not True:
            raise AssertionError('expected_original_edge_update')


class FakeBody(dict):
    def __init__(self, name, mesh):
        super().__init__()
        self.name, self.data = name, mesh


class FakeNative:
    def __init__(self):
        self.calls, self.fail = [], None
        self.primary = ValueError('fixture_primary_error')
        self.data = SimpleNamespace(objects=FakeCollection(self, 'body'), meshes=FakeCollection(self, 'mesh'), armatures=FakeCollection(self, 'armature'))
        self.context = SimpleNamespace(collection=SimpleNamespace(objects=SimpleNamespace(link=self.link)), scene={})
        self.ops = SimpleNamespace(wm=SimpleNamespace(save_as_mainfile=self.forbidden_save))

    def link(self, body):
        self.calls.append('link:' + body.name)
        if self.fail == 'link':
            raise self.primary

    def forbidden_save(self, **kwargs):
        self.calls.append('forbidden_save')
        raise AssertionError('pre_surface_lane_must_not_save')


class FakeProducer:
    PROJECT_ROOT = FixturePath('/fixture')
    MAKEHUMAN_DATA = FixturePath('/fixture/data')
    WEIGHTS_PATH = FixturePath('/fixture/data/rigs/default_weights.mhw')
    FOUNDATION_ID = 'makehuman_hm08_female_macro_source'
    CANDIDATE_AUTHOR_ID = 'avatar_foundation_authoring_pipeline_v1'
    Vector = tuple
    resolve_makehuman_skeleton_geometry = staticmethod(lambda *args: None)

    def __init__(self):
        self.bpy = FakeNative()
        self.calls = []
        self.hashes = {
            '/fixture/base.obj': integration.BASE_SHA256,
            str(self.WEIGHTS_PATH): integration.WEIGHTS_SHA256,
            '/fixture/data/rigs/default.mhskel': integration.SKELETON_SHA256,
            '/fixture/macro_a.target': sorted(integration.MACRO_PINS)[0],
            '/fixture/macro_b.target': sorted(integration.MACRO_PINS)[1],
        }
        self.bindings = [(FixturePath('/fixture/macro_a.target'), 1.0), (FixturePath('/fixture/macro_b.target'), 1.0)]
        self.authority = {'adult_eligible': True, 'foundation_authority': {'authorized': True}}
        self.config = {'candidate_id': 'rigtest_generic_female_fixture', 'target_height_m': 1.7}

    def _sha256(self, path):
        return self.hashes[str(path)]

    def _load_config(self, path):
        self.calls.append('load_config')
        return dict(self.config)

    def evaluate_adult_foundation_qualification(self, *args):
        return self.authority

    def _foundation_source_bindings(self):
        return FixturePath('/fixture/base.obj'), self.bindings, {}

    def _parse_body_group(self, path):
        self.calls.append('parse_body')
        return [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [(0, 1, 2)]

    def _apply_target(self, vertices, path, weight):
        self.calls.append('macro')
        return 3

    def _compact_and_scale(self, vertices, faces, height):
        return vertices, faces, {i: i for i in range(3)}, {'source_height_units': 1.0, 'target_height_m': height, 'uniform_scale': height, 'source_floor_z': 0.0}

    def seed_mesh_rows(self, *args):
        return [(i, i) for i in range(3)]

    def prepare_rest_handoff(self, **kwargs):
        self.calls.append('capture_rest')
        return {'projection_bytes': b'fixture_original_projection', 'projection': {'compact_rest_points_sha256': '0' * 64, 'armature_created': False, 'rig_attachment_performed': False}}

    def _attach_normalized_default_weights(self, body, mapping):
        self.calls.append('normalized_weights')
        if self.bpy.fail == 'weights':
            raise self.bpy.primary
        return {'weights_normalized': True, 'maximum_influences': 4}

    def require_mesh_rows(self, *args):
        self.calls.append('require_rows')

    def require_rest_handoff_unchanged(self, *args):
        self.calls.append('require_rest')

    def repair_bounded_self_intersections(self, *args):
        self.calls.append('forbidden_intersection_repair')
        raise AssertionError('downstream_repair_is_not_pre_surface')

    def author_continuous_adult_female_surface(self, *args, **kwargs):
        self.calls.append('forbidden_surface_authoring')
        raise AssertionError('downstream_surface_is_not_pre_surface')


class FakeBackend:
    def __init__(self, bpy, binding):
        self.bpy, self.binding, self.custody = bpy, binding, []
        if bpy.fail == 'backend_init':
            raise bpy.primary

    def observe(self, body):
        self.custody.append(('observe', body))
        return dict(self.binding)


class FakeCompiler:
    COMMON_BINDING_KEYS = ('candidate_id', 'body_profile', 'maturity_status', 'identity_scope', 'fresh_inactive_build', 'pre_surface_stage', 'handoff_sha256', 'compact_rest_points_sha256')

    def __init__(self, producer):
        self.producer, self.fail, self.primary, self.last_capture = producer, None, ValueError('compiler_primary'), None

    def compile_attachment_plan(self, rest, enrollment, observation, profile_raw):
        self.producer.calls.append('compile_attachment')
        if self.fail == 'compile':
            raise self.primary
        self.last_capture = {'plan': {'armature_name': observation['candidate_id'] + '__rest_armature', 'operations': [{'name': 'fake_bone_' + str(i)} for i in range(163)]}, 'objects': {}}
        return self.last_capture

    def attach_rest_plan(self, capture, body, backend, checkpoint):
        self.producer.calls.append('attach')
        armature = self.producer.bpy.data.armatures.new(capture['plan']['armature_name'])
        capture['objects']['armature'] = armature
        backend.custody.append(('armature', armature))
        checkpoint(capture, 'fake_native_attachment')
        if self.fail == 'attach':
            self.primary.capture = capture
            raise self.primary
        capture.update(status='IN_PROCESS_ATTACHMENT_OBSERVED_MOVEMENT_RELOAD_HOLD', full_body_ready=False, runtime_authority=False)
        return capture


class OptionalRestLaneFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global PROFILE_RAW, SKELETON_RAW
        # Future separately admitted reads of two exact immutable source fixtures.
        PROFILE_RAW = (Path(__file__).parent / 'selected-default-rig-metadata.json').read_bytes()
        SKELETON_RAW = (Path(__file__).parent / 'default.mhskel').read_bytes()

    def setUp(self):
        self.producer = FakeProducer()
        self.compiler = FakeCompiler(self.producer)
        self.pins = dict(integration.EXPECTED_SOURCE_PINS)
        self.checkpoints = []

    def checkpoint(self, state, phase):
        self.checkpoints.append(phase)
        return {'fixture_phase': phase}

    def invoke(self, *, options=None, checkpoint=None, profile_raw=None):
        return controller.run_optional_rest_lane(
            options if options is not None else {'mode': integration.MODE, 'config_path': FixturePath('/fixture/config.json'), 'acknowledge_inactive_authoring': True},
            integration=integration, producer=self.producer, compiler=self.compiler,
            backend_type=FakeBackend, profile_raw=PROFILE_RAW if profile_raw is None else profile_raw,
            source_pin_evidence=self.pins, checkpoint=self.checkpoint if checkpoint is None else checkpoint)

    def test_disabled_lane_does_not_touch_producer(self):
        result = self.invoke(options={'mode': 'disabled'})
        self.assertEqual(result['target_calls'], 0)
        self.assertEqual(self.producer.calls, [])

    def test_missing_inactive_acknowledgement_refuses_before_allocation(self):
        with self.assertRaises(ValueError):
            self.invoke(options={'mode': integration.MODE, 'config_path': FixturePath('/fixture/config.json'), 'acknowledge_inactive_authoring': False})
        self.assertEqual(len(self.producer.bpy.data.meshes), 0)

    def test_unknown_controller_field_refuses(self):
        with self.assertRaises(ValueError):
            self.invoke(options={'mode': integration.MODE, 'config_path': 'x', 'acknowledge_inactive_authoring': True, 'save': True})

    def test_wrong_source_pin_refuses_before_source_parse(self):
        self.pins['backend'] = 'f' * 64
        with self.assertRaises(integration.PreSurfaceLaneError):
            self.invoke()
        self.assertEqual(self.producer.calls, [])

    def test_wrong_profile_refuses_before_source_parse(self):
        with self.assertRaises(integration.PreSurfaceLaneError):
            self.invoke(profile_raw=b'wrong_profile')
        self.assertEqual(self.producer.calls, [])

    def test_existing_scene_is_never_deleted_or_rebound(self):
        existing = object()
        self.producer.bpy.data.objects.append(existing)
        with self.assertRaises(integration.PreSurfaceLaneError):
            self.invoke()
        self.assertIs(self.producer.bpy.data.objects[0], existing)
        self.assertEqual(self.producer.bpy.calls, [])

    def test_existing_mesh_data_refuses(self):
        self.producer.bpy.data.meshes.append(object())
        with self.assertRaises(integration.PreSurfaceLaneError):
            self.invoke()
        self.assertEqual(self.producer.bpy.calls, [])

    def test_private_candidate_id_refuses(self):
        self.producer.config['candidate_id'] = 'robert_personal_body'
        with self.assertRaises(integration.PreSurfaceLaneError):
            self.invoke()
        self.assertEqual(len(self.producer.bpy.data.meshes), 0)

    def test_wrong_weight_recipe_refuses_before_parse(self):
        self.producer.hashes[str(self.producer.WEIGHTS_PATH)] = 'f' * 64
        with self.assertRaises(integration.PreSurfaceLaneError):
            self.invoke()
        self.assertNotIn('parse_body', self.producer.calls)

    def test_duplicate_macro_refuses_before_parse(self):
        self.producer.bindings[1] = self.producer.bindings[0]
        with self.assertRaises(integration.PreSurfaceLaneError):
            self.invoke()
        self.assertNotIn('parse_body', self.producer.calls)

    def test_body_object_failure_keeps_mesh_and_primary(self):
        self.producer.bpy.fail = 'allocate:body'
        with self.assertRaises(integration.PreSurfaceLaneError) as caught:
            self.invoke()
        self.assertIs(caught.exception.primary, self.producer.bpy.primary)
        self.assertIs(caught.exception.capture['objects']['mesh'], self.producer.bpy.data.meshes[0])
        self.assertNotIn('forbidden_remove', self.producer.bpy.calls)

    def test_checkpoint_failure_after_mesh_keeps_actual_return(self):
        primary = ValueError('checkpoint_primary')
        def failing(state, phase):
            if phase == 'allocate_body_mesh':
                raise primary
        with self.assertRaises(integration.PreSurfaceLaneError) as caught:
            self.invoke(checkpoint=failing)
        allocation = next(row['value'] for row in caught.exception.capture['returns'] if row['phase'] == 'allocate_body_mesh')
        self.assertIs(allocation, self.producer.bpy.data.meshes[0])
        self.assertIs(caught.exception.primary, primary)

    def test_partial_weights_failure_keeps_body(self):
        self.producer.bpy.fail = 'weights'
        with self.assertRaises(integration.PreSurfaceLaneError) as caught:
            self.invoke()
        self.assertIs(caught.exception.capture['objects']['body'], self.producer.bpy.data.objects[0])
        self.assertFalse(self.producer.bpy.data.objects[0]['armature_present'])

    def test_backend_initialization_failure_keeps_backend_owner(self):
        self.producer.bpy.fail = 'backend_init'
        with self.assertRaises(integration.PreSurfaceLaneError) as caught:
            self.invoke()
        self.assertIs(caught.exception.capture['backend'].bpy, self.producer.bpy)
        self.assertIs(caught.exception.primary, self.producer.bpy.primary)

    def test_attachment_failure_keeps_partial_rig_primary_and_capture(self):
        self.compiler.fail = 'attach'
        with self.assertRaises(integration.PreSurfaceLaneError) as caught:
            self.invoke()
        state = caught.exception.capture
        self.assertIs(caught.exception.primary, self.compiler.primary)
        self.assertIs(state['attachment_capture'], self.compiler.last_capture)
        self.assertIs(state['underlying_partial_capture'], self.compiler.last_capture)
        self.assertEqual(len(self.producer.bpy.data.armatures), 1)
        self.assertIs(state['backend'].custody[-1][1], self.producer.bpy.data.armatures[0])
        self.assertIsNone(state['report'])

    def test_compiler_failure_keeps_body_and_backend(self):
        self.compiler.fail = 'compile'
        with self.assertRaises(integration.PreSurfaceLaneError) as caught:
            self.invoke()
        self.assertIs(caught.exception.primary, self.compiler.primary)
        self.assertIs(caught.exception.capture['objects']['body'], self.producer.bpy.data.objects[0])
        self.assertEqual(len(caught.exception.capture['backend'].custody), 1)
        self.assertEqual(len(self.producer.bpy.data.armatures), 0)

    def test_mutated_macro_binding_after_attachment_refuses_report(self):
        def mutating(state, phase):
            if phase == 'attachment:fake_native_attachment':
                self.producer.bindings[1] = self.producer.bindings[0]
        with self.assertRaises(integration.PreSurfaceLaneError) as caught:
            self.invoke(checkpoint=mutating)
        self.assertEqual(len(self.producer.bpy.data.armatures), 1)
        self.assertIsNone(caught.exception.capture['report'])

    def test_success_flags_order_and_downstream_holds(self):
        result = self.invoke()
        body = result['objects']['body']
        self.assertTrue(body['armature_present'])
        self.assertTrue(self.producer.bpy.context.scene['armature_present'])
        self.assertEqual(result['report']['bone_count'], 163)
        self.assertFalse(result['report']['surface_authoring_performed'])
        self.assertFalse(result['report']['saved_reload_performed'])
        self.assertFalse(result['full_body_ready'])
        self.assertFalse(result['normal_process_exit_observed'])
        self.assertFalse(result['runtime_authority'])
        self.assertEqual(result['rest_capture']['projection']['armature_created'], False)
        self.assertLess(self.producer.calls.index('normalized_weights'), self.producer.calls.index('attach'))
        self.assertNotIn('forbidden_intersection_repair', self.producer.calls)
        self.assertNotIn('forbidden_surface_authoring', self.producer.calls)
        self.assertNotIn('forbidden_save', self.producer.bpy.calls)
        self.assertNotIn('forbidden_remove', self.producer.bpy.calls)


if __name__ == '__main__':
    unittest.main()
