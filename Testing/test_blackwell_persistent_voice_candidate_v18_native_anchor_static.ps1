param(
    [ValidateSet('PreSeal','PostSeal')]
    [string]$Phase = 'PostSeal',
    [string]$Root = 'C:\Users\robmc\Kira'
)

$ErrorActionPreference = 'Stop'
$scratchRoot = 'C:\Users\robmc\Documents\Codex\2026-08-11\c\work\voice_v18_author\staging'
$prepRel = 'RecoverySprint\continuation_20260811\blackwell_v18_native_diagnostic_telemetry_control_anchor_static_preparation\attempt_01'
$sourceRel = 'tools\native\kira_blackwell_voice_control_anchor_v18.c'
$headerRel = 'tools\native\kira_blackwell_voice_control_anchor_v18_identity_anchor.h'
$exeRel = 'tools\native\kira_blackwell_voice_control_anchor_v18.exe'
$objRel = 'tools\native\kira_blackwell_voice_control_anchor_v18.obj'
$configRel = 'Voice\sidecars\chatterbox_blackwell_persistent_candidate_v18\candidate_config.json'
$contractRel = 'Voice\sidecars\chatterbox_blackwell_persistent_candidate_v18\native_control_contract.json'
$readmeRel = 'Voice\sidecars\chatterbox_blackwell_persistent_candidate_v18\README.md'
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
    if ($Path -like '*v18*' -and (
        $Path.StartsWith('tools/native/') -or
        $Path.StartsWith('Voice/sidecars/') -or
        $Path.StartsWith('Testing/') -or
        $Path.StartsWith('RecoverySprint/continuation_20260811/blackwell_v18_')
    )) {
        return Join-Path $Root $relative
    }
    return Join-Path 'C:\Users\robmc\Kira' $relative
}

function Test-TelemetryPredicates([string]$Text) {
    $required = @(
        'PY_FAILURE_CALL_NULL_EXCEPTION',
        'PY_FAILURE_CALL_NULL_NO_EXCEPTION',
        'PY_FAILURE_RESULT_MISMATCH',
        'PY_FAILURE_POST_VALIDATION_RECHECK',
        'E_CALL_PRE',
        'E_CALL_NULL',
        'E_CALL_RETURN',
        'E_RESULT_REFUSED',
        'E_RESULT_VALID',
        'E_POST_VALIDATION',
        'copy_sanitized_python_text',
        'capture_python_exception',
        'diagnosis->result_tuple_size = (int64_t)tuple_size;',
        'diagnosis->result_failure_code = 10U;',
        'diagnosis->result_failure_code = 24U;',
        'record.python_failure_kind = diagnosis->failure_kind;',
        'record.exception_type_length = diagnosis->exception_type_length;',
        'record.exception_message_length = diagnosis->exception_message_length;',
        'V17_STAGE50_DIAGNOSTIC_TELEMETRY_DISAMBIGUATION',
        'validate_static_control_graph_v15',
        'kira.blackwell.v15.native_validator_result.v1'
    )
    foreach ($needle in $required) {
        if ($Text.IndexOf($needle, [StringComparison]::Ordinal) -lt 0) { return $false }
    }
    return $true
}

$sourcePath = Join-Path $Root $sourceRel
$headerPath = Join-Path $Root $headerRel
$exePath = Join-Path $Root $exeRel
$objPath = Join-Path $Root $objRel
$configPath = Join-Path $Root $configRel
$contractPath = Join-Path $Root $contractRel
$readmePath = Join-Path $Root $readmeRel
$sealPath = Join-Path $Root $sealRel

foreach ($path in @($sourcePath,$headerPath,$exePath,$objPath,$configPath,$contractPath,$readmePath)) {
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "missing V18 artifact: $path"
}

$source = Get-Content -LiteralPath $sourcePath -Raw
Assert-True (Test-TelemetryPredicates $source) 'V18 telemetry predicate set is incomplete'
Assert-True ($source.Contains('#define V18_SEALED_SUBJECT_COUNT 86U')) 'wrong V18 subject count'
Assert-True ($source.Contains('actual_86_objects_exact')) 'wrong V18 audit object-count key'
Assert-True ($source.Contains('compiled_hostile_checks')) 'compiled-hostile audit binding absent'
Assert-True ($source.Contains('"62"')) 'compiled-hostile exact count absent'

$mutants = @(
    'PY_FAILURE_CALL_NULL_EXCEPTION',
    'PY_FAILURE_RESULT_MISMATCH',
    'E_CALL_PRE',
    'E_CALL_RETURN',
    'E_RESULT_REFUSED',
    'copy_sanitized_python_text',
    'capture_python_exception',
    'diagnosis->result_failure_code = 10U;',
    'diagnosis->result_failure_code = 24U;',
    'record.python_failure_kind = diagnosis->failure_kind;',
    'record.exception_type_length = diagnosis->exception_type_length;',
    'V17_STAGE50_DIAGNOSTIC_TELEMETRY_DISAMBIGUATION'
)
foreach ($needle in $mutants) {
    $mutant = $source.Replace($needle, '')
    Assert-True (-not (Test-TelemetryPredicates $mutant)) "source mutant survived: $needle"
}

