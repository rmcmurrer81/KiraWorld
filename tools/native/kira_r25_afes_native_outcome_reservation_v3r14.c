/*
 * Kira R25 AFES v3r14 native outcome-reservation diagnostic.
 *
 * This append-only successor advances exactly one native stage beyond the
 * consumed-success v3r13 pre-outcome stop.  It verifies fixed predecessor and
 * candidate subjects, verifies a future different-agent audit, reserves one
 * evidence file and one outcome receipt with CREATE_NEW/write-through, writes
 * and reads back a reservation record, appends a completion record only after
 * exact readback, verifies the exact two-record file, and returns.  It does not
 * load Python, invoke a controller, AFES, Blender, or touch a Blend/body.
 *
 * Build only (do not run during authoring/audit):
 *   cl.exe /nologo /W4 /WX /O2 /MT /guard:cf /DUNICODE /D_UNICODE /std:c17 \
 *     tools\native\kira_r25_afes_native_outcome_reservation_v3r14.c \
 *     /Fo:tools\native\kira_r25_afes_native_outcome_reservation_v3r14.obj \
 *     /Fe:tools\native\kira_r25_afes_native_outcome_reservation_v3r14.exe \
 *     /link /guard:cf /WX bcrypt.lib
 */

#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <bcrypt.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#include "kira_r25_afes_native_outcome_reservation_v3r14_identity_anchor.h"

#pragma comment(lib, "bcrypt.lib")

#define SHA256_BYTES 32U
#define SHA256_HEX_BYTES 64U
#define SMALL_FILE_LIMIT 16384U
#define HASH_BUFFER_BYTES 65536U
#define RESERVATION_STATE_PENDING_READBACK 1U
#define COMPLETION_STATE_READBACK_VERIFIED 2U

static const wchar_t PROJECT_ROOT[] = L"C:\\Users\\robmc\\Kira";
static const wchar_t SELF_PATH[] =
    L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_native_outcome_reservation_v3r14.exe";
static const wchar_t IDENTITY_ANCHOR_PATH[] =
    L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_native_outcome_reservation_v3r14_identity_anchor.h";
static const wchar_t CONTRACT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_native_outcome_reservation_v3r14.json";
static const wchar_t SOURCE_PATH[] =
    L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_native_outcome_reservation_v3r14.c";
static const wchar_t STATIC_TEST_PATH[] =
    L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_native_outcome_reservation_v3r14_static.ps1";
