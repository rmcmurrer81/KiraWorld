#!/usr/bin/env python3
"""Static V4 successor for the consumed long Kira evaluation.

V4 preserves the complete sealed V3 conversation/model/voice/state contract
and changes only the Windows process-name inventory used by the heavy-workload
preflight. The failed ``tasklist`` command is replaced by a strict read-only
Toolhelp32 snapshot. This file is inert unless all retained live capabilities
are present and a different fresh audit accepts its exact sealed bytes.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v3 as v3
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


V4_PLAN_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v4"
    / "attempt_01"
    / "EXECUTION_PLAN_V4.json"
)
V4_PLAN_SHA256 = "2a56e114b034896106e2754abe054bc2f8db59244fdf4c9de6d43554eec6aeb0"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v4"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v4"
)
HARNESS_ID = "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v4"
ONLY_ATTEMPT_LABEL = "attempt_01"

V3_ATTEMPT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v3"
    / "attempt_01"
)
V3_GENERATED = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v3"
    / "attempt_01"
)

PROCESS_INVENTORY_METHOD = "win32_toolhelp32_exact_executable_names"
TH32CS_SNAPPROCESS = 0x00000002
ERROR_NO_MORE_FILES = 18
MAX_PATH = 260
PROHIBITED_PROCESS_NAMES = frozenset(
    {"blender.exe", "blender-launcher.exe", "ffmpeg.exe"}
)
PROCESS_INVENTORY_KEYS = frozenset(
    {
        "schema_version",
        "method",
        "succeeded",
        "snapshot_created",
        "first_entry_succeeded",
        "terminal_no_more_files",
        "snapshot_closed",
        "process_names",
        "process_count",
        "error_type",
        "win32_error",
        "arbitrary_process_handle_opened",
    }
)
V4_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "predecessor",
        "retained_v3_contract",
        "process_inventory_repair",
        "execution_roots",
    }
)


class LongEvaluationV4Error(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LongEvaluationV4Error(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def _project_file(relative: str, expected_sha256: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise LongEvaluationV4Error("bound path escaped project root") from exc
    if not path.is_file() or _sha256_file(path) != expected_sha256:
        raise LongEvaluationV4Error(f"bound predecessor drifted:{relative}")
    return path


def _blank_inventory() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "method": PROCESS_INVENTORY_METHOD,
        "succeeded": False,
        "snapshot_created": False,
        "first_entry_succeeded": False,
        "terminal_no_more_files": False,
        "snapshot_closed": False,
        "process_names": [],
        "process_count": 0,
        "error_type": "",
        "win32_error": 0,
        "arbitrary_process_handle_opened": False,
    }


def win32_toolhelp32_process_inventory() -> dict[str, Any]:
    """Enumerate executable names using one read-only Toolhelp32 snapshot."""

    result = _blank_inventory()
    if os.name != "nt":
        result["error_type"] = "non_windows_platform"
        return result

    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * MAX_PATH),
        ]

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel32.Process32FirstW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESSENTRY32W),
        ]
        kernel32.Process32FirstW.restype = wintypes.BOOL
        kernel32.Process32NextW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESSENTRY32W),
        ]
        kernel32.Process32NextW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
    except (AttributeError, OSError) as exc:
        result["error_type"] = f"kernel32_setup:{type(exc).__name__}"
        result["win32_error"] = int(ctypes.get_last_error() or 0)
        return result

    handle: Any = None
    names: list[str] = []
    try:
        ctypes.set_last_error(0)
        handle = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        invalid_handle = ctypes.c_void_p(-1).value
        if handle in (None, invalid_handle):
            result["error_type"] = "CreateToolhelp32Snapshot"
            result["win32_error"] = int(ctypes.get_last_error() or 0)
            return result
        result["snapshot_created"] = True

        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ctypes.set_last_error(0)
        if not kernel32.Process32FirstW(handle, ctypes.byref(entry)):
            result["error_type"] = "Process32FirstW"
            result["win32_error"] = int(ctypes.get_last_error() or 0)
            return result
        result["first_entry_succeeded"] = True

        while True:
            name = str(entry.szExeFile or "").strip().casefold()
            if not name:
                result["error_type"] = "empty_process_name"
                return result
            names.append(name)
            ctypes.set_last_error(0)
            if kernel32.Process32NextW(handle, ctypes.byref(entry)):
                continue
            terminal_error = int(ctypes.get_last_error() or 0)
            if terminal_error != ERROR_NO_MORE_FILES:
                result["error_type"] = "Process32NextW"
                result["win32_error"] = terminal_error
                return result
            result["terminal_no_more_files"] = True
            break
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        result["error_type"] = f"enumeration_exception:{type(exc).__name__}"
        result["win32_error"] = int(ctypes.get_last_error() or 0)
    finally:
        if result["snapshot_created"]:
            try:
                ctypes.set_last_error(0)
                result["snapshot_closed"] = bool(kernel32.CloseHandle(handle))
                if not result["snapshot_closed"] and not result["error_type"]:
                    result["error_type"] = "CloseHandle"
                    result["win32_error"] = int(ctypes.get_last_error() or 0)
            except (AttributeError, OSError, TypeError, ValueError) as exc:
                result["snapshot_closed"] = False
                if not result["error_type"]:
                    result["error_type"] = f"close_exception:{type(exc).__name__}"
                    result["win32_error"] = int(ctypes.get_last_error() or 0)

    normalized = sorted(set(names))
    result["process_names"] = normalized
    result["process_count"] = len(normalized)
    result["succeeded"] = bool(
        result["snapshot_created"]
        and result["first_entry_succeeded"]
        and result["terminal_no_more_files"]
        and result["snapshot_closed"]
        and normalized
        and not result["error_type"]
        and result["win32_error"] == 0
    )
    return result


def process_inventory_contract_issues(value: Mapping[str, Any] | Any) -> list[str]:
    if not isinstance(value, Mapping):
        return ["process_inventory_not_mapping"]
    issues: list[str] = []
    if set(value) != set(PROCESS_INVENTORY_KEYS):
        issues.append("process_inventory_keys_drifted")
    if value.get("schema_version") != 1:
        issues.append("process_inventory_schema_drifted")
    if value.get("method") != PROCESS_INVENTORY_METHOD:
        issues.append("process_inventory_method_drifted")
    if value.get("succeeded") is not True:
        issues.append("process_inventory_not_succeeded")
    for key in (
        "snapshot_created",
        "first_entry_succeeded",
        "terminal_no_more_files",
        "snapshot_closed",
    ):
        if value.get(key) is not True:
            issues.append(f"process_inventory_not_proven:{key}")
    if value.get("arbitrary_process_handle_opened") is not False:
        issues.append("process_inventory_opened_arbitrary_process_handle")
    if value.get("error_type") != "" or value.get("win32_error") != 0:
        issues.append("process_inventory_error_present")

    names = value.get("process_names")
    if not isinstance(names, list) or not names:
        issues.append("process_inventory_names_missing")
        names = []
    valid_names = bool(
        names
        and all(
            isinstance(name, str)
            and name
            and name == name.strip().casefold()
            and "/" not in name
            and "\\" not in name
            for name in names
        )
    )
    if not valid_names:
        issues.append("process_inventory_names_not_normalized")
    if names != sorted(set(names)):
        issues.append("process_inventory_names_not_sorted_unique")
    count = value.get("process_count")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(names):
        issues.append("process_inventory_count_mismatch")
    return sorted(set(issues))


def heavy_workload_preflight_v4(
    *,
    inventory_provider: Callable[[], Mapping[str, Any]] = win32_toolhelp32_process_inventory,
    gpu_provider: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fail closed on inventory errors, prohibited names, or high GPU use."""

    if gpu_provider is None:
        gpu_provider = retained.base.v2._nvidia_snapshot
    try:
        inventory = dict(inventory_provider())
        inventory_exception = ""
    except BaseException as exc:
        inventory = _blank_inventory()
        inventory["error_type"] = f"provider_exception:{type(exc).__name__}"
        inventory_exception = type(exc).__name__
    inventory_issues = process_inventory_contract_issues(inventory)
    names = inventory.get("process_names") if not inventory_issues else []
    names = names if isinstance(names, list) else []
    prohibited = sorted(set(names) & set(PROHIBITED_PROCESS_NAMES))

    try:
        gpu = dict(gpu_provider())
        gpu_exception = ""
    except BaseException as exc:
        gpu = {"query_succeeded": False, "rows": []}
        gpu_exception = type(exc).__name__
    rows = gpu.get("rows") if isinstance(gpu.get("rows"), list) else []
    high_gpu_rows = [
        row
        for row in rows
        if isinstance(row, Mapping)
        and isinstance(row.get("utilization_percent"), (int, float))
        and not isinstance(row.get("utilization_percent"), bool)
        and float(row["utilization_percent"]) > 35.0
    ]
    passed = bool(
        os.name == "nt"
        and not inventory_exception
        and not inventory_issues
        and not prohibited
        and not gpu_exception
        and gpu.get("query_succeeded") is True
        and not high_gpu_rows
    )
    return {
        "passed": passed,
        "process_inventory_method": PROCESS_INVENTORY_METHOD,
        "process_inventory": inventory,
        "process_inventory_issues": inventory_issues,
        "process_inventory_exception": inventory_exception,
        "tasklist_used": False,
        "prohibited_active_processes": prohibited,
        "gpu": gpu,
        "gpu_exception": gpu_exception,
        "high_gpu_rows": high_gpu_rows,
        "arbitrary_process_termination_performed": False,
    }


