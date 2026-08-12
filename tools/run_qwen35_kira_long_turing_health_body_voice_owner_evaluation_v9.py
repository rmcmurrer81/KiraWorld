#!/usr/bin/env python3
"""Static V9 successor: canonical arguments and closed V1 compatibility gate."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
import types
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TypeVar


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools as tools_package
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as v1
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v3 as v3
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v7 as v7
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8 as v8
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


V9_PLAN_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v9"
    / "attempt_01"
    / "EXECUTION_PLAN_V9.json"
)
V9_PLAN_SHA256 = "64186f2b837b275dde4820d5df83b1080ed46533d39ff7060006c1cbbcbbbd37"
V8_PLAN_SHA256 = "9e472f839a4ecae2d538db67244db23fb6d9cc4101b29d2d3b87f3e54d32d40e"
V1_MODULE_PATH = ROOT / "tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation.py"
V1_MODULE_BYTES = 11499
V1_MODULE_SHA256 = "356a1cdf35aff2e9e9270e6c7a9b1c110e2c29b764b9fe7fdc62eb3cb2340a1c"

EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v9"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v9"
)
HARNESS_ID = "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v9"
ONLY_ATTEMPT_LABEL = "attempt_01"

_V9_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "predecessor",
        "retained_runtime_contract",
        "v9_repair_contract",
        "execution_roots",
    }
)
_V8_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "predecessor",
        "retained_runtime_contract",
        "reviewed_shell_successor",
        "v8_repair_contract",
        "execution_roots",
    }
)
_VALUE_FLAGS = ("--attempt-label", "--attempt-path", "--generated-path", "--child-nonce")
_BOOLEAN_CRITICAL_FLAGS = ("--child-run",)
_CRITICAL_FLAGS = frozenset((*_VALUE_FLAGS, *_BOOLEAN_CRITICAL_FLAGS))

_EXPECTED_RUNTIME = {
    "effective_measured_turns": 35,
    "voluntary_invitation_generations": 1,
    "maximum_qwen_generations": 36,
    "exact_model": "qwen3.5:9b",
    "exact_digest": "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    "llama_allowed": False,
    "voice_route": "blackwell_gpu_persistent_candidate_v2",
    "voice_device": "cuda",
    "cpu_fallback_allowed": False,
    "sapi_allowed": False,
    "generic_voice_allowed": False,
    "speaker_playback_requested": True,
    "child_watchdog_seconds": 5100,
    "parent_timeout_seconds": 5250,
    "sealed_maximum_seconds": 5400,
    "physical_supervision_claimed": False,
    "owner_hearing_may_be_inferred": False,
}
_EXPECTED_V8_REPAIR = {
    "v7_semantic_and_terminal_repairs_retained": True,
    "legacy_v1_plan_must_remain_exact": True,
    "legacy_shell_binding_must_match_recorded_predecessor": True,
    "current_shell_and_fast_end_evidence_must_match_exact": True,
    "all_nine_other_v1_project_bindings_must_match_exact": True,
    "no_second_project_binding_substitution_allowed": True,
    "full_nested_contract_loader_must_pass_before_live_authority": True,
    "technical_pass_is_turing_acceptance": False,
    "owner_or_independent_semantic_review_still_required": True,
}
_EXPECTED_V9_REPAIR = {
    "v8_and_rejection_preserved_exact": True,
    "critical_argument_flags_closed": True,
    "duplicate_singleton_flags_rejected": True,
    "equals_form_critical_flags_rejected": True,
    "missing_or_flag_shaped_values_rejected": True,
    "parent_child_flag_domains_separate": True,
    "canonical_argument_list_consumed_unchanged": True,
    "attempt_02_unreachable_after_validation": True,
    "canonical_v1_module_source_bound": True,
    "canonical_v1_loader_identity_bound": True,
    "preexisting_v1_loader_drift_rejected": True,
    "overlapping_or_reentrant_validation_rejected": True,
    "compatibility_gate_thread_owned": True,
    "off_thread_compatibility_access_rejected": True,
    "success_and_exception_restore_exact_original": True,
    "post_restore_identity_verified": True,
    "v9_owned_v8_validation_projection": True,
    "full_nested_contract_loader_must_pass_before_live_authority": True,
    "all_v7_semantic_and_terminal_repairs_retained": True,
    "technical_pass_is_turing_acceptance": False,
    "owner_or_independent_semantic_review_still_required": True,
}


class LongEvaluationV9Error(RuntimeError):
    """Raised when the exact append-only V9 boundary is not satisfied."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LongEvaluationV9Error(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise LongEvaluationV9Error(f"non-standard JSON numeric constant:{value}")


