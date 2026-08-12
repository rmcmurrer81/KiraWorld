/*
 * Kira R25 AFES locked-pair native launcher, append-only v3r6.
 *
 * This executable is the non-Python authority boundary for one retained,
 * independently-audited pair.  It locks and hashes the complete retained TSV
 * graph before starting an isolated embedded Python interpreter.  The only
 * process-local authority visible to retained Python is the private built-in
 * module declared below.  All mutable security state and all Win32 handles
 * remain native-owned.
 *
 * Build (x64 MSVC, Python 3.14):
 *   cl /nologo /W4 /WX /O2 /guard:cf /DUNICODE /D_UNICODE /std:c17 \
 *      /I C:\Python314\include kira_r25_afes_locked_pair_launcher_v3r6.c \
 *      /link /LIBPATH:C:\Python314\libs python314.lib bcrypt.lib delayimp.lib \
 *      /DELAYLOAD:python314.dll
 *
 * This source contains no accepted digest.  Acceptance is external and binds
 * the exact launcher image, retained manifest, fixed fresh audit, and all
 * locked rows.  A different caller-supplied manifest therefore cannot produce
 * evidence matching the independently accepted subject.
 */

#define PY_SSIZE_T_CLEAN
#ifndef NDEBUG
#define NDEBUG 1
#endif
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <bcrypt.h>
#include <Python.h>

#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "delayimp.lib")

#ifndef PROC_THREAD_ATTRIBUTE_JOB_LIST
#define PROC_THREAD_ATTRIBUTE_JOB_LIST ((DWORD_PTR)0x0002000D)
#endif

#define BROKER_MODULE_NAME "_kira_r25_afes_native_broker"
#define MANIFEST_MAGIC "KIRA_R25_AFES_RETAINED_MANIFEST_V3R6\t1"
#define MANIFEST_HEADER "label\tpath\tbytes\tsha256"
#define MAX_MANIFEST_BYTES (8U * 1024U * 1024U)
#define MAX_LOCKED_READ_BYTES (128U * 1024U * 1024U)
#define MAX_OUTCOME_BYTES (8U * 1024U * 1024U)
#define MAX_EVIDENCE_BYTES (64U * 1024U * 1024U)
#define MAX_CHILD_CAPTURE_BYTES (64U * 1024U * 1024U)
#define MAX_CHILD_TIMEOUT_SECONDS 3600.0
#define DRAIN_JOIN_MILLISECONDS 10000U
#define TERMINATION_WAIT_MILLISECONDS 10000U

typedef struct RetainedRow {
    char *label_utf8;
    char *manifest_path_utf8;
    wchar_t *path;
    uint64_t expected_bytes;
    unsigned char expected_sha256[32];
    HANDLE handle;
    ULONGLONG volume_serial;
    FILE_ID_128 file_id;
    wchar_t *final_path;
} RetainedRow;

typedef struct HeldAncestor {
    HANDLE handle;
    wchar_t *requested_path;
    wchar_t *final_path;
    ULONGLONG volume_serial;
    FILE_ID_128 file_id;
    struct HeldAncestor *next;
} HeldAncestor;

typedef struct HeldOutput {
    HANDLE handle;
    wchar_t *path;
    wchar_t *final_path;
    ULONGLONG volume_serial;
    FILE_ID_128 file_id;
    struct HeldOutput *next;
} HeldOutput;

typedef enum BrokerLifecycle {
    NEW = 0,
    GRAPH_LOCKED = 1,
    AUDIT_ACCEPTED = 2,
    ARMED = 3,
    CONSUMED = 4
} BrokerLifecycle;

typedef struct BrokerState {
    wchar_t *self_path;
    wchar_t *project_root;
    wchar_t *manifest_path;
    wchar_t *audit_path;
    HANDLE manifest_handle;
    HANDLE audit_handle;
    ULONGLONG manifest_volume_serial;
    FILE_ID_128 manifest_file_id;
    wchar_t *manifest_final_path;
    ULONGLONG audit_volume_serial;
    FILE_ID_128 audit_file_id;
    wchar_t *audit_final_path;
    uint64_t manifest_bytes;
    uint64_t audit_bytes;
    unsigned char manifest_sha256[32];
    unsigned char audit_sha256[32];
    unsigned char expected_manifest_sha256[32];
    unsigned char expected_contract_sha256[32];
    unsigned char expected_audit_sha256[32];
    RetainedRow *rows;
    size_t row_count;
    size_t bootstrap_index;
    size_t contract_index;
    int initialized;
    int claim_attempted;
    int claimed;
    int outcome_reserved;
    int outcome_committed;
    int outcome_success_provisional;
    int provisional_success_hash_valid;
    uint64_t provisional_success_bytes;
    unsigned char provisional_success_sha256[32];
    unsigned char *staged_outcome_frame;
    size_t staged_outcome_frame_size;
    unsigned char staged_outcome_sha256[32];
    int staged_outcome_sha256_known;
    char staged_outcome_kind[32];
    int output_created;
    int after_snapshot_done;
    int finished;
    int nonces_claimed;
    int next_run_number;
    DWORD process_timeout_milliseconds;
    char pair_nonce[65];
    char run_nonce_1[65];
    char run_nonce_2[65];
    HANDLE outcome_handle;
    wchar_t *outcome_path;
    wchar_t *output_root;
    HeldOutput *held_outputs;
    HeldAncestor *held_ancestors;
    DWORD process_id;
    DWORD main_os_thread_id;
    HANDLE lifecycle_mutex;
    volatile LONG active_child_count;
    volatile LONG run_attempt_consumed[2];
    volatile LONG python_runtime_sealed;
    volatile LONG partial_evidence_write;
    volatile LONG partial_outcome_write;
    volatile LONG evidence_verified_write_count;
    volatile LONG evidence_verified_mask;
    volatile LONG evidence_write_failures;
    volatile LONG multiple_evidence_write_failures;
    volatile LONG outcome_write_failures;
    volatile LONG multiple_outcome_write_failures;
    volatile LONG outcome_attempt_count;
    volatile LONG native_cleanup_failure_count;
    uint64_t partial_evidence_bytes;
    uint64_t partial_evidence_requested_bytes;
    uint64_t partial_outcome_bytes;
    uint64_t partial_outcome_requested_bytes;
    uint64_t outcome_first_attempt_bytes;
    uint64_t outcome_current_attempt_bytes;
    int partial_evidence_size_known;
    int partial_outcome_size_known;
    char partial_evidence_relative_path[260];
    char partial_evidence_phase[64];
    char partial_evidence_class[48];
    char partial_outcome_phase[64];
    char outcome_first_attempt_kind[32];
    char outcome_current_attempt_kind[32];
    char native_cleanup_failure[128];
    unsigned char outcome_first_attempt_sha256[32];
    unsigned char outcome_current_attempt_sha256[32];
    int outcome_first_attempt_seen;
    int outcome_first_attempt_sha256_known;
    int outcome_current_attempt_seen;
    int outcome_current_attempt_sha256_known;
    CRITICAL_SECTION mutex;
    int mutex_initialized;
    BrokerLifecycle lifecycle;
} BrokerState;

typedef struct ByteBuffer {
    unsigned char *data;
    size_t size;
    size_t capacity;
} ByteBuffer;

typedef enum TerminalRewriteResult {
    TERMINAL_REWRITE_NONE = 0,
    TERMINAL_REWRITE_PRIMARY_VERIFIED = 1,
    TERMINAL_REWRITE_FALLBACK_FAILURE_VERIFIED = 2
} TerminalRewriteResult;

typedef struct DrainContext {
    HANDLE read_handle;
    int overlapped_read;
    ByteBuffer captured;
    uint64_t total_bytes;
    size_t maximum;
    int overflow;
    DWORD read_error;
} DrainContext;

typedef struct CleanupList {
    char **items;
    size_t count;
    size_t capacity;
    size_t dropped_count;
    int recording_failed;
    char first_dropped_error[384];
} CleanupList;

typedef struct WideVector {
    wchar_t **items;
    size_t count;
    size_t capacity;
} WideVector;

static BrokerState g_state;

static int verify_self_image_matches_manifest(void);
static int verify_retained_row_identity(RetainedRow *row);
static int secure_load_embedded_python(void);
static int verify_output_ancestor_chain(void);

static int byte_buffer_reserve(ByteBuffer *buffer, size_t required);
static int path_is_absolute(const wchar_t *path);

static void secure_zero(void *value, size_t length) {
    if (value != NULL && length != 0U) {
        SecureZeroMemory(value, length);
    }
}

static char *duplicate_bytes_as_cstr(const char *value, size_t length) {
    char *copy;
    if (value == NULL || length > SIZE_MAX - 1U) {
        return NULL;
    }
    copy = (char *)malloc(length + 1U);
    if (copy == NULL) {
        return NULL;
    }
    memcpy(copy, value, length);
    copy[length] = '\0';
    return copy;
}

static wchar_t *duplicate_wide(const wchar_t *value) {
    size_t count;
    wchar_t *copy;
    if (value == NULL) {
        return NULL;
    }
    count = wcslen(value);
    if (count > (SIZE_MAX / sizeof(wchar_t)) - 1U) {
        return NULL;
    }
    copy = (wchar_t *)malloc((count + 1U) * sizeof(wchar_t));
    if (copy == NULL) {
        return NULL;
    }
    memcpy(copy, value, (count + 1U) * sizeof(wchar_t));
    return copy;
}

static wchar_t *utf8_to_wide_strict(const char *value, size_t length) {
    int required;
    wchar_t *result;
    if (value == NULL || length > INT_MAX) {
        return NULL;
    }
    required = MultiByteToWideChar(
        CP_UTF8, MB_ERR_INVALID_CHARS, value, (int)length, NULL, 0
    );
    if (required <= 0) {
        return NULL;
    }
    result = (wchar_t *)malloc(((size_t)required + 1U) * sizeof(wchar_t));
    if (result == NULL) {
        return NULL;
    }
    if (MultiByteToWideChar(
            CP_UTF8, MB_ERR_INVALID_CHARS, value, (int)length, result, required
        ) != required) {
        free(result);
        return NULL;
    }
    result[required] = L'\0';
    return result;
}

static char *wide_to_utf8_strict(const wchar_t *value) {
    int required;
    char *result;
    if (value == NULL) {
        return NULL;
    }
    required = WideCharToMultiByte(
        CP_UTF8, WC_ERR_INVALID_CHARS, value, -1, NULL, 0, NULL, NULL
    );
    if (required <= 0) {
        return NULL;
    }
    result = (char *)malloc((size_t)required);
    if (result == NULL) {
        return NULL;
    }
    if (WideCharToMultiByte(
            CP_UTF8, WC_ERR_INVALID_CHARS, value, -1, result, required,
            NULL, NULL
        ) != required) {
        free(result);
        return NULL;
    }
    return result;
}

static int is_lower_hex64(const char *value) {
    size_t index;
    if (value == NULL || strlen(value) != 64U) {
        return 0;
    }
    for (index = 0U; index < 64U; ++index) {
        if (!((value[index] >= '0' && value[index] <= '9') ||
              (value[index] >= 'a' && value[index] <= 'f'))) {
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
        return 10 + value - 'a';
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

static void hex_encode32(const unsigned char value[32], char output[65]) {
    static const char alphabet[] = "0123456789abcdef";
    size_t index;
    for (index = 0U; index < 32U; ++index) {
        output[index * 2U] = alphabet[(value[index] >> 4) & 0x0fU];
        output[index * 2U + 1U] = alphabet[value[index] & 0x0fU];
    }
    output[64] = '\0';
}

static int generate_nonce_hex(char output[65]) {
    unsigned char random_bytes[32];
    NTSTATUS status = BCryptGenRandom(
        NULL, random_bytes, (ULONG)sizeof(random_bytes),
        BCRYPT_USE_SYSTEM_PREFERRED_RNG
    );
    if (status < 0) {
        secure_zero(random_bytes, sizeof(random_bytes));
        return 0;
    }
    hex_encode32(random_bytes, output);
    secure_zero(random_bytes, sizeof(random_bytes));
    return 1;
}

static int constant_time_equal32(
    const unsigned char left[32], const unsigned char right[32]
) {
    unsigned char difference = 0U;
    size_t index;
    for (index = 0U; index < 32U; ++index) {
        difference |= (unsigned char)(left[index] ^ right[index]);
    }
    return difference == 0U;
}

static int parse_canonical_u64(const char *value, uint64_t *output) {
    uint64_t result = 0U;
    const unsigned char *cursor = (const unsigned char *)value;
    if (value == NULL || value[0] == '\0' ||
        (value[0] == '0' && value[1] != '\0')) {
        return 0;
    }
    while (*cursor != '\0') {
        unsigned digit;
        if (*cursor < (unsigned char)'0' || *cursor > (unsigned char)'9') {
            return 0;
        }
        digit = (unsigned)(*cursor - (unsigned char)'0');
        if (result > (UINT64_MAX - digit) / 10U) {
            return 0;
        }
        result = result * 10U + digit;
        ++cursor;
    }
    *output = result;
    return 1;
}

static wchar_t *get_module_path(HMODULE module) {
    DWORD capacity = 512U;
    for (;;) {
        wchar_t *buffer = (wchar_t *)malloc((size_t)capacity * sizeof(wchar_t));
        DWORD length;
        if (buffer == NULL) {
            return NULL;
        }
        SetLastError(ERROR_SUCCESS);
        length = GetModuleFileNameW(module, buffer, capacity);
        if (length == 0U) {
            free(buffer);
            return NULL;
        }
        if (length < capacity - 1U ||
            (length < capacity && GetLastError() != ERROR_INSUFFICIENT_BUFFER)) {
            buffer[length] = L'\0';
            return buffer;
        }
        free(buffer);
        if (capacity > 32768U) {
            return NULL;
        }
        capacity *= 2U;
    }
}

static wchar_t *canonical_full_path(const wchar_t *input) {
    DWORD required;
    wchar_t *result;
    if (input == NULL || input[0] == L'\0') {
        return NULL;
    }
    required = GetFullPathNameW(input, 0U, NULL, NULL);
    if (required == 0U) {
        return NULL;
    }
    result = (wchar_t *)malloc(((size_t)required + 1U) * sizeof(wchar_t));
    if (result == NULL) {
        return NULL;
    }
    if (GetFullPathNameW(input, required + 1U, result, NULL) == 0U) {
        free(result);
        return NULL;
    }
    return result;
}

static int handle_identity(
    HANDLE handle, ULONGLONG *volume_serial, FILE_ID_128 *file_id,
    wchar_t **final_path
) {
    FILE_ID_INFO identity;
    DWORD required;
    wchar_t *buffer;
    wchar_t *normalized;
    size_t offset = 0U;
    if (handle == NULL || handle == INVALID_HANDLE_VALUE ||
        GetFileType(handle) != FILE_TYPE_DISK ||
        !GetFileInformationByHandleEx(
            handle, FileIdInfo, &identity, (DWORD)sizeof(identity))) {
        return 0;
    }
    required = GetFinalPathNameByHandleW(
        handle, NULL, 0U, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (required == 0U) {
        return 0;
    }
    buffer = (wchar_t *)calloc((size_t)required + 2U, sizeof(wchar_t));
    if (buffer == NULL || GetFinalPathNameByHandleW(
            handle, buffer, required + 1U,
            FILE_NAME_NORMALIZED | VOLUME_NAME_DOS) == 0U) {
        free(buffer);
        return 0;
    }
    if (wcsncmp(buffer, L"\\\\?\\UNC\\", 8U) == 0) {
        offset = 6U;
        buffer[offset] = L'\\';
    } else if (wcsncmp(buffer, L"\\\\?\\", 4U) == 0) {
        offset = 4U;
    }
    normalized = duplicate_wide(buffer + offset);
    free(buffer);
    if (normalized == NULL) {
        return 0;
    }
    *volume_serial = identity.VolumeSerialNumber;
    memcpy(file_id, &identity.FileId, sizeof(*file_id));
    *final_path = normalized;
    return 1;
}

static int same_file_identity(
    ULONGLONG left_volume, const FILE_ID_128 *left_id,
    ULONGLONG right_volume, const FILE_ID_128 *right_id
) {
    return left_volume == right_volume &&
        memcmp(left_id, right_id, sizeof(*left_id)) == 0;
}

static int final_handle_matches_path(
    HANDLE handle, const wchar_t *expected_path, ULONGLONG *volume_serial,
    FILE_ID_128 *file_id, wchar_t **final_path
) {
    wchar_t *canonical = canonical_full_path(expected_path);
    wchar_t *measured = NULL;
    ULONGLONG volume = 0ULL;
    FILE_ID_128 id;
    int matches;
    memset(&id, 0, sizeof(id));
    if (canonical == NULL ||
        !handle_identity(handle, &volume, &id, &measured)) {
        free(canonical);
        free(measured);
        return 0;
    }
    matches = _wcsicmp(canonical, measured) == 0;
    free(canonical);
    if (!matches) {
        free(measured);
        return 0;
    }
    *volume_serial = volume;
    memcpy(file_id, &id, sizeof(id));
    *final_path = measured;
    return 1;
}

static int hold_directory_ancestor(const wchar_t *directory_path) {
    HANDLE handle;
    BY_HANDLE_FILE_INFORMATION info;
    ULONGLONG volume = 0ULL;
    FILE_ID_128 id;
    wchar_t *final_path = NULL;
    HeldAncestor *cursor;
    HeldAncestor *held;
    memset(&id, 0, sizeof(id));
    handle = CreateFileW(
        directory_path, FILE_READ_ATTRIBUTES | SYNCHRONIZE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (handle == INVALID_HANDLE_VALUE ||
        !GetFileInformationByHandle(handle, &info) ||
        (info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0U ||
        (info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U ||
        !final_handle_matches_path(
            handle, directory_path, &volume, &id, &final_path)) {
        if (handle != INVALID_HANDLE_VALUE) {
            CloseHandle(handle);
        }
        free(final_path);
        return 0;
    }
    for (cursor = g_state.held_ancestors; cursor != NULL; cursor = cursor->next) {
        if (same_file_identity(
                cursor->volume_serial, &cursor->file_id, volume, &id)) {
            CloseHandle(handle);
            free(final_path);
            return _wcsicmp(cursor->final_path, directory_path) == 0;
        }
    }
    held = (HeldAncestor *)calloc(1U, sizeof(*held));
    if (held == NULL) {
        CloseHandle(handle);
        free(final_path);
        return 0;
    }
    held->requested_path = canonical_full_path(directory_path);
    held->final_path = final_path;
    held->handle = handle;
    held->volume_serial = volume;
    memcpy(&held->file_id, &id, sizeof(id));
    if (held->requested_path == NULL) {
        CloseHandle(handle);
        free(held->final_path);
        free(held);
        return 0;
    }
    held->next = g_state.held_ancestors;
    g_state.held_ancestors = held;
    return 1;
}

static int hold_every_path_ancestor(const wchar_t *absolute_path) {
    wchar_t *probe;
    size_t length;
    size_t index;
    size_t last_separator = 0U;
    int ok = 1;
    if (absolute_path == NULL || !path_is_absolute(absolute_path)) {
        return 0;
    }
    probe = canonical_full_path(absolute_path);
    if (probe == NULL) {
        return 0;
    }
    length = wcslen(probe);
    for (index = 3U; index < length; ++index) {
        if (probe[index] == L'\\' || probe[index] == L'/') {
            last_separator = index;
        }
    }
    if (last_separator == 0U) {
        free(probe);
        return 0;
    }
    {
        wchar_t volume_root[4] = {probe[0], L':', L'\\', L'\0'};
        if (!hold_directory_ancestor(volume_root)) {
            ok = 0;
        }
    }
    for (index = 3U; ok && index <= last_separator; ++index) {
        if (index == last_separator || probe[index] == L'\\' ||
            probe[index] == L'/') {
            wchar_t saved = probe[index];
            probe[index] = L'\0';
            if (!hold_directory_ancestor(probe)) {
                ok = 0;
            }
            probe[index] = saved;
        }
    }
    free(probe);
    return ok;
}

static int path_is_absolute(const wchar_t *path) {
    return path != NULL &&
        (((path[0] >= L'A' && path[0] <= L'Z') ||
          (path[0] >= L'a' && path[0] <= L'z')) && path[1] == L':' &&
         (path[2] == L'\\' || path[2] == L'/')) ||
        (path[0] == L'\\' && path[1] == L'\\');
}

static int safe_relative_path(const wchar_t *path, int allow_nested) {
    const wchar_t *component;
    const wchar_t *cursor;
    if (path == NULL || path[0] == L'\0' || path_is_absolute(path) ||
        path[0] == L'\\' || path[0] == L'/' || wcschr(path, L':') != NULL ||
        wcsstr(path, L"GLOBALROOT") != NULL ||
        wcsstr(path, L"\\\\.\\") != NULL ||
        wcsstr(path, L"::$DATA") != NULL) { /* ads_name_refused */
        return 0;
    }
    component = path;
    cursor = path;
    for (;;) {
        if (*cursor == L'\\' || *cursor == L'/' || *cursor == L'\0') {
            size_t length = (size_t)(cursor - component);
            wchar_t base[16];
            size_t base_length = 0U;
            const wchar_t *reserved[] = {
                L"CON", L"PRN", L"AUX", L"NUL", L"COM1", L"COM2",
                L"COM3", L"COM4", L"COM5", L"COM6", L"COM7", L"COM8",
                L"COM9", L"LPT1", L"LPT2", L"LPT3", L"LPT4", L"LPT5",
                L"LPT6", L"LPT7", L"LPT8", L"LPT9"
            };
            size_t reserved_index;
            if (length == 0U ||
                (length == 1U && component[0] == L'.') ||
                (length == 2U && component[0] == L'.' && component[1] == L'.') ||
                component[length - 1U] == L'.' ||
                component[length - 1U] == L' ') { /* trailing_dot_or_space */
                return 0;
            }
            while (base_length < length && component[base_length] != L'.' &&
                   base_length + 1U < sizeof(base) / sizeof(base[0])) {
                base[base_length] = component[base_length];
                ++base_length;
            }
            base[base_length] = L'\0';
            for (reserved_index = 0U;
                 reserved_index < sizeof(reserved) / sizeof(reserved[0]);
                 ++reserved_index) {
                if (_wcsicmp(base, reserved[reserved_index]) == 0) {
                    return 0; /* reserved_device_name_refused */
                }
            }
            if (!allow_nested && *cursor != L'\0') {
                return 0;
            }
            if (*cursor == L'\0') {
                break;
            }
            component = cursor + 1;
        }
        ++cursor;
    }
    return 1;
}

static wchar_t *join_project_relative(const wchar_t *relative) {
    size_t root_length;
    size_t relative_length;
    wchar_t *joined;
    wchar_t *canonical;
    if (!safe_relative_path(relative, 1) || g_state.project_root == NULL) {
        return NULL;
    }
    root_length = wcslen(g_state.project_root);
    relative_length = wcslen(relative);
    if (root_length > SIZE_MAX - relative_length - 2U) {
        return NULL;
    }
    joined = (wchar_t *)malloc(
        (root_length + relative_length + 2U) * sizeof(wchar_t)
    );
    if (joined == NULL) {
        return NULL;
    }
    memcpy(joined, g_state.project_root, root_length * sizeof(wchar_t));
    joined[root_length] = L'\\';
    memcpy(
        joined + root_length + 1U, relative,
        (relative_length + 1U) * sizeof(wchar_t)
    );
    canonical = canonical_full_path(joined);
    free(joined);
    if (canonical != NULL) {
        size_t prefix_length = wcslen(g_state.project_root);
        if (_wcsnicmp(canonical, g_state.project_root, prefix_length) != 0 ||
            (canonical[prefix_length] != L'\\' &&
             canonical[prefix_length] != L'\0')) {
            free(canonical);
            canonical = NULL;
        }
    }
    return canonical;
}

static int path_has_reparse_component(const wchar_t *absolute_path) {
    wchar_t *probe;
    size_t length;
    size_t index;
    int found = 0;
    if (absolute_path == NULL || !path_is_absolute(absolute_path)) {
        return 1;
    }
    probe = duplicate_wide(absolute_path);
    if (probe == NULL) {
        return 1;
    }
    length = wcslen(probe);
    for (index = 3U; index <= length; ++index) {
        if (probe[index] == L'\\' || probe[index] == L'/' ||
            probe[index] == L'\0') {
            wchar_t saved = probe[index];
            DWORD attributes;
            probe[index] = L'\0';
            attributes = GetFileAttributesW(probe);
            probe[index] = saved;
            if (attributes == INVALID_FILE_ATTRIBUTES ||
                (attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U) {
                found = 1;
                break;
            }
        }
    }
    free(probe);
    return found;
}

static HANDLE open_locked_read_file(const wchar_t *path) {
    HANDLE handle;
    BY_HANDLE_FILE_INFORMATION info;
    handle = CreateFileW(
        path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN |
            FILE_FLAG_OPEN_REPARSE_POINT,
        NULL
    );
    if (handle == INVALID_HANDLE_VALUE) {
        return INVALID_HANDLE_VALUE;
    }
    if (GetFileType(handle) != FILE_TYPE_DISK ||
        !GetFileInformationByHandle(handle, &info) ||
        (info.dwFileAttributes &
         (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0U) {
        CloseHandle(handle);
        SetLastError(ERROR_INVALID_DATA);
        return INVALID_HANDLE_VALUE;
    }
    return handle;
}

static int seek_handle_start(HANDLE handle) {
    LARGE_INTEGER zero;
    zero.QuadPart = 0;
    return SetFilePointerEx(handle, zero, NULL, FILE_BEGIN) != 0;
}

static int sha256_handle(
    HANDLE handle, unsigned char output[32], uint64_t *bytes_read
) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    PUCHAR object = NULL;
    DWORD object_length = 0U;
    DWORD hash_length = 0U;
    DWORD returned = 0U;
    unsigned char buffer[1024U * 1024U];
    uint64_t total = 0U;
    NTSTATUS status;
    int ok = 0;
    if (!seek_handle_start(handle)) {
        return 0;
    }
    status = BCryptOpenAlgorithmProvider(
        &algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U
    );
    if (status < 0) {
        goto cleanup;
    }
    status = BCryptGetProperty(
        algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&object_length,
        sizeof(object_length), &returned, 0U
    );
    if (status < 0 || returned != sizeof(object_length)) {
        goto cleanup;
    }
    status = BCryptGetProperty(
        algorithm, BCRYPT_HASH_LENGTH, (PUCHAR)&hash_length,
        sizeof(hash_length), &returned, 0U
    );
    if (status < 0 || hash_length != 32U) {
        goto cleanup;
    }
    object = (PUCHAR)HeapAlloc(GetProcessHeap(), 0U, object_length);
    if (object == NULL) {
        goto cleanup;
    }
    status = BCryptCreateHash(
        algorithm, &hash, object, object_length, NULL, 0U, 0U
    );
    if (status < 0) {
        goto cleanup;
    }
    for (;;) {
        DWORD count = 0U;
        if (!ReadFile(handle, buffer, sizeof(buffer), &count, NULL)) {
            goto cleanup;
        }
        if (count == 0U) {
            break;
        }
        if (UINT64_MAX - total < count) {
            goto cleanup;
        }
        total += count;
        status = BCryptHashData(hash, buffer, count, 0U);
        if (status < 0) {
            goto cleanup;
        }
    }
    status = BCryptFinishHash(hash, output, 32U, 0U);
    if (status < 0) {
        goto cleanup;
    }
    *bytes_read = total;
    ok = 1;
cleanup:
    secure_zero(buffer, sizeof(buffer));
    if (hash != NULL) {
        BCryptDestroyHash(hash);
    }
    if (object != NULL) {
        secure_zero(object, object_length);
        HeapFree(GetProcessHeap(), 0U, object);
    }
    if (algorithm != NULL) {
        BCryptCloseAlgorithmProvider(algorithm, 0U);
    }
    return ok;
}

static int read_handle_all(
    HANDLE handle, uint64_t expected, size_t maximum, ByteBuffer *output
) {
    size_t target;
    DWORD count;
    if (expected > maximum || expected > SIZE_MAX) {
        return 0;
    }
    target = (size_t)expected;
    output->data = (unsigned char *)malloc(target + 1U);
    if (output->data == NULL) {
        return 0;
    }
    output->size = 0U;
    output->capacity = target + 1U;
    if (!seek_handle_start(handle)) {
        free(output->data);
        memset(output, 0, sizeof(*output));
        return 0;
    }
    while (output->size < target) {
        DWORD request = (DWORD)((target - output->size) > UINT32_MAX
            ? UINT32_MAX : (target - output->size));
        count = 0U;
        if (!ReadFile(handle, output->data + output->size, request, &count, NULL) ||
            count == 0U) {
            free(output->data);
            memset(output, 0, sizeof(*output));
            return 0;
        }
        output->size += count;
    }
    count = 0U;
    if (!ReadFile(handle, output->data + output->size, 1U, &count, NULL) ||
        count != 0U) {
        free(output->data);
        memset(output, 0, sizeof(*output));
        return 0;
    }
    output->data[output->size] = 0U;
    return 1;
}

static RetainedRow *find_row_by_label(const char *label, size_t *index_out) {
    size_t index;
    for (index = 0U; index < g_state.row_count; ++index) {
        if (strcmp(g_state.rows[index].label_utf8, label) == 0) {
            if (index_out != NULL) {
                *index_out = index;
            }
            return &g_state.rows[index];
        }
    }
    return NULL;
}

static RetainedRow *find_row_by_path(const wchar_t *path, size_t *index_out) {
    wchar_t *candidate;
    size_t index;
    RetainedRow *match = NULL;
    size_t matches = 0U;
    if (path == NULL) {
        return NULL;
    }
    if (path_is_absolute(path)) {
        candidate = canonical_full_path(path);
    } else {
        candidate = join_project_relative(path);
    }
    if (candidate == NULL) {
        return NULL;
    }
    for (index = 0U; index < g_state.row_count; ++index) {
        if (_wcsicmp(candidate, g_state.rows[index].path) == 0) {
            match = &g_state.rows[index];
            if (index_out != NULL) {
                *index_out = index;
            }
            ++matches;
        }
    }
    free(candidate);
    return matches == 1U ? match : NULL;
}

static int valid_manifest_label(const char *label) {
    size_t length;
    size_t index;
    if (label == NULL) {
        return 0;
    }
    length = strlen(label);
    if (length == 0U || length > 128U) {
        return 0;
    }
    for (index = 0U; index < length; ++index) {
        unsigned char ch = (unsigned char)label[index];
        if (!(isalnum(ch) || ch == (unsigned char)'_' ||
              ch == (unsigned char)'-' || ch == (unsigned char)'.')) {
            return 0;
        }
    }
    return 1;
}

static size_t split_exact_tabs(char *line, char **fields, size_t field_count) {
    size_t count = 0U;
    char *cursor = line;
    if (line == NULL || field_count == 0U) {
        return 0U;
    }
    fields[count++] = cursor;
    while (*cursor != '\0') {
        if (*cursor == '\t') {
            *cursor = '\0';
            if (count >= field_count) {
                return field_count + 1U;
            }
            fields[count++] = cursor + 1;
        }
        ++cursor;
    }
    return count;
}

static int parse_manifest_rows(ByteBuffer *manifest, char *error, size_t error_size) {
    char *cursor;
    char *end;
    char *line;
    size_t line_number = 0U;
    size_t capacity = 0U;
    const char *previous_label = NULL;
    if (manifest->size == 0U || manifest->data[0] == 0xefU ||
        memchr(manifest->data, '\0', manifest->size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_encoding_invalid");
        return 0;
    }
    cursor = (char *)manifest->data;
    end = cursor + manifest->size;
    if (end[-1] != '\n') {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_final_newline_required");
        return 0;
    }
    while (cursor < end) {
        char *newline = (char *)memchr(cursor, '\n', (size_t)(end - cursor));
        size_t length;
        if (newline == NULL) {
            _snprintf_s(error, error_size, _TRUNCATE, "manifest_line_unterminated");
            return 0;
        }
        line = cursor;
        length = (size_t)(newline - cursor);
        if (length > 0U && line[length - 1U] == '\r') {
            line[length - 1U] = '\0';
        } else {
            line[length] = '\0';
        }
        cursor = newline + 1;
        ++line_number;
        if (line_number == 1U) {
            if (strcmp(line, MANIFEST_MAGIC) != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "manifest_magic_invalid");
                return 0;
            }
            continue;
        }
        if (line_number == 2U) {
            if (strcmp(line, MANIFEST_HEADER) != 0) {
                _snprintf_s(error, error_size, _TRUNCATE, "manifest_header_invalid");
                return 0;
            }
            continue;
        }
        {
            char *fields[4];
            size_t fields_found;
            uint64_t byte_count;
            wchar_t *manifest_path;
            wchar_t *resolved_path;
            RetainedRow *expanded;
            if (line[0] == '\0') {
                _snprintf_s(error, error_size, _TRUNCATE,
                    "manifest_blank_row:%zu", line_number);
                return 0;
            }
            fields_found = split_exact_tabs(line, fields, 4U);
            if (fields_found != 4U || fields[0][0] == '\0' ||
                fields[1][0] == '\0' || fields[2][0] == '\0' ||
                fields[3][0] == '\0') {
                _snprintf_s(error, error_size, _TRUNCATE,
                    "manifest_row_shape_invalid:%zu", line_number);
                return 0;
            }
            if (!valid_manifest_label(fields[0]) ||
                strcmp(fields[0], "accepted_controller_audit") == 0 ||
                strcmp(fields[0], "retained_manifest") == 0 ||
                (previous_label != NULL && strcmp(previous_label, fields[0]) >= 0)) {
                _snprintf_s(error, error_size, _TRUNCATE,
                    "manifest_labels_not_unique_sorted:%zu", line_number);
                return 0;
            }
            if (!parse_canonical_u64(fields[2], &byte_count) ||
                !is_lower_hex64(fields[3])) {
                _snprintf_s(error, error_size, _TRUNCATE,
                    "manifest_row_measurement_invalid:%zu", line_number);
                return 0;
            }
            manifest_path = utf8_to_wide_strict(fields[1], strlen(fields[1]));
            if (manifest_path == NULL) {
                _snprintf_s(error, error_size, _TRUNCATE,
                    "manifest_path_utf8_invalid:%zu", line_number);
                return 0;
            }
            if (path_is_absolute(manifest_path)) {
                resolved_path = canonical_full_path(manifest_path);
            } else {
                resolved_path = join_project_relative(manifest_path);
            }
            free(manifest_path);
            if (resolved_path == NULL) {
                _snprintf_s(error, error_size, _TRUNCATE,
                    "manifest_path_invalid:%zu", line_number);
                return 0;
            }
            {
                size_t existing_index;
                for (existing_index = 0U;
                     existing_index < g_state.row_count; ++existing_index) {
                    if (_wcsicmp(
                            resolved_path,
                            g_state.rows[existing_index].path) == 0) {
                        free(resolved_path);
                        _snprintf_s(error, error_size, _TRUNCATE,
                            "manifest_paths_not_unique:%zu", line_number);
                        return 0;
                    }
                }
            }
            if (g_state.row_count == capacity) {
                size_t new_capacity = capacity == 0U ? 32U : capacity * 2U;
                if (new_capacity < capacity ||
                    new_capacity > SIZE_MAX / sizeof(RetainedRow)) {
                    free(resolved_path);
                    _snprintf_s(error, error_size, _TRUNCATE,
                        "manifest_row_capacity_overflow");
                    return 0;
                }
                expanded = (RetainedRow *)realloc(
                    g_state.rows, new_capacity * sizeof(RetainedRow)
                );
                if (expanded == NULL) {
                    free(resolved_path);
                    _snprintf_s(error, error_size, _TRUNCATE,
                        "manifest_row_allocation_failed");
                    return 0;
                }
                memset(
                    expanded + capacity, 0,
                    (new_capacity - capacity) * sizeof(RetainedRow)
                );
                g_state.rows = expanded;
                capacity = new_capacity;
            }
            g_state.rows[g_state.row_count].label_utf8 =
                duplicate_bytes_as_cstr(fields[0], strlen(fields[0]));
            g_state.rows[g_state.row_count].manifest_path_utf8 =
                duplicate_bytes_as_cstr(fields[1], strlen(fields[1]));
            g_state.rows[g_state.row_count].path = resolved_path;
            g_state.rows[g_state.row_count].expected_bytes = byte_count;
            g_state.rows[g_state.row_count].handle = INVALID_HANDLE_VALUE;
            if (g_state.rows[g_state.row_count].label_utf8 == NULL ||
                g_state.rows[g_state.row_count].manifest_path_utf8 == NULL ||
                !parse_hex64(fields[3],
                    g_state.rows[g_state.row_count].expected_sha256)) {
                _snprintf_s(error, error_size, _TRUNCATE,
                    "manifest_row_allocation_or_hash_failed:%zu", line_number);
                return 0;
            }
            previous_label = g_state.rows[g_state.row_count].label_utf8;
            ++g_state.row_count;
        }
    }
    if (line_number < 3U || g_state.row_count == 0U) {
        _snprintf_s(error, error_size, _TRUNCATE, "manifest_rows_missing");
        return 0;
    }
    return 1;
}

static int verify_self_image_matches_manifest(void) {
    RetainedRow *row = find_row_by_label("native_launcher", NULL);
    wchar_t module_probe[32768];
    DWORD length = GetModuleFileNameW(NULL, module_probe, 32768U);
    int matches = length != 0U && length < 32768U && row != NULL &&
        _wcsicmp(module_probe, g_state.self_path) == 0 &&
        verify_retained_row_identity(row);
    if (!matches) {
        SetLastError(ERROR_INVALID_IMAGE_HASH); /* native_image_identity_mismatch */
    }
    return matches; /* self_file_id_mismatch is fatal to graph locking. */
}

static int lock_and_verify_manifest_rows(char *error, size_t error_size) {
    size_t index;
    RetainedRow *self_row;
    RetainedRow *contract_row;
    RetainedRow *bootstrap_row;
    for (index = 0U; index < g_state.row_count; ++index) {
        uint64_t actual_bytes = 0U;
        unsigned char actual_hash[32];
        RetainedRow *row = &g_state.rows[index];
        if (!hold_every_path_ancestor(row->path) ||
            path_has_reparse_component(row->path)) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "retained_path_ancestor_hold_or_reparse_failed:%s",
                row->label_utf8);
            return 0;
        }
        row->handle = open_locked_read_file(row->path);
        if (row->handle == INVALID_HANDLE_VALUE) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "retained_lock_failed:%s:winerror=%lu", row->label_utf8,
                (unsigned long)GetLastError());
            return 0;
        }
        if (!final_handle_matches_path(
                row->handle, row->path, &row->volume_serial, &row->file_id,
                &row->final_path) ||
            !sha256_handle(row->handle, actual_hash, &actual_bytes) ||
            actual_bytes != row->expected_bytes ||
            !constant_time_equal32(actual_hash, row->expected_sha256)) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "retained_measurement_mismatch:%s", row->label_utf8);
            secure_zero(actual_hash, sizeof(actual_hash));
            return 0;
        }
        secure_zero(actual_hash, sizeof(actual_hash));
    }
    self_row = find_row_by_label("native_launcher", NULL);
    contract_row = find_row_by_label("execution_contract", &g_state.contract_index);
    bootstrap_row = find_row_by_label("trusted_bootstrap", &g_state.bootstrap_index);
    if (bootstrap_row == NULL) {
        /* The exact CLI bootstrap label is resolved later; this is only a
         * compatibility default and not an authority fallback. */
        g_state.bootstrap_index = SIZE_MAX;
    }
    if (self_row == NULL || contract_row == NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "required_manifest_label_missing");
        return 0;
    }
    if (_wcsicmp(self_row->path, g_state.self_path) != 0) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "native_launcher_not_os_self_image");
        return 0;
    }
    if (!constant_time_equal32(
            contract_row->expected_sha256,
            g_state.expected_contract_sha256)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "execution_contract_out_of_band_hash_mismatch");
        return 0;
    }
    if (!verify_self_image_matches_manifest()) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "native_image_identity_mismatch:self_file_id_mismatch");
        return 0;
    }
    return 1;
}

