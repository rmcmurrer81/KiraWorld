from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_builder_ai as builder_ai  # noqa: E402


CANONICAL_WRITE_TARGETS = (
    PROJECT_ROOT / "Avatar" / "avatar_builder" / "builder_memory.json",
    PROJECT_ROOT / "Avatar" / "avatar_builder" / "body_training" / "body_fit_plans" / "kira_adult_body_fit_plan.json",
    PROJECT_ROOT / "Avatar" / "avatar_builder" / "body_training" / "body_fit_plans" / "spider_gwen_spider_gwen_20260606_013325_adult_body_fit_plan.json",
    PROJECT_ROOT / "Avatar" / "avatar_builder" / "eye_training" / "kira_eye_rebuild_plan.json",
    PROJECT_ROOT / "Avatar" / "avatar_builder" / "eye_training" / "spider_gwen_spider_gwen_20260606_013325_eye_rebuild_plan.json",
    PROJECT_ROOT / "Avatar" / "avatar_builder" / "tests" / "avatar_builder_chat_understanding_20260713.json",
    PROJECT_ROOT / "Avatar" / "temp_ai" / "kira" / "avatar_builder_adjustments.json",
    PROJECT_ROOT / "Avatar" / "temp_ai" / "spider_gwen_spider_gwen_20260606_013325" / "avatar_builder_adjustments.json",
)


def _canonical_hashes() -> dict[str, str | None]:
    return {
        path.relative_to(PROJECT_ROOT).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        )
        for path in CANONICAL_WRITE_TARGETS
    }