def strict_json_loads(value: str) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_json_constant,
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_file(row: Any, label: str) -> bytes:
    if type(row) is not dict or set(row) != {"path", "bytes", "sha256"}:
        raise LongEvaluationV9Error(f"{label} row shape drifted")
    relative = Path(str(row.get("path") or ""))
    if not relative.as_posix() or relative.is_absolute() or ".." in relative.parts:
        raise LongEvaluationV9Error(f"{label} path is not project-relative")
    path = (ROOT / relative).resolve(strict=True)
    try:
        path.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LongEvaluationV9Error(f"{label} escaped project root") from exc
    raw = path.read_bytes()
    size = row.get("bytes")
    if type(size) is not int or size != len(raw):
        raise LongEvaluationV9Error(f"{label} byte drift:{relative.as_posix()}")
    if type(row.get("sha256")) is not str or row["sha256"] != _sha256_bytes(raw):
        raise LongEvaluationV9Error(f"{label} hash drift:{relative.as_posix()}")
    return raw


def _exact_keys(value: Any, expected: frozenset[str] | set[str], label: str) -> None:
    if type(value) is not dict or set(value) != set(expected):
        raise LongEvaluationV9Error(f"{label} keys drifted")


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _typed_equal(left[key], right[key]) for key in left
        )
    if type(left) in (list, tuple):
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right)
        )
    return bool(left == right)


_CANONICAL_V1_MODULE = v1
_CANONICAL_V1_LOADER = v1.load_and_validate_plan
_CANONICAL_V1_CODE = _CANONICAL_V1_LOADER.__code__
_CANONICAL_V1_DEFAULTS = _CANONICAL_V1_LOADER.__defaults__
_CANONICAL_V1_KWDEFAULTS = _CANONICAL_V1_LOADER.__kwdefaults__
_CANONICAL_V8_REVIEWED_LOADER = v8._load_v1_plan_with_reviewed_shell_successor
_CANONICAL_V8_CONFIGURE = v8.configure_retained_runner_v8
_CANONICAL_CHAIN_LOADERS = (
    (v7, "load_and_validate_v7_contract", v7.load_and_validate_v7_contract),
    (v7.v6, "load_and_validate_v6_contract", v7.v6.load_and_validate_v6_contract),
    (v7.v6.v5, "load_and_validate_v5_contract", v7.v6.v5.load_and_validate_v5_contract),
    (v7.v6.v5.v4, "load_and_validate_v4_contract", v7.v6.v5.v4.load_and_validate_v4_contract),
    (v7.v6.v5.v4.v3, "load_and_validate_v3_contract", v7.v6.v5.v4.v3.load_and_validate_v3_contract),
)
_V1_COMPATIBILITY_LOCK = threading.Lock()
_T = TypeVar("_T")


def _verify_exact_function(
    module: types.ModuleType, name: str, expected: Any, label: str
) -> None:
    observed = module.__dict__.get(name)
    if observed is not expected or type(expected) is not types.FunctionType:
        raise LongEvaluationV9Error(f"{label} callable identity drifted")
    if expected.__globals__ is not module.__dict__:
        raise LongEvaluationV9Error(f"{label} globals identity drifted")
    if expected.__module__ != module.__name__ or expected.__name__ != name:
        raise LongEvaluationV9Error(f"{label} callable metadata drifted")


