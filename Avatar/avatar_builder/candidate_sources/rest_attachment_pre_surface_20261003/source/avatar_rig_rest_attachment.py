"""SOURCE CANDIDATE: consume the v3 rest capture before surface authoring.

No Blender import, file loading/saving, activation, weights authoring, grants,
registry promotion or anatomy claim. The caller owns separate admission. Every
backend/checkpoint return is retained before validation or another callback.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct

HANDOFF_SCHEMA = 'kira.avatar.canonical_rig_rest_handoff.v1'
PROFILE_SHA256 = '271b660568ebd33c97950f9988888e36455d5637574f2a20724b436b6dd0488c'
SKELETON_SHA256 = '5acfcaff5f0f46f88bc2a2935c18b65f7ba4f10c99a6628e97d08d2ef7bb9ba0'
RESOLVER_SHA256 = 'e986c5c82596e043b7060d75a91b23fd8d1a6ab13f687f60373347a3ce257d33'
PRODUCER_UTILITY_SHA256 = '09dde1d9acfc6305fcb69ad739c8904af8c1e37ebe25660a2a5a3d97d6271b9b'
BASE_SHA256 = 'bea00279464133e86b634220cd2774ebf3b470de280d11222a6b2269e4a8d950'
IDENTITY_MATRIX_SHA256 = '5998e9d1dd9bf48af6af87a1ef8c7783b818ac8329637ada08cc5fb329042376'
MACRO_PINS = {
    '9537a8b2d76a06f49f5f8cb25955b52f1245e3119cfe0cb2634a9ca4e12b3e1f',
    '6352040adcd91d48bc2266a65246ff0be39afb1f3d309311426204a95c1cbd77',
}
COMMON_BINDING_KEYS = (
    'candidate_id', 'body_profile', 'maturity_status', 'identity_scope',
    'fresh_inactive_build', 'pre_surface_stage', 'handoff_sha256',
    'compact_rest_points_sha256', 'vertex_count', 'face_count',
    'mesh_points_sha256', 'mesh_topology_sha256', 'weights_sha256',
    'body_matrix_sha256', 'weight_group_names',
)


class AttachmentError(RuntimeError):
    def __init__(self, message, capture, primary=None):
        super().__init__(message)
        self.capture = capture
        self.primary = primary


def _raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pin(value, label):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('invalid_hash:' + label)
    return value


def _point(value):
    if type(value) not in (list, tuple) or len(value) != 3:
        raise ValueError('invalid_point_shape')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError('nonfinite_or_nonnumeric_point')
    return tuple(float(x) for x in value)


def _native_point(value):
    return list(struct.unpack('<3f', struct.pack('<3f', *_point(value))))


def _length(value):
    return math.sqrt(sum(x * x for x in value))


def _subtract(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _normalized(value):
    length = _length(value)
    if length <= 1e-10:
        raise ValueError('degenerate_selected_roll_plane')
    return tuple(x / length for x in value)


def _sampled_geometry(projection, profile):
    count = projection.get('canonical_vertex_count')
    if type(count) is not int or count <= 0:
        raise ValueError('invalid_global_vertex_domain')
    rows = projection.get('joint_sample_rows')
    needed = sorted({index for recipe in profile['joints'].values() for index in recipe})
    if type(rows) is not list or len(rows) != len(needed) or needed[-1] >= count:
        raise ValueError('missing_or_extra_canonical_joint_samples')
    points = {}
    for expected, row in zip(needed, rows):
        if type(row) is not list or len(row) != 4 or type(row[0]) is not int or row[0] != expected:
            raise ValueError('joint_sample_global_id_order_disagrees')
        point = _point(row[1:])
        if tuple(_native_point(point)) != point:
            raise ValueError('joint_sample_not_native_binary32')
        points[expected] = point
    joints = {name: tuple(sum(points[index][axis] for index in recipe) / len(recipe) for axis in range(3))
              for name, recipe in profile['joints'].items()}
    normals = {}
    for name, recipe in profile['planes'].items():
        a, b, c = (joints[joint] for joint in recipe)
        p, y = _normalized(_subtract(b, a)), _normalized(_subtract(c, b))
        normals[name] = _normalized((y[1] * p[2] - y[2] * p[1],
                                     y[2] * p[0] - y[0] * p[2],
                                     y[0] * p[1] - y[1] * p[0]))
    return joints, normals


def _static_binding(observation):
    if type(observation) is not dict or any(key not in observation for key in COMMON_BINDING_KEYS):
        raise ValueError('incomplete_observation_binding')
    result = {key: observation[key] for key in COMMON_BINDING_KEYS}
    if (result['body_profile'] != 'adult_female' or result['maturity_status'] != 'confirmed_adult'
            or result['identity_scope'] != 'generic_identity_neutral'
            or result['fresh_inactive_build'] is not True or result['pre_surface_stage'] is not True):
        raise ValueError('unselected_or_private_or_nonfresh_body_lane')
    if type(result['candidate_id']) is not str or not result['candidate_id']:
        raise ValueError('missing_candidate_id')
    if type(result['vertex_count']) is not int or result['vertex_count'] != 14658:
        raise ValueError('selected_vertex_domain_disagrees')
    if type(result['face_count']) is not int or result['face_count'] != 15976:
        raise ValueError('selected_face_domain_disagrees')
    for key in COMMON_BINDING_KEYS:
        if key.endswith('_sha256'):
            _pin(result[key], key)
    if (type(result['weight_group_names']) is not list
            or any(type(name) is not str for name in result['weight_group_names'])):
        raise ValueError('invalid_weight_group_names')
    return result


def compile_attachment_plan(producer_capture, enrollment, observation, profile_raw):
    """Compile a same-process fresh canonical-carrier rest capture.

    Enrollment must be separately prepared from independently observed fresh
    working-copy facts. Matching these dictionaries is a value check, never an
    authorization, external file rehash, saved reload or native-origin proof.
    """
    capture = {'producer_capture': producer_capture, 'enrollment': enrollment,
               'initial_observation': observation, 'profile_raw': profile_raw,
               'phase': 'compile', 'returns': [], 'objects': {}, 'execution_authority': False}
    try:
        if type(profile_raw) is not bytes or _sha(profile_raw) != PROFILE_SHA256:
            raise ValueError('unselected_default_rig_metadata')
        profile = json.loads(profile_raw)
        capture['profile'] = profile
        if (profile['skeleton_sha256'] != SKELETON_SHA256
                or profile['resolver_source_sha256'] != RESOLVER_SHA256):
            raise ValueError('selected_profile_lineage_disagrees')
        if type(producer_capture) is not dict or type(producer_capture.get('projection_bytes')) is not bytes:
            raise ValueError('missing_original_v3_rest_capture')
        projection = producer_capture.get('projection')
        if type(projection) is not dict or _raw(projection) != producer_capture['projection_bytes']:
            raise ValueError('original_projection_bytes_disagree')
        if (projection.get('schema') != HANDOFF_SCHEMA
                or projection.get('status') != 'REST_RELATION_CAPTURED_INACTIVE_PENDING_INDEPENDENT_READBACK'
                or projection.get('skeleton_sha256') != SKELETON_SHA256
                or projection.get('required_unbound_resolver_source_sha256') != RESOLVER_SHA256
                or projection.get('units') != 'meters'
                or projection.get('axes') != 'Blender_Z_up_negative_Y_forward'
                or projection.get('numeric_basis') != 'producer_two_native_Vector_stages_binary32_samples_resolver_float_arithmetic'
                or projection.get('source_id_domain') != 'zero_based_global_OBJ_v_record_index'):
            raise ValueError('rest_capture_contract_disagrees')
        for field in ('armature_created', 'rig_attachment_performed', 'saved_readback_performed', 'runtime_authority', 'rest_equals_final_surface'):
            if projection.get(field) is not False:
                raise ValueError('capture_claimed_unqualified_stage:' + field)
        if (projection.get('generated_carrier_vertex_canonical_mapping') is not None
                or projection.get('actual_blender_rest_matrices') is not None):
            raise ValueError('unselected_capture_domain')
        transform = projection.get('coordinate_transform')
        if (type(transform) is not dict or set(transform) != {'source_height_units', 'target_height_m', 'uniform_scale', 'source_floor_z'}
                or any(type(value) is not float or not math.isfinite(value) for value in transform.values())
                or transform['source_height_units'] <= 1e-8 or not 1.4 <= transform['target_height_m'] <= 2.1
                or transform['uniform_scale'] <= 0.0
                or not math.isclose(transform['uniform_scale'], transform['target_height_m'] / transform['source_height_units'], rel_tol=1e-15)):
            raise ValueError('captured_coordinate_transform_disagrees')
        if type(enrollment) is not dict or enrollment.get('producer_utility_sha256') != PRODUCER_UTILITY_SHA256:
            raise ValueError('missing_selected_producer_enrollment')
        binding = _static_binding(observation)
        if _raw(binding) != _raw(_static_binding(enrollment['binding'])):
            raise ValueError('enrollment_and_native_observation_disagree')
        if binding['handoff_sha256'] != _sha(producer_capture['projection_bytes']):
            raise ValueError('fresh_carrier_handoff_pin_disagrees')
        if binding['compact_rest_points_sha256'] != projection.get('compact_rest_points_sha256'):
            raise ValueError('rest_points_binding_disagrees')
        if binding['mesh_points_sha256'] != binding['compact_rest_points_sha256']:
            raise ValueError('surface_authoring_already_changed_canonical_carrier')
        if binding['body_matrix_sha256'] != IDENTITY_MATRIX_SHA256:
            raise ValueError('canonical_carrier_world_matrix_not_identity')
        if projection.get('body_source_vertex_count') != binding['vertex_count']:
            raise ValueError('capture_compact_domain_disagrees')
        if (type(observation.get('armature_count')) is not int or type(observation.get('armature_modifier_count')) is not int
                or observation.get('armature_count') != 0 or observation.get('armature_modifier_count') != 0
                or observation.get('parent_name') is not None):
            raise ValueError('working_copy_already_attached_or_not_isolated')
        if binding['weight_group_names'] != profile['weight_group_names']:
            raise ValueError('existing_weights_not_selected_default_groups')
        base = projection.get('base_binding')
        if type(base) is not dict or base.get('sha256') != BASE_SHA256 or base.get('face_group') != 'body':
            raise ValueError('selected_base_binding_disagrees')
        macros = projection.get('macro_target_bindings')
        if type(macros) is not list or len(macros) != 2:
            raise ValueError('selected_macro_recipe_missing')
        found = []
        for row in macros:
            if (type(row) is not dict or row.get('sha256') not in MACRO_PINS
                    or type(row.get('weight')) is not float or row.get('weight') != 1.0
                    or type(row.get('changed_vertices')) is not int or row['changed_vertices'] <= 0):
                raise ValueError('selected_female_macro_recipe_disagrees')
            found.append(row['sha256'])
        if set(found) != set(MACRO_PINS):
            raise ValueError('duplicate_or_missing_macro_target')
        if projection.get('joint_recipes') != profile['joints']:
            raise ValueError('joint_recipes_not_selected_skeleton')
        geometry = projection.get('resolved_geometry')
        if type(geometry) is not dict:
            raise ValueError('missing_resolved_rest_geometry')
        bones, order, joints = (geometry.get(key) for key in ('bones', 'bone_order', 'joint_positions'))
        if (type(bones) is not dict or set(bones) != set(profile['bones']) or len(bones) != 163
                or type(order) is not list or len(order) != 163 or len(set(order)) != 163 or set(order) != set(bones)
                or type(joints) is not dict or set(joints) != set(profile['joints'])):
            raise ValueError('resolved_named_rig_roster_disagrees')
        sampled_joints, sampled_normals = _sampled_geometry(projection, profile)
        for name, point in joints.items():
            if _point(point) != sampled_joints[name]:
                raise ValueError('joint_position_not_captured_sample_mean')
        operations, seen, roots = [], set(), []
        for name in order:
            record, recipe = bones[name], profile['bones'][name]
            if type(record) is not dict or record.get('parent') != recipe['parent']:
                raise ValueError('selected_parent_relation_disagrees')
            parent = record['parent']
            if parent is None:
                roots.append(name)
            elif parent not in seen:
                raise ValueError('parent_not_before_child_or_cycle')
            head, tail, normal = (_point(record.get(key)) for key in ('head', 'tail', 'roll_normal'))
            if (head != _point(joints[recipe['head']]) or tail != _point(joints[recipe['tail']])
                    or record.get('roll_plane') != recipe['rotation_plane']
                    or normal != sampled_normals[recipe['rotation_plane']]):
                raise ValueError('named_endpoints_or_plane_disagree')
            length = _length(tuple(tail[i] - head[i] for i in range(3)))
            declared = record.get('length_m')
            if (length <= 1e-7 or type(declared) not in (int, float) or not math.isfinite(declared)
                    or not math.isclose(length, declared, rel_tol=1e-12, abs_tol=1e-12)
                    or not math.isclose(_length(normal), 1.0, rel_tol=1e-8, abs_tol=1e-8)):
                raise ValueError('invalid_or_degenerate_resolved_bone')
            native_head, native_tail = _native_point(head), _native_point(tail)
            if _length(tuple(native_tail[i] - native_head[i] for i in range(3))) <= 1e-7:
                raise ValueError('bone_collapses_in_native_binary32')
            operations.append({'name': name, 'parent': parent, 'head': native_head, 'tail': native_tail,
                               'roll_normal': list(normal), 'use_connect': False,
                               'use_deform': name in binding['weight_group_names']})
            seen.add(name)
        if roots != ['root']:
            raise ValueError('selected_root_disagrees')
        lengths = [bones[name]['length_m'] for name in order]
        if geometry.get('minimum_bone_length_m') != min(lengths) or geometry.get('maximum_bone_length_m') != max(lengths):
            raise ValueError('captured_length_range_disagrees')
        plan = {'schema': 'kira.avatar.rest_attachment_plan.v1', 'binding': binding,
                'operations': operations, 'armature_name': binding['candidate_id'] + '__rest_armature',
                'modifier_name': 'Inactive_Rest_Attachment_Source001',
                'status': 'SOURCE_PLAN_PHYSICAL_ATTACHMENT_RELOAD_DEFORMATION_HOLD',
                'execution_authority': False}
        capture['plan'] = plan
        capture['snapshots'] = {'plan': _raw(plan), 'enrollment': _raw(enrollment),
                                'observation': _raw(observation), 'projection': producer_capture['projection_bytes']}
        capture['phase'] = 'plan_compiled'
        return capture
    except Exception as primary:
        raise AttachmentError('attachment_plan_refused', capture, primary) from primary


def require_plan_unchanged(capture):
    """Cooperating value guard; does not establish hostile/concurrent custody."""
    snapshots = capture['snapshots']
    values = {'plan': capture['plan'], 'enrollment': capture['enrollment'],
              'observation': capture['initial_observation'], 'projection': capture['producer_capture']['projection']}
    for key, value in values.items():
        if _raw(value) != snapshots[key]:
            raise ValueError('attachment_input_changed:' + key)
    if capture['producer_capture']['projection_bytes'] != snapshots['projection']:
        raise ValueError('original_projection_bytes_changed')
    if _sha(capture['profile_raw']) != PROFILE_SHA256:
        raise ValueError('selected_profile_bytes_changed')


def _verify_attached(observation, plan):
    if _raw(_static_binding(observation)) != _raw(plan['binding']):
        raise ValueError('body_topology_points_weights_matrix_or_lineage_changed')
    if (observation.get('armature_count') != 1 or observation.get('armature_modifier_count') != 1
            or observation.get('parent_name') != plan['armature_name']
            or observation.get('modifier_armature_name') != plan['armature_name']
            or observation.get('armature_world_matrix_sha256') != IDENTITY_MATRIX_SHA256
            or observation.get('parent_inverse_sha256') != IDENTITY_MATRIX_SHA256
            or observation.get('vertex_groups_enabled') is not True
            or observation.get('bone_envelopes_enabled') is not False):
        raise ValueError('actual_attachment_readback_disagrees')
    bones = observation.get('attached_bones')
    if type(bones) is not dict or set(bones) != {op['name'] for op in plan['operations']}:
        raise ValueError('actual_named_bone_readback_disagrees')
    for op in plan['operations']:
        actual = bones[op['name']]
        if (type(actual) is not dict or actual.get('parent') != op['parent']
                or actual.get('use_deform') is not op['use_deform']
                or actual.get('use_connect') is not False
                or _native_point(actual.get('head')) != op['head']
                or _native_point(actual.get('tail')) != op['tail']):
            raise ValueError('actual_bone_endpoints_or_flags_disagree:' + op['name'])


def attach_rest_plan(capture, body, backend, checkpoint):
    """Consume a compiled plan only in a separately admitted inactive working copy.

    The required checkpoint callback supplies the future root-owned cooperative
    budget/clock observer. All allocation returns and partial mutations survive
    errors; this function never deletes/retries/saves or grants admission.
    """
    capture['body'] = body
    capture['backend'] = backend
    capture['checkpoint_callback'] = checkpoint
    try:
        if not callable(checkpoint):
            raise ValueError('required_checkpoint_callback_missing')
        require_plan_unchanged(capture)
        plan = capture['plan']

        def call(label, callback, *args):
            capture['phase'] = label
            value = callback(*args)
            capture['returns'].append({'phase': label, 'value': value})
            require_plan_unchanged(capture)
            note = checkpoint(capture, label)
            capture['returns'].append({'phase': label + ':checkpoint', 'value': note})
            require_plan_unchanged(capture)
            return value

        before = call('observe_before', backend.observe, body)
        if (_raw(before) != capture['snapshots']['observation']):
            raise ValueError('initial_native_observation_changed_before_mutation')
        data = call('allocate_armature_data', backend.allocate_armature_data, plan['armature_name'])
        capture['objects']['armature_data'] = data
        if data is None:
            raise ValueError('missing_native_armature_data')
        armature = call('allocate_armature_object', backend.allocate_armature_object, plan['armature_name'], data)
        capture['objects']['armature'] = armature
        if armature is None:
            raise ValueError('missing_native_armature_object')
        call('link_armature', backend.link_armature, armature)
        call('enter_edit_mode', backend.enter_edit_mode, armature)
        created = capture['objects']['bones'] = {}
        for op in plan['operations']:
            bone = call('allocate_bone:' + op['name'], backend.allocate_bone, armature, op['name'])
            created[op['name']] = bone
            if bone is None:
                raise ValueError('missing_native_edit_bone:' + op['name'])
            call('configure_bone:' + op['name'], backend.configure_bone, bone, op, created.get(op['parent']))
        call('finish_edit_mode', backend.finish_edit_mode)
        modifier = call('allocate_modifier', backend.allocate_modifier, body, plan['modifier_name'])
        capture['objects']['modifier'] = modifier
        if modifier is None:
            raise ValueError('missing_native_modifier')
        call('configure_modifier', backend.configure_modifier, modifier, armature)
        world = call('copy_body_world', backend.copy_body_world, body)
        capture['objects']['original_body_world'] = world
        inverse = call('armature_world_inverse', backend.armature_world_inverse, armature)
        capture['objects']['parent_inverse'] = inverse
        call('bind_parent_preserving_world', backend.bind_parent_preserving_world, body, armature, world, inverse)
        after = call('observe_after', backend.observe, body)
        _verify_attached(after, plan)
        capture['phase'] = 'attachment_observed'
        capture['status'] = 'IN_PROCESS_ATTACHMENT_OBSERVED_MOVEMENT_RELOAD_HOLD'
        capture['full_body_ready'] = False
        capture['runtime_authority'] = False
        return capture
    except Exception as primary:
        capture['status'] = 'PARTIAL_ATTACHMENT_OR_REFUSAL_RETAINED_NO_CLEANUP_OR_RETRY'
        raise AttachmentError('attachment_consumer_refused', capture, primary) from primary
