#ifndef KIRA_V3R30_POST_AUDIT_BINDINGS_H
#define KIRA_V3R30_POST_AUDIT_BINDINGS_H

/*
 * Compile/analyzer-only header.  It deliberately reaches the exact
 * V3R30_MATERIALIZED=1 C control path, but it is not an Audit-A decision,
 * Stage-2 materialization, build authority, Audit-B pin, or run authority.
 */
#define V3R30_MATERIALIZED 1
#define V3R30_ANALYZER_MATERIALIZED_PATH 1
#define V3R30_STAGE1_PACKAGE_ROOT "1111111111111111111111111111111111111111111111111111111111111111"
#define V3R30_STAGE1_SEAL_SHA256 "2222222222222222222222222222222222222222222222222222222222222222"
#define V3R30_STAGE1_ALL_FILES_ROOT "3333333333333333333333333333333333333333333333333333333333333333"
#define V3R30_AUDIT_A_SHA256 "4444444444444444444444444444444444444444444444444444444444444444"
#define V3R30_INSTALL_AUTHORITY_MANIFEST_SHA256 "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
#define V3R30_INSTALL_AUTHORITY_AUDITOR "independent_compile_analyze_install_probe_only"
#define V3R30_MATERIALIZATION_CONSUMPTION_KEY "5555555555555555555555555555555555555555555555555555555555555555"
#define V3R30_AUDITOR "independent_compile_analyze_probe_only"
#define V3R30_FRAME_SHA256 "6666666666666666666666666666666666666666666666666666666666666666"
#define V3R30_SPEC_SHA256 "7777777777777777777777777777777777777777777777777777777777777777"
#define V3R30_WORKER_SHA256 "8888888888888888888888888888888888888888888888888888888888888888"
#define V3R30_EXPECTED_SELF_PATH L"C:\\Users\\robmc\\Kira\\tools\\native\\DO_NOT_RUN_v3r30_materialized_analyzer_probe.exe"
#define V3R30_WORKER_PATH L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_medical_reference_proxy_v3r30_stage2\\attempt_01\\blender_worker_v3r30.py"
#define V3R30_OUTPUT_PARENT L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_medical_reference_proxy_v3r30_stage2\\attempt_01"
#define V3R30_BLENDER_PATH L"C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe"
#define V3R30_BLENDER_BYTES 108687824ULL
#define V3R30_BLENDER_SHA256 "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5"
#define V3R30_BINDING_COUNT 1U

static const V3R30Binding V3R30_BINDINGS[1] = {
    {
        L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_medical_reference_proxy_v3r30_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json",
        1ULL,
        "9999999999999999999999999999999999999999999999999999999999999999",
        "compile_analyzer_only_unrunnable_binding"
    }
};

#endif
