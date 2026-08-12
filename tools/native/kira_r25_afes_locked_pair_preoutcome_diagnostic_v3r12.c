/*
 * Kira R25 AFES locked-pair v3r12 native pre-outcome diagnostic.
 *
 * STATIC/AUDIT BOUNDARY: compiling and inspecting this file is permitted.
 * The PE must not be invoked until a different fresh exact-byte auditor has
 * produced the canonical accepted audit described below.  It never executes
 * v3r9, a controller, bootstrap, wrapper, AFES extractor, or Blender.  Its
 * only child is one suspended copy of its own exact image.  The child verifies
 * the frozen v3r9 retained graph read-only, probes the old receipt parent's
 * FILE_ADD_FILE access without creating the receipt, inspects the retained
 * Python DLL strictly as read-only PE bytes without loading any DLL or calling
 * any Python API, and exits at an explicit pre-outcome stop.
 *
 * Build (x64 Native Tools command prompt):
 *   cl.exe /nologo /W4 /WX /O2 /MT /guard:cf /DUNICODE /D_UNICODE /std:c17 \
 *     tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.c \
 *     /Fo:tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.obj \
 *     /Fe:tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.exe \
 *     /link /guard:cf /WX bcrypt.lib
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <errno.h>

#include "kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12_identity_anchor.h"

#pragma comment(lib, "bcrypt.lib")

#define MAX_SUBJECT_BYTES (2U * 1024U * 1024U)
#define MAX_MANIFEST_ROWS 256U
#define MAX_CAPTURE_BYTES 4096U
#define CHILD_WAIT_MILLISECONDS 30000U
#define CHILD_PRE_OUTCOME_STOP_EXIT 41U
#define V3R9_LAUNCHER_SHA256 \
    "2aec90c36e3150c258f6089fd1ba3f9e5c336ca0b69d8d1a4d826bc6a8764760"
#define CAPABILITY_VERSION 1U
#define CAPABILITY_MAGIC "KIRA_R25_V3R12_OBSERVER_CAPABILITY"

static const wchar_t *const SELF_RELATIVE =
    L"tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.exe";
static const wchar_t *const CONTRACT_RELATIVE =
    L"Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r12.json";
static const wchar_t *const SOURCE_RELATIVE =
    L"tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12.c";
static const wchar_t *const IDENTITY_ANCHOR_RELATIVE =
    L"tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12_identity_anchor.h";
static const wchar_t *const STATIC_TEST_RELATIVE =
    L"Testing\\test_kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r12_static.ps1";
static const wchar_t *const CONTROL_CHECKPOINT_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t *const V3R10_REJECTION_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r10_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t *const MANIFEST_RELATIVE =
    L"RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9\\RETAINED_NATIVE_LOCK_MANIFEST.tsv";
static const wchar_t *const POSTMORTEM_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r9_consumed_run_static_postmortem\\attempt_01\\CHECKPOINT.md";
static const wchar_t *const AUDIT_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r12_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t *const AUDIT_DIGEST_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r12_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t *const EVIDENCE_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r12_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t *const OUTCOME_RECEIPT_RELATIVE =
    L"RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9\\EXECUTION_OUTCOME.receipt.bin";
static const wchar_t *const OUTCOME_PARENT_RELATIVE =
    L"RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9";

typedef struct LockedSubject {
    HANDLE handle;
    wchar_t *path;
    uint64_t bytes;
    unsigned char sha256[32];
} LockedSubject;

typedef struct ManifestRow {
    char label[129];
    wchar_t *path;
    uint64_t expected_bytes;
    unsigned char expected_sha256[32];
    HANDLE handle;
} ManifestRow;

typedef struct ParsedArguments {
    int child_mode;
    uintptr_t evidence_handle_value;
    uintptr_t capability_handle_value;
    uintptr_t parent_process_handle_value;
} ParsedArguments;

typedef struct AuthorityState {
    LockedSubject self;
    LockedSubject contract;
    LockedSubject source;
    LockedSubject identity_anchor;
    LockedSubject static_test;
    LockedSubject control_checkpoint;
    LockedSubject v3r10_rejection;
    LockedSubject manifest;
    LockedSubject postmortem;
    LockedSubject audit;
    LockedSubject audit_digest;
    char self_sha256[65];
} AuthorityState;

typedef struct CapabilityRecord {
    char magic[40];
    uint32_t version;
    uint32_t record_bytes;
    uint64_t parent_pid;
    FILETIME parent_creation;
    uint64_t child_pid;
    FILETIME child_creation;
    uint64_t evidence_volume_serial;
    FILE_ID_128 evidence_file_id;
    unsigned char nonce[32];
    unsigned char binding_sha256[32];
} CapabilityRecord;

static HANDLE g_evidence = INVALID_HANDLE_VALUE;
static int g_evidence_failed = 0;

static void secure_zero(void *value, size_t size) {
    if (value != NULL && size != 0U) {
        SecureZeroMemory(value, size);
    }
}

static int is_lower_hex64(const char *value) {
    size_t index;
    if (value == NULL || strlen(value) != 64U) {
        return 0;
    }
    for (index = 0U; index < 64U; ++index) {
        char ch = value[index];
        if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'))) {
            return 0;
        }
    }
    return 1;
}

static int safe_identifier(const char *value) {
    size_t index;
    size_t length = value != NULL ? strlen(value) : 0U;
    if (length < 3U || length > 64U) {
        return 0;
    }
    for (index = 0U; index < length; ++index) {
        char ch = value[index];
        if (!((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') ||
              ch == '_')) {
            return 0;
        }
    }
    return 1;
}

static int hex_nibble(char value) {
    if (value >= '0' && value <= '9') {
        return value - '0';
    }
    if (value >= 'a' && value <= 'f') {
        return value - 'a' + 10;
    }
    return -1;
}

static int parse_hex64(const char *value, unsigned char output[32]) {
    size_t index;
    if (!is_lower_hex64(value)) {
        return 0;
    }
    for (index = 0U; index < 32U; ++index) {
        int high = hex_nibble(value[index * 2U]);
        int low = hex_nibble(value[index * 2U + 1U]);
        output[index] = (unsigned char)((high << 4) | low);
    }
    return 1;
}

static void hex_encode32(const unsigned char input[32], char output[65]) {
    static const char digits[] = "0123456789abcdef";
    size_t index;
    for (index = 0U; index < 32U; ++index) {
        output[index * 2U] = digits[input[index] >> 4U];
        output[index * 2U + 1U] = digits[input[index] & 0x0fU];
    }
    output[64] = '\0';
}

static int same_hash(const unsigned char first[32], const unsigned char second[32]) {
    unsigned char difference = 0U;
    size_t index;
    for (index = 0U; index < 32U; ++index) {
        difference |= (unsigned char)(first[index] ^ second[index]);
    }
    return difference == 0U;
}

static wchar_t *duplicate_wide(const wchar_t *value) {
    size_t length;
    wchar_t *copy;
    if (value == NULL) {
        return NULL;
    }
    length = wcslen(value);
    if (length >= 32767U) {
        return NULL;
    }
    copy = (wchar_t *)calloc(length + 1U, sizeof(wchar_t));
    if (copy != NULL) {
        memcpy(copy, value, (length + 1U) * sizeof(wchar_t));
    }
    return copy;
}

static wchar_t *canonical_full_path(const wchar_t *input) {
    DWORD required;
    DWORD written;
    wchar_t *result;
    if (input == NULL || input[0] == L'\0' || wcsncmp(input, L"\\\\", 2U) == 0) {
        return NULL;
    }
    required = GetFullPathNameW(input, 0U, NULL, NULL);
    if (required == 0U || required >= 32767U) {
        return NULL;
    }
    result = (wchar_t *)calloc((size_t)required + 1U, sizeof(wchar_t));
    if (result == NULL) {
        return NULL;
    }
    written = GetFullPathNameW(input, required + 1U, result, NULL);
    if (written == 0U || written > required || wcsncmp(result, L"\\\\", 2U) == 0) {
        free(result);
        return NULL;
    }
    return result;
}

static wchar_t *path_from_root(const wchar_t *root, const wchar_t *relative) {
    size_t root_length;
    size_t relative_length;
    wchar_t *joined;
    wchar_t *canonical;
    if (root == NULL || relative == NULL) {
        return NULL;
    }
    root_length = wcslen(root);
    relative_length = wcslen(relative);
    if (root_length + relative_length + 2U >= 32767U) {
        return NULL;
    }
    joined = (wchar_t *)calloc(root_length + relative_length + 2U, sizeof(wchar_t));
    if (joined == NULL) {
        return NULL;
    }
    memcpy(joined, root, root_length * sizeof(wchar_t));
    if (root_length != 0U && root[root_length - 1U] != L'\\') {
        joined[root_length++] = L'\\';
    }
    memcpy(joined + root_length, relative, (relative_length + 1U) * sizeof(wchar_t));
    canonical = canonical_full_path(joined);
    free(joined);
    return canonical;
}

static wchar_t *module_path(void) {
    DWORD capacity = 512U;
    while (capacity < 32768U) {
        wchar_t *buffer = (wchar_t *)calloc(capacity, sizeof(wchar_t));
        DWORD length;
        if (buffer == NULL) {
            return NULL;
        }
        SetLastError(ERROR_SUCCESS);
        length = GetModuleFileNameW(NULL, buffer, capacity);
        if (length != 0U && length < capacity - 1U) {
            wchar_t *canonical = canonical_full_path(buffer);
            free(buffer);
            return canonical;
        }
        free(buffer);
        capacity *= 2U;
    }
    return NULL;
}

static int derive_project_root(wchar_t **self_out, wchar_t **root_out) {
    wchar_t *self = module_path();
    size_t self_length;
    size_t suffix_length = wcslen(SELF_RELATIVE);
    wchar_t *root;
    if (self == NULL) {
        return 0;
    }
    self_length = wcslen(self);
    if (self_length <= suffix_length + 1U ||
        self[self_length - suffix_length - 1U] != L'\\' ||
        _wcsicmp(self + self_length - suffix_length, SELF_RELATIVE) != 0) {
        free(self);
        return 0;
    }
    root = (wchar_t *)calloc(self_length - suffix_length, sizeof(wchar_t));
    if (root == NULL) {
        free(self);
        return 0;
    }
    memcpy(root, self, (self_length - suffix_length - 1U) * sizeof(wchar_t));
    root[self_length - suffix_length - 1U] = L'\0';
    *self_out = self;
    *root_out = root;
    return 1;
}

static int final_path_matches(HANDLE handle, const wchar_t *canonical_path) {
    DWORD required = GetFinalPathNameByHandleW(handle, NULL, 0U, FILE_NAME_NORMALIZED);
    wchar_t *actual;
    wchar_t *expected;
    size_t length;
    int match;
    if (required == 0U || required >= 32767U) {
        return 0;
    }
    actual = (wchar_t *)calloc((size_t)required + 1U, sizeof(wchar_t));
    length = wcslen(canonical_path);
    expected = (wchar_t *)calloc(length + 5U, sizeof(wchar_t));
    if (actual == NULL || expected == NULL) {
        free(actual);
        free(expected);
        return 0;
    }
    if (GetFinalPathNameByHandleW(
            handle, actual, required + 1U, FILE_NAME_NORMALIZED) == 0U) {
        free(actual);
        free(expected);
        return 0;
    }
    memcpy(expected, L"\\\\?\\", 4U * sizeof(wchar_t));
    memcpy(expected + 4U, canonical_path, (length + 1U) * sizeof(wchar_t));
    match = _wcsicmp(actual, expected) == 0;
    free(actual);
    free(expected);
    return match;
}

static int sha256_handle(HANDLE handle, unsigned char output[32], uint64_t *bytes_out) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char buffer[65536];
    LARGE_INTEGER zero;
    DWORD read_count;
    uint64_t total = 0U;
    NTSTATUS status;
    int result = 0;
    zero.QuadPart = 0;
    if (!SetFilePointerEx(handle, zero, NULL, FILE_BEGIN)) {
        return 0;
    }
    status = BCryptOpenAlgorithmProvider(
        &algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) {
        return 0;
    }
    status = BCryptCreateHash(algorithm, &hash, NULL, 0U, NULL, 0U, 0U);
    if (status < 0) {
        goto cleanup;
    }
    for (;;) {
        if (!ReadFile(handle, buffer, sizeof(buffer), &read_count, NULL)) {
            goto cleanup;
        }
        if (read_count == 0U) {
            break;
        }
        total += read_count;
        status = BCryptHashData(hash, buffer, read_count, 0U);
        if (status < 0) {
            goto cleanup;
        }
    }
    status = BCryptFinishHash(hash, output, 32U, 0U);
    if (status < 0) {
        goto cleanup;
    }
    *bytes_out = total;
    result = 1;
cleanup:
    secure_zero(buffer, sizeof(buffer));
    if (hash != NULL) {
        BCryptDestroyHash(hash);
    }
    if (algorithm != NULL) {
        BCryptCloseAlgorithmProvider(algorithm, 0U);
    }
    return result;
}

static int sha256_bytes(
    const void *input, size_t input_size, unsigned char output[32]
) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    NTSTATUS status;
    int result = 0;
    if (input == NULL || input_size > ULONG_MAX) return 0;
    status = BCryptOpenAlgorithmProvider(
        &algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) return 0;
    status = BCryptCreateHash(algorithm, &hash, NULL, 0U, NULL, 0U, 0U);
    if (status < 0) goto cleanup;
    status = BCryptHashData(
        hash, (PUCHAR)(uintptr_t)input, (ULONG)input_size, 0U);
    if (status < 0) goto cleanup;
    status = BCryptFinishHash(hash, output, 32U, 0U);
    if (status < 0) goto cleanup;
    result = 1;
cleanup:
    if (hash != NULL) BCryptDestroyHash(hash);
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
    return result;
}

static void close_subject(LockedSubject *subject) {
    if (subject->handle != NULL && subject->handle != INVALID_HANDLE_VALUE) {
        CloseHandle(subject->handle);
    }
    free(subject->path);
    secure_zero(subject, sizeof(*subject));
    subject->handle = INVALID_HANDLE_VALUE;
}

static int open_locked_subject(
    const wchar_t *path, const char *expected_sha256, uint64_t expected_bytes,
    LockedSubject *subject
) {
    FILE_ATTRIBUTE_TAG_INFO tag;
    unsigned char expected[32];
    memset(subject, 0, sizeof(*subject));
    subject->handle = INVALID_HANDLE_VALUE;
    subject->path = canonical_full_path(path);
    if (subject->path == NULL ||
        (expected_sha256 != NULL && !parse_hex64(expected_sha256, expected))) {
        close_subject(subject);
        return 0;
    }
    subject->handle = CreateFileW(
        subject->path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT |
            FILE_FLAG_SEQUENTIAL_SCAN,
        NULL);
    if (subject->handle == INVALID_HANDLE_VALUE ||
        !GetFileInformationByHandleEx(
            subject->handle, FileAttributeTagInfo, &tag, sizeof(tag)) ||
        (tag.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U ||
        !final_path_matches(subject->handle, subject->path) ||
        !sha256_handle(subject->handle, subject->sha256, &subject->bytes) ||
        (expected_sha256 != NULL && !same_hash(subject->sha256, expected)) ||
        (expected_bytes != UINT64_MAX && subject->bytes != expected_bytes)) {
        secure_zero(expected, sizeof(expected));
        close_subject(subject);
        return 0;
    }
    secure_zero(expected, sizeof(expected));
    return 1;
}

static int read_handle_all(
    HANDLE handle, uint64_t expected_bytes, unsigned char **data_out,
    size_t *size_out
) {
    unsigned char *data;
    LARGE_INTEGER zero;
    DWORD read_count;
    size_t offset = 0U;
    if (expected_bytes > MAX_SUBJECT_BYTES || expected_bytes > SIZE_MAX - 1U) {
        return 0;
    }
    data = (unsigned char *)calloc((size_t)expected_bytes + 1U, 1U);
    if (data == NULL) {
        return 0;
    }
    zero.QuadPart = 0;
    if (!SetFilePointerEx(handle, zero, NULL, FILE_BEGIN)) {
        free(data);
        return 0;
    }
    while (offset < (size_t)expected_bytes) {
        DWORD request = (DWORD)((size_t)expected_bytes - offset);
        if (!ReadFile(handle, data + offset, request, &read_count, NULL) ||
            read_count == 0U) {
            free(data);
            return 0;
        }
        offset += read_count;
    }
    *data_out = data;
    *size_out = offset;
    return 1;
}

/* Accept exactly one canonical newline style per file. A structural CR is
 * accepted only immediately before LF and is removed with that LF. Bare CR,
 * mixed LF/CRLF, missing final LF, embedded NUL, and hidden magic/header
 * whitespace remain failures. */
