param(
    [ValidateSet('PreSeal', 'PostSeal')]
    [string]$Phase = 'PreSeal'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourcePath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r19.c'
$anchorPath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r19_identity_anchor.h'
$contractPath = Join-Path $root 'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_python_controller_validation_v3r19.json'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r19_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$futureAudit = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r19_fresh_static_audit/attempt_01'
$sealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r19_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$v3r18SourcePath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r18.c'
$v3r18SealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}
function Assert-Contains([string]$Text, [string]$Needle, [string]$Message) {
    Assert-True ($Text.IndexOf($Needle, [StringComparison]::Ordinal) -ge 0) $Message
}
function Sha([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$source = [IO.File]::ReadAllText($sourcePath)
$anchor = [IO.File]::ReadAllText($anchorPath)
$contractText = [IO.File]::ReadAllText($contractPath)
$control = [IO.File]::ReadAllText($controlPath)
$v3r18Source = [IO.File]::ReadAllText($v3r18SourcePath)
$contract = $contractText | ConvertFrom-Json

Assert-True ($contract.schema -eq 'kira.avatar.r25.foundation_afes_python_controller_validation.v3r19') 'schema drift'
Assert-True ($contract.predecessor.status -eq 'REJECTED_NO_EXECUTION_AUTHORITY') 'v3r18 rejection not exact'
Assert-True ($contract.predecessor.rejection_checkpoint_sha256 -eq 'c8f95026d8549fbd12850c3c09011b9a0644050c56bdb624b6a226d876c52db9') 'v3r18 rejection checkpoint drift'
Assert-True ($contract.granular_contract_gate.bytes -eq 6174) 'contract size binding drift'
Assert-True ($contract.granular_contract_gate.sha256 -eq 'ad33386d767b516425dcbed073e22dfc9747a963a64dc5d205483d210acac79d') 'contract digest drift'
Assert-True ($contract.stop_before -contains '_build_execution_plan') 'plan-builder stop missing'
Assert-True ($contract.stop_before -contains 'AFES') 'AFES stop missing'
Assert-True ($contract.stop_before -contains 'Blender') 'Blender stop missing'
Assert-True ($contract.stop_before -contains 'body') 'body stop missing'

Assert-Contains $source 'FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE' 'granular share mode absent'
Assert-Contains $source 'FILE_FLAG_OPEN_REPARSE_POINT' 'reparse-point defense absent'
Assert-Contains $source 'open_contract_granular(&contract_telemetry' 'granular gate not invoked'
Assert-Contains $source 'kira_r25_foundation_afes_python_controller_validation_v3r15.json' 'exact v3r15 target contract absent'
Assert-Contains $source 'V3R19_TARGET_CONTRACT_BYTES' 'target size uses candidate contract binding'
Assert-Contains $source 'V3R19_TARGET_CONTRACT_SHA256' 'target digest uses candidate contract binding'
Assert-Contains $source 'finish_contract_granular(&contract_telemetry' 'same handle not terminally rechecked'
Assert-Contains $source 'memcmp(telemetry->snapshot_one_sha256, telemetry->snapshot_two_sha256' 'double snapshot comparison absent'
Assert-Contains $source 'memcmp(telemetry->snapshot_two_sha256, telemetry->final_sha256' 'final snapshot comparison absent'
Assert-Contains $source 'memcpy(&record.contract, contract, sizeof(record.contract))' 'durable granular telemetry absent'
Assert-Contains $source 'memcpy(record.manifest_sha256, reservation->manifest_sha256, SHA_BYTES)' 'terminal receipt can be blocked by post-failure path reopen'
Assert-Contains $source 'bytes != sizeof(*reservation) + sizeof(record)' 'exact two-record receipt size absent'
Assert-Contains $source 'trailing_bytes != 0U' 'trailing receipt bytes not rejected'
Assert-Contains $source 'telemetry->passed_mask != ((1U << (CONTRACT_GATE_COUNT - 1U)) - 1U)' 'granular full-mask gate absent'
Assert-Contains $source 'CreateFileW(EVIDENCE_PATH, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,' 'evidence CREATE_NEW path absent'
Assert-Contains $source 'NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH' 'CREATE_NEW write-through absent'
Assert-Contains $source 'LoadLibraryExW(PYTHON_DLL_PATH, NULL,' 'delayed exact Python DLL load absent'
Assert-Contains $source 'PyConfig_InitIsolatedConfig' 'isolated interpreter absent'
Assert-Contains $source '"_build_execution_plan", "_validate_child_payload", "_compare_pair",' 'five-export tuple absent'
Assert-Contains $source 'if _c.get(''schema'')!=''kira.avatar.r25.foundation_afes_locked_pair_execution.v3r9''' 'strict projection absent'
Assert-Contains $source 'api.finalize()' 'Python finalization absent'
Assert-Contains $source 'FreeLibrary(api.module)' 'Python DLL unload absent'
Assert-Contains $source 'CreateToolhelp32Snapshot(' 'post-release process module inventory absent'
Assert-Contains $source 'TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32' 'module inventory scope absent'
Assert-Contains $source 'entry.hModule == old_module' 'old module base absence gate absent'
Assert-Contains $source '_wcsicmp(entry.szExePath, PYTHON_DLL_PATH) == 0' 'exact Python path absence gate absent'
Assert-Contains $source 'memcpy(&record.unload, unload, sizeof(record.unload))' 'durable unload telemetry absent'
Assert-Contains $source 'memcpy(record.authority_contract_sha256, reservation->authority_contract_sha256, SHA_BYTES)' 'authority contract digest absent from terminal record'
Assert-Contains $source 'authority_contract_volume' 'authority contract file identity absent from records'
Assert-Contains $source 'memchr(audit, ''\0'', audit_bytes)' 'whole-audit embedded NUL rejection absent'
Assert-Contains $source 'lower_hex_exact(values[index], value_lengths[index])' 'raw-length digest grammar absent'
Assert-Contains $source 'auditor_exact(values[1], value_lengths[1])' 'canonical auditor grammar absent'
Assert-Contains $source 'V3R17_RUN_OUTCOME_PATH' 'V3r17 run outcome not bound'
Assert-Contains $source 'V3R17_POST_RUN_PATH' 'V3r17 post-run checkpoint not bound'
Assert-Contains $source 'ACCEPTED_FOR_ONE_BOUNDED_GRANULAR_CONTRACT_AND_PYTHON_CONTROLLER_VALIDATION_V3R19_ONLY' 'future audit decision drift'
Assert-Contains $source 'kira_r25_afes_python_controller_validation_v3r19_fresh_static_audit' 'exact future audit root absent'

$reservation = $source.IndexOf('evidence = CreateFileW(EVIDENCE_PATH', [StringComparison]::Ordinal)
$authorityLock = $source.IndexOf('if (!lock_file(&authority_contract))', [StringComparison]::Ordinal)
$auditGate = $source.IndexOf('if (!verify_audit(self_sha, audit_sha)', [StringComparison]::Ordinal)
$granular = $source.IndexOf('stage_ok = open_contract_granular(', [StringComparison]::Ordinal)
$retained = $source.IndexOf('if (!lock_file(&retained[index]))', [StringComparison]::Ordinal)
$python = $source.IndexOf('stage_ok && run_python_validation(', [StringComparison]::Ordinal)
Assert-True ($reservation -ge 0 -and $reservation -lt $granular -and $granular -lt $retained -and $retained -lt $python) 'reservation/granular/retained/Python ordering drift'
Assert-True ($authorityLock -ge 0 -and $authorityLock -lt $auditGate -and $auditGate -lt $reservation) 'authority-contract/audit/reservation ordering drift'

$pythonFunction = $source.Substring($source.IndexOf('static int run_python_validation(', [StringComparison]::Ordinal))
$finalizeOrder = $pythonFunction.IndexOf('unload->finalize_called = 1U', [StringComparison]::Ordinal)
$releaseOrder = $pythonFunction.IndexOf('FreeLibrary(api.module)', [StringComparison]::Ordinal)
$absenceOrder = $pythonFunction.IndexOf('prove_python_module_absent(old_module, unload)', [StringComparison]::Ordinal)
$evidenceOrder = $source.LastIndexOf('append_line(evidence, E_FINALIZED)', [StringComparison]::Ordinal)
Assert-True ($finalizeOrder -ge 0 -and $finalizeOrder -lt $releaseOrder -and $releaseOrder -lt $absenceOrder) 'finalize/release/absence order drift'
Assert-True ($evidenceOrder -gt $source.IndexOf('prove_python_module_absent(old_module, unload)', [StringComparison]::Ordinal)) 'E_FINALIZED precedes absence proof'

$v3r18ContractTokens = ([regex]::Matches($v3r18Source, '(?<![A-Z0-9_])CONTRACT_PATH(?![A-Z0-9_])')).Count
$v3r19ContractTokens = ([regex]::Matches($source, '(?<![A-Z0-9_])CONTRACT_PATH(?![A-Z0-9_])')).Count
Assert-True ($v3r18ContractTokens -eq 1) 'V3r18 contract-path negative control did not reproduce'
Assert-True ($v3r19ContractTokens -ge 2) 'V3r19 authority contract is not runtime-bound'
Assert-True ($v3r18Source.IndexOf('strcmp(values[0], expected[0])', [StringComparison]::Ordinal) -ge 0) 'V3r18 C-string negative control did not reproduce'
Assert-True ($source.IndexOf('strcmp(values[0], expected[0])', [StringComparison]::Ordinal) -lt 0) 'V3r19 still uses unsafe audit decision strcmp'
Assert-True (([regex]::Matches($source, '\{V3R18_[A-Z0-9_]+_PATH, V3R19_V3R18_')).Count -eq 14) 'complete V3r18 rejected closure is not runtime-bound'

foreach ($forbidden in @('CreateProcessW(', 'CreateProcessA(', 'ShellExecuteW(', 'ShellExecuteA(', 'WinExec(', 'system(', 'PyImport_ImportModule')) {
    Assert-True ($source.IndexOf($forbidden, [StringComparison]::Ordinal) -lt 0) "forbidden production primitive: $forbidden"
}
Assert-True (([regex]::Matches($source, [regex]::Escape('api->dict_get(globals, expected[index])'))).Count -eq 1) 'callable export verification drift'
Assert-True ($source.IndexOf('api.call(', [StringComparison]::Ordinal) -lt 0) 'controller callable invocation introduced'
Assert-Contains $control 'STOP_BEFORE_PLAN_BUILDER_BROKER_PROCESS_AFES_BLENDER_BODY_SAVE_RENDER' 'control stop boundary drift'
Assert-True (-not (Test-Path -LiteralPath $futureAudit)) 'future audit root must be absent at author freeze'
if ($Phase -eq 'PreSeal') {
    Assert-True (-not (Test-Path -LiteralPath $sealPath)) 'V3r19 seal must be absent during PreSeal'
}

# In-memory hostile mutations must fail the exact static predicates.
$mutatedContract = $contractText.Replace('"reservation_first": true', '"reservation_first": false')
Assert-True ($mutatedContract -ne $contractText) 'mutation setup failed'
$contractExpected = [regex]::Match($anchor, '#define V3R19_CONTRACT_SHA256 "([0-9a-f]{64})"').Groups[1].Value
$tempBytes = [Text.Encoding]::UTF8.GetBytes($mutatedContract)
$sha256 = [Security.Cryptography.SHA256]::Create()
try { $mutatedHash = ([BitConverter]::ToString($sha256.ComputeHash($tempBytes))).Replace('-', '').ToLowerInvariant() } finally { $sha256.Dispose() }
Assert-True ($mutatedHash -ne $contractExpected) 'changed contract data was accepted'
$poisonedSource = $source.Replace('CREATE_NEW', 'OPEN_ALWAYS')
Assert-True ($poisonedSource.IndexOf('NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH', [StringComparison]::Ordinal) -lt 0) 'CREATE_NEW mutation not detected'
$poisonedSource = $source.Replace('FILE_FLAG_OPEN_REPARSE_POINT', '0U')
Assert-True ($poisonedSource.IndexOf('FILE_FLAG_OPEN_REPARSE_POINT', [StringComparison]::Ordinal) -lt 0) 'reparse mutation not detected'
$poisonedSource = $source.Replace('memcmp(telemetry->snapshot_one_sha256, telemetry->snapshot_two_sha256', 'memcmp(telemetry->snapshot_one_sha256, telemetry->snapshot_one_sha256')
Assert-True ($poisonedSource.IndexOf('memcmp(telemetry->snapshot_one_sha256, telemetry->snapshot_two_sha256', [StringComparison]::Ordinal) -lt 0) 'same-snapshot mutation not detected'

$bound = @{
    V3R19_CONTRACT_SHA256 = Sha $contractPath
    V3R19_SOURCE_SHA256 = Sha $sourcePath
    V3R19_TEST_SHA256 = Sha $PSCommandPath
    V3R19_CONTROL_SHA256 = Sha $controlPath
}
foreach ($name in $bound.Keys) {
    $actual = [regex]::Match($anchor, "#define $name `"([0-9a-f]{64})`"").Groups[1].Value
    Assert-True ($actual -eq $bound[$name]) "$name mismatch"
}

if ($Phase -eq 'PostSeal') {
    Assert-True (Test-Path -LiteralPath $sealPath -PathType Leaf) 'V3r19 seal absent in PostSeal'
    $seal = [IO.File]::ReadAllText($sealPath) | ConvertFrom-Json
    $v3r18Seal = [IO.File]::ReadAllText($v3r18SealPath) | ConvertFrom-Json
    $currentArtifacts = @(
        'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_python_controller_validation_v3r19.json',
        'tools/native/kira_r25_afes_python_controller_validation_v3r19.c',
        'tools/native/kira_r25_afes_python_controller_validation_v3r19_identity_anchor.h',
        'tools/native/kira_r25_afes_python_controller_validation_v3r19.obj',
        'tools/native/kira_r25_afes_python_controller_validation_v3r19.exe',
        'Testing/test_kira_r25_foundation_afes_python_controller_validation_v3r19_static.ps1',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r19_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r19_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
    )
    $v3r14Closure = @(
        'RecoverySprint/continuation_20260810/kira_r25_afes_native_outcome_reservation_v3r14_static_preparation/attempt_01/RUN_EVIDENCE.jsonl',
        'RecoverySprint/continuation_20260810/kira_r25_afes_native_outcome_reservation_v3r14_static_preparation/attempt_01/NATIVE_DIAGNOSTIC_OUTCOME.receipt.bin',
        'RecoverySprint/continuation_20260810/kira_r25_afes_v3r14_fresh_static_audit/attempt_01/CHECKPOINT.md',
        'RecoverySprint/continuation_20260810/kira_r25_afes_v3r14_consumed_success_postmortem/attempt_01/CHECKPOINT.md'
    )
    $v3r18Rejected = @($v3r18Seal.artifacts.path) + @(
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_static_preparation/attempt_01/CHECKPOINT.md',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.sha256',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit/attempt_01/HOSTILE_STATIC_PROBES.txt',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit/attempt_01/CHECKPOINT.md'
    )
    $expectedPaths = @($currentArtifacts) + @($v3r14Closure) +
        @($v3r18Seal.exact_v3r15_python_stage_predecessor.path) +
        @($v3r18Seal.exact_v3r17_consumed_success_closure.path) +
        @($v3r18Seal.retained_runtime_locks.path) + @($v3r18Rejected)
    $rows = @($seal.artifacts) + @($seal.exact_v3r14_runtime_authority_closure) +
        @($seal.exact_v3r15_python_stage_predecessor) +
        @($seal.exact_v3r17_consumed_success_closure) +
        @($seal.exact_v3r18_sealed_rejected_closure) + @($seal.retained_runtime_locks)
    $actualPaths = @($rows.path)
    Assert-True ($expectedPaths.Count -eq 61 -and $rows.Count -eq 61) 'V3r19 seal is not exactly 61 rows'
    Assert-True (($expectedPaths | Sort-Object -Unique).Count -eq 61) 'derived V3r19 expected set is not unique'
    Assert-True (($actualPaths | Sort-Object -Unique).Count -eq 61) 'V3r19 seal paths are not unique'
    $difference = @(Compare-Object ($expectedPaths | Sort-Object) ($actualPaths | Sort-Object))
    Assert-True ($difference.Count -eq 0) 'V3r19 seal exact path set drift'
    foreach ($row in $rows) {
        $path = if ([IO.Path]::IsPathRooted([string]$row.path)) {
            [string]$row.path
        } else {
            Join-Path $root ([string]$row.path)
        }
        $item = Get-Item -LiteralPath $path
        Assert-True ($item.Length -eq [long]$row.bytes) "seal byte drift: $($row.path)"
        Assert-True ((Sha $path) -eq [string]$row.sha256) "seal digest drift: $($row.path)"
    }
}

'V3R19_HOSTILE_STATIC_TESTS_PASS'
