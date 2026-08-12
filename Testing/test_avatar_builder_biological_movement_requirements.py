from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_PATH = (
    ROOT
    / "Avatar"
    / "movement_library"
    / "avatar_builder_biological_movement_requirements_20260803.json"
)
SYSTEM_DOCUMENT_PATH = (
    ROOT / "System" / "docs" / "AVATAR_BUILDER_BIOLOGICAL_MOVEMENT_REQUIREMENTS_20260803.md"
)
PREPARATION_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "avatar_builder_biological_movement_requirements_preparation_20260803"
    / "VALIDATION_PREPARATION.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AvatarBuilderBiologicalMovementRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.requirements = json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
        cls.preparation = json.loads(PREPARATION_PATH.read_text(encoding="utf-8"))
        cls.document = SYSTEM_DOCUMENT_PATH.read_text(encoding="utf-8")
        cls.motions = {
            item["id"]: item for item in cls.requirements["motion_requirements"]
        }

    def test_scope_is_documentation_only_and_unapproved(self) -> None:
        self.assertEqual(
            self.requirements["status"],
            "DOCUMENTATION_AND_TEST_PREPARATION_ONLY_ALL_MOTIONS_PENDING_UNAPPROVED",
        )
        scope = self.requirements["scope"]
        for key in (
            "blender_run_authorized",
            "render_run_authorized",
            "runtime_activation_authorized",
            "candidate_selection_or_promotion_authorized",
            "existing_manifest_or_candidate_mutation_authorized",
        ):
            self.assertFalse(scope[key])

    def test_every_motion_is_pending_and_promotion_is_blocked(self) -> None:
        self.assertGreaterEqual(len(self.motions), 12)
        self.assertTrue(
            all(item["status"] == "PENDING_UNAPPROVED" for item in self.motions.values())
        )
        gate = self.requirements["global_motion_acceptance"]
        self.assertEqual(gate["contact_gate_status"], "PENDING_NO_PASS_EVIDENCE")
        self.assertEqual(gate["intersection_gate_status"], "PENDING_NO_PASS_EVIDENCE")
        self.assertEqual(gate["owner_approval_status"], "NOT_APPROVED")
        self.assertFalse(gate["promotion_allowed"])
        required = " ".join(gate["required_before_motion_can_be_called_validated"]).lower()
        for phrase in (
            "rendered",
            "contact",
            "self-intersection",
            "penetration",
            "owner explicitly approves",
        ):
            self.assertIn(phrase, required)

    def test_relaxed_neutral_arms_cannot_remain_abducted(self) -> None:
        neutral = self.motions["neutral_relaxed_arms"]
        phases = " ".join(neutral["required_phases"]).lower()
        rejected = " ".join(neutral["rejection_conditions"]).lower()
        self.assertIn("without_abduction", phases)
        self.assertIn("t-pose", rejected)
        self.assertIn("a-pose", rejected)
        self.assertIn("arms must not remain abducted", self.requirements["owner_truth"]["neutral_arms_requirement"])

    def test_walk_jog_and_run_have_separate_arm_swing_contracts(self) -> None:
        for motion_id in (
            "walk_with_biological_arm_swing",
            "jog_with_biological_arm_swing",
            "run_with_biological_arm_swing",
        ):
            motion = self.motions[motion_id]
            evidence = " ".join(motion["required_evidence"]).lower()
            phases = " ".join(motion["required_phases"]).lower()
            combined = f"{motion_id} {phases} {evidence}"
            self.assertIn("arm", combined)
            self.assertIn("contralateral", combined)
            self.assertIn("intersection", evidence)

    def test_book_tablet_and_phone_require_articulated_contact_and_release(self) -> None:
        expected = {
            "reach_grasp_hold_release_book": "book",
            "reach_grasp_hold_release_tablet": "tablet",
            "reach_grasp_hold_release_phone": "phone",
        }
        for motion_id, prop_class in expected.items():
            motion = self.motions[motion_id]
            self.assertEqual(motion["exact_prop_class"], prop_class)
            phases = " ".join(motion["required_phases"]).lower()
            evidence = " ".join(motion["required_evidence"]).lower()
            for concept in ("reach", "preshape", "contact", "grasp", "release"):
                self.assertIn(concept, phases)
            self.assertIn("prop id and hash", evidence)
            self.assertIn("penetration", evidence)

    def test_door_push_and_pull_require_real_handle_operation(self) -> None:
        for motion_id, direction in (
            ("door_handle_turn_and_push", "push"),
            ("door_handle_turn_and_pull", "pull"),
        ):
            motion = self.motions[motion_id]
            phases = " ".join(motion["required_phases"]).lower()
            evidence = " ".join(motion["required_evidence"]).lower()
            for concept in ("reach", "grip", "turn", "contact", direction, "release"):
                self.assertIn(concept, phases)
            self.assertIn("handle hinge and latch ids", evidence)
            self.assertIn("intersection", evidence)

    def test_handwashing_shower_and_bath_sequences_are_complete(self) -> None:
        handwashing = " ".join(
            self.motions["handwashing_complete_sequence"]["required_phases"]
        ).lower()
        for concept in (
            "water_control",
            "soap",
            "palms",
            "backs_of_hands",
            "between_fingers",
            "thumbs",
            "fingertips",
            "wrists",
            "rinse",
            "dry",
        ):
            self.assertIn(concept.replace("_", " "), handwashing)
        shower = " ".join(
            self.motions["shower_entry_controls_washing_exit"]["required_phases"]
        ).lower()
        bath = " ".join(
            self.motions["bath_entry_controls_washing_exit"]["required_phases"]
        ).lower()
        for sequence in (shower, bath):
            for concept in ("approach", "control", "wash", "exit", "towel", "balance"):
                self.assertIn(concept, sequence)
        self.assertIn("step over tub wall", bath)
        self.assertIn("step into shower", shower)

    def test_required_owner_views_include_protected_anatomy_and_deformation(self) -> None:
        views = {item["id"]: item for item in self.requirements["required_owner_views"]}
        self.assertEqual(
            set(views),
            {
                "full_body_front",
                "full_body_left_oblique",
                "full_body_right_oblique",
                "full_body_left_side",
                "full_body_right_side",
                "full_body_rear",
                "underside_perineal_clinical_private",
                "seated_support_and_contact",
                "bend_and_deformation",
            },
        )
        self.assertTrue(all(item["status"] == "PENDING_UNRENDERED_UNAPPROVED" for item in views.values()))
        self.assertEqual(
            views["underside_perineal_clinical_private"]["handling"],
            "private_owner_review_only_clinical_nonpublic",
        )

    def test_no_pelvic_candidate_is_described_as_owner_approved(self) -> None:
        self.assertEqual(
            self.requirements["owner_truth"]["pelvic_candidate_status"],
            "NO_PELVIC_CANDIDATE_IS_OWNER_APPROVED",
        )
        pelvis = self.preparation["pelvis_truth"]
        self.assertFalse(pelvis["owner_approved_pelvic_candidate_exists"])
        self.assertTrue(pelvis["movement_evidence_may_not_change_this_status"])

    def test_existing_manifests_remain_byte_identical(self) -> None:
        records = self.requirements["preservation_contract"]["preserved_records"]
        for record in records:
            self.assertEqual(sha256_file(ROOT / record["path"]), record["sha256_at_preparation"])
        self.assertFalse(self.requirements["preservation_contract"]["existing_manifest_modified"])
        self.assertFalse(self.requirements["preservation_contract"]["candidate_blend_modified"])

    def test_preparation_hash_binds_requirements_and_system_document(self) -> None:
        self.assertEqual(
            sha256_file(REQUIREMENTS_PATH), self.preparation["requirements"]["sha256"]
        )
        self.assertEqual(
            sha256_file(SYSTEM_DOCUMENT_PATH), self.preparation["system_document"]["sha256"]
        )
        execution = self.preparation["execution"]
        self.assertTrue(all(value is False for value in execution.values()))
        future = self.preparation["planned_future_evidence"]
        self.assertFalse(future["current_evidence_exists"])
        self.assertEqual(future["current_motion_approval"], "NONE")

    def test_system_document_states_truth_and_append_only_boundaries(self) -> None:
        normalized_document = " ".join(self.document.split())
        for phrase in (
            "pending, unrendered, and unapproved",
            "No pelvic candidate is owner-approved",
            "protected private underside/perineal clinical view",
            "parenting a prop to a hand",
            "does not edit or replace the existing foundation movement manifest",
            "No Blender, rendering, GPU",
        ):
            self.assertIn(phrase, normalized_document)


if __name__ == "__main__":
    unittest.main()