def load_and_validate_v4_contract() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw = V4_PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != V4_PLAN_SHA256:
        raise LongEvaluationV4Error("V4 execution plan hash drifted")
    try:
        execution = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LongEvaluationV4Error("V4 plan is not strict UTF-8 JSON") from exc
    if not isinstance(execution, dict) or set(execution) != set(V4_TOP_LEVEL_KEYS):
        raise LongEvaluationV4Error("V4 plan shape drifted")
    if execution.get("schema_version") != 4:
        raise LongEvaluationV4Error("V4 schema drifted")
    if execution.get("artifact_kind") != (
        "kira_qwen35_long_turing_health_body_voice_execution_plan_v4"
    ):
        raise LongEvaluationV4Error("V4 kind drifted")
    if execution.get("status") != "STATIC_SUCCESSOR_NOT_EXECUTED":
        raise LongEvaluationV4Error("V4 status drifted")

    predecessor = execution.get("predecessor")
    retained_contract = execution.get("retained_v3_contract")
    repair = execution.get("process_inventory_repair")
    roots = execution.get("execution_roots")
    if not all(isinstance(value, dict) for value in (predecessor, retained_contract, repair, roots)):
        raise LongEvaluationV4Error("V4 nested contract malformed")
    assert isinstance(predecessor, dict)
    assert isinstance(retained_contract, dict)
    assert isinstance(repair, dict)
    assert isinstance(roots, dict)

    for path_key, hash_key in (
        ("v3_plan_path", "v3_plan_sha256"),
        ("v3_controller_path", "v3_controller_sha256"),
        ("v3_test_path", "v3_test_sha256"),
        ("v3_preparation_checkpoint_path", "v3_preparation_checkpoint_sha256"),
        ("v3_fresh_audit_path", "v3_fresh_audit_sha256"),
        ("v3_postmortem_path", "v3_postmortem_sha256"),
    ):
        _project_file(str(predecessor.get(path_key) or ""), str(predecessor.get(hash_key) or ""))

    if predecessor.get("v3_attempt_01_consumed_no_retry") is not True:
        raise LongEvaluationV4Error("V3 attempt is not bound consumed/no-retry")
    if predecessor.get("v3_generated_attempt_empty") is not True:
        raise LongEvaluationV4Error("V3 generated-empty disposition drifted")
    expected_attempt = (ROOT / str(predecessor.get("v3_attempt_path") or "")).resolve()
    expected_generated = (ROOT / str(predecessor.get("v3_generated_path") or "")).resolve()
    if expected_attempt != V3_ATTEMPT.resolve() or expected_generated != V3_GENERATED.resolve():
        raise LongEvaluationV4Error("V3 consumed roots drifted")
    file_specs = predecessor.get("v3_attempt_files")
    if not isinstance(file_specs, list) or len(file_specs) != 8:
        raise LongEvaluationV4Error("V3 attempt file inventory drifted")
    expected_names = {str(row.get("name") or "") for row in file_specs if isinstance(row, Mapping)}
    actual_names = {path.name for path in V3_ATTEMPT.iterdir() if path.is_file()}
    if expected_names != actual_names:
        raise LongEvaluationV4Error("V3 attempt file set drifted")
    for row in file_specs:
        if not isinstance(row, Mapping):
            raise LongEvaluationV4Error("V3 attempt file row malformed")
        path = V3_ATTEMPT / str(row.get("name") or "")
        if (
            not path.is_file()
            or path.stat().st_size != row.get("bytes")
            or _sha256_file(path) != row.get("sha256")
        ):
            raise LongEvaluationV4Error(f"V3 consumed evidence drifted:{path.name}")
    if not (V3_ATTEMPT / "CHILD_AUTHORIZATION_CONSUMED.json").is_file():
        raise LongEvaluationV4Error("V3 consumed authorization missing")
    if not V3_GENERATED.is_dir() or any(V3_GENERATED.iterdir()):
        raise LongEvaluationV4Error("V3 generated directory not preserved empty")

    final = json.loads(
        (V3_ATTEMPT / "FINAL_REPORT.json").read_text(encoding="utf-8"),
        object_pairs_hook=_strict_object,
    )
    if not isinstance(final, dict):
        raise LongEvaluationV4Error("V3 final report malformed")
    exception = final.get("exception") if isinstance(final.get("exception"), Mapping) else {}
    preflight = (
        final.get("heavy_workload_preflight")
        if isinstance(final.get("heavy_workload_preflight"), Mapping)
        else {}
    )
    if (
        final.get("status") != predecessor.get("v3_failure_status")
        or exception.get("message") != predecessor.get("v3_failure_exception")
        or preflight.get("process_error") != predecessor.get("v3_failure_process_error")
        or len(final.get("turns") if isinstance(final.get("turns"), list) else [])
        != predecessor.get("v3_failure_turn_count")
        or final.get("speaker_playback_completed") is not False
    ):
        raise LongEvaluationV4Error("V3 exact failure truth drifted")

    v3_execution, effective = v3.load_and_validate_v3_contract()
    expected_retained = {
        "effective_measured_turns": 35,
        "voluntary_invitation_generations": 1,
        "maximum_qwen_generations": 36,
        "exact_model": "qwen3.5:9b",
        "exact_digest": "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        "llama_allowed": False,
        "voice_route": "blackwell_gpu_persistent_candidate_v2",
        "voice_device": "cuda",
        "fallback_allowed": False,
        "child_watchdog_seconds": 5100,
        "parent_timeout_seconds": 5250,
        "sealed_maximum_seconds": 5400,
        "unattended_authorization_flag": v3.UNATTENDED_AUTHORIZATION_FLAG,
        "physical_supervision_claimed": False,
        "owner_hearing_may_be_inferred": False,
    }
    if retained_contract != expected_retained:
        raise LongEvaluationV4Error("retained V3 contract drifted")
    if len(effective.get("turns") or []) != 35 or effective.get("model", {}).get(
        "maximum_generations"
    ) != 36:
        raise LongEvaluationV4Error("effective V3 plan drifted")

    expected_repair = {
        "old_method": "tasklist_exact_names",
        "old_reproduced_exit_code": 1,
        "old_reproduced_stderr": "ERROR: Access denied",
        "new_method": PROCESS_INVENTORY_METHOD,
        "snapshot_flag": TH32CS_SNAPPROCESS,
        "terminal_error_code": ERROR_NO_MORE_FILES,
        "tasklist_allowed": False,
        "arbitrary_process_handle_open_allowed": False,
        "requires_snapshot_created": True,
        "requires_first_entry": True,
        "requires_terminal_no_more_files": True,
        "requires_snapshot_closed": True,
        "requires_sorted_unique_casefold_names": True,
        "prohibited_exact_names": sorted(PROHIBITED_PROCESS_NAMES),
        "gpu_query_and_35_percent_threshold_preserved": True,
        "any_inventory_error_fails_closed": True,
    }
    if repair != expected_repair:
        raise LongEvaluationV4Error("process inventory repair contract drifted")
    expected_roots = {
        "evidence_root": EVIDENCE_ROOT.resolve().relative_to(ROOT.resolve()).as_posix(),
        "generated_root": GENERATED_ROOT.resolve().relative_to(ROOT.resolve()).as_posix(),
        "only_permitted_attempt_label": ONLY_ATTEMPT_LABEL,
        "append_only_reservation_required": True,
    }
    if roots != expected_roots:
        raise LongEvaluationV4Error("V4 roots drifted")
    return execution, v3_execution, effective


