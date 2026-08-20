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

$textureExts = @('.png','.jpg','.jpeg','.webp','.tga','.bmp','.gif','.tiff','.tif','.hdr','.exr','.dds','.ktx','.ktx2','.svg','.jfif')
$modelExts = @('.glb','.gltf','.usdz','.fbx','.obj','.dae','.blend','.abc','.ply','.stl','.3ds','.lwo','.x3d','.vrm','.mtl','.gltf#')
$archiveExts = @('.zip')
$allExts = $textureExts + $modelExts + $archiveExts

$categoryKeywords = [ordered]@{
    Seating = @('chair','sofa','couch','bench','stool','recliner','armchair','ottoman','seating','seat')
    Surfaces = @('table','desk','counter','coffee','kitchen','wall','slab','surface','countertop','dining','coffee_table','coffee_table','desk','bench')
    Storage = @('shelf','shelves','bookshelf','bookcase','cabinet','storage','drawer','wardrobe','closet','crate','rack','case','wardrobe')
    Lighting = @('lamp','light','chandelier','lampshade','pendant','fixture')
    Doors = @('door','entry','hinge','portal','shutter')
    Architectural = @('wall','floor','ceiling','stairs','rail','railing','hall','architecture','building','house','window','column','pillar','roof','stair')
    Human_Facilities = @('toilet','bathroom','bath','shower','sink','toile','toilette','bathtub','bed','bedroom')
    World_Specific_Low = @('star_trek','enterprise','voyager','uss','lcars','alien','dalek','starl')
    World_Plan = @('louvre','paris','museum','pyramid','eiffel')
}

$worldHintRules = @{
    star_trek = @('star_trek','star trek','enterprise','voyager','uss','lcars','delta_flyer','enterprise_a','enterprise_d')
    paris = @('louvre','paris','museum','palace','hotel','seine','pyramid')
    cross_world = @('chair','sofa','couch','table','bench','shelf','cabinet','storage','lamp','light','door','book','kitchen','bathroom','bedroom')
}

$mapsetRules = @{
    BaseColor = @('basecolor','albedo','diffuse','color','colour')
    Metallic = @('metallic','metalness','roughmetal')
    Roughness = @('roughness','rough')
    Normal = @('normal')
    AO = @('_ao', 'ao_', 'ambient', 'ambientocclusion', 'occlusion')
    Height = @('height', 'displacement', 'bump', 'parallax')
    Emissive = @('emissive', 'emission', 'selfilluminate')
    Opacity = @('opacity', 'alpha', 'transparent')
}

$canReadZip = $false
try {
    Add-Type -AssemblyName 'System.IO.Compression.FileSystem' | Out-Null
    $canReadZip = $true
} catch {
    Write-Warning 'ZipFile API unavailable; zip inner entries will be skipped.'
}

function Normalize-WindowsPath([string]$path) { return $path.Replace('/', '\') }
function Get-SourceLabel([string]$path) {
    $normalized = Normalize-WindowsPath $path
    if ($normalized -match 'staged_assets_for_world_builder\\(?<folder>[^\\]+)') {
        return $matches.folder -replace '_', ' '
    }
    return Split-Path $normalized -Leaf
}

function Get-WorldHints([string]$text) {
    $lower = $text.ToLowerInvariant()
    $hints = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $worldHintRules.GetEnumerator()) {
        foreach ($term in $entry.Value) {
            if ($lower -match [Regex]::Escape($term).Replace('\ ', '\s+')) {
                if (-not $hints.Contains($entry.Key)) { [void]$hints.Add($entry.Key) }
                break
            }
        }
    }
    if ($hints.Count -eq 0) { $hints.Add('cross_world') }
    return ,$hints.ToArray()
}

function Get-CategoryScores([string]$text) {
    $lower = $text.ToLowerInvariant()
    $scores = [ordered]@{}
    foreach ($pair in $categoryKeywords.GetEnumerator()) {
        $count = 0
        foreach ($term in $pair.Value) {
            if ($lower -match [regex]::Escape($term)) { $count++ }
        }
        if ($count -gt 0) { $scores[$pair.Key] = $count }
    }
    if ($scores.Count -eq 0) { $scores['World_Plan'] = 1 }
    return $scores
}

function Get-MapSets([string]$name) {
    $lower = $name.ToLowerInvariant()
    $sets = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $mapsetRules.GetEnumerator()) {
        foreach ($token in $entry.Value) {
            if ($lower -match [regex]::Escape($token)) {
                if (-not $sets.Contains($entry.Key)) { [void]$sets.Add($entry.Key) }
                break
            }
        }
    }
    if ($sets.Count -eq 0) { return @() }
    return [string[]]($sets | Sort-Object)
}

$entries = New-Object System.Collections.Generic.List[object]

