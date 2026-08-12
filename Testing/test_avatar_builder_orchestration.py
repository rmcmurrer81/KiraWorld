from __future__ import annotations

import copy
import unittest

from Core.avatar_builder_orchestration import (
    ADULT_TOPOLOGY_TESTS,
    CONFIRMED_ADULT_TOPOLOGY,
    FACE_LIP_SYNC_TESTS,
    LICENSED_SHAPE_PRESERVING_DERIVATIVE,
    LOCOMOTION_CONTACT_TESTS,
    NON_ADULT_DOLL_SAFE_TOPOLOGY,
    NON_ADULT_TOPOLOGY_TESTS,
    PHOTO_ONLY_RECONSTRUCTION,
    PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
    STABLE_RIG_TESTS,
    evaluate_avatar_builder_orchestration,
)
from Testing.test_garment_capability import (
    BODY_HASH,
    GARMENT_HASH,
    RIG_HASH,
    passing_manifest,
)


HAIR_HASH = "d" * 64
EYES_HASH = "e" * 64
ASSEMBLY_HASH = "f" * 64
EVIDENCE_HASH = "1" * 64
SOURCE_HASH = "2" * 64
LICENSE_HASH = "3" * 64
ROLE_MAP_HASH = "4" * 64
OWNER_AUTHORITY_HASH = "5" * 64
OWNER_APPROVAL_HASH = "6" * 64


def reviewed_gate(body_hash: str, tests: tuple[str, ...], **extra: object) -> dict:
    value = {
        "artifact_sha256": body_hash,
        "exact_artifact_hash_verified": True,
        "review_status": "passed",
        "reviewed_by": "unit_test_reviewer",
        "reviewed_at": "2026-07-16T01:00:00-04:00",
        "test_results": {name: "passed" for name in tests},
    }
    value.update(extra)
    return value


def photo_contract(candidate_id: str, treatment: str = "neutral_adult_anatomy") -> dict:
    return {
        "candidate_id": candidate_id,
        "identity_reconstruction_mode": "picture_first_models_optional",
        "staging_allowed": True,
        "runtime_activation_allowed": False,
        "picture_evidence": {"minimum_multiview_identity_set_present": True},
        "optional_model_evidence": {
            "total_count": 0,
            "optional_measurement_reference_count": 0,
        },
        "maturity_base_contract": {"base_treatment": treatment},
    }


def components() -> dict:
    return {
        "body": {
            "artifact_role": "body",
            "artifact_sha256": BODY_HASH,
            "exact_artifact_hash_verified": True,
            "separate_artifact": True,
            "contains_hair": False,
            "contains_eyes": False,
            "contains_clothes": False,
        },
        "hair": {
            "artifact_role": "hair",
            "artifact_sha256": HAIR_HASH,
            "exact_artifact_hash_verified": True,
            "separate_artifact": True,
        },
        "eyes": {
            "artifact_role": "eyes",
            "artifact_sha256": EYES_HASH,
            "exact_artifact_hash_verified": True,
            "separate_artifact": True,
        },
        "clothes": {
            "artifact_role": "clothes",
            "artifact_sha256": GARMENT_HASH,
            "exact_artifact_hash_verified": True,
            "separate_artifact": True,
        },
    }


