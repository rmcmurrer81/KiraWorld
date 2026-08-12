/*
 * Kira R25 AFES v3r20 retained-Python/controller validation diagnostic.
 *
 * Static authoring only.  This program is sealed inert until a different
 * exact-byte auditor creates its fixed audit.  One later no-argument run may
 * reserve append-only evidence, bind the exact V3r15 contract through the
 * V3r17-proven granular same-handle gate, lock the exact retained runtime
 * subjects, load the exact Python DLL, initialize isolated Python, evaluate only the
 * retained controller's inert definitions, validate its five exports and an
 * exact execution-contract projection, finalize/unload, commit one terminal
 * record, and stop.  It has no process, AFES, Blender, Blend, or body path.
 */

#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#define Py_NO_LINK_LIB 1
#include <Python.h>

#include "kira_r25_afes_python_controller_validation_v3r20_identity_anchor.h"

#pragma comment(lib, "bcrypt.lib")

#define SHA_BYTES 32U
#define SHA_HEX 64U
#define HASH_CHUNK 65536U
#define AUDIT_LIMIT 32768U
#define MANIFEST_LIMIT 65536U
#define CONTROLLER_LIMIT 131072U
#define CONTRACT_LIMIT 262144U
#define RECORD_PENDING 1U
#define RECORD_SUCCESS 2U
#define RECORD_FAILURE 3U
#define CONTRACT_GATE_COUNT 15U

static const wchar_t PROJECT_ROOT[] = L"C:\\Users\\robmc\\Kira";
static const wchar_t SELF_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r20.exe";
static const wchar_t ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r20_identity_anchor.h";
static const wchar_t CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r20.json";
static const wchar_t TARGET_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r15.json";
static const wchar_t SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r20.c";
static const wchar_t TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_python_controller_validation_v3r20_static.ps1";
static const wchar_t CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R14_EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t V3R14_RECEIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_native_outcome_reservation_v3r14_static_preparation\\attempt_01\\NATIVE_DIAGNOSTIC_OUTCOME.receipt.bin";
static const wchar_t V3R14_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r14_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R14_POSTMORTEM_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r14_consumed_success_postmortem\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R17_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R17_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R17_RUN_EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t V3R17_RECEIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_static_preparation\\attempt_01\\CONTRACT_LOCK_DIAGNOSTIC_OUTCOME.receipt.bin";
static const wchar_t V3R17_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R17_RUN_OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit\\attempt_01\\RUN_OUTCOME.json";
static const wchar_t V3R17_POST_RUN_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit\\attempt_01\\POST_RUN_CHECKPOINT.md";
static const wchar_t V3R18_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r18.json";
static const wchar_t V3R18_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r18.c";
static const wchar_t V3R18_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r18_identity_anchor.h";
static const wchar_t V3R18_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r18.obj";
static const wchar_t V3R18_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r18.exe";
static const wchar_t V3R18_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_python_controller_validation_v3r18_static.ps1";
static const wchar_t V3R18_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R18_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R18_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R18_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R18_REJECTION_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R18_REJECTION_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R18_REJECTION_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit\\attempt_01\\HOSTILE_STATIC_PROBES.txt";
static const wchar_t V3R18_REJECTION_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R19_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r19.json";
static const wchar_t V3R19_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r19.c";
static const wchar_t V3R19_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r19_identity_anchor.h";
static const wchar_t V3R19_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r19.obj";
static const wchar_t V3R19_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r19.exe";
static const wchar_t V3R19_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_python_controller_validation_v3r19_static.ps1";
static const wchar_t V3R19_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R19_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R19_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R19_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R19_ACCEPT_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R19_ACCEPT_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R19_ACCEPT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R19_FAILURE_RECHECK_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_consumed_failure_postmortem\\attempt_01\\READ_ONLY_RECHECK.json";
static const wchar_t V3R19_FAILURE_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r19_consumed_failure_postmortem\\attempt_01\\CHECKPOINT.md";
static const wchar_t MANIFEST_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9\\RETAINED_NATIVE_LOCK_MANIFEST.tsv";
static const wchar_t PYTHON_DLL_PATH[] = L"C:\\Python314\\python314.dll";
static const wchar_t STDLIB_ZIP_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\runtime\\python314_stdlib_v3r4.zip";
static const wchar_t CONTROLLER_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\run_kira_r25_foundation_afes_locked_pair_v3r9.py";
static const wchar_t EXECUTION_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_locked_pair_execution_v3r9.json";
static const wchar_t AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t AUDIT_DIGEST_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t OUTPUT_PARENT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01";
static const wchar_t EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01\\PYTHON_CONTROLLER_VALIDATION_OUTCOME.receipt.bin";

