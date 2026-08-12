$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$sourcePath = Join-Path $root 'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16.c'
$exePath = Join-Path $root 'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16.exe'
$sealPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\STATIC_SEAL_MANIFEST.json'
$runtimeEvidence = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\RUN_EVIDENCE.jsonl'
$runtimeReceipt = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\CONTRACT_LOCK_DIAGNOSTIC_OUTCOME.receipt.bin'
$candidateAudit = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r16_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.tsv'
$candidateAuditDigest = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r16_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.sha256'
$requiredAuditLiteral = 'C:\Users\robmc\Kira\RecoverySprint\continuation_20260811\kira_r25_afes_contract_lock_diagnostic_v3r16_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.tsv'

$script:run = 0
$script:failed = 0
function Check([bool]$condition, [string]$name) {
    $script:run++
    if ($condition) { Write-Host "PASS`t$name" }
    else { $script:failed++; Write-Host "FAIL`t$name" }
}
function Count-Literal([string]$text, [string]$needle) {
    $count = 0
    $at = 0
    while (($at = $text.IndexOf($needle, $at, [StringComparison]::Ordinal)) -ge 0) {
        $count++
        $at += $needle.Length
    }
    return $count
}

$seal = Get-Content -Raw -LiteralPath $sealPath | ConvertFrom-Json

# The author checkpoint is the outer exact-byte seal presented to this auditor.
$checkpointSeal = [ordered]@{
    'Avatar\avatar_builder\body_systems\kira_r25_foundation_afes_contract_lock_diagnostic_v3r16.json' = @(5276, 'b28c8778a10ffae5c163ca9ee49429c532841ecb12e9230ea66564ad3ed704df')
    'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16.c' = @(38271, 'c18d6664d586cca85d551e23cb62f9e44733451519f1155615b2660ae97724c4')
    'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16_identity_anchor.h' = @(1338, 'e0a8406850afe633f086e18ca938bed72f5b21ad3119b616c868478563efda23')
    'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16.obj' = @(48716, '0fce463d11a8e6b372bbf42c6ee55a852187757cb3e284c71af8cce83d2b6390')
    'tools\native\kira_r25_afes_contract_lock_diagnostic_v3r16.exe' = @(164864, '621fbf7fa635e475e6186530b9ae6d6e05e78856d679db0f07f8d555895ac76d')
    'Testing\test_kira_r25_foundation_afes_contract_lock_diagnostic_v3r16_static.ps1' = @(17970, '3227c11a38ab7b5e716b2386a014e40e0ca061bbed2fc7051ff1dce9963b9408')
    'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\RUNTIME_CONTROL_CHECKPOINT.md' = @(2345, '44a174e107baa9f119e1b8a391833d2d3fb78cfd2c15d91b7bbff6c4683d1128')
    'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\BUILD_AND_STATIC_TEST_RESULTS.txt' = @(2250, 'a362925de68b08738920e258e70079168d4dabb1cc5563f25ff5fea1c2f7ba2a')
    'RecoverySprint\continuation_20260810\kira_r25_afes_contract_lock_diagnostic_v3r16_static_preparation\attempt_01\STATIC_SEAL_MANIFEST.json' = @(5213, '434a2e11bb574e299136188556fafab8e5f709b05025d0a15cba1c25b3820234')
}
foreach ($relative in $checkpointSeal.Keys) {
    $path = Join-Path $root $relative
    $expected = $checkpointSeal[$relative]
    $item = Get-Item -LiteralPath $path
    $sha = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    Check ($item.Length -eq $expected[0]) "checkpoint-seal-bytes:$relative"
    Check ($sha -ceq $expected[1]) "checkpoint-seal-sha256:$relative"
}

