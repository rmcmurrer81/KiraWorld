#define WIN32_LEAN_AND_MEAN
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#include "kira_r25_afes_contract_lock_diagnostic_v3r17_identity_anchor.h"

#pragma comment(lib, "bcrypt.lib")

#define SHA_BYTES 32U
#define SHA_HEX 64U
#define SMALL_LIMIT 65536ULL
#define EVIDENCE_LIMIT 8192U
#define RECEIPT_MAGIC_BYTES 48U

static const wchar_t PROJECT_ROOT[] = L"C:\\Users\\robmc\\Kira";
static const wchar_t SELF_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_contract_lock_diagnostic_v3r17.exe";
static const wchar_t ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_contract_lock_diagnostic_v3r17_identity_anchor.h";
static const wchar_t CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_contract_lock_diagnostic_v3r17.json";
static const wchar_t SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_contract_lock_diagnostic_v3r17.c";
static const wchar_t TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_contract_lock_diagnostic_v3r17_static.ps1";
static const wchar_t CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R15_POSTMORTEM_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r15_consumed_failure_postmortem\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R15_RECHECK_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r15_consumed_failure_postmortem\\attempt_01\\READ_ONLY_CONTRACT_RECHECK.json";
static const wchar_t V3R15_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r15_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R15_TARGET_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r15.json";
static const wchar_t OUTPUT_PARENT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01";
static const wchar_t EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01\\CONTRACT_LOCK_DIAGNOSTIC_OUTCOME.receipt.bin";
static const wchar_t AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t AUDIT_DIGEST_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";

static const char AUDIT_MAGIC[] = "KIRA_R25_AFES_CONTRACT_LOCK_DIAGNOSTIC_AUDIT_V3R17\t1";
static const char AUDIT_DECISION[] = "ACCEPTED_FOR_ONE_BOUNDED_CONTRACT_LOCK_DIAGNOSTIC_ONLY";
static const char EVIDENCE_RESERVED[] = "{\"schema\":\"kira.r25.afes.contract_lock_diagnostic.v3r17.evidence.v1\",\"event\":\"RESERVED_PENDING_CONTRACT_LOCK_DIAGNOSTIC\",\"sequence\":1}\r\n";

enum RecordState {
    RECORD_PENDING = 1U,
    RECORD_TERMINAL = 2U
};

enum DiagnosticGate {
    GATE_NONE = 0U,
    GATE_TARGET_OPEN = 1U,
    GATE_ATTRIBUTES = 2U,
    GATE_SIZE_FIRST = 3U,
    GATE_FINAL_PATH_FIRST = 4U,
    GATE_FILE_ID_FIRST = 5U,
    GATE_SNAPSHOT_ONE = 6U,
    GATE_SIZE_SECOND = 7U,
    GATE_FINAL_PATH_SECOND = 8U,
    GATE_FILE_ID_SECOND = 9U,
    GATE_SNAPSHOT_TWO = 10U,
    GATE_SIZE_FINAL = 11U,
    GATE_FINAL_PATH_FINAL = 12U,
    GATE_FILE_ID_FINAL = 13U,
    GATE_SNAPSHOT_EQUALITY = 14U,
    GATE_TARGET_CLOSE = 15U
};

typedef struct Binding {
    const wchar_t *path;
    ULONGLONG bytes;
    const char *sha256;
    const char *label;
} Binding;

#pragma pack(push, 1)
typedef struct DiagnosticRecord {
    unsigned char magic[RECEIPT_MAGIC_BYTES];
    uint32_t version;
    uint32_t type;
    uint32_t bytes;
    uint32_t state;
    uint32_t success;
    uint32_t failure_gate;
    uint32_t win32_error;
    uint32_t passed_mask;
    uint32_t desired_access;
    uint32_t share_mode;
    uint32_t create_disposition;
    uint32_t open_flags;
    uint64_t expected_bytes;
    uint64_t snapshot_one_bytes;
    uint64_t snapshot_two_bytes;
    uint64_t evidence_volume;
    uint64_t receipt_volume;
    uint64_t target_volume_first;
    uint64_t target_volume_second;
    uint64_t target_volume_final;
    unsigned char evidence_id[16];
    unsigned char receipt_id[16];
    unsigned char target_id_first[16];
    unsigned char target_id_second[16];
    unsigned char target_id_final[16];
    unsigned char executable_sha256[SHA_BYTES];
    unsigned char audit_sha256[SHA_BYTES];
    unsigned char expected_target_sha256[SHA_BYTES];
    unsigned char snapshot_one_sha256[SHA_BYTES];
    unsigned char snapshot_two_sha256[SHA_BYTES];
    unsigned char evidence_sha256[SHA_BYTES];
    unsigned char pending_record_sha256[SHA_BYTES];
    unsigned char nonce[SHA_BYTES];
} DiagnosticRecord;
#pragma pack(pop)

static int lower_hex(const char *value) {
    size_t index;
    if (value == NULL || strlen(value) != SHA_HEX) return 0;
    for (index = 0U; index < SHA_HEX; ++index) {
        if (!((value[index] >= '0' && value[index] <= '9') ||
              (value[index] >= 'a' && value[index] <= 'f'))) return 0;
    }
    return 1;
}

