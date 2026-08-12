"""Focused, isolated tests for Avatar Builder conversational correction memory."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Core.avatar_builder_ai as builder_ai  # noqa: E402
from Core.avatar_builder_correction_memory import (  # noqa: E402
    evaluate_age_progression_stage_one_eligibility,
    evaluate_age_progression_stage_two_gate,
    verify_correction_event_chain,
)


PETER = "peter_parker_spider_man_no_way_home_final_suit"


def confirmed_adult_evidence(candidate_id: str, source_text: str) -> dict:
    return {
        "classification_id": f"confirmed-{candidate_id}",
        "subject_id": candidate_id,
        "maturity_status": "confirmed_adult",
        "authority": "Robert_explicit_owner_confirmation",
        "offline_confirmation_allowed": True,
        "network_lookup_required": False,
        "recorded_at_utc": "2026-08-03T12:00:00Z",
        "source_text": source_text,
        "source_text_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    }


class ConversationalCorrectionMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="avatar_builder_correction_test_")
        self.temp_root = Path(self._temp.name)
        self.avatar_temp = self.temp_root / "Avatar" / "temp_ai"
        self.avatar_state = self.temp_root / "Avatar" / "state" / "temp_ai"
        self.builder_root = self.temp_root / "Avatar" / "avatar_builder"
        self.patchers = [
            patch.object(builder_ai, "AVATAR_TEMP_DIR", self.avatar_temp),
            patch.object(builder_ai, "AVATAR_STATE_DIR", self.avatar_state),
            patch.object(builder_ai, "BUILDER_ROOT", self.builder_root),
            patch.object(builder_ai, "GLOBAL_MEMORY_PATH", self.builder_root / "builder_memory.json"),
            patch.object(builder_ai, "HAIR_TRAINING_ROOT", self.builder_root / "hair_training"),
            patch.object(builder_ai, "BODY_TRAINING_ROOT", self.builder_root / "body_training"),
            patch.object(builder_ai, "model_path_for_candidate", return_value=None),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()
        self._temp.cleanup()

    def seed(self, candidate_id: str, **values) -> Path:
        path = self.avatar_temp / candidate_id / "avatar_builder_adjustments.json"
        payload = {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "builder": "avatar_builder",
            "maturity_override": "",
            "preview_adjustments": {},
            "build_targets": [],
            "learning_notes": [],
            "conversation": [],
            "approval_status": "unreviewed",
        }
        payload.update(values)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def test_hair_only_correction_is_append_only_and_component_isolated(self) -> None:
        self.seed("kira", maturity_override="adult")
        first = builder_ai.avatar_builder_chat("kira", "They look bald; give them fuller hair.")
        self.assertTrue(first["ok"])
        after_first = builder_ai.load_adjustments("kira")
        first_event_snapshot = copy.deepcopy(after_first["correction_memory_events"][0])
        route = after_first["next_private_build_route"]
        self.assertEqual(route["components_to_rebuild"], ["hair"])
        self.assertTrue(route["hair_only_contract"]["detachable_component_only"])
        self.assertFalse(route["hair_only_contract"]["regenerate_body_face_eyes_skin_rig_weights_or_movement"])
        self.assertIn("body", route["components_to_preserve"])
        self.assertFalse(after_first["preview_adjustments"]["runtime_scalp_hair_enabled"])

        second = builder_ai.avatar_builder_chat("kira", "The hairline is too far back.")
        self.assertTrue(second["ok"])
        after_second = builder_ai.load_adjustments("kira")
        self.assertEqual(after_second["correction_memory_events"][0], first_event_snapshot)
        self.assertEqual(
            verify_correction_event_chain(after_second["correction_memory_events"])["status"],
            "passed",
        )
        self.assertIn("hairline_fit", after_second["last_understood_intents"])

    def test_eye_socket_and_face_likeness_route_only_named_components(self) -> None:
        self.seed("kira", maturity_override="adult")
        output = builder_ai.avatar_builder_chat(
            "kira",
            "The eyes are outside the sockets and the face does not look like Kira.",
        )
        self.assertTrue(output["ok"])
        data = builder_ai.load_adjustments("kira")
        self.assertEqual(data["next_private_build_route"]["components_to_rebuild"], ["face", "eyes"])
        self.assertIn("eye_socket_fit", data["last_understood_intents"])
        self.assertIn("face_likeness", data["last_understood_intents"])
        self.assertIn("body", data["next_private_build_route"]["components_to_preserve"])

    def test_peter_owner_adult_continuity_correction_overrides_bad_local_classification(self) -> None:
        self.seed(PETER, maturity_override="non_adult_doll_safe")
        output = builder_ai.avatar_builder_chat(
            PETER,
            (
                "No, he is an adult. Use Peter after No Way Home and before Brand New Day; "
                "Brand New Day has a four-year time jump, not the high-school era."
            ),
        )
        self.assertTrue(output["ok"])
        data = builder_ai.load_adjustments(PETER)
        self.assertEqual(data["maturity_override"], "adult")
        route = data["next_private_build_route"]
        self.assertEqual(route["body_lane"], "adult_male")
        self.assertEqual(route["replacement_strategy"], "metadata_only_preserve_current_body")
        self.assertEqual(route["components_to_rebuild"], [])
        self.assertFalse(route["classification_correction_is_body_approval"])
        event = data["correction_memory_events"][-1]
        authority = event["directives"]["maturity"]["owner_authority"]
        self.assertTrue(authority["offline_owner_confirmation_allowed"])
        self.assertFalse(authority["network_lookup_required"])
        markers = event["directives"]["continuity"]["markers"]
        self.assertIn("no_way_home", markers)
        self.assertIn("brand_new_day", markers)
        self.assertIn("not_high_school_era", markers)
        self.assertEqual(data["approval_status"], "correction_queued_private_inactive_unapproved")

        body_request = builder_ai.avatar_builder_chat(
            PETER,
            "Use an adult male body for this confirmed-adult Peter candidate.",
        )
        self.assertTrue(body_request["ok"])
        after_body_request = builder_ai.load_adjustments(PETER)
        self.assertIn(
            "body",
            after_body_request["next_private_build_route"]["components_to_rebuild"],
        )
        self.assertFalse(
            after_body_request["next_private_build_route"][
                "classification_correction_is_body_approval"
            ]
        )

    def test_isolated_high_school_reference_cannot_override_later_adult_lane(self) -> None:
        self.seed(PETER, maturity_override="adult")
        output = builder_ai.avatar_builder_chat(
            PETER,
            "Use the high-school-era photos only as contrast; keep the requested end of the series version.",
        )
        self.assertTrue(output["ok"])
        data = builder_ai.load_adjustments(PETER)
        self.assertEqual(data["maturity_override"], "adult")
        self.assertIn("continuity_timepoint", data["last_understood_intents"])
        self.assertEqual(data["next_private_build_route"]["body_lane"], "preserve_current_maturity_lane")

    def test_uncertain_candidate_accepts_explicit_offline_owner_adult_confirmation(self) -> None:
        candidate_id = "offline_fictional_character_v1"
        self.seed(candidate_id, maturity_override="uncertain_non_adult_safe_default")
        output = builder_ai.avatar_builder_chat(
            candidate_id,
            (
                "There is no internet and the local record is unsure, but I confirm this requested "
                "fictional version is an adult; trust my owner correction and use an adult body."
            ),
        )
        self.assertTrue(output["ok"])
        data = builder_ai.load_adjustments(candidate_id)
        self.assertEqual(data["maturity_override"], "adult")
        event = data["correction_memory_events"][-1]
        authority = event["directives"]["maturity"]["owner_authority"]
        self.assertTrue(authority["offline_owner_confirmation_allowed"])
        self.assertFalse(authority["network_lookup_required"])
        self.assertEqual(
            authority["authority"],
            "Robert_explicit_owner_correction",
        )

    def test_explicit_non_adult_body_cannot_be_aged_to_adult_in_place(self) -> None:
        candidate_id = "explicit_non_adult_character_v1"
        path = self.seed(candidate_id, maturity_override="non_adult_doll_safe")
        before = path.read_bytes()
        output = builder_ai.avatar_builder_chat(
            candidate_id,
            "No, this version is an adult; use an adult body.",
        )
        self.assertFalse(output["ok"])
        self.assertEqual(output["status"], "blocked_separate_age_up_variant_required")
        self.assertEqual(path.read_bytes(), before)

    def test_canonical_non_adult_identity_requires_a_distinct_spa_variant(self) -> None:
        candidate_id = builder_ai.NORMAL_MARINETTE_CANDIDATE_ID
        path = self.seed(candidate_id, maturity_override="non_adult_doll_safe")
        before = path.read_bytes()
        output = builder_ai.avatar_builder_chat(
            candidate_id,
            "Marinette chooses to age up at the spa; make her older first.",
        )
        self.assertFalse(output["ok"])
        self.assertEqual(output["status"], "blocked_separate_age_up_variant_required")
        self.assertEqual(path.read_bytes(), before)

    def test_spa_age_progression_queues_stage_one_without_adult_anatomy(self) -> None:
        candidate_id = "promoted_temp_person_spa_aged_up_variant"
        eligibility = {
            "status": "passed",
            "temporary_origin_verified": True,
            "permanent_promotion_verified": True,
            "multiple_prior_activations_verified": True,
            "prior_activation_count": 3,
            "resident_choice_recorded": True,
            "spa_flow_recorded": True,
        }
        self.seed(
            candidate_id,
            maturity_override="non_adult_doll_safe",
            age_progression_eligibility_evidence=eligibility,
        )
        profile = {
            "candidate_id": candidate_id,
            "display_name": "Promoted Temp Person aged-up variant",
            "metadata": {"age_up_variant": True},
        }
        output = builder_ai.avatar_builder_chat(
            candidate_id,
            "They chose the spa age up. Make the body taller and older, then give adult anatomy.",
            profile,
        )
        self.assertTrue(output["ok"])
        data = builder_ai.load_adjustments(candidate_id)
        route = data["next_private_build_route"]
        contract = route["age_progression"]
        self.assertEqual(contract["stage_1"]["status"], "queued_private_inactive")
        self.assertFalse(contract["stage_1"]["adult_anatomy_allowed"])
        self.assertFalse(contract["stage_2"]["adult_anatomy_allowed"])
        self.assertEqual(contract["stage_one_eligibility_gate"]["status"], "passed")
        self.assertFalse(contract["stage_one_eligibility_gate"]["adult_anatomy_allowed"])
        self.assertNotIn("adult_body_fit_status", data)
        anatomy_targets = [item for item in data["build_targets"] if item.get("area") == "anatomy_policy"]
        self.assertTrue(any("Stage 1" in item["instruction"] for item in anatomy_targets))

        adjustment_file = self.avatar_temp / candidate_id / "avatar_builder_adjustments.json"
        before_blocked_stage_two = adjustment_file.read_bytes()
        blocked_stage_two = builder_ai.avatar_builder_chat(
            candidate_id,
            "Stage 1 is done, now give the separate adult variant adult anatomy.",
            profile,
        )
        self.assertFalse(blocked_stage_two["ok"])
        self.assertEqual(
            blocked_stage_two["status"],
            "blocked_age_progression_stage_one_evidence_required",
        )
        self.assertEqual(adjustment_file.read_bytes(), before_blocked_stage_two)

        data["age_progression_stage_one_evidence"] = {
            "status": "passed",
            "separate_variant": True,
            "variant_candidate_id": candidate_id,
            "presentation_variant_label": "adult_aged_up_variant",
            "exact_maturity_status_at_stage_one": "unresolved",
            "adult_classification_confirmed": True,
            "confirmed_adult_classification_evidence": confirmed_adult_evidence(
                candidate_id,
                "Robert confirms this exact separate variant is adult.",
            ),
            "older_taller_presentation_verified": True,
            "adult_anatomy_absent": True,
            "resident_adult_anatomy_choice_recorded": True,
            "artifact_sha256": "b" * 64,
            "eligibility": {
                "status": "passed",
                "temporary_origin_verified": True,
                "permanent_promotion_verified": True,
                "multiple_prior_activations_verified": True,
                "prior_activation_count": 3,
                "resident_choice_recorded": True,
                "spa_flow_recorded": True,
            },
        }
        adjustment_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        allowed_stage_two = builder_ai.avatar_builder_chat(
            candidate_id,
            "The Stage 1 evidence passed; now give the separate adult variant adult anatomy.",
            profile,
        )
        self.assertTrue(allowed_stage_two["ok"])
        stage_two_data = builder_ai.load_adjustments(candidate_id)
        stage_two_contract = stage_two_data["next_private_build_route"]["age_progression"]
        self.assertEqual(stage_two_contract["stage_1"]["status"], "passed_exact_evidence")
        self.assertTrue(stage_two_contract["stage_2"]["adult_anatomy_allowed"])
        self.assertTrue(stage_two_contract["stage_2"]["adult_classification_confirmed"])
        self.assertTrue(stage_two_contract["stage_2"]["resident_adult_anatomy_choice_recorded"])
        self.assertEqual(stage_two_data["maturity_override"], "adult_aged_up_variant")
        self.assertEqual(stage_two_data["approval_status"], "correction_queued_private_inactive_unapproved")

    def test_stage_two_gate_requires_exact_stage_one_and_spa_eligibility_evidence(self) -> None:
        route = {
            "age_progression": {
                "contract": "two_stage_spa_age_progression_v1",
            }
        }
        blocked = evaluate_age_progression_stage_two_gate(route, {})
        self.assertEqual(blocked["status"], "blocked")
        self.assertFalse(blocked["adult_anatomy_allowed"])

        candidate_id = "exact_spa_variant"
        exact_evidence = {
            "status": "passed",
            "separate_variant": True,
            "variant_candidate_id": candidate_id,
            "presentation_variant_label": "adult_aged_up_variant",
            "exact_maturity_status_at_stage_one": "unresolved",
            "adult_classification_confirmed": True,
            "confirmed_adult_classification_evidence": confirmed_adult_evidence(
                candidate_id,
                "Robert confirms exact_spa_variant is adult.",
            ),
            "older_taller_presentation_verified": True,
            "adult_anatomy_absent": True,
            "resident_adult_anatomy_choice_recorded": True,
            "artifact_sha256": "a" * 64,
            "eligibility": {
                "status": "passed",
                "temporary_origin_verified": True,
                "permanent_promotion_verified": True,
                "multiple_prior_activations_verified": True,
                "prior_activation_count": 2,
                "resident_choice_recorded": True,
                "spa_flow_recorded": True,
            },
        }
        passed = evaluate_age_progression_stage_two_gate(route, exact_evidence)
        self.assertEqual(passed["status"], "passed")
        self.assertTrue(passed["adult_anatomy_allowed"])
        self.assertFalse(passed["runtime_activation_allowed"])

        tamper_cases = {
            "tampered_text": {
                "source_text": "Robert confirms exact_spa_variant is adult. changed"
            },
            "tampered_hash": {"source_text_sha256": "f" * 64},
            "wrong_subject": {"subject_id": "different_variant"},
            "missing_text": {"source_text": ""},
        }
        for case_name, change in tamper_cases.items():
            with self.subTest(case=case_name):
                tampered = copy.deepcopy(exact_evidence)
                tampered["confirmed_adult_classification_evidence"].update(change)
                result = evaluate_age_progression_stage_two_gate(route, tampered)
                self.assertEqual(result["status"], "blocked")
                self.assertFalse(result["adult_anatomy_allowed"])
        replayed = copy.deepcopy(exact_evidence)
        replayed["variant_candidate_id"] = "replayed_variant"
        replay_result = evaluate_age_progression_stage_two_gate(route, replayed)
        self.assertEqual(replay_result["status"], "blocked")
        self.assertIn(
            "confirmed_adult_classification_subject_mismatch",
            replay_result["failures"],
        )

    def test_stage_one_then_adult_confirmation_cannot_bypass_stage_two_choice(self) -> None:
        candidate_id = "sequential_spa_aged_up_variant"
        eligibility = {
            "status": "passed",
            "temporary_origin_verified": True,
            "permanent_promotion_verified": True,
            "multiple_prior_activations_verified": True,
            "prior_activation_count": 3,
            "resident_choice_recorded": True,
            "spa_flow_recorded": True,
        }
        path = self.seed(
            candidate_id,
            maturity_override="adult_aged_up_variant",
            age_progression_presentation_label="adult_aged_up_variant",
            exact_maturity_status="unresolved",
            complete_adult_curriculum_assignment=(
                "ADULT_CURRICULUM_BLOCKED_GUARANTEED_MINIMUM_WITH_SEPARATELY_APPROVED_AGE_APPROPRIATE_MODULES_ALLOWED"
            ),
            age_progression_contract={
                "contract": "two_stage_spa_age_progression_v1",
            },
            age_progression_stage_one_evidence={
                "status": "passed",
                "separate_variant": True,
                "variant_candidate_id": candidate_id,
                "presentation_variant_label": "adult_aged_up_variant",
                "exact_maturity_status_at_stage_one": "unresolved",
                "older_taller_presentation_verified": True,
                "adult_anatomy_absent": True,
                "resident_adult_anatomy_choice_recorded": False,
                "artifact_sha256": "d" * 64,
                "eligibility": eligibility,
            },
        )
        profile = {
            "candidate_id": candidate_id,
            "display_name": "Sequential spa aged-up variant",
            "metadata": {"age_up_variant": True},
        }

        classified = builder_ai.avatar_builder_chat(
            candidate_id,
            "I confirm this requested fictional version is an adult.",
            profile,
        )
        self.assertTrue(classified["ok"])
        classified_data = builder_ai.load_adjustments(candidate_id)
        self.assertEqual(
            classified_data["maturity_override"], "adult_aged_up_variant"
        )
        self.assertEqual(classified_data["exact_maturity_status"], "confirmed_adult")
        self.assertEqual(
            classified_data["complete_adult_curriculum_assignment"], "IMMEDIATE"
        )
        self.assertTrue(
            classified_data["age_progression_stage_one_evidence"].get(
                "confirmed_adult_classification_evidence"
            )
        )
        classification_route = classified_data["next_private_build_route"]
        self.assertEqual(
            classification_route["status"],
            "classification_recorded_no_body_build_queued",
        )
        self.assertEqual(classification_route["components_to_rebuild"], [])
        self.assertNotIn("body", classification_route["components_to_rebuild"])

        before_block = path.read_bytes()
        blocked = builder_ai.avatar_builder_chat(
            candidate_id,
            "Now use an adult body for this separate variant.",
            profile,
        )
        self.assertFalse(blocked["ok"])
        self.assertEqual(
            blocked["status"],
            "blocked_age_progression_stage_one_evidence_required",
        )
        self.assertIn(
            "resident_stage_two_adult_anatomy_choice_not_recorded",
            blocked["age_progression_stage_two_gate"]["failures"],
        )
        self.assertEqual(path.read_bytes(), before_block)

        classified_data["age_progression_stage_one_evidence"][
            "resident_adult_anatomy_choice_recorded"
        ] = True
        path.write_text(json.dumps(classified_data, indent=2), encoding="utf-8")
        passed = builder_ai.avatar_builder_chat(
            candidate_id,
            "The resident chooses the separate Stage 2 adult-anatomy revision.",
            profile,
        )
        self.assertTrue(passed["ok"])
        passed_data = builder_ai.load_adjustments(candidate_id)
        self.assertTrue(
            passed_data["next_private_build_route"]["age_progression"]["stage_2"][
                "adult_anatomy_allowed"
            ]
        )
        self.assertIn(
            "body", passed_data["next_private_build_route"]["components_to_rebuild"]
        )

    def test_stage_one_requires_promoted_repeatedly_activated_resident_choice(self) -> None:
        candidate_id = "ineligible_temp_person_spa_aged_up_variant"
        path = self.seed(candidate_id, maturity_override="non_adult_doll_safe")
        before = path.read_bytes()
        profile = {
            "candidate_id": candidate_id,
            "metadata": {"age_up_variant": True},
        }
        output = builder_ai.avatar_builder_chat(
            candidate_id,
            "They choose spa Age Progression; make the separate body older and taller first.",
            profile,
        )
        self.assertFalse(output["ok"])
        self.assertEqual(
            output["status"],
            "blocked_spa_age_progression_eligibility_required",
        )
        self.assertFalse(output["age_progression_stage_one_eligibility_gate"]["stage_one_allowed"])
        self.assertEqual(path.read_bytes(), before)

        gate = evaluate_age_progression_stage_one_eligibility(
            {
                "status": "passed",
                "temporary_origin_verified": True,
                "permanent_promotion_verified": True,
                "multiple_prior_activations_verified": True,
                "prior_activation_count": 2,
                "resident_choice_recorded": True,
                "spa_flow_recorded": True,
            }
        )
        self.assertEqual(gate["status"], "passed")
        self.assertTrue(gate["stage_one_allowed"])
        self.assertEqual(gate["verified_facts"]["prior_activation_count"], 2)
        self.assertFalse(gate["adult_anatomy_allowed"])

    def test_stage_two_requires_confirmed_adult_classification_and_resident_choice(self) -> None:
        route = {
            "age_progression": {
                "contract": "two_stage_spa_age_progression_v1",
            }
        }
        evidence = {
            "status": "passed",
            "separate_variant": True,
            "presentation_variant_label": "adult_aged_up_variant",
            "exact_maturity_status_at_stage_one": "unresolved",
            "older_taller_presentation_verified": True,
            "adult_anatomy_absent": True,
            "artifact_sha256": "c" * 64,
            "eligibility": {
                "status": "passed",
                "temporary_origin_verified": True,
                "permanent_promotion_verified": True,
                "multiple_prior_activations_verified": True,
                "prior_activation_count": 3,
                "resident_choice_recorded": True,
                "spa_flow_recorded": True,
            },
        }
        blocked = evaluate_age_progression_stage_two_gate(route, evidence)
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn(
            "confirmed_adult_classification_evidence_missing",
            blocked["failures"],
        )
        self.assertIn(
            "resident_stage_two_adult_anatomy_choice_not_recorded",
            blocked["failures"],
        )
        self.assertFalse(blocked["adult_anatomy_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
