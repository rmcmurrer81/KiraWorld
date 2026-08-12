$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$SourcePath = Join-Path $Root 'tools\native\kira_r25_afes_native_outcome_reservation_v3r14.c'
$HeaderPath = Join-Path $Root 'tools\native\kira_r25_afes_native_outcome_reservation_v3r14_identity_anchor.h'
$ExePath = Join-Path $Root 'tools\native\kira_r25_afes_native_outcome_reservation_v3r14.exe'
$Source = Get-Content -Raw -LiteralPath $SourcePath
$Header = Get-Content -Raw -LiteralPath $HeaderPath
$script:Ran = 0
$script:Failed = 0

function Check([bool]$Condition, [string]$Name) {
    $script:Ran++
    if ($Condition) {
        Write-Host "PASS`t$Name"
    } else {
        $script:Failed++
        Write-Host "FAIL`t$Name"
    }
}

function Exact-Count([string]$Text, [string]$Needle) {
    return ([regex]::Matches($Text, [regex]::Escape($Needle))).Count
}

function Macro-Hash([string]$Name) {
    $match = [regex]::Match(
        $Header,
        "(?m)^#define\s+$Name`_SHA256\s+\`"([0-9a-f]{64})\`"\s*$"
    )
    if (-not $match.Success) { throw "missing hash macro $Name" }
    return $match.Groups[1].Value
}

function Macro-Bytes([string]$Name) {
    $match = [regex]::Match(
        $Header,
        "(?m)^#define\s+$Name`_BYTES\s+([0-9]+)ULL\s*$"
    )
    if (-not $match.Success) { throw "missing bytes macro $Name" }
    return [uint64]$match.Groups[1].Value
}

function Check-BoundSubject([string]$Name, [string]$Relative) {
    $path = Join-Path $Root $Relative
    $item = Get-Item -LiteralPath $path
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    Check ($item.Length -eq (Macro-Bytes $Name)) "$Name exact bytes"
    Check ($hash -ceq (Macro-Hash $Name)) "$Name exact SHA-256"
}

function Test-AuditText([string]$Text) {
    $keys = @(
        'decision',
        'auditor',
        'author',
        'native_executable_sha256',
        'identity_anchor_sha256',
        'contract_sha256',
        'native_source_sha256',
        'static_test_sha256',
        'runtime_control_checkpoint_sha256',
        'v3r13_run_evidence_sha256',
        'v3r13_audit_checkpoint_sha256',
        'v3r13_one_shot_authority_sha256',
        'v3r13_independent_audit_sha256',
        'v3r13_post_success_checkpoint_sha256',
        'retained_manifest_sha256'
    )
    if (-not $Text.EndsWith("`n") -or $Text.Contains("`r") -or $Text.Contains([char]0)) {
        return $false
    }
    $lines = $Text.Substring(0, $Text.Length - 1) -split "`n"
    if ($lines.Count -ne 16 -or
        $lines[0] -cne "KIRA_R25_AFES_NATIVE_OUTCOME_RESERVATION_AUDIT_V3R14`t1") {
        return $false
    }
    $values = @{}
    for ($i = 0; $i -lt $keys.Count; $i++) {
        $parts = $lines[$i + 1] -split "`t", -1
        if ($parts.Count -ne 2 -or $parts[0] -cne $keys[$i] -or $parts[1].Length -eq 0) {
            return $false
        }
        $values[$parts[0]] = $parts[1]
    }
    if ($values['decision'] -cne 'ACCEPTED_FOR_ONE_BOUNDED_NATIVE_OUTCOME_RESERVATION_ONLY' -or
        $values['author'] -cne 'codex_r25_afes_v3r14_static_author' -or
        $values['auditor'] -ceq $values['author']) {
        return $false
    }
    foreach ($key in $keys[3..($keys.Count - 1)]) {
        if ($values[$key] -cnotmatch '^[0-9a-f]{64}$') { return $false }
    }
    return $true
}

function Test-ReceiptPair(
    [byte[]]$Reservation,
    [byte[]]$Completion,
    [uint32]$ReservationState,
    [uint32]$CompletionState,
    [byte[]]$BoundReservationHash,
    [int]$ExtraBytes
) {
    if ($Reservation.Length -eq 0 -or $Completion.Length -eq 0 -or
        $ReservationState -ne 1 -or $CompletionState -ne 2 -or
        $ExtraBytes -ne 0) {
        return $false
    }
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        [byte[]]$actual = $hasher.ComputeHash($Reservation)
    } finally {
        $hasher.Dispose()
    }
    if ($actual.Length -ne $BoundReservationHash.Length) {
        return $false
    }
    for ($index = 0; $index -lt $actual.Length; $index++) {
        if ($actual[$index] -ne $BoundReservationHash[$index]) {
            return $false
        }
    }
    return $true
}