static const char AUDIT_MAGIC[] = "KIRA_R25_AFES_PYTHON_CONTROLLER_VALIDATION_AUDIT_V3R20\t1";
static const char AUDIT_DECISION[] = "ACCEPTED_FOR_ONE_BOUNDED_GRANULAR_CONTRACT_AND_PYTHON_CONTROLLER_VALIDATION_V3R20_ONLY";
static const char E_ENTRY[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"entry\",\"status\":\"entered\"}\n";
static const char E_GATE[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"subject_manifest_audit_gate\",\"status\":\"passed\"}\n";
static const char E_RESERVED[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"outcome_reservation\",\"status\":\"passed\"}\n";
static const char E_PYTHON[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"isolated_python_runtime\",\"status\":\"passed\"}\n";
static const char E_CONTROLLER[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"controller_exports_and_contract_projection\",\"status\":\"passed\"}\n";
static const char E_FINALIZED[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"python_finalize_dll_unload_retained_recheck\",\"status\":\"passed\"}\n";
static const char E_SUCCESS[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"terminal\",\"status\":\"complete\",\"detail\":\"no_bootstrap_plan_builder_afes_blender_body\"}\n";
static const char E_FAILURE[] = "{\"schema\":\"kira.r25.afes.v3r20.native_stage.v1\",\"stage\":\"terminal\",\"status\":\"failed_consumed_no_retry\"}\n";

typedef struct Binding {
    const wchar_t *path;
    ULONGLONG bytes;
    const char *sha256;
    const char *label;
} Binding;

typedef struct LockedFile {
    const wchar_t *path;
    ULONGLONG expected_bytes;
    const char *expected_sha256;
    HANDLE handle;
    FILE_ID_INFO identity;
} LockedFile;

typedef struct ContractTelemetry {
    uint32_t passed_mask;
    uint32_t failure_gate;
    uint32_t win32_error;
    uint32_t desired_access;
    uint32_t share_mode;
    uint32_t open_disposition;
    uint32_t open_flags;
    uint64_t snapshot_one_bytes;
    uint64_t snapshot_two_bytes;
    uint64_t final_bytes;
    uint64_t volume_serial;
    unsigned char file_id[16];
    unsigned char snapshot_one_sha256[SHA_BYTES];
    unsigned char snapshot_two_sha256[SHA_BYTES];
    unsigned char final_sha256[SHA_BYTES];
} ContractTelemetry;

typedef struct UnloadTelemetry {
    uint32_t finalize_called;
    int32_t finalize_result;
    uint32_t free_library_called;
    uint32_t free_library_result;
    uint32_t snapshot_succeeded;
    uint32_t snapshot_error;
    uint32_t checked_module_count;
    uint32_t old_base_present;
    uint32_t exact_path_present;
    uint64_t old_module_base;
} UnloadTelemetry;

#pragma pack(push, 1)
typedef struct ReservationRecord {
    unsigned char magic[48];
    uint32_t version;
    uint32_t type;
    uint32_t bytes;
    uint32_t state;
    unsigned char executable_sha256[SHA_BYTES];
    unsigned char audit_sha256[SHA_BYTES];
    unsigned char v3r14_receipt_sha256[SHA_BYTES];
    unsigned char manifest_sha256[SHA_BYTES];
    unsigned char python_dll_sha256[SHA_BYTES];
    unsigned char controller_sha256[SHA_BYTES];
    unsigned char execution_contract_sha256[SHA_BYTES];
    unsigned char authority_contract_sha256[SHA_BYTES];
    uint64_t authority_contract_volume;
    unsigned char authority_contract_id[16];
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
    uint32_t reserved;
    unsigned char reservation_sha256[SHA_BYTES];
    unsigned char executable_sha256[SHA_BYTES];
    unsigned char audit_sha256[SHA_BYTES];
    unsigned char manifest_sha256[SHA_BYTES];
    unsigned char controller_sha256[SHA_BYTES];
    unsigned char execution_contract_sha256[SHA_BYTES];
    unsigned char authority_contract_sha256[SHA_BYTES];
    uint64_t authority_contract_volume;
    unsigned char authority_contract_id[16];
    uint64_t receipt_volume;
    unsigned char receipt_id[16];
    uint64_t evidence_volume;
    unsigned char evidence_id[16];
    ContractTelemetry contract;
    UnloadTelemetry unload;
} CompletionRecord;
#pragma pack(pop)

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
    PyObject *(__cdecl *run_string)(const char *, int, PyObject *, PyObject *, PyCompilerFlags *);
    PyObject *(__cdecl *dict_new)(void);
    int (__cdecl *dict_set)(PyObject *, const char *, PyObject *);
    PyObject *(__cdecl *dict_get)(PyObject *, const char *);
    PyObject *(__cdecl *get_builtins)(void);
    PyObject *(__cdecl *unicode_from_string)(const char *);
    const char *(__cdecl *unicode_utf8)(PyObject *, Py_ssize_t *);
    PyObject *(__cdecl *bytes_from_data)(const char *, Py_ssize_t);
    Py_ssize_t (__cdecl *tuple_size)(PyObject *);
    PyObject *(__cdecl *tuple_get)(PyObject *, Py_ssize_t);
    int (__cdecl *callable)(PyObject *);
    void (__cdecl *decref)(PyObject *);
    PyObject *(__cdecl *error_occurred)(void);
    void (__cdecl *error_clear)(void);
} PythonApi;

static int lower_hex_exact(const char *value, size_t length) {
    size_t index;
    if (value == NULL || length != SHA_HEX) return 0;
    for (index = 0U; index < SHA_HEX; ++index) {
        char c = value[index];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    }
    return 1;
}

static int auditor_exact(const char *value, size_t length) {
    size_t index;
    if (value == NULL || length == 0U || length > 96U) return 0;
    for (index = 0U; index < length; ++index) {
        char c = value[index];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) return 0;
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

static int sha_memory(const unsigned char *data, size_t length, unsigned char digest[SHA_BYTES]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char *object = NULL;
    DWORD object_bytes = 0U;
    DWORD returned = 0U;
    NTSTATUS status;
    int ok = 0;
    if (data == NULL || length > (size_t)ULONG_MAX) return 0;
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

static int regular_file(HANDLE file, ULONGLONG *bytes) {
    FILE_ATTRIBUTE_TAG_INFO attributes;
    FILE_STANDARD_INFO standard;
    if (!GetFileInformationByHandleEx(file, FileAttributeTagInfo, &attributes,
            (DWORD)sizeof(attributes)) ||
        (attributes.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0U ||
        !GetFileInformationByHandleEx(file, FileStandardInfo, &standard,
            (DWORD)sizeof(standard)) || standard.EndOfFile.QuadPart < 0) return 0;
    *bytes = (ULONGLONG)standard.EndOfFile.QuadPart;
    return 1;
}

static int seek_start(HANDLE file) {
    LARGE_INTEGER zero;
    zero.QuadPart = 0;
    return SetFilePointerEx(file, zero, NULL, FILE_BEGIN) != FALSE;
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
    if (!seek_start(file)) return 0;
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
        DWORD read_bytes = 0U;
        if (!ReadFile(file, buffer, HASH_CHUNK, &read_bytes, NULL)) goto cleanup;
        if (read_bytes == 0U) break;
        status = BCryptHashData(hash, buffer, read_bytes, 0U);
        if (status < 0) goto cleanup;
    }
    status = BCryptFinishHash(hash, digest, SHA_BYTES, 0U);
    if (status < 0) goto cleanup;
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
    wchar_t actual[32768];
    wchar_t expected[32768];
    DWORD length;
    size_t path_length = wcslen(path);
    if (path_length + 5U > _countof(expected)) return 0;
    memcpy(expected, L"\\\\?\\", 4U * sizeof(wchar_t));
    memcpy(expected + 4U, path, (path_length + 1U) * sizeof(wchar_t));
    length = GetFinalPathNameByHandleW(file, actual, (DWORD)_countof(actual),
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    return length != 0U && length < (DWORD)_countof(actual) && _wcsicmp(actual, expected) == 0;
}

static int same_identity(const FILE_ID_INFO *left, const FILE_ID_INFO *right) {
    return left->VolumeSerialNumber == right->VolumeSerialNumber &&
        memcmp(left->FileId.Identifier, right->FileId.Identifier, 16U) == 0;
}

static int verify_handle_capture(HANDLE file, const wchar_t *path, ULONGLONG bytes,
    const char *expected_sha, FILE_ID_INFO *observed_identity) {
    ULONGLONG actual_bytes = 0ULL;
    unsigned char digest[SHA_BYTES];
    char hex[SHA_HEX + 1U];
    FILE_ID_INFO current;
    int ok;
    SecureZeroMemory(&current, sizeof(current));
    ok = regular_file(file, &actual_bytes) && actual_bytes == bytes && exact_final_path(file, path) &&
        GetFileInformationByHandleEx(file, FileIdInfo, &current, (DWORD)sizeof(current)) &&
        hash_handle(file, digest);
    if (ok) {
        digest_hex(digest, hex);
        ok = strcmp(hex, expected_sha) == 0;
    }
    if (ok && observed_identity != NULL) *observed_identity = current;
    SecureZeroMemory(digest, sizeof(digest));
    return ok;
}

static int verify_handle_bound(HANDLE file, const wchar_t *path, ULONGLONG bytes,
    const char *expected_sha, const FILE_ID_INFO *expected_identity) {
    FILE_ID_INFO observed_identity;
    int ok;
    if (expected_identity == NULL) return 0;
    SecureZeroMemory(&observed_identity, sizeof(observed_identity));
    ok = verify_handle_capture(file, path, bytes, expected_sha, &observed_identity) &&
        same_identity(expected_identity, &observed_identity);
    SecureZeroMemory(&observed_identity, sizeof(observed_identity));
    return ok;
}

static int hash_path_exact(const wchar_t *path, ULONGLONG bytes, const char *sha,
    unsigned char *digest_output) {
    HANDLE file;
    FILE_ID_INFO identity;
    unsigned char digest[SHA_BYTES];
    int ok;
    if (!lower_hex_exact(sha, strlen(sha))) return 0;
    SecureZeroMemory(&identity, sizeof(identity));
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    ok = verify_handle_capture(file, path, bytes, sha, &identity) && hash_handle(file, digest);
    if (ok && digest_output != NULL) memcpy(digest_output, digest, SHA_BYTES);
    SecureZeroMemory(digest, sizeof(digest));
    CloseHandle(file);
    return ok;
}

static int hash_path_unbound(const wchar_t *path, ULONGLONG maximum,
    ULONGLONG *bytes_output, unsigned char digest[SHA_BYTES]) {
    HANDLE file;
    ULONGLONG bytes = 0ULL;
    int ok;
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    ok = regular_file(file, &bytes) && bytes > 0ULL && bytes <= maximum &&
        exact_final_path(file, path) && hash_handle(file, digest);
    CloseHandle(file);
    if (ok) *bytes_output = bytes;
    return ok;
}

static int append_line(HANDLE file, const char *line);

static void contract_pass(ContractTelemetry *telemetry, uint32_t gate) {
    if (gate > 0U && gate < 32U) telemetry->passed_mask |= (1U << (gate - 1U));
}

static int contract_fail(ContractTelemetry *telemetry, uint32_t gate, DWORD error) {
    telemetry->failure_gate = gate;
    telemetry->win32_error = error == ERROR_SUCCESS ? ERROR_INVALID_DATA : error;
    return 0;
}

static int open_contract_granular(ContractTelemetry *telemetry, HANDLE *handle_output,
    FILE_ID_INFO *identity_output) {
    HANDLE file = INVALID_HANDLE_VALUE;
    FILE_BASIC_INFO basic;
    FILE_ID_INFO second_identity;
    ULONGLONG bytes = 0ULL;
    SecureZeroMemory(telemetry, sizeof(*telemetry));
    SecureZeroMemory(identity_output, sizeof(*identity_output));
    SecureZeroMemory(&basic, sizeof(basic));
    SecureZeroMemory(&second_identity, sizeof(second_identity));
    *handle_output = INVALID_HANDLE_VALUE;
    telemetry->desired_access = GENERIC_READ;
    telemetry->share_mode = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE;
    telemetry->open_disposition = OPEN_EXISTING;
    telemetry->open_flags = FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN |
        FILE_FLAG_OPEN_REPARSE_POINT;
    SetLastError(ERROR_SUCCESS);
    file = CreateFileW(TARGET_CONTRACT_PATH, telemetry->desired_access, telemetry->share_mode,
        NULL, telemetry->open_disposition, telemetry->open_flags, NULL);
    if (file == INVALID_HANDLE_VALUE) return contract_fail(telemetry, 1U, GetLastError());
    contract_pass(telemetry, 1U);
    if (!GetFileInformationByHandleEx(file, FileBasicInfo, &basic, (DWORD)sizeof(basic)) ||
        (basic.FileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_DEVICE |
        FILE_ATTRIBUTE_REPARSE_POINT)) != 0U) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 2U, error);
    }
    contract_pass(telemetry, 2U);
    if (!regular_file(file, &bytes) || bytes != V3R20_TARGET_CONTRACT_BYTES) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 3U, error);
    }
    telemetry->snapshot_one_bytes = bytes;
    contract_pass(telemetry, 3U);
    if (!exact_final_path(file, TARGET_CONTRACT_PATH)) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 4U, error);
    }
    contract_pass(telemetry, 4U);
    if (!GetFileInformationByHandleEx(file, FileIdInfo, identity_output,
            (DWORD)sizeof(*identity_output))) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 5U, error);
    }
    telemetry->volume_serial = identity_output->VolumeSerialNumber;
    memcpy(telemetry->file_id, identity_output->FileId.Identifier, 16U);
    contract_pass(telemetry, 5U);
    if (!hash_handle(file, telemetry->snapshot_one_sha256)) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 6U, error);
    }
    contract_pass(telemetry, 6U);
    if (!regular_file(file, &bytes) || bytes != V3R20_TARGET_CONTRACT_BYTES ||
        bytes != telemetry->snapshot_one_bytes) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 7U, error);
    }
    telemetry->snapshot_two_bytes = bytes;
    contract_pass(telemetry, 7U);
    if (!exact_final_path(file, TARGET_CONTRACT_PATH)) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 8U, error);
    }
    contract_pass(telemetry, 8U);
    if (!GetFileInformationByHandleEx(file, FileIdInfo, &second_identity,
            (DWORD)sizeof(second_identity)) || !same_identity(identity_output, &second_identity)) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 9U, error);
    }
    contract_pass(telemetry, 9U);
    if (!hash_handle(file, telemetry->snapshot_two_sha256)) {
        DWORD error = GetLastError(); CloseHandle(file);
        return contract_fail(telemetry, 10U, error);
    }
    contract_pass(telemetry, 10U);
    *handle_output = file;
    return 1;
}