def request(
    candidate_id: str,
    subject_id: str,
    *,
    source_mode: str = PHOTO_ONLY_RECONSTRUCTION,
    maturity_class: str = "adult",
) -> dict:
    adult = maturity_class == "adult"
    topology_tests = ADULT_TOPOLOGY_TESTS if adult else NON_ADULT_TOPOLOGY_TESTS
    topology_extra = {
        "body_treatment": "neutral_adult_anatomy" if adult else "non_adult_doll_safe",
        "adult_anatomy_present": True if adult else False,
    }
    source_strategy = {
        "mode": source_mode,
        "licensed_derivative": {"selected": False},
        "photo_only": {
            "selected": True,
            "licensed_source_surface_incorporated": False,
            "reconstruction_contract": photo_contract(
                candidate_id,
                "neutral_adult_anatomy" if adult else "non_adult_doll_safe",
            ),
        },
    }
    if source_mode == LICENSED_SHAPE_PRESERVING_DERIVATIVE:
        source_strategy = {
            "mode": source_mode,
            "photo_only": {"selected": False},
            "licensed_derivative": {
                "selected": True,
                "candidate_id": candidate_id,
                "subject_id": subject_id,
                "source_sha256": SOURCE_HASH,
                "exact_source_hash_verified": True,
                "license_evidence_sha256": LICENSE_HASH,
                "license_evidence_hash_verified": True,
                "adaptation_allowed": True,
                "attribution_bound": True,
                "source_role_map_sha256": ROLE_MAP_HASH,
                "source_role_map_hash_verified": True,
                "licensed_source_surface_incorporated": True,
                "source_surface_shape_preserved": True,
                "new_body_surface_authored": False,
                "source_artifact_byte_copied": False,
                "source_materials_and_textures_exported": False,
                "candidate_output_allowlist_enforced": True,
                "candidate_body_sha256": BODY_HASH,
                "adult_only_source": adult,
            },
        }
    data = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "owner_identity": {
            "owner_id": subject_id,
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "authority_status": "verified_subject_self_owner",
            "authority_artifact_sha256": OWNER_AUTHORITY_HASH,
            "exact_authority_artifact_hash_verified": True,
        },
        "request_complete_adult_anatomy": adult,
        "render_requested": False,
        "runtime_activation_requested": False,
        "maturity_policy": {
            "maturity_class": maturity_class,
            "evidence": {
                "candidate_id": candidate_id,
                "subject_id": subject_id,
                "maturity_class": maturity_class,
                "evidence_sha256": EVIDENCE_HASH,
                "exact_evidence_hash_verified": True,
                "exact_subject_bound": True,
                "review_status": "passed",
            },
        },
        "source_strategy": source_strategy,
        "components": components(),
        "rig_binding": {
            "rig_sha256": RIG_HASH,
            "exact_rig_hash_verified": True,
        },
        "readiness_evidence": {
            "topology": reviewed_gate(BODY_HASH, topology_tests, **topology_extra),
            "stable_rig": reviewed_gate(
                BODY_HASH,
                STABLE_RIG_TESTS,
                heuristic_only=False,
                visual_deformation_reviewed=True,
            ),
            "face_lip_sync": reviewed_gate(BODY_HASH, FACE_LIP_SYNC_TESTS),
            "locomotion_contact": reviewed_gate(BODY_HASH, LOCOMOTION_CONTACT_TESTS),
            "wearable_capability": passing_manifest(),
            "owner_clothed_review": {
                "approval_status": "approved_clothed_review",
                "candidate_id": candidate_id,
                "subject_id": subject_id,
                "owner_id": subject_id,
                "owner_authority_artifact_sha256": OWNER_AUTHORITY_HASH,
                "body_sha256": BODY_HASH,
                "clothes_sha256": GARMENT_HASH,
                "clothed_assembly_sha256": ASSEMBLY_HASH,
                "approval_artifact_sha256": OWNER_APPROVAL_HASH,
                "exact_approval_artifact_hash_verified": True,
                "approved_by": subject_id,
                "approved_at": "2026-07-16T01:05:00-04:00",
                "clothed_only": True,
                "private_body_displayed": False,
            },
        },
        "privacy": {
            "normal_review_route": "clothed_only",
            "intimate_render_retained": False,
            "private_source_paths_in_report": False,
            "public_export_allowed": False,
        },
    }
    if candidate_id != "adult_test_candidate" or subject_id != "adult_test_subject":
        wearable = data["readiness_evidence"]["wearable_capability"]
        wearable["candidate_id"] = candidate_id
        wearable["subject_id"] = subject_id
        for phase_id, record in wearable["phase_evidence"].items():
            payload = record["evidence_payload"]
            payload["candidate_id"] = candidate_id
            payload["subject_id"] = subject_id
            from Core.garment_capability import canonical_sha256

            record["evidence_sha256"] = canonical_sha256(payload)
    return data


