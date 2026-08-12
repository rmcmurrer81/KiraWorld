/*
 * Blackwell voice V17 whole-document manifest disconnected control anchor.
 *
 * V17 is the append-only repair for the rejected, uninvoked V16 control.
 * V16 used substring counts rather than a whole-document parser and accepted
 * trailing bytes, a whitespace-form logical duplicate/42nd subject, and
 * terminal dot segments. V17 consumes one canonical compact JSON grammar to
 * exact EOF, counts actual subject objects, enforces unique canonical paths,
 * and requires ordered set equality with every locked Binding before output.
 *
 * Static authoring only. This image must not be invoked until its complete
 * exact-byte closure is sealed and a different fresh reviewer creates the
 * fixed V17 audit decision accepted by this source. One later accepted
 * operation may perform only the retained V15 private static Python graph
 * validation and then stop.
 * There is no model, GPU, Torch, CUDA, Chatterbox, synthesis, audio, playback,
 * process, network, person-state, body, Blender, or production-routing path.
 */

#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <bcrypt.h>
#include <tlhelp32.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#define Py_NO_LINK_LIB 1
#include <Python.h>

#include "kira_blackwell_voice_control_anchor_v17_identity_anchor.h"

#pragma comment(lib, "bcrypt.lib")

#define SHA_BYTES 32U
#define SHA_HEX 64U
#define HASH_CHUNK 65536U
#define AUDIT_LIMIT 32768U
#define SEAL_LIMIT 262144U
#define SOURCE_LIMIT 262144U
#define RECORD_PENDING 1U
#define RECORD_SUCCESS 2U
#define RECORD_FAILURE 3U
#define V17_PREDECESSOR_COUNT 6U
#define V17_SEALED_SUBJECT_COUNT 55U
#define V17_SEALED_SUBJECT_COUNT_TEXT "55"

static const wchar_t PROJECT_ROOT[] = L"C:\\Users\\robmc\\Kira";
static const wchar_t SELF_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_blackwell_voice_control_anchor_v17.exe";
static const wchar_t SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_blackwell_voice_control_anchor_v17.c";
static const wchar_t HEADER_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_blackwell_voice_control_anchor_v17_identity_anchor.h";
static const wchar_t VALIDATOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_blackwell_voice_control_anchor_v15_validator.py";
static const wchar_t PY_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\Core\\persistent_blackwell_voice_integration_v15.py";
static const wchar_t CONFIG_PATH[] = L"C:\\Users\\robmc\\Kira\\Voice\\sidecars\\chatterbox_blackwell_persistent_candidate_v15\\candidate_config.json";
static const wchar_t V17_CONFIG_PATH[] = L"C:\\Users\\robmc\\Kira\\Voice\\sidecars\\chatterbox_blackwell_persistent_candidate_v17\\candidate_config.json";
static const wchar_t NATIVE_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Voice\\sidecars\\chatterbox_blackwell_persistent_candidate_v17\\native_control_contract.json";
static const wchar_t README_PATH[] = L"C:\\Users\\robmc\\Kira\\Voice\\sidecars\\chatterbox_blackwell_persistent_candidate_v17\\README.md";
static const wchar_t SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v17_native_whole_document_manifest_control_anchor_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t AUDIT_DIGEST_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v17_native_whole_document_manifest_control_anchor_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t OUTPUT_PARENT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation\\attempt_01";
static const wchar_t EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation\\attempt_01\\RUN_EVIDENCE_V17.jsonl";
static const wchar_t OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation\\attempt_01\\STATIC_CONTROL_OUTCOME_V17.receipt.bin";
static const wchar_t PYTHON_DLL_PATH[] = L"C:\\Python314\\python314.dll";
static const wchar_t STDLIB_ZIP_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\runtime\\python314_stdlib_v3r4.zip";
static const wchar_t V15_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V15_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V15_AUDIT_TSV_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V15_AUDIT_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V15_AUDIT_DECISION_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_fresh_static_audit\\attempt_01\\AUDIT_DECISION.json";
static const wchar_t V15_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V15_REVIEW_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_fresh_static_audit\\attempt_01\\REVIEW_PROBES.md";
static const wchar_t V15_DIAGNOSIS_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_consumed_failure_diagnostic\\attempt_01\\READ_ONLY_DIAGNOSIS.json";
static const wchar_t V15_FAILURE_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\blackwell_v15_native_exact_control_anchor_consumed_failure_diagnostic\\attempt_01\\CHECKPOINT.md";

static const char AUDIT_MAGIC[] = "KIRA_BLACKWELL_VOICE_V17_WHOLE_DOCUMENT_CONTROL_AUDIT\t1";
static const char AUDIT_DECISION[] = "ACCEPTED_FOR_ONE_BOUNDED_DISCONNECTED_STATIC_CONTROL_VALIDATION_V17_ONLY";
static const char E_ENTRY[] = "{\"schema\":\"kira.blackwell.v17.native_stage.v1\",\"stage\":\"entry\",\"status\":\"entered\"}\n";
static const char E_GATE[] = "{\"schema\":\"kira.blackwell.v17.native_stage.v1\",\"stage\":\"audit_seal_retained_handles\",\"status\":\"passed\"}\n";
static const char E_RESERVED[] = "{\"schema\":\"kira.blackwell.v17.native_stage.v1\",\"stage\":\"outcome_reservation\",\"status\":\"passed\"}\n";
static const char E_PYTHON[] = "{\"schema\":\"kira.blackwell.v17.native_stage.v1\",\"stage\":\"retained_v15_private_python_control_graph\",\"status\":\"passed\"}\n";
static const char E_FINALIZED[] = "{\"schema\":\"kira.blackwell.v17.native_stage.v1\",\"stage\":\"finalize_unload_absence_recheck\",\"status\":\"passed\"}\n";
static const char E_SUCCESS[] = "{\"schema\":\"kira.blackwell.v17.native_stage.v1\",\"stage\":\"terminal\",\"status\":\"complete\",\"detail\":\"static_control_only_no_voice_audio_latency\"}\n";
static const char E_FAILURE[] = "{\"schema\":\"kira.blackwell.v17.native_stage.v1\",\"stage\":\"terminal\",\"status\":\"failed_consumed_no_retry\"}\n";

typedef struct Binding {
    const wchar_t *path;
    const char *relative_path;
    ULONGLONG bytes;
    const char *sha256;
    const char *label;
} Binding;

typedef struct LockedFile {
    Binding binding;
    HANDLE handle;
    FILE_ID_INFO identity;
} LockedFile;

typedef struct AuditValues {
    char auditor[97];
    ULONGLONG audit_bytes;
    ULONGLONG seal_bytes;
    char seal_sha256[SHA_HEX + 1U];
    ULONGLONG self_bytes;
    char self_sha256[SHA_HEX + 1U];
    ULONGLONG header_bytes;
    char header_sha256[SHA_HEX + 1U];
    unsigned char audit_sha256[SHA_BYTES];
    unsigned char audit_sidecar_sha256[SHA_BYTES];
    unsigned char nonce[SHA_BYTES];
} AuditValues;

#pragma pack(push, 1)
typedef struct ReservationRecord {
    unsigned char magic[48];
    uint32_t version;
    uint32_t type;
    uint32_t bytes;
    uint32_t state;
    unsigned char executable_sha256[SHA_BYTES];
    unsigned char audit_sha256[SHA_BYTES];
    unsigned char seal_sha256[SHA_BYTES];
    unsigned char source_sha256[SHA_BYTES];
    unsigned char python_source_sha256[SHA_BYTES];
    unsigned char v14_rejection_sha256[SHA_BYTES];
    unsigned char nonce[SHA_BYTES];
    uint64_t receipt_volume;
    unsigned char receipt_id[16];
    uint64_t evidence_volume;
    unsigned char evidence_id[16];
} ReservationRecord;

typedef struct CompletionRecord {
    unsigned char magic[48];
    uint32_t version;
    uint32_t type;
    uint32_t bytes;
    uint32_t state;
    uint32_t terminal_stage;
    uint32_t python_finalize_result;
    uint32_t free_library_succeeded;
    uint32_t old_module_absent;
    uint32_t exact_path_absent;
    uint32_t modules_enumerated;
    uint32_t reserved;
    unsigned char reservation_sha256[SHA_BYTES];
    unsigned char executable_sha256[SHA_BYTES];
    unsigned char audit_sha256[SHA_BYTES];
    unsigned char seal_sha256[SHA_BYTES];
    unsigned char source_sha256[SHA_BYTES];
    unsigned char python_source_sha256[SHA_BYTES];
    unsigned char v14_rejection_sha256[SHA_BYTES];
    uint64_t receipt_volume;
    unsigned char receipt_id[16];
    uint64_t evidence_volume;
    unsigned char evidence_id[16];
} CompletionRecord;
#pragma pack(pop)

typedef struct UnloadTelemetry {
    uint32_t finalize_called;
    uint32_t finalize_result;
    uint32_t free_library_succeeded;
    uint32_t old_module_absent;
    uint32_t exact_path_absent;
    uint32_t modules_enumerated;
} UnloadTelemetry;

typedef struct PythonApi {
    HMODULE module;
    void (__cdecl *config_init)(PyConfig *);
    PyStatus (__cdecl *config_set_string)(PyConfig *, wchar_t **, const wchar_t *);
    PyStatus (__cdecl *wide_append)(PyWideStringList *, const wchar_t *);
    PyStatus (__cdecl *initialize)(const PyConfig *);
    int (__cdecl *status_exception)(PyStatus);
    void (__cdecl *config_clear)(PyConfig *);
    int (__cdecl *finalize)(void);
    PyObject *(__cdecl *compile)(const char *, const char *, int, PyCompilerFlags *, int);
    PyObject *(__cdecl *eval_code)(PyObject *, PyObject *, PyObject *);
    PyObject *(__cdecl *dict_new)(void);
    int (__cdecl *dict_set)(PyObject *, const char *, PyObject *);
    PyObject *(__cdecl *dict_get)(PyObject *, const char *);
    PyObject *(__cdecl *get_builtins)(void);
    PyObject *(__cdecl *unicode_from_string)(const char *);
    const char *(__cdecl *unicode_utf8)(PyObject *, Py_ssize_t *);
    PyObject *(__cdecl *bytes_from_data)(const char *, Py_ssize_t);
    PyObject *(__cdecl *long_from_ull)(unsigned long long);
    long long (__cdecl *long_as_ll)(PyObject *);
    PyObject *(__cdecl *tuple_new)(Py_ssize_t);
    int (__cdecl *tuple_set)(PyObject *, Py_ssize_t, PyObject *);
    Py_ssize_t (__cdecl *tuple_size)(PyObject *);
    PyObject *(__cdecl *tuple_get)(PyObject *, Py_ssize_t);
    int (__cdecl *callable)(PyObject *);
    PyObject *(__cdecl *call)(PyObject *, PyObject *);
    int (__cdecl *truth)(PyObject *);
    void (__cdecl *decref)(PyObject *);
    PyObject *(__cdecl *error_occurred)(void);
    void (__cdecl *error_clear)(void);
} PythonApi;