static int finish_contract_granular(ContractTelemetry *telemetry, HANDLE *handle,
    const FILE_ID_INFO *identity) {
    FILE_ID_INFO final_identity;
    ULONGLONG bytes = 0ULL;
    char expected[SHA_HEX + 1U];
    int ok = 1;
    SecureZeroMemory(&final_identity, sizeof(final_identity));
    SecureZeroMemory(expected, sizeof(expected));
    if (*handle == INVALID_HANDLE_VALUE) return contract_fail(telemetry, 11U, ERROR_INVALID_HANDLE);
    if (!regular_file(*handle, &bytes) || bytes != V3R20_TARGET_CONTRACT_BYTES ||
        bytes != telemetry->snapshot_two_bytes) ok = contract_fail(telemetry, 11U, GetLastError());
    if (ok) { telemetry->final_bytes = bytes; contract_pass(telemetry, 11U); }
    if (ok && !exact_final_path(*handle, TARGET_CONTRACT_PATH))
        ok = contract_fail(telemetry, 12U, GetLastError());
    if (ok) contract_pass(telemetry, 12U);
    if (ok && (!GetFileInformationByHandleEx(*handle, FileIdInfo, &final_identity,
            (DWORD)sizeof(final_identity)) || !same_identity(identity, &final_identity)))
        ok = contract_fail(telemetry, 13U, GetLastError());
    if (ok) contract_pass(telemetry, 13U);
    if (ok && !hash_handle(*handle, telemetry->final_sha256))
        ok = contract_fail(telemetry, 14U, GetLastError());
    if (ok) contract_pass(telemetry, 14U);
    if (ok) {
        digest_hex(telemetry->final_sha256, expected);
        if (memcmp(telemetry->snapshot_one_sha256, telemetry->snapshot_two_sha256, SHA_BYTES) != 0 ||
            memcmp(telemetry->snapshot_two_sha256, telemetry->final_sha256, SHA_BYTES) != 0 ||
            strcmp(expected, V3R20_TARGET_CONTRACT_SHA256) != 0 ||
            telemetry->passed_mask != ((1U << (CONTRACT_GATE_COUNT - 1U)) - 1U))
            ok = contract_fail(telemetry, 15U, ERROR_INVALID_DATA);
    }
    if (ok) contract_pass(telemetry, CONTRACT_GATE_COUNT);
    if (!CloseHandle(*handle) && ok) ok = contract_fail(telemetry, 15U, GetLastError());
    *handle = INVALID_HANDLE_VALUE;
    if (ok) { telemetry->failure_gate = 0U; telemetry->win32_error = ERROR_SUCCESS; }
    SecureZeroMemory(expected, sizeof(expected));
    return ok;
}

static int append_contract_telemetry(HANDLE evidence, const ContractTelemetry *telemetry) {
    char line[512];
    int bytes = _snprintf_s(line, sizeof(line), _TRUNCATE,
        "{\"schema\":\"kira.r25.afes.v3r20.contract_gate.v1\",\"stage\":\"granular_same_handle_terminal\",\"passed_mask\":%u,\"failure_gate\":%u,\"win32_error\":%u,\"snapshot_one_bytes\":%llu,\"snapshot_two_bytes\":%llu,\"final_bytes\":%llu}\n",
        telemetry->passed_mask, telemetry->failure_gate, telemetry->win32_error,
        (unsigned long long)telemetry->snapshot_one_bytes,
        (unsigned long long)telemetry->snapshot_two_bytes,
        (unsigned long long)telemetry->final_bytes);
    return bytes > 0 && append_line(evidence, line);
}

static int append_unload_telemetry(HANDLE evidence, const UnloadTelemetry *telemetry) {
    char line[640];
    int bytes = _snprintf_s(line, sizeof(line), _TRUNCATE,
        "{\"schema\":\"kira.r25.afes.v3r20.python_unload.v1\",\"stage\":\"finalize_release_absence_terminal\",\"finalize_called\":%u,\"finalize_result\":%d,\"free_library_called\":%u,\"free_library_result\":%u,\"snapshot_succeeded\":%u,\"snapshot_error\":%u,\"checked_module_count\":%u,\"old_base_present\":%u,\"exact_path_present\":%u,\"old_module_base\":%llu}\n",
        telemetry->finalize_called, telemetry->finalize_result,
        telemetry->free_library_called, telemetry->free_library_result,
        telemetry->snapshot_succeeded, telemetry->snapshot_error,
        telemetry->checked_module_count, telemetry->old_base_present,
        telemetry->exact_path_present,
        (unsigned long long)telemetry->old_module_base);
    return bytes > 0 && append_line(evidence, line);
}

static int lock_file(LockedFile *locked) {
    SecureZeroMemory(&locked->identity, sizeof(locked->identity));
    locked->handle = CreateFileW(locked->path, GENERIC_READ, FILE_SHARE_READ, NULL,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (locked->handle == INVALID_HANDLE_VALUE) return 0;
    if (!verify_handle_capture(locked->handle, locked->path, locked->expected_bytes,
            locked->expected_sha256, &locked->identity)) {
        CloseHandle(locked->handle);
        locked->handle = INVALID_HANDLE_VALUE;
        return 0;
    }
    return 1;
}

static int read_locked(LockedFile *locked, ULONGLONG limit, unsigned char **data,
    DWORD *bytes_output) {
    DWORD read_bytes = 0U;
    unsigned char *buffer;
    *data = NULL;
    *bytes_output = 0U;
    if (locked->expected_bytes == 0ULL || locked->expected_bytes > limit ||
        locked->expected_bytes > MAXDWORD || !seek_start(locked->handle)) return 0;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        (SIZE_T)locked->expected_bytes + 1U);
    if (buffer == NULL) return 0;
    if (!ReadFile(locked->handle, buffer, (DWORD)locked->expected_bytes, &read_bytes, NULL) ||
        read_bytes != (DWORD)locked->expected_bytes) {
        SecureZeroMemory(buffer, (SIZE_T)locked->expected_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, buffer);
        return 0;
    }
    buffer[read_bytes] = '\0';
    *data = buffer;
    *bytes_output = read_bytes;
    return 1;
}

static int manifest_exact_row(const unsigned char *manifest, size_t bytes,
    const char *label, const char *path, ULONGLONG expected_bytes, const char *sha) {
    char row[1024];
    int written;
    size_t row_bytes;
    size_t index;
    unsigned count = 0U;
    written = _snprintf_s(row, sizeof(row), _TRUNCATE, "%s\t%s\t%llu\t%s\r\n",
        label, path, expected_bytes, sha);
    if (written <= 0) return 0;
    row_bytes = (size_t)written;
    for (index = 0U; index + row_bytes <= bytes; ++index) {
        if ((index == 0U || manifest[index - 1U] == '\n') &&
            memcmp(manifest + index, row, row_bytes) == 0) ++count;
    }
    return count == 1U;
}

static int append_line(HANDLE file, const char *line) {
    size_t length = strlen(line);
    DWORD written = 0U;
    return length > 0U && length <= MAXDWORD &&
        WriteFile(file, line, (DWORD)length, &written, NULL) &&
        written == (DWORD)length && FlushFileBuffers(file);
}

static int read_exact(HANDLE file, void *buffer, DWORD bytes) {
    DWORD total = 0U;
    while (total < bytes) {
        DWORD got = 0U;
        if (!ReadFile(file, (unsigned char *)buffer + total, bytes - total, &got, NULL) || got == 0U) return 0;
        total += got;
    }
    return 1;
}

static int seek_offset(HANDLE file, LONGLONG offset) {
    LARGE_INTEGER value;
    value.QuadPart = offset;
    return SetFilePointerEx(file, value, NULL, FILE_BEGIN) != FALSE;
}

static int read_dynamic_small(const wchar_t *path, unsigned char **data, DWORD *bytes,
    unsigned char digest[SHA_BYTES]) {
    HANDLE file;
    ULONGLONG size = 0ULL;
    DWORD got = 0U;
    unsigned char *buffer = NULL;
    int ok = 0;
    *data = NULL; *bytes = 0U;
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    if (!regular_file(file, &size) || size == 0ULL || size > AUDIT_LIMIT ||
        !exact_final_path(file, path)) goto cleanup;
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)size + 1U);
    if (buffer == NULL || !ReadFile(file, buffer, (DWORD)size, &got, NULL) ||
        got != (DWORD)size || !sha_memory(buffer, got, digest)) goto cleanup;
    buffer[got] = '\0'; *data = buffer; *bytes = got; buffer = NULL; ok = 1;
cleanup:
    if (buffer != NULL) { SecureZeroMemory(buffer, (SIZE_T)size + 1U); HeapFree(GetProcessHeap(), 0U, buffer); }
    CloseHandle(file);
    return ok;
}

