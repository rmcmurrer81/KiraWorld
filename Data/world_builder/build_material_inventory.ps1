param()

$ErrorActionPreference = 'Stop'

$projectRoot = (Get-Location).Path
$desktop = [Environment]::GetFolderPath('Desktop')

$candidateRoots = @(
    (Join-Path $projectRoot 'Data/world_builder/staged_assets_for_world_builder'),
    (Join-Path $projectRoot 'Assets/third_party/intake/3d_models_kira_world'),
    (Join-Path $projectRoot 'Assets/reusable_models'),
    (Join-Path $desktop '3d model 3'),
    (Join-Path $desktop '3d model 4'),
    (Join-Path $desktop '3d model 5'),
    (Join-Path $desktop '3d models'),
    (Join-Path $desktop '3d models 2'),
    (Join-Path $desktop 'Ladybug'),
    (Join-Path $desktop "Marinette's Bedroom"),
    (Join-Path $desktop 'robert avatar base'),
    (Join-Path $desktop 'enterprise d'),
    (Join-Path $desktop 'Spider-Gwen'),
    (Join-Path $desktop 'no way home'),
    (Join-Path $desktop 'voyager details')
) | Where-Object { Test-Path $_ } | Sort-Object -Unique

$scanRoots = @()
foreach ($root in $candidateRoots) {
    $full = (Resolve-Path $root).Path
    $scanRoots += $full
}

$textureExts = @('.png','.jpg','.jpeg','.webp','.tga','.bmp','.gif','.tiff','.tif','.hdr','.exr','.dds','.ktx','.ktx2','.svg','.jfif')
$modelExts = @('.glb','.gltf','.usdz','.fbx','.obj','.dae','.blend','.abc','.ply','.stl','.3ds','.lwo','.x3d','.vrm','.mtl','.gltf#')
$archiveExts = @('.zip')
$allModelExts = $textureExts + $modelExts + $archiveExts

$categoryKeywords = @{
    Brick = @('brick','brickwall','masonry')
    Stone = @('stone','marble','granite','slate','travertin','sandstone','cobblestone','quarry','rock','granito','limestone','andesite')
    Concrete = @('concrete','cement','cast')
    Metal = @('metal','steel','aluminum','aluminium','chrom','iron','titan','tin','bronze','brass','silver')
    Wood = @('wood','timber','oak','pine','maple','plank','beam','frame','bark','grain')
    Tile = @('tile')
    Glass = @('glass','window','transparent','tinted')
    Fabric = @('fabric','cloth','textile','canvas','denim','leather','linen','cotton','fleece')
    Plastic = @('plastic','poly','acrylic','vinyl')
    Vegetation = @('plant','leaf','grass','moss','tree','branch','bush','flower','fern')
    Plaster = @('plaster','stucco','gypsum','mold')
}

$categoryOrder = @('Brick','Stone','Concrete','Metal','Wood','Tile','Glass','Fabric','Plastic','Vegetation','Plaster','Concrete')

$worldHintRules = @{
    paris = @('louvre','paris','museum','palace','cour','courr','tuileries')
    star_trek = @('star', 'trek', 'enterprise', 'voyager', 'lcars', 'u.s.s.', 'uss_', 'uss ') 
    home = @('home', 'residence', 'house', 'kitchen', 'living', 'bedroom', 'bathroom', 'fronthall', 'door')
    notebook = @('parcel', 'street', 'road', 'mall', 'building', 'world', 'exterior', 'exterior')
}

$mapsetRules = @{
    BaseColor = @('basecolor', 'albedo', 'diffuse', 'color', 'colour')
    Metallic = @('metallic', 'metalness', 'roughmetal', 'specular')
    Roughness = @('roughness', 'rough')
    Normal = @('normal', 'nor ', 'norm_', 'normalmap')
    AO = @('_ao', 'ao_', 'ambient', 'ambientocclusion', 'occlusion')
    Height = @('height', 'displacement', 'bump', 'parallax')
    Emissive = @('emissive', 'emission', 'selfilluminate')
    Opacity = @('opacity', 'alpha', 'transparent')
}