static const unsigned char RESERVATION_MAGIC[] = "KIRA_BLACKWELL_V17_RESERVATION";
static const unsigned char TERMINAL_MAGIC[] = "KIRA_BLACKWELL_V17_TERMINAL";
_Static_assert(sizeof(RESERVATION_MAGIC) - 1U <= sizeof(((ReservationRecord *)0)->magic),
    "reservation magic field too small");
_Static_assert(sizeof(TERMINAL_MAGIC) - 1U <= sizeof(((CompletionRecord *)0)->magic),
    "terminal magic field too small");

static int valid_handle(HANDLE value) {
    return value != NULL && value != INVALID_HANDLE_VALUE;
}

static int lower_hex_exact(const char *value, size_t length) {
    size_t index;
    if (value == NULL || length != SHA_HEX) return 0;
    for (index = 0U; index < SHA_HEX; ++index) {
        const char c = value[index];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    }
    return 1;
}

static int decode_hex(const char *value, size_t length, unsigned char output[SHA_BYTES]) {
    size_t index;
    if (!lower_hex_exact(value, length)) return 0;
    for (index = 0U; index < SHA_BYTES; ++index) {
        unsigned char high;
        unsigned char low;
        const char a = value[index * 2U];
        const char b = value[index * 2U + 1U];
        high = (unsigned char)((a <= '9') ? (a - '0') : (a - 'a' + 10));
        low = (unsigned char)((b <= '9') ? (b - '0') : (b - 'a' + 10));
        output[index] = (unsigned char)((high << 4U) | low);
    }
    return 1;
}

static void digest_hex(const unsigned char digest[SHA_BYTES], char output[SHA_HEX + 1U]) {
    static const char digits[] = "0123456789abcdef";
    size_t index;
    for (index = 0U; index < SHA_BYTES; ++index) {
        output[index * 2U] = digits[(digest[index] >> 4U) & 15U];
        output[index * 2U + 1U] = digits[digest[index] & 15U];
    }
    output[SHA_HEX] = '\0';
}

static int seek_start(HANDLE file) {
    LARGE_INTEGER zero;
    zero.QuadPart = 0;
    return SetFilePointerEx(file, zero, NULL, FILE_BEGIN) != 0;
}

static int regular_file(HANDLE file, ULONGLONG *bytes) {
    FILE_ATTRIBUTE_TAG_INFO attributes;
    FILE_STANDARD_INFO standard;
    if (!valid_handle(file) || bytes == NULL) return 0;
    if (!GetFileInformationByHandleEx(file, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) ||
        (attributes.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0U ||
        !GetFileInformationByHandleEx(file, FileStandardInfo, &standard,
            (DWORD)sizeof(standard)) ||
        standard.EndOfFile.QuadPart < 0) return 0;
    *bytes = (ULONGLONG)standard.EndOfFile.QuadPart;
    return 1;
}

static int sha_memory(const unsigned char *data, size_t length, unsigned char digest[SHA_BYTES]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char *object = NULL;
    DWORD object_bytes = 0U;
    DWORD returned = 0U;
    NTSTATUS status;
    int ok = 0;
    if (data == NULL || digest == NULL || length > (size_t)ULONG_MAX) return 0;
    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) goto cleanup;
    status = BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&object_bytes,
        (ULONG)sizeof(object_bytes), &returned, 0U);
    if (status < 0 || returned != sizeof(object_bytes) || object_bytes == 0U) goto cleanup;
    object = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, object_bytes);
    if (object == NULL) goto cleanup;
    status = BCryptCreateHash(algorithm, &hash, object, object_bytes, NULL, 0U, 0U);
    if (status < 0) goto cleanup;
    status = BCryptHashData(hash, (PUCHAR)data, (ULONG)length, 0U);
    if (status < 0) goto cleanup;
    status = BCryptFinishHash(hash, digest, SHA_BYTES, 0U);
    if (status < 0) goto cleanup;
    ok = 1;
cleanup:
    if (hash != NULL) BCryptDestroyHash(hash);
    if (object != NULL) {
        SecureZeroMemory(object, object_bytes);
        HeapFree(GetProcessHeap(), 0U, object);
    }
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
    return ok;
}

static int hash_handle(HANDLE file, unsigned char digest[SHA_BYTES]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char *object = NULL;
    unsigned char *buffer = NULL;
    DWORD object_bytes = 0U;
    DWORD returned = 0U;
    NTSTATUS status;
    int ok = 0;
    if (!valid_handle(file) || digest == NULL || !seek_start(file)) return 0;
    status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U);
    if (status < 0) goto cleanup;
    status = BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&object_bytes,
        (ULONG)sizeof(object_bytes), &returned, 0U);
    if (status < 0 || returned != sizeof(object_bytes) || object_bytes == 0U) goto cleanup;
    object = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, object_bytes);
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), 0U, HASH_CHUNK);
    if (object == NULL || buffer == NULL) goto cleanup;
    status = BCryptCreateHash(algorithm, &hash, object, object_bytes, NULL, 0U, 0U);
    if (status < 0) goto cleanup;
    for (;;) {
        DWORD got = 0U;
        if (!ReadFile(file, buffer, HASH_CHUNK, &got, NULL)) goto cleanup;
        if (got == 0U) break;
        status = BCryptHashData(hash, buffer, got, 0U);
        if (status < 0) goto cleanup;
    }
    status = BCryptFinishHash(hash, digest, SHA_BYTES, 0U);
    if (status < 0 || !seek_start(file)) goto cleanup;
    ok = 1;
cleanup:
    if (hash != NULL) BCryptDestroyHash(hash);
    if (buffer != NULL) {
        SecureZeroMemory(buffer, HASH_CHUNK);
        HeapFree(GetProcessHeap(), 0U, buffer);
    }
    if (object != NULL) {
        SecureZeroMemory(object, object_bytes);
        HeapFree(GetProcessHeap(), 0U, object);
    }
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0U);
    return ok;
}

static int exact_final_path(HANDLE file, const wchar_t *path) {
    DWORD actual_length;
    DWORD expected_length;
    wchar_t *actual = NULL;
    wchar_t *expected = NULL;
    int ok = 0;
    if (!valid_handle(file) || path == NULL) return 0;
    actual_length = GetFinalPathNameByHandleW(file, NULL, 0U, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    expected_length = GetFullPathNameW(path, 0U, NULL, NULL);
    if (actual_length == 0U || expected_length == 0U ||
        actual_length > 32767U || expected_length > 32767U) return 0;
    actual = (wchar_t *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        ((SIZE_T)actual_length + 1U) * sizeof(wchar_t));
    expected = (wchar_t *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        ((SIZE_T)expected_length + 5U) * sizeof(wchar_t));
    if (actual == NULL || expected == NULL) goto cleanup;
    if (GetFinalPathNameByHandleW(file, actual, actual_length + 1U,
            FILE_NAME_NORMALIZED | VOLUME_NAME_DOS) != actual_length - 1U) goto cleanup;
    actual[actual_length] = L'\0';
    expected[0] = L'\\'; expected[1] = L'\\'; expected[2] = L'?'; expected[3] = L'\\';
    if (GetFullPathNameW(path, expected_length + 1U, expected + 4U, NULL) != expected_length - 1U)
        goto cleanup;
    expected[4U + expected_length] = L'\0';
    ok = _wcsicmp(actual, expected) == 0;
cleanup:
    if (actual != NULL) {
        SecureZeroMemory(actual, ((SIZE_T)actual_length + 1U) * sizeof(wchar_t));
        HeapFree(GetProcessHeap(), 0U, actual);
    }
    if (expected != NULL) {
        SecureZeroMemory(expected, ((SIZE_T)expected_length + 5U) * sizeof(wchar_t));
        HeapFree(GetProcessHeap(), 0U, expected);
    }
    return ok;
}

static int same_identity(const FILE_ID_INFO *left, const FILE_ID_INFO *right) {
    return left != NULL && right != NULL &&
        left->VolumeSerialNumber == right->VolumeSerialNumber &&
        memcmp(left->FileId.Identifier, right->FileId.Identifier,
            sizeof(left->FileId.Identifier)) == 0;
}

static int verify_handle_capture(HANDLE file, const Binding *binding,
    FILE_ID_INFO *observed_identity) {
    ULONGLONG actual_bytes = 0ULL;
    unsigned char digest[SHA_BYTES];
    char hex[SHA_HEX + 1U];
    FILE_ID_INFO current;
    if (!valid_handle(file) || binding == NULL || observed_identity == NULL ||
        !regular_file(file, &actual_bytes) || actual_bytes != binding->bytes ||
        !exact_final_path(file, binding->path) ||
        !GetFileInformationByHandleEx(file, FileIdInfo, &current, (DWORD)sizeof(current)) ||
        !hash_handle(file, digest)) return 0;
    digest_hex(digest, hex);
    if (memcmp(hex, binding->sha256, SHA_HEX) != 0 || binding->sha256[SHA_HEX] != '\0') return 0;
    *observed_identity = current;
    return 1;
}

static int verify_handle_bound(HANDLE file, const Binding *binding,
    const FILE_ID_INFO *expected_identity) {
    FILE_ID_INFO observed_identity;
    if (!verify_handle_capture(file, binding, &observed_identity)) return 0;
    return same_identity(expected_identity, &observed_identity);
}

static int lock_file(LockedFile *locked) {
    if (locked == NULL) return 0;
    locked->handle = CreateFileW(locked->binding.path, GENERIC_READ, FILE_SHARE_READ,
        NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT |
        FILE_FLAG_SEQUENTIAL_SCAN, NULL);
    if (!valid_handle(locked->handle)) return 0;
    if (!verify_handle_capture(locked->handle, &locked->binding, &locked->identity)) {
        CloseHandle(locked->handle);
        locked->handle = INVALID_HANDLE_VALUE;
        return 0;
    }
    return 1;
}

static int read_locked(LockedFile *locked, ULONGLONG maximum,
    unsigned char **data, size_t *length) {
    unsigned char *buffer;
    DWORD got = 0U;
    if (locked == NULL || data == NULL || length == NULL ||
        locked->binding.bytes == 0ULL || locked->binding.bytes > maximum ||
        locked->binding.bytes > (ULONGLONG)MAXDWORD ||
        locked->binding.bytes > (ULONGLONG)(SIZE_MAX - 1U) ||
        !verify_handle_bound(locked->handle, &locked->binding, &locked->identity) ||
        !seek_start(locked->handle)) return 0;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        (SIZE_T)locked->binding.bytes + 1U);
    if (buffer == NULL) return 0;
    if (!ReadFile(locked->handle, buffer, (DWORD)locked->binding.bytes, &got, NULL) ||
        got != (DWORD)locked->binding.bytes ||
        !verify_handle_bound(locked->handle, &locked->binding, &locked->identity)) {
        SecureZeroMemory(buffer, (SIZE_T)locked->binding.bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, buffer);
        return 0;
    }
    buffer[locked->binding.bytes] = 0U;
    *data = buffer;
    *length = (size_t)locked->binding.bytes;
    return 1;
}

