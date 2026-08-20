param()

$ErrorActionPreference = 'Stop'

$projectRoot = (Get-Location).Path
$desktop = [Environment]::GetFolderPath('Desktop')

$candidateRoots = @(
    (Join-Path $projectRoot 'Data/world_builder/staged_assets_for_world_builder'),
    (Join-Path $projectRoot 'Assets/reusable_models'),
    (Join-Path $projectRoot 'Assets/third_party/intake/3d_models_kira_world'),
    (Join-Path $desktop '3d model 3'),
    (Join-Path $desktop '3d model 4'),
    (Join-Path $desktop '3d model 5'),
    (Join-Path $desktop '3d models'),
    (Join-Path $desktop '3d models 2'),
    (Join-Path $desktop 'Ladybug'),
    (Join-Path $desktop "Marinette's Bedroom"),
    (Join-Path $desktop 'no way home'),
    (Join-Path $desktop 'robert avatar base'),
    (Join-Path $desktop 'enterprise d'),
    (Join-Path $desktop 'Spider-Gwen'),
    (Join-Path $desktop 'voyager details')
) | Where-Object { Test-Path $_ } | Sort-Object -Unique | ForEach-Object { (Resolve-Path $_).Path }

$modelExts = @('.glb','.gltf','.usdz','.fbx','.obj','.dae','.blend','.abc','.ply','.stl','.3ds','.lwo','.x3d','.vrm','.mtl','.gltf#')
$archiveExts = @('.zip')
$allModelExts = $modelExts + $archiveExts

$structureKeywordRules = [ordered]@{
    House = @('house','homes','home','villa','bungalow','residence','mansion')
    Apartment = @('apartment','condo','flat','studio','dwelling')
    Corridor = @('corridor','hallway','hall','lobby','staircase')
    Bridge = @('bridge','connector','passage','crossover')
    Stair = @('stairs','stairway','staircase','steps','railing')
    Garage = @('garage','carport','parking','parking lot','driveway')
    Door = @('door','entry','front-door','back-door','sidelight','threshold')
    Wall = @('wall','wallset','wall segment','walling')
    Structural_Batch = @('buildings','building','exterior','interior','site','architecture','urban')
}

$worldHintRules = @{
    star_trek = @('star_trek','enterprise','voyager','uss','lcars')
    home = @('house','home','residence','apartment','kitchen','library','bedroom','bathroom')
    paris = @('louvre','paris','museum','cour','courr','tuileries')
    notebook = @('street','road','mall','world','notebook','bridge','highway')
}

function Normalize-WindowsPath([string]$path) {
    return $path.Replace('/', '\')
}

function Get-SourceLabel([string]$path) {
    $normalized = Normalize-WindowsPath $path
    if ($normalized -match 'staged_assets_for_world_builder\\(?<folder>[^\\]+)') {
        return $matches.folder
    }
    return Split-Path $normalized -Leaf
}

function Get-StructureSignals([string]$text) {
    $lower = $text.ToLowerInvariant()
    $scores = [ordered]@{}
    foreach ($pair in $structureKeywordRules.GetEnumerator()) {
        $count = 0
        foreach ($term in $pair.Value) {
            if ($lower -match [regex]::Escape($term).Replace('\ ', '\s+')) {
                $count += 1
            }
        }
        if ($count -gt 0) {
            $scores[$pair.Key] = $count
        }
    }
    return $scores
}

function Get-WorldHints([string]$text) {
    $lower = $text.ToLowerInvariant()
    $hints = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $worldHintRules.GetEnumerator()) {
        foreach ($term in $entry.Value) {
            if ($lower -match [Regex]::Escape($term).Replace('\ ', '\s+')) {
                if (-not $hints.Contains($entry.Key)) {
                    [void]$hints.Add($entry.Key)
                }
                break
            }
        }
    }
    if ($hints.Count -eq 0) {
        $hints.Add('cross_world')
    }
    return $hints.ToArray()
}

$canReadZip = $false
try {
    Add-Type -AssemblyName 'System.IO.Compression.FileSystem' | Out-Null
    $canReadZip = $true
} catch {
    Write-Warning 'ZipFile API unavailable; zip inner entries will be skipped.'
}

$entries = New-Object System.Collections.Generic.List[object]
$teachingPackageMap = @{}