static int hex_digest(const char *text, unsigned char digest[SHA_BYTES]) {
    size_t index;
    if (!lower_hex(text)) return 0;
    for (index = 0U; index < SHA_BYTES; ++index) {
        unsigned char high = (unsigned char)(text[index * 2U] <= '9' ?
            text[index * 2U] - '0' : text[index * 2U] - 'a' + 10);
        unsigned char low = (unsigned char)(text[index * 2U + 1U] <= '9' ?
            text[index * 2U + 1U] - '0' : text[index * 2U + 1U] - 'a' + 10);
        digest[index] = (unsigned char)((high << 4U) | low);
    }
    return 1;
}

static void digest_hex(const unsigned char digest[SHA_BYTES], char text[SHA_HEX + 1U]) {
    static const char digits[] = "0123456789abcdef";
    size_t index;
    for (index = 0U; index < SHA_BYTES; ++index) {
        text[index * 2U] = digits[digest[index] >> 4U];
        text[index * 2U + 1U] = digits[digest[index] & 0x0fU];
    }
    text[SHA_HEX] = '\0';
}

static int sha_buffer(const void *bytes, ULONG length, unsigned char digest[SHA_BYTES]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    NTSTATUS status;
    int ok = 0;
    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) goto cleanup;
    status = BCryptCreateHash(algorithm, &hash, NULL, 0U, NULL, 0U, 0U);
    if (status < 0) goto cleanup;
    status = BCryptHashData(hash, (PUCHAR)bytes, length, 0U);
    if (status < 0) goto cleanup;
    status = BCryptFinishHash(hash, digest, SHA_BYTES, 0U);
    if (status < 0) goto cleanup;
    ok = 1;
cleanup:
    if (hash != NULL) BCryptDestroyHash(hash);
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
    return ok;
}

static int seek_start(HANDLE file) {
    LARGE_INTEGER zero;
    zero.QuadPart = 0;
    return SetFilePointerEx(file, zero, NULL, FILE_BEGIN) != 0;
}

static int seek_end(HANDLE file) {
    LARGE_INTEGER zero;
    zero.QuadPart = 0;
    return SetFilePointerEx(file, zero, NULL, FILE_END) != 0;
}

static int hash_handle_bytes(HANDLE file, unsigned char digest[SHA_BYTES], ULONGLONG *bytes_read) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char buffer[65536];
    DWORD count = 0U;
    ULONGLONG total = 0ULL;
    NTSTATUS status;
    int ok = 0;
    if (!seek_start(file)) return 0;
    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) { SetLastError(ERROR_INVALID_FUNCTION); goto cleanup; }
    status = BCryptCreateHash(algorithm, &hash, NULL, 0U, NULL, 0U, 0U);
    if (status < 0) { SetLastError(ERROR_INVALID_FUNCTION); goto cleanup; }
    for (;;) {
        if (!ReadFile(file, buffer, (DWORD)sizeof(buffer), &count, NULL)) goto cleanup;
        if (count == 0U) break;
        status = BCryptHashData(hash, buffer, count, 0U);
        if (status < 0) { SetLastError(ERROR_INVALID_FUNCTION); goto cleanup; }
        total += count;
    }
    status = BCryptFinishHash(hash, digest, SHA_BYTES, 0U);
    if (status < 0) { SetLastError(ERROR_INVALID_FUNCTION); goto cleanup; }
    *bytes_read = total;
    ok = 1;
cleanup:
    SecureZeroMemory(buffer, sizeof(buffer));
    if (hash != NULL) BCryptDestroyHash(hash);
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
    return ok;
}

static int get_regular_size(HANDLE file, ULONGLONG *bytes, DWORD *attributes) {
    FILE_BASIC_INFO basic;
    FILE_STANDARD_INFO standard;
    SecureZeroMemory(&basic, sizeof(basic));
    SecureZeroMemory(&standard, sizeof(standard));
    if (!GetFileInformationByHandleEx(file, FileBasicInfo, &basic, (DWORD)sizeof(basic))) return 0;
    if ((basic.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_DEVICE |
            FILE_ATTRIBUTE_REPARSE_POINT)) != 0U) {
        SetLastError(ERROR_INVALID_DATA);
        return 0;
    }
    if (!GetFileInformationByHandleEx(file, FileStandardInfo, &standard,
            (DWORD)sizeof(standard))) return 0;
    if (standard.Directory || standard.DeletePending || standard.EndOfFile.QuadPart < 0) {
        SetLastError(ERROR_INVALID_DATA);
        return 0;
    }
    *bytes = (ULONGLONG)standard.EndOfFile.QuadPart;
    if (attributes != NULL) *attributes = basic.FileAttributes;
    return 1;
}

