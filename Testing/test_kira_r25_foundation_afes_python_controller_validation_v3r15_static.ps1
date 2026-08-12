$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourcePath = Join-Path $root 'tools\native\kira_r25_afes_python_controller_validation_v3r15.c'
$headerPath = Join-Path $root 'tools\native\kira_r25_afes_python_controller_validation_v3r15_identity_anchor.h'
$exePath = Join-Path $root 'tools\native\kira_r25_afes_python_controller_validation_v3r15.exe'
$contractPath = Join-Path $root 'Avatar\avatar_builder\body_systems\kira_r25_foundation_afes_python_controller_validation_v3r15.json'
$controlPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_python_controller_validation_v3r15_static_preparation\attempt_01\RUNTIME_CONTROL_CHECKPOINT.md'
$manifestPath = Join-Path $root 'RecoverySprint\continuation_20260809\kira_r25_foundation_afes_locked_pair_execution_static_preparation\attempt_03r9\RETAINED_NATIVE_LOCK_MANIFEST.tsv'
$controllerPath = Join-Path $root 'tools\run_kira_r25_foundation_afes_locked_pair_v3r9.py'
$executionContractPath = Join-Path $root 'Avatar\avatar_builder\body_systems\kira_r25_foundation_afes_locked_pair_execution_v3r9.json'
$v3r14EvidencePath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\attempt_01\RUN_EVIDENCE.jsonl'
$v3r14ReceiptPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\attempt_01\NATIVE_DIAGNOSTIC_OUTCOME.receipt.bin'
$evidencePath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_python_controller_validation_v3r15_static_preparation\attempt_01\RUN_EVIDENCE.jsonl'
$outcomePath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_python_controller_validation_v3r15_static_preparation\attempt_01\PYTHON_CONTROLLER_VALIDATION_OUTCOME.receipt.bin'
$auditPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r15_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.tsv'
$auditDigestPath = Join-Path $root 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r15_fresh_static_audit\attempt_01\INDEPENDENT_AUDIT.sha256'

$script:run = 0
$script:failed = 0
function Assert-True([bool]$Condition, [string]$Name) {
    $script:run++
    if (-not $Condition) { $script:failed++; Write-Host "FAIL $Name" }
}
function Assert-False([bool]$Condition, [string]$Name) { Assert-True (-not $Condition) $Name }
function Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Count-Literal([string]$Text, [string]$Needle) {
    if ($Needle.Length -eq 0) { return 0 }
    $count = 0; $at = 0
    while (($at = $Text.IndexOf($Needle, $at, [StringComparison]::Ordinal)) -ge 0) { $count++; $at += $Needle.Length }
    return $count
}
function Is-LowerHex64([string]$Value) { return $Value -cmatch '^[0-9a-f]{64}$' }
function Exact-Manifest-Row([string]$Text, [string]$Label, [string]$Path, [long]$Bytes, [string]$Hash) {
    $row = "$Label`t$Path`t$Bytes`t$Hash`r`n"
    return (Count-Literal $Text $row) -eq 1
}

foreach ($path in @($sourcePath,$headerPath,$exePath,$contractPath,$controlPath,$manifestPath,$controllerPath,$executionContractPath,$v3r14EvidencePath,$v3r14ReceiptPath)) {
    Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "required:$path"
}

$source = [IO.File]::ReadAllText($sourcePath, [Text.UTF8Encoding]::new($false, $true))
$header = [IO.File]::ReadAllText($headerPath, [Text.UTF8Encoding]::new($false, $true))
$control = [IO.File]::ReadAllText($controlPath, [Text.UTF8Encoding]::new($false, $true))
$manifest = [IO.File]::ReadAllText($manifestPath, [Text.UTF8Encoding]::new($false, $true))
$controller = [IO.File]::ReadAllText($controllerPath, [Text.UTF8Encoding]::new($false, $true))
$contract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json
$execution = Get-Content -Raw -LiteralPath $executionContractPath | ConvertFrom-Json