function Record-Entry {
    param(
        [string]$sourceRoot,
        [string]$path,
        [string]$name,
        [string]$extension,
        [long]$sizeBytes,
        [bool]$isZipContainer,
        [string]$kind,
        [hashtable]$signals,
        [string[]]$worldHints,
        [string]$sourcePackage
    )

    if (-not $signals -or $signals.Count -eq 0) {
        return
    }

    $entry = [ordered]@{
        source_root = $sourceRoot
        source_label = Get-SourceLabel $sourceRoot
        path = Normalize-WindowsPath $path
        name = $name
        extension = $extension
        size_mb = [math]::Round($sizeBytes / 1MB, 4)
        bytes = [long]$sizeBytes
        kind = $kind
        is_zip_container = [bool]$isZipContainer
        categories = ($signals.GetEnumerator() | ForEach-Object { $_.Key }) -join ','
        category_scores = $signals
        world_hints = $worldHints
        package = $sourcePackage
        structure_score = 0
    }

    $score = 0
    foreach ($value in $signals.Values) {
        $score += [int]$value
    }
    $entry.structure_score = $score
    $entries.Add([PSCustomObject]$entry) | Out-Null

    if (-not $teachingPackageMap.ContainsKey($sourcePackage)) {
        $teachingPackageMap[$sourcePackage] = @()
    }
    $teachingPackageMap[$sourcePackage] += $entry
}

foreach ($root in $candidateRoots) {
    Write-Output "Scanning source: $root"
    Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $file = $_
        $full = $file.FullName
        $name = $file.Name
        $ext = $file.Extension.ToLowerInvariant()
        $size = $file.Length

        if ($ext -notin $allModelExts) {
            return
        }

        if ($ext -in $archiveExts) {
            if (-not $canReadZip) {
                $signals = Get-StructureSignals $name
                Record-Entry -sourceRoot $root -path $full -name $name -extension $ext -sizeBytes $size -isZipContainer $true -kind 'zip' -signals $signals -worldHints (Get-WorldHints $full) -sourcePackage $full
                return
            }
            try {
                $zip = [System.IO.Compression.ZipFile]::OpenRead($full)
                try {
                    foreach ($zipEntry in $zip.Entries) {
                        if ($zipEntry.FullName.EndsWith('/')) { continue }
                        $entryName = [IO.Path]::GetFileName($zipEntry.FullName)
                        if ([string]::IsNullOrWhiteSpace($entryName)) { continue }
                        $entryExt = [IO.Path]::GetExtension($entryName).ToLowerInvariant()
                        if ($allModelExts -notcontains $entryExt) { continue }
                        $signals = Get-StructureSignals "$full::$($zipEntry.FullName)"
                        if ($signals.Count -eq 0) {
                            continue
                        }
                        Record-Entry -sourceRoot $root -path "$full::$($zipEntry.FullName)" -name $entryName -extension $entryExt -sizeBytes $zipEntry.Length -isZipContainer $false -kind 'zip_entry' -signals $signals -worldHints (Get-WorldHints "$full $zipEntry.FullName") -sourcePackage $full
                    }
                } finally {
                    $zip.Dispose()
                }
            } catch {
                $signals = Get-StructureSignals $name
                if ($signals.Count -gt 0) {
                    Record-Entry -sourceRoot $root -path $full -name $name -extension $ext -sizeBytes $size -isZipContainer $true -kind 'zip' -signals $signals -worldHints (Get-WorldHints $full) -sourcePackage $full
                }
            }
            return
        }

        $signals = Get-StructureSignals $name
        if ($signals.Count -eq 0) {
            $signals = Get-StructureSignals $full
        }
        Record-Entry -sourceRoot $root -path $full -name $name -extension $ext -sizeBytes $size -isZipContainer $false -kind 'file' -signals $signals -worldHints (Get-WorldHints $full) -sourcePackage $full
    }
}

$sortedEntries = @($entries | Sort-Object structure_score, size_mb -Descending)
$topByCategory = [ordered]@{}
foreach ($category in $structureKeywordRules.Keys) {
    $topByCategory[$category] = @(
        $sortedEntries |
            Where-Object { $_.categories -match [regex]::Escape($category).Replace('_', '_') } |
            Select-Object -First 35
    )
}

$jsonPath = Join-Path $projectRoot 'Data/world_builder/structure_inventory.json'
$mdPath = Join-Path $projectRoot 'Data/world_builder/structure_inventory.md'
$manifestPath = Join-Path $projectRoot 'Data/world_builder/structure_teaching_manifest.md'
$libraryPath = Join-Path $projectRoot 'Data/world_builder/structure_library'
$preservationPath = Join-Path $projectRoot 'Data/world_builder/structure_library_manifest.json'

if (-not (Test-Path $libraryPath)) {
    New-Item -ItemType Directory -Path $libraryPath | Out-Null
}

