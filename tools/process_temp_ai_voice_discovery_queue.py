"""Process pending TemporaryAI voice-discovery requests in a bounded batch.

The operator starts this worker explicitly.  It then finds queued request files
and performs metadata-only discovery without requiring a separate command for
each candidate.  It never downloads media/model payloads, extracts audio,
builds or assigns a voice, synthesizes speech, or activates a candidate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_voice_discovery import (  # noqa: E402
    CANDIDATE_ROOT,
    INDEX_FILENAME,
    REQUEST_FILENAME,
    json_sha256,
    project_relative,
    read_json,
    run_candidate_discovery,
    slug,
    validate_request,
)


LOCK_PATH = PROJECT_ROOT / "Data" / "voice" / "temp_ai_voice_discovery_queue.lock"
SEARCHED_STATUSES = {"metadata_search_complete", "metadata_search_partial"}
MAX_BATCH_HARD_LIMIT = 10


@dataclass(frozen=True)
class QueueEntry:
    candidate_id: str
    request_path: Path
    request_sha256: str


def plan_queue(
    candidate_root: Path = CANDIDATE_ROOT,
    *,
    refresh: bool = False,
) -> tuple[list[QueueEntry], list[dict[str, str]], list[dict[str, str]]]:
    """Return eligible entries, fail-closed validation errors, and skips."""
    root = candidate_root.resolve()
    entries: list[QueueEntry] = []
    errors: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    if not root.is_dir():
        return entries, [{"candidate_id": "", "error": f"Candidate root does not exist: {root}"}], skipped

    for candidate_dir in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if not candidate_dir.is_dir() or candidate_dir.is_symlink():
            continue
        candidate_id = candidate_dir.name
        if slug(candidate_id) != candidate_id:
            skipped.append({"candidate_id": candidate_id, "reason": "invalid_candidate_directory_name"})
            continue
        request_path = candidate_dir / REQUEST_FILENAME
        if not request_path.is_file() or request_path.is_symlink():
            continue
        try:
            request_path.resolve().relative_to(root)
            request = read_json(request_path, {})
            validate_request(request, expected_candidate_id=candidate_id)
            request_hash = json_sha256(request)
        except Exception as exc:
            errors.append({"candidate_id": candidate_id, "error": str(exc)[:500]})
            continue

        index_path = candidate_dir / INDEX_FILENAME
        if index_path.is_symlink():
            errors.append({"candidate_id": candidate_id, "error": "voice_discovery_index.json may not be a symlink."})
            continue
        index = read_json(index_path, {})
        if (
            not refresh
            and isinstance(index, dict)
            and index.get("candidate_id") == candidate_id
            and index.get("request_sha256") == request_hash
            and index.get("status") in SEARCHED_STATUSES
        ):
            skipped.append({"candidate_id": candidate_id, "reason": "current_metadata_index_already_exists"})
            continue
        entries.append(QueueEntry(candidate_id, request_path, request_hash))
    return entries, errors, skipped


def process_queue(
    *,
    candidate_root: Path = CANDIDATE_ROOT,
    max_candidates: int = 3,
    refresh: bool = False,
    dry_run: bool = False,
    runner: Callable[..., tuple[Path, dict[str, Any]]] = run_candidate_discovery,
) -> dict[str, Any]:
    if not 1 <= max_candidates <= MAX_BATCH_HARD_LIMIT:
        raise ValueError(f"max_candidates must be between 1 and {MAX_BATCH_HARD_LIMIT}.")
    entries, validation_errors, skipped = plan_queue(candidate_root, refresh=refresh)
    selected = entries[:max_candidates]
    deferred = entries[max_candidates:]
    processed: list[dict[str, Any]] = []
    operation_errors = list(validation_errors)

    if not dry_run:
        for entry in selected:
            try:
                current_request = read_json(entry.request_path, {})
                validate_request(current_request, expected_candidate_id=entry.candidate_id)
                if json_sha256(current_request) != entry.request_sha256:
                    raise ValueError("Voice-discovery request changed after queue planning; retry the batch.")
                output_path, result = runner(entry.candidate_id, metadata_search=True)
                expected_output = entry.request_path.parent / INDEX_FILENAME
                if output_path.resolve() != expected_output.resolve() or output_path.is_symlink():
                    raise ValueError("Discovery output escaped the candidate's fixed index path.")
                current_request = read_json(entry.request_path, {})
                validate_request(current_request, expected_candidate_id=entry.candidate_id)
                if json_sha256(current_request) != entry.request_sha256:
                    raise ValueError("Voice-discovery request changed while providers were running; retry the batch.")
                if result.get("candidate_id", entry.candidate_id) != entry.candidate_id:
                    raise ValueError("Discovery result candidate identity does not match the queued candidate.")
                if result.get("request_sha256") != entry.request_sha256:
                    raise ValueError("Discovery result is not bound to the queued request bytes.")
                persisted = read_json(output_path, {})
                if persisted != result:
                    raise ValueError("Persisted discovery index does not match the provider result.")
                processed.append(
                    {
                        "candidate_id": entry.candidate_id,
                        "status": result.get("status"),
                        "output": project_relative(output_path),
                        "request_sha256": entry.request_sha256,
                        "provider_error_count": len(result.get("provider_errors", [])),
                    }
                )
            except Exception as exc:
                operation_errors.append({"candidate_id": entry.candidate_id, "error": str(exc)[:500]})

    return {
        "status": "dry_run" if dry_run else "batch_complete_with_errors" if operation_errors else "batch_complete",
        "metadata_only": True,
        "refresh": refresh,
        "batch_limit": max_candidates,
        "eligible_count": len(entries),
        "selected_candidate_ids": [entry.candidate_id for entry in selected],
        "processed": processed,
        "deferred_candidate_ids": [entry.candidate_id for entry in deferred],
        "skipped": skipped,
        "errors": operation_errors,
        "media_downloaded": False,
        "audio_extracted": False,
        "model_downloaded": False,
        "voice_generated": False,
        "voice_assigned": False,
        "candidate_activated": False,
    }


class QueueLock:
    """Small fail-closed process lock; no second queue worker may overlap."""

    def __init__(self, path: Path = LOCK_PATH) -> None:
        self.path = path
        self.acquired = False

    def __enter__(self) -> "QueueLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(f"Voice-discovery queue lock already exists: {self.path}") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "purpose": "metadata_only_temp_ai_voice_discovery"}, handle)
            handle.write("\n")
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self.acquired = False


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Process several queued TemporaryAI voice requests using metadata only. "
            "No media/model payload, audio extraction, cloning, synthesis, assignment, or activation is allowed."
        )
    )
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--refresh", action="store_true", help="Re-run current indexes; otherwise they are skipped.")
    parser.add_argument("--dry-run", action="store_true", help="List the bounded batch without network provider calls.")
    args = parser.parse_args()
    try:
        with QueueLock():
            result = process_queue(
                max_candidates=args.max_candidates,
                refresh=args.refresh,
                dry_run=args.dry_run,
            )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if not result["errors"] else 3
    except Exception as exc:
        print(f"VOICE DISCOVERY QUEUE BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