class AvatarBuilderAITests(unittest.TestCase):
    def setUp(self) -> None:
        self._canonical_hashes_before = _canonical_hashes()

    def tearDown(self) -> None:
        self.assertEqual(
            _canonical_hashes(),
            self._canonical_hashes_before,
            "Avatar Builder AI unit test mutated canonical builder state",
        )

    def test_maturity_parser_distinguishes_global_policy_from_candidate_age(self) -> None:
        self.assertIsNone(
            builder_ai._maturity_from_message(
                "Only non adults are supposed to get Barbie safe bodies."
            )
        )
        self.assertEqual(
            builder_ai._maturity_from_message(
                "Gwen is an adult and must not use non-adult doll-safe treatment."
            )[0],
            "adult",
        )
        self.assertEqual(
            builder_ai._maturity_from_message(
                "This teen character must not receive adult anatomy."
            )[0],
            "non_adult_doll_safe",
        )
        self.assertEqual(
            builder_ai._maturity_from_message("This is not an adult body.")[0],
            "non_adult_doll_safe",
        )
        for policy_text in (
            "Review the adult policy and adult test results.",
            "The adult anatomy reference folder is locked.",
            "This is an adult body policy document, not a person classification.",
            "Do not age up this person at the spa.",
            "The age progression policy must remain fail closed.",
        ):
            with self.subTest(policy_text=policy_text):
                self.assertIsNone(builder_ai._maturity_from_message(policy_text))
        self.assertEqual(
            builder_ai._maturity_from_message(
                "I confirm this requested fictional version is an adult."
            )[0],
            "adult",
        )
        self.assertEqual(
            builder_ai._maturity_from_message(
                "They chose to go to the spa and age up this separate variant."
            )[0],
            "adult_aged_up_variant",
        )

    def test_chat_records_head_eye_and_maturity_correction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            memory_path = builder_root / "builder_memory.json"

            with (
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", memory_path),
                patch.object(
                    builder_ai,
                    "inspect_candidate_model",
                    return_value={
                        "model_ready": True,
                        "model_path": "Avatar/models/temp_ai/test/avatar.glb",
                        "node_count": 10,
                        "mesh_count": 2,
                        "issues": ["no named eye/iris/pupil meshes; eye-socket checks cannot be automatic yet"],
                    },
                ),
            ):
                result = builder_ai.avatar_builder_chat(
                    "test_candidate",
                    "This avatar is adult, the head is too small, and the eyes are outside the sockets.",
                )
                self.assertTrue(result["ok"])

                saved = json.loads((avatar_root / "test_candidate" / "avatar_builder_adjustments.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["maturity_override"], "adult")
                self.assertGreater(saved["preview_adjustments"]["head_scale"], 1.0)
                self.assertEqual(saved["preview_adjustments"]["eye_guide_y"], 0.835)
                areas = {item["area"] for item in saved["build_targets"]}
                self.assertIn("head", areas)
                self.assertIn("eyes", areas)

    def test_kira_eye_followup_does_not_erase_persisted_brown_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            memory_path = builder_root / "builder_memory.json"

            with (
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", memory_path),
                patch.object(
                    builder_ai,
                    "inspect_candidate_model",
                    return_value={
                        "model_ready": True,
                        "model_path": "Avatar/models/temp_ai/kira/avatar.glb",
                        "node_count": 10,
                        "mesh_count": 2,
                        "issues": ["no named eye/iris/pupil meshes"],
                    },
                ),
            ):
                builder_ai.avatar_builder_chat(
                    "kira", "Give Kira realistic brown eyes inside her eye sockets."
                )
                builder_ai.avatar_builder_chat("kira", "Give Kira eyes.")

            plan = json.loads(
                (builder_root / "eye_training" / "kira_eye_rebuild_plan.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertIn("brown", plan["target_eye_color"])
            self.assertEqual(
                plan["target_eye_color_status"],
                "requested_draft_pending_avatar_owner_review",
            )

    def test_marinette_review_uses_smooth_non_adult_preview_without_box_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            memory_path = builder_root / "builder_memory.json"

            with (
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", memory_path),
                patch.object(
                    builder_ai,
                    "inspect_candidate_model",
                    return_value={
                        "model_ready": True,
                        "model_path": "Avatar/models/temp_ai/marinette/avatar.glb",
                        "node_count": 10,
                        "mesh_count": 2,
                        "issues": [],
                    },
                ),
            ):
                result = builder_ai.run_builder_review("ladybug_marinette_expanded_smoke")
                adjustments = result["adjustments"]
                self.assertEqual(adjustments["maturity_override"], "non_adult_doll_safe")
                self.assertFalse(adjustments["preview_adjustments"]["non_adult_review_garment"])
                hair_plan = builder_root / "hair_training" / "ladybug_marinette_expanded_smoke_hair_rebuild_plan.json"
                self.assertTrue(hair_plan.exists())
                eye_plan = builder_root / "eye_training" / "ladybug_marinette_expanded_smoke_eye_rebuild_plan.json"
                self.assertTrue(eye_plan.exists())

    def test_marinette_redo_job_marks_failed_preview_and_pairs_adult_test(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            memory_path = builder_root / "builder_memory.json"

            with (
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", memory_path),
                patch.object(
                    builder_ai,
                    "inspect_candidate_model",
                    return_value={
                        "model_ready": True,
                        "model_path": "Avatar/models/temp_ai/test/avatar.glb",
                        "node_count": 10,
                        "mesh_count": 2,
                        "issues": ["no named eye/iris/pupil meshes"],
                    },
                ),
            ):
                result = builder_ai.create_avatar_redo_job(
                    "ladybug_marinette_expanded_smoke",
                    "spider_gwen_spider_gwen_20260606_013325",
                    "Robert rejected the current Marinette body as not close enough.",
                )
                self.assertTrue(result["ok"])

                redo_path = builder_root / "redo_jobs" / "ladybug_marinette_expanded_smoke_redo_job.json"
                self.assertTrue(redo_path.exists())
                redo = json.loads(redo_path.read_text(encoding="utf-8"))
                self.assertFalse(redo["current_model_is_approved"])
                self.assertEqual(redo["paired_adult_test"]["candidate_id"], "spider_gwen_spider_gwen_20260606_013325")

                saved = json.loads((avatar_root / "ladybug_marinette_expanded_smoke" / "avatar_builder_adjustments.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["approval_status"], "failed_redo_required")
                self.assertEqual(saved["maturity_override"], "non_adult_doll_safe")
                self.assertFalse(saved["preview_adjustments"]["non_adult_review_garment"])
                self.assertIn("redo_job_path", saved)

    def test_gwen_review_uses_unmasked_model_and_spandex_as_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            memory_path = builder_root / "builder_memory.json"
            project_root = root
            (project_root / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen").mkdir(parents=True)
            (project_root / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen" / "spider-_gwen.glb").write_bytes(b"glTF-test")
            (project_root / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen" / "spider_gwen_low_poly_unmasked_reference.glb").write_bytes(b"glTF-test")

            with (
                patch.object(builder_ai, "PROJECT_ROOT", project_root),
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", memory_path),
                patch.object(
                    builder_ai,
                    "inspect_candidate_model",
                    return_value={
                        "model_ready": True,
                        "model_path": "Avatar/models/temp_ai/gwen/avatar.glb",
                        "node_count": 10,
                        "mesh_count": 2,
                        "issues": [],
                    },
                ),
            ):
                result = builder_ai.run_builder_review("spider_gwen_spider_gwen_20260606_013325")
                adjustments = result["adjustments"]
                self.assertEqual(adjustments["maturity_override"], "adult")
                self.assertEqual(adjustments["approval_status"], "adult_rebuild_sources_ready")
                self.assertEqual(adjustments["test_role"], "adult_reference_test_pick_sources_ready")
                instructions = " ".join(item["instruction"] for item in adjustments["build_targets"])
                self.assertIn("spandex", instructions)
                self.assertIn("removable clothing", instructions)
                self.assertIn("unmasked Gwen model", instructions)
                eye_plan = builder_root / "eye_training" / "spider_gwen_spider_gwen_20260606_013325_eye_rebuild_plan.json"
                self.assertTrue(eye_plan.exists())
                wardrobe_plan = builder_root / "wardrobe_training" / "spider_gwen_spider_gwen_20260606_013325_spandex_removable_clothing_plan.json"
                self.assertTrue(wardrobe_plan.exists())

    def test_builder_review_does_not_substring_upgrade_non_adult_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            memory_path = builder_root / "builder_memory.json"
            state_root.mkdir(parents=True)
            state_path = state_root / "sentinel.json"
            state_path.write_bytes(b"unchanged-state")
            before = state_path.read_bytes()

            with (
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", memory_path),
                patch.object(
                    builder_ai,
                    "inspect_candidate_model",
                    return_value={"model_ready": False, "issues": []},
                ),
            ):
                for candidate_id in ("minor_gwen", "child_kira", "teen_peter"):
                    with self.subTest(candidate_id=candidate_id):
                        result = builder_ai.run_builder_review(candidate_id)
                        self.assertNotIn(
                            result["adjustments"].get("maturity_override"),
                            builder_ai.ADULT_CLASSES,
                        )
            self.assertEqual(state_path.read_bytes(), before)

    def test_normal_marinette_age_up_chat_is_blocked_without_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            model_path = root / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke" / "avatar.glb"
            state_path = state_root / "ladybug_marinette_expanded_smoke.json"
            model_path.parent.mkdir(parents=True)
            state_path.parent.mkdir(parents=True)
            model_path.write_bytes(b"unchanged-model")
            state_path.write_bytes(b"unchanged-state")
            model_before = model_path.read_bytes()
            state_before = state_path.read_bytes()

            with (
                patch.object(builder_ai, "PROJECT_ROOT", root),
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", builder_root / "builder_memory.json"),
            ):
                result = builder_ai.avatar_builder_chat(
                    "ladybug_marinette_expanded_smoke",
                    "Age-up Marinette into an adult variant.",
                    {
                        "candidate_id": "ladybug_marinette_expanded_smoke",
                        "display_name": "Marinette Dupain-Cheng",
                    },
                )

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "blocked_separate_age_up_variant_required")
            self.assertFalse(result["adjustments_saved"])
            self.assertFalse((avatar_root / "ladybug_marinette_expanded_smoke" / "avatar_builder_adjustments.json").exists())
            self.assertEqual(model_path.read_bytes(), model_before)
            self.assertEqual(state_path.read_bytes(), state_before)
            self.assertFalse((builder_root / "builder_memory.json").exists())

    def test_distinct_aged_up_candidate_profile_can_record_age_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            candidate_id = "ladybug_marinette_aged_up_variant"
            profile = {
                "candidate_id": candidate_id,
                "display_name": "Marinette aged-up variant",
                "metadata": {
                    "age_up_variant": True,
                    "source_candidate_id": "ladybug_marinette_expanded_smoke",
                },
                "age_progression_eligibility_evidence": {
                    "status": "passed",
                    "temporary_origin_verified": True,
                    "permanent_promotion_verified": True,
                    "multiple_prior_activations_verified": True,
                    "prior_activation_count": 2,
                    "resident_choice_recorded": True,
                    "spa_flow_recorded": True,
                },
            }
            with (
                patch.object(builder_ai, "PROJECT_ROOT", root),
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", builder_root / "builder_memory.json"),
                patch.object(
                    builder_ai,
                    "inspect_candidate_model",
                    return_value={"model_ready": False, "issues": []},
                ),
            ):
                result = builder_ai.avatar_builder_chat(
                    candidate_id,
                    "Age-up this separate candidate into an adult variant.",
                    profile,
                )
            self.assertTrue(result["ok"])
            self.assertEqual(result["adjustments"]["maturity_override"], "adult_aged_up_variant")

    def test_confirmed_adult_cannot_be_switched_to_doll_safe_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            state_root = root / "Avatar" / "state" / "temp_ai"
            builder_root = root / "Avatar" / "avatar_builder"
            state_root.mkdir(parents=True)
            state_path = state_root / "kira.json"
            state_path.write_bytes(b"unchanged-adult-state")
            before = state_path.read_bytes()
            with (
                patch.object(builder_ai, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(builder_ai, "AVATAR_STATE_DIR", state_root),
                patch.object(builder_ai, "BUILDER_ROOT", builder_root),
                patch.object(builder_ai, "HAIR_TRAINING_ROOT", builder_root / "hair_training"),
                patch.object(builder_ai, "BODY_TRAINING_ROOT", builder_root / "body_training"),
                patch.object(builder_ai, "GLOBAL_MEMORY_PATH", builder_root / "builder_memory.json"),
            ):
                result = builder_ai.avatar_builder_chat(
                    "kira",
                    "Kira should use a doll-safe body.",
                    {"candidate_id": "kira", "display_name": "Kira"},
                )
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "blocked_maturity_identity_policy")
            self.assertIn(
                "canonical_adult_identity_cannot_switch_to_doll_safe",
                result["maturity_identity_validation"]["failures"],
            )
            self.assertFalse((avatar_root / "kira" / "avatar_builder_adjustments.json").exists())
            self.assertEqual(state_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
