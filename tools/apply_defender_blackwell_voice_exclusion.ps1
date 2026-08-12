$ErrorActionPreference = 'Stop'

$expectedTarget = 'C:\Users\robmc\Kira\Voice\sidecars\chatterbox_blackwell_gpu\.venv'
$target = [System.IO.Path]::GetFullPath($expectedTarget)

if (-not [string]::Equals($target, $expectedTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
    exit 10
}

$before = Get-MpPreference
$wasPresent = [bool](@($before.ExclusionPath) -contains $target)

if (-not $wasPresent) {
    Add-MpPreference -ExclusionPath $target
}

$after = Get-MpPreference
$isPresent = [bool](@($after.ExclusionPath) -contains $target)

if (-not $isPresent) {
    exit 20
}

if ([bool]$after.DisableRealtimeMonitoring -or [bool]$after.DisableBehaviorMonitoring) {
    exit 21
}

exit 0
