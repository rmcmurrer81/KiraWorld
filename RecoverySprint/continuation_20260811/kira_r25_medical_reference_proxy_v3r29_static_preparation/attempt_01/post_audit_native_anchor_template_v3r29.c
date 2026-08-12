#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#pragma comment(lib, "bcrypt.lib")

#define SHA_BYTES 32U
#define SHA_HEX 64U
#define LEDGER_BYTES 4096U
#define MAX_BINDINGS 128U
#define MAX_SMALL_FILE (8U * 1024U * 1024U)
#define CHILD_TIMEOUT_MS (20U * 60U * 1000U)
#define PATH_CHARS 1024U
#define FINAL_OUTPUT_COUNT 8U

typedef struct V3R29Binding {
    const wchar_t *path;
    ULONGLONG bytes;
    const char *sha256;
    const char *label;
} V3R29Binding;

#ifndef V3R29_BINDINGS_HEADER
#define V3R29_BINDINGS_HEADER "POST_AUDIT_BINDINGS_TEMPLATE_v3r29.h"
#endif
#include V3R29_BINDINGS_HEADER

typedef struct LockedBinding {
    HANDLE handle;
    FILE_ID_INFO identity;
} LockedBinding;

typedef struct ReservedOutput {
    HANDLE handle;
    FILE_ID_INFO identity;
    wchar_t path[PATH_CHARS];
    ULONGLONG bytes;
    unsigned char digest[SHA_BYTES];
} ReservedOutput;

enum LedgerState {
    LEDGER_PENDING_CONSUMED = 1U,
    LEDGER_SUCCESS_CONSUMED = 2U,
    LEDGER_FAILURE_CONSUMED = 3U
};

static const unsigned char LEDGER_MAGIC[16] = {
    'K','I','R','A','V','3','R','2','8','L','E','D','G','E','R','1'
};

static int lower_hex64(const char *value) {
    size_t index;
    if (value == NULL || strlen(value) != SHA_HEX) return 0;
    for (index = 0U; index < SHA_HEX; ++index)
        if (!((value[index] >= '0' && value[index] <= '9') ||
              (value[index] >= 'a' && value[index] <= 'f'))) return 0;
    return 1;
}

static void digest_hex(const unsigned char digest[SHA_BYTES], char output[SHA_HEX + 1U]) {
    static const char symbols[] = "0123456789abcdef";
    size_t index;
    for (index = 0U; index < SHA_BYTES; ++index) {
        output[index * 2U] = symbols[digest[index] >> 4U];
        output[index * 2U + 1U] = symbols[digest[index] & 15U];
    }
    output[SHA_HEX] = '\0';
}

static int sha_memory(const unsigned char *data, DWORD bytes, unsigned char output[SHA_BYTES]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    DWORD object_bytes = 0U, result_bytes = 0U;
    PUCHAR object = NULL;
    NTSTATUS status;
    int ok = 0;
    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) goto cleanup;
    status = BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&object_bytes,
        (ULONG)sizeof(object_bytes), &result_bytes, 0U);
    if (status < 0 || result_bytes != sizeof(object_bytes) || object_bytes == 0U) goto cleanup;
    object = (PUCHAR)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, object_bytes);
    if (object == NULL) goto cleanup;
    status = BCryptCreateHash(algorithm, &hash, object, object_bytes, NULL, 0U, 0U);
    if (status < 0) goto cleanup;
    status = BCryptHashData(hash, (PUCHAR)data, bytes, 0U);
    if (status < 0) goto cleanup;
    status = BCryptFinishHash(hash, output, SHA_BYTES, 0U);
    if (status >= 0) ok = 1;
cleanup:
    if (hash != NULL) BCryptDestroyHash(hash);
    if (object != NULL) {
        SecureZeroMemory(object, object_bytes);
        HeapFree(GetProcessHeap(), 0U, object);
    }
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
    return ok;
}

static int sha_handle(HANDLE file, unsigned char output[SHA_BYTES]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    DWORD object_bytes = 0U, result_bytes = 0U, got = 0U;
    LARGE_INTEGER zero;
    PUCHAR object = NULL;
    unsigned char *buffer = NULL;
    NTSTATUS status;
    int ok = 0;
    zero.QuadPart = 0;
    if (!SetFilePointerEx(file, zero, NULL, FILE_BEGIN)) return 0;
    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) goto cleanup;
    status = BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&object_bytes,
        (ULONG)sizeof(object_bytes), &result_bytes, 0U);
    if (status < 0 || result_bytes != sizeof(object_bytes) || object_bytes == 0U) goto cleanup;
    object = (PUCHAR)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, object_bytes);
    if (object == NULL) goto cleanup;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), 0U, 1024U * 1024U);
    if (buffer == NULL) goto cleanup;
    status = BCryptCreateHash(algorithm, &hash, object, object_bytes, NULL, 0U, 0U);
    if (status < 0) goto cleanup;
    for (;;) {
        if (!ReadFile(file, buffer, 1024U * 1024U, &got, NULL)) goto cleanup;
        if (got == 0U) break;
        status = BCryptHashData(hash, buffer, got, 0U);
        if (status < 0) goto cleanup;
    }
    status = BCryptFinishHash(hash, output, SHA_BYTES, 0U);
    if (status >= 0) ok = 1;
cleanup:
    if (buffer != NULL) {
        SecureZeroMemory(buffer, 1024U * 1024U);
        HeapFree(GetProcessHeap(), 0U, buffer);
    }
    if (hash != NULL) BCryptDestroyHash(hash);
    if (object != NULL) {
        SecureZeroMemory(object, object_bytes);
        HeapFree(GetProcessHeap(), 0U, object);
    }
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
    return ok;
}