Assert-True ($contract.schema -ceq 'kira.avatar.r25.foundation_afes_python_controller_validation.v3r15') 'contract-schema'
Assert-True ($contract.status -ceq 'STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY') 'contract-static-status'
Assert-True ($contract.predecessor.status -ceq 'CONSUMED_SUCCESS_NO_RETRY') 'predecessor-consumed'
Assert-True ($contract.controller_validation.build_execution_plan_called -eq $false) 'plan-builder-not-called'
Assert-True ($contract.controller_validation.bootstrap_evaluated -eq $false) 'bootstrap-not-evaluated'
Assert-True ($contract.controller_validation.native_broker_created -eq $false) 'broker-not-created'
Assert-True ($contract.receipt.creation -ceq 'CREATE_NEW_WRITE_THROUGH') 'create-new-contract'
Assert-True ($contract.receipt.records -eq 2) 'two-record-contract'
Assert-True ($contract.forbidden -contains 'process creation') 'process-forbidden'
Assert-True ($contract.forbidden -contains 'Blender or Blend access') 'blender-forbidden'
Assert-True ($contract.forbidden -contains 'body, mesh, armature, material, anatomy, or movement mutation') 'body-forbidden'
Assert-True ($control.Contains('NO_EXECUTION_AUTHORITY')) 'control-no-authority'
Assert-True ($control.Contains('NO_PREDECESSOR_RETRY')) 'control-no-retry'
Assert-True ($control.Contains('all 137 retained graph byte snapshots')) 'control-narrow-stop-reason'

Assert-True ((Count-Literal $source 'int wmain(') -eq 1) 'one-entrypoint'
Assert-True ($source.Contains('if (argc != 1) return 2;')) 'no-arg-gate'
Assert-True ($source.Contains('CREATE_NEW')) 'create-new-source'
Assert-True ($source.Contains('FILE_FLAG_WRITE_THROUGH')) 'write-through-source'
Assert-True ($source.Contains('FlushFileBuffers')) 'durable-flush-source'
Assert-True ($source.Contains('GetFinalPathNameByHandleW')) 'final-path-source'
Assert-True ($source.Contains('FileIdInfo')) 'file-id-source'
Assert-True ($source.Contains('same_identity')) 'same-identity-source'
Assert-True ($source.Contains('trailing_bytes != 0U')) 'trailing-byte-rejection'
Assert-True ($source.Contains('LoadLibraryExW(PYTHON_DLL_PATH')) 'exact-python-load-call'
Assert-True ($source.Contains('LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32')) 'safe-load-flags'
Assert-True ($source.Contains('SetDefaultDllDirectories')) 'default-dll-policy'
Assert-True ($source.Contains('GetProcAddress')) 'dynamic-export-resolution'
Assert-True ($source.Contains('PyConfig_InitIsolatedConfig')) 'isolated-config-export'
Assert-True ($source.Contains('config.use_environment = 0')) 'environment-disabled'
Assert-True ($source.Contains('config.user_site_directory = 0')) 'user-site-disabled'
Assert-True ($source.Contains('config.site_import = 0')) 'site-disabled'
Assert-True ($source.Contains('config.write_bytecode = 0')) 'bytecode-disabled'
Assert-True ($source.Contains('config.safe_path = 1')) 'safe-path-enabled'
Assert-True ($source.Contains('config.module_search_paths_set = 1')) 'explicit-search-path'
Assert-True ($source.Contains('api.finalize()')) 'python-finalize'
Assert-True ($source.Contains('FreeLibrary(api.module)')) 'python-unload'
Assert-True ($source.Contains('verify_controller_exports')) 'export-validation'
Assert-True ($source.Contains('CONTROLLER_EXPORTED_CALLS')) 'exact-export-tuple'
Assert-True ($source.Contains('__v3r15_contract_projection_valid__')) 'projection-marker'
Assert-False ($source.Contains('_build_execution_plan"') -and $source.Contains('PyObject_Call')) 'no-plan-builder-call-api'
Assert-False ($source.Contains('run_child(')) 'no-run-child'
Assert-False ($source.Contains('CreateProcess')) 'no-create-process'
Assert-False ($source.Contains('ShellExecute')) 'no-shell-execute'
Assert-False ($source.Contains('WinExec')) 'no-winexec'
Assert-False ($source.Contains('DeleteFile')) 'no-delete'
Assert-False ($source.Contains('MoveFile')) 'no-rename'
Assert-False ($source.Contains('ReplaceFile')) 'no-replace'
Assert-False ($source.Contains('CREATE_ALWAYS')) 'no-create-always'
Assert-False ($source.Contains('TRUNCATE_EXISTING')) 'no-truncate'
Assert-False ($source.Contains('OPEN_ALWAYS')) 'no-open-always'
Assert-False ($source.Contains('blender.exe')) 'no-blender-image-path'
Assert-False ($source.Contains('foundation.blend')) 'no-blend-path'

