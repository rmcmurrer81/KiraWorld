$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$SourcePath = Join-Path $Root 'tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.c'
$HeaderPath = Join-Path $Root 'tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12_identity_anchor.h'
$ExePath = Join-Path $Root 'tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.exe'
$Source = Get-Content -Raw -LiteralPath $SourcePath
$Header = Get-Content -Raw -LiteralPath $HeaderPath
$script:Ran = 0
$script:Failed = 0

function Check([bool]$Condition, [string]$Name) {
    $script:Ran++
    if (-not $Condition) {
        $script:Failed++
        Write-Host "FAIL`t$Name"
    } else {
        Write-Host "PASS`t$Name"
    }
}

function Exact-Count([string]$Text, [string]$Needle) {
    return ([regex]::Matches($Text, [regex]::Escape($Needle))).Count
}

function Macro-Hash([string]$Name) {
    $m = [regex]::Match($Header, "(?m)^#define\s+$Name`_SHA256\s+\`"([0-9a-f]{64})\`"\s*$")
    if (-not $m.Success) { throw "missing hash macro $Name" }
    return $m.Groups[1].Value
}

function Macro-Bytes([string]$Name) {
    $m = [regex]::Match($Header, "(?m)^#define\s+$Name`_BYTES\s+([0-9]+)ULL\s*$")
    if (-not $m.Success) { throw "missing byte macro $Name" }
    return [uint64]$m.Groups[1].Value
}

function Check-BoundSubject([string]$Name, [string]$Relative) {
    $path = Join-Path $Root $Relative
    $item = Get-Item -LiteralPath $path
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    Check ($item.Length -eq (Macro-Bytes $Name)) "$Name exact byte length"
    Check ($hash -ceq (Macro-Hash $Name)) "$Name exact SHA-256"
}

Check ($Source -match 'KIRA_R25_AFES_PREOUTCOME_DIAGNOSTIC_AUDIT_V3R12\\t1') 'v3r12 canonical audit magic'
Check ($Source -match 'kira\.r25\.afes\.v3r12\.native_stage\.v1') 'evidence schema is v3r12'
Check ($Source -notmatch 'v3r11|V3R11') 'no inherited v3r11 runtime identifier'
Check ((Exact-Count $Source 'CreateProcessW(') -eq 1) 'exactly one self-child creation call'
Check ((Exact-Count $Source 'CREATE_SUSPENDED | CREATE_NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT') -eq 1) 'child created suspended with explicit startup info'
Check ((Exact-Count $Source 'PROC_THREAD_ATTRIBUTE_HANDLE_LIST') -eq 1) 'explicit inherited-handle allowlist'
Check ($Source -match 'HANDLE inherited_handles\[5\]') 'exact five-handle allowlist storage'
Check ($Source -match 'inherited_handles\[0\] = g_evidence;[\s\S]*inherited_handles\[4\] = parent_process;') 'five allowlisted handles assigned explicitly'
Check ($Source -match 'CREATE_NEW, FILE_ATTRIBUTE_NORMAL \| FILE_FLAG_WRITE_THROUGH') 'one-shot evidence reservation is create-new and write-through'
Check ((Exact-Count $Source 'ResumeThread(') -eq 1) 'exactly one child resume call'
Check ($Source -match 'find_child_surface[\s\S]*argc == 9[\s\S]*--v3r12-child[\s\S]*observer-owned') 'child surface has exact shape and marker'
Check ($Source -match 'validate_child_provenance[\s\S]*capability_os_identity_or_binding_invalid') 'child validates observer capability and OS identities'
Check ($Source -match 'capability_record\.parent_pid[\s\S]*capability_record\.child_pid[\s\S]*evidence_identity[\s\S]*BCryptGenRandom') 'observer binds parent, child, evidence, and random nonce'
Check ($Source -match 'GetProcessTimes[\s\S]*CreateToolhelp32Snapshot[\s\S]*QueryFullProcessImageNameW') 'child provenance includes creation time, direct parent, and image'
Check ($Source.Contains("if (*scan == '\r' || *scan == '\0') return -1;") -and $Source.Contains('} else if (*newline_style_io != style) {')) 'canonical line parser rejects mixed endings and bare CR'
Check ($Source -match "data\[size - 1U\] != '\\n'") 'manifest and audit require final terminator'
Check ($Source -match 'KIRA_R25_AFES_RETAINED_MANIFEST_V3R9\\t1') 'exact retained manifest magic checked'
Check ($Source -match 'V3R12_CONTRACT_SHA256[\s\S]*V3R12_SOURCE_SHA256[\s\S]*V3R12_STATIC_TEST_SHA256') 'contract, source, and test hashes are compile-time bound'
Check ($Source -match 'V3R12_CONTROL_CHECKPOINT_SHA256[\s\S]*V3R12_V3R10_REJECTION_SHA256[\s\S]*V3R12_MANIFEST_SHA256[\s\S]*V3R12_POSTMORTEM_SHA256') 'control and inherited evidence hashes are compile-time bound'
Check ($Source -match 'identity_anchor_sha256[\s\S]*state->identity_anchor\.sha256') 'fresh audit binds exact identity-anchor bytes'
Check ($Source -match 'strcmp\(values\[2\], V3R12_AUTHOR_ID\) == 0') 'fresh auditor must differ from author'
Check ($Source -notmatch '\bLoadLibrary(?:Ex)?[AW]?\s*\(') 'no DLL loading call'
Check ($Source -notmatch '\bGetProcAddress\s*\(') 'no dynamic symbol resolution call'
Check ($Source -notmatch '\bPy_[A-Za-z0-9_]*\s*\(') 'no Python API call'
Check ($Source -match 'inspect_python_dll_pe_readonly[\s\S]*IMAGE_DOS_SIGNATURE[\s\S]*IMAGE_NT_SIGNATURE') 'Python DLL is inspected as PE bytes only'
Check ($Source -match 'FILE_ADD_FILE \| FILE_READ_ATTRIBUTES \| SYNCHRONIZE') 'outcome parent probe is access-only'
Check ($Source -match 'FILE_FLAG_BACKUP_SEMANTICS \| FILE_FLAG_OPEN_REPARSE_POINT') 'outcome parent probe does not create receipt'
Check ($Source -match 'CHILD_PRE_OUTCOME_STOP_EXIT 41U') 'terminal is explicit pre-outcome stop'
Check ($Source -notmatch 'blender\.exe|--background|bpy\.|AFES_[A-Za-z0-9_]*\s*\(') 'no Blender or AFES invocation surface'

Check-BoundSubject 'V3R12_CONTRACT' 'Avatar\avatar_builder\body_systems\kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r12.json'
Check-BoundSubject 'V3R12_SOURCE' 'tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.c'
Check-BoundSubject 'V3R12_STATIC_TEST' 'Testing\test_kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r12_static.ps1'
Check-BoundSubject 'V3R12_CONTROL_CHECKPOINT' 'RecoverySprint\continuation_20260810\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12_static_preparation\attempt_01\RUNTIME_CONTROL_CHECKPOINT.md'
Check-BoundSubject 'V3R12_V3R10_REJECTION' 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r10_fresh_static_audit\attempt_01\CHECKPOINT.md'
Check-BoundSubject 'V3R12_MANIFEST' 'RecoverySprint\continuation_20260809\kira_r25_foundation_afes_locked_pair_execution_static_preparation\attempt_03r9\RETAINED_NATIVE_LOCK_MANIFEST.tsv'
Check-BoundSubject 'V3R12_POSTMORTEM' 'RecoverySprint\continuation_20260810\kira_r25_afes_v3r9_consumed_run_static_postmortem\attempt_01\CHECKPOINT.md'

$manifestPath = Join-Path $Root 'RecoverySprint\continuation_20260809\kira_r25_foundation_afes_locked_pair_execution_static_preparation\attempt_03r9\RETAINED_NATIVE_LOCK_MANIFEST.tsv'
$manifestBytes = [IO.File]::ReadAllBytes($manifestPath)
$lf = @($manifestBytes | Where-Object { $_ -eq 10 }).Count
$cr = @($manifestBytes | Where-Object { $_ -eq 13 }).Count
$allCrStructural = $true
for ($i = 0; $i -lt $manifestBytes.Length; $i++) {
    if ($manifestBytes[$i] -eq 13 -and ($i + 1 -ge $manifestBytes.Length -or $manifestBytes[$i + 1] -ne 10)) { $allCrStructural = $false }
}
Check ($lf -gt 0 -and $lf -eq $cr -and $allCrStructural) 'retained manifest is consistently exact CRLF'
$manifestText = [Text.Encoding]::ASCII.GetString($manifestBytes)
$rows = $manifestText -split "`r`n"
Check ($rows[-1] -eq '' -and $rows[0] -ceq "KIRA_R25_AFES_RETAINED_MANIFEST_V3R9`t1") 'retained manifest exact magic and final CRLF'

Check (Test-Path -LiteralPath $ExePath) 'compiled candidate exists'
if (Test-Path -LiteralPath $ExePath) {
    $pe = [IO.File]::ReadAllBytes($ExePath)
    $peOffset = [BitConverter]::ToInt32($pe, 0x3c)
    Check ($pe[0] -eq 0x4d -and $pe[1] -eq 0x5a -and [BitConverter]::ToUInt32($pe, $peOffset) -eq 0x00004550) 'compiled candidate has valid MZ and PE signatures'
    Check ([BitConverter]::ToUInt16($pe, $peOffset + 4) -eq 0x8664) 'compiled candidate is x64'
    $ascii = [Text.Encoding]::ASCII.GetString($pe)
    Check ($ascii -notmatch '(?i)python[0-9]*\.dll|blender\.exe') 'compiled import/string surface has no Python or Blender image name'
}

Write-Host "RAN`t$script:Ran"
Write-Host "FAILED`t$script:Failed"
if ($script:Failed -ne 0) { exit 1 }