static int final_path_matches(HANDLE file, const wchar_t *expected_path) {
    wchar_t actual[1024];
    wchar_t expected[1024];
    DWORD length;
    if (wcslen(expected_path) + 5U >= _countof(expected)) {
        SetLastError(ERROR_FILENAME_EXCED_RANGE);
        return 0;
    }
    if (wcscpy_s(expected, _countof(expected), L"\\\\?\\") != 0 ||
        wcscat_s(expected, _countof(expected), expected_path) != 0) {
        SetLastError(ERROR_INVALID_NAME);
        return 0;
    }
    length = GetFinalPathNameByHandleW(file, actual, (DWORD)_countof(actual),
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (length == 0U || length >= (DWORD)_countof(actual)) return 0;
    if (wcscmp(actual, expected) != 0) {
        SetLastError(ERROR_INVALID_NAME);
        return 0;
    }
    return 1;
}

static int get_file_identity(HANDLE file, FILE_ID_INFO *identity) {
    SecureZeroMemory(identity, sizeof(*identity));
    return GetFileInformationByHandleEx(file, FileIdInfo, identity,
        (DWORD)sizeof(*identity)) != 0;
}

static int same_identity(const FILE_ID_INFO *left, const FILE_ID_INFO *right) {
    return left->VolumeSerialNumber == right->VolumeSerialNumber &&
        memcmp(left->FileId.Identifier, right->FileId.Identifier, 16U) == 0;
}

static int hash_path_unbound(const wchar_t *path, ULONGLONG maximum,
    ULONGLONG *bytes_output, unsigned char digest[SHA_BYTES]) {
    HANDLE file;
    ULONGLONG bytes = 0ULL;
    ULONGLONG read_bytes = 0ULL;
    int ok;
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    ok = get_regular_size(file, &bytes, NULL) && bytes > 0ULL && bytes <= maximum &&
        final_path_matches(file, path) && hash_handle_bytes(file, digest, &read_bytes) &&
        read_bytes == bytes;
    CloseHandle(file);
    if (ok) *bytes_output = bytes;
    return ok;
}

static int hash_path_exact(const wchar_t *path, ULONGLONG expected_bytes,
    const char *expected_sha) {
    HANDLE file;
    ULONGLONG bytes = 0ULL;
    ULONGLONG read_bytes = 0ULL;
    unsigned char digest[SHA_BYTES];
    unsigned char expected[SHA_BYTES];
    int ok;
    SecureZeroMemory(digest, sizeof(digest));
    SecureZeroMemory(expected, sizeof(expected));
    if (!hex_digest(expected_sha, expected)) return 0;
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    ok = get_regular_size(file, &bytes, NULL) && bytes == expected_bytes &&
        final_path_matches(file, path) && hash_handle_bytes(file, digest, &read_bytes) &&
        read_bytes == expected_bytes && memcmp(digest, expected, SHA_BYTES) == 0;
    CloseHandle(file);
    SecureZeroMemory(digest, sizeof(digest));
    SecureZeroMemory(expected, sizeof(expected));
    return ok;
}

static int read_dynamic_small(const wchar_t *path, unsigned char **output,
    DWORD *bytes_output, unsigned char digest[SHA_BYTES]) {
    HANDLE file = INVALID_HANDLE_VALUE;
    ULONGLONG size = 0ULL;
    ULONGLONG hashed = 0ULL;
    unsigned char *buffer = NULL;
    DWORD read_bytes = 0U;
    unsigned char trailing = 0U;
    DWORD trailing_bytes = 0U;
    int ok = 0;
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) goto cleanup;
    if (!get_regular_size(file, &size, NULL) || size == 0ULL || size > SMALL_LIMIT ||
        !final_path_matches(file, path) ||
        !hash_handle_bytes(file, digest, &hashed) || hashed != size || !seek_start(file)) goto cleanup;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)size + 1U);
    if (buffer == NULL) goto cleanup;
    if (!ReadFile(file, buffer, (DWORD)size, &read_bytes, NULL) || read_bytes != (DWORD)size ||
        !ReadFile(file, &trailing, 1U, &trailing_bytes, NULL) || trailing_bytes != 0U) goto cleanup;
    *output = buffer;
    *bytes_output = (DWORD)size;
    buffer = NULL;
    ok = 1;
cleanup:
    if (buffer != NULL) {
        SecureZeroMemory(buffer, (SIZE_T)size + 1U);
        HeapFree(GetProcessHeap(), 0U, buffer);
    }
    if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
    return ok;
}

static int consume_line(char **cursor, const char *end, const char *key,
    char *value, size_t capacity) {
    char *newline;
    size_t key_length = strlen(key);
    size_t line_length;
    size_t value_length;
    if (*cursor >= end) return 0;
    newline = (char *)memchr(*cursor, '\n', (size_t)(end - *cursor));
    if (newline == NULL) return 0;
    line_length = (size_t)(newline - *cursor);
    if (line_length <= key_length || memcmp(*cursor, key, key_length) != 0 ||
        (*cursor)[key_length] != '\t') return 0;
    value_length = line_length - key_length - 1U;
    if (value_length == 0U || value_length >= capacity ||
        memchr(*cursor + key_length + 1U, '\r', value_length) != NULL ||
        memchr(*cursor + key_length + 1U, '\t', value_length) != NULL) return 0;
    memcpy(value, *cursor + key_length + 1U, value_length);
    value[value_length] = '\0';
    *cursor = newline + 1;
    return 1;
}

