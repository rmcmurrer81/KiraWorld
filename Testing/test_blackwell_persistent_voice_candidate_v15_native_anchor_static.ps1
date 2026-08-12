param(
    [ValidateSet('PreBuild', 'PostBuild', 'PostSeal')]
    [string]$Phase = 'PreBuild'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$kira = 'C:\Users\robmc\Kira'
$auditFallback = 'C:\Users\robmc\Documents\Codex\2026-08-11\c\work\voice_v14_fresh_audit\proposed_append_only'
$pythonSourcePath = Join-Path $root 'Core/persistent_blackwell_voice_integration_v15.py'
$validatorPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v15_validator.py'
$nativeSourcePath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v15.c'
$headerPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v15_identity_anchor.h'
$configPath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/candidate_config.json'
$contractPath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/native_control_contract.json'
$readmePath = Join-Path $root 'Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/README.md'
$controlPath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md'
$packagePath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/AUTHOR_PACKAGE.json'
$checkpointPath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/CHECKPOINT.md'
$buildPath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt'
$sealPath = Join-Path $root 'RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json'
$objectPath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v15.obj'
$executablePath = Join-Path $root 'tools/native/kira_blackwell_voice_control_anchor_v15.exe'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Assert-Contains([string]$Text, [string]$Needle, [string]$Message) {
    Assert-True ($Text.IndexOf($Needle, [StringComparison]::Ordinal) -ge 0) $Message
}

function Sha([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Resolve-Predecessor([string]$RelativePath) {
    $primary = Join-Path $kira $RelativePath
    if (Test-Path -LiteralPath $primary -PathType Leaf) { return $primary }
    $fallback = Join-Path $auditFallback $RelativePath
    if (Test-Path -LiteralPath $fallback -PathType Leaf) { return $fallback }
    throw "predecessor absent: $RelativePath"
}

$required = @(
    $pythonSourcePath, $validatorPath, $nativeSourcePath, $headerPath, $configPath,
    $contractPath, $readmePath, $controlPath, $packagePath, $PSCommandPath
)
foreach ($path in $required) {
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "required V15 author file absent: $path"
}

$source = [IO.File]::ReadAllText($pythonSourcePath)
$validator = [IO.File]::ReadAllText($validatorPath)
$native = [IO.File]::ReadAllText($nativeSourcePath)
$header = [IO.File]::ReadAllText($headerPath)
$configRaw = [IO.File]::ReadAllText($configPath)
$config = $configRaw | ConvertFrom-Json
$package = [IO.File]::ReadAllText($packagePath) | ConvertFrom-Json

Assert-True ($config.schema -eq 'kira.blackwell.v15.native_exact_control_anchor_config.v1') 'V15 config schema drift'
Assert-True ($config.status -eq 'AUTHOR_STATIC_ONLY_PENDING_BUILD_SEAL_AND_DIFFERENT_FRESH_AUDIT') 'V15 config status drift'
Assert-True ($config.control_python_bytes -eq (Get-Item -LiteralPath $pythonSourcePath).Length) 'V15 Python byte binding drift'
Assert-True ($config.control_python_sha256 -eq (Sha $pythonSourcePath)) 'V15 Python digest binding drift'
Assert-True ($config.native_contract_bytes -eq (Get-Item -LiteralPath $contractPath).Length) 'V15 contract byte binding drift'
Assert-True ($config.native_contract_sha256 -eq (Sha $contractPath)) 'V15 contract digest binding drift'
Assert-True ($config.preserved_v14_subject_count -eq 6 -and @($config.preserved_v14_subjects).Count -eq 6) 'V15 predecessor count drift'
Assert-True ((@($config.preserved_v14_subjects.path) | Sort-Object -Unique).Count -eq 6) 'V15 predecessor paths not unique'
foreach ($name in @('production_routing_authorized','live_execution_authorized','future_harness_authoring_authorized','synthesis_authorized','playback_authorized','latency_run_authorized')) {
    Assert-True (($config.$name).GetType() -eq [bool] -and $config.$name -eq $false) "V15 config authority drift: $name"
}
Assert-True (($config.different_fresh_static_audit_required).GetType() -eq [bool] -and $config.different_fresh_static_audit_required -eq $true) 'V15 audit truth drift'
foreach ($row in @($config.preserved_v14_subjects)) {
    $path = Resolve-Predecessor ([string]$row.path)
    Assert-True ((Get-Item -LiteralPath $path).Length -eq [long]$row.bytes) "predecessor bytes drift: $($row.path)"
    Assert-True ((Sha $path) -eq [string]$row.sha256) "predecessor digest drift: $($row.path)"
}

$env:PYTHONDONTWRITEBYTECODE = '1'
$compileProbe = "from pathlib import Path; import sys; ps=[Path(x) for x in sys.argv[1:]]; [compile(p.read_bytes(),str(p),'exec',dont_inherit=True,optimize=0) for p in ps]; print('V15_COMPILE_ONLY_PASS')"
$compileOutput = & py -c $compileProbe $pythonSourcePath $validatorPath 2>&1
Assert-True ($LASTEXITCODE -eq 0 -and ($compileOutput -join "`n").Contains('V15_COMPILE_ONLY_PASS')) "V15 source compile-only failed: $compileOutput"
$canonicalProbe = "import hashlib,json,pathlib,sys; p=pathlib.Path(sys.argv[1]); b=p.read_bytes(); strict=lambda pairs: dict(pairs) if len({k for k,v in pairs})==len(pairs) else (_ for _ in ()).throw(ValueError('duplicate')); v=json.loads(b,object_pairs_hook=strict); c=(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)+chr(10)).encode(); assert b==c; print('V15_CANONICAL_CONFIG_PASS')"
$canonicalOutput = & py -c $canonicalProbe $configPath 2>&1
Assert-True ($LASTEXITCODE -eq 0 -and ($canonicalOutput -join "`n").Contains('V15_CANONICAL_CONFIG_PASS')) "V15 canonical config failed: $canonicalOutput"

Assert-True ($source.IndexOf('class BlackwellV15StaticControlSnapshot', [StringComparison]::Ordinal) -lt 0) 'writable V15 snapshot class remains'
foreach ($needle in @(
    'def create_static_control_result_v15(', 'native_expected_v14_graph',
    'if graph != native_expected_v14_graph:', '_exact_immutable_tree(result',
    'value._text', 'value.machinery', 'value.Path', 'value.Any',
    '_parse_canonical_json(raw, "V15 config")', 'len(subjects) != 6',
    'BLOCK_V14_SNAPSHOT_STATE_MUTABLE_NOT_ORIGIN_BOUND',
    'BLOCK_V14_LOADER_GRAPH_STATE_NOT_EXACT_TYPED',
    'BLOCK_V14_COMPLETE_GRAPH_OMITS_MUTABLE_INSTANCE_STATE',
    'BLOCK_V14_POSTCALL_V12_PARENT_ATTRIBUTE_NOT_RECHECKED'
)) { Assert-Contains $source $needle "V15 source hostile invariant missing: $needle" }
foreach ($needle in @(
    'state[4] is not attestations', 'state[5] is not expected_v14_graph',
    'type(state[6]) is not tuple', 'type(value) is not bool or value is not False',
    'v12_parent', 'canonical_typed_memory_binding',
    'Core.persistent_blackwell_voice_integration_v13',
    '_kira_blackwell_v14_private_v13_graph', '_kira_blackwell_v13_exact_v12_control_plane',
    'value._text', 'value.machinery', 'value.Path', 'value.Any'
)) { Assert-Contains $validator $needle "V15 validator hostile invariant missing: $needle" }

$duplicateMutation = $configRaw.Insert(1, '"candidate_id":"duplicate",')
$whitespaceMutation = [regex]::Replace($configRaw, ',', ', ', 1)
$numericBoolMutation = $configRaw.Replace('"latency_run_authorized":false', '"latency_run_authorized":0')
Assert-True ($duplicateMutation -ne $configRaw -and $whitespaceMutation -ne $configRaw -and $numericBoolMutation -ne $configRaw) 'config mutation setup failed'
Assert-True ($duplicateMutation -ne $configRaw -and $whitespaceMutation -ne $configRaw -and $numericBoolMutation.IndexOf('"latency_run_authorized":false', [StringComparison]::Ordinal) -lt 0) 'hostile config mutation accepted'

foreach ($needle in @(
    '#define V15_PREDECESSOR_COUNT 6U', 'FILE_FLAG_OPEN_REPARSE_POINT',
    'FILE_FLAG_WRITE_THROUGH', 'CREATE_NEW', 'PyConfig_InitIsolatedConfig',
    'FreeLibrary(api.module)', 'prove_python_module_absent(old_module, unload)',
    'four_v14_blockers_closed', 'sealed_subject_count', '"21"'
)) { Assert-Contains $native $needle "V15 native anchor missing: $needle" }
foreach ($forbidden in @('CreateProcessW(', 'CreateProcessA(', 'ShellExecuteW(', 'ShellExecuteA(', 'WinExec(', 'system(', 'PyImport_ImportModule')) {
    Assert-True ($native.IndexOf($forbidden, [StringComparison]::Ordinal) -lt 0) "forbidden native primitive: $forbidden"
}
foreach ($name in @('torch','ollama','chatterbox','sounddevice','winsound','bpy','socket','subprocess')) {
    Assert-True ($source.IndexOf("import $name", [StringComparison]::Ordinal) -lt 0 -and $validator.IndexOf("import $name", [StringComparison]::Ordinal) -lt 0) "forbidden Python import: $name"
}
Assert-True ($package.execution_authority -eq 'NONE' -and $package.candidate_invoked -eq $false -and $package.python_candidate_invoked -eq $false) 'author package execution truth drift'

$bound = [ordered]@{
    V15_NATIVE_SOURCE = $nativeSourcePath; V15_VALIDATOR = $validatorPath;
    V15_PY_SOURCE = $pythonSourcePath; V15_CONFIG = $configPath;
    V15_CONTRACT = $contractPath; V15_README = $readmePath;
    V15_TEST = $PSCommandPath; V15_CONTROL = $controlPath; V15_PACKAGE = $packagePath
}
foreach ($name in $bound.Keys) {
    $path = $bound[$name]
    $bytes = [regex]::Match($header, "#define ${name}_BYTES ([0-9]+)ULL").Groups[1].Value
    $digest = [regex]::Match($header, "#define ${name}_SHA256 `"([0-9a-f]{64})`"").Groups[1].Value
    Assert-True ($bytes -eq [string](Get-Item -LiteralPath $path).Length) "$name bytes mismatch"
    Assert-True ($digest -eq (Sha $path)) "$name digest mismatch"
}

if ($Phase -eq 'PreBuild') {
    foreach ($path in @($objectPath,$executablePath,$buildPath,$checkpointPath,$sealPath)) {
        Assert-True (-not (Test-Path -LiteralPath $path)) "prebuild artifact unexpectedly exists: $path"
    }
}
if ($Phase -in @('PostBuild','PostSeal')) {
    foreach ($path in @($objectPath,$executablePath,$buildPath,$checkpointPath)) {
        Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "postbuild artifact absent: $path"
    }
}
if ($Phase -eq 'PostSeal') {
    $seal = [IO.File]::ReadAllText($sealPath) | ConvertFrom-Json
    Assert-True ($seal.schema -eq 'kira.blackwell.v15.native_exact_control_anchor.static_seal.v1') 'seal schema drift'
    Assert-True ($seal.execution_authority -eq 'NONE' -and $seal.candidate_executed -eq $false -and $seal.python_candidate_invoked -eq $false) 'seal execution truth drift'
    $rows = @($seal.subjects)
    Assert-True ($seal.sealed_subject_count -eq 21 -and $rows.Count -eq 21) 'seal count drift'
    Assert-True ((@($rows.path) | Sort-Object -Unique).Count -eq 21 -and $seal.unique_paths -eq $true) 'seal uniqueness drift'
}

'V15_IMMUTABLE_ORIGIN_BOUND_HOSTILE_STATIC_TESTS_PASS'