function Convert-JsonSafe([object]$obj) {
    return $obj | ConvertTo-Json -Depth 20 -Compress:$false
}

function Normalize-WindowsPath([string]$path) {
    return $path.Replace('/', '\')
}

function Get-SourceLabel([string]$path) {
    $normalized = Normalize-WindowsPath $path
    if ($normalized -match 'staged_assets_for_world_builder\\(?<folder>[^\\]+)') {
        $label = $matches.folder
        return $label -replace '^desktop_', '' -replace '_', ' '
    }

    $leaf = Split-Path $normalized -Leaf
    return $leaf
}

function Get-WorldHints([string]$text) {
    $lower = $text.ToLowerInvariant()
    $hints = [System.Collections.Generic.List[string]]::new()

    foreach ($entry in $worldHintRules.GetEnumerator()) {
        $key = $entry.Key
        foreach ($term in $entry.Value) {
            if ($lower -match [Regex]::Escape($term).Replace('\ ', '\s+') ) {
                if (-not $hints.Contains($key)) {
                    $hints.Add($key)
                }
                break
            }
        }
    }

    return $hints.ToArray()
}

function Get-CategorySignals([string]$text) {
    $lower = $text.ToLowerInvariant()
    $signals = @{}

    foreach ($pair in $categoryKeywords.GetEnumerator()) {
        $name = $pair.Key
        $count = 0
        foreach ($term in $pair.Value) {
            if ($lower -match [regex]::Escape($term)) {
                $count += 1
            }
        }
        if ($count -gt 0) {
            $signals[$name] = $count
        }
    }

    return $signals
}

function Get-MapSets([string]$name) {
    $lower = $name.ToLowerInvariant()
    $sets = [System.Collections.Generic.List[string]]::new()

    foreach ($entry in $mapsetRules.GetEnumerator()) {
        $set = $entry.Key
        foreach ($token in $entry.Value) {
            if ($lower -match [regex]::Escape($token)) {
                if (-not $sets.Contains($set)) {
                    $sets.Add($set)
                }
                break
            }
        }
    }

    if ($sets.Count -eq 0) { return $null }
    return [string[]]($sets | Sort-Object)
}

$canReadZip = $false
try {
    Add-Type -AssemblyName 'System.IO.Compression.FileSystem' | Out-Null
    $canReadZip = $true
} catch {
    Write-Warning 'ZipFile API is unavailable; zip inventories will still track only archive files, not inner entries.'
}

$allEntries = New-Object System.Collections.Generic.List[object]
$packageAggs = [ordered]@{}

function Add-Package([string]$packagePath, [string]$sourceLabel, [string]$sourceRoot, [string[]]$worldHints) {
    if (-not $packageAggs.Contains($packagePath)) {
        $worldHintSet = [System.Collections.Generic.HashSet[string]]::new()
        if ($null -ne $worldHints) {
            foreach ($hint in $worldHints) {
                [void]$worldHintSet.Add([string]$hint)
            }
        }

        $packageAggs[$packagePath] = [ordered]@{
            package = $packagePath
            sourceLabel = $sourceLabel
            sourceRoot = $sourceRoot
            files = 0
            sizeBytes = 0
            categoryCounts = [ordered]@{}
            mapSets = [System.Collections.Generic.HashSet[string]]::new()
            worldHints = $worldHintSet
            kind = 'file'
        }
    }
}

function Record-Entry {
    param(
        [string]$packagePath,
        [string]$sourceLabel,
        [string]$sourceRoot,
        [string]$entryPath,
        [string]$name,
        [string]$extension,
        [long]$sizeBytes,
        [bool]$isTexture,
        [bool]$isModel,
        [string]$kind,
        [hashtable]$categorySignals,
        [string[]]$mapSets,
        [string[]]$worldHints
    )

    $entry = [ordered]@{
        path = $entryPath
        source_root = $sourceRoot
        source_label = $sourceLabel
        name = $name
        extension = $extension
        bytes = $sizeBytes
        is_texture = $isTexture
        is_model = $isModel
        kind = $kind
        categories = ($categorySignals.Keys -join ',')
        category_scores = $categorySignals
        map_sets = $mapSets
        world_hints = $worldHints
        extension_lower = $extension.ToLowerInvariant()
    }

    $allEntries.Add([PSCustomObject]$entry)

    Add-Package -packagePath $packagePath -sourceLabel $sourceLabel -sourceRoot $sourceRoot -worldHints $worldHints
    $agg = $packageAggs[$packagePath]

    $agg.files += 1
    $agg.sizeBytes += $sizeBytes
    foreach ($k in $categorySignals.Keys) {
        if (-not $agg.categoryCounts.Contains($k)) {
            $agg.categoryCounts[$k] = 0
        }
        $agg.categoryCounts[$k] += [int]$categorySignals[$k]
    }

    if ($mapSets) {
        foreach ($set in $mapSets) { [void]$agg.mapSets.Add($set) }
    }
}

foreach ($root in $scanRoots) {
    $sourceLabel = Get-SourceLabel $root
    Write-Output "Scanning source: $root"

    Get-ChildItem -LiteralPath $root -Recurse -File | ForEach-Object {
        $file = $_
        $full = $file.FullName
        $name = $file.Name
        $ext = $file.Extension.ToLowerInvariant()
        $size = $file.Length
        $entryWorldHints = Get-WorldHints ($full)

        if ($archiveExts -contains $ext) {
            if ($canReadZip) {
                try {
                    $archive = [System.IO.Compression.ZipFile]::OpenRead($full)
                    try {
                        $zipEntries = @($archive.Entries)
                        foreach ($zipEntry in $zipEntries) {
                            if ($zipEntry.FullName.EndsWith('/')) { continue }
                            $entryName = [IO.Path]::GetFileName($zipEntry.FullName)
                            if ([string]::IsNullOrWhiteSpace($entryName)) { continue }
                            $entryExt = [IO.Path]::GetExtension($entryName).ToLowerInvariant()
                            if (-not ($allModelExts -contains $entryExt)) { continue }

                            $entrySignals = Get-CategorySignals $zipEntry.FullName
                            if ($entrySignals.Count -eq 0) {
                                $entryWorld = Get-WorldHints (Join-Path $full $zipEntry.FullName)
                                if ($entryWorld -contains 'star_trek' -or $entryWorld -contains 'paris' -or $entryWorld -contains 'home' -or $entryWorld -contains 'notebook') {
                                    $entrySignals = @{ WorldHintOnly = 1 }
                                } else {
                                    continue
                                }
                            }

                            $entryMapSets = if ($entryExt -in $textureExts) { Get-MapSets $entryName } else { $null }
                            $entryIsTexture = $entryExt -in $textureExts
                            $entryIsModel = $entryExt -in $modelExts
                            $entryWorld = Get-WorldHints (Join-Path $full $zipEntry.FullName)

                            $composedPath = "$full::$($zipEntry.FullName)"
                            Record-Entry -packagePath $full -sourceLabel $sourceLabel -sourceRoot $root -entryPath $composedPath -name $entryName -extension $entryExt -sizeBytes $zipEntry.Length -isTexture $entryIsTexture -isModel $entryIsModel -kind 'zip_entry' -categorySignals $entrySignals -mapSets $entryMapSets -worldHints $entryWorld
                        }
                    } finally {
                        $archive.Dispose()
                    }
                } catch {
                    # fallback to zip file metadata entry if unreadable
                    $fallbackSignals = Get-CategorySignals $name
                    if ($fallbackSignals.Count -gt 0) {
                        $mapSets = if ($ext -in $textureExts) { Get-MapSets $name } else { $null }
                        Record-Entry -packagePath $full -sourceLabel $sourceLabel -sourceRoot $root -entryPath $full -name $name -extension $ext -sizeBytes $size -isTexture ($ext -in $textureExts) -isModel ($ext -in $modelExts) -kind 'zip' -categorySignals $fallbackSignals -mapSets $mapSets -worldHints $entryWorldHints
                    }
                    continue
                }
            } else {
                $fallbackSignals = Get-CategorySignals $name
                if ($fallbackSignals.Count -gt 0) {
                    $mapSets = if ($ext -in $textureExts) { Get-MapSets $name } else { $null }
                    Record-Entry -packagePath $full -sourceLabel $sourceLabel -sourceRoot $root -entryPath $full -name $name -extension $ext -sizeBytes $size -isTexture ($ext -in $textureExts) -isModel ($ext -in $modelExts) -kind 'zip' -categorySignals $fallbackSignals -mapSets $mapSets -worldHints $entryWorldHints
                }
                continue
            }
            continue
        }

        if ($allModelExts -notcontains $ext) {
            return
        }

        $entrySignals = Get-CategorySignals $name
        if ($entrySignals.Count -eq 0) {
            if ($entryWorldHints -contains 'star_trek' -or $entryWorldHints -contains 'paris' -or $entryWorldHints -contains 'home' -or $entryWorldHints -contains 'notebook') {
                $entrySignals = @{ WorldHintOnly = 1 }
            } else {
                return
            }
        }
        $entryMapSets = if ($ext -in $textureExts) { Get-MapSets $name } else { $null }

        $isTexture = $ext -in $textureExts
        $isModel = $ext -in $modelExts
        Record-Entry -packagePath $full -sourceLabel $sourceLabel -sourceRoot $root -entryPath $full -name $name -extension $ext -sizeBytes $size -isTexture $isTexture -isModel $isModel -kind 'file' -categorySignals $entrySignals -mapSets $entryMapSets -worldHints $entryWorldHints
    }
}

$materialEntries = @($allEntries | Where-Object {
    $_.is_texture -eq $true -or $_.name.ToLowerInvariant() -match 'texture|material|surface|surface\w*'
})

$topRaw = @($allEntries | Sort-Object bytes -Descending)

$categoryCandidates = @{}
foreach ($cat in $categoryKeywords.Keys) {
    $categoryCandidates[$cat] = New-Object System.Collections.Generic.List[object]
}

foreach ($agg in $packageAggs.Values) {
    if ($agg.files -eq 0) { continue }
    if ($agg.kind -eq $null) { $agg.kind = 'file' }

    $signals = [System.Collections.Generic.List[string]]::new()
    foreach ($key in $agg.categoryCounts.Keys) {
        if ([int]$agg.categoryCounts[$key] -gt 0) {
            $signals.Add([string]::Format('{0}:{1}', $key, $agg.categoryCounts[$key]))
        }
    }

    if ($signals.Count -eq 0) { continue }

    $signals = $signals.ToArray()
    $mapSets = if ($agg.mapSets.Count -gt 0) { [string[]]($agg.mapSets | Sort-Object) } else { @() }
    $source = Get-SourceLabel $agg.package
    if ($agg.package -match 'staged_assets_for_world_builder') {
        $source = Get-SourceLabel $agg.package
    }

    $entry = [ordered]@{
        source = $source
        package = $agg.package
        files = [int]$agg.files
        categorySignals = $signals
        mapSets = $mapSets
        score = [int]$agg.files
        sourceRoot = $agg.sourceRoot
        worldHints = [string[]]($agg.worldHints | Sort-Object -Unique)
    }

    foreach ($cat in $agg.categoryCounts.Keys) {
        $count = $agg.categoryCounts[$cat]
        if ($count -le 0) { continue }
        $catEntry = [PSCustomObject]$entry
        $catEntry | Add-Member -NotePropertyName sourceCategory -NotePropertyValue $cat -Force
        $catEntry | Add-Member -NotePropertyName categoryScore -NotePropertyValue [int]$count -Force
        if (-not $categoryCandidates.Contains($cat)) { $categoryCandidates[$cat] = New-Object System.Collections.Generic.List[object] }
        $categoryCandidates[$cat].Add($catEntry)
    }
}

$finalCategoryCandidates = [ordered]@{}
foreach ($key in $categoryKeywords.Keys) {
    $list = $categoryCandidates[$key]
    $sorted = $list | Sort-Object -Property categoryScore, files -Descending
    $finalCategoryCandidates[$key] = @($sorted)
}

$quickAssets = @()
foreach ($entry in $materialEntries | Sort-Object @{Expression = 'bytes'; Descending = $true}) {
    $mapSetText = if ($entry.map_sets) { [string]::Join(',', [array]$entry.map_sets) } else { '' }
    $sizeMb = if ($entry.bytes) { [math]::Round($entry.bytes / 1MB, 4) } else { 0 }
    $worldHint = if ($entry.world_hints -and $entry.world_hints.Count -gt 0) { $entry.world_hints -join ',' } else { 'general' }

    $quickAssets += [pscustomobject]@{
        name = $entry.name
        source = $entry.source_label
        path = Normalize-WindowsPath $entry.path
        categories = $entry.categories
        kind = $entry.kind
        size_mb = $sizeMb
        map_sets = $mapSetText
        world_hints = $worldHint
    }
}

$quickAssets = $quickAssets | Sort-Object size_mb -Descending | Select-Object -First 120

$scanTimestamp = Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffffffK'
$materialInventoryPath = Join-Path $projectRoot 'Data/world_builder/material_inventory.json'
$materialMdPath = Join-Path $projectRoot 'Data/world_builder/material_inventory.md'
$materialScanPath = Join-Path $projectRoot 'Data/world_builder/material_inventory_scan.json'
$assignmentPath = Join-Path $projectRoot 'Data/world_builder/material_world_assignment_20260706.md'

$materialJson = [ordered]@{
    schema_version = 1
    generated_at = $scanTimestamp
    scanned_roots = @($scanRoots | ForEach-Object { Normalize-WindowsPath $_ })
    category_candidates = $finalCategoryCandidates
    quick_assets = @($quickAssets)
    summary = [ordered]@{
        total_entries = $allEntries.Count
        texture_or_material_entries = $materialEntries.Count
        package_entries = $packageAggs.Count
        total_bytes = ($allEntries | Measure-Object -Property bytes -Sum).Sum
    }
}

$materialJson | ConvertTo-Json -Depth 20 | Set-Content -Path $materialInventoryPath -Encoding UTF8

$scanJson = [ordered]@{
    schema_version = 1
    generated_at = $scanTimestamp
    scanned_roots = @($scanRoots | ForEach-Object { Normalize-WindowsPath $_ })
    entries = @($allEntries | ForEach-Object {
        [ordered]@{
            source_root = $_.source_root
            source_label = $_.source_label
            path = Normalize-WindowsPath $_.path
            name = $_.name
            extension = $_.extension
            bytes = [long]$_.bytes
            kind = $_.kind
            is_texture = [bool]$_.is_texture
            is_model = [bool]$_.is_model
            categories = $_.category_scores
            map_sets = if ($_.map_sets) { $_.map_sets } else { @() }
            world_hints = if ($_.world_hints) { $_.world_hints } else { @() }
        }
    })
}
$scanJson | ConvertTo-Json -Depth 20 | Set-Content -Path $materialScanPath -Encoding UTF8

$mdLines = New-Object System.Collections.Generic.List[string]
$mdLines.Add('# Material Inventory (Updated)') | Out-Null
$mdLines.Add('') | Out-Null
$mdLines.Add("Generated: $scanTimestamp")
$mdLines.Add('') | Out-Null
$mdLines.Add('## Sources scanned') | Out-Null
foreach ($root in $scanRoots) {
    $mdLines.Add("- $(Normalize-WindowsPath $root)") | Out-Null
}
$mdLines.Add('') | Out-Null
$mdLines.Add('## Totals') | Out-Null
$mdLines.Add("- Total scanned entries: $($materialJson.summary.total_entries)")
$mdLines.Add("- Material/texture entries: $($materialJson.summary.texture_or_material_entries)")
$mdLines.Add("- Package candidates: $($materialJson.summary.package_entries)")
$mdLines.Add('') | Out-Null
$mdLines.Add('## Top quick materials (largest files)') | Out-Null
$mdLines.Add('| Source | Name | Path | Size MB | Categories | Map Sets | Kind | World Hints |') | Out-Null
$mdLines.Add('|---|---|---|---:|---|---|---|---|') | Out-Null
foreach ($item in $quickAssets) {
    $maps = if ($item.map_sets) { $item.map_sets } else { '-' }
    $mdLines.Add("| $($item.source) | $($item.name) | $($item.path) | $([math]::Round($item.size_mb,4)) | $($item.categories) | $maps | $($item.kind) | $($item.world_hints) |") | Out-Null
}
$mdLines.Add('') | Out-Null

function Add-CategoryTable([string]$name, [string]$label) {
    $mdLines.Add("### $label") | Out-Null
    $mdLines.Add('| Source | Pack/File | Signals | Map sets | Files | Score |') | Out-Null
    $mdLines.Add('|---|---|---|---|---:|---:|') | Out-Null

    $items = $finalCategoryCandidates[$name]
    if (-not $items) { $items = @() }
    $items = @($items | Select-Object -First 18)
    foreach ($i in $items) {
        $src = $i.source
        $packRoot = [string]$i.sourceRoot
        $pack = $i.package
        if (-not [string]::IsNullOrWhiteSpace($packRoot)) {
            $normPackRoot = $packRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
            if ($pack.StartsWith($normPackRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                $pack = $pack.Substring($normPackRoot.Length).TrimStart('\', '/')
            }
        }
        if ([string]::IsNullOrWhiteSpace($pack)) {
            $pack = [IO.Path]::GetFileName($i.package)
        }
        $sig = ($i.categorySignals -join '<br>')
        if ([string]::IsNullOrWhiteSpace($sig)) { $sig = '-' }
        $maps = if ($i.mapSets.Count -gt 0) { $i.mapSets -join ',' } else { '-' }
        $mdLines.Add("| $src | $([IO.Path]::GetFileName($i.package)) | $sig | $maps | $($i.files) | $($i.categoryScore) |") | Out-Null
    }
    $mdLines.Add('') | Out-Null
}

foreach ($name in @('Brick','Stone','Concrete','Wood','Tile','Plaster','Metal','Glass','Fabric','Vegetation')) {
    Add-CategoryTable $name $name
}

$mdLines.Add('## Notebook world assignment recommendations') | Out-Null
$mdLines.Add('') | Out-Null
$mdLines.Add('Below are the strongest material candidates by world intent and by material family.') | Out-Null
$mdLines.Add('') | Out-Null

function Get-CategoryWeight([object]$entry, [string[]]$targetCategories) {
    $weights = 0
    if (-not $entry.category_scores) { return 0 }
    foreach ($category in $targetCategories) {
        if ($entry.category_scores.ContainsKey($category)) {
            $weights += [int]$entry.category_scores[$category]
        }
    }
    return $weights
}

function Add-WorldMaterialSection {
    param(
        [string]$header,
        [string[]]$worldHints,
        [string]$materialFamily,
        [string[]]$targetCategories
    )

    $worldEntries = @(
        $allEntries |
            Where-Object {
                if (-not $_.world_hints) { return $false }
                $hasWorld = $false
                foreach ($hint in $_.world_hints) {
                    if ($worldHints -contains $hint) { $hasWorld = $true; break }
                }
                return $hasWorld
            }
    )
    $entries = @($worldEntries | ForEach-Object {
        $entry = $_
        $entry | Add-Member -NotePropertyName __weight -NotePropertyValue (Get-CategoryWeight -entry $_ -targetCategories $targetCategories) -Force
        return $entry
    } | Sort-Object -Property @{Expression = '__weight'; Descending = $true}, @{Expression = 'bytes'; Descending = $true} | Where-Object { $_.__weight -gt 0 })
    if (-not $entries -or $entries.Count -eq 0) {
        $entries = @($worldEntries | Sort-Object -Property @{Expression = 'bytes'; Descending = $true} | Select-Object -First 12)
    } else {
        $entries = @($entries | Select-Object -First 12)
    }

    $mdLines.Add("### $header") | Out-Null
    $mdLines.Add('| Material source | Material family | Path | Score | Size MB | Notes |') | Out-Null
    $mdLines.Add('|---|---|---|---:|---:|---|') | Out-Null
    if (-not $entries -or $entries.Count -eq 0) {
        $mdLines.Add('| - | - | - | 0 | 0 | No direct material candidates found |') | Out-Null
    } else {
        foreach ($entry in $entries) {
            $source = if ($entry.source_label) { $entry.source_label } else { '-' }
            $path = Normalize-WindowsPath $entry.path
            $size = if ($entry.bytes) { [math]::Round($entry.bytes / 1MB, 4) } else { 0 }
            $catText = ($entry.category_scores.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name):$($_.Value)" }) -join '<br>'
            $notes = if ($entry.world_hints) { $entry.world_hints -join ',' } else { 'general' }
            $mdLines.Add("| $source | $materialFamily | $path | $($entry.__weight) | $size | $notes |") | Out-Null
        }
    }
    $mdLines.Add('') | Out-Null
}

$materialFamilies = @(
    @{ Name = 'Stone / Ground'; Hints = @('paris'); Categories = @('Stone', 'Tile', 'Plaster') },
    @{ Name = 'Brick / Urban Facade'; Hints = @('paris'); Categories = @('Brick', 'Stone') },
    @{ Name = 'Ship Corridor Shell'; Hints = @('star_trek'); Categories = @('Metal', 'Concrete', 'Glass', 'Plastic') },
    @{ Name = 'LCARS / Interface Panels'; Hints = @('star_trek'); Categories = @('Metal', 'Glass') },
    @{ Name = 'Doors / Windows'; Hints = @('home', 'star_trek', 'paris'); Categories = @('Door', 'Doors', 'Lighting', 'Architectural') }
)

$seenHeaders = [System.Collections.Generic.HashSet[string]]::new()
foreach ($family in $materialFamilies) {
    if (-not $seenHeaders.Add($family.Name)) { continue }
    Add-WorldMaterialSection -header "$($family.Name)" -worldHints $family.Hints -materialFamily $family.Name -targetCategories $family.Categories
}

$mdText = $mdLines -join "`n"
Set-Content -Path $materialMdPath -Value $mdText -Encoding UTF8

$assignmentLines = New-Object System.Collections.Generic.List[string]
$assignmentLines.Add('# Material World Assignment Guide') | Out-Null
$assignmentLines.Add('') | Out-Null
$assignmentLines.Add('Generated: ' + $scanTimestamp) | Out-Null
$assignmentLines.Add('') | Out-Null
$assignmentLines.Add('## Recommended material families by world intent') | Out-Null
$assignmentLines.Add('') | Out-Null

$assignmentLines.Add('### Paris / Louvre') | Out-Null
$assignmentLines.Add('| Family | Source root | Top candidate | Size MB | Family score | World hints |') | Out-Null
$assignmentLines.Add('|---|---|---|---:|---:|---|') | Out-Null
foreach ($family in $materialFamilies | Where-Object { $_.Hints -contains 'paris' }) {
    $familyEntries = @(
        $allEntries |
            Where-Object {
                if (-not $_.world_hints) { return $false }
                $_.world_hints -contains 'paris'
            } |
            ForEach-Object {
                $entry = $_
                $entry | Add-Member -NotePropertyName __weight -NotePropertyValue (Get-CategoryWeight -entry $_ -targetCategories $family.Categories) -Force
                return $entry
            } |
            Sort-Object -Property @{Expression = '__weight'; Descending = $true}, @{Expression = 'bytes'; Descending = $true} |
            Select-Object -First 1
    )

    if (-not $familyEntries -or $familyEntries.Count -eq 0) {
        $assignmentLines.Add("| $($family.Name) | - | - | 0 | 0 | no direct paris/louvre candidate |") | Out-Null
    } else {
        $entry = $familyEntries[0]
        $source = if ($entry.source_label) { $entry.source_label } else { '-' }
        $candidate = $entry.name
        $size = if ($entry.bytes) { [math]::Round($entry.bytes / 1MB, 4) } else { 0 }
        $familyHints = if ($entry.world_hints) { $entry.world_hints -join ',' } else { 'paris' }
        $assignmentLines.Add("| $($family.Name) | $source | $candidate | $size | $($entry.__weight) | $familyHints |") | Out-Null
    }
}
$assignmentLines.Add('') | Out-Null

$assignmentLines.Add('### Star Trek / Voyager') | Out-Null
$assignmentLines.Add('| Family | Source root | Top candidate | Size MB | Family score | World hints |') | Out-Null
$assignmentLines.Add('|---|---|---|---:|---:|---|') | Out-Null
foreach ($family in $materialFamilies | Where-Object { $_.Hints -contains 'star_trek' }) {
    $familyEntries = @(
        $allEntries |
            Where-Object {
                if (-not $_.world_hints) { return $false }
                $_.world_hints -contains 'star_trek'
            } |
            ForEach-Object {
                $entry = $_
                $entry | Add-Member -NotePropertyName __weight -NotePropertyValue (Get-CategoryWeight -entry $_ -targetCategories $family.Categories) -Force
                return $entry
            } |
            Sort-Object -Property @{Expression = '__weight'; Descending = $true}, @{Expression = 'bytes'; Descending = $true} |
            Select-Object -First 1
    )

    if (-not $familyEntries -or $familyEntries.Count -eq 0) {
        $assignmentLines.Add("| $($family.Name) | - | - | 0 | 0 | no direct star_trek candidate |") | Out-Null
    } else {
        $entry = $familyEntries[0]
        $source = if ($entry.source_label) { $entry.source_label } else { '-' }
        $candidate = $entry.name
        $size = if ($entry.bytes) { [math]::Round($entry.bytes / 1MB, 4) } else { 0 }
        $familyHints = if ($entry.world_hints) { $entry.world_hints -join ',' } else { 'star_trek' }
        $assignmentLines.Add("| $($family.Name) | $source | $candidate | $size | $($entry.__weight) | $familyHints |") | Out-Null
    }
}
$assignmentLines.Add('') | Out-Null

$assignmentLines.Add('### Home / general') | Out-Null
$assignmentLines.Add('| Family | Source root | Top candidate | Size MB | Family score | World hints |') | Out-Null
$assignmentLines.Add('|---|---|---|---:|---:|---|') | Out-Null
foreach ($family in $materialFamilies | Where-Object { $_.Hints -contains 'home' }) {
    $familyEntries = @(
        $allEntries |
            Where-Object {
                if (-not $_.world_hints) { return $false }
                $_.world_hints -contains 'home'
            } |
            ForEach-Object {
                $entry = $_
                $entry | Add-Member -NotePropertyName __weight -NotePropertyValue (Get-CategoryWeight -entry $_ -targetCategories $family.Categories) -Force
                return $entry
            } |
            Sort-Object -Property @{Expression = '__weight'; Descending = $true}, @{Expression = 'bytes'; Descending = $true} |
            Select-Object -First 1
    )

    if (-not $familyEntries -or $familyEntries.Count -eq 0) {
        $assignmentLines.Add("| $($family.Name) | - | - | 0 | 0 | no direct home candidate |") | Out-Null
    } else {
        $entry = $familyEntries[0]
        $source = if ($entry.source_label) { $entry.source_label } else { '-' }
        $candidate = $entry.name
        $size = if ($entry.bytes) { [math]::Round($entry.bytes / 1MB, 4) } else { 0 }
        $familyHints = if ($entry.world_hints) { $entry.world_hints -join ',' } else { 'home' }
        $assignmentLines.Add("| $($family.Name) | $source | $candidate | $size | $($entry.__weight) | $familyHints |") | Out-Null
    }
}
$assignmentLines.Add('') | Out-Null

Set-Content -Path $assignmentPath -Value ($assignmentLines -join "`n") -Encoding UTF8

$packageCount = $packageAggs.Count
$entryCount = $allEntries.Count
[pscustomobject]@{
    material_inventory = Normalize-WindowsPath $materialInventoryPath
    material_inventory_md = Normalize-WindowsPath $materialMdPath
    material_scan = Normalize-WindowsPath $materialScanPath
    assignment_guide = Normalize-WindowsPath $assignmentPath
    package_count = $packageCount
    entry_count = $entryCount
}