$savedPackages = @{}
$copiedFiles = 0
foreach ($package in $teachingPackageMap.Keys) {
    $topForPackage = $teachingPackageMap[$package] | Sort-Object structure_score -Descending | Select-Object -First 1
    if (-not $topForPackage) { continue }

    if ($package -match '::') {
        $sourcePath = $package.Split('::')[0]
    } else {
        $sourcePath = $package
    }
    if (-not (Test-Path $sourcePath)) { continue }
    $baseName = [IO.Path]::GetFileName($sourcePath)
    $target = Join-Path $libraryPath $baseName
    if (Test-Path $target) { continue }
    try {
        Copy-Item -Path $sourcePath -Destination $target -Force
        $copiedFiles += 1
        $savedPackages[$package] = $target
    } catch {
        $savedPackages[$package] = "copy_failed: $($_.Exception.Message)"
    }
}

$summary = [ordered]@{
    schema_version = 1
    generated_at = Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffffffK'
    staged_root = Join-Path $projectRoot 'Data/world_builder/staged_assets_for_world_builder'
    scanned_roots = @($candidateRoots | ForEach-Object { Normalize-WindowsPath $_ })
    totals = [ordered]@{
        total_structure_records = $entries.Count
        structure_categories_detected = $structureKeywordRules.Count
        structure_sources = ($entries | Select-Object -ExpandProperty source_root -Unique).Count
        copied_preservation_files = $copiedFiles
    }
    by_category_top_counts = @{}
}
foreach ($category in $topByCategory.Keys) {
    $summary.by_category_top_counts[$category] = @($topByCategory[$category]).Count
}

$json = [ordered]@{
    schema_version = 1
    generated_at = $summary.generated_at
    scanned_roots = $summary.scanned_roots
    structure_records = @($sortedEntries | ForEach-Object { [ordered]@{
        source_root = $_.source_root
        source_label = $_.source_label
        path = Normalize-WindowsPath $_.path
        name = $_.name
        extension = $_.extension
        size_mb = $_.size_mb
        bytes = [long]$_.bytes
        kind = $_.kind
        is_zip_container = $_.is_zip_container
        categories = $_.categories
        category_scores = $_.category_scores
        world_hints = $_.world_hints
        package = $_.package
        structure_score = $_.structure_score
    } })
    summary = $summary
    teaching_library = @{
        folder = Normalize-WindowsPath $libraryPath
        copied_count = $copiedFiles
        package_map = $savedPackages
    }
    by_category_top = $topByCategory
}

$json | ConvertTo-Json -Depth 25 | Set-Content -Path $jsonPath -Encoding UTF8

$mdLines = New-Object System.Collections.Generic.List[string]
$mdLines.Add('# Structure Inventory for World Builder') | Out-Null
$mdLines.Add('') | Out-Null
$mdLines.Add(("Generated: {0}" -f $summary.generated_at)) | Out-Null
$mdLines.Add('') | Out-Null
$mdLines.Add('## Scan summary') | Out-Null
$mdLines.Add("- Structure-like records: $($entries.Count)") | Out-Null
$mdLines.Add("- Structure library folder: $($libraryPath)") | Out-Null
$mdLines.Add("- Preserved structure source files: $copiedFiles") | Out-Null
$mdLines.Add('') | Out-Null

function Add-CategorySection([string]$name) {
    $mdLines.Add("### $name") | Out-Null
    $mdLines.Add('| Source | File | Path | Categories | Score | Size MB | Hints |') | Out-Null
    $mdLines.Add('|---|---|---|---|---:|---:|---|') | Out-Null
    $items = $topByCategory[$name]
    if (-not $items -or $items.Count -eq 0) {
        $mdLines.Add('| _No structure match yet_ | - | - | - | 0 | 0 | - |') | Out-Null
        return
    }
    foreach ($item in $items) {
        $score = if ($item.structure_score) { $item.structure_score } else { 0 }
        $hints = if ($item.world_hints) { ($item.world_hints -join ',') } else { '-' }
        $sourceLabel = if ($item.source_label) { $item.source_label } else { '-' }
        $mdLines.Add("| $sourceLabel | $($item.name) | $($item.path) | $($item.categories) | $score | $([math]::Round($item.size_mb,4)) | $hints |") | Out-Null
    }
}

$mdLines.Add('') | Out-Null
$mdLines.Add('## Top structure candidates by class') | Out-Null
Add-CategorySection 'House'
Add-CategorySection 'Apartment'
Add-CategorySection 'Corridor'
Add-CategorySection 'Bridge'
Add-CategorySection 'Door'
Add-CategorySection 'Garage'
Add-CategorySection 'Stair'
Add-CategorySection 'Structural_Batch'