static int verify_audit(const unsigned char self_sha[SHA_BYTES],
    unsigned char audit_sha[SHA_BYTES]) {
    static const char *const keys[] = {
        "decision", "auditor", "author", "native_executable_sha256",
        "identity_anchor_sha256", "contract_sha256", "native_source_sha256",
        "static_test_sha256", "runtime_control_checkpoint_sha256",
        "v3r15_postmortem_checkpoint_sha256", "v3r15_read_only_recheck_sha256",
        "v3r15_contract_sha256", "v3r15_audit_checkpoint_sha256"
    };
    unsigned char *audit = NULL;
    unsigned char *sidecar = NULL;
    DWORD audit_bytes = 0U;
    DWORD sidecar_bytes = 0U;
    unsigned char sidecar_sha[SHA_BYTES];
    unsigned char anchor_sha[SHA_BYTES];
    ULONGLONG anchor_bytes = 0ULL;
    char self_hex[SHA_HEX + 1U];
    char audit_hex[SHA_HEX + 1U];
    char anchor_hex[SHA_HEX + 1U];
    char values[_countof(keys)][128];
    const char *expected[_countof(keys)];
    char *cursor;
    const char *end;
    size_t index;
    int ok = 0;
    SecureZeroMemory(sidecar_sha, sizeof(sidecar_sha));
    SecureZeroMemory(anchor_sha, sizeof(anchor_sha));
    SecureZeroMemory(values, sizeof(values));
    if (!read_dynamic_small(AUDIT_PATH, &audit, &audit_bytes, audit_sha) ||
        !read_dynamic_small(AUDIT_DIGEST_PATH, &sidecar, &sidecar_bytes, sidecar_sha) ||
        sidecar_bytes != SHA_HEX + 1U || sidecar[SHA_HEX] != '\n' ||
        !hash_path_unbound(ANCHOR_PATH, SMALL_LIMIT, &anchor_bytes, anchor_sha)) goto cleanup;
    digest_hex(audit_sha, audit_hex);
    if (memcmp(sidecar, audit_hex, SHA_HEX) != 0) goto cleanup;
    digest_hex(self_sha, self_hex);
    digest_hex(anchor_sha, anchor_hex);
    expected[0] = AUDIT_DECISION;
    expected[1] = NULL;
    expected[2] = V3R17_AUTHOR_ID;
    expected[3] = self_hex;
    expected[4] = anchor_hex;
    expected[5] = V3R17_CONTRACT_SHA256;
    expected[6] = V3R17_SOURCE_SHA256;
    expected[7] = V3R17_TEST_SHA256;
    expected[8] = V3R17_CONTROL_SHA256;
    expected[9] = V3R17_V3R15_POSTMORTEM_SHA256;
    expected[10] = V3R17_V3R15_RECHECK_SHA256;
    expected[11] = V3R17_V3R15_CONTRACT_SHA256;
    expected[12] = V3R17_V3R15_AUDIT_SHA256;
    cursor = (char *)audit;
    end = (const char *)audit + audit_bytes;
    {
        char *newline = (char *)memchr(cursor, '\n', (size_t)(end - cursor));
        if (newline == NULL || (size_t)(newline - cursor) != strlen(AUDIT_MAGIC) ||
            memcmp(cursor, AUDIT_MAGIC, strlen(AUDIT_MAGIC)) != 0) goto cleanup;
        cursor = newline + 1;
    }
    for (index = 0U; index < _countof(keys); ++index) {
        if (!consume_line(&cursor, end, keys[index], values[index], sizeof(values[index]))) goto cleanup;
    }
    if (cursor != end || strcmp(values[0], expected[0]) != 0 ||
        values[1][0] == '\0' || strcmp(values[1], values[2]) == 0 ||
        strcmp(values[2], expected[2]) != 0) goto cleanup;
    for (index = 3U; index < _countof(keys); ++index) {
        if (!lower_hex(values[index]) || strcmp(values[index], expected[index]) != 0) goto cleanup;
    }
    ok = 1;
cleanup:
    if (audit != NULL) {
        SecureZeroMemory(audit, (SIZE_T)audit_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, audit);
    }
    if (sidecar != NULL) {
        SecureZeroMemory(sidecar, (SIZE_T)sidecar_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, sidecar);
    }
    SecureZeroMemory(sidecar_sha, sizeof(sidecar_sha));
    SecureZeroMemory(anchor_sha, sizeof(anchor_sha));
    return ok;
}

