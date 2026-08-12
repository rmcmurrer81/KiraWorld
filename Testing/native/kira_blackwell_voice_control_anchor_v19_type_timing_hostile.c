#define wmain kira_blackwell_voice_control_anchor_v19_candidate_entrypoint_unreachable
#include "../../tools/native/kira_blackwell_voice_control_anchor_v19.c"
#undef wmain

typedef struct FakeObject {
    PyTypeObject *exact_type;
    Py_ssize_t tuple_size;
    struct FakeObject *items[10];
    const char *text;
    Py_ssize_t text_length;
    long long integer;
    int conversion_raises;
    int truthy_if_converted;
} FakeObject;

static PyTypeObject fake_tuple_type;
static PyTypeObject fake_unicode_type;
static PyTypeObject fake_bool_type;
static PyTypeObject fake_long_type;
static PyTypeObject fake_other_type;
static FakeObject fake_true_singleton;
static FakeObject fake_false_singleton;
static FakeObject fake_error_object;
static int fake_error;
static int fake_type_calls;
static int fake_tuple_size_calls;
static int fake_unicode_calls;
static int fake_long_calls;
static int fake_error_check_calls;
static int fake_error_on_check_call;

static PyObject *fake_object_type(PyObject *value) {
    FakeObject *object = (FakeObject *)value;
    ++fake_type_calls;
    if (object == NULL || object->exact_type == NULL) {
        fake_error = 1;
        return NULL;
    }
    return (PyObject *)object->exact_type;
}

static Py_ssize_t fake_tuple_size_fn(PyObject *value) {
    FakeObject *object = (FakeObject *)value;
    ++fake_tuple_size_calls;
    if (object == NULL || object->exact_type != &fake_tuple_type) {
        fake_error = 1;
        return -1;
    }
    return object->tuple_size;
}

static PyObject *fake_tuple_get(PyObject *value, Py_ssize_t index) {
    FakeObject *object = (FakeObject *)value;
    if (object == NULL || object->exact_type != &fake_tuple_type || index < 0 ||
        index >= object->tuple_size) {
        fake_error = 1;
        return NULL;
    }
    return (PyObject *)object->items[index];
}

static const char *fake_unicode_utf8(PyObject *value, Py_ssize_t *length) {
    FakeObject *object = (FakeObject *)value;
    ++fake_unicode_calls;
    if (object == NULL || object->exact_type != &fake_unicode_type || length == NULL) {
        fake_error = 1;
        return NULL;
    }
    *length = object->text_length;
    return object->text;
}

static long long fake_long_as_ll(PyObject *value) {
    FakeObject *object = (FakeObject *)value;
    ++fake_long_calls;
    if (object == NULL || object->exact_type != &fake_long_type) {
        fake_error = 1;
        return -1LL;
    }
    if (object->conversion_raises) {
        fake_error = 1;
        return -1LL;
    }
    return object->integer;
}