static int next_canonical_line(
    char **cursor_io, char *end, int *newline_style_io, char **line_out
) {
    char *cursor = *cursor_io;
    char *newline;
    char *scan;
    int style;
    if (cursor >= end) return 0;
    newline = (char *)memchr(cursor, '\n', (size_t)(end - cursor));
    if (newline == NULL) return -1;
    style = newline > cursor && newline[-1] == '\r' ? 2 : 1;
    for (scan = cursor; scan < newline - (style == 2 ? 1 : 0); ++scan) {
        if (*scan == '\r' || *scan == '\0') return -1;
    }
    if (*newline_style_io == 0) {
        *newline_style_io = style;
    } else if (*newline_style_io != style) {
        return -1;
    }
    if (style == 2) newline[-1] = '\0';
    *newline = '\0';
    *line_out = cursor;
    *cursor_io = newline + 1;
    return 1;
}

static int write_record(const char *actor, const char *stage,
                        const char *status, const char *detail) {
    char line[12288];
    int length;
    DWORD written;
    LARGE_INTEGER zero;
    if (g_evidence == INVALID_HANDLE_VALUE || g_evidence_failed) {
        return 0;
    }
    length = _snprintf_s(
        line, sizeof(line), _TRUNCATE,
        "{\"schema\":\"kira.r25.afes.v3r12.native_stage.v1\"," 
        "\"actor\":\"%s\",\"stage\":\"%s\",\"status\":\"%s\","
        "\"detail\":\"%s\"}\n",
        actor, stage, status, detail != NULL ? detail : "none");
    zero.QuadPart = 0;
    if (length <= 0 || !SetFilePointerEx(g_evidence, zero, NULL, FILE_END) ||
        !WriteFile(g_evidence, line, (DWORD)length, &written, NULL) ||
        written != (DWORD)length || !FlushFileBuffers(g_evidence)) {
        g_evidence_failed = 1;
        return 0;
    }
    return 1;
}

