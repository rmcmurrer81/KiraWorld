"""Optional controller source; accepts already separately qualified dependencies.

No file loader, imports of Blender/target modules, subprocess, save or cleanup.
Root dispatch must bind selected modules/functions/native APIs before use. An
options dictionary or checkpoint callback is not physical execution admission.
"""
from __future__ import annotations


def run_optional_rest_lane(options, *, integration, producer, compiler,
                           backend_type, profile_raw, source_pin_evidence,
                           checkpoint):
    if type(options) is not dict:
        raise ValueError('controller_options_must_be_exact_dict')
    if options == {'mode': 'disabled'}:
        return {'status': 'REST_TEST_LANE_NOT_SELECTED', 'target_calls': 0,
                'native_mutation_performed': False, 'runtime_authority': False}
    if set(options) != {'mode', 'config_path', 'acknowledge_inactive_authoring'}:
        raise ValueError('unexpected_or_missing_controller_option')
    if (options['mode'] != integration.MODE
            or options['acknowledge_inactive_authoring'] is not True
            or not callable(checkpoint)):
        raise ValueError('explicit_inactive_test_selection_and_checkpoint_required')
    return integration.produce_pre_surface_rest_lane(
        producer=producer, compiler=compiler, backend_type=backend_type,
        profile_raw=profile_raw, source_pin_evidence=source_pin_evidence,
        config_path=options['config_path'], checkpoint=checkpoint,
        selected_mode=options['mode'],
    )
