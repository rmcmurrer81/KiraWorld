param(
    [ValidateSet('PreSeal', 'PostSeal')]
    [string]$Phase = 'PreSeal',
    [string]$ProjectRoot = '',
    [string]$AuthorityRoot = 'C:\Users\robmc\Kira'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
$root = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
$authorityRoot = [IO.Path]::GetFullPath($AuthorityRoot).TrimEnd('\')
$sourcePath = Join-Path $root 'tools/native/kira_r25_afes_execution_plan_validation_v3r25.c'
$anchorPath = Join-Path $root 'tools/native/kira_r25_afes_execution_plan_validation_v3r25_identity_anchor.h'
$contractPath = Join-Path $root 'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r25.json'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$buildPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
$sealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$futureAuditPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_fresh_static_audit/attempt_01'
$futureEvidencePath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/RUN_EVIDENCE.jsonl'
$futureReceiptPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin'
$manifestPath = Join-Path $authorityRoot 'RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/RETAINED_NATIVE_LOCK_MANIFEST.tsv'
$stdlibZipPath = Join-Path $authorityRoot 'tools/native/runtime/python314_stdlib_v3r4.zip'
$v3r22AnchorPath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r22_identity_anchor.h'
$v3r23AnchorPath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r23_identity_anchor.h'
$v3r24AnchorPath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r24_identity_anchor.h'
$v3r24SourcePath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r24.c'
$v3r24RunOutcomePath = Join-Path $authorityRoot 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit/attempt_01/RUN_OUTCOME.json'
$bodyMaterialHairPolicyPath = Join-Path $authorityRoot 'System/Docs/AVATAR_BUILDER_BODY_MATERIAL_AND_HAIR_VARIANT_CURRENT_BOUNDARY_20260811.md'
$ownerPolicyCheckpointPath = Join-Path $authorityRoot 'RecoverySprint/continuation_20260811/root_multilane_continuation/attempt_26/CHECKPOINT.md'
$codeHeaderPath = 'C:\Python314\include\cpython\code.h'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Sha([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Bytes([string]$Path) {
    return [long](Get-Item -LiteralPath $Path).Length
}

function Sha-Bytes([byte[]]$Value) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($Value))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function Canonical-Root([object[]]$Rows) {
    $text = (($Rows | Sort-Object -Property path | ForEach-Object {
        "{0}`t{1}`t{2}`n" -f ([string]$_.path), ([long]$_.bytes), ([string]$_.sha256)
    }) -join '')
    $bytesValue = (New-Object Text.UTF8Encoding($false)).GetBytes($text)
    return [pscustomobject]@{ bytes = $bytesValue.Length; sha256 = (Sha-Bytes $bytesValue) }
}

function Canonical-Path([string]$Path) {
    $full = $Path.Replace('/', '\')
    foreach ($base in @($root, $authorityRoot)) {
        $prefix = $base + '\'
        if ($full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            return $full.Substring($prefix.Length).Replace('\', '/')
        }
    }
    return $Path.Replace('\', '/')
}

function Resolve-Subject([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) {
        if (Test-Path -LiteralPath $Path -PathType Leaf) { return $Path }
        $prefix = $authorityRoot + '\'
        if ($Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            $scratch = Join-Path $root $Path.Substring($prefix.Length)
            if (Test-Path -LiteralPath $scratch -PathType Leaf) { return $scratch }
        }
        return $Path
    }
    $current = Join-Path $root $Path
    if (Test-Path -LiteralPath $current -PathType Leaf) { return $current }
    return Join-Path $authorityRoot $Path
}

foreach ($required in @($sourcePath, $anchorPath, $contractPath, $controlPath,
    $manifestPath, $stdlibZipPath, $v3r22AnchorPath, $v3r23AnchorPath, $v3r24AnchorPath,
    $v3r24SourcePath, $v3r24RunOutcomePath, $bodyMaterialHairPolicyPath,
    $ownerPolicyCheckpointPath, $codeHeaderPath)) {
    Assert-True (Test-Path -LiteralPath $required -PathType Leaf) "required file absent: $required"
}

$sourceBytes = [IO.File]::ReadAllBytes($sourcePath)
$source = [Text.Encoding]::UTF8.GetString($sourceBytes)
$anchor = [IO.File]::ReadAllText($v3r22AnchorPath) + "`n" +
    [IO.File]::ReadAllText($v3r23AnchorPath) + "`n" +
    [IO.File]::ReadAllText($v3r24AnchorPath) + "`n" + [IO.File]::ReadAllText($anchorPath)
$contract = [IO.File]::ReadAllText($contractPath) | ConvertFrom-Json
$control = [IO.File]::ReadAllText($controlPath)

Assert-True (-not ($sourceBytes.Length -ge 3 -and $sourceBytes[0] -eq 0xEF -and $sourceBytes[1] -eq 0xBB -and $sourceBytes[2] -eq 0xBF)) 'source BOM forbidden'
Assert-True (-not $source.Contains("`r")) 'source must be LF-only'
Assert-True ($contract.schema -eq 'kira.avatar.r25.foundation_afes_execution_plan_validation.v3r25') 'contract schema drift'
Assert-True ($contract.status -eq 'STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY') 'contract status drift'
Assert-True ($contract.execution_authority -eq 'NONE' -and $contract.candidate_executed -eq $false) 'contract grants or claims execution'
Assert-True ($contract.predecessor.version -eq 'v3r24' -and $contract.predecessor.status -eq 'CONSUMED_BOUNDED_FAILURE_DO_NOT_RERUN' -and $contract.predecessor.candidate_executed -eq $true) 'V3r24 predecessor truth drift'
Assert-True ($contract.v3r24_consumed_failure.status -eq 'CONSUMED_BOUNDED_FAILURE_DO_NOT_RERUN' -and $contract.v3r24_consumed_failure.terminal_checkpoint -eq 110 -and $contract.v3r24_consumed_failure.plan_attempts -eq 0 -and $contract.v3r24_consumed_failure.operation_enters -eq 0 -and $contract.v3r24_consumed_failure.exception_type -eq 'ValueError' -and $contract.v3r24_consumed_failure.exception_message -eq 'unmarshallable object') 'V3r24 consumed failure truth drift'
Assert-True ($contract.v3r22_consumed_failure.status -eq 'CONSUMED_BOUNDED_FAILURE_DO_NOT_RERUN' -and $contract.v3r22_consumed_failure.terminal_stage -eq 40 -and $contract.v3r22_consumed_failure.exact_plan_call_count_known -eq $false) 'V3r22 consumed failure truth drift'
Assert-True ($contract.failure_cause_truth.actual_cause -eq 'UNKNOWN') 'unknown V3r22 cause was replaced by speculation'
Assert-True ($contract.failure_cause_truth.controller_compile_flags_literal -eq '0x1000000' -and $contract.failure_cause_truth.controller_compile_flag_name -eq 'CO_FUTURE_ANNOTATIONS' -and $contract.failure_cause_truth.controller_compile_flag_value -eq 16777216) 'future-annotations flag declaration drift'
Assert-True ($contract.failure_cause_truth.retained_controller_annotations -eq 'STRINGIZED_NOT_GLOBAL_NAME_EVALUATED' -and $contract.failure_cause_truth.excluded_cause_status -eq 'PROVEN_EXCLUDED_BY_EXACT_COMPILE_FLAG_AND_LOCKED_RUNTIME_SEMANTICS') 'excluded annotation cause truth drift'
Assert-True ($contract.v3r23_rejected_closure.row_count -eq 15 -and $contract.v3r23_rejected_closure.author_artifact_count -eq 10 -and $contract.v3r23_rejected_closure.rejection_artifact_count -eq 5 -and $contract.v3r23_rejected_closure.authority -eq 'REJECTED_NO_EXECUTION_AUTHORITY') 'V3r23 closure declaration drift'
Assert-True ($contract.v3r22_consumed_failure_closure.row_count -eq 20 -and $contract.v3r22_consumed_failure_closure.authority -eq 'CONSUMED_FAILURE_DO_NOT_RERUN') 'V3r22 closure declaration drift'
Assert-True ($contract.v3r24_consumed_failure_closure.row_count -eq 19 -and $contract.v3r24_consumed_failure_closure.author_artifact_count -eq 10 -and $contract.v3r24_consumed_failure_closure.audit_run_artifact_count -eq 9 -and $contract.v3r24_consumed_failure_closure.authority -eq 'CONSUMED_FAILURE_DO_NOT_RERUN') 'V3r24 closure declaration drift'
Assert-True ((@($contract.diagnostic_telemetry.checkpoint_sequence) -join ',') -ceq '100,110,115,120,130,140,141,150,151,160,161,170,171,180,181,190,191,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,229,230') 'checkpoint contract drift'
Assert-True ($contract.diagnostic_telemetry.operation_count_on_success -eq 21 -and $contract.single_plan_call.maximum_calls -eq 1) 'bounded operation/plan count drift'
Assert-True ($contract.diagnostic_telemetry.exception_capture.type_capacity_including_nul -eq 64 -and $contract.diagnostic_telemetry.exception_capture.message_capacity_including_nul -eq 192 -and $contract.diagnostic_telemetry.exception_capture.traceback -eq 'NOT_CAPTURED') 'bounded exception contract drift'
Assert-True ($contract.fresh_audit_grammar.line_count -eq 38 -and $contract.fresh_audit_grammar.field_line_count -eq 37) 'different-audit grammar drift'
Assert-True ($contract.marshal_compatibility.locked_runtime -eq 'CPYTHON_3_14_4' -and $contract.marshal_compatibility.locked_runtime_marshal_version -eq 5 -and $contract.marshal_compatibility.v3r25_fingerprint_format -eq 5 -and $contract.marshal_compatibility.v3r25_all_marshal_dumps_code_fingerprint_sites -eq 3) 'marshal runtime/format/site-count declaration drift'
Assert-True ($contract.downstream_owner_routing.owner -eq 'AVATAR_BUILDER_REUSABLE_METHOD_TEMPLATE_LAYER' -and $contract.downstream_owner_routing.rejected_result_route -eq 'DO_NOT_REPEAT_TESTS_ONLY' -and $contract.downstream_owner_routing.this_contract_integrates_a_body -eq $false) 'downstream owner routing drift'
$appearanceGates = $contract.downstream_owner_routing.appearance_material_activation_gates
Assert-True ($appearanceGates.enforcement_layer -eq 'DOWNSTREAM_AVATAR_BUILDER_ONLY_NOT_THIS_CONTROLLER_DIAGNOSTIC' -and $appearanceGates.final_body_material_requirement -eq 'ANATOMICALLY_REALISTIC_REGIONAL_PIGMENTATION_NOT_ONE_FLAT_COLOR' -and $appearanceGates.current_evidence_status -eq 'NOT_PROVEN_BY_V3R25_STATIC_DIAGNOSTIC') 'regional-pigmentation downstream gate drift'
Assert-True ((@($appearanceGates.required_normal_regional_variation) -join ',') -ceq 'lips,areolae,nipples,other_normal_individual_regional_variation' -and (@($appearanceGates.evidence_required_before_positive_claim) -join ',') -ceq 'Blender_material_evidence,saved_blend_evidence,render_evidence') 'regional material/evidence detail drift'
Assert-True ($appearanceGates.kira_activation_variants.lower_memory_variant -like 'BALD_*' -and $appearanceGates.kira_activation_variants.hair_equipped_variant -like '*INACTIVE_UNTIL_RAM_UPGRADE' -and $appearanceGates.synthetic_robert_activation_variants.lower_memory_variant -like 'BALD_*' -and $appearanceGates.synthetic_robert_activation_variants.hair_equipped_variant -like '*INACTIVE_UNTIL_RAM_UPGRADE') 'Kira/Synthetic Robert performance-variant gate drift'
Assert-True ($appearanceGates.other_people_hair_equipped_bodies -like '*INACTIVE_UNTIL_RAM_UPGRADE' -and $appearanceGates.body_test_policy_before_ram_upgrade -eq 'MINIMIZE_BODY_TESTS' -and $appearanceGates.sarah -eq 'PRESERVE_CURRENT_FILES_DO_NOT_INSPECT_EDIT_OR_RESUME') 'RAM/Sarah downstream boundary drift'
$policyBindings = @($appearanceGates.authoritative_policy_bindings)
Assert-True ($policyBindings.Count -eq 2) 'downstream authoritative policy binding count drift'
Assert-True ($policyBindings[0].path -eq 'System/Docs/AVATAR_BUILDER_BODY_MATERIAL_AND_HAIR_VARIANT_CURRENT_BOUNDARY_20260811.md' -and [long]$policyBindings[0].bytes -eq 3797 -and $policyBindings[0].sha256 -ceq 'f24d797fd389af3dc8611b93dd31abbd3b52fc3abead2efd792effb5114668a3') 'body material/hair policy identity declaration drift'
Assert-True ($policyBindings[1].path -eq 'RecoverySprint/continuation_20260811/root_multilane_continuation/attempt_26/CHECKPOINT.md' -and [long]$policyBindings[1].bytes -eq 3122 -and $policyBindings[1].sha256 -ceq 'c6588a4ba161910587e54b80423c0afba370798b8f70665862083643bb9c1fc5') 'owner policy checkpoint identity declaration drift'
Assert-True ((Bytes $bodyMaterialHairPolicyPath) -eq 3797 -and (Sha $bodyMaterialHairPolicyPath) -ceq 'f24d797fd389af3dc8611b93dd31abbd3b52fc3abead2efd792effb5114668a3') 'authoritative body material/hair policy bytes drift'
Assert-True ((Bytes $ownerPolicyCheckpointPath) -eq 3122 -and (Sha $ownerPolicyCheckpointPath) -ceq 'c6588a4ba161910587e54b80423c0afba370798b8f70665862083643bb9c1fc5') 'owner policy provenance checkpoint bytes drift'
Assert-True ((@($contract.stop_before) -join ',') -ceq 'bootstrap,broker,process,AFES,Blender,body,save,render,export') 'stop-before boundary drift'
Assert-True ($control.Contains('actual V3r22 stage-40 cause remains unknown')) 'control omits unknown-cause boundary'
Assert-True ($control.Contains('0x1000000 == CO_FUTURE_ANNOTATIONS')) 'control omits compile-flag proof'
Assert-True ($control.Contains('marshal.version == 5') -and $control.Contains('18,870-character embedded validator') -and $control.Contains('all 20 encode and zero fail')) 'control omits exact marshal failure/repair proof'
Assert-True ($control.Contains('Avatar Builder reusable method/template layer') -and $control.Contains('A rejected result may contribute only a `DO_NOT_REPEAT` test.')) 'control omits downstream owner routing'
Assert-True ($control.Contains('anatomically realistic regional pigmentation rather than one flat color') -and $control.Contains('bald lower-memory variant') -and $control.Contains('hair-equipped variant') -and $control.Contains("Sarah's current files are preserved")) 'control omits appearance/activation/Sarah gates'
Assert-True ($control.Contains('Execution authority: **NONE**')) 'control grants execution authority'
Assert-True (-not (Test-Path -LiteralPath $futureAuditPath)) 'future different-audit root must be absent'
Assert-True (-not (Test-Path -LiteralPath $futureEvidencePath) -and -not (Test-Path -LiteralPath $futureReceiptPath)) 'future evidence/receipt must be absent'

# Freeze every macro used by the current source and independently rehash all 136 fixed subjects.
$macroValues = @{}
foreach ($match in [regex]::Matches($anchor, '#define\s+(V3R(?:22|23|24|25)_[A-Z0-9_]+)\s+(?:"([0-9a-f]{64})"|([0-9]+)ULL)')) {
    if ($match.Groups[2].Success) { $macroValues[$match.Groups[1].Value] = $match.Groups[2].Value }
    else { $macroValues[$match.Groups[1].Value] = [long]$match.Groups[3].Value }
}
Assert-True ($macroValues.Count -ge 300) 'identity anchor macro closure unexpectedly small'
foreach ($binding in @(
    @($contractPath, 'V3R22_CONTRACT_BYTES', 'V3R22_CONTRACT_SHA256'),
    @($contractPath, 'V3R22_TARGET_CONTRACT_BYTES', 'V3R22_TARGET_CONTRACT_SHA256'),
    @($sourcePath, 'V3R22_SOURCE_BYTES', 'V3R22_SOURCE_SHA256'),
    @($PSCommandPath, 'V3R22_TEST_BYTES', 'V3R22_TEST_SHA256'),
    @($controlPath, 'V3R22_CONTROL_BYTES', 'V3R22_CONTROL_SHA256')
)) {
    Assert-True ((Bytes $binding[0]) -eq [long]$macroValues[$binding[1]]) "anchor byte drift: $($binding[1])"
    Assert-True ((Sha $binding[0]) -ceq [string]$macroValues[$binding[2]]) "anchor digest drift: $($binding[2])"
}

$pathValues = @{}
foreach ($match in [regex]::Matches($source, 'static const wchar_t\s+([A-Z0-9_]+_PATH)\[\]\s*=\s*L"((?:\\.|[^"])*)";')) {
    $pathValues[$match.Groups[1].Value] = $match.Groups[2].Value.Replace('\\', '\')
}
$fixedStart = $source.IndexOf('static const Binding fixed[]')
$fixedEnd = $source.IndexOf('    };', $fixedStart)
Assert-True ($fixedStart -ge 0 -and $fixedEnd -gt $fixedStart) 'fixed binding array absent'
$fixedBlock = $source.Substring($fixedStart, $fixedEnd - $fixedStart)
$fixedMatches = [regex]::Matches($fixedBlock, '\{([A-Z0-9_]+_PATH),\s*(V3R(?:22|25)_[A-Z0-9_]+_BYTES),\s*(V3R(?:22|25)_[A-Z0-9_]+_SHA256),\s*"([^"]+)"')
Assert-True ($fixedMatches.Count -eq 155) 'runtime fixed closure must be exactly 155 rows'
$fixedRows = @()
foreach ($match in $fixedMatches) {
    $fullPath = Resolve-Subject ([string]$pathValues[$match.Groups[1].Value])
    $expectedBytes = [long]$macroValues[$match.Groups[2].Value]
    $expectedSha = [string]$macroValues[$match.Groups[3].Value]
    Assert-True (Test-Path -LiteralPath $fullPath -PathType Leaf) "fixed subject absent: $fullPath"
    Assert-True ((Bytes $fullPath) -eq $expectedBytes -and (Sha $fullPath) -ceq $expectedSha) "fixed subject drift: $fullPath"
    $fixedRows += [pscustomobject]@{ path = (Canonical-Path $fullPath); bytes = $expectedBytes; sha256 = $expectedSha; label = $match.Groups[4].Value }
}
Assert-True (($fixedRows.path | Sort-Object -Unique).Count -eq 155) 'runtime fixed paths are not unique'
Assert-True (@($fixedRows | Where-Object label -like 'v3r24_consumed_*').Count -eq 19) 'all 19 consumed V3r24 artifacts must be fixed'
Assert-True (@($fixedRows | Where-Object label -like 'v3r23_*').Count -eq 15) 'all 15 rejected V3r23 artifacts must be fixed'
Assert-True (@($fixedRows | Where-Object label -like 'v3r22_consumed_*').Count -eq 20) 'all 20 consumed V3r22 artifacts must be fixed'
Assert-True (@($fixedRows | Where-Object label -eq 'cpython_code_header_future_annotations_definition').Count -eq 1) 'CPython header binding absent'

# Rehash predecessor closures from the contract, including their canonical roots.
foreach ($closureCase in @(
    @($contract.v3r22_consumed_failure_closure, 20, 3779, '7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0', 'V3r22'),
    @($contract.v3r23_rejected_closure, 15, 2728, '0b09c1f71154b4d56559f043f08076940bcc60e7919d6bcd8e9c3cde3b2a4ea0', 'V3r23'),
    @($contract.v3r24_consumed_failure_closure, 19, 3565, '51058e1d9c21b615c7826b4db2b8740aea6dc774107abd666c476461e5724806', 'V3r24')
)) {
    $rows = @()
    foreach ($row in @($closureCase[0].rows)) {
        $subject = Resolve-Subject ([string]$row[0])
        Assert-True (Test-Path -LiteralPath $subject -PathType Leaf) "$($closureCase[4]) closure subject absent: $($row[0])"
        Assert-True ((Bytes $subject) -eq [long]$row[1] -and (Sha $subject) -ceq [string]$row[2]) "$($closureCase[4]) closure drift: $($row[0])"
        $rows += [pscustomobject]@{ path = [string]$row[0]; bytes = [long]$row[1]; sha256 = [string]$row[2] }
    }
    $canonical = Canonical-Root $rows
    Assert-True ($rows.Count -eq [int]$closureCase[1] -and $canonical.bytes -eq [int]$closureCase[2] -and $canonical.sha256 -ceq [string]$closureCase[3]) "$($closureCase[4]) canonical root drift"
}

# Rehash the exact 137-row CRLF retained manifest without invoking Python.
$manifestBytes = [IO.File]::ReadAllBytes($manifestPath)
Assert-True ($manifestBytes.Length -eq 24975 -and (Sha $manifestPath) -eq '6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96') 'retained manifest identity drift'
Assert-True (-not ($manifestBytes -contains 0)) 'manifest embedded NUL forbidden'
$manifestText = [Text.Encoding]::UTF8.GetString($manifestBytes)
$manifestLines = $manifestText.Split([string[]]@("`r`n"), [StringSplitOptions]::None)
Assert-True ($manifestLines.Count -eq 140 -and $manifestLines[139] -eq '') 'manifest must be exactly 139 CRLF-terminated lines'
Assert-True (($manifestText.Replace("`r`n", '') -notmatch "[`r`n]")) 'manifest has bare CR/LF'
$manifestRows = @()
$lastLabel = $null
foreach ($line in @($manifestLines[2..138])) {
    $columns = $line.Split("`t"); $rowBytes = 0L
    Assert-True ($columns.Count -eq 4 -and $columns[0] -cmatch '^[a-z0-9_]{1,96}$' -and $columns[3] -cmatch '^[0-9a-f]{64}$') 'manifest row grammar drift'
    if ($null -ne $lastLabel) { Assert-True ([string]::CompareOrdinal($lastLabel, $columns[0]) -lt 0) 'manifest labels not strict sorted/unique' }
    $lastLabel = $columns[0]
    Assert-True ([long]::TryParse($columns[2], [Globalization.NumberStyles]::None, [Globalization.CultureInfo]::InvariantCulture, [ref]$rowBytes)) 'manifest byte grammar drift'
    Assert-True (-not $columns[1].Contains('\') -and $columns[1] -notmatch '(^|/)\.\.?(/|$)') 'manifest path grammar drift'
    $subject = Resolve-Subject $columns[1]
    Assert-True ((Bytes $subject) -eq $rowBytes -and (Sha $subject) -ceq $columns[3]) "manifest subject drift: $($columns[1])"
    $manifestRows += [pscustomobject]@{ path = $columns[1]; bytes = $rowBytes; sha256 = $columns[3] }
}
Assert-True ($manifestRows.Count -eq 137 -and ($manifestRows.path | Sort-Object -Unique).Count -eq 137) 'manifest must contain 137 unique rows'

# Bind the exact compile flag to the exact header and retained stdlib semantics.
Assert-True ((Bytes $codeHeaderPath) -eq 14708 -and (Sha $codeHeaderPath) -ceq '65fe295bd90aab0a5380c4b3c400713917af7f904fbb0ac86e76ffff2de1ab18') 'CPython code.h identity drift'
$codeHeader = [IO.File]::ReadAllText($codeHeaderPath)
Assert-True ($codeHeader -cmatch '(?m)^#define\s+CO_FUTURE_ANNOTATIONS\s+0x1000000(?:\s|/|$)') 'CO_FUTURE_ANNOTATIONS header definition drift'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($stdlibZipPath)
try {
    $entry = @($zip.Entries | Where-Object FullName -ceq '__future__.py')
    Assert-True ($entry.Count -eq 1) 'retained stdlib __future__.py absent or ambiguous'
    $reader = [IO.StreamReader]::new($entry[0].Open(), [Text.Encoding]::UTF8, $true)
    try { $futureText = $reader.ReadToEnd() } finally { $reader.Dispose() }
} finally { $zip.Dispose() }
Assert-True ($futureText -cmatch '(?m)^CO_FUTURE_ANNOTATIONS = 0x1000000\s+# annotations become strings at runtime\s*$') 'retained stdlib stringization semantics drift'
Assert-True ($futureText -cmatch '(?s)annotations = _Feature\(\(3, 7, 0, "beta", 1\),\s+None,\s+CO_FUTURE_ANNOTATIONS\)') 'retained stdlib annotations feature binding drift'

# Reproduce the exact V3r24 format-4 negative and format-5 success matrix without
# invoking Python, the controller, or either candidate executable.
function Extract-PlanValidator([string]$NativeSource) {
    $start = $NativeSource.IndexOf('static const char PLAN_VALIDATOR[] =')
    $end = $NativeSource.IndexOf('static int prove_python_module_absent', $start)
    Assert-True ($start -ge 0 -and $end -gt $start) 'PLAN_VALIDATOR C-string boundary absent'
    $block = $NativeSource.Substring($start, $end - $start)
    $decoded = ''
    foreach ($match in [regex]::Matches($block, '(?m)^\s*"((?:\\.|[^"\\])*)"')) {
        $decoded += [regex]::Unescape($match.Groups[1].Value)
    }
    return $decoded
}

function Validator-FunctionBlock([string]$Validator, [string]$Name) {
    $start = $Validator.IndexOf("def $Name(")
    Assert-True ($start -ge 0) "validator function absent: $Name"
    $next = $Validator.IndexOf("`ndef ", $start + 1)
    if ($next -lt 0) { $next = $Validator.Length }
    return $Validator.Substring($start, $next - $start)
}

$v3r24Source = [IO.File]::ReadAllText($v3r24SourcePath)
$v3r24Validator = Extract-PlanValidator $v3r24Source
$currentValidator = Extract-PlanValidator $source
$v3r24Outcome = [IO.File]::ReadAllText($v3r24RunOutcomePath) | ConvertFrom-Json
Assert-True ($v3r24Validator.Length -eq 18870) 'exact V3r24 embedded validator length drift'
Assert-True ($v3r24Outcome.invocation.exit_code -eq 1 -and $v3r24Outcome.invocation.checkpoint -eq 110 -and $v3r24Outcome.invocation.plan_attempts -eq 0 -and $v3r24Outcome.invocation.operation_enters -eq 0) 'V3r24 durable failure telemetry drift'
Assert-True ($v3r24Outcome.invocation.exception_type -eq 'ValueError' -and $v3r24Outcome.invocation.exception_message -eq 'unmarshallable object') 'V3r24 durable exception drift'
Assert-True ($v3r24Outcome.exact_static_reproduction.python_version -eq '3.14.4' -and $v3r24Outcome.exact_static_reproduction.marshal_version -eq 5 -and $v3r24Outcome.exact_static_reproduction.validator_code_objects_checked -eq 20 -and $v3r24Outcome.exact_static_reproduction.marshal_version_4_failures -eq 4 -and $v3r24Outcome.exact_static_reproduction.marshal_version_5_failures -eq 0) 'V3r24 exact marshal reproduction drift'
Assert-True ((@($v3r24Outcome.exact_static_reproduction.version_4_failed_qualnames) -join ',') -ceq '<module>,_v3_strict,_v3_validate_controller,_v3_glue_object') 'V3r24 format-4 failed code-object set drift'

$matrix = @($contract.marshal_compatibility.code_object_matrix)
Assert-True ($matrix.Count -eq 20 -and ($matrix.code_object | Sort-Object -Unique).Count -eq 20) 'marshal matrix must bind 20 distinct static labels'
Assert-True (@($matrix | Where-Object marshal_format_4 -like 'FAIL_*').Count -eq 4) 'marshal format-4 matrix must contain exactly four failures'
Assert-True (@($matrix | Where-Object marshal_format_4 -eq 'PASS').Count -eq 16) 'marshal format-4 matrix must contain exactly sixteen successes'
Assert-True (@($matrix | Where-Object marshal_format_5 -eq 'PASS').Count -eq 20 -and @($matrix | Where-Object marshal_format_5 -ne 'PASS').Count -eq 0) 'marshal format-5 matrix must pass all 20 code objects'
Assert-True ((@($matrix | Where-Object marshal_format_4 -like 'FAIL_*' | ForEach-Object code_object) -join ',') -ceq '<module>,_v3_strict,_v3_validate_controller,_v3_glue_object') 'marshal matrix failed code-object ordering/set drift'
Assert-True (($matrix | Measure-Object -Property direct_slice_constants -Sum).Sum -eq 5) 'marshal matrix must bind five compiled direct slice constants'

$v3r24Defs = @([regex]::Matches($v3r24Validator, '(?m)^def\s+([a-zA-Z0-9_]+)\(') | ForEach-Object { $_.Groups[1].Value })
Assert-True ($v3r24Defs.Count -eq 15 -and ($v3r24Defs | Sort-Object -Unique).Count -eq 15) 'V3r24 validator must contain exactly 15 function code objects'
Assert-True ($v3r24Validator.Contains("all(c in '0123456789abcdef' for c in value)") -and $v3r24Validator.Contains('{name:getattr(_v3_b,name) for name in _v3_builtin_names}') -and $v3r24Validator.Contains('any(type(k) is not str or type(v) is not bytes for k,v in __retained_by_path__.items())') -and $v3r24Validator.Contains("b''.join(name.encode('ascii')+b'\0'+_v3_snapshot[name][2] for name in sorted(_v3_function_names))")) 'four nested comprehension/generator code objects drift'
Assert-True ((1 + $v3r24Defs.Count + 4) -eq 20) 'static V3r24 code-object inventory arithmetic drift'
$strictBlock = Validator-FunctionBlock $v3r24Validator '_v3_strict'
$validateBlock = Validator-FunctionBlock $v3r24Validator '_v3_validate_controller'
$glueBlock = Validator-FunctionBlock $v3r24Validator '_v3_glue_object'
Assert-True ($strictBlock.Contains("raw[:3]") -and $strictBlock.Contains("raw[3:]") -and [regex]::Matches($strictBlock, 'raw\[(?::3|3:)\]').Count -eq 2) '_v3_strict slice-constant structure drift'
Assert-True ($validateBlock.Contains('aa[9:]') -and $validateBlock.Contains('ba[9:]')) '_v3_validate_controller shared slice-constant structure drift'
Assert-True ($glueBlock.Contains("raw[:3]") -and $glueBlock.Contains("raw[3:]") -and [regex]::Matches($glueBlock, 'raw\[(?::3|3:)\]').Count -eq 2) '_v3_glue_object slice-constant structure drift'

Assert-True ($currentValidator.Contains("if type(_v3_m.version) is not int or _v3_m.version != _v3_required_marshal_version: raise RuntimeError('marshal_runtime_version_not_exact_5')")) 'exact marshal.version 5 runtime gate absent'
Assert-True ($currentValidator.Contains('__v3r25_checkpoint__=115')) 'marshal gate checkpoint 115 absent'
Assert-True ([regex]::Matches($currentValidator, '_v3_m\.dumps\([^\n]*,5\)').Count -eq 3) 'all three marshal code-fingerprint sites must use literal format 5'
Assert-True ([regex]::Matches($currentValidator, '_v3_m\.dumps\([^\n]*,4\)').Count -eq 0) 'marshal format 4 remains in a current code-fingerprint site'
$currentDefs = @([regex]::Matches($currentValidator, '(?m)^def\s+([a-zA-Z0-9_]+)\(') | ForEach-Object { $_.Groups[1].Value })
Assert-True ($currentDefs.Count -eq 15 -and (1 + $currentDefs.Count + 4) -eq 20) 'V3r25 validator/controller/helper code-object inventory drift'

# Author-level hostile source probes. They inspect text only and never compile/evaluate Python.
$requiredSourceLiterals = @(
    '_Static_assert(CO_FUTURE_ANNOTATIONS == 0x1000000,',
    'flags=0x1000000,dont_inherit=True,optimize=0',
    "code.co_flags & 0x1000000 != 0x1000000",
    "a.__code__.co_flags & 0x1000000 != 0x1000000",
    "annotate=getattr(fn,'__annotate__',None)",
    'future_annotations_stringizer_missing:',
    'static const char *keys[37]',
    'v3r23_rejected_closure_root_sha256',
    'v3r24_consumed_failure_closure_root_sha256',
    'marshal_runtime_version',
    'marshal_fingerprint_format',
    'marshal_validator_code_objects',
    'controller_compile_flag_name',
    'UNRESOLVED_ANNOTATION_NAMES_PROVEN_EXCLUDED',
    '__v3r25_operation_enters__=0',
    '__v3r25_operation_returns__=0',
    '_v3_required_marshal_version=5',
    "_v3_m.dumps(fn.__code__,5)",
    "_v3_m.dumps(annotate.__code__,5)",
    '__v3r25_plan_attempts__+=1; __v3r25_checkpoint__=170',
    '__v3r25_plan_returns__+=1; __v3r25_operation_returns__+=1; __v3r25_checkpoint__=171',
    '__v3r25_plan_validation__=(137,1,222,231,4,0,__v3r25_operation_enters__,__v3r25_operation_returns__+1,_v3_code_root)',
    'telemetry->operation_enters != 21U',
    'telemetry->operation_returns != 21U',
    '_Static_assert(sizeof(ValidatorTelemetry) == 304U,',
    '_Static_assert(sizeof(CompletionRecord) == 896U,',
    '#define PY_EXCEPTION_TYPE_CAPACITY 64U',
    '#define PY_EXCEPTION_MESSAGE_CAPACITY 192U',
    'PyErr_GetRaisedException',
    'bootstrap,broker,process,AFES,Blender,body,save,render,export'
)
$expectedCheckpoints = @(100,110,115,120,130,140,141,150,151,160,161,170,171,180,181,190,191,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,229,230)
foreach ($checkpoint in $expectedCheckpoints) { $requiredSourceLiterals += "__v3r25_checkpoint__=$checkpoint" }
$forbiddenSourcePatterns = @(
    '__annotations__',
    '__annotate__\s*\(',
    '(?i)hashlib',
    '\bCreateProcess[AW]?\s*\(',
    '\bShellExecute(?:Ex)?[AW]?\s*\(',
    '\bWinExec\s*\(',
    '\b(?:_popen|popen|system)\s*\('
)
function Test-SourcePolicy([string]$Candidate) {
    $script:sourcePolicyReason = ''
    foreach ($literal in $requiredSourceLiterals) {
        if (-not $Candidate.Contains($literal)) { $script:sourcePolicyReason = "missing:$literal"; return $false }
    }
    foreach ($pattern in $forbiddenSourcePatterns) {
        if ([regex]::IsMatch($Candidate, $pattern)) { $script:sourcePolicyReason = "forbidden:$pattern"; return $false }
    }
    if ([regex]::Matches($Candidate, "_v3_left\['_build_execution_plan'\]\(").Count -ne 1) { $script:sourcePolicyReason = 'plan_call_count'; return $false }
    if ([regex]::Matches($Candidate, '__v3r25_operation_enters__\+=1').Count -ne 21) { $script:sourcePolicyReason = 'operation_enter_count'; return $false }
    if ([regex]::Matches($Candidate, '__v3r25_operation_returns__\+=1').Count -ne 21) { $script:sourcePolicyReason = 'operation_return_count'; return $false }
    if ([regex]::Matches($Candidate, '\{V3R24_CONSUMED_[A-Z0-9_]+_PATH,\s*V3R25_V3R24_').Count -ne 19) { $script:sourcePolicyReason = 'v3r24_fixed_count'; return $false }
    if ([regex]::Matches($Candidate, '\{V3R23_(?:REJECTED|REJECTION)_[A-Z0-9_]+_PATH,\s*V3R25_V3R23_').Count -ne 15) { $script:sourcePolicyReason = 'v3r23_fixed_count'; return $false }
    if ([regex]::Matches($Candidate, '_v3_m\.dumps\([^\n]*,5\)').Count -ne 3 -or [regex]::Matches($Candidate, '_v3_m\.dumps\([^\n]*,4\)').Count -ne 0) { $script:sourcePolicyReason = 'marshal_fingerprint_format'; return $false }
    return $true
}
Assert-True (Test-SourcePolicy $source) "baseline V3r25 source policy failed: $script:sourcePolicyReason"
foreach ($literal in $requiredSourceLiterals) {
    Assert-True (-not (Test-SourcePolicy ($source.Replace($literal, '__HOSTILE_REMOVAL__')))) "required source mutation survived: $literal"
}
foreach ($injection in @('__annotations__', '__annotate__(', 'hashlib', 'CreateProcessW(', 'ShellExecuteExW(', 'WinExec(', 'system(', 'popen(')) {
    Assert-True (-not (Test-SourcePolicy ($source + "`n" + $injection))) "forbidden source injection survived: $injection"
}

$auditKeysExpected = @('decision','auditor','author','native_executable_sha256',
    'identity_anchor_sha256','contract_sha256','native_source_sha256','static_test_sha256',
    'runtime_control_checkpoint_sha256','retained_manifest_sha256','retained_manifest_rows',
    'retained_manifest_line_endings','v3r22_consumed_failure_closure_root_sha256',
    'v3r23_rejected_closure_root_sha256','v3r24_consumed_failure_closure_root_sha256',
    'v3r24_author_artifact_count','v3r24_audit_run_artifact_count',
    'v3r9_v3r10_v3r11_history_closure_root_sha256','controller_compile_flag',
    'controller_compile_flag_name','excluded_failure_cause','plan_callable','marshal_runtime_version',
    'marshal_fingerprint_format','marshal_validator_code_objects','marshal_v4_failure_count',
    'marshal_v5_success_count',
    'plan_call_maximum','validator_checkpoint_terminal_success','operation_enter_maximum',
    'operation_return_maximum','exception_type_max_bytes','exception_message_max_bytes',
    'v3r22_authority','v3r23_authority','v3r24_authority','stop_before')
$auditKeysStart = $source.IndexOf('static const char *keys[37]')
$auditKeysEnd = $source.IndexOf('};', $auditKeysStart)
Assert-True ($auditKeysStart -ge 0 -and $auditKeysEnd -gt $auditKeysStart) 'audit key array boundary absent'
$auditKeys = @([regex]::Matches($source.Substring($auditKeysStart, $auditKeysEnd - $auditKeysStart), '"([a-z0-9_]+)"') | ForEach-Object { $_.Groups[1].Value })
Assert-True (($auditKeys -join "`n") -ceq ($auditKeysExpected -join "`n")) 'exact different-audit field order drift'

if ($Phase -eq 'PreSeal') {
    Assert-True (-not (Test-Path -LiteralPath $sealPath)) 'V3r24 seal must be absent during PreSeal'
}

if ($Phase -eq 'PostSeal') {
    Assert-True (Test-Path -LiteralPath $sealPath -PathType Leaf) 'V3r24 seal absent in PostSeal'
    Assert-True (Test-Path -LiteralPath $buildPath -PathType Leaf) 'V3r24 build results absent in PostSeal'
    $seal = [IO.File]::ReadAllText($sealPath) | ConvertFrom-Json
    Assert-True ($seal.schema -eq 'kira.r25.afes.v3r25.static_seal.v1' -and $seal.status -eq 'SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT') 'seal identity/status drift'
    Assert-True ($seal.execution_authority -eq 'NONE' -and $seal.candidate_executed -eq $false) 'seal grants or claims execution'
    Assert-True ($seal.sealed_subject_count -eq 292 -and $seal.unique_paths -eq $true) 'seal subject declaration drift'
    Assert-True ($seal.semantic_counts.current_artifacts -eq 8 -and $seal.semantic_counts.runtime_fixed_bindings -eq 155 -and $seal.semantic_counts.retained_manifest_rows -eq 137 -and $seal.semantic_counts.unique_union -eq 292) 'seal semantic counts drift'
    $expected = @{}
    function Add-Expected([string]$Path, [long]$ExpectedBytes, [string]$ExpectedSha, [string]$Role) {
        if ($expected.ContainsKey($Path)) {
            Assert-True ($expected[$Path].bytes -eq $ExpectedBytes -and $expected[$Path].sha256 -ceq $ExpectedSha) "overlap disagrees: $Path"
            $expected[$Path].roles += $Role
        } else { $expected[$Path] = [pscustomobject]@{ bytes = $ExpectedBytes; sha256 = $ExpectedSha; roles = @($Role) } }
    }
    foreach ($path in @(
        'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r25.json',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r25.c',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r25_identity_anchor.h',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r25.obj',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r25.exe',
        'Testing/test_kira_r25_foundation_afes_execution_plan_validation_v3r25_static.ps1',
        'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md',
        'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
    )) {
        $actual = Resolve-Subject $path
        Add-Expected $path (Bytes $actual) (Sha $actual) 'current_artifact'
    }
    foreach ($row in $fixedRows) { Add-Expected $row.path $row.bytes $row.sha256 'runtime_fixed_binding' }
    foreach ($row in $manifestRows) { Add-Expected $row.path $row.bytes $row.sha256 'retained_manifest_row' }
    Assert-True ($expected.Count -eq 292) 'derived unique seal union is not 292'
    $sealedRows = @($seal.sealed_subjects)
    Assert-True ($sealedRows.Count -eq 292 -and ($sealedRows.path | Sort-Object -Unique).Count -eq 292) 'seal rows are not 292 unique paths'
    Assert-True (@(Compare-Object ($expected.Keys | Sort-Object) ($sealedRows.path | Sort-Object) -CaseSensitive).Count -eq 0) 'seal exact path set drift'
    foreach ($row in $sealedRows) {
        $path = [string]$row.path; $actual = Resolve-Subject $path
        Assert-True ($expected.ContainsKey($path)) "unexpected sealed path: $path"
        Assert-True ([long]$row.bytes -eq [long]$expected[$path].bytes -and [string]$row.sha256 -ceq [string]$expected[$path].sha256) "seal metadata drift: $path"
        Assert-True ((Bytes $actual) -eq [long]$row.bytes -and (Sha $actual) -ceq [string]$row.sha256) "sealed subject changed: $path"
    }
}

'V3R25_HOSTILE_STATIC_TESTS_PASS'
