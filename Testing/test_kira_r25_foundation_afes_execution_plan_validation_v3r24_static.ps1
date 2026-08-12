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
$sourcePath = Join-Path $root 'tools/native/kira_r25_afes_execution_plan_validation_v3r24.c'
$anchorPath = Join-Path $root 'tools/native/kira_r25_afes_execution_plan_validation_v3r24_identity_anchor.h'
$contractPath = Join-Path $root 'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r24.json'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$buildPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
$sealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$futureAuditPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit/attempt_01'
$futureEvidencePath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/RUN_EVIDENCE.jsonl'
$futureReceiptPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin'
$manifestPath = Join-Path $authorityRoot 'RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/RETAINED_NATIVE_LOCK_MANIFEST.tsv'
$stdlibZipPath = Join-Path $authorityRoot 'tools/native/runtime/python314_stdlib_v3r4.zip'
$v3r22AnchorPath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r22_identity_anchor.h'
$v3r23AnchorPath = Join-Path $authorityRoot 'tools/native/kira_r25_afes_execution_plan_validation_v3r23_identity_anchor.h'
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
    $manifestPath, $stdlibZipPath, $v3r22AnchorPath, $v3r23AnchorPath, $codeHeaderPath)) {
    Assert-True (Test-Path -LiteralPath $required -PathType Leaf) "required file absent: $required"
}

$sourceBytes = [IO.File]::ReadAllBytes($sourcePath)
$source = [Text.Encoding]::UTF8.GetString($sourceBytes)
$anchor = [IO.File]::ReadAllText($v3r22AnchorPath) + "`n" +
    [IO.File]::ReadAllText($v3r23AnchorPath) + "`n" + [IO.File]::ReadAllText($anchorPath)
$contract = [IO.File]::ReadAllText($contractPath) | ConvertFrom-Json
$control = [IO.File]::ReadAllText($controlPath)