foreach ($root in $candidateRoots) {
    Write-Output "Scanning source: $root"
    Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $file = $_
        $full = $file.FullName
        $ext = $file.Extension.ToLowerInvariant()
        $entrySize = $file.Length
        $entryName = $file.Name
        $entryWorldHints = Get-WorldHints ($full)

        if ($ext -in $archiveExts) {
            if (-not $canReadZip) {
                $scores = Get-CategoryScores $full
                $mapSets = if ($ext -in $textureExts) { Get-MapSets $entryName } else { @() }
                $entries.Add([pscustomobject]@{
                    source_root = $root
                    source_label = Get-SourceLabel $root
                    path = Normalize-WindowsPath $full
                    name = $entryName
                    kind = 'zip'
                    size_mb = [math]::Round($entrySize / 1MB, 4)
                    bytes = [long]$entrySize
                    categories = ($scores.GetEnumerator() | ForEach-Object { $_.Key }) -join ','
                    category_scores = $scores
                    world_hint = $entryWorldHints
                    map_sets = $mapSets
                    has_pbr_hints = ($mapSets.Count -gt 0)
                }) | Out-Null
                return
            }

            try {
                $archive = [System.IO.Compression.ZipFile]::OpenRead($full)
                try {
                    foreach ($zipEntry in $archive.Entries) {
                        if ($zipEntry.FullName.EndsWith('/')) { continue }
                        $entryName = [IO.Path]::GetFileName($zipEntry.FullName)
                        if ([string]::IsNullOrWhiteSpace($entryName)) { continue }
                        $entryExt = [IO.Path]::GetExtension($entryName).ToLowerInvariant()
                        if ($allExts -notcontains $entryExt) { continue }

                        $pathText = "$full::$($zipEntry.FullName)"
                        $scores = Get-CategoryScores $pathText
                        $mapSets = if ($entryExt -in $textureExts) { Get-MapSets $entryName } else { @() }
                        $worldHints = Get-WorldHints $pathText
                        $entries.Add([pscustomobject]@{
                            source_root = $root
                            source_label = Get-SourceLabel $root
                            path = Normalize-WindowsPath $pathText
                            name = $entryName
                            kind = 'zip_entry'
                            size_mb = [math]::Round($zipEntry.Length / 1MB, 4)
                            bytes = [long]$zipEntry.Length
                            categories = ($scores.GetEnumerator() | ForEach-Object { $_.Key }) -join ','
                            category_scores = $scores
                            world_hint = $worldHints
                            map_sets = $mapSets
                            has_pbr_hints = ($mapSets.Count -gt 0)
                        }) | Out-Null
                    }
                } finally {
                    $archive.Dispose()
                }
            } catch {
                $scores = Get-CategoryScores $full
                $mapSets = Get-MapSets $entryName
                $entries.Add([pscustomobject]@{
                    source_root = $root
                    source_label = Get-SourceLabel $root
                    path = Normalize-WindowsPath $full
                    name = $entryName
                    kind = 'zip'
                    size_mb = [math]::Round($entrySize / 1MB, 4)
                    bytes = [long]$entrySize
                    categories = ($scores.GetEnumerator() | ForEach-Object { $_.Key }) -join ','
                    category_scores = $scores
                    world_hint = $entryWorldHints
                    map_sets = @()
                    has_pbr_hints = $false
                }) | Out-Null
            }
            return
        }

        if ($allExts -notcontains $ext) { return }

        $scores = Get-CategoryScores "$full::$entryName"
        $mapSets = if ($ext -in $textureExts) { Get-MapSets $entryName } else { @() }
        $worldHints = Get-WorldHints $full
        $entries.Add([pscustomobject]@{
            source_root = $root
            source_label = Get-SourceLabel $root
            path = Normalize-WindowsPath $full
            name = $entryName
            kind = 'file'
            size_mb = [math]::Round($entrySize / 1MB, 4)
            bytes = [long]$entrySize
            categories = ($scores.GetEnumerator() | ForEach-Object { $_.Key }) -join ','
            category_scores = $scores
            world_hint = $worldHints
            map_sets = $mapSets
            has_pbr_hints = ($mapSets.Count -gt 0)
        }) | Out-Null
    }
}

$scanRootCount = $candidateRoots.Count
$scanEntries = @($entries | ForEach-Object { $_ })

$topByCategory = [ordered]@{}
foreach ($category in $categoryKeywords.Keys) {
    $topByCategory[$category] = @(
        $scanEntries |
            Where-Object { $_.categories -match [regex]::Escape($category) } |
            Sort-Object @{Expression = 'size_mb'; Descending = $true } |
            Select-Object -First 35
    )
}

$jsonPath = Join-Path $projectRoot 'Data/world_builder/furniture_inventory.json'
$mdPath = Join-Path $projectRoot 'Data/world_builder/furniture_inventory.md'

$summary = [ordered]@{
    schema_version = 1
    generated_at = Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffffffK'
    staged_root = Join-Path $projectRoot 'Data/world_builder/staged_assets_for_world_builder'
    summary = [ordered]@{
        total_records = $scanEntries.Count
        flagged_records = $scanEntries.Count
        roots_scanned = @($candidateRoots | ForEach-Object { Normalize-WindowsPath $_ })
    }
    top_by_category = $topByCategory
}

