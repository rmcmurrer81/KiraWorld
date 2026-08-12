param(
    [string]$BackupRoot = 'C:\KiraVideos\Backups\StudioOutputs_pre_v2_20260723_073835',
    [string]$PayloadRoot = '',
    [switch]$CompareLiveSource,
    [string]$LiveSource = 'C:\Users\robmc\KiraVideos\StudioOutputs'
)

$ErrorActionPreference = 'Stop'

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-AdsSha256 {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [Parameter(Mandatory = $true)][string]$Stream
    )

    $extendedPath = '\\?\' + $File + ':' + $Stream
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $fileStream = [IO.File]::OpenRead($extendedPath)
        try {
            ([BitConverter]::ToString($sha.ComputeHash($fileStream))).Replace('-', '').ToLowerInvariant()
        }
        finally {
            $fileStream.Dispose()
        }
    }
    finally {
        $sha.Dispose()
    }
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Path
    )
    $Path.Substring($Root.Length).TrimStart('\')
}

$backup = (Resolve-Path -LiteralPath $BackupRoot).Path.TrimEnd('\')
$metadata = Join-Path $backup '_BACKUP_METADATA'
if (-not (Test-Path -LiteralPath $metadata -PathType Container)) {
    throw "Backup metadata is missing: $metadata"
}

if ([string]::IsNullOrWhiteSpace($PayloadRoot)) {
    $payload = $backup
}
else {
    $payload = (Resolve-Path -LiteralPath $PayloadRoot).Path.TrimEnd('\')
}

$fileManifestPath = Join-Path $metadata 'FILE_INVENTORY_AND_VERIFICATION.csv'
$streamManifestPath = Join-Path $metadata 'NAMED_STREAM_INVENTORY_AND_VERIFICATION.csv'
$directoryManifestPath = Join-Path $metadata 'DIRECTORY_VERIFICATION.csv'
$metadataManifestPath = Join-Path $metadata 'METADATA_MANIFEST_SHA256.csv'

foreach ($required in @(
    $fileManifestPath,
    $streamManifestPath,
    $directoryManifestPath,
    $metadataManifestPath
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required manifest is missing: $required"
    }
}

$fileRows = @(Import-Csv -LiteralPath $fileManifestPath)
$streamRows = @(Import-Csv -LiteralPath $streamManifestPath)
$directoryRows = @(Import-Csv -LiteralPath $directoryManifestPath)
$metadataRows = @(Import-Csv -LiteralPath $metadataManifestPath)
$problems = New-Object Collections.Generic.List[string]

foreach ($row in $metadataRows) {
    $path = Join-Path $metadata $row.filename
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $problems.Add("metadata file missing: $($row.filename)")
        continue
    }
    if ((Get-Item -LiteralPath $path).Length -ne [int64]$row.bytes) {
        $problems.Add("metadata byte mismatch: $($row.filename)")
    }
    if ((Get-Sha256 -Path $path) -ne $row.sha256.ToLowerInvariant()) {
        $problems.Add("metadata SHA-256 mismatch: $($row.filename)")
    }
}

$expectedDirectories = @{}
foreach ($row in $directoryRows) {
    $expectedDirectories[$row.relative_path.ToLowerInvariant()] = $true
    $path = Join-Path $payload $row.relative_path
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        $problems.Add("payload directory missing: $($row.relative_path)")
    }
}

