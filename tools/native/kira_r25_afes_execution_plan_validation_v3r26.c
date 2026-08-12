/*
 * Kira R25 AFES v3r26 pure retained execution-plan validation diagnostic.
 *
 * Static authoring only.  This program is inert until a different exact-byte
 * reviewer seals and accepts one no-argument invocation.  That sole possible
 * invocation may reserve append-only evidence, retain the exact v3r26
 * authority contract, parse and hold all 137 exact CRLF v3r9 manifest rows,
 * initialize the exact isolated Python runtime, bind the retained controller's
 * exact definitions/globals/code/defaults/closures/deferred annotation
 * thunks without evaluating annotations, call only its pure
 * _build_execution_plan export exactly once with retained byte snapshots,
 * validate and destroy the returned data-only plan, finalize/unload Python,
 * recheck every retained handle and predecessor closure, commit one terminal
 * record including bounded sanitized Python exception and 21 exact
 * entered/returned operation counters with fine-grained checkpoints, and stop.
 * V3r25's one consumed run proved the pure plan returned, then stopped at
 * checkpoint 218 because its post-call validator repeated the pre-call
 * byte-serialization equality predicate after executing only the left twin.
 * That predicate conflated immutable source identity with interpreter-managed
 * execution state.  This append-only repair keeps exact format-5 twin/code/
 * deferred-annotation equivalence before the call, then proves the same
 * function, code, defaults, closure, annotation, globals, and metadata objects
 * remain installed after the call without reserializing executed code.  The
 * V3r22 stage-40 cause remains unknown.  Unresolved annotation names are
 * proven excluded: the retained controller is compiled with
 * 0x1000000 == CO_FUTURE_ANNOTATIONS and its annotations are stringized without
 * evaluation.  It contains no
 * bootstrap, broker, process creation, AFES,
 * Blender invocation, body access, save, render, export, or retry path.
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

#include "kira_r25_afes_execution_plan_validation_v3r26_identity_anchor.h"

#pragma comment(lib, "bcrypt.lib")

#define SHA_BYTES 32U
#define SHA_HEX 64U
#define HASH_CHUNK 65536U
#define AUDIT_LIMIT 32768U
#define MANIFEST_LIMIT 65536U
#define CONTROLLER_LIMIT 131072U
#define CONTRACT_LIMIT 262144U
#define RETAINED_ROW_COUNT 137U
#define MANIFEST_LINE_COUNT 139U
#define RETAINED_ROW_LIMIT (128ULL * 1024ULL * 1024ULL)
#define MANIFEST_LABEL_CAPACITY 97U
#define MANIFEST_PATH_CAPACITY 512U
#define RECORD_PENDING 1U
#define RECORD_SUCCESS 2U
#define RECORD_FAILURE 3U
#define CONTRACT_GATE_COUNT 15U
#define PY_EXCEPTION_TYPE_CAPACITY 64U
#define PY_EXCEPTION_MESSAGE_CAPACITY 192U

static const wchar_t PROJECT_ROOT[] = L"C:\\Users\\robmc\\Kira";
static const wchar_t SELF_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r26.exe";
static const wchar_t ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r26_identity_anchor.h";
static const wchar_t CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_execution_plan_validation_v3r26.json";
static const wchar_t TARGET_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_execution_plan_validation_v3r26.json";
static const wchar_t SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r26.c";
static const wchar_t TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_execution_plan_validation_v3r26_static.ps1";
static const wchar_t CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r26_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
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
static const wchar_t V3R20_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r20.json";
static const wchar_t V3R20_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r20.c";
static const wchar_t V3R20_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r20_identity_anchor.h";
static const wchar_t V3R20_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r20.obj";
static const wchar_t V3R20_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r20.exe";
static const wchar_t V3R20_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_python_controller_validation_v3r20_static.ps1";
static const wchar_t V3R20_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R20_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R20_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R20_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R20_REJECTION_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R20_REJECTION_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R20_REJECTION_DECISION_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit\\attempt_01\\AUDIT_DECISION.json";
static const wchar_t V3R20_REJECTION_ANALYZE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit\\attempt_01\\MSVC_ANALYZE_RESULTS.txt";
static const wchar_t V3R20_REJECTION_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r20_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R21_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_python_controller_validation_v3r21.json";
static const wchar_t V3R21_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r21.c";
static const wchar_t V3R21_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r21_identity_anchor.h";
static const wchar_t V3R21_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r21.obj";
static const wchar_t V3R21_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_python_controller_validation_v3r21.exe";
static const wchar_t V3R21_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_python_controller_validation_v3r21_static.ps1";
static const wchar_t V3R21_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R21_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R21_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R21_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R21_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R21_AUDIT_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R21_AUDIT_DECISION_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit\\attempt_01\\AUDIT_DECISION.json";
static const wchar_t V3R21_AUDIT_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit\\attempt_01\\HOSTILE_STATIC_PROBES.txt";
static const wchar_t V3R21_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R21_RUN_EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t V3R21_RECEIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_static_preparation\\attempt_01\\PYTHON_CONTROLLER_VALIDATION_OUTCOME.receipt.bin";
static const wchar_t V3R21_RUN_OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit\\attempt_01\\RUN_OUTCOME.json";
static const wchar_t V3R21_POST_RUN_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit\\attempt_01\\POST_RUN_CHECKPOINT.md";
static const wchar_t V3R9_LAUNCHER_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_locked_pair_launcher_v3r9.c";
static const wchar_t V3R9_LAUNCHER_EXE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_locked_pair_launcher_v3r9.exe";
static const wchar_t V3R9_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_locked_pair_execution_v3r9.py";
static const wchar_t V3R9_BOOTSTRAP_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r9.py";
static const wchar_t V3R9_WRAPPER_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3r9.py";
static const wchar_t V3R9_POSTMORTEM_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r9_consumed_run_static_postmortem\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R9_COMMAND_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r9_consumed_run_static_postmortem\\attempt_01\\CONSUMED_COMMAND.txt";
static const wchar_t V3R9_TRANSCRIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r9_consumed_run_static_postmortem\\attempt_01\\RAW_TOOL_RESULT_TRANSCRIPT.txt";
static const wchar_t V3R10_CONTRACT_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r10.json";
static const wchar_t V3R10_SOURCE_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.c";
static const wchar_t V3R10_OBJECT_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.obj";
static const wchar_t V3R10_EXE_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.exe";
static const wchar_t V3R10_TEST_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r10.py";
static const wchar_t V3R10_AUTHOR_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R10_AUDIT_SCRIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r10_fresh_static_audit\\attempt_01\\STATIC_22_EQUIVALENT_AUDIT.ps1";
static const wchar_t V3R10_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r10_fresh_static_audit\\attempt_01\\HOSTILE_PROBE_RESULTS.tsv";
static const wchar_t V3R10_REJECTION_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r10_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R10_AUDIT_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r10_fresh_static_audit\\attempt_01\\build_cache\\diagnostic.obj";
static const wchar_t V3R10_AUDIT_EXE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_v3r10_fresh_static_audit\\attempt_01\\build_cache\\diagnostic.exe";
static const wchar_t V3R11_CONTRACT_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r11.json";
static const wchar_t V3R11_SOURCE_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r11.c";
static const wchar_t V3R11_CONTROL_HISTORY_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r11_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R11_BLOCKER_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260810\\kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r11_static_preparation\\attempt_01\\BLOCKER_CHECKPOINT.md";
static const wchar_t MANIFEST_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9\\RETAINED_NATIVE_LOCK_MANIFEST.tsv";
static const wchar_t PYTHON_DLL_PATH[] = L"C:\\Python314\\python314.dll";
static const wchar_t CPYTHON_CODE_HEADER_PATH[] = L"C:\\Python314\\include\\cpython\\code.h";
static const wchar_t STDLIB_ZIP_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\runtime\\python314_stdlib_v3r4.zip";
static const wchar_t CONTROLLER_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\run_kira_r25_foundation_afes_locked_pair_v3r9.py";
static const wchar_t EXECUTION_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_locked_pair_execution_v3r9.json";
static const wchar_t V3R9_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260809\\kira_r25_foundation_afes_locked_pair_execution_static_preparation\\attempt_03r9\\INDEPENDENT_AUDIT.json";
static const wchar_t AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r26_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t AUDIT_DIGEST_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r26_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t OUTPUT_PARENT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r26_static_preparation\\attempt_01";
static const wchar_t EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r26_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r26_static_preparation\\attempt_01\\EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin";

/* V3r25 ran exactly once, returned its plan, failed at checkpoint 218, and is consumed. */
static const wchar_t V3R25_CONSUMED_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_execution_plan_validation_v3r25.json";
static const wchar_t V3R25_CONSUMED_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r25.c";
static const wchar_t V3R25_CONSUMED_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r25_identity_anchor.h";
static const wchar_t V3R25_CONSUMED_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r25.obj";
static const wchar_t V3R25_CONSUMED_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r25.exe";
static const wchar_t V3R25_CONSUMED_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_execution_plan_validation_v3r25_static.ps1";
static const wchar_t V3R25_CONSUMED_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R25_CONSUMED_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R25_CONSUMED_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R25_CONSUMED_AUTHOR_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R25_CONSUMED_AUDIT_DECISION_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_fresh_static_audit\\attempt_01\\AUDIT_DECISION.json";
static const wchar_t V3R25_CONSUMED_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R25_CONSUMED_AUDIT_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_fresh_static_audit\\attempt_01\\HOSTILE_STATIC_PROBES.txt";
static const wchar_t V3R25_CONSUMED_AUDIT_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R25_CONSUMED_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R25_CONSUMED_AUDIT_RESULTS_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_fresh_static_audit\\attempt_01\\INDEPENDENT_STATIC_RESULTS.txt";
static const wchar_t V3R25_CONSUMED_EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t V3R25_CONSUMED_RECEIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin";
static const wchar_t V3R25_CONSUMED_RUN_OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\RUN_OUTCOME.json";
static const wchar_t V3R25_CONSUMED_POST_RUN_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r25_static_preparation\\attempt_01\\POST_RUN_CHECKPOINT.md";

/* V3r24 ran once, failed before a controller or plan attempt, and is consumed. */
static const wchar_t V3R24_CONSUMED_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_execution_plan_validation_v3r24.json";
static const wchar_t V3R24_CONSUMED_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r24.c";
static const wchar_t V3R24_CONSUMED_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r24_identity_anchor.h";
static const wchar_t V3R24_CONSUMED_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r24.obj";
static const wchar_t V3R24_CONSUMED_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r24.exe";
static const wchar_t V3R24_CONSUMED_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_execution_plan_validation_v3r24_static.ps1";
static const wchar_t V3R24_CONSUMED_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R24_CONSUMED_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R24_CONSUMED_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R24_CONSUMED_AUTHOR_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R24_CONSUMED_EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t V3R24_CONSUMED_RECEIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_static_preparation\\attempt_01\\EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin";
static const wchar_t V3R24_CONSUMED_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R24_CONSUMED_AUDIT_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R24_CONSUMED_AUDIT_DECISION_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit\\attempt_01\\AUDIT_DECISION.json";
static const wchar_t V3R24_CONSUMED_AUDIT_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit\\attempt_01\\HOSTILE_STATIC_PROBES.txt";
static const wchar_t V3R24_CONSUMED_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R24_CONSUMED_RUN_OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit\\attempt_01\\RUN_OUTCOME.json";
static const wchar_t V3R24_CONSUMED_POST_RUN_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit\\attempt_01\\POST_RUN_CHECKPOINT.md";

/* The complete consumed V3r22 failure closure is immutable and DO_NOT_RERUN. */
static const wchar_t V3R22_CONSUMED_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_execution_plan_validation_v3r22.json";
static const wchar_t V3R22_CONSUMED_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r22.c";
static const wchar_t V3R22_CONSUMED_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r22_identity_anchor.h";
static const wchar_t V3R22_CONSUMED_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r22.obj";
static const wchar_t V3R22_CONSUMED_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r22.exe";
static const wchar_t V3R22_CONSUMED_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_execution_plan_validation_v3r22_static.ps1";
static const wchar_t V3R22_CONSUMED_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R22_CONSUMED_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R22_CONSUMED_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R22_CONSUMED_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R22_CONSUMED_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R22_CONSUMED_AUDIT_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R22_CONSUMED_AUDIT_DECISION_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_fresh_static_audit\\attempt_01\\AUDIT_DECISION.json";
static const wchar_t V3R22_CONSUMED_AUDIT_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_fresh_static_audit\\attempt_01\\HOSTILE_STATIC_PROBES.txt";
static const wchar_t V3R22_CONSUMED_AUDIT_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_fresh_static_audit\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R22_CONSUMED_EVIDENCE_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_static_preparation\\attempt_01\\RUN_EVIDENCE.jsonl";
static const wchar_t V3R22_CONSUMED_RECEIPT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_static_preparation\\attempt_01\\EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin";
static const wchar_t V3R22_CONSUMED_RUN_OUTCOME_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_fresh_static_audit\\attempt_01\\RUN_OUTCOME.json";
static const wchar_t V3R22_CONSUMED_POSTMORTEM_RECHECK_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_consumed_failure_postmortem\\attempt_01\\READ_ONLY_RECHECK.json";
static const wchar_t V3R22_CONSUMED_POSTMORTEM_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r22_consumed_failure_postmortem\\attempt_01\\CHECKPOINT.md";

/* V3r23 is rejected and has no execution authority; preserve all 15 exact artifacts. */
static const wchar_t V3R23_REJECTED_CONTRACT_PATH[] = L"C:\\Users\\robmc\\Kira\\Avatar\\avatar_builder\\body_systems\\kira_r25_foundation_afes_execution_plan_validation_v3r23.json";
static const wchar_t V3R23_REJECTED_SOURCE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r23.c";
static const wchar_t V3R23_REJECTED_ANCHOR_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r23_identity_anchor.h";
static const wchar_t V3R23_REJECTED_OBJECT_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r23.obj";
static const wchar_t V3R23_REJECTED_EXECUTABLE_PATH[] = L"C:\\Users\\robmc\\Kira\\tools\\native\\kira_r25_afes_execution_plan_validation_v3r23.exe";
static const wchar_t V3R23_REJECTED_TEST_PATH[] = L"C:\\Users\\robmc\\Kira\\Testing\\test_kira_r25_foundation_afes_execution_plan_validation_v3r23_static.ps1";
static const wchar_t V3R23_REJECTED_CONTROL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_static_preparation\\attempt_01\\RUNTIME_CONTROL_CHECKPOINT.md";
static const wchar_t V3R23_REJECTED_BUILD_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_static_preparation\\attempt_01\\BUILD_AND_STATIC_TEST_RESULTS.txt";
static const wchar_t V3R23_REJECTED_SEAL_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_static_preparation\\attempt_01\\STATIC_SEAL_MANIFEST.json";
static const wchar_t V3R23_REJECTED_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_static_preparation\\attempt_01\\CHECKPOINT.md";
static const wchar_t V3R23_REJECTION_AUDIT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.tsv";
static const wchar_t V3R23_REJECTION_SIDECAR_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_fresh_static_audit\\attempt_01\\INDEPENDENT_AUDIT.sha256";
static const wchar_t V3R23_REJECTION_DECISION_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_fresh_static_audit\\attempt_01\\AUDIT_DECISION.json";
static const wchar_t V3R23_REJECTION_PROBES_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_fresh_static_audit\\attempt_01\\HOSTILE_STATIC_PROBES.txt";
static const wchar_t V3R23_REJECTION_CHECKPOINT_PATH[] = L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\kira_r25_afes_execution_plan_validation_v3r23_fresh_static_audit\\attempt_01\\CHECKPOINT.md";