static const wchar_t CONTROL_CHECKPOINT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R13_RUN_EVIDENCE_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r13_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t V3R13_AUDIT_CHECKPOINT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r13_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R13_ONE_SHOT_AUTHORITY_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r13_fresh_static_audit\\attempt_01\\ONE_SHOT_AUTHORITY.txt";
static const wchar_t V3R13_INDEPENDENT_AUDIT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r13_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R13_POST_SUCCESS_CHECKPOINT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r13_consumed_success_postmortem\\attempt_01\\CHECKPOINT.md";
static const wchar_t RETAINED_MANIFEST_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9\\RETAINED_NATIVE_LOCK_MANIFEST.tsv";
static const wchar_t FRESH_AUDIT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r14_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t FRESH_AUDIT_DIGEST_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r14_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t OUTPUT_PARENT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\\attempt_01";
static const wchar_t RUN_EVIDENCE_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t OUTCOME_RECEIPT_PATH[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\\attempt_01\\NATIVE_DIAGNOSTIC_OUTCOME.receipt.bin";

static const char AUDIT_MAGIC[] =
    "KIRA_R25_AFES_NATIVE_OUTCOME_RESERVATION_AUDIT_V3R14\t1";
static const char AUDIT_DECISION[] =
    "ACCEPTED_FOR_ONE_BOUNDED_NATIVE_OUTCOME_RESERVATION_ONLY";

static const char EVIDENCE_ENTRY[] =
    "{\"schema\":\"kira.r25.afes.v3r14.native_stage.v1\",\"stage\":\"wmain_entry\",\"status\":\"entered\",\"detail\":\"zero_arguments_exact_self_and_subjects_pending\"}\n";
static const char EVIDENCE_SUBJECTS[] =
    "{\"schema\":\"kira.r25.afes.v3r14.native_stage.v1\",\"stage\":\"subject_and_audit_gate\",\"status\":\"passed\",\"detail\":\"exact_v3r14_and_consumed_v3r13_bytes_different_auditor\"}\n";
static const char EVIDENCE_OUTCOME_RESERVED[] =
    "{\"schema\":\"kira.r25.afes.v3r14.native_stage.v1\",\"stage\":\"native_outcome_reservation\",\"status\":\"passed\",\"detail\":\"CREATE_NEW_write_through_reservation_record_pending_readback\"}\n";
static const char EVIDENCE_RESERVATION_READBACK[] =
    "{\"schema\":\"kira.r25.afes.v3r14.native_stage.v1\",\"stage\":\"reservation_record_readback\",\"status\":\"passed\",\"detail\":\"same_handle_exact_bytes_and_file_identity\"}\n";
static const char EVIDENCE_COMPLETION_APPENDED[] =
    "{\"schema\":\"kira.r25.afes.v3r14.native_stage.v1\",\"stage\":\"completion_record_append\",\"status\":\"passed\",\"detail\":\"completion_appended_only_after_reservation_readback\"}\n";
static const char EVIDENCE_TERMINAL[] =
    "{\"schema\":\"kira.r25.afes.v3r14.native_stage.v1\",\"stage\":\"diagnostic_terminal\",\"status\":\"complete\",\"detail\":\"two_record_receipt_exact_no_python_controller_afes_blender_body\"}\n";

typedef struct SUBJECT_BINDING {
    const wchar_t *path;
    ULONGLONG bytes;
    const char *sha256;
    const char *label;
} SUBJECT_BINDING;

#pragma pack(push, 1)
typedef struct V3R14_RESERVATION_RECORD {
    unsigned char magic[40];
    uint32_t schema_version;
    uint32_t record_type;
    uint32_t record_bytes;
    uint32_t state;
    unsigned char executable_sha256[SHA256_BYTES];
    unsigned char audit_sha256[SHA256_BYTES];
    unsigned char v3r13_run_evidence_sha256[SHA256_BYTES];
    unsigned char retained_manifest_sha256[SHA256_BYTES];
    unsigned char random_nonce[SHA256_BYTES];
    uint64_t receipt_volume_serial;
    unsigned char receipt_file_id[16];
    uint64_t evidence_volume_serial;
    unsigned char evidence_file_id[16];
} V3R14_RESERVATION_RECORD;

typedef struct V3R14_COMPLETION_RECORD {
    unsigned char magic[40];
    uint32_t schema_version;
    uint32_t record_type;
    uint32_t record_bytes;
    uint32_t state;
    unsigned char reservation_record_sha256[SHA256_BYTES];
    unsigned char executable_sha256[SHA256_BYTES];
    unsigned char audit_sha256[SHA256_BYTES];
    unsigned char v3r13_run_evidence_sha256[SHA256_BYTES];
    uint64_t receipt_volume_serial;
    unsigned char receipt_file_id[16];
    uint64_t evidence_volume_serial;
    unsigned char evidence_file_id[16];
} V3R14_COMPLETION_RECORD;
#pragma pack(pop)

static int lowercase_hex(const char *value) {
    size_t index;
    if (value == NULL || strlen(value) != SHA256_HEX_BYTES) return 0;
    for (index = 0U; index < SHA256_HEX_BYTES; ++index) {
        const char character = value[index];
        if (!((character >= '0' && character <= '9') ||
              (character >= 'a' && character <= 'f'))) return 0;
    }
    return 1;
}

static int hex_to_bytes(const char *hex, unsigned char output[SHA256_BYTES]) {
    size_t index;
    if (!lowercase_hex(hex)) return 0;
    for (index = 0U; index < SHA256_BYTES; ++index) {
        unsigned char high;
        unsigned char low;
        const char a = hex[index * 2U];
        const char b = hex[index * 2U + 1U];
        high = (unsigned char)((a <= '9') ? (a - '0') : (a - 'a' + 10));
        low = (unsigned char)((b <= '9') ? (b - '0') : (b - 'a' + 10));
        output[index] = (unsigned char)((high << 4U) | low);
    }
    return 1;
}

static void bytes_to_hex(
    const unsigned char bytes[SHA256_BYTES], char output[SHA256_HEX_BYTES + 1U]
) {
    static const char digits[] = "0123456789abcdef";
    size_t index;
    for (index = 0U; index < SHA256_BYTES; ++index) {
        output[index * 2U] = digits[(bytes[index] >> 4U) & 0x0fU];
        output[index * 2U + 1U] = digits[bytes[index] & 0x0fU];
    }
    output[SHA256_HEX_BYTES] = '\0';
}

static int sha256_begin(
    BCRYPT_ALG_HANDLE *algorithm,
    BCRYPT_HASH_HANDLE *hash,
    unsigned char **object_buffer
) {
    DWORD object_bytes = 0U;
    DWORD result_bytes = 0U;
    NTSTATUS status;
    *algorithm = NULL;
    *hash = NULL;
    *object_buffer = NULL;
    status = BCryptOpenAlgorithmProvider(
        algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U
    );
    if (status < 0) return 0;
    status = BCryptGetProperty(
        *algorithm,
        BCRYPT_OBJECT_LENGTH,
        (PUCHAR)&object_bytes,
        (ULONG)sizeof(object_bytes),
        &result_bytes,
        0U
    );
    if (status < 0 || result_bytes != sizeof(object_bytes) || object_bytes == 0U) {
        BCryptCloseAlgorithmProvider(*algorithm, 0U);
        *algorithm = NULL;
        return 0;
    }
    *object_buffer = (unsigned char *)HeapAlloc(
        GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)object_bytes
    );
    if (*object_buffer == NULL) {
        BCryptCloseAlgorithmProvider(*algorithm, 0U);
        *algorithm = NULL;
        return 0;
    }
    status = BCryptCreateHash(
        *algorithm, hash, *object_buffer, object_bytes, NULL, 0U, 0U
    );
    if (status < 0) {
        HeapFree(GetProcessHeap(), 0U, *object_buffer);
        *object_buffer = NULL;
        BCryptCloseAlgorithmProvider(*algorithm, 0U);
        *algorithm = NULL;
        return 0;
    }
    return 1;
}

