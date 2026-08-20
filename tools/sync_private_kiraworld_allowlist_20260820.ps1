[CmdletBinding()]
param(
    [string]$SourceRoot = 'C:\Users\robmc\Kira',
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SourceRoot = (Resolve-Path -LiteralPath $SourceRoot).Path
$RepositoryRoot = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$gitDir = Join-Path $RepositoryRoot '.git'
if (-not (Test-Path -LiteralPath $gitDir -PathType Container)) {
    throw "RepositoryRoot is not the KiraWorld checkout: $RepositoryRoot"
}

$deliveryRoot = Join-Path $RepositoryRoot 'private_delivery'
$bundleRoot = Join-Path $deliveryRoot 'source_tree'
New-Item -ItemType Directory -Path $bundleRoot -Force | Out-Null

$copied = [System.Collections.Generic.List[object]]::new()
$copiedDestinations = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
$repositoryFilesUpdated = [System.Collections.Generic.List[string]]::new()

function Convert-ToForwardSlash([string]$Path) {
    return $Path.Replace('\', '/')
}

function Test-ForbiddenRelativePath([string]$RelativePath) {
    $normalized = Convert-ToForwardSlash $RelativePath
    if ($normalized -match '(?i)(^|/)(?:node_modules|dist|__pycache__|\.pytest_cache|\.venv|venv|tmp|_tmp[^/]*)($|/)') {
        return $true
    }
    if ($normalized -match '(?i)(^|/)[^/]*(?:codex|handoff)[^/]*($|/)') {
        return $true
    }
    if ($normalized -match '(?i)(?:\.log|\.pid|\.tmp|\.pyc)$') {
        return $true
    }
    if ($normalized -match '(?i)(?:\.bak(?:_|\.|$)|~$)') {
        return $true
    }
    if ($normalized -match '(?i)(?:online_source\.info\.json)$') {
        return $true
    }
    return $false
}

function Copy-RelativeFile {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRelative,
        [string]$DestinationRelative = $SourceRelative,
        [switch]$Optional
    )

    if (Test-ForbiddenRelativePath $SourceRelative) {
        throw "Refusing forbidden source path: $SourceRelative"
    }
    if (Test-ForbiddenRelativePath $DestinationRelative) {
        throw "Refusing forbidden destination path: $DestinationRelative"
    }

    $sourcePath = Join-Path $SourceRoot $SourceRelative
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        if ($Optional) { return }
        throw "Required source file is missing: $sourcePath"
    }

    $destinationPath = Join-Path $bundleRoot $DestinationRelative
    $destinationParent = Split-Path -Parent $destinationPath
    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force

    $destinationKey = Convert-ToForwardSlash $DestinationRelative
    if ($copiedDestinations.Add($destinationKey)) {
        $item = Get-Item -LiteralPath $destinationPath
        $copied.Add([pscustomobject]@{
            source_path = Convert-ToForwardSlash $SourceRelative
            mirror_path = $destinationKey
            bytes = [int64]$item.Length
            sha256 = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
}

function Copy-RelativeTree {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRelative,
        [string]$DestinationRelative = $SourceRelative,
        [string[]]$AllowedExtensions = @(),
        [string]$AdditionalSkipRegex = ''
    )

    $sourceDirectory = Join-Path $SourceRoot $SourceRelative
    if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) {
        throw "Required source directory is missing: $sourceDirectory"
    }

    $allowed = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($extension in $AllowedExtensions) {
        [void]$allowed.Add($extension)
    }

    Get-ChildItem -LiteralPath $sourceDirectory -File -Recurse -Force | ForEach-Object {
        $insideTree = [System.IO.Path]::GetRelativePath($sourceDirectory, $_.FullName)
        $sourceFileRelative = Join-Path $SourceRelative $insideTree
        $destinationFileRelative = Join-Path $DestinationRelative $insideTree

        if (Test-ForbiddenRelativePath $sourceFileRelative) { return }
        if ($AdditionalSkipRegex -and (Convert-ToForwardSlash $insideTree) -match $AdditionalSkipRegex) { return }
        if ($allowed.Count -gt 0 -and -not $allowed.Contains($_.Extension)) { return }
        if (($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { return }

        Copy-RelativeFile -SourceRelative $sourceFileRelative -DestinationRelative $destinationFileRelative
    }
}

function Copy-TopLevelFiles([string]$SourceRelative) {
    $sourceDirectory = Join-Path $SourceRoot $SourceRelative
    if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) {
        throw "Required source directory is missing: $sourceDirectory"
    }
    Get-ChildItem -LiteralPath $sourceDirectory -File -Force | ForEach-Object {
        Copy-RelativeFile -SourceRelative (Join-Path $SourceRelative $_.Name)
    }
}

function Copy-MatchingFiles {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRelative,
        [Parameter(Mandatory = $true)][string]$Filter
    )
    $sourceDirectory = Join-Path $SourceRoot $SourceRelative
    Get-ChildItem -LiteralPath $sourceDirectory -File -Filter $Filter -Force | ForEach-Object {
        Copy-RelativeFile -SourceRelative (Join-Path $SourceRelative $_.Name)
    }
}

function Get-NormalizedText([string]$Path) {
    $text = [System.IO.File]::ReadAllText($Path)
    return $text.Replace("`r`n", "`n").Replace("`r", "`n")
}

function Sync-TrackedRepositoryFile([string]$RepositoryRelative) {
    if (Test-ForbiddenRelativePath $RepositoryRelative) { return }

    $sourcePath = Join-Path $SourceRoot $RepositoryRelative
    $destinationPath = Join-Path $RepositoryRoot $RepositoryRelative
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { return }
    if (-not (Test-Path -LiteralPath $destinationPath -PathType Leaf)) { return }

    $textExtensions = @(
        '.bat', '.c', '.cc', '.cfg', '.cmd', '.cpp', '.css', '.csv', '.h',
        '.hpp', '.html', '.ini', '.js', '.json', '.jsx', '.md', '.mjs',
        '.ps1', '.py', '.sh', '.toml', '.ts', '.tsx', '.tsv', '.txt',
        '.xml', '.yaml', '.yml'
    )
    $extension = [System.IO.Path]::GetExtension($sourcePath).ToLowerInvariant()
    $changed = $false
    if ($textExtensions -contains $extension) {
        $sourceNormalized = Get-NormalizedText $sourcePath
        $destinationNormalized = Get-NormalizedText $destinationPath
        if ($sourceNormalized -cne $destinationNormalized) {
            [System.IO.File]::WriteAllText(
                $destinationPath,
                $sourceNormalized,
                [System.Text.UTF8Encoding]::new($false)
            )
            $changed = $true
        }
    }
    else {
        $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
        $destinationHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash
        if ($sourceHash -cne $destinationHash) {
            Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
            $changed = $true
        }
    }

    if ($changed) {
        $repositoryFilesUpdated.Add((Convert-ToForwardSlash $RepositoryRelative))
    }
}

function Sync-TrackedRepositoryPrefix([string]$Prefix) {
    $tracked = @(& git -c core.quotepath=false -C $RepositoryRoot ls-files -- $Prefix)
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-files failed for tracked prefix: $Prefix"
    }
    foreach ($path in $tracked) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        Sync-TrackedRepositoryFile ($path.Replace('/', '\'))
    }
}

# Existing repository code remains in its normal paths. Refresh only files that
# Git already tracks under the approved framework areas, so this operation can
# replace a changed file without broadening the repository to neighboring
# resident data. Line endings are normalized to the repository's LF form to
# avoid meaningless whole-file churn.
foreach ($prefix in @('Core', 'tools', 'Avatar/avatar_builder', 'System/Docs')) {
    Sync-TrackedRepositoryPrefix $prefix
}
foreach ($rootFile in @(
    'Create_Kira_World_Shell_Desktop_Shortcut.bat',
    'Start_Kira_World_Shell.bat',
    'Start_TemporaryAI_Candidate_Builder.bat',
    'Start_TemporaryAI_Control_Center.bat',
    'Start_Kira_Avatar_Builder_Workspace.bat',
    'Start_Kira_World_Builder_Workspace.bat'
)) {
    Sync-TrackedRepositoryFile $rootFile
}

# Kira World shell/runtime support. The shell source itself is already current at
# the repository root.
foreach ($name in @('index.html', 'package.json', 'package-lock.json', 'vite.config.js')) {
    Copy-RelativeFile "Avatar\runtime3d\$name"
}
Copy-RelativeTree 'Avatar\runtime3d\src'
Copy-RelativeFile 'Data\runtime\kira_world_shell_state.json'
Copy-RelativeFile 'Assets\icons\kira_world_shell_logo.png' -Optional
Copy-RelativeFile 'Assets\icons\kira_world_shell_logo.ico' -Optional

# Current Home World source and build. The dependency tree and duplicate dist
# output are intentionally excluded; public/models is the canonical GLB set.
$homeRoot = 'Data\world_builds\notebook_worlds\home_world'
Copy-RelativeTree "$homeRoot\blueprints"
Copy-RelativeTree "$homeRoot\config"
$homePreview = "$homeRoot\builds\home_world_main_house_20260630_223000\preview"
foreach ($name in @('index.html', 'package.json', 'package-lock.json', 'vite.config.js')) {
    Copy-RelativeFile "$homePreview\$name"
}
Copy-RelativeTree "$homePreview\src"
Copy-RelativeTree "$homePreview\public\models"
Copy-RelativeFile 'Data\world_builds\notebook_world_index.json'

# Generic TemporaryAI Creator framework. Named examples not authorized for this
# upload are excluded even when they are small templates.
Copy-RelativeTree 'TemporaryAI\config'
Copy-RelativeTree 'TemporaryAI\docs'
Copy-RelativeTree 'TemporaryAI\profiles'
Copy-RelativeTree 'TemporaryAI\templates' -AdditionalSkipRegex '(?i)(^|/)example_wednesday[^/]*$'

$requestedCandidates = @(
    'peter_parker_spider_man_no_way_home_final_suit',
    'ladybug_marinette_expanded_smoke',
    'kathryn_merteuil_kathryn_merteuil_20260605_213017'
)
foreach ($candidate in $requestedCandidates) {
    Copy-TopLevelFiles "TemporaryAI\candidates\$candidate"
}
Copy-RelativeTree 'TemporaryAI\candidates\peter_parker_spider_man_no_way_home_final_suit\references' -AllowedExtensions @('.json', '.md', '.txt')
Copy-RelativeTree 'TemporaryAI\candidates\ladybug_marinette_expanded_smoke\workbench\outputs' -AllowedExtensions @('.json', '.md', '.doc', '.txt')
Copy-RelativeTree 'TemporaryAI\candidates\ladybug_marinette_expanded_smoke\workbench\runtime' -AllowedExtensions @('.json', '.md', '.txt')
Copy-RelativeTree 'TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs' -AllowedExtensions @('.json', '.md', '.txt')

$expertCandidates = @(
    'emily_carter_ai_and_computer_programming_expert_20260605_220651',
    'jessica_hale_robotics_engineer_20260611_041314',
    'laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530',
    'ryan_hale_quantum_mechanics_expert_20260608_200749',
    'sarah_bennett_enterainment_pr_agent_expert_20260606_171637'
)
foreach ($expert in $expertCandidates) {
    Copy-TopLevelFiles "TemporaryAI\candidates\$expert"
}

# Bounded historical-education candidate requested for private review. This is
# text/status material only: the candidate remains pending owner review and is
# not activated. Workbench/recovery files, raw media, generated voice, and
# movement/runtime state are deliberately outside this allowlist.
$historicalEducationCandidate = 'h_h_holmes_h_h_holmes_20260605_221432'
$historicalEducationCandidateTopLevelFiles = @(
    'activation_plan.json',
    'creation_request.json',
    'online_research_summary.json',
    'qwen3_tts_original_voice_design_evaluation_request_v2.json',
    'README.md',
    'reliable_source_pack.json',
    'source_research_queue.json',
    'temporary_ai_profile.json',
    'voice_discovery_index.json',
    'voice_discovery_request.json'
)
foreach ($name in $historicalEducationCandidateTopLevelFiles) {
    Copy-RelativeFile "TemporaryAI\candidates\$historicalEducationCandidate\$name"
}
Copy-RelativeFile "TemporaryAI\creation_requests\$historicalEducationCandidate\control_center_creation_request.json"
Copy-RelativeFile "Avatar\temp_ai\$historicalEducationCandidate\avatar_profile.json"
Copy-RelativeFile "Avatar\temp_ai\$historicalEducationCandidate\avatar_request.json"
Copy-RelativeFile 'Voice\profiles\temp_ai\h_h_holmes_voice_profile.json'
Copy-RelativeFile 'Data\school\source_packs\kira_h_h_holmes_chicago_true_crime_source_pack_20260515.json'
Copy-RelativeFile 'Data\temporary_ai_character_validation\20260726\h_h_holmes_representative_transcript.json'

# Requested generated avatar artifacts. Raw downloaded reference imagery and
# source models are deliberately not mirrored.
foreach ($candidate in $requestedCandidates) {
    Copy-TopLevelFiles "Avatar\temp_ai\$candidate"
    $generatedBody = "Avatar\temp_ai\$candidate\generated_body"
    if (Test-Path -LiteralPath (Join-Path $SourceRoot $generatedBody)) {
        Copy-RelativeTree $generatedBody
    }
    $outputs = "Avatar\temp_ai\$candidate\outputs"
    if (Test-Path -LiteralPath (Join-Path $SourceRoot $outputs)) {
        Copy-RelativeTree $outputs
    }
}
Copy-RelativeTree 'Avatar\models\temp_ai\peter_parker_spider_man_no_way_home_final_suit'
Copy-RelativeTree 'Avatar\models\temp_ai\ladybug_marinette_expanded_smoke'

# Existing synthetic voice outputs and their honest draft/not-cleared profiles.
# Raw show/movie/online reference audio and source video are excluded.
Copy-RelativeTree 'Voice\generated\temp_ai\peter_parker'
Copy-RelativeTree 'Voice\generated\temp_ai\ladybug'
Copy-RelativeTree 'Voice\generated\temp_ai\kathryn_merteuil'
Copy-RelativeFile 'Voice\profiles\temp_ai\peter_parker_voice_profile.json'
Copy-RelativeFile 'Voice\profiles\temp_ai\ladybug_voice_profile.json'
Copy-RelativeFile 'Voice\profiles\temp_ai\kathryn_merteuil_voice_profile.json'

# Lisa's dedicated identity/backstory/core-memory files and the bounded Kira/Lisa
# shared continuity requested by the owner. Unrelated Lisa Loeb media, reading
# chunks, and memories centered on other named people are not mirrored.
Copy-RelativeTree 'Lisa'
Copy-RelativeFile 'Data\memories_lisa.json'
Copy-MatchingFiles 'Data\memory_seeds' 'lisa_core_*.draft.json'
Copy-RelativeFile 'Data\memory_seeds\kira_core_002_lisa_approaches_first.draft.json' -Optional
Copy-MatchingFiles 'Data\memory_seeds' 'shared_kira_lisa_*.draft.json'
Copy-RelativeFile 'Data\backstory\candidates\kira_lisa_slumber_backstory_candidates_20260516.md' -Optional
Copy-RelativeFile 'Data\memory_reflection\kira_lisa_college_present_day_reflection_context_v1.json' -Optional
Copy-MatchingFiles 'Data\memory_reconstruction_worlds' 'shared_kira_lisa_*.draft.json'
Copy-RelativeFile 'Data\memory_reconstruction_worlds\lisa_grounded_late_001.draft.json' -Optional
Copy-RelativeFile 'Data\memory_promotion\candidates\shared_kira_lisa_adult_relationship_slumber_20260516.draft.json' -Optional
Copy-RelativeFile 'Data\memory_promotion\candidates\lisa_first_talk_candidate_template.json' -Optional
Copy-RelativeFile 'Data\school\continuity\kira_lisa_slumber_party_soft_memory_digest_20260516.json' -Optional
Copy-RelativeFile 'Data\relationships\kira_lisa_current_state.json' -Optional
Copy-RelativeFile 'Data\relationships\stages\kira_lisa_stage_track.json' -Optional

# Portable World Builder data and schemas. Multi-gigabyte asset/reference
# libraries, caches, audits, sessions, and unrelated project worlds stay local.
Copy-TopLevelFiles 'Data\world_builder'
Copy-RelativeTree 'Data\world_builder\preview_runtime'
Copy-RelativeFile 'Data\world_builder\roadmap\world_builder_roadmap_20260714_spa_campus_notebook_worlds.json'
Copy-RelativeFile 'Data\schemas\memory_reconstruction_world_schema.json'
Copy-RelativeFile 'Data\schemas\notebook_world_collection_schema.json'
Copy-RelativeFile 'Data\schemas\notebook_world_request_schema.json'
Copy-RelativeFile 'Data\world_reconstruction\place_reconstruction_policy.json'

# System/Docs already exists in the repository. Mirror only source documents that
# are missing from the repository root, and never mirror a Codex/handoff file.
$docsSource = Join-Path $SourceRoot 'System\Docs'
$docExtensions = @('.md', '.pdf', '.docx')
Get-ChildItem -LiteralPath $docsSource -File -Recurse -Force | ForEach-Object {
    if ($docExtensions -notcontains $_.Extension.ToLowerInvariant()) { return }
    $insideDocs = [System.IO.Path]::GetRelativePath($docsSource, $_.FullName)
    $sourceRelative = Join-Path 'System\Docs' $insideDocs
    if (Test-ForbiddenRelativePath $sourceRelative) { return }
    if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot $sourceRelative))) {
        Copy-RelativeFile $sourceRelative
    }
}

