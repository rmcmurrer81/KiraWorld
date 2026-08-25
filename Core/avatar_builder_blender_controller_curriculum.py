"""Validate and teach one fail-closed Blender controller safety lesson."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from Core import avatar_blender_preimport_controller as controller
from Core import avatar_builder_ai


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LESSON_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "body_systems"
    / "avatar_builder_blender_preimport_controller_lesson_v1.json"
)
LESSON_ID = "avatar_builder_blender_preimport_controller_v1"
DEFAULT_MEMORY_PATH = avatar_builder_ai.DEFAULT_GLOBAL_MEMORY_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def load_verified_lesson() -> dict[str, Any]:
    lesson = controller.read_strict_json(LESSON_PATH, max_bytes=256 * 1024)
    required_keys = {
        "schema_version",
        "lesson_id",
        "status",
        "source_bindings",
        "verified_reusable_lessons",
        "lesson",
        "current_truth",
    }
    if set(lesson) != required_keys:
        raise ValueError("Blender controller lesson keys differ")
    if lesson.get("schema_version") != 1 or lesson.get("lesson_id") != LESSON_ID:
        raise ValueError("Blender controller lesson identity differs")
    if lesson.get("status") != "VERIFIED_REUSABLE_FAIL_CLOSED_SAFETY_METHOD":
        raise ValueError("Blender controller lesson status differs")
    sources = lesson.get("source_bindings")
    if not isinstance(sources, list) or len(sources) != 3:
        raise ValueError("Blender controller lesson source bindings differ")
    expected_sources = {
        (
            "Avatar/avatar_builder/tooling/blender_5_1_preimport_controller_boundary_v1.json",
            "exact_machine_static_boundary_evidence",
        ),
        (
            "System/Docs/AVATAR_BUILDER_BLENDER_PREIMPORT_CONTROLLER_BOUNDARY_20260825.md",
            "verified_method_and_native_blocker_boundary",
        ),
        (
            "System/Docs/AVATAR_BUILDER_BLENDER_5_1_WORKER_IDENTITY_BINDING_20260822.md",
            "worker_internal_identity_boundary",
        ),
    }
    observed_sources: set[tuple[str, str]] = set()
    for binding in sources:
        if not isinstance(binding, dict) or set(binding) != {"path", "bytes", "sha256", "role"}:
            raise ValueError("Blender controller lesson source binding is invalid")
        relative = binding.get("path")
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ValueError("Blender controller lesson source path differs")
        role = binding.get("role")
        if not isinstance(role, str):
            raise ValueError("Blender controller lesson source role differs")
        observed_sources.add((relative, role))
        path = PROJECT_ROOT / Path(relative)
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError("Blender controller lesson source escapes project") from exc
        if resolved.stat().st_size != binding.get("bytes"):
            raise ValueError("Blender controller lesson source bytes differ")
        if _sha256_file(resolved) != binding.get("sha256"):
            raise ValueError("Blender controller lesson source hash differs")
        if relative == controller.MACHINE_EVIDENCE_RELATIVE_PATH:
            evidence = controller.read_strict_json(resolved, max_bytes=512 * 1024)
            controller.validate_machine_evidence(evidence)
    if observed_sources != expected_sources:
        raise ValueError("Blender controller lesson exact source set differs")
    truth = lesson.get("current_truth")
    expected_truth = {
        "static_controller_verified": True,
        "native_provider_reviewed": False,
        "execution_trust_boundary_closed": False,
        "blender_execution_authorized": False,
        "body_build_authorized": False,
        "body_created": False,
        "candidate_assignment_authorized": False,
        "anatomy_authoring_authorized": False,
        "runtime_activation_authorized": False,
        "public_export_authorized": False,
    }
    if truth != expected_truth:
        raise ValueError("Blender controller lesson truth boundary differs")
    lessons = lesson.get("verified_reusable_lessons")
    if (
        not isinstance(lessons, list)
        or len(lessons) != 6
        or any(not isinstance(item, str) or not item.strip() for item in lessons)
    ):
        raise ValueError("verified reusable lessons differ")
    text = lesson.get("lesson")
    if not isinstance(text, str) or "start no process" not in text:
        raise ValueError("Blender controller lesson text differs")
    result = dict(lesson)
    result["lesson_digest_sha256"] = controller.canonical_sha256(lesson)
    result["lesson_source"] = {
        "path": _relative(LESSON_PATH),
        "bytes": LESSON_PATH.stat().st_size,
        "sha256": _sha256_file(LESSON_PATH),
    }
    return result


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
        memory = _load_memory(memory_path)
        memory_relative = _relative(memory_path)
    except ValueError as exc:
        return {
            "ok": False,
            "status": "BLOCKED_VERIFIED_LESSON_OR_MEMORY_INVALID",
            "lesson_added": False,
            "lesson_updated": False,
            "failures": [str(exc)],
        }
    matching = [
        index
        for index, record in enumerate(memory["lessons"])
        if isinstance(record, dict) and record.get("lesson_id") == LESSON_ID
    ]
    timestamp = _utc_now()
    created_at = (
        memory["lessons"][matching[0]].get("created_at")
        if matching and isinstance(memory["lessons"][matching[0]].get("created_at"), str)
        else timestamp
    )
    desired = {
        "lesson_id": LESSON_ID,
        "created_at": created_at,
        "updated_at": timestamp,
        "candidate_id": "avatar_builder_shared",
        "source": "verified fail-closed Blender pre-import controller boundary",
        "lesson_digest_sha256": lesson["lesson_digest_sha256"],
        "lesson_source": lesson["lesson_source"],
        "source_bindings": lesson["source_bindings"],
        "tags": [
            "avatar_builder",
            "blender",
            "concurrency",
            "fail_closed",
            "process_identity",
            "replay_defense",
        ],
        "lesson": lesson["lesson"],
        "verified_reusable_lessons": lesson["verified_reusable_lessons"],
        "current_truth": lesson["current_truth"],
    }
    added = not matching
    updated = False
    if added:
        memory["lessons"].append(desired)
    else:
        existing = dict(memory["lessons"][matching[0]])
        existing.pop("updated_at", None)
        comparable = dict(desired)
        comparable.pop("updated_at", None)
        updated = existing != comparable or len(matching) != 1
        if updated:
            first = matching[0]
            memory["lessons"][:] = [
                record for index, record in enumerate(memory["lessons"]) if index not in set(matching)
            ]
            memory["lessons"].insert(first, desired)
    memory["updated_at"] = timestamp
    _atomic_write_json(memory_path, memory)
    return {
        "ok": True,
        "status": lesson["status"],
        "lesson_id": LESSON_ID,
        "lesson_added": added,
        "lesson_updated": updated,
        "lesson_count": len(memory["lessons"]),
        "memory_path": memory_relative,
        "execution_trust_boundary_closed": False,
        "blender_execution_authorized": False,
        "body_created": False,
    }


__all__ = [
    "DEFAULT_MEMORY_PATH",
    "LESSON_ID",
    "LESSON_PATH",
    "load_verified_lesson",
    "teach_verified_lesson",
]