static int recheck_ancestor_chain(void) {
    HeldAncestor *ancestor;
    for (ancestor = g_state.held_ancestors; ancestor != NULL;
         ancestor = ancestor->next) {
        ULONGLONG volume = 0ULL;
        FILE_ID_128 id;
        wchar_t *final_path = NULL;
        int matches = handle_identity(
                ancestor->handle, &volume, &id, &final_path) &&
            same_file_identity(
                volume, &id, ancestor->volume_serial, &ancestor->file_id) &&
            _wcsicmp(final_path, ancestor->final_path) == 0;
        free(final_path);
        if (!matches) {
            return 0;
        }
    }
    return 1;
}

static int verify_retained_row_identity(RetainedRow *row) {
    ULONGLONG volume = 0ULL;
    FILE_ID_128 id;
    wchar_t *final_path = NULL;
    unsigned char hash[32];
    uint64_t bytes = 0U;
    int matches = row != NULL && recheck_ancestor_chain() &&
        handle_identity(row->handle, &volume, &id, &final_path) &&
        same_file_identity(
            volume, &id, row->volume_serial, &row->file_id) &&
        _wcsicmp(final_path, row->final_path) == 0 &&
        sha256_handle(row->handle, hash, &bytes) &&
        bytes == row->expected_bytes &&
        constant_time_equal32(hash, row->expected_sha256);
    secure_zero(hash, sizeof(hash));
    free(final_path);
    return matches;
}

static wchar_t *launch_path_from_retained_handle(RetainedRow *row) {
    wchar_t final_probe[32768];
    DWORD final_length;
    if (!verify_retained_row_identity(row)) {
        return NULL;
    }
    final_length = GetFinalPathNameByHandleW(
        row->handle, final_probe, 32768U,
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (final_length == 0U || final_length >= 32768U) {
        return NULL;
    }
    return duplicate_wide(row->final_path);
}

static int verify_loaded_python_runtime(void) {
    RetainedRow *row = find_row_by_label("python_runtime_dll", NULL);
    HMODULE module = GetModuleHandleW(L"python314.dll");
    wchar_t module_probe[32768];
    DWORD length = module != NULL ?
        GetModuleFileNameW(module, module_probe, 32768U) : 0U;
    return row != NULL && length != 0U && length < 32768U &&
        _wcsicmp(module_probe, row->final_path) == 0 &&
        verify_retained_row_identity(row);
}

static int secure_load_embedded_python(void) {
    RetainedRow *row = find_row_by_label("python_runtime_dll", NULL);
    HMODULE module;
    if (row == NULL || !verify_retained_row_identity(row) ||
        !SetDefaultDllDirectories(
            LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS)) {
        return 0;
    }
    module = LoadLibraryExW(
        row->final_path, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    return module != NULL && verify_loaded_python_runtime();
}

static void *verified_python_export_address(const char *name) {
    HMODULE module = GetModuleHandleW(L"python314.dll");
    FARPROC procedure;
    void *address = NULL;
    if (module == NULL || !verify_loaded_python_runtime()) {
        return NULL;
    }
    procedure = GetProcAddress(module, name);
    if (procedure == NULL || sizeof(procedure) != sizeof(address)) {
        return NULL;
    }
    memcpy(&address, &procedure, sizeof(address));
    return address;
}

static PyObject *verified_python_exception(const char *name) {
    PyObject **slot = (PyObject **)verified_python_export_address(name);
    return slot != NULL ? *slot : NULL;
}

static PyObject *verified_python_singleton(const char *name) {
    return (PyObject *)verified_python_export_address(name);
}

static int verified_python_exact_type(PyObject *object, const char *name) {
    PyTypeObject *expected =
        (PyTypeObject *)verified_python_export_address(name);
    return object != NULL && expected != NULL && Py_TYPE(object) == expected;
}

/* Python's Windows import library exposes these as data symbols.  Resolving
 * them only after the exact retained DLL has been explicitly loaded keeps
 * /DELAYLOAD real instead of allowing the OS loader to select ambient data
 * imports before the retained graph and runtime identity gates. */
#undef Py_None
#undef Py_True
#undef Py_False
#undef Py_RETURN_NONE
#undef PyExc_ImportError
#undef PyExc_OverflowError
#undef PyExc_RuntimeError
#undef PyExc_TypeError
#undef PyExc_ValueError
#undef PyLong_CheckExact
#undef PyUnicode_CheckExact
#undef PyDict_CheckExact
#undef PyList_CheckExact
#undef PyTuple_CheckExact
#undef PyBool_Check
#undef PyFloat_Check
#undef PySet_CheckExact
#undef PyFunction_Check
#define Py_None (verified_python_singleton("_Py_NoneStruct"))
#define Py_True (verified_python_singleton("_Py_TrueStruct"))
#define Py_False (verified_python_singleton("_Py_FalseStruct"))
#define Py_RETURN_NONE return Py_NewRef(Py_None)
#define PyExc_ImportError (verified_python_exception("PyExc_ImportError"))
#define PyExc_OverflowError (verified_python_exception("PyExc_OverflowError"))
#define PyExc_RuntimeError (verified_python_exception("PyExc_RuntimeError"))
#define PyExc_TypeError (verified_python_exception("PyExc_TypeError"))
#define PyExc_ValueError (verified_python_exception("PyExc_ValueError"))
#define PyLong_CheckExact(object) \
    verified_python_exact_type((object), "PyLong_Type")
#define PyUnicode_CheckExact(object) \
    verified_python_exact_type((object), "PyUnicode_Type")
#define PyDict_CheckExact(object) \
    verified_python_exact_type((object), "PyDict_Type")
#define PyList_CheckExact(object) \
    verified_python_exact_type((object), "PyList_Type")
#define PyTuple_CheckExact(object) \
    verified_python_exact_type((object), "PyTuple_Type")
#define PyBool_Check(object) \
    verified_python_exact_type((object), "PyBool_Type")
#define PyFloat_Check(object) \
    verified_python_exact_type((object), "PyFloat_Type")
#define PySet_CheckExact(object) \
    verified_python_exact_type((object), "PySet_Type")
#define PyFunction_Check(object) \
    verified_python_exact_type((object), "PyFunction_Type")

static int parse_and_verify_exact_audit(
    const ByteBuffer *audit, char *error, size_t error_size
) {
    static const char *allowed_keys[] = {
        "schema", "authoritative_decision", "decision", "exact_subjects",
        "contract", "checkpoint", "retained_manifest", "native_launcher",
        "native_launcher_source", "static_test", "bootstrap", "controller",
        "wrapper"
    };
    static const char *subject_names[] = {
        "contract", "checkpoint", "retained_manifest", "native_launcher",
        "native_launcher_source", "static_test", "bootstrap", "controller",
        "wrapper"
    };
    static const char *row_labels[] = {
        "execution_contract", "v3r6_checkpoint", NULL, "native_launcher",
        "native_launcher_source", "v3r6_static_test", "trusted_bootstrap",
        "parent_controller", "execution_wrapper"
    };
    size_t key_counts[sizeof(allowed_keys) / sizeof(allowed_keys[0])];
    size_t index = 0U;
    char *text;
    memset(key_counts, 0, sizeof(key_counts));
    if (audit == NULL || audit->data == NULL || audit->size == 0U ||
        audit->size > MAX_MANIFEST_BYTES ||
        memchr(audit->data, '\0', audit->size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "exact_audit_empty_oversize_or_nul");
        return 0;
    }
    text = duplicate_bytes_as_cstr((const char *)audit->data, audit->size);
    if (text == NULL) {
        _snprintf_s(error, error_size, _TRUNCATE, "exact_audit_allocation_failed");
        return 0;
    }
    while (index < audit->size) {
        if (text[index] == '"') {
            size_t start = ++index;
            size_t end;
            size_t probe;
            int allowed = 0;
            while (index < audit->size && text[index] != '"') {
                if (text[index] == '\\' ||
                    (unsigned char)text[index] < 0x20U) {
                    free(text);
                    _snprintf_s(error, error_size, _TRUNCATE,
                        "exact_audit_escape_or_control_refused");
                    return 0;
                }
                ++index;
            }
            if (index >= audit->size) {
                free(text);
                _snprintf_s(error, error_size, _TRUNCATE,
                    "exact_audit_unterminated_string");
                return 0;
            }
            end = index++;
            probe = index;
            while (probe < audit->size &&
                   (text[probe] == ' ' || text[probe] == '\t' ||
                    text[probe] == '\r' || text[probe] == '\n')) {
                ++probe;
            }
            if (probe < audit->size && text[probe] == ':') {
                size_t key_index;
                for (key_index = 0U;
                     key_index < sizeof(allowed_keys) / sizeof(allowed_keys[0]);
                     ++key_index) {
                    size_t length = strlen(allowed_keys[key_index]);
                    if (end - start == length &&
                        memcmp(text + start, allowed_keys[key_index], length) == 0) {
                        allowed = 1;
                        ++key_counts[key_index];
                        if (key_counts[key_index] > 1U) {
                            free(text);
                            _snprintf_s(error, error_size, _TRUNCATE,
                                "duplicate_json_key:%s", allowed_keys[key_index]);
                            return 0;
                        }
                        break;
                    }
                }
                if (!allowed) {
                    free(text);
                    _snprintf_s(error, error_size, _TRUNCATE,
                        "unknown_json_key");
                    return 0;
                }
            }
        } else {
            ++index;
        }
    }
    for (index = 0U; index < sizeof(allowed_keys) / sizeof(allowed_keys[0]);
         ++index) {
        if (key_counts[index] != 1U) {
            free(text);
            _snprintf_s(error, error_size, _TRUNCATE,
                "exact_audit_required_key_missing:%s", allowed_keys[index]);
            return 0;
        }
    }
    if (strstr(text,
            "\"schema\":\"kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v3r6\"") == NULL ||
        strstr(text,
            "\"authoritative_decision\":{\"decision\":\"ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY\"}") == NULL ||
        strstr(text, "\"exact_subjects\":{") == NULL) {
        free(text);
        _snprintf_s(error, error_size, _TRUNCATE,
            "exact_audit_schema_or_authoritative_decision_drift");
        return 0;
    }
    for (index = 0U; index < sizeof(subject_names) / sizeof(subject_names[0]);
         ++index) {
        char needle[160];
        const char *value;
        unsigned char parsed[32];
        const unsigned char *expected;
        RetainedRow *row = row_labels[index] != NULL
            ? find_row_by_label(row_labels[index], NULL) : NULL;
        _snprintf_s(needle, sizeof(needle), _TRUNCATE,
            "\"%s\":\"", subject_names[index]);
        value = strstr(text, needle);
        value = value != NULL ? value + strlen(needle) : NULL;
        expected = row_labels[index] == NULL
            ? g_state.manifest_sha256
            : (row != NULL ? row->expected_sha256 : NULL);
        if (value == NULL || expected == NULL || strlen(value) < 65U ||
            value[64] != '"' || !parse_hex64(value, parsed) ||
            !constant_time_equal32(parsed, expected)) {
            secure_zero(parsed, sizeof(parsed));
            free(text);
            _snprintf_s(error, error_size, _TRUNCATE,
                "exact_audit_subject_hash_mismatch:%s", subject_names[index]);
            return 0;
        }
        secure_zero(parsed, sizeof(parsed));
    }
    {
        char subject_hex[9][65];
        char canonical[1536];
        int written;
        for (index = 0U;
             index < sizeof(subject_names) / sizeof(subject_names[0]);
             ++index) {
            RetainedRow *row = row_labels[index] != NULL
                ? find_row_by_label(row_labels[index], NULL) : NULL;
            const unsigned char *expected = row_labels[index] == NULL
                ? g_state.manifest_sha256
                : (row != NULL ? row->expected_sha256 : NULL);
            if (expected == NULL) {
                secure_zero(subject_hex, sizeof(subject_hex));
                free(text);
                _snprintf_s(error, error_size, _TRUNCATE,
                    "exact_audit_canonical_subject_missing");
                return 0;
            }
            hex_encode32(expected, subject_hex[index]);
        }
        written = _snprintf_s(
            canonical, sizeof(canonical), _TRUNCATE,
            "{\"schema\":\"kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v3r6\","
            "\"authoritative_decision\":{\"decision\":\"ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY\"},"
            "\"exact_subjects\":{\"contract\":\"%s\",\"checkpoint\":\"%s\","
            "\"retained_manifest\":\"%s\",\"native_launcher\":\"%s\","
            "\"native_launcher_source\":\"%s\",\"static_test\":\"%s\","
            "\"bootstrap\":\"%s\",\"controller\":\"%s\",\"wrapper\":\"%s\"}}",
            subject_hex[0], subject_hex[1], subject_hex[2], subject_hex[3],
            subject_hex[4], subject_hex[5], subject_hex[6], subject_hex[7],
            subject_hex[8]);
        secure_zero(subject_hex, sizeof(subject_hex));
        if (written < 0 || (size_t)written != audit->size ||
            memcmp(canonical, audit->data, audit->size) != 0) {
            secure_zero(canonical, sizeof(canonical));
            free(text);
            _snprintf_s(error, error_size, _TRUNCATE,
                "exact_audit_noncanonical_or_structurally_invalid");
            return 0;
        }
        secure_zero(canonical, sizeof(canonical));
    }
    free(text);
    return 1;
}

static void cleanup_state(void) {
    size_t index;
    HeldOutput *held;
    HeldAncestor *ancestor;
    if (g_state.staged_outcome_frame != NULL) {
        secure_zero(
            g_state.staged_outcome_frame,
            g_state.staged_outcome_frame_size);
        free(g_state.staged_outcome_frame);
        g_state.staged_outcome_frame = NULL;
        g_state.staged_outcome_frame_size = 0U;
    }
    if (g_state.outcome_handle != NULL &&
        g_state.outcome_handle != INVALID_HANDLE_VALUE) {
        CloseHandle(g_state.outcome_handle);
        g_state.outcome_handle = INVALID_HANDLE_VALUE;
    }
    held = g_state.held_outputs;
    while (held != NULL) {
        HeldOutput *next = held->next;
        if (held->handle != NULL && held->handle != INVALID_HANDLE_VALUE) {
            CloseHandle(held->handle);
        }
        free(held->path);
        free(held->final_path);
        free(held);
        held = next;
    }
    ancestor = g_state.held_ancestors;
    while (ancestor != NULL) {
        HeldAncestor *next = ancestor->next;
        if (ancestor->handle != NULL &&
            ancestor->handle != INVALID_HANDLE_VALUE) {
            CloseHandle(ancestor->handle);
        }
        free(ancestor->requested_path);
        free(ancestor->final_path);
        free(ancestor);
        ancestor = next;
    }
    if (g_state.audit_handle != NULL &&
        g_state.audit_handle != INVALID_HANDLE_VALUE) {
        CloseHandle(g_state.audit_handle);
    }
    for (index = 0U; index < g_state.row_count; ++index) {
        if (g_state.rows[index].handle != NULL &&
            g_state.rows[index].handle != INVALID_HANDLE_VALUE) {
            CloseHandle(g_state.rows[index].handle);
        }
        free(g_state.rows[index].label_utf8);
        free(g_state.rows[index].manifest_path_utf8);
        free(g_state.rows[index].path);
        free(g_state.rows[index].final_path);
    }
    free(g_state.rows);
    if (g_state.manifest_handle != NULL &&
        g_state.manifest_handle != INVALID_HANDLE_VALUE) {
        CloseHandle(g_state.manifest_handle);
    }
    free(g_state.self_path);
    free(g_state.project_root);
    free(g_state.manifest_path);
    free(g_state.audit_path);
    free(g_state.manifest_final_path);
    free(g_state.audit_final_path);
    free(g_state.outcome_path);
    free(g_state.output_root);
    if (g_state.lifecycle_mutex != NULL &&
        g_state.lifecycle_mutex != INVALID_HANDLE_VALUE) {
        CloseHandle(g_state.lifecycle_mutex);
    }
    if (g_state.mutex_initialized) {
        DeleteCriticalSection(&g_state.mutex);
    }
    secure_zero(&g_state, sizeof(g_state));
}

static int initialize_locked_state(
    const wchar_t *project_root_arg,
    const wchar_t *manifest_path_arg,
    const char *manifest_sha_arg,
    const char *contract_sha_arg,
    const wchar_t *audit_path_arg,
    const char *audit_sha_arg,
    const char *bootstrap_label,
    char *error,
    size_t error_size
) {
    ByteBuffer manifest = {0};
    ByteBuffer audit = {0};
    uint64_t actual_bytes = 0U;
    unsigned char actual_hash[32];
    RetainedRow *bootstrap_row;
    memset(&g_state, 0, sizeof(g_state));
    g_state.manifest_handle = INVALID_HANDLE_VALUE;
    g_state.audit_handle = INVALID_HANDLE_VALUE;
    g_state.outcome_handle = INVALID_HANDLE_VALUE;
    g_state.bootstrap_index = SIZE_MAX;
    g_state.contract_index = SIZE_MAX;
    g_state.next_run_number = 1;
    g_state.process_id = GetCurrentProcessId();
    g_state.main_os_thread_id = GetCurrentThreadId();
    g_state.lifecycle_mutex = CreateMutexW(NULL, FALSE, NULL);
    if (g_state.lifecycle_mutex == NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "native_lifecycle_mutex_create_failed:winerror=%lu",
            (unsigned long)GetLastError());
        return 0;
    }
    if (!parse_hex64(manifest_sha_arg, g_state.expected_manifest_sha256) ||
        !parse_hex64(contract_sha_arg, g_state.expected_contract_sha256) ||
        !parse_hex64(audit_sha_arg, g_state.expected_audit_sha256) ||
        !valid_manifest_label(bootstrap_label)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "invalid_out_of_band_digest_or_bootstrap_label");
        return 0;
    }
    g_state.self_path = get_module_path(NULL);
    g_state.project_root = canonical_full_path(project_root_arg);
    g_state.manifest_path = canonical_full_path(manifest_path_arg);
    if (path_is_absolute(audit_path_arg)) {
        g_state.audit_path = canonical_full_path(audit_path_arg);
    } else {
        g_state.audit_path = join_project_relative(audit_path_arg);
    }
    if (g_state.self_path == NULL || g_state.project_root == NULL ||
        g_state.manifest_path == NULL || g_state.audit_path == NULL ||
        wcsncmp(g_state.project_root, L"\\\\", 2U) == 0 ||
        wcsncmp(g_state.manifest_path, L"\\\\", 2U) == 0 ||
        wcsncmp(g_state.audit_path, L"\\\\", 2U) == 0 ||
        path_has_reparse_component(g_state.project_root) ||
        path_has_reparse_component(g_state.manifest_path) ||
        path_has_reparse_component(g_state.audit_path)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "canonical_nonreparse_startup_paths_required");
        return 0;
    }
    {
        DWORD root_attributes = GetFileAttributesW(g_state.project_root);
        if (root_attributes == INVALID_FILE_ATTRIBUTES ||
            (root_attributes & FILE_ATTRIBUTE_DIRECTORY) == 0U) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "project_root_not_directory");
            return 0;
        }
    }
    if (!hold_every_path_ancestor(g_state.project_root) ||
        !hold_every_path_ancestor(g_state.self_path) ||
        !hold_every_path_ancestor(g_state.manifest_path) ||
        !hold_every_path_ancestor(g_state.audit_path)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "startup_path_ancestor_hold_failed");
        return 0;
    }
    g_state.manifest_handle = open_locked_read_file(g_state.manifest_path);
    if (g_state.manifest_handle == INVALID_HANDLE_VALUE ||
        !final_handle_matches_path(
            g_state.manifest_handle, g_state.manifest_path,
            &g_state.manifest_volume_serial, &g_state.manifest_file_id,
            &g_state.manifest_final_path) ||
        !sha256_handle(g_state.manifest_handle, actual_hash, &actual_bytes) ||
        !constant_time_equal32(actual_hash, g_state.expected_manifest_sha256) ||
        actual_bytes > MAX_MANIFEST_BYTES) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "retained_manifest_lock_or_hash_failed");
        secure_zero(actual_hash, sizeof(actual_hash));
        return 0;
    }
    memcpy(g_state.manifest_sha256, actual_hash, sizeof(actual_hash));
    g_state.manifest_bytes = actual_bytes;
    secure_zero(actual_hash, sizeof(actual_hash));
    if (!read_handle_all(
            g_state.manifest_handle, actual_bytes, MAX_MANIFEST_BYTES, &manifest) ||
        !parse_manifest_rows(&manifest, error, error_size)) {
        free(manifest.data);
        return 0;
    }
    free(manifest.data);
    if (!lock_and_verify_manifest_rows(error, error_size)) {
        return 0;
    }
    bootstrap_row = find_row_by_label("python_runtime_dll", NULL);
    if (bootstrap_row == NULL ||
        !verify_retained_row_identity(bootstrap_row) ||
        !secure_load_embedded_python()) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "python_runtime_dll_secure_load_or_identity_mismatch");
        return 0;
    }
    g_state.lifecycle = GRAPH_LOCKED;
    bootstrap_row = find_row_by_label(bootstrap_label, &g_state.bootstrap_index);
    if (bootstrap_row == NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "exact_bootstrap_label_missing");
        return 0;
    }
    if (_wcsicmp(g_state.audit_path, g_state.manifest_path) == 0 ||
        find_row_by_path(g_state.audit_path, NULL) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "fresh_audit_must_be_outside_manifest_graph");
        return 0;
    }
    g_state.audit_handle = open_locked_read_file(g_state.audit_path);
    if (g_state.audit_handle == INVALID_HANDLE_VALUE ||
        !final_handle_matches_path(
            g_state.audit_handle, g_state.audit_path,
            &g_state.audit_volume_serial, &g_state.audit_file_id,
            &g_state.audit_final_path) ||
        !sha256_handle(g_state.audit_handle, actual_hash, &actual_bytes) ||
        !constant_time_equal32(actual_hash, g_state.expected_audit_sha256)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "fresh_audit_lock_or_hash_failed");
        secure_zero(actual_hash, sizeof(actual_hash));
        return 0;
    }
    memcpy(g_state.audit_sha256, actual_hash, sizeof(actual_hash));
    g_state.audit_bytes = actual_bytes;
    if (actual_bytes > MAX_MANIFEST_BYTES ||
        !read_handle_all(
            g_state.audit_handle, actual_bytes, MAX_MANIFEST_BYTES, &audit) ||
        !parse_and_verify_exact_audit(&audit, error, error_size)) {
        secure_zero(audit.data, audit.size);
        free(audit.data);
        secure_zero(actual_hash, sizeof(actual_hash));
        return 0;
    }
    secure_zero(audit.data, audit.size);
    free(audit.data);
    g_state.lifecycle = AUDIT_ACCEPTED;
    secure_zero(actual_hash, sizeof(actual_hash));
    InitializeCriticalSection(&g_state.mutex);
    g_state.mutex_initialized = 1;
    g_state.initialized = 1;
    g_state.lifecycle = ARMED;
    return 1;
}

static PyObject *broker_error(const char *message) {
    PyErr_SetString(PyExc_RuntimeError, message);
    return NULL;
}

static int require_main_os_thread(const char *operation) {
    if (GetCurrentThreadId() != g_state.main_os_thread_id) {
        PyErr_Format(PyExc_RuntimeError,
            "native_broker_non_main_os_thread_refused:%s", operation);
        return 0;
    }
    return 1;
}

static int acquire_lifecycle_mutex(const char *operation) {
    DWORD wait_result;
    if (!require_main_os_thread(operation) || g_state.lifecycle_mutex == NULL ||
        g_state.lifecycle_mutex == INVALID_HANDLE_VALUE) {
        return 0;
    }
    wait_result = WaitForSingleObject(g_state.lifecycle_mutex, 0U);
    if (wait_result != WAIT_OBJECT_0) {
        PyErr_Format(PyExc_RuntimeError,
            "native_broker_lifecycle_mutex_busy:%s:wait=%lu", operation,
            (unsigned long)wait_result);
        return 0;
    }
    return 1;
}

static void release_lifecycle_mutex(void) {
    if (g_state.lifecycle_mutex != NULL &&
        g_state.lifecycle_mutex != INVALID_HANDLE_VALUE) {
        (void)ReleaseMutex(g_state.lifecycle_mutex);
    }
}

static int require_claimed(const char *operation) {
    if (!require_main_os_thread(operation) || !g_state.initialized ||
        !g_state.claimed || g_state.finished) {
        PyErr_Format(PyExc_RuntimeError,
            "native_broker_state_refused:%s", operation);
        return 0;
    }
    return 1;
}

static int all_jobs_quiescent(void) {
    return InterlockedCompareExchange(&g_state.active_child_count, 0L, 0L) == 0L;
}

static int require_all_jobs_quiescent(const char *operation) {
    if (!all_jobs_quiescent()) {
        PyErr_Format(PyExc_RuntimeError,
            "native_all_jobs_quiescent_required:%s", operation);
        return 0;
    }
    return 1;
}

static int py_unicode_to_utf8_exact(
    PyObject *object, const char **value, Py_ssize_t *length
) {
    if (!PyUnicode_CheckExact(object)) {
        PyErr_SetString(PyExc_TypeError, "exact_str_required");
        return 0;
    }
    *value = PyUnicode_AsUTF8AndSize(object, length);
    return *value != NULL;
}

static wchar_t *py_unicode_to_wide_exact(PyObject *object) {
    Py_ssize_t size = 0;
    wchar_t *python_value;
    wchar_t *copy;
    if (!PyUnicode_CheckExact(object)) {
        PyErr_SetString(PyExc_TypeError, "exact_str_required");
        return NULL;
    }
    python_value = PyUnicode_AsWideCharString(object, &size);
    if (python_value == NULL) {
        return NULL;
    }
    if (size < 0 || wmemchr(python_value, L'\0', (size_t)size) != NULL) {
        PyMem_Free(python_value);
        PyErr_SetString(PyExc_ValueError, "embedded_nul_refused");
        return NULL;
    }
    copy = duplicate_wide(python_value);
    PyMem_Free(python_value);
    if (copy == NULL) {
        PyErr_NoMemory();
    }
    return copy;
}

