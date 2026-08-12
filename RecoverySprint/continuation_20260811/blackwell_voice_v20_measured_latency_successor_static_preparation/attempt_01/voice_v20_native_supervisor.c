#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <bcrypt.h>
#include <aclapi.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>

/*
 * Blackwell Voice V20 native supervision boundary (author source only).
 *
 * These bytes are deliberately not an execution package.  No sealed V20
 * executable or authority ledger exists, and wmain always refuses.  The
 * functions below provide a compile-checked x64 design/implementation for the
 * later separately audited successor: stable same-handle input binding,
 * reparse/hard-link/security rejection, one-use ledger reservation/terminal
 * append, kill-on-close Job ownership, and create-suspended/assign/prove/resume
 * process ordering.  They perform no operation unless a later executable
 * explicitly calls them.
 */

#define V20_SHA256_BYTES 32u
#define V20_FINAL_PATH_CHARS 32768u
#define V20_JOB_MEMORY_BYTES (16ull * 1024ull * 1024ull * 1024ull)
#define V20_REFUSAL_EXIT 125

typedef struct V20_FILE_BINDING_TAG {
    HANDLE handle;
    DWORD volume_serial;
    DWORD file_index_high;
    DWORD file_index_low;
    DWORD link_count;
    uint64_t byte_count;
    BYTE sha256[V20_SHA256_BYTES];
    BYTE security_sha256[V20_SHA256_BYTES];
    WCHAR final_path[V20_FINAL_PATH_CHARS];
} V20_FILE_BINDING;

typedef struct V20_LEDGER_TAG {
    HANDLE handle;
    V20_FILE_BINDING parent_directory;
    WCHAR final_path[V20_FINAL_PATH_CHARS];
    BYTE authority_sha256[V20_SHA256_BYTES];
    BYTE session_sha256[V20_SHA256_BYTES];
    BOOL terminal_appended;
} V20_LEDGER;

typedef struct V20_PROCESS_TREE_TAG {
    HANDLE job;
    PROCESS_INFORMATION process;
    BOOL assigned_before_resume;
    BOOL membership_proven_before_resume;
    BOOL resumed_once;
} V20_PROCESS_TREE;

#pragma pack(push, 1)
typedef struct V20_LEDGER_RESERVATION_TAG {
    BYTE magic[16];
    uint32_t version;
    uint32_t record_bytes;
    BYTE authority_sha256[V20_SHA256_BYTES];
    BYTE session_sha256[V20_SHA256_BYTES];
    BYTE candidate_sha256[V20_SHA256_BYTES];
} V20_LEDGER_RESERVATION;

typedef struct V20_LEDGER_TERMINAL_TAG {
    BYTE magic[16];
    uint32_t version;
    uint32_t record_bytes;
    BYTE authority_sha256[V20_SHA256_BYTES];
    BYTE session_sha256[V20_SHA256_BYTES];
    BYTE outcome_sha256[V20_SHA256_BYTES];
    uint32_t terminal_code;
    uint32_t reserved_zero;
} V20_LEDGER_TERMINAL;
#pragma pack(pop)

static const BYTE V20_RESERVATION_MAGIC[16] = {
    'K','I','R','A','V','2','0','R','E','S','E','R','V','E','D','\0'
};
static const BYTE V20_TERMINAL_MAGIC[16] = {
    'K','I','R','A','V','2','0','T','E','R','M','I','N','A','L','\0'
};

static BOOL v20_equal_digest(const BYTE left[V20_SHA256_BYTES],
                             const BYTE right[V20_SHA256_BYTES]) {
    BYTE difference = 0;
    DWORD index;
    for (index = 0; index < V20_SHA256_BYTES; ++index) {
        difference = (BYTE)(difference | (BYTE)(left[index] ^ right[index]));
    }
    return difference == 0;
}

