/*
 * Kira R25 AFES locked-pair v3r10 native pre-outcome diagnostic.
 *
 * STATIC/AUDIT BOUNDARY: compiling and inspecting this file is permitted.
 * The PE must not be invoked until a different fresh exact-byte auditor has
 * produced the canonical accepted audit described below.  It never executes
 * v3r9, a controller, bootstrap, wrapper, AFES extractor, or Blender.  Its
 * only child is one suspended copy of its own exact image.  The child verifies
 * the frozen v3r9 retained graph read-only, probes the old receipt parent's
 * FILE_ADD_FILE access without creating the receipt, verifies delayed loading
 * of the retained Python DLL without calling any Python API, and exits at an
 * explicit pre-outcome stop.
 *
 * Build (x64 Native Tools command prompt):
 *   cl.exe /nologo /W4 /WX /O2 /MT /guard:cf /DUNICODE /D_UNICODE /std:c17 \
 *     tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.c \
 *     /Fo:tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.obj \
 *     /Fe:tools\native\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.exe \
 *     /link /guard:cf /WX bcrypt.lib
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <errno.h>

#pragma comment(lib, "bcrypt.lib")

#define MAX_SUBJECT_BYTES (2U * 1024U * 1024U)
#define MAX_MANIFEST_ROWS 256U
#define MAX_CAPTURE_BYTES 4096U
#define CHILD_WAIT_MILLISECONDS 30000U
#define CHILD_PRE_OUTCOME_STOP_EXIT 41U
#define AUTHOR_ID "codex_r25_afes_v3r10_recovery_author"
#define MANIFEST_SHA256 \
    "6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96"
#define POSTMORTEM_SHA256 \
    "275fd7501a5d35ec6c5648a3935cafa56eb7854dfb80c173a2adc364738afed3"
#define V3R9_LAUNCHER_SHA256 \
    "2aec90c36e3150c258f6089fd1ba3f9e5c336ca0b69d8d1a4d826bc6a8764760"

static const wchar_t *const SELF_RELATIVE =
    L"tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.exe";
static const wchar_t *const CONTRACT_RELATIVE =
    L"Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r10.json";
static const wchar_t *const MANIFEST_RELATIVE =
    L"RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9\\RETAINED_NATIVE_LOCK_MANIFEST.tsv";
static const wchar_t *const POSTMORTEM_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r9_consumed_run_static_postmortem\\attempt_01\\CHECKPOINT.md";
static const wchar_t *const AUDIT_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r10_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t *const EVIDENCE_RELATIVE =
    L"RecoverySprint\\continuation_20260810\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
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
    const wchar_t *project_root;
    const wchar_t *manifest_path;
    const wchar_t *contract_path;
    const wchar_t *audit_path;
    char manifest_sha256[65];
    char contract_sha256[65];
    char audit_sha256[65];
    int child_mode;
    char child_nonce[65];
    uintptr_t evidence_handle_value;
} ParsedArguments;

typedef struct AuthorityState {
    LockedSubject self;
    LockedSubject contract;
    LockedSubject manifest;
    LockedSubject postmortem;
    LockedSubject audit;
    char self_sha256[65];
} AuthorityState;

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
        "{\"schema\":\"kira.r25.afes.v3r10.native_stage.v1\","
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
    for (index = 1; index < argc; ++index) {
        const wchar_t *option = argv[index];
        const wchar_t *value;
        unsigned bit;
        if (index + 1 >= argc) {
            _snprintf_s(error, error_size, _TRUNCATE, "option_missing_value");
            return 0;
        }
        value = argv[++index];
        if (wcscmp(option, L"--project-root") == 0) {
            bit = 1U << 0; parsed->project_root = value;
        } else if (wcscmp(option, L"--retained-manifest") == 0) {
            bit = 1U << 1; parsed->manifest_path = value;
        } else if (wcscmp(option, L"--manifest-sha256") == 0) {
            bit = 1U << 2;
            if (!copy_ascii_wide(value, parsed->manifest_sha256,
                                 sizeof(parsed->manifest_sha256))) return 0;
        } else if (wcscmp(option, L"--contract-path") == 0) {
            bit = 1U << 3; parsed->contract_path = value;
        } else if (wcscmp(option, L"--contract-sha256") == 0) {
            bit = 1U << 4;
            if (!copy_ascii_wide(value, parsed->contract_sha256,
                                 sizeof(parsed->contract_sha256))) return 0;
        } else if (wcscmp(option, L"--audit-path") == 0) {
            bit = 1U << 5; parsed->audit_path = value;
        } else if (wcscmp(option, L"--audit-sha256") == 0) {
            bit = 1U << 6;
            if (!copy_ascii_wide(value, parsed->audit_sha256,
                                 sizeof(parsed->audit_sha256))) return 0;
        } else if (wcscmp(option, L"--child-mode") == 0) {
            bit = 1U << 7; parsed->child_mode = 1;
            if (!copy_ascii_wide(value, parsed->child_nonce,
                                 sizeof(parsed->child_nonce))) return 0;
        } else if (wcscmp(option, L"--evidence-handle") == 0) {
            bit = 1U << 8;
            if (!parse_handle_value(value, &parsed->evidence_handle_value)) return 0;
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
    if (seen != (child_expected ? 0x1ffU : 0x7fU) ||
        parsed->project_root == NULL || parsed->manifest_path == NULL ||
        parsed->contract_path == NULL || parsed->audit_path == NULL ||
        !is_lower_hex64(parsed->manifest_sha256) ||
        !is_lower_hex64(parsed->contract_sha256) ||
        !is_lower_hex64(parsed->audit_sha256) ||
        (child_expected && (!is_lower_hex64(parsed->child_nonce) ||
                            parsed->evidence_handle_value == 0U))) {
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
    close_subject(&state->audit);
    close_subject(&state->postmortem);
    close_subject(&state->manifest);
    close_subject(&state->contract);
    close_subject(&state->self);
    secure_zero(state, sizeof(*state));
}

static int parse_exact_audit(
    LockedSubject *audit, const char *contract_sha256,
    const char *self_sha256, char *error, size_t error_size
) {
    static const char *const keys[] = {
        "decision", "auditor_boundary", "auditor_id", "contract_sha256",
        "native_executable_sha256", "native_source_sha256",
        "static_test_sha256", "static_checkpoint_sha256",
        "retained_manifest_sha256", "v3r9_postmortem_sha256"
    };
    unsigned char *data = NULL;
    size_t size = 0U;
    char *cursor;
    char *end;
    const char *values[10];
    size_t row = 0U;
    int result = 0;
    if (!read_handle_all(audit->handle, audit->bytes, &data, &size) ||
        size == 0U || data[size - 1U] != '\n' || memchr(data, '\0', size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE, "audit_read_or_encoding_failed");
        goto cleanup;
    }
    cursor = (char *)data;
    end = cursor + size;
    while (cursor < end) {
        char *newline = memchr(cursor, '\n', (size_t)(end - cursor));
        char *tab;
        if (newline == NULL) {
            _snprintf_s(error, error_size, _TRUNCATE, "audit_line_unterminated");
            goto cleanup;
        }
        *newline = '\0';
        if (row == 0U) {
            if (strcmp(cursor,
                    "KIRA_R25_AFES_PREOUTCOME_DIAGNOSTIC_AUDIT_V3R10\t1") != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_magic_invalid");
                goto cleanup;
            }
        } else {
            if (row > 10U) {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_extra_row");
                goto cleanup;
            }
            tab = strchr(cursor, '\t');
            if (tab == NULL || strchr(tab + 1, '\t') != NULL) {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_row_shape_invalid");
                goto cleanup;
            }
            *tab = '\0';
            if (strcmp(cursor, keys[row - 1U]) != 0 || tab[1] == '\0') {
                _snprintf_s(error, error_size, _TRUNCATE, "audit_key_order_invalid");
                goto cleanup;
            }
            values[row - 1U] = tab + 1;
        }
        ++row;
        cursor = newline + 1;
    }
    if (row != 11U ||
        strcmp(values[0], "ACCEPTED_FOR_ONE_BOUNDED_NATIVE_DIAGNOSTIC_ONLY") != 0 ||
        strcmp(values[1], "different_fresh_exact_byte_static_auditor") != 0 ||
        !safe_identifier(values[2]) || strcmp(values[2], AUTHOR_ID) == 0 ||
        strcmp(values[3], contract_sha256) != 0 ||
        strcmp(values[4], self_sha256) != 0 ||
        !is_lower_hex64(values[5]) || !is_lower_hex64(values[6]) ||
        !is_lower_hex64(values[7]) ||
        strcmp(values[8], MANIFEST_SHA256) != 0 ||
        strcmp(values[9], POSTMORTEM_SHA256) != 0) {
        _snprintf_s(error, error_size, _TRUNCATE,
                    "audit_decision_boundary_or_subject_invalid");
        goto cleanup;
    }
    result = 1;
cleanup:
    if (data != NULL) {
        secure_zero(data, size);
        free(data);
    }
    return result;
}

static int initialize_authority(
    const ParsedArguments *parsed, const wchar_t *derived_root,
    const wchar_t *self_path, AuthorityState *state,
    char *error, size_t error_size
) {
    wchar_t *postmortem = NULL;
    memset(state, 0, sizeof(*state));
    state->self.handle = INVALID_HANDLE_VALUE;
    state->contract.handle = INVALID_HANDLE_VALUE;
    state->manifest.handle = INVALID_HANDLE_VALUE;
    state->postmortem.handle = INVALID_HANDLE_VALUE;
    state->audit.handle = INVALID_HANDLE_VALUE;
    if (strcmp(parsed->manifest_sha256, MANIFEST_SHA256) != 0 ||
        !exact_expected_path(derived_root, parsed->manifest_path, MANIFEST_RELATIVE) ||
        !exact_expected_path(derived_root, parsed->contract_path, CONTRACT_RELATIVE) ||
        !exact_expected_path(derived_root, parsed->audit_path, AUDIT_RELATIVE)) {
        _snprintf_s(error, error_size, _TRUNCATE, "fixed_path_or_manifest_drift");
        goto failure;
    }
    if (!open_locked_subject(self_path, NULL, UINT64_MAX, &state->self)) {
        _snprintf_s(error, error_size, _TRUNCATE, "self_image_lock_or_hash_failed");
        goto failure;
    }
    hex_encode32(state->self.sha256, state->self_sha256);
    if (!open_locked_subject(parsed->contract_path, parsed->contract_sha256,
                             UINT64_MAX, &state->contract)) {
        _snprintf_s(error, error_size, _TRUNCATE, "contract_lock_or_hash_failed");
        goto failure;
    }
    if (!open_locked_subject(parsed->manifest_path, MANIFEST_SHA256, 24975U,
                             &state->manifest)) {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_lock_or_hash_failed");
        goto failure;
    }
    postmortem = path_from_root(derived_root, POSTMORTEM_RELATIVE);
    if (postmortem == NULL ||
        !open_locked_subject(postmortem, POSTMORTEM_SHA256, 8451U,
                             &state->postmortem)) {
        _snprintf_s(error, error_size, _TRUNCATE, "postmortem_lock_or_hash_failed");
        goto failure;
    }
    free(postmortem);
    postmortem = NULL;
    if (!open_locked_subject(parsed->audit_path, parsed->audit_sha256,
                             UINT64_MAX, &state->audit) ||
        !parse_exact_audit(&state->audit, parsed->contract_sha256,
                           state->self_sha256, error, error_size)) {
        if (error[0] == '\0') {
            _snprintf_s(error, error_size, _TRUNCATE, "audit_lock_or_hash_failed");
        }
        goto failure;
    }
    return 1;
failure:
    free(postmortem);
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
        char *newline = memchr(cursor, '\n', (size_t)(end - cursor));
        char *fields[4];
        size_t field_count = 1U;
        char *scan;
        wchar_t *manifest_wide = NULL;
        wchar_t *resolved = NULL;
        LockedSubject subject;
        unsigned char expected[32];
        uint64_t expected_bytes;
        size_t index;
        if (newline == NULL) {
            _snprintf_s(error, error_size, _TRUNCATE, "manifest_line_unterminated");
            goto failure;
        }
        *newline = '\0';
        ++line_number;
        if (line_number == 1U) {
            if (strcmp(cursor, "KIRA_R25_AFES_RETAINED_MANIFEST_V3R9\t1") != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "manifest_magic_invalid");
                goto failure;
            }
            cursor = newline + 1;
            continue;
        }
        if (line_number == 2U) {
            if (strcmp(cursor, "label\tpath\tbytes\tsha256") != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "manifest_header_invalid");
                goto failure;
            }
            cursor = newline + 1;
            continue;
        }
        if (count >= MAX_MANIFEST_ROWS) {
            _snprintf_s(error, error_size, _TRUNCATE, "manifest_row_bound_exceeded");
            goto failure;
        }
        fields[0] = cursor;
        for (scan = cursor; *scan != '\0'; ++scan) {
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
        cursor = newline + 1;
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

static int verify_python_dll_load(const ManifestRow *row, DWORD *error_out) {
    HMODULE module;
    wchar_t loaded_path[32768];
    DWORD length;
    LockedSubject loaded;
    char expected[65];
    int result = 0;
    if (GetModuleHandleW(L"python314.dll") != NULL) {
        *error_out = ERROR_ALREADY_EXISTS;
        return 0;
    }
    module = LoadLibraryExW(
        row->path, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (module == NULL) {
        *error_out = GetLastError();
        return 0;
    }
    length = GetModuleFileNameW(module, loaded_path,
                                (DWORD)(sizeof(loaded_path) / sizeof(loaded_path[0])));
    hex_encode32(row->expected_sha256, expected);
    if (length != 0U && length < (DWORD)(sizeof(loaded_path) / sizeof(loaded_path[0])) - 1U &&
        open_locked_subject(loaded_path, expected, row->expected_bytes, &loaded)) {
        close_subject(&loaded);
        result = 1;
        *error_out = ERROR_SUCCESS;
    } else {
        *error_out = GetLastError();
        if (*error_out == ERROR_SUCCESS) *error_out = ERROR_INVALID_DATA;
    }
    if (!FreeLibrary(module) && result) {
        *error_out = GetLastError();
        result = 0;
    }
    return result;
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

static int child_main(int argc, wchar_t **argv, const wchar_t *self_path,
                      const wchar_t *derived_root) {
    ParsedArguments parsed;
    AuthorityState authority;
    ManifestRow *rows = NULL;
    size_t row_count = 0U;
    size_t python_index = SIZE_MAX;
    char error[512];
    char detail[256];
    wchar_t *parsed_root = NULL;
    DWORD winerror = ERROR_SUCCESS;
    error[0] = '\0';
    if (!parse_arguments(argc, argv, 1, &parsed, error, sizeof(error))) {
        return 50;
    }
    g_evidence = (HANDLE)parsed.evidence_handle_value;
    if (!validate_child_evidence_handle(g_evidence, derived_root) ||
        !write_record("child", "wmain_entry", "entered", "inherited_evidence_handle_valid")) {
        return 50;
    }
    parsed_root = canonical_full_path(parsed.project_root);
    if (parsed_root == NULL || _wcsicmp(parsed_root, derived_root) != 0) {
        write_record("child", "argument_gate", "failed", "project_root_identity_mismatch");
        free(parsed_root);
        return 51;
    }
    free(parsed_root);
    write_record("child", "argument_gate", "passed", "exact_nine_option_contract");
    if (!initialize_authority(&parsed, derived_root, self_path, &authority,
                              error, sizeof(error))) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "reason=%s", error);
        write_record("child", "fresh_audit_and_subject_gate", "failed", detail);
        fwprintf(stderr, L"KIRA_R25_AFES_V3R10_CHILD_REFUSED:%hs\n", error);
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
        fwprintf(stderr, L"KIRA_R25_AFES_V3R10_CHILD_FAILED:%hs\n", error);
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
    if (!verify_python_dll_load(&rows[python_index], &winerror)) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "winerror=%lu",
                    (unsigned long)winerror);
        write_record("child", "python_dll_delayed_load_identity", "failed", detail);
        close_manifest_rows(rows, row_count);
        close_authority(&authority);
        return 56;
    }
    write_record("child", "python_dll_delayed_load_identity", "passed",
                 "loaded_exact_retained_dll_then_freed_no_python_api_called");
    write_record("child", "pre_outcome_stop", "reached",
                 "no_python_initialization_no_controller_no_reservation_no_child_no_blender");
    close_manifest_rows(rows, row_count);
    close_authority(&authority);
    fputs("KIRA_R25_AFES_V3R10_PROBE_REACHED_PRE_OUTCOME_STOP\n", stdout);
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
    wchar_t *parsed_root = NULL;
    char error[512];
    char detail[12288];
    char nonce[65];
    SECURITY_ATTRIBUTES pipe_security;
    HANDLE stdout_read = NULL;
    HANDLE stdout_write = NULL;
    HANDLE stderr_read = NULL;
    HANDLE stderr_write = NULL;
    HANDLE inherited_handles[3];
    STARTUPINFOEXW startup;
    PROCESS_INFORMATION process;
    SIZE_T attribute_size = 0U;
    wchar_t command[32768];
    size_t command_used = 0U;
    wchar_t handle_text[32];
    int index;
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
    error[0] = '\0';
    command[0] = L'\0';
    if (!write_record("observer", "wmain_entry", "entered",
                      "evidence_reserved_create_new_write_through")) return 20;
    if (!parse_arguments(argc, argv, 0, &parsed, error, sizeof(error))) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "reason=%s", error);
        write_record("observer", "argument_gate", "failed", detail);
        return 21;
    }
    parsed_root = canonical_full_path(parsed.project_root);
    if (parsed_root == NULL || _wcsicmp(parsed_root, derived_root) != 0) {
        write_record("observer", "argument_gate", "failed",
                     "project_root_identity_mismatch");
        free(parsed_root);
        return 21;
    }
    free(parsed_root);
    write_record("observer", "argument_gate", "passed", "exact_seven_option_contract");
    if (!initialize_authority(&parsed, derived_root, self_path, &authority,
                              error, sizeof(error))) {
        _snprintf_s(detail, sizeof(detail), _TRUNCATE, "reason=%s", error);
        write_record("observer", "fresh_audit_and_subject_gate", "failed", detail);
        return 22;
    }
    _snprintf_s(detail, sizeof(detail), _TRUNCATE, "self_sha256=%s",
                authority.self_sha256);
    write_record("observer", "fresh_audit_and_subject_gate", "passed", detail);
    if (!random_nonce(nonce)) {
        write_record("observer", "child_preparation", "failed", "nonce_generation_failed");
        close_authority(&authority);
        return 23;
    }
    memset(&pipe_security, 0, sizeof(pipe_security));
    pipe_security.nLength = sizeof(pipe_security);
    pipe_security.bInheritHandle = TRUE;
    if (!CreatePipe(&stdout_read, &stdout_write, &pipe_security, 0U) ||
        !CreatePipe(&stderr_read, &stderr_write, &pipe_security, 0U) ||
        !SetHandleInformation(stdout_read, HANDLE_FLAG_INHERIT, 0U) ||
        !SetHandleInformation(stderr_read, HANDLE_FLAG_INHERIT, 0U)) {
        write_record("observer", "child_preparation", "failed", "pipe_creation_failed");
        goto cleanup;
    }
    if (!append_command_argument(command, 32768U, &command_used, self_path)) goto command_fail;
    for (index = 1; index < argc; ++index) {
        if (!append_command_argument(command, 32768U, &command_used, argv[index])) goto command_fail;
    }
    if (!append_command_argument(command, 32768U, &command_used, L"--child-mode")) goto command_fail;
    {
        wchar_t nonce_wide[65];
        size_t converted = 0U;
        if (mbstowcs_s(&converted, nonce_wide, 65U, nonce, 64U) != 0 ||
            !append_command_argument(command, 32768U, &command_used, nonce_wide)) goto command_fail;
    }
    if (!append_command_argument(command, 32768U, &command_used, L"--evidence-handle")) goto command_fail;
    _snwprintf_s(handle_text, 32U, _TRUNCATE, L"%llu",
                 (unsigned long long)(uintptr_t)g_evidence);
    if (!append_command_argument(command, 32768U, &command_used, handle_text)) goto command_fail;
    startup.StartupInfo.cb = sizeof(startup);
    startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
    /* The child never reads stdin. Reusing the already allowlisted read/write
     * evidence handle avoids inheriting any ambient console or fourth handle. */
    startup.StartupInfo.hStdInput = g_evidence;
    startup.StartupInfo.hStdOutput = stdout_write;
    startup.StartupInfo.hStdError = stderr_write;
    inherited_handles[0] = g_evidence;
    inherited_handles[1] = stdout_write;
    inherited_handles[2] = stderr_write;
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
    _snprintf_s(detail, sizeof(detail), _TRUNCATE,
                "created_suspended=1;pid=%lu", (unsigned long)process.dwProcessId);
    if (!write_record("observer", "create_process", "passed", detail)) goto cleanup;
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
            "KIRA_R25_AFES_V3R10_PROBE_REACHED_PRE_OUTCOME_STOP\n") - 1U &&
        memcmp(stdout_capture,
               "KIRA_R25_AFES_V3R10_PROBE_REACHED_PRE_OUTCOME_STOP\n",
               sizeof("KIRA_R25_AFES_V3R10_PROBE_REACHED_PRE_OUTCOME_STOP\n") - 1U) == 0) {
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
    close_authority(&authority);
    secure_zero(nonce, sizeof(nonce));
    secure_zero(command, sizeof(command));
    return result;
}