static int read_unbound_small(const wchar_t *path, ULONGLONG maximum,
    unsigned char **data, DWORD *length, HANDLE *retained, FILE_ID_INFO *identity) {
    HANDLE file = INVALID_HANDLE_VALUE;
    ULONGLONG bytes = 0ULL;
    unsigned char *buffer = NULL;
    DWORD got = 0U;
    FILE_ID_INFO first;
    FILE_ID_INFO second;
    int ok = 0;
    if (path == NULL || data == NULL || length == NULL || retained == NULL || identity == NULL)
        return 0;
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_SEQUENTIAL_SCAN, NULL);
    if (!valid_handle(file) || !regular_file(file, &bytes) || bytes == 0ULL ||
        bytes > maximum || bytes > (ULONGLONG)MAXDWORD ||
        !exact_final_path(file, path) ||
        !GetFileInformationByHandleEx(file, FileIdInfo, &first, (DWORD)sizeof(first))) goto cleanup;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)bytes + 1U);
    if (buffer == NULL || !seek_start(file) ||
        !ReadFile(file, buffer, (DWORD)bytes, &got, NULL) || got != (DWORD)bytes ||
        !regular_file(file, &bytes) || !exact_final_path(file, path) ||
        !GetFileInformationByHandleEx(file, FileIdInfo, &second, (DWORD)sizeof(second)) ||
        !same_identity(&first, &second)) goto cleanup;
    buffer[got] = 0U;
    *data = buffer;
    *length = got;
    *retained = file;
    *identity = first;
    buffer = NULL;
    file = INVALID_HANDLE_VALUE;
    ok = 1;
cleanup:
    if (buffer != NULL) {
        SecureZeroMemory(buffer, (SIZE_T)bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, buffer);
    }
    if (valid_handle(file)) CloseHandle(file);
    return ok;
}

static int consume_line(char **cursor_io, const char *end, const char *key,
    const char **value, size_t *value_length) {
    char *cursor;
    const char *line_end;
    const size_t key_length = strlen(key);
    if (cursor_io == NULL || *cursor_io == NULL || end == NULL || key == NULL ||
        value == NULL || value_length == NULL) return 0;
    cursor = *cursor_io;
    if (cursor >= end || (size_t)(end - cursor) <= key_length ||
        memcmp(cursor, key, key_length) != 0 || cursor[key_length] != '\t') return 0;
    line_end = (const char *)memchr(cursor + key_length + 1U, '\n',
        (size_t)(end - (cursor + key_length + 1U)));
    if (line_end == NULL) return 0;
    *value = cursor + key_length + 1U;
    *value_length = (size_t)(line_end - *value);
    if (*value_length > 0U && (*value)[*value_length - 1U] == '\r') return 0;
    *cursor_io = (char *)(line_end + 1U);
    return 1;
}

static int exact_value(const char *value, size_t value_length, const char *expected) {
    const size_t expected_length = strlen(expected);
    return value != NULL && value_length == expected_length &&
        memcmp(value, expected, expected_length) == 0;
}

static int parse_ull_exact(const char *value, size_t length, ULONGLONG *result) {
    ULONGLONG number = 0ULL;
    size_t index;
    if (value == NULL || result == NULL || length == 0U || length > 20U) return 0;
    if (length > 1U && value[0] == '0') return 0;
    for (index = 0U; index < length; ++index) {
        const unsigned int digit = (unsigned int)(value[index] - '0');
        if (value[index] < '0' || value[index] > '9' ||
            number > (ULLONG_MAX - digit) / 10ULL) return 0;
        number = number * 10ULL + digit;
    }
    *result = number;
    return 1;
}

static int auditor_exact(const char *value, size_t length, char output[97]) {
    size_t index;
    if (value == NULL || output == NULL || length == 0U || length > 96U) return 0;
    for (index = 0U; index < length; ++index) {
        const char c = value[index];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) return 0;
    }
    memcpy(output, value, length);
    output[length] = '\0';
    return 1;
}

static int verify_audit(AuditValues *values, HANDLE *audit_handle,
    FILE_ID_INFO *audit_identity, HANDLE *digest_handle, FILE_ID_INFO *digest_identity) {
    unsigned char *audit = NULL;
    unsigned char *sidecar = NULL;
    DWORD audit_bytes = 0U;
    DWORD sidecar_bytes = 0U;
    unsigned char digest[SHA_BYTES];
    char digest_text[SHA_HEX + 1U];
    char *cursor;
    const char *end;
    const char *value;
    size_t value_length;
    int ok = 0;
    if (values == NULL || audit_handle == NULL || audit_identity == NULL ||
        digest_handle == NULL || digest_identity == NULL) return 0;
    SecureZeroMemory(values, sizeof(*values));
    *audit_handle = INVALID_HANDLE_VALUE;
    *digest_handle = INVALID_HANDLE_VALUE;
    if (!read_unbound_small(AUDIT_DIGEST_PATH, 65ULL, &sidecar, &sidecar_bytes,
            digest_handle, digest_identity) || sidecar_bytes != 65U ||
        sidecar[64] != '\n' || memchr(sidecar, '\0', 64U) != NULL ||
        !lower_hex_exact((const char *)sidecar, 64U) ||
        !read_unbound_small(AUDIT_PATH, AUDIT_LIMIT, &audit, &audit_bytes,
            audit_handle, audit_identity) || audit_bytes == 0U ||
        memchr(audit, '\0', audit_bytes) != NULL ||
        !sha_memory(audit, audit_bytes, digest) ||
        !sha_memory(sidecar, sidecar_bytes, values->audit_sidecar_sha256)) goto cleanup;
    digest_hex(digest, digest_text);
    if (memcmp(sidecar, digest_text, SHA_HEX) != 0) goto cleanup;
    memcpy(values->audit_sha256, digest, SHA_BYTES);
    values->audit_bytes = audit_bytes;
    cursor = (char *)audit;
    end = (const char *)audit + audit_bytes;
    {
        const size_t magic_length = strlen(AUDIT_MAGIC);
        if ((size_t)(end - cursor) <= magic_length ||
            memcmp(cursor, AUDIT_MAGIC, magic_length) != 0 || cursor[magic_length] != '\n')
            goto cleanup;
        cursor += magic_length + 1U;
    }
    if (!consume_line(&cursor, end, "auditor", &value, &value_length) ||
        !auditor_exact(value, value_length, values->auditor) ||
        !consume_line(&cursor, end, "decision", &value, &value_length) ||
        !exact_value(value, value_length, AUDIT_DECISION) ||
        !consume_line(&cursor, end, "seal_bytes", &value, &value_length) ||
        !parse_ull_exact(value, value_length, &values->seal_bytes) ||
        values->seal_bytes == 0ULL || values->seal_bytes > SEAL_LIMIT ||
        !consume_line(&cursor, end, "seal_sha256", &value, &value_length) ||
        !lower_hex_exact(value, value_length)) goto cleanup;
    memcpy(values->seal_sha256, value, SHA_HEX); values->seal_sha256[SHA_HEX] = '\0';
    if (!consume_line(&cursor, end, "self_bytes", &value, &value_length) ||
        !parse_ull_exact(value, value_length, &values->self_bytes) || values->self_bytes == 0ULL ||
        !consume_line(&cursor, end, "self_sha256", &value, &value_length) ||
        !lower_hex_exact(value, value_length)) goto cleanup;
    memcpy(values->self_sha256, value, SHA_HEX); values->self_sha256[SHA_HEX] = '\0';
    if (!consume_line(&cursor, end, "header_bytes", &value, &value_length) ||
        !parse_ull_exact(value, value_length, &values->header_bytes) || values->header_bytes == 0ULL ||
        !consume_line(&cursor, end, "header_sha256", &value, &value_length) ||
        !lower_hex_exact(value, value_length)) goto cleanup;
    memcpy(values->header_sha256, value, SHA_HEX); values->header_sha256[SHA_HEX] = '\0';
    if (!consume_line(&cursor, end, "sealed_subject_count", &value, &value_length) ||
        !exact_value(value, value_length, V17_SEALED_SUBJECT_COUNT_TEXT) ||
        !consume_line(&cursor, end, "all_subjects_exact", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "v16_trailing_bytes_refused", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "v16_logical_duplicate_refused", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "actual_55_objects_exact", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "unique_paths_exact", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "ordered_binding_set_equality_exact", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "all_dot_segments_refused", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "v17_provenance_exact", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "compiled_hostile_checks", &value, &value_length) ||
        !exact_value(value, value_length, "83") ||
        !consume_line(&cursor, end, "source_predicate_mutants_refused", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "retained_v15_v14_control_graph_exact", &value, &value_length) ||
        !exact_value(value, value_length, "true") ||
        !consume_line(&cursor, end, "production_routing_authorized", &value, &value_length) ||
        !exact_value(value, value_length, "false") ||
        !consume_line(&cursor, end, "live_execution_authorized", &value, &value_length) ||
        !exact_value(value, value_length, "false") ||
        !consume_line(&cursor, end, "synthesis_authorized", &value, &value_length) ||
        !exact_value(value, value_length, "false") ||
        !consume_line(&cursor, end, "playback_authorized", &value, &value_length) ||
        !exact_value(value, value_length, "false") ||
        !consume_line(&cursor, end, "latency_run_authorized", &value, &value_length) ||
        !exact_value(value, value_length, "false") ||
        !consume_line(&cursor, end, "audit_nonce", &value, &value_length) ||
        !decode_hex(value, value_length, values->nonce) || cursor != end) goto cleanup;
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
    if (!ok) {
        if (valid_handle(*audit_handle)) CloseHandle(*audit_handle);
        if (valid_handle(*digest_handle)) CloseHandle(*digest_handle);
        *audit_handle = INVALID_HANDLE_VALUE;
        *digest_handle = INVALID_HANDLE_VALUE;
    }
    return ok;
}

