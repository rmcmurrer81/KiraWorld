#!/usr/bin/env python3
"""One-shot, default-off Blackwell v9 bounded live acceptance attempt_02.

Importing this module is inert.  The live path is unavailable unless all three
exact, distinct audit bindings are present (v9 process repair, v8 worker, and a
future different-agent audit of this harness), both exact per-run live
capabilities are supplied, and the new append-only ``attempt_02`` directory can
be reserved atomically.  Playback is separately gated and remains off by
default.  This module never changes production routing or chooses a fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.persistent_blackwell_voice_integration_v9 import (  # noqa: E402
    BlackwellV9Coordinator,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8 import (  # noqa: E402
    candidate_contract as v8_contract,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v9 import (  # noqa: E402
    candidate_contract as v9_contract,
)
from tools import run_blackwell_v8_bounded_live_acceptance as v8_harness  # noqa: E402


HARNESS_ID = "blackwell_v9_exact_qwen35_single_current_answer_live_acceptance_attempt02_v1"
ATTEMPT_ID = "attempt_02"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v9_bounded_live_acceptance"
)
V9_AUDIT_AUTHORIZATION_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v9_venv_descendant_fresh_static_audit"
    / "attempt_01"
    / "AUDIT_AUTHORIZATION.json"
)
EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256 = (
    "0547257cd86ef0022138c730f9f48e5965cab352ee4a4635c9aecd292b890f78"
)
V8_WORKER_AUDIT_AUTHORIZATION_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v8_cpu_park_fresh_static_audit"
    / "attempt_01"
    / "AUDIT_AUTHORIZATION.json"
)
EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256 = (
    "d822b4f07eb3ad7873f5e48129494c08b85f0e06845ae01d57841476bd4ef16f"
)
V8_HARNESS_AUDIT_AUTHORIZATION_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v8_bounded_live_acceptance_fresh_static_audit"
    / "attempt_01"
    / "AUDIT_AUTHORIZATION.json"
)
EXPECTED_V8_HARNESS_AUDIT_AUTHORIZATION_SHA256 = (
    "5c0f19db8586375607b65b9a347ae69827ed8232b39c4cca81f37cb8ff8c6387"
)
CONSUMED_ATTEMPT01_FINAL_REPORT_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v8_bounded_live_acceptance"
    / "attempt_01"
    / "FINAL_REPORT.json"
)
EXPECTED_CONSUMED_ATTEMPT01_FINAL_REPORT_SHA256 = (
    "7820dcf4b9c46bc2fbd5338613b67c51399bc557db41c3b12f901f8720859a82"
)
HARNESS_SEAL_MANIFEST_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v9_bounded_live_acceptance_attempt02_preparation"
    / "HARNESS_SEAL_MANIFEST.json"
)
HARNESS_AUDIT_AUTHORIZATION_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v9_bounded_live_acceptance_attempt02_fresh_static_audit"
    / "attempt_01"
    / "AUDIT_AUTHORIZATION.json"
)
HARNESS_LIVE_CAPABILITY_NAME = "KIRA_AUTHORIZE_BLACKWELL_V9_ATTEMPT02_HARNESS"
HARNESS_LIVE_CAPABILITY_VALUE = (
    "execute_exact_blackwell_v9_attempt_02_after_fresh_harness_audit_only"
)
PLAYBACK_CAPABILITY_NAME = "KIRA_AUTHORIZE_BLACKWELL_V9_ATTEMPT02_SINGLE_PLAYBACK"
PLAYBACK_CAPABILITY_VALUE = "play_exact_returned_v9_attempt_02_wav_once"
EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_MODEL_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
EXPECTED_PRODUCTION_ROUTING_SHA256 = (
    "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81"
)
QWEN_TTL_SECONDS = v8_harness.QWEN_TTL_SECONDS
MESSAGES = v8_harness.MESSAGES
ATTEMPT_PATTERN = re.compile(r"attempt_[0-9]{2}\Z")

_SEALED_HARNESS_FILES = {
    "tools/run_blackwell_v9_bounded_live_acceptance_attempt02.py",
    "Testing/test_blackwell_v9_bounded_live_acceptance_attempt02_hostile_static.py",
}
_STABLE_IDENTITY_KEYS = {
    "executable_path",
    "executable_sha256",
    "executable_size",
    "executable_volume_serial",
    "executable_file_index",
}
_BOUND_ENVELOPE_KEYS = {
    "value",
    "request_id",
    "worker_pid",
    "root_pid",
    "worker_instance_id",
    "process_identity_digest",
    "launcher_process_identity_digest",
    "writer",
    "elapsed_seconds",
    "deadline_seconds",
    "deadline_monotonic",
}


class AcceptanceError(RuntimeError):
    """An exact attempt_02 acceptance gate failed closed."""


utc_now = v8_harness.utc_now
sha256_text = v8_harness.sha256_text
write_once_json = v8_harness.write_once_json
AppendOnlyLedger = v8_harness.AppendOnlyLedger


def _is_sha256(value: Any) -> bool:
    return v9_contract.is_sha256(value)


def _canonical_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=True)))


def _stable_identity(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not _STABLE_IDENTITY_KEYS.issubset(value):
        raise AcceptanceError(f"{label} stable executable identity is incomplete")
    result = {key: value[key] for key in _STABLE_IDENTITY_KEYS}
    if not isinstance(result["executable_path"], str):
        raise AcceptanceError(f"{label} executable path is invalid")
    if not _is_sha256(result["executable_sha256"]):
        raise AcceptanceError(f"{label} executable hash is invalid")
    for key in (
        "executable_size",
        "executable_volume_serial",
        "executable_file_index",
    ):
        if isinstance(result[key], bool) or not isinstance(result[key], int) or result[key] <= 0:
            raise AcceptanceError(f"{label} {key} is invalid")
    result["executable_path"] = _canonical_path(Path(result["executable_path"]))
    return result


def verify_harness_seal() -> dict[str, Any]:
    value = v9_contract.strict_json_loads(HARNESS_SEAL_MANIFEST_PATH.read_bytes())
    required = {"schema_version", "harness_id", "status", "files"}
    if not isinstance(value, dict) or set(value) != required:
        raise AcceptanceError("attempt_02 harness seal schema is not exact")
    if (
        value["schema_version"] != 1
        or value["harness_id"] != HARNESS_ID
        or value["status"]
        != "SEALED_STATIC_ONLY_PENDING_DIFFERENT_AGENT_AUDIT"
        or not isinstance(value["files"], list)
        or len(value["files"]) != len(_SEALED_HARNESS_FILES)
    ):
        raise AcceptanceError("attempt_02 harness seal identity is not exact")
    observed: set[str] = set()
    for index, record in enumerate(value["files"]):
        if not isinstance(record, dict) or set(record) != {"path", "bytes", "sha256"}:
            raise AcceptanceError(f"attempt_02 harness seal record {index} is malformed")
        relative = record["path"]
        if not isinstance(relative, str) or relative in observed:
            raise AcceptanceError("attempt_02 harness seal path is invalid or duplicated")
        observed.add(relative)
        path = ROOT / relative
        if (
            not path.is_file()
            or isinstance(record["bytes"], bool)
            or not isinstance(record["bytes"], int)
            or path.stat().st_size != record["bytes"]
            or not _is_sha256(record["sha256"])
            or v9_contract.sha256_file(path) != record["sha256"]
        ):
            raise AcceptanceError(f"attempt_02 sealed harness bytes drifted: {relative}")
    if observed != _SEALED_HARNESS_FILES:
        raise AcceptanceError("attempt_02 harness seal file set is not exact")
    return dict(value)


def verify_fresh_harness_audit(expected_sha256: str) -> dict[str, Any]:
    if not _is_sha256(expected_sha256):
        raise AcceptanceError("fresh attempt_02 harness audit SHA-256 is required")
    if (
        not HARNESS_AUDIT_AUTHORIZATION_PATH.is_file()
        or v9_contract.sha256_file(HARNESS_AUDIT_AUTHORIZATION_PATH) != expected_sha256
    ):
        raise AcceptanceError(
            "fresh different-agent attempt_02 harness audit is absent or drifted"
        )
    value = v9_contract.strict_json_loads(
        HARNESS_AUDIT_AUTHORIZATION_PATH.read_bytes()
    )
    required = {
        "schema_version",
        "harness_id",
        "harness_seal_manifest_path",
        "harness_seal_manifest_sha256",
        "fresh_independent_audit",
        "auditor_relationship",
        "verdict",
        "static_only",
        "authorized_attempt_id",
        "one_bounded_execution",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise AcceptanceError("fresh attempt_02 harness audit schema is not exact")
    expected_manifest = HARNESS_SEAL_MANIFEST_PATH.relative_to(ROOT).as_posix()
    if (
        value["schema_version"] != 1
        or value["harness_id"] != HARNESS_ID
        or value["harness_seal_manifest_path"] != expected_manifest
        or value["harness_seal_manifest_sha256"]
        != v9_contract.sha256_file(HARNESS_SEAL_MANIFEST_PATH)
        or value["fresh_independent_audit"] is not True
        or value["auditor_relationship"]
        != "different_agent_from_attempt02_harness_author"
        or value["verdict"]
        != "ACCEPT_V9_ATTEMPT02_HARNESS_FOR_ONE_BOUNDED_LIVE_EXECUTION"
        or value["static_only"] is not True
        or value["authorized_attempt_id"] != ATTEMPT_ID
        or value["one_bounded_execution"] is not True
    ):
        raise AcceptanceError("fresh attempt_02 harness audit content is unacceptable")
    verify_harness_seal()
    return dict(value)


def validate_static_and_capability_gates(
    *, playback: bool, accepted_harness_audit_sha256: str
) -> dict[str, Any]:
    config = v9_contract.load_canonical_config()
    seal = verify_harness_seal()
    harness_audit = verify_fresh_harness_audit(accepted_harness_audit_sha256)
    if v9_contract.CANONICAL_CONFIG_SHA256 != (
        "a45f05bd46dc86d2dfb35d02709ae2264211f892f4830afd90aa177032b65915"
    ):
        raise AcceptanceError("sealed v9 candidate config constant drifted")
    if v9_contract.sha256_file(V9_AUDIT_AUTHORIZATION_PATH) != (
        EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256
    ):
        raise AcceptanceError("exact accepted v9 process audit bytes are absent")
    if v9_contract.sha256_file(V8_WORKER_AUDIT_AUTHORIZATION_PATH) != (
        EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256
    ):
        raise AcceptanceError("exact accepted v8 worker audit bytes are absent")
    if len(
        {
            EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
            EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256,
            accepted_harness_audit_sha256,
        }
    ) != 3:
        raise AcceptanceError("v9, v8 worker, and attempt_02 harness audits are not distinct")
    v9_contract.verify_preserved_bytes(config)
    v9_seal_path = ROOT / config["fresh_audit_contract"]["required_seal_manifest_path"]
    v9_contract.verify_seal_manifest(config, v9_seal_path)
    v9_audit = v9_contract.verify_fresh_audit_authorization(
        config, expected_audit_sha256=EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256
    )
    topology = v9_contract.verify_topology_executables(config)
    v8_binding = config["v8_worker_audit_binding"]
    if (
        v8_binding["path"]
        != V8_WORKER_AUDIT_AUTHORIZATION_PATH.relative_to(ROOT).as_posix()
        or v8_binding["sha256"] != EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256
    ):
        raise AcceptanceError("v9 did not bind the exact distinct v8 worker audit")
    v8_config = v8_contract.load_canonical_config()
    v8_worker_audit = v8_contract.verify_fresh_audit_authorization(
        v8_config,
        expected_audit_sha256=EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256,
    )
    if v9_contract.sha256_file(V8_HARNESS_AUDIT_AUTHORIZATION_PATH) != (
        EXPECTED_V8_HARNESS_AUDIT_AUTHORIZATION_SHA256
    ):
        raise AcceptanceError("preserved v8 harness audit bytes drifted")
    v8_harness.verify_fresh_harness_audit(
        EXPECTED_V8_HARNESS_AUDIT_AUTHORIZATION_SHA256
    )
    if (
        config["engineering_run_opt_in"]
        != "KIRA_AUTHORIZE_BLACKWELL_V9_BOUNDED_ENGINEERING_RUN"
        or config["engineering_run_opt_in_value"]
        != "exact_v9_venv_direct_child_after_fresh_different_agent_audit_attempt02_only"
    ):
        raise AcceptanceError("sealed v9 per-run capability contract drifted")
    v9_contract.verify_per_run_live_capability(config)
    if os.environ.get(HARNESS_LIVE_CAPABILITY_NAME) != HARNESS_LIVE_CAPABILITY_VALUE:
        raise AcceptanceError("exact per-run attempt_02 harness capability is absent")
    if playback:
        if os.environ.get(PLAYBACK_CAPABILITY_NAME) != PLAYBACK_CAPABILITY_VALUE:
            raise AcceptanceError("separate exact attempt_02 playback capability is absent")
    elif os.environ.get(PLAYBACK_CAPABILITY_NAME) is not None:
        raise AcceptanceError("playback capability was supplied without --playback")
    if os.environ.get(config["feature_flag"]) not in (None, "", "0"):
        raise AcceptanceError("production-like v9 feature selection is forbidden")
    if config["worker_module"] != (
        "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.worker_entry"
    ):
        raise AcceptanceError("v9 did not preserve the exact v8 worker module")
    if CONSUMED_ATTEMPT01_FINAL_REPORT_PATH.resolve() == (
        EVIDENCE_ROOT / ATTEMPT_ID / "FINAL_REPORT.json"
    ).resolve():
        raise AcceptanceError("attempt_02 evidence root aliases consumed attempt_01")
    if v9_contract.sha256_file(CONSUMED_ATTEMPT01_FINAL_REPORT_PATH) != (
        EXPECTED_CONSUMED_ATTEMPT01_FINAL_REPORT_SHA256
    ):
        raise AcceptanceError("consumed attempt_01 bytes drifted")
    if os.name != "nt":
        raise AcceptanceError("the sealed v9 live candidate is Windows-only")
    return {
        "v9_audit_authorization": v9_audit,
        "v9_audit_authorization_sha256": EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
        "v8_worker_audit_authorization": v8_worker_audit,
        "v8_worker_audit_authorization_sha256": (
            EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256
        ),
        "fresh_harness_audit": harness_audit,
        "fresh_harness_audit_sha256": accepted_harness_audit_sha256,
        "harness_seal_manifest_sha256": v9_contract.sha256_file(
            HARNESS_SEAL_MANIFEST_PATH
        ),
        "harness_seal": seal,
        "v9_candidate_config_sha256": v9_contract.CANONICAL_CONFIG_SHA256,
        "topology_executables": topology,
        "v9_live_capability_name": config["engineering_run_opt_in"],
        "v9_live_capability_value_sha256": sha256_text(
            config["engineering_run_opt_in_value"]
        ),
        "harness_live_capability_name": HARNESS_LIVE_CAPABILITY_NAME,
        "harness_live_capability_value_sha256": sha256_text(
            HARNESS_LIVE_CAPABILITY_VALUE
        ),
        "playback_requested": playback,
        "playback_capability_name": PLAYBACK_CAPABILITY_NAME if playback else None,
        "playback_capability_value_sha256": (
            sha256_text(PLAYBACK_CAPABILITY_VALUE) if playback else None
        ),
        "attempt_id": ATTEMPT_ID,
        "consumed_attempt_01_reused": False,
        "production_routing_changed": False,
    }


def reserve_attempt_02() -> Path:
    """Atomically reserve only the new attempt_02 directory."""

    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    existing = sorted(
        path.name
        for path in EVIDENCE_ROOT.iterdir()
        if path.is_dir() and ATTEMPT_PATTERN.fullmatch(path.name)
    )
    if existing:
        raise AcceptanceError(f"one-shot v9 live attempt already reserved: {existing}")
    attempt = EVIDENCE_ROOT / ATTEMPT_ID
    attempt.mkdir(parents=False, exist_ok=False)
    if attempt.name != ATTEMPT_ID:
        raise AcceptanceError("attempt reservation identity changed")
    return attempt


def validate_v9_start(start: Any, *, nonce: str) -> dict[str, Any]:
    """Validate exact dual-process readiness and return immutable IPC binding."""

    if not isinstance(start, Mapping):
        raise AcceptanceError("v9 worker start returned no mapping")
    config = v9_contract.load_canonical_config()
    root_pid = start.get("root_pid")
    worker_pid = start.get("worker_pid")
    if (
        start.get("started") is not True
        or start.get("pid") != worker_pid
        or isinstance(root_pid, bool)
        or not isinstance(root_pid, int)
        or root_pid <= 0
        or isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
        or worker_pid == root_pid
        or start.get("worker_direct_parent_pid") != root_pid
    ):
        raise AcceptanceError("v9 exact launcher/direct-child PID binding failed")
    assignment = start.get("job_assignment_proof")
    child_job = start.get("worker_child_job_proof")
    if (
        start.get("job_or_process_group_owned") is not True
        or start.get("created_suspended") is not True
        or not isinstance(assignment, Mapping)
        or assignment.get("assigned_before_resume") is not True
        or assignment.get("kill_on_close") is not True
        or not isinstance(child_job, Mapping)
        or child_job.get("same_retained_job") is not True
        or child_job.get("kill_on_close") is not True
        or start.get("launcher_process_handle_owned") is not True
        or start.get("worker_process_handle_owned") is not True
        or start.get("arbitrary_descendant_accepted") is not False
        or start.get("startup_descendant_pid") is not None
    ):
        raise AcceptanceError("v9 Job/handle/direct-child ownership proof failed")
    expected_creation = sha256_text(nonce)
    if start.get("creation_token_digest") != expected_creation:
        raise AcceptanceError("v9 creation-token binding failed")
    root_identity = _stable_identity(
        start.get("launcher_process_identity"), "launcher"
    )
    worker_identity = _stable_identity(
        start.get("worker_process_identity"), "worker"
    )
    expected_root = _stable_identity(
        config["process_topology"]["launcher"], "expected launcher"
    )
    expected_worker = _stable_identity(
        config["process_topology"]["worker"], "expected worker"
    )
    if root_identity != expected_root or worker_identity != expected_worker:
        raise AcceptanceError("v9 launcher or direct worker executable identity drifted")
    hash_fields = (
        "worker_instance_id",
        "command_digest",
        "launcher_process_handle_proof",
        "worker_process_handle_proof",
        "launcher_process_identity_digest",
        "worker_process_identity_digest",
    )
    if any(not _is_sha256(start.get(field)) for field in hash_fields):
        raise AcceptanceError("v9 process identity/proof digest is invalid")
    resumed = start.get("resumed_thread_ids")
    if (
        not isinstance(resumed, list)
        or not resumed
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in resumed)
    ):
        raise AcceptanceError("v9 suspended launcher resume proof is invalid")
    elapsed = start.get("elapsed_seconds")
    deadline = start.get("start_deadline_seconds")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or isinstance(deadline, bool)
        or not isinstance(deadline, (int, float))
        or not math.isfinite(float(deadline))
        or float(deadline) <= 0
        or float(elapsed) > float(deadline)
    ):
        raise AcceptanceError("v9 start telemetry/deadline is invalid")
    return {
        "root_pid": root_pid,
        "worker_pid": worker_pid,
        "worker_instance_id": start["worker_instance_id"],
        "launcher_process_identity_digest": start[
            "launcher_process_identity_digest"
        ],
        "process_identity_digest": start["worker_process_identity_digest"],
        "seen_request_ids": set(),
    }


def require_bound_success(
    envelope: Any, stage: str, binding: dict[str, Any]
) -> dict[str, Any]:
    """Reject replay, identity drift, unbounded writers, and late telemetry."""

    if not isinstance(envelope, Mapping) or set(envelope) != _BOUND_ENVELOPE_KEYS:
        raise AcceptanceError(f"{stage} v9 response envelope schema is not exact")
    if (
        envelope.get("root_pid") != binding["root_pid"]
        or envelope.get("worker_pid") != binding["worker_pid"]
        or envelope.get("worker_instance_id") != binding["worker_instance_id"]
        or envelope.get("launcher_process_identity_digest")
        != binding["launcher_process_identity_digest"]
        or envelope.get("process_identity_digest")
        != binding["process_identity_digest"]
    ):
        raise AcceptanceError(f"{stage} v9 response process binding drifted")
    request_id = envelope.get("request_id")
    seen = binding["seen_request_ids"]
    if not _is_sha256(request_id) or request_id in seen:
        raise AcceptanceError(f"{stage} v9 response request replay was rejected")
    writer = envelope.get("writer")
    if (
        not isinstance(writer, Mapping)
        or set(writer)
        != {"completed", "byte_count", "native_thread_id", "writer_thread_exited"}
        or writer.get("completed") is not True
        or writer.get("writer_thread_exited") is not True
        or isinstance(writer.get("byte_count"), bool)
        or not isinstance(writer.get("byte_count"), int)
        or writer["byte_count"] <= 0
        or isinstance(writer.get("native_thread_id"), bool)
        or not isinstance(writer.get("native_thread_id"), int)
        or writer["native_thread_id"] <= 0
    ):
        raise AcceptanceError(f"{stage} bounded writer telemetry is invalid")
    elapsed = envelope.get("elapsed_seconds")
    deadline = envelope.get("deadline_seconds")
    deadline_monotonic = envelope.get("deadline_monotonic")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or isinstance(deadline, bool)
        or not isinstance(deadline, (int, float))
        or not math.isfinite(float(deadline))
        or float(deadline) <= 0
        or float(elapsed) > float(deadline)
        or isinstance(deadline_monotonic, bool)
        or not isinstance(deadline_monotonic, (int, float))
        or not math.isfinite(float(deadline_monotonic))
    ):
        raise AcceptanceError(f"{stage} finite response deadline telemetry is invalid")
    seen.add(request_id)
    try:
        return v8_harness.require_success(envelope, stage)
    except Exception as exc:
        raise AcceptanceError(str(exc)) from exc


def _add_expected(expected: dict[str, str], relative: str, digest: str) -> None:
    if not _is_sha256(digest):
        raise AcceptanceError(f"protected hash is invalid: {relative}")
    prior = expected.get(relative)
    if prior is not None and prior != digest:
        raise AcceptanceError(f"conflicting protected hash: {relative}")
    expected[relative] = digest


def protected_boundary_snapshot(
    *, accepted_harness_audit_sha256: str
) -> dict[str, Any]:
    """Rehash v2-v9, consumed attempt_01, audits, harness, and production."""

    config = v9_contract.load_canonical_config()
    expected: dict[str, str] = {}
    for group in ("preserved_v8_boundary", "preserved_attempt_and_audit_bytes"):
        for relative, digest in config[group].items():
            _add_expected(expected, relative, digest)
    v9_seal_relative = config["fresh_audit_contract"]["required_seal_manifest_path"]
    v9_seal_path = ROOT / v9_seal_relative
    v9_seal = v9_contract.verify_seal_manifest(config, v9_seal_path)
    _add_expected(expected, v9_seal_relative, v9_contract.sha256_file(v9_seal_path))
    for relative, record in v9_seal["files"].items():
        _add_expected(expected, relative, record["sha256"])
    _add_expected(
        expected,
        V9_AUDIT_AUTHORIZATION_PATH.relative_to(ROOT).as_posix(),
        EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
    )
    _add_expected(
        expected,
        V8_WORKER_AUDIT_AUTHORIZATION_PATH.relative_to(ROOT).as_posix(),
        EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256,
    )
    old_seal = v8_harness.verify_harness_seal()
    _add_expected(
        expected,
        v8_harness.HARNESS_SEAL_MANIFEST_PATH.relative_to(ROOT).as_posix(),
        v9_contract.sha256_file(v8_harness.HARNESS_SEAL_MANIFEST_PATH),
    )
    for record in old_seal["files"]:
        _add_expected(expected, record["path"], record["sha256"])
    _add_expected(
        expected,
        V8_HARNESS_AUDIT_AUTHORIZATION_PATH.relative_to(ROOT).as_posix(),
        EXPECTED_V8_HARNESS_AUDIT_AUTHORIZATION_SHA256,
    )
    harness_seal = verify_harness_seal()
    _add_expected(
        expected,
        HARNESS_SEAL_MANIFEST_PATH.relative_to(ROOT).as_posix(),
        v9_contract.sha256_file(HARNESS_SEAL_MANIFEST_PATH),
    )
    for record in harness_seal["files"]:
        _add_expected(expected, record["path"], record["sha256"])
    _add_expected(
        expected,
        HARNESS_AUDIT_AUTHORIZATION_PATH.relative_to(ROOT).as_posix(),
        accepted_harness_audit_sha256,
    )
    _add_expected(
        expected,
        "Voice/sidecars/kira_approved_voice_routing.json",
        EXPECTED_PRODUCTION_ROUTING_SHA256,
    )
    records: dict[str, Any] = {}
    for relative, expected_sha in sorted(expected.items()):
        path = ROOT / relative
        actual = v9_contract.sha256_file(path) if path.is_file() else None
        records[relative] = {
            "expected_sha256": expected_sha,
            "actual_sha256": actual,
            "matched": actual == expected_sha,
        }
    return {
        "captured_utc": utc_now(),
        "passed": all(record["matched"] for record in records.values()),
        "records": records,
        "production_routing_sha256": records[
            "Voice/sidecars/kira_approved_voice_routing.json"
        ]["actual_sha256"],
        "v9_audit_sha256": records[
            V9_AUDIT_AUTHORIZATION_PATH.relative_to(ROOT).as_posix()
        ]["actual_sha256"],
        "v8_worker_audit_sha256": records[
            V8_WORKER_AUDIT_AUTHORIZATION_PATH.relative_to(ROOT).as_posix()
        ]["actual_sha256"],
        "attempt_01_reused": False,
    }


def _stage_call(
    report: dict[str, Any],
    ledger: AppendOnlyLedger,
    stage: str,
    operation: Callable[[], Any],
) -> Any:
    return v8_harness._stage_call(report, ledger, stage, operation)


def execute_live(
    *, playback: bool = False, accepted_harness_audit_sha256: str = ""
) -> tuple[int, Path]:
    """Consume only attempt_02 and run the exact serialized v8 semantic sequence."""

    gates = validate_static_and_capability_gates(
        playback=playback,
        accepted_harness_audit_sha256=accepted_harness_audit_sha256,
    )
    attempt = reserve_attempt_02()
    ledger = AppendOnlyLedger(attempt)
    write_once_json(
        attempt / "RUN_AUTHORIZATION.json",
        {
            "schema_version": 1,
            "harness_id": HARNESS_ID,
            "attempt_id": ATTEMPT_ID,
            "reserved_utc": utc_now(),
            **gates,
        },
    )
    ledger.append("authorization", gates)
    report: dict[str, Any] = {
        "schema_version": 1,
        "harness_id": HARNESS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_utc": utc_now(),
        "status": "RUNNING",
        "accepted": False,
        "playback_requested": playback,
        "playback_performed": False,
        "owner_hearing_proven": False,
        "production_routing_changed": False,
        "model_identity": {"model": EXPECTED_MODEL, "digest": EXPECTED_MODEL_DIGEST},
        "v9_candidate_config_sha256": v9_contract.CANONICAL_CONFIG_SHA256,
        "v9_audit_authorization_sha256": EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
        "v8_worker_audit_authorization_sha256": (
            EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256
        ),
        "fresh_harness_audit_sha256": accepted_harness_audit_sha256,
        "consumed_attempt_01_reused": False,
        "stages": {},
        "errors": [],
    }
    coordinator: BlackwellV9Coordinator | None = None
    started_worker = False
    main_sequence_passed = False
    cleanup_value: dict[str, Any] | None = None
    close_value: dict[str, Any] | None = None
    binding: dict[str, Any] | None = None
    try:
        protected_before = protected_boundary_snapshot(
            accepted_harness_audit_sha256=accepted_harness_audit_sha256
        )
        report["protected_boundary_before"] = protected_before
        if protected_before["passed"] is not True:
            raise AcceptanceError("protected v2-v9/attempt01/production bytes drifted")
        report["resources_before"] = v8_harness.capture_host_resources(
            "before_v9_attempt_02_worker"
        )
        before = v8_harness.ollama_residency_snapshot("before_v9_attempt_02_worker")
        report["residency_before"] = before
        ledger.append(
            "pre_live", {"resources": report["resources_before"], "residency": before}
        )
        if before["all_models_absent"] is not True:
            raise AcceptanceError("a model was resident before owned attempt_02")

        nonce = sha256_text(f"{HARNESS_ID}:{ATTEMPT_ID}:{uuid.uuid4().hex}")
        owner = f"{HARNESS_ID}:owner:{uuid.uuid4().hex}"
        session = f"{HARNESS_ID}:session:{uuid.uuid4().hex}"
        token = f"{HARNESS_ID}:token:{uuid.uuid4().hex}"
        coordinator = BlackwellV9Coordinator.bounded_engineering_candidate(
            nonce=nonce,
            accepted_v9_audit_sha256=EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
            accepted_v8_worker_audit_sha256=(
                EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256
            ),
        )
        start = _stage_call(report, ledger, "worker_start", coordinator.start)
        started_worker = True
        binding = validate_v9_start(start, nonce=nonce)
        report["v9_process_binding"] = {
            key: value for key, value in binding.items() if key != "seen_request_ids"
        }

        loaded_env = _stage_call(
            report, ledger, "voice_load", lambda: coordinator.load(owner=owner)
        )
        loaded = require_bound_success(loaded_env, "voice_load", binding)
        if loaded.get("state") != "LOADED_CUDA":
            raise AcceptanceError("voice did not load on exact CUDA")
        component_fingerprint = loaded.get("component_fingerprint")
        model_generation = loaded.get("model_generation")
        condition_digest = loaded.get("condition_digest")
        if not all(
            _is_sha256(value)
            for value in (component_fingerprint, model_generation, condition_digest)
        ):
            raise AcceptanceError("voice component/model/condition hashes are invalid")

        parked_env = _stage_call(
            report,
            ledger,
            "voice_park_cpu",
            lambda: coordinator.park(
                reason="one exact Qwen 3.5 current-answer generation"
            ),
        )
        parked = require_bound_success(parked_env, "voice_park_cpu", binding)
        if (
            parked.get("state") != "PARKED_CPU"
            or parked.get("model_generation") != model_generation
            or parked.get("component_fingerprint") != component_fingerprint
            or (parked.get("component_transfer") or {}).get("from_device") != "cuda"
            or (parked.get("component_transfer") or {}).get("to_device") != "cpu"
        ):
            raise AcceptanceError("voice CPU park/component ledger is not exact")

        qwen_load_env = _stage_call(
            report,
            ledger,
            "qwen_load",
            lambda: coordinator.qwen_load(
                owner=owner,
                session=session,
                token=token,
                ttl_seconds=QWEN_TTL_SECONDS,
            ),
        )
        qwen_load = require_bound_success(qwen_load_env, "qwen_load", binding)
        if qwen_load.get("state") != "QWEN_OWNED":
            raise AcceptanceError("exact Qwen ownership did not commit")

        qwen_stream_env = _stage_call(
            report,
            ledger,
            "qwen_single_generation",
            lambda: coordinator.qwen_stream(
                owner=owner,
                session=session,
                token=token,
                messages=[dict(item) for item in MESSAGES],
            ),
        )
        qwen_stream = require_bound_success(
            qwen_stream_env, "qwen_single_generation", binding
        )
        public_text = v8_harness.validate_public_text(
            qwen_stream.get("text"), qwen_stream.get("text_sha256")
        )
        if (
            qwen_stream.get("state") != "PARKED_CPU"
            or (qwen_stream.get("residency_precommit") or {}).get("records") != []
            or (qwen_stream.get("residency_after") or {}).get("records") != []
        ):
            raise AcceptanceError("Qwen keep_alive=0 unload was not verified")
        after_qwen = v8_harness.ollama_residency_snapshot(
            "after_qwen_before_voice_resume_attempt02"
        )
        report["qwen_unload_verification"] = {
            "worker_precommit": qwen_stream["residency_precommit"],
            "worker_after": qwen_stream["residency_after"],
            "independent_after": after_qwen,
            "verified": after_qwen["all_models_absent"] is True,
        }
        ledger.append("qwen_unload_verified", report["qwen_unload_verification"])
        if after_qwen["all_models_absent"] is not True:
            raise AcceptanceError("independent Qwen unload check found residency")
        report["public_text"] = public_text
        report["public_text_sha256"] = sha256_text(public_text)
        report["raw_qwen_text_equals_public_text"] = qwen_stream["text"] == public_text
        report["spoken_text_equals_public_text"] = True

        resumed_env = _stage_call(
            report,
            ledger,
            "voice_resume_cuda",
            lambda: coordinator.resume(
                reason="Qwen absence verified before exact synthesis"
            ),
        )
        resumed = require_bound_success(resumed_env, "voice_resume_cuda", binding)
        if (
            resumed.get("state") != "LOADED_CUDA"
            or resumed.get("model_generation") != model_generation
            or resumed.get("component_fingerprint") != component_fingerprint
            or (resumed.get("component_transfer") or {}).get("from_device") != "cpu"
            or (resumed.get("component_transfer") or {}).get("to_device") != "cuda"
        ):
            raise AcceptanceError("voice CUDA resume/component ledger is not exact")

        synthesis_request = {
            "text": public_text,
            "text_sha256": sha256_text(public_text),
            "input_channel": "public_spoken_only",
            "profile_sha256": v8_harness.EXACT_PROFILE_SHA256,
            "reference_sha256": v8_harness.EXACT_REFERENCE_SHA256,
            "condition_digest": condition_digest,
        }
        synthesis_env = _stage_call(
            report,
            ledger,
            "exact_text_synthesis",
            lambda: coordinator.synthesize(synthesis_request),
        )
        synthesis = require_bound_success(
            synthesis_env, "exact_text_synthesis", binding
        )
        if (
            synthesis.get("device") != "cuda"
            or synthesis.get("text_sha256") != sha256_text(public_text)
            or synthesis.get("profile_sha256") != v8_harness.EXACT_PROFILE_SHA256
            or synthesis.get("reference_sha256") != v8_harness.EXACT_REFERENCE_SHA256
            or synthesis.get("generic_voice_used") is not False
            or synthesis.get("sapi_voice_used") is not False
            or synthesis.get("fallback_used") is not False
            or synthesis.get("model_generation") != model_generation
            or synthesis.get("component_fingerprint") != component_fingerprint
        ):
            raise AcceptanceError("synthesis used a non-exact component/text/route")
        lease = synthesis.get("artifact_lease")
        if not isinstance(lease, Mapping):
            raise AcceptanceError("synthesis returned no retained WAV lease")
        report["wav"] = v8_harness.validate_wav_lease(
            lease, sha256_text(public_text)
        )
        report["voice_hashes"] = {
            "model_generation": model_generation,
            "component_fingerprint": component_fingerprint,
            "condition_digest": condition_digest,
            "profile_sha256": v8_harness.EXACT_PROFILE_SHA256,
            "reference_sha256": v8_harness.EXACT_REFERENCE_SHA256,
            "wav_sha256": report["wav"]["artifact_sha256"],
        }
        ledger.append(
            "wav_verified",
            {"wav": report["wav"], "voice_hashes": report["voice_hashes"]},
        )

        if playback:
            playback_id = sha256_text(
                f"{HARNESS_ID}:{ATTEMPT_ID}:{lease['artifact_sha256']}:{uuid.uuid4().hex}"
            )
            playback_env = _stage_call(
                report,
                ledger,
                "optional_playback",
                lambda: coordinator.playback(lease, playback_id=playback_id),
            )
            played = require_bound_success(
                playback_env, "optional_playback", binding
            )
            telemetry = played.get("playback")
            if (
                not isinstance(telemetry, Mapping)
                or telemetry.get("artifact_sha256") != lease["artifact_sha256"]
                or telemetry.get("played_memory_sha256") != lease["artifact_sha256"]
                or telemetry.get("route") != "blackwell_gpu"
                or telemetry.get("device") != "cuda"
                or telemetry.get("generic_voice_used") is not False
                or telemetry.get("sapi_voice_used") is not False
                or telemetry.get("fallback_used") is not False
                or telemetry.get("playback_process_in_inherited_job") is not True
                or telemetry.get("owned_copy_deleted_after_return") is not True
                or telemetry.get("owner_hearing_proven") is not False
            ):
                raise AcceptanceError("playback route/bytes/Job/hearing truth is not exact")
            report["playback_performed"] = True
            report["playback"] = dict(telemetry)
        else:
            report["playback"] = {
                "requested": False,
                "performed": False,
                "reason": "separate playback capability not requested",
            }
        main_sequence_passed = True
    except BaseException as exc:
        report["errors"].append(
            {
                "phase": "main_sequence",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
    finally:
        cleanup_started_utc = utc_now()
        cleanup_started = time.monotonic()
        process = None if coordinator is None else getattr(coordinator, "process", None)
        process_reports_running = False
        if process is not None:
            try:
                process_reports_running = bool(process.is_running)
            except BaseException:
                process_reports_running = False
        if coordinator is not None and (started_worker or process_reports_running):
            try:
                cleanup_env = coordinator.cleanup(
                    reason="v9_bounded_live_acceptance_attempt02_finally"
                )
                if binding is not None:
                    require_bound_success(cleanup_env, "finally_cleanup", binding)
                cleanup_value = dict(cleanup_env)
            except BaseException as exc:
                report["errors"].append(
                    {
                        "phase": "finally_cleanup",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
        if coordinator is not None:
            try:
                close_value = coordinator.close()
            except BaseException as exc:
                report["errors"].append(
                    {
                        "phase": "finally_close",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
        try:
            final_residency = v8_harness.wait_for_zero_residency()
        except BaseException as exc:
            final_residency = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            report["errors"].append(
                {
                    "phase": "finally_residency",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        try:
            residue = v8_harness.owned_runtime_residue()
        except BaseException as exc:
            residue = {
                "zero_file_residue": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            report["errors"].append(
                {
                    "phase": "finally_residue",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        try:
            final_resources = v8_harness.capture_host_resources(
                "finally_after_v9_attempt02_cleanup"
            )
        except BaseException as exc:
            final_resources = {"error_type": type(exc).__name__, "error": str(exc)}
            report["errors"].append(
                {
                    "phase": "finally_resources",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        try:
            protected_after = protected_boundary_snapshot(
                accepted_harness_audit_sha256=accepted_harness_audit_sha256
            )
            protected_unchanged = bool(
                protected_after.get("passed") is True
                and report.get("protected_boundary_before", {}).get("records")
                == protected_after.get("records")
            )
            if not protected_unchanged:
                report["errors"].append(
                    {
                        "phase": "finally_protected_boundary",
                        "error_type": "AcceptanceError",
                        "error": "protected v2-v9/attempt01/production bytes changed",
                    }
                )
        except BaseException as exc:
            protected_after = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            protected_unchanged = False
            report["errors"].append(
                {
                    "phase": "finally_protected_boundary",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        semantic_cleanup = (
            isinstance(cleanup_value, Mapping)
            and isinstance(cleanup_value.get("value"), Mapping)
            and cleanup_value["value"].get("unloaded") is True
            and cleanup_value["value"].get("cleanup_debt") is False
        )
        process_closed = bool(
            isinstance(close_value, Mapping)
            and close_value.get("root_exited") is True
            and close_value.get("worker_child_exited") is True
            and close_value.get("entire_bound_tree_exited") is True
            and close_value.get("worker_child_handle_closed") is True
            and close_value.get("job_handle_closed") is True
            and close_value.get("root_standard_streams_closed") is True
            and close_value.get("arbitrary_descendant_accepted") is False
            and close_value.get("errors") == []
        )
        finally_cleanup = {
            "started_utc": cleanup_started_utc,
            "ended_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - cleanup_started,
            "cleanup_result": cleanup_value,
            "close_result": close_value,
            "semantic_unload_proven": semantic_cleanup,
            "exact_launcher_and_worker_exited": process_closed,
            "qwen_zero_residency": final_residency,
            "owned_runtime_residue": residue,
            "resources_after": final_resources,
            "protected_boundary_after": protected_after,
            "protected_boundary_unchanged": protected_unchanged,
        }
        finally_cleanup["zero_residue_proven"] = bool(
            semantic_cleanup
            and process_closed
            and final_residency.get("passed") is True
            and residue.get("zero_file_residue") is True
            and "error_type" not in final_resources
            and protected_unchanged
        )
        report["finally_cleanup"] = finally_cleanup
        try:
            ledger.append("finally_cleanup", finally_cleanup)
        except BaseException as exc:
            report["errors"].append(
                {
                    "phase": "finally_ledger",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    report["ended_utc"] = utc_now()
    report["event_chain"] = list(ledger.records)
    report["accepted"] = bool(
        main_sequence_passed
        and not report["errors"]
        and report["finally_cleanup"]["zero_residue_proven"] is True
    )
    if report["accepted"]:
        report["status"] = (
            "ENGINEERING_PASS_PLAYBACK_COMPLETED_OWNER_HEARING_NOT_CLAIMED"
            if playback
            else "ENGINEERING_PASS_NO_PLAYBACK"
        )
    else:
        report["status"] = "ENGINEERING_FAIL_CLEANUP_RECORDED"
    final_path = attempt / "FINAL_REPORT.json"
    write_once_json(final_path, report)
    return (0 if report["accepted"] else 1), final_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="consume the sole append-only attempt_02 after every exact gate",
    )
    parser.add_argument(
        "--playback",
        action="store_true",
        help="play the exact verified WAV once; requires a separate capability",
    )
    parser.add_argument(
        "--accepted-harness-audit-sha256",
        default="",
        help="exact SHA-256 of the future different-agent harness audit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute_live:
        sys.stderr.write(
            "Blackwell v9 attempt_02 is default-off; --execute-live, exact audits, "
            "and both per-run live capabilities are required.\n"
        )
        return 64
    try:
        code, final_path = execute_live(
            playback=bool(args.playback),
            accepted_harness_audit_sha256=args.accepted_harness_audit_sha256,
        )
    except BaseException as exc:
        sys.stderr.write(
            "Blackwell v9 attempt_02 refused before reservation: "
            f"{type(exc).__name__}: {exc}\n"
        )
        return 65
    sys.stdout.write(str(final_path) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