def validate_attempt_binding(incoming: Sequence[str]) -> None:
    child = "--child-run" in incoming

    def value(flag: str, default: str = "") -> str:
        for index, item in enumerate(incoming):
            if item == flag and index + 1 < len(incoming):
                return incoming[index + 1]
        return default

    if child:
        attempt = Path(value("--attempt-path")).resolve()
        generated = Path(value("--generated-path")).resolve()
        if attempt.name != ONLY_ATTEMPT_LABEL or generated.name != ONLY_ATTEMPT_LABEL:
            raise LongEvaluationV4Error("V4 child attempt is not exact attempt_01")
        return
    if value("--attempt-label", ONLY_ATTEMPT_LABEL) != ONLY_ATTEMPT_LABEL:
        raise LongEvaluationV4Error("V4 permits only append-only attempt_01")


def configure_retained_runner_v4(
    execution: Mapping[str, Any],
    v3_execution: Mapping[str, Any],
    effective: Mapping[str, Any],
    *,
    unattended: bool,
) -> None:
    del execution
    v3.configure_retained_runner_v3(v3_execution, effective, unattended=unattended)
    retained.__file__ = str(Path(__file__).resolve())
    retained.HARNESS_ID = HARNESS_ID
    retained.EVIDENCE_ROOT = EVIDENCE_ROOT
    retained.GENERATED_ROOT = GENERATED_ROOT
    retained.PREPARATION_ARTIFACT = V4_PLAN_PATH
    retained.CHILD_WATCHDOG_SECONDS = 5100.0
    retained.PARENT_TIMEOUT_SECONDS = 5250.0
    retained.canonical_preparation_bytes = lambda: V4_PLAN_PATH.read_bytes()
    retained.load_preparation_contract = lambda: load_and_validate_v4_contract()[0]
    retained.preparation_contract_issues = (
        lambda observed: []
        if dict(observed) == load_and_validate_v4_contract()[0]
        else ["v4_execution_plan_drifted"]
    )
    retained.heavy_workload_preflight = heavy_workload_preflight_v4