typedef struct ManifestCursor {
    const unsigned char *cursor;
    const unsigned char *end;
} ManifestCursor;

typedef struct ParsedSubject {
    char path[1901];
    ULONGLONG bytes;
    char sha256[SHA_HEX + 1U];
} ParsedSubject;

static int manifest_consume(ManifestCursor *input, const char *literal) {
    const size_t length = (literal == NULL) ? 0U : strlen(literal);
    if (input == NULL || literal == NULL || length == 0U ||
        (size_t)(input->end - input->cursor) < length ||
        memcmp(input->cursor, literal, length) != 0) return 0;
    input->cursor += length;
    return 1;
}

static int canonical_manifest_path(const char *value) {
    size_t index;
    size_t length;
    size_t segment_start = 0U;
    if (value == NULL) return 0;
    if (strcmp(value, "C:/Python314/python314.dll") == 0) return 1;
    length = strlen(value);
    if (length == 0U || length > 1900U || value[0] == '/' ||
        value[length - 1U] == '/') return 0;
    for (index = 0U; index <= length; ++index) {
        if (index == length || value[index] == '/') {
            const size_t segment_length = index - segment_start;
            if (segment_length == 0U ||
                (segment_length == 1U && value[segment_start] == '.') ||
                (segment_length == 2U && value[segment_start] == '.' &&
                    value[segment_start + 1U] == '.')) return 0; /* V17_SEGMENT_DOT_REFUSAL_PREDICATE */
            segment_start = index + 1U;
        } else {
            const unsigned char c = (unsigned char)value[index];
            if (c < 0x20U || c > 0x7eU || c == '\\' || c == '"' || c == ':')
                return 0;
        }
    }
    return 1;
}

static int manifest_path(ManifestCursor *input, char output[1901]) {
    size_t length = 0U;
    if (input == NULL || output == NULL || !manifest_consume(input, "\"")) return 0;
    while (input->cursor < input->end && *input->cursor != (unsigned char)'"') {
        const unsigned char c = *input->cursor;
        if (length >= 1900U || c < 0x20U || c > 0x7eU || c == '\\') return 0;
        output[length++] = (char)c;
        ++input->cursor;
    }
    if (input->cursor >= input->end || *input->cursor != (unsigned char)'"') return 0;
    ++input->cursor;
    output[length] = '\0';
    return canonical_manifest_path(output);
}

static int manifest_positive_u64(ManifestCursor *input, ULONGLONG *output) {
    ULONGLONG value = 0ULL;
    size_t digits = 0U;
    if (input == NULL || output == NULL || input->cursor >= input->end ||
        *input->cursor < (unsigned char)'1' || *input->cursor > (unsigned char)'9') return 0;
    while (input->cursor < input->end && *input->cursor >= (unsigned char)'0' &&
        *input->cursor <= (unsigned char)'9') {
        const ULONGLONG digit = (ULONGLONG)(*input->cursor - (unsigned char)'0');
        if (value > (ULLONG_MAX - digit) / 10ULL) return 0;
        value = value * 10ULL + digit;
        ++input->cursor;
        ++digits;
    }
    if (digits == 0U || value == 0ULL) return 0;
    *output = value;
    return 1;
}

static int manifest_digest(ManifestCursor *input, char output[SHA_HEX + 1U]) {
    size_t index;
    if (input == NULL || output == NULL || !manifest_consume(input, "\"")) return 0;
    if ((size_t)(input->end - input->cursor) < SHA_HEX + 1U) return 0;
    for (index = 0U; index < SHA_HEX; ++index) {
        const unsigned char c = input->cursor[index];
        if (!((c >= (unsigned char)'0' && c <= (unsigned char)'9') ||
            (c >= (unsigned char)'a' && c <= (unsigned char)'f'))) return 0;
        output[index] = (char)c;
    }
    input->cursor += SHA_HEX;
    if (*input->cursor != (unsigned char)'"') return 0;
    ++input->cursor;
    output[SHA_HEX] = '\0';
    return 1;
}

static int manifest_subject(ManifestCursor *input, ParsedSubject *subject) {
    if (input == NULL || subject == NULL) return 0;
    SecureZeroMemory(subject, sizeof(*subject));
    return manifest_consume(input, "{\"path\":") &&
        manifest_path(input, subject->path) &&
        manifest_consume(input, ",\"bytes\":") &&
        manifest_positive_u64(input, &subject->bytes) &&
        manifest_consume(input, ",\"sha256\":") &&
        manifest_digest(input, subject->sha256) &&
        manifest_consume(input, "}");
}