def _verify_canonical_loader_state(expected_v1: Any) -> None:
    if type(v1) is not types.ModuleType or v1 is not _CANONICAL_V1_MODULE:
        raise LongEvaluationV9Error("canonical V1 module object drifted")
    if sys.modules.get(v1.__name__) is not v1:
        raise LongEvaluationV9Error("canonical V1 sys.modules binding drifted")
    package_value = getattr(
        tools_package,
        "run_qwen35_kira_long_turing_health_body_voice_owner_evaluation",
        None,
    )
    if package_value is not v1:
        raise LongEvaluationV9Error("canonical V1 package binding drifted")
    if Path(str(v1.__file__)).resolve(strict=True) != V1_MODULE_PATH.resolve(strict=True):
        raise LongEvaluationV9Error("canonical V1 module path drifted")
    if V1_MODULE_PATH.stat().st_size != V1_MODULE_BYTES or _sha256_file(
        V1_MODULE_PATH
    ) != V1_MODULE_SHA256:
        raise LongEvaluationV9Error("canonical V1 module bytes drifted")
    if v1.load_and_validate_plan is not expected_v1:
        raise LongEvaluationV9Error("V1 loader binding drifted")
    if type(_CANONICAL_V1_LOADER) is not types.FunctionType:
        raise LongEvaluationV9Error("canonical V1 loader is not an exact function")
    if _CANONICAL_V1_LOADER.__globals__ is not v1.__dict__:
        raise LongEvaluationV9Error("canonical V1 loader globals drifted")
    if _CANONICAL_V1_LOADER.__code__ is not _CANONICAL_V1_CODE:
        raise LongEvaluationV9Error("canonical V1 loader code identity drifted")
    if (
        _CANONICAL_V1_LOADER.__defaults__ is not _CANONICAL_V1_DEFAULTS
        or _CANONICAL_V1_LOADER.__kwdefaults__ is not _CANONICAL_V1_KWDEFAULTS
        or _CANONICAL_V1_LOADER.__module__ != v1.__name__
        or _CANONICAL_V1_LOADER.__name__ != "load_and_validate_plan"
        or _CANONICAL_V1_LOADER.__qualname__ != "load_and_validate_plan"
        or _CANONICAL_V1_CODE.co_firstlineno != 110
        or _CANONICAL_V1_CODE.co_argcount != 0
    ):
        raise LongEvaluationV9Error("canonical V1 loader metadata drifted")
    _verify_exact_function(
        v8,
        "_load_v1_plan_with_reviewed_shell_successor",
        _CANONICAL_V8_REVIEWED_LOADER,
        "canonical V8 reviewed-shell loader",
    )
    _verify_exact_function(
        v8,
        "configure_retained_runner_v8",
        _CANONICAL_V8_CONFIGURE,
        "canonical V8 configuration",
    )
    for module, name, expected in _CANONICAL_CHAIN_LOADERS:
        _verify_exact_function(module, name, expected, f"canonical nested loader {name}")


def _run_with_closed_v1_compatibility(
    reviewed: Mapping[str, Any], operation: Callable[[], _T]
) -> _T:
    if not _V1_COMPATIBILITY_LOCK.acquire(blocking=False):
        raise LongEvaluationV9Error(
            "overlapping or reentrant V1 compatibility validation rejected"
        )
    owner_thread = threading.get_ident()
    active = True
    installed = False

    def compatibility_gate() -> dict[str, Any]:
        if not active or threading.get_ident() != owner_thread:
            raise LongEvaluationV9Error(
                "V1 compatibility loader is closed outside its owner call"
            )
        if v1.load_and_validate_plan is not compatibility_gate:
            raise LongEvaluationV9Error("V1 compatibility gate binding drifted")
        return _CANONICAL_V8_REVIEWED_LOADER(reviewed)

    observed_before_restore: Any = None
    try:
        _verify_canonical_loader_state(_CANONICAL_V1_LOADER)
        v1.load_and_validate_plan = compatibility_gate
        installed = True
        _verify_canonical_loader_state(compatibility_gate)
        result = operation()
        _verify_canonical_loader_state(compatibility_gate)
        return result
    finally:
        observed_before_restore = v1.load_and_validate_plan
        active = False
        v1.load_and_validate_plan = _CANONICAL_V1_LOADER
        try:
            _verify_canonical_loader_state(_CANONICAL_V1_LOADER)
            if installed and observed_before_restore is not compatibility_gate:
                raise LongEvaluationV9Error(
                    "V1 loader changed inside compatibility validation"
                )
        finally:
            _V1_COMPATIBILITY_LOCK.release()


