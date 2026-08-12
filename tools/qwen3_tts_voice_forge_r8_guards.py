"""Inert R8 coherence guards for the TemporaryAI Qwen3-TTS voice forge.

R8 is an append-only, static-only successor to the rejected R7 package.  It
loads the exact sealed R7 guard and adds only the four independently reported
coherence repairs.  There is intentionally no R8 parent or worker integration;
``verify_execution_authorization`` always fails closed after validating a
document.  This module uses only Python's standard library.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import time
import types
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


HASH = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
ZERO_HASH = "0" * 64

R8_PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v8.json"
)
R7_PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json"
)
R7_PAYLOAD_MANIFEST_SHA256 = (
    "509d2b802310b1c0e075039da28e18744dad59bccd816f7623a8b0963169e6eb"
)
R7_REJECTED_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_INDEPENDENT_AUDIT_20260810.md"
)
R7_REJECTED_AUDIT_SHA256 = (
    "577fd3cf047fbaa0abddeea7dfb7f86602b6b94f97b9f43a724d77affc7ab966"
)
R7_GUARD_REL = Path("tools/qwen3_tts_voice_forge_r7_guards.py")
R7_GUARD_SHA256 = (
    "a92c9cf4fd7d6058a1a0f901725480a13380004478577b543b69475d56b5fc60"
)
R8_AUTHORIZATION_ROOT_REL = Path(
    "Data/voice/authorizations/qwen3_tts_voice_forge_v8"
)

MAX_AUTHORIZATION_SECONDS = 15 * 60
MAX_AUDIT_TO_ISSUE_SECONDS = 24 * 60 * 60
ELAPSED_TOLERANCE_SECONDS = 0.001
UTC_MONOTONIC_TOLERANCE_SECONDS = 0.250
MAX_PARENT_WALL_SECONDS = 1860.0
UINT32_MAX = 2**32 - 1
UINT64_MAX = 2**64 - 1


class R8GuardError(RuntimeError):
    """An R8 static trust or evidence boundary failed closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R8GuardError(f"duplicate R8 JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise R8GuardError(f"non-finite R8 JSON constant: {value}")


def strict_json_bytes(payload: bytes, label: str) -> Any:
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except R8GuardError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R8GuardError(f"{label} is not strict finite UTF-8 JSON") from exc


def strict_read_json(
    path: Path, *, expected_sha256: str | None = None, label: str
) -> Any:
    if not path.is_file() or path.is_symlink():
        raise R8GuardError(f"{label} is missing or unsafe")
    payload = path.read_bytes()
    if expected_sha256 is not None and sha256_bytes(payload) != require_hash(
        expected_sha256, f"{label} expected hash"
    ):
        raise R8GuardError(f"{label} differs from its exact hash")
    return strict_json_bytes(payload, label)


def require_exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = set(value) if isinstance(value, dict) else set()
        raise R8GuardError(
            f"{label} fields are not exact; "
            f"missing={sorted(keys-actual)}, extra={sorted(actual-keys)}"
        )
    return value


def require_hash(value: Any, label: str, *, nonzero: bool = True) -> str:
    text = str(value or "")
    if not HASH.fullmatch(text) or (nonzero and text == ZERO_HASH):
        raise R8GuardError(f"{label} is not an exact nonzero SHA-256")
    return text


def require_id(value: Any, label: str) -> str:
    text = str(value or "")
    if not SAFE_ID.fullmatch(text):
        raise R8GuardError(f"{label} is not one safe opaque ID")
    return text


def finite_number(
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise R8GuardError(f"{label} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise R8GuardError(f"{label} is not finite")
    if minimum is not None and number < minimum:
        raise R8GuardError(f"{label} is below its closed lower bound")
    if maximum is not None and number > maximum:
        raise R8GuardError(f"{label} is above its closed upper bound")
    return number


def exact_int(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = UINT64_MAX,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise R8GuardError(f"{label} is not an exact bounded integer")
    return value


def parse_utc(value: Any, label: str) -> datetime:
    text = str(value or "")
    if not text.endswith("Z"):
        raise R8GuardError(f"{label} is not exact UTC Z time")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise R8GuardError(f"{label} is not an exact timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise R8GuardError(f"{label} is not UTC")
    return parsed


def inside(root: Path, value: str | Path, label: str) -> Path:
    root = root.resolve()
    candidate = Path(str(value))
    result = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise R8GuardError(f"{label} escaped its exact root") from exc
    return result


def project_relative(project_root: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise R8GuardError(f"{label} escaped the project") from exc


def _load_exact_r7() -> Any:
    path = Path(__file__).resolve().parents[1] / R7_GUARD_REL
    payload = path.read_bytes()
    if sha256_bytes(payload) != R7_GUARD_SHA256:
        raise R8GuardError("sealed R7 guard dependency drifted")
    module = types.ModuleType("qwen3_tts_voice_forge_r7_for_r8")
    module.__file__ = str(path)
    module.__package__ = ""
    exec(compile(payload, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
    if sha256_file(path) != R7_GUARD_SHA256:
        raise R8GuardError("sealed R7 guard changed during exact import")
    return module


_SEALED_R7: Any | None = None


def sealed_r7() -> Any:
    global _SEALED_R7
    if _SEALED_R7 is None:
        _SEALED_R7 = _load_exact_r7()
    return _SEALED_R7


@dataclass(frozen=True, slots=True)
class ClockSample:
    utc: datetime
    monotonic_ns: int
    clock_id_sha256: str


class SystemClockAuthority:
    """Internally sample wall and monotonic time for local freshness.

    This prevents authorization documents or callers from supplying the time
    used for production verification. It does not claim the host is tamper-proof.
    """

    CLOCK_ID_SHA256 = sha256_bytes(b"voice-forge-r8-system-wall-monotonic-clock-v1")

    def sample(self) -> ClockSample:
        before = time.monotonic_ns()
        now = datetime.now(timezone.utc)
        after = time.monotonic_ns()
        if after <= before or before <= 0:
            raise R8GuardError("R8 trusted monotonic clock did not advance safely")
        return ClockSample(now, after, self.CLOCK_ID_SHA256)


R8_MANIFEST_KEYS = {
    "schema",
    "status",
    "execution_allowed",
    "self_authorization_allowed",
    "parent_worker_integration_present",
    "revision",
    "predecessor_payload_manifest_path",
    "predecessor_payload_manifest_sha256",
    "rejected_r7_audit_path",
    "rejected_r7_audit_sha256",
    "files",
}

AUDITOR_SEPARATION_KEYS = {
    "fresh_independent_process",
    "subject_sources_authored_by_auditor",
}

AUDIT_DECISION_KEYS = {
    "schema",
    "status",
    "authoritative_decision",
    "static_only",
    "runtime_execution_performed",
    "audit_authorizes_execution",
    "unresolved_blockers",
    "payload_manifest_path",
    "payload_manifest_sha256",
    "payload_file_inventory_sha256",
    "rejected_r7_audit_path",
    "rejected_r7_audit_sha256",
    "subject_sha256",
    "auditor_identity_sha256",
    "auditor_separation",
    "audit_report_path",
    "audit_report_sha256",
    "completed_utc",
}

AUTHORIZATION_KEYS = {
    "schema",
    "status",
    "execution_allowed",
    "one_use",
    "payload_manifest_path",
    "payload_manifest_sha256",
    "independent_audit_decision_path",
    "independent_audit_decision_sha256",
    "independent_audit_subject_sha256",
    "independent_auditor_identity_sha256",
    "independent_audit_path",
    "independent_audit_sha256",
    "rejected_r7_audit_path",
    "rejected_r7_audit_sha256",
    "bundle_id",
    "run_id",
    "authorization_nonce_sha256",
    "worker_instance_nonce_sha256",
    "generation_seed",
    "clock_id_sha256",
    "ttl_seconds",
    "issued_utc",
    "expires_utc",
    "issued_monotonic_ns",
    "expires_monotonic_ns",
}


def verify_payload_manifest(
    *, project_root: Path, expected_manifest_sha256: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    project_root = project_root.resolve()
    manifest = strict_read_json(
        project_root / R8_PAYLOAD_MANIFEST_REL,
        expected_sha256=expected_manifest_sha256,
        label="R8 immutable payload manifest",
    )
    require_exact_keys(manifest, R8_MANIFEST_KEYS, "R8 payload manifest")
    if (
        manifest["schema"] != "qwen3_tts_voice_forge_payload_manifest_v8"
        or manifest["status"]
        != "INERT_STATIC_GUARD_SUCCESSOR_REQUIRES_FRESH_AUDIT_AND_PARENT_WORKER_INTEGRATION"
        or manifest["execution_allowed"] is not False
        or manifest["self_authorization_allowed"] is not False
        or manifest["parent_worker_integration_present"] is not False
        or manifest["predecessor_payload_manifest_path"]
        != R7_PAYLOAD_MANIFEST_REL.as_posix()
        or manifest["predecessor_payload_manifest_sha256"]
        != R7_PAYLOAD_MANIFEST_SHA256
        or manifest["rejected_r7_audit_path"] != R7_REJECTED_AUDIT_REL.as_posix()
        or manifest["rejected_r7_audit_sha256"] != R7_REJECTED_AUDIT_SHA256
    ):
        raise R8GuardError("R8 payload is executable, self-authorizing, or unbound")
    if sha256_file(project_root / R7_PAYLOAD_MANIFEST_REL) != R7_PAYLOAD_MANIFEST_SHA256:
        raise R8GuardError("sealed R7 payload manifest drifted")
    if sha256_file(project_root / R7_REJECTED_AUDIT_REL) != R7_REJECTED_AUDIT_SHA256:
        raise R8GuardError("sealed rejected R7 audit drifted")
    predecessor = strict_read_json(
        project_root / R7_PAYLOAD_MANIFEST_REL,
        expected_sha256=R7_PAYLOAD_MANIFEST_SHA256,
        label="sealed R7 payload manifest",
    )
    predecessor_paths = {str(row["path"]) for row in predecessor.get("files", [])}
    expected_paths = predecessor_paths | {
        R7_PAYLOAD_MANIFEST_REL.as_posix(),
        R7_REJECTED_AUDIT_REL.as_posix(),
        "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R8_REPAIR_BOUNDARY_20260810.md",
        "tools/qwen3_tts_voice_forge_r8_guards.py",
    }
    rows = manifest["files"]
    if not isinstance(rows, list):
        raise R8GuardError("R8 payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        require_exact_keys(row, {"path", "bytes", "sha256"}, "R8 payload row")
        rel = str(row["path"] or "")
        target = inside(project_root, rel, "R8 payload file")
        if (
            not rel
            or rel in indexed
            or rel == R8_PAYLOAD_MANIFEST_REL.as_posix()
            or project_relative(project_root, target, "R8 payload file") != rel
            or not target.is_file()
            or target.is_symlink()
            or exact_int(row["bytes"], f"R8 payload {rel} bytes") != target.stat().st_size
            or sha256_file(target) != require_hash(row["sha256"], f"R8 payload {rel}")
        ):
            raise R8GuardError(f"R8 immutable payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != expected_paths:
        raise R8GuardError("R8 immutable payload inventory is not the exact predecessor closure")
    return manifest, indexed


def payload_inventory_sha256(manifest: dict[str, Any]) -> str:
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R8GuardError("R8 payload inventory is not a list")
    return canonical_sha256(rows)


def audit_subject(
    *, manifest_sha256: str, inventory_sha256: str
) -> dict[str, Any]:
    return {
        "payload_manifest_path": R8_PAYLOAD_MANIFEST_REL.as_posix(),
        "payload_manifest_sha256": require_hash(manifest_sha256, "R8 audit payload"),
        "payload_file_inventory_sha256": require_hash(
            inventory_sha256, "R8 audit inventory"
        ),
        "rejected_r7_audit_path": R7_REJECTED_AUDIT_REL.as_posix(),
        "rejected_r7_audit_sha256": R7_REJECTED_AUDIT_SHA256,
    }


def validate_independent_audit_v8(
    *,
    project_root: Path,
    audit_decision_path: Path,
    expected_audit_decision_sha256: str,
    expected_manifest_sha256: str,
    expected_inventory_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    rel = project_relative(project_root, audit_decision_path, "R8 audit decision")
    if not rel.startswith("RecoverySprint/"):
        raise R8GuardError("R8 audit decision is outside append-only evidence")
    if not audit_decision_path.is_file() or audit_decision_path.is_symlink():
        raise R8GuardError("R8 audit decision is missing or unsafe")
    decision_hash = require_hash(expected_audit_decision_sha256, "R8 audit hash")
    payload = audit_decision_path.read_bytes()
    audit = strict_json_bytes(payload, "R8 independent audit decision")
    if sha256_bytes(payload) != decision_hash or payload != canonical_bytes(audit) + b"\n":
        raise R8GuardError("R8 audit decision is not canonical JSON plus LF")
    require_exact_keys(audit, AUDIT_DECISION_KEYS, "R8 independent audit decision")
    separation = require_exact_keys(
        audit["auditor_separation"], AUDITOR_SEPARATION_KEYS, "R8 auditor separation"
    )
    subject = audit_subject(
        manifest_sha256=expected_manifest_sha256,
        inventory_sha256=expected_inventory_sha256,
    )
    if (
        audit["schema"] != "qwen3_tts_voice_forge_independent_static_audit_v8"
        or audit["status"] != "FINAL"
        or audit["authoritative_decision"] != "ACCEPT_STATIC_ONLY"
        or audit["static_only"] is not True
        or audit["runtime_execution_performed"] is not False
        or audit["audit_authorizes_execution"] is not False
        or audit["unresolved_blockers"] != []
        or any(audit[key] != value for key, value in subject.items())
        or audit["subject_sha256"] != canonical_sha256(subject)
        or separation["fresh_independent_process"] is not True
        or separation["subject_sources_authored_by_auditor"] is not False
    ):
        raise R8GuardError("R8 audit is not one closed static acceptance")
    require_hash(audit["auditor_identity_sha256"], "R8 auditor identity")
    completed = parse_utc(audit["completed_utc"], "R8 audit completion")
    report_rel = str(audit["audit_report_path"] or "")
    report = inside(project_root, report_rel, "R8 audit report")
    if (
        not report_rel.startswith("System/Docs/")
        or not report.is_file()
        or report.is_symlink()
        or sha256_file(report)
        != require_hash(audit["audit_report_sha256"], "R8 audit report hash")
    ):
        raise R8GuardError("R8 audit report binding mismatch")
    return audit, {
        "decision_path": rel,
        "decision_sha256": decision_hash,
        "subject_sha256": audit["subject_sha256"],
        "auditor_identity_sha256": audit["auditor_identity_sha256"],
        "report_path": report_rel,
        "report_sha256": audit["audit_report_sha256"],
        "completed_utc": completed,
    }


def _trusted_sample() -> ClockSample:
    sample = SystemClockAuthority().sample()
    if (
        not isinstance(sample, ClockSample)
        or sample.utc.tzinfo != timezone.utc
        or exact_int(sample.monotonic_ns, "R8 trusted monotonic time", minimum=1) <= 0
        or sample.clock_id_sha256 != SystemClockAuthority.CLOCK_ID_SHA256
    ):
        raise R8GuardError("R8 trusted clock returned an invalid sample")
    return sample


def validate_execution_authorization_document(
    *,
    project_root: Path,
    authorization_path: Path,
    expected_authorization_sha256: str,
    expected_manifest_sha256: str,
    expected_inventory_sha256: str,
    bundle_id: str,
    run_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one inert R8 bearer document; this never grants execution."""

    project_root = project_root.resolve()
    authorization_path = authorization_path.resolve()
    rel = project_relative(project_root, authorization_path, "R8 authorization")
    if not rel.startswith(R8_AUTHORIZATION_ROOT_REL.as_posix() + "/"):
        raise R8GuardError("R8 authorization is outside its append-only authority root")
    if not authorization_path.is_file() or authorization_path.is_symlink():
        raise R8GuardError("R8 authorization is missing or unsafe")
    auth_hash = require_hash(expected_authorization_sha256, "R8 authorization hash")
    payload = authorization_path.read_bytes()
    authorization = strict_json_bytes(payload, "R8 execution authorization")
    if sha256_bytes(payload) != auth_hash or payload != canonical_bytes(authorization) + b"\n":
        raise R8GuardError("R8 authorization is not canonical JSON plus LF")
    require_exact_keys(authorization, AUTHORIZATION_KEYS, "R8 execution authorization")
    if (
        authorization["schema"] != "qwen3_tts_voice_forge_execution_authorization_v8"
        or authorization["status"]
        != "FRESH_R8_STATIC_AUDIT_ACCEPTED_ONE_BOUNDED_RUN_DOCUMENT_ONLY"
        or authorization["execution_allowed"] is not True
        or authorization["one_use"] is not True
        or authorization["payload_manifest_path"] != R8_PAYLOAD_MANIFEST_REL.as_posix()
        or authorization["payload_manifest_sha256"] != expected_manifest_sha256
        or authorization["rejected_r7_audit_path"] != R7_REJECTED_AUDIT_REL.as_posix()
        or authorization["rejected_r7_audit_sha256"] != R7_REJECTED_AUDIT_SHA256
        or authorization["bundle_id"] != require_id(bundle_id, "R8 bundle ID")
        or authorization["run_id"] != require_id(run_id, "R8 run ID")
    ):
        raise R8GuardError("R8 authorization scope or predecessor binding mismatch")
    require_hash(authorization["authorization_nonce_sha256"], "R8 authorization nonce")
    require_hash(authorization["worker_instance_nonce_sha256"], "R8 worker nonce")
    exact_int(authorization["generation_seed"], "R8 generation seed", maximum=2**63 - 1)
    audit_path = inside(
        project_root,
        authorization["independent_audit_decision_path"],
        "R8 authorized audit decision",
    )
    _audit, audit_evidence = validate_independent_audit_v8(
        project_root=project_root,
        audit_decision_path=audit_path,
        expected_audit_decision_sha256=authorization[
            "independent_audit_decision_sha256"
        ],
        expected_manifest_sha256=expected_manifest_sha256,
        expected_inventory_sha256=expected_inventory_sha256,
    )
    if (
        authorization["independent_audit_subject_sha256"]
        != audit_evidence["subject_sha256"]
        or authorization["independent_auditor_identity_sha256"]
        != audit_evidence["auditor_identity_sha256"]
        or authorization["independent_audit_path"] != audit_evidence["report_path"]
        or authorization["independent_audit_sha256"] != audit_evidence["report_sha256"]
    ):
        raise R8GuardError("R8 authorization changed the accepted audit identity")
    ttl = exact_int(
        authorization["ttl_seconds"],
        "R8 authorization TTL",
        minimum=1,
        maximum=MAX_AUTHORIZATION_SECONDS,
    )
    issued = parse_utc(authorization["issued_utc"], "R8 issued UTC")
    expires = parse_utc(authorization["expires_utc"], "R8 expires UTC")
    issued_mono = exact_int(
        authorization["issued_monotonic_ns"], "R8 issued monotonic", minimum=1
    )
    expires_mono = exact_int(
        authorization["expires_monotonic_ns"], "R8 expires monotonic", minimum=1
    )
    if expires != issued + timedelta(seconds=ttl):
        raise R8GuardError("R8 UTC authorization lifetime contradicts its exact TTL")
    if expires_mono != issued_mono + ttl * 1_000_000_000:
        raise R8GuardError("R8 monotonic authorization lifetime contradicts its exact TTL")
    audit_age = (issued - audit_evidence["completed_utc"]).total_seconds()
    if audit_age < 0 or audit_age > MAX_AUDIT_TO_ISSUE_SECONDS:
        raise R8GuardError("R8 authorization is not bound to a fresh completed audit")
    sample = _trusted_sample()
    if authorization["clock_id_sha256"] != sample.clock_id_sha256:
        raise R8GuardError("R8 authorization clock identity mismatch")
    if not issued <= sample.utc <= expires:
        raise R8GuardError("R8 authorization is not fresh on trusted UTC")
    if not issued_mono <= sample.monotonic_ns <= expires_mono:
        raise R8GuardError("R8 authorization is not fresh on trusted monotonic time")
    return authorization, {
        "path": rel,
        "bytes": authorization_path.stat().st_size,
        "sha256": auth_hash,
        "payload_manifest_sha256": expected_manifest_sha256,
        "verified_clock_id_sha256": sample.clock_id_sha256,
        "verified_monotonic_ns": sample.monotonic_ns,
        **audit_evidence,
    }


def verify_execution_authorization(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fail closed even for a valid document: R8 has no audited executor."""

    validate_execution_authorization_document(**kwargs)
    raise R8GuardError(
        "R8 parent/worker integration is absent; static document validation cannot authorize execution"
    )


R8_RSS_ADDITIONS = {"started_monotonic_ns", "ended_monotonic_ns"}
R8_TELEMETRY_ADDITIONS = {
    "design_generation_observed_cuda_reserved_bytes",
    "after_design_unload_cuda_reserved_bytes",
    "clone_generation_observed_cuda_reserved_bytes",
}
R8_PARENT_ADDITIONS = {"parent_started_monotonic_ns", "parent_ended_monotonic_ns"}

CUDA_PAIRS = (
    ("baseline_cuda_allocated_bytes", "baseline_cuda_reserved_bytes"),
    (
        "after_design_load_observed_cuda_allocated_bytes",
        "after_design_load_observed_cuda_reserved_bytes",
    ),
    (
        "design_generation_observed_cuda_allocated_bytes",
        "design_generation_observed_cuda_reserved_bytes",
    ),
    (
        "after_design_unload_cuda_allocated_bytes",
        "after_design_unload_cuda_reserved_bytes",
    ),
    (
        "after_base_load_observed_cuda_allocated_bytes",
        "after_base_load_observed_cuda_reserved_bytes",
    ),
    (
        "clone_generation_observed_cuda_allocated_bytes",
        "clone_generation_observed_cuda_reserved_bytes",
    ),
    ("final_cuda_allocated_bytes", "final_cuda_reserved_bytes"),
    ("torch_peak_cuda_allocated_bytes", "torch_peak_cuda_reserved_bytes"),
)


def _r7_worker_projection(evidence: dict[str, Any]) -> dict[str, Any]:
    r7 = sealed_r7()
    projected = copy.deepcopy(evidence)
    projected["schema"] = "qwen3_tts_voice_forge_worker_resource_evidence_v7"
    telemetry = projected["worker_reported_telemetry"]
    rss = telemetry["rss_sampler"]
    for key in R8_RSS_ADDITIONS:
        rss.pop(key, None)
    for key in R8_TELEMETRY_ADDITIONS:
        telemetry.pop(key, None)
    projected["worker_reported_telemetry_sha256"] = r7.canonical_sha256(telemetry)
    return projected


def _validate_elapsed(
    *, started_ns: Any, ended_ns: Any, elapsed: Any, label: str
) -> float:
    started = exact_int(started_ns, f"{label} start", minimum=1)
    ended = exact_int(ended_ns, f"{label} end", minimum=1)
    claimed = finite_number(elapsed, f"{label} elapsed", minimum=0)
    if ended <= started or claimed <= 0:
        raise R8GuardError(f"{label} monotonic interval is not positive")
    observed = (ended - started) / 1_000_000_000.0
    if abs(claimed - observed) > ELAPSED_TOLERANCE_SECONDS:
        raise R8GuardError(f"{label} elapsed contradicts its monotonic timestamps")
    return observed


def validate_worker_resource_evidence(
    evidence: dict[str, Any], *, semantic_binding: dict[str, Any]
) -> dict[str, Any]:
    r7 = sealed_r7()
    require_exact_keys(evidence, set(r7.WORKER_RESOURCE_EVIDENCE_KEYS), "R8 worker evidence")
    if evidence["schema"] != "qwen3_tts_voice_forge_worker_resource_evidence_v8":
        raise R8GuardError("R8 worker evidence schema mismatch")
    telemetry = require_exact_keys(
        evidence["worker_reported_telemetry"],
        set(r7.WORKER_TELEMETRY_KEYS) | R8_TELEMETRY_ADDITIONS,
        "R8 worker telemetry",
    )
    if canonical_sha256(telemetry) != evidence["worker_reported_telemetry_sha256"]:
        raise R8GuardError("R8 worker telemetry digest mismatch")
    rss = require_exact_keys(
        telemetry["rss_sampler"],
        set(r7.RSS_SAMPLER_KEYS) | R8_RSS_ADDITIONS,
        "R8 RSS sampler",
    )
    mono_elapsed = _validate_elapsed(
        started_ns=rss["started_monotonic_ns"],
        ended_ns=rss["ended_monotonic_ns"],
        elapsed=rss["elapsed_seconds"],
        label="R8 RSS",
    )
    utc_elapsed = (
        parse_utc(rss["ended_utc"], "R8 RSS end UTC")
        - parse_utc(rss["started_utc"], "R8 RSS start UTC")
    ).total_seconds()
    if utc_elapsed < 0 or abs(utc_elapsed - mono_elapsed) > UTC_MONOTONIC_TOLERANCE_SECONDS:
        raise R8GuardError("R8 RSS UTC interval contradicts monotonic time")
    interval = finite_number(
        rss["sampling_interval_seconds"], "R8 RSS sampling interval", minimum=0.001
    )
    count = exact_int(rss["sample_count"], "R8 RSS sample count", minimum=2)
    maximum_plausible_count = math.ceil(mono_elapsed / interval) + 2
    if count > maximum_plausible_count:
        raise R8GuardError("R8 RSS sample count is impossible for its interval and duration")
    for allocated_key, reserved_key in CUDA_PAIRS:
        allocated = exact_int(telemetry[allocated_key], f"R8 CUDA {allocated_key}")
        reserved = exact_int(telemetry[reserved_key], f"R8 CUDA {reserved_key}")
        if reserved < allocated:
            raise R8GuardError(
                f"R8 CUDA reserved bytes are below allocated bytes at {allocated_key}"
            )
    r7.validate_worker_resource_evidence(
        _r7_worker_projection(evidence), semantic_binding=semantic_binding
    )
    return evidence


JOB_COUNTER_BOUNDS = {
    "primary_worker_pid": (1, UINT32_MAX),
    "parent_pid": (1, UINT32_MAX),
    "primary_worker_exit_code": (0, UINT32_MAX),
    "active_processes_after_termination": (0, UINT32_MAX),
    "total_processes": (1, UINT32_MAX),
    "total_terminated_processes": (0, UINT32_MAX),
    "peak_process_memory_used_bytes": (1, UINT64_MAX),
    "peak_job_memory_used_bytes": (1, UINT64_MAX),
    "io_read_operation_count": (0, UINT64_MAX),
    "io_write_operation_count": (0, UINT64_MAX),
    "io_read_bytes": (0, UINT64_MAX),
    "io_write_bytes": (0, UINT64_MAX),
    "worker_stdout_bytes": (0, UINT64_MAX),
    "worker_stderr_bytes": (0, UINT64_MAX),
}


def _r7_parent_projection(evidence: dict[str, Any]) -> dict[str, Any]:
    r7 = sealed_r7()
    projected = copy.deepcopy(evidence)
    projected["schema"] = "qwen3_tts_voice_forge_resource_reconciliation_v7"
    parent = projected["parent_job_observation"]
    parent["schema"] = "qwen3_tts_voice_forge_parent_job_observation_v7"
    for key in R8_PARENT_ADDITIONS:
        parent.pop(key, None)
    projected["parent_job_observation_sha256"] = r7.canonical_sha256(parent)
    return projected


def validate_resource_evidence(
    evidence: dict[str, Any],
    *,
    worker_evidence: dict[str, Any],
    semantic_binding: dict[str, Any],
    worker_claim: dict[str, Any],
    stdout_row: dict[str, Any],
    stderr_row: dict[str, Any],
) -> dict[str, Any]:
    r7 = sealed_r7()
    validate_worker_resource_evidence(worker_evidence, semantic_binding=semantic_binding)
    require_exact_keys(evidence, set(r7.RESOURCE_EVIDENCE_KEYS), "R8 resource evidence")
    if evidence["schema"] != "qwen3_tts_voice_forge_resource_reconciliation_v8":
        raise R8GuardError("R8 resource evidence schema mismatch")
    parent = require_exact_keys(
        evidence["parent_job_observation"],
        set(r7.PARENT_OBSERVATION_KEYS) | R8_PARENT_ADDITIONS,
        "R8 parent Job observation",
    )
    if parent["schema"] != "qwen3_tts_voice_forge_parent_job_observation_v8":
        raise R8GuardError("R8 parent Job observation schema mismatch")
    if canonical_sha256(parent) != evidence["parent_job_observation_sha256"]:
        raise R8GuardError("R8 parent Job observation digest mismatch")
    parent_wall = finite_number(
        parent["parent_wall_seconds"],
        "R8 parent wall seconds",
        minimum=0,
        maximum=MAX_PARENT_WALL_SECONDS,
    )
    _validate_elapsed(
        started_ns=parent["parent_started_monotonic_ns"],
        ended_ns=parent["parent_ended_monotonic_ns"],
        elapsed=parent_wall,
        label="R8 parent wall",
    )
    for key, (minimum, maximum) in JOB_COUNTER_BOUNDS.items():
        exact_int(parent[key], f"R8 parent counter {key}", minimum=minimum, maximum=maximum)
    if parent["primary_worker_pid"] == parent["parent_pid"]:
        raise R8GuardError("R8 parent and worker PIDs cannot be the same process")
    if parent["total_terminated_processes"] > parent["total_processes"]:
        raise R8GuardError("R8 terminated Job processes exceed total processes")
    if parent["active_processes_after_termination"] > parent["total_processes"]:
        raise R8GuardError("R8 active Job processes exceed total processes")
    if parent["peak_job_memory_used_bytes"] < parent["peak_process_memory_used_bytes"]:
        raise R8GuardError("R8 Job peak memory is below its process peak")
    if parent["io_read_bytes"] > 0 and parent["io_read_operation_count"] == 0:
        raise R8GuardError("R8 positive read bytes have zero read operations")
    if parent["io_write_bytes"] > 0 and parent["io_write_operation_count"] == 0:
        raise R8GuardError("R8 positive write bytes have zero write operations")
    r7.validate_resource_evidence(
        _r7_parent_projection(evidence),
        worker_evidence=_r7_worker_projection(worker_evidence),
        semantic_binding=semantic_binding,
        worker_claim=worker_claim,
        stdout_row=stdout_row,
        stderr_row=stderr_row,
    )
    return evidence


__all__ = [
    "AUTHORIZATION_KEYS",
    "ClockSample",
    "CUDA_PAIRS",
    "ELAPSED_TOLERANCE_SECONDS",
    "MAX_AUDIT_TO_ISSUE_SECONDS",
    "MAX_AUTHORIZATION_SECONDS",
    "R7_PAYLOAD_MANIFEST_SHA256",
    "R7_REJECTED_AUDIT_SHA256",
    "R8GuardError",
    "R8_AUTHORIZATION_ROOT_REL",
    "R8_PAYLOAD_MANIFEST_REL",
    "SystemClockAuthority",
    "audit_subject",
    "canonical_bytes",
    "canonical_sha256",
    "payload_inventory_sha256",
    "sealed_r7",
    "sha256_file",
    "validate_execution_authorization_document",
    "validate_independent_audit_v8",
    "validate_resource_evidence",
    "validate_worker_resource_evidence",
    "verify_execution_authorization",
    "verify_payload_manifest",
]