static PyObject *fake_error_occurred(void) {
    ++fake_error_check_calls;
    if (fake_error_on_check_call != 0 &&
        fake_error_check_calls >= fake_error_on_check_call)
        return (PyObject *)&fake_error_object;
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
    SecureZeroMemory(&fake_true_singleton, sizeof(fake_true_singleton));
    SecureZeroMemory(&fake_false_singleton, sizeof(fake_false_singleton));
    fake_true_singleton.exact_type = &fake_bool_type;
    fake_true_singleton.truthy_if_converted = 1;
    fake_false_singleton.exact_type = &fake_bool_type;
    fake_false_singleton.truthy_if_converted = 0;
    tuple->exact_type = &fake_tuple_type;
    tuple->tuple_size = 10;
    for (index = 0U; index < 10U; ++index) tuple->items[index] = &objects[index];
    objects[0].exact_type = &fake_unicode_type;
    objects[0].text = schema;
    objects[0].text_length = (Py_ssize_t)(sizeof(schema) - 1U);
    tuple->items[1] = &fake_true_singleton;
    objects[2].exact_type = &fake_long_type;
    objects[2].integer = 6LL;
    objects[3].exact_type = &fake_long_type;
    objects[3].integer = 1LL;
    for (index = 4U; index < 10U; ++index)
        tuple->items[index] = &fake_false_singleton;
    api->tuple_size = fake_tuple_size_fn;
    api->tuple_get = fake_tuple_get;
    api->unicode_utf8 = fake_unicode_utf8;
    api->long_as_ll = fake_long_as_ll;
    api->object_type = fake_object_type;
    api->error_occurred = fake_error_occurred;
    api->error_fetch = fake_error_fetch;
    api->error_normalize = fake_error_normalize;
    api->error_clear = fake_error_clear;
    api->decref = fake_decref;
    api->tuple_type = &fake_tuple_type;
    api->unicode_type = &fake_unicode_type;
    api->bool_type = &fake_bool_type;
    api->long_type = &fake_long_type;
    api->true_singleton = (PyObject *)&fake_true_singleton;
    api->false_singleton = (PyObject *)&fake_false_singleton;
    fake_error = 0;
    fake_type_calls = 0;
    fake_tuple_size_calls = 0;
    fake_unicode_calls = 0;
    fake_long_calls = 0;
    fake_error_check_calls = 0;
    fake_error_on_check_call = 0;
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

static void wrong_boolean_type_case(PythonApi *api, PythonDiagnosis *diagnosis,
    FakeObject *tuple, FakeObject objects[10], size_t index,
    uint32_t expected_stage, uint32_t expected_code, int truthy) {
    objects[index].exact_type = &fake_other_type;
    objects[index].truthy_if_converted = truthy;
    tuple->items[index] = &objects[index];
    expect_refusal(api, diagnosis, tuple, expected_stage, expected_code,
        truthy ? "truthy wrong Boolean type" : "falsey wrong Boolean type");
}

int main(void) {
    PythonApi api;
    PythonDiagnosis diagnosis;
    FakeObject tuple;
    FakeObject objects[10];
    FakeObject wrong_identity;
    uint32_t stage;
    char sanitized[8];
    uint32_t length;

    reset_fixture(&api, &diagnosis, &tuple, objects);
    stage = 0U;
    CHECK(result_exact(&api, (PyObject *)&tuple, &stage, &diagnosis) == 1,
        "exact result accepted");
    CHECK(stage == 85U, "exact result terminal stage");
    CHECK(diagnosis.result_failure_code == 0U, "exact result failure code");
    CHECK(diagnosis.result_tuple_size == 10LL, "exact result tuple size");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.exact_type = &fake_other_type;
    expect_refusal(&api, &diagnosis, &tuple, 60U, 10U, "tuple exact type");
    CHECK(fake_tuple_size_calls == 0, "wrong tuple type not sized");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.tuple_size = 9;
    expect_refusal(&api, &diagnosis, &tuple, 61U, 11U, "tuple exact size");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[0].exact_type = &fake_other_type;
    expect_refusal(&api, &diagnosis, &tuple, 62U, 12U, "schema exact type");
    CHECK(fake_unicode_calls == 0, "wrong schema type not converted");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[0].text = "kira.blackwell.v15.native_validator_result.v0";
    expect_refusal(&api, &diagnosis, &tuple, 63U, 13U, "schema exact value");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    wrong_boolean_type_case(&api, &diagnosis, &tuple, objects, 1U, 64U, 14U, 1);

    reset_fixture(&api, &diagnosis, &tuple, objects);
    SecureZeroMemory(&wrong_identity, sizeof(wrong_identity));
    wrong_identity.exact_type = &fake_bool_type;
    tuple.items[1] = &wrong_identity;
    expect_refusal(&api, &diagnosis, &tuple, 65U, 15U, "true singleton identity");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[2].exact_type = &fake_other_type;
    objects[2].integer = 6LL;
    expect_refusal(&api, &diagnosis, &tuple, 66U, 16U, "predecessor exact integer type");
    CHECK(fake_long_calls == 0, "wrong predecessor type not converted");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[2].conversion_raises = 1;
    expect_refusal(&api, &diagnosis, &tuple, 67U, 17U, "predecessor int64 range");
    CHECK(fake_long_calls == 1, "predecessor overflow converted once");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[2].integer = 5LL;
    expect_refusal(&api, &diagnosis, &tuple, 68U, 18U, "predecessor exact value");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[3].exact_type = &fake_other_type;
    objects[3].integer = 1LL;
    expect_refusal(&api, &diagnosis, &tuple, 69U, 19U, "graph exact integer type");
    CHECK(fake_long_calls == 1, "wrong graph type adds no conversion");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[3].conversion_raises = 1;
    expect_refusal(&api, &diagnosis, &tuple, 70U, 20U, "graph int64 range");
    CHECK(fake_long_calls == 2, "graph overflow converted after predecessor");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    objects[3].integer = 0LL;
    expect_refusal(&api, &diagnosis, &tuple, 71U, 21U, "graph positive value");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    wrong_boolean_type_case(&api, &diagnosis, &tuple, objects, 4U, 72U, 22U, 0);
    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.items[4] = &fake_true_singleton;
    expect_refusal(&api, &diagnosis, &tuple, 73U, 23U, "boolean 4 false identity");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    wrong_boolean_type_case(&api, &diagnosis, &tuple, objects, 5U, 74U, 24U, 1);
    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.items[5] = &fake_true_singleton;
    expect_refusal(&api, &diagnosis, &tuple, 75U, 25U, "boolean 5 false identity");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    wrong_boolean_type_case(&api, &diagnosis, &tuple, objects, 6U, 76U, 26U, 0);
    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.items[6] = &fake_true_singleton;
    expect_refusal(&api, &diagnosis, &tuple, 77U, 27U, "boolean 6 false identity");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    wrong_boolean_type_case(&api, &diagnosis, &tuple, objects, 7U, 78U, 28U, 1);
    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.items[7] = &fake_true_singleton;
    expect_refusal(&api, &diagnosis, &tuple, 79U, 29U, "boolean 7 false identity");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    wrong_boolean_type_case(&api, &diagnosis, &tuple, objects, 8U, 80U, 30U, 0);
    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.items[8] = &fake_true_singleton;
    expect_refusal(&api, &diagnosis, &tuple, 81U, 31U, "boolean 8 false identity");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    wrong_boolean_type_case(&api, &diagnosis, &tuple, objects, 9U, 82U, 32U, 1);
    reset_fixture(&api, &diagnosis, &tuple, objects);
    tuple.items[9] = &fake_true_singleton;
    expect_refusal(&api, &diagnosis, &tuple, 83U, 33U, "boolean 9 false identity");

    reset_fixture(&api, &diagnosis, &tuple, objects);
    fake_error_on_check_call = 3;
    expect_refusal(&api, &diagnosis, &tuple, 84U, 34U, "pending Python error");

    length = copy_sanitized_python_text("A\n\x80Z", 4, sanitized, sizeof(sanitized));
    CHECK(length == 4U, "sanitized length");
    CHECK(sanitized[0] == 'A', "sanitized ASCII");
    CHECK(sanitized[1] == ' ', "sanitized newline");
    CHECK(sanitized[2] == '?', "sanitized non-ASCII");
    CHECK(sanitized[3] == 'Z' && sanitized[4] == '\0', "sanitized terminator");
    length = copy_sanitized_python_text("abcdef", 6, sanitized, 4U);
    CHECK(length == 3U && strcmp(sanitized, "abc") == 0, "sanitized bounded text");
    CHECK(copy_sanitized_python_text(NULL, 0, sanitized, sizeof(sanitized)) == 0U,
        "sanitized null input");
    CHECK(sizeof(((PythonDiagnosis *)0)->exception_type) == EXCEPTION_TYPE_CAP,
        "exception type capacity");
    CHECK(sizeof(((PythonDiagnosis *)0)->exception_message) == EXCEPTION_MESSAGE_CAP,
        "exception message capacity");
    CHECK(sizeof(PythonDiagnosis) == 280U, "diagnosis payload expectation");
    CHECK(sizeof(ReservationRecord) == 336U, "reservation size retained");
    CHECK(sizeof(CompletionRecord) == 644U, "completion diagnostic size");
    reset_fixture(&api, &diagnosis, &tuple, objects);
    CHECK(python_type_exact(&api, (PyObject *)&tuple, &fake_tuple_type) == 1,
        "exact type helper accepts exact type");
    CHECK(python_type_exact(&api, (PyObject *)&tuple, &fake_other_type) == 0,
        "exact type helper refuses different type");
    CHECK(python_type_exact(&api, NULL, &fake_tuple_type) == 0,
        "exact type helper refuses null");

    printf("SUMMARY checks=%d failures=%d candidate_entrypoint_invoked=0 python_invoked=0 "
        "truthy_falsey_wrong_types_refused=7 integer_wrong_types_not_converted=2\n",
        checks, failures);
    return failures == 0 && checks == 100 ? 0 : 1;
}
