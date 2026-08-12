#define wmain kira_blackwell_voice_control_anchor_v17_candidate_entrypoint_unreachable
#include "../../tools/native/kira_blackwell_voice_control_anchor_v17.c"
#undef wmain

#include "kira_blackwell_voice_control_anchor_v17_manifest_fixture.h"

static const char HARNESS_PREFIX[] =
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

static int failures = 0;
static int checks = 0;

static void report(const char *name, int passed) {
    ++checks;
    if (!passed) ++failures;
    printf("%s\t%s\n", passed ? "PASS" : "FAIL", name);
}

static int extract_expected(Binding expected[V17_SEALED_SUBJECT_COUNT],
    ParsedSubject parsed[V17_SEALED_SUBJECT_COUNT]) {
    ManifestCursor input;
    size_t index;
    input.cursor = V17_CANONICAL_SEAL;
    input.end = V17_CANONICAL_SEAL + V17_CANONICAL_SEAL_BYTES;
    if (!manifest_consume(&input, HARNESS_PREFIX)) return 0;
    for (index = 0U; index < V17_SEALED_SUBJECT_COUNT; ++index) {
        if (index != 0U && !manifest_consume(&input, ",")) return 0;
        if (!manifest_subject(&input, &parsed[index])) return 0;
        expected[index].path = NULL;
        expected[index].relative_path = parsed[index].path;
        expected[index].bytes = parsed[index].bytes;
        expected[index].sha256 = parsed[index].sha256;
        expected[index].label = "compiled hostile fixture";
    }
    return manifest_consume(&input, "]}") && input.cursor == input.end;
}

static const unsigned char *find_once(const unsigned char *source, size_t source_bytes,
    const unsigned char *needle, size_t needle_bytes) {
    const unsigned char *found = NULL;
    size_t index;
    if (source == NULL || needle == NULL || needle_bytes == 0U ||
        needle_bytes > source_bytes) return NULL;
    for (index = 0U; index + needle_bytes <= source_bytes; ++index) {
        if (memcmp(source + index, needle, needle_bytes) == 0) {
            if (found != NULL) return NULL;
            found = source + index;
        }
    }
    return found;
}

static unsigned char *replace_once(const unsigned char *source, size_t source_bytes,
    const unsigned char *needle, size_t needle_bytes,
    const unsigned char *replacement, size_t replacement_bytes, size_t *output_bytes) {
    const unsigned char *where;
    unsigned char *output;
    size_t prefix;
    size_t total;
    if (output_bytes == NULL || replacement == NULL) return NULL;
    *output_bytes = 0U;
    where = find_once(source, source_bytes, needle, needle_bytes);
    if (where == NULL || source_bytes - needle_bytes > SIZE_MAX - replacement_bytes)
        return NULL;
    prefix = (size_t)(where - source);
    total = source_bytes - needle_bytes + replacement_bytes;
    output = (unsigned char *)HeapAlloc(GetProcessHeap(), 0U, total + 1U);
    if (output == NULL) return NULL;
    memcpy(output, source, prefix);
    memcpy(output + prefix, replacement, replacement_bytes);
    memcpy(output + prefix + replacement_bytes, where + needle_bytes,
        source_bytes - prefix - needle_bytes);
    output[total] = 0U;
    *output_bytes = total;
    return output;
}

static unsigned char *append_bytes(const unsigned char *source, size_t source_bytes,
    const unsigned char *suffix, size_t suffix_bytes, size_t *output_bytes) {
    unsigned char *output;
    if (source == NULL || suffix == NULL || output_bytes == NULL ||
        source_bytes > SIZE_MAX - suffix_bytes) return NULL;
    output = (unsigned char *)HeapAlloc(GetProcessHeap(), 0U,
        source_bytes + suffix_bytes + 1U);
    if (output == NULL) return NULL;
    memcpy(output, source, source_bytes);
    memcpy(output + source_bytes, suffix, suffix_bytes);
    output[source_bytes + suffix_bytes] = 0U;
    *output_bytes = source_bytes + suffix_bytes;
    return output;
}

static int exact_row(const Binding *binding, char *output, size_t output_size) {
    const int length = _snprintf_s(output, output_size, _TRUNCATE,
        "{\"path\":\"%s\",\"bytes\":%llu,\"sha256\":\"%s\"}",
        binding->relative_path, (unsigned long long)binding->bytes, binding->sha256);
    return length > 0 && (size_t)length < output_size;
}

