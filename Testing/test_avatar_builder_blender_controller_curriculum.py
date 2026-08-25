"""Tests for the verified Blender controller lesson publication."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_builder_blender_controller_curriculum as curriculum


class AvatarBuilderBlenderControllerCurriculumTests(unittest.TestCase):
    def test_lesson_binds_exact_sources_and_preserves_all_false_authority(self) -> None:
        lesson = curriculum.load_verified_lesson()
        self.assertEqual(
            "VERIFIED_REUSABLE_FAIL_CLOSED_SAFETY_METHOD",
            lesson["status"],
        )
        truth = lesson["current_truth"]
        self.assertIs(truth["static_controller_verified"], True)
        self.assertIs(truth["static_native_contract_verified"], True)
        for key in (
            "native_provider_reviewed",
            "operating_system_evidence_verified",
            "execution_trust_boundary_closed",
            "resume_authorized",
            "blender_execution_authorized",
            "body_build_authorized",
            "body_created",
            "candidate_assignment_authorized",
            "anatomy_authoring_authorized",
            "runtime_activation_authorized",
            "public_export_authorized",
        ):
            self.assertIs(truth[key], False)
        self.assertEqual(3, len(lesson["source_bindings"]))
        self.assertEqual(9, len(lesson["verified_reusable_lessons"]))
        self.assertIn("start no process", lesson["lesson"])
        self.assertIn("not OS proof", lesson["lesson"])

    def test_teaching_is_idempotent_and_repairs_a_tampered_duplicate(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            memory_path = Path(raw) / "builder_memory.json"
            first = curriculum.teach_verified_lesson(memory_path=memory_path)
            second = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertTrue(first["ok"])
            self.assertTrue(first["lesson_added"])
            self.assertTrue(second["ok"])
            self.assertFalse(second["lesson_added"])
            self.assertFalse(second["lesson_updated"])

            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            taught = [
                row for row in memory["lessons"] if row.get("lesson_id") == curriculum.LESSON_ID
            ]
            self.assertEqual(1, len(taught))
            bad = deepcopy(taught[0])
            bad["lesson"] = "A body was built and activated."
            memory["lessons"].append(bad)
            memory_path.write_text(json.dumps(memory), encoding="utf-8")
            repaired = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertTrue(repaired["lesson_updated"])
            repaired_memory = json.loads(memory_path.read_text(encoding="utf-8"))
            repaired_rows = [
                row
                for row in repaired_memory["lessons"]
                if row.get("lesson_id") == curriculum.LESSON_ID
            ]
            self.assertEqual(1, len(repaired_rows))
            self.assertIn("start no process", repaired_rows[0]["lesson"])
            self.assertFalse(repaired_rows[0]["current_truth"]["body_created"])

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

    def test_source_tamper_blocks_lesson_and_memory_write(self) -> None:
        lesson = json.loads(curriculum.LESSON_PATH.read_text(encoding="utf-8"))
        lesson["current_truth"]["blender_execution_authorized"] = True
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            fake_lesson = root / "lesson.json"
            memory_path = root / "builder_memory.json"
            fake_lesson.write_text(json.dumps(lesson), encoding="utf-8")
            with mock.patch.object(curriculum, "LESSON_PATH", fake_lesson):
                result = curriculum.teach_verified_lesson(memory_path=memory_path)
            self.assertFalse(result["ok"])
            self.assertFalse(memory_path.exists())

    def test_lesson_rejects_source_role_or_path_substitution(self) -> None:
        original = json.loads(curriculum.LESSON_PATH.read_text(encoding="utf-8"))
        mutations = []
        wrong_role = deepcopy(original)
        wrong_role["source_bindings"][0]["role"] = "unrelated_role"
        mutations.append(wrong_role)
        duplicate = deepcopy(original)
        duplicate["source_bindings"][0] = deepcopy(duplicate["source_bindings"][1])
        mutations.append(duplicate)
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            for index, mutation in enumerate(mutations):
                fake_lesson = root / f"lesson_{index}.json"
                fake_lesson.write_text(json.dumps(mutation), encoding="utf-8")
                with mock.patch.object(curriculum, "LESSON_PATH", fake_lesson):
                    with self.subTest(index=index), self.assertRaises(ValueError):
                        curriculum.load_verified_lesson()


if __name__ == "__main__":
    unittest.main()