static void sha256_abort(
    BCRYPT_ALG_HANDLE algorithm,
    BCRYPT_HASH_HANDLE hash,
    unsigned char *object_buffer
) {
    if (hash != NULL) BCryptDestroyHash(hash);
    if (object_buffer != NULL) {
        SecureZeroMemory(object_buffer, 1U);
        HeapFree(GetProcessHeap(), 0U, object_buffer);
    }
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
}

static int sha256_memory(
    const unsigned char *data,
    size_t data_bytes,
    unsigned char digest[SHA256_BYTES]
) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char *object_buffer = NULL;
    NTSTATUS status;
    if (data == NULL || data_bytes > (size_t)ULONG_MAX) return 0;
    if (!sha256_begin(&algorithm, &hash, &object_buffer)) return 0;
    status = BCryptHashData(hash, (PUCHAR)data, (ULONG)data_bytes, 0U);
    if (status >= 0) {
        status = BCryptFinishHash(hash, digest, SHA256_BYTES, 0U);
    }
    sha256_abort(algorithm, hash, object_buffer);
    return status >= 0;
}

static int handle_is_regular_nonreparse(HANDLE file, ULONGLONG *bytes) {
    FILE_ATTRIBUTE_TAG_INFO attributes;
    FILE_STANDARD_INFO standard;
    if (!GetFileInformationByHandleEx(
            file, FileAttributeTagInfo, &attributes, (DWORD)sizeof(attributes))) {
        return 0;
    }
    if ((attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U ||
        (attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0U) {
        return 0;
    }
    if (!GetFileInformationByHandleEx(
            file, FileStandardInfo, &standard, (DWORD)sizeof(standard))) {
        return 0;
    }
    if (standard.EndOfFile.QuadPart < 0) return 0;
    *bytes = (ULONGLONG)standard.EndOfFile.QuadPart;
    return 1;
}

static int sha256_open_handle(
    HANDLE file, unsigned char digest[SHA256_BYTES]
) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char *object_buffer = NULL;
    unsigned char *buffer = NULL;
    LARGE_INTEGER zero;
    NTSTATUS status = (NTSTATUS)-1;
    int success = 0;
    zero.QuadPart = 0;
    if (!SetFilePointerEx(file, zero, NULL, FILE_BEGIN)) return 0;
    if (!sha256_begin(&algorithm, &hash, &object_buffer)) return 0;
    buffer = (unsigned char *)HeapAlloc(
        GetProcessHeap(), 0U, (SIZE_T)HASH_BUFFER_BYTES
    );
    if (buffer == NULL) goto cleanup;
    for (;;) {
        DWORD read_bytes = 0U;
        if (!ReadFile(file, buffer, HASH_BUFFER_BYTES, &read_bytes, NULL)) goto cleanup;
        if (read_bytes == 0U) break;
        status = BCryptHashData(hash, buffer, read_bytes, 0U);
        if (status < 0) goto cleanup;
    }
    status = BCryptFinishHash(hash, digest, SHA256_BYTES, 0U);
    if (status < 0) goto cleanup;
    success = 1;
cleanup:
    if (buffer != NULL) {
        SecureZeroMemory(buffer, HASH_BUFFER_BYTES);
        HeapFree(GetProcessHeap(), 0U, buffer);
    }
    sha256_abort(algorithm, hash, object_buffer);
    return success;
}

static int hash_file_exact(
    const wchar_t *path,
    ULONGLONG expected_bytes,
    const char *expected_sha256,
    unsigned char *digest_output
) {
    HANDLE file;
    ULONGLONG actual_bytes = 0ULL;
    unsigned char digest[SHA256_BYTES];
    char hex[SHA256_HEX_BYTES + 1U];
    int success = 0;
    if (path == NULL || !lowercase_hex(expected_sha256)) return 0;
    file = CreateFileW(
        path,
        GENERIC_READ,
        FILE_SHARE_READ,
        NULL,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN |
            FILE_FLAG_OPEN_REPARSE_POINT,
        NULL
    );
    if (file == INVALID_HANDLE_VALUE) return 0;
    if (!handle_is_regular_nonreparse(file, &actual_bytes) ||
        actual_bytes != expected_bytes ||
        !sha256_open_handle(file, digest)) {
        CloseHandle(file);
        return 0;
    }
    bytes_to_hex(digest, hex);
    if (strcmp(hex, expected_sha256) == 0) {
        if (digest_output != NULL) memcpy(digest_output, digest, SHA256_BYTES);
        success = 1;
    }
    SecureZeroMemory(digest, sizeof(digest));
    CloseHandle(file);
    return success;
}

static int hash_file_unbound(
    const wchar_t *path,
    ULONGLONG maximum_bytes,
    ULONGLONG *actual_bytes_output,
    unsigned char digest_output[SHA256_BYTES]
) {
    HANDLE file;
    ULONGLONG actual_bytes = 0ULL;
    int success = 0;
    if (path == NULL || maximum_bytes == 0ULL ||
        actual_bytes_output == NULL || digest_output == NULL) return 0;
    file = CreateFileW(
        path,
        GENERIC_READ,
        FILE_SHARE_READ,
        NULL,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN |
            FILE_FLAG_OPEN_REPARSE_POINT,
        NULL
    );
    if (file == INVALID_HANDLE_VALUE) return 0;
    if (handle_is_regular_nonreparse(file, &actual_bytes) &&
        actual_bytes > 0ULL && actual_bytes <= maximum_bytes &&
        sha256_open_handle(file, digest_output)) {
        *actual_bytes_output = actual_bytes;
        success = 1;
    }
    CloseHandle(file);
    return success;
}

static int read_small_file(
    const wchar_t *path,
    unsigned char **data_output,
    DWORD *bytes_output,
    unsigned char digest_output[SHA256_BYTES]
) {
    HANDLE file;
    ULONGLONG size64 = 0ULL;
    unsigned char *data = NULL;
    DWORD read_bytes = 0U;
    int success = 0;
    *data_output = NULL;
    *bytes_output = 0U;
    file = CreateFileW(
        path,
        GENERIC_READ,
        FILE_SHARE_READ,
        NULL,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
        NULL
    );
    if (file == INVALID_HANDLE_VALUE) return 0;
    if (!handle_is_regular_nonreparse(file, &size64) ||
        size64 == 0ULL || size64 > (ULONGLONG)SMALL_FILE_LIMIT) {
        CloseHandle(file);
        return 0;
    }
    data = (unsigned char *)HeapAlloc(
        GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)size64 + 1U
    );
    if (data == NULL) {
        CloseHandle(file);
        return 0;
    }
    if (!ReadFile(file, data, (DWORD)size64, &read_bytes, NULL) ||
        read_bytes != (DWORD)size64 ||
        !sha256_memory(data, (size_t)read_bytes, digest_output)) {
        goto cleanup;
    }
    data[read_bytes] = '\0';
    *data_output = data;
    *bytes_output = read_bytes;
    data = NULL;
    success = 1;
cleanup:
    if (data != NULL) {
        SecureZeroMemory(data, (SIZE_T)size64 + 1U);
        HeapFree(GetProcessHeap(), 0U, data);
    }
    CloseHandle(file);
    return success;
}