Assert-True ($controller.StartsWith('#!/usr/bin/env python3')) 'controller-exact-text-readable'
Assert-True ($controller.Contains('This source has no filesystem, process, handle, lock, Job, outcome, or Blender')) 'controller-purity-declaration'
Assert-True ($controller.Contains('Direct execution is deliberately inert.')) 'controller-inert-declaration'
Assert-False ($controller.Contains('import subprocess')) 'controller-no-subprocess'
Assert-False ($controller.Contains('open(')) 'controller-no-open'
Assert-False ($controller.Contains('Path(')) 'controller-no-path-call'
Assert-False ($controller -cmatch '(?m)^if __name__') 'controller-no-main-entry'

$rows = @(
    @('python_runtime_dll','C:/Python314/python314.dll',6767440,'a07f7d09c3121492bb066535c6d0811df5fbc2090cbca7031a97bb47ce1480c9'),
    @('retained_stdlib_zip','tools/native/runtime/python314_stdlib_v3r4.zip',28997479,'7e07541a67b8eba5835c9c371ec90e5732fba6602576ae0a6f22e09b09271846'),
    @('parent_controller','tools/run_kira_r25_foundation_afes_locked_pair_v3r9.py',50907,'60674e104d69ac9166aca7ea9001ff32e8494d07677748fbb633955ee1d9ebaf'),
    @('execution_contract','Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v3r9.json',146969,'f50df32a70093cf968e2d6be7c7de228d84f003605f854b97bfa542b9ea396d5')
)
foreach ($row in $rows) {
    Assert-True (Exact-Manifest-Row $manifest $row[0] $row[1] ([long]$row[2]) $row[3]) "manifest-exact:$($row[0])"
    Assert-False (Exact-Manifest-Row ($manifest + "$($row[0])`t$($row[1])`t$($row[2])`t$($row[3])`r`n") $row[0] $row[1] ([long]$row[2]) $row[3]) "manifest-duplicate:$($row[0])"
    Assert-False (Exact-Manifest-Row $manifest $row[0] $row[1] ([long]$row[2] + 1) $row[3]) "manifest-size-mutation:$($row[0])"
    Assert-False (Exact-Manifest-Row $manifest $row[0] $row[1] ([long]$row[2]) ('0' * 64)) "manifest-hash-mutation:$($row[0])"
}

Assert-True ($execution.schema -ceq 'kira.avatar.r25.foundation_afes_locked_pair_execution.v3r9') 'retained-contract-schema'
Assert-True ($execution.attempt_id -ceq 'attempt_03r9') 'retained-contract-attempt'
Assert-True ($execution.required_fresh_run_count -eq 2) 'retained-contract-two-runs'
Assert-True ($execution.scope.body_work_only -eq $true) 'retained-body-only'
Assert-True ($execution.scope.blend_mutation_allowed -eq $false) 'retained-no-blend-mutation'
Assert-True ($execution.scope.body_authoring_allowed -eq $false) 'retained-no-body-authoring'
Assert-True ($execution.bindings.python_runtime_dll.sha256 -ceq $rows[0][3]) 'contract-python-binding'
Assert-True ($execution.bindings.retained_stdlib_zip.sha256 -ceq $rows[1][3]) 'contract-stdlib-binding'
Assert-True ($execution.bindings.parent_controller.sha256 -ceq $rows[2][3]) 'contract-controller-binding'