Assert-True (-not ($sourceBytes.Length -ge 3 -and $sourceBytes[0] -eq 0xEF -and $sourceBytes[1] -eq 0xBB -and $sourceBytes[2] -eq 0xBF)) 'source BOM forbidden'
Assert-True (-not $source.Contains("`r")) 'source must be LF-only'
Assert-True ($contract.schema -eq 'kira.avatar.r25.foundation_afes_execution_plan_validation.v3r24') 'contract schema drift'
Assert-True ($contract.status -eq 'STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY') 'contract status drift'
Assert-True ($contract.execution_authority -eq 'NONE' -and $contract.candidate_executed -eq $false) 'contract grants or claims execution'
Assert-True ($contract.predecessor.version -eq 'v3r23' -and $contract.predecessor.status -eq 'REJECTED_NO_EXECUTION_AUTHORITY' -and $contract.predecessor.candidate_executed -eq $false) 'V3r23 predecessor truth drift'
Assert-True ($contract.v3r22_consumed_failure.status -eq 'CONSUMED_BOUNDED_FAILURE_DO_NOT_RERUN' -and $contract.v3r22_consumed_failure.terminal_stage -eq 40 -and $contract.v3r22_consumed_failure.exact_plan_call_count_known -eq $false) 'V3r22 consumed failure truth drift'
Assert-True ($contract.failure_cause_truth.actual_cause -eq 'UNKNOWN') 'unknown V3r22 cause was replaced by speculation'
Assert-True ($contract.failure_cause_truth.controller_compile_flags_literal -eq '0x1000000' -and $contract.failure_cause_truth.controller_compile_flag_name -eq 'CO_FUTURE_ANNOTATIONS' -and $contract.failure_cause_truth.controller_compile_flag_value -eq 16777216) 'future-annotations flag declaration drift'
Assert-True ($contract.failure_cause_truth.retained_controller_annotations -eq 'STRINGIZED_NOT_GLOBAL_NAME_EVALUATED' -and $contract.failure_cause_truth.excluded_cause_status -eq 'PROVEN_EXCLUDED_BY_EXACT_COMPILE_FLAG_AND_LOCKED_RUNTIME_SEMANTICS') 'excluded annotation cause truth drift'
Assert-True ($contract.v3r23_rejected_closure.row_count -eq 15 -and $contract.v3r23_rejected_closure.author_artifact_count -eq 10 -and $contract.v3r23_rejected_closure.rejection_artifact_count -eq 5 -and $contract.v3r23_rejected_closure.authority -eq 'REJECTED_NO_EXECUTION_AUTHORITY') 'V3r23 closure declaration drift'
Assert-True ($contract.v3r22_consumed_failure_closure.row_count -eq 20 -and $contract.v3r22_consumed_failure_closure.authority -eq 'CONSUMED_FAILURE_DO_NOT_RERUN') 'V3r22 closure declaration drift'
Assert-True ((@($contract.diagnostic_telemetry.checkpoint_sequence) -join ',') -ceq '100,110,120,130,140,141,150,151,160,161,170,171,180,181,190,191,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,229,230') 'checkpoint contract drift'
Assert-True ($contract.diagnostic_telemetry.operation_count_on_success -eq 21 -and $contract.single_plan_call.maximum_calls -eq 1) 'bounded operation/plan count drift'
Assert-True ($contract.diagnostic_telemetry.exception_capture.type_capacity_including_nul -eq 64 -and $contract.diagnostic_telemetry.exception_capture.message_capacity_including_nul -eq 192 -and $contract.diagnostic_telemetry.exception_capture.traceback -eq 'NOT_CAPTURED') 'bounded exception contract drift'
Assert-True ($contract.fresh_audit_grammar.line_count -eq 29 -and $contract.fresh_audit_grammar.field_line_count -eq 28) 'different-audit grammar drift'
Assert-True ($contract.downstream_owner_routing.owner -eq 'AVATAR_BUILDER_REUSABLE_METHOD_TEMPLATE_LAYER' -and $contract.downstream_owner_routing.rejected_result_route -eq 'DO_NOT_REPEAT_TESTS_ONLY' -and $contract.downstream_owner_routing.this_contract_integrates_a_body -eq $false) 'downstream owner routing drift'
Assert-True ((@($contract.stop_before) -join ',') -ceq 'bootstrap,broker,process,AFES,Blender,body,save,render,export') 'stop-before boundary drift'
Assert-True ($control.Contains('actual V3r22 stage-40 cause remains unknown')) 'control omits unknown-cause boundary'
Assert-True ($control.Contains('0x1000000 == CO_FUTURE_ANNOTATIONS')) 'control omits compile-flag proof'
Assert-True ($control.Contains('Avatar Builder reusable method/template layer') -and $control.Contains('A rejected result may contribute only a `DO_NOT_REPEAT` test.')) 'control omits downstream owner routing'
Assert-True ($control.Contains('Execution authority: **NONE**')) 'control grants execution authority'
Assert-True (-not (Test-Path -LiteralPath $futureAuditPath)) 'future different-audit root must be absent'
Assert-True (-not (Test-Path -LiteralPath $futureEvidencePath) -and -not (Test-Path -LiteralPath $futureReceiptPath)) 'future evidence/receipt must be absent'