$mdLines.Add('') | Out-Null
$mdLines.Add('## Suggested world-generator structure seeds') | Out-Null
$mdLines.Add('| World intent | Best source files | Why |') | Out-Null
$mdLines.Add('|---|---|---|') | Out-Null

$homeSeeds = @(
    $sortedEntries |
        Where-Object { $_.world_hints -contains 'home' } |
        Sort-Object @{ Expression = 'structure_score'; Descending = $true }, @{ Expression = 'bytes'; Descending = $true } |
        Select-Object -First 12
)
$ifEmpty = @('_none_')
foreach ($seed in @($homeSeeds | Where-Object { $_ })) {
    $why = if ($seed.categories) { $seed.categories } else { 'house-like asset' }
    $mdLines.Add("| Home | $($seed.name) | $why |") | Out-Null
}
if (-not $homeSeeds -or $homeSeeds.Count -eq 0) {
    $mdLines.Add("| Home | _none_ | scan a new model batch |") | Out-Null
}

$bridgeSeeds = @(
    $sortedEntries |
        Where-Object { $_.categories -match 'Corridor|Bridge' -or $_.name -match 'corridor|bridge' } |
        Sort-Object @{ Expression = 'structure_score'; Descending = $true }, @{ Expression = 'bytes'; Descending = $true } |
        Select-Object -First 10
)
$bridgeSourceAdded = $false
foreach ($seed in @($bridgeSeeds | Where-Object { $_ })) {
    $bridgeSourceAdded = $true
    $why = if ($seed.categories) { $seed.categories } else { 'corridor/bridge or hall element' }
    $mdLines.Add("| Star Trek / Sci-fi | $($seed.name) | $why |") | Out-Null
}
if (-not $bridgeSourceAdded) {
    $mdLines.Add("| Star Trek / Sci-fi | _none_ | scan more corridor or bridge packs |") | Out-Null
}

$mdText = $mdLines -join "`n"
Set-Content -Path $mdPath -Value $mdText -Encoding UTF8

$preservation = [ordered]@{
    generated_at = $summary.generated_at
    source = "Data/world_builder/build_structure_inventory.ps1"
    structure_library_path = Normalize-WindowsPath $libraryPath
    package_count = $savedPackages.Count
    preserved = @($savedPackages.GetEnumerator() | ForEach-Object {
        [ordered]@{
            source_package = $_.Key
            saved_target = $_.Value
        }
    })
}

$preservation | ConvertTo-Json -Depth 25 | Set-Content -Path $preservationPath -Encoding UTF8

$manifestLines = New-Object System.Collections.Generic.List[string]
$manifestLines.Add('# Structure Teaching Manifest') | Out-Null
$manifestLines.Add('') | Out-Null
$manifestLines.Add("Generated: $($summary.generated_at)") | Out-Null
$manifestLines.Add('') | Out-Null
$manifestLines.Add('## Recommended generator seeds for the next house/building tests') | Out-Null
$manifestLines.Add('- Prefer house candidates with explicit `house`, `entry`, `apartment`, or `bridge/corridor` terms.') | Out-Null
$manifestLines.Add('- When generating a neighbor shell, reuse structure proportions from the top house candidates and verify:') | Out-Null
$manifestLines.Add('  - true walkable floor above the second floor') | Out-Null
$manifestLines.Add('  - at least 2m clear path around the front door and front face') | Out-Null
$manifestLines.Add('  - open/close door states and blocked doorway collision') | Out-Null
$manifestLines.Add('  - readable window frames and window opening positions') | Out-Null
$manifestLines.Add('') | Out-Null

$topHouse = $topByCategory.House
if ($topHouse -and $topHouse.Count -gt 0) {
    $manifestLines.Add('### Top house references') | Out-Null
    foreach ($item in ($topHouse | Select-Object -First 12)) {
        $manifestLines.Add("- $($item.name) ($($item.structure_score)): $($item.path)") | Out-Null
    }
}

$topCorridor = $topByCategory.Corridor + $topByCategory.Bridge
if ($topCorridor -and $topCorridor.Count -gt 0) {
    $manifestLines.Add('') | Out-Null
    $manifestLines.Add('### Corridor / bridge references') | Out-Null
    foreach ($item in ($topCorridor | Select-Object -First 12)) {
        $manifestLines.Add("- $($item.name) ($($item.structure_score)): $($item.path)") | Out-Null
    }
}

Set-Content -Path $manifestPath -Value ($manifestLines -join "`n") -Encoding UTF8

Write-Output "structure_inventory_json=$jsonPath"
Write-Output "structure_inventory_md=$mdPath"
Write-Output "structure_library=$libraryPath"
Write-Output "structure_teaching_manifest=$manifestPath"