class AvatarBuilderOrchestrationTests(unittest.TestCase):
    def test_unrelated_approver_cannot_satisfy_owner_review(self) -> None:
        data = request("adult_test_candidate", "adult_test_subject")
        data["readiness_evidence"]["owner_clothed_review"]["approved_by"] = (
            "unrelated_non_owner"
        )

        result = evaluate_avatar_builder_orchestration(data)

        owner_gate = result["capability_gates"]["owner_clothed_review"]
        self.assertFalse(owner_gate["passed"])
        self.assertIn("owner_review_approver_is_not_bound_owner", owner_gate["failures"])
        self.assertFalse(result["review_stage_allowed"])

    def test_owner_review_requires_matching_hashed_authority_artifact(self) -> None:
        data = request("adult_test_candidate", "adult_test_subject")
        data["readiness_evidence"]["owner_clothed_review"][
            "owner_authority_artifact_sha256"
        ] = "7" * 64

        result = evaluate_avatar_builder_orchestration(data)

        owner_gate = result["capability_gates"]["owner_clothed_review"]
        self.assertFalse(owner_gate["passed"])
        self.assertIn("owner_review_authority_artifact_mismatch", owner_gate["failures"])
        self.assertFalse(result["review_stage_allowed"])

    def test_beth_routes_to_confirmed_adult_licensed_derivative(self) -> None:
        data = request(
            "beth_smith_ordinary_temp_20260716",
            "beth_smith",
            source_mode=LICENSED_SHAPE_PRESERVING_DERIVATIVE,
        )
        del data["readiness_evidence"]["face_lip_sync"]
        result = evaluate_avatar_builder_orchestration(data)
        self.assertEqual(result["route"]["topology_lane"], CONFIRMED_ADULT_TOPOLOGY)
        self.assertEqual(
            result["route"]["reconstruction_source_lane"],
            LICENSED_SHAPE_PRESERVING_DERIVATIVE,
        )
        self.assertEqual(result["route"]["status"], "selected_and_valid")
        self.assertFalse(result["review_stage_allowed"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_gwen_routes_to_adult_photo_only_without_model_copy(self) -> None:
        data = request(
            "spider_gwen_spider_gwen_20260606_013325",
            "gwen_stacy_earth_65",
        )
        result = evaluate_avatar_builder_orchestration(data)
        self.assertEqual(result["route"]["topology_lane"], CONFIRMED_ADULT_TOPOLOGY)
        self.assertEqual(result["route"]["reconstruction_source_lane"], PHOTO_ONLY_RECONSTRUCTION)
        self.assertTrue(result["route"]["lane_decisions"][PHOTO_ONLY_RECONSTRUCTION])

    def test_robert_routes_to_accuracy_first_adult_photo_only(self) -> None:
        data = request("robert_user_avatar_20260716", "robert_mcmurrer")
        result = evaluate_avatar_builder_orchestration(data)
        self.assertEqual(
            result["route"]["ordered_lanes"],
            [PHOTO_ONLY_RECONSTRUCTION, CONFIRMED_ADULT_TOPOLOGY],
        )
        self.assertFalse(result["runtime_activation_allowed"])

    def test_picture_primary_route_accepts_model_only_as_hashed_measurement_guidance(self) -> None:
        data = request("model_bonus_candidate", "model_bonus_subject")
        contract = photo_contract("model_bonus_candidate")
        contract["picture_evidence"]["accepted_pictures_are_identity_authority"] = True
        contract["optional_model_evidence"] = {
            "total_count": 1,
            "optional_measurement_reference_count": 1,
            "models_are_identity_authority": False,
            "surface_copy_allowed": False,
        }
        data["source_strategy"] = {
            "mode": PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
            "licensed_derivative": {"selected": False},
            "photo_only": {"selected": False},
            "photo_primary_with_reference_model_measurement": {
                "selected": True,
                "pictures_are_identity_authority": True,
                "reference_model_is_identity_authority": False,
                "licensed_source_surface_incorporated": False,
                "reference_model_surface_copied": False,
                "reference_model_materials_or_textures_copied": False,
                "new_candidate_surface_authored": True,
                "candidate_body_sha256": BODY_HASH,
                "reference_model": {
                    "artifact_sha256": "7" * 64,
                    "exact_artifact_hash_verified": True,
                    "role": "measurement_and_topology_guidance_only",
                    "usage_evidence_sha256": "8" * 64,
                    "usage_evidence_hash_verified": True,
                    "measurement_guidance_use_allowed": True,
                    "surface_copy_allowed": False,
                    "adult_only_source": True,
                },
                "reconstruction_contract": contract,
            },
        }

        result = evaluate_avatar_builder_orchestration(data)

        self.assertEqual("selected_and_valid", result["route"]["status"])
        self.assertEqual(
            PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
            result["route"]["reconstruction_source_lane"],
        )
        self.assertTrue(
            result["route"]["lane_decisions"][
                PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT
            ]
        )

    def test_picture_primary_model_route_rejects_surface_copy_and_model_identity(self) -> None:
        data = request("model_bonus_candidate", "model_bonus_subject")
        contract = photo_contract("model_bonus_candidate")
        contract["picture_evidence"]["accepted_pictures_are_identity_authority"] = True
        contract["optional_model_evidence"] = {
            "total_count": 1,
            "optional_measurement_reference_count": 1,
            "models_are_identity_authority": False,
            "surface_copy_allowed": False,
        }
        lane = {
            "selected": True,
            "pictures_are_identity_authority": True,
            "reference_model_is_identity_authority": True,
            "licensed_source_surface_incorporated": False,
            "reference_model_surface_copied": True,
            "reference_model_materials_or_textures_copied": False,
            "new_candidate_surface_authored": True,
            "candidate_body_sha256": BODY_HASH,
            "reference_model": {
                "artifact_sha256": "7" * 64,
                "exact_artifact_hash_verified": True,
                "role": "measurement_and_topology_guidance_only",
                "usage_evidence_sha256": "8" * 64,
                "usage_evidence_hash_verified": True,
                "measurement_guidance_use_allowed": True,
                "surface_copy_allowed": False,
                "adult_only_source": True,
            },
            "reconstruction_contract": contract,
        }
        data["source_strategy"] = {
            "mode": PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
            "licensed_derivative": {"selected": False},
            "photo_only": {"selected": False},
            "photo_primary_with_reference_model_measurement": lane,
        }

        result = evaluate_avatar_builder_orchestration(data)

        self.assertIn(
            "reference_model_must_not_be_identity_authority", result["route"]["failures"]
        )
        self.assertIn(
            "reference_model_surface_copy_forbidden", result["route"]["failures"]
        )
        self.assertFalse(result["review_stage_allowed"])

    def test_non_adult_route_rejects_adult_only_licensed_source(self) -> None:
        data = request(
            "normal_non_adult_candidate",
            "normal_non_adult_subject",
            source_mode=LICENSED_SHAPE_PRESERVING_DERIVATIVE,
            maturity_class="non_adult_doll_safe",
        )
        data["source_strategy"]["licensed_derivative"]["adult_only_source"] = True
        result = evaluate_avatar_builder_orchestration(data)
        self.assertEqual(result["route"]["topology_lane"], NON_ADULT_DOLL_SAFE_TOPOLOGY)
        self.assertIn(
            "adult_only_or_unscoped_licensed_source_forbidden_in_non_adult_lane",
            result["route"]["failures"],
        )

    def test_multiple_source_lanes_fail_closed(self) -> None:
        data = request("adult_test_candidate", "adult_test_subject")
        data["source_strategy"]["licensed_derivative"] = {"selected": True}
        result = evaluate_avatar_builder_orchestration(data)
        self.assertIn("multiple_reconstruction_source_lanes_selected", result["route"]["failures"])
        self.assertFalse(result["review_stage_allowed"])

    def test_component_hash_reuse_and_embedded_clothes_are_blocked(self) -> None:
        data = request("adult_test_candidate", "adult_test_subject")
        data["components"]["hair"]["artifact_sha256"] = BODY_HASH
        data["components"]["body"]["contains_clothes"] = True
        result = evaluate_avatar_builder_orchestration(data)
        failures = result["capability_gates"]["component_integrity"]["failures"]
        self.assertIn("component_artifact_hashes_must_be_distinct", failures)
        self.assertIn("body_artifact_contains_or_does_not_exclude_clothes", failures)

    def test_missing_lip_sync_and_visual_rig_evidence_are_honest_blockers(self) -> None:
        data = request("adult_test_candidate", "adult_test_subject")
        data["readiness_evidence"]["face_lip_sync"]["test_results"].pop("audio_lip_sync")
        data["readiness_evidence"]["stable_rig"]["heuristic_only"] = True
        result = evaluate_avatar_builder_orchestration(data)
        self.assertIn("face_lip_sync_test_not_passed_audio_lip_sync", result["blocking_reasons"])
        self.assertIn("stable_rig_remains_heuristic_only", result["blocking_reasons"])
        self.assertFalse(result["review_stage_allowed"])

    def test_every_capability_can_pass_review_but_never_grants_runtime(self) -> None:
        data = request("adult_test_candidate", "adult_test_subject")
        result = evaluate_avatar_builder_orchestration(data)
        self.assertEqual(result["status"], "ready_for_private_clothed_review_only")
        self.assertTrue(result["body_private_review_ready"])
        self.assertTrue(result["advanced_garment_capability_ready"])
        self.assertTrue(result["review_stage_allowed"], result["blocking_reasons"])
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertTrue(result["separate_runtime_authority_required"])

    def test_missing_robe_capability_does_not_block_basic_clothed_body_review(self) -> None:
        data = request("adult_test_candidate", "adult_test_subject")
        data["readiness_evidence"]["wearable_capability"] = {}

        result = evaluate_avatar_builder_orchestration(data)

        self.assertTrue(result["body_private_review_ready"], result["body_blocking_reasons"])
        self.assertTrue(result["review_stage_allowed"])
        self.assertFalse(result["advanced_garment_capability_ready"])
        self.assertIn(
            "wearable_capability_manifest_missing", result["garment_blocking_reasons"]
        )
        self.assertNotIn(
            "wearable_capability_manifest_missing", result["body_blocking_reasons"]
        )
        self.assertEqual(
            "ready_for_private_clothed_review_garment_capability_pending",
            result["status"],
        )
        self.assertFalse(result["runtime_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