static void expect_replacement_refusal(const char *name, const unsigned char *needle,
    size_t needle_bytes, const unsigned char *replacement, size_t replacement_bytes,
    const Binding expected[V17_SEALED_SUBJECT_COUNT]) {
    size_t bytes = 0U;
    unsigned char *mutation = replace_once(V17_CANONICAL_SEAL, V17_CANONICAL_SEAL_BYTES,
        needle, needle_bytes, replacement, replacement_bytes, &bytes);
    const int passed = mutation != NULL &&
        !seal_contract_exact(mutation, bytes, expected, V17_SEALED_SUBJECT_COUNT);
    report(name, passed);
    if (mutation != NULL) HeapFree(GetProcessHeap(), 0U, mutation);
}

static void expect_string_replacement_refusal(const char *name, const char *needle,
    const char *replacement, const Binding expected[V17_SEALED_SUBJECT_COUNT]) {
    expect_replacement_refusal(name, (const unsigned char *)needle, strlen(needle),
        (const unsigned char *)replacement, strlen(replacement), expected);
}

static void expect_append_refusal(const char *name, const unsigned char *suffix,
    size_t suffix_bytes, const Binding expected[V17_SEALED_SUBJECT_COUNT]) {
    size_t bytes = 0U;
    unsigned char *mutation = append_bytes(V17_CANONICAL_SEAL, V17_CANONICAL_SEAL_BYTES,
        suffix, suffix_bytes, &bytes);
    const int passed = mutation != NULL &&
        !seal_contract_exact(mutation, bytes, expected, V17_SEALED_SUBJECT_COUNT);
    report(name, passed);
    if (mutation != NULL) HeapFree(GetProcessHeap(), 0U, mutation);
}

static void test_path_refusals(const Binding expected[V17_SEALED_SUBJECT_COUNT]) {
    static const char *const paths[] = {
        "tools/.", "tools/..", ".", "..", "./x", "../x", "x/./y",
        "x/../y", "x//y", "/x", "x/", "x\\y", "x/y\\z", "C:/Other/x",
        "x:y", "x\x01y", "x\x80y", "x\"y"
    };
    size_t index;
    const char *good = expected[0].relative_path;
    for (index = 0U; index < _countof(paths); ++index) {
        char label[160];
        _snprintf_s(label, sizeof(label), _TRUNCATE, "path refused: case %llu",
            (unsigned long long)index);
        report(label, !canonical_manifest_path(paths[index]));
        expect_replacement_refusal(label, (const unsigned char *)good, strlen(good),
            (const unsigned char *)paths[index], strlen(paths[index]), expected);
    }
    report("exact absolute Python binding accepted",
        canonical_manifest_path("C:/Python314/python314.dll"));
    report("ordinary canonical relative binding accepted",
        canonical_manifest_path("tools/native/example.bin"));
}