static int consume_exact_line(
    char **cursor_io,
    const char *end,
    const char *expected_key,
    char *value_output,
    size_t value_capacity
) {
    char *cursor = *cursor_io;
    char *newline;
    char *tab;
    size_t value_bytes;
    if (cursor >= end) return 0;
    newline = (char *)memchr(cursor, '\n', (size_t)(end - cursor));
    if (newline == NULL) return 0;
    if (memchr(cursor, '\r', (size_t)(newline - cursor)) != NULL ||
        memchr(cursor, '\0', (size_t)(newline - cursor)) != NULL) return 0;
    tab = (char *)memchr(cursor, '\t', (size_t)(newline - cursor));
    if (tab == NULL ||
        memchr(tab + 1, '\t', (size_t)(newline - (tab + 1))) != NULL ||
        (size_t)(tab - cursor) != strlen(expected_key) ||
        memcmp(cursor, expected_key, strlen(expected_key)) != 0) return 0;
    value_bytes = (size_t)(newline - (tab + 1));
    if (value_bytes == 0U || value_bytes + 1U > value_capacity) return 0;
    memcpy(value_output, tab + 1, value_bytes);
    value_output[value_bytes] = '\0';
    *cursor_io = newline + 1;
    return 1;
}

static int consume_magic_line(char **cursor_io, const char *end) {
    char *cursor = *cursor_io;
    char *newline;
    size_t bytes;
    newline = (char *)memchr(cursor, '\n', (size_t)(end - cursor));
    if (newline == NULL) return 0;
    bytes = (size_t)(newline - cursor);
    if (bytes != strlen(AUDIT_MAGIC) ||
        memcmp(cursor, AUDIT_MAGIC, bytes) != 0) return 0;
    *cursor_io = newline + 1;
    return 1;
}