static int verify_output_parent(void) {
    HANDLE directory;
    FILE_ATTRIBUTE_TAG_INFO attributes;
    int ok = 0;
    directory = CreateFileW(OUTPUT_PARENT_PATH, FILE_READ_ATTRIBUTES,
        FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (!valid_handle(directory)) return 0;
    if (GetFileInformationByHandleEx(directory, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0U &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0U &&
        exact_final_path(directory, OUTPUT_PARENT_PATH)) ok = 1;
    CloseHandle(directory);
    return ok;
}

static int append_line(HANDLE file, const char *line) {
    DWORD wrote = 0U;
    const size_t length = strlen(line);
    if (!valid_handle(file) || line == NULL || length == 0U || length > MAXDWORD) return 0;
    if (!WriteFile(file, line, (DWORD)length, &wrote, NULL) || wrote != (DWORD)length)
        return 0;
    return FlushFileBuffers(file) != 0;
}

static int read_exact_at(HANDLE file, LONGLONG offset, void *buffer, DWORD bytes) {
    LARGE_INTEGER position;
    DWORD got = 0U;
    position.QuadPart = offset;
    if (!valid_handle(file) || buffer == NULL || bytes == 0U ||
        !SetFilePointerEx(file, position, NULL, FILE_BEGIN) ||
        !ReadFile(file, buffer, bytes, &got, NULL) || got != bytes) return 0;
    return 1;
}

static int file_identity(HANDLE file, FILE_ID_INFO *identity) {
    return valid_handle(file) && identity != NULL &&
        GetFileInformationByHandleEx(file, FileIdInfo, identity, (DWORD)sizeof(*identity)) != 0;
}

static int reserve_outcome(HANDLE receipt, HANDLE evidence,
    const LockedFile *self, const LockedFile *seal, const LockedFile *source,
    const LockedFile *python_source, const LockedFile *v14_decision,
    const AuditValues *audit, ReservationRecord *record_out,
    FILE_ID_INFO *receipt_identity, FILE_ID_INFO *evidence_identity) {
    ReservationRecord record;
    DWORD wrote = 0U;
    unsigned char digest[SHA_BYTES];
    FILE_ID_INFO current_receipt;
    FILE_ID_INFO current_evidence;
    if (!valid_handle(receipt) || !valid_handle(evidence) || self == NULL || seal == NULL ||
        source == NULL || python_source == NULL || v14_decision == NULL || audit == NULL ||
        record_out == NULL || receipt_identity == NULL || evidence_identity == NULL ||
        !file_identity(receipt, &current_receipt) || !file_identity(evidence, &current_evidence))
        return 0;
    SecureZeroMemory(&record, sizeof(record));
    memcpy(record.magic, RESERVATION_MAGIC, sizeof(RESERVATION_MAGIC) - 1U);
    record.version = 1U;
    record.type = 1U;
    record.bytes = (uint32_t)sizeof(record);
    record.state = RECORD_PENDING;
    if (!decode_hex(self->binding.sha256, SHA_HEX, record.executable_sha256) ||
        !decode_hex(seal->binding.sha256, SHA_HEX, record.seal_sha256) ||
        !decode_hex(source->binding.sha256, SHA_HEX, record.source_sha256) ||
        !decode_hex(python_source->binding.sha256, SHA_HEX, record.python_source_sha256) ||
        !decode_hex(v14_decision->binding.sha256, SHA_HEX, record.v14_rejection_sha256))
        return 0;
    memcpy(record.audit_sha256, audit->audit_sha256, SHA_BYTES);
    memcpy(record.nonce, audit->nonce, SHA_BYTES);
    record.receipt_volume = current_receipt.VolumeSerialNumber;
    memcpy(record.receipt_id, current_receipt.FileId.Identifier, sizeof(record.receipt_id));
    record.evidence_volume = current_evidence.VolumeSerialNumber;
    memcpy(record.evidence_id, current_evidence.FileId.Identifier, sizeof(record.evidence_id));
    if (!seek_start(receipt) ||
        !WriteFile(receipt, &record, (DWORD)sizeof(record), &wrote, NULL) ||
        wrote != sizeof(record) || !FlushFileBuffers(receipt) ||
        !read_exact_at(receipt, 0LL, record_out, (DWORD)sizeof(*record_out)) ||
        memcmp(&record, record_out, sizeof(record)) != 0 ||
        !sha_memory((const unsigned char *)record_out, sizeof(*record_out), digest)) return 0;
    *receipt_identity = current_receipt;
    *evidence_identity = current_evidence;
    return append_line(evidence, E_RESERVED);
}

static int finish_outcome(HANDLE receipt, HANDLE evidence,
    const FILE_ID_INFO *receipt_identity, const FILE_ID_INFO *evidence_identity,
    const ReservationRecord *reservation, uint32_t state, uint32_t terminal_stage,
    const UnloadTelemetry *unload) {
    CompletionRecord record;
    FILE_ID_INFO current_receipt;
    FILE_ID_INFO current_evidence;
    LARGE_INTEGER end;
    DWORD wrote = 0U;
    if (!valid_handle(receipt) || !valid_handle(evidence) || receipt_identity == NULL ||
        evidence_identity == NULL || reservation == NULL || unload == NULL ||
        !file_identity(receipt, &current_receipt) || !same_identity(receipt_identity, &current_receipt) ||
        !file_identity(evidence, &current_evidence) || !same_identity(evidence_identity, &current_evidence))
        return 0;
    SecureZeroMemory(&record, sizeof(record));
    memcpy(record.magic, TERMINAL_MAGIC, sizeof(TERMINAL_MAGIC) - 1U);
    record.version = 1U;
    record.type = 2U;
    record.bytes = (uint32_t)sizeof(record);
    record.state = state;
    record.terminal_stage = terminal_stage;
    record.python_finalize_result = unload->finalize_called ? unload->finalize_result : UINT32_MAX;
    record.free_library_succeeded = unload->free_library_succeeded;
    record.old_module_absent = unload->old_module_absent;
    record.exact_path_absent = unload->exact_path_absent;
    record.modules_enumerated = unload->modules_enumerated;
    if (!sha_memory((const unsigned char *)reservation, sizeof(*reservation),
            record.reservation_sha256)) return 0;
    memcpy(record.executable_sha256, reservation->executable_sha256, SHA_BYTES);
    memcpy(record.audit_sha256, reservation->audit_sha256, SHA_BYTES);
    memcpy(record.seal_sha256, reservation->seal_sha256, SHA_BYTES);
    memcpy(record.source_sha256, reservation->source_sha256, SHA_BYTES);
    memcpy(record.python_source_sha256, reservation->python_source_sha256, SHA_BYTES);
    memcpy(record.v14_rejection_sha256, reservation->v14_rejection_sha256, SHA_BYTES);
    record.receipt_volume = current_receipt.VolumeSerialNumber;
    memcpy(record.receipt_id, current_receipt.FileId.Identifier, sizeof(record.receipt_id));
    record.evidence_volume = current_evidence.VolumeSerialNumber;
    memcpy(record.evidence_id, current_evidence.FileId.Identifier, sizeof(record.evidence_id));
    end.QuadPart = 0LL;
    if (!SetFilePointerEx(receipt, end, NULL, FILE_END) ||
        !WriteFile(receipt, &record, (DWORD)sizeof(record), &wrote, NULL) ||
        wrote != sizeof(record) || !FlushFileBuffers(receipt)) return 0;
    return append_line(evidence, state == RECORD_SUCCESS ? E_SUCCESS : E_FAILURE);
}

#define RESOLVE_API(api, member, export_name) do { \
    FARPROC procedure = GetProcAddress((api)->module, (export_name)); \
    if (procedure == NULL || sizeof(procedure) != sizeof((api)->member)) return 0; \
    memcpy(&(api)->member, &procedure, sizeof(procedure)); \
} while (0)

static int resolve_python_api(PythonApi *api) {
    if (api == NULL || api->module == NULL) return 0;
    RESOLVE_API(api, config_init, "PyConfig_InitIsolatedConfig");
    RESOLVE_API(api, config_set_string, "PyConfig_SetString");
    RESOLVE_API(api, wide_append, "PyWideStringList_Append");
    RESOLVE_API(api, initialize, "Py_InitializeFromConfig");
    RESOLVE_API(api, status_exception, "PyStatus_Exception");
    RESOLVE_API(api, config_clear, "PyConfig_Clear");
    RESOLVE_API(api, finalize, "Py_FinalizeEx");
    RESOLVE_API(api, compile, "Py_CompileStringExFlags");
    RESOLVE_API(api, eval_code, "PyEval_EvalCode");
    RESOLVE_API(api, dict_new, "PyDict_New");
    RESOLVE_API(api, dict_set, "PyDict_SetItemString");
    RESOLVE_API(api, dict_get, "PyDict_GetItemString");
    RESOLVE_API(api, get_builtins, "PyEval_GetBuiltins");
    RESOLVE_API(api, unicode_from_string, "PyUnicode_FromString");
    RESOLVE_API(api, unicode_utf8, "PyUnicode_AsUTF8AndSize");
    RESOLVE_API(api, bytes_from_data, "PyBytes_FromStringAndSize");
    RESOLVE_API(api, long_from_ull, "PyLong_FromUnsignedLongLong");
    RESOLVE_API(api, long_as_ll, "PyLong_AsLongLong");
    RESOLVE_API(api, tuple_new, "PyTuple_New");
    RESOLVE_API(api, tuple_set, "PyTuple_SetItem");
    RESOLVE_API(api, tuple_size, "PyTuple_Size");
    RESOLVE_API(api, tuple_get, "PyTuple_GetItem");
    RESOLVE_API(api, callable, "PyCallable_Check");
    RESOLVE_API(api, call, "PyObject_CallObject");
    RESOLVE_API(api, truth, "PyObject_IsTrue");
    RESOLVE_API(api, decref, "Py_DecRef");
    RESOLVE_API(api, error_occurred, "PyErr_Occurred");
    RESOLVE_API(api, error_clear, "PyErr_Clear");
    return 1;
}

static int prove_python_module_absent(HMODULE old_module, UnloadTelemetry *telemetry) {
    HANDLE snapshot;
    MODULEENTRY32W entry;
    int first;
    int old_absent = 1;
    int path_absent = 1;
    uint32_t count = 0U;
    if (old_module == NULL || telemetry == NULL) return 0;
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
        GetCurrentProcessId());
    if (!valid_handle(snapshot)) return 0;
    SecureZeroMemory(&entry, sizeof(entry));
    entry.dwSize = sizeof(entry);
    first = Module32FirstW(snapshot, &entry);
    while (first) {
        if (count == UINT32_MAX) {
            CloseHandle(snapshot);
            return 0;
        }
        ++count;
        if ((HMODULE)entry.modBaseAddr == old_module) old_absent = 0;
        if (_wcsicmp(entry.szExePath, PYTHON_DLL_PATH) == 0) path_absent = 0;
        entry.dwSize = sizeof(entry);
        first = Module32NextW(snapshot, &entry);
    }
    if (GetLastError() != ERROR_NO_MORE_FILES) {
        CloseHandle(snapshot);
        return 0;
    }
    CloseHandle(snapshot);
    telemetry->old_module_absent = old_absent ? 1U : 0U;
    telemetry->exact_path_absent = path_absent ? 1U : 0U;
    telemetry->modules_enumerated = count;
    return old_absent && path_absent && count > 0U;
}

static PyObject *make_predecessor_attestations(PythonApi *api,
    const LockedFile predecessors[V17_PREDECESSOR_COUNT]) {
    PyObject *outer;
    size_t index;
    if (api == NULL || predecessors == NULL) return NULL;
    outer = api->tuple_new((Py_ssize_t)V17_PREDECESSOR_COUNT);
    if (outer == NULL) return NULL;
    for (index = 0U; index < V17_PREDECESSOR_COUNT; ++index) {
        const LockedFile *locked = &predecessors[index];
        PyObject *row = api->tuple_new(5);
        PyObject *path = NULL;
        PyObject *bytes = NULL;
        PyObject *digest = NULL;
        PyObject *volume = NULL;
        PyObject *identifier = NULL;
        if (row == NULL) goto fail;
        path = api->unicode_from_string(locked->binding.relative_path);
        bytes = api->long_from_ull((unsigned long long)locked->binding.bytes);
        digest = api->unicode_from_string(locked->binding.sha256);
        volume = api->long_from_ull((unsigned long long)locked->identity.VolumeSerialNumber);
        identifier = api->bytes_from_data(
            (const char *)locked->identity.FileId.Identifier,
            (Py_ssize_t)sizeof(locked->identity.FileId.Identifier));
        if (path == NULL || bytes == NULL || digest == NULL || volume == NULL ||
            identifier == NULL) {
            if (path != NULL) api->decref(path);
            if (bytes != NULL) api->decref(bytes);
            if (digest != NULL) api->decref(digest);
            if (volume != NULL) api->decref(volume);
            if (identifier != NULL) api->decref(identifier);
            api->decref(row);
            goto fail;
        }
        if (api->tuple_set(row, 0, path) < 0) goto row_fail;
        path = NULL;
        if (api->tuple_set(row, 1, bytes) < 0) goto row_fail;
        bytes = NULL;
        if (api->tuple_set(row, 2, digest) < 0) goto row_fail;
        digest = NULL;
        if (api->tuple_set(row, 3, volume) < 0) goto row_fail;
        volume = NULL;
        if (api->tuple_set(row, 4, identifier) < 0) goto row_fail;
        identifier = NULL;
        if (api->tuple_set(outer, (Py_ssize_t)index, row) < 0) {
            api->decref(row);
            goto fail;
        }
        continue;
row_fail:
        {
            if (path != NULL) api->decref(path);
            if (bytes != NULL) api->decref(bytes);
            if (digest != NULL) api->decref(digest);
            if (volume != NULL) api->decref(volume);
            if (identifier != NULL) api->decref(identifier);
            api->decref(row);
            goto fail;
        }
    }
    return outer;
fail:
    api->decref(outer);
    return NULL;
}

static int result_exact(PythonApi *api, PyObject *result) {
    static const char expected_schema[] = "kira.blackwell.v15.native_validator_result.v1";
    PyObject *schema;
    Py_ssize_t length = 0;
    const char *text;
    long long predecessor_count;
    long long graph_count;
    Py_ssize_t index;
    if (api == NULL || result == NULL || api->tuple_size(result) != 10) return 0;
    schema = api->tuple_get(result, 0);
    text = schema != NULL ? api->unicode_utf8(schema, &length) : NULL;
    if (text == NULL || length != (Py_ssize_t)(sizeof(expected_schema) - 1U) ||
        memcmp(text, expected_schema, sizeof(expected_schema) - 1U) != 0 ||
        api->truth(api->tuple_get(result, 1)) != 1) return 0;
    predecessor_count = api->long_as_ll(api->tuple_get(result, 2));
    graph_count = api->long_as_ll(api->tuple_get(result, 3));
    if (predecessor_count != 6LL || graph_count <= 0LL) return 0;
    for (index = 4; index < 10; ++index) {
        if (api->truth(api->tuple_get(result, index)) != 0) return 0;
    }
    return api->error_occurred() == NULL;
}