static PyObject *py_claim_once(PyObject *self, PyObject *args) {
    PyObject *manifest_object;
    PyObject *contract_object;
    PyObject *audit_object;
    const char *manifest;
    const char *contract;
    const char *audit;
    Py_ssize_t manifest_length;
    Py_ssize_t contract_length;
    Py_ssize_t audit_length;
    unsigned char manifest_hash[32];
    unsigned char contract_hash[32];
    unsigned char audit_hash[32];
    (void)self;
    if (!require_main_os_thread("claim_once") ||
        !acquire_lifecycle_mutex("claim_once")) {
        return NULL;
    }
    if (!PyArg_UnpackTuple(
            args, "claim_once", 3, 3, &manifest_object, &contract_object,
            &audit_object)) {
        release_lifecycle_mutex();
        return NULL;
    }
    EnterCriticalSection(&g_state.mutex);
    if (g_state.claim_attempted) {
        LeaveCriticalSection(&g_state.mutex);
        release_lifecycle_mutex();
        return broker_error("native_broker_claim_already_attempted");
    }
    g_state.claim_attempted = 1;
    g_state.lifecycle = CONSUMED;
    LeaveCriticalSection(&g_state.mutex);
    if (!py_unicode_to_utf8_exact(
            manifest_object, &manifest, &manifest_length) ||
        !py_unicode_to_utf8_exact(
            contract_object, &contract, &contract_length) ||
        !py_unicode_to_utf8_exact(audit_object, &audit, &audit_length)) {
        release_lifecycle_mutex();
        return NULL;
    }
    if (manifest_length != 64 || contract_length != 64 || audit_length != 64 ||
        !parse_hex64(manifest, manifest_hash) ||
        !parse_hex64(contract, contract_hash) ||
        !parse_hex64(audit, audit_hash) ||
        !constant_time_equal32(manifest_hash, g_state.manifest_sha256) ||
        !constant_time_equal32(
            contract_hash, g_state.rows[g_state.contract_index].expected_sha256) ||
        !constant_time_equal32(audit_hash, g_state.audit_sha256) ||
        !constant_time_equal32(manifest_hash, g_state.expected_manifest_sha256) ||
        !constant_time_equal32(contract_hash, g_state.expected_contract_sha256) ||
        !constant_time_equal32(audit_hash, g_state.expected_audit_sha256)) {
        secure_zero(manifest_hash, sizeof(manifest_hash));
        secure_zero(contract_hash, sizeof(contract_hash));
        secure_zero(audit_hash, sizeof(audit_hash));
        release_lifecycle_mutex();
        return broker_error("native_broker_out_of_band_claim_mismatch");
    }
    secure_zero(manifest_hash, sizeof(manifest_hash));
    secure_zero(contract_hash, sizeof(contract_hash));
    secure_zero(audit_hash, sizeof(audit_hash));
    EnterCriticalSection(&g_state.mutex);
    g_state.claimed = 1;
    LeaveCriticalSection(&g_state.mutex);
    release_lifecycle_mutex();
    Py_RETURN_NONE;
}

static PyObject *identity_dict(
    const wchar_t *path, uint64_t bytes, const unsigned char sha256[32]
) {
    PyObject *result = NULL;
    PyObject *path_object = NULL;
    PyObject *bytes_object = NULL;
    PyObject *hash_object = NULL;
    char hash_hex[65];
    path_object = PyUnicode_FromWideChar(path, -1);
    bytes_object = PyLong_FromUnsignedLongLong(bytes);
    hex_encode32(sha256, hash_hex);
    hash_object = PyUnicode_FromStringAndSize(hash_hex, 64);
    if (path_object == NULL || bytes_object == NULL || hash_object == NULL) {
        goto cleanup;
    }
    result = PyDict_New();
    if (result == NULL ||
        PyDict_SetItemString(result, "path", path_object) < 0 ||
        PyDict_SetItemString(result, "bytes", bytes_object) < 0 ||
        PyDict_SetItemString(result, "sha256", hash_object) < 0) {
        Py_CLEAR(result);
    }
cleanup:
    Py_XDECREF(path_object);
    Py_XDECREF(bytes_object);
    Py_XDECREF(hash_object);
    return result;
}

static PyObject *py_manifest_identity(PyObject *self, PyObject *args) {
    (void)self;
    if (!PyArg_ParseTuple(args, ":manifest_identity")) {
        return NULL;
    }
    if (!require_claimed("manifest_identity")) {
        return NULL;
    }
    return identity_dict(
        g_state.manifest_path, g_state.manifest_bytes, g_state.manifest_sha256
    );
}

static PyObject *py_audit_identity(PyObject *self, PyObject *args) {
    (void)self;
    if (!PyArg_ParseTuple(args, ":audit_identity")) {
        return NULL;
    }
    if (!require_claimed("audit_identity")) {
        return NULL;
    }
    return identity_dict(
        g_state.audit_path, g_state.audit_bytes, g_state.audit_sha256
    );
}

static PyObject *py_audit_bytes(PyObject *self, PyObject *args) {
    ByteBuffer value = {0};
    PyObject *result;
    (void)self;
    if (!PyArg_ParseTuple(args, ":audit_bytes") ||
        !require_claimed("audit_bytes")) {
        return NULL;
    }
    if (!read_handle_all(
            g_state.audit_handle, g_state.audit_bytes,
            MAX_LOCKED_READ_BYTES, &value)) {
        return broker_error("locked_audit_read_failed_or_too_large");
    }
    result = PyBytes_FromStringAndSize(
        (const char *)value.data, (Py_ssize_t)value.size
    );
    secure_zero(value.data, value.size);
    free(value.data);
    return result;
}

static PyObject *py_broker_process_id(PyObject *self, PyObject *args) {
    (void)self;
    if (!PyArg_ParseTuple(args, ":broker_process_id")) {
        return NULL;
    }
    if (!require_claimed("broker_process_id")) {
        return NULL;
    }
    return PyLong_FromUnsignedLong((unsigned long)g_state.process_id);
}

static PyObject *py_claim_nonce_bundle(PyObject *self, PyObject *args) {
    PyObject *result;
    (void)self;
    if (!PyArg_ParseTuple(args, ":claim_nonce_bundle") ||
        !require_main_os_thread("claim_nonce_bundle") ||
        !require_claimed("claim_nonce_bundle")) {
        return NULL;
    }
    if (g_state.nonces_claimed || g_state.next_run_number != 1 ||
        !generate_nonce_hex(g_state.pair_nonce) ||
        !generate_nonce_hex(g_state.run_nonce_1) ||
        !generate_nonce_hex(g_state.run_nonce_2) ||
        strcmp(g_state.pair_nonce, g_state.run_nonce_1) == 0 ||
        strcmp(g_state.pair_nonce, g_state.run_nonce_2) == 0 ||
        strcmp(g_state.run_nonce_1, g_state.run_nonce_2) == 0) {
        secure_zero(g_state.pair_nonce, sizeof(g_state.pair_nonce));
        secure_zero(g_state.run_nonce_1, sizeof(g_state.run_nonce_1));
        secure_zero(g_state.run_nonce_2, sizeof(g_state.run_nonce_2));
        return broker_error("native_nonce_bundle_generation_or_reuse_refused");
    }
    g_state.nonces_claimed = 1;
    result = Py_BuildValue(
        "(sss)", g_state.pair_nonce, g_state.run_nonce_1,
        g_state.run_nonce_2
    );
    return result;
}

static PyObject *py_locked_rows(PyObject *self, PyObject *args) {
    PyObject *result;
    size_t index;
    char hash_hex[65];
    (void)self;
    if (!PyArg_ParseTuple(args, ":locked_rows")) {
        return NULL;
    }
    if (!require_claimed("locked_rows")) {
        return NULL;
    }
    result = PyTuple_New((Py_ssize_t)g_state.row_count + 1);
    if (result == NULL) {
        return NULL;
    }
    for (index = 0U; index < g_state.row_count; ++index) {
        RetainedRow *row = &g_state.rows[index];
        PyObject *entry;
        PyObject *label;
        PyObject *path;
        PyObject *bytes;
        PyObject *hash;
        hex_encode32(row->expected_sha256, hash_hex);
        label = PyUnicode_FromString(row->label_utf8);
        path = PyUnicode_FromString(row->manifest_path_utf8);
        bytes = PyLong_FromUnsignedLongLong(row->expected_bytes);
        hash = PyUnicode_FromStringAndSize(hash_hex, 64);
        entry = (label != NULL && path != NULL && bytes != NULL && hash != NULL)
            ? PyTuple_Pack(4, label, path, bytes, hash) : NULL;
        Py_XDECREF(label);
        Py_XDECREF(path);
        Py_XDECREF(bytes);
        Py_XDECREF(hash);
        if (entry == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, (Py_ssize_t)index, entry);
    }
    {
        PyObject *entry;
        PyObject *label;
        PyObject *path;
        PyObject *bytes;
        PyObject *hash;
        hex_encode32(g_state.audit_sha256, hash_hex);
        label = PyUnicode_FromString("accepted_controller_audit");
        path = PyUnicode_FromWideChar(g_state.audit_path, -1);
        bytes = PyLong_FromUnsignedLongLong(g_state.audit_bytes);
        hash = PyUnicode_FromStringAndSize(hash_hex, 64);
        entry = (label != NULL && path != NULL && bytes != NULL && hash != NULL)
            ? PyTuple_Pack(4, label, path, bytes, hash) : NULL;
        Py_XDECREF(label);
        Py_XDECREF(path);
        Py_XDECREF(bytes);
        Py_XDECREF(hash);
        if (entry == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, (Py_ssize_t)g_state.row_count, entry);
    }
    return result;
}