static void test_document_and_row_mutations(
    const Binding expected[V17_SEALED_SUBJECT_COUNT]) {
    char row0[2304];
    char row1[2304];
    char row54[2304];
    char needle[2500];
    char replacement[5000];
    static const unsigned char nul_byte[] = {0U};
    if (!exact_row(&expected[0], row0, sizeof(row0)) ||
        !exact_row(&expected[1], row1, sizeof(row1)) ||
        !exact_row(&expected[54], row54, sizeof(row54))) {
        report("fixture rows formatted", 0);
        return;
    }

    expect_append_refusal("V16 bypass: trailing non-JSON byte refused",
        (const unsigned char *)"X", 1U, expected);
    expect_append_refusal("trailing LF refused", (const unsigned char *)"\n", 1U, expected);
    expect_append_refusal("trailing space refused", (const unsigned char *)" ", 1U, expected);
    expect_append_refusal("trailing tab refused", (const unsigned char *)"\t", 1U, expected);
    expect_append_refusal("trailing CR refused", (const unsigned char *)"\r", 1U, expected);
    expect_append_refusal("trailing NUL refused", nul_byte, sizeof(nul_byte), expected);

    expect_string_replacement_refusal("declared count 54 refused",
        "\"sealed_subject_count\":55", "\"sealed_subject_count\":54", expected);
    expect_string_replacement_refusal("declared count 56 refused",
        "\"sealed_subject_count\":55", "\"sealed_subject_count\":56", expected);
    expect_string_replacement_refusal("declared count quoted refused",
        "\"sealed_subject_count\":55", "\"sealed_subject_count\":\"55\"", expected);

    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE, ",%s]}", row0);
    expect_string_replacement_refusal("extra exact 56th subject refused", "]}", replacement,
        expected);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        ",{\"path\": \"%s\", \"bytes\": %llu, \"sha256\": \"%s\"}]}",
        expected[0].relative_path, (unsigned long long)expected[0].bytes,
        expected[0].sha256);
    expect_string_replacement_refusal(
        "V16 bypass: whitespace logical duplicate/56th subject refused", "]}", replacement,
        expected);

    expect_string_replacement_refusal("duplicate exact row with missing expected row refused",
        row1, row0, expected);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        "{\"path\":\"%s\",\"bytes\":%llu,\"sha256\":\"%s\"}",
        expected[0].relative_path, (unsigned long long)expected[1].bytes,
        expected[1].sha256);
    expect_string_replacement_refusal("duplicate path with changed bytes and digest refused",
        row1, replacement, expected);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        "{\"path\":\"%s\",\"bytes\":%llu,\"sha256\":\"%s\"}",
        expected[0].relative_path, (unsigned long long)expected[1].bytes,
        expected[0].sha256);
    expect_string_replacement_refusal("cross-row field splice refused", row1, replacement,
        expected);

    _snprintf_s(needle, sizeof(needle), _TRUNCATE, "%s,", row0);
    expect_string_replacement_refusal("missing expected row refused", needle, "", expected);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        ",{\"path\":\"unknown/new.bin\",\"bytes\":1,\"sha256\":\"%s\"}]}",
        expected[0].sha256);
    expect_string_replacement_refusal("extra unknown row refused", "]}", replacement, expected);
    _snprintf_s(needle, sizeof(needle), _TRUNCATE, "%s,%s", row0, row1);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE, "%s,%s", row1, row0);
    expect_string_replacement_refusal("reordered subject rows refused", needle, replacement,
        expected);

    expect_string_replacement_refusal("leading whitespace refused", "{\"schema\"",
        " {\"schema\"", expected);
    expect_string_replacement_refusal("top-level missing key refused",
        ",\"candidate_id\":\"kira_chatterbox_blackwell_native_whole_document_manifest_control_anchor_candidate_v17\"",
        "", expected);
    expect_string_replacement_refusal("top-level extra key refused",
        "\"execution_authority\":\"NONE\"",
        "\"execution_authority\":\"NONE\",\"unknown\":0", expected);
    expect_string_replacement_refusal("top-level duplicate key refused",
        "\"execution_authority\":\"NONE\"",
        "\"execution_authority\":\"NONE\",\"execution_authority\":\"NONE\"", expected);
    expect_string_replacement_refusal("top-level reordered fields refused",
        "\"execution_authority\":\"NONE\",\"candidate_executed\":false",
        "\"candidate_executed\":false,\"execution_authority\":\"NONE\"", expected);
    expect_string_replacement_refusal("top-level value wrong type refused",
        "\"candidate_executed\":false", "\"candidate_executed\":0", expected);

    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        "{\"bytes\":%llu,\"sha256\":\"%s\"}",
        (unsigned long long)expected[0].bytes, expected[0].sha256);
    expect_string_replacement_refusal("row missing path key refused", row0, replacement, expected);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        "{\"path\":\"%s\",\"bytes\":%llu,\"extra\":0,\"sha256\":\"%s\"}",
        expected[0].relative_path, (unsigned long long)expected[0].bytes,
        expected[0].sha256);
    expect_string_replacement_refusal("row extra key refused", row0, replacement, expected);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        "{\"path\":\"%s\",\"path\":\"%s\",\"bytes\":%llu,\"sha256\":\"%s\"}",
        expected[0].relative_path, expected[0].relative_path,
        (unsigned long long)expected[0].bytes, expected[0].sha256);
    expect_string_replacement_refusal("row duplicate key refused", row0, replacement, expected);
    _snprintf_s(replacement, sizeof(replacement), _TRUNCATE,
        "{\"bytes\":%llu,\"path\":\"%s\",\"sha256\":\"%s\"}",
        (unsigned long long)expected[0].bytes, expected[0].relative_path,
        expected[0].sha256);
    expect_string_replacement_refusal("row reordered keys refused", row0, replacement, expected);

    _snprintf_s(needle, sizeof(needle), _TRUNCATE, "\"bytes\":%llu",
        (unsigned long long)expected[0].bytes);
    {
        static const char *const bad_bytes[] = {
            "\"bytes\":0", "\"bytes\":-1", "\"bytes\":+1", "\"bytes\":01",
            "\"bytes\":1.0", "\"bytes\":1e1", "\"bytes\":18446744073709551616",
            "\"bytes\":\"1\"", "\"bytes\":true"
        };
        size_t index;
        for (index = 0U; index < _countof(bad_bytes); ++index) {
            char label[128];
            _snprintf_s(label, sizeof(label), _TRUNCATE, "noncanonical bytes refused: %llu",
                (unsigned long long)index);
            expect_string_replacement_refusal(label, needle, bad_bytes[index], expected);
        }
    }

    _snprintf_s(needle, sizeof(needle), _TRUNCATE, "\"sha256\":\"%s\"",
        expected[0].sha256);
    {
        char short_digest[SHA_HEX];
        char long_digest[SHA_HEX + 2U];
        char upper_digest[SHA_HEX + 1U];
        char nonhex_digest[SHA_HEX + 1U];
        char digest_field[SHA_HEX + 32U];
        memcpy(short_digest, expected[0].sha256, SHA_HEX - 1U);
        short_digest[SHA_HEX - 1U] = '\0';
        memcpy(long_digest, expected[0].sha256, SHA_HEX);
        long_digest[SHA_HEX] = '0';
        long_digest[SHA_HEX + 1U] = '\0';
        memcpy(upper_digest, expected[0].sha256, SHA_HEX + 1U);
        upper_digest[0] = 'A';
        memcpy(nonhex_digest, expected[0].sha256, SHA_HEX + 1U);
        nonhex_digest[0] = 'g';
        _snprintf_s(digest_field, sizeof(digest_field), _TRUNCATE,
            "\"sha256\":\"%s\"", short_digest);
        expect_string_replacement_refusal("63-digit digest refused", needle, digest_field,
            expected);
        _snprintf_s(digest_field, sizeof(digest_field), _TRUNCATE,
            "\"sha256\":\"%s\"", long_digest);
        expect_string_replacement_refusal("65-digit digest refused", needle, digest_field,
            expected);
        _snprintf_s(digest_field, sizeof(digest_field), _TRUNCATE,
            "\"sha256\":\"%s\"", upper_digest);
        expect_string_replacement_refusal("uppercase digest refused", needle, digest_field,
            expected);
        _snprintf_s(digest_field, sizeof(digest_field), _TRUNCATE,
            "\"sha256\":\"%s\"", nonhex_digest);
        expect_string_replacement_refusal("nonhex digest refused", needle, digest_field,
            expected);
        _snprintf_s(digest_field, sizeof(digest_field), _TRUNCATE,
            "\"sha256\":\"%s\"junk", expected[0].sha256);
        expect_string_replacement_refusal("quoted-junk digest refused", needle, digest_field,
            expected);
    }

    {
        const unsigned char *where = find_once(V17_CANONICAL_SEAL,
            V17_CANONICAL_SEAL_BYTES, (const unsigned char *)needle, strlen(needle));
        unsigned char *mutation = (unsigned char *)HeapAlloc(GetProcessHeap(), 0U,
            V17_CANONICAL_SEAL_BYTES + 1U);
        int passed = 0;
        if (where != NULL && mutation != NULL) {
            const size_t quote_offset = (size_t)(where - V17_CANONICAL_SEAL) +
                strlen("\"sha256\":\"") + SHA_HEX;
            memcpy(mutation, V17_CANONICAL_SEAL, V17_CANONICAL_SEAL_BYTES);
            mutation[quote_offset] = 0U;
            passed = !seal_contract_exact(mutation, V17_CANONICAL_SEAL_BYTES,
                expected, V17_SEALED_SUBJECT_COUNT);
        }
        report("NUL-suffixed digest refused", passed);
        if (mutation != NULL) HeapFree(GetProcessHeap(), 0U, mutation);
    }

    {
        const unsigned char *where = find_once(V17_CANONICAL_SEAL,
            V17_CANONICAL_SEAL_BYTES, (const unsigned char *)expected[0].relative_path,
            strlen(expected[0].relative_path));
        unsigned char *mutation = (unsigned char *)HeapAlloc(GetProcessHeap(), 0U,
            V17_CANONICAL_SEAL_BYTES + 1U);
        int passed = 0;
        if (where != NULL && mutation != NULL) {
            const size_t offset = (size_t)(where - V17_CANONICAL_SEAL) + 5U;
            memcpy(mutation, V17_CANONICAL_SEAL, V17_CANONICAL_SEAL_BYTES);
            mutation[offset] = 0U;
            passed = !seal_contract_exact(mutation, V17_CANONICAL_SEAL_BYTES,
                expected, V17_SEALED_SUBJECT_COUNT);
        }
        report("NUL-bearing path refused", passed);
        if (mutation != NULL) HeapFree(GetProcessHeap(), 0U, mutation);
    }
}

int wmain(void) {
    Binding expected[V17_SEALED_SUBJECT_COUNT];
    ParsedSubject parsed[V17_SEALED_SUBJECT_COUNT];
    SecureZeroMemory(expected, sizeof(expected));
    SecureZeroMemory(parsed, sizeof(parsed));
    report("exact canonical fixture extracted", extract_expected(expected, parsed));
    if (failures == 0) {
        report("exact canonical whole document accepted",
            seal_contract_exact(V17_CANONICAL_SEAL, V17_CANONICAL_SEAL_BYTES,
                expected, V17_SEALED_SUBJECT_COUNT));
        test_path_refusals(expected);
        test_document_and_row_mutations(expected);
    }
    printf("SUMMARY\tchecks=%d\tfailures=%d\n", checks, failures);
    return failures == 0 ? 0 : 3;
}
