from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_voice_discovery import (  # noqa: E402
    INDEX_FILENAME,
    REQUEST_FILENAME,
    build_candidate_voice_discovery_request,
    json_sha256,
)
from tools.process_temp_ai_voice_discovery_queue import (  # noqa: E402
    QueueLock,
    plan_queue,
    process_queue,
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def add_candidate(root: Path, candidate_id: str) -> tuple[Path, dict]:
    candidate = root / candidate_id
    request = build_candidate_voice_discovery_request(
        {
            "candidate_id": candidate_id,
            "display_name": candidate_id.replace("_", " ").title(),
            "ai_type": "canon_reconstruction_temp_ai",
            "ui_category": "Fictional Character",
        },
        {},
    )
    write_json(candidate / REQUEST_FILENAME, request)
    return candidate, request


class TemporaryAIVoiceDiscoveryQueueTests(unittest.TestCase):
    def test_current_metadata_index_is_skipped_without_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, request = add_candidate(root, "already_searched")
            write_json(
                candidate / INDEX_FILENAME,
                {
                    "candidate_id": "already_searched",
                    "request_sha256": json_sha256(request),
                    "status": "metadata_search_complete",
                },
            )
            entries, errors, skipped = plan_queue(root)
            self.assertEqual(entries, [])
            self.assertEqual(errors, [])
            self.assertEqual(skipped[0]["reason"], "current_metadata_index_already_exists")
            refreshed, _, _ = plan_queue(root, refresh=True)
            self.assertEqual([item.candidate_id for item in refreshed], ["already_searched"])

    def test_changed_request_becomes_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, request = add_candidate(root, "changed_request")
            write_json(
                candidate / INDEX_FILENAME,
                {
                    "candidate_id": "changed_request",
                    "request_sha256": "0" * 64,
                    "status": "metadata_search_complete",
                },
            )
            entries, errors, _ = plan_queue(root)
            self.assertEqual(errors, [])
            self.assertEqual(entries[0].request_sha256, json_sha256(request))

    def test_batch_is_bounded_and_runner_is_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for candidate_id in ("candidate_a", "candidate_b", "candidate_c"):
                add_candidate(root, candidate_id)
            calls: list[tuple[str, bool]] = []

            def runner(candidate_id: str, *, metadata_search: bool):
                calls.append((candidate_id, metadata_search))
                request = json.loads((root / candidate_id / REQUEST_FILENAME).read_text(encoding="utf-8"))
                result = {
                    "candidate_id": candidate_id,
                    "status": "metadata_search_complete",
                    "request_sha256": json_sha256(request),
                    "provider_errors": [],
                }
                output = root / candidate_id / INDEX_FILENAME
                write_json(output, result)
                return output, result

            result = process_queue(candidate_root=root, max_candidates=2, runner=runner)
            self.assertEqual(calls, [("candidate_a", True), ("candidate_b", True)])
            self.assertEqual(result["deferred_candidate_ids"], ["candidate_c"])
            self.assertFalse(result["media_downloaded"])
            self.assertFalse(result["voice_generated"])
            self.assertFalse(result["candidate_activated"])

    def test_dry_run_never_calls_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            add_candidate(root, "candidate_a")

            def forbidden_runner(*args, **kwargs):
                raise AssertionError("dry run called the provider runner")

            result = process_queue(candidate_root=root, dry_run=True, runner=forbidden_runner)
            self.assertEqual(result["status"], "dry_run")
            self.assertEqual(result["selected_candidate_ids"], ["candidate_a"])
            self.assertEqual(result["processed"], [])

    def test_invalid_request_fails_closed_without_blocking_other_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            add_candidate(root, "good_candidate")
            bad = root / "bad_candidate"
            write_json(bad / REQUEST_FILENAME, {"schema_version": 1, "candidate_id": "bad_candidate"})
            entries, errors, _ = plan_queue(root)
            self.assertEqual([item.candidate_id for item in entries], ["good_candidate"])
            self.assertEqual(errors[0]["candidate_id"], "bad_candidate")

    def test_runner_cannot_replace_request_during_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, request = add_candidate(root, "changed_during_batch")

            def runner(candidate_id: str, *, metadata_search: bool):
                original_hash = json_sha256(request)
                request["identity_target"]["display_name"] = "Changed Name"
                write_json(candidate / REQUEST_FILENAME, request)
                result = {
                    "candidate_id": candidate_id,
                    "status": "metadata_search_complete",
                    "request_sha256": original_hash,
                    "provider_errors": [],
                }
                output = candidate / INDEX_FILENAME
                write_json(output, result)
                return output, result

            result = process_queue(candidate_root=root, runner=runner)
            self.assertEqual(result["processed"], [])
            self.assertIn("changed while providers", result["errors"][0]["error"])

    def test_result_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, _ = add_candidate(root, "candidate_a")

            def mismatched_runner(candidate_id: str, *, metadata_search: bool):
                result = {
                    "candidate_id": "candidate_b",
                    "status": "metadata_search_complete",
                    "request_sha256": json_sha256(
                        json.loads((candidate / REQUEST_FILENAME).read_text(encoding="utf-8"))
                    ),
                    "provider_errors": [],
                }
                output = candidate / INDEX_FILENAME
                write_json(output, result)
                return output, result

            result = process_queue(candidate_root=root, runner=mismatched_runner)
            self.assertEqual(result["processed"], [])
            self.assertIn("identity", result["errors"][0]["error"])

    def test_lock_rejects_overlap_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock_path = Path(temp) / "queue.lock"
            with QueueLock(lock_path):
                self.assertTrue(lock_path.exists())
                with self.assertRaisesRegex(RuntimeError, "already exists"):
                    with QueueLock(lock_path):
                        pass
            self.assertFalse(lock_path.exists())

    def test_hard_batch_limit_rejects_unbounded_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "between 1 and 10"):
                process_queue(candidate_root=Path(temp), max_candidates=11, dry_run=True)


if __name__ == "__main__":
    unittest.main()