static const char AUDIT_MAGIC[] = "KIRA_R25_AFES_EXECUTION_PLAN_VALIDATION_AUDIT_V3R26\t1";
static const char AUDIT_DECISION[] = "ACCEPTED_FOR_ONE_BOUNDED_DIAGNOSTIC_PURE_BUILD_EXECUTION_PLAN_VALIDATION_V3R26_ONLY";
static const char E_ENTRY[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"entry\",\"status\":\"entered\"}\n";
static const char E_GATE[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"subject_manifest_audit_gate\",\"status\":\"passed\"}\n";
static const char E_RESERVED[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"outcome_reservation\",\"status\":\"passed\"}\n";
static const char E_PYTHON[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"isolated_python_runtime\",\"status\":\"passed\"}\n";
static const char E_CONTROLLER[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"restricted_twin_controller_code_globals_gate\",\"status\":\"passed\"}\n";
static const char E_PLAN[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"pure_build_execution_plan_once_and_data_only_result_validation\",\"status\":\"passed\",\"manifest_rows\":137,\"plan_attempts\":1,\"plan_returns\":1,\"operation_enters\":21,\"operation_returns\":21,\"sha_helper_calls\":222,\"hex_helper_calls\":231,\"json_helper_calls\":4,\"forbidden_helper_calls\":0}\n";
static const char E_FINALIZED[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"python_finalize_dll_unload_retained_recheck\",\"status\":\"passed\"}\n";
static const char E_SUCCESS[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"terminal\",\"status\":\"complete\",\"detail\":\"plan_destroyed_no_bootstrap_broker_process_afes_blender_body_save_render_export\"}\n";
static const char E_FAILURE[] = "{\"schema\":\"kira.r25.afes.v3r26.native_stage.v1\",\"stage\":\"terminal\",\"status\":\"failed_consumed_no_retry\"}\n";
static const unsigned char RESERVATION_MAGIC[] = "KIRA_R25_AFES_V3R26_RESERVATION";
static const unsigned char TERMINAL_MAGIC[] = "KIRA_R25_AFES_V3R26_TERMINAL";

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

typedef struct ManifestRowV3R22 {
    char label[MANIFEST_LABEL_CAPACITY];
    char manifest_path[MANIFEST_PATH_CAPACITY];
    char sha256[SHA_HEX + 1U];
    wchar_t absolute_path[MAX_PATH];
    LockedFile locked;
} ManifestRowV3R22;

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

typedef struct ValidatorTelemetry {
    uint32_t checkpoint;
    uint32_t plan_attempts;
    uint32_t plan_returns;
    uint32_t operation_enters;
    uint32_t operation_returns;
    uint32_t marker_present;
    uint32_t python_error_captured;
    uint32_t exception_message_truncated;
    uint32_t retained_recheck_passed;
    uint32_t reserved;
    uint64_t native_sha_calls;
    char exception_type[PY_EXCEPTION_TYPE_CAPACITY];
    char exception_message[PY_EXCEPTION_MESSAGE_CAPACITY];
} ValidatorTelemetry;

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
    ValidatorTelemetry validator;
} CompletionRecord;
#pragma pack(pop)

typedef struct PythonApi {
    HMODULE module;
    PyObject *runtime_error;
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
    PyObject *(__cdecl *unicode_from_string_size)(const char *, Py_ssize_t);
    const char *(__cdecl *unicode_utf8)(PyObject *, Py_ssize_t *);
    PyObject *(__cdecl *bytes_from_data)(const char *, Py_ssize_t);
    int (__cdecl *bytes_as_data)(PyObject *, char **, Py_ssize_t *);
    PyObject *(__cdecl *cfunction_new)(PyMethodDef *, PyObject *, PyObject *);
    void (__cdecl *error_set_string)(PyObject *, const char *);
    unsigned long long (__cdecl *long_as_ull)(PyObject *);
    Py_ssize_t (__cdecl *tuple_size)(PyObject *);
    PyObject *(__cdecl *tuple_get)(PyObject *, Py_ssize_t);
    int (__cdecl *callable)(PyObject *);
    void (__cdecl *decref)(PyObject *);
    PyObject *(__cdecl *error_occurred)(void);
    void (__cdecl *error_clear)(void);
    PyObject *(__cdecl *error_get_raised)(void);
    PyObject *(__cdecl *object_type)(PyObject *);
    PyObject *(__cdecl *object_get_attr_string)(PyObject *, const char *);
    PyObject *(__cdecl *object_str)(PyObject *);
} PythonApi;

static PythonApi *g_plan_python_api = NULL;
static unsigned long long g_plan_native_sha_calls = 0ULL;

_Static_assert(sizeof(RESERVATION_MAGIC) - 1U <= sizeof(((ReservationRecord *)0)->magic),
    "reservation magic exceeds durable field");
_Static_assert(sizeof(TERMINAL_MAGIC) - 1U <= sizeof(((CompletionRecord *)0)->magic),
    "terminal magic exceeds durable field");
_Static_assert(sizeof(ReservationRecord) == 424U,
    "reservation durable grammar drift");
_Static_assert(CO_FUTURE_ANNOTATIONS == 0x1000000,
    "retained controller future-annotations flag drift");
_Static_assert(sizeof(ValidatorTelemetry) == 304U,
    "validator telemetry durable grammar drift");
_Static_assert(sizeof(CompletionRecord) == 896U,
    "completion durable grammar drift");

static int valid_handle(HANDLE value) {
    return value != NULL && value != INVALID_HANDLE_VALUE;
}

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

static int sha_memory(const unsigned char *data, size_t length,
    unsigned char digest[SHA_BYTES]);

static PyObject *v3r26_native_sha256_hex(PyObject *self, PyObject *args) {
    char *data = NULL;
    Py_ssize_t length = 0;
    unsigned char digest[SHA_BYTES];
    char hex[SHA_HEX + 1U];
    PyObject *result;
    (void)self;
    if (g_plan_python_api == NULL || g_plan_python_api->runtime_error == NULL ||
        g_plan_python_api->tuple_size(args) != 1 ||
        g_plan_python_api->bytes_as_data(
            g_plan_python_api->tuple_get(args, 0), &data, &length) != 0 ||
        data == NULL || length < 0 ||
        !sha_memory((const unsigned char *)data, (size_t)length, digest)) {
        if (g_plan_python_api != NULL && g_plan_python_api->runtime_error != NULL)
            g_plan_python_api->error_set_string(
                g_plan_python_api->runtime_error, "v3r26_native_sha256_input_or_digest_failed");
        return NULL;
    }
    ++g_plan_native_sha_calls;
    digest_hex(digest, hex);
    SecureZeroMemory(digest, sizeof(digest));
    result = g_plan_python_api->unicode_from_string_size(hex, SHA_HEX);
    SecureZeroMemory(hex, sizeof(hex));
    return result;
}

static PyMethodDef V3R22_NATIVE_SHA_METHOD = {
    "v3r26_native_sha256_hex", v3r26_native_sha256_hex, METH_VARARGS, NULL
};

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
    const size_t capacity = 32768U;
    wchar_t *actual = NULL;
    wchar_t *expected = NULL;
    DWORD length;
    size_t path_length = wcslen(path);
    int ok = 0;
    if (path_length + 5U > capacity) return 0;
    actual = (wchar_t *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        capacity * sizeof(wchar_t));
    expected = (wchar_t *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
        capacity * sizeof(wchar_t));
    if (actual == NULL || expected == NULL) goto cleanup;
    memcpy(expected, L"\\\\?\\", 4U * sizeof(wchar_t));
    memcpy(expected + 4U, path, path_length * sizeof(wchar_t));
    expected[4U + path_length] = L'\0';
    length = GetFinalPathNameByHandleW(file, actual, (DWORD)capacity,
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (length != 0U && length < (DWORD)capacity) {
        actual[length] = L'\0';
        ok = _wcsicmp(actual, expected) == 0;
    }
cleanup:
    if (actual != NULL) {
        SecureZeroMemory(actual, capacity * sizeof(wchar_t));
        HeapFree(GetProcessHeap(), 0U, actual);
    }
    if (expected != NULL) {
        SecureZeroMemory(expected, capacity * sizeof(wchar_t));
        HeapFree(GetProcessHeap(), 0U, expected);
    }
    return ok;
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
    if (!regular_file(file, &bytes) || bytes != V3R22_TARGET_CONTRACT_BYTES) {
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
    if (!regular_file(file, &bytes) || bytes != V3R22_TARGET_CONTRACT_BYTES ||
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
    if (!regular_file(*handle, &bytes) || bytes != V3R22_TARGET_CONTRACT_BYTES ||
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
            strcmp(expected, V3R22_TARGET_CONTRACT_SHA256) != 0 ||
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
        "{\"schema\":\"kira.r25.afes.v3r26.contract_gate.v1\",\"stage\":\"granular_same_handle_terminal\",\"passed_mask\":%u,\"failure_gate\":%u,\"win32_error\":%u,\"snapshot_one_bytes\":%llu,\"snapshot_two_bytes\":%llu,\"final_bytes\":%llu}\n",
        telemetry->passed_mask, telemetry->failure_gate, telemetry->win32_error,
        (unsigned long long)telemetry->snapshot_one_bytes,
        (unsigned long long)telemetry->snapshot_two_bytes,
        (unsigned long long)telemetry->final_bytes);
    return bytes > 0 && append_line(evidence, line);
}

static int append_unload_telemetry(HANDLE evidence, const UnloadTelemetry *telemetry) {
    char line[640];
    int bytes = _snprintf_s(line, sizeof(line), _TRUNCATE,
        "{\"schema\":\"kira.r25.afes.v3r26.python_unload.v1\",\"stage\":\"finalize_release_absence_terminal\",\"finalize_called\":%u,\"finalize_result\":%d,\"free_library_called\":%u,\"free_library_result\":%u,\"snapshot_succeeded\":%u,\"snapshot_error\":%u,\"checked_module_count\":%u,\"old_base_present\":%u,\"exact_path_present\":%u,\"old_module_base\":%llu}\n",
        telemetry->finalize_called, telemetry->finalize_result,
        telemetry->free_library_called, telemetry->free_library_result,
        telemetry->snapshot_succeeded, telemetry->snapshot_error,
        telemetry->checked_module_count, telemetry->old_base_present,
        telemetry->exact_path_present,
        (unsigned long long)telemetry->old_module_base);
    return bytes > 0 && append_line(evidence, line);
}

static int append_validator_telemetry(HANDLE evidence,
    const ValidatorTelemetry *telemetry) {
    char line[1024];
    int bytes = _snprintf_s(line, sizeof(line), _TRUNCATE,
        "{\"schema\":\"kira.r25.afes.v3r26.plan_validator_telemetry.v1\","
        "\"stage\":\"bounded_sanitized_diagnostic\",\"checkpoint\":%u,"
        "\"plan_attempts\":%u,\"plan_returns\":%u,"
        "\"operation_enters\":%u,\"operation_returns\":%u,\"marker_present\":%u,"
        "\"native_sha_calls\":%llu,\"python_error_captured\":%u,"
        "\"exception_message_truncated\":%u,\"retained_recheck_passed\":%u,"
        "\"exception_type\":\"%s\",\"exception_message\":\"%s\"}\n",
        telemetry->checkpoint, telemetry->plan_attempts, telemetry->plan_returns,
        telemetry->operation_enters, telemetry->operation_returns,
        telemetry->marker_present,
        (unsigned long long)telemetry->native_sha_calls,
        telemetry->python_error_captured,
        telemetry->exception_message_truncated,
        telemetry->retained_recheck_passed,
        telemetry->exception_type, telemetry->exception_message);
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

static int manifest_label_valid(const char *value) {
    size_t index;
    size_t length = value != NULL ? strlen(value) : 0U;
    if (length == 0U || length >= MANIFEST_LABEL_CAPACITY) return 0;
    for (index = 0U; index < length; ++index) {
        char c = value[index];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) return 0;
    }
    return 1;
}

static int manifest_bytes_valid(const char *value, ULONGLONG *result) {
    ULONGLONG total = 0ULL;
    size_t index;
    size_t length = value != NULL ? strlen(value) : 0U;
    if (length == 0U || (length > 1U && value[0] == '0')) return 0;
    for (index = 0U; index < length; ++index) {
        unsigned digit;
        if (value[index] < '0' || value[index] > '9') return 0;
        digit = (unsigned)(value[index] - '0');
        if (total > (ULLONG_MAX - digit) / 10ULL) return 0;
        total = total * 10ULL + digit;
    }
    if (total == 0ULL || total > RETAINED_ROW_LIMIT || total > MAXDWORD) return 0;
    *result = total;
    return 1;
}

static int manifest_relative_path_valid(const char *path) {
    const char *segment;
    const char *cursor;
    size_t length = path != NULL ? strlen(path) : 0U;
    if (length == 0U || length >= MANIFEST_PATH_CAPACITY || path[0] == '/' ||
        path[length - 1U] == '/' || strchr(path, '\\') != NULL ||
        strchr(path, ':') != NULL || strstr(path, "//") != NULL) return 0;
    segment = path;
    for (cursor = path; ; ++cursor) {
        if (*cursor == '/' || *cursor == '\0') {
            size_t segment_length = (size_t)(cursor - segment);
            if (segment_length == 0U ||
                (segment_length == 1U && segment[0] == '.') ||
                (segment_length == 2U && segment[0] == '.' && segment[1] == '.')) return 0;
            if (*cursor == '\0') break;
            segment = cursor + 1;
        } else if ((unsigned char)*cursor < 0x20U || (unsigned char)*cursor > 0x7eU) {
            return 0;
        }
    }
    return 1;
}

static int manifest_path_to_absolute(const char *path, wchar_t output[MAX_PATH]) {
    wchar_t converted[MAX_PATH];
    int converted_length;
    size_t index;
    int written;
    int external = path != NULL && strncmp(path, "C:/", 3U) == 0;
    if (path == NULL || strlen(path) >= MANIFEST_PATH_CAPACITY) return 0;
    if (external) {
        if (strcmp(path, "C:/Python314/python314.dll") != 0 &&
            strcmp(path, "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe") != 0) return 0;
    } else if (!manifest_relative_path_valid(path)) {
        return 0;
    }
    converted_length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1,
        converted, (int)_countof(converted));
    if (converted_length <= 0 || converted_length > (int)_countof(converted)) return 0;
    for (index = 0U; converted[index] != L'\0'; ++index)
        if (converted[index] == L'/') converted[index] = L'\\';
    if (external) {
        if (wcscpy_s(output, MAX_PATH, converted) != 0) return 0;
    } else {
        written = _snwprintf_s(output, MAX_PATH, _TRUNCATE, L"%ls\\%ls", PROJECT_ROOT, converted);
        if (written <= 0 || written >= MAX_PATH) return 0;
    }
    return 1;
}

static void release_manifest_rows(ManifestRowV3R22 rows[RETAINED_ROW_COUNT]) {
    size_t index;
    for (index = 0U; index < RETAINED_ROW_COUNT; ++index) {
        if (valid_handle(rows[index].locked.handle)) CloseHandle(rows[index].locked.handle);
        rows[index].locked.handle = INVALID_HANDLE_VALUE;
    }
    SecureZeroMemory(rows, sizeof(*rows) * RETAINED_ROW_COUNT);
}

static int parse_and_lock_manifest_rows(unsigned char *manifest, DWORD bytes,
    ManifestRowV3R22 rows[RETAINED_ROW_COUNT]) {
    static const char magic[] = "KIRA_R25_AFES_RETAINED_MANIFEST_V3R9\t1";
    static const char header[] = "label\tpath\tbytes\tsha256";
    char *cursor = (char *)manifest;
    char *end = (char *)manifest + bytes;
    size_t line_number = 0U;
    size_t row_count = 0U;
    size_t index;
    if (manifest == NULL || bytes != V3R22_MANIFEST_BYTES || bytes < 4U ||
        manifest[bytes - 2U] != '\r' || manifest[bytes - 1U] != '\n' ||
        memchr(manifest, '\0', bytes) != NULL) return 0;
    for (index = 0U; index < bytes; ++index) {
        if ((manifest[index] == '\r' &&
                (index + 1U >= bytes || manifest[index + 1U] != '\n')) ||
            (manifest[index] == '\n' &&
                (index == 0U || manifest[index - 1U] != '\r'))) return 0;
    }
    SecureZeroMemory(rows, sizeof(*rows) * RETAINED_ROW_COUNT);
    for (index = 0U; index < RETAINED_ROW_COUNT; ++index)
        rows[index].locked.handle = INVALID_HANDLE_VALUE;
    while (cursor < end) {
        char *cr = (char *)memchr(cursor, '\r', (size_t)(end - cursor));
        size_t line_bytes;
        if (cr == NULL || cr + 1 >= end || cr[1] != '\n') goto failure;
        line_bytes = (size_t)(cr - cursor);
        if (line_number == 0U) {
            if (line_bytes != sizeof(magic) - 1U || memcmp(cursor, magic, line_bytes) != 0) goto failure;
        } else if (line_number == 1U) {
            if (line_bytes != sizeof(header) - 1U || memcmp(cursor, header, line_bytes) != 0) goto failure;
        } else {
            char line[1024];
            char *fields[4];
            size_t field_count = 1U;
            ULONGLONG expected_bytes;
            ManifestRowV3R22 *row;
            if (row_count >= RETAINED_ROW_COUNT || line_bytes == 0U ||
                line_bytes >= sizeof(line)) goto failure;
            memcpy(line, cursor, line_bytes);
            line[line_bytes] = '\0';
            fields[0] = line;
            for (index = 0U; index < line_bytes; ++index) {
                if (line[index] == '\t') {
                    if (field_count >= _countof(fields)) goto failure;
                    line[index] = '\0';
                    fields[field_count++] = line + index + 1U;
                }
            }
            if (field_count != _countof(fields) || !manifest_label_valid(fields[0]) ||
                !manifest_bytes_valid(fields[2], &expected_bytes) ||
                !lower_hex_exact(fields[3], strlen(fields[3])) ||
                strlen(fields[1]) >= MANIFEST_PATH_CAPACITY) goto failure;
            row = &rows[row_count];
            if (strcpy_s(row->label, sizeof(row->label), fields[0]) != 0 ||
                strcpy_s(row->manifest_path, sizeof(row->manifest_path), fields[1]) != 0 ||
                strcpy_s(row->sha256, sizeof(row->sha256), fields[3]) != 0 ||
                !manifest_path_to_absolute(row->manifest_path, row->absolute_path)) goto failure;
            if (row_count > 0U && strcmp(rows[row_count - 1U].label, row->label) >= 0) goto failure;
            for (index = 0U; index < row_count; ++index)
                if (_stricmp(rows[index].manifest_path, row->manifest_path) == 0) goto failure;
            row->locked.path = row->absolute_path;
            row->locked.expected_bytes = expected_bytes;
            row->locked.expected_sha256 = row->sha256;
            ++row_count;
        }
        ++line_number;
        cursor = cr + 2;
    }
    if (cursor != end || line_number != MANIFEST_LINE_COUNT ||
        row_count != RETAINED_ROW_COUNT) goto failure;
    for (index = 0U; index < RETAINED_ROW_COUNT; ++index)
        if (!lock_file(&rows[index].locked)) goto failure;
    return 1;
failure:
    release_manifest_rows(rows);
    return 0;
}

static ManifestRowV3R22 *find_manifest_row(ManifestRowV3R22 rows[RETAINED_ROW_COUNT],
    const char *label) {
    size_t index;
    for (index = 0U; index < RETAINED_ROW_COUNT; ++index)
        if (strcmp(rows[index].label, label) == 0) return &rows[index];
    return NULL;
}

static int manifest_row_exact(const ManifestRowV3R22 *row, const char *path,
    ULONGLONG bytes, const char *sha256) {
    return row != NULL && strcmp(row->manifest_path, path) == 0 &&
        row->locked.expected_bytes == bytes && strcmp(row->sha256, sha256) == 0;
}

static int recheck_manifest_rows(ManifestRowV3R22 rows[RETAINED_ROW_COUNT]) {
    size_t index;
    for (index = 0U; index < RETAINED_ROW_COUNT; ++index)
        if (!verify_handle_bound(rows[index].locked.handle, rows[index].locked.path,
                rows[index].locked.expected_bytes, rows[index].locked.expected_sha256,
                &rows[index].locked.identity)) return 0;
    return 1;
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
    static const char *keys[50] = {
        "decision", "auditor", "author", "native_executable_sha256",
        "identity_anchor_sha256", "contract_sha256", "native_source_sha256",
        "static_test_sha256", "runtime_control_checkpoint_sha256",
        "retained_manifest_sha256", "retained_manifest_rows",
        "retained_manifest_line_endings", "v3r22_consumed_failure_closure_root_sha256",
        "v3r23_rejected_closure_root_sha256",
        "v3r24_consumed_failure_closure_root_sha256", "v3r24_author_artifact_count",
        "v3r24_audit_run_artifact_count",
        "v3r25_consumed_failure_closure_root_sha256", "v3r25_author_artifact_count",
        "v3r25_audit_artifact_count", "v3r25_run_artifact_count",
        "v3r25_terminal_checkpoint", "v3r25_plan_attempts", "v3r25_plan_returns",
        "v3r25_operation_enters", "v3r25_operation_returns", "v3r25_authority",
        "post_call_validation_mode", "precall_marshaled_equivalence",
        "postcall_object_identity_and_immutable_metadata",
        "v3r9_v3r10_v3r11_history_closure_root_sha256", "controller_compile_flag",
        "controller_compile_flag_name", "excluded_failure_cause", "plan_callable",
        "marshal_runtime_version", "marshal_fingerprint_format",
        "marshal_validator_code_objects", "marshal_v4_failure_count",
        "marshal_v5_success_count", "plan_call_maximum", "validator_checkpoint_terminal_success",
        "operation_enter_maximum", "operation_return_maximum",
        "exception_type_max_bytes", "exception_message_max_bytes",
        "v3r22_authority", "v3r23_authority", "v3r24_authority", "stop_before"
    };
    const char *expected[50] = {
        AUDIT_DECISION, NULL, V3R22_AUTHOR_ID, NULL, NULL,
        V3R22_CONTRACT_SHA256, V3R22_SOURCE_SHA256, V3R22_TEST_SHA256,
        V3R22_CONTROL_SHA256, V3R22_MANIFEST_SHA256, "137",
        "CRLF_EXACT_139_LINES", V3R26_V3R22_CONSUMED_FAILURE_CLOSURE_ROOT_SHA256,
        V3R26_V3R23_REJECTED_CLOSURE_ROOT_SHA256,
        V3R26_V3R24_CONSUMED_FAILURE_CLOSURE_ROOT_SHA256, "10", "9",
        V3R26_V3R25_CONSUMED_FAILURE_CLOSURE_ROOT_SHA256, "10", "6", "4",
        "218", "1", "1", "16", "15", "CONSUMED_FAILURE_DO_NOT_RERUN",
        "PRECALL_STRUCTURAL_EQUIVALENCE_POSTCALL_IDENTITY",
        "FORMAT5_EXACT_TWIN_CODE_AND_ANNOTATE_BYTES",
        "EXACT_FUNCTION_CODE_ANNOTATE_DEFAULT_CLOSURE_GLOBAL_OBJECT_IDENTITY_AND_IMMUTABLE_METADATA",
        V3R22_V3R9_V3R10_V3R11_HISTORY_CLOSURE_ROOT_SHA256, "0x1000000",
        "CO_FUTURE_ANNOTATIONS", "UNRESOLVED_ANNOTATION_NAMES_PROVEN_EXCLUDED",
        "_build_execution_plan", "5", "5", "20", "4", "20", "1", "230", "21", "21", "63", "191",
        "CONSUMED_FAILURE_DO_NOT_RERUN", "REJECTED_NO_EXECUTION_AUTHORITY", "CONSUMED_FAILURE_DO_NOT_RERUN",
        "bootstrap,broker,process,AFES,Blender,body,save,render,export"
    };
    char values[50][257];
    size_t value_lengths[50];
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
        int is_hash = strstr(keys[index], "sha256") != NULL;
        if (expected[index] == NULL ||
            value_lengths[index] != strlen(expected[index]) ||
            memcmp(values[index], expected[index], value_lengths[index]) != 0 ||
            (is_hash && !lower_hex_exact(values[index], value_lengths[index]))) goto cleanup;
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
    memcpy(record.magic, RESERVATION_MAGIC, sizeof(RESERVATION_MAGIC) - 1U);
    record.version = 1U; record.type = 1U; record.bytes = (uint32_t)sizeof(record); record.state = RECORD_PENDING;
    memcpy(record.executable_sha256, self_sha, SHA_BYTES); memcpy(record.audit_sha256, audit_sha, SHA_BYTES);
    if (!hash_path_exact(V3R14_RECEIPT_PATH, V3R22_V3R14_RECEIPT_BYTES, V3R22_V3R14_RECEIPT_SHA256, record.v3r14_receipt_sha256) ||
        !hash_path_exact(MANIFEST_PATH, V3R22_MANIFEST_BYTES, V3R22_MANIFEST_SHA256, record.manifest_sha256) ||
        !hash_path_exact(PYTHON_DLL_PATH, V3R22_PYTHON_DLL_BYTES, V3R22_PYTHON_DLL_SHA256, record.python_dll_sha256) ||
        !hash_path_exact(CONTROLLER_PATH, V3R22_CONTROLLER_BYTES, V3R22_CONTROLLER_SHA256, record.controller_sha256) ||
        !hash_path_exact(EXECUTION_CONTRACT_PATH, V3R22_EXECUTION_CONTRACT_BYTES, V3R22_EXECUTION_CONTRACT_SHA256, record.execution_contract_sha256) ||
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
    const ValidatorTelemetry *validator, uint32_t state, uint32_t stage) {
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
    memcpy(record.magic, TERMINAL_MAGIC, sizeof(TERMINAL_MAGIC) - 1U);
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
    memcpy(&record.validator, validator, sizeof(record.validator));
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
    FARPROC runtime_error_symbol;
    PyObject **runtime_error_address = NULL;
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
    RESOLVE_API(api, unicode_from_string_size, "PyUnicode_FromStringAndSize");
    RESOLVE_API(api, unicode_utf8, "PyUnicode_AsUTF8AndSize");
    RESOLVE_API(api, bytes_from_data, "PyBytes_FromStringAndSize");
    RESOLVE_API(api, bytes_as_data, "PyBytes_AsStringAndSize");
    RESOLVE_API(api, cfunction_new, "PyCFunction_NewEx");
    RESOLVE_API(api, error_set_string, "PyErr_SetString");
    RESOLVE_API(api, long_as_ull, "PyLong_AsUnsignedLongLong");
    RESOLVE_API(api, tuple_size, "PyTuple_Size");
    RESOLVE_API(api, tuple_get, "PyTuple_GetItem");
    RESOLVE_API(api, callable, "PyCallable_Check");
    RESOLVE_API(api, decref, "Py_DecRef");
    RESOLVE_API(api, error_occurred, "PyErr_Occurred");
    RESOLVE_API(api, error_clear, "PyErr_Clear");
    RESOLVE_API(api, error_get_raised, "PyErr_GetRaisedException");
    RESOLVE_API(api, object_type, "PyObject_Type");
    RESOLVE_API(api, object_get_attr_string, "PyObject_GetAttrString");
    RESOLVE_API(api, object_str, "PyObject_Str");
    runtime_error_symbol = GetProcAddress(api->module, "PyExc_RuntimeError");
    if (runtime_error_symbol == NULL ||
        sizeof(runtime_error_symbol) != sizeof(runtime_error_address)) return 0;
    memcpy(&runtime_error_address, &runtime_error_symbol, sizeof(runtime_error_address));
    if (runtime_error_address == NULL || *runtime_error_address == NULL) return 0;
    api->runtime_error = *runtime_error_address;
    return 1;
}

static void sanitize_python_text(const char *input, Py_ssize_t length,
    char *output, size_t capacity, uint32_t *truncated) {
    size_t index;
    size_t written = 0U;
    if (capacity == 0U) return;
    output[0] = '\0';
    if (input == NULL || length <= 0) return;
    for (index = 0U; index < (size_t)length; ++index) {
        unsigned char c = (unsigned char)input[index];
        char kept;
        if (written + 1U >= capacity) {
            *truncated = 1U;
            break;
        }
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == ' ' || c == '_' || c == '-' ||
            c == '.' || c == ':' || c == ',' || c == '/' || c == '(' ||
            c == ')' || c == '[' || c == ']' || c == '=' || c == '\'') kept = (char)c;
        else kept = '?';
        output[written++] = kept;
    }
    output[written] = '\0';
}

static void capture_python_exception(PythonApi *api, ValidatorTelemetry *telemetry) {
    PyObject *error = NULL;
    PyObject *error_type = NULL;
    PyObject *type_name = NULL;
    PyObject *message = NULL;
    const char *value;
    Py_ssize_t length = 0;
    uint32_t ignored_truncation = 0U;
    if (api == NULL || telemetry == NULL || api->error_occurred == NULL ||
        api->error_get_raised == NULL || api->error_occurred() == NULL) return;
    error = api->error_get_raised();
    if (error == NULL) return;
    telemetry->python_error_captured = 1U;
    error_type = api->object_type(error);
    if (error_type != NULL)
        type_name = api->object_get_attr_string(error_type, "__name__");
    if (type_name != NULL) {
        value = api->unicode_utf8(type_name, &length);
        if (value != NULL)
            sanitize_python_text(value, length, telemetry->exception_type,
                sizeof(telemetry->exception_type), &ignored_truncation);
    }
    if (telemetry->exception_type[0] == '\0')
        memcpy(telemetry->exception_type, "PythonException", sizeof("PythonException"));
    if (api->error_occurred() != NULL) api->error_clear();
    message = api->object_str(error);
    if (message != NULL) {
        value = api->unicode_utf8(message, &length);
        if (value != NULL)
            sanitize_python_text(value, length, telemetry->exception_message,
                sizeof(telemetry->exception_message),
                &telemetry->exception_message_truncated);
    }
    if (api->error_occurred() != NULL) api->error_clear();
    if (message != NULL) api->decref(message);
    if (type_name != NULL) api->decref(type_name);
    if (error_type != NULL) api->decref(error_type);
    api->decref(error);
}

static int capture_progress_value(PythonApi *api, PyObject *globals,
    const char *name, uint32_t *output) {
    PyObject *value;
    unsigned long long number;
    if (api == NULL || globals == NULL || name == NULL || output == NULL) return 0;
    value = api->dict_get(globals, name);
    if (value == NULL) return 0;
    number = api->long_as_ull(value);
    if (api->error_occurred() != NULL || number > UINT32_MAX) {
        api->error_clear();
        return 0;
    }
    *output = (uint32_t)number;
    return 1;
}

static const char PLAN_VALIDATOR[] =
    "__v3r26_checkpoint__=100\n"
    "__v3r26_plan_attempts__=0\n"
    "__v3r26_plan_returns__=0\n"
    "__v3r26_operation_enters__=0\n"
    "__v3r26_operation_returns__=0\n"
    "import builtins as _v3_b\n"
    "import json as _v3_j\n"
    "import marshal as _v3_m\n"
    "import types as _v3_t\n"
    "_v3_zip='C:/Users/robmc/Kira/tools/native/runtime/python314_stdlib_v3r4.zip'\n"
    "def _v3_origin(module,label,allowed):\n"
    "    spec=getattr(module,'__spec__',None); origin=getattr(spec,'origin',None)\n"
    "    if type(origin) is not str: raise RuntimeError('module_origin_missing:'+label)\n"
    "    normalized=origin.replace('\\\\','/')\n"
    "    if normalized not in allowed: raise RuntimeError('module_origin_outside_locked_runtime:'+label+':'+normalized)\n"
    "    file_value=getattr(module,'__file__',None)\n"
    "    if normalized not in {'built-in','frozen'} and file_value is not None and (type(file_value) is not str or file_value.replace('\\\\','/')!=normalized): raise RuntimeError('module_file_origin_disagreement:'+label)\n"
    "    return (id(module),id(spec),id(getattr(module,'__loader__',None)),normalized)\n"
    "def _v3_module_fingerprint():\n"
    "    return (_v3_origin(_v3_b,'builtins',{'built-in'}),_v3_origin(_v3_m,'marshal',{'built-in'}),_v3_origin(_v3_j,'json',{_v3_zip+'/json/__init__.py',_v3_zip+'/json/__pycache__/__init__.cpython-314.pyc'}),_v3_origin(_v3_t,'types',{'frozen',_v3_zip+'/types.py',_v3_zip+'/__pycache__/types.cpython-314.pyc'}))\n"
    "_v3_module_snapshot=_v3_module_fingerprint()\n"
    "__v3r26_checkpoint__=110\n"
    "_v3_required_marshal_version=5\n"
    "if type(_v3_m.version) is not int or _v3_m.version != _v3_required_marshal_version: raise RuntimeError('marshal_runtime_version_not_exact_5')\n"
    "_v3_marshal_snapshot=(id(_v3_m),_v3_m.version,_v3_required_marshal_version)\n"
    "__v3r26_checkpoint__=115\n"
    "_v3_counts={'sha':0,'hex':0,'json':0,'forbidden':0,'plan':0}\n"
    "def _v3_sha(value):\n"
    "    _v3_counts['sha']+=1\n"
    "    if type(value) is not bytes: raise RuntimeError('sha_input_not_exact_bytes')\n"
    "    return __native_sha256_hex__(value)\n"
    "def _v3_hex(value):\n"
    "    _v3_counts['hex']+=1\n"
    "    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)\n"
    "def _v3_pairs(pairs):\n"
    "    result={}\n"
    "    for key,value in pairs:\n"
    "        if type(key) is not str or key in result: raise ValueError('strict_json_duplicate_or_non_string_key')\n"
    "        result[key]=value\n"
    "    return result\n"
    "def _v3_reject_number(value):\n"
    "    raise ValueError('strict_json_float_or_nonfinite_refused')\n"
    "def _v3_strict(raw,label):\n"
    "    _v3_counts['json']+=1\n"
    "    if type(raw) is not bytes: raise RuntimeError('strict_json_input_not_exact_bytes:'+label)\n"
    "    if raw[:3]==b'\\xef\\xbb\\xbf': raw=raw[3:]\n"
    "    parsed=_v3_j.loads(raw.decode('utf-8','strict'),object_pairs_hook=_v3_pairs,parse_float=_v3_reject_number,parse_constant=_v3_reject_number)\n"
    "    if type(parsed) is not dict: raise ValueError('strict_json_root_not_object:'+label)\n"
    "    return parsed\n"
    "def _v3_blob_trap(*args,**kwargs):\n"
    "    _v3_counts['forbidden']+=1\n"
    "    raise RuntimeError('decode_u32_blob_outside_plan_boundary')\n"
    "def _v3_canonical_trap(*args,**kwargs):\n"
    "    _v3_counts['forbidden']+=1\n"
    "    raise RuntimeError('canonical_json_outside_plan_boundary')\n"
    "_v3_builtin_names=('__build_class__','RuntimeError','any','bytes','dict','int','isinstance','len','list','set','sorted','str','tuple','type')\n"
    "_v3_function_names=('_sha256_bytes','_strict_object','_signed64','_u32','_normalize_indices','_decode_blob','_decode_index_reference','_decode_edge_reference','_validate_compact_afes_analysis','_exact_row','_iter_contract_rows','_scope','_process_contract','_pair_contract','_truth_boundary','_bootstrap_contract','_native_launcher_contract','_audit_gate','_outer_truth','_verify_retained_rows','_validate_audit','_build_execution_plan','_validate_child_payload','_compare_pair','_success_payload','_failure_payload')\n"
    "_v3_global_keys={'__builtins__','__name__','__doc__','_native_sha256_hex','_native_is_lower_hex64','_native_parse_strict_json_object','_native_decode_u32_blob','_native_canonical_json_sha256','CONTRACT_RELATIVE_PATH','AUDIT_RELATIVE_PATH','OUTPUT_RELATIVE_PATH','OUTCOME_RELATIVE_PATH','MANIFEST_RELATIVE_PATH','CHECKPOINT_RELATIVE_PATH','MAX_FRAME_BYTES','MAX_STDOUT_BYTES','MAX_STDERR_BYTES','UINT32_MAX','SIGNED64_MIN','SIGNED64_MAX','NANOMETERS_PER_METER','BLOB_CODEC','INDEX_SEMANTIC','EDGE_SEMANTIC','ROUNDING_RULE','ENVIRONMENT_INHERITED_EXACT_KEYS','MUTABLE_ENVIRONMENT_UNDER_UNIQUE_RUN_ROOT','CONSTANT_ENVIRONMENT','BLENDER_COMMAND_TEMPLATE','LockedPairV3R9PlanError','_sha256_bytes','_strict_object','_signed64','_u32','_normalize_indices','_decode_blob','_decode_index_reference','_decode_edge_reference','_validate_compact_afes_analysis','_exact_row','_iter_contract_rows','_scope','_process_contract','_pair_contract','_truth_boundary','_bootstrap_contract','_native_launcher_contract','_audit_gate','_outer_truth','_verify_retained_rows','_validate_audit','_build_execution_plan','_validate_child_payload','_compare_pair','_success_payload','_failure_payload','CONTROLLER_EXPORTED_CALLS'}\n"
    "def _v3_new_controller():\n"
    "    restricted={name:getattr(_v3_b,name) for name in _v3_builtin_names}\n"
    "    g={'__builtins__':restricted,'__name__':'_kira_r25_v3r9_pure_controller_retained','_native_sha256_hex':_v3_sha,'_native_is_lower_hex64':_v3_hex,'_native_parse_strict_json_object':_v3_strict,'_native_decode_u32_blob':_v3_blob_trap,'_native_canonical_json_sha256':_v3_canonical_trap}\n"
    "    code=compile(__controller_bytes__,'<native-retained-controller-v3r9>','exec',flags=0x1000000,dont_inherit=True,optimize=0)\n"
    "    if code.co_flags & 0x1000000 != 0x1000000: raise RuntimeError('controller_compile_flag_not_CO_FUTURE_ANNOTATIONS')\n"
    "    exec(code,g,g)\n"
    "    if set(g)!=_v3_global_keys: raise RuntimeError('controller_exact_global_key_closure_drift')\n"
    "    return g\n"
    "def _v3_code_bytes(fn):\n"
    "    return _v3_m.dumps(fn.__code__,5)\n"
    "def _v3_annotate_fingerprint(fn,expected_globals,required=False,include_code_bytes=True):\n"
    "    annotate=getattr(fn,'__annotate__',None)\n"
    "    if annotate is None:\n"
    "        if required: raise RuntimeError('future_annotations_stringizer_missing:'+fn.__qualname__)\n"
    "        return None\n"
    "    if type(annotate) is not _v3_t.FunctionType or annotate.__globals__ is not expected_globals: raise RuntimeError('deferred_annotate_type_or_globals_drift:'+fn.__qualname__)\n"
    "    closure=annotate.__closure__; cells=[]\n"
    "    if closure is not None:\n"
    "        for cell in closure:\n"
    "            try: value=cell.cell_contents; cells.append((id(cell),id(value),type(value),getattr(type(value),'__module__',None),getattr(type(value),'__qualname__',None)))\n"
    "            except ValueError: cells.append((id(cell),None,None,None,None))\n"
    "    return (id(annotate),id(annotate.__code__),_v3_m.dumps(annotate.__code__,5) if include_code_bytes else None,id(annotate.__defaults__),annotate.__defaults__,id(annotate.__kwdefaults__),None if annotate.__kwdefaults__ is None else dict(annotate.__kwdefaults__),id(closure),tuple(cells),annotate.__module__,annotate.__name__,annotate.__qualname__)\n"
    "def _v3_validate_controller(left,right,snapshot=None):\n"
    "    if set(left)!=_v3_global_keys or set(right)!=_v3_global_keys: raise RuntimeError('controller_global_key_drift')\n"
    "    if set(left['__builtins__'])!=set(_v3_builtin_names) or set(right['__builtins__'])!=set(_v3_builtin_names): raise RuntimeError('controller_builtin_key_drift')\n"
    "    for name in _v3_builtin_names:\n"
    "        if left['__builtins__'][name] is not getattr(_v3_b,name) or right['__builtins__'][name] is not getattr(_v3_b,name): raise RuntimeError('controller_builtin_identity_drift:'+name)\n"
    "    captured={}\n"
    "    for name in _v3_function_names:\n"
    "        a=left[name]; b=right[name]\n"
    "        if type(a) is not _v3_t.FunctionType or type(b) is not _v3_t.FunctionType: raise RuntimeError('controller_function_type:'+name)\n"
    "        if a.__globals__ is not left or b.__globals__ is not right: raise RuntimeError('controller_function_globals:'+name)\n"
    "        if a.__code__.co_flags & 0x1000000 != 0x1000000 or b.__code__.co_flags & 0x1000000 != 0x1000000: raise RuntimeError('controller_function_future_annotations_flag_drift:'+name)\n"
    "        if a.__defaults__ is not None or b.__defaults__ is not None or a.__kwdefaults__ is not None or b.__kwdefaults__ is not None or a.__closure__ is not None or b.__closure__ is not None: raise RuntimeError('controller_function_defaults_or_closure:'+name)\n"
    "        if a.__module__!='_kira_r25_v3r9_pure_controller_retained' or b.__module__!='_kira_r25_v3r9_pure_controller_retained' or a.__qualname__!=name or b.__qualname__!=name: raise RuntimeError('controller_function_stable_metadata:'+name)\n"
    "        if snapshot is None:\n"
    "            ac=_v3_code_bytes(a); bc=_v3_code_bytes(b); aa=_v3_annotate_fingerprint(a,left,True,True); ba=_v3_annotate_fingerprint(b,right,True,True)\n"
    "            if ac!=bc or (aa is None)!=(ba is None) or (aa is not None and (aa[2]!=ba[2] or aa[4]!=ba[4] or aa[6]!=ba[6] or len(aa[8])!=len(ba[8]) or aa[9:]!=ba[9:])): raise RuntimeError('controller_function_pre_call_code_or_deferred_annotate_metadata:'+name)\n"
    "            captured[name]=(id(a),id(b),ac,bc,id(a.__code__),id(b.__code__),id(a.__defaults__),id(b.__defaults__),a.__defaults__,b.__defaults__,id(a.__kwdefaults__),id(b.__kwdefaults__),a.__kwdefaults__,b.__kwdefaults__,aa,ba)\n"
    "        else:\n"
    "            prior=snapshot[name]; aa=_v3_annotate_fingerprint(a,left,True,False); ba=_v3_annotate_fingerprint(b,right,True,False)\n"
    "            stable=(id(a),id(b),id(a.__code__),id(b.__code__),id(a.__defaults__),id(b.__defaults__),a.__defaults__,b.__defaults__,id(a.__kwdefaults__),id(b.__kwdefaults__),a.__kwdefaults__,b.__kwdefaults__)\n"
    "            expected=(prior[0],prior[1],prior[4],prior[5],prior[6],prior[7],prior[8],prior[9],prior[10],prior[11],prior[12],prior[13])\n"
    "            if stable!=expected or aa[:2]+aa[3:]!=prior[14][:2]+prior[14][3:] or ba[:2]+ba[3:]!=prior[15][:2]+prior[15][3:]: raise RuntimeError('controller_function_post_call_identity_or_immutable_metadata_drift:'+name)\n"
    "            captured[name]=prior\n"
    "    cls_a=left['LockedPairV3R9PlanError']; cls_b=right['LockedPairV3R9PlanError']\n"
    "    if type(cls_a) is not type or type(cls_b) is not type or cls_a.__bases__!=(RuntimeError,) or cls_b.__bases__!=(RuntimeError,) or cls_a.__name__!='LockedPairV3R9PlanError' or cls_b.__name__!='LockedPairV3R9PlanError' or cls_a.__doc__!=cls_b.__doc__ or set(cls_a.__dict__)!=set(cls_b.__dict__): raise RuntimeError('controller_exception_class_drift')\n"
    "    special=set(_v3_function_names)|{'LockedPairV3R9PlanError','__builtins__'}\n"
    "    for name in _v3_global_keys-special:\n"
    "        if name.startswith('_native_'):\n"
    "            if left[name] is not right[name]: raise RuntimeError('controller_native_helper_identity_drift:'+name)\n"
    "        elif type(left[name]) is not type(right[name]) or left[name]!=right[name]: raise RuntimeError('controller_constant_drift:'+name)\n"
    "    return captured\n"
    "def _v3_glue_object(raw,label):\n"
    "    if raw[:3]==b'\\xef\\xbb\\xbf': raw=raw[3:]\n"
    "    value=_v3_j.loads(raw.decode('utf-8','strict'),object_pairs_hook=_v3_pairs,parse_float=_v3_reject_number,parse_constant=_v3_reject_number)\n"
    "    if type(value) is not dict: raise RuntimeError('glue_json_root:'+label)\n"
    "    return value\n"
    "_v3_helper_names=('_v3_origin','_v3_module_fingerprint','_v3_sha','_v3_hex','_v3_pairs','_v3_reject_number','_v3_strict','_v3_blob_trap','_v3_canonical_trap','_v3_new_controller','_v3_code_bytes','_v3_annotate_fingerprint','_v3_validate_controller','_v3_glue_object','_v3_capture_helpers')\n"
    "def _v3_capture_helpers(snapshot=None):\n"
    "    harness=_v3_sha.__globals__; captured={}\n"
    "    for name in _v3_helper_names:\n"
    "        fn=harness.get(name)\n"
    "        if type(fn) is not _v3_t.FunctionType or fn.__globals__ is not harness or fn.__closure__ is not None or fn.__module__!='__main__' or fn.__qualname__!=name: raise RuntimeError('harness_helper_metadata_drift:'+name)\n"
    "        if snapshot is None:\n"
    "            captured[name]=(id(fn),id(fn.__code__),_v3_m.dumps(fn.__code__,5),id(fn.__defaults__),fn.__defaults__,id(fn.__kwdefaults__),None if fn.__kwdefaults__ is None else dict(fn.__kwdefaults__),id(fn.__closure__),_v3_annotate_fingerprint(fn,harness,False,True),id(fn.__globals__))\n"
    "        else:\n"
    "            prior=snapshot[name]; annotate=_v3_annotate_fingerprint(fn,harness,False,False)\n"
    "            stable=(id(fn),id(fn.__code__),id(fn.__defaults__),fn.__defaults__,id(fn.__kwdefaults__),None if fn.__kwdefaults__ is None else dict(fn.__kwdefaults__),id(fn.__closure__),id(fn.__globals__))\n"
    "            expected=(prior[0],prior[1],prior[3],prior[4],prior[5],prior[6],prior[7],prior[9])\n"
    "            if stable!=expected or (annotate is None)!=(prior[8] is None) or (annotate is not None and annotate[:2]+annotate[3:]!=prior[8][:2]+prior[8][3:]): raise RuntimeError('harness_helper_post_call_identity_or_immutable_metadata_drift:'+name)\n"
    "            captured[name]=prior\n"
    "    return captured\n"
    "_v3_helper_snapshot=_v3_capture_helpers()\n"
    "__v3r26_checkpoint__=120\n"
    "_v3_native_sha_snapshot=(id(__native_sha256_hex__),type(__native_sha256_hex__),getattr(__native_sha256_hex__,'__name__',None),getattr(__native_sha256_hex__,'__module__',None))\n"
    "if type(__retained_by_path__) is not dict or len(__retained_by_path__)!=137 or any(type(k) is not str or type(v) is not bytes for k,v in __retained_by_path__.items()): raise RuntimeError('retained_manifest_dictionary_not_exact_137')\n"
    "__v3r26_checkpoint__=130\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=140\n"
    "_v3_left=_v3_new_controller()\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=141\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=150\n"
    "_v3_right=_v3_new_controller()\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=151\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=160\n"
    "_v3_snapshot=_v3_validate_controller(_v3_left,_v3_right)\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=161\n"
    "__v3r26_operation_enters__+=1; _v3_counts['plan']+=1; __v3r26_plan_attempts__+=1; __v3r26_checkpoint__=170\n"
    "_v3_plan=_v3_left['_build_execution_plan'](contract_bytes=__execution_contract_bytes__,audit_bytes=__v3r9_audit_bytes__,retained_by_path=__retained_by_path__,expected_contract_sha256='f50df32a70093cf968e2d6be7c7de228d84f003605f854b97bfa542b9ea396d5',accepted_audit_sha256='2e21632eb1d394e43af6da8dbdfcdfbd2db4c86b7460fc3def319273e4e4c414',manifest_row={'path':'RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/RETAINED_NATIVE_LOCK_MANIFEST.tsv','bytes':24975,'sha256':'6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96'})\n"
    "__v3r26_plan_returns__+=1; __v3r26_operation_returns__+=1; __v3r26_checkpoint__=171\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=180\n"
    "if _v3_counts!={'sha':222,'hex':231,'json':4,'forbidden':0,'plan':1}: raise RuntimeError('controller_exact_helper_or_plan_call_count_drift')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=181\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=190\n"
    "_v3_expected_keys={'schema','contract_sha256','contract_bytes','blender_executable','foundation_blend','execution_wrapper','output_relative_path','outcome_relative_path','process_contract','outer_truth_boundary','contract','v5','v2'}\n"
    "if type(_v3_plan) is not dict or set(_v3_plan)!=_v3_expected_keys: raise RuntimeError('plan_exact_key_shape')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=191\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=200\n"
    "_v3_contract=_v3_glue_object(__execution_contract_bytes__,'contract')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=201\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=202\n"
    "_v3_bindings=_v3_contract['bindings']; _v3_v5_path=_v3_bindings['afes_v5_config']['path']; _v3_v2_path=_v3_contract['afes_v5_transitive_rows']['attempt_02_preservation']['config']['path']\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=203\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=204\n"
    "_v3_v5=_v3_glue_object(__retained_by_path__[_v3_v5_path],'v5')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=205\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=206\n"
    "_v3_v2=_v3_glue_object(__retained_by_path__[_v3_v2_path],'v2')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=207\n"
    "_v3_outer=['READ_ONLY_FOUNDATION_DIAGNOSTIC','NO_BLEND_MUTATION_OR_SAVE','NO_RENDER_OR_EXPORT','NO_CANDIDATE_OR_BODY_AUTHORING','THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE','V3R1_REJECTED_AND_NOT_EXECUTED','V3R2_REJECTED_AND_NOT_EXECUTED','V3R3_REJECTED_AND_NOT_EXECUTED','V3R4_REJECTED_AND_NOT_EXECUTED','V3R5_REJECTED_AND_NOT_EXECUTED','V3R6_STATIC_AUDIT_ACCEPTED_BUT_STARTUP_FAILED_BEFORE_SIDE_EFFECT','V3R7_STATIC_AUDIT_ACCEPTED_BUT_RECORDED_COMMAND_TEMPLATE_CONSUMED_AND_REJECTED','V3R8_REJECTED_BY_FRESH_STATIC_AUDIT_WITHOUT_EXECUTION']\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=208\n"
    "if _v3_plan['schema']!='kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r9' or _v3_plan['contract_sha256']!='f50df32a70093cf968e2d6be7c7de228d84f003605f854b97bfa542b9ea396d5' or _v3_plan['contract_bytes']!=146969: raise RuntimeError('plan_identity_drift')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=209\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=210\n"
    "if _v3_plan['blender_executable']!=_v3_bindings['blender_executable']['path'] or _v3_plan['foundation_blend']!=_v3_bindings['foundation_blend']['path'] or _v3_plan['execution_wrapper']!=_v3_bindings['execution_wrapper']['path']: raise RuntimeError('plan_retained_path_drift')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=211\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=212\n"
    "if _v3_plan['output_relative_path']!='RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution/attempt_03r9' or _v3_plan['outcome_relative_path']!='RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/EXECUTION_OUTCOME.receipt.bin': raise RuntimeError('plan_output_path_drift')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=213\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=214\n"
    "if _v3_plan['process_contract']!=_v3_contract['process_contract'] or _v3_plan['outer_truth_boundary']!=_v3_outer or _v3_plan['contract']!=_v3_contract or _v3_plan['v5']!=_v3_v5 or _v3_plan['v2']!=_v3_v2: raise RuntimeError('plan_projection_drift')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=215\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=216\n"
    "_v3_stack=[_v3_plan]; _v3_nodes=0\n"
    "while _v3_stack:\n"
    "    value=_v3_stack.pop(); _v3_nodes+=1\n"
    "    if _v3_nodes>500000: raise RuntimeError('plan_data_node_bound')\n"
    "    if type(value) is dict:\n"
    "        if any(type(k) is not str for k in value): raise RuntimeError('plan_non_string_key')\n"
    "        _v3_stack.extend(value.values())\n"
    "    elif type(value) is list: _v3_stack.extend(value)\n"
    "    elif type(value) not in (str,int,bool,type(None)): raise RuntimeError('plan_non_data_authority_type:'+type(value).__name__)\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=217\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=218\n"
    "_v3_validate_controller(_v3_left,_v3_right,_v3_snapshot)\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=219\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=220\n"
    "_v3_capture_helpers(_v3_helper_snapshot)\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=221\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=222\n"
    "if _v3_module_fingerprint()!=_v3_module_snapshot or (id(_v3_m),_v3_m.version,_v3_required_marshal_version)!=_v3_marshal_snapshot: raise RuntimeError('locked_runtime_module_identity_origin_or_marshal_version_post_call_drift')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=223\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=224\n"
    "if (id(__native_sha256_hex__),type(__native_sha256_hex__),getattr(__native_sha256_hex__,'__name__',None),getattr(__native_sha256_hex__,'__module__',None))!=_v3_native_sha_snapshot: raise RuntimeError('native_sha_helper_post_call_drift')\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=225\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=226\n"
    "_v3_code_root=__native_sha256_hex__(b''.join(name.encode('ascii')+b'\\0'+_v3_snapshot[name][2] for name in sorted(_v3_function_names)))\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=227\n"
    "__v3r26_operation_enters__+=1; __v3r26_checkpoint__=228\n"
    "__v3r26_plan_validation__=(137,1,222,231,4,0,__v3r26_operation_enters__,__v3r26_operation_returns__+1,_v3_code_root)\n"
    "__v3r26_operation_returns__+=1; __v3r26_checkpoint__=229\n"
    "if __v3r26_operation_enters__!=21 or __v3r26_operation_returns__!=21: raise RuntimeError('operation_enter_return_terminal_drift')\n"
    "__v3r26_checkpoint__=230\n"
    "del _v3_plan,_v3_left,_v3_right,_v3_snapshot,_v3_contract,_v3_bindings,_v3_v5,_v3_v2,_v3_stack,_v3_helper_snapshot,_v3_native_sha_snapshot,_v3_module_snapshot,_v3_marshal_snapshot\n"
    "__retained_by_path__.clear()\n";

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
    LockedFile *controller, LockedFile *execution_contract, LockedFile *v3r9_audit,
    ManifestRowV3R22 rows[RETAINED_ROW_COUNT], UnloadTelemetry *unload,
    ValidatorTelemetry *telemetry, uint32_t *stage) {
    PythonApi api;
    PyConfig config;
    PyStatus status;
    unsigned char *controller_bytes = NULL;
    unsigned char *contract_bytes = NULL;
    unsigned char *audit_bytes = NULL;
    unsigned char *row_bytes = NULL;
    DWORD controller_length = 0U;
    DWORD contract_length = 0U;
    DWORD audit_length = 0U;
    DWORD row_length = 0U;
    PyObject *globals = NULL;
    PyObject *builtins;
    PyObject *name = NULL;
    PyObject *controller_object = NULL;
    PyObject *contract_object = NULL;
    PyObject *audit_object = NULL;
    PyObject *retained_object = NULL;
    PyObject *native_sha_object = NULL;
    PyObject *row_object = NULL;
    PyObject *validation = NULL;
    PyObject *marker;
    wchar_t module_path[MAX_PATH];
    DWORD module_length;
    size_t index;
    int initialized = 0;
    int ok = 0;
    int finalize_ok = 1;
    HMODULE old_module = NULL;
    SecureZeroMemory(&api, sizeof(api));
    SecureZeroMemory(unload, sizeof(*unload));
    SecureZeroMemory(telemetry, sizeof(*telemetry));
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
        !verify_handle_bound(stdlib_zip->handle, stdlib_zip->path,
            stdlib_zip->expected_bytes, stdlib_zip->expected_sha256, &stdlib_zip->identity) ||
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
    if (!api.status_exception(status)) status = api.wide_append(&config.argv, L"<v3r26-retained-controller-validation>");
    if (api.status_exception(status)) {
        api.config_clear(&config);
        goto cleanup;
    }
    status = api.initialize(&config);
    api.config_clear(&config);
    if (api.status_exception(status)) goto cleanup;
    initialized = 1;
    g_plan_python_api = &api;
    g_plan_native_sha_calls = 0ULL;
    *stage = 30U;
    if (!read_locked(controller, CONTROLLER_LIMIT, &controller_bytes, &controller_length) ||
        memchr(controller_bytes, '\0', controller_length) != NULL ||
        !read_locked(execution_contract, CONTRACT_LIMIT, &contract_bytes, &contract_length) ||
        memchr(contract_bytes, '\0', contract_length) != NULL ||
        !read_locked(v3r9_audit, 4096ULL, &audit_bytes, &audit_length) ||
        memchr(audit_bytes, '\0', audit_length) != NULL) goto cleanup;
    globals = api.dict_new();
    builtins = api.get_builtins();
    name = api.unicode_from_string("__main__");
    controller_object = api.bytes_from_data(
        (const char *)controller_bytes, (Py_ssize_t)controller_length);
    contract_object = api.bytes_from_data(
        (const char *)contract_bytes, (Py_ssize_t)contract_length);
    audit_object = api.bytes_from_data((const char *)audit_bytes, (Py_ssize_t)audit_length);
    retained_object = api.dict_new();
    native_sha_object = api.cfunction_new(&V3R22_NATIVE_SHA_METHOD, NULL, NULL);
    if (globals == NULL || builtins == NULL || name == NULL ||
        controller_object == NULL || contract_object == NULL || audit_object == NULL ||
        retained_object == NULL || native_sha_object == NULL ||
        api.dict_set(globals, "__builtins__", builtins) < 0 ||
        api.dict_set(globals, "__name__", name) < 0 ||
        api.dict_set(globals, "__controller_bytes__", controller_object) < 0 ||
        api.dict_set(globals, "__execution_contract_bytes__", contract_object) < 0 ||
        api.dict_set(globals, "__v3r9_audit_bytes__", audit_object) < 0 ||
        api.dict_set(globals, "__retained_by_path__", retained_object) < 0 ||
        api.dict_set(globals, "__native_sha256_hex__", native_sha_object) < 0) goto cleanup;
    for (index = 0U; index < RETAINED_ROW_COUNT; ++index) {
        if (!read_locked(&rows[index].locked, RETAINED_ROW_LIMIT, &row_bytes, &row_length))
            goto cleanup;
        row_object = api.bytes_from_data((const char *)row_bytes, (Py_ssize_t)row_length);
        SecureZeroMemory(row_bytes, (SIZE_T)row_length + 1U);
        HeapFree(GetProcessHeap(), 0U, row_bytes);
        row_bytes = NULL;
        row_length = 0U;
        if (row_object == NULL ||
            api.dict_set(retained_object, rows[index].manifest_path, row_object) < 0)
            goto cleanup;
        api.decref(row_object);
        row_object = NULL;
    }
    *stage = 40U;
    validation = api.run_string(PLAN_VALIDATOR, Py_file_input, globals, globals, NULL);
    if (validation == NULL) capture_python_exception(&api, telemetry);
    telemetry->native_sha_calls = g_plan_native_sha_calls;
    (void)capture_progress_value(&api, globals, "__v3r26_checkpoint__",
        &telemetry->checkpoint);
    (void)capture_progress_value(&api, globals, "__v3r26_plan_attempts__",
        &telemetry->plan_attempts);
    (void)capture_progress_value(&api, globals, "__v3r26_plan_returns__",
        &telemetry->plan_returns);
    (void)capture_progress_value(&api, globals, "__v3r26_operation_enters__",
        &telemetry->operation_enters);
    (void)capture_progress_value(&api, globals, "__v3r26_operation_returns__",
        &telemetry->operation_returns);
    marker = validation != NULL ? api.dict_get(globals, "__v3r26_plan_validation__") : NULL;
    telemetry->marker_present = marker != NULL ? 1U : 0U;
    if (marker == NULL || api.tuple_size(marker) != 9 ||
        telemetry->checkpoint != 230U || telemetry->plan_attempts != 1U ||
        telemetry->plan_returns != 1U || telemetry->operation_enters != 21U ||
        telemetry->operation_returns != 21U || g_plan_native_sha_calls != 223ULL)
        goto cleanup;
    {
        static const unsigned long long expected[8] = {
            137ULL, 1ULL, 222ULL, 231ULL, 4ULL, 0ULL, 21ULL, 21ULL
        };
        for (index = 0U; index < _countof(expected); ++index) {
            PyObject *item = api.tuple_get(marker, (Py_ssize_t)index);
            unsigned long long value = item != NULL ? api.long_as_ull(item) : ULLONG_MAX;
            if (item == NULL || api.error_occurred() != NULL || value != expected[index])
                goto cleanup;
        }
    }
    {
        PyObject *item = api.tuple_get(marker, 8);
        Py_ssize_t length = 0;
        const char *value = item != NULL ? api.unicode_utf8(item, &length) : NULL;
        if (value == NULL || length != SHA_HEX || !lower_hex_exact(value, (size_t)length))
            goto cleanup;
    }
    *stage = 50U;
    ok = 1;
cleanup:
    if (initialized && api.error_occurred != NULL && api.error_occurred() != NULL) {
        if (telemetry->python_error_captured == 0U) capture_python_exception(&api, telemetry);
        if (api.error_occurred() != NULL && api.error_clear != NULL) api.error_clear();
    }
    if (api.decref != NULL) {
        if (row_object != NULL) api.decref(row_object);
        if (validation != NULL) api.decref(validation);
        if (native_sha_object != NULL) api.decref(native_sha_object);
        if (retained_object != NULL) api.decref(retained_object);
        if (audit_object != NULL) api.decref(audit_object);
        if (contract_object != NULL) api.decref(contract_object);
        if (controller_object != NULL) api.decref(controller_object);
        if (name != NULL) api.decref(name);
        if (globals != NULL) api.decref(globals);
    }
    if (row_bytes != NULL) {
        SecureZeroMemory(row_bytes, (SIZE_T)row_length + 1U);
        HeapFree(GetProcessHeap(), 0U, row_bytes);
    }
    if (controller_bytes != NULL) {
        SecureZeroMemory(controller_bytes, (SIZE_T)controller_length + 1U);
        HeapFree(GetProcessHeap(), 0U, controller_bytes);
    }
    if (contract_bytes != NULL) {
        SecureZeroMemory(contract_bytes, (SIZE_T)contract_length + 1U);
        HeapFree(GetProcessHeap(), 0U, contract_bytes);
    }
    if (audit_bytes != NULL) {
        SecureZeroMemory(audit_bytes, (SIZE_T)audit_length + 1U);
        HeapFree(GetProcessHeap(), 0U, audit_bytes);
    }
    g_plan_python_api = NULL;
    g_plan_native_sha_calls = 0ULL;
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
    return ok;
}

int wmain(int argc, wchar_t **argv) {
    static const Binding fixed[] = {
        {SOURCE_PATH, V3R22_SOURCE_BYTES, V3R22_SOURCE_SHA256, "source"},
        {TEST_PATH, V3R22_TEST_BYTES, V3R22_TEST_SHA256, "test"},
        {CONTROL_PATH, V3R22_CONTROL_BYTES, V3R22_CONTROL_SHA256, "control"},
        {V3R25_CONSUMED_CONTRACT_PATH, V3R26_V3R25_CONTRACT_BYTES, V3R26_V3R25_CONTRACT_SHA256, "v3r25_consumed_contract"},
        {V3R25_CONSUMED_SOURCE_PATH, V3R26_V3R25_SOURCE_BYTES, V3R26_V3R25_SOURCE_SHA256, "v3r25_consumed_source"},
        {V3R25_CONSUMED_ANCHOR_PATH, V3R26_V3R25_ANCHOR_BYTES, V3R26_V3R25_ANCHOR_SHA256, "v3r25_consumed_anchor"},
        {V3R25_CONSUMED_OBJECT_PATH, V3R26_V3R25_OBJECT_BYTES, V3R26_V3R25_OBJECT_SHA256, "v3r25_consumed_object"},
        {V3R25_CONSUMED_EXECUTABLE_PATH, V3R26_V3R25_EXECUTABLE_BYTES, V3R26_V3R25_EXECUTABLE_SHA256, "v3r25_consumed_executable_do_not_rerun"},
        {V3R25_CONSUMED_TEST_PATH, V3R26_V3R25_TEST_BYTES, V3R26_V3R25_TEST_SHA256, "v3r25_consumed_test"},
        {V3R25_CONSUMED_CONTROL_PATH, V3R26_V3R25_CONTROL_BYTES, V3R26_V3R25_CONTROL_SHA256, "v3r25_consumed_control"},
        {V3R25_CONSUMED_BUILD_PATH, V3R26_V3R25_BUILD_BYTES, V3R26_V3R25_BUILD_SHA256, "v3r25_consumed_build"},
        {V3R25_CONSUMED_SEAL_PATH, V3R26_V3R25_SEAL_BYTES, V3R26_V3R25_SEAL_SHA256, "v3r25_consumed_seal"},
        {V3R25_CONSUMED_AUTHOR_CHECKPOINT_PATH, V3R26_V3R25_AUTHOR_CHECKPOINT_BYTES, V3R26_V3R25_AUTHOR_CHECKPOINT_SHA256, "v3r25_consumed_author_checkpoint"},
        {V3R25_CONSUMED_AUDIT_DECISION_PATH, V3R26_V3R25_AUDIT_DECISION_BYTES, V3R26_V3R25_AUDIT_DECISION_SHA256, "v3r25_consumed_audit_decision"},
        {V3R25_CONSUMED_AUDIT_CHECKPOINT_PATH, V3R26_V3R25_AUDIT_CHECKPOINT_BYTES, V3R26_V3R25_AUDIT_CHECKPOINT_SHA256, "v3r25_consumed_audit_checkpoint"},
        {V3R25_CONSUMED_AUDIT_PROBES_PATH, V3R26_V3R25_AUDIT_PROBES_BYTES, V3R26_V3R25_AUDIT_PROBES_SHA256, "v3r25_consumed_audit_probes"},
        {V3R25_CONSUMED_AUDIT_SIDECAR_PATH, V3R26_V3R25_AUDIT_SIDECAR_BYTES, V3R26_V3R25_AUDIT_SIDECAR_SHA256, "v3r25_consumed_audit_sidecar"},
        {V3R25_CONSUMED_AUDIT_PATH, V3R26_V3R25_AUDIT_BYTES, V3R26_V3R25_AUDIT_SHA256, "v3r25_consumed_audit"},
        {V3R25_CONSUMED_AUDIT_RESULTS_PATH, V3R26_V3R25_AUDIT_RESULTS_BYTES, V3R26_V3R25_AUDIT_RESULTS_SHA256, "v3r25_consumed_audit_results"},
        {V3R25_CONSUMED_EVIDENCE_PATH, V3R26_V3R25_EVIDENCE_BYTES, V3R26_V3R25_EVIDENCE_SHA256, "v3r25_consumed_run_evidence"},
        {V3R25_CONSUMED_RECEIPT_PATH, V3R26_V3R25_RECEIPT_BYTES, V3R26_V3R25_RECEIPT_SHA256, "v3r25_consumed_receipt"},
        {V3R25_CONSUMED_RUN_OUTCOME_PATH, V3R26_V3R25_RUN_OUTCOME_BYTES, V3R26_V3R25_RUN_OUTCOME_SHA256, "v3r25_consumed_run_outcome"},
        {V3R25_CONSUMED_POST_RUN_PATH, V3R26_V3R25_POST_RUN_BYTES, V3R26_V3R25_POST_RUN_SHA256, "v3r25_consumed_post_run_do_not_rerun"},
        {CPYTHON_CODE_HEADER_PATH, V3R26_CPYTHON_CODE_HEADER_BYTES, V3R26_CPYTHON_CODE_HEADER_SHA256, "cpython_code_header_future_annotations_definition"},
        {V3R24_CONSUMED_CONTRACT_PATH, V3R26_V3R24_CONTRACT_BYTES, V3R26_V3R24_CONTRACT_SHA256, "v3r24_consumed_contract"},
        {V3R24_CONSUMED_SOURCE_PATH, V3R26_V3R24_SOURCE_BYTES, V3R26_V3R24_SOURCE_SHA256, "v3r24_consumed_source"},
        {V3R24_CONSUMED_ANCHOR_PATH, V3R26_V3R24_ANCHOR_BYTES, V3R26_V3R24_ANCHOR_SHA256, "v3r24_consumed_anchor"},
        {V3R24_CONSUMED_OBJECT_PATH, V3R26_V3R24_OBJECT_BYTES, V3R26_V3R24_OBJECT_SHA256, "v3r24_consumed_object"},
        {V3R24_CONSUMED_EXECUTABLE_PATH, V3R26_V3R24_EXECUTABLE_BYTES, V3R26_V3R24_EXECUTABLE_SHA256, "v3r24_consumed_executable_do_not_rerun"},
        {V3R24_CONSUMED_TEST_PATH, V3R26_V3R24_TEST_BYTES, V3R26_V3R24_TEST_SHA256, "v3r24_consumed_test"},
        {V3R24_CONSUMED_CONTROL_PATH, V3R26_V3R24_CONTROL_BYTES, V3R26_V3R24_CONTROL_SHA256, "v3r24_consumed_control"},
        {V3R24_CONSUMED_BUILD_PATH, V3R26_V3R24_BUILD_BYTES, V3R26_V3R24_BUILD_SHA256, "v3r24_consumed_build"},
        {V3R24_CONSUMED_SEAL_PATH, V3R26_V3R24_SEAL_BYTES, V3R26_V3R24_SEAL_SHA256, "v3r24_consumed_seal"},
        {V3R24_CONSUMED_AUTHOR_CHECKPOINT_PATH, V3R26_V3R24_AUTHOR_CHECKPOINT_BYTES, V3R26_V3R24_AUTHOR_CHECKPOINT_SHA256, "v3r24_consumed_author_checkpoint"},
        {V3R24_CONSUMED_EVIDENCE_PATH, V3R26_V3R24_EVIDENCE_BYTES, V3R26_V3R24_EVIDENCE_SHA256, "v3r24_consumed_run_evidence"},
        {V3R24_CONSUMED_RECEIPT_PATH, V3R26_V3R24_RECEIPT_BYTES, V3R26_V3R24_RECEIPT_SHA256, "v3r24_consumed_receipt"},
        {V3R24_CONSUMED_AUDIT_PATH, V3R26_V3R24_AUDIT_BYTES, V3R26_V3R24_AUDIT_SHA256, "v3r24_consumed_audit"},
        {V3R24_CONSUMED_AUDIT_SIDECAR_PATH, V3R26_V3R24_AUDIT_SIDECAR_BYTES, V3R26_V3R24_AUDIT_SIDECAR_SHA256, "v3r24_consumed_audit_sidecar"},
        {V3R24_CONSUMED_AUDIT_DECISION_PATH, V3R26_V3R24_AUDIT_DECISION_BYTES, V3R26_V3R24_AUDIT_DECISION_SHA256, "v3r24_consumed_audit_decision"},
        {V3R24_CONSUMED_AUDIT_PROBES_PATH, V3R26_V3R24_AUDIT_PROBES_BYTES, V3R26_V3R24_AUDIT_PROBES_SHA256, "v3r24_consumed_audit_probes"},
        {V3R24_CONSUMED_AUDIT_CHECKPOINT_PATH, V3R26_V3R24_AUDIT_CHECKPOINT_BYTES, V3R26_V3R24_AUDIT_CHECKPOINT_SHA256, "v3r24_consumed_audit_checkpoint"},
        {V3R24_CONSUMED_RUN_OUTCOME_PATH, V3R26_V3R24_RUN_OUTCOME_BYTES, V3R26_V3R24_RUN_OUTCOME_SHA256, "v3r24_consumed_run_outcome"},
        {V3R24_CONSUMED_POST_RUN_PATH, V3R26_V3R24_POST_RUN_BYTES, V3R26_V3R24_POST_RUN_SHA256, "v3r24_consumed_post_run_do_not_rerun"},
        {V3R23_REJECTED_CONTRACT_PATH, V3R26_V3R23_CONTRACT_BYTES, V3R26_V3R23_CONTRACT_SHA256, "v3r23_rejected_contract"},
        {V3R23_REJECTED_SOURCE_PATH, V3R26_V3R23_SOURCE_BYTES, V3R26_V3R23_SOURCE_SHA256, "v3r23_rejected_source"},
        {V3R23_REJECTED_ANCHOR_PATH, V3R26_V3R23_ANCHOR_BYTES, V3R26_V3R23_ANCHOR_SHA256, "v3r23_rejected_anchor"},
        {V3R23_REJECTED_OBJECT_PATH, V3R26_V3R23_OBJECT_BYTES, V3R26_V3R23_OBJECT_SHA256, "v3r23_rejected_object"},
        {V3R23_REJECTED_EXECUTABLE_PATH, V3R26_V3R23_EXECUTABLE_BYTES, V3R26_V3R23_EXECUTABLE_SHA256, "v3r23_rejected_executable_do_not_run"},
        {V3R23_REJECTED_TEST_PATH, V3R26_V3R23_TEST_BYTES, V3R26_V3R23_TEST_SHA256, "v3r23_rejected_test"},
        {V3R23_REJECTED_CONTROL_PATH, V3R26_V3R23_CONTROL_BYTES, V3R26_V3R23_CONTROL_SHA256, "v3r23_rejected_control"},
        {V3R23_REJECTED_BUILD_PATH, V3R26_V3R23_BUILD_BYTES, V3R26_V3R23_BUILD_SHA256, "v3r23_rejected_build"},
        {V3R23_REJECTED_SEAL_PATH, V3R26_V3R23_SEAL_BYTES, V3R26_V3R23_SEAL_SHA256, "v3r23_rejected_seal"},
        {V3R23_REJECTED_CHECKPOINT_PATH, V3R26_V3R23_CHECKPOINT_BYTES, V3R26_V3R23_CHECKPOINT_SHA256, "v3r23_rejected_author_checkpoint"},
        {V3R23_REJECTION_AUDIT_PATH, V3R26_V3R23_REJECTION_AUDIT_BYTES, V3R26_V3R23_REJECTION_AUDIT_SHA256, "v3r23_rejection_audit"},
        {V3R23_REJECTION_SIDECAR_PATH, V3R26_V3R23_REJECTION_SIDECAR_BYTES, V3R26_V3R23_REJECTION_SIDECAR_SHA256, "v3r23_rejection_sidecar"},
        {V3R23_REJECTION_DECISION_PATH, V3R26_V3R23_REJECTION_DECISION_BYTES, V3R26_V3R23_REJECTION_DECISION_SHA256, "v3r23_rejection_decision"},
        {V3R23_REJECTION_PROBES_PATH, V3R26_V3R23_REJECTION_PROBES_BYTES, V3R26_V3R23_REJECTION_PROBES_SHA256, "v3r23_rejection_probes"},
        {V3R23_REJECTION_CHECKPOINT_PATH, V3R26_V3R23_REJECTION_CHECKPOINT_BYTES, V3R26_V3R23_REJECTION_CHECKPOINT_SHA256, "v3r23_rejection_checkpoint"},
        {V3R22_CONSUMED_CONTRACT_PATH, V3R26_V3R22_CONTRACT_BYTES, V3R26_V3R22_CONTRACT_SHA256, "v3r22_consumed_contract"},
        {V3R22_CONSUMED_SOURCE_PATH, V3R26_V3R22_SOURCE_BYTES, V3R26_V3R22_SOURCE_SHA256, "v3r22_consumed_source"},
        {V3R22_CONSUMED_ANCHOR_PATH, V3R26_V3R22_ANCHOR_BYTES, V3R26_V3R22_ANCHOR_SHA256, "v3r22_consumed_anchor"},
        {V3R22_CONSUMED_OBJECT_PATH, V3R26_V3R22_OBJECT_BYTES, V3R26_V3R22_OBJECT_SHA256, "v3r22_consumed_object"},
        {V3R22_CONSUMED_EXECUTABLE_PATH, V3R26_V3R22_EXECUTABLE_BYTES, V3R26_V3R22_EXECUTABLE_SHA256, "v3r22_consumed_executable_do_not_rerun"},
        {V3R22_CONSUMED_TEST_PATH, V3R26_V3R22_TEST_BYTES, V3R26_V3R22_TEST_SHA256, "v3r22_consumed_test"},
        {V3R22_CONSUMED_CONTROL_PATH, V3R26_V3R22_CONTROL_BYTES, V3R26_V3R22_CONTROL_SHA256, "v3r22_consumed_control"},
        {V3R22_CONSUMED_BUILD_PATH, V3R26_V3R22_BUILD_BYTES, V3R26_V3R22_BUILD_SHA256, "v3r22_consumed_build"},
        {V3R22_CONSUMED_SEAL_PATH, V3R26_V3R22_SEAL_BYTES, V3R26_V3R22_SEAL_SHA256, "v3r22_consumed_seal"},
        {V3R22_CONSUMED_CHECKPOINT_PATH, V3R26_V3R22_CHECKPOINT_BYTES, V3R26_V3R22_CHECKPOINT_SHA256, "v3r22_consumed_checkpoint"},
        {V3R22_CONSUMED_AUDIT_PATH, V3R26_V3R22_AUDIT_BYTES, V3R26_V3R22_AUDIT_SHA256, "v3r22_consumed_audit"},
        {V3R22_CONSUMED_AUDIT_SIDECAR_PATH, V3R26_V3R22_AUDIT_SIDECAR_BYTES, V3R26_V3R22_AUDIT_SIDECAR_SHA256, "v3r22_consumed_audit_sidecar"},
        {V3R22_CONSUMED_AUDIT_DECISION_PATH, V3R26_V3R22_AUDIT_DECISION_BYTES, V3R26_V3R22_AUDIT_DECISION_SHA256, "v3r22_consumed_audit_decision"},
        {V3R22_CONSUMED_AUDIT_PROBES_PATH, V3R26_V3R22_AUDIT_PROBES_BYTES, V3R26_V3R22_AUDIT_PROBES_SHA256, "v3r22_consumed_audit_probes"},
        {V3R22_CONSUMED_AUDIT_CHECKPOINT_PATH, V3R26_V3R22_AUDIT_CHECKPOINT_BYTES, V3R26_V3R22_AUDIT_CHECKPOINT_SHA256, "v3r22_consumed_audit_checkpoint"},
        {V3R22_CONSUMED_EVIDENCE_PATH, V3R26_V3R22_EVIDENCE_BYTES, V3R26_V3R22_EVIDENCE_SHA256, "v3r22_consumed_failure_evidence"},
        {V3R22_CONSUMED_RECEIPT_PATH, V3R26_V3R22_RECEIPT_BYTES, V3R26_V3R22_RECEIPT_SHA256, "v3r22_consumed_failure_receipt"},
        {V3R22_CONSUMED_RUN_OUTCOME_PATH, V3R26_V3R22_RUN_OUTCOME_BYTES, V3R26_V3R22_RUN_OUTCOME_SHA256, "v3r22_consumed_run_outcome"},
        {V3R22_CONSUMED_POSTMORTEM_RECHECK_PATH, V3R26_V3R22_POSTMORTEM_RECHECK_BYTES, V3R26_V3R22_POSTMORTEM_RECHECK_SHA256, "v3r22_consumed_postmortem_recheck"},
        {V3R22_CONSUMED_POSTMORTEM_CHECKPOINT_PATH, V3R26_V3R22_POSTMORTEM_CHECKPOINT_BYTES, V3R26_V3R22_POSTMORTEM_CHECKPOINT_SHA256, "v3r22_consumed_postmortem_checkpoint_do_not_rerun"},
        {V3R14_EVIDENCE_PATH, V3R22_V3R14_EVIDENCE_BYTES, V3R22_V3R14_EVIDENCE_SHA256, "v3r14_evidence"},
        {V3R14_RECEIPT_PATH, V3R22_V3R14_RECEIPT_BYTES, V3R22_V3R14_RECEIPT_SHA256, "v3r14_receipt"},
        {V3R14_AUDIT_CHECKPOINT_PATH, V3R22_V3R14_AUDIT_BYTES, V3R22_V3R14_AUDIT_SHA256, "v3r14_audit"},
        {V3R14_POSTMORTEM_PATH, V3R22_V3R14_POSTMORTEM_BYTES, V3R22_V3R14_POSTMORTEM_SHA256, "v3r14_postmortem"},
        {V3R17_CHECKPOINT_PATH, V3R22_V3R17_CHECKPOINT_BYTES, V3R22_V3R17_CHECKPOINT_SHA256, "v3r17_checkpoint"},
        {V3R17_SEAL_PATH, V3R22_V3R17_SEAL_BYTES, V3R22_V3R17_SEAL_SHA256, "v3r17_seal"},
        {V3R17_RUN_EVIDENCE_PATH, V3R22_V3R17_RUN_EVIDENCE_BYTES, V3R22_V3R17_RUN_EVIDENCE_SHA256, "v3r17_run_evidence"},
        {V3R17_RECEIPT_PATH, V3R22_V3R17_RECEIPT_BYTES, V3R22_V3R17_RECEIPT_SHA256, "v3r17_receipt"},
        {V3R17_AUDIT_CHECKPOINT_PATH, V3R22_V3R17_AUDIT_CHECKPOINT_BYTES, V3R22_V3R17_AUDIT_CHECKPOINT_SHA256, "v3r17_audit_checkpoint"},
        {V3R17_RUN_OUTCOME_PATH, V3R22_V3R17_RUN_OUTCOME_BYTES, V3R22_V3R17_RUN_OUTCOME_SHA256, "v3r17_run_outcome"},
        {V3R17_POST_RUN_PATH, V3R22_V3R17_POST_RUN_BYTES, V3R22_V3R17_POST_RUN_SHA256, "v3r17_post_run"},
        {V3R18_CONTRACT_PATH, V3R22_V3R18_CONTRACT_BYTES, V3R22_V3R18_CONTRACT_SHA256, "v3r18_contract"},
        {V3R18_SOURCE_PATH, V3R22_V3R18_SOURCE_BYTES, V3R22_V3R18_SOURCE_SHA256, "v3r18_source"},
        {V3R18_ANCHOR_PATH, V3R22_V3R18_ANCHOR_BYTES, V3R22_V3R18_ANCHOR_SHA256, "v3r18_anchor"},
        {V3R18_OBJECT_PATH, V3R22_V3R18_OBJECT_BYTES, V3R22_V3R18_OBJECT_SHA256, "v3r18_object"},
        {V3R18_EXECUTABLE_PATH, V3R22_V3R18_EXECUTABLE_BYTES, V3R22_V3R18_EXECUTABLE_SHA256, "v3r18_executable"},
        {V3R18_TEST_PATH, V3R22_V3R18_TEST_BYTES, V3R22_V3R18_TEST_SHA256, "v3r18_test"},
        {V3R18_CONTROL_PATH, V3R22_V3R18_CONTROL_BYTES, V3R22_V3R18_CONTROL_SHA256, "v3r18_control"},
        {V3R18_BUILD_PATH, V3R22_V3R18_BUILD_BYTES, V3R22_V3R18_BUILD_SHA256, "v3r18_build"},
        {V3R18_SEAL_PATH, V3R22_V3R18_SEAL_BYTES, V3R22_V3R18_SEAL_SHA256, "v3r18_seal"},
        {V3R18_CHECKPOINT_PATH, V3R22_V3R18_CHECKPOINT_BYTES, V3R22_V3R18_CHECKPOINT_SHA256, "v3r18_checkpoint"},
        {V3R18_REJECTION_AUDIT_PATH, V3R22_V3R18_REJECTION_AUDIT_BYTES, V3R22_V3R18_REJECTION_AUDIT_SHA256, "v3r18_rejection_audit"},
        {V3R18_REJECTION_SIDECAR_PATH, V3R22_V3R18_REJECTION_SIDECAR_BYTES, V3R22_V3R18_REJECTION_SIDECAR_SHA256, "v3r18_rejection_sidecar"},
        {V3R18_REJECTION_PROBES_PATH, V3R22_V3R18_REJECTION_PROBES_BYTES, V3R22_V3R18_REJECTION_PROBES_SHA256, "v3r18_rejection_probes"},
        {V3R18_REJECTION_CHECKPOINT_PATH, V3R22_V3R18_REJECTION_CHECKPOINT_BYTES, V3R22_V3R18_REJECTION_CHECKPOINT_SHA256, "v3r18_rejection_checkpoint"},
        {V3R19_CONTRACT_PATH, V3R22_V3R19_CONTRACT_BYTES, V3R22_V3R19_CONTRACT_SHA256, "v3r19_contract"},
        {V3R19_SOURCE_PATH, V3R22_V3R19_SOURCE_BYTES, V3R22_V3R19_SOURCE_SHA256, "v3r19_source"},
        {V3R19_ANCHOR_PATH, V3R22_V3R19_ANCHOR_BYTES, V3R22_V3R19_ANCHOR_SHA256, "v3r19_anchor"},
        {V3R19_OBJECT_PATH, V3R22_V3R19_OBJECT_BYTES, V3R22_V3R19_OBJECT_SHA256, "v3r19_object"},
        {V3R19_EXECUTABLE_PATH, V3R22_V3R19_EXECUTABLE_BYTES, V3R22_V3R19_EXECUTABLE_SHA256, "v3r19_executable"},
        {V3R19_TEST_PATH, V3R22_V3R19_TEST_BYTES, V3R22_V3R19_TEST_SHA256, "v3r19_test"},
        {V3R19_CONTROL_PATH, V3R22_V3R19_CONTROL_BYTES, V3R22_V3R19_CONTROL_SHA256, "v3r19_control"},
        {V3R19_BUILD_PATH, V3R22_V3R19_BUILD_BYTES, V3R22_V3R19_BUILD_SHA256, "v3r19_build"},
        {V3R19_SEAL_PATH, V3R22_V3R19_SEAL_BYTES, V3R22_V3R19_SEAL_SHA256, "v3r19_seal"},
        {V3R19_CHECKPOINT_PATH, V3R22_V3R19_CHECKPOINT_BYTES, V3R22_V3R19_CHECKPOINT_SHA256, "v3r19_checkpoint"},
        {V3R19_ACCEPT_AUDIT_PATH, V3R22_V3R19_ACCEPT_AUDIT_BYTES, V3R22_V3R19_ACCEPT_AUDIT_SHA256, "v3r19_accept_audit"},
        {V3R19_ACCEPT_SIDECAR_PATH, V3R22_V3R19_ACCEPT_SIDECAR_BYTES, V3R22_V3R19_ACCEPT_SIDECAR_SHA256, "v3r19_accept_sidecar"},
        {V3R19_ACCEPT_CHECKPOINT_PATH, V3R22_V3R19_ACCEPT_CHECKPOINT_BYTES, V3R22_V3R19_ACCEPT_CHECKPOINT_SHA256, "v3r19_accept_checkpoint"},
        {V3R19_FAILURE_RECHECK_PATH, V3R22_V3R19_FAILURE_RECHECK_BYTES, V3R22_V3R19_FAILURE_RECHECK_SHA256, "v3r19_failure_recheck"},
        {V3R19_FAILURE_CHECKPOINT_PATH, V3R22_V3R19_FAILURE_CHECKPOINT_BYTES, V3R22_V3R19_FAILURE_CHECKPOINT_SHA256, "v3r19_failure_checkpoint"},
        {V3R20_CONTRACT_PATH, V3R22_V3R20_CONTRACT_BYTES, V3R22_V3R20_CONTRACT_SHA256, "v3r20_contract"},
        {V3R20_SOURCE_PATH, V3R22_V3R20_SOURCE_BYTES, V3R22_V3R20_SOURCE_SHA256, "v3r20_source"},
        {V3R20_ANCHOR_PATH, V3R22_V3R20_ANCHOR_BYTES, V3R22_V3R20_ANCHOR_SHA256, "v3r20_anchor"},
        {V3R20_OBJECT_PATH, V3R22_V3R20_OBJECT_BYTES, V3R22_V3R20_OBJECT_SHA256, "v3r20_object"},
        {V3R20_EXECUTABLE_PATH, V3R22_V3R20_EXECUTABLE_BYTES, V3R22_V3R20_EXECUTABLE_SHA256, "v3r20_executable"},
        {V3R20_TEST_PATH, V3R22_V3R20_TEST_BYTES, V3R22_V3R20_TEST_SHA256, "v3r20_test"},
        {V3R20_CONTROL_PATH, V3R22_V3R20_CONTROL_BYTES, V3R22_V3R20_CONTROL_SHA256, "v3r20_control"},
        {V3R20_BUILD_PATH, V3R22_V3R20_BUILD_BYTES, V3R22_V3R20_BUILD_SHA256, "v3r20_build"},
        {V3R20_SEAL_PATH, V3R22_V3R20_SEAL_BYTES, V3R22_V3R20_SEAL_SHA256, "v3r20_seal"},
        {V3R20_CHECKPOINT_PATH, V3R22_V3R20_CHECKPOINT_BYTES, V3R22_V3R20_CHECKPOINT_SHA256, "v3r20_checkpoint"},
        {V3R20_REJECTION_AUDIT_PATH, V3R22_V3R20_REJECTION_AUDIT_BYTES, V3R22_V3R20_REJECTION_AUDIT_SHA256, "v3r20_rejection_audit"},
        {V3R20_REJECTION_SIDECAR_PATH, V3R22_V3R20_REJECTION_SIDECAR_BYTES, V3R22_V3R20_REJECTION_SIDECAR_SHA256, "v3r20_rejection_sidecar"},
        {V3R20_REJECTION_DECISION_PATH, V3R22_V3R20_REJECTION_DECISION_BYTES, V3R22_V3R20_REJECTION_DECISION_SHA256, "v3r20_rejection_decision"},
        {V3R20_REJECTION_ANALYZE_PATH, V3R22_V3R20_REJECTION_ANALYZE_BYTES, V3R22_V3R20_REJECTION_ANALYZE_SHA256, "v3r20_rejection_analyze"},
        {V3R20_REJECTION_CHECKPOINT_PATH, V3R22_V3R20_REJECTION_CHECKPOINT_BYTES, V3R22_V3R20_REJECTION_CHECKPOINT_SHA256, "v3r20_rejection_checkpoint"},
        {V3R21_CONTRACT_PATH, V3R22_V3R21_CONTRACT_BYTES, V3R22_V3R21_CONTRACT_SHA256, "v3r21_contract"},
        {V3R21_SOURCE_PATH, V3R22_V3R21_SOURCE_BYTES, V3R22_V3R21_SOURCE_SHA256, "v3r21_source"},
        {V3R21_ANCHOR_PATH, V3R22_V3R21_ANCHOR_BYTES, V3R22_V3R21_ANCHOR_SHA256, "v3r21_anchor"},
        {V3R21_OBJECT_PATH, V3R22_V3R21_OBJECT_BYTES, V3R22_V3R21_OBJECT_SHA256, "v3r21_object"},
        {V3R21_EXECUTABLE_PATH, V3R22_V3R21_EXECUTABLE_BYTES, V3R22_V3R21_EXECUTABLE_SHA256, "v3r21_executable_consumed"},
        {V3R21_TEST_PATH, V3R22_V3R21_TEST_BYTES, V3R22_V3R21_TEST_SHA256, "v3r21_test"},
        {V3R21_CONTROL_PATH, V3R22_V3R21_CONTROL_BYTES, V3R22_V3R21_CONTROL_SHA256, "v3r21_control"},
        {V3R21_BUILD_PATH, V3R22_V3R21_BUILD_BYTES, V3R22_V3R21_BUILD_SHA256, "v3r21_build"},
        {V3R21_SEAL_PATH, V3R22_V3R21_SEAL_BYTES, V3R22_V3R21_SEAL_SHA256, "v3r21_seal"},
        {V3R21_CHECKPOINT_PATH, V3R22_V3R21_CHECKPOINT_BYTES, V3R22_V3R21_CHECKPOINT_SHA256, "v3r21_checkpoint"},
        {V3R21_AUDIT_PATH, V3R22_V3R21_AUDIT_BYTES, V3R22_V3R21_AUDIT_SHA256, "v3r21_accept_audit"},
        {V3R21_AUDIT_SIDECAR_PATH, V3R22_V3R21_AUDIT_SIDECAR_BYTES, V3R22_V3R21_AUDIT_SIDECAR_SHA256, "v3r21_accept_sidecar"},
        {V3R21_AUDIT_DECISION_PATH, V3R22_V3R21_AUDIT_DECISION_BYTES, V3R22_V3R21_AUDIT_DECISION_SHA256, "v3r21_accept_decision"},
        {V3R21_AUDIT_PROBES_PATH, V3R22_V3R21_AUDIT_PROBES_BYTES, V3R22_V3R21_AUDIT_PROBES_SHA256, "v3r21_accept_probes"},
        {V3R21_AUDIT_CHECKPOINT_PATH, V3R22_V3R21_AUDIT_CHECKPOINT_BYTES, V3R22_V3R21_AUDIT_CHECKPOINT_SHA256, "v3r21_accept_checkpoint"},
        {V3R21_RUN_EVIDENCE_PATH, V3R22_V3R21_RUN_EVIDENCE_BYTES, V3R22_V3R21_RUN_EVIDENCE_SHA256, "v3r21_run_evidence_consumed"},
        {V3R21_RECEIPT_PATH, V3R22_V3R21_RECEIPT_BYTES, V3R22_V3R21_RECEIPT_SHA256, "v3r21_receipt_consumed"},
        {V3R21_RUN_OUTCOME_PATH, V3R22_V3R21_RUN_OUTCOME_BYTES, V3R22_V3R21_RUN_OUTCOME_SHA256, "v3r21_run_outcome"},
        {V3R21_POST_RUN_PATH, V3R22_V3R21_POST_RUN_BYTES, V3R22_V3R21_POST_RUN_SHA256, "v3r21_post_run_do_not_rerun"},
        {V3R9_LAUNCHER_SOURCE_PATH, V3R22_V3R9_LAUNCHER_SOURCE_BYTES, V3R22_V3R9_LAUNCHER_SOURCE_SHA256, "v3r9_launcher_source_consumed"},
        {V3R9_LAUNCHER_EXE_PATH, V3R22_V3R9_LAUNCHER_EXE_BYTES, V3R22_V3R9_LAUNCHER_EXE_SHA256, "v3r9_launcher_consumed"},
        {V3R9_TEST_PATH, V3R22_V3R9_TEST_BYTES, V3R22_V3R9_TEST_SHA256, "v3r9_test"},
        {V3R9_BOOTSTRAP_PATH, V3R22_V3R9_BOOTSTRAP_BYTES, V3R22_V3R9_BOOTSTRAP_SHA256, "v3r9_bootstrap_consumed"},
        {V3R9_WRAPPER_PATH, V3R22_V3R9_WRAPPER_BYTES, V3R22_V3R9_WRAPPER_SHA256, "v3r9_wrapper_consumed"},
        {V3R9_POSTMORTEM_PATH, V3R22_V3R9_POSTMORTEM_BYTES, V3R22_V3R9_POSTMORTEM_SHA256, "v3r9_postmortem_do_not_retry"},
        {V3R9_COMMAND_PATH, V3R22_V3R9_COMMAND_BYTES, V3R22_V3R9_COMMAND_SHA256, "v3r9_consumed_command"},
        {V3R9_TRANSCRIPT_PATH, V3R22_V3R9_TRANSCRIPT_BYTES, V3R22_V3R9_TRANSCRIPT_SHA256, "v3r9_raw_tool_transcript"},
        {V3R10_CONTRACT_HISTORY_PATH, V3R22_V3R10_HISTORY_CONTRACT_BYTES, V3R22_V3R10_HISTORY_CONTRACT_SHA256, "v3r10_rejected_contract"},
        {V3R10_SOURCE_HISTORY_PATH, V3R22_V3R10_HISTORY_SOURCE_BYTES, V3R22_V3R10_HISTORY_SOURCE_SHA256, "v3r10_rejected_source"},
        {V3R10_OBJECT_HISTORY_PATH, V3R22_V3R10_HISTORY_OBJECT_BYTES, V3R22_V3R10_HISTORY_OBJECT_SHA256, "v3r10_rejected_object"},
        {V3R10_EXE_HISTORY_PATH, V3R22_V3R10_HISTORY_EXE_BYTES, V3R22_V3R10_HISTORY_EXE_SHA256, "v3r10_rejected_executable"},
        {V3R10_TEST_HISTORY_PATH, V3R22_V3R10_HISTORY_TEST_BYTES, V3R22_V3R10_HISTORY_TEST_SHA256, "v3r10_rejected_test"},
        {V3R10_AUTHOR_CHECKPOINT_PATH, V3R22_V3R10_AUTHOR_CHECKPOINT_BYTES, V3R22_V3R10_AUTHOR_CHECKPOINT_SHA256, "v3r10_author_checkpoint"},
        {V3R10_AUDIT_SCRIPT_PATH, V3R22_V3R10_AUDIT_SCRIPT_BYTES, V3R22_V3R10_AUDIT_SCRIPT_SHA256, "v3r10_rejection_audit_script"},
        {V3R10_PROBES_PATH, V3R22_V3R10_PROBES_BYTES, V3R22_V3R10_PROBES_SHA256, "v3r10_rejection_probes"},
        {V3R10_REJECTION_CHECKPOINT_PATH, V3R22_V3R10_REJECTION_CHECKPOINT_BYTES, V3R22_V3R10_REJECTION_CHECKPOINT_SHA256, "v3r10_rejection_checkpoint"},
        {V3R10_AUDIT_OBJECT_PATH, V3R22_V3R10_AUDIT_OBJECT_BYTES, V3R22_V3R10_AUDIT_OBJECT_SHA256, "v3r10_audit_rebuild_object"},
        {V3R10_AUDIT_EXE_PATH, V3R22_V3R10_AUDIT_EXE_BYTES, V3R22_V3R10_AUDIT_EXE_SHA256, "v3r10_audit_rebuild_executable"},
        {V3R11_CONTRACT_HISTORY_PATH, V3R22_V3R11_CONTRACT_BYTES, V3R22_V3R11_CONTRACT_SHA256, "v3r11_incomplete_contract"},
        {V3R11_SOURCE_HISTORY_PATH, V3R22_V3R11_SOURCE_BYTES, V3R22_V3R11_SOURCE_SHA256, "v3r11_incomplete_source"},
        {V3R11_CONTROL_HISTORY_PATH, V3R22_V3R11_CONTROL_BYTES, V3R22_V3R11_CONTROL_SHA256, "v3r11_incomplete_control"},
        {V3R11_BLOCKER_PATH, V3R22_V3R11_BLOCKER_BYTES, V3R22_V3R11_BLOCKER_SHA256, "v3r11_blocker_no_execution"}
    };
    LockedFile manifest_file = {
        MANIFEST_PATH, V3R22_MANIFEST_BYTES, V3R22_MANIFEST_SHA256,
        INVALID_HANDLE_VALUE, {0}
    };
    LockedFile v3r9_audit = {
        V3R9_AUDIT_PATH, V3R22_V3R9_AUDIT_BYTES, V3R22_V3R9_AUDIT_SHA256,
        INVALID_HANDLE_VALUE, {0}
    };
    LockedFile authority_contract = {
        CONTRACT_PATH, V3R22_CONTRACT_BYTES, V3R22_CONTRACT_SHA256,
        INVALID_HANDLE_VALUE, {0}
    };
    unsigned char *manifest = NULL;
    DWORD manifest_bytes = 0U;
    ManifestRowV3R22 *manifest_rows = NULL;
    ManifestRowV3R22 *python_row = NULL;
    ManifestRowV3R22 *stdlib_row = NULL;
    ManifestRowV3R22 *controller_row = NULL;
    ManifestRowV3R22 *execution_contract_row = NULL;
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
    ValidatorTelemetry validator_telemetry;
    FILE_ID_INFO contract_identity;
    size_t index;
    uint32_t terminal_stage = 1U;
    int stage_ok = 0;
    int python_attempted = 0;
    int python_ok = 0;
    int retained_recheck_ok = 0;
    int python_evidence_ok = 1;
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
    SecureZeroMemory(&validator_telemetry, sizeof(validator_telemetry));
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
            fwprintf(stderr, L"V3R26_SUBJECT_REFUSED:%S\n", fixed[index].label);
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
        manifest_rows = (ManifestRowV3R22 *)HeapAlloc(GetProcessHeap(),
            HEAP_ZERO_MEMORY, sizeof(*manifest_rows) * RETAINED_ROW_COUNT);
        if (manifest_rows == NULL || !lock_file(&manifest_file) ||
            !read_locked(&manifest_file, MANIFEST_LIMIT, &manifest, &manifest_bytes) ||
            !parse_and_lock_manifest_rows(manifest, manifest_bytes, manifest_rows) ||
            !lock_file(&v3r9_audit)) stage_ok = 0;
    }
    if (stage_ok) {
        python_row = find_manifest_row(manifest_rows, "python_runtime_dll");
        stdlib_row = find_manifest_row(manifest_rows, "retained_stdlib_zip");
        controller_row = find_manifest_row(manifest_rows, "parent_controller");
        execution_contract_row = find_manifest_row(manifest_rows, "execution_contract");
        stage_ok = manifest_row_exact(python_row, "C:/Python314/python314.dll",
                V3R22_PYTHON_DLL_BYTES, V3R22_PYTHON_DLL_SHA256) &&
            manifest_row_exact(stdlib_row, "tools/native/runtime/python314_stdlib_v3r4.zip",
                V3R22_STDLIB_ZIP_BYTES, V3R22_STDLIB_ZIP_SHA256) &&
            manifest_row_exact(controller_row,
                "tools/run_kira_r25_foundation_afes_locked_pair_v3r9.py",
                V3R22_CONTROLLER_BYTES, V3R22_CONTROLLER_SHA256) &&
            manifest_row_exact(execution_contract_row,
                "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v3r9.json",
                V3R22_EXECUTION_CONTRACT_BYTES, V3R22_EXECUTION_CONTRACT_SHA256);
        terminal_stage = 30U;
    }
    if (stage_ok) {
        python_attempted = 1;
        python_ok = run_python_validation(&python_row->locked, &stdlib_row->locked,
            &controller_row->locked, &execution_contract_row->locked, &v3r9_audit,
            manifest_rows, &unload_telemetry, &validator_telemetry, &terminal_stage);
    }
    if (python_attempted) {
        if (python_ok) terminal_stage = 70U;
        retained_recheck_ok = recheck_manifest_rows(manifest_rows) &&
            verify_handle_bound(manifest_file.handle, manifest_file.path,
                manifest_file.expected_bytes, manifest_file.expected_sha256,
                &manifest_file.identity) &&
            verify_handle_bound(v3r9_audit.handle, v3r9_audit.path,
                v3r9_audit.expected_bytes, v3r9_audit.expected_sha256,
                &v3r9_audit.identity) &&
            verify_handle_bound(authority_contract.handle, authority_contract.path,
                authority_contract.expected_bytes, authority_contract.expected_sha256,
                &authority_contract.identity);
        for (index = 0U; index < _countof(fixed); ++index) {
            if (!hash_path_exact(fixed[index].path, fixed[index].bytes,
                    fixed[index].sha256, NULL)) retained_recheck_ok = 0;
        }
        validator_telemetry.retained_recheck_passed = retained_recheck_ok ? 1U : 0U;
        if (python_ok)
            python_evidence_ok = append_line(evidence, E_PYTHON) &&
                append_line(evidence, E_CONTROLLER) && append_line(evidence, E_PLAN);
        if (unload_telemetry.finalize_called == 1U &&
            unload_telemetry.finalize_result >= 0 &&
            unload_telemetry.free_library_called == 1U &&
            unload_telemetry.free_library_result == 1U &&
            unload_telemetry.snapshot_succeeded == 1U &&
            unload_telemetry.snapshot_error == ERROR_SUCCESS &&
            unload_telemetry.old_base_present == 0U &&
            unload_telemetry.exact_path_present == 0U && retained_recheck_ok)
            python_evidence_ok = append_line(evidence, E_FINALIZED) && python_evidence_ok;
        python_evidence_ok = append_validator_telemetry(evidence, &validator_telemetry) &&
            append_unload_telemetry(evidence, &unload_telemetry) && python_evidence_ok;
        stage_ok = python_ok && retained_recheck_ok && python_evidence_ok;
        if (stage_ok) terminal_stage = 80U;
    }
    if (contract_handle != INVALID_HANDLE_VALUE) {
        if (!finish_contract_granular(&contract_telemetry, &contract_handle,
                &contract_identity)) stage_ok = 0;
    } else {
        stage_ok = 0;
    }
    if (!append_contract_telemetry(evidence, &contract_telemetry)) stage_ok = 0;
    if (stage_ok) terminal_stage = 90U;
    if (receipt != INVALID_HANDLE_VALUE) {
        outcome_ok = finish_outcome(receipt, &receipt_identity, &evidence_identity,
            &reservation, self_sha, audit_sha, &contract_telemetry,
            &unload_telemetry, &validator_telemetry,
            stage_ok ? RECORD_SUCCESS : RECORD_FAILURE, terminal_stage);
    }
    if (stage_ok && outcome_ok && append_line(evidence, E_SUCCESS)) result = 0;
    else if (evidence != INVALID_HANDLE_VALUE) (void)append_line(evidence, E_FAILURE);
cleanup:
    if (manifest != NULL) {
        SecureZeroMemory(manifest, (SIZE_T)manifest_bytes + 1U);
        HeapFree(GetProcessHeap(), 0U, manifest);
    }
    if (manifest_rows != NULL) {
        release_manifest_rows(manifest_rows);
        HeapFree(GetProcessHeap(), 0U, manifest_rows);
    }
    SecureZeroMemory(&reservation, sizeof(reservation));
    SecureZeroMemory(self_sha, sizeof(self_sha));
    SecureZeroMemory(audit_sha, sizeof(audit_sha));
    if (valid_handle(receipt)) CloseHandle(receipt);
    if (evidence != NULL && evidence != INVALID_HANDLE_VALUE) CloseHandle(evidence);
    if (valid_handle(contract_handle)) CloseHandle(contract_handle);
    if (valid_handle(authority_contract.handle)) CloseHandle(authority_contract.handle);
    if (valid_handle(manifest_file.handle)) CloseHandle(manifest_file.handle);
    if (valid_handle(v3r9_audit.handle)) CloseHandle(v3r9_audit.handle);
    return result;
}
