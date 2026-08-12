[CmdletBinding()]
param(
    [ValidateSet('Describe', 'PRECHANGE', 'POST_APPLY_BASELINE', 'POSTCHANGE', 'ROLLBACK')]
    [string]$Stage = 'Describe',
    [string]$EvidenceDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ExactTarget = [System.IO.Path]::GetFullPath(
    (Join-Path $ProjectRoot 'Voice\sidecars\chatterbox_blackwell_gpu\.venv')
)
$EvidenceRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $ProjectRoot 'RecoverySprint\continuation_20260803\defender_blackwell_voice_narrow_exclusion')
)
$ApplyHelper = Join-Path $ProjectRoot 'tools\apply_defender_blackwell_voice_exclusion.ps1'
$ExpectedApplyHelperSha256 = '87527f0c5973a6e1c3c698b0a21395562ae6db4fb94849b6271cf99591664919'
$PriorAttemptDirectory = Join-Path $EvidenceRoot 'attempt_01'
$PriorEvidenceHashes = [ordered]@{
    'APPLY_FAILURE.json' = '311b6b2b091e52f91cf39109794a54cd1f101cbc8d81283a90d4604f0c731df7'
    'FIREWALL_RESTORATION.json' = 'dcf417b0767013f39e4b16b09f8dc259415ac2af7fa44dad997db95a48d4dc2c'
    'PRECHANGE_CHECKPOINT.md' = '9023e4c4b3a42526bc903c3b3a72a3a6bbf1cdffc491a8faf1ddf95750f7f021'
}

function Get-UtcNow {
    return [DateTimeOffset]::UtcNow.ToString('o')
}

function Get-FileSha256([string]$LiteralPath) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $LiteralPath).Hash.ToLowerInvariant()
}