$summary | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('# World Builder Furniture + Reusable Object Inventory') | Out-Null
$lines.Add('') | Out-Null
$lines.Add(("Generated: {0}" -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffffffK'))) | Out-Null
$lines.Add('') | Out-Null
$lines.Add('## Scan summary') | Out-Null
$lines.Add("- Total flagged furniture/object records: $($scanEntries.Count)") | Out-Null
$lines.Add("- Source asset records from live scans: $($scanEntries.Count)") | Out-Null
$lines.Add("- Zip entries included: $($scanEntries | Where-Object kind -eq 'zip_entry' | Measure-Object | Select-Object -ExpandProperty Count)") | Out-Null
$lines.Add('') | Out-Null
$lines.Add('## Sources scanned') | Out-Null
foreach ($root in $candidateRoots) { $lines.Add("- $root") | Out-Null }
$lines.Add('') | Out-Null
$lines.Add('## Category summary (top picks)') | Out-Null

function Add-CategorySection([string]$name) {
    $lines.Add("### $name") | Out-Null
    $lines.Add('| Source | Name | Path | Path type | Categories | Score | Size MB | World hint |') | Out-Null
    $lines.Add('|---|---|---|---|---|---:|---:|---|') | Out-Null

    $items = $topByCategory[$name]
    if (-not $items -or $items.Count -eq 0) {
        $lines.Add('| _No matches yet_ | - | - | - | - | 0 | 0 | - |') | Out-Null
    } else {
        foreach ($item in $items) {
            $source = $item.source_label
            $catText = if ($item.categories) { $item.categories } else { 'General' }
            $hint = if ($item.world_hint) { $item.world_hint -join ',' } else { 'cross_world' }
            $score = 1
            if ($item.category_scores) {
                $score = [Math]::Max(1, ($item.category_scores.Values | Measure-Object -Maximum).Maximum)
            }
            $lines.Add("| $source | $($item.name) | $($item.path) | $($item.kind) | $catText | $score | $($item.size_mb) | $hint |") | Out-Null
        }
    }
    $lines.Add('') | Out-Null
}

$lines.Add('') | Out-Null
Add-CategorySection 'Seating'
Add-CategorySection 'Surfaces'
Add-CategorySection 'Storage'
Add-CategorySection 'Lighting'
Add-CategorySection 'Doors'
Add-CategorySection 'Architectural'
Add-CategorySection 'Human_Facilities'
Add-CategorySection 'World_Specific_Low'
Add-CategorySection 'World_Plan'

$lines.Add('## World-first reusable priority suggestions') | Out-Null
$lines.Add('') | Out-Null
$lines.Add('### Star Trek / Voyager') | Out-Null
$lines.Add('| Path | Name | Score | Size MB | Why it fits |') | Out-Null
$lines.Add('|---|---|---:|---:|---|') | Out-Null
$star = @($scanEntries | Where-Object { $_.world_hint -contains 'star_trek' } | Sort-Object {[math]::Round($_.size_mb,4)} -Descending | Select-Object -First 60)
foreach ($entry in $star) {
    $score = if ($entry.category_scores.PSObject.Properties['World_Specific_Low']) { $entry.category_scores.World_Specific_Low } else { 1 }
    $lines.Add("| $($entry.path) | $($entry.name) | $score | $([math]::Round($entry.size_mb,4)) | ship/corridor/bridge hint |") | Out-Null
}
$lines.Add('') | Out-Null
$lines.Add('### Paris / Louvre / Museum') | Out-Null
$lines.Add('| Path | Name | Score | Size MB | Why it fits |') | Out-Null
$lines.Add('|---|---|---:|---:|---|') | Out-Null
$paris = @($scanEntries | Where-Object { $_.world_hint -contains 'paris' } | Sort-Object {[math]::Round($_.size_mb,4)} -Descending | Select-Object -First 60)
foreach ($entry in $paris) {
    $score = if ($entry.category_scores.PSObject.Properties['World_Plan']) { $entry.category_scores.World_Plan } else { 1 }
    $lines.Add("| $($entry.path) | $($entry.name) | $score | $([math]::Round($entry.size_mb,4)) | museum/cultural/architectural hint |") | Out-Null
}
$lines.Add('') | Out-Null
$lines.Add('### Cross-world utility objects') | Out-Null
$lines.Add('| Path | Name | Score | Size MB | Categories |') | Out-Null
$lines.Add('|---|---|---:|---:|---|') | Out-Null
$cross = @(
    $scanEntries |
    Where-Object { $_.world_hint -contains 'cross_world' -and $_.categories -match 'Seating|Storage|Surfaces|Lighting|Doors' } |
    Sort-Object -Property @{Expression='size_mb'; Descending=$true} |
    Select-Object -First 40
)
foreach ($entry in $cross) {
    $topScore = 1
    if ($entry.category_scores.Count -gt 0) {
        $topScore = @($entry.category_scores.Values | Measure-Object -Maximum).Maximum
    }
    $lines.Add("| $($entry.path) | $($entry.name) | $topScore | $([math]::Round($entry.size_mb,4)) | $($entry.categories) |") | Out-Null
}

Set-Content -Path $mdPath -Value ($lines -join "`n") -Encoding UTF8

Write-Output "furniture_inventory_json=$jsonPath"
Write-Output "furniture_inventory_md=$mdPath"
