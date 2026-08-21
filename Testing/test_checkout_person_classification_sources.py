import hashlib
import json
from pathlib import Path
import unittest

from Core.adult_health_curriculum_runtime import (
    EXPERT_CURRICULUM_EXTENSION_BINDING,
    PERSON_CLASSIFICATION_BINDINGS,
)
from Core.kira_lisa_college_reflection_runtime import OWNER_DIRECTIVE_BINDING


ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CheckoutPersonClassificationSourcesTest(unittest.TestCase):
    def test_every_runtime_classification_binding_is_present_and_exact(self) -> None:
        for person_id, binding in PERSON_CLASSIFICATION_BINDINGS.items():
            path = Path(binding["path"])
            with self.subTest(person_id=person_id):
                self.assertTrue(path.is_file())
                self.assertEqual(file_sha256(path), binding["sha256"])
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["subject_id"], person_id)
                self.assertEqual(payload["maturity_status"], "confirmed_adult")
                self.assertFalse(payload["effects"]["lesson_completion_claimed"])
                self.assertFalse(payload["effects"]["body_function_claimed"])
                self.assertFalse(
                    payload["effects"]["relationship_or_activity_permission_created"]
                )

    def test_supporting_owner_records_are_present_and_exact(self) -> None:
        bindings = (
            EXPERT_CURRICULUM_EXTENSION_BINDING,
            OWNER_DIRECTIVE_BINDING,
        )
        for binding in bindings:
            path = ROOT / binding["path"]
            with self.subTest(path=binding["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(file_sha256(path), binding["sha256"])

    def test_marinette_is_not_added_to_confirmed_adult_runtime_bindings(self) -> None:
        self.assertNotIn("marinette", PERSON_CLASSIFICATION_BINDINGS)
        self.assertFalse(
            any("marinette" in person_id for person_id in PERSON_CLASSIFICATION_BINDINGS)
        )


if __name__ == "__main__":
    unittest.main()