def _load_v7_with_closed_v1(
    reviewed: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = _run_with_closed_v1_compatibility(
        reviewed, lambda: _CANONICAL_CHAIN_LOADERS[0][2]()
    )
    if type(result) is not tuple or len(result) != 4:
        raise LongEvaluationV9Error("canonical V7 nested result shape drifted")
    return result


def _load_and_validate_v8_projection() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    raw = v8.V8_PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != V8_PLAN_SHA256 or V8_PLAN_SHA256 != v8.V8_PLAN_SHA256:
        raise LongEvaluationV9Error("preserved V8 plan hash drifted")
    try:
        execution = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, LongEvaluationV9Error) as exc:
        raise LongEvaluationV9Error("preserved V8 plan is not strict UTF-8 JSON") from exc
    _exact_keys(execution, _V8_TOP_LEVEL_KEYS, "preserved V8 plan")
    if (
        execution.get("schema_version") != 8
        or execution.get("artifact_kind")
        != "kira_qwen35_long_turing_health_body_voice_execution_plan_v8"
        or execution.get("status")
        != "STATIC_SUCCESSOR_NOT_EXECUTED_PENDING_DIFFERENT_FRESH_AUDIT"
    ):
        raise LongEvaluationV9Error("preserved V8 plan identity drifted")
    predecessor = execution.get("predecessor")
    runtime = execution.get("retained_runtime_contract")
    reviewed = execution.get("reviewed_shell_successor")
    repair = execution.get("v8_repair_contract")
    roots = execution.get("execution_roots")
    if not all(type(item) is dict for item in (predecessor, runtime, reviewed, repair, roots)):
        raise LongEvaluationV9Error("preserved V8 nested contract malformed")
    _exact_keys(
        predecessor,
        {"v7_rejected_no_live_attempt", "v7_live_retry_allowed", "subjects"},
        "preserved V8 predecessor",
    )
    if (
        predecessor["v7_rejected_no_live_attempt"] is not True
        or predecessor["v7_live_retry_allowed"] is not False
    ):
        raise LongEvaluationV9Error("preserved V8 rejection truth drifted")
    subjects = predecessor["subjects"]
    if type(subjects) is not list or len(subjects) != 8:
        raise LongEvaluationV9Error("preserved V8 predecessor closure drifted")
    seen: set[str] = set()
    for row in subjects:
        _project_file(row, "preserved V8 predecessor")
        path = str(row["path"])
        if path in seen:
            raise LongEvaluationV9Error("preserved V8 predecessor path repeated")
        seen.add(path)
    _exact_keys(
        reviewed,
        {
            "legacy_plan",
            "legacy_shell_binding_sha256",
            "current_shell",
            "fast_end_test",
            "fast_end_checkpoint",
            "original_other_project_binding_count",
            "exact_one_substitution_only",
            "historical_v1_files_unchanged",
        },
        "preserved V8 reviewed shell",
    )
    v7_execution, v6_execution, v5_execution, effective = _load_v7_with_closed_v1(
        reviewed
    )
    if not _typed_equal(runtime, _EXPECTED_RUNTIME) or not _typed_equal(
        runtime, v7_execution.get("retained_runtime_contract")
    ):
        raise LongEvaluationV9Error("preserved V8 runtime contract drifted")
    if not _typed_equal(repair, _EXPECTED_V8_REPAIR):
        raise LongEvaluationV9Error("preserved V8 repair contract drifted")
    expected_roots = {
        "evidence_root": v8.EVIDENCE_ROOT.relative_to(ROOT).as_posix(),
        "generated_root": v8.GENERATED_ROOT.relative_to(ROOT).as_posix(),
        "only_permitted_attempt_label": v8.ONLY_ATTEMPT_LABEL,
        "append_only_reservation_required": True,
        "future_different_fresh_exact_byte_audit_required": True,
    }
    if not _typed_equal(roots, expected_roots):
        raise LongEvaluationV9Error("preserved V8 roots drifted")
    if v8.EVIDENCE_ROOT.exists() or v8.GENERATED_ROOT.exists():
        raise LongEvaluationV9Error("preserved V8 output roots already exist")
    return execution, v7_execution, v6_execution, v5_execution, effective