static int run_python_validation(LockedFile *python_dll, LockedFile *stdlib_zip,
    LockedFile *validator, LockedFile *python_source, LockedFile *config,
    LockedFile predecessors[V17_PREDECESSOR_COUNT], uint32_t *stage,
    UnloadTelemetry *unload) {
    PythonApi api;
    PyConfig python_config;
    PyStatus status;
    unsigned char *validator_bytes = NULL;
    unsigned char *python_bytes = NULL;
    unsigned char *config_bytes = NULL;
    unsigned char *v14_source_bytes = NULL;
    unsigned char *v14_config_bytes = NULL;
    unsigned char *v14_seal_bytes = NULL;
    unsigned char *v14_decision_bytes = NULL;
    size_t validator_length = 0U;
    size_t python_length = 0U;
    size_t config_length = 0U;
    size_t v14_source_length = 0U;
    size_t v14_config_length = 0U;
    size_t v14_seal_length = 0U;
    size_t v14_decision_length = 0U;
    PyObject *globals = NULL;
    PyObject *builtins;
    PyObject *name = NULL;
    PyObject *file_name = NULL;
    PyObject *code = NULL;
    PyObject *evaluation = NULL;
    PyObject *callable = NULL;
    PyObject *arguments = NULL;
    PyObject *attestations = NULL;
    PyObject *result = NULL;
    wchar_t module_path[MAX_PATH];
    DWORD module_length;
    HMODULE old_module = NULL;
    int initialized = 0;
    int ok = 0;
    size_t index;
    SecureZeroMemory(&api, sizeof(api));
    SecureZeroMemory(unload, sizeof(*unload));
    if (!SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS) ||
        !verify_handle_bound(python_dll->handle, &python_dll->binding, &python_dll->identity) ||
        !verify_handle_bound(stdlib_zip->handle, &stdlib_zip->binding, &stdlib_zip->identity))
        return 0;
    api.module = LoadLibraryExW(PYTHON_DLL_PATH, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (api.module == NULL) return 0;
    old_module = api.module;
    module_length = GetModuleFileNameW(api.module, module_path, (DWORD)_countof(module_path));
    if (module_length == 0U || module_length >= (DWORD)_countof(module_path) ||
        _wcsicmp(module_path, PYTHON_DLL_PATH) != 0 || !resolve_python_api(&api)) goto cleanup;
    *stage = 30U;
    api.config_init(&python_config);
    python_config.use_environment = 0;
    python_config.user_site_directory = 0;
    python_config.site_import = 0;
    python_config.write_bytecode = 0;
    python_config.install_signal_handlers = 0;
    python_config.parse_argv = 0;
    python_config.safe_path = 1;
    python_config.module_search_paths_set = 1;
    status = api.config_set_string(&python_config, &python_config.program_name, SELF_PATH);
    if (!api.status_exception(status))
        status = api.config_set_string(&python_config, &python_config.executable, SELF_PATH);
    if (!api.status_exception(status))
        status = api.wide_append(&python_config.module_search_paths, STDLIB_ZIP_PATH);
    if (!api.status_exception(status))
        status = api.wide_append(&python_config.argv, L"<blackwell-v15-static-control>");
    if (api.status_exception(status)) {
        api.config_clear(&python_config);
        goto cleanup;
    }
    status = api.initialize(&python_config);
    api.config_clear(&python_config);
    if (api.status_exception(status)) goto cleanup;
    initialized = 1;
    *stage = 40U;
    if (!read_locked(validator, SOURCE_LIMIT, &validator_bytes, &validator_length) ||
        memchr(validator_bytes, '\0', validator_length) != NULL ||
        !read_locked(python_source, SOURCE_LIMIT, &python_bytes, &python_length) ||
        memchr(python_bytes, '\0', python_length) != NULL ||
        !read_locked(config, SOURCE_LIMIT, &config_bytes, &config_length) ||
        memchr(config_bytes, '\0', config_length) != NULL ||
        !read_locked(&predecessors[0], SOURCE_LIMIT, &v14_source_bytes, &v14_source_length) ||
        memchr(v14_source_bytes, '\0', v14_source_length) != NULL ||
        !read_locked(&predecessors[1], SOURCE_LIMIT, &v14_config_bytes, &v14_config_length) ||
        memchr(v14_config_bytes, '\0', v14_config_length) != NULL ||
        !read_locked(&predecessors[3], SOURCE_LIMIT, &v14_seal_bytes, &v14_seal_length) ||
        memchr(v14_seal_bytes, '\0', v14_seal_length) != NULL ||
        !read_locked(&predecessors[4], SOURCE_LIMIT, &v14_decision_bytes, &v14_decision_length) ||
        memchr(v14_decision_bytes, '\0', v14_decision_length) != NULL) goto cleanup;
    globals = api.dict_new();
    builtins = api.get_builtins();
    name = api.unicode_from_string("_kira_blackwell_v15_private_native_validator");
    file_name = api.unicode_from_string(
        "C:/Users/robmc/Kira/tools/native/kira_blackwell_voice_control_anchor_v15_validator.py");
    if (globals == NULL || builtins == NULL || name == NULL || file_name == NULL ||
        api.dict_set(globals, "__builtins__", builtins) < 0 ||
        api.dict_set(globals, "__name__", name) < 0 ||
        api.dict_set(globals, "__file__", file_name) < 0) goto cleanup;
    code = api.compile((const char *)validator_bytes,
        "C:/Users/robmc/Kira/tools/native/kira_blackwell_voice_control_anchor_v15_validator.py",
        Py_file_input, NULL, -1);
    if (code == NULL) goto cleanup;
    evaluation = api.eval_code(code, globals, globals);
    if (evaluation == NULL) goto cleanup;
    callable = api.dict_get(globals, "validate_static_control_graph_v15");
    if (callable == NULL || api.callable == NULL || api.callable(callable) != 1) goto cleanup;
    attestations = make_predecessor_attestations(&api, predecessors);
    arguments = api.tuple_new(7);
    if (attestations == NULL || arguments == NULL) goto cleanup;
    {
        const unsigned char *buffers[6] = {
            python_bytes, config_bytes, v14_source_bytes, v14_config_bytes,
            v14_seal_bytes, v14_decision_bytes
        };
        const size_t lengths[6] = {
            python_length, config_length, v14_source_length, v14_config_length,
            v14_seal_length, v14_decision_length
        };
        for (index = 0U; index < 6U; ++index) {
            PyObject *item;
            if (lengths[index] > (size_t)PY_SSIZE_T_MAX) goto cleanup;
            item = api.bytes_from_data((const char *)buffers[index], (Py_ssize_t)lengths[index]);
            if (item == NULL || api.tuple_set(arguments, (Py_ssize_t)index, item) < 0) {
                if (item != NULL) api.decref(item);
                goto cleanup;
            }
        }
    }
    if (api.tuple_set(arguments, 6, attestations) < 0) goto cleanup;
    attestations = NULL;
    *stage = 50U;
    result = api.call(callable, arguments);
    if (result == NULL || !result_exact(&api, result)) goto cleanup;
    for (index = 0U; index < V17_PREDECESSOR_COUNT; ++index) {
        if (!verify_handle_bound(predecessors[index].handle,
                &predecessors[index].binding, &predecessors[index].identity)) goto cleanup;
    }
    if (!verify_handle_bound(validator->handle, &validator->binding, &validator->identity) ||
        !verify_handle_bound(python_source->handle, &python_source->binding,
            &python_source->identity) ||
        !verify_handle_bound(config->handle, &config->binding, &config->identity) ||
        !verify_handle_bound(python_dll->handle, &python_dll->binding, &python_dll->identity) ||
        !verify_handle_bound(stdlib_zip->handle, &stdlib_zip->binding, &stdlib_zip->identity))
        goto cleanup;
    ok = 1;
cleanup:
    if (api.error_occurred != NULL && api.error_occurred() != NULL && api.error_clear != NULL)
        api.error_clear();
    if (api.decref != NULL) {
        if (result != NULL) api.decref(result);
        if (arguments != NULL) api.decref(arguments);
        if (attestations != NULL) api.decref(attestations);
        if (evaluation != NULL) api.decref(evaluation);
        if (code != NULL) api.decref(code);
        if (file_name != NULL) api.decref(file_name);
        if (name != NULL) api.decref(name);
        if (globals != NULL) api.decref(globals);
    }
    if (validator_bytes != NULL) {
        SecureZeroMemory(validator_bytes, validator_length + 1U);
        HeapFree(GetProcessHeap(), 0U, validator_bytes);
    }
    if (python_bytes != NULL) {
        SecureZeroMemory(python_bytes, python_length + 1U);
        HeapFree(GetProcessHeap(), 0U, python_bytes);
    }
    if (config_bytes != NULL) {
        SecureZeroMemory(config_bytes, config_length + 1U);
        HeapFree(GetProcessHeap(), 0U, config_bytes);
    }
    if (v14_source_bytes != NULL) {
        SecureZeroMemory(v14_source_bytes, v14_source_length + 1U);
        HeapFree(GetProcessHeap(), 0U, v14_source_bytes);
    }
    if (v14_config_bytes != NULL) {
        SecureZeroMemory(v14_config_bytes, v14_config_length + 1U);
        HeapFree(GetProcessHeap(), 0U, v14_config_bytes);
    }
    if (v14_seal_bytes != NULL) {
        SecureZeroMemory(v14_seal_bytes, v14_seal_length + 1U);
        HeapFree(GetProcessHeap(), 0U, v14_seal_bytes);
    }
    if (v14_decision_bytes != NULL) {
        SecureZeroMemory(v14_decision_bytes, v14_decision_length + 1U);
        HeapFree(GetProcessHeap(), 0U, v14_decision_bytes);
    }
    if (initialized) {
        const int finalize_result = api.finalize();
        unload->finalize_called = 1U;
        unload->finalize_result = (uint32_t)finalize_result;
        if (finalize_result < 0) ok = 0;
    }
    if (api.module != NULL) {
        if (FreeLibrary(api.module)) unload->free_library_succeeded = 1U;
        else ok = 0;
        api.module = NULL;
    }
    if (!prove_python_module_absent(old_module, unload)) ok = 0;
    if (ok) *stage = 60U;
    return ok;
}

static int verify_audit_handles(const AuditValues *audit, HANDLE audit_handle,
    const FILE_ID_INFO *audit_identity, HANDLE digest_handle,
    const FILE_ID_INFO *digest_identity) {
    Binding audit_binding;
    Binding digest_binding;
    char audit_hex[SHA_HEX + 1U];
    char digest_hex_text[SHA_HEX + 1U];
    if (audit == NULL || audit_identity == NULL || digest_identity == NULL) return 0;
    digest_hex(audit->audit_sha256, audit_hex);
    digest_hex(audit->audit_sidecar_sha256, digest_hex_text);
    audit_binding.path = AUDIT_PATH;
    audit_binding.relative_path = "RecoverySprint/continuation_20260811/blackwell_v17_native_whole_document_manifest_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv";
    audit_binding.bytes = audit->audit_bytes;
    audit_binding.sha256 = audit_hex;
    audit_binding.label = "different-review audit";
    digest_binding.path = AUDIT_DIGEST_PATH;
    digest_binding.relative_path = "RecoverySprint/continuation_20260811/blackwell_v17_native_whole_document_manifest_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.sha256";
    digest_binding.bytes = 65ULL;
    digest_binding.sha256 = digest_hex_text;
    digest_binding.label = "different-review audit sidecar";
    return verify_handle_bound(audit_handle, &audit_binding, audit_identity) &&
        verify_handle_bound(digest_handle, &digest_binding, digest_identity);
}