static int consume_line(char **cursor_io, const char *end, const char *key,
    char *value, size_t capacity, size_t *value_length) {
    char *cursor = *cursor_io;
    char *newline;
    char *tab;
    size_t length;
    if (cursor >= end) return 0;
    newline = (char *)memchr(cursor, '\n', (size_t)(end - cursor));
    if (newline == NULL || memchr(cursor, '\0', (size_t)(newline - cursor)) != NULL ||
        memchr(cursor, '\r', (size_t)(newline - cursor)) != NULL) return 0;
    tab = (char *)memchr(cursor, '\t', (size_t)(newline - cursor));
    if (tab == NULL || (size_t)(tab - cursor) != strlen(key) ||
        memcmp(cursor, key, strlen(key)) != 0 ||
        memchr(tab + 1, '\t', (size_t)(newline - tab - 1)) != NULL) return 0;
    length = (size_t)(newline - tab - 1);
    if (length == 0U || length + 1U > capacity) return 0;
    memcpy(value, tab + 1, length); value[length] = '\0';
    *value_length = length; *cursor_io = newline + 1;
    return 1;
}

static int verify_audit(const unsigned char self_sha[SHA_BYTES], unsigned char audit_sha[SHA_BYTES]) {
    static const char *keys[54] = {
        "decision", "auditor", "author", "native_executable_sha256", "identity_anchor_sha256",
        "contract_sha256", "native_source_sha256", "static_test_sha256",
        "runtime_control_checkpoint_sha256", "v3r14_run_evidence_sha256",
        "v3r14_outcome_receipt_sha256", "v3r14_audit_checkpoint_sha256", "v3r14_postmortem_sha256",
        "v3r17_checkpoint_sha256", "v3r17_seal_sha256", "v3r17_run_evidence_sha256",
        "v3r17_outcome_receipt_sha256", "v3r17_audit_checkpoint_sha256",
        "v3r17_run_outcome_sha256", "v3r17_post_run_checkpoint_sha256",
        "retained_manifest_sha256", "python_runtime_dll_sha256", "retained_stdlib_zip_sha256",
        "parent_controller_sha256", "execution_contract_sha256",
        "v3r18_contract_sha256", "v3r18_source_sha256", "v3r18_identity_anchor_sha256",
        "v3r18_object_sha256", "v3r18_executable_sha256", "v3r18_static_test_sha256",
        "v3r18_runtime_control_sha256", "v3r18_build_result_sha256",
        "v3r18_static_seal_sha256", "v3r18_static_checkpoint_sha256",
        "v3r18_rejection_audit_sha256", "v3r18_rejection_sidecar_sha256",
        "v3r18_rejection_probes_sha256", "v3r18_rejection_checkpoint_sha256",
        "v3r19_contract_sha256", "v3r19_source_sha256", "v3r19_identity_anchor_sha256",
        "v3r19_object_sha256", "v3r19_executable_sha256", "v3r19_static_test_sha256",
        "v3r19_runtime_control_sha256", "v3r19_build_result_sha256",
        "v3r19_static_seal_sha256", "v3r19_static_checkpoint_sha256",
        "v3r19_accept_audit_sha256", "v3r19_accept_sidecar_sha256",
        "v3r19_accept_checkpoint_sha256", "v3r19_failure_recheck_sha256",
        "v3r19_failure_checkpoint_sha256"
    };
    const char *expected[54] = {
        AUDIT_DECISION, NULL, V3R20_AUTHOR_ID, NULL, NULL,
        V3R20_CONTRACT_SHA256, V3R20_SOURCE_SHA256, V3R20_TEST_SHA256, V3R20_CONTROL_SHA256,
        V3R20_V3R14_EVIDENCE_SHA256, V3R20_V3R14_RECEIPT_SHA256, V3R20_V3R14_AUDIT_SHA256,
        V3R20_V3R14_POSTMORTEM_SHA256, V3R20_V3R17_CHECKPOINT_SHA256, V3R20_V3R17_SEAL_SHA256,
        V3R20_V3R17_RUN_EVIDENCE_SHA256, V3R20_V3R17_RECEIPT_SHA256,
        V3R20_V3R17_AUDIT_CHECKPOINT_SHA256, V3R20_V3R17_RUN_OUTCOME_SHA256,
        V3R20_V3R17_POST_RUN_SHA256, V3R20_MANIFEST_SHA256, V3R20_PYTHON_DLL_SHA256,
        V3R20_STDLIB_ZIP_SHA256, V3R20_CONTROLLER_SHA256, V3R20_EXECUTION_CONTRACT_SHA256,
        V3R20_V3R18_CONTRACT_SHA256, V3R20_V3R18_SOURCE_SHA256,
        V3R20_V3R18_ANCHOR_SHA256, V3R20_V3R18_OBJECT_SHA256,
        V3R20_V3R18_EXECUTABLE_SHA256, V3R20_V3R18_TEST_SHA256,
        V3R20_V3R18_CONTROL_SHA256, V3R20_V3R18_BUILD_SHA256,
        V3R20_V3R18_SEAL_SHA256, V3R20_V3R18_CHECKPOINT_SHA256,
        V3R20_V3R18_REJECTION_AUDIT_SHA256, V3R20_V3R18_REJECTION_SIDECAR_SHA256,
        V3R20_V3R18_REJECTION_PROBES_SHA256, V3R20_V3R18_REJECTION_CHECKPOINT_SHA256,
        V3R20_V3R19_CONTRACT_SHA256, V3R20_V3R19_SOURCE_SHA256,
        V3R20_V3R19_ANCHOR_SHA256, V3R20_V3R19_OBJECT_SHA256,
        V3R20_V3R19_EXECUTABLE_SHA256, V3R20_V3R19_TEST_SHA256,
        V3R20_V3R19_CONTROL_SHA256, V3R20_V3R19_BUILD_SHA256,
        V3R20_V3R19_SEAL_SHA256, V3R20_V3R19_CHECKPOINT_SHA256,
        V3R20_V3R19_ACCEPT_AUDIT_SHA256, V3R20_V3R19_ACCEPT_SIDECAR_SHA256,
        V3R20_V3R19_ACCEPT_CHECKPOINT_SHA256, V3R20_V3R19_FAILURE_RECHECK_SHA256,
        V3R20_V3R19_FAILURE_CHECKPOINT_SHA256
    };
    char values[54][129];
    size_t value_lengths[54];
    unsigned char *audit = NULL, *sidecar = NULL;
    DWORD audit_bytes = 0U, sidecar_bytes = 0U;
    unsigned char sidecar_digest[SHA_BYTES], anchor_digest[SHA_BYTES];
    ULONGLONG anchor_bytes = 0ULL;
    char audit_hex[SHA_HEX + 1U], self_hex[SHA_HEX + 1U], anchor_hex[SHA_HEX + 1U];
    char *cursor;
    const char *end;
    size_t index;
    int ok = 0;
    if (!read_dynamic_small(AUDIT_PATH, &audit, &audit_bytes, audit_sha) ||
        !read_dynamic_small(AUDIT_DIGEST_PATH, &sidecar, &sidecar_bytes, sidecar_digest) ||
        sidecar_bytes != SHA_HEX + 1U || sidecar[SHA_HEX] != '\n' ||
        memchr(audit, '\0', audit_bytes) != NULL ||
        memchr(sidecar, '\0', sidecar_bytes) != NULL ||
        !lower_hex_exact((const char *)sidecar, SHA_HEX)) goto cleanup;
    digest_hex(audit_sha, audit_hex);
    if (memcmp(sidecar, audit_hex, SHA_HEX) != 0 ||
        !hash_path_unbound(ANCHOR_PATH, 65536ULL, &anchor_bytes, anchor_digest)) goto cleanup;
    digest_hex(self_sha, self_hex); digest_hex(anchor_digest, anchor_hex);
    expected[3] = self_hex; expected[4] = anchor_hex;
    cursor = (char *)audit; end = (const char *)audit + audit_bytes;
    {
        char *newline = (char *)memchr(cursor, '\n', (size_t)(end - cursor));
        if (newline == NULL || (size_t)(newline - cursor) != strlen(AUDIT_MAGIC) ||
            memcmp(cursor, AUDIT_MAGIC, strlen(AUDIT_MAGIC)) != 0) goto cleanup;
        cursor = newline + 1;
    }
    for (index = 0U; index < _countof(keys); ++index)
        if (!consume_line(&cursor, end, keys[index], values[index], sizeof(values[index]),
                &value_lengths[index])) goto cleanup;
    if (cursor != end || value_lengths[0] != strlen(expected[0]) ||
        memcmp(values[0], expected[0], value_lengths[0]) != 0 ||
        !auditor_exact(values[1], value_lengths[1]) ||
        value_lengths[2] != strlen(expected[2]) ||
        memcmp(values[2], expected[2], value_lengths[2]) != 0 ||
        (value_lengths[1] == value_lengths[2] &&
            memcmp(values[1], values[2], value_lengths[1]) == 0)) goto cleanup;
    for (index = 3U; index < _countof(keys); ++index) {
        if (!lower_hex_exact(values[index], value_lengths[index]) ||
            memcmp(values[index], expected[index], SHA_HEX) != 0) goto cleanup;
    }
    ok = 1;
cleanup:
    if (audit != NULL) { SecureZeroMemory(audit, (SIZE_T)audit_bytes + 1U); HeapFree(GetProcessHeap(), 0U, audit); }
    if (sidecar != NULL) { SecureZeroMemory(sidecar, (SIZE_T)sidecar_bytes + 1U); HeapFree(GetProcessHeap(), 0U, sidecar); }
    SecureZeroMemory(sidecar_digest, sizeof(sidecar_digest)); SecureZeroMemory(anchor_digest, sizeof(anchor_digest));
    return ok;
}

