"""Source-only optional generic rig-test producer; never saves or activates.

Uses selected v3 parsing/transform/lineage/weight helpers, then stops at the
pre-surface attachment stage. Every successful native return stays reachable
before a later callback. Caller admission/origin/input/clock/IO/normal-exit
qualification is separate; the callback and matching pins grant none of it.
"""
from __future__ import annotations

import hashlib
import json

MODE = 'generic_female_pre_surface_rest_test_v1'
EXPECTED_SOURCE_PINS = {
    'v3_producer': '63e968a6a6a3681b996228adee9e491581c6d75f507decba63d62cb9fd570b44',
    'rest_utility': '09dde1d9acfc6305fcb69ad739c8904af8c1e37ebe25660a2a5a3d97d6271b9b',
    'canonical_lineage': '8926c9b6736ae124287b97ef55f583742c1525f56daf57f81c9ac82648b31c29',
    'resolver': 'e986c5c82596e043b7060d75a91b23fd8d1a6ab13f687f60373347a3ce257d33',
    'compiler': '2ea78d0694b33e006d7be713a0857cf65117cf4ce941ce46375549578c2ebbde',
    'backend': 'c0af42735fbec2a70d76e65911a9e3cbb6063565e62490bfa3cc6b16c69abe5a',
    'profile': '271b660568ebd33c97950f9988888e36455d5637574f2a20724b436b6dd0488c',
}
BASE_SHA256 = 'bea00279464133e86b634220cd2774ebf3b470de280d11222a6b2269e4a8d950'
SKELETON_SHA256 = '5acfcaff5f0f46f88bc2a2935c18b65f7ba4f10c99a6628e97d08d2ef7bb9ba0'
WEIGHTS_SHA256 = 'ae2d830adb5ee890c90e071bde6efaa2b9c1f2937b49770f7b5264041637b071'
MACRO_PINS = {
    '9537a8b2d76a06f49f5f8cb25955b52f1245e3119cfe0cb2634a9ca4e12b3e1f',
    '6352040adcd91d48bc2266a65246ff0be39afb1f3d309311426204a95c1cbd77',
}
HELD_POSE_GATE = (
    'Pre-surface attachment observation only. Independent saved reload, rest '
    'roll/deformation, coherent later surface authoring, movement, collision, '
    'sensory mapping, full anatomy and physiology remain required.'
)


class PreSurfaceLaneError(RuntimeError):
    def __init__(self, capture, primary):
        super().__init__('pre_surface_rest_lane_failed_no_cleanup_or_retry')
        self.capture = capture
        self.primary = primary


