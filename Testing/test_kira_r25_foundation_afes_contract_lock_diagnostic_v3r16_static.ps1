$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourcePath = Join-Path $root 'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16.c'
$headerPath = Join-Path $root 'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16_identity_anchor.h'
$exePath = Join-Path $root 'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16.exe'
$contractPath = Join-Path $root 'Avatar\avatar_builder\body_systems\kira_r25_foundation_afes_contract_lock_diagnostic_v3r16.json'
$controlPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\RUNTIME_CONTROL_CHECKPOINT.md'
$postmortemPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r15_consumed_failure_postmortem\attempt_01\CHECKPOINT.md'
$recheckPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r15_consumed_failure_postmortem\attempt_01\READ_ONLY_CONTRACT_RECHECK.json'
$v3r15ContractPath = Join-Path $root 'Avatar\avatar_builder\body_systems\kira_r25_foundation_afes_python_controller_validation_v3r15.json'
$v3r15SourcePath = Join-Path $root 'tools\native\kira_r25_afes_python_controller_validation_v3r15.c'
$v3r15ExePath = Join-Path $root 'tools\native\kira_r25_afes_python_controller_validation_v3r15.exe'
$v3r15AuditPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r15_fresh_static_audit\attempt_01\CHECKPOINT.md'
$evidencePath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\RUN_EVIDENCE.jsonl'
$outcomePath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\CONTRACT_LOCK_DIAGNOSTIC_OUTCOME.receipt.bin'
$auditPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r16_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.tsv'
$auditDigestPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r16_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.sha256'