static int verify_output_parent(void) {
    HANDLE directory = CreateFileW(OUTPUT_PARENT_PATH, FILE_ADD_FILE | FILE_READ_ATTRIBUTES |
        SYNCHRONIZE, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL,
        OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    FILE_ATTRIBUTE_TAG_INFO attributes;
    int ok = 0;
    if (directory == INVALID_HANDLE_VALUE) return 0;
    if (GetFileInformationByHandleEx(directory, FileAttributeTagInfo, &attributes, (DWORD)sizeof(attributes)) &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0U &&
        (attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0U) ok = 1;
    CloseHandle(directory);
    return ok;
}

static int reserve_outcome(HANDLE evidence, const FILE_ID_INFO *evidence_identity,
    const unsigned char self_sha[SHA_BYTES], const unsigned char audit_sha[SHA_BYTES],
    const LockedFile *authority_contract,
    HANDLE *receipt_output, FILE_ID_INFO *receipt_identity, ReservationRecord *reservation_output) {
    HANDLE receipt = INVALID_HANDLE_VALUE;
    ReservationRecord record, readback;
    DWORD written = 0U;
    ULONGLONG bytes = 0ULL;
    SecureZeroMemory(&record, sizeof(record)); SecureZeroMemory(&readback, sizeof(readback));
    SecureZeroMemory(receipt_identity, sizeof(*receipt_identity));
    receipt = CreateFileW(OUTCOME_PATH, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,
        NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (receipt == INVALID_HANDLE_VALUE || !exact_final_path(receipt, OUTCOME_PATH) ||
        !GetFileInformationByHandleEx(receipt, FileIdInfo, receipt_identity, (DWORD)sizeof(*receipt_identity))) goto fail;
    memcpy(record.magic, "KIRA_R25_AFES_V3R20_RESERVATION", 34U);
    record.version = 1U; record.type = 1U; record.bytes = (uint32_t)sizeof(record); record.state = RECORD_PENDING;
    memcpy(record.executable_sha256, self_sha, SHA_BYTES); memcpy(record.audit_sha256, audit_sha, SHA_BYTES);
    if (!hash_path_exact(V3R14_RECEIPT_PATH, V3R20_V3R14_RECEIPT_BYTES, V3R20_V3R14_RECEIPT_SHA256, record.v3r14_receipt_sha256) ||
        !hash_path_exact(MANIFEST_PATH, V3R20_MANIFEST_BYTES, V3R20_MANIFEST_SHA256, record.manifest_sha256) ||
        !hash_path_exact(PYTHON_DLL_PATH, V3R20_PYTHON_DLL_BYTES, V3R20_PYTHON_DLL_SHA256, record.python_dll_sha256) ||
        !hash_path_exact(CONTROLLER_PATH, V3R20_CONTROLLER_BYTES, V3R20_CONTROLLER_SHA256, record.controller_sha256) ||
        !hash_path_exact(EXECUTION_CONTRACT_PATH, V3R20_EXECUTION_CONTRACT_BYTES, V3R20_EXECUTION_CONTRACT_SHA256, record.execution_contract_sha256) ||
        !verify_handle_bound(authority_contract->handle, authority_contract->path,
            authority_contract->expected_bytes, authority_contract->expected_sha256,
            &authority_contract->identity) ||
        !hash_handle(authority_contract->handle, record.authority_contract_sha256) ||
        BCryptGenRandom(NULL, record.nonce, SHA_BYTES, BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) goto fail;
    record.authority_contract_volume = authority_contract->identity.VolumeSerialNumber;
    memcpy(record.authority_contract_id, authority_contract->identity.FileId.Identifier, 16U);
    record.receipt_volume = receipt_identity->VolumeSerialNumber; memcpy(record.receipt_id, receipt_identity->FileId.Identifier, 16U);
    record.evidence_volume = evidence_identity->VolumeSerialNumber; memcpy(record.evidence_id, evidence_identity->FileId.Identifier, 16U);
    if (!WriteFile(receipt, &record, (DWORD)sizeof(record), &written, NULL) || written != sizeof(record) ||
        !FlushFileBuffers(receipt) || !seek_start(receipt) || !read_exact(receipt, &readback, (DWORD)sizeof(readback)) ||
        memcmp(&record, &readback, sizeof(record)) != 0 || !regular_file(receipt, &bytes) || bytes != sizeof(record)) goto fail;
    *receipt_output = receipt; *reservation_output = record; SecureZeroMemory(&readback, sizeof(readback)); return 1;
fail:
    SecureZeroMemory(&record, sizeof(record)); SecureZeroMemory(&readback, sizeof(readback));
    if (receipt != INVALID_HANDLE_VALUE) CloseHandle(receipt); (void)evidence; return 0;
}

static int finish_outcome(HANDLE receipt, const FILE_ID_INFO *receipt_identity,
    const FILE_ID_INFO *evidence_identity, const ReservationRecord *reservation,
    const unsigned char self_sha[SHA_BYTES], const unsigned char audit_sha[SHA_BYTES],
    const ContractTelemetry *contract, const UnloadTelemetry *unload,
    uint32_t state, uint32_t stage) {
    CompletionRecord record;
    ReservationRecord reservation_readback;
    CompletionRecord completion_readback;
    FILE_ID_INFO identity_after;
    ULONGLONG bytes = 0ULL;
    DWORD written = 0U;
    unsigned char trailing = 0U;
    DWORD trailing_bytes = 0U;
    SecureZeroMemory(&record, sizeof(record));
    SecureZeroMemory(&reservation_readback, sizeof(reservation_readback));
    SecureZeroMemory(&completion_readback, sizeof(completion_readback));
    SecureZeroMemory(&identity_after, sizeof(identity_after));
    memcpy(record.magic, "KIRA_R25_AFES_V3R20_TERMINAL", 31U);
    record.version = 1U;
    record.type = 2U;
    record.bytes = (uint32_t)sizeof(record);
    record.state = state;
    record.terminal_stage = stage;
    if (!sha_memory((const unsigned char *)reservation, sizeof(*reservation),
            record.reservation_sha256)) return 0;
    memcpy(record.executable_sha256, self_sha, SHA_BYTES);
    memcpy(record.audit_sha256, audit_sha, SHA_BYTES);
    memcpy(record.manifest_sha256, reservation->manifest_sha256, SHA_BYTES);
    memcpy(record.controller_sha256, reservation->controller_sha256, SHA_BYTES);
    memcpy(record.execution_contract_sha256, reservation->execution_contract_sha256, SHA_BYTES);
    memcpy(record.authority_contract_sha256, reservation->authority_contract_sha256, SHA_BYTES);
    record.authority_contract_volume = reservation->authority_contract_volume;
    memcpy(record.authority_contract_id, reservation->authority_contract_id, 16U);
    record.receipt_volume = receipt_identity->VolumeSerialNumber;
    memcpy(record.receipt_id, receipt_identity->FileId.Identifier, 16U);
    record.evidence_volume = evidence_identity->VolumeSerialNumber;
    memcpy(record.evidence_id, evidence_identity->FileId.Identifier, 16U);
    memcpy(&record.contract, contract, sizeof(record.contract));
    memcpy(&record.unload, unload, sizeof(record.unload));
    if (!seek_offset(receipt, (LONGLONG)sizeof(*reservation)) ||
        !WriteFile(receipt, &record, (DWORD)sizeof(record), &written, NULL) ||
        written != sizeof(record) || !FlushFileBuffers(receipt) || !seek_start(receipt) ||
        !read_exact(receipt, &reservation_readback, (DWORD)sizeof(reservation_readback)) ||
        !read_exact(receipt, &completion_readback, (DWORD)sizeof(completion_readback)) ||
        ReadFile(receipt, &trailing, 1U, &trailing_bytes, NULL) == FALSE || trailing_bytes != 0U ||
        memcmp(reservation, &reservation_readback, sizeof(*reservation)) != 0 ||
        memcmp(&record, &completion_readback, sizeof(record)) != 0 ||
        !regular_file(receipt, &bytes) ||
        bytes != sizeof(*reservation) + sizeof(record) ||
        !GetFileInformationByHandleEx(receipt, FileIdInfo, &identity_after,
            (DWORD)sizeof(identity_after)) || !same_identity(receipt_identity, &identity_after)) return 0;
    SecureZeroMemory(&record, sizeof(record));
    SecureZeroMemory(&reservation_readback, sizeof(reservation_readback));
    SecureZeroMemory(&completion_readback, sizeof(completion_readback));
    return 1;
}

#define RESOLVE_API(api, member, export_name) do { \
    FARPROC procedure = GetProcAddress((api)->module, (export_name)); \
    if (procedure == NULL || sizeof(procedure) != sizeof((api)->member)) return 0; \
    memcpy(&(api)->member, &procedure, sizeof(procedure)); \
} while (0)

static int resolve_python_api(PythonApi *api) {
    RESOLVE_API(api, config_init, "PyConfig_InitIsolatedConfig");
    RESOLVE_API(api, config_set_string, "PyConfig_SetString");
    RESOLVE_API(api, wide_append, "PyWideStringList_Append");
    RESOLVE_API(api, initialize, "Py_InitializeFromConfig");
    RESOLVE_API(api, status_exception, "PyStatus_Exception");
    RESOLVE_API(api, config_clear, "PyConfig_Clear");
    RESOLVE_API(api, finalize, "Py_FinalizeEx");
    RESOLVE_API(api, compile, "Py_CompileStringExFlags");
    RESOLVE_API(api, eval_code, "PyEval_EvalCode");
    RESOLVE_API(api, run_string, "PyRun_StringFlags");
    RESOLVE_API(api, dict_new, "PyDict_New");
    RESOLVE_API(api, dict_set, "PyDict_SetItemString");
    RESOLVE_API(api, dict_get, "PyDict_GetItemString");
    RESOLVE_API(api, get_builtins, "PyEval_GetBuiltins");
    RESOLVE_API(api, unicode_from_string, "PyUnicode_FromString");
    RESOLVE_API(api, unicode_utf8, "PyUnicode_AsUTF8AndSize");
    RESOLVE_API(api, bytes_from_data, "PyBytes_FromStringAndSize");
    RESOLVE_API(api, tuple_size, "PyTuple_Size");
    RESOLVE_API(api, tuple_get, "PyTuple_GetItem");
    RESOLVE_API(api, callable, "PyCallable_Check");
    RESOLVE_API(api, decref, "Py_DecRef");
    RESOLVE_API(api, error_occurred, "PyErr_Occurred");
    RESOLVE_API(api, error_clear, "PyErr_Clear");
    return 1;
}

static int verify_controller_exports(PythonApi *api, PyObject *globals) {
    static const char *expected[5] = {
        "_build_execution_plan", "_validate_child_payload", "_compare_pair",
        "_success_payload", "_failure_payload"
    };
    PyObject *tuple = api->dict_get(globals, "CONTROLLER_EXPORTED_CALLS");
    size_t index;
    if (tuple == NULL || api->tuple_size(tuple) != 5) return 0;
    for (index = 0U; index < _countof(expected); ++index) {
        PyObject *name = api->tuple_get(tuple, (Py_ssize_t)index);
        PyObject *callable;
        Py_ssize_t length = 0;
        const char *text = name != NULL ? api->unicode_utf8(name, &length) : NULL;
        if (text == NULL || length != (Py_ssize_t)strlen(expected[index]) ||
            memcmp(text, expected[index], (size_t)length) != 0) return 0;
        callable = api->dict_get(globals, expected[index]);
        if (callable == NULL || api->callable(callable) != 1) return 0;
    }
    return 1;
}

static const char CONTRACT_VALIDATOR[] =
    "import json as _j\n"
    "_c=_j.loads(__contract_bytes__.decode('utf-8'))\n"
    "if type(_c) is not dict: raise RuntimeError('contract_root')\n"
    "if _c.get('schema')!='kira.avatar.r25.foundation_afes_locked_pair_execution.v3r9': raise RuntimeError('schema')\n"
    "if _c.get('attempt_id')!='attempt_03r9': raise RuntimeError('attempt')\n"
    "if _c.get('status')!='PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY': raise RuntimeError('status')\n"
    "if _c.get('required_fresh_run_count')!=2: raise RuntimeError('run_count')\n"
    "_s=_c.get('scope')\n"
    "if _s!={'body_work_only':True,'read_only_blender_diagnostic':True,'blend_mutation_allowed':False,'blend_save_allowed':False,'render_allowed':False,'candidate_creation_allowed':False,'body_authoring_allowed':False,'runtime_activation_allowed':False,'assignment_allowed':False,'export_allowed':False,'publication_allowed':False}: raise RuntimeError('scope')\n"
    "_b=_c.get('bindings')\n"
    "if type(_b) is not dict: raise RuntimeError('bindings')\n"
    "_x=(('python_runtime_dll','C:/Python314/python314.dll',6767440,'a07f7d09c3121492bb066535c6d0811df5fbc2090cbca7031a97bb47ce1480c9'),('retained_stdlib_zip','tools/native/runtime/python314_stdlib_v3r4.zip',28997479,'7e07541a67b8eba5835c9c371ec90e5732fba6602576ae0a6f22e09b09271846'),('parent_controller','tools/run_kira_r25_foundation_afes_locked_pair_v3r9.py',50907,'60674e104d69ac9166aca7ea9001ff32e8494d07677748fbb633955ee1d9ebaf'))\n"
    "for _n,_p,_z,_h in _x:\n"
    "    if _b.get(_n)!={'path':_p,'bytes':_z,'sha256':_h}: raise RuntimeError('binding:'+_n)\n"
    "_v=_c.get('native_launcher_contract')\n"
    "if type(_v) is not dict or _v.get('secure_python_load_occurs_after_retained_graph_lock') is not True: raise RuntimeError('load_order')\n"
    "__v3r20_contract_projection_valid__=True\n";

static int prove_python_module_absent(HMODULE old_module, UnloadTelemetry *telemetry) {
    HANDLE snapshot;
    MODULEENTRY32W entry;
    BOOL more;
    DWORD terminal_error = ERROR_SUCCESS;
    snapshot = CreateToolhelp32Snapshot(
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId());
    if (snapshot == INVALID_HANDLE_VALUE) {
        telemetry->snapshot_error = GetLastError();
        return 0;
    }
    SecureZeroMemory(&entry, sizeof(entry));
    entry.dwSize = (DWORD)sizeof(entry);
    more = Module32FirstW(snapshot, &entry);
    if (!more) {
        telemetry->snapshot_error = GetLastError();
        CloseHandle(snapshot);
        return 0;
    }
    do {
        telemetry->checked_module_count += 1U;
        if (entry.hModule == old_module) telemetry->old_base_present = 1U;
        if (_wcsicmp(entry.szExePath, PYTHON_DLL_PATH) == 0) telemetry->exact_path_present = 1U;
        more = Module32NextW(snapshot, &entry);
        if (!more) terminal_error = GetLastError();
    } while (more);
    CloseHandle(snapshot);
    if (terminal_error != ERROR_NO_MORE_FILES) {
        telemetry->snapshot_error = terminal_error;
        return 0;
    }
    telemetry->snapshot_succeeded = 1U;
    return telemetry->old_base_present == 0U && telemetry->exact_path_present == 0U;
}

static int run_python_validation(LockedFile *python_dll, LockedFile *stdlib_zip,
    LockedFile *controller, LockedFile *execution_contract, UnloadTelemetry *unload,
    uint32_t *stage) {
    PythonApi api;
    PyConfig config;
    PyStatus status;
    unsigned char *controller_bytes = NULL;
    unsigned char *contract_bytes = NULL;
    DWORD controller_length = 0U;
    DWORD contract_length = 0U;
    PyObject *globals = NULL;
    PyObject *builtins;
    PyObject *name = NULL;
    PyObject *code = NULL;
    PyObject *evaluation = NULL;
    PyObject *contract_object = NULL;
    PyObject *projection = NULL;
    wchar_t module_path[32768];
    DWORD module_length;
    int initialized = 0;
    int ok = 0;
    int finalize_ok = 1;
    HMODULE old_module = NULL;
    SecureZeroMemory(&api, sizeof(api));
    SecureZeroMemory(unload, sizeof(*unload));
    if (!SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS)) return 0;
    api.module = LoadLibraryExW(PYTHON_DLL_PATH, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (api.module == NULL) return 0;
    old_module = api.module;
    unload->old_module_base = (uint64_t)(uintptr_t)old_module;
    module_length = GetModuleFileNameW(api.module, module_path, (DWORD)_countof(module_path));
    if (module_length == 0U || module_length >= (DWORD)_countof(module_path) ||
        _wcsicmp(module_path, PYTHON_DLL_PATH) != 0 ||
        !verify_handle_bound(python_dll->handle, python_dll->path,
            python_dll->expected_bytes, python_dll->expected_sha256, &python_dll->identity) ||
        !resolve_python_api(&api)) goto cleanup;
    *stage = 20U;
    api.config_init(&config);
    config.use_environment = 0;
    config.user_site_directory = 0;
    config.site_import = 0;
    config.write_bytecode = 0;
    config.install_signal_handlers = 0;
    config.parse_argv = 0;
    config.safe_path = 1;
    config.module_search_paths_set = 1;
    status = api.config_set_string(&config, &config.program_name, SELF_PATH);
    if (!api.status_exception(status)) status = api.config_set_string(&config, &config.executable, SELF_PATH);
    if (!api.status_exception(status)) status = api.wide_append(&config.module_search_paths, STDLIB_ZIP_PATH);
    if (!api.status_exception(status)) status = api.wide_append(&config.argv, L"<v3r20-retained-controller-validation>");
    if (api.status_exception(status)) {
        api.config_clear(&config);
        goto cleanup;
    }
    status = api.initialize(&config);
    api.config_clear(&config);
    if (api.status_exception(status)) goto cleanup;
    initialized = 1;
    *stage = 30U;
    if (!read_locked(controller, CONTROLLER_LIMIT, &controller_bytes, &controller_length) ||
        memchr(controller_bytes, '\0', controller_length) != NULL ||
        !read_locked(execution_contract, CONTRACT_LIMIT, &contract_bytes, &contract_length) ||
        memchr(contract_bytes, '\0', contract_length) != NULL) goto cleanup;
    globals = api.dict_new();
    builtins = api.get_builtins();
    name = api.unicode_from_string("__main__");
    if (globals == NULL || builtins == NULL || name == NULL ||
        api.dict_set(globals, "__builtins__", builtins) < 0 ||
        api.dict_set(globals, "__name__", name) < 0) goto cleanup;
    code = api.compile((const char *)controller_bytes, "<retained-controller-v3r9>",
        Py_file_input, NULL, -1);
    if (code == NULL) goto cleanup;
    evaluation = api.eval_code(code, globals, globals);
    if (evaluation == NULL || !verify_controller_exports(&api, globals)) goto cleanup;
    *stage = 40U;
    contract_object = api.bytes_from_data((const char *)contract_bytes, (Py_ssize_t)contract_length);
    if (contract_object == NULL || api.dict_set(globals, "__contract_bytes__", contract_object) < 0) goto cleanup;
    projection = api.run_string(CONTRACT_VALIDATOR, Py_file_input, globals, globals, NULL);
    if (projection == NULL || api.dict_get(globals, "__v3r20_contract_projection_valid__") == NULL) goto cleanup;
    *stage = 50U;
    ok = 1;
cleanup:
    if (initialized && api.error_occurred != NULL && api.error_occurred() != NULL &&
        api.error_clear != NULL) api.error_clear();
    if (api.decref != NULL) {
        if (projection != NULL) api.decref(projection);
        if (contract_object != NULL) api.decref(contract_object);
        if (evaluation != NULL) api.decref(evaluation);
        if (code != NULL) api.decref(code);
        if (name != NULL) api.decref(name);
        if (globals != NULL) api.decref(globals);
    }
    if (controller_bytes != NULL) {
        SecureZeroMemory(controller_bytes, (SIZE_T)controller_length + 1U);
        HeapFree(GetProcessHeap(), 0U, controller_bytes);
    }
    if (contract_bytes != NULL) {
        SecureZeroMemory(contract_bytes, (SIZE_T)contract_length + 1U);
        HeapFree(GetProcessHeap(), 0U, contract_bytes);
    }
    if (initialized) {
        unload->finalize_called = 1U;
        unload->finalize_result = api.finalize();
        if (unload->finalize_result < 0) finalize_ok = 0;
    }
    if (api.module != NULL) {
        unload->free_library_called = 1U;
        unload->free_library_result = FreeLibrary(api.module) ? 1U : 0U;
        if (unload->free_library_result == 0U) finalize_ok = 0;
    }
    api.module = NULL;
    if (old_module == NULL || !prove_python_module_absent(old_module, unload)) finalize_ok = 0;
    if (!finalize_ok) ok = 0;
    if (ok) *stage = 60U;
    (void)stdlib_zip;
    return ok;
}

int wmain(int argc, wchar_t **argv) {
    static const Binding fixed[] = {
        {SOURCE_PATH, V3R20_SOURCE_BYTES, V3R20_SOURCE_SHA256, "source"},
        {TEST_PATH, V3R20_TEST_BYTES, V3R20_TEST_SHA256, "test"},
        {CONTROL_PATH, V3R20_CONTROL_BYTES, V3R20_CONTROL_SHA256, "control"},
        {V3R14_EVIDENCE_PATH, V3R20_V3R14_EVIDENCE_BYTES, V3R20_V3R14_EVIDENCE_SHA256, "v3r14_evidence"},
        {V3R14_RECEIPT_PATH, V3R20_V3R14_RECEIPT_BYTES, V3R20_V3R14_RECEIPT_SHA256, "v3r14_receipt"},
        {V3R14_AUDIT_CHECKPOINT_PATH, V3R20_V3R14_AUDIT_BYTES, V3R20_V3R14_AUDIT_SHA256, "v3r14_audit"},
        {V3R14_POSTMORTEM_PATH, V3R20_V3R14_POSTMORTEM_BYTES, V3R20_V3R14_POSTMORTEM_SHA256, "v3r14_postmortem"},
        {V3R17_CHECKPOINT_PATH, V3R20_V3R17_CHECKPOINT_BYTES, V3R20_V3R17_CHECKPOINT_SHA256, "v3r17_checkpoint"},
        {V3R17_SEAL_PATH, V3R20_V3R17_SEAL_BYTES, V3R20_V3R17_SEAL_SHA256, "v3r17_seal"},
        {V3R17_RUN_EVIDENCE_PATH, V3R20_V3R17_RUN_EVIDENCE_BYTES, V3R20_V3R17_RUN_EVIDENCE_SHA256, "v3r17_run_evidence"},
        {V3R17_RECEIPT_PATH, V3R20_V3R17_RECEIPT_BYTES, V3R20_V3R17_RECEIPT_SHA256, "v3r17_receipt"},
        {V3R17_AUDIT_CHECKPOINT_PATH, V3R20_V3R17_AUDIT_CHECKPOINT_BYTES, V3R20_V3R17_AUDIT_CHECKPOINT_SHA256, "v3r17_audit_checkpoint"},
        {V3R17_RUN_OUTCOME_PATH, V3R20_V3R17_RUN_OUTCOME_BYTES, V3R20_V3R17_RUN_OUTCOME_SHA256, "v3r17_run_outcome"},
        {V3R17_POST_RUN_PATH, V3R20_V3R17_POST_RUN_BYTES, V3R20_V3R17_POST_RUN_SHA256, "v3r17_post_run"},
        {V3R18_CONTRACT_PATH, V3R20_V3R18_CONTRACT_BYTES, V3R20_V3R18_CONTRACT_SHA256, "v3r18_contract"},
        {V3R18_SOURCE_PATH, V3R20_V3R18_SOURCE_BYTES, V3R20_V3R18_SOURCE_SHA256, "v3r18_source"},
        {V3R18_ANCHOR_PATH, V3R20_V3R18_ANCHOR_BYTES, V3R20_V3R18_ANCHOR_SHA256, "v3r18_anchor"},
        {V3R18_OBJECT_PATH, V3R20_V3R18_OBJECT_BYTES, V3R20_V3R18_OBJECT_SHA256, "v3r18_object"},
        {V3R18_EXECUTABLE_PATH, V3R20_V3R18_EXECUTABLE_BYTES, V3R20_V3R18_EXECUTABLE_SHA256, "v3r18_executable"},
        {V3R18_TEST_PATH, V3R20_V3R18_TEST_BYTES, V3R20_V3R18_TEST_SHA256, "v3r18_test"},
        {V3R18_CONTROL_PATH, V3R20_V3R18_CONTROL_BYTES, V3R20_V3R18_CONTROL_SHA256, "v3r18_control"},
        {V3R18_BUILD_PATH, V3R20_V3R18_BUILD_BYTES, V3R20_V3R18_BUILD_SHA256, "v3r18_build"},
        {V3R18_SEAL_PATH, V3R20_V3R18_SEAL_BYTES, V3R20_V3R18_SEAL_SHA256, "v3r18_seal"},
        {V3R18_CHECKPOINT_PATH, V3R20_V3R18_CHECKPOINT_BYTES, V3R20_V3R18_CHECKPOINT_SHA256, "v3r18_checkpoint"},
        {V3R18_REJECTION_AUDIT_PATH, V3R20_V3R18_REJECTION_AUDIT_BYTES, V3R20_V3R18_REJECTION_AUDIT_SHA256, "v3r18_rejection_audit"},
        {V3R18_REJECTION_SIDECAR_PATH, V3R20_V3R18_REJECTION_SIDECAR_BYTES, V3R20_V3R18_REJECTION_SIDECAR_SHA256, "v3r18_rejection_sidecar"},
        {V3R18_REJECTION_PROBES_PATH, V3R20_V3R18_REJECTION_PROBES_BYTES, V3R20_V3R18_REJECTION_PROBES_SHA256, "v3r18_rejection_probes"},
        {V3R18_REJECTION_CHECKPOINT_PATH, V3R20_V3R18_REJECTION_CHECKPOINT_BYTES, V3R20_V3R18_REJECTION_CHECKPOINT_SHA256, "v3r18_rejection_checkpoint"},
        {V3R19_CONTRACT_PATH, V3R20_V3R19_CONTRACT_BYTES, V3R20_V3R19_CONTRACT_SHA256, "v3r19_contract"},
        {V3R19_SOURCE_PATH, V3R20_V3R19_SOURCE_BYTES, V3R20_V3R19_SOURCE_SHA256, "v3r19_source"},
        {V3R19_ANCHOR_PATH, V3R20_V3R19_ANCHOR_BYTES, V3R20_V3R19_ANCHOR_SHA256, "v3r19_anchor"},
        {V3R19_OBJECT_PATH, V3R20_V3R19_OBJECT_BYTES, V3R20_V3R19_OBJECT_SHA256, "v3r19_object"},
        {V3R19_EXECUTABLE_PATH, V3R20_V3R19_EXECUTABLE_BYTES, V3R20_V3R19_EXECUTABLE_SHA256, "v3r19_executable"},
        {V3R19_TEST_PATH, V3R20_V3R19_TEST_BYTES, V3R20_V3R19_TEST_SHA256, "v3r19_test"},
        {V3R19_CONTROL_PATH, V3R20_V3R19_CONTROL_BYTES, V3R20_V3R19_CONTROL_SHA256, "v3r19_control"},
        {V3R19_BUILD_PATH, V3R20_V3R19_BUILD_BYTES, V3R20_V3R19_BUILD_SHA256, "v3r19_build"},
        {V3R19_SEAL_PATH, V3R20_V3R19_SEAL_BYTES, V3R20_V3R19_SEAL_SHA256, "v3r19_seal"},
        {V3R19_CHECKPOINT_PATH, V3R20_V3R19_CHECKPOINT_BYTES, V3R20_V3R19_CHECKPOINT_SHA256, "v3r19_checkpoint"},
        {V3R19_ACCEPT_AUDIT_PATH, V3R20_V3R19_ACCEPT_AUDIT_BYTES, V3R20_V3R19_ACCEPT_AUDIT_SHA256, "v3r19_accept_audit"},
        {V3R19_ACCEPT_SIDECAR_PATH, V3R20_V3R19_ACCEPT_SIDECAR_BYTES, V3R20_V3R19_ACCEPT_SIDECAR_SHA256, "v3r19_accept_sidecar"},
        {V3R19_ACCEPT_CHECKPOINT_PATH, V3R20_V3R19_ACCEPT_CHECKPOINT_BYTES, V3R20_V3R19_ACCEPT_CHECKPOINT_SHA256, "v3r19_accept_checkpoint"},
        {V3R19_FAILURE_RECHECK_PATH, V3R20_V3R19_FAILURE_RECHECK_BYTES, V3R20_V3R19_FAILURE_RECHECK_SHA256, "v3r19_failure_recheck"},
        {V3R19_FAILURE_CHECKPOINT_PATH, V3R20_V3R19_FAILURE_CHECKPOINT_BYTES, V3R20_V3R19_FAILURE_CHECKPOINT_SHA256, "v3r19_failure_checkpoint"}
    };
    LockedFile retained[5] = {
        {MANIFEST_PATH, V3R20_MANIFEST_BYTES, V3R20_MANIFEST_SHA256, INVALID_HANDLE_VALUE, {0}},
        {PYTHON_DLL_PATH, V3R20_PYTHON_DLL_BYTES, V3R20_PYTHON_DLL_SHA256, INVALID_HANDLE_VALUE, {0}},
        {STDLIB_ZIP_PATH, V3R20_STDLIB_ZIP_BYTES, V3R20_STDLIB_ZIP_SHA256, INVALID_HANDLE_VALUE, {0}},
        {CONTROLLER_PATH, V3R20_CONTROLLER_BYTES, V3R20_CONTROLLER_SHA256, INVALID_HANDLE_VALUE, {0}},
        {EXECUTION_CONTRACT_PATH, V3R20_EXECUTION_CONTRACT_BYTES, V3R20_EXECUTION_CONTRACT_SHA256, INVALID_HANDLE_VALUE, {0}}
    };
    LockedFile authority_contract = {
        CONTRACT_PATH, V3R20_CONTRACT_BYTES, V3R20_CONTRACT_SHA256,
        INVALID_HANDLE_VALUE, {0}
    };
    unsigned char *manifest = NULL;
    DWORD manifest_bytes = 0U;
    wchar_t current[MAX_PATH];
    wchar_t module[MAX_PATH];
    DWORD current_length;
    DWORD module_length;
    ULONGLONG self_bytes = 0ULL;
    unsigned char self_sha[SHA_BYTES];
    unsigned char audit_sha[SHA_BYTES];
    HANDLE evidence = INVALID_HANDLE_VALUE;
    HANDLE receipt = INVALID_HANDLE_VALUE;
    HANDLE contract_handle = INVALID_HANDLE_VALUE;
    FILE_ID_INFO evidence_identity;
    FILE_ID_INFO receipt_identity;
    ReservationRecord reservation;
    ContractTelemetry contract_telemetry;
    UnloadTelemetry unload_telemetry;
    FILE_ID_INFO contract_identity;
    size_t index;
    uint32_t terminal_stage = 1U;
    int stage_ok = 0;
    int outcome_ok = 0;
    int result = 1;
    (void)argv;
    SecureZeroMemory(self_sha, sizeof(self_sha));
    SecureZeroMemory(audit_sha, sizeof(audit_sha));
    SecureZeroMemory(&evidence_identity, sizeof(evidence_identity));
    SecureZeroMemory(&receipt_identity, sizeof(receipt_identity));
    SecureZeroMemory(&reservation, sizeof(reservation));
    SecureZeroMemory(&contract_telemetry, sizeof(contract_telemetry));
    SecureZeroMemory(&unload_telemetry, sizeof(unload_telemetry));
    SecureZeroMemory(&contract_identity, sizeof(contract_identity));
    if (argc != 1) return 2;
    current_length = GetCurrentDirectoryW((DWORD)_countof(current), current);
    module_length = GetModuleFileNameW(NULL, module, (DWORD)_countof(module));
    if (current_length == 0U || current_length >= (DWORD)_countof(current) ||
        wcscmp(current, PROJECT_ROOT) != 0 || module_length == 0U ||
        module_length >= (DWORD)_countof(module) || wcscmp(module, SELF_PATH) != 0 ||
        !hash_path_unbound(SELF_PATH, 4194304ULL, &self_bytes, self_sha)) return 3;
    for (index = 0U; index < _countof(fixed); ++index) {
        if (!hash_path_exact(fixed[index].path, fixed[index].bytes,
                fixed[index].sha256, NULL)) {
            fwprintf(stderr, L"V3R20_SUBJECT_REFUSED:%S\n", fixed[index].label);
            return 4;
        }
    }
    if (!lock_file(&authority_contract)) return 5;
    if (!verify_audit(self_sha, audit_sha) || !verify_output_parent()) {
        CloseHandle(authority_contract.handle);
        return 5;
    }
    terminal_stage = 10U;
    evidence = CreateFileW(EVIDENCE_PATH, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,
        NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH |
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (evidence == INVALID_HANDLE_VALUE || !exact_final_path(evidence, EVIDENCE_PATH) ||
        !GetFileInformationByHandleEx(evidence, FileIdInfo, &evidence_identity,
            (DWORD)sizeof(evidence_identity)) || !append_line(evidence, E_ENTRY) ||
        !append_line(evidence, E_GATE) || !reserve_outcome(evidence, &evidence_identity,
            self_sha, audit_sha, &authority_contract, &receipt, &receipt_identity, &reservation) ||
        !append_line(evidence, E_RESERVED)) goto cleanup;
    terminal_stage = 15U;
    stage_ok = open_contract_granular(&contract_telemetry, &contract_handle,
        &contract_identity);
    terminal_stage = 20U;
    if (stage_ok) {
        for (index = 0U; index < _countof(retained); ++index) {
            if (!lock_file(&retained[index])) { stage_ok = 0; break; }
        }
    }
    if (stage_ok) {
        stage_ok = read_locked(&retained[0], MANIFEST_LIMIT, &manifest, &manifest_bytes) &&
            manifest_exact_row(manifest, manifest_bytes, "python_runtime_dll",
                "C:/Python314/python314.dll", V3R20_PYTHON_DLL_BYTES, V3R20_PYTHON_DLL_SHA256) &&
            manifest_exact_row(manifest, manifest_bytes, "retained_stdlib_zip",
                "tools/native/runtime/python314_stdlib_v3r4.zip", V3R20_STDLIB_ZIP_BYTES, V3R20_STDLIB_ZIP_SHA256) &&
            manifest_exact_row(manifest, manifest_bytes, "parent_controller",
                "tools/run_kira_r25_foundation_afes_locked_pair_v3r9.py", V3R20_CONTROLLER_BYTES, V3R20_CONTROLLER_SHA256) &&
            manifest_exact_row(manifest, manifest_bytes, "execution_contract",
                "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v3r9.json",
                V3R20_EXECUTION_CONTRACT_BYTES, V3R20_EXECUTION_CONTRACT_SHA256);
        terminal_stage = 30U;
    }
    if (stage_ok && run_python_validation(&retained[1], &retained[2], &retained[3],
            &retained[4], &unload_telemetry, &terminal_stage)) {
        stage_ok = append_line(evidence, E_PYTHON) && append_line(evidence, E_CONTROLLER);
    } else if (stage_ok) {
        stage_ok = 0;
    }
    if (stage_ok) {
        for (index = 0U; index < _countof(retained); ++index) {
            if (!verify_handle_bound(retained[index].handle, retained[index].path,
                    retained[index].expected_bytes, retained[index].expected_sha256,
                    &retained[index].identity)) {
                stage_ok = 0;
                break;
            }
        }
    }
    if (stage_ok) stage_ok = append_line(evidence, E_FINALIZED) &&
        append_unload_telemetry(evidence, &unload_telemetry);
    if (stage_ok && !verify_handle_bound(authority_contract.handle,
            authority_contract.path, authority_contract.expected_bytes,
            authority_contract.expected_sha256, &authority_contract.identity)) stage_ok = 0;
    if (contract_handle != INVALID_HANDLE_VALUE) {
        if (!finish_contract_granular(&contract_telemetry, &contract_handle,
                &contract_identity)) stage_ok = 0;
    } else {
        stage_ok = 0;
    }
    if (!append_contract_telemetry(evidence, &contract_telemetry)) stage_ok = 0;
    if (receipt != INVALID_HANDLE_VALUE) {
        outcome_ok = finish_outcome(receipt, &receipt_identity, &evidence_identity,
            &reservation, self_sha, audit_sha, &contract_telemetry,
            &unload_telemetry,
            stage_ok ? RECORD_SUCCESS : RECORD_FAILURE, terminal_stage);
    }
    if (stage_ok && outcome_ok && append_line(evidence, E_SUCCESS)) result = 0;
    else if (evidence != INVALID_HANDLE_VALUE) (void)append_line(evidence, E_FAILURE);
cleanup:
    if (manifest != NULL) {
        SecureZeroMemory(manifest, (SIZE_T)manifest_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, manifest);
    }
    SecureZeroMemory(&reservation, sizeof(reservation));
    SecureZeroMemory(self_sha, sizeof(self_sha));
    SecureZeroMemory(audit_sha, sizeof(audit_sha));
    if (receipt != INVALID_HANDLE_VALUE) CloseHandle(receipt);
    if (evidence != INVALID_HANDLE_VALUE) CloseHandle(evidence);
    if (contract_handle != INVALID_HANDLE_VALUE) CloseHandle(contract_handle);
    if (authority_contract.handle != INVALID_HANDLE_VALUE) CloseHandle(authority_contract.handle);
    for (index = 0U; index < _countof(retained); ++index) {
        if (retained[index].handle != INVALID_HANDLE_VALUE) CloseHandle(retained[index].handle);
    }
    return result;
}
