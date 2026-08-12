$ErrorActionPreference = 'Stop'

$root = Join-Path $PSScriptRoot ('fixture_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
$staging = Join-Path $root 'worker_staging'
$outside = Join-Path $root 'outside'
New-Item -ItemType Directory -Path $staging | Out-Null
New-Item -ItemType Directory -Path $outside | Out-Null

$insideSource = Join-Path $staging 'inside_source.json'
$outsideSource = Join-Path $staging 'outside_source.json'
[System.IO.File]::WriteAllBytes($insideSource, [byte[]](1, 2, 3, 4))
[System.IO.File]::WriteAllBytes($outsideSource, [byte[]](5, 6, 7, 8))

$dacl = 'D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;GRGW;;;OW)'
foreach ($source in @($insideSource, $outsideSource)) {
    $security = New-Object System.Security.AccessControl.FileSecurity
    $security.SetSecurityDescriptorSddlForm($dacl)
    Set-Acl -LiteralPath $source -AclObject $security
}

$canonical = (Get-Acl -LiteralPath $outsideSource).Sddl
$insideAlias = Join-Path $staging 'inside_alias.json'
$outsideAlias = Join-Path $outside 'outside_alias.json'

$insideCreated = $false
$outsideCreated = $false
$outsideDeleted = $false
$insideError = $null
$outsideError = $null

try {
    New-Item -ItemType HardLink -Path $insideAlias -Target $insideSource | Out-Null
    $insideCreated = Test-Path -LiteralPath $insideAlias
} catch {
    $insideError = $_.Exception.Message
}

$heldNoDeleteShare = [System.IO.File]::Open(
    $outsideSource,
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::Read
)
try {
    New-Item -ItemType HardLink -Path $outsideAlias -Target $outsideSource | Out-Null
    $outsideCreated = Test-Path -LiteralPath $outsideAlias
    if ($outsideCreated) {
        Remove-Item -LiteralPath $outsideAlias
        $outsideDeleted = -not (Test-Path -LiteralPath $outsideAlias)
    }
} catch {
    $outsideError = $_.Exception.Message
} finally {
    $heldNoDeleteShare.Dispose()
}

$outsideLinksAfter = @(& fsutil.exe hardlink list $outsideSource | Where-Object { $_.Trim() -ne '' }).Count
$result = [ordered]@{
    schema = 'kira.r25.medical_reference_proxy.v3r31.independent_hardlink_probe.v1'
    source_dacl_requested = $dacl
    source_dacl_readback = $canonical
    inside_hardlink_created = $insideCreated
    outside_hardlink_created_while_source_open_without_delete_share = $outsideCreated
    outside_hardlink_deleted_while_source_open_without_delete_share = $outsideDeleted
    outside_source_link_count_after_alias_delete = $outsideLinksAfter
    inside_error = $insideError
    outside_error = $outsideError
    transient_outside_alias_can_restore_link_count = ($outsideCreated -and $outsideDeleted -and $outsideLinksAfter -eq 1)
    v3r31_claim_refuted = ($insideCreated -or $outsideCreated)
}
$result | ConvertTo-Json -Depth 4