static int reserve_evidence(const wchar_t *project_root) {
    wchar_t *path = path_from_root(project_root, EVIDENCE_RELATIVE);
    SECURITY_ATTRIBUTES security;
    if (path == NULL) {
        return 0;
    }
    memset(&security, 0, sizeof(security));
    security.nLength = sizeof(security);
    security.bInheritHandle = TRUE;
    g_evidence = CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, &security,
        CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
    free(path);
    return g_evidence != INVALID_HANDLE_VALUE;
}

static int copy_ascii_wide(const wchar_t *input, char *output, size_t capacity) {
    size_t index;
    size_t length = input != NULL ? wcslen(input) : 0U;
    if (input == NULL || length + 1U > capacity) {
        return 0;
    }
    for (index = 0U; index < length; ++index) {
        if (input[index] < 0x21 || input[index] > 0x7e) {
            return 0;
        }
        output[index] = (char)input[index];
    }
    output[length] = '\0';
    return 1;
}

static int parse_handle_value(const wchar_t *value, uintptr_t *result) {
    wchar_t *end = NULL;
    unsigned long long parsed;
    if (value == NULL || value[0] == L'\0' || value[0] == L'-') {
        return 0;
    }
    errno = 0;
    parsed = wcstoull(value, &end, 10);
    if (errno != 0 || end == value || *end != L'\0' ||
        parsed > (unsigned long long)UINTPTR_MAX) {
        return 0;
    }
    *result = (uintptr_t)parsed;
    return 1;
}

static int parse_arguments(
    int argc, wchar_t **argv, int child_expected, ParsedArguments *parsed,
    char *error, size_t error_size
) {
    int index;
    unsigned seen = 0U;
    memset(parsed, 0, sizeof(*parsed));
    if (!child_expected) {
        if (argc != 1) {
            _snprintf_s(error, error_size, _TRUNCATE,
                        "observer_accepts_no_arguments");
            return 0;
        }
        return 1;
    }
    for (index = 1; index < argc; ++index) {
        const wchar_t *option = argv[index];
        const wchar_t *value;
        unsigned bit;
        if (index + 1 >= argc) {
            _snprintf_s(error, error_size, _TRUNCATE, "option_missing_value");
            return 0;
        }
        value = argv[++index];
        if (wcscmp(option, L"--v3r12-child") == 0) {
            bit = 1U << 0;
            if (wcscmp(value, L"observer-owned") != 0) return 0;
            parsed->child_mode = 1;
        } else if (wcscmp(option, L"--evidence-handle") == 0) {
            bit = 1U << 1;
            if (!parse_handle_value(value, &parsed->evidence_handle_value)) return 0;
        } else if (wcscmp(option, L"--capability-read-handle") == 0) {
            bit = 1U << 2;
            if (!parse_handle_value(value, &parsed->capability_handle_value)) return 0;
        } else if (wcscmp(option, L"--parent-process-handle") == 0) {
            bit = 1U << 3;
            if (!parse_handle_value(value, &parsed->parent_process_handle_value)) return 0;
        } else {
            _snprintf_s(error, error_size, _TRUNCATE, "unknown_option");
            return 0;
        }
        if ((seen & bit) != 0U) {
            _snprintf_s(error, error_size, _TRUNCATE, "duplicate_option");
            return 0;
        }
        seen |= bit;
    }
    if (seen != 0x0fU || !parsed->child_mode ||
        parsed->evidence_handle_value == 0U ||
        parsed->capability_handle_value == 0U ||
        parsed->parent_process_handle_value == 0U) {
        _snprintf_s(error, error_size, _TRUNCATE, "argument_contract_invalid");
        return 0;
    }
    return 1;
}

static int exact_expected_path(
    const wchar_t *root, const wchar_t *provided, const wchar_t *relative
) {
    wchar_t *expected = path_from_root(root, relative);
    wchar_t *actual = canonical_full_path(provided);
    int match = expected != NULL && actual != NULL && _wcsicmp(expected, actual) == 0;
    free(expected);
    free(actual);
    return match;
}

static void close_authority(AuthorityState *state) {
    close_subject(&state->audit_digest);
    close_subject(&state->audit);
    close_subject(&state->postmortem);
    close_subject(&state->manifest);
    close_subject(&state->v3r10_rejection);
    close_subject(&state->control_checkpoint);
    close_subject(&state->static_test);
    close_subject(&state->identity_anchor);
    close_subject(&state->source);
    close_subject(&state->contract);
    close_subject(&state->self);
    secure_zero(state, sizeof(*state));
}

static int verify_audit_digest(
    LockedSubject *audit, LockedSubject *digest_subject,
    char *error, size_t error_size
) {
    unsigned char *data = NULL;
    size_t size = 0U;
    char actual[65];
    char expected[73];
    int result = 0;
    hex_encode32(audit->sha256, actual);
    _snprintf_s(expected, sizeof(expected), _TRUNCATE,
                "sha256\t%s\n", actual);
    if (!read_handle_all(digest_subject->handle, digest_subject->bytes,
                         &data, &size) ||
        size != strlen(expected) || memcmp(data, expected, size) != 0) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "audit_digest_sidecar_mismatch");
        goto cleanup;
    }
    result = 1;
cleanup:
    secure_zero(actual, sizeof(actual));
    secure_zero(expected, sizeof(expected));
    if (data != NULL) {
        secure_zero(data, size);
        free(data);
    }
    return result;
}

static int parse_exact_audit(
    AuthorityState *state, char *error, size_t error_size
) {
    static const char *const keys[] = {
        "decision", "auditor_boundary", "auditor_id",
        "native_executable_sha256", "identity_anchor_sha256",
        "contract_sha256", "native_source_sha256", "static_test_sha256",
        "runtime_control_checkpoint_sha256",
        "v3r10_rejection_checkpoint_sha256",
        "retained_manifest_sha256", "v3r9_postmortem_sha256"
    };
    unsigned char *data = NULL;
    size_t size = 0U;
    char *cursor;
    char *end;
    const char *values[12];
    size_t row = 0U;
    int newline_style = 0;
    char anchor_hash[65];
    int result = 0;
    if (!read_handle_all(state->audit.handle, state->audit.bytes, &data, &size) ||
        size == 0U || data[size - 1U] != '\n' ||
        memchr(data, '\0', size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE, "audit_read_or_encoding_failed");
        goto cleanup;
    }
    hex_encode32(state->identity_anchor.sha256, anchor_hash);
    cursor = (char *)data;
    end = cursor + size;
    while (cursor < end) {
        char *line = NULL;
        char *tab;
        int line_result = next_canonical_line(
            &cursor, end, &newline_style, &line);
        if (line_result != 1 || newline_style != 1) {
            _snprintf_s(error, error_size, _TRUNCATE,
                        "audit_noncanonical_lf_or_line_unterminated");
            goto cleanup;
        }
        if (row == 0U) {
            if (strcmp(line,
                    "KIRA_R25_AFES_PREOUTCOME_DIAGNOSTIC_AUDIT_V3R12\t1") != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_magic_invalid");
                goto cleanup;
            }
        } else {
            if (row > 12U) {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_extra_row");
                goto cleanup;
            }
            tab = strchr(line, '\t');
            if (tab == NULL || strchr(tab + 1, '\t') != NULL) {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_row_shape_invalid");
                goto cleanup;
            }
            *tab = '\0';
            if (strcmp(line, keys[row - 1U]) != 0 || tab[1] == '\0') {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_key_order_invalid");
                goto cleanup;
            }
            values[row - 1U] = tab + 1;
        }
        ++row;
    }
    if (row != 13U ||
        strcmp(values[0], "ACCEPTED_FOR_ONE_BOUNDED_NATIVE_DIAGNOSTIC_ONLY") != 0 ||
        strcmp(values[1], "different_fresh_exact_byte_static_auditor") != 0 ||
        !safe_identifier(values[2]) || strcmp(values[2], V3R12_AUTHOR_ID) == 0 ||
        strcmp(values[3], state->self_sha256) != 0 ||
        strcmp(values[4], anchor_hash) != 0 ||
        strcmp(values[5], V3R12_CONTRACT_SHA256) != 0 ||
        strcmp(values[6], V3R12_SOURCE_SHA256) != 0 ||
        strcmp(values[7], V3R12_STATIC_TEST_SHA256) != 0 ||
        strcmp(values[8], V3R12_CONTROL_CHECKPOINT_SHA256) != 0 ||
        strcmp(values[9], V3R12_V3R10_REJECTION_SHA256) != 0 ||
        strcmp(values[10], V3R12_MANIFEST_SHA256) != 0 ||
        strcmp(values[11], V3R12_POSTMORTEM_SHA256) != 0) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "audit_decision_boundary_or_subject_invalid");
        goto cleanup;
    }
    result = 1;