$script:run = 0
$script:failed = 0
function Assert-True([bool]$Condition, [string]$Name) {
    $script:run++
    if (-not $Condition) { $script:failed++; Write-Host "FAIL $Name" }
}
function Assert-False([bool]$Condition, [string]$Name) { Assert-True (-not $Condition) $Name }
function Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Count-Literal([string]$Text, [string]$Needle) {
    if ($Needle.Length -eq 0) { return 0 }
    $count = 0; $at = 0
    while (($at = $Text.IndexOf($Needle, $at, [StringComparison]::Ordinal)) -ge 0) {
        $count++; $at += $Needle.Length
    }
    return $count
}
function Macro([string]$Text, [string]$Name) {
    $pattern = '(?m)^#define\s+' + [regex]::Escape($Name) + '\s+(?:"([^"]+)"|([0-9]+)ULL)$'
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) { return $null }
    if ($match.Groups[1].Success) { return $match.Groups[1].Value }
    return $match.Groups[2].Value
}
function Is-LowerHex64([string]$Value) { return $null -ne $Value -and $Value -cmatch '^[0-9a-f]{64}$' }
function Static-Policy([string]$Text) {
    $required = @(
        'if (argc != 1) return 2;',
        'verify_audit(self_sha, audit_sha)',
        'verify_output_parent()',
        'reserve_outputs(&evidence, &receipt',
        'diagnostic_ok = diagnose_contract(&terminal);',
        'CreateFileW(V3R15_TARGET_CONTRACT_PATH, GENERIC_READ,',
        'C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r15.json',
        'FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE',
        'FILE_FLAG_OPEN_REPARSE_POINT',
        'GetFileInformationByHandleEx(target, FileBasicInfo',
        'GetFileInformationByHandleEx(target, FileStandardInfo',
        'final_path_matches(target, V3R15_TARGET_CONTRACT_PATH)',
        'get_file_identity(target, &first_identity)',
        'get_file_identity(target, &second_identity)',
        'get_file_identity(target, &final_identity)',
        'hash_handle_bytes(target, record->snapshot_one_sha256',
        'hash_handle_bytes(target, record->snapshot_two_sha256',
        'memcmp(record->snapshot_one_sha256, record->snapshot_two_sha256, SHA_BYTES)',
        'memcmp(record->snapshot_one_sha256, record->expected_target_sha256, SHA_BYTES)',
        'CREATE_NEW',
        'FILE_FLAG_WRITE_THROUGH',
        'FlushFileBuffers',
        'pending_record_sha256',
        'trailing_bytes != 0U',
        'GATE_TARGET_OPEN',
        'GATE_ATTRIBUTES',
        'GATE_SIZE_FIRST',
        'GATE_FINAL_PATH_FIRST',
        'GATE_FILE_ID_FIRST',
        'GATE_SNAPSHOT_ONE',
        'GATE_SIZE_SECOND',
        'GATE_FINAL_PATH_SECOND',
        'GATE_FILE_ID_SECOND',
        'GATE_SNAPSHOT_TWO',
        'GATE_SIZE_FINAL',
        'GATE_FINAL_PATH_FINAL',
        'GATE_FILE_ID_FINAL',
        'GATE_SNAPSHOT_EQUALITY',
        'SetLastError(ERROR_INVALID_NAME)',
        'mark_failure(record, GATE_TARGET_OPEN, GetLastError())',
        'ERROR_INVALID_DATA'
    )
    foreach ($needle in $required) { if (-not $Text.Contains($needle)) { return $false } }
    $forbidden = @(
        'LoadLibrary', 'GetProcAddress', 'Py_Initialize', 'PyConfig_', 'python314.dll',
        'run_kira_r25_foundation_afes_locked_pair_v3r9.py',
        'kira_r25_foundation_afes_locked_pair_execution_v3r9.json',
        '_build_execution_plan', 'CreateProcess', 'ShellExecute', 'WinExec',
        'blender.exe', 'foundation.blend', 'DeleteFile', 'MoveFile', 'ReplaceFile',
        'CREATE_ALWAYS', 'OPEN_ALWAYS', 'TRUNCATE_EXISTING'
    )
    foreach ($needle in $forbidden) { if ($Text.Contains($needle)) { return $false } }
    $auditAt = $Text.IndexOf('verify_audit(self_sha, audit_sha)', [StringComparison]::Ordinal)
    $reserveAt = $Text.IndexOf('reserve_outputs(&evidence, &receipt', [StringComparison]::Ordinal)
    $diagnoseAt = $Text.IndexOf('diagnostic_ok = diagnose_contract(&terminal);', [StringComparison]::Ordinal)
    if (-not ($auditAt -ge 0 -and $reserveAt -gt $auditAt -and $diagnoseAt -gt $reserveAt)) { return $false }
    if ((Count-Literal $Text 'hash_handle_bytes(target, record->snapshot_one_sha256') -ne 1) { return $false }
    if ((Count-Literal $Text 'hash_handle_bytes(target, record->snapshot_two_sha256') -ne 1) { return $false }
    if ((Count-Literal $Text 'CreateFileW(V3R15_TARGET_CONTRACT_PATH, GENERIC_READ,') -ne 1) { return $false }
    $targetOpenAt = $Text.IndexOf('CreateFileW(V3R15_TARGET_CONTRACT_PATH, GENERIC_READ,', [StringComparison]::Ordinal)
    $targetOpenEnd = if ($targetOpenAt -ge 0) { $Text.IndexOf('NULL);', $targetOpenAt, [StringComparison]::Ordinal) } else { -1 }
    if ($targetOpenEnd -lt 0) { return $false }
    $targetOpen = $Text.Substring($targetOpenAt, $targetOpenEnd - $targetOpenAt)
    if (-not $targetOpen.Contains('FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE')) { return $false }
    if ($Text.Contains('diagnose_contract(&terminal); reserve_outputs')) { return $false }
    return $true
}

foreach ($path in @($sourcePath,$headerPath,$exePath,$contractPath,$controlPath,
        $postmortemPath,$recheckPath,$v3r15ContractPath,$v3r15SourcePath,$v3r15ExePath,$v3r15AuditPath)) {
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "required:$path"
}

$utf8 = [Text.UTF8Encoding]::new($false, $true)
$source = [IO.File]::ReadAllText($sourcePath, $utf8)
$header = [IO.File]::ReadAllText($headerPath, $utf8)
$control = [IO.File]::ReadAllText($controlPath, $utf8)
$postmortem = [IO.File]::ReadAllText($postmortemPath, $utf8)
$recheck = Get-Content -Raw -LiteralPath $recheckPath | ConvertFrom-Json
$contract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json