# Verified U.S.-public-domain scans. Keep original subject folders below an
# explicit public-domain selection boundary.
$publicDomainFiles = @(
    'Data\library\novels\historical_romance\samantha_at_saratoga_or_flirtin_with_fashion.pdf',
    'Data\library\science\biology_and_chemistry\naturalhistoryf00smitgoog.pdf',
    'Data\library\novels\deedsofheroismbr00elwy.pdf',
    'Data\library\history\chicago\chicago_1917.pdf',
    'Data\library\history\chicago\reminiscences_of_early_chicago_and_vicinity.pdf',
    'Data\library\history\civil_war\a_history_of_the_civil_war_1861_65_and_the_causes_that_led_up_to_the_great_conflict.pdf',
    'Data\library\history\civil_war\civilwarstories00newy.pdf',
    'Data\library\history\united_states\new_jersey\newark\historicnewarkco00newa.pdf',
    'Data\library\psychology_and_relationships\psychology\studiesinpsychol00neet.pdf',
    'Data\library\reference\life_skills\lifehowtoenjoyit00fowl.pdf'
)
foreach ($sourceRelative in $publicDomainFiles) {
    $insideLibrary = $sourceRelative.Substring('Data\library\'.Length)
    Copy-RelativeFile $sourceRelative "Data\library\public_domain_selection\$insideLibrary"
}

# A deliberately small, isolated private-reference script set. These are not
# represented as public-domain or redistribution-cleared.
$privateScripts = @(
    'Data\library\scripts\spider_man\555726778-Spider-Man-No-Way-Home-Read-the-Screenplay.pdf',
    'Data\library\scripts\miraculous_ladybug\season_1\844482771-LB-106-Mister-Pigeon-Locked-script-11-13-13.pdf',
    'Data\library\scripts\miraculous_ladybug\season_3\855858415-MLB-319-Timetagger-Locked-script-17-09-17-VA.pdf'
)
foreach ($sourceRelative in $privateScripts) {
    $insideScripts = $sourceRelative.Substring('Data\library\scripts\'.Length)
    Copy-RelativeFile $sourceRelative "Data\library\private_reference_scripts\$insideScripts"
}

# Reconcile the generated mirror after the allowlist has been evaluated. A file
# removed or renamed at the source, or dropped from the allowlist, must not
# silently survive. Deletion is limited to exact files already beneath the
# resolved generated source_tree root; source files and repository-root files
# are never deleted here.
$resolvedBundleRoot = [System.IO.Path]::GetFullPath($bundleRoot).TrimEnd('\')
Get-ChildItem -LiteralPath $bundleRoot -File -Recurse -Force | ForEach-Object {
    $relative = Convert-ToForwardSlash ([System.IO.Path]::GetRelativePath($bundleRoot, $_.FullName))
    if ($copiedDestinations.Contains($relative)) { return }

    $resolvedCandidate = [System.IO.Path]::GetFullPath($_.FullName)
    $requiredPrefix = $resolvedBundleRoot + '\'
    if (-not $resolvedCandidate.StartsWith($requiredPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing stale-file deletion outside generated mirror: $resolvedCandidate"
    }
    Remove-Item -LiteralPath $resolvedCandidate
}

# Generate a deterministic inventory of the mirrored source tree. These writes
# are mechanical build outputs; they contain relative paths only.
$inventoryItems = @($copied | Sort-Object mirror_path)
$inventory = [ordered]@{
    schema_version = 'kiraworld-private-source-mirror-v1'
    generated_utc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    source_root_label = 'resident-private-kira-workspace'
    file_count = $inventoryItems.Count
    total_bytes = [int64](($inventoryItems | Measure-Object -Property bytes -Sum).Sum)
    files = $inventoryItems
}
$inventoryPath = Join-Path $deliveryRoot 'PACKAGE_INVENTORY.json'
$inventory | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $inventoryPath -Encoding utf8

$checksumLines = $inventoryItems | ForEach-Object {
    '{0}  source_tree/{1}' -f $_.sha256, $_.mirror_path
}
$checksumPath = Join-Path $deliveryRoot 'SHA256SUMS.txt'
$checksumLines | Set-Content -LiteralPath $checksumPath -Encoding utf8

$summary = [ordered]@{
    delivery_root = $deliveryRoot
    copied_files = $inventoryItems.Count
    copied_bytes = $inventory.total_bytes
    repository_files_updated = @($repositoryFilesUpdated | Sort-Object)
    inventory = $inventoryPath
    checksums = $checksumPath
}
$summary | ConvertTo-Json -Depth 3
