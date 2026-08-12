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
$sourcePath = Join-Path $root 'tools/native/kira_r25_afes_execution_plan_validation_v3r23.c'
$anchorPath = Join-Path $root 'tools/native/kira_r25_afes_execution_plan_validation_v3r23_identity_anchor.h'
$contractPath = Join-Path $root 'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r23.json'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$buildPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
$sealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$futureAuditPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_fresh_static_audit/attempt_01'
$manifestPath = Join-Path $authorityRoot 'RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/RETAINED_NATIVE_LOCK_MANIFEST.tsv'
$v3r20SourcePath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_python_controller_validation_v3r20.c'
$v3r22SourcePath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r22.c'
$v3r22ControllerPath = Join-Path $authorityRoot 'tools/run_kira_r25_foundation_afes_locked_pair_v3r9.py'
$v3r22AnchorPath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r22_identity_anchor.h'
$futureEvidencePath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_static_preparation/attempt_01/RUN_EVIDENCE.jsonl'
$futureReceiptPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_static_preparation/attempt_01/EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Sha([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Bytes([string]$Path) {
    return [long](Get-Item -LiteralPath $Path).Length
}

function Sha-Bytes([byte[]]$BytesValue) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($algorithm.ComputeHash($BytesValue))).Replace('-', '').ToLowerInvariant()
    } finally {
        $algorithm.Dispose()
    }
}