cleanup:
    secure_zero(anchor_hash, sizeof(anchor_hash));
    if (data != NULL) {
        secure_zero(data, size);
        free(data);
    }
    return result;
}

static int open_fixed_subject(
    const wchar_t *root, const wchar_t *relative, const char *expected_sha256,
    uint64_t expected_bytes, LockedSubject *subject
) {
    wchar_t *path = path_from_root(root, relative);
    int result = path != NULL && open_locked_subject(
        path, expected_sha256, expected_bytes, subject);
    free(path);
    return result;
}

static int initialize_authority(
    const wchar_t *derived_root, const wchar_t *self_path, AuthorityState *state,
    char *error, size_t error_size
) {
    memset(state, 0, sizeof(*state));
    state->self.handle = INVALID_HANDLE_VALUE;
    state->contract.handle = INVALID_HANDLE_VALUE;
    state->source.handle = INVALID_HANDLE_VALUE;
    state->identity_anchor.handle = INVALID_HANDLE_VALUE;
    state->static_test.handle = INVALID_HANDLE_VALUE;
    state->control_checkpoint.handle = INVALID_HANDLE_VALUE;
    state->v3r10_rejection.handle = INVALID_HANDLE_VALUE;
    state->manifest.handle = INVALID_HANDLE_VALUE;
    state->postmortem.handle = INVALID_HANDLE_VALUE;
    state->audit.handle = INVALID_HANDLE_VALUE;
    state->audit_digest.handle = INVALID_HANDLE_VALUE;
    if (!open_locked_subject(self_path, NULL, UINT64_MAX, &state->self)) {
        _snprintf_s(error, error_size, _TRUNCATE, "self_image_lock_or_hash_failed");
        goto failure;
    }
    hex_encode32(state->self.sha256, state->self_sha256);
    if (!open_fixed_subject(derived_root, CONTRACT_RELATIVE,
                            V3R12_CONTRACT_SHA256, V3R12_CONTRACT_BYTES,
                            &state->contract)) {
        _snprintf_s(error, error_size, _TRUNCATE, "contract_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(derived_root, SOURCE_RELATIVE,
                            V3R12_SOURCE_SHA256, V3R12_SOURCE_BYTES,
                            &state->source)) {
        _snprintf_s(error, error_size, _TRUNCATE, "source_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(derived_root, IDENTITY_ANCHOR_RELATIVE, NULL,
                            UINT64_MAX, &state->identity_anchor)) {
        _snprintf_s(error, error_size, _TRUNCATE, "identity_anchor_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(derived_root, STATIC_TEST_RELATIVE,
                            V3R12_STATIC_TEST_SHA256, V3R12_STATIC_TEST_BYTES,
                            &state->static_test)) {
        _snprintf_s(error, error_size, _TRUNCATE, "static_test_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(
            derived_root, CONTROL_CHECKPOINT_RELATIVE,
            V3R12_CONTROL_CHECKPOINT_SHA256,
            V3R12_CONTROL_CHECKPOINT_BYTES, &state->control_checkpoint)) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "control_checkpoint_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(
            derived_root, V3R10_REJECTION_RELATIVE,
            V3R12_V3R10_REJECTION_SHA256,
            V3R12_V3R10_REJECTION_BYTES, &state->v3r10_rejection)) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "v3r10_rejection_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(derived_root, MANIFEST_RELATIVE,
                            V3R12_MANIFEST_SHA256, V3R12_MANIFEST_BYTES,
                            &state->manifest)) {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(derived_root, POSTMORTEM_RELATIVE,
                            V3R12_POSTMORTEM_SHA256,
                            V3R12_POSTMORTEM_BYTES, &state->postmortem)) {
        _snprintf_s(error, error_size, _TRUNCATE, "postmortem_lock_or_hash_failed");
        goto failure;
    }
    if (!open_fixed_subject(derived_root, AUDIT_RELATIVE, NULL,
                            UINT64_MAX, &state->audit) ||
        !open_fixed_subject(derived_root, AUDIT_DIGEST_RELATIVE, NULL,
                            UINT64_MAX, &state->audit_digest) ||
        !verify_audit_digest(&state->audit, &state->audit_digest,
                             error, error_size) ||
        !parse_exact_audit(state, error, error_size)) {
        if (error[0] == '\0') {
            _snprintf_s(error, error_size, _TRUNCATE, "audit_lock_or_hash_failed");
        }
        goto failure;
    }
    return 1;
failure:
    close_authority(state);
    return 0;
}

static wchar_t *utf8_to_wide(const char *value) {
    int required;
    wchar_t *result;
    if (value == NULL || value[0] == '\0') {
        return NULL;
    }
    required = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value, -1,
                                   NULL, 0);
    if (required <= 0 || required >= 32767) {
        return NULL;
    }
    result = (wchar_t *)calloc((size_t)required, sizeof(wchar_t));
    if (result == NULL || MultiByteToWideChar(
            CP_UTF8, MB_ERR_INVALID_CHARS, value, -1, result, required) != required) {
        free(result);
        return NULL;
    }
    return result;
}

static int is_absolute_manifest_path(const wchar_t *path) {
    return path != NULL &&
        ((path[0] >= L'A' && path[0] <= L'Z') ||
         (path[0] >= L'a' && path[0] <= L'z')) &&
        path[1] == L':' && (path[2] == L'\\' || path[2] == L'/');
}

static int path_under_root(const wchar_t *path, const wchar_t *root) {
    size_t length = wcslen(root);
    return _wcsnicmp(path, root, length) == 0 &&
        (path[length] == L'\\' || path[length] == L'\0');
}

static int parse_canonical_u64(const char *value, uint64_t *result) {
    char *end = NULL;
    unsigned long long parsed;
    if (value == NULL || value[0] == '\0' ||
        (value[0] == '0' && value[1] != '\0')) {
        return 0;
    }
    errno = 0;
    parsed = strtoull(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0') {
        return 0;
    }
    *result = (uint64_t)parsed;
    return 1;
}

static void close_manifest_rows(ManifestRow *rows, size_t count) {
    size_t index;
    if (rows == NULL) {
        return;
    }
    for (index = 0U; index < count; ++index) {
        if (rows[index].handle != NULL && rows[index].handle != INVALID_HANDLE_VALUE) {
            CloseHandle(rows[index].handle);
        }
        free(rows[index].path);
    }
    secure_zero(rows, MAX_MANIFEST_ROWS * sizeof(*rows));
    free(rows);
}

