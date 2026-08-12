param(
    [ValidateSet('PreBuild', 'PostBuild', 'PostSeal')]
    [string]$Phase = 'PreBuild'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$kira = 'C:\Users\robmc\Kira'
$prep = 'RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_static_preparation/attempt_01'
$diagnostic = 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_consumed_failure_diagnostic/attempt_01'
$v15Prep = 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01'
$v15Audit = 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_fresh_static_audit/attempt_01'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Count-Ordinal([string]$Text, [string]$Needle) {
    if ([string]::IsNullOrEmpty($Needle)) { return 0 }
    $count = 0
    $at = 0
    while (($at = $Text.IndexOf($Needle, $at, [StringComparison]::Ordinal)) -ge 0) {
        $count++
        $at += $Needle.Length
    }
    return $count
}

function Sha([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Resolve-Subject([string]$RelativePath) {
    if ([IO.Path]::IsPathRooted($RelativePath)) { return [IO.Path]::GetFullPath($RelativePath) }
    $staged = Join-Path $root $RelativePath
    if (Test-Path -LiteralPath $staged -PathType Leaf) { return $staged }
    $retained = Join-Path $kira $RelativePath
    if (Test-Path -LiteralPath $retained -PathType Leaf) { return $retained }
    throw "subject absent: $RelativePath"
}

function Compact-Row([object]$Row) {
    $path = [string]$Row.path
    Assert-True ($path -notmatch '[\\"\x00-\x1f]' -and -not $path.StartsWith('/') -and
        -not $path.EndsWith('/') -and $path.IndexOf('//', [StringComparison]::Ordinal) -lt 0 -and
        $path.IndexOf('/./', [StringComparison]::Ordinal) -lt 0 -and
        $path.IndexOf('/../', [StringComparison]::Ordinal) -lt 0) "noncanonical row path: $path"
    $bytes = [long]$Row.bytes
    $sha = [string]$Row.sha256
    Assert-True ($bytes -gt 0 -and $sha -cmatch '^[0-9a-f]{64}$') "invalid row values: $path"
    return '{"path":"' + $path + '","bytes":' + $bytes + ',"sha256":"' + $sha + '"}'
}

$nativePath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v16.c'
$headerPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v16_identity_anchor.h'
$configPath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v16/candidate_config.json'
$contractPath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v16/native_control_contract.json'
$readmePath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v16/README.md'
$controlPath = Join-Path $root ($prep + '/RUNTIME_CONTROL_CHECKPOINT.md')
$packagePath = Join-Path $root ($prep + '/AUTHOR_PACKAGE.json')
$diagnosisPath = Join-Path $root ($diagnostic + '/READ_ONLY_DIAGNOSIS.json')
$failureCheckpointPath = Join-Path $root ($diagnostic + '/CHECKPOINT.md')
$sealPath = Join-Path $root ($prep + '/STATIC_SEAL_MANIFEST.json')
$objectPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v16.obj'
$executablePath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v16.exe'
$buildPath = Join-Path $root ($prep + '/BUILD_AND_STATIC_TEST_RESULTS.txt')

$required = @($nativePath,$configPath,$contractPath,$readmePath,$controlPath,$packagePath,
    $diagnosisPath,$failureCheckpointPath,$PSCommandPath)
foreach ($path in $required) {
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "required V16 author file absent: $path"
}
if ($Phase -ne 'PreBuild') {
    Assert-True (Test-Path -LiteralPath $headerPath -PathType Leaf) 'V16 header absent'
}

$native = [IO.File]::ReadAllText($nativePath)
$configRaw = [IO.File]::ReadAllText($configPath)
$config = $configRaw | ConvertFrom-Json
$package = [IO.File]::ReadAllText($packagePath) | ConvertFrom-Json
$diagnosis = [IO.File]::ReadAllText($diagnosisPath) | ConvertFrom-Json

Assert-True ($config.schema -eq 'kira.blackwell.v16.native_exact_manifest_row_control_anchor_config.v1') 'V16 config schema drift'
Assert-True ($config.sealed_subject_count -eq 41 -and $config.v15_authority_consumed -eq $true) 'V16 config count/consumption drift'
foreach ($name in @('production_routing_authorized','live_execution_authorized','future_harness_authoring_authorized','synthesis_authorized','playback_authorized','latency_run_authorized')) {
    Assert-True (($config.$name).GetType() -eq [bool] -and $config.$name -eq $false) "V16 authority drift: $name"
}
Assert-True ($config.different_fresh_static_audit_required.GetType() -eq [bool] -and $config.different_fresh_static_audit_required -eq $true) 'V16 audit truth drift'
Assert-True ($package.execution_authority -eq 'NONE' -and $package.candidate_invoked -eq $false -and
    $package.python_candidate_invoked -eq $false -and $package.v15_authority_consumed -eq $true -and
    $package.v15_rerun -eq $false) 'V16 author boundary drift'
Assert-True ($diagnosis.status -eq 'CONSUMED_FAILURE_DO_NOT_RERUN_V15' -and
    $diagnosis.exit_code -eq 4 -and $diagnosis.coarse_stage -eq 10 -and
    $diagnosis.run_evidence_created -eq $false -and $diagnosis.static_control_outcome_created -eq $false) 'V15 diagnosis drift'

$env:PYTHONDONTWRITEBYTECODE = '1'
$canonicalProbe = "import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); b=p.read_bytes(); strict=lambda pairs: dict(pairs) if len({k for k,v in pairs})==len(pairs) else (_ for _ in ()).throw(ValueError('duplicate')); v=json.loads(b,object_pairs_hook=strict); c=(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)+chr(10)).encode(); assert b==c; print('V16_CANONICAL_CONFIG_PASS')"
$canonicalOutput = & py -c $canonicalProbe $configPath 2>&1
Assert-True ($LASTEXITCODE -eq 0 -and ($canonicalOutput -join "`n").Contains('V16_CANONICAL_CONFIG_PASS')) "V16 canonical config failed: $canonicalOutput"

foreach ($needle in @(
    '#define V16_SEALED_SUBJECT_COUNT 41U',
    'V15_STAGE10_WHITESPACE_SENSITIVE_SEAL_ROW_FORMAT_MISMATCH',
    '{\"path\":\"%s\",\"bytes\":%llu,\"sha256\":\"%s\"}',
    'count_bytes(seal, seal_bytes, row_token, (size_t)row_length) == 1U',
    'count_bytes(seal, seal_bytes, row_prefix, sizeof(row_prefix) - 1U)',
    'v15_manifest_row_failure_closed',
    'KIRA_BLACKWELL_VOICE_V16_NATIVE_EXACT_CONTROL_AUDIT',
    'ACCEPTED_FOR_ONE_BOUNDED_DISCONNECTED_STATIC_CONTROL_VALIDATION_V16_ONLY',
    'kira_blackwell_voice_control_anchor_v15_validator.py',
    'persistent_blackwell_voice_integration_v15.py',
    'CONSUMED_FAILURE_DO_NOT_RERUN'
)) {
    Assert-True ($native.IndexOf($needle, [StringComparison]::Ordinal) -ge 0) "V16 native invariant absent: $needle"
}
foreach ($forbidden in @('window_end','"\"path\": \"%s\""','"\"bytes\": %llu"','CreateProcessW(','CreateProcessA(','ShellExecuteW(','ShellExecuteA(','WinExec(','system(','PyImport_ImportModule')) {
    Assert-True ($native.IndexOf($forbidden, [StringComparison]::Ordinal) -lt 0) "forbidden V16 native primitive/pattern: $forbidden"
}

$v15SealPath = Join-Path $kira ($v15Prep + '/STATIC_SEAL_MANIFEST.json')
$v15Raw = [IO.File]::ReadAllText($v15SealPath)
$v15Seal = $v15Raw | ConvertFrom-Json
$oldObject = '"path": "tools/native/kira_blackwell_voice_control_anchor_v15.obj"'
$oldBuild = '"path": "RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt"'
Assert-True ((Count-Ordinal $v15Raw $oldObject) -eq 0 -and (Count-Ordinal $v15Raw $oldBuild) -eq 0) 'V15 root-cause negative control not reproduced'
$oldMissing = 0
$compactExact = 0
foreach ($row in @($v15Seal.subjects)) {
    if ((Count-Ordinal $v15Raw ('"path": "' + $row.path + '"')) -eq 0) { $oldMissing++ }
    if ((Count-Ordinal $v15Raw (Compact-Row $row)) -eq 1) { $compactExact++ }
}
Assert-True ($oldMissing -eq 21 -and $compactExact -eq 21) 'V15 21-row mismatch reproduction failed'

$sample = [pscustomobject]@{path='tools/native/example.bin';bytes=123;sha256=('a' * 64)}
$rowToken = Compact-Row $sample
$baseSeal = "{`"subjects`":[$rowToken]}"
Assert-True ((Count-Ordinal $baseSeal $rowToken) -eq 1) 'exact row reference failed'
Assert-True ((Count-Ordinal ($baseSeal.Replace($rowToken,'')) $rowToken) -eq 0) 'missing-row mutation accepted'
Assert-True ((Count-Ordinal ($baseSeal.Replace($rowToken,$rowToken+','+$rowToken)) $rowToken) -eq 2) 'duplicate-row mutation accepted'
$spaced = $rowToken.Replace('"path":"','"path": "')
Assert-True ((Count-Ordinal ($baseSeal.Replace($rowToken,$spaced)) $rowToken) -eq 0) 'whitespace mutation accepted'
$wrongBytes = $rowToken.Replace('"bytes":123','"bytes":124')
Assert-True ((Count-Ordinal ($baseSeal.Replace($rowToken,$wrongBytes)) $rowToken) -eq 0) 'wrong-bytes mutation accepted'
$wrongDigest = $rowToken.Replace(('a' * 64),('b' * 64))
Assert-True ((Count-Ordinal ($baseSeal.Replace($rowToken,$wrongDigest)) $rowToken) -eq 0) 'wrong-digest mutation accepted'
$split = '{"path":"tools/native/example.bin","bytes":124,"sha256":"' + ('b' * 64) + '"},{"path":"decoy","bytes":123,"sha256":"' + ('a' * 64) + '"}'
Assert-True ((Count-Ordinal ($baseSeal.Replace($rowToken,$split)) $rowToken) -eq 0) 'cross-row splice accepted'
Assert-True (($baseSeal + [char]0).IndexOf([char]0) -ge 0) 'NUL mutation setup failed'

$v15OutputPaths = @(
    (Join-Path $kira ($v15Prep + '/RUN_EVIDENCE.jsonl')),
    (Join-Path $kira ($v15Prep + '/STATIC_CONTROL_OUTCOME.receipt.bin'))
)
foreach ($path in $v15OutputPaths) { Assert-True (-not (Test-Path -LiteralPath $path)) "V15 output unexpectedly exists: $path" }

if ($Phase -eq 'PreBuild') {
    foreach ($path in @($objectPath,$executablePath,$buildPath,$sealPath)) {
        Assert-True (-not (Test-Path -LiteralPath $path)) "V16 prebuild artifact unexpectedly exists: $path"
    }
}
if ($Phase -in @('PostBuild','PostSeal')) {
    foreach ($path in @($headerPath,$objectPath,$executablePath,$buildPath)) {
        Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "V16 postbuild artifact absent: $path"
    }
}
if ($Phase -eq 'PostSeal') {
    $sealRaw = [IO.File]::ReadAllText($sealPath)
    $strictSealProbe = "import json,pathlib,sys; b=pathlib.Path(sys.argv[1]).read_bytes(); strict=lambda pairs: dict(pairs) if len({k for k,v in pairs})==len(pairs) else (_ for _ in ()).throw(ValueError('duplicate')); v=json.loads(b,object_pairs_hook=strict); assert v['sealed_subject_count']==41 and len(v['subjects'])==41; print('V16_STRICT_SEAL_PASS')"
    $strictSealOutput = & py -c $strictSealProbe $sealPath 2>&1
    Assert-True ($LASTEXITCODE -eq 0 -and ($strictSealOutput -join "`n").Contains('V16_STRICT_SEAL_PASS')) "V16 strict seal parse failed: $strictSealOutput"
    $seal = $sealRaw | ConvertFrom-Json
    $rows = @($seal.subjects)
    Assert-True ($seal.schema -eq 'kira.blackwell.v16.native_exact_manifest_row_control_anchor.static_seal.v1' -and
        $seal.execution_authority -eq 'NONE' -and $seal.candidate_executed -eq $false -and
        $seal.v15_authority_consumed -eq $true -and $seal.sealed_subject_count -eq 41 -and
        $rows.Count -eq 41 -and (@($rows.path | Sort-Object -Unique).Count -eq 41)) 'V16 seal contract drift'
    Assert-True ((Count-Ordinal $sealRaw '{"path":"') -eq 41) 'V16 compact row prefix count drift'
    foreach ($row in $rows) {
        Assert-True ((Count-Ordinal $sealRaw (Compact-Row $row)) -eq 1) "V16 complete compact row count drift: $($row.path)"
        $path = Resolve-Subject ([string]$row.path)
        Assert-True ((Get-Item -LiteralPath $path).Length -eq [long]$row.bytes -and (Sha $path) -ceq [string]$row.sha256) "V16 sealed subject drift: $($row.path)"
    }
}

'V16_EXACT_MANIFEST_ROW_HOSTILE_STATIC_TESTS_PASS'
