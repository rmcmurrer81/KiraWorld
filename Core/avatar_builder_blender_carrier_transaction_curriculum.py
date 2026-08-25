"""Validate and teach the exact reviewed Blender carrier safety lesson."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from Core import avatar_blender_carrier_transaction_closure as transaction_closure
from Core import avatar_blender_preimport_controller as controller
from Core import avatar_builder_ai
from Core.avatar_builder_memory_lock import (
    AvatarBuilderMemoryLockError,
    is_canonical_utc_timestamp,
    locked_memory_write,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "body_systems"
    / "avatar_builder_blender_carrier_transaction_closure_candidate_v1.json"
)
REVIEW_PATH = (
    PROJECT_ROOT
    / "System"
    / "Docs"
    / "AVATAR_BUILDER_BLENDER_CARRIER_TRANSACTION_CURRICULUM_REVIEW_20260825.md"
)
LESSON_PATH = CANDIDATE_PATH
LESSON_ID = "avatar_builder_blender_carrier_transaction_closure_v1"
LESSON_STATUS = "VERIFIED_REUSABLE_FAIL_CLOSED_CARRIER_TRANSACTION_LESSON"
DEFAULT_MEMORY_PATH = avatar_builder_ai.DEFAULT_GLOBAL_MEMORY_PATH

EXPECTED_CANDIDATE_SOURCE = {
    "role": "exact_reviewed_author_candidate",
    "path": "Avatar/avatar_builder/body_systems/"
    "avatar_builder_blender_carrier_transaction_closure_candidate_v1.json",
    "bytes": 2805,
    "sha256": "c44ab1e90dde09d48d86bed45bcf11ea5ef7a4915af41c20828baafd3a0cb849",
}
EXPECTED_REVIEW_SOURCE = {
    "role": "independent_receiver_review",
    "path": "System/Docs/"
    "AVATAR_BUILDER_BLENDER_CARRIER_TRANSACTION_CURRICULUM_REVIEW_20260825.md",
    "bytes": 2559,
    "sha256": "22ac93e18d038ac0e9f0abb26fea9aabd007e257bce58f37eb67c5aeff247199",
}
EXPECTED_CANDIDATE_SOURCES = {
    "transaction_closure_controller": {
        "path": "Core/avatar_blender_carrier_transaction_closure.py",
        "bytes": 31794,
        "sha256": "408a9d82d16173ca2849a7a14db7e69468c607640eefe6f4e986a5d97448c9d3",
    },
    "transaction_closure_tests": {
        "path": "Testing/test_avatar_blender_carrier_transaction_closure.py",
        "bytes": 5822,
        "sha256": "0bb49fd092759d03b5e7564b7740bf7fc169a4f921d512e64f418a2215101856",
    },
    "transaction_closure_authority": {
        "path": "System/Docs/AVATAR_BUILDER_BLENDER_CARRIER_TRANSACTION_CLOSURE_20260825.md",
        "bytes": 5657,
        "sha256": "067602374a2cde5e60cbe7c99514940c105fa35e9c3ce3cd56a7e24f7aca0133",
    },
}
EXPECTED_CANDIDATE_TRUTH = {
    "installed_blender_and_interpreter_hashes_match": True,
    "static_complete_input_output_closure_verified": True,
    "static_two_stage_transaction_closure_verified": True,
    "native_provider_reviewed": False,
    "native_transaction_interface_available": False,
    "authorization_present": False,
    "native_claim_root_selected": False,
    "native_claim_created": False,
    "operating_system_evidence_verified": False,
    "blender_execution_authorized": False,
    "body_build_authorized": False,
    "body_created": False,
    "candidate_assignment_authorized": False,
    "anatomy_authoring_authorized": False,
    "runtime_activation_authorized": False,
    "public_export_authorized": False,
}
EXPECTED_LESSON_TEXT = (
    "A carrier build and its pose audit are one transaction, not two independent successes. "
    "Bind and retain the complete source, code, and tool closure; reserve every output "
    "create-new; keep the build result held through the audit; and terminalize exactly once. "
    "If a native provider cannot prove that whole chain, create no body and start no process."
)
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_created_at(value: Any) -> bool:
    return is_canonical_utc_timestamp(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(PROJECT_ROOT.resolve(strict=True)).as_posix()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("memory path must remain inside the project") from exc


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _validate_exact_source(expected: dict[str, Any]) -> Path:
    relative = expected["path"]
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("carrier curriculum source path differs")
    try:
        resolved = (PROJECT_ROOT / Path(relative)).resolve(strict=True)
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("carrier curriculum source escapes project") from exc
    if resolved.stat().st_size != expected["bytes"]:
        raise ValueError("carrier curriculum source bytes differ")
    if _sha256_file(resolved) != expected["sha256"]:
        raise ValueError("carrier curriculum source hash differs")
    return resolved


def _validate_candidate_binding_set(bindings: Any) -> None:
    if not isinstance(bindings, list) or len(bindings) != len(EXPECTED_CANDIDATE_SOURCES):
        raise ValueError("carrier candidate source binding count differs")
    observed: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {"path", "bytes", "sha256", "role"}:
            raise ValueError("carrier candidate source binding is invalid")
        role = binding.get("role")
        if not isinstance(role, str) or role not in EXPECTED_CANDIDATE_SOURCES or role in observed:
            raise ValueError("carrier candidate source role differs")
        expected = {**EXPECTED_CANDIDATE_SOURCES[role], "role": role}
        if binding != expected:
            raise ValueError("carrier candidate source identity differs")
        _validate_exact_source(expected)
        observed.add(role)
    if observed != set(EXPECTED_CANDIDATE_SOURCES):
        raise ValueError("carrier candidate exact source set differs")


def _validate_candidate(path: Path) -> dict[str, Any]:
    candidate = controller.read_strict_json(path, max_bytes=128 * 1024)
    required_keys = {
        "schema",
        "lesson_id",
        "status",
        "source_bindings",
        "current_truth",
        "verified_static_scope",
        "lesson",
        "receiver_integration",
        "prohibited_claims",
    }
    if set(candidate) != required_keys:
        raise ValueError("carrier candidate keys differ")
    if candidate.get("schema") != "kira.avatar_builder.reusable_lesson_candidate.v1":
        raise ValueError("carrier candidate schema differs")
    if candidate.get("lesson_id") != LESSON_ID:
        raise ValueError("carrier candidate identity differs")
    if candidate.get("status") != "STATIC_AUTHOR_CANDIDATE_NOT_TAUGHT_AWAITING_DIFFERENT_REVIEW":
        raise ValueError("carrier candidate review status differs")
    _validate_candidate_binding_set(candidate.get("source_bindings"))
    if candidate.get("current_truth") != EXPECTED_CANDIDATE_TRUTH:
        raise ValueError("carrier candidate truth boundary differs")
    if candidate.get("verified_static_scope") != {
        "input_count": 18,
        "output_count": 4,
        "commands": ["build", "audit"],
        "transaction_stage_count": 7,
        "long_path_input_bound": True,
        "machine_private_paths_published": False,
        "process_started": False,
    }:
        raise ValueError("carrier candidate verified scope differs")
    if candidate.get("receiver_integration") != {
        "different_review_required": True,
        "teaching_allowed": False,
        "resident_memory_write_allowed": False,
        "selectable_method_allowed": False,
        "default_enabled": False,
    }:
        raise ValueError("carrier candidate receiver boundary differs")
    if candidate.get("lesson") != EXPECTED_LESSON_TEXT:
        raise ValueError("carrier candidate lesson text differs")
    if candidate.get("prohibited_claims") != [
        "native provider implemented or reviewed",
        "Blender execution authorized",
        "body or anatomy created",
        "carrier accepted or assigned",
        "runtime activation authorized",
        "public export authorized",
    ]:
        raise ValueError("carrier candidate prohibited claims differ")
    raw_text = path.read_text(encoding="utf-8")
    for prohibited in ("C:\\\\Users", r"\\?\\", "Robert user-avatar", "private reference"):
        if prohibited in raw_text:
            raise ValueError("carrier candidate publishes private machine or person data")
    return candidate


def _validate_live_static_closure() -> dict[str, Any]:
    record = transaction_closure.load_machine_static_transaction_closure()
    transaction_closure.validate_static_transaction_closure_record(record)
    if record.get("input_count") != 18 or len(record.get("outputs", [])) != 4:
        raise ValueError("live carrier transaction closure count differs")
    if len(record.get("transaction_stages", [])) != 7:
        raise ValueError("live carrier transaction stage count differs")
    if record.get("authorization_present") is not False:
        raise ValueError("live carrier authorization unexpectedly exists")
    authority = record.get("authority")
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        raise ValueError("live carrier authority is not entirely false")
    return {
        "scope": "TEACH_TIME_READ_ONLY_STATIC_EVIDENCE_NOT_RUNTIME_AUTHORITY",
        "input_count": record["input_count"],
        "output_count": len(record["outputs"]),
        "transaction_stage_count": len(record["transaction_stages"]),
        "input_closure_sha256": record["input_closure_sha256"],
        "output_closure_sha256": record["output_closure_sha256"],
        "build_argv_sha256": record["build_argv_sha256"],
        "audit_argv_sha256": record["audit_argv_sha256"],
        "all_authority_false": True,
        "process_started": False,
    }


def load_verified_lesson() -> dict[str, Any]:
    candidate_path = _validate_exact_source(EXPECTED_CANDIDATE_SOURCE)
    review_path = _validate_exact_source(EXPECTED_REVIEW_SOURCE)
    candidate = _validate_candidate(candidate_path)
    normalized_review = " ".join(review_path.read_text(encoding="utf-8").split())
    for required in (
        "independent receiver-side source and publication reviewer",
        "exact `lesson` string inside the candidate bytes",
        "only lesson text accepted for resident teaching",
        "does not accept the closure as an execution provider",
        "create no body and start no process",
        "Kira body created: no",
        "Robert body created: no",
    ):
        if required not in normalized_review:
            raise ValueError("carrier transaction review statement differs")
    live_validation = _validate_live_static_closure()
    source_bindings = [dict(EXPECTED_CANDIDATE_SOURCE), dict(EXPECTED_REVIEW_SOURCE)]
    digest_payload = {
        "lesson_id": LESSON_ID,
        "lesson": candidate["lesson"],
        "source_bindings": source_bindings,
    }
    return {
        "schema_version": 1,
        "lesson_id": LESSON_ID,
        "status": LESSON_STATUS,
        "source_bindings": source_bindings,
        "candidate_source_bindings": candidate["source_bindings"],
        "lesson": candidate["lesson"],
        "verified_reusable_lessons": [candidate["lesson"]],
        "reviewed_candidate_truth": candidate["current_truth"],
        "live_static_validation": live_validation,
        "lesson_digest_sha256": controller.canonical_sha256(digest_payload),
        "lesson_source": {
            "path": _relative(candidate_path),
            "bytes": candidate_path.stat().st_size,
            "sha256": _sha256_file(candidate_path),
        },
        "review_source": {
            "path": _relative(review_path),
            "bytes": review_path.stat().st_size,
            "sha256": _sha256_file(review_path),
        },
    }


def _load_memory(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("existing Avatar Builder memory is not valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("existing Avatar Builder memory must be an object")
        if "lessons" in value and not isinstance(value["lessons"], list):
            raise ValueError("existing Avatar Builder lessons must be a list")
    else:
        value = {
            "schema_version": 1,
            "updated_at": _utc_now(),
            "lessons": [],
            "activation_log": [],
        }
    value.setdefault("lessons", [])
    return value


def _result(
    *,
    lesson: dict[str, Any],
    memory_path: str,
    lesson_count: int,
    added: bool,
    updated: bool,
) -> dict[str, Any]:
    return {
        "ok": True,
        "status": lesson["status"],
        "lesson_id": LESSON_ID,
        "lesson_added": added,
        "lesson_updated": updated,
        "lesson_count": lesson_count,
        "memory_path": memory_path,
        "native_provider_reviewed": False,
        "operating_system_evidence_verified": False,
        "blender_execution_authorized": False,
        "body_build_authorized": False,
        "body_created": False,
    }


def teach_verified_lesson(*, memory_path: Path = DEFAULT_MEMORY_PATH) -> dict[str, Any]:
    if not avatar_builder_ai.builder_memory_publication_boundary_is_closed():
        return {
            "ok": False,
            "status": "BLOCKED_BUILDER_MEMORY_PUBLICATION_BOUNDARY_OPEN",
            "lesson_added": False,
            "lesson_updated": False,
        }
    try:
        lesson = load_verified_lesson()
        memory_relative = _relative(memory_path)
        with locked_memory_write(memory_path):
            memory = _load_memory(memory_path)
            memory_updated_at_valid = is_canonical_utc_timestamp(memory.get("updated_at"))
            matching = [
                index
                for index, record in enumerate(memory["lessons"])
                if isinstance(record, dict) and record.get("lesson_id") == LESSON_ID
            ]
            timestamp = _utc_now()
            existing_created_at = (
                memory["lessons"][matching[0]].get("created_at") if matching else None
            )
            created_at = (
                existing_created_at if _valid_created_at(existing_created_at) else timestamp
            )
            desired = {
                "lesson_id": LESSON_ID,
                "created_at": created_at,
                "updated_at": timestamp,
                "candidate_id": "avatar_builder_shared",
                "source": "exact independently reviewed fail-closed carrier transaction lesson",
                "lesson_digest_sha256": lesson["lesson_digest_sha256"],
                "lesson_source": lesson["lesson_source"],
                "review_source": lesson["review_source"],
                "source_bindings": lesson["source_bindings"],
                "candidate_source_bindings": lesson["candidate_source_bindings"],
                "static_validation_evidence": lesson["live_static_validation"],
                "tags": [
                    "avatar_builder",
                    "blender",
                    "build_audit_transaction",
                    "create_new_outputs",
                    "fail_closed",
                    "output_closure",
                    "replay_defense",
                    "transaction_durability",
                ],
                "lesson": lesson["lesson"],
                "verified_reusable_lessons": lesson["verified_reusable_lessons"],
            }
            added = not matching
            updated = False
            if not added:
                existing = dict(memory["lessons"][matching[0]])
                existing_updated_at = existing.get("updated_at")
                existing.pop("updated_at", None)
                comparable = dict(desired)
                comparable.pop("updated_at", None)
                updated = (
                    not memory_updated_at_valid
                    or not is_canonical_utc_timestamp(existing_updated_at)
                    or existing != comparable
                    or len(matching) != 1
                )
                if not updated:
                    return _result(
                        lesson=lesson,
                        memory_path=memory_relative,
                        lesson_count=len(memory["lessons"]),
                        added=False,
                        updated=False,
                    )
            if added:
                memory["lessons"].append(desired)
            else:
                first = matching[0]
                matching_set = set(matching)
                memory["lessons"][:] = [
                    record
                    for index, record in enumerate(memory["lessons"])
                    if index not in matching_set
                ]
                memory["lessons"].insert(first, desired)
            memory["updated_at"] = timestamp
            _atomic_write_json(memory_path, memory)
            return _result(
                lesson=lesson,
                memory_path=memory_relative,
                lesson_count=len(memory["lessons"]),
                added=added,
                updated=updated,
            )
    except (ValueError, AvatarBuilderMemoryLockError) as exc:
        return {
            "ok": False,
            "status": "BLOCKED_VERIFIED_LESSON_OR_MEMORY_INVALID",
            "lesson_added": False,
            "lesson_updated": False,
            "failures": [str(exc)],
        }


__all__ = [
    "CANDIDATE_PATH",
    "DEFAULT_MEMORY_PATH",
    "LESSON_ID",
    "LESSON_PATH",
    "LESSON_STATUS",
    "REVIEW_PATH",
    "load_verified_lesson",
    "teach_verified_lesson",
]
