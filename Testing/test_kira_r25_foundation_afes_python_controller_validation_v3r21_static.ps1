param(
    [ValidateSet('PreSeal', 'PostSeal')]
    [string]$Phase = 'PreSeal'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourcePath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r21.c'
$anchorPath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r21_identity_anchor.h'
$contractPath = Join-Path $root 'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_python_controller_validation_v3r21.json'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$futureAudit = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit/attempt_01'
$sealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$v3r18SourcePath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r18.c'
$v3r18SealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$v3r19SourcePath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r19.c'
$v3r20SourcePath = Join-Path $root 'tools/native/kira_r25_afes_python_controller_validation_v3r20.c'
$v3r20SealPath = Join-Path $root 'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'

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
$v3r19Source = [IO.File]::ReadAllText($v3r19SourcePath)
$v3r20Source = [IO.File]::ReadAllText($v3r20SourcePath)
$contract = $contractText | ConvertFrom-Json

Assert-True ($contract.schema -eq 'kira.avatar.r25.foundation_afes_python_controller_validation.v3r21') 'schema drift'
Assert-True ($contract.predecessor.version -eq 'v3r20') 'predecessor version drift'
Assert-True ($contract.predecessor.status -eq 'REJECTED_NO_EXECUTION_AUTHORITY') 'v3r20 rejection status not exact'
Assert-True ($contract.predecessor.static_seal_sha256 -eq '3dacef076bc0046cd42c1fdbe34f331e391177776125efb146465801fcbf13c2') 'v3r20 seal drift'
Assert-True ($contract.predecessor.rejection_audit_sha256 -eq '790b122d1eb135754b78673b57fa74e48babf0bec4b5e07498015b95bd7a1273') 'v3r20 audit drift'
Assert-True ($contract.predecessor.rejection_checkpoint_sha256 -eq '16174d65ab9da57c1f9508de2ef71aae07aa5d95fd2c1bed7517a5ba35c40a4c') 'v3r20 rejection checkpoint drift'
Assert-True ($contract.predecessor.candidate_executed -eq $false -and $contract.predecessor.run_evidence_present -eq $false -and $contract.predecessor.outcome_receipt_present -eq $false) 'v3r20 execution/output truth drift'
Assert-True (@($contract.rejected_v3r20_closure.PSObject.Properties).Count -eq 15) 'v3r20 exact rejected closure must contain 15 subjects'
Assert-True ($contract.inherited_file_identity_control.ambiguous_zero_sentinel_removed -eq $true) 'inherited identity control missing'
Assert-True ($contract.literal_copy_and_analyzer_repair.c17_static_assert_fits_destination -eq $true) 'literal field fit proof missing'
Assert-True ($contract.literal_copy_and_analyzer_repair.required_msvc_analyze_result -eq 'ZERO_UNSUPPRESSED_WARNINGS') 'analyzer requirement missing'
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
Assert-Contains $source 'V3R21_TARGET_CONTRACT_BYTES' 'target size uses candidate contract binding'
Assert-Contains $source 'V3R21_TARGET_CONTRACT_SHA256' 'target digest uses candidate contract binding'
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
Assert-Contains $source 'static int verify_handle_capture(' 'identity capture function absent'
Assert-Contains $source 'static int verify_handle_bound(' 'bound identity function absent'
Assert-Contains $source 'verify_handle_capture(file, path, bytes, sha, &identity)' 'exact path hash does not use capture operation'
Assert-Contains $source 'verify_handle_capture(locked->handle, locked->path' 'new retained handle does not capture identity'
Assert-Contains $source 'verify_handle_bound(retained[index].handle, retained[index].path' 'retained handle is not rechecked against its bound identity'
Assert-True ($source.IndexOf('verify_handle_exact(', [StringComparison]::Ordinal) -lt 0) 'ambiguous V3r19 identity API survived'
Assert-Contains $source 'memchr(audit, ''\0'', audit_bytes)' 'whole-audit embedded NUL rejection absent'
Assert-Contains $source 'lower_hex_exact(values[index], value_lengths[index])' 'raw-length digest grammar absent'
Assert-Contains $source 'auditor_exact(values[1], value_lengths[1])' 'canonical auditor grammar absent'
Assert-Contains $source 'V3R17_RUN_OUTCOME_PATH' 'V3r17 run outcome not bound'
Assert-Contains $source 'V3R17_POST_RUN_PATH' 'V3r17 post-run checkpoint not bound'
Assert-Contains $source 'ACCEPTED_FOR_ONE_BOUNDED_GRANULAR_CONTRACT_AND_PYTHON_CONTROLLER_VALIDATION_V3R21_ONLY' 'future audit decision drift'
Assert-Contains $source 'kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit' 'exact future audit root absent'
Assert-Contains $source 'static const unsigned char RESERVATION_MAGIC[] = "KIRA_R25_AFES_V3R21_RESERVATION";' 'named reservation magic absent'
Assert-Contains $source 'static const unsigned char TERMINAL_MAGIC[] = "KIRA_R25_AFES_V3R21_TERMINAL";' 'named terminal magic absent'
Assert-Contains $source '_Static_assert(sizeof(RESERVATION_MAGIC) - 1U <= sizeof(((ReservationRecord *)0)->magic),' 'reservation field fit assertion absent'
Assert-Contains $source '_Static_assert(sizeof(TERMINAL_MAGIC) - 1U <= sizeof(((CompletionRecord *)0)->magic),' 'terminal field fit assertion absent'
Assert-Contains $source 'memcpy(record.magic, RESERVATION_MAGIC, sizeof(RESERVATION_MAGIC) - 1U);' 'safe reservation magic copy absent'
Assert-Contains $source 'memcpy(record.magic, TERMINAL_MAGIC, sizeof(TERMINAL_MAGIC) - 1U);' 'safe terminal magic copy absent'
Assert-Contains $source 'expected[4U + path_length] = L''\0'';' 'explicit expected-path terminator absent'
Assert-Contains $source 'actual[length] = L''\0'';' 'explicit actual-path terminator absent'
Assert-Contains $source 'wchar_t module[MAX_PATH];' 'bounded Python module path buffer absent'
Assert-Contains $source 'return value != NULL && value != INVALID_HANDLE_VALUE;' 'exact valid-handle cleanup predicate absent'
Assert-True ($source.IndexOf('wchar_t actual[32768]', [StringComparison]::Ordinal) -lt 0 -and $source.IndexOf('wchar_t expected[32768]', [StringComparison]::Ordinal) -lt 0) 'large final-path stack buffers survived'
Assert-True ($source.IndexOf('memcpy(record.magic, "KIRA_R25_AFES_V3R21_RESERVATION", 34U)', [StringComparison]::Ordinal) -lt 0) 'numeric reservation overread pattern survived'
Assert-True ($source.IndexOf('memcpy(record.magic, "KIRA_R25_AFES_V3R21_TERMINAL", 31U)', [StringComparison]::Ordinal) -lt 0) 'numeric terminal overread pattern survived'

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
$v3r21ContractTokens = ([regex]::Matches($source, '(?<![A-Z0-9_])CONTRACT_PATH(?![A-Z0-9_])')).Count
Assert-True ($v3r18ContractTokens -eq 1) 'V3r18 contract-path negative control did not reproduce'
Assert-True ($v3r21ContractTokens -ge 2) 'V3r21 authority contract is not runtime-bound'
Assert-True ($v3r18Source.IndexOf('strcmp(values[0], expected[0])', [StringComparison]::Ordinal) -ge 0) 'V3r18 C-string negative control did not reproduce'
Assert-True ($source.IndexOf('strcmp(values[0], expected[0])', [StringComparison]::Ordinal) -lt 0) 'V3r19 still uses unsafe audit decision strcmp'
Assert-True (([regex]::Matches($source, '\{V3R18_[A-Z0-9_]+_PATH, V3R21_V3R18_')).Count -eq 14) 'complete V3r18 rejected closure is not runtime-bound'
Assert-True (([regex]::Matches($source, '\{V3R19_[A-Z0-9_]+_PATH, V3R21_V3R19_')).Count -eq 15) 'complete V3r19 consumed-failure closure is not runtime-bound'
Assert-True (([regex]::Matches($source, '\{V3R20_[A-Z0-9_]+_PATH, V3R21_V3R20_')).Count -eq 15) 'complete V3r20 rejected closure is not runtime-bound'
Assert-Contains $source 'static const char *keys[69]' 'V3r21 audit grammar does not bind all 15 V3r20 subjects'

# Reproduce the exact V3r20 C6385 defects from its sealed source. The source
# object contains 31 payload bytes plus NUL for reservation and 28 plus NUL for
# terminal; its numeric copy counts therefore read two bytes past each object.
Assert-Contains $v3r20Source 'memcpy(record.magic, "KIRA_R25_AFES_V3R20_RESERVATION", 34U);' 'V3r20 reservation overread negative control missing'
Assert-Contains $v3r20Source 'memcpy(record.magic, "KIRA_R25_AFES_V3R20_TERMINAL", 31U);' 'V3r20 terminal overread negative control missing'
Assert-True (('KIRA_R25_AFES_V3R20_RESERVATION'.Length + 1) -eq 32 -and 34 -gt 32) 'V3r20 reservation object-size proof drift'
Assert-True (('KIRA_R25_AFES_V3R20_TERMINAL'.Length + 1) -eq 29 -and 31 -gt 29) 'V3r20 terminal object-size proof drift'

# Reproduce the V3r19 capture bug from exact source and prove V3r20 removed its
# ambiguous zero-identity sentinel without weakening already-bound rechecks.
$v3r19PrematureCompare = $v3r19Source.IndexOf('(identity == NULL || same_identity(identity, &current))', [StringComparison]::Ordinal)
$v3r19LateCapture = $v3r19Source.IndexOf('identity->VolumeSerialNumber == 0ULL) *identity = current', [StringComparison]::Ordinal)
Assert-True ($v3r19PrematureCompare -ge 0 -and $v3r19LateCapture -gt $v3r19PrematureCompare) 'V3r19 zero-identity failure negative control did not reproduce'
$captureStart = $source.IndexOf('static int verify_handle_capture(', [StringComparison]::Ordinal)
$boundStart = $source.IndexOf('static int verify_handle_bound(', [StringComparison]::Ordinal)
$hashPathStart = $source.IndexOf('static int hash_path_exact(', [StringComparison]::Ordinal)
Assert-True ($captureStart -ge 0 -and $boundStart -gt $captureStart -and $hashPathStart -gt $boundStart) 'capture/bound/hash API order drift'
$captureBody = $source.Substring($captureStart, $boundStart - $captureStart)
$boundBody = $source.Substring($boundStart, $hashPathStart - $boundStart)
Assert-True ($captureBody.IndexOf('same_identity(', [StringComparison]::Ordinal) -lt 0) 'capture operation still compares an unbound identity'
Assert-Contains $captureBody '*observed_identity = current' 'capture operation does not return observed identity'
Assert-Contains $boundBody 'same_identity(expected_identity, &observed_identity)' 'bound operation does not compare retained identity'

foreach ($forbidden in @('CreateProcessW(', 'CreateProcessA(', 'ShellExecuteW(', 'ShellExecuteA(', 'WinExec(', 'system(', 'PyImport_ImportModule')) {
    Assert-True ($source.IndexOf($forbidden, [StringComparison]::Ordinal) -lt 0) "forbidden production primitive: $forbidden"
}
Assert-True (([regex]::Matches($source, [regex]::Escape('api->dict_get(globals, expected[index])'))).Count -eq 1) 'callable export verification drift'
Assert-True ($source.IndexOf('api.call(', [StringComparison]::Ordinal) -lt 0) 'controller callable invocation introduced'
Assert-Contains $control 'STOP_BEFORE_PLAN_BUILDER_BROKER_PROCESS_AFES_BLENDER_BODY_SAVE_RENDER' 'control stop boundary drift'
Assert-True (-not (Test-Path -LiteralPath $futureAudit)) 'future audit root must be absent at author freeze'
if ($Phase -eq 'PreSeal') {
    Assert-True (-not (Test-Path -LiteralPath $sealPath)) 'V3r21 seal must be absent during PreSeal'
}

# In-memory hostile mutations must fail the exact static predicates.
$mutatedContract = $contractText.Replace('"reservation_first": true', '"reservation_first": false')
Assert-True ($mutatedContract -ne $contractText) 'mutation setup failed'
$contractExpected = [regex]::Match($anchor, '#define V3R21_CONTRACT_SHA256 "([0-9a-f]{64})"').Groups[1].Value
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
    V3R21_CONTRACT_SHA256 = Sha $contractPath
    V3R21_SOURCE_SHA256 = Sha $sourcePath
    V3R21_TEST_SHA256 = Sha $PSCommandPath
    V3R21_CONTROL_SHA256 = Sha $controlPath
}
foreach ($name in $bound.Keys) {
    $actual = [regex]::Match($anchor, "#define $name `"([0-9a-f]{64})`"").Groups[1].Value
    Assert-True ($actual -eq $bound[$name]) "$name mismatch"
}

if ($Phase -eq 'PostSeal') {
    Assert-True (Test-Path -LiteralPath $sealPath -PathType Leaf) 'V3r21 seal absent in PostSeal'
    $seal = [IO.File]::ReadAllText($sealPath) | ConvertFrom-Json
    $v3r20Seal = [IO.File]::ReadAllText($v3r20SealPath) | ConvertFrom-Json
    $currentArtifacts = @(
        'Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_python_controller_validation_v3r21.json',
        'tools/native/kira_r25_afes_python_controller_validation_v3r21.c',
        'tools/native/kira_r25_afes_python_controller_validation_v3r21_identity_anchor.h',
        'tools/native/kira_r25_afes_python_controller_validation_v3r21.obj',
        'tools/native/kira_r25_afes_python_controller_validation_v3r21.exe',
        'Testing/test_kira_r25_foundation_afes_python_controller_validation_v3r21_static.ps1',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
    )
    $v3r20Rejected = @($v3r20Seal.artifacts.path) + @(
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_static_preparation/attempt_01/CHECKPOINT.md',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.sha256',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit/attempt_01/AUDIT_DECISION.json',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit/attempt_01/MSVC_ANALYZE_RESULTS.txt',
        'RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit/attempt_01/CHECKPOINT.md'
    )
    $expectedPaths = @($currentArtifacts) + @($v3r20Seal.exact_v3r14_runtime_authority_closure.path) +
        @($v3r20Seal.exact_v3r15_python_stage_predecessor.path) +
        @($v3r20Seal.exact_v3r17_consumed_success_closure.path) +
        @($v3r20Seal.exact_v3r18_sealed_rejected_closure.path) +
        @($v3r20Seal.exact_v3r19_consumed_failure_closure.path) +
        @($v3r20Seal.retained_runtime_locks.path) + @($v3r20Rejected)
    $rows = @($seal.artifacts) + @($seal.exact_v3r14_runtime_authority_closure) +
        @($seal.exact_v3r15_python_stage_predecessor) +
        @($seal.exact_v3r17_consumed_success_closure) +
        @($seal.exact_v3r18_sealed_rejected_closure) +
        @($seal.exact_v3r19_consumed_failure_closure) +
        @($seal.exact_v3r20_sealed_rejected_closure) + @($seal.retained_runtime_locks)
    $actualPaths = @($rows.path)
    Assert-True ($seal.schema -eq 'kira.r25.afes.v3r21.static_seal.v1') 'V3r21 seal schema drift'
    Assert-True ($seal.status -eq 'SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT') 'V3r21 seal status drift'
    Assert-True ($seal.execution_authority -eq 'NONE' -and $seal.candidate_executed -eq $false) 'V3r21 execution boundary drift'
    Assert-True ($seal.sealed_subject_count -eq 91 -and $seal.unique_paths -eq $true) 'V3r21 declared closure drift'
    Assert-True (@($seal.artifacts).Count -eq 8 -and @($seal.exact_v3r20_sealed_rejected_closure).Count -eq 15) 'V3r21 current/predecessor group count drift'
    Assert-True ($expectedPaths.Count -eq 91 -and $rows.Count -eq 91) 'V3r21 seal is not exactly 91 rows'
    Assert-True (($expectedPaths | Sort-Object -Unique).Count -eq 91) 'derived V3r21 expected set is not unique'
    Assert-True (($actualPaths | Sort-Object -Unique).Count -eq 91) 'V3r21 seal paths are not unique'
    $difference = @(Compare-Object ($expectedPaths | Sort-Object) ($actualPaths | Sort-Object))
    Assert-True ($difference.Count -eq 0) 'V3r21 seal exact path set drift'
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

'V3R21_HOSTILE_STATIC_TESTS_PASS'