Check ($Source -match 'KIRA_R25_AFES_NATIVE_OUTCOME_RESERVATION_AUDIT_V3R14\\t1') 'canonical v3r14 audit magic'
Check ($Source -match 'kira\.r25\.afes\.v3r14\.native_stage\.v1') 'v3r14 evidence schema'
Check ($Source -match 'argc != 1') 'zero caller arguments only'
Check ($Source -match 'wcscmp\(current_directory, PROJECT_ROOT\) != 0') 'exact working-directory gate'
Check ($Source -match 'wcscmp\(module_path, SELF_PATH\) != 0') 'exact self-image path gate'
Check ($Source -match 'V3R14_V3R13_RUN_EVIDENCE_SHA256') 'consumed v3r13 success evidence is compile-time bound'
Check ($Source -match 'V3R14_V3R13_AUDIT_CHECKPOINT_SHA256') 'v3r13 accepted audit checkpoint is bound'
Check ($Source -match 'V3R14_V3R13_ONE_SHOT_AUTHORITY_SHA256') 'consumed v3r13 authority is bound'
Check ($Source -match 'V3R14_V3R13_INDEPENDENT_AUDIT_SHA256') 'v3r13 audit TSV is bound'
Check ($Source -match 'V3R14_V3R13_POST_SUCCESS_CHECKPOINT_SHA256') 'v3r13 success checkpoint is bound'
Check ($Source -match 'V3R14_RETAINED_MANIFEST_SHA256') 'retained manifest is bound'
Check ($Source -match 'strcmp\(values\[1\], values\[2\]\) == 0') 'fresh auditor must differ from author'
Check ($Source -match 'sidecar_bytes != SHA256_HEX_BYTES \+ 1U') 'audit digest sidecar has exact bounded length'
Check ($Source -match 'cursor != end') 'audit parser rejects trailing content'
Check ((Exact-Count $Source 'CREATE_NEW,') -eq 2) 'exact two create-new runtime files'
Check ((Exact-Count $Source 'FILE_FLAG_WRITE_THROUGH') -eq 2) 'both runtime files are write-through'
Check ($Source -match 'RUN_EVIDENCE_PATH[\s\S]*CREATE_NEW') 'evidence is create-new'
Check ($Source -match 'OUTCOME_RECEIPT_PATH[\s\S]*CREATE_NEW') 'outcome receipt is create-new'
Check ($Source -notmatch '\bDeleteFile[AW]?\s*\(') 'no receipt deletion path'
Check ($Source -notmatch '\bMoveFile(?:Ex)?[AW]?\s*\(') 'no receipt move or replacement path'
Check ($Source -notmatch '\bReplaceFile[AW]?\s*\(') 'no receipt replacement path'
Check ($Source -notmatch 'CREATE_ALWAYS|OPEN_ALWAYS|TRUNCATE_EXISTING') 'no overwrite or truncate disposition'
Check ($Source -match 'RESERVATION_STATE_PENDING_READBACK 1U') 'reservation state is pending readback only'
Check ($Source -match 'COMPLETION_STATE_READBACK_VERIFIED 2U') 'completion state is readback verified'
Check ((Exact-Count $Source 'WriteFile(') -eq 3) 'only evidence helper and two receipt WriteFile sites'
Check (([regex]::Matches($Source, 'WriteFile\(\s*receipt,\s*&reservation')).Count -eq 1) 'one reservation-record write'
Check (([regex]::Matches($Source, 'WriteFile\(\s*receipt,\s*&completion')).Count -eq 1) 'one completion-record write'
Check ($Source -match 'written != \(DWORD\)sizeof\(reservation\)') 'partial reservation write fails'
Check ($Source -match 'written != \(DWORD\)sizeof\(completion\)') 'partial completion write fails'
Check ($Source -match 'memcmp\(&reservation, &reservation_readback, sizeof\(reservation\)\) != 0') 'reservation exact-byte readback gate'
Check ($Source -match 'same_file_identity\(&receipt_identity_before, &receipt_identity_after\)') 'receipt stable identity is rechecked'
Check ($Source -match 'GetFinalPathNameByHandleW\(') 'new output handles use normalized final-path verification'
Check ((Exact-Count $Source 'final_path_matches(') -eq 3) 'final-path verifier has exactly one definition and two call sites'
Check ($Source -match 'final_path_matches\(receipt, OUTCOME_RECEIPT_PATH\)') 'receipt handle proves exact final path'
Check ($Source -match 'final_path_matches\(evidence, RUN_EVIDENCE_PATH\)') 'evidence handle proves exact final path'
Check ($Source -match 'sha256_memory\([\s\S]*reservation_sha256') 'completion binds reservation-record hash'
Check ($Source -match 'file_size\.QuadPart !=[\s\S]*sizeof\(reservation\) \+ sizeof\(completion\)') 'final receipt exact size gate'
Check ($Source -match 'extra_read != 0U') 'final receipt rejects trailing byte'
Check ($Source -match 'memcmp\(&completion, &completion_readback, sizeof\(completion\)\) != 0') 'completion exact-byte readback gate'
Check ($Source.IndexOf('append_evidence(evidence, EVIDENCE_RESERVATION_READBACK)') -lt $Source.IndexOf('completion.state = COMPLETION_STATE_READBACK_VERIFIED')) 'completion state occurs after reservation-readback evidence append'
Check ($Source -match 'EVIDENCE_TERMINAL[\s\S]*no_python_controller_afes_blender_body') 'terminal truth remains narrow'
Check ((Exact-Count $Source 'CreateProcessW(') -eq 0) 'no child or Blender process creation'
Check ($Source -notmatch '\bLoadLibrary(?:Ex)?[AW]?\s*\(') 'no application DLL loading'
Check ($Source -notmatch '\bGetProcAddress\s*\(') 'no application dynamic symbol resolution'
Check ($Source -notmatch '\bPy_[A-Za-z0-9_]*\s*\(') 'no Python API call'
Check ($Source -notmatch '\bbpy\.|--background|blender\.exe') 'no Blender invocation surface'
Check ($Source -notmatch '\bAFES_[A-Za-z0-9_]*\s*\(') 'no AFES invocation surface'

