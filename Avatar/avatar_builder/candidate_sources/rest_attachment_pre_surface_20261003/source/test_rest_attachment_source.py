"""UNRUN stdlib fixtures. Random coordinates are synthetic, not a human mesh.

Tests the new compiler/consumer through a fake backend. It never imports bpy,
loads any .blend/person/private state, decodes media or qualifies physical rigs.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import unittest

import avatar_rig_rest_attachment as target

HERE = Path(__file__).resolve().parent


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def fixture():
    profile_raw = (HERE / 'selected-default-rig-metadata.json').read_bytes()
    profile = json.loads(profile_raw)
    needed = sorted({i for values in profile['joints'].values() for i in values})
    rng = random.Random(163326)
    samples = {i: [rng.randint(-100000, 100000) / 65536.0 for _ in range(3)] for i in needed}
    positions = {name: [sum(samples[i][a] for i in values) / len(values) for a in range(3)]
                 for name, values in profile['joints'].items()}

    def unit(v):
        n = math.sqrt(sum(x * x for x in v))
        return [x / n for x in v]

    normals = {}
    for name, names in profile['planes'].items():
        a, b, c = (positions[n] for n in names)
        p = unit([b[i] - a[i] for i in range(3)])
        y = unit([c[i] - b[i] for i in range(3)])
        normals[name] = unit([y[1] * p[2] - y[2] * p[1], y[2] * p[0] - y[0] * p[2], y[0] * p[1] - y[1] * p[0]])
    order = []
    pending = set(profile['bones'])
    while pending:
        ready = sorted(n for n in pending if profile['bones'][n]['parent'] is None or profile['bones'][n]['parent'] in order)
        if not ready:
            raise ValueError('fixture recipe contains a cycle')
        order.extend(ready)
        pending.difference_update(ready)
    records = {}
    for name in order:
        recipe = profile['bones'][name]
        head, tail = positions[recipe['head']], positions[recipe['tail']]
        records[name] = {'head': head[:], 'tail': tail[:], 'parent': recipe['parent'],
                         'roll_plane': recipe['rotation_plane'], 'roll_normal': normals[recipe['rotation_plane']][:],
                         'length_m': math.sqrt(sum((tail[a] - head[a]) ** 2 for a in range(3)))}
    point_pin = hashlib.sha256(b'SYNTHETIC_FAKE_BACKEND_NO_NATIVE_MESH').hexdigest()
    projection = {
        'schema': target.HANDOFF_SCHEMA, 'status': 'REST_RELATION_CAPTURED_INACTIVE_PENDING_INDEPENDENT_READBACK',
        'source_id_domain': 'zero_based_global_OBJ_v_record_index', 'canonical_vertex_count': max(needed) + 1,
        'body_source_vertex_count': 14658, 'canonical_scaled_points_sha256': point_pin,
        'compact_rest_points_sha256': point_pin, 'joint_sample_rows': [[i, *samples[i]] for i in needed],
        'joint_recipes': copy.deepcopy(profile['joints']),
        'resolved_geometry': {'bones': records, 'bone_order': order, 'joint_positions': positions,
                              'minimum_bone_length_m': min(row['length_m'] for row in records.values()),
                              'maximum_bone_length_m': max(row['length_m'] for row in records.values())},
        'coordinate_transform': {'source_height_units': 2.0, 'target_height_m': 1.7, 'uniform_scale': 0.85, 'source_floor_z': 0.0},
        'units': 'meters', 'axes': 'Blender_Z_up_negative_Y_forward',
        'numeric_basis': 'producer_two_native_Vector_stages_binary32_samples_resolver_float_arithmetic',
        'base_binding': {'path': 'GENERIC_FIXTURE_BASE_NOT_OPENED', 'sha256': target.BASE_SHA256, 'face_group': 'body'},
        'macro_target_bindings': [{'path': 'GENERIC_FIXTURE_MACRO_NOT_OPENED', 'sha256': pin, 'weight': 1.0, 'changed_vertices': 1}
                                  for pin in sorted(target.MACRO_PINS)],
        'skeleton_sha256': target.SKELETON_SHA256, 'required_unbound_resolver_source_sha256': target.RESOLVER_SHA256,
        'generated_carrier_vertex_canonical_mapping': None, 'actual_blender_rest_matrices': None,
        'armature_created': False, 'rig_attachment_performed': False, 'saved_readback_performed': False,
        'runtime_authority': False, 'rest_equals_final_surface': False,
    }
    original_capture = {'projection': projection, 'projection_bytes': encoded(projection)}
    observation = {
        'candidate_id': 'generic_synthetic_fixture_source001', 'body_profile': 'adult_female',
        'maturity_status': 'confirmed_adult', 'identity_scope': 'generic_identity_neutral',
        'fresh_inactive_build': True, 'pre_surface_stage': True,
        'handoff_sha256': hashlib.sha256(original_capture['projection_bytes']).hexdigest(),
        'compact_rest_points_sha256': point_pin, 'vertex_count': 14658, 'face_count': 15976,
        'mesh_points_sha256': point_pin, 'mesh_topology_sha256': point_pin, 'weights_sha256': point_pin,
        'body_matrix_sha256': target.IDENTITY_MATRIX_SHA256, 'weight_group_names': profile['weight_group_names'],
        'armature_count': 0, 'armature_modifier_count': 0, 'parent_name': None,
    }
    enrollment = {'producer_utility_sha256': target.PRODUCER_UTILITY_SHA256, 'binding': copy.deepcopy(observation)}
    return original_capture, enrollment, observation, profile_raw


def reseal(inputs):
    producer, enrollment, observation, _ = inputs
    producer['projection_bytes'] = encoded(producer['projection'])
    observation['handoff_sha256'] = hashlib.sha256(producer['projection_bytes']).hexdigest()
    enrollment['binding'] = copy.deepcopy(observation)


class FakeBackend:
    """Injected fake operations, independent state from the returned plan."""
    def __init__(self, observation):
        self.initial = copy.deepcopy(observation)
        self.objects = []
        self.bones = {}
        self.modifier = None
        self.parent = None
        self.after_change = None
        self.fail_configure = None
        self.custody = []

    def observe(self, body):
        result = copy.deepcopy(self.initial)
        if self.parent is not None:
            result.update({'armature_count': len(self.objects), 'armature_modifier_count': 1,
                           'parent_name': self.parent['name'], 'modifier_armature_name': self.modifier['object']['name'],
                           'vertex_groups_enabled': self.modifier['groups'], 'bone_envelopes_enabled': self.modifier['envelopes'],
                           'armature_world_matrix_sha256': target.IDENTITY_MATRIX_SHA256,
                           'parent_inverse_sha256': target.IDENTITY_MATRIX_SHA256,
                           'attached_bones': copy.deepcopy(self.bones)})
            if self.after_change:
                self.after_change(result)
        return result

    def allocate_armature_data(self, name):
        result = {'data_name': name}
        self.custody.append(result)
        return result

    def allocate_armature_object(self, name, data):
        result = {'name': name, 'data': data}
        self.custody.append(result)
        return result

    def link_armature(self, armature):
        self.objects.append(armature)

    def enter_edit_mode(self, armature):
        self.edit = True

    def allocate_bone(self, armature, name):
        bone = {'name': name}
        self.bones[name] = bone
        self.custody.append(bone)
        return bone

    def configure_bone(self, bone, operation, parent):
        bone.update({'head': operation['head'][:], 'tail': operation['tail'][:],
                     'parent': parent['name'] if parent else None,
                     'use_connect': False, 'use_deform': operation['use_deform']})
        if self.fail_configure and len(self.bones) == 2:
            raise self.fail_configure

    def finish_edit_mode(self):
        self.edit = False

    def allocate_modifier(self, body, name):
        self.modifier = {'name': name}
        self.custody.append(self.modifier)
        return self.modifier

    def configure_modifier(self, modifier, armature):
        modifier.update({'object': armature, 'groups': True, 'envelopes': False})

    def copy_body_world(self, body):
        return {'fake_identity_matrix': True}

    def armature_world_inverse(self, armature):
        return {'fake_inverse_identity_matrix': True}

    def bind_parent_preserving_world(self, body, armature, world, inverse):
        self.parent = armature


class SourceFixtures(unittest.TestCase):
    def plan(self):
        return target.compile_attachment_plan(*fixture())

    def refused(self, inputs, expected):
        with self.assertRaises(target.AttachmentError) as caught:
            target.compile_attachment_plan(*inputs)
        self.assertIn(expected, str(caught.exception.primary))
        self.assertFalse(caught.exception.capture['execution_authority'])

    def test_compiles_all_163_names_and_139_existing_deform_groups(self):
        inputs = fixture()
        result = target.compile_attachment_plan(*inputs)
        self.assertIs(result['producer_capture'], inputs[0])
        self.assertEqual(len(result['plan']['operations']), 163)
        self.assertEqual(sum(op['use_deform'] for op in result['plan']['operations']), 139)
        self.assertFalse(result['plan']['execution_authority'])

    def test_old_carrier_without_original_v3_capture_is_refused(self):
        inputs = list(fixture())
        inputs[0] = {'projection': inputs[0]['projection']}
        self.refused(inputs, 'missing_original_v3_rest_capture')

    def test_female_recipe_cannot_be_relabelled_as_male(self):
        inputs = fixture()
        inputs[2]['body_profile'] = 'adult_male'
        reseal(inputs)
        self.refused(inputs, 'unselected_or_private_or_nonfresh_body_lane')

    def test_private_identity_is_not_promoted_to_generic_recipe(self):
        inputs = fixture()
        inputs[2]['identity_scope'] = 'private_person'
        reseal(inputs)
        self.refused(inputs, 'unselected_or_private_or_nonfresh_body_lane')

    def test_altered_profile_bytes_are_refused(self):
        inputs = list(fixture())
        inputs[3] += b' '
        self.refused(inputs, 'unselected_default_rig_metadata')

    def test_wrong_macro_recipe_is_refused(self):
        inputs = fixture()
        inputs[0]['projection']['macro_target_bindings'][0]['sha256'] = '0' * 64
        reseal(inputs)
        self.refused(inputs, 'selected_female_macro_recipe_disagrees')

    def test_invalid_scale_is_refused(self):
        inputs = fixture()
        inputs[0]['projection']['coordinate_transform']['uniform_scale'] = -0.85
        reseal(inputs)
        self.refused(inputs, 'captured_coordinate_transform_disagrees')

    def test_duplicate_bone_order_is_refused(self):
        inputs = fixture()
        order = inputs[0]['projection']['resolved_geometry']['bone_order']
        order[-1] = order[0]
        reseal(inputs)
        self.refused(inputs, 'resolved_named_rig_roster_disagrees')

    def test_child_before_parent_is_refused(self):
        inputs = fixture()
        inputs[0]['projection']['resolved_geometry']['bone_order'].reverse()
        reseal(inputs)
        self.refused(inputs, 'parent_not_before_child_or_cycle')

    def test_changed_parent_relation_is_refused(self):
        inputs = fixture()
        inputs[0]['projection']['resolved_geometry']['bones']['root']['parent'] = 'root'
        reseal(inputs)
        self.refused(inputs, 'selected_parent_relation_disagrees')

    def test_global_joint_sample_id_alias_is_refused(self):
        inputs = fixture()
        rows = inputs[0]['projection']['joint_sample_rows']
        rows[0][0] = rows[1][0]
        reseal(inputs)
        self.refused(inputs, 'joint_sample_global_id_order_disagrees')

    def test_unbound_joint_position_is_refused(self):
        inputs = fixture()
        joints = inputs[0]['projection']['resolved_geometry']['joint_positions']
        joints[next(iter(joints))][0] += 0.125
        reseal(inputs)
        self.refused(inputs, 'joint_position_not_captured_sample_mean')

    def test_changed_roll_normal_is_refused(self):
        inputs = fixture()
        inputs[0]['projection']['resolved_geometry']['bones']['root']['roll_normal'] = [0.0, 0.0, 0.0]
        reseal(inputs)
        self.refused(inputs, 'named_endpoints_or_plane_disagree')

    def test_existing_weights_and_rest_points_are_required(self):
        for field in ('weight_group_names', 'mesh_points_sha256'):
            with self.subTest(field=field):
                inputs = fixture()
                if field == 'weight_group_names':
                    inputs[2][field] = inputs[2][field][:-1]
                    expected = 'existing_weights_not_selected_default_groups'
                else:
                    inputs[2][field] = '0' * 64
                    expected = 'surface_authoring_already_changed_canonical_carrier'
                reseal(inputs)
                self.refused(inputs, expected)

    def test_fake_attachment_success_stays_movement_and_reload_hold(self):
        capture = self.plan()
        backend = FakeBackend(capture['initial_observation'])
        result = target.attach_rest_plan(capture, object(), backend, lambda cap, phase: None)
        self.assertEqual(result['status'], 'IN_PROCESS_ATTACHMENT_OBSERVED_MOVEMENT_RELOAD_HOLD')
        self.assertEqual(len(backend.bones), 163)
        self.assertFalse(result['full_body_ready'])
        self.assertFalse(result['runtime_authority'])

    def test_new_native_observation_change_refuses_before_allocation(self):
        capture = self.plan()
        backend = FakeBackend(capture['initial_observation'])
        backend.initial['mesh_topology_sha256'] = '0' * 64
        with self.assertRaises(target.AttachmentError):
            target.attach_rest_plan(capture, object(), backend, lambda cap, phase: None)
        self.assertEqual(backend.custody, [])

    def test_checkpoint_error_preserves_primary_and_original_allocation(self):
        capture = self.plan()
        backend = FakeBackend(capture['initial_observation'])
        primary = RuntimeError('SOURCE_FIXTURE_CHECKPOINT_STOP')

        def checkpoint(cap, phase):
            if phase == 'allocate_armature_data':
                raise primary

        with self.assertRaises(target.AttachmentError) as caught:
            target.attach_rest_plan(capture, object(), backend, checkpoint)
        self.assertIs(caught.exception.primary, primary)
        self.assertIs(capture['returns'][-1]['value'], backend.custody[0])

    def test_callback_plan_mutation_preserves_return_then_refuses(self):
        capture = self.plan()
        backend = FakeBackend(capture['initial_observation'])

        def checkpoint(cap, phase):
            if phase == 'allocate_armature_data':
                cap['plan']['armature_name'] += '_mutated'
            return 'checkpoint_return_retained'

        with self.assertRaises(target.AttachmentError) as caught:
            target.attach_rest_plan(capture, object(), backend, checkpoint)
        self.assertIn('attachment_input_changed:plan', str(caught.exception.primary))
        self.assertIs(capture['returns'][-2]['value'], backend.custody[0])
        self.assertEqual(capture['returns'][-1]['value'], 'checkpoint_return_retained')

    def test_partial_bones_and_primary_error_survive_without_cleanup(self):
        capture = self.plan()
        backend = FakeBackend(capture['initial_observation'])
        primary = RuntimeError('SOURCE_FIXTURE_SECOND_BONE_CONFIGURE_ERROR')
        backend.fail_configure = primary
        with self.assertRaises(target.AttachmentError) as caught:
            target.attach_rest_plan(capture, object(), backend, lambda cap, phase: None)
        self.assertIs(caught.exception.primary, primary)
        self.assertEqual(len(backend.bones), 2)
        for name, bone in backend.bones.items():
            self.assertIs(capture['objects']['bones'][name], bone)
        self.assertTrue(backend.edit)

    def test_zero_armature_final_readback_is_refused_and_retained(self):
        capture = self.plan()
        backend = FakeBackend(capture['initial_observation'])
        backend.after_change = lambda result: result.update(armature_count=0)
        with self.assertRaises(target.AttachmentError) as caught:
            target.attach_rest_plan(capture, object(), backend, lambda cap, phase: None)
        self.assertIn('actual_attachment_readback_disagrees', str(caught.exception.primary))
        self.assertEqual(len(backend.objects), 1)

    def test_any_post_attachment_body_evidence_change_is_refused(self):
        for field in ('mesh_points_sha256', 'mesh_topology_sha256', 'weights_sha256', 'body_matrix_sha256'):
            with self.subTest(field=field):
                capture = self.plan()
                backend = FakeBackend(capture['initial_observation'])
                backend.after_change = lambda result, key=field: result.update({key: '0' * 64})
                with self.assertRaises(target.AttachmentError) as caught:
                    target.attach_rest_plan(capture, object(), backend, lambda cap, phase: None)
                self.assertIn('body_topology_points_weights_matrix_or_lineage_changed', str(caught.exception.primary))
                self.assertEqual(len(backend.objects), 1)

    def test_wrong_native_bone_parent_is_refused(self):
        capture = self.plan()
        backend = FakeBackend(capture['initial_observation'])

        def wrong_parent(result):
            result['attached_bones']['root']['parent'] = 'root'

        backend.after_change = wrong_parent
        with self.assertRaises(target.AttachmentError) as caught:
            target.attach_rest_plan(capture, object(), backend, lambda cap, phase: None)
        self.assertIn('actual_bone_endpoints_or_flags_disagree:root', str(caught.exception.primary))


if __name__ == '__main__':
    unittest.main()