static int verify_manifest_graph(
    LockedSubject *manifest, const wchar_t *project_root,
    ManifestRow **rows_out, size_t *count_out, size_t *python_index_out,
    char *error, size_t error_size
) {
    unsigned char *data = NULL;
    size_t size = 0U;
    ManifestRow *rows = NULL;
    size_t count = 0U;
    size_t line_number = 0U;
    char *cursor;
    char *end;
    int newline_style = 0;
    int launcher_seen = 0;
    int blender_seen = 0;
    size_t python_index = SIZE_MAX;
    if (!read_handle_all(manifest->handle, manifest->bytes, &data, &size) ||
        size == 0U || data[size - 1U] != '\n' || memchr(data, '\0', size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_read_or_encoding_failed");
        goto failure;
    }
    rows = (ManifestRow *)calloc(MAX_MANIFEST_ROWS, sizeof(*rows));
    if (rows == NULL) {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_row_allocation_failed");
        goto failure;
    }
    cursor = (char *)data;
    end = cursor + size;
    while (cursor < end) {
        char *line = NULL;
        char *fields[4];
        size_t field_count = 1U;
        char *scan;
        wchar_t *manifest_wide = NULL;
        wchar_t *resolved = NULL;
        LockedSubject subject;
        unsigned char expected[32];
        uint64_t expected_bytes;
        size_t index;
        if (next_canonical_line(
                &cursor, end, &newline_style, &line) != 1 ||
            newline_style != 2) {
            _snprintf_s(error, error_size, _TRUNCATE,
                        "manifest_noncanonical_crlf_or_line_unterminated");
            goto failure;
        }
        ++line_number;
        if (line_number == 1U) {
            if (strcmp(line, "KIRA_R25_AFES_RETAINED_MANIFEST_V3R9\t1") != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "manifest_magic_invalid");
                goto failure;
            }
            continue;
        }
        if (line_number == 2U) {
            if (strcmp(line, "label\tpath\tbytes\tsha256") != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "manifest_header_invalid");
                goto failure;
            }
            continue;
        }
        if (count >= MAX_MANIFEST_ROWS) {
            _snprintf_s(error, error_size, _TRUNCATE, "manifest_row_bound_exceeded");
            goto failure;
        }
        fields[0] = line;
        for (scan = line; *scan != '\0'; ++scan) {
            if (*scan == '\t') {
                *scan = '\0';
                if (field_count >= 4U) {
                    _snprintf_s(error, error_size, _TRUNCATE, "manifest_row_shape_invalid");
                    goto failure;
                }
                fields[field_count++] = scan + 1;
            }
        }
        if (field_count != 4U || !safe_identifier(fields[0]) ||
            (count != 0U && strcmp(rows[count - 1U].label, fields[0]) >= 0) ||
            !parse_canonical_u64(fields[2], &expected_bytes) ||
            !parse_hex64(fields[3], expected)) {
            _snprintf_s(error, error_size, _TRUNCATE, "manifest_row_invalid");
            goto failure;
        }
        manifest_wide = utf8_to_wide(fields[1]);
        if (manifest_wide != NULL) {
            size_t position;
            for (position = 0U; manifest_wide[position] != L'\0'; ++position) {
                if (manifest_wide[position] == L'/') manifest_wide[position] = L'\\';
            }
        }
        if (manifest_wide == NULL) {
            _snprintf_s(error, error_size, _TRUNCATE, "manifest_path_utf8_invalid");
            goto failure;
        }
        if (is_absolute_manifest_path(manifest_wide)) {
            resolved = canonical_full_path(manifest_wide);
        } else {
            resolved = path_from_root(project_root, manifest_wide);
            if (resolved != NULL && !path_under_root(resolved, project_root)) {
                free(resolved);
                resolved = NULL;
            }
        }
        free(manifest_wide);
        if (resolved == NULL) {
            _snprintf_s(error, error_size, _TRUNCATE, "manifest_path_resolution_failed");
            goto failure;
        }
        for (index = 0U; index < count; ++index) {
            if (_wcsicmp(rows[index].path, resolved) == 0) {
                free(resolved);
                _snprintf_s(error, error_size, _TRUNCATE, "manifest_path_duplicate");
                goto failure;
            }
        }
        if (!open_locked_subject(resolved, fields[3], expected_bytes, &subject)) {
            free(resolved);
            _snprintf_s(error, error_size, _TRUNCATE,
                        "manifest_subject_lock_or_hash_failed:%s", fields[0]);
            goto failure;
        }
        free(resolved);
        strcpy_s(rows[count].label, sizeof(rows[count].label), fields[0]);
        rows[count].path = subject.path;
        rows[count].expected_bytes = expected_bytes;
        memcpy(rows[count].expected_sha256, expected, sizeof(expected));
        rows[count].handle = subject.handle;
        subject.path = NULL;
        subject.handle = INVALID_HANDLE_VALUE;
        if (strcmp(fields[0], "native_launcher") == 0) {
            char digest[65];
            hex_encode32(rows[count].expected_sha256, digest);
            launcher_seen = strcmp(digest, V3R9_LAUNCHER_SHA256) == 0;
        } else if (strcmp(fields[0], "python_runtime_dll") == 0) {
            python_index = count;
        } else if (strcmp(fields[0], "blender_executable") == 0) {
            blender_seen = 1;
        }
        ++count;
    }
    if (count != 137U || !launcher_seen || !blender_seen || python_index == SIZE_MAX) {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_required_graph_drift");
        goto failure;
    }
    secure_zero(data, size);
    free(data);
    *rows_out = rows;
    *count_out = count;
    *python_index_out = python_index;
    return 1;
failure:
    if (data != NULL) {
        secure_zero(data, size);
        free(data);
    }
    close_manifest_rows(rows, count);
    return 0;
}

static int probe_outcome_parent(const wchar_t *project_root, DWORD *error_out) {
    wchar_t *receipt = path_from_root(project_root, OUTCOME_RECEIPT_RELATIVE);
    wchar_t *parent = path_from_root(project_root, OUTCOME_PARENT_RELATIVE);
    DWORD attributes;
    HANDLE handle;
    int result = 0;
    if (receipt == NULL || parent == NULL) {
        *error_out = ERROR_NOT_ENOUGH_MEMORY;
        goto cleanup;
    }
    SetLastError(ERROR_SUCCESS);
    attributes = GetFileAttributesW(receipt);
    if (attributes != INVALID_FILE_ATTRIBUTES ||
        (GetLastError() != ERROR_FILE_NOT_FOUND &&
         GetLastError() != ERROR_PATH_NOT_FOUND)) {
        *error_out = attributes != INVALID_FILE_ATTRIBUTES ? ERROR_FILE_EXISTS : GetLastError();
        goto cleanup;
    }
    handle = CreateFileW(
        parent, FILE_ADD_FILE | FILE_READ_ATTRIBUTES | SYNCHRONIZE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (handle == INVALID_HANDLE_VALUE) {
        *error_out = GetLastError();
        goto cleanup;
    }
    CloseHandle(handle);
    *error_out = ERROR_SUCCESS;
    result = 1;
cleanup:
    free(receipt);
    free(parent);
    return result;
}

static int inspect_python_dll_pe_readonly(
    const ManifestRow *row, char *detail, size_t detail_size,
    DWORD *error_out
) {
    unsigned char header[4096];
    IMAGE_DOS_HEADER dos;
    DWORD signature;
    IMAGE_FILE_HEADER file_header;
    IMAGE_OPTIONAL_HEADER64 optional_header;
    LARGE_INTEGER zero;
    DWORD read_count = 0U;
    size_t nt_offset;
    size_t required;
    zero.QuadPart = 0;
    if (!SetFilePointerEx(row->handle, zero, NULL, FILE_BEGIN) ||
        !ReadFile(row->handle, header, sizeof(header), &read_count, NULL)) {
        *error_out = GetLastError();
        return 0;
    }
    if (read_count < sizeof(dos)) {
        *error_out = ERROR_BAD_EXE_FORMAT;
        return 0;
    }
    memcpy(&dos, header, sizeof(dos));
    if (dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew < 0) {
        *error_out = ERROR_BAD_EXE_FORMAT;
        return 0;
    }
    nt_offset = (size_t)dos.e_lfanew;
    required = nt_offset + sizeof(signature) + sizeof(file_header) +
        sizeof(optional_header);
    if (required > read_count) {
        *error_out = ERROR_BAD_EXE_FORMAT;
        return 0;
    }
    memcpy(&signature, header + nt_offset, sizeof(signature));
    memcpy(&file_header, header + nt_offset + sizeof(signature),
           sizeof(file_header));
    memcpy(&optional_header,
           header + nt_offset + sizeof(signature) + sizeof(file_header),
           sizeof(optional_header));
    if (signature != IMAGE_NT_SIGNATURE ||
        file_header.Machine != IMAGE_FILE_MACHINE_AMD64 ||
        (file_header.Characteristics & IMAGE_FILE_DLL) == 0U ||
        file_header.NumberOfSections == 0U ||
        file_header.SizeOfOptionalHeader < sizeof(optional_header) ||
        optional_header.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
        optional_header.NumberOfRvaAndSizes <= IMAGE_DIRECTORY_ENTRY_IMPORT ||
        optional_header.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress == 0U ||
        optional_header.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].Size == 0U) {
        *error_out = ERROR_BAD_EXE_FORMAT;
        return 0;
    }
    _snprintf_s(
        detail, detail_size, _TRUNCATE,
        "readonly_bytes=4096;machine=0x%04x;sections=%u;"
        "import_rva=%lu;import_bytes=%lu;delay_import_rva=%lu;"
        "delay_import_bytes=%lu;dll_never_loaded=1",
        (unsigned)file_header.Machine,
        (unsigned)file_header.NumberOfSections,
        (unsigned long)optional_header.DataDirectory[
            IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress,
        (unsigned long)optional_header.DataDirectory[
            IMAGE_DIRECTORY_ENTRY_IMPORT].Size,
        (unsigned long)optional_header.DataDirectory[
            IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT].VirtualAddress,
        (unsigned long)optional_header.DataDirectory[
            IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT].Size);
    secure_zero(header, sizeof(header));
    secure_zero(&dos, sizeof(dos));
    secure_zero(&file_header, sizeof(file_header));
    secure_zero(&optional_header, sizeof(optional_header));
    *error_out = ERROR_SUCCESS;
    return 1;
}

static int validate_child_evidence_handle(
    HANDLE handle, const wchar_t *project_root
) {
    wchar_t *expected = path_from_root(project_root, EVIDENCE_RELATIVE);
    DWORD type = GetFileType(handle);
    int result = expected != NULL && type == FILE_TYPE_DISK &&
        final_path_matches(handle, expected);
    free(expected);
    return result;
}

static int same_filetime(FILETIME first, FILETIME second) {
    return first.dwLowDateTime == second.dwLowDateTime &&
        first.dwHighDateTime == second.dwHighDateTime;
}

static int process_creation_time(HANDLE process, FILETIME *creation_out) {
    FILETIME exit_time;
    FILETIME kernel_time;
    FILETIME user_time;
    return GetProcessTimes(
        process, creation_out, &exit_time, &kernel_time, &user_time) != 0;
}

static int direct_parent_pid(DWORD child_pid, DWORD *parent_out) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0U);
    PROCESSENTRY32W entry;
    int result = 0;
    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    memset(&entry, 0, sizeof(entry));
    entry.dwSize = sizeof(entry);
    if (Process32FirstW(snapshot, &entry)) {
        do {
            if (entry.th32ProcessID == child_pid) {
                *parent_out = entry.th32ParentProcessID;
                result = 1;
                break;
            }
        } while (Process32NextW(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return result;
}

static int process_image_matches(HANDLE process, const wchar_t *expected) {
    wchar_t path[32768];
    DWORD size = (DWORD)(sizeof(path) / sizeof(path[0]));
    wchar_t *canonical = NULL;
    int result = 0;
    if (!QueryFullProcessImageNameW(process, 0U, path, &size) ||
        size == 0U || size >= (DWORD)(sizeof(path) / sizeof(path[0]))) {
        return 0;
    }
    path[size] = L'\0';
    canonical = canonical_full_path(path);
    result = canonical != NULL && _wcsicmp(canonical, expected) == 0;
    free(canonical);
    secure_zero(path, sizeof(path));
    return result;
}

static int evidence_identity(
    HANDLE evidence, uint64_t *volume_out, FILE_ID_128 *id_out
) {
    FILE_ID_INFO info;
    if (!GetFileInformationByHandleEx(
            evidence, FileIdInfo, &info, sizeof(info))) return 0;
    *volume_out = info.VolumeSerialNumber;
    memcpy(id_out, &info.FileId, sizeof(*id_out));
    secure_zero(&info, sizeof(info));
    return 1;
}

static int read_capability_record(HANDLE pipe, CapabilityRecord *record) {
    unsigned char *target = (unsigned char *)record;
    size_t used = 0U;
    while (used < sizeof(*record)) {
        DWORD got = 0U;
        if (!ReadFile(pipe, target + used,
                      (DWORD)(sizeof(*record) - used), &got, NULL) ||
            got == 0U) return 0;
        used += got;
    }
    return 1;
}

static int validate_child_provenance(
    const ParsedArguments *parsed, const wchar_t *self_path,
    const wchar_t *project_root, char *error, size_t error_size
) {
    HANDLE evidence = (HANDLE)parsed->evidence_handle_value;
    HANDLE capability = (HANDLE)parsed->capability_handle_value;
    HANDLE parent = (HANDLE)parsed->parent_process_handle_value;
    CapabilityRecord record;
    CapabilityRecord hashed;
    unsigned char binding[32];
    FILETIME parent_creation;
    FILETIME child_creation;
    FILE_ID_128 evidence_id;
    uint64_t evidence_volume = 0U;
    DWORD inherited_parent_pid;
    DWORD direct_parent = 0U;
    DWORD child_pid = GetCurrentProcessId();
    int result = 0;
    memset(&record, 0, sizeof(record));
    memset(&hashed, 0, sizeof(hashed));
    memset(&evidence_id, 0, sizeof(evidence_id));
    if (!validate_child_evidence_handle(evidence, project_root) ||
        GetFileType(capability) != FILE_TYPE_PIPE ||
        GetFileType(parent) != FILE_TYPE_UNKNOWN) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "inherited_handle_type_or_evidence_identity_invalid");
        goto cleanup;
    }
    inherited_parent_pid = GetProcessId(parent);
    if (inherited_parent_pid == 0U ||
        !direct_parent_pid(child_pid, &direct_parent) ||
        direct_parent != inherited_parent_pid ||
        !process_image_matches(parent, self_path) ||
        !process_creation_time(parent, &parent_creation) ||
        !process_creation_time(GetCurrentProcess(), &child_creation) ||
        !evidence_identity(evidence, &evidence_volume, &evidence_id) ||
        !read_capability_record(capability, &record)) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "observer_parent_or_capability_read_invalid");
        goto cleanup;
    }
    memcpy(&hashed, &record, sizeof(hashed));
    secure_zero(hashed.binding_sha256, sizeof(hashed.binding_sha256));
    if (!sha256_bytes(&hashed, offsetof(CapabilityRecord, binding_sha256),
                      binding) ||
        strcmp(record.magic, CAPABILITY_MAGIC) != 0 ||
        record.version != CAPABILITY_VERSION ||
        record.record_bytes != sizeof(record) ||
        record.parent_pid != (uint64_t)inherited_parent_pid ||
        record.child_pid != (uint64_t)child_pid ||
        !same_filetime(record.parent_creation, parent_creation) ||
        !same_filetime(record.child_creation, child_creation) ||
        record.evidence_volume_serial != evidence_volume ||
        memcmp(&record.evidence_file_id, &evidence_id,
               sizeof(evidence_id)) != 0 ||
        !same_hash(record.binding_sha256, binding)) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "capability_os_identity_or_binding_invalid");
        goto cleanup;
    }
    result = 1;