$payloadDirectories = @(
    Get-ChildItem -LiteralPath $payload -Recurse -Force -Directory |
        Where-Object {
            $payload -ne $backup -or
            ($_.FullName -ne $metadata -and
            -not $_.FullName.StartsWith($metadata + '\', [StringComparison]::OrdinalIgnoreCase))
        }
)
foreach ($item in $payloadDirectories) {
    $relative = Get-RelativePath -Root $payload -Path $item.FullName
    if (-not $expectedDirectories.ContainsKey($relative.ToLowerInvariant())) {
        $problems.Add("unexpected payload directory: $relative")
    }
}

$expectedFiles = @{}
foreach ($row in $fileRows) {
    $expectedFiles[$row.relative_path.ToLowerInvariant()] = $true
    $path = Join-Path $payload $row.relative_path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $problems.Add("payload file missing: $($row.relative_path)")
        continue
    }
    if ((Get-Item -LiteralPath $path).Length -ne [int64]$row.bytes) {
        $problems.Add("payload byte mismatch: $($row.relative_path)")
    }
    if ((Get-Sha256 -Path $path) -ne $row.source_sha256.ToLowerInvariant()) {
        $problems.Add("payload SHA-256 mismatch: $($row.relative_path)")
    }

    if ($CompareLiveSource) {
        $livePath = Join-Path $LiveSource $row.relative_path
        if (-not (Test-Path -LiteralPath $livePath -PathType Leaf)) {
            $problems.Add("live source file missing: $($row.relative_path)")
        }
        elseif ((Get-Sha256 -Path $livePath) -ne $row.source_sha256.ToLowerInvariant()) {
            $problems.Add("live source file changed: $($row.relative_path)")
        }
    }
}

$payloadFiles = @(
    Get-ChildItem -LiteralPath $payload -Recurse -Force -File |
        Where-Object {
            $payload -ne $backup -or
            -not $_.FullName.StartsWith($metadata + '\', [StringComparison]::OrdinalIgnoreCase)
        }
)
foreach ($item in $payloadFiles) {
    $relative = Get-RelativePath -Root $payload -Path $item.FullName
    if (-not $expectedFiles.ContainsKey($relative.ToLowerInvariant())) {
        $problems.Add("unexpected payload file: $relative")
    }
}

$streamRowsByFile = @{}
foreach ($row in $streamRows) {
    $key = $row.relative_path.ToLowerInvariant()
    if (-not $streamRowsByFile.ContainsKey($key)) {
        $streamRowsByFile[$key] = @{}
    }
    $streamRowsByFile[$key][$row.stream.ToLowerInvariant()] = $row

    $path = Join-Path $payload $row.relative_path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }
    $actualStream = Get-Item -LiteralPath $path -Stream $row.stream -ErrorAction SilentlyContinue
    if ($null -eq $actualStream) {
        $problems.Add("named stream missing: $($row.relative_path):$($row.stream)")
        continue
    }
    if ([int64]$actualStream.Length -ne [int64]$row.bytes) {
        $problems.Add("named stream byte mismatch: $($row.relative_path):$($row.stream)")
    }
    if ((Get-AdsSha256 -File $path -Stream $row.stream) -ne $row.source_sha256.ToLowerInvariant()) {
        $problems.Add("named stream SHA-256 mismatch: $($row.relative_path):$($row.stream)")
    }

    if ($CompareLiveSource) {
        $livePath = Join-Path $LiveSource $row.relative_path
        $liveStream = Get-Item -LiteralPath $livePath -Stream $row.stream -ErrorAction SilentlyContinue
        if ($null -eq $liveStream) {
            $problems.Add("live source named stream missing: $($row.relative_path):$($row.stream)")
        }
        elseif ((Get-AdsSha256 -File $livePath -Stream $row.stream) -ne $row.source_sha256.ToLowerInvariant()) {
            $problems.Add("live source named stream changed: $($row.relative_path):$($row.stream)")
        }
    }
}

foreach ($row in $fileRows) {
    $path = Join-Path $payload $row.relative_path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }
    $expected = @{}
    $key = $row.relative_path.ToLowerInvariant()
    if ($streamRowsByFile.ContainsKey($key)) {
        $expected = $streamRowsByFile[$key]
    }
    $actualStreams = @(
        Get-Item -LiteralPath $path -Stream * -ErrorAction SilentlyContinue |
            Where-Object Stream -ne ':$DATA'
    )
    foreach ($stream in $actualStreams) {
        if (-not $expected.ContainsKey($stream.Stream.ToLowerInvariant())) {
            $problems.Add("unexpected named stream: $($row.relative_path):$($stream.Stream)")
        }
    }
}

$result = [ordered]@{
    backup_root = $backup
    payload_root = $payload
    ordinary_files_checked = $fileRows.Count
    named_streams_checked = $streamRows.Count
    directories_checked = $directoryRows.Count
    metadata_files_checked = $metadataRows.Count
    live_source_compared = [bool]$CompareLiveSource
    problems = $problems.Count
    passed = ($problems.Count -eq 0)
}

$result | ConvertTo-Json -Depth 4
if ($problems.Count -gt 0) {
    $problems | ForEach-Object { Write-Error $_ }
    exit 1
}

exit 0