static int verify_fresh_audit(
    const unsigned char self_sha256[SHA256_BYTES],
    unsigned char audit_sha256_output[SHA256_BYTES]
) {
    unsigned char *audit = NULL;
    unsigned char *sidecar = NULL;
    DWORD audit_bytes = 0U;
    DWORD sidecar_bytes = 0U;
    unsigned char audit_sha256[SHA256_BYTES];
    unsigned char ignored[SHA256_BYTES];
    unsigned char identity_anchor_sha256[SHA256_BYTES];
    ULONGLONG identity_anchor_bytes = 0ULL;
    char audit_hex[SHA256_HEX_BYTES + 1U];
    char self_hex[SHA256_HEX_BYTES + 1U];
    char identity_hex[SHA256_HEX_BYTES + 1U];
    char values[15][129];
    static const char *keys[15] = {
        "decision",
        "auditor",
        "author",
        "native_executable_sha256",
        "identity_anchor_sha256",
        "contract_sha256",
        "native_source_sha256",
        "static_test_sha256",
        "runtime_control_checkpoint_sha256",
        "v3r13_run_evidence_sha256",
        "v3r13_audit_checkpoint_sha256",
        "v3r13_one_shot_authority_sha256",
        "v3r13_independent_audit_sha256",
        "v3r13_post_success_checkpoint_sha256",
        "retained_manifest_sha256"
    };
    const char *expected[15];
    char *cursor;
    const char *end;
    size_t index;
    int success = 0;

    if (!read_small_file(FRESH_AUDIT_PATH, &audit, &audit_bytes, audit_sha256) ||
        !read_small_file(FRESH_AUDIT_DIGEST_PATH, &sidecar, &sidecar_bytes, ignored)) {
        goto cleanup;
    }
    if (sidecar_bytes != SHA256_HEX_BYTES + 1U ||
        sidecar[SHA256_HEX_BYTES] != '\n') goto cleanup;
    bytes_to_hex(audit_sha256, audit_hex);
    if (memcmp(sidecar, audit_hex, SHA256_HEX_BYTES) != 0) goto cleanup;
    if (!hash_file_unbound(
            IDENTITY_ANCHOR_PATH,
            65536ULL,
            &identity_anchor_bytes,
            identity_anchor_sha256)) goto cleanup;
    bytes_to_hex(self_sha256, self_hex);
    bytes_to_hex(identity_anchor_sha256, identity_hex);

    expected[0] = AUDIT_DECISION;
    expected[1] = NULL;
    expected[2] = V3R14_AUTHOR_ID;
    expected[3] = self_hex;
    expected[4] = identity_hex;
    expected[5] = V3R14_CONTRACT_SHA256;
    expected[6] = V3R14_SOURCE_SHA256;
    expected[7] = V3R14_STATIC_TEST_SHA256;
    expected[8] = V3R14_CONTROL_CHECKPOINT_SHA256;
    expected[9] = V3R14_V3R13_RUN_EVIDENCE_SHA256;
    expected[10] = V3R14_V3R13_AUDIT_CHECKPOINT_SHA256;
    expected[11] = V3R14_V3R13_ONE_SHOT_AUTHORITY_SHA256;
    expected[12] = V3R14_V3R13_INDEPENDENT_AUDIT_SHA256;
    expected[13] = V3R14_V3R13_POST_SUCCESS_CHECKPOINT_SHA256;
    expected[14] = V3R14_RETAINED_MANIFEST_SHA256;

    cursor = (char *)audit;
    end = (const char *)audit + audit_bytes;
    if (!consume_magic_line(&cursor, end)) goto cleanup;
    for (index = 0U; index < 15U; ++index) {
        if (!consume_exact_line(
                &cursor, end, keys[index], values[index], sizeof(values[index]))) {
            goto cleanup;
        }
    }
    if (cursor != end) goto cleanup;
    if (strcmp(values[0], expected[0]) != 0 ||
        strcmp(values[2], expected[2]) != 0 ||
        strcmp(values[1], values[2]) == 0 ||
        values[1][0] == '\0') goto cleanup;
    for (index = 3U; index < 15U; ++index) {
        if (!lowercase_hex(values[index]) ||
            strcmp(values[index], expected[index]) != 0) goto cleanup;
    }
    memcpy(audit_sha256_output, audit_sha256, SHA256_BYTES);
    success = 1;
cleanup:
    if (audit != NULL) {
        SecureZeroMemory(audit, (SIZE_T)audit_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, audit);
    }
    if (sidecar != NULL) {
        SecureZeroMemory(sidecar, (SIZE_T)sidecar_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, sidecar);
    }
    SecureZeroMemory(audit_sha256, sizeof(audit_sha256));
    SecureZeroMemory(identity_anchor_sha256, sizeof(identity_anchor_sha256));
    return success;
}

static int append_evidence(HANDLE evidence, const char *line) {
    size_t length;
    DWORD written = 0U;
    if (evidence == NULL || evidence == INVALID_HANDLE_VALUE || line == NULL) return 0;
    length = strlen(line);
    if (length == 0U || length > (size_t)MAXDWORD) return 0;
    if (!WriteFile(evidence, line, (DWORD)length, &written, NULL) ||
        written != (DWORD)length ||
        !FlushFileBuffers(evidence)) return 0;
    return 1;
}

static int get_file_identity(HANDLE file, FILE_ID_INFO *identity) {
    if (identity == NULL) return 0;
    SecureZeroMemory(identity, sizeof(*identity));
    return GetFileInformationByHandleEx(
        file, FileIdInfo, identity, (DWORD)sizeof(*identity)
    ) != FALSE;
}