static DWORD v20_sha256_bytes(const BYTE *data,
                              ULONG data_bytes,
                              BYTE output[V20_SHA256_BYTES]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    BYTE *object = NULL;
    DWORD object_bytes = 0;
    DWORD result_bytes = 0;
    NTSTATUS status;
    DWORD result = ERROR_GEN_FAILURE;

    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0);
    if (!BCRYPT_SUCCESS(status)) {
        return ERROR_INVALID_FUNCTION;
    }
    status = BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH,
                               (PUCHAR)&object_bytes, sizeof(object_bytes),
                               &result_bytes, 0);
    if (!BCRYPT_SUCCESS(status) || object_bytes == 0) {
        result = ERROR_INVALID_DATA;
        goto cleanup;
    }
    object = (BYTE *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, object_bytes);
    if (object == NULL) {
        result = ERROR_OUTOFMEMORY;
        goto cleanup;
    }
    status = BCryptCreateHash(algorithm, &hash, object, object_bytes, NULL, 0, 0);
    if (!BCRYPT_SUCCESS(status)) {
        result = ERROR_INVALID_FUNCTION;
        goto cleanup;
    }
    status = BCryptHashData(hash, (PUCHAR)data, data_bytes, 0);
    if (!BCRYPT_SUCCESS(status)) {
        result = ERROR_INVALID_DATA;
        goto cleanup;
    }
    status = BCryptFinishHash(hash, output, V20_SHA256_BYTES, 0);
    result = BCRYPT_SUCCESS(status) ? ERROR_SUCCESS : ERROR_INVALID_DATA;

cleanup:
    if (hash != NULL) {
        BCryptDestroyHash(hash);
    }
    if (object != NULL) {
        SecureZeroMemory(object, object_bytes);
        HeapFree(GetProcessHeap(), 0, object);
    }
    if (algorithm != NULL) {
        BCryptCloseAlgorithmProvider(algorithm, 0);
    }
    return result;
}

static DWORD v20_sha256_handle(HANDLE file,
                               BYTE output[V20_SHA256_BYTES],
                               uint64_t *byte_count) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    BYTE *object = NULL;
    BYTE *buffer = NULL;
    DWORD object_bytes = 0;
    DWORD result_bytes = 0;
    DWORD bytes_read = 0;
    DWORD result = ERROR_GEN_FAILURE;
    NTSTATUS status;
    LARGE_INTEGER original;
    LARGE_INTEGER zero;
    uint64_t total = 0;

    zero.QuadPart = 0;
    if (!SetFilePointerEx(file, zero, &original, FILE_CURRENT) ||
        !SetFilePointerEx(file, zero, NULL, FILE_BEGIN)) {
        return GetLastError();
    }
    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0);
    if (!BCRYPT_SUCCESS(status)) {
        result = ERROR_INVALID_FUNCTION;
        goto cleanup;
    }
    buffer = (BYTE *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 1024u * 1024u);
    if (buffer == NULL) {
        result = ERROR_OUTOFMEMORY;
        goto cleanup;
    }
    status = BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH,
                               (PUCHAR)&object_bytes, sizeof(object_bytes),
                               &result_bytes, 0);
    if (!BCRYPT_SUCCESS(status) || object_bytes == 0) {
        result = ERROR_INVALID_DATA;
        goto cleanup;
    }
    object = (BYTE *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, object_bytes);
    if (object == NULL) {
        result = ERROR_OUTOFMEMORY;
        goto cleanup;
    }
    status = BCryptCreateHash(algorithm, &hash, object, object_bytes, NULL, 0, 0);
    if (!BCRYPT_SUCCESS(status)) {
        result = ERROR_INVALID_FUNCTION;
        goto cleanup;
    }
    for (;;) {
        if (!ReadFile(file, buffer, 1024u * 1024u, &bytes_read, NULL)) {
            result = GetLastError();
            goto cleanup;
        }
        if (bytes_read == 0) {
            break;
        }
        status = BCryptHashData(hash, buffer, bytes_read, 0);
        if (!BCRYPT_SUCCESS(status)) {
            result = ERROR_INVALID_DATA;
            goto cleanup;
        }
        total += bytes_read;
    }
    status = BCryptFinishHash(hash, output, V20_SHA256_BYTES, 0);
    if (!BCRYPT_SUCCESS(status)) {
        result = ERROR_INVALID_DATA;
        goto cleanup;
    }
    *byte_count = total;
    result = ERROR_SUCCESS;

cleanup:
    if (buffer != NULL) {
        SecureZeroMemory(buffer, 1024u * 1024u);
        HeapFree(GetProcessHeap(), 0, buffer);
    }
    SetFilePointerEx(file, original, NULL, FILE_BEGIN);
    if (hash != NULL) {
        BCryptDestroyHash(hash);
    }
    if (object != NULL) {
        SecureZeroMemory(object, object_bytes);
        HeapFree(GetProcessHeap(), 0, object);
    }
    if (algorithm != NULL) {
        BCryptCloseAlgorithmProvider(algorithm, 0);
    }
    return result;
}

