"""Tests for serialized, fail-closed Avatar Builder resident-memory writes."""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_builder_ai
from Core.avatar_builder_memory_lock import is_canonical_utc_timestamp


def _append_worker(memory_path: str) -> None:
    avatar_builder_ai.GLOBAL_MEMORY_PATH = Path(memory_path)
    avatar_builder_ai.append_global_lesson(
        "concurrent_candidate",
        ["concurrency"],
        "Concurrent lesson.",
        source="test",
    )


def _activation_worker(memory_path: str) -> None:
    avatar_builder_ai.GLOBAL_MEMORY_PATH = Path(memory_path)
    avatar_builder_ai.log_activation("concurrent_candidate", "review")


class AvatarBuilderMemoryTransactionTests(unittest.TestCase):
    @staticmethod
    def _base_memory() -> dict[str, object]:
        return {
            "schema_version": 1,
            "updated_at": "2026-08-25T00:00:00+00:00",
            "lessons": [
                {
                    "lesson_id": "sentinel_lesson",
                    "created_at": "2026-08-25T00:00:00+00:00",
                    "lesson": "Preserve me.",
                }
            ],
            "activation_log": [],
        }

    def test_append_and_activation_preserve_existing_memory(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            memory_path.write_text(json.dumps(self._base_memory()), encoding="utf-8")
            with mock.patch.object(avatar_builder_ai, "GLOBAL_MEMORY_PATH", memory_path):
                avatar_builder_ai.append_global_lesson(
                    "new_candidate",
                    ["voice", "voice"],
                    "New lesson.",
                    source="test",
                )
                avatar_builder_ai.log_activation("new_candidate", "review")
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            self.assertIn("sentinel_lesson", {row.get("lesson_id") for row in memory["lessons"]})
            self.assertTrue(
                any(row.get("candidate_id") == "new_candidate" for row in memory["lessons"])
            )
            self.assertEqual("new_candidate", memory["activation_log"][-1]["candidate_id"])

    def test_invalid_memory_is_never_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            memory_path.write_text("{broken", encoding="utf-8")
            with mock.patch.object(avatar_builder_ai, "GLOBAL_MEMORY_PATH", memory_path):
                with self.assertRaises(ValueError):
                    avatar_builder_ai.append_global_lesson("candidate", [], "lesson")
                self.assertEqual("{broken", memory_path.read_text(encoding="utf-8"))
                with self.assertRaises(ValueError):
                    avatar_builder_ai.log_activation("candidate", "review")
            self.assertEqual("{broken", memory_path.read_text(encoding="utf-8"))

    def test_complete_body_teacher_repairs_invalid_top_level_timestamp(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            with mock.patch.object(avatar_builder_ai, "GLOBAL_MEMORY_PATH", memory_path):
                first = avatar_builder_ai.teach_complete_body_curriculum()
                self.assertTrue(first["ok"])
                memory = json.loads(memory_path.read_text(encoding="utf-8"))
                memory["updated_at"] = "C:\\Users\\private-person\\secret"
                memory_path.write_text(json.dumps(memory), encoding="utf-8")
                repaired = avatar_builder_ai.teach_complete_body_curriculum()
            self.assertTrue(repaired["ok"])
            self.assertTrue(repaired["lesson_updated"])
            repaired_memory = json.loads(memory_path.read_text(encoding="utf-8"))
            self.assertTrue(is_canonical_utc_timestamp(repaired_memory["updated_at"]))
            self.assertNotIn("C:\\", repaired_memory["updated_at"])

    def test_atomic_write_failure_leaves_existing_bytes_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            original = json.dumps(self._base_memory()).encode("utf-8")
            memory_path.write_bytes(original)
            with (
                mock.patch.object(avatar_builder_ai, "GLOBAL_MEMORY_PATH", memory_path),
                mock.patch.object(
                    avatar_builder_ai,
                    "_write_json_atomic",
                    side_effect=OSError("simulated write failure"),
                ),
            ):
                with self.assertRaises(OSError):
                    avatar_builder_ai.append_global_lesson("candidate", [], "lesson")
            self.assertEqual(original, memory_path.read_bytes())

    def test_concurrent_different_writers_preserve_both_updates(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            memory_path.write_text(json.dumps(self._base_memory()), encoding="utf-8")
            context = multiprocessing.get_context("spawn")
            workers = [
                context.Process(target=_append_worker, args=(str(memory_path),)),
                context.Process(target=_activation_worker, args=(str(memory_path),)),
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(30)
                self.assertEqual(0, worker.exitcode)
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            self.assertIn("sentinel_lesson", {row.get("lesson_id") for row in memory["lessons"]})
            self.assertTrue(
                any(
                    row.get("candidate_id") == "concurrent_candidate"
                    for row in memory["lessons"]
                )
            )
            self.assertTrue(
                any(
                    row.get("candidate_id") == "concurrent_candidate"
                    for row in memory["activation_log"]
                )
            )


if __name__ == "__main__":
    unittest.main()