static int same_file_identity(
    const FILE_ID_INFO *left, const FILE_ID_INFO *right
) {
    return left != NULL && right != NULL &&
        left->VolumeSerialNumber == right->VolumeSerialNumber &&
        memcmp(left->FileId.Identifier, right->FileId.Identifier,
               sizeof(left->FileId.Identifier)) == 0;
}

static int final_path_matches(HANDLE file, const wchar_t *canonical_path) {
    wchar_t actual[32768];
    wchar_t expected[32768];
    DWORD actual_length;
    size_t canonical_length;
    if (file == NULL || file == INVALID_HANDLE_VALUE || canonical_path == NULL) {
        return 0;
    }
    canonical_length = wcslen(canonical_path);
    if (canonical_length + 5U > _countof(expected)) return 0;
    memcpy(expected, L"\\\\?\\", 4U * sizeof(wchar_t));
    memcpy(expected + 4U, canonical_path,
           (canonical_length + 1U) * sizeof(wchar_t));
    actual_length = GetFinalPathNameByHandleW(
        file, actual, (DWORD)_countof(actual),
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS
    );
    if (actual_length == 0U || actual_length >= (DWORD)_countof(actual)) return 0;
    return _wcsicmp(actual, expected) == 0;
}

static int seek_absolute(HANDLE file, LONGLONG offset) {
    LARGE_INTEGER distance;
    distance.QuadPart = offset;
    return SetFilePointerEx(file, distance, NULL, FILE_BEGIN) != FALSE;
}

static int read_exact(HANDLE file, void *buffer, DWORD bytes) {
    unsigned char *cursor = (unsigned char *)buffer;
    DWORD total = 0U;
    while (total < bytes) {
        DWORD chunk = 0U;
        if (!ReadFile(file, cursor + total, bytes - total, &chunk, NULL) ||
            chunk == 0U) return 0;
        total += chunk;
    }
    return 1;
}