static PyObject *py_locked_read(PyObject *self, PyObject *args) {
    PyObject *key_object;
    const char *key_utf8;
    Py_ssize_t key_length;
    RetainedRow *row = NULL;
    HANDLE handle = INVALID_HANDLE_VALUE;
    uint64_t expected_bytes = 0U;
    ByteBuffer value = {0};
    wchar_t *wide_key = NULL;
    PyObject *result;
    (void)self;
    if (!PyArg_UnpackTuple(args, "locked_read", 1, 1, &key_object) ||
        !require_claimed("locked_read") ||
        !py_unicode_to_utf8_exact(key_object, &key_utf8, &key_length)) {
        return NULL;
    }
    if (key_length > 0 && key_length <= 128) {
        char *label = duplicate_bytes_as_cstr(key_utf8, (size_t)key_length);
        if (label == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
        row = find_row_by_label(label, NULL);
        if (row == NULL && strcmp(label, "accepted_controller_audit") == 0) {
            handle = g_state.audit_handle;
            expected_bytes = g_state.audit_bytes;
        }
        free(label);
    }
    if (row == NULL && handle == INVALID_HANDLE_VALUE) {
        wide_key = py_unicode_to_wide_exact(key_object);
        if (wide_key == NULL) {
            return NULL;
        }
        row = find_row_by_path(wide_key, NULL);
        if (row == NULL) {
            wchar_t *canonical = path_is_absolute(wide_key)
                ? canonical_full_path(wide_key) : join_project_relative(wide_key);
            if (canonical != NULL && _wcsicmp(canonical, g_state.audit_path) == 0) {
                handle = g_state.audit_handle;
                expected_bytes = g_state.audit_bytes;
            }
            free(canonical);
        }
        free(wide_key);
    }
    if (row != NULL) {
        handle = row->handle;
        expected_bytes = row->expected_bytes;
    }
    if (handle == INVALID_HANDLE_VALUE) {
        return broker_error("locked_read_unknown_or_ambiguous_identity");
    }
    if (!read_handle_all(
            handle, expected_bytes, MAX_LOCKED_READ_BYTES, &value)) {
        return broker_error("locked_read_failed_or_too_large");
    }
    result = PyBytes_FromStringAndSize(
        (const char *)value.data, (Py_ssize_t)value.size
    );
    secure_zero(value.data, value.size);
    free(value.data);
    return result;
}

static int write_all_handle(HANDLE handle, const unsigned char *data, size_t size) {
    size_t offset = 0U;
    while (offset < size) {
        DWORD request = (DWORD)((size - offset) > UINT32_MAX
            ? UINT32_MAX : (size - offset));
        DWORD written = 0U;
        if (!WriteFile(handle, data + offset, request, &written, NULL) ||
            written == 0U) {
            return 0;
        }
        offset += written;
    }
    return 1;
}

static int sha256_memory(
    const unsigned char *data, size_t size, unsigned char output[32]
);
static void write_be32(unsigned char *target, uint32_t value);
static void write_be64(unsigned char *target, uint64_t value);
static void json_escape_ascii(
    const char *input, char *output, size_t output_size
);
static PyObject *encode_receipt_frame_object(PyObject *payload);
static int dict_has_exact_keys(
    PyObject *value, const char *const *keys, size_t key_count
);
static int exact_unicode_equals_ascii(PyObject *value, const char *expected);

static void copy_evidence_name_ascii(
    const wchar_t *name, char output[260]
) {
    size_t index = 0U;
    output[0] = '\0';
    if (name == NULL) {
        return;
    }
    while (name[index] != L'\0' && index + 1U < 260U) {
        if (name[index] < 0x20 || name[index] > 0x7e) {
            output[0] = '\0';
            return;
        }
        output[index] = (char)name[index];
        ++index;
    }
    if (name[index] != L'\0') {
        output[0] = '\0';
        return;
    }
    output[index] = '\0';
}

static int expected_evidence_name_at(LONG index, const char *name) {
    static const char *const expected_names[8] = {
        "run_01_raw_frame.bin", "run_01_stdout.log",
        "run_01_stderr.log", "run_01_receipt.bin",
        "run_02_raw_frame.bin", "run_02_stdout.log",
        "run_02_stderr.log", "run_02_receipt.bin"
    };
    return index >= 0L && index < 8L && name != NULL &&
        strcmp(name, expected_names[index]) == 0;
}

static void record_partial_evidence(
    HANDLE handle, const wchar_t *relative_name, uint64_t requested_bytes,
    const char *phase
) {
    LARGE_INTEGER current;
    LONG failure_count;
    const char *failure_class;
    current.QuadPart = 0;
    InterlockedExchange(&g_state.partial_evidence_write, 1L);
    failure_count = InterlockedIncrement(&g_state.evidence_write_failures);
    if (failure_count != 1L) {
        InterlockedExchange(&g_state.multiple_evidence_write_failures, 1L);
        return;
    }
    g_state.partial_evidence_size_known =
        handle != NULL && handle != INVALID_HANDLE_VALUE &&
        GetFileSizeEx(handle, &current) && current.QuadPart >= 0;
    g_state.partial_evidence_bytes = g_state.partial_evidence_size_known
        ? (uint64_t)current.QuadPart : 0U;
    g_state.partial_evidence_requested_bytes = requested_bytes;
    copy_evidence_name_ascii(
        relative_name, g_state.partial_evidence_relative_path);
    strcpy_s(g_state.partial_evidence_phase,
        sizeof(g_state.partial_evidence_phase),
        phase != NULL ? phase : "UNKNOWN_EVIDENCE_FAILURE");
    if (handle == NULL || handle == INVALID_HANDLE_VALUE) {
        failure_class = "ZERO_BYTE_CREATE_FAILED";
    } else if (!g_state.partial_evidence_size_known) {
        failure_class = "SIZE_MEASUREMENT_FAILED";
    } else if (g_state.partial_evidence_bytes == 0U) {
        failure_class = "ZERO_BYTE";
    } else if (g_state.partial_evidence_bytes < requested_bytes) {
        failure_class = "PARTIAL_BYTES";
    } else if (g_state.partial_evidence_bytes == requested_bytes) {
        failure_class = "FULL_BYTES_UNVERIFIED";
    } else {
        failure_class = "OBSERVED_BYTES_EXCEED_REQUEST";
    }
    strcpy_s(g_state.partial_evidence_class,
        sizeof(g_state.partial_evidence_class), failure_class);
}

static void record_partial_outcome(
    uint64_t requested_bytes, const char *phase
) {
    LARGE_INTEGER current;
    LONG failure_count;
    current.QuadPart = 0;
    InterlockedExchange(&g_state.partial_outcome_write, 1L);
    failure_count = InterlockedIncrement(&g_state.outcome_write_failures);
    if (failure_count != 1L) {
        InterlockedExchange(&g_state.multiple_outcome_write_failures, 1L);
        return;
    }
    g_state.partial_outcome_size_known =
        g_state.outcome_handle != NULL &&
        g_state.outcome_handle != INVALID_HANDLE_VALUE &&
        GetFileSizeEx(g_state.outcome_handle, &current) && current.QuadPart >= 0;
    g_state.partial_outcome_bytes = g_state.partial_outcome_size_known
        ? (uint64_t)current.QuadPart : 0U;
    g_state.partial_outcome_requested_bytes = requested_bytes;
    strcpy_s(g_state.partial_outcome_phase,
        sizeof(g_state.partial_outcome_phase),
        phase != NULL ? phase : "UNKNOWN_OUTCOME_FAILURE");
}

static int build_native_terminal_failure_frame(
    const char *reason, ByteBuffer *frame_out
) {
    char escaped_reason[4096];
    char escaped_path[560];
    char escaped_cleanup[260];
    char prior_success_sha256[65];
    char first_attempt_sha256[65];
    char current_attempt_sha256[65];
    char staged_outcome_sha256[65];
    char payload[8192];
    int payload_length;
    unsigned char payload_digest[32];
    unsigned char *frame;
    LONG evidence_failures = InterlockedCompareExchange(
        &g_state.evidence_write_failures, 0L, 0L);
    LONG multiple_failures = InterlockedCompareExchange(
        &g_state.multiple_evidence_write_failures, 0L, 0L);
    LONG partial_outcome = InterlockedCompareExchange(
        &g_state.partial_outcome_write, 0L, 0L);
    LONG outcome_failures = InterlockedCompareExchange(
        &g_state.outcome_write_failures, 0L, 0L);
    LONG multiple_outcome_failures = InterlockedCompareExchange(
        &g_state.multiple_outcome_write_failures, 0L, 0L);
    LONG verified_evidence_count = InterlockedCompareExchange(
        &g_state.evidence_verified_write_count, 0L, 0L);
    LONG verified_evidence_mask = InterlockedCompareExchange(
        &g_state.evidence_verified_mask, 0L, 0L);
    LONG outcome_attempt_count = InterlockedCompareExchange(
        &g_state.outcome_attempt_count, 0L, 0L);
    LONG native_cleanup_failure_count = InterlockedCompareExchange(
        &g_state.native_cleanup_failure_count, 0L, 0L);
    int evidence_package_complete = evidence_failures == 0L &&
        verified_evidence_count == 8L && verified_evidence_mask == 0xffL;
    int staged_outcome_superseded = g_state.staged_outcome_frame != NULL &&
        g_state.staged_outcome_sha256_known;
    const char *failure_class = evidence_failures == 0L
        ? "NONE" : (g_state.partial_evidence_class[0] != '\0'
            ? g_state.partial_evidence_class : "UNKNOWN");
    const char *failure_phase = evidence_failures == 0L
        ? "NONE" : (g_state.partial_evidence_phase[0] != '\0'
            ? g_state.partial_evidence_phase : "UNKNOWN");
    const char *outcome_phase = partial_outcome == 0L
        ? "NONE" : (g_state.partial_outcome_phase[0] != '\0'
            ? g_state.partial_outcome_phase : "UNKNOWN");
    memset(frame_out, 0, sizeof(*frame_out));
    json_escape_ascii(reason != NULL ? reason : "unspecified_native_failure",
        escaped_reason, sizeof(escaped_reason));
    json_escape_ascii(g_state.partial_evidence_relative_path,
        escaped_path, sizeof(escaped_path));
    json_escape_ascii(g_state.native_cleanup_failure,
        escaped_cleanup, sizeof(escaped_cleanup));
    prior_success_sha256[0] = '\0';
    if (g_state.outcome_first_attempt_sha256_known) {
        hex_encode32(
            g_state.outcome_first_attempt_sha256, first_attempt_sha256);
    } else {
        first_attempt_sha256[0] = '\0';
    }
    if (g_state.outcome_current_attempt_sha256_known) {
        hex_encode32(
            g_state.outcome_current_attempt_sha256,
            current_attempt_sha256);
    } else {
        current_attempt_sha256[0] = '\0';
    }
    if (g_state.staged_outcome_sha256_known) {
        hex_encode32(
            g_state.staged_outcome_sha256, staged_outcome_sha256);
    } else {
        staged_outcome_sha256[0] = '\0';
    }
    payload_length = _snprintf_s(
        payload, sizeof(payload), _TRUNCATE,
        "{\"all_attempted_evidence_writes_verified\":%s,"
        "\"evidence_failure_class\":\"%s\","
        "\"evidence_failure_path\":\"%s\","
        "\"evidence_failure_phase\":\"%s\","
        "\"evidence_multiple_failures\":%s,"
        "\"evidence_observed_bytes\":%" PRIu64 ","
        "\"evidence_observed_bytes_known\":%s,"
        "\"evidence_package_complete\":%s,"
        "\"evidence_requested_bytes\":%" PRIu64 ","
        "\"evidence_verified_write_count\":%ld,"
        "\"evidence_write_failures\":%ld,"
        "\"native_broker_pid\":%lu,"
        "\"native_cleanup_failure\":\"%s\","
        "\"native_cleanup_failure_count\":%ld,"
        "\"outcome_attempt_count\":%ld,"
        "\"outcome_current_attempt_bytes\":%" PRIu64 ","
        "\"outcome_current_attempt_kind\":\"%s\","
        "\"outcome_current_attempt_seen\":%s,"
        "\"outcome_current_attempt_sha256\":\"%s\","
        "\"outcome_current_attempt_sha256_known\":%s,"
        "\"outcome_first_attempt_bytes\":%" PRIu64 ","
        "\"outcome_first_attempt_kind\":\"%s\","
        "\"outcome_first_attempt_seen\":%s,"
        "\"outcome_first_attempt_sha256\":\"%s\","
        "\"outcome_first_attempt_sha256_known\":%s,"
        "\"outcome_first_write_observed_bytes\":%" PRIu64 ","
        "\"outcome_first_write_observed_bytes_known\":%s,"
        "\"outcome_first_write_phase\":\"%s\","
        "\"outcome_first_write_requested_bytes\":%" PRIu64 ","
        "\"outcome_multiple_failures\":%s,"
        "\"outcome_partial_write\":%s,"
        "\"outcome_write_failures\":%ld,"
        "\"prior_success_frame_bytes\":%" PRIu64 ","
        "\"prior_success_frame_sha256\":\"%s\","
        "\"prior_success_superseded\":%s,"
        "\"reason\":\"%s\","
        "\"schema\":\"kira.avatar.r25.afes.native_terminal_failure.v3r6\","
        "\"staged_outcome_bytes\":%" PRIu64 ","
        "\"staged_outcome_kind\":\"%s\","
        "\"staged_outcome_sha256\":\"%s\","
        "\"staged_outcome_sha256_known\":%s,"
        "\"staged_outcome_superseded\":%s,"
        "\"status\":\"FAILED_APPEND_ONLY_NO_BODY_AUTHORITY\"}",
        evidence_failures == 0L ? "true" : "false",
        failure_class, escaped_path, failure_phase,
        multiple_failures != 0L ? "true" : "false",
        g_state.partial_evidence_bytes,
        g_state.partial_evidence_size_known ? "true" : "false",
        evidence_package_complete ? "true" : "false",
        g_state.partial_evidence_requested_bytes,
        (long)verified_evidence_count,
        (long)evidence_failures, (unsigned long)g_state.process_id,
        escaped_cleanup, (long)native_cleanup_failure_count,
        (long)outcome_attempt_count,
        g_state.outcome_current_attempt_bytes,
        g_state.outcome_current_attempt_kind,
        g_state.outcome_current_attempt_seen ? "true" : "false",
        current_attempt_sha256,
        g_state.outcome_current_attempt_sha256_known ? "true" : "false",
        g_state.outcome_first_attempt_bytes,
        g_state.outcome_first_attempt_kind,
        g_state.outcome_first_attempt_seen ? "true" : "false",
        first_attempt_sha256,
        g_state.outcome_first_attempt_sha256_known ? "true" : "false",
        g_state.partial_outcome_bytes,
        g_state.partial_outcome_size_known ? "true" : "false",
        outcome_phase,
        g_state.partial_outcome_requested_bytes,
        multiple_outcome_failures != 0L ? "true" : "false",
        partial_outcome != 0L ? "true" : "false",
        (long)outcome_failures,
        (uint64_t)0U,
        prior_success_sha256,
        "false",
        escaped_reason,
        (uint64_t)g_state.staged_outcome_frame_size,
        g_state.staged_outcome_kind,
        staged_outcome_sha256,
        g_state.staged_outcome_sha256_known ? "true" : "false",
        staged_outcome_superseded ? "true" : "false");
    if (payload_length <= 0 || (size_t)payload_length >= sizeof(payload) ||
        !sha256_memory(
            (const unsigned char *)payload, (size_t)payload_length,
            payload_digest)) {
        secure_zero(payload, sizeof(payload));
        return 0;
    }
    frame = (unsigned char *)malloc(52U + (size_t)payload_length);
    if (frame == NULL) {
        secure_zero(payload, sizeof(payload));
        secure_zero(payload_digest, sizeof(payload_digest));
        return 0;
    }
    memcpy(frame, "K25RCPT!", 8U);
    write_be32(frame + 8U, 1U);
    write_be64(frame + 12U, (uint64_t)payload_length);
    memcpy(frame + 20U, payload_digest, 32U);
    memcpy(frame + 52U, payload, (size_t)payload_length);
    secure_zero(payload, sizeof(payload));
    secure_zero(payload_digest, sizeof(payload_digest));
    frame_out->data = frame;
    frame_out->size = 52U + (size_t)payload_length;
    frame_out->capacity = frame_out->size;
    return 1;
}

static TerminalRewriteResult rewrite_terminal_outcome(
    const unsigned char *data, size_t size, const char *attempt_kind
) {
    LARGE_INTEGER zero;
    const char *failure_phase = NULL;
    ByteBuffer fallback = {0};
    unsigned char attempt_digest[32];
    unsigned char expected_digest[32];
    unsigned char observed_digest[32];
    uint64_t observed_bytes = 0U;
    int first_attempt_this_call = 0;
    zero.QuadPart = 0;
    if (g_state.outcome_handle == NULL ||
        g_state.outcome_handle == INVALID_HANDLE_VALUE) {
        return TERMINAL_REWRITE_NONE;
    }
    g_state.outcome_current_attempt_bytes = 0U;
    g_state.outcome_current_attempt_kind[0] = '\0';
    g_state.outcome_current_attempt_seen = 0;
    secure_zero(
        g_state.outcome_current_attempt_sha256,
        sizeof(g_state.outcome_current_attempt_sha256));
    g_state.outcome_current_attempt_sha256_known = 0;
    if (data != NULL &&
        size > 0U && size <= MAX_OUTCOME_BYTES && attempt_kind != NULL &&
        (strcmp(attempt_kind, "SUCCESS") == 0 ||
         strcmp(attempt_kind, "CALLER_FAILURE") == 0 ||
         strcmp(attempt_kind, "NATIVE_FAILURE") == 0)) {
        g_state.outcome_current_attempt_bytes = (uint64_t)size;
        strncpy_s(
            g_state.outcome_current_attempt_kind,
            sizeof(g_state.outcome_current_attempt_kind), attempt_kind,
            _TRUNCATE);
        g_state.outcome_current_attempt_seen = 1;
        (void)InterlockedIncrement(&g_state.outcome_attempt_count);
        if (!g_state.outcome_first_attempt_seen) {
            first_attempt_this_call = 1;
            g_state.outcome_first_attempt_bytes = (uint64_t)size;
            strncpy_s(
                g_state.outcome_first_attempt_kind,
                sizeof(g_state.outcome_first_attempt_kind), attempt_kind,
                _TRUNCATE);
            g_state.outcome_first_attempt_seen = 1;
        }
        if (sha256_memory(data, size, attempt_digest)) {
            memcpy(
                g_state.outcome_current_attempt_sha256, attempt_digest,
                sizeof(attempt_digest));
            g_state.outcome_current_attempt_sha256_known = 1;
            if (first_attempt_this_call) {
                memcpy(
                    g_state.outcome_first_attempt_sha256, attempt_digest,
                    sizeof(attempt_digest));
                g_state.outcome_first_attempt_sha256_known = 1;
            }
        }
    }
    secure_zero(attempt_digest, sizeof(attempt_digest));
    if (data == NULL || size == 0U || size > MAX_OUTCOME_BYTES) {
        failure_phase = "OUTCOME_INPUT_INVALID";
    } else if (!verify_output_ancestor_chain()) {
        failure_phase = "OUTCOME_ANCESTOR_REVALIDATION_FAILED";
    } else if (!SetFilePointerEx(
            g_state.outcome_handle, zero, NULL, FILE_BEGIN)) {
        failure_phase = "OUTCOME_SEEK_FAILED";
    } else if (!SetEndOfFile(g_state.outcome_handle)) {
        failure_phase = "OUTCOME_TRUNCATE_FAILED";
    } else if (!write_all_handle(g_state.outcome_handle, data, size)) {
        failure_phase = "OUTCOME_WRITE_FAILED";
    } else if (!FlushFileBuffers(g_state.outcome_handle)) {
        failure_phase = "OUTCOME_FLUSH_FAILED";
    } else if (!sha256_memory(data, size, expected_digest) ||
        !sha256_handle(
            g_state.outcome_handle, observed_digest, &observed_bytes) ||
        observed_bytes != (uint64_t)size ||
        !constant_time_equal32(expected_digest, observed_digest)) {
        failure_phase = "OUTCOME_READBACK_VERIFICATION_FAILED";
    } else if (!verify_output_ancestor_chain()) {
        failure_phase = "OUTCOME_FINAL_ANCESTOR_REVALIDATION_FAILED";
    }
    secure_zero(expected_digest, sizeof(expected_digest));
    secure_zero(observed_digest, sizeof(observed_digest));
    if (failure_phase != NULL) {
        record_partial_outcome((uint64_t)size, failure_phase);
        if (!build_native_terminal_failure_frame(
                "terminal_outcome_first_write_failed", &fallback)) {
            return TERMINAL_REWRITE_NONE;
        }
        if (!SetFilePointerEx(
                g_state.outcome_handle, zero, NULL, FILE_BEGIN) ||
            !SetEndOfFile(g_state.outcome_handle) ||
            !write_all_handle(
                g_state.outcome_handle, fallback.data, fallback.size) ||
            !FlushFileBuffers(g_state.outcome_handle) ||
            !sha256_memory(fallback.data, fallback.size, expected_digest) ||
            !sha256_handle(
                g_state.outcome_handle, observed_digest, &observed_bytes) ||
            observed_bytes != (uint64_t)fallback.size ||
            !constant_time_equal32(expected_digest, observed_digest)) {
            record_partial_outcome(
                (uint64_t)fallback.size, "OUTCOME_FALLBACK_WRITE_FAILED");
            secure_zero(expected_digest, sizeof(expected_digest));
            secure_zero(observed_digest, sizeof(observed_digest));
            secure_zero(fallback.data, fallback.size);
            free(fallback.data);
            return TERMINAL_REWRITE_NONE;
        }
        if (!verify_output_ancestor_chain()) {
            record_partial_outcome(
                (uint64_t)fallback.size,
                "OUTCOME_FALLBACK_ANCESTOR_REVALIDATION_FAILED");
            secure_zero(expected_digest, sizeof(expected_digest));
            secure_zero(observed_digest, sizeof(observed_digest));
            secure_zero(fallback.data, fallback.size);
            free(fallback.data);
            return TERMINAL_REWRITE_NONE;
        }
        secure_zero(expected_digest, sizeof(expected_digest));
        secure_zero(observed_digest, sizeof(observed_digest));
        secure_zero(fallback.data, fallback.size);
        free(fallback.data);
        return TERMINAL_REWRITE_FALLBACK_FAILURE_VERIFIED;
    }
    return TERMINAL_REWRITE_PRIMARY_VERIFIED;
}

static void clear_staged_outcome(void) {
    if (g_state.staged_outcome_frame != NULL) {
        secure_zero(
            g_state.staged_outcome_frame,
            g_state.staged_outcome_frame_size);
        free(g_state.staged_outcome_frame);
    }
    g_state.staged_outcome_frame = NULL;
    g_state.staged_outcome_frame_size = 0U;
    secure_zero(
        g_state.staged_outcome_sha256,
        sizeof(g_state.staged_outcome_sha256));
    g_state.staged_outcome_sha256_known = 0;
    g_state.staged_outcome_kind[0] = '\0';
}

static int stage_terminal_outcome(
    const unsigned char *data, size_t size, const char *kind
) {
    unsigned char digest[32];
    unsigned char *copy;
    if (g_state.staged_outcome_frame != NULL || data == NULL || size == 0U ||
        size > MAX_OUTCOME_BYTES || kind == NULL ||
        (strcmp(kind, "SUCCESS") != 0 &&
         strcmp(kind, "CALLER_FAILURE") != 0)) {
        return 0;
    }
    copy = (unsigned char *)malloc(size);
    if (copy == NULL || !sha256_memory(data, size, digest)) {
        free(copy);
        secure_zero(digest, sizeof(digest));
        return 0;
    }
    memcpy(copy, data, size);
    g_state.staged_outcome_frame = copy;
    g_state.staged_outcome_frame_size = size;
    memcpy(g_state.staged_outcome_sha256, digest, sizeof(digest));
    g_state.staged_outcome_sha256_known = 1;
    strncpy_s(
        g_state.staged_outcome_kind, sizeof(g_state.staged_outcome_kind),
        kind, _TRUNCATE);
    secure_zero(digest, sizeof(digest));
    return 1;
}

static wchar_t *validated_project_output_path(PyObject *relative_object) {
    wchar_t *relative = py_unicode_to_wide_exact(relative_object);
    wchar_t *result;
    if (relative == NULL) {
        return NULL;
    }
    result = join_project_relative(relative);
    free(relative);
    if (result == NULL) {
        PyErr_SetString(PyExc_ValueError, "unsafe_project_relative_output_path");
    }
    return result;
}

static int verify_output_ancestor_chain(void) {
    HeldOutput *held;
    if (!recheck_ancestor_chain()) {
        return 0;
    }
    for (held = g_state.held_outputs; held != NULL; held = held->next) {
        ULONGLONG volume = 0ULL;
        FILE_ID_128 id;
        wchar_t *final_path = NULL;
        int matches = handle_identity(
                held->handle, &volume, &id, &final_path) &&
            same_file_identity(
                volume, &id, held->volume_serial, &held->file_id) &&
            _wcsicmp(final_path, held->final_path) == 0;
        free(final_path);
        if (!matches) {
            return 0;
        }
    }
    return 1;
}

static int verify_new_output_handle(
    HANDLE handle, const wchar_t *expected_path, int require_directory,
    HeldOutput **tracked_output
) {
    BY_HANDLE_FILE_INFORMATION basic;
    ULONGLONG volume = 0ULL;
    FILE_ID_128 id;
    wchar_t *final_path = NULL;
    HANDLE retained = INVALID_HANDLE_VALUE;
    HeldOutput *held = NULL;
    int attributes_match;
    if (!GetFileInformationByHandle(handle, &basic)) {
        return 0;
    }
    attributes_match = require_directory
        ? ((basic.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0U)
        : ((basic.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0U);
    if (!attributes_match ||
        (basic.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U ||
        !final_handle_matches_path(
            handle, expected_path, &volume, &id, &final_path) ||
        !DuplicateHandle(
            GetCurrentProcess(), handle, GetCurrentProcess(), &retained,
            FILE_READ_ATTRIBUTES | SYNCHRONIZE, FALSE, 0U)) {
        free(final_path);
        return 0;
    }
    held = (HeldOutput *)calloc(1U, sizeof(*held));
    if (held == NULL) {
        CloseHandle(retained);
        free(final_path);
        return 0;
    }
    held->handle = retained;
    held->path = canonical_full_path(expected_path);
    held->final_path = final_path;
    held->volume_serial = volume;
    memcpy(&held->file_id, &id, sizeof(id));
    if (held->path == NULL) {
        CloseHandle(retained);
        free(held->final_path);
        free(held);
        return 0;
    }
    held->next = g_state.held_outputs;
    g_state.held_outputs = held;
    if (tracked_output != NULL) {
        *tracked_output = held;
    }
    return verify_output_ancestor_chain();
}

static PyObject *py_reserve_outcome(PyObject *self, PyObject *args) {
    PyObject *relative_object;
    wchar_t *path;
    HANDLE handle;
    (void)self;
    if (!require_main_os_thread("reserve_outcome") ||
        !PyArg_UnpackTuple(args, "reserve_outcome", 1, 1, &relative_object) ||
        !require_claimed("reserve_outcome")) {
        return NULL;
    }
    EnterCriticalSection(&g_state.mutex);
    if (g_state.outcome_reserved) {
        LeaveCriticalSection(&g_state.mutex);
        return broker_error("outcome_already_reserved");
    }
    LeaveCriticalSection(&g_state.mutex);
    path = validated_project_output_path(relative_object);
    if (path == NULL) {
        return NULL;
    }
    if (!hold_every_path_ancestor(path) || !verify_output_ancestor_chain()) {
        free(path);
        return broker_error("outcome_ancestor_identity_refused");
    }
    handle = CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL
    );
    if (handle == INVALID_HANDLE_VALUE ||
        !verify_new_output_handle(handle, path, 0, NULL) ||
        !verify_output_ancestor_chain()) {
        DWORD code = GetLastError();
        if (handle != INVALID_HANDLE_VALUE) {
            CloseHandle(handle);
        }
        free(path);
        PyErr_Format(PyExc_RuntimeError,
            "native_outcome_reservation_failed:winerror=%lu",
            (unsigned long)code);
        return NULL;
    }
    EnterCriticalSection(&g_state.mutex);
    g_state.outcome_handle = handle;
    g_state.outcome_path = path;
    g_state.outcome_reserved = 1;
    LeaveCriticalSection(&g_state.mutex);
    Py_RETURN_NONE;
}

static PyObject *py_create_output_root(PyObject *self, PyObject *args) {
    PyObject *relative_object;
    wchar_t *path;
    (void)self;
    if (!require_main_os_thread("create_output_root") ||
        !PyArg_UnpackTuple(args, "create_output_root", 1, 1, &relative_object) ||
        !require_claimed("create_output_root")) {
        return NULL;
    }
    if (!g_state.outcome_reserved || g_state.output_created) {
        return broker_error("output_root_state_refused");
    }
    path = validated_project_output_path(relative_object);
    if (path == NULL) {
        return NULL;
    }
    if (!hold_every_path_ancestor(path) || !verify_output_ancestor_chain() ||
        !CreateDirectoryW(path, NULL)) {
        DWORD code = GetLastError();
        free(path);
        PyErr_Format(PyExc_RuntimeError,
            "native_output_root_create_new_failed:winerror=%lu",
            (unsigned long)code);
        return NULL;
    }
    {
        HANDLE root_handle = CreateFileW(
            path, FILE_READ_ATTRIBUTES | SYNCHRONIZE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
        int verified = root_handle != INVALID_HANDLE_VALUE &&
            verify_new_output_handle(root_handle, path, 1, NULL) &&
            verify_output_ancestor_chain();
        if (root_handle != INVALID_HANDLE_VALUE) {
            CloseHandle(root_handle);
        }
        if (!verified) {
            free(path);
            return broker_error("output_root_final_handle_identity_refused");
        }
    }
    g_state.output_root = path;
    g_state.output_created = 1;
    Py_RETURN_NONE;
}

static int path_is_under_output_root(const wchar_t *path) {
    size_t prefix;
    if (path == NULL || g_state.output_root == NULL) {
        return 0;
    }
    if (!verify_output_ancestor_chain()) {
        return 0;
    }
    prefix = wcslen(g_state.output_root);
    return _wcsnicmp(path, g_state.output_root, prefix) == 0 &&
        path[prefix] == L'\\';
}

static PyObject *py_write_evidence(PyObject *self, PyObject *args) {
    PyObject *name_object;
    PyObject *data_object;
    wchar_t *name;
    wchar_t *joined = NULL;
    wchar_t *canonical = NULL;
    Py_buffer view;
    HANDLE handle = INVALID_HANDLE_VALUE;
    HeldOutput *held = NULL;
    size_t root_length;
    size_t name_length;
    unsigned char hash[32];
    unsigned char expected_hash[32];
    uint64_t measured = 0U;
    char hash_hex[65];
    char evidence_name_ascii[260];
    const char *failure_phase = NULL;
    DWORD failure_code = ERROR_SUCCESS;
    PyObject *result = NULL;
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!require_main_os_thread("write_evidence") ||
        !PyArg_UnpackTuple(
            args, "write_evidence", 2, 2, &name_object, &data_object) ||
        !require_claimed("write_evidence")) {
        return NULL;
    }
    if (!g_state.output_created || g_state.outcome_committed) {
        return broker_error("write_evidence_state_refused");
    }
    name = py_unicode_to_wide_exact(name_object);
    if (name == NULL) {
        return NULL;
    }
    if (!safe_relative_path(name, 0)) {
        free(name);
        return broker_error("evidence_name_must_be_one_safe_component");
    }
    copy_evidence_name_ascii(name, evidence_name_ascii);
    if (evidence_name_ascii[0] == '\0') {
        free(name);
        return broker_error("evidence_name_must_be_bounded_ascii");
    }
    {
        LONG next_evidence = InterlockedCompareExchange(
            &g_state.evidence_verified_write_count, 0L, 0L);
        if (!expected_evidence_name_at(next_evidence, evidence_name_ascii) ||
            (InterlockedCompareExchange(
                &g_state.evidence_verified_mask, 0L, 0L) &
             (1L << next_evidence)) != 0L) {
            free(name);
            return broker_error("evidence_exact_order_or_identity_refused");
        }
    }
    if (PyObject_GetBuffer(data_object, &view, PyBUF_CONTIG_RO) < 0) {
        free(name);
        return NULL;
    }
    if (view.len < 0 || (uint64_t)view.len > MAX_EVIDENCE_BYTES) {
        PyBuffer_Release(&view);
        free(name);
        return broker_error("evidence_size_refused");
    }
    if (!sha256_memory(
            (const unsigned char *)view.buf, (size_t)view.len,
            expected_hash)) {
        record_partial_evidence(
            INVALID_HANDLE_VALUE, name, (uint64_t)view.len,
            "EVIDENCE_INPUT_HASH_FAILED");
        PyBuffer_Release(&view);
        free(name);
        return broker_error("evidence_input_hash_failed");
    }
    root_length = wcslen(g_state.output_root);
    name_length = wcslen(name);
    joined = (wchar_t *)malloc(
        (root_length + name_length + 2U) * sizeof(wchar_t)
    );
    if (joined == NULL) {
        PyBuffer_Release(&view);
        free(name);
        return PyErr_NoMemory();
    }
    memcpy(joined, g_state.output_root, root_length * sizeof(wchar_t));
    joined[root_length] = L'\\';
    memcpy(joined + root_length + 1U, name,
        (name_length + 1U) * sizeof(wchar_t));
    canonical = canonical_full_path(joined);
    free(joined);
    if (canonical == NULL || !path_is_under_output_root(canonical) ||
        !hold_every_path_ancestor(canonical) ||
        !verify_output_ancestor_chain()) {
        failure_code = GetLastError();
        record_partial_evidence(
            INVALID_HANDLE_VALUE, name, (uint64_t)view.len,
            "EVIDENCE_PATH_REVALIDATION_FAILED");
        PyBuffer_Release(&view);
        free(name);
        free(canonical);
        PyErr_Format(PyExc_RuntimeError,
            "evidence_path_escape_refused:winerror=%lu",
            (unsigned long)failure_code);
        return NULL;
    }
    handle = CreateFileW(
        canonical, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL,
        CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL
    );
    if (handle == INVALID_HANDLE_VALUE) {
        failure_phase = "EVIDENCE_CREATE_NEW_FAILED";
    } else if (!write_all_handle(
            handle, (const unsigned char *)view.buf, (size_t)view.len)) {
        failure_phase = "EVIDENCE_WRITE_FAILED";
    } else if (!FlushFileBuffers(handle)) {
        failure_phase = "EVIDENCE_FLUSH_FAILED";
    } else if (!verify_new_output_handle(handle, canonical, 0, &held)) {
        failure_phase = "EVIDENCE_HANDLE_IDENTITY_FAILED";
    } else if (!verify_output_ancestor_chain()) {
        failure_phase = "EVIDENCE_ANCESTOR_REVALIDATION_FAILED";
    } else if (!sha256_handle(handle, hash, &measured)) {
        failure_phase = "EVIDENCE_READBACK_HASH_FAILED";
    } else if (measured != (uint64_t)view.len) {
        failure_phase = "EVIDENCE_READBACK_LENGTH_FAILED";
    } else if (!constant_time_equal32(expected_hash, hash)) {
        failure_phase = "EVIDENCE_READBACK_DIGEST_MISMATCH";
    }
    if (failure_phase != NULL) {
        failure_code = GetLastError();
        record_partial_evidence(
            handle, name, (uint64_t)view.len, failure_phase);
        if (handle != INVALID_HANDLE_VALUE) {
            CloseHandle(handle);
        }
        PyBuffer_Release(&view);
        free(name);
        free(canonical);
        secure_zero(expected_hash, sizeof(expected_hash));
        secure_zero(hash, sizeof(hash));
        PyErr_Format(PyExc_RuntimeError,
            "native_evidence_write_failed:%s:winerror=%lu",
            failure_phase, (unsigned long)failure_code);
        return NULL;
    }
    {
        LONG completed_index = InterlockedIncrement(
            &g_state.evidence_verified_write_count) - 1L;
        if (completed_index < 0L || completed_index >= 8L ||
            !expected_evidence_name_at(completed_index, evidence_name_ascii)) {
            secure_zero(expected_hash, sizeof(expected_hash));
            secure_zero(hash, sizeof(hash));
            PyBuffer_Release(&view);
            CloseHandle(handle);
            free(name);
            free(canonical);
            return broker_error("evidence_verified_counter_drift");
        }
        (void)InterlockedOr(
            &g_state.evidence_verified_mask, 1L << completed_index);
    }
    PyBuffer_Release(&view);
    CloseHandle(handle);
    free(name);
    free(canonical);
    hex_encode32(hash, hash_hex);
    secure_zero(expected_hash, sizeof(expected_hash));
    secure_zero(hash, sizeof(hash));
    result = PyUnicode_FromStringAndSize(hash_hex, 64);
    return result;
}

static PyObject *snapshot_entry(
    uint64_t actual_bytes, const unsigned char actual_hash[32], int matches
) {
    PyObject *entry = PyDict_New();
    PyObject *bytes = NULL;
    PyObject *hash = NULL;
    PyObject *match = matches ? Py_True : Py_False;
    char hash_hex[65];
    if (entry == NULL) {
        return NULL;
    }
    bytes = PyLong_FromUnsignedLongLong(actual_bytes);
    hex_encode32(actual_hash, hash_hex);
    hash = PyUnicode_FromStringAndSize(hash_hex, 64);
    Py_INCREF(match);
    if (bytes == NULL || hash == NULL ||
        PyDict_SetItemString(entry, "bytes", bytes) < 0 ||
        PyDict_SetItemString(entry, "sha256", hash) < 0 ||
        PyDict_SetItemString(entry, "matches", match) < 0) {
        Py_CLEAR(entry);
    }
    Py_XDECREF(bytes);
    Py_XDECREF(hash);
    Py_DECREF(match);
    return entry;
}

static int sha256_memory(
    const unsigned char *data, size_t size, unsigned char output[32]
) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    PUCHAR object = NULL;
    DWORD object_length = 0U;
    DWORD returned = 0U;
    NTSTATUS status;
    int ok = 0;
    status = BCryptOpenAlgorithmProvider(
        &algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0U
    );
    if (status < 0) {
        goto cleanup;
    }
    status = BCryptGetProperty(
        algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&object_length,
        sizeof(object_length), &returned, 0U
    );
    if (status < 0 || returned != sizeof(object_length)) {
        goto cleanup;
    }
    object = (PUCHAR)HeapAlloc(GetProcessHeap(), 0U, object_length);
    if (object == NULL) {
        goto cleanup;
    }
    status = BCryptCreateHash(
        algorithm, &hash, object, object_length, NULL, 0U, 0U
    );
    if (status < 0 || size > ULONG_MAX) {
        goto cleanup;
    }
    {
        static unsigned char empty_input = 0U;
        status = BCryptHashData(
            hash, (PUCHAR)(size == 0U ? &empty_input : data),
            (ULONG)size, 0U
        );
    }
    if (status < 0 || BCryptFinishHash(hash, output, 32U, 0U) < 0) {
        goto cleanup;
    }
    ok = 1;
cleanup:
    if (hash != NULL) {
        BCryptDestroyHash(hash);
    }
    if (object != NULL) {
        secure_zero(object, object_length);
        HeapFree(GetProcessHeap(), 0U, object);
    }
    if (algorithm != NULL) {
        BCryptCloseAlgorithmProvider(algorithm, 0U);
    }
    return ok;
}

static PyObject *py_after_snapshot(PyObject *self, PyObject *args) {
    PyObject *result;
    PyObject *rows_result;
    size_t index;
    ByteBuffer canonical = {0};
    int unchanged = 1;
    unsigned char snapshot_hash[32];
    char snapshot_hex[65];
    (void)self;
    if (!require_main_os_thread("after_snapshot") ||
        !PyArg_ParseTuple(args, ":after_snapshot") ||
        !require_claimed("after_snapshot")) {
        return NULL;
    }
    if (!require_all_jobs_quiescent("after_snapshot") ||
        InterlockedCompareExchange(&g_state.active_child_count, 0L, 0L) != 0L ||
        g_state.run_attempt_consumed[0] != 1L ||
        g_state.run_attempt_consumed[1] != 1L) {
        return broker_error("after_snapshot_all_jobs_quiescent_refused");
    }
    if (g_state.next_run_number != 3 || g_state.after_snapshot_done) {
        return broker_error("after_snapshot_pair_state_refused");
    }
    result = PyDict_New();
    rows_result = PyDict_New();
    if (result == NULL || rows_result == NULL) {
        Py_XDECREF(result);
        Py_XDECREF(rows_result);
        return NULL;
    }
    {
        unsigned char hash[32];
        uint64_t bytes = 0U;
        int measured = sha256_handle(g_state.manifest_handle, hash, &bytes);
        int matches = measured && bytes == g_state.manifest_bytes &&
            constant_time_equal32(hash, g_state.manifest_sha256);
        PyObject *entry;
        char line[512];
        int length;
        if (!measured) {
            memset(hash, 0, sizeof(hash));
        }
        entry = snapshot_entry(bytes, hash, matches);
        hex_encode32(hash, snapshot_hex);
        secure_zero(hash, sizeof(hash));
        if (!matches) {
            unchanged = 0;
        }
        length = _snprintf_s(
            line, sizeof(line), _TRUNCATE,
            "retained_manifest\t%" PRIu64 "\t%s\n", bytes, snapshot_hex
        );
        if (length <= 0 || !byte_buffer_reserve(
                &canonical, canonical.size + (size_t)length) || entry == NULL ||
            PyDict_SetItemString(rows_result, "retained_manifest", entry) < 0) {
            Py_XDECREF(entry);
            Py_DECREF(rows_result);
            Py_DECREF(result);
            free(canonical.data);
            return PyErr_NoMemory();
        }
        memcpy(canonical.data + canonical.size, line, (size_t)length);
        canonical.size += (size_t)length;
        Py_DECREF(entry);
    }
    for (index = 0U; index < g_state.row_count; ++index) {
        RetainedRow *row = &g_state.rows[index];
        unsigned char hash[32];
        uint64_t bytes = 0U;
        int measured = sha256_handle(row->handle, hash, &bytes);
        int matches = measured && bytes == row->expected_bytes &&
            constant_time_equal32(hash, row->expected_sha256);
        PyObject *entry;
        if (!measured) {
            memset(hash, 0, sizeof(hash));
        }
        entry = snapshot_entry(bytes, hash, matches);
        if (!matches) {
            unchanged = 0;
        }
        hex_encode32(hash, snapshot_hex);
        secure_zero(hash, sizeof(hash));
        {
            char line[512];
            int length = _snprintf_s(
                line, sizeof(line), _TRUNCATE, "%s\t%" PRIu64 "\t%s\n",
                row->label_utf8, bytes, snapshot_hex
            );
            if (length <= 0 || !byte_buffer_reserve(
                    &canonical, canonical.size + (size_t)length)) {
                Py_XDECREF(entry);
                Py_DECREF(rows_result);
                Py_DECREF(result);
                free(canonical.data);
                return PyErr_NoMemory();
            }
            memcpy(canonical.data + canonical.size, line, (size_t)length);
            canonical.size += (size_t)length;
        }
        if (entry == NULL ||
            PyDict_SetItemString(rows_result, row->label_utf8, entry) < 0) {
            Py_XDECREF(entry);
            Py_DECREF(rows_result);
            Py_DECREF(result);
            free(canonical.data);
            return NULL;
        }
        Py_DECREF(entry);
    }
    {
        unsigned char hash[32];
        uint64_t bytes = 0U;
        int measured = sha256_handle(g_state.audit_handle, hash, &bytes);
        int matches = measured && bytes == g_state.audit_bytes &&
            constant_time_equal32(hash, g_state.audit_sha256);
        PyObject *entry;
        if (!measured) {
            memset(hash, 0, sizeof(hash));
        }
        entry = snapshot_entry(bytes, hash, matches);
        if (!matches) {
            unchanged = 0;
        }
        hex_encode32(hash, snapshot_hex);
        secure_zero(hash, sizeof(hash));
        {
            char line[512];
            int length = _snprintf_s(
                line, sizeof(line), _TRUNCATE,
                "accepted_controller_audit\t%" PRIu64 "\t%s\n",
                bytes, snapshot_hex
            );
            if (length <= 0 || !byte_buffer_reserve(
                    &canonical, canonical.size + (size_t)length)) {
                Py_XDECREF(entry);
                Py_DECREF(rows_result);
                Py_DECREF(result);
                free(canonical.data);
                return PyErr_NoMemory();
            }
            memcpy(canonical.data + canonical.size, line, (size_t)length);
            canonical.size += (size_t)length;
        }
        if (entry == NULL || PyDict_SetItemString(
                rows_result, "accepted_controller_audit", entry) < 0) {
            Py_XDECREF(entry);
            Py_DECREF(rows_result);
            Py_DECREF(result);
            free(canonical.data);
            return NULL;
        }
        Py_DECREF(entry);
    }
    if (!sha256_memory(canonical.data, canonical.size, snapshot_hash)) {
        Py_DECREF(rows_result);
        Py_DECREF(result);
        free(canonical.data);
        return broker_error("native_snapshot_digest_failed");
    }
    free(canonical.data);
    hex_encode32(snapshot_hash, snapshot_hex);
    secure_zero(snapshot_hash, sizeof(snapshot_hash));
    {
        PyObject *unchanged_object = unchanged ? Py_True : Py_False;
        PyObject *hash_object = PyUnicode_FromStringAndSize(snapshot_hex, 64);
        Py_INCREF(unchanged_object);
        if (hash_object == NULL ||
            PyDict_SetItemString(result, "unchanged", unchanged_object) < 0 ||
            PyDict_SetItemString(result, "snapshot_sha256", hash_object) < 0 ||
            PyDict_SetItemString(result, "rows", rows_result) < 0) {
            Py_CLEAR(result);
        }
        Py_DECREF(unchanged_object);
        Py_XDECREF(hash_object);
    }
    Py_DECREF(rows_result);
    g_state.after_snapshot_done = 1;
    return result;
}

static PyObject *py_commit_outcome(PyObject *self, PyObject *args) {
    PyObject *frame_object;
    Py_buffer view;
    unsigned char provisional_hash[32];
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!require_main_os_thread("commit_outcome") ||
        !PyArg_UnpackTuple(args, "commit_outcome", 1, 1, &frame_object) ||
        !require_claimed("commit_outcome")) {
        return NULL;
    }
    if (!require_all_jobs_quiescent("commit_outcome") ||
        InterlockedCompareExchange(&g_state.active_child_count, 0L, 0L) != 0L ||
        InterlockedCompareExchange(
            &g_state.evidence_verified_write_count, 0L, 0L) != 8L ||
        InterlockedCompareExchange(
            &g_state.evidence_verified_mask, 0L, 0L) != 0xffL ||
        InterlockedCompareExchange(
            &g_state.evidence_write_failures, 0L, 0L) != 0L ||
        g_state.run_attempt_consumed[0] != 1L ||
        g_state.run_attempt_consumed[1] != 1L) {
        return broker_error("commit_outcome_all_jobs_quiescent_refused");
    }
    if (!g_state.outcome_reserved || g_state.outcome_committed ||
        !g_state.after_snapshot_done || g_state.next_run_number != 3) {
        return broker_error("commit_outcome_state_refused");
    }
    if (PyObject_GetBuffer(frame_object, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    if (view.len <= 0 || (uint64_t)view.len > MAX_OUTCOME_BYTES ||
        !sha256_memory(
            (const unsigned char *)view.buf, (size_t)view.len,
            provisional_hash)) {
        secure_zero(provisional_hash, sizeof(provisional_hash));
        PyBuffer_Release(&view);
        return broker_error("native_outcome_commit_failed");
    }
    if (!stage_terminal_outcome(
            (const unsigned char *)view.buf, (size_t)view.len, "SUCCESS")) {
        secure_zero(provisional_hash, sizeof(provisional_hash));
        PyBuffer_Release(&view);
        return broker_error("native_outcome_stage_failed");
    }
    memcpy(
        g_state.provisional_success_sha256, provisional_hash,
        sizeof(provisional_hash));
    secure_zero(provisional_hash, sizeof(provisional_hash));
    g_state.provisional_success_bytes = (uint64_t)view.len;
    g_state.provisional_success_hash_valid = 1;
    g_state.outcome_success_provisional = 1;
    PyBuffer_Release(&view);
    /* A Python-produced success is only staged in native-owned memory.  The
     * reserved outcome file remains externally non-accepting until bootstrap
     * return, module-delta verification, and Py_FinalizeEx all succeed. */
    g_state.outcome_committed = 1;
    Py_RETURN_NONE;
}

static PyObject *py_commit_failure_outcome(PyObject *self, PyObject *args) {
    static const char *const failure_core_keys[] = {
        "schema", "status", "stage", "primary_failure_type",
        "primary_failure", "cleanup_errors", "execution_contract_sha256"
    };
    PyObject *failure_core;
    PyObject *cleanup_errors;
    PyObject *contract_sha;
    PyObject *native_evidence = NULL;
    PyObject *envelope = NULL;
    PyObject *frame = NULL;
    Py_buffer view;
    LONG evidence_write_failures;
    LONG multiple_evidence_failures;
    LONG verified_evidence_count;
    LONG verified_evidence_mask;
    unsigned char caller_contract_hash[32];
    Py_ssize_t index;
    int ok = 0;
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!require_main_os_thread("commit_failure_outcome") ||
        !PyArg_UnpackTuple(
            args, "commit_failure_outcome", 1, 1, &failure_core) ||
        !require_claimed("commit_failure_outcome")) {
        return NULL;
    }
    if (!require_all_jobs_quiescent("commit_failure_outcome") ||
        InterlockedCompareExchange(&g_state.active_child_count, 0L, 0L) != 0L ||
        g_state.run_attempt_consumed[0] < 0L ||
        g_state.run_attempt_consumed[1] < 0L) {
        return broker_error("commit_failure_all_jobs_quiescent_refused");
    }
    if (!g_state.outcome_reserved || g_state.outcome_committed) {
        return broker_error("commit_failure_outcome_state_refused");
    }
    if (!dict_has_exact_keys(
            failure_core, failure_core_keys,
            sizeof(failure_core_keys) / sizeof(failure_core_keys[0])) ||
        !exact_unicode_equals_ascii(
            PyDict_GetItemString(failure_core, "schema"),
            "kira.avatar.r25.foundation_afes_locked_pair_failure.v3r6") ||
        !exact_unicode_equals_ascii(
            PyDict_GetItemString(failure_core, "status"),
            "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY") ||
        !PyUnicode_CheckExact(PyDict_GetItemString(failure_core, "stage")) ||
        !PyUnicode_CheckExact(
            PyDict_GetItemString(failure_core, "primary_failure_type")) ||
        !PyUnicode_CheckExact(
            PyDict_GetItemString(failure_core, "primary_failure"))) {
        return broker_error("caller_failure_core_shape_or_identity_refused");
    }
    cleanup_errors = PyDict_GetItemString(failure_core, "cleanup_errors");
    contract_sha = PyDict_GetItemString(
        failure_core, "execution_contract_sha256");
    if (!PyList_CheckExact(cleanup_errors) || PyList_GET_SIZE(cleanup_errors) > 32 ||
        !PyUnicode_CheckExact(contract_sha)) {
        return broker_error("caller_failure_cleanup_or_contract_shape_refused");
    }
    for (index = 0; index < PyList_GET_SIZE(cleanup_errors); ++index) {
        if (!PyUnicode_CheckExact(PyList_GET_ITEM(cleanup_errors, index))) {
            return broker_error("caller_failure_cleanup_item_refused");
        }
    }
    {
        const char *sha_text;
        Py_ssize_t sha_length;
        if (!py_unicode_to_utf8_exact(contract_sha, &sha_text, &sha_length) ||
            sha_length != 64 || !is_lower_hex64(sha_text) ||
            !parse_hex64(sha_text, caller_contract_hash) ||
            !constant_time_equal32(
                caller_contract_hash, g_state.expected_contract_sha256)) {
            secure_zero(caller_contract_hash, sizeof(caller_contract_hash));
            return broker_error("caller_failure_contract_sha_refused");
        }
        secure_zero(caller_contract_hash, sizeof(caller_contract_hash));
    }
    evidence_write_failures = InterlockedCompareExchange(
        &g_state.evidence_write_failures, 0L, 0L);
    multiple_evidence_failures = InterlockedCompareExchange(
        &g_state.multiple_evidence_write_failures, 0L, 0L);
    verified_evidence_count = InterlockedCompareExchange(
        &g_state.evidence_verified_write_count, 0L, 0L);
    verified_evidence_mask = InterlockedCompareExchange(
        &g_state.evidence_verified_mask, 0L, 0L);
    if (evidence_write_failures < 0L ||
        (evidence_write_failures == 0L &&
         InterlockedCompareExchange(
             &g_state.partial_evidence_write, 0L, 0L) != 0L) ||
        (evidence_write_failures > 0L &&
         InterlockedCompareExchange(
             &g_state.partial_evidence_write, 0L, 0L) == 0L) ||
        g_state.partial_evidence_bytes > MAX_EVIDENCE_BYTES ||
        g_state.partial_evidence_requested_bytes > MAX_EVIDENCE_BYTES) {
        return broker_error("native_evidence_measurement_state_invalid");
    }
    native_evidence = Py_BuildValue(
        "{s:O,s:O,s:s,s:s,s:s,s:O,s:K,s:O,s:K,s:l,s:l,"
        "s:K,s:O,s:s,s:K,s:O,s:O,s:l,s:K,s:s,s:O}",
        "all_attempted_evidence_writes_verified",
            evidence_write_failures == 0L ? Py_True : Py_False,
        "evidence_package_complete",
            evidence_write_failures == 0L && verified_evidence_count == 8L &&
            verified_evidence_mask == 0xffL ? Py_True : Py_False,
        "evidence_failure_class", evidence_write_failures == 0L
            ? "NONE" : g_state.partial_evidence_class,
        "evidence_failure_path", evidence_write_failures == 0L
            ? "" : g_state.partial_evidence_relative_path,
        "evidence_failure_phase", evidence_write_failures == 0L
            ? "NONE" : g_state.partial_evidence_phase,
        "evidence_multiple_failures", multiple_evidence_failures != 0L
            ? Py_True : Py_False,
        "evidence_observed_bytes",
            (unsigned long long)g_state.partial_evidence_bytes,
        "evidence_observed_bytes_known", g_state.partial_evidence_size_known
            ? Py_True : Py_False,
        "evidence_requested_bytes",
            (unsigned long long)g_state.partial_evidence_requested_bytes,
        "evidence_verified_write_count", (long)verified_evidence_count,
        "evidence_write_failures", (long)evidence_write_failures,
        "outcome_first_write_observed_bytes", 0ULL,
        "outcome_first_write_observed_bytes_known", Py_False,
        "outcome_first_write_phase", "NONE",
        "outcome_first_write_requested_bytes", 0ULL,
        "outcome_multiple_failures", Py_False,
        "outcome_partial_write", Py_False,
        "outcome_write_failures", 0L,
        "prior_success_frame_bytes", 0ULL,
        "prior_success_frame_sha256", "",
        "prior_success_superseded", Py_False);
    envelope = native_evidence != NULL ? Py_BuildValue(
        "{s:O,s:O,s:s,s:s}",
        "caller_failure", failure_core,
        "native_terminal_evidence", native_evidence,
        "schema", "kira.avatar.r25.afes.native_failure_envelope.v3r6",
        "status", "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY") : NULL;
    frame = envelope != NULL ? encode_receipt_frame_object(envelope) : NULL;
    if (frame != NULL &&
        PyObject_GetBuffer(frame, &view, PyBUF_CONTIG_RO) == 0 &&
        view.len > 0 && (uint64_t)view.len <= MAX_OUTCOME_BYTES &&
        stage_terminal_outcome(
            (const unsigned char *)view.buf, (size_t)view.len,
            "CALLER_FAILURE")) {
        ok = 1;
    }
    if (view.obj != NULL) {
        PyBuffer_Release(&view);
    }
    Py_XDECREF(frame);
    Py_XDECREF(envelope);
    Py_XDECREF(native_evidence);
    if (!ok) {
        return broker_error("native_failure_outcome_stage_failed");
    }
    g_state.outcome_success_provisional = 0;
    g_state.outcome_committed = 1;
    Py_RETURN_NONE;
}

static PyObject *py_quiesce_owned_resources(PyObject *self, PyObject *args) {
    PyObject *result;
    (void)self;
    if (!PyArg_ParseTuple(args, ":quiesce_owned_resources") ||
        !require_claimed("quiesce_owned_resources")) {
        return NULL;
    }
    if (InterlockedCompareExchange(&g_state.active_child_count, 0L, 0L) != 0L) {
        result = PyTuple_New(1);
        if (result != NULL) {
            PyTuple_SET_ITEM(result, 0,
                PyUnicode_FromString("native_active_count_not_quiescent"));
            if (PyTuple_GET_ITEM(result, 0) == NULL) {
                Py_DECREF(result);
                return NULL;
            }
        }
        return result;
    }
    return PyTuple_New(0);
}

static PyObject *py_finish(PyObject *self, PyObject *args) {
    (void)self;
    if (!require_main_os_thread("finish") ||
        !PyArg_ParseTuple(args, ":finish") ||
        !require_claimed("finish")) {
        return NULL;
    }
    if (!require_all_jobs_quiescent("finish") ||
        InterlockedCompareExchange(&g_state.active_child_count, 0L, 0L) != 0L ||
        g_state.run_attempt_consumed[0] < 0L ||
        g_state.run_attempt_consumed[1] < 0L) {
        return broker_error("native_finish_all_jobs_quiescent_refused");
    }
    g_state.lifecycle = CONSUMED;
    if (!g_state.outcome_committed) {
        /* Do not mask an earlier Python exception in the bootstrap finally.
         * The native main will reject a normal return without a committed
         * outcome and will record the original exception when available. */
        Py_RETURN_NONE;
    }
    if (InterlockedCompareExchange(&g_state.active_child_count, 0L, 0L) != 0L) {
        return broker_error("native_finish_active_count_refused");
    }
    g_state.finished = 1;
    Py_RETURN_NONE;
}

static int byte_buffer_reserve(ByteBuffer *buffer, size_t required) {
    unsigned char *expanded;
    size_t capacity;
    if (required <= buffer->capacity) {
        return 1;
    }
    capacity = buffer->capacity == 0U ? 4096U : buffer->capacity;
    while (capacity < required) {
        if (capacity > SIZE_MAX / 2U) {
            return 0;
        }
        capacity *= 2U;
    }
    expanded = (unsigned char *)realloc(buffer->data, capacity);
    if (expanded == NULL) {
        return 0;
    }
    buffer->data = expanded;
    buffer->capacity = capacity;
    return 1;
}

static DWORD WINAPI drain_thread_main(LPVOID parameter) {
    DrainContext *context = (DrainContext *)parameter;
    unsigned char temporary[65536];
    HANDLE overlapped_event = NULL;
    if (context->overlapped_read) {
        overlapped_event = CreateEventW(NULL, TRUE, FALSE, NULL);
        if (overlapped_event == NULL) {
            context->read_error = GetLastError();
            return 0U;
        }
    }
    for (;;) {
        DWORD count = 0U;
        DWORD code = ERROR_SUCCESS;
        BOOL read_ok;
        if (context->overlapped_read) {
            OVERLAPPED operation;
            DWORD wait_result;
            memset(&operation, 0, sizeof(operation));
            ResetEvent(overlapped_event);
            operation.hEvent = overlapped_event;
            read_ok = ReadFile(
                context->read_handle, temporary, sizeof(temporary), NULL,
                &operation);
            if (!read_ok) {
                code = GetLastError();
                if (code == ERROR_IO_PENDING) {
                    wait_result = WaitForSingleObject(overlapped_event, INFINITE);
                    if (wait_result == WAIT_OBJECT_0 && GetOverlappedResult(
                            context->read_handle, &operation, &count, FALSE)) {
                        read_ok = TRUE;
                        code = ERROR_SUCCESS;
                    } else {
                        code = wait_result == WAIT_OBJECT_0
                            ? GetLastError() : ERROR_INVALID_DATA;
                    }
                }
            } else if (!GetOverlappedResult(
                    context->read_handle, &operation, &count, TRUE)) {
                read_ok = FALSE;
                code = GetLastError();
            }
        } else {
            read_ok = ReadFile(
                context->read_handle, temporary, sizeof(temporary), &count,
                NULL);
            if (!read_ok) {
                code = GetLastError();
            }
        }
        if (!read_ok) {
            if (code != ERROR_BROKEN_PIPE && code != ERROR_HANDLE_EOF &&
                code != ERROR_OPERATION_ABORTED) {
                context->read_error = code;
            }
            break;
        }
        if (count == 0U) {
            break;
        }
        if (UINT64_MAX - context->total_bytes < count) {
            context->overflow = 1;
            context->total_bytes = UINT64_MAX;
        } else {
            context->total_bytes += count;
        }
        if (context->captured.size < context->maximum) {
            size_t available = context->maximum - context->captured.size;
            size_t keep = count < available ? (size_t)count : available;
            if (keep != 0U) {
                if (!byte_buffer_reserve(
                        &context->captured, context->captured.size + keep)) {
                    context->read_error = ERROR_NOT_ENOUGH_MEMORY;
                    context->overflow = 1;
                    /* Continue draining even when evidence cannot be kept. */
                } else {
                    memcpy(
                        context->captured.data + context->captured.size,
                        temporary, keep
                    );
                    context->captured.size += keep;
                }
            }
            if ((size_t)count > keep) {
                context->overflow = 1;
            }
        } else {
            context->overflow = 1;
        }
    }
    if (overlapped_event != NULL) {
        CloseHandle(overlapped_event);
    }
    secure_zero(temporary, sizeof(temporary));
    return 0U;
}

static void cleanup_record_drop(
    CleanupList *list, const char *description
) {
    list->recording_failed = 1;
    if (list->dropped_count != SIZE_MAX) {
        ++list->dropped_count;
    }
    if (list->first_dropped_error[0] == '\0') {
        strncpy_s(
            list->first_dropped_error, sizeof(list->first_dropped_error),
            description != NULL ? description : "cleanup_error_unavailable",
            _TRUNCATE);
    }
}

static int cleanup_add(CleanupList *list, const char *format, ...) {
    va_list arguments;
    char temporary[384];
    char *copy;
    va_start(arguments, format);
    _vsnprintf_s(temporary, sizeof(temporary), _TRUNCATE, format, arguments);
    va_end(arguments);
    if (list->count == list->capacity) {
        size_t capacity = list->capacity == 0U ? 8U : list->capacity * 2U;
        char **expanded;
        if (capacity < list->capacity || capacity > SIZE_MAX / sizeof(char *)) {
            cleanup_record_drop(list, temporary);
            return 0;
        }
        expanded = (char **)realloc(list->items, capacity * sizeof(char *));
        if (expanded == NULL) {
            cleanup_record_drop(list, temporary);
            return 0;
        }
        list->items = expanded;
        list->capacity = capacity;
    }
    copy = duplicate_bytes_as_cstr(temporary, strlen(temporary));
    if (copy == NULL) {
        cleanup_record_drop(list, temporary);
        return 0;
    }
    list->items[list->count++] = copy;
    return 1;
}

static void cleanup_list_free(CleanupList *list) {
    size_t index;
    for (index = 0U; index < list->count; ++index) {
        free(list->items[index]);
    }
    free(list->items);
    memset(list, 0, sizeof(*list));
}

static int wait_for_job_active_processes_zero(
    HANDLE job, CleanupList *cleanup, const char *label
) {
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION accounting;
    int active_processes_are_zero;
    DWORD returned = 0U;
    DWORD wait_result;
    if (job == NULL || job == INVALID_HANDLE_VALUE) {
        (void)cleanup_add(cleanup, "%s_job_missing", label);
        return 0;
    }
    wait_result = WaitForSingleObject(job, TERMINATION_WAIT_MILLISECONDS);
    if (wait_result == WAIT_TIMEOUT) {
        if (!TerminateJobObject(job, 0xE0000003U)) {
            (void)cleanup_add(cleanup,
                "%s_job_descendant_terminate:winerror=%lu", label,
                (unsigned long)GetLastError());
        }
        /* No retained lock, snapshot, outcome commit, or lifecycle release is
         * permitted while even one Job member remains.  A forced termination
         * therefore waits without returning until the Job signals empty. */
        wait_result = WaitForSingleObject(job, INFINITE);
    }
    if (wait_result != WAIT_OBJECT_0) {
        (void)cleanup_add(cleanup, "%s_job_zero_wait:wait=%lu", label,
            (unsigned long)wait_result);
        return 0;
    }
    memset(&accounting, 0, sizeof(accounting));
    if (!QueryInformationJobObject(
            job, JobObjectBasicAccountingInformation, &accounting,
            sizeof(accounting), &returned) || returned < sizeof(accounting)) {
        (void)cleanup_add(cleanup,
            "%s_job_accounting_query_failed:winerror=%lu", label,
            (unsigned long)GetLastError());
        return 0;
    }
    active_processes_are_zero = accounting.ActiveProcesses == 0;
    if (!active_processes_are_zero) {
        (void)cleanup_add(cleanup,
            "%s_job_active_processes_not_zero:active=%lu:winerror=%lu", label,
            (unsigned long)accounting.ActiveProcesses,
            (unsigned long)GetLastError());
        return 0;
    }
    return 1;
}

static PyObject *cleanup_list_tuple(const CleanupList *list) {
    size_t total = list->count + (list->recording_failed ? 1U : 0U);
    PyObject *result;
    size_t index;
    if (total > (size_t)PY_SSIZE_T_MAX) {
        PyErr_SetString(PyExc_OverflowError, "cleanup_tuple_size_overflow");
        return NULL;
    }
    result = PyTuple_New((Py_ssize_t)total);
    if (result == NULL) {
        return NULL;
    }
    for (index = 0U; index < list->count; ++index) {
        PyObject *item = PyUnicode_FromString(list->items[index]);
        if (item == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, (Py_ssize_t)index, item);
    }
    if (list->recording_failed) {
        char sentinel[640];
        PyObject *item;
        _snprintf_s(
            sentinel, sizeof(sentinel), _TRUNCATE,
            "cleanup_error_recording_failed:dropped=%zu:first=%s",
            list->dropped_count, list->first_dropped_error);
        item = PyUnicode_FromString(sentinel);
        if (item == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, (Py_ssize_t)list->count, item);
    }
    return result;
}

static void close_handle_record(
    HANDLE *handle, CleanupList *cleanup, const char *label
) {
    if (*handle != NULL && *handle != INVALID_HANDLE_VALUE) {
        if (!CloseHandle(*handle)) {
            (void)cleanup_add(cleanup, "%s_close:winerror=%lu", label,
                (unsigned long)GetLastError());
        }
        *handle = INVALID_HANDLE_VALUE;
    }
}

static DWORD remaining_deadline_milliseconds(ULONGLONG absolute_deadline) {
    ULONGLONG now = GetTickCount64();
    ULONGLONG remaining;
    if (now >= absolute_deadline) {
        return 0U;
    }
    remaining = absolute_deadline - now;
    return remaining > (ULONGLONG)(MAXDWORD - 1U)
        ? (MAXDWORD - 1U) : (DWORD)remaining;
}

static int create_inherited_pipe(HANDLE *read_end, HANDLE *write_end) {
    SECURITY_ATTRIBUTES security;
    memset(&security, 0, sizeof(security));
    security.nLength = sizeof(security);
    security.bInheritHandle = TRUE;
    if (!CreatePipe(read_end, write_end, &security, 0U)) {
        return 0;
    }
    if (!SetHandleInformation(*read_end, HANDLE_FLAG_INHERIT, 0U)) {
        CloseHandle(*read_end);
        CloseHandle(*write_end);
        *read_end = INVALID_HANDLE_VALUE;
        *write_end = INVALID_HANDLE_VALUE;
        return 0;
    }
    return 1;
}

static int authenticate_result_pipe_root_pid(
    const wchar_t *pipe_name, DWORD expected_root_pid,
    DWORD timeout_milliseconds, HANDLE *pipe_handle, CleanupList *cleanup
) {
    SECURITY_ATTRIBUTES security;
    OVERLAPPED overlapped;
    DWORD client_pid = 0U;
    DWORD transferred = 0U;
    DWORD wait_result;
    BOOL connected;
    memset(&security, 0, sizeof(security));
    security.nLength = sizeof(security);
    security.bInheritHandle = FALSE;
    if (*pipe_handle == INVALID_HANDLE_VALUE) {
        *pipe_handle = CreateNamedPipeW(
            pipe_name,
            PIPE_ACCESS_INBOUND | FILE_FLAG_OVERLAPPED | FILE_FLAG_WRITE_THROUGH,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT |
                PIPE_REJECT_REMOTE_CLIENTS,
            1U, 65536U, 65536U, timeout_milliseconds, &security);
        if (*pipe_handle == INVALID_HANDLE_VALUE) {
            (void)cleanup_add(cleanup,
                "result_named_pipe_create_failed:winerror=%lu",
                (unsigned long)GetLastError());
            return 0;
        }
        return expected_root_pid == 0U;
    }
    if (expected_root_pid == 0U) {
        (void)cleanup_add(cleanup, "result_named_pipe_expected_root_pid_missing");
        return 0;
    }
    memset(&overlapped, 0, sizeof(overlapped));
    overlapped.hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (overlapped.hEvent == NULL) {
        (void)cleanup_add(cleanup,
            "result_named_pipe_event_failed:winerror=%lu",
            (unsigned long)GetLastError());
        return 0;
    }
    connected = ConnectNamedPipe(*pipe_handle, &overlapped);
    if (!connected) {
        DWORD code = GetLastError();
        if (code == ERROR_IO_PENDING) {
            wait_result = WaitForSingleObject(
                overlapped.hEvent, timeout_milliseconds);
            if (wait_result != WAIT_OBJECT_0 ||
                !GetOverlappedResult(
                    *pipe_handle, &overlapped, &transferred, FALSE)) {
                (void)CancelIoEx(*pipe_handle, &overlapped);
                (void)WaitForSingleObject(overlapped.hEvent, INFINITE);
                CloseHandle(overlapped.hEvent);
                (void)cleanup_add(cleanup,
                    "result_named_pipe_connect_timeout_or_failure:wait=%lu:winerror=%lu",
                    (unsigned long)wait_result, (unsigned long)GetLastError());
                return 0;
            }
        } else if (code != ERROR_PIPE_CONNECTED) {
            CloseHandle(overlapped.hEvent);
            (void)cleanup_add(cleanup,
                "result_named_pipe_connect_failed:winerror=%lu",
                (unsigned long)code);
            return 0;
        }
    }
    CloseHandle(overlapped.hEvent);
    if (!GetNamedPipeClientProcessId(*pipe_handle, &client_pid) ||
        client_pid != expected_root_pid) {
        (void)cleanup_add(cleanup,
            "named_pipe_client_pid_mismatch:client=%lu:expected=%lu:winerror=%lu",
            (unsigned long)client_pid, (unsigned long)expected_root_pid,
            (unsigned long)GetLastError());
        (void)DisconnectNamedPipe(*pipe_handle);
        return 0;
    }
    return 1;
}

static int wide_vector_add(WideVector *vector, wchar_t *owned) {
    wchar_t **expanded;
    size_t capacity;
    if (vector->count == vector->capacity) {
        capacity = vector->capacity == 0U ? 16U : vector->capacity * 2U;
        if (capacity < vector->capacity ||
            capacity > SIZE_MAX / sizeof(wchar_t *)) {
            return 0;
        }
        expanded = (wchar_t **)realloc(
            vector->items, capacity * sizeof(wchar_t *)
        );
        if (expanded == NULL) {
            return 0;
        }
        vector->items = expanded;
        vector->capacity = capacity;
    }
    vector->items[vector->count++] = owned;
    return 1;
}

static void wide_vector_free(WideVector *vector) {
    size_t index;
    for (index = 0U; index < vector->count; ++index) {
        free(vector->items[index]);
    }
    free(vector->items);
    memset(vector, 0, sizeof(*vector));
}

typedef struct WideBuilder {
    wchar_t *data;
    size_t size;
    size_t capacity;
} WideBuilder;

static int wide_builder_reserve(WideBuilder *builder, size_t required) {
    wchar_t *expanded;
    size_t capacity = builder->capacity == 0U ? 256U : builder->capacity;
    if (required <= builder->capacity) {
        return 1;
    }
    while (capacity < required) {
        if (capacity > SIZE_MAX / 2U) {
            return 0;
        }
        capacity *= 2U;
    }
    expanded = (wchar_t *)realloc(builder->data, capacity * sizeof(wchar_t));
    if (expanded == NULL) {
        return 0;
    }
    builder->data = expanded;
    builder->capacity = capacity;
    return 1;
}

static int wide_builder_char(WideBuilder *builder, wchar_t value) {
    if (!wide_builder_reserve(builder, builder->size + 2U)) {
        return 0;
    }
    builder->data[builder->size++] = value;
    builder->data[builder->size] = L'\0';
    return 1;
}

static int wide_builder_repeat(
    WideBuilder *builder, wchar_t value, size_t count
) {
    size_t index;
    if (!wide_builder_reserve(builder, builder->size + count + 1U)) {
        return 0;
    }
    for (index = 0U; index < count; ++index) {
        builder->data[builder->size++] = value;
    }
    builder->data[builder->size] = L'\0';
    return 1;
}

static int append_quoted_windows_argument(
    WideBuilder *builder, const wchar_t *argument
) {
    const wchar_t *cursor;
    int quote;
    size_t backslashes = 0U;
    if (argument == NULL) {
        return 0;
    }
    quote = argument[0] == L'\0' || wcspbrk(argument, L" \t\n\v\"") != NULL;
    if (!quote) {
        for (cursor = argument; *cursor != L'\0'; ++cursor) {
            if (!wide_builder_char(builder, *cursor)) {
                return 0;
            }
        }
        return 1;
    }
    if (!wide_builder_char(builder, L'\"')) {
        return 0;
    }
    for (cursor = argument; ; ++cursor) {
        if (*cursor == L'\\') {
            ++backslashes;
            continue;
        }
        if (*cursor == L'\"') {
            if (!wide_builder_repeat(builder, L'\\', backslashes * 2U + 1U) ||
                !wide_builder_char(builder, L'\"')) {
                return 0;
            }
            backslashes = 0U;
            continue;
        }
        if (*cursor == L'\0') {
            if (!wide_builder_repeat(builder, L'\\', backslashes * 2U) ||
                !wide_builder_char(builder, L'\"')) {
                return 0;
            }
            break;
        }
        if (!wide_builder_repeat(builder, L'\\', backslashes) ||
            !wide_builder_char(builder, *cursor)) {
            return 0;
        }
        backslashes = 0U;
    }
    return 1;
}

static wchar_t *build_command_line(const WideVector *arguments) {
    WideBuilder builder = {0};
    size_t index;
    if (arguments->count == 0U) {
        return NULL;
    }
    for (index = 0U; index < arguments->count; ++index) {
        if (index != 0U && !wide_builder_char(&builder, L' ')) {
            free(builder.data);
            return NULL;
        }
        if (!append_quoted_windows_argument(&builder, arguments->items[index])) {
            free(builder.data);
            return NULL;
        }
    }
    return builder.data;
}

static int compare_environment_entries(const void *left, const void *right) {
    const wchar_t *const *left_value = (const wchar_t *const *)left;
    const wchar_t *const *right_value = (const wchar_t *const *)right;
    int insensitive = _wcsicmp(*left_value, *right_value);
    return insensitive != 0 ? insensitive : wcscmp(*left_value, *right_value);
}

static wchar_t *build_environment_block(PyObject *environment) {
    static const wchar_t *exact_environment_keys[] = {
        L"SYSTEMROOT", L"WINDIR", L"USERNAME", L"TEMP", L"TMP",
        L"BLENDER_USER_CONFIG", L"BLENDER_USER_SCRIPTS",
        L"BLENDER_USER_DATAFILES", L"PYTHONPYCACHEPREFIX",
        L"PYTHONNOUSERSITE", L"PYTHONDONTWRITEBYTECODE", L"PYTHONHASHSEED"
    };
    Py_ssize_t position = 0;
    Py_ssize_t environment_exact_key_count;
    PyObject *key;
    PyObject *value;
    WideVector entries = {0};
    size_t total = 1U;
    size_t index;
    wchar_t *block;
    wchar_t *cursor;
    if (!PyDict_CheckExact(environment)) {
        PyErr_SetString(PyExc_TypeError, "environment_exact_dict_required");
        return NULL;
    }
    environment_exact_key_count = PyDict_Size(environment);
    if (environment_exact_key_count !=
        (Py_ssize_t)(sizeof(exact_environment_keys) /
                     sizeof(exact_environment_keys[0]))) {
        PyErr_SetString(PyExc_ValueError, "environment_exact_key_count_drift");
        return NULL;
    }
    while (PyDict_Next(environment, &position, &key, &value)) {
        wchar_t *wide_key = py_unicode_to_wide_exact(key);
        wchar_t *wide_value = NULL;
        wchar_t *entry = NULL;
        size_t key_length;
        size_t value_length;
        size_t allowed_index;
        int exact_key = 0;
        if (wide_key == NULL) {
            wide_vector_free(&entries);
            return NULL;
        }
        wide_value = py_unicode_to_wide_exact(value);
        if (wide_value == NULL) {
            free(wide_key);
            wide_vector_free(&entries);
            return NULL;
        }
        key_length = wcslen(wide_key);
        value_length = wcslen(wide_value);
        for (allowed_index = 0U;
             allowed_index < sizeof(exact_environment_keys) /
                 sizeof(exact_environment_keys[0]);
             ++allowed_index) {
            if (wcscmp(wide_key, exact_environment_keys[allowed_index]) == 0) {
                exact_key = 1;
                break;
            }
        }
        if (key_length == 0U || wide_key[0] == L'=' ||
            wcschr(wide_key, L'=') != NULL || wcschr(wide_value, L'\0') == NULL ||
            key_length > 32767U || value_length > 32767U ||
            key_length > SIZE_MAX - value_length - 2U || !exact_key) {
            free(wide_key);
            free(wide_value);
            wide_vector_free(&entries);
            PyErr_SetString(PyExc_ValueError,
                exact_key ? "invalid_environment_entry" :
                    "unknown_exact_environment_key");
            return NULL;
        }
        entry = (wchar_t *)malloc(
            (key_length + value_length + 2U) * sizeof(wchar_t)
        );
        if (entry == NULL) {
            free(wide_key);
            free(wide_value);
            wide_vector_free(&entries);
            PyErr_NoMemory();
            return NULL;
        }
        memcpy(entry, wide_key, key_length * sizeof(wchar_t));
        entry[key_length] = L'=';
        memcpy(entry + key_length + 1U, wide_value,
            (value_length + 1U) * sizeof(wchar_t));
        free(wide_key);
        free(wide_value);
        if (!wide_vector_add(&entries, entry)) {
            free(entry);
            wide_vector_free(&entries);
            PyErr_NoMemory();
            return NULL;
        }
    }
    qsort(entries.items, entries.count, sizeof(wchar_t *),
        compare_environment_entries);
    for (index = 0U; index < entries.count; ++index) {
        if (index != 0U) {
            const wchar_t *previous = entries.items[index - 1U];
            const wchar_t *current = entries.items[index];
            size_t previous_key = (size_t)(wcschr(previous, L'=') - previous);
            size_t current_key = (size_t)(wcschr(current, L'=') - current);
            if (previous_key == current_key &&
                _wcsnicmp(previous, current, previous_key) == 0) {
                wide_vector_free(&entries);
                PyErr_SetString(PyExc_ValueError,
                    "case_insensitive_environment_duplicate");
                return NULL;
            }
        }
        if (total > SIZE_MAX - wcslen(entries.items[index]) - 1U) {
            wide_vector_free(&entries);
            PyErr_SetString(PyExc_OverflowError, "environment_block_too_large");
            return NULL;
        }
        total += wcslen(entries.items[index]) + 1U;
    }
    block = (wchar_t *)calloc(total, sizeof(wchar_t));
    if (block == NULL) {
        wide_vector_free(&entries);
        PyErr_NoMemory();
        return NULL;
    }
    cursor = block;
    for (index = 0U; index < entries.count; ++index) {
        size_t length = wcslen(entries.items[index]);
        memcpy(cursor, entries.items[index], (length + 1U) * sizeof(wchar_t));
        cursor += length + 1U;
    }
    *cursor = L'\0';
    wide_vector_free(&entries);
    return block;
}

static int exact_plan_keys(PyObject *plan) {
    static const char *allowed[] = {
        "schema", "contract_sha256", "contract_bytes",
        "blender_executable", "foundation_blend", "execution_wrapper",
        "output_relative_path", "outcome_relative_path", "process_contract",
        "outer_truth_boundary", "contract", "v5", "v2"
    };
    Py_ssize_t position = 0;
    PyObject *key;
    PyObject *value;
    if (!PyDict_CheckExact(plan)) {
        PyErr_SetString(PyExc_TypeError, "plan_exact_dict_required");
        return 0;
    }
    if (PyDict_Size(plan) != (Py_ssize_t)(sizeof(allowed) / sizeof(allowed[0]))) {
        PyErr_SetString(PyExc_ValueError, "child_plan_exact_key_count_drift");
        return 0;
    }
    while (PyDict_Next(plan, &position, &key, &value)) {
        const char *text;
        Py_ssize_t length;
        size_t index;
        int known = 0;
        (void)value;
        if (!py_unicode_to_utf8_exact(key, &text, &length)) {
            return 0;
        }
        for (index = 0U; index < sizeof(allowed) / sizeof(allowed[0]); ++index) {
            if ((size_t)length == strlen(allowed[index]) &&
                memcmp(text, allowed[index], (size_t)length) == 0) {
                known = 1;
                break;
            }
        }
        if (!known) {
            PyErr_SetString(PyExc_ValueError, "unknown_child_plan_key");
            return 0;
        }
    }
    return 1;
}

static int add_wide_copy(WideVector *vector, const wchar_t *value) {
    wchar_t *copy = duplicate_wide(value);
    if (copy == NULL || !wide_vector_add(vector, copy)) {
        free(copy);
        PyErr_NoMemory();
        return 0;
    }
    return 1;
}

static wchar_t *join_unique_cache_child(
    const wchar_t *unique_run_cache_root, const wchar_t *leaf
) {
    size_t root_length;
    size_t leaf_length;
    wchar_t *joined;
    wchar_t *canonical;
    if (unique_run_cache_root == NULL ||
        !path_is_absolute(unique_run_cache_root) ||
        !safe_relative_path(leaf, 0)) {
        return NULL;
    }
    root_length = wcslen(unique_run_cache_root);
    leaf_length = wcslen(leaf);
    if (root_length > SIZE_MAX - leaf_length - 2U) {
        return NULL;
    }
    joined = (wchar_t *)malloc(
        (root_length + leaf_length + 2U) * sizeof(wchar_t));
    if (joined == NULL) {
        return NULL;
    }
    memcpy(joined, unique_run_cache_root, root_length * sizeof(wchar_t));
    joined[root_length] = L'\\';
    memcpy(joined + root_length + 1U, leaf,
        (leaf_length + 1U) * sizeof(wchar_t));
    canonical = canonical_full_path(joined);
    free(joined);
    if (canonical == NULL ||
        _wcsnicmp(canonical, unique_run_cache_root, root_length) != 0 ||
        canonical[root_length] != L'\\') {
        free(canonical);
        return NULL;
    }
    return canonical;
}

static int verify_cache_root_handle(
    HANDLE handle, const wchar_t *path
) {
    return verify_new_output_handle(handle, path, 1, NULL) &&
        verify_output_ancestor_chain();
}

static wchar_t *create_sealed_cache_directory(
    const wchar_t *unique_run_cache_root, const wchar_t *leaf
) {
    wchar_t *path = join_unique_cache_child(unique_run_cache_root, leaf);
    HANDLE handle = INVALID_HANDLE_VALUE;
    DWORD code;
    if (path == NULL || !hold_every_path_ancestor(path) ||
        !verify_output_ancestor_chain()) {
        free(path);
        PyErr_SetString(PyExc_RuntimeError,
            "cache_directory_ancestor_identity_refused");
        return NULL;
    }
    if (!CreateDirectoryW(path, NULL)) {
        code = GetLastError();
        free(path);
        PyErr_Format(PyExc_RuntimeError,
            code == ERROR_ALREADY_EXISTS
                ? "cache_directory_nonce_collision:winerror=%lu"
                : "cache_directory_create_failed:winerror=%lu",
            (unsigned long)code);
        return NULL;
    }
    handle = CreateFileW(
        path, FILE_READ_ATTRIBUTES | SYNCHRONIZE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (handle == INVALID_HANDLE_VALUE ||
        !verify_cache_root_handle(handle, path)) {
        code = GetLastError();
        if (handle != INVALID_HANDLE_VALUE) {
            CloseHandle(handle);
        }
        free(path);
        PyErr_Format(PyExc_RuntimeError,
            "cache_directory_handle_seal_failed:winerror=%lu",
            (unsigned long)code);
        return NULL;
    }
    CloseHandle(handle);
    return path;
}

static wchar_t *create_unique_cache_root(
    const char *pair_nonce, const char *run_nonce
) {
    static const wchar_t *required_children[] = {
        L"temp", L"blender_config", L"blender_scripts",
        L"blender_datafiles", L"python_pycache"
    };
    wchar_t *pair_wide = NULL;
    wchar_t *run_wide = NULL;
    wchar_t relative[384];
    wchar_t *root = NULL;
    HANDLE root_handle = INVALID_HANDLE_VALUE;
    DWORD code = ERROR_SUCCESS;
    size_t index;
    if (pair_nonce == NULL || run_nonce == NULL ||
        !is_lower_hex64(pair_nonce) || !is_lower_hex64(run_nonce)) {
        PyErr_SetString(PyExc_ValueError, "cache_nonce_identity_refused");
        return NULL;
    }
    pair_wide = utf8_to_wide_strict(pair_nonce, 64U);
    run_wide = utf8_to_wide_strict(run_nonce, 64U);
    if (pair_wide == NULL || run_wide == NULL ||
        _snwprintf_s(relative, sizeof(relative) / sizeof(relative[0]),
            _TRUNCATE,
            L"RecoverySprint\\runtime_cache\\r25_afes_v3r6-%ls-%ls",
            pair_wide, run_wide) < 0) {
        free(pair_wide);
        free(run_wide);
        PyErr_SetString(PyExc_RuntimeError, "cache_root_name_failed");
        return NULL;
    }
    free(pair_wide);
    free(run_wide);
    root = join_project_relative(relative);
    if (root == NULL || !hold_every_path_ancestor(root) ||
        !verify_output_ancestor_chain()) {
        free(root);
        PyErr_SetString(PyExc_RuntimeError,
            "cache_root_parent_identity_refused");
        return NULL;
    }
    if (!CreateDirectoryW(root, NULL)) {
        code = GetLastError();
        free(root);
        PyErr_Format(PyExc_RuntimeError,
            code == ERROR_ALREADY_EXISTS
                ? "cache_root_nonce_collision:winerror=%lu"
                : "cache_root_create_failed:winerror=%lu",
            (unsigned long)code);
        return NULL;
    }
    root_handle = CreateFileW(
        root, FILE_READ_ATTRIBUTES | SYNCHRONIZE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (root_handle == INVALID_HANDLE_VALUE ||
        !verify_cache_root_handle(root_handle, root)) {
        code = GetLastError();
        if (root_handle != INVALID_HANDLE_VALUE) {
            CloseHandle(root_handle);
        }
        free(root);
        PyErr_Format(PyExc_RuntimeError,
            "cache_root_handle_seal_failed:winerror=%lu",
            (unsigned long)code);
        return NULL;
    }
    CloseHandle(root_handle);
    for (index = 0U;
         index < sizeof(required_children) / sizeof(required_children[0]);
         ++index) {
        wchar_t *child = create_sealed_cache_directory(
            root, required_children[index]);
        if (child == NULL) {
            free(root);
            return NULL;
        }
        free(child);
    }
    return root;
}

static PyObject *native_restricted_environment(
    const wchar_t *unique_run_cache_root
) {
    static const wchar_t *inherited_names[] = {
        L"SYSTEMROOT", L"WINDIR", L"USERNAME"
    };
    static const char *mutable_names[] = {
        "TEMP", "TMP", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS",
        "BLENDER_USER_DATAFILES", "PYTHONPYCACHEPREFIX"
    };
    static const wchar_t *mutable_leafs[] = {
        L"temp", L"temp", L"blender_config", L"blender_scripts",
        L"blender_datafiles", L"python_pycache"
    };
    static const char *constant_names[] = {
        "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED"
    };
    static const char *constant_values[] = {"1", "1", "0"};
    PyObject *result = PyDict_New();
    size_t index;
    /* PATH_OMITTED_BY_DESIGN: every executable and retained input is absolute. */
    if (result == NULL || unique_run_cache_root == NULL ||
        !path_is_absolute(unique_run_cache_root)) {
        Py_XDECREF(result);
        return broker_error("unique_run_cache_root_required");
    }
    for (index = 0U;
         index < sizeof(inherited_names) / sizeof(inherited_names[0]);
         ++index) {
        DWORD required;
        wchar_t *value;
        PyObject *key_object;
        PyObject *value_object;
        SetLastError(ERROR_SUCCESS);
        required = GetEnvironmentVariableW(inherited_names[index], NULL, 0U);
        if (required == 0U) {
            Py_DECREF(result);
            return broker_error("required_windows_environment_missing");
        }
        value = (wchar_t *)malloc(((size_t)required + 1U) * sizeof(wchar_t));
        if (value == NULL || GetEnvironmentVariableW(
                inherited_names[index], value, required + 1U) == 0U) {
            free(value);
            Py_DECREF(result);
            return broker_error("required_windows_environment_read_failed");
        }
        key_object = PyUnicode_FromWideChar(inherited_names[index], -1);
        value_object = PyUnicode_FromWideChar(value, -1);
        free(value);
        if (key_object == NULL || value_object == NULL ||
            PyDict_SetItem(result, key_object, value_object) < 0) {
            Py_XDECREF(key_object);
            Py_XDECREF(value_object);
            Py_DECREF(result);
            return NULL;
        }
        Py_DECREF(key_object);
        Py_DECREF(value_object);
    }
    for (index = 0U;
         index < sizeof(mutable_names) / sizeof(mutable_names[0]);
         ++index) {
        wchar_t *value = join_unique_cache_child(
            unique_run_cache_root, mutable_leafs[index]);
        PyObject *value_object;
        DWORD attributes;
        if (value == NULL) {
            Py_DECREF(result);
            return broker_error("mutable_environment_path_failed");
        }
        attributes = GetFileAttributesW(value);
        if (attributes == INVALID_FILE_ATTRIBUTES ||
            (attributes & FILE_ATTRIBUTE_DIRECTORY) == 0U ||
            (attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0U ||
            !verify_output_ancestor_chain()) {
            free(value);
            Py_DECREF(result);
            return broker_error("mutable_environment_directory_not_sealed");
        }
        value_object = PyUnicode_FromWideChar(value, -1);
        free(value);
        if (value_object == NULL || PyDict_SetItemString(
                result, mutable_names[index], value_object) < 0) {
            Py_XDECREF(value_object);
            Py_DECREF(result);
            return NULL;
        }
        Py_DECREF(value_object);
    }
    for (index = 0U;
         index < sizeof(constant_names) / sizeof(constant_names[0]);
         ++index) {
        PyObject *value_object = PyUnicode_FromString(constant_values[index]);
        if (value_object == NULL || PyDict_SetItemString(
                result, constant_names[index], value_object) < 0) {
            Py_XDECREF(value_object);
            Py_DECREF(result);
            return NULL;
        }
        Py_DECREF(value_object);
    }
    if (PyDict_Size(result) != 12) {
        Py_DECREF(result);
        return broker_error("restricted_environment_exact_key_count_drift");
    }
    return result;
}

static RetainedRow *plan_locked_path_row(
    PyObject *plan, const char *key, const char *expected_label
) {
    PyObject *value = PyDict_GetItemString(plan, key);
    wchar_t *path;
    RetainedRow *row;
    if (value == NULL) {
        PyErr_Format(PyExc_ValueError, "plan_path_missing:%s", key);
        return NULL;
    }
    path = py_unicode_to_wide_exact(value);
    if (path == NULL) {
        return NULL;
    }
    row = find_row_by_path(path, NULL);
    free(path);
    if (row == NULL || strcmp(row->label_utf8, expected_label) != 0) {
        PyErr_Format(PyExc_ValueError, "plan_path_not_exact_locked_row:%s", key);
        return NULL;
    }
    return row;
}

static int cancel_join_and_destroy_drain(
    HANDLE *thread, DrainContext **context_pointer, DrainContext *snapshot,
    CleanupList *cleanup, const char *label
) {
    DrainContext *context = *context_pointer;
    DWORD wait_result;
    int ok = 1;
    memset(snapshot, 0, sizeof(*snapshot));
    snapshot->read_handle = INVALID_HANDLE_VALUE;
    if (context == NULL) {
        return 1;
    }
    if (*thread == NULL || *thread == INVALID_HANDLE_VALUE) {
        wait_result = WAIT_OBJECT_0;
    } else {
        wait_result = WaitForSingleObject(*thread, DRAIN_JOIN_MILLISECONDS);
    }
    if (*thread != NULL && *thread != INVALID_HANDLE_VALUE &&
        wait_result != WAIT_OBJECT_0) {
        BOOL cancelled = context->overlapped_read
            ? CancelIoEx(context->read_handle, NULL)
            : CancelSynchronousIo(*thread);
        if (!cancelled) {
            DWORD code = GetLastError();
            if (code != ERROR_NOT_FOUND) {
                (void)cleanup_add(cleanup,
                    "%s_cancel:winerror=%lu", label, (unsigned long)code);
            }
        }
        /* The heap DrainContext is not freed and this function cannot return
         * until the worker has definitely stopped referencing it. */
        wait_result = WaitForSingleObject(*thread, INFINITE);
    }
    if (wait_result != WAIT_OBJECT_0) {
        (void)cleanup_add(cleanup, "%s_join:wait=%lu", label,
            (unsigned long)wait_result);
        ok = 0;
    } else if (*thread != NULL && *thread != INVALID_HANDLE_VALUE) {
        DWORD thread_exit = STILL_ACTIVE;
        if (!GetExitCodeThread(*thread, &thread_exit) ||
            thread_exit == STILL_ACTIVE) {
            (void)cleanup_add(cleanup,
                "%s_join_not_verified:winerror=%lu", label,
                (unsigned long)GetLastError());
            ok = 0;
        }
    }
    if (*thread != NULL && *thread != INVALID_HANDLE_VALUE) {
        close_handle_record(thread, cleanup, label);
    }
    /* The context is the sole read-handle owner after explicit transfer.
     * Close it exactly once here and clear it before copying evidence-only
     * state to the snapshot. */
    close_handle_record(&context->read_handle, cleanup, label);
    *snapshot = *context;
    snapshot->read_handle = INVALID_HANDLE_VALUE;
    secure_zero(context, sizeof(*context));
    free(context);
    *context_pointer = NULL;
    return ok;
}

static PyObject *make_child_result(
    const DrainContext *frame,
    const DrainContext *stdout_context,
    const DrainContext *stderr_context,
    DWORD process_id,
    DWORD exit_code,
    int have_exit,
    int timed_out,
    const wchar_t *result_pipe_name,
    const char *pair_nonce,
    const char *run_nonce,
    const CleanupList *cleanup
) {
    PyObject *result = PyDict_New();
    PyObject *frame_bytes = NULL;
    PyObject *stdout_bytes = NULL;
    PyObject *stderr_bytes = NULL;
    PyObject *pid = NULL;
    PyObject *exit = NULL;
    PyObject *cleanup_tuple = NULL;
    PyObject *result_pipe = NULL;
    PyObject *pair_nonce_object = NULL;
    PyObject *run_nonce_object = NULL;
    PyObject *stdout_total = NULL;
    PyObject *stderr_total = NULL;
    PyObject *stdout_hash_object = NULL;
    PyObject *stderr_hash_object = NULL;
    unsigned char stdout_hash[32];
    unsigned char stderr_hash[32];
    char stdout_hash_hex[65];
    char stderr_hash_hex[65];
    PyObject *timed = timed_out ? Py_True : Py_False;
    PyObject *frame_overflow = frame->overflow ? Py_True : Py_False;
    PyObject *stdout_overflow = stdout_context->overflow ? Py_True : Py_False;
    PyObject *stderr_overflow = stderr_context->overflow ? Py_True : Py_False;
    if (result == NULL ||
        !sha256_memory(stdout_context->captured.data,
            stdout_context->captured.size, stdout_hash) ||
        !sha256_memory(stderr_context->captured.data,
            stderr_context->captured.size, stderr_hash)) {
        Py_XDECREF(result);
        PyErr_SetString(PyExc_RuntimeError, "child_capture_digest_failed");
        return NULL;
    }
    hex_encode32(stdout_hash, stdout_hash_hex);
    hex_encode32(stderr_hash, stderr_hash_hex);
    secure_zero(stdout_hash, sizeof(stdout_hash));
    secure_zero(stderr_hash, sizeof(stderr_hash));
    frame_bytes = PyBytes_FromStringAndSize(
        (const char *)frame->captured.data, (Py_ssize_t)frame->captured.size);
    stdout_bytes = PyBytes_FromStringAndSize(
        (const char *)stdout_context->captured.data,
        (Py_ssize_t)stdout_context->captured.size);
    stderr_bytes = PyBytes_FromStringAndSize(
        (const char *)stderr_context->captured.data,
        (Py_ssize_t)stderr_context->captured.size);
    pid = PyLong_FromUnsignedLong((unsigned long)process_id);
    if (have_exit) {
        exit = PyLong_FromUnsignedLong((unsigned long)exit_code);
    } else {
        exit = Py_NewRef(Py_None);
    }
    cleanup_tuple = cleanup_list_tuple(cleanup);
    result_pipe = PyUnicode_FromWideChar(result_pipe_name, -1);
    pair_nonce_object = PyUnicode_FromStringAndSize(pair_nonce, 64);
    run_nonce_object = PyUnicode_FromStringAndSize(run_nonce, 64);
    stdout_total = PyLong_FromUnsignedLongLong(stdout_context->total_bytes);
    stderr_total = PyLong_FromUnsignedLongLong(stderr_context->total_bytes);
    stdout_hash_object = PyUnicode_FromStringAndSize(stdout_hash_hex, 64);
    stderr_hash_object = PyUnicode_FromStringAndSize(stderr_hash_hex, 64);
    Py_INCREF(timed);
    Py_INCREF(frame_overflow);
    Py_INCREF(stdout_overflow);
    Py_INCREF(stderr_overflow);
    if (frame_bytes == NULL || stdout_bytes == NULL || stderr_bytes == NULL ||
        pid == NULL || exit == NULL || cleanup_tuple == NULL ||
        result_pipe == NULL || pair_nonce_object == NULL ||
        run_nonce_object == NULL || stdout_total == NULL ||
        stderr_total == NULL ||
        stdout_hash_object == NULL || stderr_hash_object == NULL ||
        PyDict_SetItemString(result, "frame", frame_bytes) < 0 ||
        PyDict_SetItemString(result, "stdout", stdout_bytes) < 0 ||
        PyDict_SetItemString(result, "stderr", stderr_bytes) < 0 ||
        PyDict_SetItemString(result, "pid", pid) < 0 ||
        PyDict_SetItemString(result, "exit", exit) < 0 ||
        PyDict_SetItemString(result, "exit_code", exit) < 0 ||
        PyDict_SetItemString(result, "result_pipe_name", result_pipe) < 0 ||
        PyDict_SetItemString(
            result, "pair_session_nonce", pair_nonce_object) < 0 ||
        PyDict_SetItemString(result, "run_nonce", run_nonce_object) < 0 ||
        PyDict_SetItemString(result, "cleanup", cleanup_tuple) < 0 ||
        PyDict_SetItemString(result, "cleanup_errors", cleanup_tuple) < 0 ||
        PyDict_SetItemString(result, "stdout_total_bytes", stdout_total) < 0 ||
        PyDict_SetItemString(result, "stderr_total_bytes", stderr_total) < 0 ||
        PyDict_SetItemString(result, "stdout_sha256", stdout_hash_object) < 0 ||
        PyDict_SetItemString(result, "stderr_sha256", stderr_hash_object) < 0 ||
        PyDict_SetItemString(result, "timed_out", timed) < 0 ||
        PyDict_SetItemString(result, "frame_overflow", frame_overflow) < 0 ||
        PyDict_SetItemString(result, "stdout_overflow", stdout_overflow) < 0 ||
        PyDict_SetItemString(result, "stderr_overflow", stderr_overflow) < 0) {
        Py_CLEAR(result);
    }
    Py_XDECREF(frame_bytes);
    Py_XDECREF(stdout_bytes);
    Py_XDECREF(stderr_bytes);
    Py_XDECREF(pid);
    Py_XDECREF(exit);
    Py_XDECREF(cleanup_tuple);
    Py_XDECREF(result_pipe);
    Py_XDECREF(pair_nonce_object);
    Py_XDECREF(run_nonce_object);
    Py_XDECREF(stdout_total);
    Py_XDECREF(stderr_total);
    Py_XDECREF(stdout_hash_object);
    Py_XDECREF(stderr_hash_object);
    Py_DECREF(timed);
    Py_DECREF(frame_overflow);
    Py_DECREF(stdout_overflow);
    Py_DECREF(stderr_overflow);
    return result;
}

static void set_composite_child_error(
    const char *primary, const CleanupList *cleanup
) {
    char message[2048];
    size_t offset;
    size_t index;
    offset = (size_t)_snprintf_s(
        message, sizeof(message), _TRUNCATE, "%s", primary
    );
    if (offset >= sizeof(message)) {
        offset = sizeof(message) - 1U;
    }
    for (index = 0U; index < cleanup->count && offset < sizeof(message) - 1U;
         ++index) {
        int written = _snprintf_s(
            message + offset, sizeof(message) - offset, _TRUNCATE,
            "%s%s", index == 0U ? "|cleanup=" : ";", cleanup->items[index]
        );
        if (written < 0) {
            break;
        }
        offset += (size_t)written;
    }
    if (cleanup->recording_failed && offset < sizeof(message) - 1U) {
        (void)_snprintf_s(
            message + offset, sizeof(message) - offset, _TRUNCATE,
            "%scleanup_error_recording_failed:dropped=%zu:first=%s",
            cleanup->count == 0U ? "|cleanup=" : ";",
            cleanup->dropped_count, cleanup->first_dropped_error);
    }
    PyErr_SetString(PyExc_RuntimeError, message);
}

static PyObject *py_run_child(PyObject *self, PyObject *args) {
    PyObject *plan;
    PyObject *run_number_object;
    long run_number;
    const char *pair_nonce;
    const char *run_nonce;
    RetainedRow *executable_row;
    RetainedRow *foundation_row;
    RetainedRow *wrapper_row;
    wchar_t *executable_launch_path = NULL;
    wchar_t *foundation_launch_path = NULL;
    wchar_t *wrapper_launch_path = NULL;
    PyObject *environment_object = NULL;
    PyObject *contract_hash_object;
    PyObject *schema_object;
    const char *contract_hash;
    const char *schema;
    Py_ssize_t contract_hash_length;
    Py_ssize_t schema_length;
    wchar_t *cwd = NULL;
    wchar_t *unique_run_cache_root = NULL;
    wchar_t *environment_block = NULL;
    WideVector arguments = {0};
    wchar_t *command_line = NULL;
    DWORD timeout_milliseconds;
    ULONGLONG absolute_deadline;
    size_t max_frame = 1048628U;
    size_t max_stdout = 4U * 1024U * 1024U;
    size_t max_stderr = 4U * 1024U * 1024U;
    HANDLE frame_read = INVALID_HANDLE_VALUE;
    HANDLE stdout_read = INVALID_HANDLE_VALUE;
    HANDLE stdout_write = INVALID_HANDLE_VALUE;
    HANDLE stderr_read = INVALID_HANDLE_VALUE;
    HANDLE stderr_write = INVALID_HANDLE_VALUE;
    HANDLE null_input = INVALID_HANDLE_VALUE;
    HANDLE job = INVALID_HANDLE_VALUE;
    HANDLE drain_threads[3] = {INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE,
        INVALID_HANDLE_VALUE};
    DrainContext *drains[3] = {NULL, NULL, NULL};
    DrainContext drain_snapshots[3];
    CleanupList cleanup = {0};
    STARTUPINFOEXW startup;
    PROCESS_INFORMATION process;
    SIZE_T attribute_size = 0U;
    LPPROC_THREAD_ATTRIBUTE_LIST attributes = NULL;
    HANDLE inherited_handles[3];
    HANDLE job_list[1];
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION job_info;
    BOOL in_job = FALSE;
    DWORD creation_flags = CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT |
        CREATE_NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT;
    DWORD wait_result = WAIT_FAILED;
    DWORD remaining_milliseconds = 0U;
    DWORD exit_code = 0U;
    int have_exit = 0;
    int timed_out = 0;
    int process_created = 0;
    int resumed = 0;
    int native_cleanup_done = 0;
    int lifecycle_acquired = 0;
    int attempt_consumed = 0;
    wchar_t result_pipe_name[256];
    char primary[512] = "";
    PyObject *result = NULL;
    size_t index;
    (void)self;
    memset(&startup, 0, sizeof(startup));
    memset(&process, 0, sizeof(process));
    memset(&job_info, 0, sizeof(job_info));
    memset(drain_snapshots, 0, sizeof(drain_snapshots));
    memset(result_pipe_name, 0, sizeof(result_pipe_name));
    startup.StartupInfo.cb = sizeof(startup);
    if (!require_main_os_thread("run_child") ||
        !acquire_lifecycle_mutex("run_child")) {
        return NULL;
    }
    lifecycle_acquired = 1;
    if (!PyArg_UnpackTuple(
            args, "run_child", 2, 2, &plan, &run_number_object) ||
        !require_claimed("run_child")) {
        release_lifecycle_mutex();
        return NULL;
    }
    if (!g_state.outcome_reserved || !g_state.output_created ||
        g_state.outcome_committed || !exact_plan_keys(plan)) {
        release_lifecycle_mutex();
        return broker_error("run_child_broker_state_or_plan_refused");
    }
    if (!PyLong_CheckExact(run_number_object) || !g_state.nonces_claimed ||
        g_state.process_timeout_milliseconds != 180000U) {
        release_lifecycle_mutex();
        return broker_error("run_number_exact_int_required");
    }
    run_number = PyLong_AsLong(run_number_object);
    if (PyErr_Occurred() || run_number != g_state.next_run_number ||
        (run_number != 1 && run_number != 2)) {
        release_lifecycle_mutex();
        return broker_error("run_identity_refused");
    }
    pair_nonce = g_state.pair_nonce;
    run_nonce = run_number == 1 ? g_state.run_nonce_1 : g_state.run_nonce_2;
    if (!is_lower_hex64(pair_nonce) || !is_lower_hex64(run_nonce) ||
        strcmp(pair_nonce, run_nonce) == 0 ||
        (run_number == 2 && strcmp(run_nonce, g_state.run_nonce_1) == 0)) {
        release_lifecycle_mutex();
        return broker_error("pair_or_run_nonce_reuse_refused");
    }
    timeout_milliseconds = g_state.process_timeout_milliseconds;
    schema_object = PyDict_GetItemString(plan, "schema");
    contract_hash_object = PyDict_GetItemString(plan, "contract_sha256");
    if (schema_object == NULL || contract_hash_object == NULL ||
        !py_unicode_to_utf8_exact(schema_object, &schema, &schema_length) ||
        !py_unicode_to_utf8_exact(
            contract_hash_object, &contract_hash, &contract_hash_length) ||
        schema_length != (Py_ssize_t)(sizeof(
            "kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r6") - 1U) ||
        memcmp(
            schema,
            "kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r6",
            sizeof("kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r6") - 1U
        ) != 0 || contract_hash_length != 64 ||
        !is_lower_hex64(contract_hash)) {
        release_lifecycle_mutex();
        return broker_error("native_child_plan_identity_drift");
    }
    {
        unsigned char parsed_contract_hash[32];
        if (!parse_hex64(contract_hash, parsed_contract_hash) ||
            !constant_time_equal32(
                parsed_contract_hash, g_state.expected_contract_sha256)) {
            secure_zero(parsed_contract_hash, sizeof(parsed_contract_hash));
            release_lifecycle_mutex();
            return broker_error("native_child_plan_contract_hash_drift");
        }
        secure_zero(parsed_contract_hash, sizeof(parsed_contract_hash));
    }
    executable_row = plan_locked_path_row(
        plan, "blender_executable", "blender_executable");
    foundation_row = plan_locked_path_row(
        plan, "foundation_blend", "foundation_blend");
    wrapper_row = plan_locked_path_row(
        plan, "execution_wrapper", "execution_wrapper");
    if (executable_row == NULL || foundation_row == NULL || wrapper_row == NULL) {
        release_lifecycle_mutex();
        return NULL;
    }
    if (!recheck_ancestor_chain() ||
        !verify_retained_row_identity(executable_row) ||
        !verify_retained_row_identity(foundation_row) ||
        !verify_retained_row_identity(wrapper_row)) {
        release_lifecycle_mutex();
        return broker_error("retained_child_graph_identity_recheck_failed");
    }
    executable_launch_path = launch_path_from_retained_handle(executable_row);
    foundation_launch_path = launch_path_from_retained_handle(foundation_row);
    wrapper_launch_path = launch_path_from_retained_handle(wrapper_row);
    if (executable_launch_path == NULL || foundation_launch_path == NULL ||
        wrapper_launch_path == NULL) {
        free(executable_launch_path);
        free(foundation_launch_path);
        free(wrapper_launch_path);
        release_lifecycle_mutex();
        return broker_error("retained_handle_launch_path_failed");
    }
    EnterCriticalSection(&g_state.mutex);
    if (InterlockedCompareExchange(
            &g_state.run_attempt_consumed[run_number - 1], 1L, 0L) != 0L) {
        LeaveCriticalSection(&g_state.mutex);
        release_lifecycle_mutex();
        return broker_error("native_run_attempt_already_consumed");
    }
    if (InterlockedIncrement(&g_state.active_child_count) != 1L) {
        (void)InterlockedDecrement(&g_state.active_child_count);
        LeaveCriticalSection(&g_state.mutex);
        release_lifecycle_mutex();
        return broker_error("concurrent_child_run_refused");
    }
    ++g_state.next_run_number;
    LeaveCriticalSection(&g_state.mutex);
    attempt_consumed = 1;
    unique_run_cache_root = create_unique_cache_root(pair_nonce, run_nonce);
    if (unique_run_cache_root == NULL) {
        goto python_failure;
    }
    for (index = 0U; index < 3U; ++index) {
        drains[index] = (DrainContext *)calloc(1U, sizeof(DrainContext));
        if (drains[index] == NULL) {
            PyErr_NoMemory();
            goto python_failure;
        }
        drains[index]->read_handle = INVALID_HANDLE_VALUE;
    }
    cwd = duplicate_wide(g_state.project_root);
    if (cwd == NULL) {
        PyErr_NoMemory();
        goto python_failure;
    }
    {
        DWORD attributes_value = GetFileAttributesW(cwd);
        if (attributes_value == INVALID_FILE_ATTRIBUTES ||
            (attributes_value & FILE_ATTRIBUTE_DIRECTORY) == 0U ||
            path_has_reparse_component(cwd)) {
            PyErr_SetString(PyExc_ValueError, "child_cwd_not_plain_directory");
            goto python_failure;
        }
    }
    environment_object = native_restricted_environment(unique_run_cache_root);
    if (environment_object == NULL) {
        goto python_failure;
    }
    environment_block = build_environment_block(environment_object);
    Py_CLEAR(environment_object);
    if (environment_block == NULL) {
        goto python_failure;
    }
    if (_snwprintf_s(
            result_pipe_name,
            sizeof(result_pipe_name) / sizeof(result_pipe_name[0]),
            _TRUNCATE, L"\\\\.\\pipe\\KiraR25AFES-%lu-%S-%S",
            (unsigned long)g_state.process_id, pair_nonce, run_nonce) < 0 ||
        !authenticate_result_pipe_root_pid(
            result_pipe_name, 0U, timeout_milliseconds, &frame_read,
            &cleanup) ||
        !create_inherited_pipe(&stdout_read, &stdout_write) ||
        !create_inherited_pipe(&stderr_read, &stderr_write)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_pipe_create_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    null_input = CreateFileW(
        L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL
    );
    if (null_input == INVALID_HANDLE_VALUE || !SetHandleInformation(
            null_input, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_null_input_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    {
        wchar_t run_number_text[8];
        wchar_t *contract_hash_wide = utf8_to_wide_strict(contract_hash, 64U);
        wchar_t *pair_nonce_wide = utf8_to_wide_strict(pair_nonce, 64U);
        wchar_t *run_nonce_wide = utf8_to_wide_strict(run_nonce, 64U);
        _snwprintf_s(run_number_text, 8U, _TRUNCATE, L"%ld", run_number);
        if (contract_hash_wide == NULL || pair_nonce_wide == NULL ||
            run_nonce_wide == NULL ||
            !add_wide_copy(&arguments, executable_launch_path) ||
            !add_wide_copy(&arguments, L"--background") ||
            !add_wide_copy(&arguments, L"--factory-startup") ||
            !add_wide_copy(&arguments, L"--disable-autoexec") ||
            !add_wide_copy(&arguments, foundation_launch_path) ||
            !add_wide_copy(&arguments, L"--python-exit-code") ||
            !add_wide_copy(&arguments, L"1") ||
            !add_wide_copy(&arguments, L"--python") ||
            !add_wide_copy(&arguments, wrapper_launch_path) ||
            !add_wide_copy(&arguments, L"--") ||
            !add_wide_copy(&arguments, L"--result-pipe-name") ||
            !add_wide_copy(&arguments, result_pipe_name) ||
            !add_wide_copy(&arguments, L"--execution-contract-sha256") ||
            !add_wide_copy(&arguments, contract_hash_wide) ||
            !add_wide_copy(&arguments, L"--pair-session-nonce") ||
            !add_wide_copy(&arguments, pair_nonce_wide) ||
            !add_wide_copy(&arguments, L"--run-nonce") ||
            !add_wide_copy(&arguments, run_nonce_wide) ||
            !add_wide_copy(&arguments, L"--run-number") ||
            !add_wide_copy(&arguments, run_number_text)) {
            free(contract_hash_wide);
            free(pair_nonce_wide);
            free(run_nonce_wide);
            goto python_failure;
        }
        free(contract_hash_wide);
        free(pair_nonce_wide);
        free(run_nonce_wide);
    }
    if (arguments.count != 20U) {
        PyErr_SetString(PyExc_RuntimeError,
            "native_exact_command_argument_count_drift");
        goto python_failure;
    }
    command_line = build_command_line(&arguments);
    if (command_line == NULL) {
        PyErr_NoMemory();
        goto python_failure;
    }
    job = CreateJobObjectW(NULL, NULL);
    job_info.BasicLimitInformation.LimitFlags =
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (job == NULL || !SetInformationJobObject(
            job, JobObjectExtendedLimitInformation, &job_info,
            sizeof(job_info))) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "kill_on_close_job_create_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    inherited_handles[0] = stdout_write;
    inherited_handles[1] = stderr_write;
    inherited_handles[2] = null_input;
    job_list[0] = job;
    (void)InitializeProcThreadAttributeList(NULL, 2U, 0U, &attribute_size);
    if (attribute_size == 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "attribute_list_size_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    attributes = (LPPROC_THREAD_ATTRIBUTE_LIST)HeapAlloc(
        GetProcessHeap(), HEAP_ZERO_MEMORY, attribute_size
    );
    if (attributes == NULL || !InitializeProcThreadAttributeList(
            attributes, 2U, 0U, &attribute_size) ||
        !UpdateProcThreadAttribute(
            attributes, 0U, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            inherited_handles, sizeof(inherited_handles), NULL, NULL) ||
        !UpdateProcThreadAttribute(
            attributes, 0U, PROC_THREAD_ATTRIBUTE_JOB_LIST,
            job_list, sizeof(job_list), NULL, NULL)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "attribute_list_initialize_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    startup.lpAttributeList = attributes;
    startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
    startup.StartupInfo.hStdInput = null_input;
    startup.StartupInfo.hStdOutput = stdout_write;
    startup.StartupInfo.hStdError = stderr_write;
    if (!verify_retained_row_identity(executable_row) ||
        !verify_retained_row_identity(foundation_row) ||
        !verify_retained_row_identity(wrapper_row) ||
        !recheck_ancestor_chain() ||
        !CreateProcessW(
            executable_launch_path, command_line, NULL, NULL, TRUE,
            creation_flags, environment_block, cwd, &startup.StartupInfo,
            &process)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "create_suspended_child_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    process_created = 1;
    if (!IsProcessInJob(process.hProcess, job, &in_job) || !in_job) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "suspended_child_not_in_native_job:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    drains[1]->read_handle = stdout_read;
    stdout_read = INVALID_HANDLE_VALUE;
    drains[1]->maximum = max_stdout;
    drains[2]->read_handle = stderr_read;
    stderr_read = INVALID_HANDLE_VALUE;
    drains[2]->maximum = max_stderr;
    for (index = 1U; index < 3U; ++index) {
        drain_threads[index] = CreateThread(
            NULL, 0U, drain_thread_main, drains[index], 0U, NULL
        );
        if (drain_threads[index] == NULL) {
            _snprintf_s(primary, sizeof(primary), _TRUNCATE,
                "child_drain_thread_create_failed:%zu:winerror=%lu", index,
                (unsigned long)GetLastError());
            goto native_cleanup;
        }
    }
    if (ResumeThread(process.hThread) == (DWORD)-1) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "contained_child_resume_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    resumed = 1;
    /* One contract deadline begins when the contained child first runs and is
     * shared by pipe authentication plus process completion. */
    absolute_deadline = GetTickCount64() + (ULONGLONG)timeout_milliseconds;
    close_handle_record(&stdout_write, &cleanup, "parent_stdout_write");
    close_handle_record(&stderr_write, &cleanup, "parent_stderr_write");
    close_handle_record(&null_input, &cleanup, "parent_null_input");
    remaining_milliseconds = remaining_deadline_milliseconds(
        absolute_deadline);
    if (remaining_milliseconds == 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_absolute_deadline_expired_before_pipe_authentication");
        goto native_cleanup;
    }
    Py_BEGIN_ALLOW_THREADS
    in_job = authenticate_result_pipe_root_pid(
        result_pipe_name, process.dwProcessId, remaining_milliseconds,
        &frame_read, &cleanup);
    Py_END_ALLOW_THREADS
    if (!in_job) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "result_writer_pid_authentication_failed");
        goto native_cleanup;
    }
    drains[0]->read_handle = frame_read;
    frame_read = INVALID_HANDLE_VALUE;
    drains[0]->overlapped_read = 1;
    drains[0]->maximum = max_frame;
    drain_threads[0] = CreateThread(
        NULL, 0U, drain_thread_main, drains[0], 0U, NULL);
    if (drain_threads[0] == NULL) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "result_pipe_drain_thread_create_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    remaining_milliseconds = remaining_deadline_milliseconds(
        absolute_deadline);
    Py_BEGIN_ALLOW_THREADS
    wait_result = remaining_milliseconds == 0U ? WAIT_TIMEOUT :
        WaitForSingleObject(process.hProcess, remaining_milliseconds);
    Py_END_ALLOW_THREADS
    if (wait_result == WAIT_TIMEOUT) {
        timed_out = 1;
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_timeout_at_contract_deadline_%lu_ms",
            (unsigned long)timeout_milliseconds);
        if (!TerminateJobObject(job, 0xE0000001U)) {
            (void)cleanup_add(&cleanup, "timeout_terminate_job:winerror=%lu",
                (unsigned long)GetLastError());
        }
        wait_result = WaitForSingleObject(
            process.hProcess, TERMINATION_WAIT_MILLISECONDS);
        if (wait_result != WAIT_OBJECT_0) {
            (void)cleanup_add(&cleanup, "timeout_process_wait:wait=%lu",
                (unsigned long)wait_result);
        }
    } else if (wait_result != WAIT_OBJECT_0) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_wait_failed:wait=%lu:winerror=%lu",
            (unsigned long)wait_result, (unsigned long)GetLastError());
    }
    if (GetExitCodeProcess(process.hProcess, &exit_code)) {
        have_exit = 1;
    } else {
        (void)cleanup_add(&cleanup, "get_exit_code:winerror=%lu",
            (unsigned long)GetLastError());
    }

native_cleanup:
    if (process_created && (primary[0] != '\0' || !resumed)) {
        if (!TerminateJobObject(job, 0xE0000002U)) {
            (void)cleanup_add(&cleanup,
                "suspended_failure_terminate_job:winerror=%lu",
                (unsigned long)GetLastError());
        }
        if (WaitForSingleObject(
                process.hProcess, TERMINATION_WAIT_MILLISECONDS) !=
            WAIT_OBJECT_0) {
            (void)cleanup_add(&cleanup, "suspended_failure_process_wait");
        }
    }
    if (process_created &&
        !wait_for_job_active_processes_zero(job, &cleanup, "child_tree")) {
        if (primary[0] == '\0') {
            _snprintf_s(primary, sizeof(primary), _TRUNCATE,
                "job_process_tree_quiescence_failed");
        }
    }
    close_handle_record(&stdout_write, &cleanup, "stdout_write");
    close_handle_record(&stderr_write, &cleanup, "stderr_write");
    close_handle_record(&null_input, &cleanup, "null_input");
    {
        HANDLE active_drain_threads[3];
        DWORD active_drain_count = 0U;
        DWORD drain_wait;
        for (index = 0U; index < 3U; ++index) {
            if (drain_threads[index] != NULL &&
                drain_threads[index] != INVALID_HANDLE_VALUE) {
                active_drain_threads[active_drain_count++] =
                    drain_threads[index];
            }
        }
        if (active_drain_count != 0U) {
            drain_wait = WaitForMultipleObjects(
                active_drain_count, active_drain_threads, TRUE,
                DRAIN_JOIN_MILLISECONDS
            );
            if (drain_wait != WAIT_OBJECT_0) {
                (void)cleanup_add(&cleanup,
                    "bounded_drain_join:wait=%lu", (unsigned long)drain_wait);
            }
        }
    }
    (void)cancel_join_and_destroy_drain(
        &drain_threads[0], &drains[0], &drain_snapshots[0], &cleanup,
        "frame_drain");
    (void)cancel_join_and_destroy_drain(
        &drain_threads[1], &drains[1], &drain_snapshots[1], &cleanup,
        "stdout_drain");
    (void)cancel_join_and_destroy_drain(
        &drain_threads[2], &drains[2], &drain_snapshots[2], &cleanup,
        "stderr_drain");
    /* Caller aliases were invalidated at transfer.  Snapshots intentionally
     * contain evidence only and can never resurrect a numeric handle value. */
    close_handle_record(&frame_read, &cleanup, "frame_read");
    close_handle_record(&stdout_read, &cleanup, "stdout_read");
    close_handle_record(&stderr_read, &cleanup, "stderr_read");
    if (process_created &&
        !wait_for_job_active_processes_zero(job, &cleanup, "child_tree_final")) {
        if (primary[0] == '\0') {
            _snprintf_s(primary, sizeof(primary), _TRUNCATE,
                "job_active_processes_nonzero_after_drain");
        }
    }
    close_handle_record(&process.hThread, &cleanup, "process_thread");
    close_handle_record(&process.hProcess, &cleanup, "process_handle");
    close_handle_record(&job, &cleanup, "kill_on_close_job");
    if (attributes != NULL) {
        DeleteProcThreadAttributeList(attributes);
        HeapFree(GetProcessHeap(), 0U, attributes);
        attributes = NULL;
    }
    native_cleanup_done = 1;
    if (primary[0] == '\0' && drain_snapshots[0].read_error != 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "frame_drain_failed:winerror=%lu",
            (unsigned long)drain_snapshots[0].read_error);
    }
    if (primary[0] == '\0' && drain_snapshots[1].read_error != 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "stdout_drain_failed:winerror=%lu",
            (unsigned long)drain_snapshots[1].read_error);
    }
    if (primary[0] == '\0' && drain_snapshots[2].read_error != 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "stderr_drain_failed:winerror=%lu",
            (unsigned long)drain_snapshots[2].read_error);
    }
    if (primary[0] == '\0' && (!have_exit || exit_code != 0U)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_nonzero_or_unknown_exit:%lu", (unsigned long)exit_code);
    }
    if (primary[0] == '\0' &&
        (drain_snapshots[0].overflow || drain_snapshots[1].overflow ||
         drain_snapshots[2].overflow)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_capture_limit_exceeded");
    }
    if (primary[0] == '\0' &&
        (cleanup.count != 0U || cleanup.recording_failed)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "native_child_cleanup_failed");
    }
    if (primary[0] != '\0') {
        set_composite_child_error(primary, &cleanup);
        goto final_cleanup;
    }
    result = make_child_result(
        &drain_snapshots[0], &drain_snapshots[1], &drain_snapshots[2],
        process.dwProcessId,
        exit_code, have_exit, timed_out, result_pipe_name,
        pair_nonce, run_nonce,
        &cleanup);
    goto final_cleanup;

python_failure:
    if (!native_cleanup_done &&
        (frame_read != INVALID_HANDLE_VALUE ||
         stdout_read != INVALID_HANDLE_VALUE ||
         stdout_write != INVALID_HANDLE_VALUE ||
         stderr_read != INVALID_HANDLE_VALUE ||
         stderr_write != INVALID_HANDLE_VALUE ||
         null_input != INVALID_HANDLE_VALUE || job != INVALID_HANDLE_VALUE ||
         process_created || attributes != NULL)) {
        PyObject *exception = PyErr_GetRaisedException();
        PyObject *text = exception != NULL ? PyObject_Str(exception) : NULL;
        const char *detail = text != NULL ? PyUnicode_AsUTF8(text) : NULL;
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_plan_validation_failed:%s",
            detail != NULL ? detail : "unprintable_python_error");
        Py_XDECREF(text);
        Py_XDECREF(exception);
        goto native_cleanup;
    }