static int exact_final_path(HANDLE file, const wchar_t *expected) {
    const SIZE_T capacity = PATH_CHARS;
    wchar_t *observed = (wchar_t *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        capacity * sizeof(wchar_t));
    wchar_t *normalized = (wchar_t *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        capacity * sizeof(wchar_t));
    DWORD length;
    const wchar_t *source;
    int ok = 0;
    if (observed == NULL || normalized == NULL) goto cleanup;
    length = GetFinalPathNameByHandleW(file, observed, (DWORD)capacity,
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    source = observed;
    if (length == 0U || length >= (DWORD)capacity) goto cleanup;
    if (wcsncmp(source, L"\\\\?\\", 4U) == 0) source += 4U;
    if (wcsncmp(source, L"UNC\\", 4U) == 0) {
        if (swprintf_s(normalized, capacity, L"\\\\%s", source + 4U) < 0) goto cleanup;
        source = normalized;
    }
    ok = _wcsicmp(source, expected) == 0;
cleanup:
    if (observed != NULL) HeapFree(GetProcessHeap(), 0U, observed);
    if (normalized != NULL) HeapFree(GetProcessHeap(), 0U, normalized);
    return ok;
}

static int regular_nonreparse(HANDLE file, ULONGLONG *bytes, FILE_ID_INFO *identity) {
    FILE_ATTRIBUTE_TAG_INFO attributes;
    FILE_STANDARD_INFO standard;
    if (!GetFileInformationByHandleEx(file, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) ||
        (attributes.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_DEVICE |
            FILE_ATTRIBUTE_REPARSE_POINT)) != 0U ||
        !GetFileInformationByHandleEx(file, FileStandardInfo, &standard,
            (DWORD)sizeof(standard)) || standard.EndOfFile.QuadPart < 0 ||
        !GetFileInformationByHandleEx(file, FileIdInfo, identity,
            (DWORD)sizeof(*identity))) return 0;
    *bytes = (ULONGLONG)standard.EndOfFile.QuadPart;
    return 1;
}