# Freeze every macro used by the current source and independently rehash all 136 fixed subjects.
$macroValues = @{}
foreach ($match in [regex]::Matches($anchor, '#define\s+(V3R(?:22|23|24)_[A-Z0-9_]+)\s+(?:"([0-9a-f]{64})"|([0-9]+)ULL)')) {
    if ($match.Groups[2].Success) { $macroValues[$match.Groups[1].Value] = $match.Groups[2].Value }
    else { $macroValues[$match.Groups[1].Value] = [long]$match.Groups[3].Value }
}
Assert-True ($macroValues.Count -ge 260) 'identity anchor macro closure unexpectedly small'
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
$fixedMatches = [regex]::Matches($fixedBlock, '\{([A-Z0-9_]+_PATH),\s*(V3R(?:22|24)_[A-Z0-9_]+_BYTES),\s*(V3R(?:22|24)_[A-Z0-9_]+_SHA256),\s*"([^"]+)"')
Assert-True ($fixedMatches.Count -eq 136) 'runtime fixed closure must be exactly 136 rows'
$fixedRows = @()
foreach ($match in $fixedMatches) {
    $fullPath = Resolve-Subject ([string]$pathValues[$match.Groups[1].Value])
    $expectedBytes = [long]$macroValues[$match.Groups[2].Value]
    $expectedSha = [string]$macroValues[$match.Groups[3].Value]
    Assert-True (Test-Path -LiteralPath $fullPath -PathType Leaf) "fixed subject absent: $fullPath"
    Assert-True ((Bytes $fullPath) -eq $expectedBytes -and (Sha $fullPath) -ceq $expectedSha) "fixed subject drift: $fullPath"
    $fixedRows += [pscustomobject]@{ path = (Canonical-Path $fullPath); bytes = $expectedBytes; sha256 = $expectedSha; label = $match.Groups[4].Value }
}
Assert-True (($fixedRows.path | Sort-Object -Unique).Count -eq 136) 'runtime fixed paths are not unique'
Assert-True (@($fixedRows | Where-Object label -like 'v3r23_*').Count -eq 15) 'all 15 rejected V3r23 artifacts must be fixed'
Assert-True (@($fixedRows | Where-Object label -like 'v3r22_consumed_*').Count -eq 20) 'all 20 consumed V3r22 artifacts must be fixed'
Assert-True (@($fixedRows | Where-Object label -eq 'cpython_code_header_future_annotations_definition').Count -eq 1) 'CPython header binding absent'

# Rehash predecessor closures from the contract, including their canonical roots.
foreach ($closureCase in @(
    @($contract.v3r22_consumed_failure_closure, 20, 3779, '7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0', 'V3r22'),
    @($contract.v3r23_rejected_closure, 15, 2728, '0b09c1f71154b4d56559f043f08076940bcc60e7919d6bcd8e9c3cde3b2a4ea0', 'V3r23')
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

# Author-level hostile source probes. They inspect text only and never compile/evaluate Python.
$requiredSourceLiterals = @(
    '_Static_assert(CO_FUTURE_ANNOTATIONS == 0x1000000,',
    'flags=0x1000000,dont_inherit=True,optimize=0',
    "code.co_flags & 0x1000000 != 0x1000000",
    "a.__code__.co_flags & 0x1000000 != 0x1000000",
    "annotate=getattr(fn,'__annotate__',None)",
    'future_annotations_stringizer_missing:',
    'static const char *keys[28]',
    'v3r23_rejected_closure_root_sha256',
    'controller_compile_flag_name',
    'UNRESOLVED_ANNOTATION_NAMES_PROVEN_EXCLUDED',
    '__v3r24_operation_enters__=0',
    '__v3r24_operation_returns__=0',
    '__v3r24_plan_attempts__+=1; __v3r24_checkpoint__=170',
    '__v3r24_plan_returns__+=1; __v3r24_operation_returns__+=1; __v3r24_checkpoint__=171',
    '__v3r24_plan_validation__=(137,1,222,231,4,0,__v3r24_operation_enters__,__v3r24_operation_returns__+1,_v3_code_root)',
    'telemetry->operation_enters != 21U',
    'telemetry->operation_returns != 21U',
    '_Static_assert(sizeof(ValidatorTelemetry) == 304U,',
    '_Static_assert(sizeof(CompletionRecord) == 896U,',
    '#define PY_EXCEPTION_TYPE_CAPACITY 64U',
    '#define PY_EXCEPTION_MESSAGE_CAPACITY 192U',
    'PyErr_GetRaisedException',
    'bootstrap,broker,process,AFES,Blender,body,save,render,export'
)
$expectedCheckpoints = @(100,110,120,130,140,141,150,151,160,161,170,171,180,181,190,191,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,229,230)
foreach ($checkpoint in $expectedCheckpoints) { $requiredSourceLiterals += "__v3r24_checkpoint__=$checkpoint" }
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
    if ([regex]::Matches($Candidate, '__v3r24_operation_enters__\+=1').Count -ne 21) { $script:sourcePolicyReason = 'operation_enter_count'; return $false }
    if ([regex]::Matches($Candidate, '__v3r24_operation_returns__\+=1').Count -ne 21) { $script:sourcePolicyReason = 'operation_return_count'; return $false }
    if ([regex]::Matches($Candidate, '\{V3R23_(?:REJECTED|REJECTION)_[A-Z0-9_]+_PATH,\s*V3R24_V3R23_').Count -ne 15) { $script:sourcePolicyReason = 'v3r23_fixed_count'; return $false }
    return $true
}
Assert-True (Test-SourcePolicy $source) "baseline V3r24 source policy failed: $script:sourcePolicyReason"
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
    'v3r23_rejected_closure_root_sha256','v3r9_v3r10_v3r11_history_closure_root_sha256',
    'controller_compile_flag','controller_compile_flag_name','excluded_failure_cause','plan_callable',
    'plan_call_maximum','validator_checkpoint_terminal_success','operation_enter_maximum',
    'operation_return_maximum','exception_type_max_bytes','exception_message_max_bytes',
    'v3r22_authority','v3r23_authority','stop_before')