Assert-True ($contract.schema -ceq 'kira.avatar.r25.foundation_afes_contract_lock_diagnostic.v3r16') 'contract-schema'
Assert-True ($contract.status -ceq 'STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY') 'contract-static-status'
Assert-True ($contract.predecessor.status -ceq 'CONSUMED_FAILURE_NO_RETRY') 'v3r15-consumed-no-retry'
Assert-True ($contract.predecessor.python_dll_touched -eq $false) 'v3r15-python-untouched'
Assert-True ($contract.predecessor.controller_touched -eq $false) 'v3r15-controller-untouched'
Assert-True ($contract.single_stage.name -ceq 'RESERVATION_FIRST_GRANULAR_CONTRACT_LOCK_DIAGNOSTIC_ONLY') 'single-stage'
Assert-True ($contract.single_stage.target_expected_bytes -eq 6174) 'target-bytes'
Assert-True ($contract.single_stage.target_expected_sha256 -ceq 'ad33386d767b516425dcbed073e22dfc9747a963a64dc5d205483d210acac79d') 'target-sha'
Assert-True ($contract.single_stage.python_dll_load -eq $false) 'no-python-load'
Assert-True ($contract.single_stage.python_interpreter_initialization -eq $false) 'no-python-init'
Assert-True ($contract.single_stage.controller_read_or_evaluation -eq $false) 'no-controller'
Assert-True ($contract.single_stage.execution_contract_read -eq $false) 'no-execution-contract'
Assert-True ($contract.single_stage.plan_builder_called -eq $false) 'no-plan-builder'
Assert-True ($contract.single_stage.broker_or_child_created -eq $false) 'no-broker-child'
Assert-True ($contract.outputs.creation -ceq 'CREATE_NEW_WRITE_THROUGH') 'output-create-new'
Assert-True ($contract.outputs.receipt_records -eq 2) 'two-receipt-records'
Assert-True ($contract.outputs.starting_executable_consumes_authority -eq $true) 'start-consumes'
Assert-True ($contract.outputs.partial_output_consumes_authority -eq $true) 'partial-consumes'
Assert-True ($contract.outputs.retry -eq $false) 'no-retry'
Assert-True ($contract.required_future_audit.decision -ceq 'ACCEPTED_FOR_ONE_BOUNDED_CONTRACT_LOCK_DIAGNOSTIC_ONLY') 'future-audit-decision'
Assert-True ($contract.forbidden -contains 'Python DLL load or Python interpreter initialization') 'contract-forbids-python'
Assert-True ($contract.forbidden -contains 'AFES or Blender access') 'contract-forbids-afes-blender'
Assert-True ($contract.forbidden -contains 'body, mesh, armature, anatomy, material, pose, or movement access') 'contract-forbids-body'

Assert-True ($recheck.consumed_status -ceq 'CONSUMED_FAILURE_NO_RETRY') 'recheck-consumed'
Assert-True ($recheck.earliest_exact_failure.fixed_subject_index -eq 0) 'recheck-first-subject'
Assert-True ($recheck.earliest_exact_failure.exact_failed_subcondition_recoverable -eq $false) 'recheck-not-invented'
Assert-True ($recheck.unreached_operations.python_dll_load -eq $true) 'recheck-python-unreached'
Assert-True ($postmortem.Contains('CONSUMED_FAILURE_NO_RETRY')) 'postmortem-consumed'
Assert-True ($postmortem.Contains('The exact historical subcondition cannot be recovered.')) 'postmortem-truth'
Assert-True ($control.Contains('NO_EXECUTION_AUTHORITY')) 'control-no-authority'
Assert-True ($control.Contains('V3r15 CONSUMED_FAILURE_NO_RETRY')) 'control-no-retry'
Assert-True ($control.Contains('V3r16 contains no retained Python stage.')) 'control-no-python-stage'