static int verify_output_parent(void) {
    HANDLE directory;
    FILE_ATTRIBUTE_TAG_INFO attributes;
    int success = 0;
    directory = CreateFileW(
        OUTPUT_PARENT_PATH,
        FILE_ADD_FILE | FILE_READ_ATTRIBUTES | SYNCHRONIZE,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
        NULL
    );
    if (directory == INVALID_HANDLE_VALUE) return 0;
    if (GetFileInformationByHandleEx(
            directory, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0U &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0U) {
        success = 1;
    }
    CloseHandle(directory);
    return success;
}

static int write_and_verify_outcome(
    HANDLE evidence,
    const unsigned char self_sha256[SHA256_BYTES],
    const unsigned char audit_sha256[SHA256_BYTES],
    const FILE_ID_INFO *evidence_identity
) {
    HANDLE receipt = INVALID_HANDLE_VALUE;
    FILE_ID_INFO receipt_identity_before;
    FILE_ID_INFO receipt_identity_after;
    V3R14_RESERVATION_RECORD reservation;
    V3R14_RESERVATION_RECORD reservation_readback;
    V3R14_COMPLETION_RECORD completion;
    V3R14_COMPLETION_RECORD completion_readback;
    unsigned char reservation_sha256[SHA256_BYTES];
    LARGE_INTEGER file_size;
    DWORD written = 0U;
    unsigned char extra = 0U;
    DWORD extra_read = 0U;
    int success = 0;

    SecureZeroMemory(&reservation, sizeof(reservation));
    SecureZeroMemory(&reservation_readback, sizeof(reservation_readback));
    SecureZeroMemory(&completion, sizeof(completion));
    SecureZeroMemory(&completion_readback, sizeof(completion_readback));
    SecureZeroMemory(&receipt_identity_before, sizeof(receipt_identity_before));
    SecureZeroMemory(&receipt_identity_after, sizeof(receipt_identity_after));

    receipt = CreateFileW(
        OUTCOME_RECEIPT_PATH,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ,
        NULL,
        CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
            FILE_FLAG_OPEN_REPARSE_POINT,
        NULL
    );
    if (receipt == INVALID_HANDLE_VALUE) goto cleanup;
    if (!final_path_matches(receipt, OUTCOME_RECEIPT_PATH) ||
        !get_file_identity(receipt, &receipt_identity_before)) goto cleanup;

    memcpy(reservation.magic, "KIRA_R25_AFES_V3R14_RESERVATION", 33U);
    reservation.schema_version = 1U;
    reservation.record_type = 1U;
    reservation.record_bytes = (uint32_t)sizeof(reservation);
    reservation.state = RESERVATION_STATE_PENDING_READBACK;
    memcpy(reservation.executable_sha256, self_sha256, SHA256_BYTES);
    memcpy(reservation.audit_sha256, audit_sha256, SHA256_BYTES);
    if (!hex_to_bytes(
            V3R14_V3R13_RUN_EVIDENCE_SHA256,
            reservation.v3r13_run_evidence_sha256) ||
        !hex_to_bytes(
            V3R14_RETAINED_MANIFEST_SHA256,
            reservation.retained_manifest_sha256) ||
        BCryptGenRandom(
            NULL, reservation.random_nonce, SHA256_BYTES,
            BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) goto cleanup;
    reservation.receipt_volume_serial = receipt_identity_before.VolumeSerialNumber;
    memcpy(
        reservation.receipt_file_id,
        receipt_identity_before.FileId.Identifier,
        sizeof(reservation.receipt_file_id)
    );
    reservation.evidence_volume_serial = evidence_identity->VolumeSerialNumber;
    memcpy(
        reservation.evidence_file_id,
        evidence_identity->FileId.Identifier,
        sizeof(reservation.evidence_file_id)
    );

    if (!WriteFile(
            receipt, &reservation, (DWORD)sizeof(reservation), &written, NULL) ||
        written != (DWORD)sizeof(reservation) ||
        !FlushFileBuffers(receipt)) goto cleanup;
    if (!append_evidence(evidence, EVIDENCE_OUTCOME_RESERVED)) goto cleanup;
    if (!GetFileSizeEx(receipt, &file_size) ||
        file_size.QuadPart != (LONGLONG)sizeof(reservation) ||
        !seek_absolute(receipt, 0LL) ||
        !read_exact(receipt, &reservation_readback, (DWORD)sizeof(reservation_readback)) ||
        memcmp(&reservation, &reservation_readback, sizeof(reservation)) != 0 ||
        !get_file_identity(receipt, &receipt_identity_after) ||
        !same_file_identity(&receipt_identity_before, &receipt_identity_after)) goto cleanup;
    if (!append_evidence(evidence, EVIDENCE_RESERVATION_READBACK)) goto cleanup;
    if (!sha256_memory(
            (const unsigned char *)&reservation,
            sizeof(reservation), reservation_sha256)) goto cleanup;

    memcpy(completion.magic, "KIRA_R25_AFES_V3R14_COMPLETION", 32U);
    completion.schema_version = 1U;
    completion.record_type = 2U;
    completion.record_bytes = (uint32_t)sizeof(completion);
    completion.state = COMPLETION_STATE_READBACK_VERIFIED;
    memcpy(
        completion.reservation_record_sha256,
        reservation_sha256,
        SHA256_BYTES
    );
    memcpy(completion.executable_sha256, self_sha256, SHA256_BYTES);
    memcpy(completion.audit_sha256, audit_sha256, SHA256_BYTES);
    if (!hex_to_bytes(
            V3R14_V3R13_RUN_EVIDENCE_SHA256,
            completion.v3r13_run_evidence_sha256)) goto cleanup;
    completion.receipt_volume_serial = receipt_identity_before.VolumeSerialNumber;
    memcpy(
        completion.receipt_file_id,
        receipt_identity_before.FileId.Identifier,
        sizeof(completion.receipt_file_id)
    );
    completion.evidence_volume_serial = evidence_identity->VolumeSerialNumber;
    memcpy(
        completion.evidence_file_id,
        evidence_identity->FileId.Identifier,
        sizeof(completion.evidence_file_id)
    );
    if (!seek_absolute(receipt, (LONGLONG)sizeof(reservation)) ||
        !WriteFile(
            receipt, &completion, (DWORD)sizeof(completion), &written, NULL) ||
        written != (DWORD)sizeof(completion) ||
        !FlushFileBuffers(receipt)) goto cleanup;
    if (!append_evidence(evidence, EVIDENCE_COMPLETION_APPENDED)) goto cleanup;

    if (!GetFileSizeEx(receipt, &file_size) ||
        file_size.QuadPart !=
            (LONGLONG)(sizeof(reservation) + sizeof(completion)) ||
        !seek_absolute(receipt, 0LL) ||
        !read_exact(receipt, &reservation_readback, (DWORD)sizeof(reservation_readback)) ||
        !read_exact(receipt, &completion_readback, (DWORD)sizeof(completion_readback)) ||
        ReadFile(receipt, &extra, 1U, &extra_read, NULL) == FALSE ||
        extra_read != 0U ||
        memcmp(&reservation, &reservation_readback, sizeof(reservation)) != 0 ||
        memcmp(&completion, &completion_readback, sizeof(completion)) != 0 ||
        !get_file_identity(receipt, &receipt_identity_after) ||
        !same_file_identity(&receipt_identity_before, &receipt_identity_after)) goto cleanup;
    success = 1;
cleanup:
    SecureZeroMemory(&reservation, sizeof(reservation));
    SecureZeroMemory(&reservation_readback, sizeof(reservation_readback));
    SecureZeroMemory(&completion, sizeof(completion));
    SecureZeroMemory(&completion_readback, sizeof(completion_readback));
    SecureZeroMemory(reservation_sha256, sizeof(reservation_sha256));
    if (receipt != INVALID_HANDLE_VALUE) CloseHandle(receipt);
    return success;
}

int wmain(int argc, wchar_t **argv) {
    wchar_t current_directory[MAX_PATH];
    wchar_t module_path[MAX_PATH];
    DWORD current_length;
    DWORD module_length;
    unsigned char self_sha256[SHA256_BYTES];
    unsigned char audit_sha256[SHA256_BYTES];
    ULONGLONG self_bytes = 0ULL;
    HANDLE evidence = INVALID_HANDLE_VALUE;
    FILE_ID_INFO evidence_identity;
    size_t index;
    int result = 1;
    static const SUBJECT_BINDING subjects[] = {
        {CONTRACT_PATH, V3R14_CONTRACT_BYTES, V3R14_CONTRACT_SHA256, "contract"},
        {SOURCE_PATH, V3R14_SOURCE_BYTES, V3R14_SOURCE_SHA256, "source"},
        {STATIC_TEST_PATH, V3R14_STATIC_TEST_BYTES, V3R14_STATIC_TEST_SHA256, "static_test"},
        {CONTROL_CHECKPOINT_PATH, V3R14_CONTROL_CHECKPOINT_BYTES, V3R14_CONTROL_CHECKPOINT_SHA256, "control_checkpoint"},
        {V3R13_RUN_EVIDENCE_PATH, V3R14_V3R13_RUN_EVIDENCE_BYTES, V3R14_V3R13_RUN_EVIDENCE_SHA256, "v3r13_run_evidence"},
        {V3R13_AUDIT_CHECKPOINT_PATH, V3R14_V3R13_AUDIT_CHECKPOINT_BYTES, V3R14_V3R13_AUDIT_CHECKPOINT_SHA256, "v3r13_audit_checkpoint"},
        {V3R13_ONE_SHOT_AUTHORITY_PATH, V3R14_V3R13_ONE_SHOT_AUTHORITY_BYTES, V3R14_V3R13_ONE_SHOT_AUTHORITY_SHA256, "v3r13_one_shot_authority"},
        {V3R13_INDEPENDENT_AUDIT_PATH, V3R14_V3R13_INDEPENDENT_AUDIT_BYTES, V3R14_V3R13_INDEPENDENT_AUDIT_SHA256, "v3r13_independent_audit"},
        {V3R13_POST_SUCCESS_CHECKPOINT_PATH, V3R14_V3R13_POST_SUCCESS_CHECKPOINT_BYTES, V3R14_V3R13_POST_SUCCESS_CHECKPOINT_SHA256, "v3r13_post_success_checkpoint"},
        {RETAINED_MANIFEST_PATH, V3R14_RETAINED_MANIFEST_BYTES, V3R14_RETAINED_MANIFEST_SHA256, "retained_manifest"}
    };
    (void)argv;
    SecureZeroMemory(self_sha256, sizeof(self_sha256));
    SecureZeroMemory(audit_sha256, sizeof(audit_sha256));
    SecureZeroMemory(&evidence_identity, sizeof(evidence_identity));

    if (argc != 1) return 2;
    current_length = GetCurrentDirectoryW((DWORD)_countof(current_directory), current_directory);
    if (current_length == 0U || current_length >= (DWORD)_countof(current_directory) ||
        wcscmp(current_directory, PROJECT_ROOT) != 0) return 3;
    module_length = GetModuleFileNameW(
        NULL, module_path, (DWORD)_countof(module_path)
    );
    if (module_length == 0U || module_length >= (DWORD)_countof(module_path) ||
        wcscmp(module_path, SELF_PATH) != 0 ||
        !hash_file_unbound(SELF_PATH, 4194304ULL, &self_bytes, self_sha256)) {
        return 4;
    }
    for (index = 0U; index < _countof(subjects); ++index) {
        if (!hash_file_exact(
                subjects[index].path,
                subjects[index].bytes,
                subjects[index].sha256,
                NULL)) {
            fwprintf(stderr, L"V3R14_SUBJECT_REFUSED:%S\n", subjects[index].label);
            return 5;
        }
    }
    if (!verify_fresh_audit(self_sha256, audit_sha256) ||
        !verify_output_parent()) return 6;

    evidence = CreateFileW(
        RUN_EVIDENCE_PATH,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ,
        NULL,
        CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
            FILE_FLAG_OPEN_REPARSE_POINT,
        NULL
    );
    if (evidence == INVALID_HANDLE_VALUE) return 7;
    if (!final_path_matches(evidence, RUN_EVIDENCE_PATH) ||
        !get_file_identity(evidence, &evidence_identity) ||
        !append_evidence(evidence, EVIDENCE_ENTRY) ||
        !append_evidence(evidence, EVIDENCE_SUBJECTS)) goto cleanup;
    if (!write_and_verify_outcome(
            evidence, self_sha256, audit_sha256, &evidence_identity)) goto cleanup;
    if (!append_evidence(evidence, EVIDENCE_TERMINAL)) goto cleanup;
    result = 0;
cleanup:
    SecureZeroMemory(self_sha256, sizeof(self_sha256));
    SecureZeroMemory(audit_sha256, sizeof(audit_sha256));
    if (evidence != INVALID_HANDLE_VALUE) CloseHandle(evidence);
    return result;
}