def load_and_validate_v9_contract() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    raw = V9_PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != V9_PLAN_SHA256:
        raise LongEvaluationV9Error("V9 execution plan hash drifted")
    try:
        execution = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, LongEvaluationV9Error) as exc:
        raise LongEvaluationV9Error("V9 plan is not strict UTF-8 JSON") from exc
    _exact_keys(execution, _V9_TOP_LEVEL_KEYS, "V9 plan")
    if (
        execution.get("schema_version") != 9
        or execution.get("artifact_kind")
        != "kira_qwen35_long_turing_health_body_voice_execution_plan_v9"
        or execution.get("status")
        != "STATIC_SUCCESSOR_NOT_EXECUTED_PENDING_DIFFERENT_FRESH_AUDIT"
    ):
        raise LongEvaluationV9Error("V9 plan identity drifted")
    predecessor = execution.get("predecessor")
    runtime = execution.get("retained_runtime_contract")
    repair = execution.get("v9_repair_contract")
    roots = execution.get("execution_roots")
    if not all(type(item) is dict for item in (predecessor, runtime, repair, roots)):
        raise LongEvaluationV9Error("V9 nested contract malformed")
    _exact_keys(
        predecessor,
        {"v8_rejected_no_live_attempt", "v8_live_retry_allowed", "subjects"},
        "V9 predecessor",
    )
    if (
        predecessor["v8_rejected_no_live_attempt"] is not True
        or predecessor["v8_live_retry_allowed"] is not False
    ):
        raise LongEvaluationV9Error("V8 rejection/no-retry truth drifted")
    subjects = predecessor["subjects"]
    if type(subjects) is not list or len(subjects) != 11:
        raise LongEvaluationV9Error("V9 predecessor subjects drifted")
    seen: set[str] = set()
    for row in subjects:
        _project_file(row, "V9 predecessor")
        path = str(row["path"])
        if path in seen:
            raise LongEvaluationV9Error("V9 predecessor path repeated")
        seen.add(path)
    v8_execution, v7_execution, v6_execution, v5_execution, effective = (
        _load_and_validate_v8_projection()
    )
    if not _typed_equal(runtime, _EXPECTED_RUNTIME) or not _typed_equal(
        runtime, v8_execution.get("retained_runtime_contract")
    ):
        raise LongEvaluationV9Error("V9 retained runtime contract drifted")
    if not _typed_equal(repair, _EXPECTED_V9_REPAIR):
        raise LongEvaluationV9Error("V9 repair contract drifted")
    expected_roots = {
        "evidence_root": EVIDENCE_ROOT.relative_to(ROOT).as_posix(),
        "generated_root": GENERATED_ROOT.relative_to(ROOT).as_posix(),
        "only_permitted_attempt_label": ONLY_ATTEMPT_LABEL,
        "append_only_reservation_required": True,
        "future_different_fresh_exact_byte_audit_required": True,
    }
    if not _typed_equal(roots, expected_roots):
        raise LongEvaluationV9Error("V9 roots drifted")
    if EVIDENCE_ROOT.exists() or GENERATED_ROOT.exists():
        raise LongEvaluationV9Error("V9 output roots already exist")
    return (
        execution,
        v8_execution,
        v7_execution,
        v6_execution,
        v5_execution,
        effective,
    )


def _critical_occurrences(incoming: Sequence[str], flag: str) -> list[int]:
    equals_prefix = flag + "="
    if any(item.startswith(equals_prefix) for item in incoming):
        raise LongEvaluationV9Error(f"equals-form critical flag rejected:{flag}")
    positions = [index for index, item in enumerate(incoming) if item == flag]
    if len(positions) > 1:
        raise LongEvaluationV9Error(f"duplicate critical flag rejected:{flag}")
    return positions


