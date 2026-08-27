[CmdletBinding()]
param(
    [switch]$Execute
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# V3 repairs the rejected V2 directory-namespace and process-image identity
# boundary. This source is execution-capable only after a different
# independent audit and an externally authenticated one-use authority exist.
# The independent V3 audit is present; positive one-use authority remains absent.
# Running without -Execute stops before native initialization, and execution
# cannot proceed without a separately issued, currently valid authority file.
$ProjectRoot = 'C:\Users\robmc\Kira'
$PolicyRel = 'Avatar/avatar_builder/tooling/blender_5_1_separate_foundation_trusted_launcher_v3.json'
$WorkerPolicyCompatRel = 'Avatar/avatar_builder/tooling/blender_5_1_separate_foundation_trusted_launcher_v2.json'
$RuntimeIdentityRel = 'Avatar/avatar_builder/tooling/blender_5_1_runtime_identity_v1.json'
$WorkerRel = 'tools/blender_author_separate_foundation_bodies_successor_v1.py'
$WorkerConfigRel = 'Avatar/avatar_builder/tooling/blender_5_1_separate_foundation_authoring_successor_v1.json'
$LauncherRel = 'tools/run_avatar_builder_blender_5_1_separate_foundation_trusted_launcher_v3.ps1'
$IndependentAuditRel = 'System/Docs/AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_TRUSTED_LAUNCHER_V3_INDEPENDENT_AUDIT.json'
$WorkerAuditCompatRel = 'System/Docs/AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_TRUSTED_LAUNCHER_V2_INDEPENDENT_AUDIT.json'
$AuthorityRel = 'Avatar/avatar_builder/runtime/separate_foundation_authoring_v1/RUN_AUTHORIZATION_V2.json'
$ConsumptionRel = 'Avatar/avatar_builder/runtime/separate_foundation_authoring_v1/RUN_AUTHORIZATION_V2.consumed.json'
$WorkerClaimRel = 'Avatar/avatar_builder/runtime/separate_foundation_authoring_v1/RUN_AUTHORIZATION_V2.worker_claimed.json'
$AuthoringStaticReceiptRel = 'System/Docs/AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_AUTHORING_SUCCESSOR_RECEIPT_20260826.json'
$AuthoringStaticReceiptBytes = 1924
$AuthoringStaticReceiptSha256 = '070f71a3296e0e3591a6ed22071db0ee99a5aa2782397513c713ddd83d7fee08'
$OutputContractSha256 = '11a564fa1bc9f5a4b21a59dfb4eecce622c11418be8a9c14babb4a2f78274c71'
$MaxJsonBytes = 1048576
$CanonicalWindowsRoot = 'C:\Windows'
$CanonicalSystemDirectory = 'C:\Windows\System32'

function Get-ProjectPath([string]$Relative, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or $Relative.Contains('\') -or [IO.Path]::IsPathRooted($Relative)) {
        throw "Unsafe $Label path"
    }
    $Parts = $Relative.Split('/')
    if ($Parts -contains '..' -or $Parts -contains '.' -or $Parts -contains '') {
        throw "Unsafe $Label path"
    }
    $Path = [IO.Path]::GetFullPath([IO.Path]::Combine($ProjectRoot, [IO.Path]::Combine($Parts)))
    if (-not $Path.StartsWith($ProjectRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label escaped project root"
    }
    return $Path
}

function Assert-NoReparseAncestry([string]$Path, [string]$Label) {
    $Current = [IO.Path]::GetFullPath($Path)
    while ($true) {
        if (Test-Path -LiteralPath $Current) {
            $Item = Get-Item -LiteralPath $Current -Force
            if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "$Label contains a reparse point: $Current"
            }
        }
        $Parent = [IO.Directory]::GetParent($Current)
        if ($null -eq $Parent) { return }
        $Current = $Parent.FullName
    }
}

function Get-Sha256Bytes([byte[]]$Bytes) {
    $Hasher = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($Hasher.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $Hasher.Dispose() }
}

function Get-CanonicalJsonBytes([object]$Value) {
    $Text = $Value | ConvertTo-Json -Depth 32 -Compress
    return [Text.UTF8Encoding]::new($false).GetBytes($Text + "`n")
}

function Assert-ExactKeys([object]$Value, [string[]]$Expected, [string]$Label) {
    if ($null -eq $Value) { throw "$Label is absent" }
    $Actual = @($Value.PSObject.Properties.Name | Sort-Object -CaseSensitive)
    $Wanted = @($Expected | Sort-Object -CaseSensitive)
    if (($Actual -join "`n") -cne ($Wanted -join "`n")) { throw "$Label key set differs" }
}

function Assert-JsonBoolean([object]$Value, [string]$Label) {
    if ($null -eq $Value -or $Value -isnot [bool]) { throw "$Label must be a JSON boolean" }
}

function Assert-JsonInteger([object]$Value, [string]$Label) {
    if ($null -eq $Value -or ($Value -isnot [int32] -and $Value -isnot [int64])) { throw "$Label must be a JSON integer" }
}

function Assert-JsonString([object]$Value, [string]$Label) {
    if ($null -eq $Value -or $Value -isnot [string]) { throw "$Label must be a JSON string" }
}

function Assert-JsonArray([object]$Value, [string]$Label) {
    if ($null -eq $Value -or $Value -isnot [Array]) { throw "$Label must be a JSON array" }
}

function Read-JsonBinding([string]$Path, [string]$Label) {
    Assert-NoReparseAncestry $Path $Label
    if (-not [IO.File]::Exists($Path)) { throw "$Label is absent" }
    $Before = Get-Item -LiteralPath $Path -Force
    if (($Before.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "$Label is a reparse point" }
    if ($Before.Length -le 0 -or $Before.Length -gt $MaxJsonBytes) { throw "$Label JSON byte boundary differs" }
    $Raw = [IO.File]::ReadAllBytes($Path)
    $After = Get-Item -LiteralPath $Path -Force
    if ($Raw.Length -ne $Before.Length -or $After.Length -ne $Before.Length -or $After.LastWriteTimeUtc.Ticks -ne $Before.LastWriteTimeUtc.Ticks) {
        throw "$Label changed while read"
    }
    $Text = [Text.UTF8Encoding]::new($false, $true).GetString($Raw)
    [AvatarFoundationNativeV2]::AssertUniqueJsonObjectKeys($Raw)
    $Document = $Text | ConvertFrom-Json
    if ($null -eq $Document -or $Document -is [Array]) { throw "$Label must be one JSON object" }
    return [pscustomobject]@{ Path = $Path; Raw = $Raw; Document = $Document; Bytes = [long]$Raw.Length; Sha256 = Get-Sha256Bytes $Raw }
}

function Assert-Binding([object]$Binding, [long]$Bytes, [string]$Sha256, [string]$Label) {
    if ($Binding.Bytes -ne $Bytes -or $Binding.Sha256 -cne $Sha256) { throw "$Label byte/hash binding differs" }
}

function New-LockRow([string]$Path, [long]$Bytes, [string]$Sha256, [string]$FileId = '') {
    return [pscustomobject]@{ path = $Path; bytes = $Bytes; sha256 = $Sha256; file_id = $FileId }
}

function Initialize-NativeBoundary {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

public static class AvatarFoundationNativeV2 {
    public const uint GENERIC_READ = 0x80000000;
    public const uint FILE_READ_ATTRIBUTES = 0x00000080;
    public const uint DELETE_ACCESS = 0x00010000;
    public const uint FILE_SHARE_READ = 0x00000001;
    public const uint FILE_SHARE_WRITE = 0x00000002;
    public const uint FILE_SHARE_DELETE = 0x00000004;
    public const uint OPEN_EXISTING = 3;
    public const uint FILE_FLAG_BACKUP_SEMANTICS = 0x02000000;
    public const uint FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000;
    public const uint FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400;
    public const uint CREATE_SUSPENDED = 0x00000004;
    public const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
    public const uint MOVEFILE_WRITE_THROUGH = 0x00000008;
    public const uint DUPLICATE_SAME_ACCESS = 0x00000002;
    public const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    public const uint WAIT_OBJECT_0 = 0;
    public const uint WAIT_TIMEOUT = 258;
    public const int JobObjectExtendedLimitInformation = 9;
    public const int FileIdInfo = 18;
    public const int FileRenameInfo = 3;

    [StructLayout(LayoutKind.Sequential)]
    public struct STARTUPINFO {
        public uint cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public uint dwX; public uint dwY; public uint dwXSize; public uint dwYSize;
        public uint dwXCountChars; public uint dwYCountChars; public uint dwFillAttribute;
        public uint dwFlags; public ushort wShowWindow; public ushort cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public uint dwProcessId; public uint dwThreadId; }
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public long PerProcessUserTimeLimit; public long PerJobUserTimeLimit; public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize; public UIntPtr MaximumWorkingSetSize; public uint ActiveProcessLimit;
        public UIntPtr Affinity; public uint PriorityClass; public uint SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS {
        public ulong ReadOperationCount; public ulong WriteOperationCount; public ulong OtherOperationCount;
        public ulong ReadTransferCount; public ulong WriteTransferCount; public ulong OtherTransferCount;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation; public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit; public UIntPtr JobMemoryLimit; public UIntPtr PeakProcessMemoryUsed; public UIntPtr PeakJobMemoryUsed;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct FILE_ID_INFO { public ulong VolumeSerialNumber; [MarshalAs(UnmanagedType.ByValArray, SizeConst=16)] public byte[] FileId; }
    [StructLayout(LayoutKind.Sequential)]
    public struct BY_HANDLE_FILE_INFORMATION {
        public uint FileAttributes; public System.Runtime.InteropServices.ComTypes.FILETIME CreationTime;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastAccessTime; public System.Runtime.InteropServices.ComTypes.FILETIME LastWriteTime;
        public uint VolumeSerialNumber; public uint FileSizeHigh; public uint FileSizeLow; public uint NumberOfLinks;
        public uint FileIndexHigh; public uint FileIndexLow;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_BASIC_INFORMATION {
        public IntPtr Reserved1; public IntPtr PebBaseAddress;
        public IntPtr Reserved2_0; public IntPtr Reserved2_1;
        public IntPtr UniqueProcessId; public IntPtr Reserved3;
    }

    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern SafeFileHandle CreateFileW(string name, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool GetFileInformationByHandleEx(SafeFileHandle handle, int infoClass, out FILE_ID_INFO info, uint size);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool GetFileInformationByHandle(SafeFileHandle handle, out BY_HANDLE_FILE_INFORMATION info);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool SetFileInformationByHandle(SafeFileHandle handle, int infoClass, IntPtr info, uint size);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool CreateProcessW(string application, StringBuilder commandLine, IntPtr processAttributes, IntPtr threadAttributes, bool inheritHandles, uint flags, IntPtr environment, string currentDirectory, ref STARTUPINFO startupInfo, out PROCESS_INFORMATION processInformation);
    [DllImport("ntdll.dll")]
    static extern int NtQueryInformationProcess(IntPtr process, int processInformationClass, out PROCESS_BASIC_INFORMATION processInformation, uint processInformationLength, out uint returnLength);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool ReadProcessMemory(IntPtr process, IntPtr baseAddress, out IntPtr buffer, UIntPtr size, out UIntPtr bytesRead);
    [DllImport("psapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern uint GetMappedFileNameW(IntPtr process, IntPtr address, StringBuilder fileName, uint size);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern uint QueryDosDeviceW(string deviceName, StringBuilder targetPath, uint maxChars);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr CreateJobObjectW(IntPtr security, string name);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern bool SetInformationJobObject(IntPtr job, int infoClass, IntPtr info, uint length);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern bool GetExitCodeProcess(IntPtr process, out uint exitCode);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern bool TerminateJobObject(IntPtr job, uint exitCode);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern bool TerminateProcess(IntPtr process, uint exitCode);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool MoveFileExW(string existingName, string newName, uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateDirectoryW(string path, IntPtr securityAttributes);
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool DuplicateHandle(IntPtr sourceProcess, IntPtr sourceHandle, IntPtr targetProcess, out IntPtr targetHandle, uint desiredAccess, bool inheritHandle, uint options);

    public static SafeFileHandle OpenDirectoryIdentity(string path) {
        // Deliberately omit FILE_SHARE_DELETE: the directory itself cannot be
        // renamed or deleted while its identity is part of the live closure.
        var share = FILE_SHARE_READ | FILE_SHARE_WRITE;
        var h = CreateFileW(path, FILE_READ_ATTRIBUTES, share, IntPtr.Zero, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, IntPtr.Zero);
        if (h.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to open directory identity handle");
        return h;
    }
    public static SafeFileHandle OpenDirectoryIdentityForRename(string path) {
        var share = FILE_SHARE_READ | FILE_SHARE_WRITE;
        var h = CreateFileW(path, FILE_READ_ATTRIBUTES | DELETE_ACCESS, share, IntPtr.Zero, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, IntPtr.Zero);
        if (h.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to open rename-bound directory identity handle");
        return h;
    }
    public static SafeFileHandle OpenFileDenyWriteDelete(string path) {
        var h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, IntPtr.Zero, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, IntPtr.Zero);
        if (h.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to open deny-write/delete file handle");
        return h;
    }
    public static SafeFileHandle OpenOutputFileDenyWriteAllowRename(string path) {
        var h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, IntPtr.Zero, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, IntPtr.Zero);
        if (h.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to lock staged output");
        return h;
    }
    public static string FileId128(SafeFileHandle handle) {
        FILE_ID_INFO info;
        if (!GetFileInformationByHandleEx(handle, FileIdInfo, out info, (uint)Marshal.SizeOf(typeof(FILE_ID_INFO)))) throw new Win32Exception(Marshal.GetLastWin32Error());
        Array.Reverse(info.FileId);
        return "0x" + BitConverter.ToString(info.FileId).Replace("-", "").ToLowerInvariant();
    }
    public static string StableVolumeFileIdentity(SafeFileHandle handle) {
        FILE_ID_INFO info;
        if (!GetFileInformationByHandleEx(handle, FileIdInfo, out info, (uint)Marshal.SizeOf(typeof(FILE_ID_INFO)))) throw new Win32Exception(Marshal.GetLastWin32Error());
        Array.Reverse(info.FileId);
        return "volume=0x" + info.VolumeSerialNumber.ToString("x16") + ";file=0x" + BitConverter.ToString(info.FileId).Replace("-", "").ToLowerInvariant();
    }
    public static bool IsReparsePoint(SafeFileHandle handle) {
        BY_HANDLE_FILE_INFORMATION info;
        if (!GetFileInformationByHandle(handle, out info)) throw new Win32Exception(Marshal.GetLastWin32Error());
        return (info.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0;
    }
    public static void RenameDirectoryHandleNoReplace(SafeFileHandle handle, string finalPath) {
        byte[] name = Encoding.Unicode.GetBytes(finalPath);
        int rootOffset = IntPtr.Size == 8 ? 8 : 4;
        int lengthOffset = rootOffset + IntPtr.Size;
        int nameOffset = lengthOffset + 4;
        int total = nameOffset + name.Length;
        IntPtr buffer = Marshal.AllocHGlobal(total);
        try {
            for (int index = 0; index < total; index++) Marshal.WriteByte(buffer, index, 0);
            Marshal.WriteByte(buffer, 0, 0); // ReplaceIfExists = FALSE
            Marshal.WriteIntPtr(buffer, rootOffset, IntPtr.Zero);
            Marshal.WriteInt32(buffer, lengthOffset, name.Length);
            Marshal.Copy(name, 0, IntPtr.Add(buffer, nameOffset), name.Length);
            if (!SetFileInformationByHandle(handle, FileRenameInfo, buffer, (uint)total)) throw new Win32Exception(Marshal.GetLastWin32Error(), "Atomic handle-bound no-replace directory rename failed");
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }
    public static string ProcessMappedImageDevicePath(IntPtr process) {
        PROCESS_BASIC_INFORMATION basic;
        uint returned;
        int status = NtQueryInformationProcess(process, 0, out basic, (uint)Marshal.SizeOf(typeof(PROCESS_BASIC_INFORMATION)), out returned);
        if (status != 0 || basic.PebBaseAddress == IntPtr.Zero) throw new InvalidOperationException("Unable to query the suspended process PEB; status=0x" + status.ToString("x8"));
        int imageBaseOffset = IntPtr.Size == 8 ? 0x10 : 0x08;
        IntPtr imageBase;
        UIntPtr bytesRead;
        if (!ReadProcessMemory(process, IntPtr.Add(basic.PebBaseAddress, imageBaseOffset), out imageBase, (UIntPtr)IntPtr.Size, out bytesRead) || imageBase == IntPtr.Zero || bytesRead.ToUInt64() != (ulong)IntPtr.Size) {
            throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to read the suspended process image base");
        }
        var mapped = new StringBuilder(32768);
        uint count = GetMappedFileNameW(process, imageBase, mapped, (uint)mapped.Capacity);
        if (count == 0 || count >= mapped.Capacity - 1) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to resolve the suspended process mapped image");
        return mapped.ToString();
    }
    public static string DosPathToDevicePath(string path) {
        string full = System.IO.Path.GetFullPath(path);
        string root = System.IO.Path.GetPathRoot(full);
        if (String.IsNullOrEmpty(root) || root.Length < 2 || root[1] != ':') throw new InvalidOperationException("Executable path has no drive-letter device mapping");
        string drive = root.Substring(0, 2);
        var device = new StringBuilder(32768);
        uint count = QueryDosDeviceW(drive, device, (uint)device.Capacity);
        if (count == 0) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to resolve executable drive device identity");
        return device.ToString() + full.Substring(root.Length - 1);
    }
    public static SafeFileHandle DuplicateReadHandle(SafeFileHandle source) {
        bool added = false;
        source.DangerousAddRef(ref added);
        try {
            IntPtr duplicate;
            IntPtr process = GetCurrentProcess();
            if (!DuplicateHandle(process, source.DangerousGetHandle(), process, out duplicate, 0, false, DUPLICATE_SAME_ACCESS)) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to duplicate locked handle");
            return new SafeFileHandle(duplicate, true);
        }
        finally { if (added) source.DangerousRelease(); }
    }
    public static void CreateDirectoryExclusive(string path) {
        if (!CreateDirectoryW(path, IntPtr.Zero)) throw new Win32Exception(Marshal.GetLastWin32Error(), "Unable to create fresh stage directory");
    }
    public static void AssertUniqueJsonObjectKeys(byte[] raw) {
        string text = new UTF8Encoding(false, true).GetString(raw);
        int index = 0;
        ParseJsonValue(text, ref index);
        SkipJsonWhitespace(text, ref index);
        if (index != text.Length) throw new FormatException("Trailing JSON content is forbidden");
    }
    static void ParseJsonValue(string text, ref int index) {
        SkipJsonWhitespace(text, ref index);
        if (index >= text.Length) throw new FormatException("JSON value is absent");
        char value = text[index];
        if (value == '{') { ParseJsonObject(text, ref index); return; }
        if (value == '[') { ParseJsonArray(text, ref index); return; }
        if (value == '"') { ParseJsonString(text, ref index); return; }
        if (value == 't') { ParseJsonLiteral(text, ref index, "true"); return; }
        if (value == 'f') { ParseJsonLiteral(text, ref index, "false"); return; }
        if (value == 'n') { ParseJsonLiteral(text, ref index, "null"); return; }
        if (value == '-' || (value >= '0' && value <= '9')) { ParseJsonNumber(text, ref index); return; }
        throw new FormatException("Invalid JSON value");
    }
    static void ParseJsonObject(string text, ref int index) {
        index++;
        SkipJsonWhitespace(text, ref index);
        var keys = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (index < text.Length && text[index] == '}') { index++; return; }
        while (true) {
            SkipJsonWhitespace(text, ref index);
            if (index >= text.Length || text[index] != '"') throw new FormatException("JSON object key is invalid");
            string key = ParseJsonString(text, ref index);
            if (!keys.Add(key)) throw new FormatException("Duplicate or case-colliding JSON object key");
            SkipJsonWhitespace(text, ref index);
            if (index >= text.Length || text[index] != ':') throw new FormatException("JSON object colon is absent");
            index++;
            ParseJsonValue(text, ref index);
            SkipJsonWhitespace(text, ref index);
            if (index >= text.Length) throw new FormatException("JSON object is unterminated");
            if (text[index] == '}') { index++; return; }
            if (text[index] != ',') throw new FormatException("JSON object separator is invalid");
            index++;
        }
    }
    static void ParseJsonArray(string text, ref int index) {
        index++;
        SkipJsonWhitespace(text, ref index);
        if (index < text.Length && text[index] == ']') { index++; return; }
        while (true) {
            ParseJsonValue(text, ref index);
            SkipJsonWhitespace(text, ref index);
            if (index >= text.Length) throw new FormatException("JSON array is unterminated");
            if (text[index] == ']') { index++; return; }
            if (text[index] != ',') throw new FormatException("JSON array separator is invalid");
            index++;
        }
    }
    static string ParseJsonString(string text, ref int index) {
        if (index >= text.Length || text[index] != '"') throw new FormatException("JSON string is absent");
        index++;
        var value = new StringBuilder();
        while (index < text.Length) {
            char item = text[index++];
            if (item == '"') return value.ToString();
            if (item < 0x20) throw new FormatException("JSON string contains a control character");
            if (item != '\\') { value.Append(item); continue; }
            if (index >= text.Length) throw new FormatException("JSON escape is incomplete");
            char escaped = text[index++];
            if (escaped == '"' || escaped == '\\' || escaped == '/') { value.Append(escaped); continue; }
            if (escaped == 'b') { value.Append('\b'); continue; }
            if (escaped == 'f') { value.Append('\f'); continue; }
            if (escaped == 'n') { value.Append('\n'); continue; }
            if (escaped == 'r') { value.Append('\r'); continue; }
            if (escaped == 't') { value.Append('\t'); continue; }
            if (escaped != 'u' || index + 4 > text.Length) throw new FormatException("JSON escape is invalid");
            int code = 0;
            for (int offset = 0; offset < 4; offset++) {
                char hex = text[index++];
                code <<= 4;
                if (hex >= '0' && hex <= '9') code += hex - '0';
                else if (hex >= 'a' && hex <= 'f') code += hex - 'a' + 10;
                else if (hex >= 'A' && hex <= 'F') code += hex - 'A' + 10;
                else throw new FormatException("JSON Unicode escape is invalid");
            }
            value.Append((char)code);
        }
        throw new FormatException("JSON string is unterminated");
    }
    static void ParseJsonNumber(string text, ref int index) {
        if (text[index] == '-') { index++; if (index >= text.Length) throw new FormatException("JSON number is incomplete"); }
        if (text[index] == '0') index++;
        else {
            if (text[index] < '1' || text[index] > '9') throw new FormatException("JSON number integer is invalid");
            while (index < text.Length && text[index] >= '0' && text[index] <= '9') index++;
        }
        if (index < text.Length && text[index] == '.') {
            index++;
            int start = index;
            while (index < text.Length && text[index] >= '0' && text[index] <= '9') index++;
            if (index == start) throw new FormatException("JSON number fraction is invalid");
        }
        if (index < text.Length && (text[index] == 'e' || text[index] == 'E')) {
            index++;
            if (index < text.Length && (text[index] == '+' || text[index] == '-')) index++;
            int start = index;
            while (index < text.Length && text[index] >= '0' && text[index] <= '9') index++;
            if (index == start) throw new FormatException("JSON number exponent is invalid");
        }
    }
    static void ParseJsonLiteral(string text, ref int index, string expected) {
        if (index + expected.Length > text.Length || String.CompareOrdinal(text, index, expected, 0, expected.Length) != 0) throw new FormatException("JSON literal is invalid");
        index += expected.Length;
    }
    static void SkipJsonWhitespace(string text, ref int index) {
        while (index < text.Length) {
            char value = text[index];
            if (value != ' ' && value != '\t' && value != '\r' && value != '\n') return;
            index++;
        }
    }
}
'@
}

function Get-OrderedAncestorDirectories([string[]]$Paths) {
    $Set = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($Path in $Paths) {
        $Current = [IO.Directory]::GetParent([IO.Path]::GetFullPath($Path))
        while ($null -ne $Current) {
            $Set.Add($Current.FullName) | Out-Null
            $Current = $Current.Parent
        }
    }
    return @($Set | Sort-Object @{Expression={ $_.Split([IO.Path]::DirectorySeparatorChar).Count }}, @{Expression={ $_ }})
}

function Get-HandleIdentity([Microsoft.Win32.SafeHandles.SafeFileHandle]$Handle) {
    if ($Handle.IsClosed -or $Handle.IsInvalid) { throw 'Locked file handle is not live' }
    $Duplicate = [AvatarFoundationNativeV2]::DuplicateReadHandle($Handle)
    $Stream = [IO.FileStream]::new($Duplicate, [IO.FileAccess]::Read, 1048576, $false)
    try {
        $Stream.Seek(0, [IO.SeekOrigin]::Begin) | Out-Null
        $Bytes = $Stream.Length
        $Hasher = [Security.Cryptography.SHA256]::Create()
        try { $Sha = ([BitConverter]::ToString($Hasher.ComputeHash($Stream))).Replace('-', '').ToLowerInvariant() }
        finally { $Hasher.Dispose() }
    }
    finally { $Stream.Dispose() }
    if ($Handle.IsClosed -or $Handle.IsInvalid) { throw 'Identity hashing closed the locked handle' }
    return [pscustomobject]@{
        bytes = $Bytes
        sha256 = $Sha
        file_id = [AvatarFoundationNativeV2]::FileId128($Handle)
        stable_identity = [AvatarFoundationNativeV2]::StableVolumeFileIdentity($Handle)
    }
}

function Get-HandleBytes([Microsoft.Win32.SafeHandles.SafeFileHandle]$Handle) {
    $Duplicate = [AvatarFoundationNativeV2]::DuplicateReadHandle($Handle)
    $Stream = [IO.FileStream]::new($Duplicate, [IO.FileAccess]::Read, 65536, $false)
    $Memory = [IO.MemoryStream]::new()
    try {
        $Stream.Seek(0, [IO.SeekOrigin]::Begin) | Out-Null
        $Stream.CopyTo($Memory)
        return $Memory.ToArray()
    }
    finally { $Memory.Dispose(); $Stream.Dispose() }
}

function Open-DirectoryIdentityClosure([string[]]$Paths) {
    $Entries = [Collections.Generic.List[object]]::new()
    try {
        foreach ($Directory in Get-OrderedAncestorDirectories $Paths) {
            Assert-NoReparseAncestry $Directory 'locked ancestor directory'
            $Handle = [AvatarFoundationNativeV2]::OpenDirectoryIdentity($Directory)
            try {
                if ([AvatarFoundationNativeV2]::IsReparsePoint($Handle)) { throw "Locked ancestor directory is a reparse point: $Directory" }
                $StableIdentity = [AvatarFoundationNativeV2]::StableVolumeFileIdentity($Handle)
                $Entries.Add([pscustomobject]@{ Path = [IO.Path]::GetFullPath($Directory); Handle = $Handle; StableIdentity = $StableIdentity })
                $Handle = $null
            }
            finally { if ($null -ne $Handle) { $Handle.Dispose() } }
        }
        Assert-DirectoryIdentityClosure $Entries 'new directory identity closure'
        return $Entries
    }
    catch { foreach ($Entry in $Entries) { $Entry.Handle.Dispose() }; throw }
}

function Assert-DirectoryIdentityClosure([object]$Closure, [string]$Label) {
    foreach ($Entry in @($Closure)) {
        if ($Entry.Handle.IsClosed -or $Entry.Handle.IsInvalid) { throw "$Label contains a closed directory handle" }
        if ([AvatarFoundationNativeV2]::IsReparsePoint($Entry.Handle)) { throw "$Label held directory became a reparse point" }
        if ([AvatarFoundationNativeV2]::StableVolumeFileIdentity($Entry.Handle) -cne [string]$Entry.StableIdentity) { throw "$Label held directory identity changed" }
        Assert-NoReparseAncestry ([string]$Entry.Path) $Label
        $AtPath = [AvatarFoundationNativeV2]::OpenDirectoryIdentity([string]$Entry.Path)
        try {
            if ([AvatarFoundationNativeV2]::IsReparsePoint($AtPath)) { throw "$Label path names a reparse point" }
            if ([AvatarFoundationNativeV2]::StableVolumeFileIdentity($AtPath) -cne [string]$Entry.StableIdentity) { throw "$Label path no longer names the locked directory identity" }
        }
        finally { $AtPath.Dispose() }
    }
}

function Open-And-RevalidateLockedRows([object[]]$Rows, [string]$Label) {
    $Paths = [Collections.Generic.List[string]]::new()
    $Seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($Row in $Rows) {
        $Path = if ([IO.Path]::IsPathRooted([string]$Row.path)) { [IO.Path]::GetFullPath([string]$Row.path) } else { Get-ProjectPath ([string]$Row.path) "$Label file" }
        if (-not $Seen.Add($Path)) { throw "$Label contains a duplicate path" }
        $Paths.Add($Path)
    }
    $DirectoryClosure = Open-DirectoryIdentityClosure @($Paths)
    $FileHandles = [Collections.Generic.List[IDisposable]]::new()
    try {
        for ($Index = 0; $Index -lt $Rows.Count; $Index++) {
            $Path = $Paths[$Index]
            $Row = $Rows[$Index]
            Assert-NoReparseAncestry $Path "$Label file"
            $Handle = [AvatarFoundationNativeV2]::OpenFileDenyWriteDelete($Path)
            $FileHandles.Add($Handle)
            $Actual = Get-HandleIdentity $Handle
            if ($Actual.bytes -ne [long]$Row.bytes -or $Actual.sha256 -cne [string]$Row.sha256) { throw "$Label byte/hash differs: $Path" }
            if (-not [string]::IsNullOrEmpty([string]$Row.file_id) -and $Actual.file_id -cne [string]$Row.file_id) { throw "$Label file identity differs: $Path" }
        }
        for ($Index = 0; $Index -lt $Rows.Count; $Index++) {
            $Actual = Get-HandleIdentity $FileHandles[$Index]
            if ($Actual.bytes -ne [long]$Rows[$Index].bytes -or $Actual.sha256 -cne [string]$Rows[$Index].sha256) { throw "$Label changed after complete lock acquisition" }
        }
        return [pscustomobject]@{ Rows = $Rows; Paths = @($Paths); DirectoryClosure = $DirectoryClosure; FileHandles = $FileHandles }
    }
    catch { foreach ($Handle in $FileHandles) { $Handle.Dispose() }; foreach ($Entry in $DirectoryClosure) { $Entry.Handle.Dispose() }; throw }
}

function Assert-LockedRows([object]$Locked, [string]$Label) {
    Assert-DirectoryIdentityClosure $Locked.DirectoryClosure "$Label directory closure"
    for ($Index = 0; $Index -lt $Locked.Rows.Count; $Index++) {
        $Actual = Get-HandleIdentity $Locked.FileHandles[$Index]
        $Row = $Locked.Rows[$Index]
        if ($Actual.bytes -ne [long]$Row.bytes -or $Actual.sha256 -cne [string]$Row.sha256) { throw "$Label changed while locked" }
        if (-not [string]::IsNullOrEmpty([string]$Row.file_id) -and $Actual.file_id -cne [string]$Row.file_id) { throw "$Label file identity changed while locked" }
    }
}

function Dispose-LockedRows([object]$Locked) {
    if ($null -eq $Locked) { return }
    foreach ($Handle in $Locked.FileHandles) { $Handle.Dispose() }
    foreach ($Entry in $Locked.DirectoryClosure) { $Entry.Handle.Dispose() }
}

function Commit-BytesExclusive([string]$PreparedPath, [string]$FinalPath, [byte[]]$Bytes) {
    if (Test-Path -LiteralPath $PreparedPath -or Test-Path -LiteralPath $FinalPath) { throw 'Exclusive claim target already exists' }
    $Stream = [IO.File]::Open($PreparedPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $Stream.Write($Bytes, 0, $Bytes.Length); $Stream.Flush($true) }
    finally { $Stream.Dispose() }
    if (-not [AvatarFoundationNativeV2]::MoveFileExW($PreparedPath, $FinalPath, [AvatarFoundationNativeV2]::MOVEFILE_WRITE_THROUGH)) {
        $ErrorCode = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Remove-Item -LiteralPath $PreparedPath -Force -ErrorAction SilentlyContinue
        throw "Atomic exclusive claim failed; winerror=$ErrorCode"
    }
}

function Quote-WindowsArgument([string]$Value) {
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + (($Value -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
}

function New-TrustedEnvironmentBlock([string]$BlenderRoot, [string]$PythonBin) {
    if (-not [Environment]::SystemDirectory.Equals($CanonicalSystemDirectory, [StringComparison]::OrdinalIgnoreCase)) { throw 'Windows System32 API identity differs' }
    foreach ($Name in @('SystemRoot','WINDIR')) {
        $Value = [Environment]::GetEnvironmentVariable($Name)
        if ([string]::IsNullOrWhiteSpace($Value) -or -not [IO.Path]::GetFullPath($Value).TrimEnd('\').Equals($CanonicalWindowsRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "Inherited $Name differs from the sealed Windows root" }
    }
    foreach ($Variable in Get-ChildItem Env:) { if ($Variable.Name -like 'CUDA_PATH*' -or $Variable.Name -in @('CUDA_HOME','CUDA_ROOT')) { throw "Inherited CUDA path is forbidden: $($Variable.Name)" } }
    $Variables = [ordered]@{
        'ALLUSERSPROFILE' = 'C:\ProgramData'
        'HOMEDRIVE' = 'C:'
        'HOMEPATH' = '\Users\robmc'
        'LOCALAPPDATA' = 'C:\Users\robmc\AppData\Local'
        'NoDefaultCurrentDirectoryInExePath' = '1'
        'PATH' = "$BlenderRoot;$PythonBin;$CanonicalSystemDirectory"
        'PROGRAMDATA' = 'C:\ProgramData'
        'PYTHONDONTWRITEBYTECODE' = '1'
        'PYTHONNOUSERSITE' = '1'
        'PYTHONSAFEPATH' = '1'
        'SYSTEMDRIVE' = 'C:'
        'SYSTEMROOT' = $CanonicalWindowsRoot
        'TEMP' = 'C:\Users\robmc\AppData\Local\Temp'
        'TMP' = 'C:\Users\robmc\AppData\Local\Temp'
        'USERPROFILE' = 'C:\Users\robmc'
        'WINDIR' = $CanonicalWindowsRoot
    }
    $Text = (($Variables.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join "`0") + "`0`0"
    return [Text.Encoding]::Unicode.GetBytes($Text)
}

function Start-SuspendedJobBoundBlender([string]$Blender, [string[]]$Arguments, [byte[]]$Environment, [object]$Locked, [object]$RuntimeIdentity, [int]$TimeoutSeconds) {
    Assert-DirectoryIdentityClosure $Locked.DirectoryClosure 'runtime namespace immediately before suspended CreateProcess'
    $BlenderIndex = -1
    for ($Index = 0; $Index -lt $Locked.Paths.Count; $Index++) {
        if ([IO.Path]::GetFullPath([string]$Locked.Paths[$Index]).Equals([IO.Path]::GetFullPath($Blender), [StringComparison]::OrdinalIgnoreCase)) {
            if ($BlenderIndex -ne -1) { throw 'Locked Blender executable path is duplicated' }
            $BlenderIndex = $Index
        }
    }
    if ($BlenderIndex -lt 0) { throw 'Locked Blender executable is absent from the file-identity closure' }
    $LockedBlenderIdentity = Get-HandleIdentity $Locked.FileHandles[$BlenderIndex]
    $Job = [AvatarFoundationNativeV2]::CreateJobObjectW([IntPtr]::Zero, $null)
    if ($Job -eq [IntPtr]::Zero) { throw 'CreateJobObjectW failed' }
    $ProcessInfo = [AvatarFoundationNativeV2+PROCESS_INFORMATION]::new()
    $EnvironmentPointer = [Runtime.InteropServices.Marshal]::AllocHGlobal($Environment.Length)
    [Runtime.InteropServices.Marshal]::Copy($Environment, 0, $EnvironmentPointer, $Environment.Length)
    $LimitsPointer = [IntPtr]::Zero
    try {
        $Limits = [AvatarFoundationNativeV2+JOBOBJECT_EXTENDED_LIMIT_INFORMATION]::new()
        $Limits.BasicLimitInformation.LimitFlags = [AvatarFoundationNativeV2]::JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        $Size = [Runtime.InteropServices.Marshal]::SizeOf($Limits)
        $LimitsPointer = [Runtime.InteropServices.Marshal]::AllocHGlobal($Size)
        [Runtime.InteropServices.Marshal]::StructureToPtr($Limits, $LimitsPointer, $false)
        if (-not [AvatarFoundationNativeV2]::SetInformationJobObject($Job, [AvatarFoundationNativeV2]::JobObjectExtendedLimitInformation, $LimitsPointer, [uint32]$Size)) { throw 'SetInformationJobObject failed' }
        $Startup = [AvatarFoundationNativeV2+STARTUPINFO]::new()
        $Startup.cb = [Runtime.InteropServices.Marshal]::SizeOf($Startup)
        $Command = [Text.StringBuilder]::new(((Quote-WindowsArgument $Blender) + ' ' + (($Arguments | ForEach-Object { Quote-WindowsArgument $_ }) -join ' ')))
        $Flags = [AvatarFoundationNativeV2]::CREATE_SUSPENDED -bor [AvatarFoundationNativeV2]::CREATE_UNICODE_ENVIRONMENT
        if (-not [AvatarFoundationNativeV2]::CreateProcessW($Blender, $Command, [IntPtr]::Zero, [IntPtr]::Zero, $false, $Flags, $EnvironmentPointer, $CanonicalSystemDirectory, [ref]$Startup, [ref]$ProcessInfo)) { throw 'CreateProcessW CREATE_SUSPENDED failed' }
        try {
            if (-not [AvatarFoundationNativeV2]::AssignProcessToJobObject($Job, $ProcessInfo.hProcess)) { throw 'AssignProcessToJobObject failed before resume' }
            # Query the file mapping backing the suspended process image, not
            # merely its configured image-name text. Convert the already locked
            # executable path to the same NT device namespace and require an
            # exact match before the initial thread can run.
            $MappedImageDevicePath = [AvatarFoundationNativeV2]::ProcessMappedImageDevicePath($ProcessInfo.hProcess)
            $LockedBlenderDevicePath = [AvatarFoundationNativeV2]::DosPathToDevicePath($Blender)
            if (-not $MappedImageDevicePath.Equals($LockedBlenderDevicePath, [StringComparison]::OrdinalIgnoreCase)) { throw 'Suspended process mapped-image device identity differs from the locked Blender executable' }
            Assert-DirectoryIdentityClosure $Locked.DirectoryClosure 'runtime namespace after suspended CreateProcess'
            Assert-NoReparseAncestry $Blender 'suspended process image locked path'
            $ProcessImageHandle = [AvatarFoundationNativeV2]::OpenFileDenyWriteDelete($Blender)
            try {
                if ([AvatarFoundationNativeV2]::IsReparsePoint($ProcessImageHandle)) { throw 'Suspended process image path is a reparse point' }
                $ProcessImageIdentity = Get-HandleIdentity $ProcessImageHandle
                if ($ProcessImageIdentity.stable_identity -cne $LockedBlenderIdentity.stable_identity -or $ProcessImageIdentity.bytes -ne $LockedBlenderIdentity.bytes -or $ProcessImageIdentity.sha256 -cne $LockedBlenderIdentity.sha256) {
                    throw 'Suspended process-backed image identity differs from the locked Blender executable identity'
                }
            }
            finally { $ProcessImageHandle.Dispose() }
            Assert-LockedRows $Locked 'full runtime/static/source/authority/claim closure while suspended'
            foreach ($Component in @($RuntimeIdentity.components)) {
                $Match = @($Locked.Rows | Where-Object { [string]$_.path -ceq [string]$Component.path })
                if ($Match.Count -ne 1) { throw 'Runtime component is absent from the suspended lock closure' }
            }
            if ([AvatarFoundationNativeV2]::ResumeThread($ProcessInfo.hThread) -ne 1) { throw 'ResumeThread suspend count differs' }
            $Wait = [AvatarFoundationNativeV2]::WaitForSingleObject($ProcessInfo.hProcess, [uint32]($TimeoutSeconds * 1000))
            if ($Wait -eq [AvatarFoundationNativeV2]::WAIT_TIMEOUT) { [AvatarFoundationNativeV2]::TerminateJobObject($Job, 124) | Out-Null; throw 'Blender worker timed out' }
            if ($Wait -ne [AvatarFoundationNativeV2]::WAIT_OBJECT_0) { throw 'Blender process wait failed' }
            [uint32]$ExitCode = 0
            if (-not [AvatarFoundationNativeV2]::GetExitCodeProcess($ProcessInfo.hProcess, [ref]$ExitCode)) { throw 'GetExitCodeProcess failed' }
            return $ExitCode
        }
        catch {
            if ($ProcessInfo.hProcess -ne [IntPtr]::Zero) {
                [AvatarFoundationNativeV2]::TerminateProcess($ProcessInfo.hProcess, 125) | Out-Null
                [AvatarFoundationNativeV2]::TerminateJobObject($Job, 125) | Out-Null
                [AvatarFoundationNativeV2]::WaitForSingleObject($ProcessInfo.hProcess, 5000) | Out-Null
            }
            throw
        }
        finally {
            if ($ProcessInfo.hThread -ne [IntPtr]::Zero) { [AvatarFoundationNativeV2]::CloseHandle($ProcessInfo.hThread) | Out-Null }
            if ($ProcessInfo.hProcess -ne [IntPtr]::Zero) { [AvatarFoundationNativeV2]::CloseHandle($ProcessInfo.hProcess) | Out-Null }
        }
    }
    finally {
        if ($LimitsPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::FreeHGlobal($LimitsPointer) }
        [Runtime.InteropServices.Marshal]::FreeHGlobal($EnvironmentPointer)
        [AvatarFoundationNativeV2]::CloseHandle($Job) | Out-Null
    }
}

function Open-And-ValidateOutputClosure([string]$Stage, [object]$Config, [object]$Policy, [object]$Claim, [string]$ClaimSha256, [string]$PolicySha256, [string]$AuthoritySha256, [string]$ConsumptionSha256, [string]$Invocation) {
    $ExpectedNames = @($Config.output_transaction.exact_final_files | Sort-Object -CaseSensitive)
    $Names = @(Get-ChildItem -LiteralPath $Stage -Force | ForEach-Object Name | Sort-Object -CaseSensitive)
    if (($Names -join "`n") -cne ($ExpectedNames -join "`n") -or $Names.Count -ne 4) { throw 'Stage exact four-file closure differs' }
    $Handles = [ordered]@{}
    $Identities = [ordered]@{}
    try {
        foreach ($Name in $ExpectedNames) {
            $Path = Join-Path $Stage $Name
            Assert-NoReparseAncestry $Path 'staged output'
            $Handle = [AvatarFoundationNativeV2]::OpenOutputFileDenyWriteAllowRename($Path)
            $Handles[$Name] = $Handle
            $Identities[$Name] = Get-HandleIdentity $Handle
        }
        $OutputFileIds = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($Identity in $Identities.Values) { if (-not $OutputFileIds.Add([string]$Identity.stable_identity)) { throw 'Stage output volume/file identities are not distinct' } }
        if ($OutputFileIds.Count -ne 4) { throw 'Stage output file identity closure differs' }
        $NamesAfterLock = @(Get-ChildItem -LiteralPath $Stage -Force | ForEach-Object Name | Sort-Object -CaseSensitive)
        if (($NamesAfterLock -join "`n") -cne ($ExpectedNames -join "`n")) { throw 'Stage closure changed during output lock acquisition' }
        foreach ($Name in @('output.manifest.json','success.receipt.json')) { if ($Identities[$Name].bytes -le 0 -or $Identities[$Name].bytes -gt $MaxJsonBytes) { throw "Staged $Name JSON byte boundary differs" } }
        $ManifestRaw = Get-HandleBytes $Handles['output.manifest.json']
        $ReceiptRaw = Get-HandleBytes $Handles['success.receipt.json']
        if ((Get-Sha256Bytes $ManifestRaw) -cne $Identities['output.manifest.json'].sha256 -or (Get-Sha256Bytes $ReceiptRaw) -cne $Identities['success.receipt.json'].sha256) { throw 'Locked JSON output bytes differ' }
        [AvatarFoundationNativeV2]::AssertUniqueJsonObjectKeys($ManifestRaw)
        [AvatarFoundationNativeV2]::AssertUniqueJsonObjectKeys($ReceiptRaw)
        $Manifest = ([Text.UTF8Encoding]::new($false, $true).GetString($ManifestRaw)) | ConvertFrom-Json
        $Receipt = ([Text.UTF8Encoding]::new($false, $true).GetString($ReceiptRaw)) | ConvertFrom-Json
        Assert-ExactKeys $Manifest @($Config.output_transaction.manifest_exact_keys) 'output manifest'
        Assert-ExactKeys $Receipt @($Config.output_transaction.success_receipt_exact_keys) 'success receipt'
        Assert-JsonInteger $Manifest.schema_version 'output manifest schema_version'
        foreach ($Name in @('record_type','status','invocation_id','worker_sha256','worker_config_sha256','worker_claim_sha256','success_receipt_file')) { Assert-JsonString $Manifest.$Name "output manifest $Name" }
        foreach ($Name in @('network_used','activation_performed','publication_performed')) { Assert-JsonBoolean $Manifest.$Name "output manifest $Name" }
        Assert-JsonArray $Manifest.artifacts 'output manifest artifacts'
        if ($Manifest.schema_version -ne 1 -or $Manifest.record_type -ne 'avatar_builder_separate_foundation_output_manifest' -or $Manifest.status -ne 'TWO_DISTINCT_FOUNDATION_CANDIDATES_AUTHORED_ACCEPTANCE_PENDING' -or $Manifest.invocation_id -cne $Invocation -or $Manifest.worker_sha256 -cne $Policy.worker_sha256 -or $Manifest.worker_config_sha256 -cne $Policy.worker_config_sha256 -or $Manifest.worker_claim_sha256 -cne $ClaimSha256 -or $Manifest.success_receipt_file -cne 'success.receipt.json' -or $Manifest.network_used -ne $false -or $Manifest.activation_performed -ne $false -or $Manifest.publication_performed -ne $false) { throw 'Output manifest provenance or truth differs' }
        $Artifacts = @($Manifest.artifacts)
        if ($Artifacts.Count -ne 2) { throw 'Output manifest artifact count differs' }
        $ArtifactHashes = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        $SubjectIds = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($Artifact in $Artifacts) {
            Assert-ExactKeys $Artifact @($Config.output_transaction.manifest_artifact_exact_keys) 'manifest artifact'
            foreach ($Name in @('subject_id','artifact_file','artifact_sha256','source_project_path','source_sha256')) { Assert-JsonString $Artifact.$Name "manifest artifact $Name" }
            foreach ($Name in @('artifact_bytes','source_bytes')) { Assert-JsonInteger $Artifact.$Name "manifest artifact $Name" }
            foreach ($Name in @('source_modified','body_accepted')) { Assert-JsonBoolean $Artifact.$Name "manifest artifact $Name" }
            $Subject = @($Config.subjects | Where-Object { [string]$_.subject_id -ceq [string]$Artifact.subject_id })
            if ($Subject.Count -ne 1 -or -not $SubjectIds.Add([string]$Artifact.subject_id)) { throw 'Manifest subject binding differs' }
            $ExpectedFile = [string]$Subject[0].output_file
            if ($Artifact.artifact_file -cne $ExpectedFile -or -not $Handles.Contains($ExpectedFile)) { throw 'Manifest artifact file differs' }
            $Identity = $Identities[$ExpectedFile]
            if ($Artifact.artifact_bytes -ne $Identity.bytes -or $Artifact.artifact_sha256 -cne $Identity.sha256 -or -not $ArtifactHashes.Add([string]$Artifact.artifact_sha256)) { throw 'Manifest artifact byte/hash identity differs' }
            if ($Artifact.source_project_path -cne $Subject[0].source.path -or $Artifact.source_bytes -ne $Subject[0].source.bytes -or $Artifact.source_sha256 -cne $Subject[0].source.sha256 -or $Artifact.source_modified -ne $false -or $Artifact.body_accepted -ne $false) { throw 'Manifest source or acceptance truth differs' }
            Assert-ExactKeys $Artifact.import_evidence @('actions','armature_objects','mesh_objects','polygons','vertices') 'manifest import evidence'
            foreach ($Name in @('actions','armature_objects','mesh_objects','polygons','vertices')) { Assert-JsonInteger $Artifact.import_evidence.$Name "manifest import evidence $Name"; if ([long]$Artifact.import_evidence.$Name -lt [long]$Subject[0].minimum_import_evidence.$Name) { throw 'Manifest import evidence is below the sealed minimum' } }
        }
        if ($ArtifactHashes.Count -ne 2 -or $SubjectIds.Count -ne 2) { throw 'Two distinct subject artifacts are not proven' }
        Assert-JsonInteger $Receipt.schema_version 'success receipt schema_version'
        Assert-JsonInteger $Receipt.artifact_count 'success receipt artifact_count'
        foreach ($Name in @('record_type','status','invocation_id','authority_sha256','consumption_sha256','launcher_policy_sha256','worker_sha256','worker_config_sha256','worker_claim_sha256','output_contract_sha256','output_manifest_sha256')) { Assert-JsonString $Receipt.$Name "success receipt $Name" }
        Assert-JsonArray $Receipt.subject_ids 'success receipt subject_ids'
        foreach ($Name in @('body_authoring_performed','source_files_modified','kira_body_accepted','synthetic_robert_body_accepted','internal_anatomy_accepted','skin_soft_tissue_accepted','movement_accepted','hair_physics_accepted','runtime_activation_allowed','network_used','publication_performed')) { Assert-JsonBoolean $Receipt.$Name "success receipt $Name" }
        if ($Receipt.schema_version -ne 1 -or $Receipt.record_type -ne 'avatar_builder_separate_foundation_success_receipt' -or $Receipt.status -ne 'AUTHORING_OUTPUT_CREATED_BODY_ACCEPTANCE_PENDING' -or $Receipt.invocation_id -cne $Invocation -or $Receipt.authority_sha256 -cne $AuthoritySha256 -or $Receipt.consumption_sha256 -cne $ConsumptionSha256 -or $Receipt.launcher_policy_sha256 -cne $PolicySha256 -or $Receipt.worker_sha256 -cne $Policy.worker_sha256 -or $Receipt.worker_config_sha256 -cne $Policy.worker_config_sha256 -or $Receipt.worker_claim_sha256 -cne $ClaimSha256 -or $Receipt.output_contract_sha256 -cne $OutputContractSha256 -or $Receipt.output_manifest_sha256 -cne (Get-Sha256Bytes $ManifestRaw) -or $Receipt.artifact_count -ne 2 -or (@($Receipt.subject_ids) -join "`n") -cne "kira`nsynthetic_robert" -or $Receipt.body_authoring_performed -ne $true -or $Receipt.source_files_modified -ne $false) { throw 'Success receipt provenance differs' }
        foreach ($Name in @('kira_body_accepted','synthetic_robert_body_accepted','internal_anatomy_accepted','skin_soft_tissue_accepted','movement_accepted','hair_physics_accepted','runtime_activation_allowed','network_used','publication_performed')) { if ($Receipt.$Name -ne $false) { throw "Success receipt acceptance escalation: $Name" } }
        return [pscustomobject]@{ Handles = $Handles; Identities = $Identities; ExpectedNames = $ExpectedNames }
    }
    catch { foreach ($Handle in $Handles.Values) { $Handle.Dispose() }; throw }
}

function Assert-CommittedOutputClosure([object]$OutputLocked, [string]$Final) {
    $Names = @(Get-ChildItem -LiteralPath $Final -Force | ForEach-Object Name | Sort-Object -CaseSensitive)
    if (($Names -join "`n") -cne ($OutputLocked.ExpectedNames -join "`n")) { throw 'Committed final-directory closure differs' }
    foreach ($Name in $OutputLocked.ExpectedNames) {
        $Held = Get-HandleIdentity $OutputLocked.Handles[$Name]
        $Before = $OutputLocked.Identities[$Name]
        if ($Held.bytes -ne $Before.bytes -or $Held.sha256 -cne $Before.sha256 -or $Held.stable_identity -cne $Before.stable_identity) { throw 'Held output identity changed across final commit' }
        $PathHandle = [AvatarFoundationNativeV2]::OpenFileDenyWriteDelete((Join-Path $Final $Name))
        try {
            $AtFinal = Get-HandleIdentity $PathHandle
            if ($AtFinal.bytes -ne $Before.bytes -or $AtFinal.sha256 -cne $Before.sha256 -or $AtFinal.stable_identity -cne $Before.stable_identity) { throw 'Final path does not name the locked output volume/file identity' }
        }
        finally { $PathHandle.Dispose() }
    }
}

function Get-PreservedInvocationResidueState([string]$Path, [string]$StableParent, [string]$ExpectedName, [object]$IdentityHandle, [string]$ExpectedStableIdentity, [object]$OriginalNamespaceClosure) {
    $Absolute = [IO.Path]::GetFullPath($Path)
    if ([IO.Directory]::GetParent($Absolute).FullName -cne [IO.Path]::GetFullPath($StableParent) -or [IO.Path]::GetFileName($Absolute) -cne $ExpectedName) { throw 'Invocation residue text boundary differs' }
    if (-not (Test-Path -LiteralPath $Absolute)) { return [pscustomobject]@{ path = $Absolute; present = $false; identity_verified = $false; preserved = $true } }
    Assert-DirectoryIdentityClosure $OriginalNamespaceClosure 'failure residue original parent/ancestor identity closure'
    if ($null -eq $IdentityHandle -or $IdentityHandle.IsClosed -or $IdentityHandle.IsInvalid) { throw 'Invocation residue exists without its original live identity handle' }
    Assert-NoReparseAncestry $Absolute 'invocation residue'
    if ([AvatarFoundationNativeV2]::IsReparsePoint($IdentityHandle)) { throw 'Original invocation residue handle is a reparse point' }
    if ([AvatarFoundationNativeV2]::StableVolumeFileIdentity($IdentityHandle) -cne $ExpectedStableIdentity) { throw 'Original invocation residue handle identity differs' }
    $AtPath = [AvatarFoundationNativeV2]::OpenDirectoryIdentity($Absolute)
    try {
        if ([AvatarFoundationNativeV2]::IsReparsePoint($AtPath)) { throw 'Invocation residue path is a reparse point' }
        if ([AvatarFoundationNativeV2]::StableVolumeFileIdentity($AtPath) -cne $ExpectedStableIdentity) { throw 'Invocation residue path does not name the original directory identity' }
    }
    finally { $AtPath.Dispose() }
    # Deliberately preserve residue. V3 never recursively deletes a directory
    # during failure handling; a later separately reviewed recovery tool may do so.
    return [pscustomobject]@{ path = $Absolute; present = $true; identity_verified = $true; preserved = $true }
}

function Invoke-SeparateFoundationTrustedLauncher {
    if (-not $Execute) { throw 'Execution was not requested; static successor grants no authority' }
    Initialize-NativeBoundary

    $PolicyPath = Get-ProjectPath $PolicyRel 'launcher policy'
    $WorkerPolicyCompatPath = Get-ProjectPath $WorkerPolicyCompatRel 'worker policy compatibility mirror'
    $RuntimeIdentityPath = Get-ProjectPath $RuntimeIdentityRel 'runtime identity'
    $WorkerPath = Get-ProjectPath $WorkerRel 'worker'
    $WorkerConfigPath = Get-ProjectPath $WorkerConfigRel 'worker configuration'
    $LauncherPath = Get-ProjectPath $LauncherRel 'launcher source'
    $AuditPath = Get-ProjectPath $IndependentAuditRel 'independent launcher audit'
    $WorkerAuditCompatPath = Get-ProjectPath $WorkerAuditCompatRel 'worker audit compatibility mirror'
    $AuthorityPath = Get-ProjectPath $AuthorityRel 'positive one-use authority'

    $PolicyBinding = Read-JsonBinding $PolicyPath 'launcher policy'
    Assert-ExactKeys $PolicyBinding.Document @('output_contract_sha256','record_type','runtime_identity_sha256','schema_version','sealed_launcher_closure_sha256','status','worker_config_sha256','worker_sha256') 'launcher policy'
    $Policy = $PolicyBinding.Document
    Assert-JsonInteger $Policy.schema_version 'launcher policy schema_version'
    foreach ($Name in @('record_type','status','sealed_launcher_closure_sha256','runtime_identity_sha256','worker_sha256','worker_config_sha256','output_contract_sha256')) { Assert-JsonString $Policy.$Name "launcher policy $Name" }
    if ($Policy.schema_version -ne 2 -or $Policy.record_type -ne 'avatar_builder_blender_separate_foundation_trusted_launcher_contract' -or $Policy.status -ne 'FROZEN_SUCCESSOR_INDEPENDENT_AUDIT_PASSED_AUTHORITY_SEPARATE' -or $Policy.output_contract_sha256 -cne $OutputContractSha256) { throw 'Launcher policy identity differs' }
    $WorkerPolicyCompatBinding = Read-JsonBinding $WorkerPolicyCompatPath 'worker policy compatibility mirror'
    if ($WorkerPolicyCompatBinding.Sha256 -cne $PolicyBinding.Sha256 -or $WorkerPolicyCompatBinding.Bytes -ne $PolicyBinding.Bytes) { throw 'Worker policy compatibility mirror differs from the V3 policy' }
    $LauncherRaw = [IO.File]::ReadAllBytes($LauncherPath)
    if ((Get-Sha256Bytes $LauncherRaw) -cne $Policy.sealed_launcher_closure_sha256) { throw 'Launcher source differs from the sealed launcher closure' }
    $RuntimeBinding = Read-JsonBinding $RuntimeIdentityPath 'runtime identity'
    $WorkerRaw = [IO.File]::ReadAllBytes($WorkerPath)
    $ConfigBinding = Read-JsonBinding $WorkerConfigPath 'worker configuration'
    if ($RuntimeBinding.Sha256 -cne $Policy.runtime_identity_sha256 -or (Get-Sha256Bytes $WorkerRaw) -cne $Policy.worker_sha256 -or $ConfigBinding.Sha256 -cne $Policy.worker_config_sha256) { throw 'Launcher worker/config/runtime binding differs' }
    $RuntimeIdentity = $RuntimeBinding.Document
    $Config = $ConfigBinding.Document
    if ($RuntimeIdentity.status -ne 'STATIC_RUNTIME_IDENTITY_CANDIDATE_EXECUTION_BLOCKED' -or $Config.status -ne 'STATIC_NON_INERT_OPERATION_DEFINED_EXECUTION_AUTHORITY_ABSENT') { throw 'Bound runtime or worker configuration status differs' }
    if ($Config.worker.sha256 -cne $Policy.worker_sha256 -or $Config.worker.path -cne $WorkerRel -or $Config.blender_runtime.sha256 -cne $Policy.runtime_identity_sha256 -or $Config.output_transaction.exact_final_file_count -ne 4 -or (@($Config.output_transaction.exact_final_files) -join "`n") -cne "kira_foundation_candidate.blend`noutput.manifest.json`nsuccess.receipt.json`nsynthetic_robert_foundation_candidate.blend") { throw 'Worker configuration closure differs' }

    # The independent audit is read before authority or claim mutation and must
    # bind this exact frozen source. The launcher cannot create that audit.
    $AuditBinding = Read-JsonBinding $AuditPath 'different independent launcher audit'
    Assert-ExactKeys $AuditBinding.Document @('launcher_policy_sha256','output_contract_sha256','record_type','runtime_identity_sha256','schema_version','sealed_launcher_closure_sha256','status','worker_config_sha256','worker_sha256') 'independent launcher audit'
    $Audit = $AuditBinding.Document
    Assert-JsonInteger $Audit.schema_version 'independent launcher audit schema_version'
    foreach ($Name in @('record_type','status','launcher_policy_sha256','sealed_launcher_closure_sha256','runtime_identity_sha256','worker_sha256','worker_config_sha256','output_contract_sha256')) { Assert-JsonString $Audit.$Name "independent launcher audit $Name" }
    if ($Audit.schema_version -ne 1 -or $Audit.record_type -ne 'avatar_builder_blender_separate_foundation_launcher_independent_audit' -or $Audit.status -ne 'PASS_FROZEN_SUCCESSOR_EXECUTION_AUTHORITY_SEPARATE' -or $Audit.launcher_policy_sha256 -cne $PolicyBinding.Sha256 -or $Audit.sealed_launcher_closure_sha256 -cne $Policy.sealed_launcher_closure_sha256 -or $Audit.runtime_identity_sha256 -cne $Policy.runtime_identity_sha256 -or $Audit.worker_sha256 -cne $Policy.worker_sha256 -or $Audit.worker_config_sha256 -cne $Policy.worker_config_sha256 -or $Audit.output_contract_sha256 -cne $OutputContractSha256) { throw 'Independent launcher audit binding differs' }
    $WorkerAuditCompatBinding = Read-JsonBinding $WorkerAuditCompatPath 'worker audit compatibility mirror'
    if ($WorkerAuditCompatBinding.Sha256 -cne $AuditBinding.Sha256 -or $WorkerAuditCompatBinding.Bytes -ne $AuditBinding.Bytes) { throw 'Worker audit compatibility mirror differs from the V3 independent audit' }

    $AuthorityBinding = Read-JsonBinding $AuthorityPath 'positive one-use authority'
    Assert-ExactKeys $AuthorityBinding.Document @('exclusive_filesystem_control_attested','execution_authorized','expires_utc','invocation_id','issued_utc','issuer_identity','launcher_independent_audit_sha256','launcher_policy_sha256','output_contract_sha256','proposal_only','record_type','schema_version','trusted_channel_attested','worker_config_sha256','worker_sha256') 'positive one-use authority'
    $Authority = $AuthorityBinding.Document
    Assert-JsonInteger $Authority.schema_version 'positive one-use authority schema_version'
    foreach ($Name in @('record_type','invocation_id','issued_utc','expires_utc','issuer_identity','launcher_policy_sha256','launcher_independent_audit_sha256','worker_sha256','worker_config_sha256','output_contract_sha256')) { Assert-JsonString $Authority.$Name "positive one-use authority $Name" }
    foreach ($Name in @('execution_authorized','proposal_only','trusted_channel_attested','exclusive_filesystem_control_attested')) { Assert-JsonBoolean $Authority.$Name "positive one-use authority $Name" }
    if ($Authority.schema_version -ne 2 -or $Authority.record_type -ne 'AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_ONE_RUN_AUTHORIZATION' -or $Authority.execution_authorized -ne $true -or $Authority.proposal_only -ne $false -or $Authority.trusted_channel_attested -ne $true -or $Authority.exclusive_filesystem_control_attested -ne $true -or [string]::IsNullOrWhiteSpace([string]$Authority.issuer_identity) -or $Authority.launcher_policy_sha256 -cne $PolicyBinding.Sha256 -or $Authority.launcher_independent_audit_sha256 -cne $AuditBinding.Sha256 -or $Authority.worker_sha256 -cne $Policy.worker_sha256 -or $Authority.worker_config_sha256 -cne $Policy.worker_config_sha256 -or $Authority.output_contract_sha256 -cne $OutputContractSha256) { throw 'Positive one-use authority state differs' }
    if (-not ([string]$Authority.issued_utc).EndsWith('Z', [StringComparison]::Ordinal) -or -not ([string]$Authority.expires_utc).EndsWith('Z', [StringComparison]::Ordinal)) { throw 'Authority timestamps must be explicit UTC values' }
    [DateTimeOffset]$IssuedUtc = [DateTimeOffset]::MinValue
    [DateTimeOffset]$ExpiresUtc = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse([string]$Authority.issued_utc, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$IssuedUtc) -or -not [DateTimeOffset]::TryParse([string]$Authority.expires_utc, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$ExpiresUtc) -or $IssuedUtc.Offset -ne [TimeSpan]::Zero -or $ExpiresUtc.Offset -ne [TimeSpan]::Zero) { throw 'Authority UTC parsing differs' }
    if ($IssuedUtc -ge $ExpiresUtc -or ($ExpiresUtc - $IssuedUtc).TotalSeconds -gt 900) { throw 'Authority lifetime exceeds the sealed 900-second boundary' }
    $NowUtc = [DateTimeOffset]::UtcNow
    if ($NowUtc -lt $IssuedUtc -or $NowUtc -ge $ExpiresUtc) { throw 'Authority is not currently valid' }
    $Invocation = [string]$Authority.invocation_id
    if ($Invocation -notmatch '^[0-9a-f]{32}$') { throw 'Invocation ID is invalid' }

    $StableParent = Get-ProjectPath ([string]$Config.output_transaction.stable_parent_relative_path) 'stable output parent'
    if (-not [IO.Directory]::Exists($StableParent)) { throw 'Stable output parent must preexist' }
    $Stage = Join-Path $StableParent ".stage-$Invocation"
    $Final = Join-Path $StableParent "candidate-$Invocation"
    $Failure = Join-Path $StableParent "failure-$Invocation.receipt.json"
    if (Test-Path -LiteralPath $Stage -or Test-Path -LiteralPath $Final -or Test-Path -LiteralPath $Failure) { throw 'Invocation stage/final/failure namespace is not fresh' }
    $ConsumptionPath = Get-ProjectPath $ConsumptionRel 'authority consumption'
    $WorkerClaimPath = Get-ProjectPath $WorkerClaimRel 'worker claim'
    if (Test-Path -LiteralPath $ConsumptionPath -or Test-Path -LiteralPath $WorkerClaimPath) { throw 'Authority was already consumed or claimed' }

    $AuthoringReceiptPath = Get-ProjectPath $AuthoringStaticReceiptRel 'authoring static receipt'
    $AuthoringReceiptRaw = [IO.File]::ReadAllBytes($AuthoringReceiptPath)
    if ($AuthoringReceiptRaw.Length -ne $AuthoringStaticReceiptBytes -or (Get-Sha256Bytes $AuthoringReceiptRaw) -cne $AuthoringStaticReceiptSha256) { throw 'Authoring static receipt binding differs' }
    $PreclaimRows = [Collections.Generic.List[object]]::new()
    foreach ($Component in @($RuntimeIdentity.components)) { $PreclaimRows.Add((New-LockRow ([string]$Component.path) ([long]$Component.bytes) ([string]$Component.sha256) ([string]$Component.file_id))) }
    foreach ($Row in @(
        (New-LockRow $PolicyRel $PolicyBinding.Bytes $PolicyBinding.Sha256),
        (New-LockRow $WorkerPolicyCompatRel $WorkerPolicyCompatBinding.Bytes $WorkerPolicyCompatBinding.Sha256),
        (New-LockRow $LauncherRel $LauncherRaw.Length (Get-Sha256Bytes $LauncherRaw)),
        (New-LockRow $RuntimeIdentityRel $RuntimeBinding.Bytes $RuntimeBinding.Sha256),
        (New-LockRow $WorkerRel $WorkerRaw.Length (Get-Sha256Bytes $WorkerRaw)),
        (New-LockRow $WorkerConfigRel $ConfigBinding.Bytes $ConfigBinding.Sha256),
        (New-LockRow ([string]$Config.predecessor_execution_boundary.launcher_policy_path) ([long]$Config.predecessor_execution_boundary.launcher_policy_bytes) ([string]$Config.predecessor_execution_boundary.launcher_policy_sha256)),
        (New-LockRow ([string]$Config.predecessor_execution_boundary.independent_reaudit_path) ([long]$Config.predecessor_execution_boundary.independent_reaudit_bytes) ([string]$Config.predecessor_execution_boundary.independent_reaudit_sha256)),
        (New-LockRow ([string]$Config.source_preflight.policy_path) ([long]$Config.source_preflight.policy_bytes) ([string]$Config.source_preflight.policy_sha256)),
        (New-LockRow ([string]$Config.source_preflight.receipt_path) ([long]$Config.source_preflight.receipt_bytes) ([string]$Config.source_preflight.receipt_sha256)),
        (New-LockRow $AuthoringStaticReceiptRel $AuthoringStaticReceiptBytes $AuthoringStaticReceiptSha256),
        (New-LockRow $IndependentAuditRel $AuditBinding.Bytes $AuditBinding.Sha256),
        (New-LockRow $WorkerAuditCompatRel $WorkerAuditCompatBinding.Bytes $WorkerAuditCompatBinding.Sha256),
        (New-LockRow $AuthorityRel $AuthorityBinding.Bytes $AuthorityBinding.Sha256)
    )) { $PreclaimRows.Add($Row) }
    foreach ($Subject in @($Config.subjects)) { $PreclaimRows.Add((New-LockRow ([string]$Subject.source.path) ([long]$Subject.source.bytes) ([string]$Subject.source.sha256))) }

    $NamespaceClosure = Open-DirectoryIdentityClosure @($StableParent, $ConsumptionPath, $WorkerClaimPath, $Stage, $Final, $Failure)
    $PreclaimLocked = $null
    $FullLocked = $null
    $StageHandle = $null
    $StageStableIdentity = ''
    $OutputLocked = $null
    $ConsumptionBytes = $null
    $WorkerClaimBytes = $null
    $AuthorityConsumed = $false
    $FinalCommitted = $false
    try {
        $PreclaimLocked = Open-And-RevalidateLockedRows @($PreclaimRows) 'pre-consumption runtime/static/source/audit/authority closure'
        $ConsumedUtc = [DateTimeOffset]::UtcNow
        if ($ConsumedUtc -lt $IssuedUtc -or $ConsumedUtc -ge $ExpiresUtc) { throw 'Authority expired before consumption' }
        $Consumption = [ordered]@{
            schema_version = 2; record_type = 'AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_AUTHORITY_CONSUMPTION'; invocation_id = $Invocation
            consumed_utc = $ConsumedUtc.ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ', [Globalization.CultureInfo]::InvariantCulture)
            authority_sha256 = $AuthorityBinding.Sha256; launcher_policy_sha256 = $PolicyBinding.Sha256; launcher_independent_audit_sha256 = $AuditBinding.Sha256
            worker_sha256 = [string]$Policy.worker_sha256; worker_config_sha256 = [string]$Policy.worker_config_sha256; output_contract_sha256 = $OutputContractSha256
            single_use = $true; no_replace_commit = $true
        }
        $ConsumptionBytes = Get-CanonicalJsonBytes $Consumption
        Commit-BytesExclusive ($ConsumptionPath + ".prepared-$Invocation") $ConsumptionPath $ConsumptionBytes
        $AuthorityConsumed = $true
        $WorkerClaim = [ordered]@{
            schema_version = 2; record_type = 'AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_WORKER_CLAIM'; invocation_id = $Invocation
            authority_sha256 = $AuthorityBinding.Sha256; consumption_sha256 = (Get-Sha256Bytes $ConsumptionBytes)
            launcher_policy_sha256 = $PolicyBinding.Sha256; launcher_independent_audit_sha256 = $AuditBinding.Sha256
            worker_sha256 = [string]$Policy.worker_sha256; worker_config_sha256 = [string]$Policy.worker_config_sha256; output_contract_sha256 = $OutputContractSha256
        }
        $WorkerClaimBytes = Get-CanonicalJsonBytes $WorkerClaim
        Commit-BytesExclusive ($WorkerClaimPath + ".prepared-$Invocation") $WorkerClaimPath $WorkerClaimBytes
        $PostclaimRows = [Collections.Generic.List[object]]::new()
        foreach ($Row in $PreclaimRows) { $PostclaimRows.Add($Row) }
        $PostclaimRows.Add((New-LockRow $ConsumptionRel $ConsumptionBytes.Length (Get-Sha256Bytes $ConsumptionBytes)))
        $PostclaimRows.Add((New-LockRow $WorkerClaimRel $WorkerClaimBytes.Length (Get-Sha256Bytes $WorkerClaimBytes)))
        $FullLocked = Open-And-RevalidateLockedRows @($PostclaimRows) 'full runtime/static/source/authority/consumption/claim closure'
        Assert-LockedRows $PreclaimLocked 'continuous pre-consumption closure overlap'

        [AvatarFoundationNativeV2]::CreateDirectoryExclusive($Stage)
        $StageHandle = [AvatarFoundationNativeV2]::OpenDirectoryIdentityForRename($Stage)
        if ([AvatarFoundationNativeV2]::IsReparsePoint($StageHandle)) { throw 'Exclusively created stage is a reparse point' }
        if ((Get-ChildItem -LiteralPath $Stage -Force).Count -ne 0) { throw 'Exclusively created stage is not empty' }
        $StageStableIdentity = [AvatarFoundationNativeV2]::StableVolumeFileIdentity($StageHandle)
        $Blender = [string]$RuntimeIdentity.process_identity_requirements.canonical_blender_executable
        $Python = [string]$RuntimeIdentity.process_identity_requirements.canonical_bundled_python_executable
        $Arguments = @('--background','--factory-startup','--disable-autoexec','--python',$WorkerPath,'--','--config',$WorkerConfigPath,'--invocation-id',$Invocation,'--stage',$Stage,'--worker-claim',$WorkerClaimPath)
        $Environment = New-TrustedEnvironmentBlock ([IO.Directory]::GetParent($Blender).FullName) ([IO.Directory]::GetParent($Python).FullName)
        $ExitCode = Start-SuspendedJobBoundBlender $Blender $Arguments $Environment $FullLocked $RuntimeIdentity 900
        if ($ExitCode -ne 0) { throw "Blender worker failed with nonzero exit code $ExitCode" }
        Assert-LockedRows $FullLocked 'continuous closure after zero worker exit'
        $ClaimSha256 = Get-Sha256Bytes $WorkerClaimBytes
        $OutputLocked = Open-And-ValidateOutputClosure $Stage $Config $Policy $WorkerClaim $ClaimSha256 $PolicyBinding.Sha256 $AuthorityBinding.Sha256 (Get-Sha256Bytes $ConsumptionBytes) $Invocation
        Assert-DirectoryIdentityClosure $NamespaceClosure 'runtime namespace before final commit'
        if ([AvatarFoundationNativeV2]::StableVolumeFileIdentity($StageHandle) -cne $StageStableIdentity) { throw 'Stage directory identity changed before final commit' }
        if (Test-Path -LiteralPath $Final) { throw 'Final directory already exists' }
        [AvatarFoundationNativeV2]::RenameDirectoryHandleNoReplace($StageHandle, $Final)
        $FinalCommitted = $true
        if (Test-Path -LiteralPath $Stage -or -not (Test-Path -LiteralPath $Final)) { throw 'Final-directory namespace transition differs' }
        if ([AvatarFoundationNativeV2]::StableVolumeFileIdentity($StageHandle) -cne $StageStableIdentity) { throw 'Stage/final directory identity changed across commit' }
        $FinalPathHandle = [AvatarFoundationNativeV2]::OpenDirectoryIdentity($Final)
        try {
            if ([AvatarFoundationNativeV2]::IsReparsePoint($FinalPathHandle)) { throw 'Final path is a reparse point' }
            if ([AvatarFoundationNativeV2]::StableVolumeFileIdentity($FinalPathHandle) -cne $StageStableIdentity) { throw 'Final path does not name the exclusively created stage volume/file identity' }
        }
        finally { $FinalPathHandle.Dispose() }
        Assert-CommittedOutputClosure $OutputLocked $Final
        Assert-LockedRows $FullLocked 'continuous closure through terminal final commit'
    }
    catch {
        $PrimaryFailure = $_
        if ($null -ne $OutputLocked) { foreach ($Handle in $OutputLocked.Handles.Values) { $Handle.Dispose() }; $OutputLocked = $null }
        if ($AuthorityConsumed) {
            $ResiduePath = if ($FinalCommitted) { $Final } else { $Stage }
            $ResidueName = if ($FinalCommitted) { "candidate-$Invocation" } else { ".stage-$Invocation" }
            $ResidueState = $null
            $ResidueVerificationFailure = ''
            try { $ResidueState = Get-PreservedInvocationResidueState $ResiduePath $StableParent $ResidueName $StageHandle $StageStableIdentity $NamespaceClosure }
            catch { $ResidueVerificationFailure = $_.Exception.Message }
            $FailureValue = [ordered]@{
                schema_version = 2; record_type = 'AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_FAILURE_RECEIPT'; invocation_id = $Invocation
                authority_sha256 = $AuthorityBinding.Sha256; consumption_sha256 = (Get-Sha256Bytes $ConsumptionBytes); worker_claim_sha256 = if ($null -ne $WorkerClaimBytes) { Get-Sha256Bytes $WorkerClaimBytes } else { '' }
                four_file_output_committed = $false; body_accepted = $false; runtime_activation_allowed = $false; publication_performed = $false
                cleanup_performed = $false; residue_preserved = $true; residue_path = $ResiduePath
                residue_identity_verified = if ($null -ne $ResidueState) { [bool]$ResidueState.identity_verified } else { $false }
                residue_verification_failure = $ResidueVerificationFailure
                failure_type = $PrimaryFailure.Exception.GetType().FullName; failure_message = $PrimaryFailure.Exception.Message
            }
            Commit-BytesExclusive ($Failure + '.prepared') $Failure (Get-CanonicalJsonBytes $FailureValue)
        }
        throw $PrimaryFailure
    }
    finally {
        if ($null -ne $OutputLocked) { foreach ($Handle in $OutputLocked.Handles.Values) { $Handle.Dispose() } }
        if ($null -ne $StageHandle) { $StageHandle.Dispose() }
        Dispose-LockedRows $FullLocked
        Dispose-LockedRows $PreclaimLocked
        foreach ($Entry in $NamespaceClosure) { $Entry.Handle.Dispose() }
    }
}

Invoke-SeparateFoundationTrustedLauncher