final_cleanup:
    free(executable_launch_path);
    free(foundation_launch_path);
    free(wrapper_launch_path);
    free(cwd);
    free(unique_run_cache_root);
    Py_XDECREF(environment_object);
    free(environment_block);
    wide_vector_free(&arguments);
    free(command_line);
    for (index = 0U; index < 3U; ++index) {
        if (drains[index] != NULL) {
            secure_zero(
                drains[index]->captured.data, drains[index]->captured.size);
            free(drains[index]->captured.data);
            free(drains[index]);
        }
        secure_zero(
            drain_snapshots[index].captured.data,
            drain_snapshots[index].captured.size);
        free(drain_snapshots[index].captured.data);
    }
    cleanup_list_free(&cleanup);
    if (attempt_consumed) {
        --g_state.active_child_count;
    }
    if (lifecycle_acquired) {
        release_lifecycle_mutex();
    }
    return result;
}

static PyObject *py_pure_sha256_hex(PyObject *, PyObject *);
static PyObject *py_pure_is_lower_hex64(PyObject *, PyObject *);
static PyObject *py_decode_receipt_frame(PyObject *, PyObject *);
static PyObject *py_encode_receipt_frame(PyObject *, PyObject *);
static PyObject *py_canonical_json_sha256(PyObject *, PyObject *);