static int lock_exact(const V3R29Binding *binding, LockedBinding *locked) {
    ULONGLONG bytes = 0ULL;
    unsigned char digest[SHA_BYTES];
    char hex[SHA_HEX + 1U];
    SecureZeroMemory(locked, sizeof(*locked));
    locked->handle = INVALID_HANDLE_VALUE;
    if (!lower_hex64(binding->sha256) || binding->bytes == 0ULL) return 0;
    locked->handle = CreateFileW(binding->path, GENERIC_READ, FILE_SHARE_READ, NULL,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (locked->handle == INVALID_HANDLE_VALUE ||
        !regular_nonreparse(locked->handle, &bytes, &locked->identity) ||
        bytes != binding->bytes || !exact_final_path(locked->handle, binding->path) ||
        !sha_handle(locked->handle, digest)) goto fail;
    digest_hex(digest, hex);
    SecureZeroMemory(digest, sizeof(digest));
    if (memcmp(hex, binding->sha256, SHA_HEX) != 0) goto fail;
    return 1;
fail:
    SecureZeroMemory(digest, sizeof(digest));
    if (locked->handle != INVALID_HANDLE_VALUE) CloseHandle(locked->handle);
    locked->handle = INVALID_HANDLE_VALUE;
    return 0;
}

static void close_bindings(LockedBinding locked[MAX_BINDINGS], UINT count) {
    UINT index;
    for (index = 0U; index < count; ++index) {
        if (locked[index].handle != INVALID_HANDLE_VALUE) CloseHandle(locked[index].handle);
        locked[index].handle = INVALID_HANDLE_VALUE;
        SecureZeroMemory(&locked[index].identity, sizeof(locked[index].identity));
    }
}

static int verify_all_bindings(LockedBinding locked[MAX_BINDINGS]) {
    UINT index;
    volatile UINT materialized_count = V3R29_BINDING_COUNT;
    const UINT count = materialized_count;
    const char *stage1_root = V3R29_STAGE1_PACKAGE_ROOT;
    const char *audit_digest = V3R29_AUDIT_A_SHA256;
    const char *auditor = V3R29_AUDITOR;
    if (count == 0U || count > MAX_BINDINGS ||
        !lower_hex64(stage1_root) || !lower_hex64(audit_digest) ||
        strcmp(auditor, "UNMATERIALIZED") == 0) return 0;
    for (index = 0U; index < count; ++index)
        if (!lock_exact(&V3R29_BINDINGS[index], &locked[index])) {
            close_bindings(locked, index);
            return 0;
        }
    return 1;
}

static int open_self(HANDLE *output, unsigned char digest[SHA_BYTES]) {
    wchar_t module[PATH_CHARS];
    DWORD length = GetModuleFileNameW(NULL, module, (DWORD)_countof(module));
    ULONGLONG bytes = 0ULL;
    FILE_ID_INFO identity;
    if (length == 0U || length >= (DWORD)_countof(module) ||
        _wcsicmp(module, V3R29_EXPECTED_SELF_PATH) != 0) return 0;
    *output = CreateFileW(module, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (*output == INVALID_HANDLE_VALUE || !regular_nonreparse(*output, &bytes, &identity) ||
        !exact_final_path(*output, V3R29_EXPECTED_SELF_PATH) || !sha_handle(*output, digest)) {
        if (*output != INVALID_HANDLE_VALUE) CloseHandle(*output);
        *output = INVALID_HANDLE_VALUE;
        return 0;
    }
    return 1;
}

static int open_output_parent(HANDLE *output) {
    FILE_ATTRIBUTE_TAG_INFO attributes;
    *output = CreateFileW(V3R29_OUTPUT_PARENT, FILE_ADD_FILE | FILE_ADD_SUBDIRECTORY |
        FILE_READ_ATTRIBUTES | SYNCHRONIZE, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
        OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (*output == INVALID_HANDLE_VALUE ||
        !GetFileInformationByHandleEx(*output, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) ||
        (attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0U ||
        (attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U ||
        !exact_final_path(*output, V3R29_OUTPUT_PARENT)) {
        if (*output != INVALID_HANDLE_VALUE) CloseHandle(*output);
        *output = INVALID_HANDLE_VALUE;
        return 0;
    }
    return 1;
}

static int join_path(wchar_t output[PATH_CHARS], const wchar_t *leaf) {
    return swprintf_s(output, PATH_CHARS, L"%s\\%s", V3R29_OUTPUT_PARENT, leaf) > 0;
}

static int write_all(HANDLE file, const unsigned char *data, DWORD bytes) {
    DWORD total = 0U;
    while (total < bytes) {
        DWORD wrote = 0U;
        if (!WriteFile(file, data + total, bytes - total, &wrote, NULL) || wrote == 0U) return 0;
        total += wrote;
    }
    return 1;
}

static int ledger_update(HANDLE ledger, uint32_t state, uint32_t stage,
    DWORD win32_error, DWORD child_exit, const unsigned char self_sha[SHA_BYTES],
    const unsigned char manifest_sha[SHA_BYTES]) {
    unsigned char record[LEDGER_BYTES], readback[LEDGER_BYTES], integrity[SHA_BYTES];
    LARGE_INTEGER zero;
    DWORD got = 0U;
    zero.QuadPart = 0;
    SecureZeroMemory(record, sizeof(record));
    SecureZeroMemory(readback, sizeof(readback));
    memcpy(record, LEDGER_MAGIC, sizeof(LEDGER_MAGIC));
    memcpy(record + 16U, &state, sizeof(state));
    memcpy(record + 20U, &stage, sizeof(stage));
    memcpy(record + 24U, &win32_error, sizeof(win32_error));
    memcpy(record + 28U, &child_exit, sizeof(child_exit));
    memcpy(record + 32U, self_sha, SHA_BYTES);
    memcpy(record + 64U, manifest_sha, SHA_BYTES);
    memcpy(record + 96U, V3R29_STAGE1_PACKAGE_ROOT, SHA_HEX);
    memcpy(record + 160U, V3R29_AUDIT_A_SHA256, SHA_HEX);
    memcpy(record + 224U, V3R29_STAGE1_SEAL_SHA256, SHA_HEX);
    memcpy(record + 288U, V3R29_STAGE1_ALL_FILES_ROOT, SHA_HEX);
    memcpy(record + 352U, V3R29_MATERIALIZATION_CONSUMPTION_KEY, SHA_HEX);
    if (!sha_memory(record, LEDGER_BYTES - SHA_BYTES, integrity)) return 0;
    memcpy(record + LEDGER_BYTES - SHA_BYTES, integrity, SHA_BYTES);
    if (!SetFilePointerEx(ledger, zero, NULL, FILE_BEGIN) ||
        !write_all(ledger, record, LEDGER_BYTES) || !SetEndOfFile(ledger) ||
        !FlushFileBuffers(ledger) || !SetFilePointerEx(ledger, zero, NULL, FILE_BEGIN) ||
        !ReadFile(ledger, readback, LEDGER_BYTES, &got, NULL) || got != LEDGER_BYTES ||
        memcmp(record, readback, LEDGER_BYTES) != 0) {
        SecureZeroMemory(record, sizeof(record));
        SecureZeroMemory(readback, sizeof(readback));
        SecureZeroMemory(integrity, sizeof(integrity));
        return 0;
    }
    SecureZeroMemory(record, sizeof(record));
    SecureZeroMemory(readback, sizeof(readback));
    SecureZeroMemory(integrity, sizeof(integrity));
    return 1;
}

static HANDLE create_ledger(const unsigned char self_sha[SHA_BYTES]) {
    wchar_t path[PATH_CHARS];
    HANDLE ledger;
    unsigned char zero_sha[SHA_BYTES];
    SecureZeroMemory(zero_sha, sizeof(zero_sha));
    if (!join_path(path, L"V3R29_ATTEMPT_OUTCOME_RECEIPT.bin")) return INVALID_HANDLE_VALUE;
    ledger = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL,
        CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (ledger == INVALID_HANDLE_VALUE || !exact_final_path(ledger, path) ||
        !ledger_update(ledger, LEDGER_PENDING_CONSUMED, 10U, ERROR_SUCCESS,
            STILL_ACTIVE, self_sha, zero_sha)) {
        if (ledger != INVALID_HANDLE_VALUE) CloseHandle(ledger);
        return INVALID_HANDLE_VALUE;
    }
    return ledger;
}

static int random_hex(char output[SHA_HEX + 1U]) {
    unsigned char data[SHA_BYTES];
    NTSTATUS status = BCryptGenRandom(NULL, data, SHA_BYTES, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (status < 0) return 0;
    digest_hex(data, output);
    SecureZeroMemory(data, sizeof(data));
    return 1;
}

static int create_exact_directory(const wchar_t *leaf, HANDLE *directory) {
    wchar_t path[PATH_CHARS];
    FILE_ATTRIBUTE_TAG_INFO attributes;
    if (!join_path(path, leaf) || !CreateDirectoryW(path, NULL)) return 0;
    *directory = CreateFileW(path, FILE_ADD_FILE | FILE_ADD_SUBDIRECTORY |
        FILE_READ_ATTRIBUTES | SYNCHRONIZE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (*directory == INVALID_HANDLE_VALUE ||
        !GetFileInformationByHandleEx(*directory, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) ||
        (attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0U ||
        (attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U ||
        !exact_final_path(*directory, path)) {
        if (*directory != INVALID_HANDLE_VALUE) CloseHandle(*directory);
        *directory = INVALID_HANDLE_VALUE;
        return 0;
    }
    return 1;
}

static const wchar_t *FINAL_OUTPUT_LEAVES[FINAL_OUTPUT_COUNT] = {
    L"outputs\\kira_v3r29_normalized_pelvic_core_reference_proxy.blend",
    L"outputs\\front_clinical.png", L"outputs\\right_clinical.png",
    L"outputs\\iso_clinical.png", L"outputs\\iso_xray.png",
    L"outputs\\WORKER_RESULT.json", L"outputs\\WORKER_RECEIPT.tsv",
    L"outputs\\FINAL_OUTPUT_MANIFEST.tsv"
};

static void close_reserved_outputs(ReservedOutput outputs[FINAL_OUTPUT_COUNT]) {
    UINT index;
    for (index = 0U; index < FINAL_OUTPUT_COUNT; ++index) {
        if (outputs[index].handle != INVALID_HANDLE_VALUE && outputs[index].handle != NULL)
            CloseHandle(outputs[index].handle);
        outputs[index].handle = INVALID_HANDLE_VALUE;
        SecureZeroMemory(&outputs[index].identity, sizeof(outputs[index].identity));
        SecureZeroMemory(outputs[index].path, sizeof(outputs[index].path));
        outputs[index].bytes = 0ULL;
        SecureZeroMemory(outputs[index].digest, sizeof(outputs[index].digest));
    }
}

static int reserve_final_outputs(ReservedOutput outputs[FINAL_OUTPUT_COUNT]) {
    UINT index;
    ULONGLONG bytes = 0ULL;
    for (index = 0U; index < FINAL_OUTPUT_COUNT; ++index) {
        SecureZeroMemory(&outputs[index], sizeof(outputs[index]));
        outputs[index].handle = INVALID_HANDLE_VALUE;
    }
    for (index = 0U; index < FINAL_OUTPUT_COUNT; ++index) {
        if (!join_path(outputs[index].path, FINAL_OUTPUT_LEAVES[index])) goto fail;
        outputs[index].handle = CreateFileW(outputs[index].path,
            GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
                FILE_FLAG_OPEN_REPARSE_POINT, NULL);
        if (outputs[index].handle == INVALID_HANDLE_VALUE ||
            !regular_nonreparse(outputs[index].handle, &bytes, &outputs[index].identity) ||
            bytes != 0ULL || !exact_final_path(outputs[index].handle, outputs[index].path))
            goto fail;
    }
    return 1;
fail:
    close_reserved_outputs(outputs);
    return 0;
}

static int create_capability(wchar_t path[PATH_CHARS], char digest_hex_out[SHA_HEX + 1U]) {
    char nonce[SHA_HEX + 1U];
    char json[8192];
    unsigned char digest[SHA_BYTES];
    HANDLE file;
    int bytes;
    if (!join_path(path, L"V3R29_NATIVE_CAPABILITY.json") || !random_hex(nonce)) return 0;
    bytes = sprintf_s(json, sizeof(json),
        "{\"audit_a_sha256\":\"%s\",\"blend_path\":\"%ls\\\\outputs\\\\worker_staging\\\\kira_v3r29_normalized_pelvic_core_reference_proxy.blend\","
        "\"frame_sha256\":\"%s\",\"native_parent_pid\":%lu,\"nonce\":\"%s\",\"output_root\":\"%ls\\\\outputs\\\\worker_staging\","
        "\"render_paths\":{\"front_clinical\":\"%ls\\\\outputs\\\\worker_staging\\\\front_clinical.png\",\"iso_clinical\":\"%ls\\\\outputs\\\\worker_staging\\\\iso_clinical.png\","
        "\"iso_xray\":\"%ls\\\\outputs\\\\worker_staging\\\\iso_xray.png\",\"right_clinical\":\"%ls\\\\outputs\\\\worker_staging\\\\right_clinical.png\"},"
        "\"receipt_path\":\"%ls\\\\outputs\\\\worker_staging\\\\WORKER_RECEIPT.tsv\",\"result_path\":\"%ls\\\\outputs\\\\worker_staging\\\\WORKER_RESULT.json\"," 
        "\"schema\":\"kira.r25.medical_reference_proxy.v3r29.native_capability.v1\"," 
        "\"spec_sha256\":\"%s\",\"stage1_package_root\":\"%s\",\"state\":\"PENDING_CONSUMED\",\"worker_sha256\":\"%s\"}\n",
        V3R29_AUDIT_A_SHA256, V3R29_OUTPUT_PARENT, V3R29_FRAME_SHA256,
        (unsigned long)GetCurrentProcessId(), nonce, V3R29_OUTPUT_PARENT,
        V3R29_OUTPUT_PARENT, V3R29_OUTPUT_PARENT, V3R29_OUTPUT_PARENT,
        V3R29_OUTPUT_PARENT, V3R29_OUTPUT_PARENT, V3R29_OUTPUT_PARENT,
        V3R29_SPEC_SHA256,
        V3R29_STAGE1_PACKAGE_ROOT, V3R29_WORKER_SHA256);
    if (bytes <= 0 || (size_t)bytes >= sizeof(json) ||
        !sha_memory((const unsigned char *)json, (DWORD)bytes, digest)) return 0;
    digest_hex(digest, digest_hex_out);
    SecureZeroMemory(digest, sizeof(digest));
    file = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL,
        CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE || !exact_final_path(file, path) ||
        !write_all(file, (const unsigned char *)json, (DWORD)bytes) ||
        !FlushFileBuffers(file)) {
        if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
        SecureZeroMemory(json, sizeof(json));
        return 0;
    }
    CloseHandle(file);
    SecureZeroMemory(json, sizeof(json));
    return 1;
}

static int create_inherited_log(const wchar_t *leaf, HANDLE *output) {
    wchar_t path[PATH_CHARS];
    SECURITY_ATTRIBUTES security;
    SecureZeroMemory(&security, sizeof(security));
    security.nLength = sizeof(security);
    security.bInheritHandle = TRUE;
    if (!join_path(path, leaf)) return 0;
    *output = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, &security,
        CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    return *output != INVALID_HANDLE_VALUE && exact_final_path(*output, path);
}

static int launch_worker(const wchar_t *capability_path, const char *capability_sha,
    DWORD *child_exit, DWORD *failure_error) {
    static wchar_t isolated_environment[] =
        L"APPDATA=" V3R29_OUTPUT_PARENT L"\\outputs\0"
        L"LOCALAPPDATA=" V3R29_OUTPUT_PARENT L"\\outputs\0"
        L"PATH=C:\\Windows\\System32;C:\\Windows\0"
        L"PYTHONNOUSERSITE=1\0"
        L"PYTHONSAFEPATH=1\0"
        L"SystemRoot=C:\\Windows\0"
        L"TEMP=" V3R29_OUTPUT_PARENT L"\\outputs\0"
        L"TMP=" V3R29_OUTPUT_PARENT L"\\outputs\0"
        L"USERPROFILE=" V3R29_OUTPUT_PARENT L"\\outputs\0"
        L"WINDIR=C:\\Windows\0\0";
    wchar_t command[PATH_CHARS];
    STARTUPINFOEXW startup;
    PROCESS_INFORMATION process;
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits;
    SECURITY_ATTRIBUTES input_security;
    HANDLE job = NULL, stdin_file = INVALID_HANDLE_VALUE,
        stdout_file = INVALID_HANDLE_VALUE, stderr_file = INVALID_HANDLE_VALUE;
    HANDLE inherit_list[3];
    SIZE_T attribute_bytes = 0U;
    DWORD wait_result;
    int result = 0;
    SecureZeroMemory(&startup, sizeof(startup));
    SecureZeroMemory(&process, sizeof(process));
    SecureZeroMemory(&limits, sizeof(limits));
    SecureZeroMemory(&input_security, sizeof(input_security));
    startup.StartupInfo.cb = sizeof(startup);
    input_security.nLength = sizeof(input_security);
    input_security.bInheritHandle = TRUE;
    stdin_file = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        &input_security, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (stdin_file == INVALID_HANDLE_VALUE ||
        !create_inherited_log(L"outputs\\WORKER_STDOUT.txt", &stdout_file) ||
        !create_inherited_log(L"outputs\\WORKER_STDERR.txt", &stderr_file)) goto cleanup;
    startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
    startup.StartupInfo.hStdOutput = stdout_file;
    startup.StartupInfo.hStdError = stderr_file;
    startup.StartupInfo.hStdInput = stdin_file;
    inherit_list[0] = stdin_file;
    inherit_list[1] = stdout_file;
    inherit_list[2] = stderr_file;
    (void)InitializeProcThreadAttributeList(NULL, 1U, 0U, &attribute_bytes);
    if (attribute_bytes == 0U) goto cleanup;
    startup.lpAttributeList = (LPPROC_THREAD_ATTRIBUTE_LIST)HeapAlloc(
        GetProcessHeap(), HEAP_ZERO_MEMORY, attribute_bytes);
    if (startup.lpAttributeList == NULL ||
        !InitializeProcThreadAttributeList(startup.lpAttributeList, 1U, 0U, &attribute_bytes) ||
        !UpdateProcThreadAttribute(startup.lpAttributeList, 0U,
            PROC_THREAD_ATTRIBUTE_HANDLE_LIST, inherit_list, sizeof(inherit_list), NULL, NULL)) goto cleanup;
    if (swprintf_s(command, _countof(command),
        L"\"%s\" --background --factory-startup --disable-autoexec --python-exit-code 91 --python \"%s\" -- --capability \"%s\" --capability-sha256 %S",
        V3R29_BLENDER_PATH, V3R29_WORKER_PATH, capability_path, capability_sha) < 0) goto cleanup;
    job = CreateJobObjectW(NULL, NULL);
    if (job == NULL) goto cleanup;
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits,
            (DWORD)sizeof(limits)) ||
        !CreateProcessW(V3R29_BLENDER_PATH, command, NULL, NULL, TRUE,
            CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT |
                EXTENDED_STARTUPINFO_PRESENT,
            isolated_environment, L"C:\\Users\\robmc\\Kira",
            &startup.StartupInfo, &process) ||
        !AssignProcessToJobObject(job, process.hProcess) ||
        ResumeThread(process.hThread) == (DWORD)-1) goto cleanup;
    wait_result = WaitForSingleObject(process.hProcess, CHILD_TIMEOUT_MS);
    if (wait_result != WAIT_OBJECT_0) {
        TerminateJobObject(job, 90U);
        *failure_error = wait_result == WAIT_TIMEOUT ? ERROR_TIMEOUT : GetLastError();
        goto cleanup;
    }
    if (!GetExitCodeProcess(process.hProcess, child_exit) || *child_exit != 0U) goto cleanup;
    result = 1;
cleanup:
    if (!result && *failure_error == ERROR_SUCCESS) *failure_error = GetLastError();
    if (!result && process.hProcess != NULL) {
        (void)TerminateProcess(process.hProcess, 90U);
        (void)WaitForSingleObject(process.hProcess, 5000U);
    }
    if (process.hThread != NULL) CloseHandle(process.hThread);
    if (process.hProcess != NULL) CloseHandle(process.hProcess);
    if (job != NULL) CloseHandle(job);
    if (startup.lpAttributeList != NULL) {
        DeleteProcThreadAttributeList(startup.lpAttributeList);
        HeapFree(GetProcessHeap(), 0U, startup.lpAttributeList);
    }
    if (stdin_file != INVALID_HANDLE_VALUE) CloseHandle(stdin_file);
    if (stdout_file != INVALID_HANDLE_VALUE) { FlushFileBuffers(stdout_file); CloseHandle(stdout_file); }
    if (stderr_file != INVALID_HANDLE_VALUE) { FlushFileBuffers(stderr_file); CloseHandle(stderr_file); }
    SecureZeroMemory(command, sizeof(command));
    return result;
}

static int open_hash_output(const wchar_t *leaf, ULONGLONG minimum, ULONGLONG maximum,
    unsigned char digest[SHA_BYTES], ULONGLONG *bytes_out, HANDLE *handle_out) {
    wchar_t path[PATH_CHARS];
    FILE_ID_INFO identity;
    if (!join_path(path, leaf)) return 0;
    *handle_out = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (*handle_out == INVALID_HANDLE_VALUE ||
        !regular_nonreparse(*handle_out, bytes_out, &identity) ||
        *bytes_out < minimum || *bytes_out > maximum || !exact_final_path(*handle_out, path) ||
        !sha_handle(*handle_out, digest)) {
        if (*handle_out != INVALID_HANDLE_VALUE) CloseHandle(*handle_out);
        *handle_out = INVALID_HANDLE_VALUE;
        return 0;
    }
    return 1;
}

static int png_640(HANDLE file) {
    unsigned char header[24];
    LARGE_INTEGER zero;
    DWORD got = 0U;
    zero.QuadPart = 0;
    if (!SetFilePointerEx(file, zero, NULL, FILE_BEGIN) ||
        !ReadFile(file, header, (DWORD)sizeof(header), &got, NULL) || got != sizeof(header)) return 0;
    return memcmp(header, "\x89PNG\r\n\x1a\n", 8U) == 0 &&
        memcmp(header + 12U, "IHDR", 4U) == 0 &&
        header[16] == 0U && header[17] == 0U && header[18] == 2U && header[19] == 128U &&
        header[20] == 0U && header[21] == 0U && header[22] == 2U && header[23] == 128U;
}

static int file_contains_hashes(HANDLE file, const char hashes[][SHA_HEX + 1U], UINT count) {
    FILE_STANDARD_INFO standard;
    LARGE_INTEGER zero;
    unsigned char *data = NULL;
    DWORD got = 0U;
    UINT index;
    int ok = 0;
    zero.QuadPart = 0;
    if (!GetFileInformationByHandleEx(file, FileStandardInfo, &standard,
            (DWORD)sizeof(standard)) || standard.EndOfFile.QuadPart <= 0 ||
        standard.EndOfFile.QuadPart > MAX_SMALL_FILE ||
        !SetFilePointerEx(file, zero, NULL, FILE_BEGIN)) return 0;
    data = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        (SIZE_T)standard.EndOfFile.QuadPart + 1U);
    if (data == NULL || !ReadFile(file, data, (DWORD)standard.EndOfFile.QuadPart, &got, NULL) ||
        got != (DWORD)standard.EndOfFile.QuadPart) goto cleanup;
    if (strstr((const char *)data, "\"status\":\"WORKER_VALIDATED_AWAITING_NATIVE_FINALIZATION\"") == NULL ||
        strstr((const char *)data, "\"truth\":\"ISOLATED_NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_KIRA_BODY\"") == NULL) goto cleanup;
    for (index = 0U; index < count; ++index)
        if (strstr((const char *)data, hashes[index]) == NULL) goto cleanup;
    ok = 1;
cleanup:
    if (data != NULL) {
        SecureZeroMemory(data, (SIZE_T)standard.EndOfFile.QuadPart + 1U);
        HeapFree(GetProcessHeap(), 0U, data);
    }
    return ok;
}

static int file_equals_memory(HANDLE file, const unsigned char *expected, DWORD expected_bytes) {
    unsigned char *observed = NULL;
    LARGE_INTEGER zero;
    DWORD got = 0U;
    int ok = 0;
    zero.QuadPart = 0;
    observed = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        (SIZE_T)expected_bytes + 1U);
    if (observed == NULL || !SetFilePointerEx(file, zero, NULL, FILE_BEGIN) ||
        !ReadFile(file, observed, expected_bytes + 1U, &got, NULL) ||
        got != expected_bytes || memcmp(observed, expected, expected_bytes) != 0) goto cleanup;
    ok = 1;
cleanup:
    if (observed != NULL) {
        SecureZeroMemory(observed, (SIZE_T)expected_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, observed);
    }
    return ok;
}

static int write_memory_to_reserved(ReservedOutput *target,
    const unsigned char *data, DWORD bytes) {
    LARGE_INTEGER zero;
    FILE_ID_INFO identity;
    ULONGLONG observed_bytes = 0ULL;
    zero.QuadPart = 0;
    if (target == NULL || target->handle == INVALID_HANDLE_VALUE ||
        target->handle == NULL || !SetFilePointerEx(target->handle, zero, NULL, FILE_BEGIN) ||
        !SetEndOfFile(target->handle) || !write_all(target->handle, data, bytes) ||
        !FlushFileBuffers(target->handle) ||
        !regular_nonreparse(target->handle, &observed_bytes, &identity) ||
        observed_bytes != (ULONGLONG)bytes ||
        memcmp(&identity, &target->identity, sizeof(identity)) != 0 ||
        !exact_final_path(target->handle, target->path) ||
        !sha_handle(target->handle, target->digest)) return 0;
    target->bytes = observed_bytes;
    return 1;
}

static int copy_to_reserved(HANDLE source, ULONGLONG source_bytes,
    const unsigned char source_digest[SHA_BYTES], ReservedOutput *target) {
    unsigned char *buffer = NULL;
    LARGE_INTEGER zero;
    DWORD got = 0U;
    ULONGLONG total = 0ULL;
    int ok = 0;
    zero.QuadPart = 0;
    if (target == NULL || target->handle == INVALID_HANDLE_VALUE ||
        target->handle == NULL || !SetFilePointerEx(source, zero, NULL, FILE_BEGIN) ||
        !SetFilePointerEx(target->handle, zero, NULL, FILE_BEGIN) ||
        !SetEndOfFile(target->handle)) return 0;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), 0U, 1024U * 1024U);
    if (buffer == NULL) return 0;
    for (;;) {
        if (!ReadFile(source, buffer, 1024U * 1024U, &got, NULL)) goto cleanup;
        if (got == 0U) break;
        if (!write_all(target->handle, buffer, got)) goto cleanup;
        total += got;
        if (total > source_bytes) goto cleanup;
    }
    if (total != source_bytes || !FlushFileBuffers(target->handle) ||
        !sha_handle(target->handle, target->digest) ||
        memcmp(target->digest, source_digest, SHA_BYTES) != 0) goto cleanup;
    target->bytes = total;
    ok = 1;
cleanup:
    if (buffer != NULL) {
        SecureZeroMemory(buffer, 1024U * 1024U);
        HeapFree(GetProcessHeap(), 0U, buffer);
    }
    return ok;
}

static int revalidate_reserved_outputs(ReservedOutput outputs[FINAL_OUTPUT_COUNT],
    const unsigned char manifest_sha[SHA_BYTES]) {
    UINT index;
    FILE_ID_INFO identity;
    ULONGLONG bytes = 0ULL;
    unsigned char digest[SHA_BYTES];
    for (index = 0U; index < FINAL_OUTPUT_COUNT; ++index) {
        SecureZeroMemory(digest, sizeof(digest));
        if (outputs[index].handle == INVALID_HANDLE_VALUE || outputs[index].handle == NULL ||
            !regular_nonreparse(outputs[index].handle, &bytes, &identity) ||
            bytes != outputs[index].bytes ||
            memcmp(&identity, &outputs[index].identity, sizeof(identity)) != 0 ||
            !exact_final_path(outputs[index].handle, outputs[index].path) ||
            !sha_handle(outputs[index].handle, digest) ||
            memcmp(digest, outputs[index].digest, SHA_BYTES) != 0) {
            SecureZeroMemory(digest, sizeof(digest));
            return 0;
        }
    }
    SecureZeroMemory(digest, sizeof(digest));
    return memcmp(outputs[FINAL_OUTPUT_COUNT - 1U].digest, manifest_sha, SHA_BYTES) == 0;
}

static int finalize_outputs(const char *capability_sha,
    ReservedOutput final_outputs[FINAL_OUTPUT_COUNT],
    unsigned char manifest_sha[SHA_BYTES]) {
    static const wchar_t *staging_leaves[7] = {
        L"outputs\\worker_staging\\kira_v3r29_normalized_pelvic_core_reference_proxy.blend",
        L"outputs\\worker_staging\\front_clinical.png",
        L"outputs\\worker_staging\\right_clinical.png",
        L"outputs\\worker_staging\\iso_clinical.png",
        L"outputs\\worker_staging\\iso_xray.png",
        L"outputs\\worker_staging\\WORKER_RESULT.json",
        L"outputs\\worker_staging\\WORKER_RECEIPT.tsv"
    };
    HANDLE staging[7];
    ULONGLONG bytes[7];
    unsigned char digests[7][SHA_BYTES];
    char hashes[7][SHA_HEX + 1U];
    char manifest[4096], expected_receipt[4096];
    int manifest_bytes, receipt_bytes;
    UINT index, other;
    int ok = 0;
    for (index = 0U; index < 7U; ++index) staging[index] = INVALID_HANDLE_VALUE;
    if (!open_hash_output(staging_leaves[0], 4096ULL, 256ULL * 1024ULL * 1024ULL,
            digests[0], &bytes[0], &staging[0])) goto cleanup;
    for (index = 1U; index <= 4U; ++index)
        if (!open_hash_output(staging_leaves[index], 1024ULL, 64ULL * 1024ULL * 1024ULL,
                digests[index], &bytes[index], &staging[index]) || !png_640(staging[index]))
            goto cleanup;
    if (!open_hash_output(staging_leaves[5], 1024ULL, MAX_SMALL_FILE,
            digests[5], &bytes[5], &staging[5])) goto cleanup;
    if (!open_hash_output(staging_leaves[6], 512ULL, 8192ULL,
            digests[6], &bytes[6], &staging[6])) goto cleanup;
    for (index = 0U; index < 7U; ++index) digest_hex(digests[index], hashes[index]);
    for (index = 1U; index <= 4U; ++index)
        for (other = index + 1U; other <= 4U; ++other)
            if (memcmp(hashes[index], hashes[other], SHA_HEX) == 0) goto cleanup;
    if (!file_contains_hashes(staging[5], hashes, 5U)) goto cleanup;
    receipt_bytes = sprintf_s(expected_receipt, sizeof(expected_receipt),
        "schema\tkira.r25.medical_reference_proxy.v3r29.worker_receipt.v1\n"
        "status\tWORKER_VALIDATED_AWAITING_NATIVE_FINALIZATION\n"
        "truth\tISOLATED_NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_KIRA_BODY\n"
        "stage1_package_root\t%s\naudit_a_sha256\t%s\ncapability_sha256\t%s\n"
        "blend\t%llu\t%s\nfront_clinical\t%llu\t%s\nright_clinical\t%llu\t%s\n"
        "iso_clinical\t%llu\t%s\niso_xray\t%llu\t%s\nworker_result_json\t%llu\t%s\n"
        "proxy_objects\t9\nproxy_materials\t6\nlandmark_gates\t8\nrender_views\t4\n"
        "initial_reload_validated\ttrue\nfinal_snapshot_reload_validated\ttrue\n"
        "source_imported\tfalse\nexported\tfalse\nrig_weights_animation\tfalse\n"
        "live_avatar_activation_promotion\tfalse\n",
        V3R29_STAGE1_PACKAGE_ROOT, V3R29_AUDIT_A_SHA256, capability_sha,
        bytes[0], hashes[0], bytes[1], hashes[1], bytes[2], hashes[2],
        bytes[3], hashes[3], bytes[4], hashes[4], bytes[5], hashes[5]);
    if (receipt_bytes <= 0 || (size_t)receipt_bytes >= sizeof(expected_receipt) ||
        bytes[6] != (ULONGLONG)receipt_bytes ||
        !file_equals_memory(staging[6], (const unsigned char *)expected_receipt,
            (DWORD)receipt_bytes)) goto cleanup;
    for (index = 0U; index < 7U; ++index)
        if (!copy_to_reserved(staging[index], bytes[index], digests[index],
                &final_outputs[index])) goto cleanup;
    manifest_bytes = sprintf_s(manifest, sizeof(manifest),
        "path\tbytes\tsha256\n"
        "kira_v3r29_normalized_pelvic_core_reference_proxy.blend\t%llu\t%s\n"
        "front_clinical.png\t%llu\t%s\nright_clinical.png\t%llu\t%s\n"
        "iso_clinical.png\t%llu\t%s\niso_xray.png\t%llu\t%s\n"
        "WORKER_RESULT.json\t%llu\t%s\nWORKER_RECEIPT.tsv\t%llu\t%s\n",
        final_outputs[0].bytes, hashes[0], final_outputs[1].bytes, hashes[1],
        final_outputs[2].bytes, hashes[2], final_outputs[3].bytes, hashes[3],
        final_outputs[4].bytes, hashes[4], final_outputs[5].bytes, hashes[5],
        final_outputs[6].bytes, hashes[6]);
    if (manifest_bytes <= 0 || (size_t)manifest_bytes >= sizeof(manifest) ||
        !write_memory_to_reserved(&final_outputs[7],
            (const unsigned char *)manifest, (DWORD)manifest_bytes)) goto cleanup;
    memcpy(manifest_sha, final_outputs[7].digest, SHA_BYTES);
    ok = 1;
cleanup:
    for (index = 0U; index < 7U; ++index)
        if (staging[index] != INVALID_HANDLE_VALUE && staging[index] != NULL)
            CloseHandle(staging[index]);
    SecureZeroMemory(digests, sizeof(digests));
    SecureZeroMemory(hashes, sizeof(hashes));
    SecureZeroMemory(manifest, sizeof(manifest));
    SecureZeroMemory(expected_receipt, sizeof(expected_receipt));
    return ok;
}

int wmain(int argc, wchar_t **argv) {
    LockedBinding locked[MAX_BINDINGS];
    ReservedOutput *final_outputs = NULL;
    HANDLE self = INVALID_HANDLE_VALUE, parent = INVALID_HANDLE_VALUE,
        ledger = INVALID_HANDLE_VALUE, output_directory = INVALID_HANDLE_VALUE,
        staging_directory = INVALID_HANDLE_VALUE;
    unsigned char self_sha[SHA_BYTES], manifest_sha[SHA_BYTES], zero_sha[SHA_BYTES];
    wchar_t current[PATH_CHARS], capability_path[PATH_CHARS];
    char capability_sha[SHA_HEX + 1U];
    DWORD current_length, child_exit = STILL_ACTIVE, failure_error = ERROR_SUCCESS;
    uint32_t stage = 1U;
    int success = 0;
    UINT index;
    volatile int materialized = V3R29_MATERIALIZED;
    (void)argv;
    for (index = 0U; index < MAX_BINDINGS; ++index) locked[index].handle = INVALID_HANDLE_VALUE;
    SecureZeroMemory(self_sha, sizeof(self_sha));
    SecureZeroMemory(manifest_sha, sizeof(manifest_sha));
    SecureZeroMemory(zero_sha, sizeof(zero_sha));
    if (materialized == 0) {
        fwprintf(stderr, L"V3R29_UNMATERIALIZED_STATIC_TEMPLATE\n");
        return 70;
    }
    current_length = GetCurrentDirectoryW((DWORD)_countof(current), current);
    if (argc != 1 || current_length == 0U || current_length >= (DWORD)_countof(current) ||
        wcscmp(current, L"C:\\Users\\robmc\\Kira") != 0 ||
        !open_self(&self, self_sha) ||
        !open_output_parent(&parent)) return 71;
    final_outputs = (ReservedOutput *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        sizeof(ReservedOutput) * FINAL_OUTPUT_COUNT);
    if (final_outputs == NULL) goto cleanup;
    for (index = 0U; index < FINAL_OUTPUT_COUNT; ++index)
        final_outputs[index].handle = INVALID_HANDLE_VALUE;
    stage = 5U;
    ledger = create_ledger(self_sha);
    if (ledger == INVALID_HANDLE_VALUE || ledger == NULL) goto cleanup;
    stage = 10U;
    if (!verify_all_bindings(locked)) goto cleanup;
    stage = 20U;
    if (!create_exact_directory(L"outputs", &output_directory) ||
        !create_exact_directory(L"outputs\\worker_staging", &staging_directory) ||
        !reserve_final_outputs(final_outputs) ||
        !create_capability(capability_path, capability_sha)) goto cleanup;
    stage = 30U;
    if (!launch_worker(capability_path, capability_sha, &child_exit, &failure_error)) goto cleanup;
    stage = 40U;
    if (!finalize_outputs(capability_sha, final_outputs, manifest_sha)) goto cleanup;
    stage = 90U;
    if (!ledger_update(ledger, LEDGER_SUCCESS_CONSUMED, stage, ERROR_SUCCESS,
            child_exit, self_sha, manifest_sha)) goto cleanup;
    stage = 95U;
    if (!revalidate_reserved_outputs(final_outputs, manifest_sha)) goto cleanup;
    success = 1;
cleanup:
    if (!success && ledger != INVALID_HANDLE_VALUE && ledger != NULL)
        (void)ledger_update(ledger, LEDGER_FAILURE_CONSUMED, stage,
            failure_error == ERROR_SUCCESS ? GetLastError() : failure_error,
            child_exit, self_sha, zero_sha);
    if (final_outputs != NULL) {
        close_reserved_outputs(final_outputs);
        HeapFree(GetProcessHeap(), 0U, final_outputs);
        final_outputs = NULL;
    }
    if (staging_directory != INVALID_HANDLE_VALUE && staging_directory != NULL)
        CloseHandle(staging_directory);
    if (output_directory != INVALID_HANDLE_VALUE && output_directory != NULL)
        CloseHandle(output_directory);
    if (ledger != INVALID_HANDLE_VALUE && ledger != NULL) CloseHandle(ledger);
    if (parent != INVALID_HANDLE_VALUE && parent != NULL) CloseHandle(parent);
    close_bindings(locked, V3R29_BINDING_COUNT <= MAX_BINDINGS ? V3R29_BINDING_COUNT : 0U);
    if (self != INVALID_HANDLE_VALUE && self != NULL) CloseHandle(self);
    SecureZeroMemory(self_sha, sizeof(self_sha));
    SecureZeroMemory(manifest_sha, sizeof(manifest_sha));
    SecureZeroMemory(zero_sha, sizeof(zero_sha));
    SecureZeroMemory(capability_sha, sizeof(capability_sha));
    return success ? 0 : 1;
}