static int verify_output_parent(void) {
    HANDLE directory;
    FILE_ATTRIBUTE_TAG_INFO attributes;
    int ok = 0;
    directory = CreateFileW(OUTPUT_PARENT_PATH, FILE_ADD_FILE | FILE_READ_ATTRIBUTES |
        SYNCHRONIZE, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL,
        OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (directory == INVALID_HANDLE_VALUE) return 0;
    SecureZeroMemory(&attributes, sizeof(attributes));
    if (GetFileInformationByHandleEx(directory, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0U &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0U) ok = 1;
    CloseHandle(directory);
    return ok;
}

static int write_exact(HANDLE file, const void *bytes, DWORD length) {
    DWORD written = 0U;
    return WriteFile(file, bytes, length, &written, NULL) != 0 && written == length;
}

static int read_exact(HANDLE file, void *bytes, DWORD length) {
    DWORD read_bytes = 0U;
    return ReadFile(file, bytes, length, &read_bytes, NULL) != 0 && read_bytes == length;
}

static int verify_exact_content(HANDLE file, const void *first, DWORD first_bytes,
    const void *second, DWORD second_bytes) {
    unsigned char *buffer = NULL;
    DWORD total = first_bytes + second_bytes;
    DWORD read_bytes = 0U;
    DWORD trailing_bytes = 0U;
    unsigned char trailing = 0U;
    int ok = 0;
    if (total > EVIDENCE_LIMIT || !seek_start(file)) return 0;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, total == 0U ? 1U : total);
    if (buffer == NULL) return 0;
    if (!ReadFile(file, buffer, total, &read_bytes, NULL) || read_bytes != total ||
        !ReadFile(file, &trailing, 1U, &trailing_bytes, NULL) || trailing_bytes != 0U) goto cleanup;
    if (first_bytes != 0U && memcmp(buffer, first, first_bytes) != 0) goto cleanup;
    if (second_bytes != 0U && memcmp(buffer + first_bytes, second, second_bytes) != 0) goto cleanup;
    ok = 1;
cleanup:
    SecureZeroMemory(buffer, total == 0U ? 1U : total);
    HeapFree(GetProcessHeap(), 0U, buffer);
    return ok;
}

static int reserve_outputs(HANDLE *evidence_output, HANDLE *receipt_output,
    FILE_ID_INFO *evidence_identity, FILE_ID_INFO *receipt_identity,
    const unsigned char self_sha[SHA_BYTES], const unsigned char audit_sha[SHA_BYTES],
    DiagnosticRecord *pending) {
    HANDLE evidence = INVALID_HANDLE_VALUE;
    HANDLE receipt = INVALID_HANDLE_VALUE;
    DiagnosticRecord readback;
    ULONGLONG bytes = 0ULL;
    SecureZeroMemory(pending, sizeof(*pending));
    SecureZeroMemory(&readback, sizeof(readback));
    SecureZeroMemory(evidence_identity, sizeof(*evidence_identity));
    SecureZeroMemory(receipt_identity, sizeof(*receipt_identity));
    evidence = CreateFileW(EVIDENCE_PATH, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,
        NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (evidence == INVALID_HANDLE_VALUE || !final_path_matches(evidence, EVIDENCE_PATH) ||
        !get_file_identity(evidence, evidence_identity) ||
        !write_exact(evidence, EVIDENCE_RESERVED, (DWORD)strlen(EVIDENCE_RESERVED)) ||
        !FlushFileBuffers(evidence) ||
        !verify_exact_content(evidence, EVIDENCE_RESERVED, (DWORD)strlen(EVIDENCE_RESERVED), NULL, 0U)) goto fail;
    receipt = CreateFileW(OUTCOME_PATH, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,
        NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (receipt == INVALID_HANDLE_VALUE || !final_path_matches(receipt, OUTCOME_PATH) ||
        !get_file_identity(receipt, receipt_identity)) goto fail;
    memcpy(pending->magic, "KIRA_R25_AFES_V3R17_CONTRACT_DIAGNOSTIC",
        strlen("KIRA_R25_AFES_V3R17_CONTRACT_DIAGNOSTIC"));
    pending->version = 1U;
    pending->type = 1U;
    pending->bytes = (uint32_t)sizeof(*pending);
    pending->state = RECORD_PENDING;
    pending->desired_access = GENERIC_READ;
    pending->share_mode = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE;
    pending->create_disposition = OPEN_EXISTING;
    pending->open_flags = FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN |
        FILE_FLAG_OPEN_REPARSE_POINT;
    pending->expected_bytes = V3R17_V3R15_CONTRACT_BYTES;
    pending->evidence_volume = evidence_identity->VolumeSerialNumber;
    pending->receipt_volume = receipt_identity->VolumeSerialNumber;
    memcpy(pending->evidence_id, evidence_identity->FileId.Identifier, 16U);
    memcpy(pending->receipt_id, receipt_identity->FileId.Identifier, 16U);
    memcpy(pending->executable_sha256, self_sha, SHA_BYTES);
    memcpy(pending->audit_sha256, audit_sha, SHA_BYTES);
    if (!hex_digest(V3R17_V3R15_CONTRACT_SHA256, pending->expected_target_sha256) ||
        BCryptGenRandom(NULL, pending->nonce, SHA_BYTES, BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0 ||
        !write_exact(receipt, pending, (DWORD)sizeof(*pending)) ||
        !FlushFileBuffers(receipt) || !seek_start(receipt) ||
        !read_exact(receipt, &readback, (DWORD)sizeof(readback)) ||
        memcmp(pending, &readback, sizeof(*pending)) != 0 ||
        !get_regular_size(receipt, &bytes, NULL) || bytes != sizeof(*pending)) goto fail;
    *evidence_output = evidence;
    *receipt_output = receipt;
    SecureZeroMemory(&readback, sizeof(readback));
    return 1;
fail:
    SecureZeroMemory(&readback, sizeof(readback));
    if (receipt != INVALID_HANDLE_VALUE) CloseHandle(receipt);
    if (evidence != INVALID_HANDLE_VALUE) CloseHandle(evidence);
    return 0;
}

static void mark_pass(DiagnosticRecord *record, uint32_t gate) {
    if (gate > 0U && gate < 32U) record->passed_mask |= (1U << (gate - 1U));
}

static void mark_failure(DiagnosticRecord *record, uint32_t gate, DWORD error) {
    record->success = 0U;
    record->failure_gate = gate;
    record->win32_error = error == ERROR_SUCCESS ? ERROR_INVALID_DATA : error;
}

static int diagnose_contract(DiagnosticRecord *record) {
    HANDLE target = INVALID_HANDLE_VALUE;
    FILE_BASIC_INFO basic;
    FILE_STANDARD_INFO standard;
    FILE_ID_INFO first_identity;
    FILE_ID_INFO second_identity;
    FILE_ID_INFO final_identity;
    ULONGLONG size = 0ULL;
    DWORD error = ERROR_SUCCESS;
    int ok = 0;
    SecureZeroMemory(&basic, sizeof(basic));
    SecureZeroMemory(&standard, sizeof(standard));
    SecureZeroMemory(&first_identity, sizeof(first_identity));
    SecureZeroMemory(&second_identity, sizeof(second_identity));
    SecureZeroMemory(&final_identity, sizeof(final_identity));
    SetLastError(ERROR_SUCCESS);
    target = CreateFileW(V3R15_TARGET_CONTRACT_PATH, GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (target == INVALID_HANDLE_VALUE) {
        mark_failure(record, GATE_TARGET_OPEN, GetLastError());
        goto cleanup;
    }
    mark_pass(record, GATE_TARGET_OPEN);
    if (!GetFileInformationByHandleEx(target, FileBasicInfo, &basic, (DWORD)sizeof(basic))) {
        mark_failure(record, GATE_ATTRIBUTES, GetLastError()); goto cleanup;
    }
    if ((basic.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_DEVICE |
            FILE_ATTRIBUTE_REPARSE_POINT)) != 0U) {
        mark_failure(record, GATE_ATTRIBUTES, ERROR_INVALID_DATA); goto cleanup;
    }
    mark_pass(record, GATE_ATTRIBUTES);
    if (!GetFileInformationByHandleEx(target, FileStandardInfo, &standard,
            (DWORD)sizeof(standard))) {
        mark_failure(record, GATE_SIZE_FIRST, GetLastError()); goto cleanup;
    }
    if (standard.Directory || standard.DeletePending || standard.EndOfFile.QuadPart < 0 ||
        (ULONGLONG)standard.EndOfFile.QuadPart != V3R17_V3R15_CONTRACT_BYTES) {
        mark_failure(record, GATE_SIZE_FIRST, ERROR_INVALID_DATA); goto cleanup;
    }
    mark_pass(record, GATE_SIZE_FIRST);
    if (!final_path_matches(target, V3R15_TARGET_CONTRACT_PATH)) {
        mark_failure(record, GATE_FINAL_PATH_FIRST, GetLastError()); goto cleanup;
    }
    mark_pass(record, GATE_FINAL_PATH_FIRST);
    if (!get_file_identity(target, &first_identity)) {
        mark_failure(record, GATE_FILE_ID_FIRST, GetLastError()); goto cleanup;
    }
    record->target_volume_first = first_identity.VolumeSerialNumber;
    memcpy(record->target_id_first, first_identity.FileId.Identifier, 16U);
    mark_pass(record, GATE_FILE_ID_FIRST);
    if (!hash_handle_bytes(target, record->snapshot_one_sha256,
            &record->snapshot_one_bytes)) {
        mark_failure(record, GATE_SNAPSHOT_ONE, GetLastError()); goto cleanup;
    }
    mark_pass(record, GATE_SNAPSHOT_ONE);
    SecureZeroMemory(&standard, sizeof(standard));
    if (!GetFileInformationByHandleEx(target, FileStandardInfo, &standard,
            (DWORD)sizeof(standard))) {
        mark_failure(record, GATE_SIZE_SECOND, GetLastError()); goto cleanup;
    }
    size = standard.EndOfFile.QuadPart < 0 ? 0ULL : (ULONGLONG)standard.EndOfFile.QuadPart;
    if (standard.Directory || standard.DeletePending ||
        size != V3R17_V3R15_CONTRACT_BYTES || size != record->snapshot_one_bytes) {
        mark_failure(record, GATE_SIZE_SECOND, ERROR_INVALID_DATA); goto cleanup;
    }
    mark_pass(record, GATE_SIZE_SECOND);
    if (!final_path_matches(target, V3R15_TARGET_CONTRACT_PATH)) {
        mark_failure(record, GATE_FINAL_PATH_SECOND, GetLastError()); goto cleanup;
    }
    mark_pass(record, GATE_FINAL_PATH_SECOND);
    if (!get_file_identity(target, &second_identity)) {
        mark_failure(record, GATE_FILE_ID_SECOND, GetLastError()); goto cleanup;
    }
    record->target_volume_second = second_identity.VolumeSerialNumber;
    memcpy(record->target_id_second, second_identity.FileId.Identifier, 16U);
    if (!same_identity(&first_identity, &second_identity)) {
        mark_failure(record, GATE_FILE_ID_SECOND, ERROR_INVALID_DATA); goto cleanup;
    }
    mark_pass(record, GATE_FILE_ID_SECOND);
    if (!hash_handle_bytes(target, record->snapshot_two_sha256,
            &record->snapshot_two_bytes)) {
        mark_failure(record, GATE_SNAPSHOT_TWO, GetLastError()); goto cleanup;
    }
    mark_pass(record, GATE_SNAPSHOT_TWO);
    SecureZeroMemory(&standard, sizeof(standard));
    if (!GetFileInformationByHandleEx(target, FileStandardInfo, &standard,
            (DWORD)sizeof(standard))) {
        mark_failure(record, GATE_SIZE_FINAL, GetLastError()); goto cleanup;
    }
    size = standard.EndOfFile.QuadPart < 0 ? 0ULL : (ULONGLONG)standard.EndOfFile.QuadPart;
    if (standard.Directory || standard.DeletePending ||
        size != V3R17_V3R15_CONTRACT_BYTES || size != record->snapshot_two_bytes) {
        mark_failure(record, GATE_SIZE_FINAL, ERROR_INVALID_DATA); goto cleanup;
    }
    mark_pass(record, GATE_SIZE_FINAL);
    if (!final_path_matches(target, V3R15_TARGET_CONTRACT_PATH)) {
        mark_failure(record, GATE_FINAL_PATH_FINAL, GetLastError()); goto cleanup;
    }
    mark_pass(record, GATE_FINAL_PATH_FINAL);
    if (!get_file_identity(target, &final_identity)) {
        mark_failure(record, GATE_FILE_ID_FINAL, GetLastError()); goto cleanup;
    }
    record->target_volume_final = final_identity.VolumeSerialNumber;
    memcpy(record->target_id_final, final_identity.FileId.Identifier, 16U);
    if (!same_identity(&first_identity, &final_identity)) {
        mark_failure(record, GATE_FILE_ID_FINAL, ERROR_INVALID_DATA); goto cleanup;
    }
    mark_pass(record, GATE_FILE_ID_FINAL);
    if (record->snapshot_one_bytes != V3R17_V3R15_CONTRACT_BYTES ||
        record->snapshot_two_bytes != V3R17_V3R15_CONTRACT_BYTES ||
        memcmp(record->snapshot_one_sha256, record->snapshot_two_sha256, SHA_BYTES) != 0 ||
        memcmp(record->snapshot_one_sha256, record->expected_target_sha256, SHA_BYTES) != 0) {
        mark_failure(record, GATE_SNAPSHOT_EQUALITY, ERROR_INVALID_DATA); goto cleanup;
    }
    mark_pass(record, GATE_SNAPSHOT_EQUALITY);
    record->success = 1U;
    record->failure_gate = GATE_NONE;
    record->win32_error = ERROR_SUCCESS;
    ok = 1;
cleanup:
    if (target != INVALID_HANDLE_VALUE) {
        if (!CloseHandle(target) && ok) {
            error = GetLastError();
            mark_failure(record, GATE_TARGET_CLOSE, error);
            ok = 0;
        } else if (ok) {
            mark_pass(record, GATE_TARGET_CLOSE);
        }
    }
    return ok;
}

static int finish_outputs(HANDLE evidence, HANDLE receipt,
    const FILE_ID_INFO *evidence_identity, const FILE_ID_INFO *receipt_identity,
    const DiagnosticRecord *pending, DiagnosticRecord *terminal) {
    char terminal_line[512];
    int line_bytes;
    DiagnosticRecord pending_readback;
    DiagnosticRecord terminal_readback;
    FILE_ID_INFO current_identity;
    ULONGLONG receipt_bytes = 0ULL;
    ULONGLONG evidence_bytes = 0ULL;
    unsigned char trailing = 0U;
    DWORD trailing_bytes = 0U;
    int ok = 0;
    SecureZeroMemory(&pending_readback, sizeof(pending_readback));
    SecureZeroMemory(&terminal_readback, sizeof(terminal_readback));
    SecureZeroMemory(&current_identity, sizeof(current_identity));
    line_bytes = sprintf_s(terminal_line, sizeof(terminal_line),
        "{\"schema\":\"kira.r25.afes.contract_lock_diagnostic.v3r17.evidence.v1\","
        "\"event\":\"TERMINAL\",\"sequence\":2,\"success\":%u,\"failure_gate\":%u,"
        "\"win32_error\":%u,\"passed_mask\":%u,\"snapshot_one_bytes\":%llu,"
        "\"snapshot_two_bytes\":%llu}\r\n",
        terminal->success, terminal->failure_gate, terminal->win32_error,
        terminal->passed_mask, (unsigned long long)terminal->snapshot_one_bytes,
        (unsigned long long)terminal->snapshot_two_bytes);
    if (line_bytes <= 0 || (size_t)line_bytes >= sizeof(terminal_line) ||
        !get_file_identity(evidence, &current_identity) ||
        !same_identity(evidence_identity, &current_identity) || !seek_end(evidence) ||
        !write_exact(evidence, terminal_line, (DWORD)line_bytes) ||
        !FlushFileBuffers(evidence) ||
        !verify_exact_content(evidence, EVIDENCE_RESERVED, (DWORD)strlen(EVIDENCE_RESERVED),
            terminal_line, (DWORD)line_bytes) ||
        !hash_handle_bytes(evidence, terminal->evidence_sha256, &evidence_bytes) ||
        evidence_bytes != strlen(EVIDENCE_RESERVED) + (ULONGLONG)line_bytes) goto cleanup;
    if (!sha_buffer(pending, (ULONG)sizeof(*pending), terminal->pending_record_sha256) ||
        !get_file_identity(receipt, &current_identity) ||
        !same_identity(receipt_identity, &current_identity) || !seek_end(receipt) ||
        !write_exact(receipt, terminal, (DWORD)sizeof(*terminal)) ||
        !FlushFileBuffers(receipt) || !seek_start(receipt) ||
        !read_exact(receipt, &pending_readback, (DWORD)sizeof(pending_readback)) ||
        !read_exact(receipt, &terminal_readback, (DWORD)sizeof(terminal_readback)) ||
        memcmp(pending, &pending_readback, sizeof(*pending)) != 0 ||
        memcmp(terminal, &terminal_readback, sizeof(*terminal)) != 0 ||
        !ReadFile(receipt, &trailing, 1U, &trailing_bytes, NULL) || trailing_bytes != 0U ||
        !get_regular_size(receipt, &receipt_bytes, NULL) ||
        receipt_bytes != sizeof(*pending) + sizeof(*terminal)) goto cleanup;
    ok = 1;
cleanup:
    SecureZeroMemory(&pending_readback, sizeof(pending_readback));
    SecureZeroMemory(&terminal_readback, sizeof(terminal_readback));
    SecureZeroMemory(terminal_line, sizeof(terminal_line));
    return ok;
}

int wmain(int argc, wchar_t **argv) {
    static const Binding fixed[] = {
        {CONTRACT_PATH, V3R17_CONTRACT_BYTES, V3R17_CONTRACT_SHA256, "contract"},
        {SOURCE_PATH, V3R17_SOURCE_BYTES, V3R17_SOURCE_SHA256, "source"},
        {TEST_PATH, V3R17_TEST_BYTES, V3R17_TEST_SHA256, "test"},
        {CONTROL_PATH, V3R17_CONTROL_BYTES, V3R17_CONTROL_SHA256, "control"},
        {V3R15_POSTMORTEM_PATH, V3R17_V3R15_POSTMORTEM_BYTES,
            V3R17_V3R15_POSTMORTEM_SHA256, "v3r15_postmortem"},
        {V3R15_RECHECK_PATH, V3R17_V3R15_RECHECK_BYTES,
            V3R17_V3R15_RECHECK_SHA256, "v3r15_recheck"},
        {V3R15_AUDIT_CHECKPOINT_PATH, V3R17_V3R15_AUDIT_BYTES,
            V3R17_V3R15_AUDIT_SHA256, "v3r15_audit"}
    };
    wchar_t current[MAX_PATH];
    wchar_t module[MAX_PATH];
    DWORD current_length;
    DWORD module_length;
    ULONGLONG self_bytes = 0ULL;
    unsigned char self_sha[SHA_BYTES];
    unsigned char audit_sha[SHA_BYTES];
    HANDLE evidence = INVALID_HANDLE_VALUE;
    HANDLE receipt = INVALID_HANDLE_VALUE;
    FILE_ID_INFO evidence_identity;
    FILE_ID_INFO receipt_identity;
    DiagnosticRecord pending;
    DiagnosticRecord terminal;
    size_t index;
    int diagnostic_ok;
    int result = 1;
    (void)argv;
    SecureZeroMemory(self_sha, sizeof(self_sha));
    SecureZeroMemory(audit_sha, sizeof(audit_sha));
    SecureZeroMemory(&evidence_identity, sizeof(evidence_identity));
    SecureZeroMemory(&receipt_identity, sizeof(receipt_identity));
    SecureZeroMemory(&pending, sizeof(pending));
    SecureZeroMemory(&terminal, sizeof(terminal));
    if (argc != 1) return 2;
    current_length = GetCurrentDirectoryW((DWORD)_countof(current), current);
    module_length = GetModuleFileNameW(NULL, module, (DWORD)_countof(module));
    if (current_length == 0U || current_length >= (DWORD)_countof(current) ||
        wcscmp(current, PROJECT_ROOT) != 0 || module_length == 0U ||
        module_length >= (DWORD)_countof(module) || wcscmp(module, SELF_PATH) != 0 ||
        !hash_path_unbound(SELF_PATH, 4194304ULL, &self_bytes, self_sha)) return 3;
    for (index = 0U; index < _countof(fixed); ++index) {
        if (!hash_path_exact(fixed[index].path, fixed[index].bytes, fixed[index].sha256)) {
            fwprintf(stderr, L"V3R17_SEALED_SUBJECT_REFUSED:%S\n", fixed[index].label);
            return 4;
        }
    }
    if (!verify_audit(self_sha, audit_sha) || !verify_output_parent()) return 5;
    if (!reserve_outputs(&evidence, &receipt, &evidence_identity, &receipt_identity,
            self_sha, audit_sha, &pending)) return 6;
    terminal = pending;
    SecureZeroMemory(terminal.magic, sizeof(terminal.magic));
    memcpy(terminal.magic, "KIRA_R25_AFES_V3R17_CONTRACT_TERMINAL",
        strlen("KIRA_R25_AFES_V3R17_CONTRACT_TERMINAL"));
    terminal.type = 2U;
    terminal.state = RECORD_TERMINAL;
    terminal.success = 0U;
    terminal.failure_gate = GATE_TARGET_OPEN;
    terminal.win32_error = ERROR_GEN_FAILURE;
    diagnostic_ok = diagnose_contract(&terminal);
    if (!finish_outputs(evidence, receipt, &evidence_identity, &receipt_identity,
            &pending, &terminal)) {
        result = 8;
    } else if (diagnostic_ok) {
        wprintf(L"V3R17_CONTRACT_LOCK_DIAGNOSTIC_SUCCESS\n");
        result = 0;
    } else {
        wprintf(L"V3R17_CONTRACT_LOCK_DIAGNOSTIC_FAILURE:%u:%u\n",
            terminal.failure_gate, terminal.win32_error);
        result = 7;
    }
    if (receipt != INVALID_HANDLE_VALUE) CloseHandle(receipt);
    if (evidence != INVALID_HANDLE_VALUE) CloseHandle(evidence);
    SecureZeroMemory(&pending, sizeof(pending));
    SecureZeroMemory(&terminal, sizeof(terminal));
    SecureZeroMemory(self_sha, sizeof(self_sha));
    SecureZeroMemory(audit_sha, sizeof(audit_sha));
    return result;
}

