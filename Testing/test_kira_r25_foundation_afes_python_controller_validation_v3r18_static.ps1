$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourcePath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r18.c'
$anchorPath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r18_identity_anchor.h'
$contractPath = Join-Path $root 'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_python_controller_validation_v3r18.json'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$futureAudit = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit/attempt_01'

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
$contract = $contractText | ConvertFrom-Json

Assert-True ($contract.schema -eq 'kira.avatar.r25.foundation_afes_python_controller_validation.v3r18') 'schema drift'
Assert-True ($contract.predecessor.status -eq 'CONSUMED_SUCCESS_NO_RETRY') 'v3r17 not consumed'
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
Assert-Contains $source 'V3R18_TARGET_CONTRACT_BYTES' 'target size uses candidate contract binding'
Assert-Contains $source 'V3R18_TARGET_CONTRACT_SHA256' 'target digest uses candidate contract binding'
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
Assert-Contains $source 'V3R17_RUN_OUTCOME_PATH' 'V3r17 run outcome not bound'
Assert-Contains $source 'V3R17_POST_RUN_PATH' 'V3r17 post-run checkpoint not bound'
Assert-Contains $source 'ACCEPTED_FOR_ONE_BOUNDED_GRANULAR_CONTRACT_AND_PYTHON_CONTROLLER_VALIDATION_ONLY' 'future audit decision drift'
Assert-Contains $source 'kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit' 'exact future audit root absent'

$reservation = $source.IndexOf('evidence = CreateFileW(EVIDENCE_PATH', [StringComparison]::Ordinal)
$granular = $source.IndexOf('stage_ok = open_contract_granular(', [StringComparison]::Ordinal)
$retained = $source.IndexOf('if (!lock_file(&retained[index]))', [StringComparison]::Ordinal)
$python = $source.IndexOf('stage_ok && run_python_validation(', [StringComparison]::Ordinal)
Assert-True ($reservation -ge 0 -and $reservation -lt $granular -and $granular -lt $retained -and $retained -lt $python) 'reservation/granular/retained/Python ordering drift'

foreach ($forbidden in @('CreateProcessW(', 'CreateProcessA(', 'ShellExecuteW(', 'ShellExecuteA(', 'WinExec(', 'system(', 'PyImport_ImportModule')) {
    Assert-True ($source.IndexOf($forbidden, [StringComparison]::Ordinal) -lt 0) "forbidden production primitive: $forbidden"
}
Assert-True (([regex]::Matches($source, [regex]::Escape('api->dict_get(globals, expected[index])'))).Count -eq 1) 'callable export verification drift'
Assert-True ($source.IndexOf('api.call(', [StringComparison]::Ordinal) -lt 0) 'controller callable invocation introduced'
Assert-Contains $control 'STOP_BEFORE_PLAN_BUILDER_BROKER_PROCESS_AFES_BLENDER_BODY_SAVE_RENDER' 'control stop boundary drift'
Assert-True (-not (Test-Path -LiteralPath $futureAudit)) 'future audit root must be absent at author freeze'

# In-memory hostile mutations must fail the exact static predicates.
$mutatedContract = $contractText.Replace('"reservation_first": true', '"reservation_first": false')
Assert-True ($mutatedContract -ne $contractText) 'mutation setup failed'
$contractExpected = [regex]::Match($anchor, '#define V3R18_CONTRACT_SHA256 "([0-9a-f]{64})"').Groups[1].Value
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
    V3R18_CONTRACT_SHA256 = Sha $contractPath
    V3R18_SOURCE_SHA256 = Sha $sourcePath
    V3R18_CONTROL_SHA256 = Sha $controlPath
}
foreach ($name in $bound.Keys) {
    $actual = [regex]::Match($anchor, "#define $name `"([0-9a-f]{64})`"").Groups[1].Value
    Assert-True ($actual -eq $bound[$name]) "$name mismatch"
}

'V3R18_HOSTILE_STATIC_TESTS_PASS'