static int find_child_surface(int argc, wchar_t **argv, uintptr_t *handle_out) {
    int index;
    int child_seen = 0;
    int handle_seen = 0;
    for (index = 1; index + 1 < argc; index += 2) {
        if (wcscmp(argv[index], L"--child-mode") == 0) child_seen = 1;
        if (wcscmp(argv[index], L"--evidence-handle") == 0) {
            handle_seen = parse_handle_value(argv[index + 1], handle_out);
        }
    }
    return child_seen && handle_seen;
}

int wmain(int argc, wchar_t **argv) {
    wchar_t *self_path = NULL;
    wchar_t *derived_root = NULL;
    uintptr_t inherited_handle = 0U;
    int child_surface;
    int result;
    if (!derive_project_root(&self_path, &derived_root)) {
        fwprintf(stderr, L"KIRA_R25_AFES_V3R10_REFUSED:self_location_invalid\n");
        return 10;
    }
    child_surface = find_child_surface(argc, argv, &inherited_handle);
    if (child_surface) {
        g_evidence = (HANDLE)inherited_handle;
        result = child_main(argc, argv, self_path, derived_root);
    } else {
        if (!reserve_evidence(derived_root)) {
            fwprintf(stderr,
                     L"KIRA_R25_AFES_V3R10_REFUSED:evidence_create_new_failed:%lu\n",
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
