from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from Core.avatar_component_production import plan_orchestration_request
from Core.avatar_profile_preflight import (
    AvatarProfilePreflightError,
    evaluate_avatar_profile_preflight,
    evaluate_current_avatar_profile_batch,
    evaluate_orchestration_identity_preflight,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUEST_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder" / "orchestration_requests"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


class AvatarProfilePreflightTests(unittest.TestCase):
    def test_beth_has_bound_version_and_adult_lane_without_profile_mutation(self) -> None:
        profile = (
            PROJECT_ROOT
            / "TemporaryAI"
            / "candidates"
            / "beth_smith_ordinary_temp_20260716"
            / "temporary_ai_profile.json"
        )
        creation = profile.with_name("creation_request.json")
        before = (sha256(profile), sha256(creation))
        request = json.loads(
            (REQUEST_ROOT / "beth_smith_ordinary_temp_20260716.json").read_text()
        )
        result = evaluate_orchestration_identity_preflight(PROJECT_ROOT, request)
        after = (sha256(profile), sha256(creation))

        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual("home_beth_through_s9e8_20260712", result["identity"]["selected_version"])
        self.assertEqual("adult", result["maturity"]["lane"])
        self.assertEqual("confirmed_adult_topology", result["maturity"]["safety_topology_lane"])
        self.assertEqual(before, after)
        self.assertFalse(result["canonical_profile"]["mutation_performed"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_robert_body_request_resolves_explicit_alias_to_one_profile(self) -> None:
        request = json.loads((REQUEST_ROOT / "robert_user_avatar_20260716.json").read_text())
        result = evaluate_orchestration_identity_preflight(PROJECT_ROOT, request)
        self.assertTrue(result["passed"], result["failures"])
        self.assertTrue(result["candidate_alias_used"])
        self.assertEqual("robert_mcmurrer_presence_ai", result["canonical_candidate_id"])
        self.assertEqual("robert_mcmurrer", result["identity"]["subject_id"])
        self.assertEqual("adult", result["maturity"]["lane"])

    def test_still_blank_fictional_versions_remain_unresolved_and_authoring_blocked(self) -> None:
        candidates = (
            "cameron_terminator_cameron_terminator_20260605_225316",
            "mary_campbell_mary_campbell_20260605_224544",
            "peter_parker_spider_man_no_way_home_final_suit",
        )
        for candidate_id in candidates:
            with self.subTest(candidate_id=candidate_id):
                result = evaluate_avatar_profile_preflight(PROJECT_ROOT, candidate_id)
                self.assertFalse(result["passed"])
                self.assertIn("fictional_version_blank", result["failures"])
                self.assertIn("maturity_unresolved_authoring_blocked", result["failures"])
                self.assertEqual("unresolved_doll_safe", result["maturity"]["lane"])
                self.assertEqual(
                    "non_adult_doll_safe_topology",
                    result["maturity"]["safety_topology_lane"],
                )
                self.assertFalse(result["maturity"]["unresolved_fallback_is_authoring_authority"])

    def test_ruby_whole_series_knowledge_is_resolved_but_body_remains_blocked(self) -> None:
        result = evaluate_avatar_profile_preflight(
            PROJECT_ROOT,
            "ruby_supernatural_ruby_supernatural_20260605_223416",
        )
        self.assertFalse(result["passed"])
        self.assertNotIn("fictional_version_blank", result["failures"])
        self.assertNotIn("fictional_version_binding_mismatch", result["failures"])
        self.assertIn("maturity_unresolved_authoring_blocked", result["failures"])
        self.assertEqual(
            "Supernatural television series",
            result["identity"]["selected_version"],
        )
        self.assertEqual("unresolved_doll_safe", result["maturity"]["lane"])

    def test_all_generated_expert_profiles_use_owner_confirmed_adult_lane(self) -> None:
        directive_path = (
            PROJECT_ROOT
            / "Avatar"
            / "avatar_builder"
            / "policies"
            / "evidence"
            / "generated_experts_adult_owner_directive_20260716.json"
        )
        directive = json.loads(directive_path.read_text(encoding="utf-8"))
        expected_ids = {
            "emily_carter_ai_and_computer_programming_expert_20260605_220651",
            "jessica_hale_robotics_engineer_20260611_041314",
            "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530",
            "ryan_hale_quantum_mechanics_expert_20260608_200749",
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
        }
        self.assertEqual(expected_ids, set(directive["candidate_ids"]))
        self.assertFalse(directive["creates_body"])
        self.assertFalse(directive["creates_mind"])
        self.assertFalse(directive["runtime_activation_allowed"])

        for candidate_id in sorted(expected_ids):
            with self.subTest(candidate_id=candidate_id):
                result = evaluate_avatar_profile_preflight(PROJECT_ROOT, candidate_id)
                profile = json.loads(
                    (PROJECT_ROOT / result["canonical_profile"]["path"]).read_text(
                        encoding="utf-8"
                    )
                )
                selection = profile["avatar_identity_selection"]
                self.assertEqual("expert_temp_ai", profile["ai_type"])
                self.assertTrue(result["passed"], result["failures"])
                self.assertEqual("adult", result["maturity"]["lane"])
                self.assertEqual(
                    "confirmed_adult_topology",
                    result["maturity"]["safety_topology_lane"],
                )
                self.assertEqual(sha256(directive_path), selection["owner_directive_sha256"])
                self.assertFalse(selection["body_authored"])
                self.assertFalse(selection["runtime_activation_allowed"])
                self.assertFalse(result["runtime_activation_allowed"])

    def test_existing_gwen_current_build_is_explicit_adult_without_separate_variant(self) -> None:
        request = json.loads(
            (REQUEST_ROOT / "spider_gwen_spider_gwen_20260606_013325.json").read_text()
        )
        preflight = evaluate_orchestration_identity_preflight(PROJECT_ROOT, request)
        plan = plan_orchestration_request(request, identity_preflight=preflight)
        self.assertTrue(preflight["passed"], preflight["failures"])
        self.assertEqual(
            "earth_65_main_ghost_spider_young_adult_18_20_current_build_v1",
            preflight["identity"]["selected_version"],
        )
        self.assertEqual("adult", preflight["maturity"]["lane"])
        self.assertFalse(preflight["adult_variant_policy"]["separate_variant_required"])
        self.assertEqual(
            "blocked_multiview_evidence_manifest_missing",
            plan["production_state"],
        )
        self.assertEqual(
            "create_exact_hash_multiview_manifest_then_review_inputs", plan["next_action"]
        )
        self.assertFalse(plan["activation_allowed"])

    def test_kara_maws_current_build_uses_owner_confirmed_adult_lane(self) -> None:
        candidate_id = (
            "kara_zor_el_my_adventures_with_superman_"
            "kara_zor_el_20260606_181026"
        )
        result = evaluate_avatar_profile_preflight(PROJECT_ROOT, candidate_id)
        profile = json.loads(
            (PROJECT_ROOT / result["canonical_profile"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        selection = profile["identity_selection"]
        evidence_path = PROJECT_ROOT / selection["evidence_path"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual("My Adventures With Superman", result["identity"]["selected_version"])
        self.assertEqual("adult", result["maturity"]["lane"])
        self.assertEqual(
            "confirmed_adult_topology",
            result["maturity"]["safety_topology_lane"],
        )
        self.assertFalse(result["adult_variant_policy"]["separate_variant_required"])
        self.assertEqual(sha256(evidence_path), selection["evidence_sha256"])
        self.assertFalse(evidence["numeric_age_claimed"])
        self.assertTrue(evidence["movement_notes"]["floating_and_flight_are_primary_character_motion"])
        self.assertFalse(evidence["movement_notes"]["movement_proven_by_this_record"])
        self.assertFalse(selection["body_authored"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_kathryn_adult_continuation_preserves_existing_chat_by_hash(self) -> None:
        candidate_id = "kathryn_merteuil_kathryn_merteuil_20260605_213017"
        chat_path = (
            PROJECT_ROOT
            / "Data"
            / "personhood_evaluations"
            / "temporary_ai_live_chats"
            / "temporary_ai_live_chat_kathryn_merteuil_kathryn_merteuil_20260605_213017_20260605_213041.json"
        )
        result = evaluate_avatar_profile_preflight(PROJECT_ROOT, candidate_id)
        profile = json.loads((PROJECT_ROOT / result["canonical_profile"]["path"]).read_text())
        evidence = json.loads(
            (
                PROJECT_ROOT
                / profile["continuity_selection"]["evidence_path"]
            ).read_text()
        )

        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(
            "kathryn_ci2_ci1999_pilot2016_adult_continuation_v1",
            result["identity"]["selected_version"],
        )
        self.assertEqual("adult", result["maturity"]["lane"])
        self.assertEqual(sha256(chat_path), profile["existing_branch_continuity"]["live_chat_sha256"])
        self.assertEqual(
            "Amy Adams", evidence["continuity_order"][0]["performer_for_kathryn"]
        )
        self.assertEqual(
            "Sarah Michelle Gellar",
            evidence["continuity_order"][2]["performer_for_kathryn"],
        )
        self.assertFalse(result["runtime_activation_allowed"])

    def test_ruby_conflict_is_reported_without_rewriting_profile(self) -> None:
        candidate_id = "ruby_supernatural_ruby_supernatural_20260605_223416"
        profile = (
            PROJECT_ROOT
            / "TemporaryAI"
            / "candidates"
            / candidate_id
            / "temporary_ai_profile.json"
        )
        before = sha256(profile)
        result = evaluate_avatar_profile_preflight(PROJECT_ROOT, candidate_id)
        self.assertTrue(any("gender_preference" in note for note in result["manual_review_notes"]))
        self.assertEqual(before, sha256(profile))

    def test_explicit_non_adult_fixture_can_use_doll_safe_authoring_lane(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_id = "fictional_young_person_v1"
            profile = {
                "candidate_id": candidate_id,
                "source_canon": {"selected_version": "canon_episode_1"},
                "avatar_plan": {"maturity_policy": "non_adult_doll_safe"},
            }
            creation = {"candidate_id": candidate_id}
            write_json(
                root / "TemporaryAI" / "candidates" / candidate_id / "temporary_ai_profile.json",
                profile,
            )
            write_json(
                root / "TemporaryAI" / "candidates" / candidate_id / "creation_request.json",
                creation,
            )
            registry = {
                "schema_version": 1,
                "candidates": [
                    {
                        "canonical_candidate_id": candidate_id,
                        "aliases": [],
                        "subject_id": "fictional_young_person",
                        "identity_class": "fictional_character",
                        "variant_kind": "canon_base",
                        "version_policy": {
                            "required": True,
                            "binding": {
                                "source": "temporary_ai_profile",
                                "path": ["source_canon", "selected_version"],
                                "expected": "canon_episode_1",
                            },
                        },
                        "maturity_policy": {
                            "lane": "non_adult_doll_safe",
                            "binding": {
                                "source": "temporary_ai_profile",
                                "path": ["avatar_plan", "maturity_policy"],
                                "accepted_values": ["non_adult_doll_safe"],
                            },
                        },
                        "adult_variant_policy": {
                            "separate_variant_required": True,
                            "adult_variant_candidate_id": "",
                        },
                        "manual_review_notes": [],
                    }
                ],
            }
            write_json(
                root
                / "Avatar"
                / "avatar_builder"
                / "policies"
                / "candidate_identity_variant_registry.json",
                registry,
            )
            result = evaluate_avatar_profile_preflight(
                root,
                candidate_id,
                requested_subject_id="fictional_young_person",
                requested_maturity_class="non_adult_doll_safe",
                request_complete_adult_anatomy=False,
            )
            self.assertTrue(result["passed"], result["failures"])
            self.assertTrue(result["authoring_allowed"])
            self.assertEqual("non_adult_doll_safe_topology", result["maturity"]["safety_topology_lane"])

    def test_alias_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            records = []
            for number in (1, 2):
                candidate_id = f"candidate_{number}"
                write_json(
                    root
                    / "TemporaryAI"
                    / "candidates"
                    / candidate_id
                    / "temporary_ai_profile.json",
                    {"candidate_id": candidate_id},
                )
                write_json(
                    root
                    / "TemporaryAI"
                    / "candidates"
                    / candidate_id
                    / "creation_request.json",
                    {"candidate_id": candidate_id},
                )
                records.append(
                    {
                        "canonical_candidate_id": candidate_id,
                        "aliases": ["same_alias"],
                        "subject_id": f"subject_{number}",
                        "identity_class": "real_owner_variant",
                        "variant_kind": "fixture",
                        "version_policy": {"required": False},
                        "maturity_policy": {"lane": "unresolved_doll_safe"},
                        "adult_variant_policy": {"separate_variant_required": False},
                        "manual_review_notes": [],
                    }
                )
            write_json(
                root
                / "Avatar"
                / "avatar_builder"
                / "policies"
                / "candidate_identity_variant_registry.json",
                {"schema_version": 1, "candidates": records},
            )
            with self.assertRaisesRegex(AvatarProfilePreflightError, "alias collision"):
                evaluate_avatar_profile_preflight(root, "candidate_1")

    def test_current_batch_covers_all_22_real_profiles(self) -> None:
        result = evaluate_current_avatar_profile_batch(PROJECT_ROOT)
        self.assertTrue(result["coverage_passed"], result)
        self.assertEqual(22, result["evaluated_profile_count"])
        self.assertEqual([], result["unexpected_profile_directories"])
        self.assertEqual([], result["missing_profile_directories"])
        self.assertEqual(
            ["emily_continuity_smoke", "ladybug_prompt_smoke"],
            result["excluded_empty_smoke_directories"],
        )
        ids = {item["canonical_candidate_id"] for item in result["profiles"]}
        self.assertIn("sarah_bennett_entertainment_pr_agent_expert_20260606_171637", ids)
        skynet = next(item for item in result["profiles"] if item["canonical_candidate_id"].startswith("skynet_"))
        self.assertEqual("confirmed_adult_topology", skynet["topology_lane"])
        self.assertTrue(skynet["authoring_allowed"])

    def test_skynet_genisys_nonhuman_uses_selected_adult_presenting_embodiment(self) -> None:
        candidate_id = "skynet_skynet_20260605_224820"
        result = evaluate_avatar_profile_preflight(PROJECT_ROOT, candidate_id)
        profile = json.loads(
            (PROJECT_ROOT / result["canonical_profile"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        selection = profile["identity_selection"]
        evidence_path = PROJECT_ROOT / selection["evidence_path"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(
            "Terminator Genisys Alex / Skynet physical embodiment",
            result["identity"]["selected_version"],
        )
        self.assertEqual("fictional_nonhuman", result["identity"]["identity_class"])
        self.assertEqual("adult", result["maturity"]["lane"])
        self.assertEqual(
            "confirmed_adult_topology",
            result["maturity"]["safety_topology_lane"],
        )
        self.assertEqual("Matt Smith", evidence["performer"])
        self.assertFalse(selection["mind_is_human"])
        self.assertFalse(evidence["body_is_biological_human_claimed"])
        self.assertEqual(sha256(evidence_path), selection["evidence_sha256"])
        self.assertFalse(selection["body_authored"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_gwen_adult_avatar_only_variant_passes_without_creating_a_mind(self) -> None:
        candidate_id = "spider_gwen_adult_avatar_project_variant_20260716"
        result = evaluate_avatar_profile_preflight(
            PROJECT_ROOT,
            candidate_id,
            requested_subject_id="gwen_stacy_adult_project_variant",
            requested_maturity_class="adult",
            request_complete_adult_anatomy=True,
        )
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual("avatar_only_variant", result["canonical_profile"]["profile_kind"])
        self.assertEqual("confirmed_adult_topology", result["maturity"]["safety_topology_lane"])
        self.assertTrue(result["source_bindings"])
        profile = json.loads((PROJECT_ROOT / result["canonical_profile"]["path"]).read_text())
        self.assertFalse(profile["creates_temporary_ai_or_mind"])
        self.assertFalse(profile["runtime_activation_allowed"])

    def test_batch_bound_is_enforced(self) -> None:
        with self.assertRaisesRegex(AvatarProfilePreflightError, "exceeds bound"):
            evaluate_current_avatar_profile_batch(PROJECT_ROOT, max_candidates=21)

    def test_kira_adult_avatar_only_build_target_passes_without_runtime_replacement(self) -> None:
        result = evaluate_avatar_profile_preflight(
            PROJECT_ROOT,
            "kira_adult_avatar_build_variant_20260716",
            requested_subject_id="kira_adult_avatar_build",
            requested_maturity_class="adult",
            request_complete_adult_anatomy=True,
        )
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual("confirmed_adult_topology", result["maturity"]["safety_topology_lane"])
        profile = json.loads((PROJECT_ROOT / result["canonical_profile"]["path"]).read_text())
        self.assertFalse(profile["creates_temporary_ai_or_mind"])
        self.assertFalse(profile["replaces_current_runtime_body"])
        self.assertFalse(profile["runtime_activation_allowed"])

    def test_marinette_main_series_avatar_only_target_passes_doll_safe_lane(self) -> None:
        result = evaluate_avatar_profile_preflight(
            PROJECT_ROOT,
            "marinette_main_series_doll_safe_avatar_variant_20260716",
            requested_subject_id="marinette_main_series_avatar_build",
            requested_maturity_class="non_adult_doll_safe",
            request_complete_adult_anatomy=False,
        )
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual("non_adult_doll_safe_topology", result["maturity"]["safety_topology_lane"])
        profile = json.loads((PROJECT_ROOT / result["canonical_profile"]["path"]).read_text())
        self.assertFalse(profile["creates_temporary_ai_or_mind"])
        self.assertFalse(profile["replaces_current_runtime_body"])
        self.assertFalse(profile["maturity"]["adult_anatomy_allowed"])


if __name__ == "__main__":
    unittest.main()
