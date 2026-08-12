/*
 * Kira R25 AFES locked-pair native launcher, append-only v3r3.
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
 *      /I C:\Python314\include kira_r25_afes_locked_pair_launcher_v3r3.c \
 *      /link /LIBPATH:C:\Python314\libs python314.lib bcrypt.lib
 *
 * This source contains no accepted digest.  Acceptance is external and binds
 * the exact launcher image, retained manifest, fixed fresh audit, and all
 * locked rows.  A different caller-supplied manifest therefore cannot produce
 * evidence matching the independently accepted subject.
 */

#define PY_SSIZE_T_CLEAN
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

#ifndef PROC_THREAD_ATTRIBUTE_JOB_LIST
#define PROC_THREAD_ATTRIBUTE_JOB_LIST ((DWORD_PTR)0x0002000D)
#endif

#define BROKER_MODULE_NAME "_kira_r25_afes_native_broker"
#define MANIFEST_MAGIC "KIRA_R25_AFES_RETAINED_MANIFEST_V3R3\t1"
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
} RetainedRow;

typedef struct HeldOutput {
    HANDLE handle;
    wchar_t *path;
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
    int output_created;
    int after_snapshot_done;
    int finished;
    int active_process;
    int next_run_number;
    char pair_nonce[65];
    char run_nonce_1[65];
    char run_nonce_2[65];
    HANDLE outcome_handle;
    wchar_t *outcome_path;
    wchar_t *output_root;
    HeldOutput *held_outputs;
    DWORD process_id;
    CRITICAL_SECTION mutex;
    int mutex_initialized;
    BrokerLifecycle lifecycle;
} BrokerState;

typedef struct ByteBuffer {
    unsigned char *data;
    size_t size;
    size_t capacity;
} ByteBuffer;

typedef struct DrainContext {
    HANDLE read_handle;
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
} CleanupList;

typedef struct WideVector {
    wchar_t **items;
    size_t count;
    size_t capacity;
} WideVector;

static BrokerState g_state;