def main(argv: Sequence[str] | None = None) -> int:
    incoming = list(sys.argv[1:] if argv is None else argv)
    unattended = v3.classify_invocation_mode(incoming)
    validate_attempt_binding(incoming)
    execution, v3_execution, effective = load_and_validate_v4_contract()
    configure_retained_runner_v4(
        execution,
        v3_execution,
        effective,
        unattended=unattended,
    )
    forwarded = [value for value in incoming if value != v3.UNATTENDED_MARKER]
    base_exit = retained.main(forwarded)
    if not unattended:
        return int(base_exit)

    attempt = EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL
    final_path = attempt / "FINAL_REPORT.json"
    wrapper_path = attempt / "PARENT_WRAPPER.json"
    try:
        final = json.loads(final_path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
        wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (OSError, json.JSONDecodeError):
        return int(base_exit)
    if not isinstance(final, dict) or not isinstance(wrapper, dict):
        return int(base_exit)
    acknowledgment = wrapper.get("owner_post_playback_acknowledgment")
    acknowledgment = acknowledgment if isinstance(acknowledgment, Mapping) else {}
    turns = final.get("turns") if isinstance(final.get("turns"), list) else []
    expected_ids = [row["id"] for row in effective["turns"]]
    technical_complete = bool(
        final.get("engineering_pass") is True
        and final.get("speaker_playback_completed") is True
        and final.get("owner_post_playback_acknowledged") is False
        and wrapper.get("process_gate_passed") is True
        and wrapper.get("parent_report_contract_issues") == []
        and acknowledgment.get("acknowledged") is False
        and acknowledgment.get("physical_supervision_claimed") is False
        and len(turns) == 35
        and [row.get("turn_id") for row in turns if isinstance(row, Mapping)]
        == expected_ids
    )
    print(
        json.dumps(
            {
                "unattended_log_only": True,
                "owner_authorized_unattended_log_review": True,
                "physical_owner_supervision_claimed": False,
                "technical_engineering_and_playback_complete": technical_complete,
                "owner_hearing_acknowledged": False,
                "owner_hearing_pending": True,
                "attempt": attempt.resolve().relative_to(ROOT.resolve()).as_posix(),
            },
            indent=2,
        )
    )
    return 0 if technical_complete else int(base_exit)


if __name__ == "__main__":
    raise SystemExit(main())