$header = Get-Content -LiteralPath $headerPath -Raw
$byteMacros = [regex]::Matches($header, '#define V18_S(\d{2})_BYTES ([0-9]+)ULL')
$hashMacros = [regex]::Matches($header, '#define V18_S(\d{2})_SHA256 "([0-9a-f]{64})"')
Assert-True ($byteMacros.Count -eq 84) "V18 byte macro count $($byteMacros.Count)"
Assert-True ($hashMacros.Count -eq 84) "V18 hash macro count $($hashMacros.Count)"

$subjectMatches = [regex]::Matches(
    $source,
    '\{"([^"]+)", V18_S(\d{2})_BYTES, V18_S\2_SHA256, "sealed subject \2"\}'
)
Assert-True ($subjectMatches.Count -eq 84) "V18 static subject count $($subjectMatches.Count)"
$paths = @($subjectMatches | ForEach-Object { $_.Groups[1].Value })
Assert-True (($paths | Select-Object -Unique).Count -eq 84) 'V18 static subject paths are not unique'

for ($index = 0; $index -lt 84; $index++) {
    $token = $index.ToString('00')
    Assert-True ($subjectMatches[$index].Groups[2].Value -ceq $token) "V18 subject ordinal mismatch $token"
    $actual = Resolve-Subject $paths[$index]
    Assert-True (Test-Path -LiteralPath $actual -PathType Leaf) "missing sealed subject: $actual"
    $expectedBytes = [int64]$byteMacros[$index].Groups[2].Value
    $expectedHash = $hashMacros[$index].Groups[2].Value
    Assert-True ((Get-Item -LiteralPath $actual).Length -eq $expectedBytes) "byte drift: $actual"
    Assert-True ((Get-LowerHash $actual) -ceq $expectedHash) "hash drift: $actual"
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
Assert-True ($config.candidate_id -ceq 'kira_chatterbox_blackwell_native_diagnostic_telemetry_control_anchor_candidate_v18') 'wrong V18 config identity'
Assert-True ($config.predecessor_status -ceq 'V17_CONSUMED_FAILURE_DO_NOT_RERUN') 'V17 terminal status not retained'
Assert-True ($config.v17_run_outcome_sha256 -ceq '2651db197caa103b33b7d16fb718707a81cb3a5f2c9906246b775d7a46357dea') 'V17 outcome hash drift'
Assert-True ($config.v17_post_run_checkpoint_sha256 -ceq '758c444a4c6b989de1ea9a2413f23b2b798668c22561150889ad9c5e52b60f8f') 'V17 checkpoint hash drift'
Assert-True ($config.v17_root_attempt_35_sha256 -ceq '65d212ae07d8f7eeea4a23cc328965be13f647a5cd3fe4fd038b7cba9793dbc4') 'V17 root hash drift'
Assert-True (-not $config.live_execution_authorized -and -not $config.synthesis_authorized -and -not $config.playback_authorized -and -not $config.latency_run_authorized) 'V18 config opened a live route'

$evidencePath = Join-Path (Join-Path $Root $prepRel) 'RUN_EVIDENCE_V18.jsonl'
$outcomePath = Join-Path (Join-Path $Root $prepRel) 'STATIC_CONTROL_OUTCOME_V18.receipt.bin'
Assert-True (-not (Test-Path -LiteralPath $evidencePath)) 'V18 evidence exists; candidate may have run'
Assert-True (-not (Test-Path -LiteralPath $outcomePath)) 'V18 outcome exists; candidate may have run'

if ($Phase -eq 'PostSeal') {
    Assert-True (Test-Path -LiteralPath $sealPath -PathType Leaf) 'V18 seal absent'
    $sealRaw = Get-Content -LiteralPath $sealPath -Raw
    Assert-True ($sealRaw.IndexOfAny([char[]]" `t`r`n") -lt 0) 'V18 seal is not compact canonical bytes'
    $seal = $sealRaw | ConvertFrom-Json
    Assert-True ($seal.schema -ceq 'kira.blackwell.v18.native_diagnostic_telemetry_control_anchor.static_seal.v1') 'wrong V18 seal schema'
    Assert-True ($seal.candidate_id -ceq 'kira_chatterbox_blackwell_native_diagnostic_telemetry_control_anchor_candidate_v18') 'wrong V18 seal identity'
    Assert-True ($seal.v17_authority_consumed -and $seal.v17_do_not_rerun -and -not $seal.v17_rerun) 'V17 terminal truth drifted'
    Assert-True ($seal.sealed_subject_count -eq 86 -and $seal.subjects.Count -eq 86) 'wrong V18 seal size'
    Assert-True (($seal.subjects.path | Select-Object -Unique).Count -eq 86) 'V18 seal paths not unique'
    foreach ($row in $seal.subjects) {
        $actual = Resolve-Subject $row.path
        Assert-True (Test-Path -LiteralPath $actual -PathType Leaf) "missing seal row: $actual"
        Assert-True ((Get-Item -LiteralPath $actual).Length -eq [int64]$row.bytes) "seal byte drift: $actual"
        Assert-True ((Get-LowerHash $actual) -ceq [string]$row.sha256) "seal hash drift: $actual"
    }
}

Write-Output "V18_DIAGNOSTIC_TELEMETRY_HOSTILE_STATIC_TESTS_PASS phase=$Phase compiled_checks=62 source_mutants=12 sealed_subjects=86"