static PyMethodDef broker_methods[] = {
    {"claim_once", py_claim_once, METH_VARARGS,
        "Claim this exact locked subject once."},
    {"manifest_identity", py_manifest_identity, METH_VARARGS,
        "Return the out-of-band retained-manifest identity."},
    {"audit_identity", py_audit_identity, METH_VARARGS,
        "Return the separately locked fresh-audit identity."},
    {"audit_bytes", py_audit_bytes, METH_VARARGS,
        "Return the separately locked fresh-audit bytes."},
    {"broker_process_id", py_broker_process_id, METH_VARARGS,
        "Return the native broker PID."},
    {"claim_nonce_bundle", py_claim_nonce_bundle, METH_VARARGS,
        "Claim the one BCrypt-generated pair/run nonce bundle."},
    {"is_lower_hex64", py_pure_is_lower_hex64, METH_VARARGS,
        "Validate one lowercase 64-hex value."},
    {"sha256_hex", py_pure_sha256_hex, METH_VARARGS,
        "Hash immutable bytes without exposing a module."},
    {"decode_receipt_frame", py_decode_receipt_frame, METH_VARARGS,
        "Decode one strict canonical receipt frame."},
    {"encode_receipt_frame", py_encode_receipt_frame, METH_VARARGS,
        "Encode one strict canonical receipt frame."},
    {"canonical_json_sha256", py_canonical_json_sha256, METH_VARARGS,
        "Hash one strict canonical JSON object."},
    {"locked_rows", py_locked_rows, METH_VARARGS,
        "Return immutable identities for all held rows and the fresh audit."},
    {"locked_read", py_locked_read, METH_VARARGS,
        "Read a retained row by exact label or unique exact path."},
    {"reserve_outcome", py_reserve_outcome, METH_VARARGS,
        "Reserve the canonical append-only outcome before other outputs."},
    {"create_output_root", py_create_output_root, METH_VARARGS,
        "Create one new pair output root after outcome reservation."},
    {"run_child", py_run_child, METH_VARARGS,
        "Run one numbered child suspended inside a native kill-on-close Job."},
    {"write_evidence", py_write_evidence, METH_VARARGS,
        "Create and retain a new evidence file under the output root."},
    {"after_snapshot", py_after_snapshot, METH_VARARGS,
        "Rehash every still-locked input after the exact pair."},
    {"commit_outcome", py_commit_outcome, METH_VARARGS,
        "Commit exact caller-framed bytes to the reserved outcome."},
    {"commit_failure_outcome", py_commit_failure_outcome, METH_VARARGS,
        "Commit a failure frame after reservation at any later stage."},
    {"quiesce_owned_resources", py_quiesce_owned_resources, METH_VARARGS,
        "Report whether all native child resources are quiescent."},
    {"finish", py_finish, METH_VARARGS,
        "Seal the one-shot native broker state."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef broker_module = {
    PyModuleDef_HEAD_INIT,
    BROKER_MODULE_NAME,
    "Private native capability for one retained Kira R25 AFES pair.",
    -1,
    broker_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC PyInit__kira_r25_afes_native_broker(void) {
    return PyModule_Create(&broker_module);
}

static void json_escape_ascii(
    const char *input, char *output, size_t output_size
) {
    size_t used = 0U;
    const unsigned char *cursor = (const unsigned char *)input;
    if (output_size == 0U) {
        return;
    }
    while (*cursor != 0U && used + 2U < output_size) {
        unsigned char value = *cursor++;
        if (value == '"' || value == '\\') {
            if (used + 2U >= output_size) {
                break;
            }
            output[used++] = '\\';
            output[used++] = (char)value;
        } else if (value == '\n' || value == '\r' || value == '\t') {
            if (used + 2U >= output_size) {
                break;
            }
            output[used++] = '\\';
            output[used++] = value == '\n' ? 'n' : (value == '\r' ? 'r' : 't');
        } else if (value >= 0x20U && value <= 0x7eU) {
            output[used++] = (char)value;
        } else {
            output[used++] = '?';
        }
    }
    output[used] = '\0';
}

static void commit_native_failure_if_reserved(const char *reason) {
    ByteBuffer frame = {0};
    TerminalRewriteResult rewrite_result;
    if (!g_state.outcome_reserved ||
        (g_state.outcome_committed &&
         g_state.staged_outcome_frame == NULL) ||
        g_state.outcome_handle == NULL ||
        g_state.outcome_handle == INVALID_HANDLE_VALUE) {
        return;
    }
    if (!build_native_terminal_failure_frame(reason, &frame)) {
        return;
    }
    rewrite_result = rewrite_terminal_outcome(
        frame.data, frame.size, "NATIVE_FAILURE");
    if (rewrite_result != TERMINAL_REWRITE_NONE) {
        g_state.outcome_committed = 1;
        g_state.outcome_success_provisional = 0;
    }
    clear_staged_outcome();
    secure_zero(frame.data, frame.size);
    free(frame.data);
}

static void fetch_python_error(char *output, size_t output_size) {
    PyObject *exception;
    PyObject *text;
    const char *utf8;
    Py_ssize_t length;
    if (output_size == 0U) {
        return;
    }
    output[0] = '\0';
    exception = PyErr_GetRaisedException();
    if (exception == NULL) {
        _snprintf_s(output, output_size, _TRUNCATE,
            "embedded_python_failed_without_exception");
        return;
    }
    text = PyObject_Str(exception);
    if (text != NULL) {
        utf8 = PyUnicode_AsUTF8AndSize(text, &length);
        if (utf8 != NULL && length >= 0) {
            _snprintf_s(output, output_size, _TRUNCATE,
                "embedded_python_exception:%.*s",
                (int)(length > 1500 ? 1500 : length), utf8);
        }
        Py_DECREF(text);
    }
    Py_DECREF(exception);
    if (output[0] == '\0') {
        PyErr_Clear();
        _snprintf_s(output, output_size, _TRUNCATE,
            "embedded_python_exception_unprintable");
    }
}

static PyObject *build_exact_builtins(
    const char *const *names, size_t name_count
) {
    PyObject *ambient = PyEval_GetBuiltins();
    PyObject *result = PyDict_New();
    size_t index;
    if (ambient == NULL || result == NULL) {
        Py_XDECREF(result);
        return NULL;
    }
    for (index = 0U; index < name_count; ++index) {
        PyObject *value = PyDict_GetItemString(ambient, names[index]);
        if (value == NULL || PyDict_SetItemString(result, names[index], value) < 0) {
            Py_DECREF(result);
            return NULL;
        }
    }
    return result;
}

static int parent_module_delta_is_allowed(PyObject *name_object) {
    static const char *const allowed[] = {
        "_abc", "_blake2", "_collections", "_collections_abc", "_functools",
        "_hashlib", "_json", "_operator", "_sre", "_types", "abc",
        "collections", "collections.abc", "copyreg", "enum", "functools",
        "hashlib", "itertools", "json", "json.decoder", "json.encoder",
        "json.scanner", "keyword", "operator", "re", "re._casefix",
        "re._compiler", "re._constants", "re._parser", "reprlib", "types"
    };
    const char *name;
    Py_ssize_t length;
    size_t index;
    if (!PyUnicode_CheckExact(name_object)) {
        return 0;
    }
    name = PyUnicode_AsUTF8AndSize(name_object, &length);
    if (name == NULL || length < 0) {
        return 0;
    }
    for (index = 0U; index < sizeof(allowed) / sizeof(allowed[0]); ++index) {
        if ((size_t)length == strlen(allowed[index]) &&
            memcmp(name, allowed[index], (size_t)length) == 0) {
            return 1;
        }
    }
    return 0;
}

static PyObject *capture_parent_module_baseline(void) {
    PyObject *modules = PyImport_GetModuleDict();
    PyObject *keys;
    PyObject *baseline;
    if (modules == NULL || !PyDict_CheckExact(modules)) {
        return NULL;
    }
    keys = PyDict_Keys(modules);
    baseline = keys != NULL ? PySet_New(keys) : NULL;
    Py_XDECREF(keys);
    return baseline;
}

static int verify_exact_parent_module_delta(PyObject *baseline) {
    PyObject *modules = PyImport_GetModuleDict();
    PyObject *name;
    PyObject *module;
    Py_ssize_t position = 0;
    if (baseline == NULL || !PySet_CheckExact(baseline) ||
        modules == NULL || !PyDict_CheckExact(modules)) {
        PyErr_SetString(PyExc_RuntimeError,
            "parent_module_baseline_or_table_invalid");
        return 0;
    }
    while (PyDict_Next(modules, &position, &name, &module)) {
        int present = PySet_Contains(baseline, name);
        if (present < 0) {
            return 0;
        }
        if (present == 0 && !parent_module_delta_is_allowed(name)) {
            PyErr_SetString(PyExc_RuntimeError,
                "parent_module_delta_outside_exact_allowlist");
            return 0;
        }
        (void)module;
    }
    return 1;
}

static PyObject *py_pure_sha256_hex(PyObject *self, PyObject *args) {
    Py_buffer view;
    unsigned char digest[32];
    char hex[65];
    PyObject *result;
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!PyArg_ParseTuple(args, "y*:sha256_hex", &view)) {
        return NULL;
    }
    if (!sha256_memory(
            (const unsigned char *)view.buf, (size_t)view.len, digest)) {
        PyBuffer_Release(&view);
        return broker_error("pure_sha256_failed");
    }
    PyBuffer_Release(&view);
    hex_encode32(digest, hex);
    secure_zero(digest, sizeof(digest));
    result = PyUnicode_FromStringAndSize(hex, 64);
    return result;
}

static PyObject *py_pure_is_lower_hex64(PyObject *self, PyObject *args) {
    const char *value;
    Py_ssize_t length;
    (void)self;
    if (!PyArg_ParseTuple(args, "s#:is_lower_hex64", &value, &length)) {
        return NULL;
    }
    return PyBool_FromLong(length == 64 && is_lower_hex64(value));
}

static PyObject *py_json_unique_pairs(PyObject *self, PyObject *args) {
    PyObject *pairs;
    PyObject *result;
    Py_ssize_t index;
    (void)self;
    if (!PyArg_ParseTuple(args, "O:json_unique_pairs", &pairs) ||
        !PyList_CheckExact(pairs)) {
        return NULL;
    }
    result = PyDict_New();
    if (result == NULL) {
        return NULL;
    }
    for (index = 0; index < PyList_GET_SIZE(pairs); ++index) {
        PyObject *pair = PyList_GET_ITEM(pairs, index);
        PyObject *key;
        PyObject *value;
        if (!PyTuple_CheckExact(pair) || PyTuple_GET_SIZE(pair) != 2) {
            Py_DECREF(result);
            return broker_error("strict_json_pair_shape");
        }
        key = PyTuple_GET_ITEM(pair, 0);
        value = PyTuple_GET_ITEM(pair, 1);
        if (!PyUnicode_CheckExact(key) || PyDict_Contains(result, key) != 0 ||
            PyDict_SetItem(result, key, value) < 0) {
            Py_DECREF(result);
            if (!PyErr_Occurred()) {
                PyErr_SetString(PyExc_ValueError, "strict_json_duplicate_key");
            }
            return NULL;
        }
    }
    return result;
}

static PyObject *py_json_reject_number(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    PyErr_SetString(PyExc_ValueError,
        "strict_json_float_or_nonfinite_number_refused");
    return NULL;
}

static PyMethodDef pure_sha256_method = {
    "sha256_hex", py_pure_sha256_hex, METH_VARARGS, NULL
};
static PyMethodDef pure_hex_method = {
    "is_lower_hex64", py_pure_is_lower_hex64, METH_VARARGS, NULL
};
static PyMethodDef json_pairs_method = {
    "_strict_pairs", py_json_unique_pairs, METH_VARARGS, NULL
};
static PyMethodDef json_reject_method = {
    "_reject_number", py_json_reject_number, METH_VARARGS, NULL
};

static PyObject *parse_strict_json_object_bytes(
    PyObject *bytes_object, const char *label
) {
    Py_buffer view;
    PyObject *json_module = NULL;
    PyObject *loads = NULL;
    PyObject *text = NULL;
    PyObject *positional = NULL;
    PyObject *keywords = NULL;
    PyObject *pairs_hook = NULL;
    PyObject *reject = NULL;
    PyObject *parsed = NULL;
    const unsigned char *data;
    Py_ssize_t size;
    memset(&view, 0, sizeof(view));
    if (PyObject_GetBuffer(bytes_object, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    data = (const unsigned char *)view.buf;
    size = view.len;
    if (size < 0 || (uint64_t)size > MAX_LOCKED_READ_BYTES) {
        PyBuffer_Release(&view);
        return broker_error("strict_json_input_bound_refused");
    }
    if (size >= 3 && data[0] == 0xefU && data[1] == 0xbbU && data[2] == 0xbfU) {
        data += 3;
        size -= 3;
    }
    text = PyUnicode_DecodeUTF8((const char *)data, size, "strict");
    PyBuffer_Release(&view);
    json_module = text != NULL ? PyImport_ImportModule("json") : NULL;
    loads = json_module != NULL ? PyObject_GetAttrString(json_module, "loads") : NULL;
    pairs_hook = PyCFunction_NewEx(&json_pairs_method, NULL, NULL);
    reject = PyCFunction_NewEx(&json_reject_method, NULL, NULL);
    positional = text != NULL ? PyTuple_Pack(1, text) : NULL;
    keywords = PyDict_New();
    if (loads == NULL || pairs_hook == NULL || reject == NULL ||
        positional == NULL || keywords == NULL ||
        PyDict_SetItemString(keywords, "object_pairs_hook", pairs_hook) < 0 ||
        PyDict_SetItemString(keywords, "parse_float", reject) < 0 ||
        PyDict_SetItemString(keywords, "parse_constant", reject) < 0) {
        goto cleanup;
    }
    parsed = PyObject_Call(loads, positional, keywords);
    if (parsed != NULL && !PyDict_CheckExact(parsed)) {
        Py_CLEAR(parsed);
        PyErr_Format(PyExc_ValueError, "strict_json_root_not_object:%s", label);
    }
cleanup:
    Py_XDECREF(keywords);
    Py_XDECREF(positional);
    Py_XDECREF(reject);
    Py_XDECREF(pairs_hook);
    Py_XDECREF(text);
    Py_XDECREF(loads);
    Py_XDECREF(json_module);
    return parsed;
}

static PyObject *py_pure_parse_strict_json_object(
    PyObject *self, PyObject *args
) {
    PyObject *bytes_object;
    const char *label;
    (void)self;
    if (!PyArg_ParseTuple(args, "Os:parse_strict_json_object",
            &bytes_object, &label)) {
        return NULL;
    }
    return parse_strict_json_object_bytes(bytes_object, label);
}

static PyMethodDef pure_json_method = {
    "parse_strict_json_object", py_pure_parse_strict_json_object,
    METH_VARARGS, NULL
};

static int dict_has_exact_keys(
    PyObject *value, const char *const *keys, size_t key_count
) {
    size_t index;
    if (!PyDict_CheckExact(value) ||
        PyDict_Size(value) != (Py_ssize_t)key_count) {
        return 0;
    }
    for (index = 0U; index < key_count; ++index) {
        if (PyDict_GetItemString(value, keys[index]) == NULL) {
            return 0;
        }
    }
    return 1;
}

static int base64_digit(unsigned char value, unsigned *decoded) {
    if (value >= 'A' && value <= 'Z') {
        *decoded = (unsigned)(value - 'A');
        return 1;
    }
    if (value >= 'a' && value <= 'z') {
        *decoded = 26U + (unsigned)(value - 'a');
        return 1;
    }
    if (value >= '0' && value <= '9') {
        *decoded = 52U + (unsigned)(value - '0');
        return 1;
    }
    if (value == '+') {
        *decoded = 62U;
        return 1;
    }
    if (value == '/') {
        *decoded = 63U;
        return 1;
    }
    return 0;
}

static int decode_canonical_base64(
    const char *encoded, size_t encoded_size,
    unsigned char **raw_out, size_t *raw_size_out
) {
    size_t padding = 0U;
    size_t raw_size;
    unsigned char *raw;
    size_t source_position;
    size_t target_position = 0U;
    *raw_out = NULL;
    *raw_size_out = 0U;
    if (encoded_size > 2U * MAX_OUTCOME_BYTES || encoded_size % 4U != 0U) {
        return 0;
    }
    if (encoded_size >= 1U && encoded[encoded_size - 1U] == '=') {
        padding = 1U;
        if (encoded_size >= 2U && encoded[encoded_size - 2U] == '=') {
            padding = 2U;
        }
    }
    raw_size = (encoded_size / 4U) * 3U - padding;
    if (raw_size > MAX_OUTCOME_BYTES) {
        return 0;
    }
    raw = (unsigned char *)HeapAlloc(
        GetProcessHeap(), HEAP_ZERO_MEMORY, raw_size == 0U ? 1U : raw_size);
    if (raw == NULL) {
        return 0;
    }
    for (source_position = 0U; source_position < encoded_size;
         source_position += 4U) {
        unsigned first;
        unsigned second;
        unsigned third = 0U;
        unsigned fourth = 0U;
        int final_group = source_position + 4U == encoded_size;
        int third_padding = encoded[source_position + 2U] == '=';
        int fourth_padding = encoded[source_position + 3U] == '=';
        if (!base64_digit((unsigned char)encoded[source_position], &first) ||
            !base64_digit((unsigned char)encoded[source_position + 1U], &second) ||
            (!third_padding && !base64_digit(
                (unsigned char)encoded[source_position + 2U], &third)) ||
            (!fourth_padding && !base64_digit(
                (unsigned char)encoded[source_position + 3U], &fourth)) ||
            (!final_group && (third_padding || fourth_padding)) ||
            (third_padding && !fourth_padding) ||
            (third_padding && (second & 0x0fU) != 0U) ||
            (fourth_padding && !third_padding && (third & 0x03U) != 0U)) {
            secure_zero(raw, raw_size);
            HeapFree(GetProcessHeap(), 0U, raw);
            return 0;
        }
        if (target_position < raw_size) {
            raw[target_position++] = (unsigned char)((first << 2U) | (second >> 4U));
        }
        if (!third_padding && target_position < raw_size) {
            raw[target_position++] = (unsigned char)((second << 4U) | (third >> 2U));
        }
        if (!fourth_padding && target_position < raw_size) {
            raw[target_position++] = (unsigned char)((third << 6U) | fourth);
        }
    }
    if (target_position != raw_size ||
        (padding == 0U && encoded_size != 0U &&
         (encoded[encoded_size - 1U] == '=' || encoded[encoded_size - 2U] == '=')) ||
        (padding == 1U && encoded[encoded_size - 2U] == '=') ||
        (padding == 2U && encoded[encoded_size - 3U] == '=')) {
        secure_zero(raw, raw_size);
        HeapFree(GetProcessHeap(), 0U, raw);
        return 0;
    }
    *raw_out = raw;
    *raw_size_out = raw_size;
    return 1;
}

static int exact_u32_object(PyObject *value, uint32_t *result) {
    unsigned long long converted;
    if (!PyLong_CheckExact(value)) {
        return 0;
    }
    converted = PyLong_AsUnsignedLongLong(value);
    if (PyErr_Occurred() || converted > UINT32_MAX) {
        PyErr_Clear();
        return 0;
    }
    *result = (uint32_t)converted;
    return 1;
}

static int exact_unicode_ascii(
    PyObject *value, const char **text, Py_ssize_t *length
) {
    if (!PyUnicode_CheckExact(value)) {
        return 0;
    }
    *text = PyUnicode_AsUTF8AndSize(value, length);
    return *text != NULL;
}

static int exact_unicode_equals_ascii(PyObject *value, const char *expected) {
    const char *text;
    Py_ssize_t length;
    size_t expected_size = strlen(expected);
    return exact_unicode_ascii(value, &text, &length) && length >= 0 &&
        (size_t)length == expected_size &&
        memcmp(text, expected, expected_size) == 0;
}

static PyObject *py_pure_decode_u32_blob(PyObject *self, PyObject *args) {
    static const char *const record_keys[] = {
        "codec", "endianness", "u32_count", "raw_bytes", "raw_sha256", "base64"
    };
    PyObject *reference_object;
    PyObject *record;
    PyObject *encoded_object;
    PyObject *raw_sha_object;
    const char *reference;
    const char *encoded;
    const char *raw_sha;
    Py_ssize_t reference_length;
    Py_ssize_t encoded_length;
    Py_ssize_t raw_sha_length;
    uint32_t declared_count;
    uint32_t declared_raw_bytes;
    unsigned char *raw = NULL;
    size_t raw_size = 0U;
    unsigned char digest[32];
    char digest_hex[65];
    PyObject *result = NULL;
    uint32_t index;
    (void)self;
    if (!PyArg_ParseTuple(args, "OO:decode_u32_blob", &reference_object, &record) ||
        !dict_has_exact_keys(record, record_keys,
            sizeof(record_keys) / sizeof(record_keys[0])) ||
        !exact_unicode_equals_ascii(
            PyDict_GetItemString(record, "codec"), "uint32_big_endian_v1") ||
        !exact_unicode_equals_ascii(PyDict_GetItemString(record, "endianness"), "big") ||
        !exact_u32_object(PyDict_GetItemString(record, "u32_count"), &declared_count) ||
        !exact_u32_object(PyDict_GetItemString(record, "raw_bytes"), &declared_raw_bytes) ||
        (uint64_t)declared_count * 4U != declared_raw_bytes ||
        declared_raw_bytes > MAX_OUTCOME_BYTES ||
        !exact_unicode_ascii(reference_object, &reference, &reference_length) ||
        reference_length != 71 || memcmp(reference, "sha256:", 7U) != 0 ||
        !is_lower_hex64(reference + 7U)) {
        return broker_error("compact_blob_record_or_reference_invalid");
    }
    encoded_object = PyDict_GetItemString(record, "base64");
    raw_sha_object = PyDict_GetItemString(record, "raw_sha256");
    if (!exact_unicode_ascii(encoded_object, &encoded, &encoded_length) ||
        encoded_length < 0 ||
        !exact_unicode_ascii(raw_sha_object, &raw_sha, &raw_sha_length) ||
        raw_sha_length != 64 || !is_lower_hex64(raw_sha) ||
        !decode_canonical_base64(
            encoded, (size_t)encoded_length, &raw, &raw_size) ||
        raw_size != (size_t)declared_raw_bytes ||
        !sha256_memory(raw, raw_size, digest)) {
        if (raw != NULL) {
            secure_zero(raw, raw_size);
            HeapFree(GetProcessHeap(), 0U, raw);
        }
        return broker_error("compact_blob_base64_length_or_hash_failed");
    }
    hex_encode32(digest, digest_hex);
    secure_zero(digest, sizeof(digest));
    if (memcmp(digest_hex, raw_sha, 64U) != 0 ||
        memcmp(digest_hex, reference + 7U, 64U) != 0) {
        secure_zero(raw, raw_size);
        HeapFree(GetProcessHeap(), 0U, raw);
        return broker_error("compact_blob_digest_identity_failed");
    }
    result = PyTuple_New((Py_ssize_t)declared_count);
    if (result == NULL) {
        secure_zero(raw, raw_size);
        HeapFree(GetProcessHeap(), 0U, raw);
        return NULL;
    }
    for (index = 0U; index < declared_count; ++index) {
        const unsigned char *item = raw + (size_t)index * 4U;
        uint32_t value = ((uint32_t)item[0] << 24U) |
            ((uint32_t)item[1] << 16U) | ((uint32_t)item[2] << 8U) |
            (uint32_t)item[3];
        PyObject *integer = PyLong_FromUnsignedLong((unsigned long)value);
        if (integer == NULL) {
            Py_DECREF(result);
            result = NULL;
            break;
        }
        PyTuple_SET_ITEM(result, (Py_ssize_t)index, integer);
    }
    secure_zero(raw, raw_size);
    HeapFree(GetProcessHeap(), 0U, raw);
    return result;
}

static PyMethodDef pure_blob_method = {
    "decode_u32_blob", py_pure_decode_u32_blob, METH_VARARGS, NULL
};

static int validate_canonical_value(
    PyObject *value, unsigned depth, size_t *nodes
) {
    Py_ssize_t index;
    PyObject *key;
    PyObject *child;
    Py_ssize_t position = 0;
    if (++(*nodes) > 8192U || depth > 32U) {
        PyErr_SetString(PyExc_ValueError, "canonical_json_structure_bound");
        return 0;
    }
    if (value == Py_None || PyBool_Check(value)) {
        return 1;
    }
    if (PyUnicode_CheckExact(value)) {
        Py_ssize_t length = PyUnicode_GetLength(value);
        for (index = 0; index < length; ++index) {
            Py_UCS4 character = PyUnicode_ReadChar(value, index);
            if (character > 0x7fU) {
                PyErr_SetString(PyExc_ValueError,
                    "canonical_json_string_must_be_ascii_subset");
                return 0;
            }
        }
        return 1;
    }
    if (PyLong_CheckExact(value)) {
        int overflow = 0;
        (void)PyLong_AsLongLongAndOverflow(value, &overflow);
        if (overflow != 0 || PyErr_Occurred()) {
            PyErr_SetString(PyExc_ValueError,
                "canonical_json_integer_outside_signed64");
            return 0;
        }
        return 1;
    }
    if (PyFloat_Check(value)) {
        PyErr_SetString(PyExc_ValueError, "canonical_json_float_refused");
        return 0;
    }
    if (PyList_CheckExact(value)) {
        for (index = 0; index < PyList_GET_SIZE(value); ++index) {
            if (!validate_canonical_value(
                    PyList_GET_ITEM(value, index), depth + 1U, nodes)) {
                return 0;
            }
        }
        return 1;
    }
    if (PyDict_CheckExact(value)) {
        while (PyDict_Next(value, &position, &key, &child)) {
            if (!PyUnicode_CheckExact(key) ||
                !validate_canonical_value(key, depth + 1U, nodes) ||
                !validate_canonical_value(child, depth + 1U, nodes)) {
                return 0;
            }
        }
        return 1;
    }
    PyErr_SetString(PyExc_ValueError, "canonical_json_type_refused");
    return 0;
}

static PyObject *canonical_json_bytes_object(PyObject *payload) {
    PyObject *json_module = NULL;
    PyObject *dumps = NULL;
    PyObject *positional = NULL;
    PyObject *keywords = NULL;
    PyObject *separators = NULL;
    PyObject *text = NULL;
    PyObject *encoded = NULL;
    size_t nodes = 0U;
    if (!PyDict_CheckExact(payload) ||
        !validate_canonical_value(payload, 1U, &nodes)) {
        return NULL;
    }
    json_module = PyImport_ImportModule("json");
    dumps = json_module != NULL ? PyObject_GetAttrString(json_module, "dumps") : NULL;
    positional = PyTuple_Pack(1, payload);
    keywords = PyDict_New();
    separators = Py_BuildValue("(ss)", ",", ":");
    if (dumps == NULL || positional == NULL || keywords == NULL ||
        separators == NULL ||
        PyDict_SetItemString(keywords, "ensure_ascii", Py_False) < 0 ||
        PyDict_SetItemString(keywords, "allow_nan", Py_False) < 0 ||
        PyDict_SetItemString(keywords, "sort_keys", Py_True) < 0 ||
        PyDict_SetItemString(keywords, "separators", separators) < 0) {
        goto cleanup;
    }
    text = PyObject_Call(dumps, positional, keywords);
    encoded = text != NULL ? PyUnicode_AsEncodedString(text, "utf-8", "strict") : NULL;
    if (encoded != NULL && PyBytes_GET_SIZE(encoded) > 1024 * 1024) {
        Py_CLEAR(encoded);
        PyErr_SetString(PyExc_ValueError, "canonical_json_payload_too_large");
    }
cleanup:
    Py_XDECREF(text);
    Py_XDECREF(separators);
    Py_XDECREF(keywords);
    Py_XDECREF(positional);
    Py_XDECREF(dumps);
    Py_XDECREF(json_module);
    return encoded;
}

static void write_be32(unsigned char *target, uint32_t value) {
    target[0] = (unsigned char)(value >> 24);
    target[1] = (unsigned char)(value >> 16);
    target[2] = (unsigned char)(value >> 8);
    target[3] = (unsigned char)value;
}

static void write_be64(unsigned char *target, uint64_t value) {
    size_t index;
    for (index = 0U; index < 8U; ++index) {
        target[index] = (unsigned char)(value >> (56U - index * 8U));
    }
}

static uint32_t read_be32(const unsigned char *source) {
    return ((uint32_t)source[0] << 24) | ((uint32_t)source[1] << 16) |
        ((uint32_t)source[2] << 8) | source[3];
}

static uint64_t read_be64(const unsigned char *source) {
    uint64_t result = 0U;
    size_t index;
    for (index = 0U; index < 8U; ++index) {
        result = (result << 8) | source[index];
    }
    return result;
}

static PyObject *encode_receipt_frame_object(PyObject *payload) {
    static const unsigned char magic[8] = {
        'K', '2', '5', 'R', 'C', 'P', 'T', '!'
    };
    PyObject *canonical = canonical_json_bytes_object(payload);
    PyObject *frame = NULL;
    unsigned char digest[32];
    unsigned char *target;
    Py_ssize_t payload_size;
    if (canonical == NULL) {
        return NULL;
    }
    payload_size = PyBytes_GET_SIZE(canonical);
    if (!sha256_memory((const unsigned char *)PyBytes_AS_STRING(canonical),
            (size_t)payload_size, digest)) {
        Py_DECREF(canonical);
        return broker_error("receipt_payload_digest_failed");
    }
    frame = PyBytes_FromStringAndSize(NULL, 52 + payload_size);
    if (frame != NULL) {
        target = (unsigned char *)PyBytes_AS_STRING(frame);
        memcpy(target, magic, 8U);
        write_be32(target + 8U, 1U);
        write_be64(target + 12U, (uint64_t)payload_size);
        memcpy(target + 20U, digest, 32U);
        memcpy(target + 52U, PyBytes_AS_STRING(canonical),
            (size_t)payload_size);
    }
    secure_zero(digest, sizeof(digest));
    Py_DECREF(canonical);
    return frame;
}

static PyObject *py_encode_receipt_frame(PyObject *self, PyObject *args) {
    PyObject *payload;
    (void)self;
    if (!PyArg_ParseTuple(args, "O:encode_receipt_frame", &payload)) {
        return NULL;
    }
    return encode_receipt_frame_object(payload);
}

static PyObject *py_canonical_json_sha256(PyObject *self, PyObject *args) {
    PyObject *payload;
    PyObject *canonical;
    unsigned char digest[32];
    char hex[65];
    PyObject *result;
    (void)self;
    if (!PyArg_ParseTuple(args, "O:canonical_json_sha256", &payload)) {
        return NULL;
    }
    canonical = canonical_json_bytes_object(payload);
    if (canonical == NULL || !sha256_memory(
        (const unsigned char *)PyBytes_AS_STRING(canonical),
            (size_t)PyBytes_GET_SIZE(canonical),
            digest)) {
        Py_XDECREF(canonical);
        return broker_error("canonical_json_digest_failed");
    }
    Py_DECREF(canonical);
    hex_encode32(digest, hex);
    secure_zero(digest, sizeof(digest));
    result = PyUnicode_FromStringAndSize(hex, 64);
    return result;
}

static PyMethodDef pure_canonical_sha_method = {
    "canonical_json_sha256", py_canonical_json_sha256, METH_VARARGS, NULL
};

static PyObject *py_decode_receipt_frame(PyObject *self, PyObject *args) {
    Py_buffer view;
    const unsigned char *frame;
    uint64_t payload_size;
    unsigned char payload_digest[32];
    unsigned char frame_digest[32];
    PyObject *payload_bytes = NULL;
    PyObject *payload = NULL;
    PyObject *canonical = NULL;
    PyObject *result = NULL;
    char payload_hex[65];
    char frame_hex[65];
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!PyArg_ParseTuple(args, "y*:decode_receipt_frame", &view)) {
        return NULL;
    }
    frame = (const unsigned char *)view.buf;
    if (view.len < 52 || view.len > 52 + 1024 * 1024 ||
        memcmp(frame, "K25RCPT!", 8U) != 0 || read_be32(frame + 8U) != 1U) {
        PyBuffer_Release(&view);
        return broker_error("receipt_header_or_bound_invalid");
    }
    payload_size = read_be64(frame + 12U);
    if (payload_size > 1024U * 1024U ||
        (uint64_t)view.len != 52U + payload_size ||
        !sha256_memory(frame + 52U, (size_t)payload_size, payload_digest) ||
        !constant_time_equal32(payload_digest, frame + 20U) ||
        !sha256_memory(frame, (size_t)view.len, frame_digest)) {
        PyBuffer_Release(&view);
        secure_zero(payload_digest, sizeof(payload_digest));
        return broker_error("receipt_length_or_digest_invalid");
    }
    payload_bytes = PyBytes_FromStringAndSize(
        (const char *)(frame + 52U), (Py_ssize_t)payload_size);
    PyBuffer_Release(&view);
    payload = payload_bytes != NULL ? parse_strict_json_object_bytes(
        payload_bytes, "receipt_payload") : NULL;
    canonical = payload != NULL ? canonical_json_bytes_object(payload) : NULL;
    if (canonical == NULL || PyObject_RichCompareBool(
            canonical, payload_bytes, Py_EQ) != 1) {
        Py_XDECREF(canonical);
        Py_XDECREF(payload);
        Py_XDECREF(payload_bytes);
        secure_zero(payload_digest, sizeof(payload_digest));
        secure_zero(frame_digest, sizeof(frame_digest));
        return broker_error("receipt_payload_not_canonical");
    }
    hex_encode32(payload_digest, payload_hex);
    hex_encode32(frame_digest, frame_hex);
    secure_zero(payload_digest, sizeof(payload_digest));
    secure_zero(frame_digest, sizeof(frame_digest));
    result = Py_BuildValue(
        "{s:O,s:s,s:s}", "payload", payload,
        "payload_sha256", payload_hex, "frame_sha256", frame_hex);
    Py_DECREF(canonical);
    Py_DECREF(payload);
    Py_DECREF(payload_bytes);
    return result;
}

static int parse_structural_contract_timeout(
    char *error, size_t error_size
) {
    RetainedRow *row = &g_state.rows[g_state.contract_index];
    ByteBuffer bytes = {0};
    PyObject *bytes_object = NULL;
    PyObject *contract = NULL;
    PyObject *process_contract;
    PyObject *timeout;
    int ok = 0;
    if (!read_handle_all(row->handle, row->expected_bytes,
            MAX_LOCKED_READ_BYTES, &bytes)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "contract_timeout_locked_read_failed");
        return 0;
    }
    bytes_object = PyBytes_FromStringAndSize(
        (const char *)bytes.data, (Py_ssize_t)bytes.size);
    contract = bytes_object != NULL ? parse_strict_json_object_bytes(
        bytes_object, "execution_contract") : NULL;
    process_contract = contract != NULL ? PyDict_GetItemString(
        contract, "process_contract") : NULL;
    timeout = process_contract != NULL && PyDict_CheckExact(process_contract)
        ? PyDict_GetItemString(process_contract, "process_timeout_seconds")
        : NULL;
    if (timeout == NULL || !PyLong_CheckExact(timeout) ||
        PyLong_AsLong(timeout) != 180L || PyErr_Occurred()) {
        fetch_python_error(error, error_size);
        if (error[0] == '\0') {
            _snprintf_s(error, error_size, _TRUNCATE,
                "contract_process_timeout_must_be_exact_integer_180");
        }
    } else {
        g_state.process_timeout_milliseconds = 180000U;
        ok = 1;
    }
    Py_XDECREF(contract);
    Py_XDECREF(bytes_object);
    secure_zero(bytes.data, bytes.size);
    free(bytes.data);
    return ok;
}

static int copy_ascii_wide(
    const wchar_t *input, char *output, size_t output_size
);

typedef struct BootstrapSeed {
    char contract_sha256[65];
    char audit_sha256[65];
    char manifest_sha256[65];
} BootstrapSeed;

static int parse_bootstrap_seed(
    int argc, wchar_t **argv, BootstrapSeed *seed
) {
    unsigned seen = 0U;
    int index;
    memset(seed, 0, sizeof(*seed));
    if (argc != 6) {
        return 0;
    }
    for (index = 0; index < argc; index += 2) {
        unsigned bit;
        char *destination;
        if (wcscmp(argv[index], L"--expected-contract-sha256") == 0) {
            bit = 1U;
            destination = seed->contract_sha256;
        } else if (wcscmp(argv[index], L"--accepted-audit-sha256") == 0) {
            bit = 2U;
            destination = seed->audit_sha256;
        } else if (wcscmp(argv[index], L"--retained-manifest-sha256") == 0) {
            bit = 4U;
            destination = seed->manifest_sha256;
        } else {
            return 0;
        }
        if ((seen & bit) != 0U ||
            !copy_ascii_wide(argv[index + 1], destination, 65U) ||
            !is_lower_hex64(destination)) {
            return 0;
        }
        seen |= bit;
    }
    return seen == 7U &&
        strcmp(seed->contract_sha256,
            "") != 0;
}

static PyObject *new_null_self_callable(PyMethodDef *definition) {
    PyObject *callable = PyCFunction_NewEx(definition, NULL, NULL);
    if (callable != NULL && PyCFunction_GetSelf(callable) != NULL) {
        Py_DECREF(callable);
        PyErr_SetString(PyExc_RuntimeError,
            "pure_native_callable_unexpected_self_authority");
        return NULL;
    }
    return callable;
}

static PyObject *load_pure_controller_calls(
    char *error, size_t error_size
) {
    static const char *const builtin_names[] = {
        "__build_class__", "RuntimeError", "any", "bytes",
        "dict", "int", "isinstance", "len", "list", "set", "sorted",
        "str", "tuple", "type"
    };
    static const char *const exports[] = {
        "_build_execution_plan", "_validate_child_payload", "_compare_pair",
        "_success_payload", "_failure_payload"
    };
    static const char *const exact_controller_global_keys[] = {
        "__builtins__", "__name__", "__doc__",
        "_native_sha256_hex", "_native_is_lower_hex64",
        "_native_parse_strict_json_object", "_native_decode_u32_blob",
        "_native_canonical_json_sha256",
        "CONTRACT_RELATIVE_PATH", "AUDIT_RELATIVE_PATH", "OUTPUT_RELATIVE_PATH",
        "OUTCOME_RELATIVE_PATH", "MANIFEST_RELATIVE_PATH",
        "CHECKPOINT_RELATIVE_PATH", "MAX_FRAME_BYTES", "MAX_STDOUT_BYTES",
        "MAX_STDERR_BYTES", "UINT32_MAX", "SIGNED64_MIN", "SIGNED64_MAX",
        "NANOMETERS_PER_METER", "BLOB_CODEC", "INDEX_SEMANTIC",
        "EDGE_SEMANTIC", "ROUNDING_RULE", "ENVIRONMENT_INHERITED_EXACT_KEYS",
        "MUTABLE_ENVIRONMENT_UNDER_UNIQUE_RUN_ROOT", "CONSTANT_ENVIRONMENT",
        "BLENDER_COMMAND_TEMPLATE", "LockedPairV3R6PlanError", "_sha256_bytes",
        "_strict_object", "_signed64", "_u32", "_normalize_indices",
        "_decode_blob", "_decode_index_reference", "_decode_edge_reference",
        "_validate_compact_afes_analysis", "_exact_row", "_iter_contract_rows",
        "_scope", "_process_contract", "_pair_contract", "_truth_boundary",
        "_bootstrap_contract", "_native_launcher_contract", "_audit_gate",
        "_outer_truth", "_verify_retained_rows", "_validate_audit",
        "_build_execution_plan", "_validate_child_payload", "_compare_pair",
        "_success_payload", "_failure_payload", "CONTROLLER_EXPORTED_CALLS"
    };
    RetainedRow *row = find_row_by_label("parent_controller", NULL);
    ByteBuffer source = {0};
    PyObject *globals = NULL;
    PyObject *builtins = NULL;
    PyObject *sha = NULL;
    PyObject *hex = NULL;
    PyObject *json = NULL;
    PyObject *blob = NULL;
    PyObject *canonical_sha = NULL;
    PyObject *name = NULL;
    PyObject *code = NULL;
    PyObject *evaluation = NULL;
    PyObject *result = NULL;
    PyCompilerFlags compiler_flags = {0};
    size_t index;
    if (row == NULL || !verify_retained_row_identity(row) ||
        !read_handle_all(row->handle, row->expected_bytes,
            MAX_LOCKED_READ_BYTES, &source) ||
        memchr(source.data, '\0', source.size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "pure_controller_retained_read_failed");
        goto cleanup;
    }
    globals = PyDict_New();
    builtins = build_exact_builtins(
        builtin_names, sizeof(builtin_names) / sizeof(builtin_names[0]));
    sha = new_null_self_callable(&pure_sha256_method);
    hex = new_null_self_callable(&pure_hex_method);
    json = new_null_self_callable(&pure_json_method);
    blob = new_null_self_callable(&pure_blob_method);
    canonical_sha = new_null_self_callable(&pure_canonical_sha_method);
    name = PyUnicode_FromString("_kira_r25_v3r6_pure_controller_retained");
    if (globals == NULL || builtins == NULL || sha == NULL || hex == NULL ||
        json == NULL || blob == NULL || canonical_sha == NULL || name == NULL ||
        PyDict_SetItemString(globals, "__builtins__", builtins) < 0 ||
        PyDict_SetItemString(globals, "__name__", name) < 0 ||
        PyDict_SetItemString(globals, "_native_sha256_hex", sha) < 0 ||
        PyDict_SetItemString(globals, "_native_is_lower_hex64", hex) < 0 ||
        PyDict_SetItemString(
            globals, "_native_parse_strict_json_object", json) < 0 ||
        PyDict_SetItemString(globals, "_native_decode_u32_blob", blob) < 0 ||
        PyDict_SetItemString(
            globals, "_native_canonical_json_sha256", canonical_sha) < 0) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    compiler_flags.cf_flags = CO_FUTURE_ANNOTATIONS;
    code = Py_CompileStringExFlags(
        (const char *)source.data, "<native-retained-controller-v3r6>",
        Py_file_input, &compiler_flags, -1);
    evaluation = code != NULL ? PyEval_EvalCode(code, globals, globals) : NULL;
    if (evaluation == NULL) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    if (!dict_has_exact_keys(
            globals, exact_controller_global_keys,
            sizeof(exact_controller_global_keys) /
                sizeof(exact_controller_global_keys[0]))) {
        PyErr_SetString(PyExc_RuntimeError,
            "pure_controller_exact_global_dependency_closure_drift");
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    result = PyDict_New();
    if (result == NULL) {
        goto cleanup;
    }
    for (index = 0U; index < sizeof(exports) / sizeof(exports[0]); ++index) {
        PyObject *callable = PyDict_GetItemString(globals, exports[index]);
        if (callable == NULL || !PyFunction_Check(callable) ||
            PyFunction_GetGlobals(callable) != globals ||
            PyDict_SetItemString(result, exports[index], callable) < 0) {
            Py_CLEAR(result);
            PyErr_SetString(PyExc_RuntimeError,
                "pure_controller_export_or_globals_closure_invalid");
            fetch_python_error(error, error_size);
            goto cleanup;
        }
    }
cleanup:
    Py_XDECREF(evaluation);
    Py_XDECREF(code);
    Py_XDECREF(name);
    Py_XDECREF(canonical_sha);
    Py_XDECREF(blob);
    Py_XDECREF(json);
    Py_XDECREF(hex);
    Py_XDECREF(sha);
    Py_XDECREF(builtins);
    /* Exported functions retain this exact globals dictionary by identity. */
    Py_XDECREF(globals);
    secure_zero(source.data, source.size);
    free(source.data);
    return result;
}

static void record_native_cleanup_failure(
    const char *description, char *error, size_t error_size
) {
    LONG count = InterlockedIncrement(&g_state.native_cleanup_failure_count);
    size_t used;
    if (count == 1L) {
        strncpy_s(
            g_state.native_cleanup_failure,
            sizeof(g_state.native_cleanup_failure),
            description != NULL ? description : "native_cleanup_failed",
            _TRUNCATE);
    }
    if (error == NULL || error_size == 0U) {
        return;
    }
    used = strnlen_s(error, error_size);
    if (used < error_size - 1U) {
        (void)_snprintf_s(
            error + used, error_size - used, _TRUNCATE,
            "%snative_cleanup_failure:%s",
            used == 0U ? "" : "|",
            description != NULL ? description : "unknown");
    }
}

static int execute_retained_bootstrap(
    int bootstrap_argc, wchar_t **bootstrap_argv,
    const char *bootstrap_label, char *error, size_t error_size
) {
    PyStatus status;
    PyConfig config;
    BootstrapSeed seed;
    ByteBuffer source = {0};
    RetainedRow *bootstrap = &g_state.rows[g_state.bootstrap_index];
    RetainedRow *retained_stdlib_zip =
        find_row_by_label("retained_stdlib_zip", NULL);
    PyObject *globals = NULL;
    PyObject *code = NULL;
    PyObject *evaluation = NULL;
    PyObject *restricted_builtins = NULL;
    PyObject *broker_object = NULL;
    PyObject *controller_calls = NULL;
    PyObject *parent_module_baseline = NULL;
    PyObject *seed_object = NULL;
    PyObject *value = NULL;
    char bootstrap_hash[65];
    char gate_error[512];
    int initialized = 0;
    int result = 0;
    int finalize_failed = 0;
    int terminal_gate_checked = 0;
    int terminal_gate_ok = 0;
    TerminalRewriteResult terminal_result;
    static const char *const bootstrap_builtin_names[] = {
        "__build_class__", "BaseException", "NameError",
        "RuntimeError", "SystemExit", "all", "any", "bytes",
        "callable", "dict", "int", "isinstance", "len", "list", "set",
        "str", "tuple", "type"
    };
    if (!secure_load_embedded_python() || retained_stdlib_zip == NULL ||
        !verify_retained_row_identity(retained_stdlib_zip)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "embedded_python_runtime_closure_identity_failed");
        return 0;
    }
    if (!parse_bootstrap_seed(bootstrap_argc, bootstrap_argv, &seed) ||
        strcmp(seed.contract_sha256, "") == 0) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "native_bootstrap_seed_parse_failed");
        return 0;
    }
    PyConfig_InitIsolatedConfig(&config);
    config.use_environment = 0;
    config.user_site_directory = 0;
    config.site_import = 0;
    config.write_bytecode = 0;
    config.install_signal_handlers = 0;
    config.parse_argv = 0;
    config.safe_path = 1;
    config.module_search_paths_set = 1;
    status = PyConfig_SetString(&config, &config.program_name, g_state.self_path);
    if (!PyStatus_Exception(status)) {
        status = PyConfig_SetString(&config, &config.executable, g_state.self_path);
    }
    if (!PyStatus_Exception(status)) {
        status = PyWideStringList_Append(
            &config.module_search_paths, retained_stdlib_zip->final_path);
    }
    if (!PyStatus_Exception(status)) {
        status = PyWideStringList_Append(
            &config.argv, L"<native-retained-bootstrap-v3r6>"
        );
    }
    if (PyStatus_Exception(status)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "embedded_python_config_failed:%s",
            status.err_msg != NULL ? status.err_msg : "unknown");
        PyConfig_Clear(&config);
        return 0;
    }
    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "embedded_python_initialize_failed:%s",
            status.err_msg != NULL ? status.err_msg : "unknown");
        return 0;
    }
    initialized = 1;
    parent_module_baseline = capture_parent_module_baseline();
    if (parent_module_baseline == NULL) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    if (!parse_structural_contract_timeout(error, error_size)) {
        goto cleanup;
    }
    if (!read_handle_all(
            bootstrap->handle, bootstrap->expected_bytes,
            MAX_LOCKED_READ_BYTES, &source) ||
        memchr(source.data, '\0', source.size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "retained_bootstrap_read_or_nul_failed");
        goto cleanup;
    }
    globals = PyDict_New();
    restricted_builtins = build_exact_builtins(
        bootstrap_builtin_names,
        sizeof(bootstrap_builtin_names) /
            sizeof(bootstrap_builtin_names[0]));
    broker_object = PyModule_Create(&broker_module);
    controller_calls = load_pure_controller_calls(error, error_size);
    seed_object = Py_BuildValue(
        "{s:s,s:s,s:s,s:s}",
        "marker", "KIRA_R25_AFES_NATIVE_BROKER_V3R6",
        "expected_contract_sha256", seed.contract_sha256,
        "accepted_audit_sha256", seed.audit_sha256,
        "retained_manifest_sha256", seed.manifest_sha256
    );
    if (globals == NULL || restricted_builtins == NULL ||
        broker_object == NULL || controller_calls == NULL ||
        seed_object == NULL ||
        PyDict_SetItemString(globals, "__builtins__", restricted_builtins) < 0 ||
        PyDict_SetItemString(
            globals, "__KIRA_NATIVE_BROKER_OBJECT_V3R6__",
            broker_object) < 0 ||
        PyDict_SetItemString(
            globals, "__KIRA_NATIVE_CONTROLLER_CALLS_V3R6__",
            controller_calls) < 0 ||
        PyDict_SetItemString(
            globals, "__KIRA_NATIVE_SEED_IDENTITY_V3R6__",
            seed_object) < 0) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    value = PyUnicode_FromString("__main__");
    if (value == NULL || PyDict_SetItemString(globals, "__name__", value) < 0) {
        Py_XDECREF(value);
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyUnicode_FromString("<native-retained-bootstrap-v3r6>");
    if (value == NULL || PyDict_SetItemString(globals, "__file__", value) < 0) {
        Py_XDECREF(value);
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    Py_CLEAR(value);
    hex_encode32(bootstrap->expected_sha256, bootstrap_hash);
    value = PyUnicode_FromStringAndSize(bootstrap_hash, 64);
    if (value == NULL || PyDict_SetItemString(
            globals, "__KIRA_RETAINED_BOOTSTRAP_SHA256__", value) < 0) {
        Py_XDECREF(value);
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyUnicode_FromString(bootstrap_label);
    if (value == NULL || PyDict_SetItemString(
            globals, "__KIRA_RETAINED_BOOTSTRAP_LABEL__", value) < 0) {
        Py_XDECREF(value);
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    Py_CLEAR(value);
    code = Py_CompileStringExFlags(
        (const char *)source.data, "<native-retained-bootstrap-v3r6>",
        Py_file_input, NULL, -1
    );
    if (code == NULL) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    evaluation = PyEval_EvalCode(code, globals, globals);
    if (evaluation == NULL) {
        fetch_python_error(error, error_size);
        if (g_state.staged_outcome_frame != NULL) {
            terminal_gate_checked = 1;
            if (!g_state.finished) {
                record_native_cleanup_failure(
                    "retained_bootstrap_failure_path_missing_native_finish",
                    error, error_size);
            } else if (!verify_exact_parent_module_delta(
                    parent_module_baseline)) {
                gate_error[0] = '\0';
                fetch_python_error(gate_error, sizeof(gate_error));
                record_native_cleanup_failure(
                    gate_error[0] != '\0' ? gate_error :
                    "failure_path_parent_module_delta_failed",
                    error, error_size);
            } else {
                terminal_gate_ok = 1;
            }
        }
        goto cleanup;
    }
    terminal_gate_checked = 1;
    if (!g_state.finished) {
        record_native_cleanup_failure(
            "retained_bootstrap_returned_without_native_finish",
            error, error_size);
        goto cleanup;
    }
    if (!verify_exact_parent_module_delta(parent_module_baseline)) {
        gate_error[0] = '\0';
        fetch_python_error(gate_error, sizeof(gate_error));
        record_native_cleanup_failure(
            gate_error[0] != '\0' ? gate_error :
            "success_path_parent_module_delta_failed",
            error, error_size);
        goto cleanup;
    }
    terminal_gate_ok = 1;
    result = 1;
cleanup:
    Py_XDECREF(seed_object);
    Py_XDECREF(controller_calls);
    Py_XDECREF(parent_module_baseline);
    Py_XDECREF(broker_object);
    Py_XDECREF(restricted_builtins);
    Py_XDECREF(evaluation);
    Py_XDECREF(code);
    Py_XDECREF(globals);
    secure_zero(source.data, source.size);
    free(source.data);
    if (initialized && Py_FinalizeEx() < 0) {
        record_native_cleanup_failure(
            "embedded_python_finalize_failed", error, error_size);
        finalize_failed = 1;
        result = 0;
    }
    /* Python-produced terminal frames stay solely in native memory until
     * after bootstrap return, exact module-delta verification and clean
     * Python finalization.  Therefore no late failure can leave a valid
     * externally visible success or incomplete caller-failure receipt. */
    if (!finalize_failed && terminal_gate_checked && terminal_gate_ok &&
        g_state.staged_outcome_frame != NULL) {
        if (result && strcmp(g_state.staged_outcome_kind, "SUCCESS") == 0) {
            terminal_result = rewrite_terminal_outcome(
                g_state.staged_outcome_frame,
                g_state.staged_outcome_frame_size, "SUCCESS");
            if (terminal_result == TERMINAL_REWRITE_PRIMARY_VERIFIED) {
                g_state.outcome_success_provisional = 0;
                g_state.outcome_committed = 1;
                clear_staged_outcome();
            } else {
                if (terminal_result ==
                    TERMINAL_REWRITE_FALLBACK_FAILURE_VERIFIED) {
                    g_state.outcome_success_provisional = 0;
                    g_state.outcome_committed = 1;
                    clear_staged_outcome();
                }
                _snprintf_s(error, error_size, _TRUNCATE,
                    "final_native_success_commit_failed");
                result = 0;
            }
        } else if (!result &&
            strcmp(g_state.staged_outcome_kind, "CALLER_FAILURE") == 0) {
            terminal_result = rewrite_terminal_outcome(
                g_state.staged_outcome_frame,
                g_state.staged_outcome_frame_size, "CALLER_FAILURE");
            if (terminal_result != TERMINAL_REWRITE_NONE) {
                g_state.outcome_committed = 1;
                g_state.outcome_success_provisional = 0;
                clear_staged_outcome();
            }
        } else if (result) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "staged_outcome_kind_or_result_drift");
            result = 0;
        }
    }
    return result;
}

typedef struct ParsedArguments {
    const wchar_t *project_root;
    const wchar_t *manifest_path;
    const wchar_t *audit_path;
    char manifest_sha256[65];
    char contract_sha256[65];
    char audit_sha256[65];
    char bootstrap_label[129];
    int bootstrap_argc;
    wchar_t **bootstrap_argv;
} ParsedArguments;

static int copy_ascii_wide(
    const wchar_t *input, char *output, size_t output_size
) {
    size_t length;
    size_t index;
    if (input == NULL) {
        return 0;
    }
    length = wcslen(input);
    if (length + 1U > output_size) {
        return 0;
    }
    for (index = 0U; index < length; ++index) {
        if (input[index] < 0x20 || input[index] > 0x7e) {
            return 0;
        }
        output[index] = (char)input[index];
    }
    output[length] = '\0';
    return 1;
}

static int parse_main_arguments(
    int argc, wchar_t **argv, ParsedArguments *parsed,
    char *error, size_t error_size
) {
    int index;
    unsigned seen = 0U;
    memset(parsed, 0, sizeof(*parsed));
    for (index = 1; index < argc; ++index) {
        const wchar_t *option = argv[index];
        const wchar_t *value;
        unsigned bit;
        if (wcscmp(option, L"--") == 0) {
            parsed->bootstrap_argc = argc - index - 1;
            parsed->bootstrap_argv = argv + index + 1;
            break;
        }
        if (index + 1 >= argc) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "startup_option_missing_value");
            return 0;
        }
        value = argv[++index];
        if (wcscmp(option, L"--project-root") == 0) {
            bit = 1U << 0;
            parsed->project_root = value;
        } else if (wcscmp(option, L"--retained-manifest") == 0) {
            bit = 1U << 1;
            parsed->manifest_path = value;
        } else if (wcscmp(option, L"--manifest-sha256") == 0) {
            bit = 1U << 2;
            if (!copy_ascii_wide(
                    value, parsed->manifest_sha256,
                    sizeof(parsed->manifest_sha256))) {
                return 0;
            }
        } else if (wcscmp(option, L"--contract-sha256") == 0) {
            bit = 1U << 3;
            if (!copy_ascii_wide(
                    value, parsed->contract_sha256,
                    sizeof(parsed->contract_sha256))) {
                return 0;
            }
        } else if (wcscmp(option, L"--audit-path") == 0) {
            bit = 1U << 4;
            parsed->audit_path = value;
        } else if (wcscmp(option, L"--audit-sha256") == 0) {
            bit = 1U << 5;
            if (!copy_ascii_wide(value, parsed->audit_sha256,
                    sizeof(parsed->audit_sha256))) {
                return 0;
            }
        } else if (wcscmp(option, L"--bootstrap-label") == 0) {
            bit = 1U << 6;
            if (!copy_ascii_wide(value, parsed->bootstrap_label,
                    sizeof(parsed->bootstrap_label))) {
                return 0;
            }
        } else {
            _snprintf_s(error, error_size, _TRUNCATE,
                "unknown_startup_option");
            return 0;
        }
        if ((seen & bit) != 0U) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "duplicate_startup_option");
            return 0;
        }
        seen |= bit;
    }
    if (seen != 0x7fU || parsed->project_root == NULL ||
        parsed->manifest_path == NULL || parsed->audit_path == NULL ||
        !is_lower_hex64(parsed->manifest_sha256) ||
        !is_lower_hex64(parsed->contract_sha256) ||
        !is_lower_hex64(parsed->audit_sha256) ||
        !valid_manifest_label(parsed->bootstrap_label)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "incomplete_or_invalid_startup_contract");
        return 0;
    }
    return 1;
}

int wmain(int argc, wchar_t **argv) {
    ParsedArguments parsed;
    char error[2048];
    int ok;
    error[0] = '\0';
    if (!parse_main_arguments(argc, argv, &parsed, error, sizeof(error))) {
        fwprintf(stderr, L"KIRA_R25_AFES_NATIVE_V3R6_REFUSED: %hs\n", error);
        return 2;
    }
    if (!initialize_locked_state(
            parsed.project_root, parsed.manifest_path, parsed.manifest_sha256,
            parsed.contract_sha256, parsed.audit_path, parsed.audit_sha256,
            parsed.bootstrap_label, error, sizeof(error))) {
        fwprintf(stderr, L"KIRA_R25_AFES_NATIVE_V3R6_REFUSED: %hs\n", error);
        cleanup_state();
        return 3;
    }
    ok = execute_retained_bootstrap(
        parsed.bootstrap_argc, parsed.bootstrap_argv, parsed.bootstrap_label,
        error, sizeof(error)
    );
    if (!ok) {
        commit_native_failure_if_reserved(error);
        fwprintf(stderr, L"KIRA_R25_AFES_NATIVE_V3R6_FAILED: %hs\n", error);
        cleanup_state();
        return 4;
    }
    cleanup_state();
    return 0;
}

