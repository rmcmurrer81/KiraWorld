param(
    [ValidateSet('PreBuild', 'PostBuild', 'PostSeal')]
    [string]$Phase = 'PostSeal'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$KiraRoot = 'C:\Users\robmc\Kira'
$Source = Join-Path $Root 'tools\native\kira_blackwell_voice_control_anchor_v17.c'
$Header = Join-Path $Root 'tools\native\kira_blackwell_voice_control_anchor_v17_identity_anchor.h'
$Candidate = Join-Path $Root 'tools\native\kira_blackwell_voice_control_anchor_v17.exe'
$Seal = Join-Path $Root 'RecoverySprint\continuation_20260811\blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation\attempt_01\STATIC_SEAL_MANIFEST.json'
$Harness = Join-Path $Root 'Testing\native\kira_blackwell_voice_control_anchor_v17_parser_hostile.exe'
$Evidence = Join-Path $Root 'RecoverySprint\continuation_20260811\blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation\attempt_01\RUN_EVIDENCE_V17.jsonl'
$Outcome = Join-Path $Root 'RecoverySprint\continuation_20260811\blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation\attempt_01\STATIC_CONTROL_OUTCOME_V17.receipt.bin'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-LowerSha256([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-SourceContract([string]$Text) {
    $Required = @(
        'if (input.cursor != input.end) return 0; /* V17_FINAL_EOF_PREDICATE */',
        'if (actual_object_count != expected_count) return 0; /* V17_ACTUAL_OBJECT_COUNT_PREDICATE */',
        'if (matched[match_index] != 0U) return 0; /* V17_PARSED_PATH_UNIQUENESS_PREDICATE */',
        'if (match_index != actual_object_count) return 0; /* V17_EXPECTED_SET_EQUALITY_PREDICATE */',
        'value[segment_start + 1U] == ''.'')) return 0; /* V17_SEGMENT_DOT_REFUSAL_PREDICATE */',
        'if (!manifest_consume(&input, canonical_prefix)) return 0; /* V17_PROVENANCE_PREDICATE */',
        'KIRA_BLACKWELL_VOICE_V17_WHOLE_DOCUMENT_CONTROL_AUDIT\t1',
        'ACCEPTED_FOR_ONE_BOUNDED_DISCONNECTED_STATIC_CONTROL_VALIDATION_V17_ONLY',
        'KIRA_BLACKWELL_V17_RESERVATION',
        'KIRA_BLACKWELL_V17_TERMINAL',
        'RUN_EVIDENCE_V17.jsonl',
        'STATIC_CONTROL_OUTCOME_V17.receipt.bin',
        'blackwell_v17_native_whole_document_manifest_control_anchor_fresh_static_audit',
        'blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation',
        '#define V17_SEALED_SUBJECT_COUNT 55U',
        '#define V17_SEALED_SUBJECT_COUNT_TEXT "55"'
    )
    foreach ($Needle in $Required) {
        if (-not $Text.Contains($Needle)) { return $false }
    }
    $Forbidden = @(
        'KIRA_BLACKWELL_V15_RESERVATION',
        'KIRA_BLACKWELL_V15_TERMINAL',
        'blackwell_v17_native_exact_manifest_row_control_anchor',
        'complete V15 static seal'
    )
    foreach ($Needle in $Forbidden) {
        if ($Text.Contains($Needle)) { return $false }
    }
    return $true
}

function Test-CanonicalManifestPath([string]$Path) {
    if ($Path -ceq 'C:/Python314/python314.dll') { return $true }
    if ([string]::IsNullOrEmpty($Path) -or $Path.StartsWith('/') -or
        $Path.EndsWith('/') -or $Path.Contains('\') -or $Path.Contains(':')) {
        return $false
    }
    foreach ($Character in $Path.ToCharArray()) {
        $Code = [int][char]$Character
        if ($Code -lt 0x20 -or $Code -gt 0x7e -or $Character -eq '"') { return $false }
    }
    foreach ($Segment in $Path.Split('/')) {
        if ($Segment.Length -eq 0 -or $Segment -ceq '.' -or $Segment -ceq '..') {
            return $false
        }
    }
    return $true
}

foreach ($RequiredPath in @($Source, $Header, $Candidate, $Seal, $Harness)) {
    Assert-True (Test-Path -LiteralPath $RequiredPath -PathType Leaf) "missing $RequiredPath"
}
Assert-True (-not (Test-Path -LiteralPath $Evidence)) 'V17 run evidence must remain absent'
Assert-True (-not (Test-Path -LiteralPath $Outcome)) 'V17 outcome receipt must remain absent'

$SourceText = [IO.File]::ReadAllText($Source)
Assert-True (Test-SourceContract $SourceText) 'exact V17 source contract failed'

$PredicateMutations = @(
    'if (input.cursor != input.end) return 0; /* V17_FINAL_EOF_PREDICATE */',
    'if (actual_object_count != expected_count) return 0; /* V17_ACTUAL_OBJECT_COUNT_PREDICATE */',
    'if (matched[match_index] != 0U) return 0; /* V17_PARSED_PATH_UNIQUENESS_PREDICATE */',
    'if (match_index != actual_object_count) return 0; /* V17_EXPECTED_SET_EQUALITY_PREDICATE */',
    'value[segment_start + 1U] == ''.'')) return 0; /* V17_SEGMENT_DOT_REFUSAL_PREDICATE */',
    'if (!manifest_consume(&input, canonical_prefix)) return 0; /* V17_PROVENANCE_PREDICATE */'
)
foreach ($Predicate in $PredicateMutations) {
    $Mutant = $SourceText.Replace($Predicate, '')
    Assert-True (-not (Test-SourceContract $Mutant)) "source predicate mutant survived: $Predicate"
}

$SealBytes = [IO.File]::ReadAllBytes($Seal)
$SealText = [Text.Encoding]::UTF8.GetString($SealBytes)
Assert-True (-not $SealText.Contains("`r") -and -not $SealText.Contains("`n") -and
    -not $SealText.Contains("`t")) 'canonical seal contains JSON whitespace'
$Parsed = $SealText | ConvertFrom-Json
Assert-True ($Parsed.schema -ceq 'kira.blackwell.v17.native_whole_document_manifest_control_anchor.static_seal.v1') 'wrong V17 seal schema'
Assert-True ($Parsed.candidate_id -ceq 'kira_chatterbox_blackwell_native_whole_document_manifest_control_anchor_candidate_v17') 'wrong V17 candidate id'
Assert-True ($Parsed.repair_id -ceq 'V16_WHOLE_DOCUMENT_CANONICAL_SET_EQUALITY_REPAIR') 'wrong V17 repair id'
Assert-True (($Parsed.sealed_subject_count -is [int] -or $Parsed.sealed_subject_count -is [long]) -and $Parsed.sealed_subject_count -eq 55) 'declared count/type is not exact'
Assert-True ($Parsed.subjects.Count -eq 55) 'actual subject count is not 55'
Assert-True (($Parsed.subjects.path | Select-Object -Unique).Count -eq 55) 'subject paths are not unique'

$LowerHex = '^[0-9a-f]{64}$'
foreach ($Row in $Parsed.subjects) {
    Assert-True ($Row.path -is [string] -and (Test-CanonicalManifestPath $Row.path)) "noncanonical path: $($Row.path)"
    Assert-True (($Row.bytes -is [int] -or $Row.bytes -is [long]) -and $Row.bytes -gt 0) "wrong byte type/value: $($Row.path)"
    Assert-True ($Row.sha256 -is [string] -and $Row.sha256 -cmatch $LowerHex) "wrong digest: $($Row.path)"
    if ($Row.path -ceq 'C:/Python314/python314.dll') {
        $Actual = 'C:\Python314\python314.dll'
    } elseif ($Row.path -like '*v17*' -and
        ($Row.path.StartsWith('tools/native/') -or $Row.path.StartsWith('Voice/sidecars/'))) {
        $Actual = Join-Path $Root ($Row.path.Replace('/', '\'))
    } else {
        $Actual = Join-Path $KiraRoot ($Row.path.Replace('/', '\'))
    }
    Assert-True (Test-Path -LiteralPath $Actual -PathType Leaf) "sealed subject absent: $($Row.path)"
    Assert-True ((Get-Item -LiteralPath $Actual).Length -eq [long]$Row.bytes) "sealed byte mismatch: $($Row.path)"
    Assert-True ((Get-LowerSha256 $Actual) -ceq $Row.sha256) "sealed hash mismatch: $($Row.path)"
}

$V16SealPath = Join-Path $KiraRoot 'RecoverySprint\continuation_20260811\blackwell_v16_native_exact_manifest_row_control_anchor_static_preparation\attempt_01\STATIC_SEAL_MANIFEST.json'
$V16 = Get-Content -Raw -LiteralPath $V16SealPath | ConvertFrom-Json
Assert-True ($V16.subjects.Count -eq 41) 'preserved V16 author seal no longer has 41 rows'
foreach ($V16Row in $V16.subjects) {
    $Match = @($Parsed.subjects | Where-Object { $_.path -ceq $V16Row.path })
    Assert-True ($Match.Count -eq 1) "V16 subject not bound exactly once: $($V16Row.path)"
    Assert-True ([long]$Match[0].bytes -eq [long]$V16Row.bytes -and
        $Match[0].sha256 -ceq $V16Row.sha256) "V16 subject binding changed: $($V16Row.path)"
}

$ExpectedV16Closure = @(
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json',
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/AUDIT_DECISION.json',
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/CHECKPOINT.md',
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/PARSER_PROBE_RESULTS.txt',
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/REVIEW_PROBES.md',
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv',
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.sha256',
    'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/CLOSURE_REHASH.tsv'
)
foreach ($Path in $ExpectedV16Closure) {
    Assert-True (@($Parsed.subjects | Where-Object { $_.path -ceq $Path }).Count -eq 1) "missing V16 rejection closure row: $Path"
}

$HarnessOutput = @(& $Harness 2>&1)
Assert-True ($LASTEXITCODE -eq 0) 'compiled exact-parser hostile harness failed'
Assert-True (@($HarnessOutput | Where-Object { $_ -ceq "SUMMARY`tchecks=83`tfailures=0" }).Count -eq 1) 'compiled hostile summary mismatch'
Assert-True (@($HarnessOutput | Where-Object { $_ -like 'FAIL*' }).Count -eq 0) 'compiled hostile harness reported failure'

Write-Output "V17_WHOLE_DOCUMENT_MANIFEST_HOSTILE_STATIC_TESTS_PASS phase=$Phase compiled_checks=83 source_mutants=6 sealed_subjects=55"