def _critical_value(values: Sequence[str], flag: str, index: int) -> str:
    if index + 1 >= len(values):
        raise LongEvaluationV9Error(f"critical flag missing exact value:{flag}")
    value = values[index + 1]
    if (
        type(value) is not str
        or not value
        or value.startswith("-")
        or "\x00" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise LongEvaluationV9Error(f"critical flag malformed value:{flag}")
    return value


def canonicalize_attempt_binding(incoming: Sequence[str]) -> list[str]:
    values = list(incoming)
    if any(type(item) is not str for item in values):
        raise LongEvaluationV9Error("argument list contains a non-string value")
    positions = {flag: _critical_occurrences(values, flag) for flag in _CRITICAL_FLAGS}
    child = bool(positions["--child-run"])
    consumed: set[int] = set(positions["--child-run"])
    parsed_values: dict[str, str] = {}
    for flag in _VALUE_FLAGS:
        found = positions[flag]
        if not found:
            continue
        index = found[0]
        parsed = _critical_value(values, flag, index)
        consumed.update({index, index + 1})
        parsed_values[flag] = parsed

    if child:
        if "--attempt-label" in parsed_values:
            raise LongEvaluationV9Error("child must not provide an attempt label")
        for required in ("--attempt-path", "--generated-path", "--child-nonce"):
            if required not in parsed_values:
                raise LongEvaluationV9Error(f"child critical value missing:{required}")
        expected_attempt = (EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL).resolve()
        expected_generated = (GENERATED_ROOT / ONLY_ATTEMPT_LABEL).resolve()
        try:
            attempt_path = Path(parsed_values["--attempt-path"]).resolve()
            generated_path = Path(parsed_values["--generated-path"]).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise LongEvaluationV9Error("V9 child path value is malformed") from exc
        if attempt_path != expected_attempt:
            raise LongEvaluationV9Error("V9 child evidence path is not exact attempt_01")
        if generated_path != expected_generated:
            raise LongEvaluationV9Error("V9 child generated path is not exact attempt_01")
        nonce = parsed_values["--child-nonce"]
        if re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
            raise LongEvaluationV9Error("V9 child nonce is malformed")
        canonical_critical = [
            "--child-run",
            "--attempt-path",
            str(expected_attempt),
            "--generated-path",
            str(expected_generated),
            "--child-nonce",
            nonce,
        ]
    else:
        for forbidden in ("--attempt-path", "--generated-path", "--child-nonce"):
            if forbidden in parsed_values:
                raise LongEvaluationV9Error(f"parent received child-only flag:{forbidden}")
        label = parsed_values.get("--attempt-label", ONLY_ATTEMPT_LABEL)
        if label != ONLY_ATTEMPT_LABEL:
            raise LongEvaluationV9Error("V9 permits only append-only attempt_01")
        canonical_critical = ["--attempt-label", ONLY_ATTEMPT_LABEL]

    canonical = [item for index, item in enumerate(values) if index not in consumed]
    canonical.extend(canonical_critical)
    delegated = [item for item in canonical if item != v3.UNATTENDED_MARKER]
    try:
        parsed = retained.build_parser().parse_args(delegated)
    except SystemExit as exc:
        raise LongEvaluationV9Error("retained parser rejected canonical arguments") from exc
    if child:
        if (
            parsed.child_run is not True
            or Path(parsed.attempt_path).resolve()
            != (EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL).resolve()
            or Path(parsed.generated_path).resolve()
            != (GENERATED_ROOT / ONLY_ATTEMPT_LABEL).resolve()
            or parsed.child_nonce != parsed_values["--child-nonce"]
        ):
            raise LongEvaluationV9Error("retained child parser consumed different values")
    elif (
        parsed.child_run is not False
        or parsed.attempt_label != ONLY_ATTEMPT_LABEL
        or parsed.attempt_path != ""
        or parsed.generated_path != ""
        or parsed.child_nonce != ""
    ):
        raise LongEvaluationV9Error("retained parent parser consumed different values")
    return canonical


def validate_attempt_binding(incoming: Sequence[str]) -> list[str]:
    return canonicalize_attempt_binding(incoming)


def configure_retained_runner_v9(
    execution: Mapping[str, Any],
    v8_execution: Mapping[str, Any],
    v7_execution: Mapping[str, Any],
    v6_execution: Mapping[str, Any],
    v5_execution: Mapping[str, Any],
    effective: Mapping[str, Any],
    *,
    unattended: bool,
) -> None:
    del execution
    reviewed = v8_execution["reviewed_shell_successor"]
    _run_with_closed_v1_compatibility(
        reviewed,
        lambda: _CANONICAL_V8_CONFIGURE(
            v8_execution,
            v7_execution,
            v6_execution,
            v5_execution,
            effective,
            unattended=unattended,
        ),
    )
    retained.__file__ = str(Path(__file__).resolve())
    retained.HARNESS_ID = HARNESS_ID
    retained.EVIDENCE_ROOT = EVIDENCE_ROOT
    retained.GENERATED_ROOT = GENERATED_ROOT
    retained.PREPARATION_ARTIFACT = V9_PLAN_PATH
    retained.canonical_preparation_bytes = lambda: V9_PLAN_PATH.read_bytes()
    retained.load_preparation_contract = lambda: load_and_validate_v9_contract()[0]
    retained.preparation_contract_issues = (
        lambda observed: []
        if _typed_equal(observed, load_and_validate_v9_contract()[0])
        else ["v9_execution_plan_drifted"]
    )
    _verify_canonical_loader_state(_CANONICAL_V1_LOADER)


def main(argv: Sequence[str] | None = None) -> int:
    incoming = list(sys.argv[1:] if argv is None else argv)
    canonical_incoming = canonicalize_attempt_binding(incoming)
    unattended = v3.classify_invocation_mode(canonical_incoming)
    (
        execution,
        v8_execution,
        v7_execution,
        v6_execution,
        v5_execution,
        effective,
    ) = load_and_validate_v9_contract()
    configure_retained_runner_v9(
        execution,
        v8_execution,
        v7_execution,
        v6_execution,
        v5_execution,
        effective,
        unattended=unattended,
    )
    forwarded = [
        value for value in canonical_incoming if value != v3.UNATTENDED_MARKER
    ]
    base_exit = retained.main(forwarded)
    if not unattended:
        return int(base_exit)
    attempt = EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL
    try:
        final = strict_json_loads(
            (attempt / "FINAL_REPORT.json").read_text(encoding="utf-8")
        )
        wrapper = strict_json_loads(
            (attempt / "PARENT_WRAPPER.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError, LongEvaluationV9Error):
        return int(base_exit)
    if type(final) is not dict or type(wrapper) is not dict:
        return int(base_exit)
    turns = final.get("turns") if type(final.get("turns")) is list else []
    expected_ids = [row["id"] for row in effective["turns"]]
    acknowledgment = wrapper.get("owner_post_playback_acknowledgment")
    acknowledgment = acknowledgment if type(acknowledgment) is dict else {}
    semantic_and_epoch_complete = not v7.v5.v5_worker_epoch_contract_issues(final)
    technical_complete = bool(
        final.get("engineering_pass") is True
        and final.get("speaker_playback_completed") is True
        and final.get("owner_post_playback_acknowledged") is False
        and wrapper.get("process_gate_passed") is True
        and wrapper.get("parent_report_contract_issues") == []
        and acknowledgment.get("acknowledged") is False
        and acknowledgment.get("physical_supervision_claimed") is False
        and len(turns) == 35
        and [row.get("turn_id") for row in turns if type(row) is dict] == expected_ids
        and semantic_and_epoch_complete
    )
    print(
        json.dumps(
            {
                "unattended_log_only": True,
                "owner_authorized_unattended_log_review": True,
                "physical_owner_supervision_claimed": False,
                "technical_engineering_playback_and_semantic_gate_complete": technical_complete,
                "owner_hearing_acknowledged": False,
                "owner_hearing_pending": True,
                "turing_psychology_acceptance": "PENDING_OWNER_OR_INDEPENDENT_REVIEW",
                "attempt": attempt.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0 if technical_complete else int(base_exit)


if __name__ == "__main__":
    raise SystemExit(main())
