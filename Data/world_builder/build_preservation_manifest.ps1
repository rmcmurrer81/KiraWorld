param()

$ErrorActionPreference = 'Stop'

$desktop = [Environment]::GetFolderPath('Desktop')
$projectRoot = (Get-Location).Path
$stageRoot = Join-Path $projectRoot 'Data/world_builder/staged_assets_for_world_builder'

if (-not (Test-Path $stageRoot)) {
    New-Item -ItemType Directory -Path $stageRoot | Out-Null
}

$assetPairs = @(
    @{ SourceRelative = '3d model 3'; StageFolder = 'desktop_3d_model_3' },
    @{ SourceRelative = '3d model 4'; StageFolder = 'desktop_3d_model_4' },
    @{ SourceRelative = '3d model 5'; StageFolder = 'desktop_3d_model_5' },
    @{ SourceRelative = 'a bunch more'; StageFolder = 'desktop_a_bunch_more' },
    @{ SourceRelative = 'beds models'; StageFolder = 'desktop_beds_models' },
    @{ SourceRelative = '3d models'; StageFolder = 'desktop_3d_models' },
    @{ SourceRelative = '3d models\3D Models Kira World'; StageFolder = 'desktop_3d_models_kira_world' },
    @{ SourceRelative = '3d models\more 3d models'; StageFolder = 'desktop_more_3d_models' },
    @{ SourceRelative = '3d models\some more 3d'; StageFolder = 'desktop_some_more_3d' },
    @{ SourceRelative = '3d models 2'; StageFolder = 'desktop_3d_models_2' },
    @{ SourceRelative = 'enterprise d'; StageFolder = 'desktop_enterprise_d' },
    @{ SourceRelative = 'Ladybug'; StageFolder = 'desktop_Ladybug' },
    @{ SourceRelative = "Marinette's Bedroom"; StageFolder = 'desktop_Marinette_Bedroom' },
    @{ SourceRelative = 'no way home'; StageFolder = 'desktop_no_way_home' },
    @{ SourceRelative = 'real acting'; StageFolder = 'desktop_real_acting' },
    @{ SourceRelative = 'robert avatar base'; StageFolder = 'desktop_robert_avatar_base' },
    @{ SourceRelative = 'school'; StageFolder = 'desktop_school' },
    @{ SourceRelative = 'Spider-Gwen'; StageFolder = 'desktop_Spider_Gwen' },
    @{ SourceRelative = 'voyager details'; StageFolder = 'desktop_voyager_details' }
)

function Get-FileCount([string]$path) {
    if (-not (Test-Path $path)) { return 0 }
    return (Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
}

$rows = @()

foreach ($asset in $assetPairs) {
    $sourcePath = Join-Path $desktop $asset.SourceRelative
    $stagePath = Join-Path $stageRoot $asset.StageFolder

    $exists = Test-Path $sourcePath
    $sourceCount = 0
    $stagedCount = 0

    if ($exists) {
        $sourceCount = Get-FileCount $sourcePath
        if (-not (Test-Path $stagePath)) {
            New-Item -ItemType Directory -Path $stagePath | Out-Null
        }
        Copy-Item -Path (Join-Path $sourcePath '*') -Destination $stagePath -Recurse -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path $stagePath) {
        $stagedCount = Get-FileCount $stagePath
    }

    $rows += [pscustomobject]@{
        desktop_folder = $sourcePath
        staged_folder = $stagePath
        exists = $exists
        source_file_count = $sourceCount
        staged_file_count = $stagedCount
    }
}

$manifestPathJson = Join-Path $projectRoot 'Data/world_builder/model_preservation_manifest.json'
$manifestPathCsv = Join-Path $projectRoot 'Data/world_builder/model_preservation_manifest.csv'

$json = @{
    generated_at = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffffffK')
    folder_count = $rows.Count
    entries = @($rows)
}

$json | ConvertTo-Json -Depth 20 | Set-Content -Path $manifestPathJson -Encoding UTF8
$rows | Export-Csv -NoTypeInformation -Path $manifestPathCsv

[pscustomobject]@{
    manifest_json = $manifestPathJson
    manifest_csv = $manifestPathCsv
    copied_source_folders = ($rows | Where-Object { $_.exists }).Count
    total_rows = $rows.Count
}