Check-BoundSubject 'V3R14_CONTRACT' 'Avatar\avatar_builder\body_systems\kira_r25_foundation_afes_native_outcome_reservation_v3r14.json'
Check-BoundSubject 'V3R14_SOURCE' 'tools\native\kira_r25_afes_native_outcome_reservation_v3r14.c'
Check-BoundSubject 'V3R14_STATIC_TEST' 'Testing\test_kira_r25_foundation_afes_native_outcome_reservation_v3r14_static.ps1'
Check-BoundSubject 'V3R14_CONTROL_CHECKPOINT' 'RecoverySprint\continuation_20260810\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\attempt_01\RUNTIME_CONTROL_CHECKPOINT.md'
Check-BoundSubject 'V3R14_V3R13_RUN_EVIDENCE' 'RecoverySprint\continuation_20260810\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r13_static_preparation\attempt_01\RUN_EVIDENCE.jsonl'
Check-BoundSubject 'V3R14_V3R13_AUDIT_CHECKPOINT' 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r13_fresh_static_audit\attempt_01\CHECKPOINT.md'
Check-BoundSubject 'V3R14_V3R13_ONE_SHOT_AUTHORITY' 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r13_fresh_static_audit\attempt_01\ONE_SHOT_AUTHORITY.txt'
Check-BoundSubject 'V3R14_V3R13_INDEPENDENT_AUDIT' 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r13_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.tsv'
Check-BoundSubject 'V3R14_V3R13_POST_SUCCESS_CHECKPOINT' 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r13_consumed_success_postmortem\attempt_01\CHECKPOINT.md'
Check-BoundSubject 'V3R14_RETAINED_MANIFEST' 'RecoverySprint\continuation_20260809\kira_r25_foundation_afes_locked_pair_execution_static_preparation\attempt_03r9\RETAINED_NATIVE_LOCK_MANIFEST.tsv'

