"""Tests for reviewed Blender carrier transaction lesson publication."""

from __future__ import annotations

from copy import deepcopy
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

from Core import avatar_builder_blender_carrier_transaction_curriculum as curriculum
from Core import avatar_builder_blender_controller_curriculum as controller_curriculum


def _teach_in_process(memory_path: str, result_queue: object) -> None:
    result = curriculum.teach_verified_lesson(memory_path=Path(memory_path))
    result_queue.put(result)


def _teach_controller_in_process(memory_path: str, result_queue: object) -> None:
    result = controller_curriculum.teach_verified_lesson(memory_path=Path(memory_path))
    result_queue.put(result)


class AvatarBuilderBlenderCarrierTransactionCurriculumTests(unittest.TestCase):
    def test_reviewed_lesson_uses_exact_candidate_text_and_live_static_validation(self) -> None:
        lesson = curriculum.load_verified_lesson()
        candidate = json.loads(curriculum.CANDIDATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(curriculum.LESSON_STATUS, lesson["status"])
        self.assertEqual(candidate["lesson"], lesson["lesson"])
        self.assertEqual([candidate["lesson"]], lesson["verified_reusable_lessons"])
        self.assertEqual(2, len(lesson["source_bindings"]))
        self.assertEqual(candidate["current_truth"], lesson["reviewed_candidate_truth"])
        evidence = lesson["live_static_validation"]
        self.assertEqual(18, evidence["input_count"])
        self.assertEqual(4, evidence["output_count"])
        self.assertEqual(7, evidence["transaction_stage_count"])
        self.assertTrue(evidence["all_authority_false"])
        self.assertFalse(evidence["process_started"])
        self.assertIn("create no body", lesson["lesson"])
        self.assertIn("start no process", lesson["lesson"])

    def test_teaching_is_byte_idempotent_and_repairs_tampered_duplicates(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            first = curriculum.teach_verified_lesson(memory_path=memory_path)
            before_noop = memory_path.read_bytes()
            second = curriculum.teach_verified_lesson(memory_path=memory_path)
            after_noop = memory_path.read_bytes()
            self.assertTrue(first["ok"])
            self.assertTrue(first["lesson_added"])
            self.assertTrue(second["ok"])
            self.assertFalse(second["lesson_added"])
            self.assertFalse(second["lesson_updated"])
            self.assertEqual(before_noop, after_noop)

            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            taught = [
                row for row in memory["lessons"] if row.get("lesson_id") == curriculum.LESSON_ID
            ]
            self.assertEqual(1, len(taught))
            self.assertNotIn("current_truth", taught[0])
            tampered = deepcopy(taught[0])
            tampered["lesson"] = "A body was built."
            memory["lessons"].append(tampered)
            memory_path.write_text(json.dumps(memory), encoding="utf-8")

            repaired = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertTrue(repaired["ok"])
            self.assertTrue(repaired["lesson_updated"])
            repaired_memory = json.loads(memory_path.read_text(encoding="utf-8"))
            repaired_rows = [
                row
                for row in repaired_memory["lessons"]
                if row.get("lesson_id") == curriculum.LESSON_ID
            ]
            self.assertEqual(1, len(repaired_rows))
            self.assertIn("start no process", repaired_rows[0]["lesson"])
            self.assertNotIn("current_truth", repaired_rows[0])

    def test_invalid_created_at_is_replaced_and_private_shape_is_not_retained(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            self.assertTrue(curriculum.teach_verified_lesson(memory_path=memory_path)["ok"])
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            taught = next(
                row for row in memory["lessons"] if row.get("lesson_id") == curriculum.LESSON_ID
            )
            taught["created_at"] = "C:\\Users\\private-person\\secret"
            taught["updated_at"] = "C:\\Users\\private-person\\secret"
            memory["updated_at"] = "C:\\Users\\private-person\\secret"
            memory_path.write_text(json.dumps(memory), encoding="utf-8")
            repaired = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertTrue(repaired["ok"])
            self.assertTrue(repaired["lesson_updated"])
            repaired_memory = json.loads(memory_path.read_text(encoding="utf-8"))
            repaired_row = next(
                row
                for row in repaired_memory["lessons"]
                if row.get("lesson_id") == curriculum.LESSON_ID
            )
            self.assertNotIn("C:\\", repaired_row["created_at"])
            self.assertNotIn("C:\\", repaired_row["updated_at"])
            self.assertTrue(curriculum._valid_created_at(repaired_row["created_at"]))
            self.assertTrue(curriculum._valid_created_at(repaired_row["updated_at"]))
            self.assertNotIn("C:\\", repaired_memory["updated_at"])
            self.assertTrue(curriculum._valid_created_at(repaired_memory["updated_at"]))

    def test_concurrent_teachers_converge_on_one_exact_lesson(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            context = multiprocessing.get_context("spawn")
            queue = context.Queue()
            workers = [
                context.Process(target=_teach_in_process, args=(str(memory_path), queue))
                for _ in range(4)
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(30)
                self.assertEqual(0, worker.exitcode)
            results = [queue.get(timeout=5) for _ in workers]
            self.assertTrue(all(result["ok"] for result in results))
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            rows = [
                row for row in memory["lessons"] if row.get("lesson_id") == curriculum.LESSON_ID
            ]
            self.assertEqual(1, len(rows))
            self.assertEqual(curriculum.EXPECTED_LESSON_TEXT, rows[0]["lesson"])

    def test_different_curriculum_writers_preserve_each_other_across_processes(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            context = multiprocessing.get_context("spawn")
            queue = context.Queue()
            workers = [
                context.Process(target=_teach_in_process, args=(str(memory_path), queue)),
                context.Process(
                    target=_teach_controller_in_process,
                    args=(str(memory_path), queue),
                ),
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(30)
                self.assertEqual(0, worker.exitcode)
            results = [queue.get(timeout=5) for _ in workers]
            self.assertTrue(all(result["ok"] for result in results))
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            lesson_ids = {
                row.get("lesson_id") for row in memory["lessons"] if isinstance(row, dict)
            }
            self.assertEqual(
                {curriculum.LESSON_ID, controller_curriculum.LESSON_ID},
                lesson_ids,
            )

    def test_invalid_existing_memory_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            memory_path.write_text("{broken", encoding="utf-8")
            result = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertFalse(result["ok"])
            self.assertEqual(
                "BLOCKED_VERIFIED_LESSON_OR_MEMORY_INVALID",
                result["status"],
            )
            self.assertEqual("{broken", memory_path.read_text(encoding="utf-8"))

    def test_candidate_truth_tamper_is_rejected(self) -> None:
        candidate = json.loads(curriculum.CANDIDATE_PATH.read_text(encoding="utf-8"))
        candidate["current_truth"]["blender_execution_authorized"] = True
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            fake_candidate = Path(raw) / "candidate.json"
            fake_candidate.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaises(ValueError):
                curriculum._validate_candidate(fake_candidate)

    def test_live_static_drift_blocks_lesson(self) -> None:
        live = dict(curriculum.transaction_closure.load_machine_static_transaction_closure())
        live["input_count"] = 17
        with mock.patch.object(
            curriculum.transaction_closure,
            "load_machine_static_transaction_closure",
            return_value=live,
        ):
            with self.assertRaises(ValueError):
                curriculum.load_verified_lesson()

    def test_exact_source_hash_or_path_substitution_is_rejected(self) -> None:
        wrong_hash = dict(curriculum.EXPECTED_CANDIDATE_SOURCE)
        wrong_hash["sha256"] = "0" * 64
        wrong_path = dict(curriculum.EXPECTED_REVIEW_SOURCE)
        wrong_path["path"] = curriculum.EXPECTED_CANDIDATE_SOURCE["path"]
        with self.assertRaises(ValueError):
            curriculum._validate_exact_source(wrong_hash)
        with self.assertRaises(ValueError):
            curriculum._validate_exact_source(wrong_path)

    def test_load_failure_blocks_memory_write(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            with mock.patch.object(
                curriculum,
                "load_verified_lesson",
                side_effect=ValueError("review differs"),
            ):
                result = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertFalse(result["ok"])
            self.assertFalse(memory_path.exists())

    def test_lock_initialization_failure_returns_a_fail_closed_result(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            blocked_parent = Path(raw) / "not_a_directory"
            blocked_parent.write_text("file", encoding="utf-8")
            memory_path = blocked_parent / "builder_memory.json"
            result = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertFalse(result["ok"])
            self.assertEqual(
                "BLOCKED_VERIFIED_LESSON_OR_MEMORY_INVALID",
                result["status"],
            )
            self.assertIn(
                "unable to initialize Avatar Builder memory write lock",
                result["failures"],
            )

    def test_memory_path_outside_project_is_rejected_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            memory_path = Path(raw) / "builder_memory.json"
            result = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertFalse(result["ok"])
            self.assertIn("memory path must remain inside the project", result["failures"])
            self.assertFalse(memory_path.exists())


if __name__ == "__main__":
    unittest.main()
