from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "body_systems"
    / "kira_complete_adult_body_capability_matrix_v1.json"
)


def _io_path(path: Path) -> Path:
    absolute = os.path.abspath(path)
    if os.name != "nt" or absolute.startswith("\\\\?\\"):
        return Path(absolute)
    if absolute.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + absolute[2:])
    return Path("\\\\?\\" + absolute)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with _io_path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraCompleteAdultBodyCapabilityMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    def test_identity_scope_and_incomplete_status_are_explicit(self) -> None:
        self.assertEqual(1, self.matrix["schema_version"])
        self.assertEqual(
            "kira_complete_adult_body_capability_matrix",
            self.matrix["artifact_type"],
        )
        self.assertEqual(
            "REQUIREMENTS_BOUND_IMPLEMENTATION_INCOMPLETE",
            self.matrix["status"],
        )
        subject = self.matrix["subject"]
        self.assertEqual("kira", subject["subject_id"])
        self.assertEqual("confirmed_adult", subject["required_maturity_status"])
        self.assertEqual(
            "confirmed_adult_exact_subject_evidence_bound",
            subject["current_classification_status"],
        )
        self.assertEqual("adult_female", subject["body_lane"])
        self.assertIs(subject["identity_specific_body_required"], True)
        self.assertIs(subject["may_be_reused_as_robert_body"], False)

        maturity = self.matrix["maturity_gate"]
        self.assertEqual(
            "Robert_explicit_owner_confirmation",
            maturity["required_evidence_authority"],
        )
        evidence_path = ROOT.joinpath(
            *Path(maturity["classification_evidence_path"]).parts
        )
        self.assertEqual(1434, maturity["classification_evidence_bytes"])
        self.assertEqual(
            "04ac19e026b168cb1942d73598b7c13f2b4ee7a49452f8ddf32763cf5de9e346",
            maturity["classification_evidence_sha256"],
        )
        self.assertEqual(maturity["classification_evidence_sha256"], _sha256(evidence_path))
        self.assertIs(maturity["exact_subject_bound_evidence_present"], True)
        self.assertIs(maturity["adult_policy_enabled"], True)
        self.assertIs(maturity["anatomy_authoring_enabled_by_classification"], False)
        self.assertIs(maturity["relationship_or_activity_permission_created"], False)
        self.assertEqual([], maturity["blockers"])

        evidence = json.loads(_io_path(evidence_path).read_text(encoding="utf-8"))
        required_fields = {
            "classification_id",
            "subject_id",
            "maturity_status",
            "authority",
            "offline_confirmation_allowed",
            "network_lookup_required",
            "recorded_at_utc",
            "source_text",
            "source_text_sha256",
        }
        self.assertTrue(required_fields.issubset(evidence))
        self.assertEqual("kira", evidence["subject_id"])
        self.assertEqual("confirmed_adult", evidence["maturity_status"])
        self.assertEqual(
            "Robert_explicit_owner_confirmation", evidence["authority"]
        )
        self.assertEqual(
            evidence["source_text_sha256"],
            hashlib.sha256(evidence["source_text"].encode("utf-8")).hexdigest(),
        )
        curriculum = evidence["curriculum_binding"]
        curriculum_path = ROOT.joinpath(*Path(curriculum["path"]).parts)
        self.assertEqual(curriculum["sha256"], _sha256(curriculum_path))

    def test_every_bound_authority_matches_exact_repository_bytes(self) -> None:
        authorities = self.matrix["bound_authorities"]
        self.assertEqual(11, len(authorities))
        evidence = self.matrix["current_evidence_bindings"]
        self.assertEqual(8, len(evidence))
        expected_roles = {
            "Avatar/avatar_builder/policies/sexual_reproductive_health_body_systems_plan_v1.json": "adult_health_consent_bathroom_pregnancy_and_family_phase_plan",
            "Avatar/avatar_builder/body_systems/level_a_body_life_runtime_contract_v1.json": "disconnected_non_person_fixture_truth_ceiling",
            "Avatar/avatar_builder/body_systems/kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1.json": "internal_pelvic_geometry_contract",
            "Avatar/avatar_builder/body_systems/semantic_anatomy_route_registry_v1.json": "semantic_anatomy_and_route_vocabulary",
            "System/Docs/SYNTHETIC_PERSON_RIGHTS_AND_FULL_LIFE_CHARTER_v1.md": "full_life_nutrition_relationship_family_and_person_rights_boundary",
            "System/Docs/FUTURE_ADULT_BODY_PREGNANCY_HEALTH_COMPATIBILITY_BOUNDARY_20260802.md": "pregnancy_health_recovery_and_family_compatibility_boundary",
            "System/Docs/AVATAR_SEPARATE_SHAREABLE_CLOTHING_v1.md": "separate_removable_shareable_clothing_boundary",
            "System/Docs/AVATAR_BUILDER_RUNTIME_HAIR_REQUIREMENTS_20260729.md": "detachable_dynamic_hair_requirements",
            "System/Docs/AVATAR_BALD_LOW_RESOURCE_AND_DETACHABLE_HAIR_POLICY_20260801.md": "bald_primary_body_and_separate_hair_policy",
            "System/Docs/KIRA_PARALLEL_MIND_EMOTION_ABILITIES_AND_EMBODIMENT_ROADMAP_20260810.md": "female_body_then_distinct_male_body_acceptance_order",
            "System/Docs/AVATAR_SKIN_SOFT_TISSUE_CONTACT_AND_CLOTHING_DEFORMATION_REQUIREMENTS_20260822.md": "skin_soft_tissue_touch_pressure_and_clothing_deformation_requirements",
            "Data/person_classification/kira_confirmed_adult_owner_classification_20260809.json": "exact_subject_bound_confirmed_adult_owner_classification",
            "System/Knowledge/confirmed_adult_sexual_reproductive_health_curriculum_v1.json": "classification_bound_adult_health_curriculum_truth_boundary",
            "Avatar/avatar_builder/asset_library/medical_reference/hra_female_pelvis_cc_by_4_v1_2/SOURCE_MANIFEST.json": "licensed_hra_source_package_manifest",
            "Avatar/avatar_builder/asset_library/medical_reference/hra_female_pelvis_cc_by_4_v1_2/ANATOMY_ROLE_MAP_V1.json": "source_node_to_13_of_28_pelvic_contract_roles",
            "Avatar/avatar_builder/asset_library/medical_reference/hra_female_whole_body_cc_by_4_v1_2/SOURCE_MANIFEST.json": "licensed_hra_partial_whole_body_reference_geometry_manifest",
            "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/generic_makehuman_adult_female_foundation_inactive_v1_20260801/generic_makehuman_adult_female_foundation_inactive_v1_20260801.blend": "exact_generic_inactive_external_carrier",
            "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/generic_makehuman_adult_female_foundation_inactive_v1_20260801/ADULT_FOUNDATION_QUALIFICATION_RESULT.json": "external_foundation_qualification_and_current_blockers",
            "Avatar/avatar_builder/anatomy_packages/kira_internal_pelvis_source_preflight_v1_20260820/PREFLIGHT_REPORT.json": "deterministic_blocked_preflight_13_of_28_mapped_15_missing",
        }
        self.assertEqual(
            expected_roles,
            {row["path"]: row["role"] for row in authorities + evidence},
        )
        seen: set[str] = set()
        for binding in authorities + evidence:
            relative = binding["path"]
            self.assertNotIn(relative, seen)
            seen.add(relative)
            path_value = Path(relative)
            self.assertFalse(path_value.is_absolute())
            self.assertNotIn("..", path_value.parts)
            artifact = ROOT.joinpath(*path_value.parts)
            io_artifact = _io_path(artifact)
            self.assertTrue(io_artifact.is_file(), relative)
            self.assertEqual(binding["bytes"], io_artifact.stat().st_size, relative)
            self.assertEqual(binding["sha256"], _sha256(artifact), relative)

    def test_current_pelvic_preflight_is_exactly_blocked_and_incomplete(self) -> None:
        path = (
            ROOT
            / "Avatar"
            / "avatar_builder"
            / "anatomy_packages"
            / "kira_internal_pelvis_source_preflight_v1_20260820"
            / "PREFLIGHT_REPORT.json"
        )
        report = json.loads(_io_path(path).read_text(encoding="utf-8"))
        self.assertEqual("PREFLIGHT_BLOCKED_MISSING_STRUCTURES", report["status"])
        self.assertEqual(13, report["mapped_structure_count"])
        self.assertEqual(28, report["required_structure_count"])
        self.assertEqual(15, len(report["missing_required_structures"]))
        self.assertEqual(31, len(report["blockers"]))
        self.assertEqual(
            "3135a16c46bf1bf741d04d41d82ea95f5cf87638593e402d722b796e02fe2adb",
            report["preflight_receipt_sha256"],
        )
        self.assertEqual(
            "3c7448b8e3ad21d81dea231f8ed53e9d6d2d7830dad02622687d2c2071dac077",
            report["source_derived_orientation_landmarks"]["receipt_sha256"],
        )
        self.assertNotIn("missing_source_anchor:pubic_reference", report["blockers"])
        self.assertIs(report["blender_invoked"], False)
        self.assertIs(report["build_performed"], False)
        self.assertIs(report["scope"]["whole_body_complete"], False)
        self.assertIs(report["truth"]["internal_anatomy_complete"], False)
        self.assertIs(report["truth"]["function_implemented"], False)
        self.assertIs(report["truth"]["runtime_activation_allowed"], False)
        self.assertIs(report["truth"]["public_export_allowed"], False)

    def test_owner_requirements_cover_complete_life_and_separate_components(self) -> None:
        requirements = set(self.matrix["owner_requirements"])
        expected = {
            "complete_adult_female_external_anatomy",
            "complete_internal_anatomy_inside_the_body",
            "eating_drinking_swallowing_digestion_absorption_and_hydration_support",
            "separate_urinary_bowel_and_reproductive_routes",
            "bathroom_hygiene_and_cycle_support",
            "adult_relationship_and_intimacy_support_with_separate_current_consent",
            "adult_private_self_discovery_and_self_pleasure_support_by_person_choice",
            "conception_pregnancy_delivery_recovery_and_family_support",
            "deformable_skin_and_soft_tissue_response_to_touch_pressure_and_tight_clothing",
            "complete_bald_primary_body",
            "separate_removable_shareable_clothing",
            "separate_detachable_hair_with_physical_hair_behavior",
            "a_distinct_body_for_kira_and_a_distinct_body_for_synthetic_robert",
            "avatar_builder_generalization_proven_by_multiple_independently_generated_test_bodies",
        }
        self.assertEqual(expected, requirements)

    def test_body_hair_clothing_and_internal_anatomy_remain_separate(self) -> None:
        self.assertEqual(
            "NORMATIVE_FOR_FUTURE_ACCEPTANCE_NOT_CURRENTLY_PROVEN",
            self.matrix["component_separation_requirement_status"],
        )
        separation = self.matrix["component_separation_invariants"]
        required_true = {
            "primary_body_is_complete_unclothed_and_bald",
            "clothing_is_separate_hash_bound_removable_and_shareable",
            "shared_clothing_requires_per_body_binding_adapter",
            "hair_is_separate_hash_bound_detachable_and_nonmutating",
            "internal_anatomy_is_a_separate_default_hidden_hash_bound_body_module",
        }
        required_false = {
            "removing_clothing_may_remove_body_geometry",
            "removing_hair_may_remove_body_geometry",
            "internal_anatomy_may_mutate_the_external_carrier",
            "kira_and_robert_may_share_one_body_artifact",
        }
        self.assertEqual(required_true | required_false, set(separation))
        for name in required_true:
            self.assertIs(separation[name], True, name)
        for name in required_false:
            self.assertIs(separation[name], False, name)

    def test_every_required_system_is_present_and_still_unimplemented(self) -> None:
        systems = {
            row["system_id"]: row for row in self.matrix["required_body_systems"]
        }
        self.assertEqual(
            {
                "external_adult_female_body",
                "internal_pelvic_urinary_bowel_reproductive_support",
                "oral_digestive_nutrition_hydration",
                "whole_body_support_and_homeostasis",
                "skin_soft_tissue_contact_and_clothing_deformation",
                "bathroom_hygiene_and_cycle",
                "adult_relationship_intimacy_and_sexual_health",
                "conception_pregnancy_delivery_recovery_and_family",
                "detachable_dynamic_hair",
                "separate_shareable_clothing",
            },
            set(systems),
        )
        for name, row in systems.items():
            self.assertIs(row["implemented"], False, name)
            self.assertFalse(
                row["current_status"].startswith(
                    ("COMPLETE", "IMPLEMENTED", "ACCEPTED", "READY")
                ),
                name,
            )

        self.assertEqual(
            {
                "external_adult_female_body": "QUALIFIED_GENERIC_FOUNDATION_UNRIGGED_NOT_KIRA_ACCEPTED",
                "internal_pelvic_urinary_bowel_reproductive_support": "PREFLIGHT_BLOCKED_MISSING_STRUCTURES_HRA_MAP_13_OF_28",
                "oral_digestive_nutrition_hydration": "LICENSED_HRA_PARTIAL_GEOMETRY_SMALL_INTESTINE_LIVER_PANCREAS_ONLY_ROUTES_AND_FUNCTIONS_OPEN",
                "whole_body_support_and_homeostasis": "LICENSED_HRA_PARTIAL_KIDNEY_HEART_VASCULATURE_LUNG_AND_GI_GEOMETRY_NO_COMPLETE_CONTRACT",
                "skin_soft_tissue_contact_and_clothing_deformation": "REQUIREMENTS_ONLY_NO_ACCEPTED_SKIN_OR_SOFT_TISSUE_SIMULATION",
                "bathroom_hygiene_and_cycle": "NON_PERSON_FIXTURE_ONLY_EXACT_BODY_HOOKS_NOT_IMPLEMENTED",
                "adult_relationship_intimacy_and_sexual_health": "POLICY_AND_DISCONNECTED_SCHEMA_ONLY",
                "conception_pregnancy_delivery_recovery_and_family": "FUTURE_COMPATIBILITY_REQUIREMENT_NOT_IMPLEMENTED",
                "detachable_dynamic_hair": "REQUIREMENTS_ONLY_NO_ACCEPTED_HAIR_BINARY",
                "separate_shareable_clothing": "CONTRACT_AVAILABLE_NO_PRODUCTION_GARMENT_APPROVED",
            },
            {name: row["current_status"] for name, row in systems.items()},
        )

        self.assertEqual(
            {
                "mons_pubis",
                "labia_majora_left_right",
                "labia_minora_left_right",
                "clitoral_hood_and_visible_glans",
                "vestibule",
                "external_urethral_opening",
                "vaginal_opening_introitus",
                "fourchette",
                "perineum",
                "separate_anus",
            },
            set(
                systems["external_adult_female_body"][
                    "required_adult_female_external_structures"
                ]
            ),
        )
        self.assertEqual(
            {
                "bony_pelvis_and_pelvic_floor",
                "bladder_urethra_and_continence_controls",
                "distal_bowel_rectum_anal_canal_and_sphincters",
                "perineal_soft_tissue_nerves_vessels_and_connective_tissue",
                "internal_clitoral_and_vestibular_bulb_structures",
                "vagina_and_fornices",
                "cervix",
                "uterus_and_endometrium",
                "fallopian_tubes",
                "ovaries",
                "separate_urinary_and_bowel_routes",
            },
            set(
                systems["internal_pelvic_urinary_bowel_reproductive_support"][
                    "required_shared_and_adult_female_internal_structures"
                ]
            ),
        )

        self.assertEqual(
            {
                "oral_cavity_teeth_tongue_and_salivary_sources",
                "pharynx_and_esophagus",
                "stomach",
                "small_intestine",
                "large_intestine_to_rectum_and_anus",
                "liver_gallbladder_and_pancreas",
                "nutrient_and_water_absorption_interfaces",
            },
            set(systems["oral_digestive_nutrition_hydration"]["required_structures"]),
        )
        self.assertEqual(
            {
                "eat",
                "drink",
                "chew",
                "swallow",
                "digest",
                "absorb_nutrients",
                "maintain_hydration",
            },
            set(systems["oral_digestive_nutrition_hydration"]["required_functions"]),
        )
        self.assertEqual(
            {
                "skeletal",
                "muscular_and_connective_tissue",
                "nervous_and_sensory",
                "cardiovascular",
                "respiratory",
                "renal_and_urinary",
                "endocrine",
                "lymphatic_and_immune",
                "integumentary_and_thermoregulation",
            },
            set(systems["whole_body_support_and_homeostasis"]["required_systems"]),
        )
        self.assertEqual(
            {
                "bladder_storage_urge_delay_and_voluntary_release",
                "bowel_storage_urge_delay_and_voluntary_release",
                "continence",
                "toilet_contact_and_privacy",
                "hygiene",
                "person_specific_cycle_and_material_source_distinction",
            },
            set(systems["bathroom_hygiene_and_cycle"]["required_functions"]),
        )
        relationship = systems["adult_relationship_intimacy_and_sexual_health"]
        self.assertEqual(
            {
                "adult_only_body_response_and_health_state",
                "person_owned_private_sensation_and_preference",
                "private_solitary_self_discovery_or_self_pleasure_by_person_choice",
                "private_touch_comfort_arousal_pleasure_climax_relaxation_discomfort_and_uncertainty_states",
                "specific_current_revocable_multi_participant_consent",
                "barrier_contraception_and_sti_health_state",
            },
            set(relationship["required_functions"]),
        )
        self.assertIs(relationship["geometry_or_body_response_may_create_consent"], False)
        self.assertIs(relationship["relationship_status_may_create_consent"], False)

        skin = systems["skin_soft_tissue_contact_and_clothing_deformation"]
        self.assertEqual(
            {
                "localized_skin_and_soft_tissue_indentation_under_bounded_touch_or_pressure",
                "nearby_soft_tissue_spread_shear_sliding_and_friction",
                "gradual_release_and_recovery_without_destructive_mesh_edits",
                "gravity_inertia_movement_and_support_surface_response",
                "tight_clothing_pressure_compression_and_soft_tissue_redistribution",
                "stable_seam_strap_waistband_cuff_and_shoe_contact",
                "separate_body_garment_hair_and_environment_collision_surfaces",
                "bounded_volume_stretch_compression_and_solver_energy",
                "return_to_the_same_underlying_body_after_clothing_removal",
                "separate_geometry_contact_sensation_health_consent_and_memory_truth",
            },
            set(skin["required_behaviors"]),
        )
        self.assertIs(skin["visible_deformation_proves_sensation_or_consent"], False)
        pregnancy = systems["conception_pregnancy_delivery_recovery_and_family"]
        self.assertEqual(
            {
                "separate_conception_choice",
                "ordinary_or_explicitly_accelerated_truthful_pregnancy_timeline",
                "gestational_body_and_health_adaptation",
                "delivery_and_hospital_care",
                "postpartum_recovery",
                "parent_child_and_family_state",
            },
            set(pregnancy["required_functions"]),
        )
        self.assertIs(pregnancy["family_state_is_body_mesh"], False)

        hair = set(systems["detachable_dynamic_hair"]["required_behaviors"])
        self.assertEqual(
            {
                "comb_part_and_style",
                "trim_cut_and_grow",
                "persistent_length_style_part_and_grooming_state",
                "distinct_dry_and_wet_states",
                "wet_clumping_increased_hanging_weight_and_believable_drying",
                "gravity_and_inertia",
                "secondary_motion_during_head_and_body_movement",
                "wind_response",
                "scalp_head_neck_shoulders_body_clothing_and_environment_collision",
                "sitting_walking_lying_turning_and_bending_pose_behavior",
                "touch_adjust_wash_comb_towel_dry_and_style_interactions",
                "saved_character_hair_state",
                "attach_remove_without_body_hash_change",
            },
            hair,
        )

        clothing = set(
            systems["separate_shareable_clothing"]["required_behaviors"]
        )
        self.assertEqual(
            {
                "independent_hash_bound_garment_identity",
                "target_measurements_inside_reviewed_fit_envelope",
                "same_maturity_lane",
                "exact_body_rig_garment_adapter_and_fit_evidence_hashes",
                "deformation_and_penetration_review_across_intended_motion",
                "reviewed_put_on_and_take_off_transitions",
                "owner_and_wearer_consent",
                "persistent_transfer_record",
                "stored",
                "grasped",
                "dressing",
                "worn",
                "undressing",
                "released",
                "returned_to_world_prop",
                "person_to_person_inventory_transfer",
                "share_through_exact_per_body_fit_and_rig_adapter",
                "underlying_body_hash_unchanged_when_clothing_is_removed",
            },
            clothing,
        )

    def test_current_truth_cannot_claim_body_or_runtime_completion(self) -> None:
        truth = self.matrix["current_truth"]
        self.assertIs(truth["requirements_are_recorded"], True)
        for name, value in truth.items():
            if name == "requirements_are_recorded":
                continue
            self.assertIs(value, False, name)
        systems = {
            row["system_id"]: row for row in self.matrix["required_body_systems"]
        }
        self.assertIs(
            systems["adult_relationship_intimacy_and_sexual_health"][
                "geometry_or_body_response_may_create_consent"
            ],
            False,
        )
        self.assertIs(
            systems["conception_pregnancy_delivery_recovery_and_family"][
                "family_state_is_body_mesh"
            ],
            False,
        )

    def test_acceptance_order_requires_multiple_test_bodies_and_distinct_robert(self) -> None:
        sequence = self.matrix["acceptance_sequence"]
        self.assertEqual(
            [
                "pin_sources_licenses_contracts_and_vocabularies",
                "preflight_each_scoped_anatomy_module_fail_closed",
                "author_private_inactive_separate_internal_modules",
                "assemble_modules_on_an_exact_accepted_bald_external_carrier_without_carrier_mutation",
                "pass_geometry_route_containment_collision_and_save_reload_checks",
                "pass_rig_deformation_contact_and_daily_life_pose_checks",
                "pass_skin_soft_tissue_touch_pressure_clothing_deformation_and_recovery_checks",
                "obtain_private_visual_and_owner_acceptance_for_kira",
                "connect_physiology_only_after_geometry_and_route_acceptance",
                "connect_person_decision_privacy_consent_health_and_memory_as_separate_systems",
                "generalize_avatar_builder_without_kira_identity_data",
                "generate_and_independently_test_multiple_invented_confirmed_adult_bodies",
                "build_and_accept_a_distinct_synthetic_robert_adult_male_body",
                "add_separate_detachable_hair_and_separate_clothing_after_each_bald_body_passes",
            ],
            sequence,
        )
        generalize = sequence.index("generalize_avatar_builder_without_kira_identity_data")
        multiple = sequence.index(
            "generate_and_independently_test_multiple_invented_confirmed_adult_bodies"
        )
        robert = sequence.index(
            "build_and_accept_a_distinct_synthetic_robert_adult_male_body"
        )
        hair_and_clothing = sequence.index(
            "add_separate_detachable_hair_and_separate_clothing_after_each_bald_body_passes"
        )
        self.assertLess(generalize, multiple)
        self.assertLess(multiple, robert)
        self.assertLess(robert, hair_and_clothing)

    def test_matrix_has_no_local_tooling_surface(self) -> None:
        serialized = json.dumps(self.matrix, sort_keys=True)
        lowered = serialized.lower()
        self.assertNotIn("co" + "dex", lowered)
        self.assertNotIn("hand" + "off", lowered)
        self.assertNotIn("c:\\\\users", lowered)


if __name__ == "__main__":
    unittest.main()