static int recheck_locked_set(LockedFile *items, size_t count) {
    size_t index;
    if (items == NULL) return 0;
    for (index = 0U; index < count; ++index) {
        if (!verify_handle_bound(items[index].handle, &items[index].binding,
                &items[index].identity)) return 0;
    }
    return 1;
}

static int seal_contract_exact(const unsigned char *seal, size_t seal_bytes,
    const Binding *expected, size_t expected_count) {
    static const char canonical_prefix[] =
        "{\"schema\":\"kira.blackwell.v17.native_whole_document_manifest_control_anchor.static_seal.v1\"," 
        "\"candidate_id\":\"kira_chatterbox_blackwell_native_whole_document_manifest_control_anchor_candidate_v17\"," 
        "\"status\":\"SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT\"," 
        "\"execution_authority\":\"NONE\",\"candidate_executed\":false,"
        "\"python_candidate_invoked\":false,\"model_calls\":0,\"gpu_voice_calls\":0,"
        "\"synthesis_calls\":0,\"playback_calls\":0,\"latency_measurements\":0,"
        "\"v15_authority_consumed\":true,\"v16_rejected_uninvoked\":true,"
        "\"v15_rerun\":false,\"v16_run\":false,"
        "\"repair_id\":\"V16_WHOLE_DOCUMENT_CANONICAL_SET_EQUALITY_REPAIR\","
        "\"sealed_subject_count\":55,\"unique_paths\":true,\"subjects\":[";
    ManifestCursor input;
    unsigned char matched[V17_SEALED_SUBJECT_COUNT];
    size_t actual_object_count = 0U;
    size_t index;
    if (seal == NULL || expected == NULL || seal_bytes == 0U || seal_bytes > SEAL_LIMIT ||
        expected_count != V17_SEALED_SUBJECT_COUNT) return 0;
    SecureZeroMemory(matched, sizeof(matched));
    for (index = 0U; index < expected_count; ++index) {
        size_t prior;
        if (expected[index].relative_path == NULL ||
            !canonical_manifest_path(expected[index].relative_path) ||
            expected[index].bytes == 0ULL || expected[index].sha256 == NULL ||
            !lower_hex_exact(expected[index].sha256, strlen(expected[index].sha256))) return 0;
        for (prior = 0U; prior < index; ++prior) {
            if (strcmp(expected[index].relative_path, expected[prior].relative_path) == 0)
                return 0;
        }
    }
    input.cursor = seal;
    input.end = seal + seal_bytes;
    if (!manifest_consume(&input, canonical_prefix)) return 0; /* V17_PROVENANCE_PREDICATE */
    while (actual_object_count < expected_count) {
        ParsedSubject subject;
        size_t match_index = expected_count;
        if (actual_object_count != 0U && !manifest_consume(&input, ",")) return 0;
        if (!manifest_subject(&input, &subject)) return 0;
        for (index = 0U; index < expected_count; ++index) {
            if (strcmp(subject.path, expected[index].relative_path) == 0 &&
                subject.bytes == expected[index].bytes &&
                strcmp(subject.sha256, expected[index].sha256) == 0) {
                if (match_index != expected_count) return 0;
                match_index = index;
            }
        }
        if (match_index == expected_count) return 0;
        if (matched[match_index] != 0U) return 0; /* V17_PARSED_PATH_UNIQUENESS_PREDICATE */
        if (match_index != actual_object_count) return 0; /* V17_EXPECTED_SET_EQUALITY_PREDICATE */
        matched[match_index] = 1U;
        ++actual_object_count;
    }
    if (actual_object_count != expected_count) return 0; /* V17_ACTUAL_OBJECT_COUNT_PREDICATE */
    if (!manifest_consume(&input, "]}")) return 0;
    if (input.cursor != input.end) return 0; /* V17_FINAL_EOF_PREDICATE */
    for (index = 0U; index < expected_count; ++index) {
        if (matched[index] != 1U) return 0;
    }
    return 1;
}

typedef struct StaticSubject {
    const char *relative_path;
    ULONGLONG bytes;
    const char *sha256;
    const char *label;
} StaticSubject;