# Also show whether the current inner manifest is self-consistent. This cannot
# repair or replace a mismatch against the earlier outer checkpoint seal.
foreach ($artifact in $seal.artifacts) {
    $path = Join-Path $root ($artifact.path.Replace('/', '\'))
    $exists = Test-Path -LiteralPath $path -PathType Leaf
    Check $exists "seal-present:$($artifact.path)"
    if ($exists) {
        $item = Get-Item -LiteralPath $path
        $sha = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        Check ($item.Length -eq $artifact.bytes) "seal-bytes:$($artifact.path)"
        Check ($sha -ceq $artifact.sha256) "seal-sha256:$($artifact.path)"
    }
}

$source = [IO.File]::ReadAllText($sourcePath, [Text.UTF8Encoding]::new($false, $true))

# Audit binding is exact and must point at the evidence path authorized for this review.
Check ($source.Contains($requiredAuditLiteral)) 'audit-binding-required-20260811-path'
Check ($source.Contains('sidecar_bytes != SHA_HEX + 1U')) 'audit-sidecar-exact-length'
Check ($source.Contains('sidecar[SHA_HEX] != ''\n''')) 'audit-sidecar-newline'
Check ($source.Contains('memcmp(sidecar, audit_hex, SHA_HEX) != 0')) 'audit-sidecar-binds-tsv'
Check ($source.Contains('values[1][0] == ''\0'' || strcmp(values[1], values[2]) == 0')) 'audit-different-nonempty-auditor'
Check ($source.Contains('if (cursor != end')) 'audit-rejects-trailing-records'

# CREATE_NEW one-shot reservation must precede diagnosis and bind both handles.
$reserveAt = $source.IndexOf('reserve_outputs(&evidence, &receipt', [StringComparison]::Ordinal)
$diagnoseAt = $source.IndexOf('diagnostic_ok = diagnose_contract(&terminal);', [StringComparison]::Ordinal)
Check ($reserveAt -ge 0 -and $diagnoseAt -gt $reserveAt) 'reserve-before-diagnostic'
Check ((Count-Literal $source 'NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |') -eq 2) 'two-create-new-write-through-reservations'
Check ($source.Contains('final_path_matches(evidence, EVIDENCE_PATH)')) 'evidence-exact-final-path'
Check ($source.Contains('final_path_matches(receipt, OUTCOME_PATH)')) 'receipt-exact-final-path'
Check ($source.Contains('get_file_identity(evidence, evidence_identity)')) 'evidence-file-id-captured'
Check ($source.Contains('get_file_identity(receipt, receipt_identity)')) 'receipt-file-id-captured'

# One target handle, granular first-failure gates, broad diagnostic sharing, two snapshots.
Check ((Count-Literal $source 'CreateFileW(V3R15_TARGET_CONTRACT_PATH, GENERIC_READ,') -eq 1) 'one-target-open'
Check ($source.Contains('FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING,')) 'diagnostic-share-mask-exact'
Check ((Count-Literal $source 'hash_handle_bytes(target, record->snapshot_one_sha256') -eq 1) 'snapshot-one-on-target-handle'
Check ((Count-Literal $source 'hash_handle_bytes(target, record->snapshot_two_sha256') -eq 1) 'snapshot-two-on-target-handle'
foreach ($gate in @('GATE_TARGET_OPEN','GATE_ATTRIBUTES','GATE_SIZE_FIRST','GATE_FINAL_PATH_FIRST','GATE_FILE_ID_FIRST','GATE_SNAPSHOT_ONE','GATE_SIZE_SECOND','GATE_FINAL_PATH_SECOND','GATE_FILE_ID_SECOND','GATE_SNAPSHOT_TWO','GATE_SIZE_FINAL','GATE_FINAL_PATH_FINAL','GATE_FILE_ID_FINAL','GATE_SNAPSHOT_EQUALITY')) {
    Check ($source.Contains($gate)) "granular-gate:$gate"
}
Check ($source.Contains('same_identity(&first_identity, &second_identity)')) 'same-handle-second-identity'
Check ($source.Contains('same_identity(&first_identity, &final_identity)')) 'same-handle-final-identity'
Check ($source.Contains('memcmp(record->snapshot_one_sha256, record->snapshot_two_sha256, SHA_BYTES)')) 'snapshots-equal'
Check ($source.Contains('memcmp(record->snapshot_one_sha256, record->expected_target_sha256, SHA_BYTES)')) 'snapshot-matches-sealed-digest'

# Durable pending + terminal evidence and receipt, exact readback, no trailing bytes.
Check ((Count-Literal $source 'FlushFileBuffers(evidence)') -ge 2) 'evidence-flushed-pending-and-terminal'
Check ((Count-Literal $source 'FlushFileBuffers(receipt)') -ge 2) 'receipt-flushed-pending-and-terminal'
Check ($source.Contains('sha_buffer(pending, (ULONG)sizeof(*pending), terminal->pending_record_sha256)')) 'terminal-binds-pending-receipt'
Check ($source.Contains('hash_handle_bytes(evidence, terminal->evidence_sha256')) 'terminal-binds-final-evidence'
Check ($source.Contains('memcmp(pending, &pending_readback')) 'pending-readback-exact'
Check ($source.Contains('memcmp(terminal, &terminal_readback')) 'terminal-readback-exact'
Check ($source.Contains('receipt_bytes != sizeof(*pending) + sizeof(*terminal)')) 'receipt-two-record-exact-size'
Check ($source.Contains('trailing_bytes != 0U')) 'trailing-bytes-rejected'
Check ($source.Contains('written == length')) 'partial-write-rejected'

# Reparse/path/readback failures stop; no Python/controller/AFES/Blender/process stage.
Check ((Count-Literal $source 'FILE_FLAG_OPEN_REPARSE_POINT') -ge 6) 'reparse-open-policy-present'
Check ($source.Contains('(attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0U')) 'output-parent-reparse-refused'
Check ($source.Contains('SetLastError(ERROR_INVALID_NAME)')) 'path-mismatch-error-code'
Check ($source.Contains('error == ERROR_SUCCESS ? ERROR_INVALID_DATA : error')) 'zero-error-normalized-fail-closed'
foreach ($forbidden in @('LoadLibrary','GetProcAddress','Py_Initialize','PyConfig_','python314.dll','CreateProcess','ShellExecute','WinExec','blender.exe','foundation.blend','_build_execution_plan')) {
    Check (-not $source.Contains($forbidden)) "forbidden-source:$forbidden"
}

$bytes = [IO.File]::ReadAllBytes($exePath)
Check ($bytes.Length -gt 1024 -and $bytes[0] -eq 0x4d -and $bytes[1] -eq 0x5a) 'pe-mz'
$peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
Check ($peOffset -gt 0 -and [BitConverter]::ToUInt16($bytes, $peOffset + 4) -eq 0x8664) 'pe-x64'
Check ([BitConverter]::ToUInt16($bytes, $peOffset + 24) -eq 0x20b) 'pe32-plus'
$ascii = [Text.Encoding]::ASCII.GetString($bytes)
foreach ($forbidden in @('python314.dll','blender.exe','CreateProcessW','ShellExecuteW')) {
    Check (-not $ascii.Contains($forbidden)) "forbidden-pe:$forbidden"
}
Check ($ascii.Contains('BCryptFinishHash')) 'pe-bcrypt-hash-import'

Check (-not (Test-Path -LiteralPath $runtimeEvidence)) 'runtime-evidence-absent'
Check (-not (Test-Path -LiteralPath $runtimeReceipt)) 'runtime-receipt-absent'
Check (-not (Test-Path -LiteralPath $candidateAudit)) 'candidate-expected-audit-tsv-absent'
Check (-not (Test-Path -LiteralPath $candidateAuditDigest)) 'candidate-expected-audit-digest-absent'

Write-Host ("V3R16_INDEPENDENT_STATIC run={0} failed={1}" -f $script:run, $script:failed)
if ($script:failed -ne 0) { exit 1 }