def produce_pre_surface_rest_lane(*, producer, compiler, backend_type,
                                  profile_raw, source_pin_evidence,
                                  config_path, checkpoint, selected_mode):
    """Explicit inactive lane, called only by a separately admitted controller.

    `source_pin_evidence` records the caller's selected source checks. It does
    not authenticate supplied function objects or establish physical custody.
    The caller must pin Core/tools imports, bpy, Vector, all sources and origins
    before admitting this function. No old carrier is accepted or rebound.
    """
    state = {'schema': 'kira.avatar.pre_surface_rest_lane.capture.v1',
             'phase': 'preflight', 'producer': producer, 'compiler': compiler,
             'backend_type': backend_type, 'profile_raw': profile_raw,
             'source_pin_evidence': source_pin_evidence, 'checkpoint': checkpoint,
             'returns': [], 'objects': {}, 'attachment_capture': None,
             'report': None, 'runtime_authority': False, 'full_body_ready': False,
             'normal_process_exit_observed': False}

    def call(label, callback, *args, **kwargs):
        state['phase'] = label
        value = callback(*args, **kwargs)
        state['returns'].append({'phase': label, 'value': value})
        note = checkpoint(state, label)
        state['returns'].append({'phase': label + ':checkpoint', 'value': note})
        return value

    def require_sources_unchanged():
        if source_pin_evidence != EXPECTED_SOURCE_PINS:
            raise ValueError('selected_source_evidence_changed')
        if hashlib.sha256(profile_raw).hexdigest() != EXPECTED_SOURCE_PINS['profile']:
            raise ValueError('selected_profile_bytes_changed')
        if producer._sha256(base_path) != BASE_SHA256:
            raise ValueError('base_changed_during_pre_surface_lane')
        if producer._sha256(producer.WEIGHTS_PATH) != WEIGHTS_SHA256:
            raise ValueError('weights_changed_during_pre_surface_lane')
        if producer._sha256(skeleton_path) != SKELETON_SHA256:
            raise ValueError('skeleton_changed_during_pre_surface_lane')
        if tuple(target_bindings) != state['target_binding_snapshot']:
            raise ValueError('selected_macro_binding_order_or_path_changed')
        for path, weight in target_bindings:
            if producer._sha256(path) not in MACRO_PINS or weight != 1.0:
                raise ValueError('macro_changed_during_pre_surface_lane')

    try:
        if selected_mode != MODE or not callable(checkpoint):
            raise ValueError('explicit_lane_and_root_checkpoint_required')
        if type(source_pin_evidence) is not dict or source_pin_evidence != EXPECTED_SOURCE_PINS:
            raise ValueError('unselected_source_evidence')
        if type(profile_raw) is not bytes or hashlib.sha256(profile_raw).hexdigest() != EXPECTED_SOURCE_PINS['profile']:
            raise ValueError('unselected_profile_bytes')
        state['selected_source_snapshot'] = dict(source_pin_evidence)
        # No blanket scene deletion: fresh separate process/empty scene only.
        if (len(producer.bpy.data.objects) != 0 or len(producer.bpy.data.meshes) != 0
                or len(producer.bpy.data.armatures) != 0):
            raise ValueError('fresh_empty_scene_required_no_deletion_authorized')
        call('initial_empty_scene_checkpoint', lambda: None)
        config = call('load_selected_config', producer._load_config, config_path)
        state['config'] = config
        candidate_id = config['candidate_id']
        if not candidate_id.startswith('rigtest_generic_female_'):
            raise ValueError('generic_test_id_prefix_required')
        if not 1.4 <= float(config['target_height_m']) <= 2.05:
            raise ValueError('height_outside_shared_selected_lane')
        authority = call('foundation_source_authority', producer.evaluate_adult_foundation_qualification,
                         producer.PROJECT_ROOT, producer.FOUNDATION_ID)
        if (authority.get('adult_eligible') is not True
                or authority['foundation_authority'].get('authorized') is not True):
            raise ValueError('selected_confirmed_adult_source_authority_missing')
        base_path, target_bindings, registry_entry = call('foundation_source_bindings', producer._foundation_source_bindings)
        state['source_bindings'] = (base_path, target_bindings, registry_entry)
        state['target_binding_snapshot'] = tuple(target_bindings)
        if (len(target_bindings) != 2
                or {producer._sha256(path) for path, _weight in target_bindings} != MACRO_PINS
                or any(type(weight) is not float or weight != 1.0 for _path, weight in target_bindings)
                or producer._sha256(base_path) != BASE_SHA256
                or producer._sha256(producer.WEIGHTS_PATH) != WEIGHTS_SHA256):
            raise ValueError('selected_base_macro_or_weights_recipe_disagrees')
        vertices, faces = call('parse_selected_body_group', producer._parse_body_group, base_path)
        state['original_vertices_and_faces'] = (vertices, faces)
        target_records = state['target_records'] = []
        for path, weight in target_bindings:
            count = call('apply_selected_macro:' + path.name, producer._apply_target, vertices, path, weight)
            target_records.append({'path': path.relative_to(producer.PROJECT_ROOT).as_posix(),
                                   'sha256': producer._sha256(path), 'weight': weight,
                                   'changed_vertices': count})
        compact, compact_faces, old_to_new, transform = call('compact_and_scale', producer._compact_and_scale,
                                                            vertices, faces, float(config['target_height_m']))
        state['compact_inputs'] = (compact, compact_faces, old_to_new, transform)
        name = candidate_id + '__primary_surface'
        # Keep each body/datablock allocation before configuration can fail.
        mesh = call('allocate_body_mesh', producer.bpy.data.meshes.new, name)
        state['objects']['mesh'] = mesh
        call('populate_body_mesh', mesh.from_pydata, [tuple(point) for point in compact], [], compact_faces)
        call('update_body_mesh', mesh.update, calc_edges=True)
        body = call('allocate_body_object', producer.bpy.data.objects.new, name, mesh)
        state['objects']['body'] = body
        call('link_body', producer.bpy.context.collection.objects.link, body)
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        flags = {
            'primary_surface': True, 'body_class': 'adult_female',
            'source_foundation_id': producer.FOUNDATION_ID,
            'wrong_sex_helper_present': False, 'wrong_sex_helper_excluded': True,
            'source_anatomy_geometry_copied': False, 'private_inactive_authoring_only': True,
            'runtime_activation_allowed': False, 'adult_foundation_qualified': False,
            'candidate_author_id': producer.CANDIDATE_AUTHOR_ID,
            'generic_identity_neutral_foundation': True, 'kira_styling_applied': False,
            'armature_present': False, 'pose_space_pelvic_patch_deformation_audit_passed': False,
            'mandatory_downstream_pose_gate': HELD_POSE_GATE,
            'pre_surface_rest_test_lane': True,
        }
        state['body_flag_intent'] = flags
        for key, value in flags.items():
            body[key] = value
        call('body_flags_checkpoint', lambda: None)
        lineage_rows = call('seed_canonical_lineage', producer.seed_mesh_rows,
                            body.data, old_to_new, compact, len(vertices))
        state['source_lineage_rows'] = lineage_rows
        skeleton_path = producer.MAKEHUMAN_DATA / 'rigs' / 'default.mhskel'
        skeleton_raw = call('read_selected_skeleton', skeleton_path.read_bytes)
        state['skeleton_raw'] = skeleton_raw
        if hashlib.sha256(skeleton_raw).hexdigest() != SKELETON_SHA256:
            raise ValueError('selected_skeleton_bytes_disagree')
        skeleton_payload = json.loads(skeleton_raw.decode('utf-8'))
        rest = call('capture_original_rest', producer.prepare_rest_handoff,
                    vertices=vertices, compact=compact, old_to_new=old_to_new,
                    transform=transform, skeleton_payload=skeleton_payload,
                    skeleton_raw=skeleton_raw,
                    base_binding={'path': base_path.relative_to(producer.PROJECT_ROOT).as_posix(),
                                  'sha256': BASE_SHA256, 'face_group': 'body'},
                    macro_target_bindings=target_records, vector_factory=producer.Vector,
                    resolver=producer.resolve_makehuman_skeleton_geometry)
        state['rest_capture'] = rest
        # This is the exact desired insertion: normalized weights, then rig.
        weights = call('attach_normalized_default_weights', producer._attach_normalized_default_weights, body, old_to_new)
        state['weights'] = weights
        call('require_canonical_rows', producer.require_mesh_rows, body.data, lineage_rows)
        call('require_original_rest_unchanged', producer.require_rest_handoff_unchanged, rest)
        require_sources_unchanged()
        binding = {'candidate_id': candidate_id, 'body_profile': 'adult_female',
                   'maturity_status': 'confirmed_adult', 'identity_scope': 'generic_identity_neutral',
                   'fresh_inactive_build': True, 'pre_surface_stage': True,
                   'handoff_sha256': hashlib.sha256(rest['projection_bytes']).hexdigest(),
                   'compact_rest_points_sha256': rest['projection']['compact_rest_points_sha256']}
        state['lineage_binding'] = binding
        backend = backend_type.__new__(backend_type)
        state['backend'] = backend
        call('initialize_retained_backend', backend_type.__init__, backend, producer.bpy, binding)
        observation = call('observe_fresh_pre_surface_body', backend.observe, body)
        state['initial_observation'] = observation
        enrollment = {'producer_utility_sha256': EXPECTED_SOURCE_PINS['rest_utility'],
                      'binding': {key: observation[key] for key in compiler.COMMON_BINDING_KEYS}}
        state['enrollment'] = enrollment
        attachment = call('compile_actual_rest_attachment', compiler.compile_attachment_plan,
                          rest, enrollment, observation, profile_raw)
        state['attachment_capture'] = attachment

        def attachment_checkpoint(capture, label):
            state['attachment_capture'] = capture
            note = checkpoint(state, 'attachment:' + label)
            state['returns'].append({'phase': 'attachment:' + label + ':checkpoint', 'value': note})
            return note

        attached = call('consume_actual_rest_attachment', compiler.attach_rest_plan,
                        attachment, body, backend, attachment_checkpoint)
        if (attached is not attachment
                or attachment.get('status') != 'IN_PROCESS_ATTACHMENT_OBSERVED_MOVEMENT_RELOAD_HOLD'
                or attachment.get('full_body_ready') is not False
                or attachment.get('runtime_authority') is not False):
            raise ValueError('attachment_return_does_not_match_observed_held_stage')
        call('require_canonical_rows_after_attachment', producer.require_mesh_rows, body.data, lineage_rows)
        call('require_original_rest_after_attachment', producer.require_rest_handoff_unchanged, rest)
        require_sources_unchanged()
        # Historical rest-capture flags remain untouched; later stage is separate.
        report = {
            'schema': 'kira.avatar.pre_surface_rest_lane.report.v1',
            'status': 'IN_PROCESS_PRE_SURFACE_ATTACHMENT_OBSERVED_EXIT_RELOAD_MOVEMENT_HOLD',
            'candidate_id': candidate_id, 'body_profile': 'adult_female',
            'identity_scope': 'generic_identity_neutral', 'selected_mode': MODE,
            'armature_present': True, 'attachment_status': attachment['status'],
            'armature_name': attachment['plan']['armature_name'],
            'bone_count': len(attachment['plan']['operations']),
            'original_rest_capture': {
                'schema': rest['projection'].get('schema'),
                'projection_sha256': hashlib.sha256(rest['projection_bytes']).hexdigest(),
                'compact_rest_points_sha256': rest['projection']['compact_rest_points_sha256'],
                'armature_created_at_capture': rest['projection']['armature_created'],
                'rig_attachment_performed_at_capture': rest['projection']['rig_attachment_performed'],
            },
            'skin_weights': {
                'source_sha256': WEIGHTS_SHA256,
                'weights_normalized': weights['weights_normalized'],
                'maximum_influences': weights['maximum_influences'],
            },
            'intersection_cleanup_performed': False, 'surface_authoring_performed': False,
            'scene_deletion_performed': False, 'save_performed': False,
            'render_performed': False, 'glb_export_performed': False,
            'runtime_activation_allowed': False, 'adult_foundation_qualified': False,
            'full_body_ready': False, 'saved_reload_performed': False,
            'movement_validated': False, 'anatomy_validated': False,
            'physiology_validated': False, 'normal_process_exit_observed': False,
            'mandatory_downstream_pose_gate': HELD_POSE_GATE,
            'source_pin_checks_are_caller_evidence_not_custody_or_authority': True,
        }
        state['report'] = report
        report_text = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False)
        state['report_text'] = report_text
        if len(report_text.encode('utf-8')) > 8192:
            raise ValueError('native_report_property_exceeds_fixed_8192_byte_cap')
        body['armature_present'] = True
        body['inactive_foundation_build_manifest_json'] = report_text
        for key, value in {'inactive_adult_foundation_candidate': True,
                           'runtime_activation_allowed': False, 'render_performed': False,
                           'glb_export_performed': False, 'generic_identity_neutral_foundation': True,
                           'kira_styling_applied': False, 'clothing_applied': False,
                           'armature_present': True, 'adult_foundation_qualified': False,
                           'pose_space_pelvic_patch_deformation_audit_passed': False,
                           'mandatory_downstream_pose_gate': HELD_POSE_GATE}.items():
            producer.bpy.context.scene[key] = value
        call('held_report_flags_checkpoint', lambda: None)
        state['phase'] = 'complete_in_process_exit_pending'
        state['status'] = report['status']
        return state
    except Exception as primary:
        # Underlying rest/attachment exceptions retain their own partial captures.
        state['primary'] = primary
        state['underlying_partial_capture'] = getattr(primary, 'capture', None)
        state['status'] = 'FAILED_PARTIAL_NATIVE_STATE_RETAINED_NO_CLEANUP_NO_RETRY'
        raise PreSurfaceLaneError(state, primary) from primary