static const StaticSubject V17_STATIC_SUBJECTS[] = {
    {"tools/native/kira_blackwell_voice_control_anchor_v17.c", V17_S00_BYTES, V17_S00_SHA256, "sealed subject 00"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v17/candidate_config.json", V17_S01_BYTES, V17_S01_SHA256, "sealed subject 01"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v17/native_control_contract.json", V17_S02_BYTES, V17_S02_SHA256, "sealed subject 02"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v17/README.md", V17_S03_BYTES, V17_S03_SHA256, "sealed subject 03"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v16/candidate_config.json", V17_S04_BYTES, V17_S04_SHA256, "sealed subject 04"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v16/native_control_contract.json", V17_S05_BYTES, V17_S05_SHA256, "sealed subject 05"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v16/README.md", V17_S06_BYTES, V17_S06_SHA256, "sealed subject 06"},
    {"tools/native/kira_blackwell_voice_control_anchor_v16.c", V17_S07_BYTES, V17_S07_SHA256, "sealed subject 07"},
    {"Testing/test_blackwell_persistent_voice_candidate_v16_native_anchor_static.ps1", V17_S08_BYTES, V17_S08_SHA256, "sealed subject 08"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md", V17_S09_BYTES, V17_S09_SHA256, "sealed subject 09"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_static_preparation/attempt_01/AUTHOR_PACKAGE.json", V17_S10_BYTES, V17_S10_SHA256, "sealed subject 10"},
    {"tools/native/kira_blackwell_voice_control_anchor_v16_identity_anchor.h", V17_S11_BYTES, V17_S11_SHA256, "sealed subject 11"},
    {"tools/native/kira_blackwell_voice_control_anchor_v16.obj", V17_S12_BYTES, V17_S12_SHA256, "sealed subject 12"},
    {"tools/native/kira_blackwell_voice_control_anchor_v16.exe", V17_S13_BYTES, V17_S13_SHA256, "sealed subject 13"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt", V17_S14_BYTES, V17_S14_SHA256, "sealed subject 14"},
    {"Core/persistent_blackwell_voice_integration_v15.py", V17_S15_BYTES, V17_S15_SHA256, "sealed subject 15"},
    {"tools/native/kira_blackwell_voice_control_anchor_v15_validator.py", V17_S16_BYTES, V17_S16_SHA256, "sealed subject 16"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/candidate_config.json", V17_S17_BYTES, V17_S17_SHA256, "sealed subject 17"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/native_control_contract.json", V17_S18_BYTES, V17_S18_SHA256, "sealed subject 18"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/README.md", V17_S19_BYTES, V17_S19_SHA256, "sealed subject 19"},
    {"tools/native/kira_blackwell_voice_control_anchor_v15.c", V17_S20_BYTES, V17_S20_SHA256, "sealed subject 20"},
    {"Testing/test_blackwell_persistent_voice_candidate_v15_native_anchor_static.ps1", V17_S21_BYTES, V17_S21_SHA256, "sealed subject 21"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md", V17_S22_BYTES, V17_S22_SHA256, "sealed subject 22"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/AUTHOR_PACKAGE.json", V17_S23_BYTES, V17_S23_SHA256, "sealed subject 23"},
    {"tools/native/kira_blackwell_voice_control_anchor_v15_identity_anchor.h", V17_S24_BYTES, V17_S24_SHA256, "sealed subject 24"},
    {"tools/native/kira_blackwell_voice_control_anchor_v15.obj", V17_S25_BYTES, V17_S25_SHA256, "sealed subject 25"},
    {"tools/native/kira_blackwell_voice_control_anchor_v15.exe", V17_S26_BYTES, V17_S26_SHA256, "sealed subject 26"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt", V17_S27_BYTES, V17_S27_SHA256, "sealed subject 27"},
    {"Core/persistent_blackwell_voice_integration_v14.py", V17_S28_BYTES, V17_S28_SHA256, "sealed subject 28"},
    {"Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/candidate_config.json", V17_S29_BYTES, V17_S29_SHA256, "sealed subject 29"},
    {"RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/CHECKPOINT.md", V17_S30_BYTES, V17_S30_SHA256, "sealed subject 30"},
    {"RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json", V17_S31_BYTES, V17_S31_SHA256, "sealed subject 31"},
    {"RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_fresh_static_audit/attempt_01/AUDIT_DECISION.json", V17_S32_BYTES, V17_S32_SHA256, "sealed subject 32"},
    {"RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_fresh_static_audit/attempt_01/CHECKPOINT.md", V17_S33_BYTES, V17_S33_SHA256, "sealed subject 33"},
    {"C:/Python314/python314.dll", V17_S34_BYTES, V17_S34_SHA256, "sealed subject 34"},
    {"tools/native/runtime/python314_stdlib_v3r4.zip", V17_S35_BYTES, V17_S35_SHA256, "sealed subject 35"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json", V17_S36_BYTES, V17_S36_SHA256, "sealed subject 36"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/CHECKPOINT.md", V17_S37_BYTES, V17_S37_SHA256, "sealed subject 37"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv", V17_S38_BYTES, V17_S38_SHA256, "sealed subject 38"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.sha256", V17_S39_BYTES, V17_S39_SHA256, "sealed subject 39"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_fresh_static_audit/attempt_01/AUDIT_DECISION.json", V17_S40_BYTES, V17_S40_SHA256, "sealed subject 40"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_fresh_static_audit/attempt_01/CHECKPOINT.md", V17_S41_BYTES, V17_S41_SHA256, "sealed subject 41"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_fresh_static_audit/attempt_01/REVIEW_PROBES.md", V17_S42_BYTES, V17_S42_SHA256, "sealed subject 42"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_consumed_failure_diagnostic/attempt_01/READ_ONLY_DIAGNOSIS.json", V17_S43_BYTES, V17_S43_SHA256, "sealed subject 43"},
    {"RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_consumed_failure_diagnostic/attempt_01/CHECKPOINT.md", V17_S44_BYTES, V17_S44_SHA256, "sealed subject 44"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json", V17_S45_BYTES, V17_S45_SHA256, "sealed subject 45"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/AUDIT_DECISION.json", V17_S46_BYTES, V17_S46_SHA256, "sealed subject 46"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/CHECKPOINT.md", V17_S47_BYTES, V17_S47_SHA256, "sealed subject 47"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/PARSER_PROBE_RESULTS.txt", V17_S48_BYTES, V17_S48_SHA256, "sealed subject 48"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/REVIEW_PROBES.md", V17_S49_BYTES, V17_S49_SHA256, "sealed subject 49"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv", V17_S50_BYTES, V17_S50_SHA256, "sealed subject 50"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.sha256", V17_S51_BYTES, V17_S51_SHA256, "sealed subject 51"},
    {"RecoverySprint/continuation_20260811/blackwell_v16_native_exact_manifest_row_control_anchor_fresh_static_audit/attempt_01/CLOSURE_REHASH.tsv", V17_S52_BYTES, V17_S52_SHA256, "sealed subject 52"}
};

static int absolute_binding_path(const char *relative_path, wchar_t *output,
    size_t output_count) {
    size_t out_index = 0U;
    size_t input_index = 0U;
    const int absolute_python = relative_path != NULL &&
        strcmp(relative_path, "C:/Python314/python314.dll") == 0;
    if (relative_path == NULL || output == NULL || output_count == 0U ||
        !canonical_manifest_path(relative_path)) return 0;
    if (!absolute_python) {
        const size_t root_length = wcslen(PROJECT_ROOT);
        if (root_length + 2U >= output_count) return 0;
        memcpy(output, PROJECT_ROOT, root_length * sizeof(wchar_t));
        out_index = root_length;
        output[out_index++] = L'\\';
    }
    while (relative_path[input_index] != '\0') {
        const unsigned char c = (unsigned char)relative_path[input_index++];
        if (out_index + 1U >= output_count) return 0;
        output[out_index++] = (c == (unsigned char)'/') ? L'\\' : (wchar_t)c;
    }
    output[out_index] = L'\0';
    return 1;
}

int wmain(int argc, wchar_t **argv) {
    AuditValues audit;
    HANDLE audit_handle = INVALID_HANDLE_VALUE;
    HANDLE audit_digest_handle = INVALID_HANDLE_VALUE;
    FILE_ID_INFO audit_identity;
    FILE_ID_INFO audit_digest_identity;
    LockedFile closure[_countof(V17_STATIC_SUBJECTS)];
    wchar_t (*closure_paths)[2048] = NULL;
    Binding expected[V17_SEALED_SUBJECT_COUNT];
    LockedFile self;
    LockedFile header;
    LockedFile seal;
    unsigned char *seal_bytes = NULL;
    size_t seal_length = 0U;
    HANDLE evidence = INVALID_HANDLE_VALUE;
    HANDLE receipt = INVALID_HANDLE_VALUE;
    ReservationRecord reservation;
    FILE_ID_INFO receipt_identity;
    FILE_ID_INFO evidence_identity;
    UnloadTelemetry unload;
    uint32_t stage = 0U;
    int reserved = 0;
    int success = 0;
    size_t index;
    (void)argv;
    SecureZeroMemory(&audit, sizeof(audit));
    SecureZeroMemory(&audit_identity, sizeof(audit_identity));
    SecureZeroMemory(&audit_digest_identity, sizeof(audit_digest_identity));
    SecureZeroMemory(closure, sizeof(closure));
    SecureZeroMemory(expected, sizeof(expected));
    SecureZeroMemory(&self, sizeof(self)); self.handle = INVALID_HANDLE_VALUE;
    SecureZeroMemory(&header, sizeof(header)); header.handle = INVALID_HANDLE_VALUE;
    SecureZeroMemory(&seal, sizeof(seal)); seal.handle = INVALID_HANDLE_VALUE;
    SecureZeroMemory(&reservation, sizeof(reservation));
    SecureZeroMemory(&receipt_identity, sizeof(receipt_identity));
    SecureZeroMemory(&evidence_identity, sizeof(evidence_identity));
    SecureZeroMemory(&unload, sizeof(unload));
    for (index = 0U; index < _countof(closure); ++index)
        closure[index].handle = INVALID_HANDLE_VALUE;
    if (argc != 1) goto cleanup;
    closure_paths = (wchar_t (*)[2048])HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        _countof(V17_STATIC_SUBJECTS) * 2048U * sizeof(wchar_t));
    if (closure_paths == NULL) goto cleanup;
    stage = 10U;
    if (!verify_audit(&audit, &audit_handle, &audit_identity,
            &audit_digest_handle, &audit_digest_identity)) goto cleanup;
    self.binding.path = SELF_PATH;
    self.binding.relative_path = "tools/native/kira_blackwell_voice_control_anchor_v17.exe";
    self.binding.bytes = audit.self_bytes;
    self.binding.sha256 = audit.self_sha256;
    self.binding.label = "running native image";
    header.binding.path = HEADER_PATH;
    header.binding.relative_path = "tools/native/kira_blackwell_voice_control_anchor_v17_identity_anchor.h";
    header.binding.bytes = audit.header_bytes;
    header.binding.sha256 = audit.header_sha256;
    header.binding.label = "identity anchor header";
    seal.binding.path = SEAL_PATH;
    seal.binding.relative_path = "RecoverySprint/continuation_20260811/blackwell_v17_native_whole_document_manifest_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json";
    seal.binding.bytes = audit.seal_bytes;
    seal.binding.sha256 = audit.seal_sha256;
    seal.binding.label = "complete V17 whole-document static seal";
    if (!lock_file(&self) || !lock_file(&header) || !lock_file(&seal)) goto cleanup;
    for (index = 0U; index < _countof(closure); ++index) {
        if (!absolute_binding_path(V17_STATIC_SUBJECTS[index].relative_path,
                closure_paths[index], _countof(closure_paths[index]))) goto cleanup;
        closure[index].binding.path = closure_paths[index];
        closure[index].binding.relative_path = V17_STATIC_SUBJECTS[index].relative_path;
        closure[index].binding.bytes = V17_STATIC_SUBJECTS[index].bytes;
        closure[index].binding.sha256 = V17_STATIC_SUBJECTS[index].sha256;
        closure[index].binding.label = V17_STATIC_SUBJECTS[index].label;
        if (!lock_file(&closure[index])) goto cleanup;
    }
    expected[0] = closure[0].binding;
    expected[1] = header.binding;
    expected[2] = self.binding;
    for (index = 1U; index < _countof(closure); ++index)
        expected[index + 2U] = closure[index].binding;
    if (!read_locked(&seal, SEAL_LIMIT, &seal_bytes, &seal_length) ||
        !seal_contract_exact(seal_bytes, seal_length, expected, _countof(expected))) goto cleanup;
    SecureZeroMemory(seal_bytes, seal_length + 1U);
    HeapFree(GetProcessHeap(), 0U, seal_bytes);
    seal_bytes = NULL;
    if (!verify_audit_handles(&audit, audit_handle, &audit_identity,
            audit_digest_handle, &audit_digest_identity) ||
        !recheck_locked_set(closure, _countof(closure)) ||
        !verify_handle_bound(self.handle, &self.binding, &self.identity) ||
        !verify_handle_bound(header.handle, &header.binding, &header.identity) ||
        !verify_handle_bound(seal.handle, &seal.binding, &seal.identity) ||
        !verify_output_parent()) goto cleanup;
    stage = 20U;
    evidence = CreateFileW(EVIDENCE_PATH, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,
        NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
    if (!valid_handle(evidence) || !append_line(evidence, E_ENTRY) ||
        !append_line(evidence, E_GATE)) goto cleanup;
    receipt = CreateFileW(OUTCOME_PATH, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,
        NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
    if (!valid_handle(receipt) ||
        !reserve_outcome(receipt, evidence, &self, &seal, &closure[0], &closure[15],
            &closure[32], &audit, &reservation, &receipt_identity,
            &evidence_identity)) goto cleanup;
    reserved = 1;
    if (!run_python_validation(&closure[34], &closure[35], &closure[16], &closure[15],
            &closure[17], &closure[28], &stage, &unload) ||
        !append_line(evidence, E_PYTHON)) goto cleanup;
    if (!verify_audit_handles(&audit, audit_handle, &audit_identity,
            audit_digest_handle, &audit_digest_identity) ||
        !recheck_locked_set(closure, _countof(closure)) ||
        !verify_handle_bound(self.handle, &self.binding, &self.identity) ||
        !verify_handle_bound(header.handle, &header.binding, &header.identity) ||
        !verify_handle_bound(seal.handle, &seal.binding, &seal.identity) ||
        unload.finalize_called != 1U || unload.finalize_result != 0U ||
        unload.free_library_succeeded != 1U || unload.old_module_absent != 1U ||
        unload.exact_path_absent != 1U || unload.modules_enumerated == 0U ||
        !append_line(evidence, E_FINALIZED)) goto cleanup;
    stage = 70U;
    if (!finish_outcome(receipt, evidence, &receipt_identity, &evidence_identity,
            &reservation, RECORD_SUCCESS, stage, &unload)) goto cleanup;
    success = 1;
cleanup:
    if (!success && reserved) {
        (void)finish_outcome(receipt, evidence, &receipt_identity, &evidence_identity,
            &reservation, RECORD_FAILURE, stage, &unload);
    }
    if (seal_bytes != NULL) {
        SecureZeroMemory(seal_bytes, seal_length + 1U);
        HeapFree(GetProcessHeap(), 0U, seal_bytes);
    }
    if (valid_handle(receipt)) CloseHandle(receipt);
    if (valid_handle(evidence)) CloseHandle(evidence);
    for (index = 0U; index < _countof(closure); ++index) {
        if (valid_handle(closure[index].handle)) CloseHandle(closure[index].handle);
    }
    if (valid_handle(seal.handle)) CloseHandle(seal.handle);
    if (valid_handle(header.handle)) CloseHandle(header.handle);
    if (valid_handle(self.handle)) CloseHandle(self.handle);
    if (valid_handle(audit_digest_handle)) CloseHandle(audit_digest_handle);
    if (valid_handle(audit_handle)) CloseHandle(audit_handle);
    if (closure_paths != NULL) {
        SecureZeroMemory(closure_paths,
            _countof(V17_STATIC_SUBJECTS) * 2048U * sizeof(wchar_t));
        HeapFree(GetProcessHeap(), 0U, closure_paths);
    }
    SecureZeroMemory(&reservation, sizeof(reservation));
    SecureZeroMemory(&audit, sizeof(audit));
    return success ? 0 : 4;
}