function Canonical-Root([object[]]$Rows) {
    $text = (($Rows | Sort-Object -Property path | ForEach-Object {
        "{0}`t{1}`t{2}`n" -f ([string]$_.path), ([long]$_.bytes), ([string]$_.sha256)
    }) -join '')
    $encoding = New-Object Text.UTF8Encoding($false)
    $bytesValue = $encoding.GetBytes($text)
    return [pscustomobject]@{ bytes = $bytesValue.Length; sha256 = (Sha-Bytes $bytesValue); text = $text }
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

function Resolve-Subject([string]$CanonicalPath) {
    if ([IO.Path]::IsPathRooted($CanonicalPath)) {
        if (Test-Path -LiteralPath $CanonicalPath -PathType Leaf) { return $CanonicalPath }
        $authorityPrefix = $authorityRoot + '\'
        if ($CanonicalPath.StartsWith($authorityPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            $scratchCandidate = Join-Path $root $CanonicalPath.Substring($authorityPrefix.Length)
            if (Test-Path -LiteralPath $scratchCandidate -PathType Leaf) { return $scratchCandidate }
        }
        return $CanonicalPath
    }
    $current = Join-Path $root $CanonicalPath
    if (Test-Path -LiteralPath $current -PathType Leaf) { return $current }
    return Join-Path $authorityRoot $CanonicalPath
}

foreach ($requiredFile in @($sourcePath, $anchorPath, $contractPath, $controlPath,
    $manifestPath, $v3r20SourcePath, $v3r22SourcePath, $v3r22ControllerPath,
    $v3r22AnchorPath)) {
    Assert-True (Test-Path -LiteralPath $requiredFile -PathType Leaf) "required file absent: $requiredFile"
}

$sourceBytes = [IO.File]::ReadAllBytes($sourcePath)
$source = [Text.Encoding]::UTF8.GetString($sourceBytes)
$anchor = [IO.File]::ReadAllText($v3r22AnchorPath) + "`n" + [IO.File]::ReadAllText($anchorPath)
$contractText = [IO.File]::ReadAllText($contractPath)
$control = [IO.File]::ReadAllText($controlPath)
$v3r20Source = [IO.File]::ReadAllText($v3r20SourcePath)
$v3r22Source = [IO.File]::ReadAllText($v3r22SourcePath)
$v3r22Controller = [IO.File]::ReadAllText($v3r22ControllerPath)
$contract = $contractText | ConvertFrom-Json

Assert-True (-not ($sourceBytes.Length -ge 3 -and $sourceBytes[0] -eq 0xEF -and $sourceBytes[1] -eq 0xBB -and $sourceBytes[2] -eq 0xBF)) 'source BOM forbidden'
Assert-True (-not $source.Contains("`r")) 'source must be LF-only'
Assert-True ($contract.schema -eq 'kira.avatar.r25.foundation_afes_execution_plan_validation.v3r23') 'contract schema drift'
Assert-True ($contract.status -eq 'STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY') 'contract status drift'
Assert-True ($contract.execution_authority -eq 'NONE' -and $contract.candidate_executed -eq $false) 'author contract grants or claims execution'
Assert-True ($contract.predecessor.version -eq 'v3r22' -and $contract.predecessor.status -eq 'CONSUMED_BOUNDED_FAILURE_DO_NOT_RERUN') 'consumed V3r22 predecessor truth drift'
Assert-True ($contract.predecessor.recorded_previous_invocations -eq 1 -and $contract.predecessor.maximum_previous_invocations -eq 1 -and $contract.predecessor.exit_code -eq 1 -and $contract.predecessor.receipt_state -eq 3 -and $contract.predecessor.terminal_stage -eq 40) 'V3r22 consumed failure facts drift'
Assert-True ($contract.v3r22_consumed_failure_closure.row_count -eq 20 -and $contract.v3r22_consumed_failure_closure.canonical_root_bytes -eq 3779 -and $contract.v3r22_consumed_failure_closure.canonical_root_sha256 -eq '7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0' -and $contract.v3r22_consumed_failure_closure.authority -eq 'CONSUMED_FAILURE_DO_NOT_RERUN') 'V3r22 closure declaration drift'
Assert-True ($contract.retained_manifest.data_row_count -eq 137 -and $contract.retained_manifest.line_count -eq 139 -and $contract.retained_manifest.line_endings -eq 'CRLF_EXACT') 'manifest contract drift'
Assert-True ($contract.read_only_failure_diagnosis.confidence -eq 'LIKELY_STATIC_CAUSE_NOT_RUNTIME_PROOF' -and $contract.read_only_failure_diagnosis.v3r23_repair -like 'NEVER_READ___ANNOTATIONS__*') 'static diagnosis truth boundary drift'
Assert-True ($contract.single_plan_call.callable -eq '_build_execution_plan' -and $contract.single_plan_call.maximum_calls -eq 1) 'single plan call declaration drift'
Assert-True ($contract.single_plan_call.controller_sha_helper_calls_on_success -eq 222 -and $contract.single_plan_call.controller_hex_helper_calls_on_success -eq 231 -and $contract.single_plan_call.controller_json_helper_calls_on_success -eq 4 -and $contract.single_plan_call.forbidden_blob_or_canonical_helper_calls -eq 0 -and $contract.single_plan_call.native_sha_total_calls_on_success_including_code_root -eq 223) 'exact helper call counts drift'
Assert-True ((@($contract.diagnostic_telemetry.checkpoint_sequence) -join ',') -ceq '100,110,120,130,140,150,160,170,180,190,200,210,220,230') 'checkpoint contract drift'
Assert-True ($contract.diagnostic_telemetry.exception_capture.type_capacity_including_nul -eq 64 -and $contract.diagnostic_telemetry.exception_capture.message_capacity_including_nul -eq 192 -and $contract.diagnostic_telemetry.exception_capture.traceback -eq 'NOT_CAPTURED') 'bounded exception contract drift'
Assert-True ((@($contract.stop_before) -join ',') -ceq 'bootstrap,broker,process,AFES,Blender,body,save,render,export') 'stop boundary drift'
Assert-True ($control.Contains('No V3r23 candidate has been invoked')) 'runtime control execution truth absent'
Assert-True ($control.Contains('V3r22 is a consumed bounded failure and is `DO_NOT_RERUN`')) 'runtime control predecessor truth absent'
Assert-True ($control.Contains('No bootstrap, broker, process, AFES, Blender, body, save, render, or export authority exists here.')) 'runtime control stop boundary absent'
Assert-True (-not (Test-Path -LiteralPath $futureAuditPath)) 'future different-audit path must be absent during authored PreSeal/PostSeal'
Assert-True (-not (Test-Path -LiteralPath $futureEvidencePath) -and -not (Test-Path -LiteralPath $futureReceiptPath)) 'V3r23 output roots must remain absent during static authoring'

# Parse the identity anchor without compiling or executing anything.
$macroValues = @{}
foreach ($match in [regex]::Matches($anchor, '#define\s+(V3R(?:22|23)_[A-Z0-9_]+)\s+(?:"([0-9a-f]{64})"|([0-9]+)ULL)')) {
    if ($match.Groups[2].Success) { $macroValues[$match.Groups[1].Value] = $match.Groups[2].Value }
    else { $macroValues[$match.Groups[1].Value] = [long]$match.Groups[3].Value }
}
Assert-True ($macroValues.Count -ge 230) 'identity anchor macro closure unexpectedly small'
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

# Parse every source fixed binding and prove all 100 exact subjects.
$pathValues = @{}
foreach ($match in [regex]::Matches($source, 'static const wchar_t\s+([A-Z0-9_]+_PATH)\[\]\s*=\s*L"((?:\\.|[^"])*)";')) {
    $pathValues[$match.Groups[1].Value] = $match.Groups[2].Value.Replace('\\', '\')
}
$fixedStart = $source.IndexOf('static const Binding fixed[]')
$fixedEnd = $source.IndexOf('    };', $fixedStart)
Assert-True ($fixedStart -ge 0 -and $fixedEnd -gt $fixedStart) 'fixed binding array absent'
$fixedBlock = $source.Substring($fixedStart, $fixedEnd - $fixedStart)
$fixedMatches = [regex]::Matches($fixedBlock, '\{([A-Z0-9_]+_PATH),\s*(V3R(?:22|23)_[A-Z0-9_]+_BYTES),\s*(V3R(?:22|23)_[A-Z0-9_]+_SHA256),\s*"([^"]+)"')
Assert-True ($fixedMatches.Count -eq 120) 'runtime fixed closure must be exactly 120 rows'
$fixedRows = @()
foreach ($match in $fixedMatches) {
    $fullPath = Resolve-Subject ([string]$pathValues[$match.Groups[1].Value])
    $expectedBytes = [long]$macroValues[$match.Groups[2].Value]
    $expectedSha = [string]$macroValues[$match.Groups[3].Value]
    Assert-True (Test-Path -LiteralPath $fullPath -PathType Leaf) "fixed subject absent: $fullPath"
    Assert-True ((Bytes $fullPath) -eq $expectedBytes) "fixed subject byte drift: $fullPath"
    Assert-True ((Sha $fullPath) -ceq $expectedSha) "fixed subject digest drift: $fullPath"
    $fixedRows += [pscustomobject]@{ path = (Canonical-Path $fullPath); bytes = $expectedBytes; sha256 = $expectedSha; label = $match.Groups[4].Value }
}
Assert-True (($fixedRows.path | Sort-Object -Unique).Count -eq 120) 'runtime fixed paths are not unique'
Assert-True (@($fixedRows | Where-Object { $_.label -like 'v3r22_consumed_*' }).Count -eq 20) 'all 20 consumed V3r22 runtime bindings are required'
Assert-True (@($fixedRows | Where-Object { $_.label -like 'v3r21_*' }).Count -eq 19) 'all 19 consumed V3r21 runtime bindings are required'
Assert-True (@($fixedRows | Where-Object { $_.label -like 'v3r10_*' }).Count -eq 11) 'all 11 rejected V3r10 history bindings are required'
Assert-True (@($fixedRows | Where-Object { $_.label -like 'v3r11_*' }).Count -eq 4) 'all four incomplete V3r11 bindings are required'

# Parse the exact retained CRLF manifest, prove all 137 rows, and reject every
# line-ending/path/label ambiguity that V3r10 left open.
$manifestBytes = [IO.File]::ReadAllBytes($manifestPath)
Assert-True ($manifestBytes.Length -eq 24975 -and (Sha $manifestPath) -eq '6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96') 'retained manifest identity drift'
Assert-True (-not ($manifestBytes -contains 0)) 'manifest embedded NUL forbidden'
$manifestText = [Text.Encoding]::UTF8.GetString($manifestBytes)
$manifestLines = $manifestText.Split([string[]]@("`r`n"), [StringSplitOptions]::None)
Assert-True ($manifestLines.Count -eq 140 -and $manifestLines[139] -eq '') 'manifest must be exactly 139 CRLF-terminated lines'
Assert-True ((($manifestText.Replace("`r`n", '')).IndexOf("`r") -lt 0) -and (($manifestText.Replace("`r`n", '')).IndexOf("`n") -lt 0)) 'manifest has bare CR or LF'
Assert-True ($manifestLines[0] -ceq "KIRA_R25_AFES_RETAINED_MANIFEST_V3R9`t1" -and $manifestLines[1] -ceq "label`tpath`tbytes`tsha256") 'manifest header drift'
$manifestRows = @()
$lastLabel = $null
foreach ($line in @($manifestLines[2..138])) {
    $columns = $line.Split("`t")
    Assert-True ($columns.Count -eq 4) 'manifest row column count drift'
    $label = $columns[0]; $rowPath = $columns[1]; $rowBytes = 0L
    Assert-True ($label -cmatch '^[a-z0-9_]{1,96}$') "manifest label grammar drift: $label"
    if ($null -ne $lastLabel) { Assert-True ([string]::CompareOrdinal($lastLabel, $label) -lt 0) 'manifest labels not strict ordinal sorted/unique' }
    $lastLabel = $label
    Assert-True ([long]::TryParse($columns[2], [Globalization.NumberStyles]::None, [Globalization.CultureInfo]::InvariantCulture, [ref]$rowBytes) -and $rowBytes -ge 0 -and $rowBytes -le 134217728) "manifest byte grammar drift: $label"
    Assert-True ($columns[3] -cmatch '^[0-9a-f]{64}$') "manifest digest grammar drift: $label"
    Assert-True (-not $rowPath.Contains('\') -and -not $rowPath.Contains('//') -and -not $rowPath.EndsWith('/') -and $rowPath -notmatch '(^|/)\.\.?(/|$)') "manifest path grammar drift: $label"
    $actualPath = Resolve-Subject $rowPath
    Assert-True (Test-Path -LiteralPath $actualPath -PathType Leaf) "retained row absent: $rowPath"
    Assert-True ((Bytes $actualPath) -eq $rowBytes) "retained row byte drift: $rowPath"
    Assert-True ((Sha $actualPath) -ceq $columns[3]) "retained row digest drift: $rowPath"
    $manifestRows += [pscustomobject]@{ path = $rowPath; bytes = $rowBytes; sha256 = $columns[3]; label = $label }
}
Assert-True ($manifestRows.Count -eq 137 -and ($manifestRows.path | Sort-Object -Unique).Count -eq 137) 'manifest must contain 137 unique paths'

# Independently close and rehash all 20 consumed V3r22 failure artifacts.
$v3r22Rows = @()
foreach ($row in @($contract.v3r22_consumed_failure_closure.rows)) {
    $subject = Resolve-Subject ([string]$row[0])
    Assert-True (Test-Path -LiteralPath $subject -PathType Leaf) "V3r22 closure subject absent: $($row[0])"
    Assert-True ((Bytes $subject) -eq [long]$row[1] -and (Sha $subject) -ceq [string]$row[2]) "V3r22 closure drift: $($row[0])"
    $v3r22Rows += [pscustomobject]@{ path = [string]$row[0]; bytes = [long]$row[1]; sha256 = [string]$row[2] }
}
$v3r22Root = Canonical-Root $v3r22Rows
Assert-True ($v3r22Rows.Count -eq 20 -and $v3r22Root.bytes -eq 3779 -and $v3r22Root.sha256 -ceq '7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0') 'V3r22 canonical closure root drift'

# Reconstruct the exact 27-row V3r9/V3r10/V3r11 history root rather than
# trusting its declaration. Twenty-three rows are in fixed[]; four retained
# plan/audit roots are held separately.
$historyRows = @($fixedRows | Where-Object { $_.label -match '^v3r(9|10|11)_' } | ForEach-Object {
    [pscustomobject]@{ path = $_.path; bytes = $_.bytes; sha256 = $_.sha256 }
})
$historyExtras = @(
    @('MANIFEST_PATH', 'V3R22_MANIFEST_BYTES', 'V3R22_MANIFEST_SHA256'),
    @('CONTROLLER_PATH', 'V3R22_CONTROLLER_BYTES', 'V3R22_CONTROLLER_SHA256'),
    @('EXECUTION_CONTRACT_PATH', 'V3R22_EXECUTION_CONTRACT_BYTES', 'V3R22_EXECUTION_CONTRACT_SHA256'),
    @('V3R9_AUDIT_PATH', 'V3R22_V3R9_AUDIT_BYTES', 'V3R22_V3R9_AUDIT_SHA256')
)
foreach ($binding in $historyExtras) {
    $fullPath = Resolve-Subject ([string]$pathValues[$binding[0]])
    Assert-True (Test-Path -LiteralPath $fullPath -PathType Leaf) "history subject absent: $fullPath"
    Assert-True ((Bytes $fullPath) -eq [long]$macroValues[$binding[1]] -and (Sha $fullPath) -ceq [string]$macroValues[$binding[2]]) "history subject drift: $fullPath"
    $historyRows += [pscustomobject]@{ path = (Canonical-Path $fullPath); bytes = [long]$macroValues[$binding[1]]; sha256 = [string]$macroValues[$binding[2]] }
}
$historyRoot = Canonical-Root $historyRows
Assert-True ($historyRows.Count -eq 27 -and ($historyRows.path | Sort-Object -Unique).Count -eq 27 -and $historyRoot.bytes -eq 4593 -and $historyRoot.sha256 -ceq 'ac609d3149b18546431377a8ec846d4cd3af098663649c03f41e4d83a0a9ff82') '27-row history canonical closure drift'

# Reproduce, but never execute, V3r20's exact sealed analyzer negatives.
Assert-True ($v3r20Source.Contains('memcpy(record.magic, "KIRA_R25_AFES_V3R20_RESERVATION", 34U);')) 'V3r20 34-from-32 negative control absent'
Assert-True ($v3r20Source.Contains('memcpy(record.magic, "KIRA_R25_AFES_V3R20_TERMINAL", 31U);')) 'V3r20 31-from-29 negative control absent'

# The V3r22 likely-cause diagnosis is static and does not evaluate Python.
Assert-True ([regex]::Matches($v3r22Source, '__annotations__').Count -ge 4) 'V3r22 annotation-evaluation trigger absent'
Assert-True ($v3r22Controller -match '\bdict\[str, Any\]' -and $v3r22Controller -match '\bMapping\[str, Any\]' -and $v3r22Controller -match '\bSequence\[Mapping\[str, Any\]\]' -and $v3r22Controller -match '\bBaseException\b') 'controller unresolved annotation names absent'
Assert-True ($v3r22Controller -notmatch '(?m)^from __future__ import annotations\s*$' -and $v3r22Controller -notmatch '(?m)^(?:from typing import|import typing\b)') 'controller unexpectedly resolves annotations'

# Every required V3r23 source predicate is attacked independently in memory.
# The checker itself never compiles, imports, or invokes the candidate.
$requiredSourceLiterals = @(
    '#define RETAINED_ROW_COUNT 137U',
    '#define MANIFEST_LINE_COUNT 139U',
    'static int parse_and_lock_manifest_rows(',
    'row_count != RETAINED_ROW_COUNT) goto failure;',
    '!parse_and_lock_manifest_rows(manifest, manifest_bytes, manifest_rows)',
    'retained_recheck_ok = recheck_manifest_rows(manifest_rows) &&',
    'static const char *keys[21]',
    'KIRA_R25_AFES_EXECUTION_PLAN_VALIDATION_AUDIT_V3R23\t1',
    'memchr(audit, ''\0'', audit_bytes) != NULL',
    'v3r22_consumed_failure_closure_root_sha256',
    'v3r9_v3r10_v3r11_history_closure_root_sha256',
    '_v3_zip=''C:/Users/robmc/Kira/tools/native/runtime/python314_stdlib_v3r4.zip''',
    '_v3_origin(_v3_b,''builtins'',{''built-in''})',
    '_v3_origin(_v3_m,''marshal'',{''built-in''})',
    '_v3_origin(_v3_j,''json''',
    '_v3_origin(_v3_t,''types''',
    'def _v3_annotate_fingerprint(fn,expected_globals):',
    "annotate=getattr(fn,'__annotate__',None)",
    'controller_function_code_or_deferred_annotate_metadata:',
    'captured[name]=(id(a),id(b),ac,bc,id(a.__code__),id(b.__code__)',
    'a.__globals__ is not left or b.__globals__ is not right',
    'a.__closure__ is not None or b.__closure__ is not None',
    '_v3_helper_names=(''',
    'def _v3_capture_helpers(snapshot=None):',
    '_v3_annotate_fingerprint(fn,harness)',
    '_v3_helper_snapshot=_v3_capture_helpers()',
    '_v3_capture_helpers(_v3_helper_snapshot)',
    '_v3_module_fingerprint()!=_v3_module_snapshot',
    'native_sha_helper_post_call_drift',
    '_v3_counts!={''sha'':222,''hex'':231,''json'':4,''forbidden'':0,''plan'':1}',
    'g_plan_native_sha_calls != 223ULL',
    '__v3r23_checkpoint__=100',
    '__v3r23_checkpoint__=110',
    '__v3r23_checkpoint__=120',
    '__v3r23_checkpoint__=130',
    '__v3r23_checkpoint__=140',
    '__v3r23_checkpoint__=150',
    '__v3r23_plan_attempts__+=1; __v3r23_checkpoint__=160',
    '__v3r23_plan_returns__+=1; __v3r23_checkpoint__=170',
    '__v3r23_checkpoint__=180',
    '__v3r23_checkpoint__=190',
    '__v3r23_checkpoint__=200',
    '__v3r23_checkpoint__=210',
    '__v3r23_checkpoint__=220',
    '__v3r23_checkpoint__=230',
    'RESOLVE_API(api, error_get_raised, "PyErr_GetRaisedException")',
    '#define PY_EXCEPTION_TYPE_CAPACITY 64U',
    '#define PY_EXCEPTION_MESSAGE_CAPACITY 192U',
    '_Static_assert(sizeof(ReservationRecord) == 424U,',
    '_Static_assert(sizeof(ValidatorTelemetry) == 296U,',
    '_Static_assert(sizeof(CompletionRecord) == 888U,',
    'static void sanitize_python_text(',
    'static void capture_python_exception(',
    'static int capture_progress_value(',
    'append_validator_telemetry(evidence, &validator_telemetry)',
    'validator_telemetry.retained_recheck_passed = retained_recheck_ok ? 1U : 0U;',
    '__v3r23_plan_validation__=(137,1,222,231,4,0,_v3_code_root)',
    'python_evidence_ok = append_line(evidence, E_PYTHON) &&',
    'append_line(evidence, E_CONTROLLER) && append_line(evidence, E_PLAN)',
    'bootstrap,broker,process,AFES,Blender,body,save,render,export'
)
$forbiddenSourcePatterns = @(
    '(?i)hashlib',
    '__annotations__',
    '\bCreateProcess[AW]?\s*\(',
    '\bShellExecute(?:Ex)?[AW]?\s*\(',
    '\bWinExec\s*\(',
    '\b(?:_popen|popen|system)\s*\('
)
function Test-SourcePolicy([string]$Candidate) {
    $script:sourcePolicyReason = ''
    foreach ($literal in $requiredSourceLiterals) { if (-not $Candidate.Contains($literal)) { $script:sourcePolicyReason = "missing:$literal"; return $false } }
    foreach ($pattern in $forbiddenSourcePatterns) { if ([regex]::IsMatch($Candidate, $pattern)) { $script:sourcePolicyReason = "forbidden:$pattern"; return $false } }
    if ([regex]::Matches($Candidate, "_v3_left\['_build_execution_plan'\]\(").Count -ne 1) { $script:sourcePolicyReason = 'plan_call_count'; return $false }
    if ([regex]::Matches($Candidate, '\{V3R21_[A-Z0-9_]+_PATH,\s*V3R22_V3R21_').Count -ne 19) { $script:sourcePolicyReason = 'v3r21_fixed_count'; return $false }
    if ([regex]::Matches($Candidate, '\{V3R22_CONSUMED_[A-Z0-9_]+_PATH,\s*V3R23_V3R22_').Count -ne 20) { $script:sourcePolicyReason = 'v3r22_fixed_count'; return $false }
    return $true
}
Assert-True (Test-SourcePolicy $source) "baseline V3r23 source policy failed: $script:sourcePolicyReason"
foreach ($literal in $requiredSourceLiterals) {
    $mutant = $source.Replace($literal, '__HOSTILE_REMOVAL__')
    Assert-True (-not (Test-SourcePolicy $mutant)) "required source mutation survived: $literal"
}
foreach ($injection in @('hashlib', 'CreateProcessW(', 'ShellExecuteExW(', 'WinExec(', 'system(', 'popen(')) {
    Assert-True (-not (Test-SourcePolicy ($source + "`n" + $injection))) "forbidden source injection survived: $injection"
}
Assert-True (-not (Test-SourcePolicy ($source.Replace('__annotate__', '__annotations__')))) 'deferred-annotation evaluation hostile substitution survived'
$doubleCall = $source.Replace("_v3_counts['plan']+=1", "_v3_left['_build_execution_plan'](`n_v3_counts['plan']+=1")
Assert-True (-not (Test-SourcePolicy $doubleCall)) 'second direct plan call hostile mutation survived'

if ($Phase -eq 'PreSeal') {
    Assert-True (-not (Test-Path -LiteralPath $sealPath)) 'V3r23 seal must be absent during PreSeal'
}

if ($Phase -eq 'PostSeal') {
    Assert-True (Test-Path -LiteralPath $sealPath -PathType Leaf) 'V3r23 seal absent in PostSeal'
    Assert-True (Test-Path -LiteralPath $buildPath -PathType Leaf) 'V3r23 build/static results absent in PostSeal'
    $seal = [IO.File]::ReadAllText($sealPath) | ConvertFrom-Json
    Assert-True ($seal.schema -eq 'kira.r25.afes.v3r23.static_seal.v1') 'V3r22 seal schema drift'
    Assert-True ($seal.status -eq 'SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT') 'V3r22 seal status drift'
    Assert-True ($seal.execution_authority -eq 'NONE' -and $seal.candidate_executed -eq $false) 'seal grants or claims execution'
    Assert-True ($seal.sealed_subject_count -eq 257 -and $seal.unique_paths -eq $true) 'seal unique subject declaration drift'
    Assert-True ($seal.semantic_counts.current_artifacts -eq 8 -and $seal.semantic_counts.runtime_fixed_bindings -eq 120 -and $seal.semantic_counts.retained_manifest_rows -eq 137 -and $seal.semantic_counts.unique_union -eq 257) 'seal semantic group counts drift'

    $expected = @{}
    function Add-Expected([string]$Path, [long]$ExpectedBytes, [string]$ExpectedSha, [string]$Role) {
        if ($expected.ContainsKey($Path)) {
            Assert-True ($expected[$Path].bytes -eq $ExpectedBytes -and $expected[$Path].sha256 -ceq $ExpectedSha) "overlapping seal role disagrees: $Path"
            $expected[$Path].roles += $Role
        } else {
            $expected[$Path] = [pscustomobject]@{ bytes = $ExpectedBytes; sha256 = $ExpectedSha; roles = @($Role) }
        }
    }
    $currentPaths = @(
        'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r23.json',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r23.c',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r23_identity_anchor.h',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r23.obj',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r23.exe',
        'Testing/test_kira_r25_foundation_afes_execution_plan_validation_v3r23_static.ps1',
        'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md',
        'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r23_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
    )
    foreach ($path in $currentPaths) {
        $actual = Resolve-Subject $path
        Assert-True (Test-Path -LiteralPath $actual -PathType Leaf) "current seal artifact absent: $path"
        Add-Expected $path (Bytes $actual) (Sha $actual) 'current_artifact'
    }
    foreach ($row in $fixedRows) { Add-Expected $row.path $row.bytes $row.sha256 'runtime_fixed_binding' }
    foreach ($row in $manifestRows) { Add-Expected $row.path $row.bytes $row.sha256 'retained_manifest_row' }
    Assert-True ($expected.Count -eq 257) 'derived V3r23 unique union is not exactly 257'

    $sealedRows = @($seal.sealed_subjects)
    Assert-True ($sealedRows.Count -eq 257 -and ($sealedRows.path | Sort-Object -Unique).Count -eq 257) 'seal rows are not exactly 257 unique paths'
    $difference = @(Compare-Object ($expected.Keys | Sort-Object) ($sealedRows.path | Sort-Object) -CaseSensitive)
    Assert-True ($difference.Count -eq 0) 'seal exact path set drift'
    foreach ($row in $sealedRows) {
        $path = [string]$row.path
        Assert-True ($expected.ContainsKey($path)) "unexpected sealed path: $path"
        Assert-True ([long]$row.bytes -eq [long]$expected[$path].bytes -and [string]$row.sha256 -ceq [string]$expected[$path].sha256) "sealed row metadata drift: $path"
        $actual = Resolve-Subject $path
        Assert-True ((Bytes $actual) -eq [long]$row.bytes -and (Sha $actual) -ceq [string]$row.sha256) "sealed subject changed: $path"
    }
}

'V3R23_HOSTILE_STATIC_TESTS_PASS'