cleanup:
    secure_zero(&record, sizeof(record));
    secure_zero(&hashed, sizeof(hashed));
    secure_zero(binding, sizeof(binding));
    secure_zero(&parent_creation, sizeof(parent_creation));
    secure_zero(&child_creation, sizeof(child_creation));
    secure_zero(&evidence_id, sizeof(evidence_id));
    return result;
}

static int child_main(int argc, wchar_t **argv, const wchar_t *self_path,
                      const wchar_t *derived_root) {
    ParsedArguments parsed;
    AuthorityState authority;
    ManifestRow *rows = NULL;
    size_t row_count = 0U;
    size_t python_index = SIZE_MAX;
    char error[512];
    char detail[256];
    DWORD winerror = ERROR_SUCCESS;
    error[0] = '\0';
    if (!parse_arguments(argc, argv, 1, &parsed, error, sizeof(error))) {
        return 50;
    }
    g_evidence = (HANDLE)parsed.evidence_handle_value;
    if (!validate_child_provenance(
            &parsed, self_path, derived_root, error, sizeof(error))) {
        return 50;
    }
    if (!write_record(
            "child", "wmain_entry", "entered",
            "observer_owned_capability_parent_child_and_evidence_identity_valid")) {
        return 50;
    }
    write_record("child", "argument_gate", "passed",
                 "exact_four_internal_option_contract_no_caller_hashes");
    if (!initialize_authority(derived_root, self_path, &authority,
                              error, sizeof(error))) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "reason=%s", error);
        write_record("child", "fresh_audit_and_subject_gate", "failed", detail);
        fwprintf(stderr, L"KIRA_R25_AFES_V3R12_CHILD_REFUSED:%hs\n", error);
        return 53;
    }
    _snprintf_s(detail, sizeof(detail), _TRUNCATE, "self_sha256=%s",
                authority.self_sha256);
    write_record("child", "self_image_identity", "passed", detail);
    write_record("child", "fresh_audit_and_subject_gate", "passed",
                 "different_auditor_decision_and_runtime_subjects_exact");
    if (!verify_manifest_graph(&authority.manifest, derived_root, &rows,
                               &row_count, &python_index, error, sizeof(error))) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "reason=%s", error);
        write_record("child", "retained_graph_gate", "failed", detail);
        fwprintf(stderr, L"KIRA_R25_AFES_V3R12_CHILD_FAILED:%hs\n", error);
        close_authority(&authority);
        return 54;
    }
    _snprintf_s(detail, sizeof(detail), _TRUNCATE, "locked_rows=%zu", row_count);
    write_record("child", "retained_graph_gate", "passed", detail);
    if (!probe_outcome_parent(derived_root, &winerror)) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "winerror=%lu",
                    (unsigned long)winerror);
        write_record("child", "pre_outcome_parent_access_gate", "failed", detail);
        close_manifest_rows(rows, row_count);
        close_authority(&authority);
        return 55;
    }
    write_record("child", "pre_outcome_parent_access_gate", "passed",
                 "FILE_ADD_FILE_open_only_receipt_absent");
    if (!inspect_python_dll_pe_readonly(
            &rows[python_index], detail, sizeof(detail), &winerror)) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "winerror=%lu",
                    (unsigned long)winerror);
        write_record("child", "python_dll_readonly_pe_identity", "failed", detail);
        close_manifest_rows(rows, row_count);
        close_authority(&authority);
        return 56;
    }
    write_record("child", "python_dll_readonly_pe_identity", "passed", detail);
    write_record("child", "pre_outcome_stop", "reached",
                 "no_dll_load_no_python_no_controller_no_reservation_no_afes_no_blender");
    close_manifest_rows(rows, row_count);
    close_authority(&authority);
    fputs("KIRA_R25_AFES_V3R12_PROBE_REACHED_PRE_OUTCOME_STOP\n", stdout);
    fflush(stdout);
    return (int)CHILD_PRE_OUTCOME_STOP_EXIT;
}

static int append_quoted(wchar_t *command, size_t capacity, size_t *used,
                         const wchar_t *argument) {
    size_t index;
    size_t backslashes = 0U;
    if (*used + 3U >= capacity) return 0;
    command[(*used)++] = L'"';
    for (index = 0U;; ++index) {
        wchar_t ch = argument[index];
        if (ch == L'\\') {
            ++backslashes;
            continue;
        }
        if (ch == L'"' || ch == L'\0') {
            size_t repeat = backslashes * 2U + (ch == L'"' ? 1U : 0U);
            while (repeat-- != 0U) {
                if (*used + 2U >= capacity) return 0;
                command[(*used)++] = L'\\';
            }
            backslashes = 0U;
            if (ch == L'\0') break;
            if (*used + 2U >= capacity) return 0;
            command[(*used)++] = L'"';
        } else {
            while (backslashes-- != 0U) {
                if (*used + 2U >= capacity) return 0;
                command[(*used)++] = L'\\';
            }
            backslashes = 0U;
            if (*used + 2U >= capacity) return 0;
            command[(*used)++] = ch;
        }
    }
    command[(*used)++] = L'"';
    command[*used] = L'\0';
    return 1;
}