Assert-True (Static-Policy $source) 'source-static-policy'
Assert-True ((Count-Literal $source 'int wmain(') -eq 1) 'one-entrypoint'
Assert-True ((Count-Literal $source 'FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE') -ge 3) 'diagnostic-share-mask'
Assert-True ($source.Contains('terminal = pending;')) 'terminal-binds-pending'
Assert-True ($source.Contains('sha_buffer(pending, (ULONG)sizeof(*pending), terminal->pending_record_sha256)')) 'terminal-pending-hash'
Assert-True ($source.Contains('hash_handle_bytes(evidence, terminal->evidence_sha256')) 'terminal-evidence-hash'
Assert-True ($source.Contains('memcmp(pending, &pending_readback')) 'pending-readback'
Assert-True ($source.Contains('memcmp(terminal, &terminal_readback')) 'terminal-readback'
Assert-True ($source.Contains('receipt_bytes != sizeof(*pending) + sizeof(*terminal)')) 'receipt-exact-size'
Assert-True ($source.Contains('same_identity(&first_identity, &second_identity)')) 'same-id-second'
Assert-True ($source.Contains('same_identity(&first_identity, &final_identity)')) 'same-id-final'

$mutations = @(
    $source.Replace('FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING,', 'FILE_SHARE_READ, NULL, OPEN_EXISTING,'),
    $source.Replace('hash_handle_bytes(target, record->snapshot_two_sha256', 'hash_handle_bytes_removed(target, record->snapshot_two_sha256'),
    $source.Replace('CREATE_NEW', 'OPEN_ALWAYS'),
    $source.Replace('diagnostic_ok = diagnose_contract(&terminal);', 'LoadLibraryW(L"python314.dll"); diagnostic_ok = diagnose_contract(&terminal);'),
    $source.Replace('diagnostic_ok = diagnose_contract(&terminal);', 'CreateProcessW(NULL,NULL,NULL,NULL,FALSE,0,NULL,NULL,NULL,NULL); diagnostic_ok = diagnose_contract(&terminal);'),
    $source.Replace('C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r15.json', 'C:\\temp\\wrong.json'),
    $source.Replace('reserve_outputs(&evidence, &receipt', 'diagnose_contract(&terminal); reserve_outputs(&evidence, &receipt')
)
$mutationNames = @('share-narrowed','second-snapshot-removed','create-new-weakened','python-inserted','process-inserted','target-drift','diagnose-before-reserve')
for ($index = 0; $index -lt $mutations.Count; $index++) {
    Assert-False (Static-Policy $mutations[$index]) "hostile:$($mutationNames[$index])"
}

$macroChecks = @(
    @('V3R16_CONTRACT_BYTES',(Get-Item $contractPath).Length.ToString()),
    @('V3R16_CONTRACT_SHA256',(Sha $contractPath)),
    @('V3R16_SOURCE_BYTES',(Get-Item $sourcePath).Length.ToString()),
    @('V3R16_SOURCE_SHA256',(Sha $sourcePath)),
    @('V3R16_TEST_BYTES',(Get-Item $PSCommandPath).Length.ToString()),
    @('V3R16_TEST_SHA256',(Sha $PSCommandPath)),
    @('V3R16_CONTROL_BYTES',(Get-Item $controlPath).Length.ToString()),
    @('V3R16_CONTROL_SHA256',(Sha $controlPath)),
    @('V3R16_V3R15_POSTMORTEM_BYTES',(Get-Item $postmortemPath).Length.ToString()),
    @('V3R16_V3R15_POSTMORTEM_SHA256',(Sha $postmortemPath)),
    @('V3R16_V3R15_RECHECK_BYTES',(Get-Item $recheckPath).Length.ToString()),
    @('V3R16_V3R15_RECHECK_SHA256',(Sha $recheckPath)),
    @('V3R16_V3R15_CONTRACT_BYTES','6174'),
    @('V3R16_V3R15_CONTRACT_SHA256','ad33386d767b516425dcbed073e22dfc9747a963a64dc5d205483d210acac79d'),
    @('V3R16_V3R15_AUDIT_BYTES',(Get-Item $v3r15AuditPath).Length.ToString()),
    @('V3R16_V3R15_AUDIT_SHA256',(Sha $v3r15AuditPath))
)
Assert-True ((Macro $header 'V3R16_AUTHOR_ID') -ceq 'codex_r25_afes_v3r16_static_author_blackwell_v9_agent') 'header-author'
foreach ($pair in $macroChecks) {
    Assert-True ((Macro $header $pair[0]) -ceq $pair[1]) "header-binding:$($pair[0])"
    if ($pair[0].EndsWith('_SHA256')) { Assert-True (Is-LowerHex64 (Macro $header $pair[0])) "header-lower:$($pair[0])" }
}