$hashA = 'a' * 64
$hashB = 'b' * 64
$hashC = 'c' * 64
$hashD = 'd' * 64
$hashE = 'e' * 64
$hashF = 'f' * 64
$hash0 = '0' * 64
$hash1 = '1' * 64
$hash2 = '2' * 64
$hash3 = '3' * 64
$hash4 = '4' * 64
$hash5 = '5' * 64
$auditLines = @(
    "KIRA_R25_AFES_NATIVE_OUTCOME_RESERVATION_AUDIT_V3R14`t1",
    "decision`tACCEPTED_FOR_ONE_BOUNDED_NATIVE_OUTCOME_RESERVATION_ONLY",
    "auditor`tfresh_other_agent",
    "author`tcodex_r25_afes_v3r14_static_author",
    "native_executable_sha256`t$hashA",
    "identity_anchor_sha256`t$hashB",
    "contract_sha256`t$hashC",
    "native_source_sha256`t$hashD",
    "static_test_sha256`t$hashE",
    "runtime_control_checkpoint_sha256`t$hashF",
    "v3r13_run_evidence_sha256`t$hash0",
    "v3r13_audit_checkpoint_sha256`t$hash1",
    "v3r13_one_shot_authority_sha256`t$hash2",
    "v3r13_independent_audit_sha256`t$hash3",
    "v3r13_post_success_checkpoint_sha256`t$hash4",
    "retained_manifest_sha256`t$hash5"
)
$exactAudit = ($auditLines -join "`n") + "`n"
Check (Test-AuditText $exactAudit) 'reference audit gate accepts exact canonical audit'
Check (-not (Test-AuditText ($exactAudit + "extra`tx`n"))) 'reference audit gate rejects trailing row'
Check (-not (Test-AuditText $exactAudit.Replace("`n", "`r`n"))) 'reference audit gate rejects CRLF'
Check (-not (Test-AuditText $exactAudit.TrimEnd("`n"))) 'reference audit gate requires final LF'
Check (-not (Test-AuditText $exactAudit.Replace('fresh_other_agent', 'codex_r25_afes_v3r14_static_author'))) 'reference audit gate rejects same author/auditor'
Check (-not (Test-AuditText $exactAudit.Replace($hashA, $hashA.ToUpperInvariant()))) 'reference audit gate rejects uppercase hash'
Check (-not (Test-AuditText $exactAudit.Replace("decision`tACCEPTED", "decision`tREJECTED"))) 'reference audit gate rejects wrong decision'

[byte[]]$reservation = [Text.Encoding]::ASCII.GetBytes('reservation-record')
[byte[]]$completion = [Text.Encoding]::ASCII.GetBytes('completion-record')
$sha256 = [Security.Cryptography.SHA256]::Create()
try {
    [byte[]]$reservationHash = $sha256.ComputeHash($reservation)
} finally {
    $sha256.Dispose()
}
[byte[]]$wrongHash = [byte[]]::new(32)
Check (Test-ReceiptPair $reservation $completion 1 2 $reservationHash 0) 'reference receipt gate accepts exact pair'
Check (-not (Test-ReceiptPair $reservation ([byte[]]::new(0)) 1 2 $reservationHash 0)) 'reference receipt gate rejects missing completion'
Check (-not (Test-ReceiptPair $reservation $completion 0 2 $reservationHash 0)) 'reference receipt gate rejects wrong reservation state'
Check (-not (Test-ReceiptPair $reservation $completion 1 1 $reservationHash 0)) 'reference receipt gate rejects premature completion state'
Check (-not (Test-ReceiptPair $reservation $completion 1 2 $wrongHash 0)) 'reference receipt gate rejects reservation hash mismatch'
Check (-not (Test-ReceiptPair $reservation $completion 1 2 $reservationHash 1)) 'reference receipt gate rejects trailing bytes'

$futureAudit = Join-Path $Root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r14_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.tsv'
$futureDigest = Join-Path $Root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r14_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.sha256'
$runtimeEvidence = Join-Path $Root 'RecoverySprint\continuation_20260810\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\attempt_01\RUN_EVIDENCE.jsonl'
$runtimeOutcome = Join-Path $Root 'RecoverySprint\continuation_20260810\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\attempt_01\NATIVE_DIAGNOSTIC_OUTCOME.receipt.bin'
Check (-not (Test-Path -LiteralPath $futureAudit)) 'author did not create future audit'
Check (-not (Test-Path -LiteralPath $futureDigest)) 'author did not create future audit digest'
Check (-not (Test-Path -LiteralPath $runtimeEvidence)) 'v3r14 runtime evidence remains absent'
Check (-not (Test-Path -LiteralPath $runtimeOutcome)) 'v3r14 outcome receipt remains absent'

Check (Test-Path -LiteralPath $ExePath) 'compiled candidate exists'
if (Test-Path -LiteralPath $ExePath) {
    $pe = [IO.File]::ReadAllBytes($ExePath)
    $peOffset = [BitConverter]::ToInt32($pe, 0x3c)
    Check ($pe[0] -eq 0x4d -and $pe[1] -eq 0x5a -and
        [BitConverter]::ToUInt32($pe, $peOffset) -eq 0x00004550) 'compiled candidate has valid PE signatures'
    Check ([BitConverter]::ToUInt16($pe, $peOffset + 4) -eq 0x8664) 'compiled candidate is x64'
    $ascii = [Text.Encoding]::ASCII.GetString($pe)
    Check ($ascii -notmatch '(?i)python[0-9]*\.dll|blender\.exe') 'compiled string/import surface has no Python or Blender image'
}

Write-Host "RAN`t$script:Ran"
Write-Host "FAILED`t$script:Failed"
if ($script:Failed -ne 0) { exit 1 }
