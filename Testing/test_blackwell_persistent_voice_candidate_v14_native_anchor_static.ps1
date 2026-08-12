param(
    [ValidateSet('PreBuild', 'PostBuild', 'PostSeal')]
    [string]$Phase = 'PreBuild'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$referenceRoot = if (Test-Path -LiteralPath (Join-Path $root 'Core/persistent_blackwell_voice_integration_v13.py')) {
    $root
} else {
    'C:\Users\robmc\Kira'
}
$pythonSourcePath = Join-Path $root 'Core/persistent_blackwell_voice_integration_v14.py'
$validatorPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v14_validator.py'
$nativeSourcePath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v14.c'
$headerPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v14_identity_anchor.h'
$configPath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/candidate_config.json'
$contractPath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/native_control_contract.json'
$readmePath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/README.md'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$packagePath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/AUTHOR_PACKAGE.json'
$buildPath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
$sealPath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$futureAudit = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_fresh_static_audit/attempt_01'
$objectPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v14.obj'
$executablePath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v14.exe'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Assert-Contains([string]$Text, [string]$Needle, [string]$Message) {
    Assert-True ($Text.IndexOf($Needle, [StringComparison]::Ordinal) -ge 0) $Message
}

function Sha([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function ItemRow([string]$Path) {
    $item = Get-Item -LiteralPath $Path
    return @([long]$item.Length, (Sha $Path))
}

$required = @(
    $pythonSourcePath, $validatorPath, $nativeSourcePath, $headerPath, $configPath, $contractPath,
    $readmePath, $controlPath, $packagePath, $PSCommandPath
)
foreach ($path in $required) {
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "required V14 author file absent: $path"
}

$pythonSource = [IO.File]::ReadAllText($pythonSourcePath)
$validator = [IO.File]::ReadAllText($validatorPath)
$native = [IO.File]::ReadAllText($nativeSourcePath)
$header = [IO.File]::ReadAllText($headerPath)
$control = [IO.File]::ReadAllText($controlPath)
$configRaw = [IO.File]::ReadAllText($configPath)
$config = $configRaw | ConvertFrom-Json
$package = [IO.File]::ReadAllText($packagePath) | ConvertFrom-Json

Assert-True ($config.schema -eq 'kira.blackwell.v14.native_exact_control_anchor_config.v1') 'V14 config schema drift'
Assert-True ($config.status -eq 'AUTHOR_STATIC_ONLY_PENDING_BUILD_SEAL_AND_DIFFERENT_FRESH_AUDIT') 'V14 config status drift'
Assert-True (@($config.preserved_v13_subjects).Count -eq 15 -and $config.preserved_v13_subject_count -eq 15) 'V13 closure count drift'
Assert-True ((@($config.preserved_v13_subjects.path) | Sort-Object -Unique).Count -eq 15) 'V13 closure paths are not unique'
foreach ($name in @('production_routing_authorized','live_execution_authorized','future_harness_authoring_authorized','synthesis_authorized','playback_authorized','latency_run_authorized')) {
    Assert-True (($config.$name).GetType() -eq [bool] -and $config.$name -eq $false) "V14 config authority drift: $name"
}
Assert-True (($config.different_fresh_static_audit_required).GetType() -eq [bool] -and $config.different_fresh_static_audit_required -eq $true) 'V14 review truth drift'
Assert-True ($config.control_python_bytes -eq (Get-Item -LiteralPath $pythonSourcePath).Length) 'V14 Python byte binding drift'
Assert-True ($config.control_python_sha256 -eq (Sha $pythonSourcePath)) 'V14 Python digest binding drift'

foreach ($row in @($config.preserved_v13_subjects)) {
    $path = if ([IO.Path]::IsPathRooted([string]$row.path)) { [string]$row.path } else { Join-Path $referenceRoot ([string]$row.path) }
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "preserved V13 subject absent: $($row.path)"
    $item = Get-Item -LiteralPath $path
    Assert-True ($item.Length -eq [long]$row.bytes) "preserved V13 bytes drift: $($row.path)"
    Assert-True ((Sha $path) -eq [string]$row.sha256) "preserved V13 digest drift: $($row.path)"
}

$compileProbe = @'
from pathlib import Path
import sys
for raw in sys.argv[1:]:
    path = Path(raw)
    compile(path.read_bytes(), str(path), 'exec', dont_inherit=True, optimize=0)
print('V14_PRIVATE_SOURCES_COMPILE_PASS')
'@
$env:PYTHONDONTWRITEBYTECODE = '1'
$compileOutput = & py -c $compileProbe $pythonSourcePath $validatorPath 2>&1
Assert-True ($LASTEXITCODE -eq 0) "V14 private source compile failed: $compileOutput"
Assert-True (($compileOutput -join "`n").Contains('V14_PRIVATE_SOURCES_COMPILE_PASS')) 'V14 compile marker absent'

foreach ($needle in @(
    'def _validate_v13_graph(v13_source: bytes)',
    'first_signature = _module_graph_signature(first)',
    'second_signature = _module_graph_signature(second)',
    'if first_signature != second_signature:',
    'first.clear()',
    'second.clear()',
    '_exact_bool(self._quarantined, False, "V14 quarantine state")',
    '("private_globals_only", None, None, None, False)',
    'def create_static_control_snapshot_v14(',
    'LATENCY_RUN_AUTHORIZED = False'
)) { Assert-Contains $pythonSource $needle "V14 Python control missing: $needle" }

foreach ($needle in @(
    'def _function_cross(',
    'def _same_identity_graph(',
    '_graph(primary, cross=True) != _graph(reference, cross=True)',
    'factory_code = factory.__code__',
    'revalidate_code = revalidate.__code__',
    '_same_identity_graph(primary, captured)',
    '_slots_clean(system)',
    'primary.clear()',
    'reference.clear()'
)) { Assert-Contains $validator $needle "V14 private validator missing: $needle" }

foreach ($needle in @(
    'FILE_FLAG_OPEN_REPARSE_POINT',
    'FILE_FLAG_WRITE_THROUGH',
    'CREATE_NEW',
    'static int verify_handle_capture(',
    'static int verify_handle_bound(',
    'PyConfig_InitIsolatedConfig',
    'PyObject_CallObject',
    'FreeLibrary(api.module)',
    'prove_python_module_absent(old_module, unload)',
    '_wcsicmp(entry.szExePath, PYTHON_DLL_PATH) == 0',
    'V14_PREDECESSOR_COUNT 15U',
    'four_v13_blockers_closed',
    'latency_run_authorized',
    'memchr(audit, ''\0'', audit_bytes)',
    'lower_hex_exact(value, value_length)'
)) { Assert-Contains $native $needle "V14 native anchor missing: $needle" }

$reservationOrder = $native.IndexOf('evidence = CreateFileW(EVIDENCE_PATH', [StringComparison]::Ordinal)
$pythonOrder = $native.IndexOf('run_python_validation(&fixed[9]', [StringComparison]::Ordinal)
$finalizeOrder = $native.IndexOf('const int finalize_result = api.finalize()', [StringComparison]::Ordinal)
$releaseOrder = $native.IndexOf('FreeLibrary(api.module)', [StringComparison]::Ordinal)
$absenceOrder = $native.IndexOf('prove_python_module_absent(old_module, unload)', [StringComparison]::Ordinal)
Assert-True ($reservationOrder -ge 0 -and $reservationOrder -lt $pythonOrder) 'reservation does not precede Python'
Assert-True ($finalizeOrder -ge 0 -and $finalizeOrder -lt $releaseOrder -and $releaseOrder -lt $absenceOrder) 'finalize/release/absence order drift'

foreach ($forbidden in @(
    'CreateProcessW(', 'CreateProcessA(', 'ShellExecuteW(', 'ShellExecuteA(',
    'WinExec(', 'system(', 'PyImport_ImportModule', 'torch', 'ollama',
    'chatterbox', 'sounddevice', 'winsound', 'bpy', 'socket'
)) {
    if ($forbidden -in @('torch','ollama','chatterbox','bpy')) {
        # Boundary comments may name forbidden systems; executable Python/C tokens may not import them.
        Assert-True ($pythonSource.IndexOf("import $forbidden", [StringComparison]::Ordinal) -lt 0 -and $validator.IndexOf("import $forbidden", [StringComparison]::Ordinal) -lt 0) "forbidden Python import: $forbidden"
    } else {
        Assert-True ($native.IndexOf($forbidden, [StringComparison]::Ordinal) -lt 0) "forbidden native primitive: $forbidden"
    }
}
Assert-Contains $control 'STOP_BEFORE_MODEL_GPU_TORCH_CUDA_CHATTERBOX_SYNTHESIS_AUDIO_PLAYBACK_LATENCY_NETWORK_PROCESS_PERSON_STATE_PRODUCTION_ROUTE' 'runtime stop boundary drift'
Assert-True ($package.execution_authority -eq 'NONE' -and $package.candidate_invoked -eq $false -and $package.python_candidate_invoked -eq $false) 'author package execution truth drift'

# Negative controls: the exact rejection retains all four reproduced V13 blocker IDs.
$decisionPath = Join-Path $referenceRoot 'RecoverySprint/continuation_20260811/blackwell_v13_control_plane_binding_fresh_static_audit/attempt_01/AUDIT_DECISION.json'
$decision = [IO.File]::ReadAllText($decisionPath) | ConvertFrom-Json
$expectedBlockers = @(
    'BLOCK_V13_PRECALL_SELF_MODULE_PACKAGE_IDENTITY_NOT_BOUND',
    'BLOCK_V13_SELF_CLASS_METHODS_NOT_BOUND_PRIVATE_V12_BYPASS',
    'BLOCK_V13_CONTROL_STATE_NOT_REVALIDATED',
    'BLOCK_V13_CONFIG_QUARANTINE_LOADER_STATE_NOT_EXACT'
)
Assert-True (@($decision.blocking_findings.id).Count -eq 4) 'V13 blocker count drift'
Assert-True (@(Compare-Object $expectedBlockers @($decision.blocking_findings.id)).Count -eq 0) 'V13 blocker identity drift'

# In-memory mutations must leave the exact sealed author inputs.
$mutatedConfig = $configRaw.Replace('"latency_run_authorized": false', '"latency_run_authorized": 0')
Assert-True ($mutatedConfig -ne $configRaw) 'numeric-bool mutation setup failed'
$sha = [Security.Cryptography.SHA256]::Create()
try {
    $mutatedHash = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($mutatedConfig)))).Replace('-', '').ToLowerInvariant()
} finally { $sha.Dispose() }
Assert-True ($mutatedHash -ne (Sha $configPath)) 'numeric-bool mutation retained exact digest'
$poisonedNative = $native.Replace('CREATE_NEW', 'OPEN_ALWAYS')
Assert-True ($poisonedNative -ne $native -and $poisonedNative.IndexOf('NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH', [StringComparison]::Ordinal) -lt 0) 'append-only mutation was accepted'
$poisonedValidator = $validator.Replace('_same_identity_graph(primary, captured)', 'pass # graph check removed')
Assert-True ($poisonedValidator -ne $validator) 'graph-recheck mutation setup failed'

