param(
    [ValidateSet('PreSeal','PostSeal')]
    [string]$Phase = 'PostSeal',
    [string]$Root = 'C:\Users\robmc\Documents\Codex\2026-08-11\c\work\voice_v19_author\staging'
)

$ErrorActionPreference = 'Stop'
$kiraRoot = 'C:\Users\robmc\Kira'
$prepRel = 'RecoverySprint\continuation_20260811\blackwell_v19_native_exact_type_and_camera_schema_static_preparation\attempt_01'
$sourceRel = 'tools\native\kira_blackwell_voice_control_anchor_v19.c'
$headerRel = 'tools\native\kira_blackwell_voice_control_anchor_v19_identity_anchor.h'
$exeRel = 'tools\native\kira_blackwell_voice_control_anchor_v19.exe'
$objRel = 'tools\native\kira_blackwell_voice_control_anchor_v19.obj'
$configRel = 'Voice\sidecars\chatterbox_blackwell_persistent_candidate_v19\candidate_config.json'
$contractRel = 'Voice\sidecars\chatterbox_blackwell_persistent_candidate_v19\native_control_contract.json'
$readmeRel = 'Voice\sidecars\chatterbox_blackwell_persistent_candidate_v19\README.md'
$hostileRel = 'Testing\native\kira_blackwell_voice_control_anchor_v19_type_timing_hostile.exe'
$sealRel = Join-Path $prepRel 'STATIC_SEAL_MANIFEST.json'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-LowerHash([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Resolve-Subject([string]$Path) {
    if ($Path -ceq 'C:/Python314/python314.dll') { return 'C:\Python314\python314.dll' }
    $relative = $Path.Replace('/', '\')
    if ($Path -ceq 'tools/native/kira_blackwell_voice_control_anchor_v19.c' -or
        $Path -ceq 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v19/candidate_config.json' -or
        $Path -ceq 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v19/native_control_contract.json' -or
        $Path -ceq 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v19/README.md' -or
        $Path -ceq 'tools/native/kira_blackwell_voice_control_anchor_v19_identity_anchor.h' -or
        $Path -ceq 'tools/native/kira_blackwell_voice_control_anchor_v19.exe') {
        return Join-Path $Root $relative
    }
    return Join-Path $kiraRoot $relative
}

function Assert-ExactList($Actual, [string[]]$Expected, [string]$Label) {
    Assert-True ($Actual.Count -eq $Expected.Count) "$Label count $($Actual.Count), expected $($Expected.Count)"
    for ($index = 0; $index -lt $Expected.Count; $index++) {
        Assert-True ([string]$Actual[$index] -ceq $Expected[$index]) "$Label mismatch at $index"
    }
}

function Test-ExactRepairPredicates([string]$Text) {
    $required = @(
        '#define V19_SEALED_SUBJECT_COUNT 110U',
        'actual_110_objects_exact',
        'V18_EXACT_RESULT_TYPES_AND_COMPLETE_CAMERA_TIMING_SCHEMA_REPAIR',
        'RESOLVE_API(api, object_type, "PyObject_Type");',
        'RESOLVE_API(api, tuple_type, "PyTuple_Type");',
        'RESOLVE_API(api, unicode_type, "PyUnicode_Type");',
        'RESOLVE_API(api, bool_type, "PyBool_Type");',
        'RESOLVE_API(api, long_type, "PyLong_Type");',
        'RESOLVE_API(api, true_singleton, "_Py_TrueStruct");',
        'RESOLVE_API(api, false_singleton, "_Py_FalseStruct");',
        'static int python_type_exact(',
        'if (!python_type_exact(api, result, api->tuple_type))',
        'if (!python_type_exact(api, item, api->unicode_type))',
        'if (!python_type_exact(api, item, api->bool_type))',
        'if (!python_type_exact(api, item, api->long_type))',
        'if (item != api->true_singleton)',
        'if (item != api->false_singleton)',
        'diagnosis->result_failure_code = 10U;',
        'diagnosis->result_failure_code = 21U;',
        'diagnosis->result_failure_code = 34U;',
        'diagnosis->result_failure_code = (uint32_t)(14 + index * 2);',
        'diagnosis->result_failure_code = (uint32_t)(15 + index * 2);',
        '*stage = (uint32_t)(64 + index * 2);',
        '*stage = (uint32_t)(65 + index * 2);',
        '*stage = 85U;',
        'exact_python_types_and_boolean_identities',
        'complete_camera_timing_schema_exact',
        'camera_schema_non_executable_exact',
        'compiled_hostile_checks',
        'validate_static_control_graph_v15',
        'kira.blackwell.v15.native_validator_result.v1'
    )
    foreach ($needle in $required) {
        if ($Text.IndexOf($needle, [StringComparison]::Ordinal) -lt 0) { return $false }
    }
    return $Text.IndexOf('PyObject_IsTrue', [StringComparison]::Ordinal) -lt 0 -and
        $Text.IndexOf('api->truth', [StringComparison]::Ordinal) -lt 0
}

$sourcePath = Join-Path $Root $sourceRel
$headerPath = Join-Path $Root $headerRel
$exePath = Join-Path $Root $exeRel
$objPath = Join-Path $Root $objRel
$configPath = Join-Path $Root $configRel
$contractPath = Join-Path $Root $contractRel
$readmePath = Join-Path $Root $readmeRel
$hostilePath = Join-Path $Root $hostileRel
$sealPath = Join-Path $Root $sealRel

foreach ($path in @($sourcePath,$headerPath,$exePath,$objPath,$configPath,$contractPath,$readmePath,$hostilePath)) {
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "missing V19 artifact: $path"
}

$source = Get-Content -LiteralPath $sourcePath -Raw
Assert-True (Test-ExactRepairPredicates $source) 'V19 exact-type predicate set is incomplete'
Assert-True ($source.Contains('v17_do_not_rerun_exact')) 'V17 consumed boundary absent'
Assert-True ($source.Contains('v18_rejected_closure_exact')) 'V18 rejection boundary absent'
Assert-True ($source.Contains('!run_python_validation(&closure[40], &closure[41], &closure[22], &closure[21],')) 'retained validator binding indices drifted'
Assert-True ($source.Contains('&closure[23], &closure[34], evidence')) 'retained config/predecessor binding indices drifted'

$mutants = @(
    'V18_EXACT_RESULT_TYPES_AND_COMPLETE_CAMERA_TIMING_SCHEMA_REPAIR',
    'RESOLVE_API(api, object_type, "PyObject_Type");',
    'RESOLVE_API(api, tuple_type, "PyTuple_Type");',
    'RESOLVE_API(api, unicode_type, "PyUnicode_Type");',
    'RESOLVE_API(api, bool_type, "PyBool_Type");',
    'RESOLVE_API(api, long_type, "PyLong_Type");',
    'RESOLVE_API(api, true_singleton, "_Py_TrueStruct");',
    'RESOLVE_API(api, false_singleton, "_Py_FalseStruct");',
    'static int python_type_exact(',
    'if (!python_type_exact(api, result, api->tuple_type))',
    'if (item != api->true_singleton)',
    'if (item != api->false_singleton)',
    'diagnosis->result_failure_code = 10U;',
    'diagnosis->result_failure_code = 34U;',
    'diagnosis->result_failure_code = (uint32_t)(14 + index * 2);',
    'diagnosis->result_failure_code = (uint32_t)(15 + index * 2);',
    'complete_camera_timing_schema_exact',
    'camera_schema_non_executable_exact'
)
foreach ($needle in $mutants) {
    $mutant = $source.Replace($needle, '')
    Assert-True (-not (Test-ExactRepairPredicates $mutant)) "source mutant survived: $needle"
}

$header = Get-Content -LiteralPath $headerPath -Raw
$byteMacros = [regex]::Matches($header, '#define V19_S(\d{3})_BYTES ([0-9]+)ULL')
$hashMacros = [regex]::Matches($header, '#define V19_S(\d{3})_SHA256 "([0-9a-f]{64})"')
Assert-True ($byteMacros.Count -eq 108) "V19 byte macro count $($byteMacros.Count)"
Assert-True ($hashMacros.Count -eq 108) "V19 hash macro count $($hashMacros.Count)"

$subjectMatches = [regex]::Matches(
    $source,
    '\{"([^"]+)", V19_S(\d{3})_BYTES, V19_S\2_SHA256, "sealed subject \2"\}'
)
Assert-True ($subjectMatches.Count -eq 108) "V19 static subject count $($subjectMatches.Count)"
$paths = @($subjectMatches | ForEach-Object { $_.Groups[1].Value })
Assert-True (($paths | Select-Object -Unique).Count -eq 108) 'V19 static subject paths are not unique'

for ($index = 0; $index -lt 108; $index++) {
    $token = $index.ToString('000')
    Assert-True ($subjectMatches[$index].Groups[2].Value -ceq $token) "V19 subject ordinal mismatch $token"
    Assert-True ($byteMacros[$index].Groups[1].Value -ceq $token) "V19 byte macro ordinal mismatch $token"
    Assert-True ($hashMacros[$index].Groups[1].Value -ceq $token) "V19 hash macro ordinal mismatch $token"
    $actual = Resolve-Subject $paths[$index]
    Assert-True (Test-Path -LiteralPath $actual -PathType Leaf) "missing sealed subject: $actual"
    $expectedBytes = [int64]$byteMacros[$index].Groups[2].Value
    $expectedHash = $hashMacros[$index].Groups[2].Value
    Assert-True ((Get-Item -LiteralPath $actual).Length -eq $expectedBytes) "byte drift: $actual"
    Assert-True ((Get-LowerHash $actual) -ceq $expectedHash) "hash drift: $actual"
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
Assert-True ($config.candidate_id -ceq 'kira_chatterbox_blackwell_native_exact_type_and_camera_schema_control_anchor_candidate_v19') 'wrong V19 config identity'
Assert-True ($config.v17_status -ceq 'CONSUMED_FAILURE_DO_NOT_RERUN') 'V17 terminal status not retained'
Assert-True ($config.v18_status -ceq 'REJECT_STATIC_NO_EXECUTION_AUTHORITY') 'V18 rejection not retained'
Assert-True ($config.v18_audit_decision_sha256 -ceq '2d2ac8919ab05b8b142198552bdacd6963d193102a844e5266f48c10f19919a4') 'V18 rejection hash drift'
Assert-True ($config.retained_validator_bytes -eq 21931 -and $config.retained_validator_sha256 -ceq '2bf232b07b0b7b93de8776f5210bd2d89068ad76cb4ee46555b861ad2818d16a') 'retained validator identity drift'
Assert-True ($config.sealed_subject_count -eq 110 -and $config.result_predicate_failure_codes -eq 25 -and $config.compiled_hostile_check_count -eq 100) 'V19 exact counts drifted'
Assert-True ($config.camera_timing_condition_count -eq 4 -and $config.camera_timing_timestamp_count -eq 51 -and $config.camera_timing_metadata_count -eq 42 -and $config.camera_timing_duration_count -eq 30 -and $config.camera_timing_ordering_rule_count -eq 15) 'camera schema counts drifted'
Assert-True ($config.exact_current_text_model_id -ceq 'qwen3.5:9b' -and $config.exact_current_text_model_digest -ceq '6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7') 'current Qwen identity drifted'
Assert-True (-not $config.live_execution_authorized -and -not $config.python_authorized -and -not $config.model_or_gpu_authorized -and -not $config.synthesis_authorized -and -not $config.audio_or_playback_authorized -and -not $config.latency_measurement_authorized -and -not $config.camera_or_device_authorized -and -not $config.production_routing_authorized) 'V19 config opened an execution route'

$contractRaw = Get-Content -LiteralPath $contractPath -Raw
$contract = $contractRaw | ConvertFrom-Json
$timing = $contract.future_matched_camera_text_voice_timing
Assert-True ($contract.repair.exact_result_predicates.Count -eq 25 -and $contract.repair.failure_code_count -eq 25) 'exact result contract count drifted'
Assert-True ($contract.repair.wrong_type_conversion_must_not_run -and $contract.repair.boolean_identity_must_be_exact_singleton) 'exact type/identity contract weakened'
Assert-True ($contract.retained_validator_provenance.bytes -eq 21931 -and $contract.retained_validator_provenance.sha256 -ceq '2bf232b07b0b7b93de8776f5210bd2d89068ad76cb4ee46555b861ad2818d16a') 'contract validator provenance drifted'

$expectedConditions = @('camera_off_ordinary_conversation','camera_on_preview_local_cues_only','camera_on_explicit_one_still_sensory_question','camera_on_post_still_follow_up_after_cue_consumed')
$expectedTimestamps = @((@'
trial_started
user_input_started
user_input_ended
transcript_ready
local_camera_permission_requested
local_camera_permission_resolved
camera_open_requested
camera_open_completed
preview_ready
frame_capture_started
frame_capture_completed
frame_draw_started
frame_draw_completed
jpeg_encode_started
jpeg_encode_completed
upload_or_local_handoff_started
upload_or_local_handoff_completed
local_cue_completed
vision_lock_wait_started
vision_lock_acquired
vision_model_load_started
vision_model_load_completed
vision_inference_started
vision_first_output
vision_inference_completed
vision_model_unload_started
vision_model_unload_completed_keep_alive_zero
vision_lock_released
chat_queue_wait_started
chat_queue_acquired
text_model_load_started
text_model_load_completed
text_generation_started
text_first_token
text_generation_completed
text_model_unload_started
text_model_unload_completed_keep_alive_zero
displayed_text
voice_queue_wait_started
voice_queue_acquired
voice_model_load_or_resume_started
voice_model_ready
voice_synthesis_started
first_synthesized_sample
voice_audio_ready
playback_requested
playback_started
playback_completed
camera_close_requested
camera_close_completed
trial_completed
'@).Trim() -split "`n" | ForEach-Object { $_.Trim() })
$expectedMetadata = @((@'
trial_id
matched_pair_id
matched_pair_order
condition
monotonic_clock_id
prompt_sha256
prompt_byte_count
response_sha256
response_byte_count
state_snapshot_sha256
history_message_count
history_byte_count
generation_limits_sha256
exact_text_model_id
exact_text_model_digest
exact_voice_route_id
vision_queue_depth_at_entry
chat_queue_depth_at_entry
voice_queue_depth_at_entry
qwen_residency_before
qwen_residency_after_vision
qwen_residency_before_voice
voice_residency_before
voice_residency_after
gpu_utilization_percent_samples
vram_used_bytes_samples
cpu_utilization_percent_samples
prior_voice_job_in_flight
prior_frame_in_flight
camera_permission_result
frame_requested
frame_consumed
local_cue_digest
vision_context_digest
cue_consumed
upload_or_handoff_route
camera_close_confirmed
event_sequence_sha256
dropped_event_count
duplicated_event_count
reordered_event_count
raw_frame_retained
'@).Trim() -split "`n" | ForEach-Object { $_.Trim() })
$expectedDurations = @((@'
user_end_to_transcript_ready_ms
camera_permission_ms
camera_open_ms
frame_capture_ms
frame_draw_ms
jpeg_encode_ms
upload_or_local_handoff_ms
local_cue_ms
vision_lock_queue_wait_ms
vision_model_load_ms
vision_first_output_ms
vision_inference_total_ms
vision_model_unload_ms
chat_queue_wait_ms
text_model_load_ms
text_first_token_ms
text_generation_total_ms
text_model_unload_ms
text_complete_to_display_ms
voice_queue_wait_ms
voice_model_load_or_resume_ms
voice_first_sample_ms
voice_audio_ready_ms
displayed_text_to_audio_ready_ms
playback_onset_ms
playback_duration_ms
camera_close_ms
user_end_to_first_text_ms
user_end_to_audio_ready_ms
user_end_to_playback_onset_ms
'@).Trim() -split "`n" | ForEach-Object { $_.Trim() })
$expectedOrdering = @((@'
all_present_timestamps_share_one_monotonic_clock
events_are_unique_and_strictly_non_decreasing
queue_wait_precedes_queue_acquire
model_load_precedes_inference_or_generation
text_model_unload_completes_before_voice_model_ready
first_synthesized_sample_precedes_audio_ready
audio_ready_precedes_playback_started
playback_started_precedes_playback_completed
camera_close_completes_on_success_failure_or_timeout
camera_off_records_no_frame_requested_or_consumed
preview_only_records_no_vision_model_call
explicit_still_uses_one_frame_and_one_consumed_cue
post_still_follow_up_records_prior_cue_consumed
matched_pairs_bind_equal_prompt_family_state_history_limits_and_voice_route
no_event_drop_duplicate_reorder_or_silent_merge
'@).Trim() -split "`n" | ForEach-Object { $_.Trim() })
Assert-ExactList $timing.conditions $expectedConditions 'camera timing conditions'
Assert-ExactList $timing.required_monotonic_timestamps $expectedTimestamps 'camera timing timestamps'
Assert-ExactList $timing.required_metadata $expectedMetadata 'camera timing metadata'
Assert-ExactList $timing.required_derived_durations $expectedDurations 'camera timing durations'
Assert-ExactList $timing.ordering_requirements $expectedOrdering 'camera timing ordering'
Assert-True ($timing.schema_only_non_executable -and -not $timing.live_measurements_present -and $timing.no_live_camera_or_latency_claim) 'camera schema made a live claim'
Assert-True ($timing.exact_current_text_model_id -ceq 'qwen3.5:9b' -and $timing.exact_current_text_model_digest -ceq '6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7' -and $timing.qwen_keep_alive_before_voice -eq 0) 'camera schema Qwen/residency identity drifted'
Assert-True ($timing.camera_off_requires_frame_requested_false -and $timing.camera_off_requires_frame_consumed_false -and -not $timing.raw_frames_retained -and -not $timing.person_or_private_state_in_schema) 'camera OFF/privacy schema drifted'
Assert-True ($contract.execution_boundary.v19_execution_authority -ceq 'NONE' -and -not $contract.execution_boundary.v17_rerun_authorized -and -not $contract.execution_boundary.v18_run_authorized -and -not $contract.execution_boundary.python_authorized -and -not $contract.execution_boundary.camera_or_device_authorized) 'contract opened an execution route'
Assert-True ($contractRaw.IndexOf('llama', [StringComparison]::OrdinalIgnoreCase) -lt 0) 'stale Llama route claimed by V19 contract'

$hostileOutput = @(& $hostilePath 2>&1)
$hostileExit = $LASTEXITCODE
$hostileText = $hostileOutput -join "`n"
Assert-True ($hostileExit -eq 0) "compiled hostile suite failed: $hostileText"
Assert-True ($hostileText.Contains('SUMMARY checks=100 failures=0 candidate_entrypoint_invoked=0 python_invoked=0')) 'hostile exact count/invocation boundary drifted'
Assert-True ($hostileText.Contains('truthy_falsey_wrong_types_refused=7 integer_wrong_types_not_converted=2')) 'hostile wrong-type coverage drifted'

$evidencePath = Join-Path (Join-Path $Root $prepRel) 'RUN_EVIDENCE_V19.jsonl'
$outcomePath = Join-Path (Join-Path $Root $prepRel) 'STATIC_CONTROL_OUTCOME_V19.receipt.bin'
Assert-True (-not (Test-Path -LiteralPath $evidencePath)) 'V19 evidence exists; candidate may have run'
Assert-True (-not (Test-Path -LiteralPath $outcomePath)) 'V19 outcome exists; candidate may have run'

if ($Phase -eq 'PostSeal') {
    Assert-True (Test-Path -LiteralPath $sealPath -PathType Leaf) 'V19 seal absent'
    $sealRaw = Get-Content -LiteralPath $sealPath -Raw
    Assert-True ($sealRaw.IndexOfAny([char[]]" `t`r`n") -lt 0) 'V19 seal is not compact canonical bytes'
    $seal = $sealRaw | ConvertFrom-Json
    Assert-True ($seal.schema -ceq 'kira.blackwell.v19.native_exact_type_and_camera_schema_control_anchor.static_seal.v1') 'wrong V19 seal schema'
    Assert-True ($seal.candidate_id -ceq 'kira_chatterbox_blackwell_native_exact_type_and_camera_schema_control_anchor_candidate_v19') 'wrong V19 seal identity'
    Assert-True ($seal.v17_authority_consumed -and $seal.v17_do_not_rerun -and -not $seal.v17_rerun) 'V17 terminal truth drifted'
    Assert-True ($seal.v18_rejected_uninvoked -and $seal.v18_do_not_run -and -not $seal.v18_run) 'V18 rejected truth drifted'
    Assert-True ($seal.execution_authority -ceq 'NONE' -and -not $seal.candidate_executed -and -not $seal.python_candidate_invoked -and $seal.model_calls -eq 0 -and $seal.gpu_voice_calls -eq 0 -and $seal.synthesis_calls -eq 0 -and $seal.playback_calls -eq 0 -and $seal.latency_measurements -eq 0) 'V19 seal opened or claimed execution'
    Assert-True ($seal.sealed_subject_count -eq 110 -and $seal.subjects.Count -eq 110) 'wrong V19 seal size'
    Assert-True (($seal.subjects.path | Select-Object -Unique).Count -eq 110) 'V19 seal paths not unique'
    $expectedSealPaths = @($paths[0], 'tools/native/kira_blackwell_voice_control_anchor_v19_identity_anchor.h', 'tools/native/kira_blackwell_voice_control_anchor_v19.exe') + @($paths[1..107])
    Assert-ExactList $seal.subjects.path $expectedSealPaths 'V19 seal subject order'
    foreach ($row in $seal.subjects) {
        $actual = Resolve-Subject $row.path
        Assert-True (Test-Path -LiteralPath $actual -PathType Leaf) "missing seal row: $actual"
        Assert-True ((Get-Item -LiteralPath $actual).Length -eq [int64]$row.bytes) "seal byte drift: $actual"
        Assert-True ((Get-LowerHash $actual) -ceq [string]$row.sha256) "seal hash drift: $actual"
    }
}

Write-Output "V19_EXACT_TYPE_CAMERA_SCHEMA_HOSTILE_STATIC_TESTS_PASS phase=$Phase compiled_checks=100 source_mutants=18 sealed_subjects=110 camera_schema=4/51/42/30/15"