$auditKeysStart = $source.IndexOf('static const char *keys[28]')
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
    Assert-True ($seal.schema -eq 'kira.r25.afes.v3r24.static_seal.v1' -and $seal.status -eq 'SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT') 'seal identity/status drift'
    Assert-True ($seal.execution_authority -eq 'NONE' -and $seal.candidate_executed -eq $false) 'seal grants or claims execution'
    Assert-True ($seal.sealed_subject_count -eq 273 -and $seal.unique_paths -eq $true) 'seal subject declaration drift'
    Assert-True ($seal.semantic_counts.current_artifacts -eq 8 -and $seal.semantic_counts.runtime_fixed_bindings -eq 136 -and $seal.semantic_counts.retained_manifest_rows -eq 137 -and $seal.semantic_counts.unique_union -eq 273) 'seal semantic counts drift'
    $expected = @{}
    function Add-Expected([string]$Path, [long]$ExpectedBytes, [string]$ExpectedSha, [string]$Role) {
        if ($expected.ContainsKey($Path)) {
            Assert-True ($expected[$Path].bytes -eq $ExpectedBytes -and $expected[$Path].sha256 -ceq $ExpectedSha) "overlap disagrees: $Path"
            $expected[$Path].roles += $Role
        } else { $expected[$Path] = [pscustomobject]@{ bytes = $ExpectedBytes; sha256 = $ExpectedSha; roles = @($Role) } }
    }
    foreach ($path in @(
        'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r24.json',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r24.c',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r24_identity_anchor.h',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r24.obj',
        'tools/native/kira_r25_afes_execution_plan_validation_v3r24.exe',
        'Testing/test_kira_r25_foundation_afes_execution_plan_validation_v3r24_static.ps1',
        'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md',
        'RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
    )) {
        $actual = Resolve-Subject $path
        Add-Expected $path (Bytes $actual) (Sha $actual) 'current_artifact'
    }
    foreach ($row in $fixedRows) { Add-Expected $row.path $row.bytes $row.sha256 'runtime_fixed_binding' }
    foreach ($row in $manifestRows) { Add-Expected $row.path $row.bytes $row.sha256 'retained_manifest_row' }
    Assert-True ($expected.Count -eq 273) 'derived unique seal union is not 273'
    $sealedRows = @($seal.sealed_subjects)
    Assert-True ($sealedRows.Count -eq 273 -and ($sealedRows.path | Sort-Object -Unique).Count -eq 273) 'seal rows are not 273 unique paths'
    Assert-True (@(Compare-Object ($expected.Keys | Sort-Object) ($sealedRows.path | Sort-Object) -CaseSensitive).Count -eq 0) 'seal exact path set drift'
    foreach ($row in $sealedRows) {
        $path = [string]$row.path; $actual = Resolve-Subject $path
        Assert-True ($expected.ContainsKey($path)) "unexpected sealed path: $path"
        Assert-True ([long]$row.bytes -eq [long]$expected[$path].bytes -and [string]$row.sha256 -ceq [string]$expected[$path].sha256) "seal metadata drift: $path"
        Assert-True ((Bytes $actual) -eq [long]$row.bytes -and (Sha $actual) -ceq [string]$row.sha256) "sealed subject changed: $path"
    }
}

'V3R24_HOSTILE_STATIC_TESTS_PASS'