$bound = [ordered]@{
    V14_NATIVE_SOURCE = $nativeSourcePath
    V14_VALIDATOR = $validatorPath
    V14_PY_SOURCE = $pythonSourcePath
    V14_CONFIG = $configPath
    V14_CONTRACT = $contractPath
    V14_README = $readmePath
    V14_TEST = $PSCommandPath
    V14_CONTROL = $controlPath
    V14_PACKAGE = $packagePath
}
foreach ($name in $bound.Keys) {
    $row = ItemRow $bound[$name]
    $bytes = [regex]::Match($header, "#define ${name}_BYTES ([0-9]+)ULL").Groups[1].Value
    $digest = [regex]::Match($header, "#define ${name}_SHA256 `"([0-9a-f]{64})`"").Groups[1].Value
    Assert-True ($bytes -eq [string]$row[0]) "$name bytes mismatch"
    Assert-True ($digest -eq [string]$row[1]) "$name digest mismatch"
}

Assert-True (-not (Test-Path -LiteralPath $futureAudit)) 'future different-review audit root must be absent at author freeze'
if ($Phase -eq 'PreBuild') {
    Assert-True (-not (Test-Path -LiteralPath $objectPath)) 'V14 object must be absent in PreBuild'
    Assert-True (-not (Test-Path -LiteralPath $executablePath)) 'V14 executable must be absent in PreBuild'
    Assert-True (-not (Test-Path -LiteralPath $buildPath)) 'V14 build result must be absent in PreBuild'
    Assert-True (-not (Test-Path -LiteralPath $sealPath)) 'V14 seal must be absent in PreBuild'
}
if ($Phase -in @('PostBuild','PostSeal')) {
    foreach ($path in @($objectPath,$executablePath,$buildPath)) {
        Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "post-build artifact absent: $path"
    }
}
if ($Phase -eq 'PostSeal') {
    Assert-True (Test-Path -LiteralPath $sealPath -PathType Leaf) 'V14 seal absent in PostSeal'
    $seal = [IO.File]::ReadAllText($sealPath) | ConvertFrom-Json
    Assert-True ($seal.schema -eq 'kira.blackwell.v14.native_exact_control_anchor.static_seal.v1') 'V14 seal schema drift'
    Assert-True ($seal.status -eq 'SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT') 'V14 seal status drift'
    Assert-True ($seal.execution_authority -eq 'NONE' -and $seal.candidate_executed -eq $false) 'V14 seal authority drift'
    Assert-True ($seal.sealed_subject_count -eq 30 -and $seal.unique_paths -eq $true) 'V14 seal count drift'
    $rows = @($seal.subjects)
    Assert-True ($rows.Count -eq 30 -and (@($rows.path) | Sort-Object -Unique).Count -eq 30) 'V14 seal paths are not exactly 30 unique rows'
    foreach ($row in $rows) {
        $path = if ([IO.Path]::IsPathRooted([string]$row.path)) { [string]$row.path } else { Join-Path $root ([string]$row.path) }
        $item = Get-Item -LiteralPath $path
        Assert-True ($item.Length -eq [long]$row.bytes) "seal byte drift: $($row.path)"
        Assert-True ((Sha $path) -eq [string]$row.sha256) "seal digest drift: $($row.path)"
    }
}

'V14_NATIVE_EXACT_CONTROL_HOSTILE_STATIC_TESTS_PASS'