function Get-TextSha256([string]$Value) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-ContainedRelativePath([string]$BasePath, [string]$ChildPath) {
    $base = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\')
    $child = [System.IO.Path]::GetFullPath($ChildPath)
    $prefix = $base + '\'
    if (-not $child.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the required root: $child"
    }
    return $child.Substring($prefix.Length).Replace('\', '/')
}

function Write-ExclusiveJson([string]$LiteralPath, [object]$Payload) {
    $text = ($Payload | ConvertTo-Json -Depth 12) + "`n"
    $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($text)
    $stream = [System.IO.File]::Open(
        $LiteralPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
    return Get-TextSha256 $text
}

function Assert-SealedInputs {
    if (-not (Test-Path -LiteralPath $ExactTarget -PathType Container)) {
        throw "The exact Blackwell virtual environment is absent: $ExactTarget"
    }
    $resolved = (Resolve-Path -LiteralPath $ExactTarget).Path
    if (-not [string]::Equals($resolved, $ExactTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'The exact Defender target resolved to a different path.'
    }
    $item = Get-Item -LiteralPath $resolved -Force
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'The exact Defender target is a reparse point.'
    }
    $applyHash = Get-FileSha256 $ApplyHelper
    if ($applyHash -ne $ExpectedApplyHelperSha256) {
        throw "The sole approved Defender apply helper changed: $applyHash"
    }
}

function Get-PriorAttemptEvidence {
    $result = @()
    foreach ($entry in $PriorEvidenceHashes.GetEnumerator()) {
        $path = Join-Path $PriorAttemptDirectory $entry.Key
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Prior Defender evidence is absent: $path"
        }
        $actual = Get-FileSha256 $path
        if ($actual -ne $entry.Value) {
            throw "Prior Defender evidence changed: $($entry.Key)"
        }
        $item = Get-Item -LiteralPath $path
        $result += [ordered]@{
            path = Get-ContainedRelativePath $ProjectRoot $path
            bytes = $item.Length
            sha256 = $actual
        }
    }
    return $result
}

function Get-CriticalRuntimeFiles {
    $paths = @(
        (Join-Path $ExactTarget 'Scripts\python.exe'),
        (Join-Path $ExactTarget 'Lib\site-packages\torch\__init__.py'),
        (Join-Path $ExactTarget 'Lib\site-packages\torch\_C.cp311-win_amd64.pyd'),
        (Join-Path $ExactTarget 'Lib\site-packages\numpy\__init__.py'),
        (Join-Path $ExactTarget 'Lib\site-packages\numpy\core\_multiarray_umath.cp311-win_amd64.pyd')
    )
    $openBlas = @(
        Get-ChildItem -LiteralPath (Join-Path $ExactTarget 'Lib\site-packages\numpy.libs') `
            -Filter 'libopenblas*.dll' -File -ErrorAction Stop
    )
    if ($openBlas.Count -ne 1) {
        throw "Expected exactly one NumPy OpenBLAS DLL; found $($openBlas.Count)."
    }
    $paths += $openBlas[0].FullName
    $result = @()
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Critical runtime file is absent: $path"
        }
        $item = Get-Item -LiteralPath $path
        $result += [ordered]@{
            path = Get-ContainedRelativePath $ProjectRoot $item.FullName
            bytes = $item.Length
            sha256 = Get-FileSha256 $item.FullName
        }
    }
    return $result
}

function Get-State {
    if (-not (Get-Command Get-MpPreference -ErrorAction SilentlyContinue)) {
        throw 'Get-MpPreference is unavailable.'
    }
    try {
        $preference = Get-MpPreference -ErrorAction Stop
    }
    catch {
        throw "Get-MpPreference failed. Use legitimate elevated PowerShell/UAC; do not bypass Defender: $($_.Exception.Message)"
    }
    $paths = @(
        $preference.ExclusionPath |
            Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
            ForEach-Object { [System.IO.Path]::GetFullPath([string]$_).TrimEnd('\') } |
            Sort-Object -Unique
    )
    $target = $ExactTarget.TrimEnd('\')
    $targetPresent = $false
    foreach ($path in $paths) {
        if ([string]::Equals($path, $target, [System.StringComparison]::OrdinalIgnoreCase)) {
            $targetPresent = $true
            break
        }
    }
    $others = @(
        $paths | Where-Object {
            -not [string]::Equals($_, $target, [System.StringComparison]::OrdinalIgnoreCase)
        }
    )
    $realtimeDisabled = [bool]$preference.DisableRealtimeMonitoring
    $behaviorDisabled = [bool]$preference.DisableBehaviorMonitoring
    $ioavDisabled = [bool]$preference.DisableIOAVProtection
    return [ordered]@{
        exact_target_path = $ExactTarget
        exact_target_present = $targetPresent
        defender_disabled = ($realtimeDisabled -or $behaviorDisabled -or $ioavDisabled)
        realtime_monitoring_disabled = $realtimeDisabled
        behavior_monitoring_disabled = $behaviorDisabled
        ioav_protection_disabled = $ioavDisabled
        exclusion_path_count = $paths.Count
        all_exclusion_paths_sha256 = Get-TextSha256 (($paths | ForEach-Object { $_.ToLowerInvariant() }) -join "`n")
        other_exclusion_path_count = $others.Count
        other_exclusion_paths_sha256 = Get-TextSha256 (($others | ForEach-Object { $_.ToLowerInvariant() }) -join "`n")
    }
}

function New-AttemptDirectory {
    [System.IO.Directory]::CreateDirectory($EvidenceRoot) | Out-Null
    for ($number = 1; $number -le 999; $number++) {
        $candidate = Join-Path $EvidenceRoot ('attempt_{0:d2}' -f $number)
        if (Test-Path -LiteralPath $candidate) {
            continue
        }
        try {
            $created = New-Item -ItemType Directory -Path $candidate -ErrorAction Stop
            return $created.FullName
        }
        catch {
            if (Test-Path -LiteralPath $candidate) {
                continue
            }
            throw
        }
    }
    throw 'No append-only Defender evidence attempt directory is available.'
}

function Resolve-AttemptDirectory([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Stage requires -EvidenceDirectory from PRECHANGE."
    }
    $resolved = (Resolve-Path -LiteralPath $Value).Path
    $relative = Get-ContainedRelativePath $EvidenceRoot $resolved
    if (-not (Split-Path -Leaf $resolved).StartsWith('attempt_')) {
        throw 'Evidence directory is not an append-only attempt directory.'
    }
    return $resolved
}

if ($Stage -eq 'Describe') {
    [ordered]@{
        schema_version = 1
        artifact_kind = 'blackwell_defender_exclusion_state_capture_description'
        status = 'PREPARED_NOT_EXECUTED'
        exact_target_path = $ExactTarget
        sole_apply_helper_path = Get-ContainedRelativePath $ProjectRoot $ApplyHelper
        sole_apply_helper_expected_sha256 = $ExpectedApplyHelperSha256
        changes_defender = $false
        records_raw_other_exclusion_paths = $false
        stages = @('PRECHANGE', 'POST_APPLY_BASELINE', 'POSTCHANGE', 'ROLLBACK')
    } | ConvertTo-Json -Depth 6
    exit 0
}

Assert-SealedInputs
$attempt = if ($Stage -in @('PRECHANGE', 'POST_APPLY_BASELINE')) {
    if (-not [string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
        throw "$Stage allocates its own append-only evidence directory."
    }
    New-AttemptDirectory
}
else {
    Resolve-AttemptDirectory $EvidenceDirectory
}

$targetFile = Join-Path $attempt ($Stage + '.json')
if (Test-Path -LiteralPath $targetFile) {
    throw "Evidence already exists and will not be overwritten: $targetFile"
}
$state = Get-State
$prechange = $null
if ($Stage -notin @('PRECHANGE', 'POST_APPLY_BASELINE')) {
    $prechangePath = Join-Path $attempt 'PRECHANGE.json'
    if (-not (Test-Path -LiteralPath $prechangePath -PathType Leaf)) {
        throw 'The exact PRECHANGE.json is absent.'
    }
    $prechange = Get-Content -LiteralPath $prechangePath -Raw | ConvertFrom-Json
}

$payload = [ordered]@{
    schema_version = 1
    artifact_kind = 'blackwell_exact_venv_defender_exclusion_state'
    stage = $Stage
    recorded_at_utc = Get-UtcNow
    exact_target_path = $state.exact_target_path
    exact_target_present = $state.exact_target_present
    defender_disabled = $state.defender_disabled
    realtime_monitoring_disabled = $state.realtime_monitoring_disabled
    behavior_monitoring_disabled = $state.behavior_monitoring_disabled
    ioav_protection_disabled = $state.ioav_protection_disabled
    exclusion_path_count = $state.exclusion_path_count
    all_exclusion_paths_sha256 = $state.all_exclusion_paths_sha256
    other_exclusion_path_count = $state.other_exclusion_path_count
    other_exclusion_paths_sha256 = $state.other_exclusion_paths_sha256
    raw_other_exclusion_paths_recorded = $false
    other_exclusions_preserved = if ($Stage -eq 'POST_APPLY_BASELINE') {
        'NOT_PROVEN_NO_MACHINE_PRESTATE'
    }
    elseif ($null -eq $prechange) {
        $true
    }
    else {
        $state.other_exclusion_paths_sha256 -eq [string]$prechange.other_exclusion_paths_sha256
    }
    defender_changed_by_capture = $false
    defender_globally_disabled_by_capture = $false
    apply_helper_path = Get-ContainedRelativePath $ProjectRoot $ApplyHelper
    apply_helper_sha256 = Get-FileSha256 $ApplyHelper
    capture_helper_path = Get-ContainedRelativePath $ProjectRoot $PSCommandPath
    capture_helper_sha256 = Get-FileSha256 $PSCommandPath
    critical_runtime_files = Get-CriticalRuntimeFiles
}
if ($Stage -eq 'POST_APPLY_BASELINE') {
    $payload.machine_prechange_state_available = $false
    $payload.paired_pre_post_causality_claimed = $false
    $payload.exclusion_effectiveness_proven = $false
    $payload.prior_attempt_evidence = Get-PriorAttemptEvidence
}
if ($Stage -eq 'POSTCHANGE') {
    $payload.added_by_apply_helper_inferred = (
        -not [bool]$prechange.exact_target_present -and [bool]$state.exact_target_present
    )
}
if ($Stage -eq 'ROLLBACK') {
    $payload.restored_prechange_target_state = (
        [bool]$prechange.exact_target_present -eq [bool]$state.exact_target_present
    )
}
$sha256 = Write-ExclusiveJson $targetFile $payload
[ordered]@{
    path = $targetFile
    sha256 = $sha256
    stage = $Stage
    exact_target_present = $state.exact_target_present
    defender_disabled = $state.defender_disabled
    other_exclusions_preserved = $payload.other_exclusions_preserved
} | ConvertTo-Json -Depth 6

if ($state.defender_disabled) {
    exit 21
}
if ($Stage -in @('POSTCHANGE', 'POST_APPLY_BASELINE') -and -not $state.exact_target_present) {
    exit 20
}
if ($Stage -eq 'ROLLBACK' -and -not $payload.restored_prechange_target_state) {
    exit 22
}
exit 0
