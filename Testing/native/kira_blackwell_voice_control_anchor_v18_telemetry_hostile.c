#define wmain kira_blackwell_voice_control_anchor_v18_candidate_entrypoint_unreachable
#include "../../tools/native/kira_blackwell_voice_control_anchor_v18.c"
#undef wmain

typedef enum FakeKind {
    FAKE_TUPLE,
    FAKE_STRING,
    FAKE_BOOLEAN,
    FAKE_LONG,
    FAKE_OTHER
} FakeKind;

typedef struct FakeObject {
    FakeKind kind;
    Py_ssize_t tuple_size;
    struct FakeObject *items[10];
    const char *text;
    Py_ssize_t text_length;
    long long integer;
    int truth;
} FakeObject;

static int fake_error;
static int fake_truth_calls;
static int fake_error_on_truth_call;
static FakeObject fake_error_object;

static Py_ssize_t fake_tuple_size(PyObject *value) {
    FakeObject *object = (FakeObject *)value;
    if (object == NULL || object->kind != FAKE_TUPLE) {
        fake_error = 1;
        return -1;
    }
    return object->tuple_size;
}

static PyObject *fake_tuple_get(PyObject *value, Py_ssize_t index) {
    FakeObject *object = (FakeObject *)value;
    if (object == NULL || object->kind != FAKE_TUPLE || index < 0 ||
        index >= object->tuple_size) {
        fake_error = 1;
        return NULL;
    }
    return (PyObject *)object->items[index];
}

static const char *fake_unicode_utf8(PyObject *value, Py_ssize_t *length) {
    FakeObject *object = (FakeObject *)value;
    if (object == NULL || object->kind != FAKE_STRING || length == NULL) {
        fake_error = 1;
        return NULL;
    }
    *length = object->text_length;
    return object->text;
}

static long long fake_long_as_ll(PyObject *value) {
    FakeObject *object = (FakeObject *)value;
    if (object == NULL || object->kind != FAKE_LONG) {
        fake_error = 1;
        return -1LL;
    }
    return object->integer;
}

static int fake_truth(PyObject *value) {
    FakeObject *object = (FakeObject *)value;
    ++fake_truth_calls;
    if (fake_error_on_truth_call != 0 && fake_truth_calls == fake_error_on_truth_call)
        fake_error = 1;
    if (object == NULL || object->kind != FAKE_BOOLEAN) {
        fake_error = 1;
        return -1;
    }
    return object->truth;
}

static PyObject *fake_error_occurred(void) {
    return fake_error ? (PyObject *)&fake_error_object : NULL;
}

static void fake_error_fetch(PyObject **type, PyObject **value, PyObject **traceback) {
    if (type != NULL) *type = NULL;
    if (value != NULL) *value = NULL;
    if (traceback != NULL) *traceback = NULL;
    fake_error = 0;
}

static void fake_error_normalize(PyObject **type, PyObject **value, PyObject **traceback) {
    (void)type;
    (void)value;
    (void)traceback;
}

static void fake_error_clear(void) {
    fake_error = 0;
}

static void fake_decref(PyObject *value) {
    (void)value;
}

static void reset_fixture(PythonApi *api, PythonDiagnosis *diagnosis,
    FakeObject *tuple, FakeObject objects[10]) {
    size_t index;
    static const char schema[] = "kira.blackwell.v15.native_validator_result.v1";
    SecureZeroMemory(api, sizeof(*api));
    SecureZeroMemory(diagnosis, sizeof(*diagnosis));
    SecureZeroMemory(tuple, sizeof(*tuple));
    SecureZeroMemory(objects, sizeof(FakeObject) * 10U);
    tuple->kind = FAKE_TUPLE;
    tuple->tuple_size = 10;
    for (index = 0U; index < 10U; ++index) tuple->items[index] = &objects[index];
    objects[0].kind = FAKE_STRING;
    objects[0].text = schema;
    objects[0].text_length = (Py_ssize_t)(sizeof(schema) - 1U);
    objects[1].kind = FAKE_BOOLEAN;
    objects[1].truth = 1;
    objects[2].kind = FAKE_LONG;
    objects[2].integer = 6LL;
    objects[3].kind = FAKE_LONG;
    objects[3].integer = 1LL;
    for (index = 4U; index < 10U; ++index) {
        objects[index].kind = FAKE_BOOLEAN;
        objects[index].truth = 0;
    }
    api->tuple_size = fake_tuple_size;
    api->tuple_get = fake_tuple_get;
    api->unicode_utf8 = fake_unicode_utf8;
    api->long_as_ll = fake_long_as_ll;
    api->truth = fake_truth;
    api->error_occurred = fake_error_occurred;
    api->error_fetch = fake_error_fetch;
    api->error_normalize = fake_error_normalize;
    api->error_clear = fake_error_clear;
    api->decref = fake_decref;
    fake_error = 0;
    fake_truth_calls = 0;
    fake_error_on_truth_call = 0;
    diagnosis->result_tuple_size = -1LL;
}