static int byte_buffer_reserve(ByteBuffer *buffer, size_t required);

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
        path[0] == L'\\' || path[0] == L'/' || wcschr(path, L':') != NULL) {
        return 0;
    }
    component = path;
    cursor = path;
    for (;;) {
        if (*cursor == L'\\' || *cursor == L'/' || *cursor == L'\0') {
            size_t length = (size_t)(cursor - component);
            if (length == 0U ||
                (length == 1U && component[0] == L'.') ||
                (length == 2U && component[0] == L'.' && component[1] == L'.')) {
                return 0;
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

static int get_handle_size(HANDLE handle, uint64_t *size) {
    LARGE_INTEGER value;
    if (!GetFileSizeEx(handle, &value) || value.QuadPart < 0) {
        return 0;
    }
    *size = (uint64_t)value.QuadPart;
    return 1;
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

static int lock_and_verify_manifest_rows(char *error, size_t error_size) {
    size_t index;
    RetainedRow *self_row;
    RetainedRow *contract_row;
    RetainedRow *bootstrap_row;
    for (index = 0U; index < g_state.row_count; ++index) {
        uint64_t actual_bytes = 0U;
        unsigned char actual_hash[32];
        RetainedRow *row = &g_state.rows[index];
        if (path_has_reparse_component(row->path)) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "retained_path_reparse_or_missing:%s", row->label_utf8);
            return 0;
        }
        row->handle = open_locked_read_file(row->path);
        if (row->handle == INVALID_HANDLE_VALUE) {
            _snprintf_s(error, error_size, _TRUNCATE,
                "retained_lock_failed:%s:winerror=%lu", row->label_utf8,
                (unsigned long)GetLastError());
            return 0;
        }
        if (!sha256_handle(row->handle, actual_hash, &actual_bytes) ||
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
    return 1;
}

static void cleanup_state(void) {
    size_t index;
    HeldOutput *held;
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
        free(held);
        held = next;
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
    free(g_state.outcome_path);
    free(g_state.output_root);
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
    g_state.manifest_handle = open_locked_read_file(g_state.manifest_path);
    if (g_state.manifest_handle == INVALID_HANDLE_VALUE ||
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
        !sha256_handle(g_state.audit_handle, actual_hash, &actual_bytes) ||
        !constant_time_equal32(actual_hash, g_state.expected_audit_sha256)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "fresh_audit_lock_or_hash_failed");
        secure_zero(actual_hash, sizeof(actual_hash));
        return 0;
    }
    memcpy(g_state.audit_sha256, actual_hash, sizeof(actual_hash));
    g_state.audit_bytes = actual_bytes;
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

static int require_claimed(const char *operation) {
    if (!g_state.initialized || !g_state.claimed || g_state.finished) {
        PyErr_Format(PyExc_RuntimeError,
            "native_broker_state_refused:%s", operation);
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
    if (!PyArg_UnpackTuple(
            args, "claim_once", 3, 3, &manifest_object, &contract_object,
            &audit_object)) {
        return NULL;
    }
    EnterCriticalSection(&g_state.mutex);
    if (g_state.claim_attempted) {
        LeaveCriticalSection(&g_state.mutex);
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
        return broker_error("native_broker_out_of_band_claim_mismatch");
    }
    secure_zero(manifest_hash, sizeof(manifest_hash));
    secure_zero(contract_hash, sizeof(contract_hash));
    secure_zero(audit_hash, sizeof(audit_hash));
    EnterCriticalSection(&g_state.mutex);
    g_state.claimed = 1;
    LeaveCriticalSection(&g_state.mutex);
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

static PyObject *py_reserve_outcome(PyObject *self, PyObject *args) {
    PyObject *relative_object;
    wchar_t *path;
    HANDLE handle;
    (void)self;
    if (!PyArg_UnpackTuple(args, "reserve_outcome", 1, 1, &relative_object) ||
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
    handle = CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL
    );
    if (handle == INVALID_HANDLE_VALUE) {
        DWORD code = GetLastError();
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
    if (!PyArg_UnpackTuple(args, "create_output_root", 1, 1, &relative_object) ||
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
    if (!CreateDirectoryW(path, NULL)) {
        DWORD code = GetLastError();
        free(path);
        PyErr_Format(PyExc_RuntimeError,
            "native_output_root_create_new_failed:winerror=%lu",
            (unsigned long)code);
        return NULL;
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
    uint64_t measured = 0U;
    char hash_hex[65];
    PyObject *result = NULL;
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!PyArg_UnpackTuple(
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
    if (PyObject_GetBuffer(data_object, &view, PyBUF_CONTIG_RO) < 0) {
        free(name);
        return NULL;
    }
    if (view.len < 0 || (uint64_t)view.len > MAX_EVIDENCE_BYTES) {
        PyBuffer_Release(&view);
        free(name);
        return broker_error("evidence_size_refused");
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
    free(name);
    canonical = canonical_full_path(joined);
    free(joined);
    if (canonical == NULL || !path_is_under_output_root(canonical)) {
        PyBuffer_Release(&view);
        free(canonical);
        return broker_error("evidence_path_escape_refused");
    }
    handle = CreateFileW(
        canonical, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL,
        CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL
    );
    if (handle == INVALID_HANDLE_VALUE ||
        !write_all_handle(handle, (const unsigned char *)view.buf,
            (size_t)view.len) ||
        !FlushFileBuffers(handle) ||
        !sha256_handle(handle, hash, &measured) || measured != (uint64_t)view.len) {
        DWORD code = GetLastError();
        if (handle != INVALID_HANDLE_VALUE) {
            CloseHandle(handle);
        }
        PyBuffer_Release(&view);
        free(canonical);
        PyErr_Format(PyExc_RuntimeError,
            "native_evidence_write_failed:winerror=%lu", (unsigned long)code);
        return NULL;
    }
    PyBuffer_Release(&view);
    held = (HeldOutput *)calloc(1U, sizeof(HeldOutput));
    if (held == NULL) {
        CloseHandle(handle);
        free(canonical);
        return PyErr_NoMemory();
    }
    held->handle = handle;
    held->path = canonical;
    held->next = g_state.held_outputs;
    g_state.held_outputs = held;
    hex_encode32(hash, hash_hex);
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
    if (!PyArg_ParseTuple(args, ":after_snapshot") ||
        !require_claimed("after_snapshot")) {
        return NULL;
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
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!PyArg_UnpackTuple(args, "commit_outcome", 1, 1, &frame_object) ||
        !require_claimed("commit_outcome")) {
        return NULL;
    }
    if (!g_state.outcome_reserved || g_state.outcome_committed ||
        !g_state.after_snapshot_done || g_state.next_run_number != 3) {
        return broker_error("commit_outcome_state_refused");
    }
    if (PyObject_GetBuffer(frame_object, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    if (view.len <= 0 || (uint64_t)view.len > MAX_OUTCOME_BYTES ||
        !write_all_handle(g_state.outcome_handle,
            (const unsigned char *)view.buf, (size_t)view.len) ||
        !FlushFileBuffers(g_state.outcome_handle)) {
        PyBuffer_Release(&view);
        return broker_error("native_outcome_commit_failed");
    }
    PyBuffer_Release(&view);
    g_state.outcome_committed = 1;
    Py_RETURN_NONE;
}

static PyObject *py_commit_failure_outcome(PyObject *self, PyObject *args) {
    PyObject *frame_object;
    Py_buffer view;
    (void)self;
    memset(&view, 0, sizeof(view));
    if (!PyArg_UnpackTuple(
            args, "commit_failure_outcome", 1, 1, &frame_object) ||
        !require_claimed("commit_failure_outcome")) {
        return NULL;
    }
    if (!g_state.outcome_reserved || g_state.outcome_committed) {
        return broker_error("commit_failure_outcome_state_refused");
    }
    if (PyObject_GetBuffer(frame_object, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    if (view.len <= 0 || (uint64_t)view.len > MAX_OUTCOME_BYTES ||
        !write_all_handle(g_state.outcome_handle,
            (const unsigned char *)view.buf, (size_t)view.len) ||
        !FlushFileBuffers(g_state.outcome_handle)) {
        PyBuffer_Release(&view);
        return broker_error("native_failure_outcome_commit_failed");
    }
    PyBuffer_Release(&view);
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
    if (g_state.active_process) {
        result = PyTuple_New(1);
        if (result != NULL) {
            PyTuple_SET_ITEM(result, 0,
                PyUnicode_FromString("active_process_not_quiescent"));
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
    if (!PyArg_ParseTuple(args, ":finish") ||
        !require_claimed("finish")) {
        return NULL;
    }
    if (!g_state.outcome_committed) {
        /* Do not mask an earlier Python exception in the bootstrap's finally.
         * The native main will reject a normal return without a committed
         * outcome and will record the original exception when available. */
        Py_RETURN_NONE;
    }
    if (g_state.active_process) {
        return broker_error("native_finish_active_process_refused");
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
    for (;;) {
        DWORD count = 0U;
        if (!ReadFile(
                context->read_handle, temporary, sizeof(temporary), &count,
                NULL)) {
            DWORD code = GetLastError();
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
    secure_zero(temporary, sizeof(temporary));
    return 0U;
}

static int cleanup_add(CleanupList *list, const char *format, ...) {
    va_list arguments;
    char temporary[384];
    char *copy;
    if (list->count == list->capacity) {
        size_t capacity = list->capacity == 0U ? 8U : list->capacity * 2U;
        char **expanded;
        if (capacity < list->capacity || capacity > SIZE_MAX / sizeof(char *)) {
            return 0;
        }
        expanded = (char **)realloc(list->items, capacity * sizeof(char *));
        if (expanded == NULL) {
            return 0;
        }
        list->items = expanded;
        list->capacity = capacity;
    }
    va_start(arguments, format);
    _vsnprintf_s(temporary, sizeof(temporary), _TRUNCATE, format, arguments);
    va_end(arguments);
    copy = duplicate_bytes_as_cstr(temporary, strlen(temporary));
    if (copy == NULL) {
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

static PyObject *cleanup_list_tuple(const CleanupList *list) {
    PyObject *result = PyTuple_New((Py_ssize_t)list->count);
    size_t index;
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
    Py_ssize_t position = 0;
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
    while (PyDict_Next(environment, &position, &key, &value)) {
        wchar_t *wide_key = py_unicode_to_wide_exact(key);
        wchar_t *wide_value = NULL;
        wchar_t *entry = NULL;
        size_t key_length;
        size_t value_length;
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
        if (key_length == 0U || wide_key[0] == L'=' ||
            wcschr(wide_key, L'=') != NULL || wcschr(wide_value, L'\0') == NULL ||
            key_length > 32767U || value_length > 32767U ||
            key_length > SIZE_MAX - value_length - 2U) {
            free(wide_key);
            free(wide_value);
            wide_vector_free(&entries);
            PyErr_SetString(PyExc_ValueError, "invalid_environment_entry");
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

static int parse_size_option(
    PyObject *plan, const char *name, size_t default_value, size_t *output
) {
    PyObject *value = PyDict_GetItemString(plan, name);
    unsigned long long parsed;
    if (value == NULL) {
        *output = default_value;
        return 1;
    }
    if (!PyLong_CheckExact(value)) {
        PyErr_Format(PyExc_TypeError, "%s_exact_int_required", name);
        return 0;
    }
    parsed = PyLong_AsUnsignedLongLong(value);
    if (PyErr_Occurred() || parsed == 0ULL ||
        parsed > MAX_CHILD_CAPTURE_BYTES || parsed > SIZE_MAX) {
        PyErr_Format(PyExc_ValueError, "%s_out_of_range", name);
        return 0;
    }
    *output = (size_t)parsed;
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

static PyObject *native_restricted_environment(void) {
    static const wchar_t *allowlist[] = {
        L"SYSTEMROOT", L"WINDIR", L"TEMP", L"TMP", L"USERNAME",
        L"USERPROFILE", L"HOMEDRIVE", L"HOMEPATH", L"LOCALAPPDATA",
        L"APPDATA", L"Path"
    };
    static const wchar_t *forced_names[] = {
        L"PYTHONNOUSERSITE", L"PYTHONDONTWRITEBYTECODE", L"PYTHONHASHSEED",
        L"BLENDER_USER_CONFIG", L"BLENDER_USER_SCRIPTS",
        L"BLENDER_USER_DATAFILES"
    };
    static const wchar_t *forced_values[] = {
        L"1", L"1", L"0",
        L"RecoverySprint/runtime_cache/r25_blender/user_config",
        L"RecoverySprint/runtime_cache/r25_blender/user_scripts",
        L"RecoverySprint/runtime_cache/r25_blender/user_datafiles"
    };
    PyObject *result = PyDict_New();
    size_t index;
    if (result == NULL) {
        return NULL;
    }
    for (index = 0U; index < sizeof(allowlist) / sizeof(allowlist[0]); ++index) {
        DWORD required = GetEnvironmentVariableW(allowlist[index], NULL, 0U);
        if (required != 0U) {
            wchar_t *value = (wchar_t *)malloc(
                ((size_t)required + 1U) * sizeof(wchar_t));
            PyObject *key_object;
            PyObject *value_object;
            if (value == NULL || GetEnvironmentVariableW(
                    allowlist[index], value, required + 1U) == 0U) {
                free(value);
                Py_DECREF(result);
                return broker_error("restricted_environment_read_failed");
            }
            key_object = PyUnicode_FromWideChar(allowlist[index], -1);
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
        } else if (GetLastError() != ERROR_ENVVAR_NOT_FOUND &&
                   GetLastError() != ERROR_SUCCESS) {
            Py_DECREF(result);
            return broker_error("restricted_environment_probe_failed");
        }
    }
    for (index = 0U; index < sizeof(forced_names) / sizeof(forced_names[0]);
         ++index) {
        wchar_t *value = NULL;
        PyObject *key_object;
        PyObject *value_object;
        if (index < 3U) {
            value = duplicate_wide(forced_values[index]);
        } else {
            value = join_project_relative(forced_values[index]);
        }
        if (value == NULL) {
            Py_DECREF(result);
            return broker_error("forced_environment_path_failed");
        }
        key_object = PyUnicode_FromWideChar(forced_names[index], -1);
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

static int add_python_argv(
    PyObject *sequence, const wchar_t *placeholder, HANDLE result_write,
    WideVector *arguments, int *placeholder_count
) {
    PyObject *fast;
    Py_ssize_t index;
    wchar_t handle_text[32];
    _snwprintf_s(handle_text, 32U, _TRUNCATE, L"%" PRIuPTR,
        (uintptr_t)result_write);
    if (!(PyList_CheckExact(sequence) || PyTuple_CheckExact(sequence))) {
        PyErr_SetString(PyExc_TypeError, "argv_exact_list_or_tuple_required");
        return 0;
    }
    fast = PySequence_Fast(sequence, "argv sequence required");
    if (fast == NULL) {
        return 0;
    }
    if (PySequence_Fast_GET_SIZE(fast) > 1024) {
        Py_DECREF(fast);
        PyErr_SetString(PyExc_ValueError, "argv_too_long");
        return 0;
    }
    for (index = 0; index < PySequence_Fast_GET_SIZE(fast); ++index) {
        PyObject *item = PySequence_Fast_GET_ITEM(fast, index);
        wchar_t *wide = py_unicode_to_wide_exact(item);
        if (wide == NULL) {
            Py_DECREF(fast);
            return 0;
        }
        if (wcscmp(wide, placeholder) == 0) {
            free(wide);
            wide = duplicate_wide(handle_text);
            ++*placeholder_count;
            if (wide == NULL) {
                Py_DECREF(fast);
                PyErr_NoMemory();
                return 0;
            }
        }
        if (!wide_vector_add(arguments, wide)) {
            free(wide);
            Py_DECREF(fast);
            PyErr_NoMemory();
            return 0;
        }
    }
    Py_DECREF(fast);
    return 1;
}

static int wait_and_close_drain(
    HANDLE *thread, DrainContext *context, CleanupList *cleanup,
    const char *label
) {
    DWORD wait_result;
    int ok = 1;
    if (*thread == NULL || *thread == INVALID_HANDLE_VALUE) {
        return 1;
    }
    wait_result = WaitForSingleObject(*thread, DRAIN_JOIN_MILLISECONDS);
    if (wait_result == WAIT_TIMEOUT) {
        if (!CancelSynchronousIo(*thread)) {
            DWORD code = GetLastError();
            if (code != ERROR_NOT_FOUND) {
                (void)cleanup_add(cleanup,
                    "%s_cancel:winerror=%lu", label, (unsigned long)code);
            }
        }
        if (context->read_handle != NULL &&
            context->read_handle != INVALID_HANDLE_VALUE) {
            if (!CloseHandle(context->read_handle)) {
                (void)cleanup_add(cleanup,
                    "%s_pipe_force_close:winerror=%lu", label,
                    (unsigned long)GetLastError());
            }
            context->read_handle = INVALID_HANDLE_VALUE;
        }
        wait_result = WaitForSingleObject(*thread, DRAIN_JOIN_MILLISECONDS);
    }
    if (wait_result != WAIT_OBJECT_0) {
        (void)cleanup_add(cleanup, "%s_join:wait=%lu", label,
            (unsigned long)wait_result);
        ok = 0;
    }
    close_handle_record(thread, cleanup, label);
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
    uintptr_t result_handle_value,
    const CleanupList *cleanup
) {
    PyObject *result = PyDict_New();
    PyObject *frame_bytes = NULL;
    PyObject *stdout_bytes = NULL;
    PyObject *stderr_bytes = NULL;
    PyObject *pid = NULL;
    PyObject *exit = NULL;
    PyObject *cleanup_tuple = NULL;
    PyObject *result_handle = NULL;
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
    result_handle = PyLong_FromUnsignedLongLong(
        (unsigned long long)result_handle_value);
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
        result_handle == NULL || stdout_total == NULL || stderr_total == NULL ||
        stdout_hash_object == NULL || stderr_hash_object == NULL ||
        PyDict_SetItemString(result, "frame", frame_bytes) < 0 ||
        PyDict_SetItemString(result, "stdout", stdout_bytes) < 0 ||
        PyDict_SetItemString(result, "stderr", stderr_bytes) < 0 ||
        PyDict_SetItemString(result, "pid", pid) < 0 ||
        PyDict_SetItemString(result, "exit", exit) < 0 ||
        PyDict_SetItemString(result, "exit_code", exit) < 0 ||
        PyDict_SetItemString(result, "result_handle", result_handle) < 0 ||
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
    Py_XDECREF(result_handle);
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
    PyErr_SetString(PyExc_RuntimeError, message);
}

static PyObject *py_run_child(PyObject *self, PyObject *args) {
    PyObject *plan;
    PyObject *run_number_object;
    PyObject *pair_object;
    PyObject *run_object;
    long run_number;
    const char *pair_nonce;
    const char *run_nonce;
    Py_ssize_t pair_length;
    Py_ssize_t run_length;
    RetainedRow *executable_row;
    RetainedRow *foundation_row;
    RetainedRow *wrapper_row;
    PyObject *environment_object = NULL;
    PyObject *contract_hash_object;
    PyObject *schema_object;
    const char *contract_hash;
    const char *schema;
    Py_ssize_t contract_hash_length;
    Py_ssize_t schema_length;
    wchar_t *cwd = NULL;
    wchar_t *environment_block = NULL;
    WideVector arguments = {0};
    wchar_t *command_line = NULL;
    DWORD timeout_milliseconds = 300000U;
    size_t max_frame = 1048628U;
    size_t max_stdout = 4U * 1024U * 1024U;
    size_t max_stderr = 4U * 1024U * 1024U;
    HANDLE frame_read = INVALID_HANDLE_VALUE;
    HANDLE frame_write = INVALID_HANDLE_VALUE;
    HANDLE stdout_read = INVALID_HANDLE_VALUE;
    HANDLE stdout_write = INVALID_HANDLE_VALUE;
    HANDLE stderr_read = INVALID_HANDLE_VALUE;
    HANDLE stderr_write = INVALID_HANDLE_VALUE;
    HANDLE null_input = INVALID_HANDLE_VALUE;
    HANDLE job = INVALID_HANDLE_VALUE;
    HANDLE drain_threads[3] = {INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE,
        INVALID_HANDLE_VALUE};
    DrainContext drains[3];
    CleanupList cleanup = {0};
    STARTUPINFOEXW startup;
    PROCESS_INFORMATION process;
    SIZE_T attribute_size = 0U;
    LPPROC_THREAD_ATTRIBUTE_LIST attributes = NULL;
    HANDLE inherited_handles[4];
    HANDLE job_list[1];
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION job_info;
    BOOL in_job = FALSE;
    DWORD creation_flags = CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT |
        CREATE_NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT;
    DWORD wait_result = WAIT_FAILED;
    DWORD exit_code = 0U;
    int have_exit = 0;
    int timed_out = 0;
    int process_created = 0;
    int resumed = 0;
    int native_cleanup_done = 0;
    uintptr_t inherited_result_handle_value = 0U;
    char primary[512] = "";
    PyObject *result = NULL;
    size_t index;
    (void)self;
    memset(drains, 0, sizeof(drains));
    memset(&startup, 0, sizeof(startup));
    memset(&process, 0, sizeof(process));
    memset(&job_info, 0, sizeof(job_info));
    startup.StartupInfo.cb = sizeof(startup);
    for (index = 0U; index < 3U; ++index) {
        drains[index].read_handle = INVALID_HANDLE_VALUE;
    }
    if (!PyArg_UnpackTuple(
            args, "run_child", 4, 4, &plan, &run_number_object, &pair_object,
            &run_object) || !require_claimed("run_child")) {
        return NULL;
    }
    if (!g_state.outcome_reserved || !g_state.output_created ||
        g_state.outcome_committed || !exact_plan_keys(plan)) {
        return broker_error("run_child_broker_state_or_plan_refused");
    }
    if (!PyLong_CheckExact(run_number_object)) {
        return broker_error("run_number_exact_int_required");
    }
    run_number = PyLong_AsLong(run_number_object);
    if (PyErr_Occurred() || run_number != g_state.next_run_number ||
        (run_number != 1 && run_number != 2) ||
        !py_unicode_to_utf8_exact(pair_object, &pair_nonce, &pair_length) ||
        !py_unicode_to_utf8_exact(run_object, &run_nonce, &run_length) ||
        pair_length != 64 || run_length != 64 || !is_lower_hex64(pair_nonce) ||
        !is_lower_hex64(run_nonce)) {
        return broker_error("run_identity_refused");
    }
    if ((run_number == 2 && strcmp(pair_nonce, g_state.pair_nonce) != 0) ||
        (run_number == 2 && strcmp(run_nonce, g_state.run_nonce_1) == 0)) {
        return broker_error("pair_or_run_nonce_reuse_refused");
    }
    schema_object = PyDict_GetItemString(plan, "schema");
    contract_hash_object = PyDict_GetItemString(plan, "contract_sha256");
    if (schema_object == NULL || contract_hash_object == NULL ||
        !py_unicode_to_utf8_exact(schema_object, &schema, &schema_length) ||
        !py_unicode_to_utf8_exact(
            contract_hash_object, &contract_hash, &contract_hash_length) ||
        schema_length != (Py_ssize_t)(sizeof(
            "kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r3") - 1U) ||
        memcmp(
            schema,
            "kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r3",
            sizeof("kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r3") - 1U
        ) != 0 || contract_hash_length != 64 ||
        !is_lower_hex64(contract_hash)) {
        return broker_error("native_child_plan_identity_drift");
    }
    {
        unsigned char parsed_contract_hash[32];
        if (!parse_hex64(contract_hash, parsed_contract_hash) ||
            !constant_time_equal32(
                parsed_contract_hash, g_state.expected_contract_sha256)) {
            secure_zero(parsed_contract_hash, sizeof(parsed_contract_hash));
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
        return NULL;
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
    environment_object = native_restricted_environment();
    if (environment_object == NULL) {
        goto python_failure;
    }
    environment_block = build_environment_block(environment_object);
    Py_CLEAR(environment_object);
    if (environment_block == NULL) {
        goto python_failure;
    }
    if (!create_inherited_pipe(&frame_read, &frame_write) ||
        !create_inherited_pipe(&stdout_read, &stdout_write) ||
        !create_inherited_pipe(&stderr_read, &stderr_write)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_pipe_create_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    inherited_result_handle_value = (uintptr_t)frame_write;
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
        wchar_t result_handle_text[32];
        wchar_t run_number_text[8];
        wchar_t *contract_hash_wide = utf8_to_wide_strict(contract_hash, 64U);
        wchar_t *pair_nonce_wide = utf8_to_wide_strict(pair_nonce, 64U);
        wchar_t *run_nonce_wide = utf8_to_wide_strict(run_nonce, 64U);
        _snwprintf_s(result_handle_text, 32U, _TRUNCATE, L"%" PRIuPTR,
            (uintptr_t)frame_write);
        _snwprintf_s(run_number_text, 8U, _TRUNCATE, L"%ld", run_number);
        if (contract_hash_wide == NULL || pair_nonce_wide == NULL ||
            run_nonce_wide == NULL ||
            !add_wide_copy(&arguments, executable_row->path) ||
            !add_wide_copy(&arguments, L"--background") ||
            !add_wide_copy(&arguments, L"--factory-startup") ||
            !add_wide_copy(&arguments, L"--disable-autoexec") ||
            !add_wide_copy(&arguments, foundation_row->path) ||
            !add_wide_copy(&arguments, L"--python-exit-code") ||
            !add_wide_copy(&arguments, L"1") ||
            !add_wide_copy(&arguments, L"--python") ||
            !add_wide_copy(&arguments, wrapper_row->path) ||
            !add_wide_copy(&arguments, L"--") ||
            !add_wide_copy(&arguments, L"--result-handle") ||
            !add_wide_copy(&arguments, result_handle_text) ||
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
    inherited_handles[0] = frame_write;
    inherited_handles[1] = stdout_write;
    inherited_handles[2] = stderr_write;
    inherited_handles[3] = null_input;
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
    if (run_number == 1) {
        memcpy(g_state.pair_nonce, pair_nonce, 65U);
        memcpy(g_state.run_nonce_1, run_nonce, 65U);
    } else {
        memcpy(g_state.run_nonce_2, run_nonce, 65U);
    }
    ++g_state.next_run_number; /* An attempted numbered child is never replayed. */
    if (!CreateProcessW(
            executable_row->path, command_line, NULL, NULL, TRUE,
            creation_flags, environment_block, cwd, &startup.StartupInfo,
            &process)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "create_suspended_child_failed:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    process_created = 1;
    g_state.active_process = 1;
    if (!IsProcessInJob(process.hProcess, job, &in_job) || !in_job) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "suspended_child_not_in_native_job:winerror=%lu",
            (unsigned long)GetLastError());
        goto native_cleanup;
    }
    drains[0].read_handle = frame_read;
    drains[0].maximum = max_frame;
    drains[1].read_handle = stdout_read;
    drains[1].maximum = max_stdout;
    drains[2].read_handle = stderr_read;
    drains[2].maximum = max_stderr;
    for (index = 0U; index < 3U; ++index) {
        drain_threads[index] = CreateThread(
            NULL, 0U, drain_thread_main, &drains[index], 0U, NULL
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
    close_handle_record(&frame_write, &cleanup, "parent_frame_write");
    close_handle_record(&stdout_write, &cleanup, "parent_stdout_write");
    close_handle_record(&stderr_write, &cleanup, "parent_stderr_write");
    close_handle_record(&null_input, &cleanup, "parent_null_input");
    Py_BEGIN_ALLOW_THREADS
    wait_result = WaitForSingleObject(process.hProcess, timeout_milliseconds);
    Py_END_ALLOW_THREADS
    if (wait_result == WAIT_TIMEOUT) {
        timed_out = 1;
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_timeout_after_%lu_ms", (unsigned long)timeout_milliseconds);
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
        if (wait_result == WAIT_OBJECT_0) {
            g_state.active_process = 0;
        }
    } else if (wait_result != WAIT_OBJECT_0) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_wait_failed:wait=%lu:winerror=%lu",
            (unsigned long)wait_result, (unsigned long)GetLastError());
    } else {
        g_state.active_process = 0;
    }
    if (GetExitCodeProcess(process.hProcess, &exit_code)) {
        have_exit = 1;
    } else {
        (void)cleanup_add(&cleanup, "get_exit_code:winerror=%lu",
            (unsigned long)GetLastError());
    }

native_cleanup:
    if (process_created && (primary[0] != '\0' || !resumed) &&
        g_state.active_process) {
        if (!TerminateJobObject(job, 0xE0000002U)) {
            (void)cleanup_add(&cleanup,
                "suspended_failure_terminate_job:winerror=%lu",
                (unsigned long)GetLastError());
        }
        if (WaitForSingleObject(
                process.hProcess, TERMINATION_WAIT_MILLISECONDS) !=
            WAIT_OBJECT_0) {
            (void)cleanup_add(&cleanup, "suspended_failure_process_wait");
        } else {
            g_state.active_process = 0;
        }
    }
    close_handle_record(&frame_write, &cleanup, "frame_write");
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
    if (drain_threads[0] != INVALID_HANDLE_VALUE) {
        (void)wait_and_close_drain(
            &drain_threads[0], &drains[0], &cleanup, "frame_drain");
    }
    if (drain_threads[1] != INVALID_HANDLE_VALUE) {
        (void)wait_and_close_drain(
            &drain_threads[1], &drains[1], &cleanup, "stdout_drain");
    }
    if (drain_threads[2] != INVALID_HANDLE_VALUE) {
        (void)wait_and_close_drain(
            &drain_threads[2], &drains[2], &cleanup, "stderr_drain");
    }
    if (drains[0].read_handle != INVALID_HANDLE_VALUE) {
        frame_read = drains[0].read_handle;
    }
    if (drains[1].read_handle != INVALID_HANDLE_VALUE) {
        stdout_read = drains[1].read_handle;
    }
    if (drains[2].read_handle != INVALID_HANDLE_VALUE) {
        stderr_read = drains[2].read_handle;
    }
    close_handle_record(&frame_read, &cleanup, "frame_read");
    close_handle_record(&stdout_read, &cleanup, "stdout_read");
    close_handle_record(&stderr_read, &cleanup, "stderr_read");
    close_handle_record(&process.hThread, &cleanup, "process_thread");
    close_handle_record(&process.hProcess, &cleanup, "process_handle");
    close_handle_record(&job, &cleanup, "kill_on_close_job");
    if (attributes != NULL) {
        DeleteProcThreadAttributeList(attributes);
        HeapFree(GetProcessHeap(), 0U, attributes);
        attributes = NULL;
    }
    native_cleanup_done = 1;
    if (primary[0] == '\0' && drains[0].read_error != 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "frame_drain_failed:winerror=%lu",
            (unsigned long)drains[0].read_error);
    }
    if (primary[0] == '\0' && drains[1].read_error != 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "stdout_drain_failed:winerror=%lu",
            (unsigned long)drains[1].read_error);
    }
    if (primary[0] == '\0' && drains[2].read_error != 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "stderr_drain_failed:winerror=%lu",
            (unsigned long)drains[2].read_error);
    }
    if (primary[0] == '\0' && (!have_exit || exit_code != 0U)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_nonzero_or_unknown_exit:%lu", (unsigned long)exit_code);
    }
    if (primary[0] == '\0' &&
        (drains[0].overflow || drains[1].overflow || drains[2].overflow)) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "child_capture_limit_exceeded");
    }
    if (primary[0] == '\0' && cleanup.count != 0U) {
        _snprintf_s(primary, sizeof(primary), _TRUNCATE,
            "native_child_cleanup_failed");
    }
    if (primary[0] != '\0') {
        set_composite_child_error(primary, &cleanup);
        goto final_cleanup;
    }
    result = make_child_result(
        &drains[0], &drains[1], &drains[2], process.dwProcessId,
        exit_code, have_exit, timed_out, inherited_result_handle_value,
        &cleanup);
    goto final_cleanup;

python_failure:
    if (!native_cleanup_done &&
        (frame_read != INVALID_HANDLE_VALUE ||
         frame_write != INVALID_HANDLE_VALUE ||
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
    free(cwd);
    Py_XDECREF(environment_object);
    free(environment_block);
    wide_vector_free(&arguments);
    free(command_line);
    for (index = 0U; index < 3U; ++index) {
        secure_zero(drains[index].captured.data, drains[index].captured.size);
        free(drains[index].captured.data);
    }
    cleanup_list_free(&cleanup);
    return result;
}

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
    char escaped[4096];
    char receipt[4608];
    int length;
    LARGE_INTEGER zero;
    if (!g_state.outcome_reserved || g_state.outcome_committed ||
        g_state.outcome_handle == NULL ||
        g_state.outcome_handle == INVALID_HANDLE_VALUE) {
        return;
    }
    json_escape_ascii(reason != NULL ? reason : "unspecified_native_failure",
        escaped, sizeof(escaped));
    length = _snprintf_s(
        receipt, sizeof(receipt), _TRUNCATE,
        "{\"schema\":\"kira.avatar.r25.afes.native_outcome.v3r3\","
        "\"status\":\"FAILED\",\"native_broker_pid\":%lu,"
        "\"reason\":\"%s\"}\n",
        (unsigned long)g_state.process_id, escaped
    );
    if (length <= 0) {
        return;
    }
    zero.QuadPart = 0;
    if (SetFilePointerEx(g_state.outcome_handle, zero, NULL, FILE_BEGIN) &&
        SetEndOfFile(g_state.outcome_handle) &&
        write_all_handle(g_state.outcome_handle,
            (const unsigned char *)receipt, (size_t)length) &&
        FlushFileBuffers(g_state.outcome_handle)) {
        g_state.outcome_committed = 1;
    }
    secure_zero(receipt, sizeof(receipt));
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

static wchar_t *python_home_from_runtime(void) {
    HMODULE runtime = GetModuleHandleW(L"python314.dll");
    wchar_t *path;
    wchar_t *separator;
    if (runtime == NULL) {
        return NULL;
    }
    path = get_module_path(runtime);
    if (path == NULL) {
        return NULL;
    }
    separator = wcsrchr(path, L'\\');
    if (separator == NULL) {
        free(path);
        return NULL;
    }
    *separator = L'\0';
    return path;
}

static int execute_retained_bootstrap(
    int bootstrap_argc, wchar_t **bootstrap_argv,
    const char *bootstrap_label, char *error, size_t error_size
) {
    PyStatus status;
    PyConfig config;
    wchar_t *python_home = NULL;
    ByteBuffer source = {0};
    RetainedRow *bootstrap = &g_state.rows[g_state.bootstrap_index];
    PyObject *globals = NULL;
    PyObject *code = NULL;
    PyObject *evaluation = NULL;
    PyObject *builtins = NULL;
    PyObject *value = NULL;
    char bootstrap_hash[65];
    int initialized = 0;
    int result = 0;
    int index;
    if (PyImport_AppendInittab(
            BROKER_MODULE_NAME, PyInit__kira_r25_afes_native_broker) == -1) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "append_private_builtin_failed");
        return 0;
    }
    python_home = python_home_from_runtime();
    if (python_home == NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "python314_runtime_home_not_found");
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
    status = PyConfig_SetString(&config, &config.program_name, g_state.self_path);
    if (!PyStatus_Exception(status)) {
        status = PyConfig_SetString(&config, &config.executable, g_state.self_path);
    }
    if (!PyStatus_Exception(status)) {
        status = PyConfig_SetString(&config, &config.home, python_home);
    }
    if (!PyStatus_Exception(status)) {
        status = PyWideStringList_Append(
            &config.argv, L"<native-retained-bootstrap-v3r3>"
        );
    }
    for (index = 0; index < bootstrap_argc && !PyStatus_Exception(status);
         ++index) {
        status = PyWideStringList_Append(&config.argv, bootstrap_argv[index]);
    }
    if (PyStatus_Exception(status)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "embedded_python_config_failed:%s",
            status.err_msg != NULL ? status.err_msg : "unknown");
        PyConfig_Clear(&config);
        free(python_home);
        return 0;
    }
    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    free(python_home);
    if (PyStatus_Exception(status)) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "embedded_python_initialize_failed:%s",
            status.err_msg != NULL ? status.err_msg : "unknown");
        return 0;
    }
    initialized = 1;
    if (!read_handle_all(
            bootstrap->handle, bootstrap->expected_bytes,
            MAX_LOCKED_READ_BYTES, &source) ||
        memchr(source.data, '\0', source.size) != NULL) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "retained_bootstrap_read_or_nul_failed");
        goto cleanup;
    }
    globals = PyDict_New();
    builtins = PyEval_GetBuiltins();
    if (globals == NULL || builtins == NULL ||
        PyDict_SetItemString(globals, "__builtins__", builtins) < 0) {
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
    value = PyUnicode_FromString("<native-retained-bootstrap-v3r3>");
    if (value == NULL || PyDict_SetItemString(globals, "__file__", value) < 0) {
        Py_XDECREF(value);
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    Py_CLEAR(value);
    if (PyDict_SetItemString(
            globals, "__KIRA_NATIVE_BROKER_V3R3__", Py_True) < 0) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
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
        (const char *)source.data, "<native-retained-bootstrap-v3r3>",
        Py_file_input, NULL, -1
    );
    if (code == NULL) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    evaluation = PyEval_EvalCode(code, globals, globals);
    if (evaluation == NULL) {
        fetch_python_error(error, error_size);
        goto cleanup;
    }
    if (!g_state.finished) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "retained_bootstrap_returned_without_native_finish");
        goto cleanup;
    }
    result = 1;
cleanup:
    Py_XDECREF(evaluation);
    Py_XDECREF(code);
    Py_XDECREF(globals);
    secure_zero(source.data, source.size);
    free(source.data);
    if (initialized && Py_FinalizeEx() < 0 && result) {
        _snprintf_s(error, error_size, _TRUNCATE,
            "embedded_python_finalize_failed");
        result = 0;
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
        fwprintf(stderr, L"KIRA_R25_AFES_NATIVE_V3R3_REFUSED: %hs\n", error);
        return 2;
    }
    if (!initialize_locked_state(
            parsed.project_root, parsed.manifest_path, parsed.manifest_sha256,
            parsed.contract_sha256, parsed.audit_path, parsed.audit_sha256,
            parsed.bootstrap_label, error, sizeof(error))) {
        fwprintf(stderr, L"KIRA_R25_AFES_NATIVE_V3R3_REFUSED: %hs\n", error);
        cleanup_state();
        return 3;
    }
    ok = execute_retained_bootstrap(
        parsed.bootstrap_argc, parsed.bootstrap_argv, parsed.bootstrap_label,
        error, sizeof(error)
    );
    if (!ok) {
        commit_native_failure_if_reserved(error);
        fwprintf(stderr, L"KIRA_R25_AFES_NATIVE_V3R3_FAILED: %hs\n", error);
        cleanup_state();
        return 4;
    }
    cleanup_state();
    return 0;
}