static int append_command_argument(wchar_t *command, size_t capacity,
                                   size_t *used, const wchar_t *argument) {
    if (*used != 0U) {
        if (*used + 2U >= capacity) return 0;
        command[(*used)++] = L' ';
        command[*used] = L'\0';
    }
    return append_quoted(command, capacity, used, argument);
}

static int random_nonce(char output[65]) {
    unsigned char bytes[32];
    NTSTATUS status = BCryptGenRandom(NULL, bytes, sizeof(bytes),
                                      BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (status < 0) return 0;
    hex_encode32(bytes, output);
    secure_zero(bytes, sizeof(bytes));
    return 1;
}

static int read_pipe_bounded(HANDLE pipe, unsigned char output[MAX_CAPTURE_BYTES],
                             size_t *size_out, int *overflow_out) {
    size_t used = 0U;
    int overflow = 0;
    for (;;) {
        DWORD read_count = 0U;
        unsigned char buffer[512];
        if (!ReadFile(pipe, buffer, sizeof(buffer), &read_count, NULL)) {
            DWORD error = GetLastError();
            if (error == ERROR_BROKEN_PIPE) break;
            return 0;
        }
        if (read_count == 0U) break;
        if (used + read_count <= MAX_CAPTURE_BYTES) {
            memcpy(output + used, buffer, read_count);
            used += read_count;
        } else {
            overflow = 1;
        }
    }
    *size_out = used;
    *overflow_out = overflow;
    return 1;
}

static char *hex_encode_bytes(const unsigned char *data, size_t size) {
    static const char digits[] = "0123456789abcdef";
    char *result = (char *)calloc(size * 2U + 1U, 1U);
    size_t index;
    if (result == NULL) return NULL;
    for (index = 0U; index < size; ++index) {
        result[index * 2U] = digits[data[index] >> 4U];
        result[index * 2U + 1U] = digits[data[index] & 0x0fU];
    }
    return result;
}

static int observer_main(int argc, wchar_t **argv, const wchar_t *self_path,
                         const wchar_t *derived_root) {
    ParsedArguments parsed;
    AuthorityState authority;
    char error[512];
    char detail[12288];
    SECURITY_ATTRIBUTES pipe_security;
    HANDLE stdout_read = NULL;
    HANDLE stdout_write = NULL;
    HANDLE stderr_read = NULL;
    HANDLE stderr_write = NULL;
    HANDLE capability_read = NULL;
    HANDLE capability_write = NULL;
    HANDLE parent_process = NULL;
    HANDLE inherited_handles[5];
    CapabilityRecord capability_record;
    STARTUPINFOEXW startup;
    PROCESS_INFORMATION process;
    SIZE_T attribute_size = 0U;
    wchar_t command[32768];
    size_t command_used = 0U;
    wchar_t handle_text[32];
    DWORD creation_error = ERROR_SUCCESS;
    DWORD wait_result = WAIT_FAILED;
    DWORD raw_exit = STILL_ACTIVE;
    unsigned char stdout_capture[MAX_CAPTURE_BYTES];
    unsigned char stderr_capture[MAX_CAPTURE_BYTES];
    size_t stdout_size = 0U;
    size_t stderr_size = 0U;
    int stdout_overflow = 0;
    int stderr_overflow = 0;
    char *stdout_hex = NULL;
    char *stderr_hex = NULL;
    int result = 20;
    int child_created = 0;
    int child_resumed = 0;
    memset(&startup, 0, sizeof(startup));
    memset(&process, 0, sizeof(process));
    memset(&capability_record, 0, sizeof(capability_record));
    error[0] = '\0';
    command[0] = L'\0';
    if (!write_record("observer", "wmain_entry", "entered",
                      "evidence_reserved_create_new_write_through")) return 20;
    if (!parse_arguments(argc, argv, 0, &parsed, error, sizeof(error))) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "reason=%s", error);
        write_record("observer", "argument_gate", "failed", detail);
        return 21;
    }
    write_record("observer", "argument_gate", "passed",
                 "zero_caller_arguments_no_caller_paths_or_hashes");
    if (!initialize_authority(derived_root, self_path, &authority,
                              error, sizeof(error))) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "reason=%s", error);
        write_record("observer", "fresh_audit_and_subject_gate", "failed", detail);
        return 22;
    }
    _snprintf_s(detail, sizeof(detail), _TRUNCATE, "self_sha256=%s",
                authority.self_sha256);
    write_record("observer", "fresh_audit_and_subject_gate", "passed", detail);
    memset(&pipe_security, 0, sizeof(pipe_security));
    pipe_security.nLength = sizeof(pipe_security);
    pipe_security.bInheritHandle = TRUE;
    if (!CreatePipe(&stdout_read, &stdout_write, &pipe_security, 0U) ||
        !CreatePipe(&stderr_read, &stderr_write, &pipe_security, 0U) ||
        !CreatePipe(&capability_read, &capability_write, &pipe_security, 0U) ||
        !SetHandleInformation(stdout_read, HANDLE_FLAG_INHERIT, 0U) ||
        !SetHandleInformation(stderr_read, HANDLE_FLAG_INHERIT, 0U) ||
        !SetHandleInformation(capability_write, HANDLE_FLAG_INHERIT, 0U)) {
        write_record("observer", "child_preparation", "failed", "pipe_creation_failed");
        goto cleanup;
    }
    parent_process = OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, FALSE,
        GetCurrentProcessId());
    if (parent_process == NULL || !SetHandleInformation(
            parent_process, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT)) {
        write_record("observer", "child_preparation", "failed",
                     "inheritable_parent_identity_handle_failed");
        goto cleanup;
    }
    if (!append_command_argument(command, 32768U, &command_used, self_path)) goto command_fail;
    if (!append_command_argument(command, 32768U, &command_used,
                                 L"--v3r12-child") ||
        !append_command_argument(command, 32768U, &command_used,
                                 L"observer-owned")) goto command_fail;
    if (!append_command_argument(command, 32768U, &command_used, L"--evidence-handle")) goto command_fail;
    _snwprintf_s(handle_text, 32U, _TRUNCATE, L"%llu",
                 (unsigned long long)(uintptr_t)g_evidence);
    if (!append_command_argument(command, 32768U, &command_used, handle_text)) goto command_fail;
    if (!append_command_argument(command, 32768U, &command_used,
                                 L"--capability-read-handle")) goto command_fail;
    _snwprintf_s(handle_text, 32U, _TRUNCATE, L"%llu",
                 (unsigned long long)(uintptr_t)capability_read);
    if (!append_command_argument(command, 32768U, &command_used, handle_text)) goto command_fail;
    if (!append_command_argument(command, 32768U, &command_used,
                                 L"--parent-process-handle")) goto command_fail;
    _snwprintf_s(handle_text, 32U, _TRUNCATE, L"%llu",
                 (unsigned long long)(uintptr_t)parent_process);
    if (!append_command_argument(command, 32768U, &command_used, handle_text)) goto command_fail;
    startup.StartupInfo.cb = sizeof(startup);
    startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
    /* The child never reads stdin. Exactly five handles are allowlisted: the
     * evidence file, two stream writers, the capability read end, and a
     * query-only handle to the exact observer process. */
    startup.StartupInfo.hStdInput = g_evidence;
    startup.StartupInfo.hStdOutput = stdout_write;
    startup.StartupInfo.hStdError = stderr_write;
    inherited_handles[0] = g_evidence;
    inherited_handles[1] = stdout_write;
    inherited_handles[2] = stderr_write;
    inherited_handles[3] = capability_read;
    inherited_handles[4] = parent_process;
    InitializeProcThreadAttributeList(NULL, 1U, 0U, &attribute_size);
    if (GetLastError() != ERROR_INSUFFICIENT_BUFFER || attribute_size == 0U) {
        write_record("observer", "child_preparation", "failed",
                     "attribute_list_size_failed");
        goto cleanup;
    }
    startup.lpAttributeList = (LPPROC_THREAD_ATTRIBUTE_LIST)calloc(attribute_size, 1U);
    if (startup.lpAttributeList == NULL ||
        !InitializeProcThreadAttributeList(startup.lpAttributeList, 1U, 0U,
                                           &attribute_size) ||
        !UpdateProcThreadAttribute(
            startup.lpAttributeList, 0U, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            inherited_handles, sizeof(inherited_handles), NULL, NULL)) {
        write_record("observer", "child_preparation", "failed",
                     "attribute_handle_allowlist_failed");
        goto cleanup;
    }
    SetLastError(ERROR_SUCCESS);
    if (!CreateProcessW(
            self_path, command, NULL, NULL, TRUE,
            CREATE_SUSPENDED | CREATE_NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT,
            NULL, derived_root, &startup.StartupInfo, &process)) {
        creation_error = GetLastError();
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "winerror=%lu",
                    (unsigned long)creation_error);
        write_record("observer", "create_process", "failed", detail);
        goto cleanup;
    }
    child_created = 1;
    CloseHandle(stdout_write); stdout_write = NULL;
    CloseHandle(stderr_write); stderr_write = NULL;
    CloseHandle(capability_read); capability_read = NULL;
    _snprintf_s(detail, sizeof(detail), _TRUNCATE,
                "created_suspended=1;pid=%lu", (unsigned long)process.dwProcessId);
    if (!write_record("observer", "create_process", "passed", detail)) goto cleanup;
    strcpy_s(capability_record.magic, sizeof(capability_record.magic),
             CAPABILITY_MAGIC);
    capability_record.version = CAPABILITY_VERSION;
    capability_record.record_bytes = (uint32_t)sizeof(capability_record);
    capability_record.parent_pid = (uint64_t)GetCurrentProcessId();
    capability_record.child_pid = (uint64_t)process.dwProcessId;
    if (!process_creation_time(
            GetCurrentProcess(), &capability_record.parent_creation) ||
        !process_creation_time(process.hProcess,
                               &capability_record.child_creation) ||
        !evidence_identity(
            g_evidence, &capability_record.evidence_volume_serial,
            &capability_record.evidence_file_id) ||
        BCryptGenRandom(NULL, capability_record.nonce,
                        sizeof(capability_record.nonce),
                        BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0 ||
        !sha256_bytes(
            &capability_record,
            offsetof(CapabilityRecord, binding_sha256),
            capability_record.binding_sha256)) {
        write_record("observer", "child_capability", "failed",
                     "os_identity_nonce_or_binding_creation_failed");
        goto cleanup;
    }
    {
        DWORD written = 0U;
        if (!WriteFile(capability_write, &capability_record,
                       sizeof(capability_record), &written, NULL) ||
            written != sizeof(capability_record)) {
            write_record("observer", "child_capability", "failed",
                         "capability_pipe_write_failed");
            goto cleanup;
        }
    }
    CloseHandle(capability_write); capability_write = NULL;
    CloseHandle(parent_process); parent_process = NULL;
    _snprintf_s(
        detail, sizeof(detail), _TRUNCATE,
        "parent_pid=%lu;child_pid=%lu;parent_child_creation_times_bound=1;"
        "evidence_file_id_bound=1;nonce_bytes=32",
        (unsigned long)GetCurrentProcessId(),
        (unsigned long)process.dwProcessId);
    if (!write_record("observer", "child_capability", "passed", detail)) {
        goto cleanup;
    }
    if (ResumeThread(process.hThread) == (DWORD)-1) {
        creation_error = GetLastError();
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "winerror=%lu",
                    (unsigned long)creation_error);
        write_record("observer", "resume_child", "failed", detail);
        TerminateProcess(process.hProcess, 0xe1U);
        WaitForSingleObject(process.hProcess, CHILD_WAIT_MILLISECONDS);
        goto capture;
    }
    child_resumed = 1;
    wait_result = WaitForSingleObject(process.hProcess, CHILD_WAIT_MILLISECONDS);
    if (wait_result == WAIT_TIMEOUT) {
        TerminateProcess(process.hProcess, 0xe2U);
        WaitForSingleObject(process.hProcess, CHILD_WAIT_MILLISECONDS);
        write_record("observer", "resume_child", "passed", "child_was_resumed");
        write_record("observer", "wait_child", "failed", "timeout_30000ms");
    } else if (wait_result != WAIT_OBJECT_0) {
        creation_error = GetLastError();
        TerminateProcess(process.hProcess, 0xe3U);
        WaitForSingleObject(process.hProcess, CHILD_WAIT_MILLISECONDS);
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "winerror=%lu",
                    (unsigned long)creation_error);
        write_record("observer", "resume_child", "passed", "child_was_resumed");
        write_record("observer", "wait_child", "failed", detail);
    } else {
        write_record("observer", "resume_child", "passed", "child_was_resumed");
        write_record("observer", "wait_child", "passed", "process_signaled");
    }