static int checks;
static int failures;

#define CHECK(condition, label) do { \
    ++checks; \
    if (!(condition)) { \
        ++failures; \
        fprintf(stderr, "FAIL %s\n", (label)); \
    } \
} while (0)

static void expect_refusal(PythonApi *api, PythonDiagnosis *diagnosis,
    FakeObject *tuple, uint32_t expected_stage, uint32_t expected_code,
    const char *label) {
    uint32_t stage = 0U;
    const int accepted = result_exact(api, (PyObject *)tuple, &stage, diagnosis);
    CHECK(accepted == 0, label);
    CHECK(stage == expected_stage, label);
    CHECK(diagnosis->result_failure_code == expected_code, label);
}

int main(void) {
    PythonApi api;
    PythonDiagnosis diagnosis;
    FakeObject tuple;
    FakeObject objects[10];
    uint32_t stage;
    size_t index;
    char sanitized[8];
    uint32_t length;

    reset_fixture(&api, &diagnosis, &tuple, objects);
    stage = 0U;
    CHECK(result_exact(&api, (PyObject *)&tuple, &stage, &diagnosis) == 1,
        "exact result accepted");
    CHECK(stage == 75U, "exact result terminal stage");
    CHECK(diagnosis.result_failure_code == 0U, "exact result failure code");
    CHECK(diagnosis.result_tuple_size == 10LL, "exact result tuple size");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.tuple_size = 9;
    expect_refusal(&api, &diagnosis, &tuple, 60U, 10U, "tuple size");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[0].kind = FAKE_OTHER;
    expect_refusal(&api, &diagnosis, &tuple, 61U, 11U, "schema type");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[0].text = "kira.blackwell.v15.native_validator_result.v0";
    expect_refusal(&api, &diagnosis, &tuple, 62U, 12U, "schema value");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[1].truth = 0;
    expect_refusal(&api, &diagnosis, &tuple, 63U, 13U, "success boolean");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[2].kind = FAKE_OTHER;
    expect_refusal(&api, &diagnosis, &tuple, 64U, 14U, "predecessor type");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[2].integer = 5LL;
    expect_refusal(&api, &diagnosis, &tuple, 65U, 15U, "predecessor value");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[3].kind = FAKE_OTHER;
    expect_refusal(&api, &diagnosis, &tuple, 66U, 16U, "graph type");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[3].integer = 0LL;
    expect_refusal(&api, &diagnosis, &tuple, 67U, 17U, "graph value");

    for (index = 4U; index < 10U; ++index) {
        reset_fixture(&api, &diagnosis, &tuple, objects);
        objects[index].truth = 1;
        expect_refusal(&api, &diagnosis, &tuple, (uint32_t)(64U + index),
            (uint32_t)(14U + index), "false boolean field");
    }

    reset_fixture(&api, &diagnosis, &tuple, objects);
    fake_error_on_truth_call = 7;
    expect_refusal(&api, &diagnosis, &tuple, 74U, 24U, "pending error");

    length = copy_sanitized_python_text("A\n\x80Z", 4, sanitized, sizeof(sanitized));
    CHECK(length == 4U, "sanitized length");
    CHECK(sanitized[0] == 'A', "sanitized ASCII");
    CHECK(sanitized[1] == ' ', "sanitized newline");
    CHECK(sanitized[2] == '?', "sanitized non-ASCII");
    CHECK(sanitized[3] == 'Z' && sanitized[4] == '\0', "sanitized terminator");
    length = copy_sanitized_python_text("abcdef", 6, sanitized, 4U);
    CHECK(length == 3U, "sanitized bounded length");
    CHECK(strcmp(sanitized, "abc") == 0, "sanitized bounded text");
    CHECK(copy_sanitized_python_text(NULL, 0, sanitized, sizeof(sanitized)) == 0U,
        "sanitized null input");
    CHECK(sizeof(((PythonDiagnosis *)0)->exception_type) == EXCEPTION_TYPE_CAP,
        "exception type capacity");
    CHECK(sizeof(((PythonDiagnosis *)0)->exception_message) == EXCEPTION_MESSAGE_CAP,
        "exception message capacity");
    CHECK(sizeof(PythonDiagnosis) == 280U, "diagnosis packed payload expectation");
    CHECK(sizeof(ReservationRecord) == 336U, "reservation size retained");
    CHECK(sizeof(CompletionRecord) == 644U, "completion diagnostic size");

    printf("SUMMARY checks=%d failures=%d candidate_entrypoint_invoked=0 python_invoked=0\n",
        checks, failures);
    return failures == 0 ? 0 : 1;
}