static DWORD v20_security_digest(HANDLE handle,
                                 BYTE output[V20_SHA256_BYTES]) {
    PSECURITY_DESCRIPTOR descriptor = NULL;
    PSID owner = NULL;
    PACL dacl = NULL;
    DWORD result;
    DWORD descriptor_bytes;

    result = GetSecurityInfo(handle, SE_FILE_OBJECT,
                             OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
                             &owner, NULL, &dacl, NULL, &descriptor);
    (void)owner;
    (void)dacl;
    if (result != ERROR_SUCCESS) {
        return result;
    }
    descriptor_bytes = GetSecurityDescriptorLength(descriptor);
    if (descriptor_bytes == 0) {
        LocalFree(descriptor);
        return ERROR_INVALID_SECURITY_DESCR;
    }
    result = v20_sha256_bytes((const BYTE *)descriptor, descriptor_bytes, output);
    LocalFree(descriptor);
    return result;
}

DWORD v20_open_and_bind_path(const WCHAR *path,
                             BOOL require_directory,
                             const BYTE expected_sha256[V20_SHA256_BYTES],
                             const BYTE expected_security_sha256[V20_SHA256_BYTES],
                             V20_FILE_BINDING *binding) {
    DWORD attributes;
    DWORD flags = FILE_FLAG_OPEN_REPARSE_POINT;
    BY_HANDLE_FILE_INFORMATION information;
    FILE_ATTRIBUTE_TAG_INFO tag;
    DWORD final_chars;
    DWORD result;
    uint64_t byte_count = 0;

    if (path == NULL || expected_security_sha256 == NULL || binding == NULL) {
        return ERROR_INVALID_PARAMETER;
    }
    ZeroMemory(binding, sizeof(*binding));
    binding->handle = INVALID_HANDLE_VALUE;
    attributes = GetFileAttributesW(path);
    if (attributes == INVALID_FILE_ATTRIBUTES) {
        return GetLastError();
    }
    if (require_directory) {
        if ((attributes & FILE_ATTRIBUTE_DIRECTORY) == 0) {
            return ERROR_DIRECTORY;
        }
        flags |= FILE_FLAG_BACKUP_SEMANTICS;
    } else if ((attributes & FILE_ATTRIBUTE_DIRECTORY) != 0) {
        return ERROR_DIRECTORY;
    }
    binding->handle = CreateFileW(path, GENERIC_READ | READ_CONTROL,
                                  FILE_SHARE_READ, NULL, OPEN_EXISTING,
                                  flags, NULL);
    if (binding->handle == INVALID_HANDLE_VALUE) {
        return GetLastError();
    }
    if (!GetFileInformationByHandleEx(binding->handle, FileAttributeTagInfo,
                                      &tag, sizeof(tag))) {
        result = GetLastError();
        goto fail;
    }
    if ((tag.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0) {
        result = ERROR_REPARSE_TAG_INVALID;
        goto fail;
    }
    if (!GetFileInformationByHandle(binding->handle, &information)) {
        result = GetLastError();
        goto fail;
    }
    if (!require_directory && information.nNumberOfLinks != 1) {
        result = ERROR_TOO_MANY_LINKS;
        goto fail;
    }
    final_chars = GetFinalPathNameByHandleW(binding->handle, binding->final_path,
                                             V20_FINAL_PATH_CHARS,
                                             FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (final_chars == 0 || final_chars >= V20_FINAL_PATH_CHARS) {
        result = final_chars == 0 ? GetLastError() : ERROR_INSUFFICIENT_BUFFER;
        goto fail;
    }
    binding->volume_serial = information.dwVolumeSerialNumber;
    binding->file_index_high = information.nFileIndexHigh;
    binding->file_index_low = information.nFileIndexLow;
    binding->link_count = information.nNumberOfLinks;
    if (!require_directory) {
        result = v20_sha256_handle(binding->handle, binding->sha256, &byte_count);
        if (result != ERROR_SUCCESS) {
            goto fail;
        }
        binding->byte_count = byte_count;
        if (expected_sha256 == NULL ||
            !v20_equal_digest(binding->sha256, expected_sha256)) {
            result = ERROR_CRC;
            goto fail;
        }
    }
    result = v20_security_digest(binding->handle, binding->security_sha256);
    if (result != ERROR_SUCCESS) {
        goto fail;
    }
    if (!v20_equal_digest(binding->security_sha256, expected_security_sha256)) {
        result = ERROR_ACCESS_DENIED;
        goto fail;
    }
    return ERROR_SUCCESS;

fail:
    CloseHandle(binding->handle);
    ZeroMemory(binding, sizeof(*binding));
    binding->handle = INVALID_HANDLE_VALUE;
    return result;
}

void v20_close_file_binding(V20_FILE_BINDING *binding) {
    if (binding != NULL && binding->handle != NULL &&
        binding->handle != INVALID_HANDLE_VALUE) {
        CloseHandle(binding->handle);
        binding->handle = INVALID_HANDLE_VALUE;
    }
}

DWORD v20_reserve_one_use_ledger(
    const WCHAR *ledger_path,
    const V20_FILE_BINDING *bound_parent,
    const BYTE authority_sha256[V20_SHA256_BYTES],
    const BYTE session_sha256[V20_SHA256_BYTES],
    const BYTE candidate_sha256[V20_SHA256_BYTES],
    V20_LEDGER *ledger) {
    V20_LEDGER_RESERVATION reservation;
    DWORD written = 0;
    DWORD final_chars;
    size_t parent_chars;

    if (ledger_path == NULL || bound_parent == NULL ||
        bound_parent->handle == NULL || bound_parent->handle == INVALID_HANDLE_VALUE ||
        authority_sha256 == NULL || session_sha256 == NULL ||
        candidate_sha256 == NULL || ledger == NULL) {
        return ERROR_INVALID_PARAMETER;
    }
    ZeroMemory(ledger, sizeof(*ledger));
    ledger->handle = INVALID_HANDLE_VALUE;
    ledger->parent_directory = *bound_parent;
    ledger->handle = CreateFileW(ledger_path, GENERIC_READ | GENERIC_WRITE,
                                 0, NULL, CREATE_NEW,
                                 FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH,
                                 NULL);
    if (ledger->handle == INVALID_HANDLE_VALUE) {
        return GetLastError();
    }
    final_chars = GetFinalPathNameByHandleW(ledger->handle, ledger->final_path,
                                             V20_FINAL_PATH_CHARS,
                                             FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (final_chars == 0 || final_chars >= V20_FINAL_PATH_CHARS) {
        DWORD result = final_chars == 0 ? GetLastError() : ERROR_INSUFFICIENT_BUFFER;
        CloseHandle(ledger->handle);
        ledger->handle = INVALID_HANDLE_VALUE;
        return result;
    }
    parent_chars = wcslen(bound_parent->final_path);
    if (parent_chars == 0 ||
        _wcsnicmp(ledger->final_path, bound_parent->final_path, parent_chars) != 0 ||
        (ledger->final_path[parent_chars] != L'\\' &&
         ledger->final_path[parent_chars] != L'/')) {
        CloseHandle(ledger->handle);
        ledger->handle = INVALID_HANDLE_VALUE;
        return ERROR_ACCESS_DENIED;
    }
    ZeroMemory(&reservation, sizeof(reservation));
    CopyMemory(reservation.magic, V20_RESERVATION_MAGIC, sizeof(reservation.magic));
    reservation.version = 1;
    reservation.record_bytes = (uint32_t)sizeof(reservation);
    CopyMemory(reservation.authority_sha256, authority_sha256, V20_SHA256_BYTES);
    CopyMemory(reservation.session_sha256, session_sha256, V20_SHA256_BYTES);
    CopyMemory(reservation.candidate_sha256, candidate_sha256, V20_SHA256_BYTES);
    if (!WriteFile(ledger->handle, &reservation, (DWORD)sizeof(reservation),
                   &written, NULL) || written != sizeof(reservation) ||
        !FlushFileBuffers(ledger->handle)) {
        DWORD result = GetLastError();
        CloseHandle(ledger->handle);
        ledger->handle = INVALID_HANDLE_VALUE;
        return result == ERROR_SUCCESS ? ERROR_WRITE_FAULT : result;
    }
    CopyMemory(ledger->authority_sha256, authority_sha256, V20_SHA256_BYTES);
    CopyMemory(ledger->session_sha256, session_sha256, V20_SHA256_BYTES);
    ledger->terminal_appended = FALSE;
    return ERROR_SUCCESS;
}

DWORD v20_append_terminal_same_handle(
    V20_LEDGER *ledger,
    const BYTE outcome_sha256[V20_SHA256_BYTES],
    uint32_t terminal_code) {
    V20_LEDGER_TERMINAL terminal;
    LARGE_INTEGER zero;
    DWORD written = 0;

    if (ledger == NULL || ledger->handle == NULL ||
        ledger->handle == INVALID_HANDLE_VALUE || outcome_sha256 == NULL ||
        ledger->terminal_appended) {
        return ERROR_INVALID_PARAMETER;
    }
    ZeroMemory(&terminal, sizeof(terminal));
    CopyMemory(terminal.magic, V20_TERMINAL_MAGIC, sizeof(terminal.magic));
    terminal.version = 1;
    terminal.record_bytes = (uint32_t)sizeof(terminal);
    CopyMemory(terminal.authority_sha256, ledger->authority_sha256, V20_SHA256_BYTES);
    CopyMemory(terminal.session_sha256, ledger->session_sha256, V20_SHA256_BYTES);
    CopyMemory(terminal.outcome_sha256, outcome_sha256, V20_SHA256_BYTES);
    terminal.terminal_code = terminal_code;
    zero.QuadPart = 0;
    if (!SetFilePointerEx(ledger->handle, zero, NULL, FILE_END) ||
        !WriteFile(ledger->handle, &terminal, (DWORD)sizeof(terminal),
                   &written, NULL) || written != sizeof(terminal) ||
        !FlushFileBuffers(ledger->handle)) {
        DWORD result = GetLastError();
        return result == ERROR_SUCCESS ? ERROR_WRITE_FAULT : result;
    }
    ledger->terminal_appended = TRUE;
    return ERROR_SUCCESS;
}

void v20_close_ledger(V20_LEDGER *ledger) {
    if (ledger != NULL && ledger->handle != NULL &&
        ledger->handle != INVALID_HANDLE_VALUE) {
        CloseHandle(ledger->handle);
        ledger->handle = INVALID_HANDLE_VALUE;
    }
}

DWORD v20_create_owned_job(HANDLE *job_out) {
    HANDLE job;
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits;
    if (job_out == NULL) {
        return ERROR_INVALID_PARAMETER;
    }
    *job_out = NULL;
    job = CreateJobObjectW(NULL, NULL);
    if (job == NULL) {
        return GetLastError();
    }
    ZeroMemory(&limits, sizeof(limits));
    limits.BasicLimitInformation.LimitFlags =
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_JOB_MEMORY;
    limits.JobMemoryLimit = (SIZE_T)V20_JOB_MEMORY_BYTES;
    if (!SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                 &limits, sizeof(limits))) {
        DWORD result = GetLastError();
        CloseHandle(job);
        return result;
    }
    *job_out = job;
    return ERROR_SUCCESS;
}

DWORD v20_spawn_suspended_assign_prove_resume(
    WCHAR *mutable_command_line,
    const WCHAR *working_directory,
    WCHAR *environment_block,
    const HANDLE *inherited_handles,
    SIZE_T inherited_handle_count,
    V20_PROCESS_TREE *tree) {
    STARTUPINFOEXW startup;
    SIZE_T attribute_bytes = 0;
    BOOL in_job = FALSE;
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION observed_limits;
    DWORD result;
    DWORD creation_flags = CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT |
                           CREATE_NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT;

    if (mutable_command_line == NULL || inherited_handles == NULL ||
        inherited_handle_count == 0 || tree == NULL) {
        return ERROR_INVALID_PARAMETER;
    }
    ZeroMemory(tree, sizeof(*tree));
    ZeroMemory(&startup, sizeof(startup));
    startup.StartupInfo.cb = sizeof(startup);
    InitializeProcThreadAttributeList(NULL, 1, 0, &attribute_bytes);
    if (attribute_bytes == 0) {
        return GetLastError();
    }
    startup.lpAttributeList = (LPPROC_THREAD_ATTRIBUTE_LIST)HeapAlloc(
        GetProcessHeap(), HEAP_ZERO_MEMORY, attribute_bytes);
    if (startup.lpAttributeList == NULL) {
        return ERROR_OUTOFMEMORY;
    }
    if (!InitializeProcThreadAttributeList(startup.lpAttributeList, 1, 0,
                                           &attribute_bytes)) {
        result = GetLastError();
        goto fail_attributes;
    }
    if (!UpdateProcThreadAttribute(
            startup.lpAttributeList, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            (PVOID)inherited_handles,
            inherited_handle_count * sizeof(HANDLE), NULL, NULL)) {
        result = GetLastError();
        goto fail_list;
    }
    result = v20_create_owned_job(&tree->job);
    if (result != ERROR_SUCCESS) {
        goto fail_list;
    }
    if (!CreateProcessW(NULL, mutable_command_line, NULL, NULL, TRUE,
                        creation_flags, environment_block, working_directory,
                        &startup.StartupInfo, &tree->process)) {
        result = GetLastError();
        goto fail_job;
    }
    if (!AssignProcessToJobObject(tree->job, tree->process.hProcess)) {
        result = GetLastError();
        goto fail_process;
    }
    tree->assigned_before_resume = TRUE;
    if (!IsProcessInJob(tree->process.hProcess, tree->job, &in_job) || !in_job) {
        result = GetLastError();
        if (result == ERROR_SUCCESS) {
            result = ERROR_ACCESS_DENIED;
        }
        goto fail_process;
    }
    ZeroMemory(&observed_limits, sizeof(observed_limits));
    if (!QueryInformationJobObject(tree->job, JobObjectExtendedLimitInformation,
                                   &observed_limits, sizeof(observed_limits), NULL) ||
        (observed_limits.BasicLimitInformation.LimitFlags &
         JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) == 0 ||
        (observed_limits.BasicLimitInformation.LimitFlags &
         JOB_OBJECT_LIMIT_JOB_MEMORY) == 0 ||
        observed_limits.JobMemoryLimit != (SIZE_T)V20_JOB_MEMORY_BYTES) {
        result = GetLastError();
        if (result == ERROR_SUCCESS) {
            result = ERROR_INVALID_DATA;
        }
        goto fail_process;
    }
    tree->membership_proven_before_resume = TRUE;
    if (ResumeThread(tree->process.hThread) != 1u) {
        result = GetLastError();
        goto fail_process;
    }
    tree->resumed_once = TRUE;
    DeleteProcThreadAttributeList(startup.lpAttributeList);
    HeapFree(GetProcessHeap(), 0, startup.lpAttributeList);
    return ERROR_SUCCESS;

fail_process:
    TerminateJobObject(tree->job, result);
    WaitForSingleObject(tree->process.hProcess, 5000u);
    CloseHandle(tree->process.hThread);
    CloseHandle(tree->process.hProcess);
    ZeroMemory(&tree->process, sizeof(tree->process));
fail_job:
    CloseHandle(tree->job);
    tree->job = NULL;
fail_list:
    DeleteProcThreadAttributeList(startup.lpAttributeList);
fail_attributes:
    HeapFree(GetProcessHeap(), 0, startup.lpAttributeList);
    return result;
}

DWORD v20_terminate_owned_tree(V20_PROCESS_TREE *tree, UINT exit_code) {
    DWORD result = ERROR_SUCCESS;
    if (tree == NULL || tree->job == NULL) {
        return ERROR_INVALID_PARAMETER;
    }
    if (!TerminateJobObject(tree->job, exit_code)) {
        result = GetLastError();
    }
    if (tree->process.hProcess != NULL) {
        WaitForSingleObject(tree->process.hProcess, 5000u);
    }
    if (tree->process.hThread != NULL) {
        CloseHandle(tree->process.hThread);
    }
    if (tree->process.hProcess != NULL) {
        CloseHandle(tree->process.hProcess);
    }
    CloseHandle(tree->job);
    ZeroMemory(tree, sizeof(*tree));
    return result;
}

int wmain(int argc, WCHAR **argv) {
    (void)argc;
    (void)argv;
    fwprintf(stderr,
             L"Blackwell Voice V20 author source has no execution authority; "
             L"no process, model, GPU, audio, camera, or ledger was opened.\n");
    return V20_REFUSAL_EXIT;
}