$macroPairs = [regex]::Matches($header, '(?m)^#define\s+(V3R15_[A-Z0-9_]+_SHA256)\s+"([0-9a-f]{64})"$')
Assert-True ($macroPairs.Count -ge 12) 'header-hash-macro-count'
foreach ($match in $macroPairs) { Assert-True (Is-LowerHex64 $match.Groups[2].Value) "header-lower-hash:$($match.Groups[1].Value)" }
Assert-True ($header.Contains('#define V3R15_AUTHOR_ID "codex_r25_afes_v3r15_static_author"')) 'distinct-author-id'

$exeBytes = [IO.File]::ReadAllBytes($exePath)
Assert-True ($exeBytes.Length -gt 1024) 'pe-nonempty'
Assert-True ($exeBytes[0] -eq 0x4d -and $exeBytes[1] -eq 0x5a) 'pe-mz'
$peOffset = [BitConverter]::ToInt32($exeBytes, 0x3c)
Assert-True ($peOffset -gt 0 -and $peOffset + 26 -lt $exeBytes.Length) 'pe-offset'
Assert-True ($exeBytes[$peOffset] -eq 0x50 -and $exeBytes[$peOffset+1] -eq 0x45) 'pe-signature'
Assert-True ([BitConverter]::ToUInt16($exeBytes, $peOffset + 4) -eq 0x8664) 'pe-x64'
Assert-True ([BitConverter]::ToUInt16($exeBytes, $peOffset + 24) -eq 0x20b) 'pe32-plus'
$ascii = [Text.Encoding]::ASCII.GetString($exeBytes)
$dumpbin = Get-ChildItem -LiteralPath 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC' -Directory |
    Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName 'bin\Hostx64\x64\dumpbin.exe' } |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1
Assert-True ($null -ne $dumpbin) 'dumpbin-found'
$imports = if ($null -ne $dumpbin) { (& $dumpbin /imports $exePath 2>&1 | Out-String) } else { '' }
Assert-False ($imports.Contains('python314.dll')) 'no-normal-or-delay-python-import-name'
Assert-True ($imports.Contains('bcrypt.dll')) 'bcrypt-import'
Assert-False ($ascii.Contains('blender.exe')) 'no-blender-pe-name'
Assert-False ($ascii.Contains('CreateProcessW')) 'no-process-pe-import'
Assert-True ($ascii.Contains('LoadLibraryExW')) 'loadlibrary-pe-import'
Assert-True ($ascii.Contains('GetProcAddress')) 'getproc-pe-import'

Assert-False (Test-Path -LiteralPath $evidencePath) 'runtime-evidence-absent'
Assert-False (Test-Path -LiteralPath $outcomePath) 'runtime-outcome-absent'
Assert-False (Test-Path -LiteralPath $auditPath) 'future-audit-absent'
Assert-False (Test-Path -LiteralPath $auditDigestPath) 'future-audit-digest-absent'
Assert-True ((Sha $v3r14EvidencePath) -ceq '8132271b60034d3afbad5138390d8a2e49a5bee91aeb2e0c9d9b1c0a97b552b1') 'v3r14-evidence-preserved'
Assert-True ((Sha $v3r14ReceiptPath) -ceq 'd6734ad3faaae2ca0c60c969d380af9d1c834fed2b87b45034da8336fcc1a58e') 'v3r14-receipt-preserved'

Write-Host ("V3R15_STATIC_TESTS run={0} failed={1}" -f $script:run, $script:failed)
if ($script:failed -ne 0) { exit 1 }
exit 0