capture:
    if (!GetExitCodeProcess(process.hProcess, &raw_exit)) {
        raw_exit = 0xffffffffU;
    }
    CloseHandle(process.hThread); process.hThread = NULL;
    CloseHandle(process.hProcess); process.hProcess = NULL;
    if (!read_pipe_bounded(stdout_read, stdout_capture, &stdout_size, &stdout_overflow) ||
        !read_pipe_bounded(stderr_read, stderr_capture, &stderr_size, &stderr_overflow)) {
        write_record("observer", "stream_capture", "failed", "ReadFile_failed");
        goto cleanup;
    }
    stdout_hex = hex_encode_bytes(stdout_capture, stdout_size);
    stderr_hex = hex_encode_bytes(stderr_capture, stderr_size);
    if (stdout_hex == NULL || stderr_hex == NULL) {
        write_record("observer", "stream_capture", "failed", "allocation_failed");
        goto cleanup;
    }
    _snprintf_s(detail, sizeof(detail), _TRUNCATE,
                "raw_exit=%lu;stdout_bytes=%zu;stderr_bytes=%zu;"
                "stdout_overflow=%d;stderr_overflow=%d;stdout_hex=%s;stderr_hex=%s",
                (unsigned long)raw_exit, stdout_size, stderr_size,
                stdout_overflow, stderr_overflow, stdout_hex, stderr_hex);
    write_record("observer", "raw_exit_and_captured_streams", "recorded", detail);
    if (child_resumed && wait_result == WAIT_OBJECT_0 &&
        raw_exit == CHILD_PRE_OUTCOME_STOP_EXIT && !stdout_overflow &&
        !stderr_overflow && stderr_size == 0U &&
        stdout_size == sizeof(
            "KIRA_R25_AFES_V3R12_PROBE_REACHED_PRE_OUTCOME_STOP\n") - 1U &&
        memcmp(stdout_capture,
               "KIRA_R25_AFES_V3R12_PROBE_REACHED_PRE_OUTCOME_STOP\n",
               sizeof("KIRA_R25_AFES_V3R12_PROBE_REACHED_PRE_OUTCOME_STOP\n") - 1U) == 0) {
        write_record("observer", "diagnostic_terminal", "complete",
                     "child_reached_pre_outcome_stop_raw_exit_41");
        result = 0;
    } else {
        write_record("observer", "diagnostic_terminal", "failed",
                     "child_did_not_reach_exact_pre_outcome_stop");
        result = 24;
    }
    goto cleanup;
command_fail:
    write_record("observer", "child_preparation", "failed", "command_encoding_failed");
cleanup:
    free(stdout_hex);
    free(stderr_hex);
    secure_zero(stdout_capture, sizeof(stdout_capture));
    secure_zero(stderr_capture, sizeof(stderr_capture));
    if (startup.lpAttributeList != NULL) {
        DeleteProcThreadAttributeList(startup.lpAttributeList);
        free(startup.lpAttributeList);
    }
    if (process.hThread != NULL) CloseHandle(process.hThread);
    if (process.hProcess != NULL) {
        if (child_created) {
            TerminateProcess(process.hProcess, 0xe4U);
            WaitForSingleObject(process.hProcess, CHILD_WAIT_MILLISECONDS);
        }
        CloseHandle(process.hProcess);
    }
    if (stdout_read != NULL) CloseHandle(stdout_read);
    if (stdout_write != NULL) CloseHandle(stdout_write);
    if (stderr_read != NULL) CloseHandle(stderr_read);
    if (stderr_write != NULL) CloseHandle(stderr_write);
    if (capability_read != NULL) CloseHandle(capability_read);
    if (capability_write != NULL) CloseHandle(capability_write);
    if (parent_process != NULL) CloseHandle(parent_process);
    close_authority(&authority);
    secure_zero(&capability_record, sizeof(capability_record));
    secure_zero(command, sizeof(command));
    return result;
}

static int find_child_surface(int argc, wchar_t **argv) {
    return argc == 9 &&
        wcscmp(argv[1], L"--v3r12-child") == 0 &&
        wcscmp(argv[2], L"observer-owned") == 0;
}

int wmain(int argc, wchar_t **argv) {
    wchar_t *self_path = NULL;
    wchar_t *derived_root = NULL;
    int child_surface;
    int result;
    if (!derive_project_root(&self_path, &derived_root)) {
        fwprintf(stderr, L"KIRA_R25_AFES_V3R12_REFUSED:self_location_invalid\n");
        return 10;
    }
    child_surface = find_child_surface(argc, argv);
    if (child_surface) {
        result = child_main(argc, argv, self_path, derived_root);
    } else {
        if (!reserve_evidence(derived_root)) {
            fwprintf(stderr,
                     L"KIRA_R25_AFES_V3R12_REFUSED:evidence_create_new_failed:%lu\n",
                     (unsigned long)GetLastError());
            free(self_path);
            free(derived_root);
            return 11;
        }
        result = observer_main(argc, argv, self_path, derived_root);
    }
    if (g_evidence != INVALID_HANDLE_VALUE) {
        FlushFileBuffers(g_evidence);
        CloseHandle(g_evidence);
        g_evidence = INVALID_HANDLE_VALUE;
    }
    free(self_path);
    free(derived_root);
    return result;
}
