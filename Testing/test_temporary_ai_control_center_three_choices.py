from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools import temporary_ai_control_center as control_center  # noqa: E402


class TemporaryAIControlCenterThreeChoiceTests(unittest.TestCase):
    def test_visible_creator_choices_are_exactly_the_three_owner_choices(self) -> None:
        self.assertEqual(
            control_center.VISIBLE_AI_TYPE_LABELS,
            {
                "Expert": "Expert",
                "Fictional": "Fictional Character",
                "Historical": "Historical Person",
            },
        )

    def test_existing_internal_type_labels_remain_available(self) -> None:
        self.assertEqual(control_center.AI_TYPE_LABELS["Expert"], "expert_temp_ai")
        self.assertEqual(
            control_center.AI_TYPE_LABELS["Fictional Character"],
            "canon_reconstruction_temp_ai",
        )
        self.assertEqual(
            control_center.AI_TYPE_LABELS["Historical Person"],
            "historical_temp_ai",
        )

    def test_shared_identity_is_stable_and_portable(self) -> None:
        first = control_center.shared_person_id_for("candidate-001", "Mira Sol")
        second = control_center.shared_person_id_for("candidate-001", "Mira Sol")
        changed = control_center.shared_person_id_for("candidate-002", "Mira Sol")
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertTrue(first.startswith("temporary_mira_sol_"))
        self.assertLessEqual(len(first), 80)

    def test_one_creator_command_queues_the_shared_person_pipeline(self) -> None:
        expected = {
            "person_id": "temporary_mira_sol_deadbeef0000",
            "bundle_id": "bundle-001",
            "workspace_relative": "TemporaryAI/creator_work_orders/person",
            "overall_status": "queued",
            "result_sha256": "a" * 64,
        }
        with (
            patch.object(
                control_center,
                "shared_person_id_for",
                return_value=expected["person_id"],
            ),
            patch.object(
                control_center,
                "orchestrate_temporary_creator",
                return_value=expected,
            ) as orchestrate,
        ):
            result = control_center.queue_shared_person_pipeline(
                candidate_id="candidate-001",
                kind_label="Expert",
                query="algebra",
                version="",
                gender="Female",
                personality="patient and encouraging",
                display_name="Mira Sol",
                role_title="algebra expert",
                allow_kira=True,
                allow_lisa=False,
            )

        self.assertEqual(result, expected)
        root, workspace, payload = orchestrate.call_args.args
        self.assertEqual(root, control_center.PROJECT_ROOT)
        self.assertEqual(
            workspace,
            Path("TemporaryAI") / "creator_work_orders" / expected["person_id"],
        )
        self.assertEqual(payload["creator_type"], "expert")
        self.assertEqual(payload["subject_or_domain"], "algebra")
        self.assertEqual(payload["person_id"], expected["person_id"])
        self.assertTrue(payload["requested_by"]["authenticated"])
        self.assertTrue(payload["requested_by"]["authorized"])
        self.assertEqual(payload["requested_by"]["authority_class"], "founder")


if __name__ == "__main__":
    unittest.main()