Assert-True ((Sha $v3r15ContractPath) -ceq 'ad33386d767b516425dcbed073e22dfc9747a963a64dc5d205483d210acac79d') 'v3r15-contract-preserved'
Assert-True ((Sha $v3r15SourcePath) -ceq '1977d6c2fd273899a4f003ad88e52b44e493bfb8b132b579076e764f68f94c2d') 'v3r15-source-preserved'
Assert-True ((Sha $v3r15ExePath) -ceq '0fa6a3e261d0b7e480f456c236db47608f36d7698b63d890f191f59bd19fb6cd') 'v3r15-exe-preserved'
Assert-True ((Sha $v3r15AuditPath) -ceq '61b28a4f4e62f2713a74991c0f669f709f45782e131377210d266be484c07dfd') 'v3r15-audit-preserved'

$exeBytes = [IO.File]::ReadAllBytes($exePath)
Assert-True ($exeBytes.Length -gt 1024) 'pe-nonempty'
Assert-True ($exeBytes[0] -eq 0x4d -and $exeBytes[1] -eq 0x5a) 'pe-mz'
$peOffset = [BitConverter]::ToInt32($exeBytes, 0x3c)
Assert-True ($peOffset -gt 0 -and $peOffset + 26 -lt $exeBytes.Length) 'pe-offset'
Assert-True ($exeBytes[$peOffset] -eq 0x50 -and $exeBytes[$peOffset+1] -eq 0x45) 'pe-signature'
Assert-True ([BitConverter]::ToUInt16($exeBytes, $peOffset + 4) -eq 0x8664) 'pe-x64'
Assert-True ([BitConverter]::ToUInt16($exeBytes, $peOffset + 24) -eq 0x20b) 'pe32-plus'
$ascii = [Text.Encoding]::ASCII.GetString($exeBytes)
Assert-False ($ascii.Contains('python314.dll')) 'pe-no-python'
Assert-False ($ascii.Contains('blender.exe')) 'pe-no-blender'
Assert-False ($ascii.Contains('CreateProcessW')) 'pe-no-create-process'
Assert-False ($ascii.Contains('ShellExecuteW')) 'pe-no-shell-execute'
Assert-True ($ascii.Contains('BCryptFinishHash')) 'pe-bcrypt'

$dumpbin = Get-ChildItem -LiteralPath 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC' -Directory |
    Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName 'bin\Hostx64\x64\dumpbin.exe' } |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1
Assert-True ($null -ne $dumpbin) 'dumpbin-found'
$imports = if ($null -ne $dumpbin) { (& $dumpbin /imports $exePath 2>&1 | Out-String) } else { '' }
$headers = if ($null -ne $dumpbin) { (& $dumpbin /headers $exePath 2>&1 | Out-String) } else { '' }
Assert-True ($imports.Contains('bcrypt.dll')) 'imports-bcrypt'
Assert-True ($imports.Contains('KERNEL32.dll')) 'imports-kernel32'
Assert-False ($imports.Contains('python314.dll')) 'imports-no-python'
Assert-False ($imports.Contains('USER32.dll')) 'imports-no-user32'
Assert-True ($headers -match '(?i)high entropy virtual addresses') 'pe-high-entropy'
Assert-True ($headers.Contains('Dynamic base')) 'pe-dynamic-base'
Assert-True ($headers.Contains('NX compatible')) 'pe-nx'
Assert-True ($headers.Contains('Guard')) 'pe-cfg'

Assert-False (Test-Path -LiteralPath $evidencePath) 'runtime-evidence-absent'
Assert-False (Test-Path -LiteralPath $outcomePath) 'runtime-outcome-absent'
Assert-False (Test-Path -LiteralPath $auditPath) 'future-audit-absent'
Assert-False (Test-Path -LiteralPath $auditDigestPath) 'future-audit-digest-absent'

Write-Host ("V3R16_STATIC_TESTS run={0} failed={1}" -f $script:run, $script:failed)
if ($script:failed -ne 0) { exit 1 }
exit 0
