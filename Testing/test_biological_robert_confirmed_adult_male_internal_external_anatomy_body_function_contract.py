from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "Avatar/avatar_builder/body_systems/biological_robert_confirmed_adult_male_internal_external_anatomy_body_function_contract_v1.json"
DOC = ROOT / "System/Docs/BIOLOGICAL_ROBERT_CONFIRMED_ADULT_MALE_INTERNAL_EXTERNAL_ANATOMY_AND_BODY_FUNCTION_CONTRACT_20260809.md"


class BiologicalRobertConfirmedAdultMaleAnatomyBodyFunctionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.document = DOC.read_text(encoding="utf-8")

    def test_design_only_kira_priority_and_no_authoring(self) -> None:
        self.assertEqual(
            self.contract["status"],
            "SOURCE_BACKED_DESIGN_AND_ACCEPTANCE_CONTRACT_ONLY_NOT_IMPLEMENTED_NOT_RUNTIME_AUTHORITY",
        )
        scope = self.contract["priority_and_scope"]
        self.assertTrue(scope["kira_body_priority_preserved"])
        self.assertEqual(scope["robert_authoring_state"], "PENDING_KIRA_OWNER_REVIEW")
        self.assertFalse(scope["accepted_robert_carrier_exists"])
        for key in (
            "body_or_mesh_authoring_authorized",
            "blender_execution_authorized",
            "private_photos_opened_or_copied_by_this_contract",
            "runtime_activation_authorized",
            "explicit_behavior_scene_authorized",
            "physiology_or_sensation_implemented",
        ):
            self.assertIs(scope[key], False, key)

    def test_protected_references_are_hash_only_subject_bound_and_not_reused(self) -> None:
        separation = self.contract["subject_reference_separation"]
        self.assertEqual(len(separation["protected_hash_only_manifests"]), 2)
        for relative in separation["protected_hash_only_manifests"]:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["subject_id"], "robert_user_avatar")
        for key in (
            "raw_source_paths_recorded",
            "raw_source_filenames_recorded",
            "raw_pixels_or_derivatives_emitted",
            "contact_sheet_or_thumbnail_emitted",
            "medical_sources_may_supply_robert_specific_dimensions",
            "robert_private_values_reusable_for_other_subjects",
            "generic_builder_training_allowed",
            "circumcision_or_variant_inference_from_generic_atlas_allowed",
        ):
            self.assertIs(separation[key], False, key)

    def test_confirmed_adult_privacy_fails_closed(self) -> None:
        privacy = self.contract["maturity_and_privacy"]
        self.assertEqual(privacy["maturity_status_required"], "confirmed_adult")
        self.assertEqual(privacy["non_adult_or_unresolved_body_representation"], "doll_safe_non_anatomical")
        self.assertTrue(privacy["private_review_lease_required"])
        self.assertEqual(privacy["allowed_unclothed_reviewers"], ["robert_exact_subject_and_biological_owner"])
        for key in (
            "synthetic_person_or_general_gallery_access_allowed",
            "review_lease_is_consent_or_activity_authority",
            "public_export_or_upload_allowed",
            "runtime_instantiation_allowed",
            "raw_reference_in_review_package_allowed",
        ):
            self.assertIs(privacy[key], False, key)

    def test_external_body_is_complete_not_a_painted_or_doll_safe_panel(self) -> None:
        external = self.contract["external_surface_requirements"]
        self.assertTrue(external["one_structurally_complete_connected_adult_body_required"])
        required = set(external["required_semantic_regions"])
        self.assertTrue({"penile_root_attachment", "external_urethral_meatus", "scrotal_compartment_left", "scrotal_compartment_right", "perineal_raphe_and_body", "anal_opening"}.issubset(required))
        forbidden = set(external["forbidden_visual_or_geometry_failures"])
        self.assertTrue({"doll_safe_pelvic_surface", "painted_or_plate_substitute", "fused_shaft_scrotum_block", "open_cavity_or_hole"}.issubset(forbidden))

    def test_required_internal_systems_and_metadata_are_present(self) -> None:
        meshes = self.contract["required_internal_module_meshes"]
        self.assertEqual(set(meshes), {"urinary", "reproductive", "penile_support", "posterior_bowel", "pelvic_perineal_support", "orientation"})
        self.assertTrue({"bladder_shell", "prostatic_urethra", "membranous_urethra", "spongy_urethra"}.issubset(meshes["urinary"]))
        self.assertTrue({"testis_left", "testis_right", "vas_deferens_left", "vas_deferens_right", "ejaculatory_duct_left", "ejaculatory_duct_right", "prostate"}.issubset(meshes["reproductive"]))
        self.assertTrue({"rectum", "anal_canal", "external_anal_sphincter_proxy"}.issubset(meshes["posterior_bowel"]))
        self.assertEqual(
            set(self.contract["per_mesh_required_metadata"]),
            {"anatomy_id", "system", "laterality", "review_visibility", "material_id", "source_contract_id", "function_implemented"},
        )

    def test_male_route_has_two_external_outlets_and_named_shared_urethral_convergence(self) -> None:
        topology = self.contract["route_topology"]
        self.assertEqual(topology["external_outlet_count_in_scope"], 2)
        bindings = topology["external_outlet_bindings"]
        self.assertEqual({row["anchor"] for row in bindings}, {"external_urethral_meatus", "anal_opening"})
        meatus = next(row for row in bindings if row["anchor"] == "external_urethral_meatus")
        self.assertEqual(meatus["systems"], ["urinary", "reproductive"])
        self.assertTrue(meatus["shared_downstream_conduit_is_anatomically_required"])
        self.assertIn("ejaculatory_duct_left_to_prostatic_urethra", topology["permitted_cross_system_junctions"])
        self.assertIn("ejaculatory_duct_right_to_prostatic_urethra", topology["permitted_cross_system_junctions"])
        self.assertFalse(topology["other_cross_system_lumen_or_endpoint_merging_allowed"])
        self.assertFalse(topology["bowel_urogenital_shared_lumen_or_outlet_allowed"])
        self.assertFalse(topology["female_three_outlet_rule_applies"])
        self.assertFalse(topology["duplicated_urinary_and_reproductive_external_meatus_required"])

    def test_carrier_is_write_protected_and_deformation_gates_are_explicit(self) -> None:
        interface = self.contract["attachment_interface"]
        self.assertTrue(interface["accepted_carrier_required"])
        self.assertTrue(interface["source_carrier_hash_must_match_before_and_after"])
        self.assertEqual(interface["carrier_dependency_mode"], "READ_ONLY_TRANSFORM_FOLLOWING_ONLY")
        self.assertEqual(
            set(interface["forbidden_carrier_writes"]),
            {"vertices", "uvs", "materials", "armature_bones", "constraints", "weights", "shape_keys", "drivers", "actions"},
        )
        gates = set(self.contract["rig_collision_and_deformation_gates"])
        self.assertIn("root_attached_with_bounded_stretch", gates)
        self.assertIn("left_right_scrotal_compartments_distinct_not_fused_inverted_or_collapsed", gates)
        self.assertIn("bowel_route_separate_in_every_pose", gates)

    def test_body_function_and_bathroom_readiness_require_real_pose_evidence(self) -> None:
        matrix = self.contract["acceptance_matrix"]
        poses = set(matrix["required_poses"])
        self.assertTrue({"walk_stride", "jog_run_stride", "door_handle_reach", "handwashing_reach", "shower_bath_entry", "seated_toilet_contact", "neutral_standing_bathroom_posture"}.issubset(poses))
        self.assertIn("pose_contact_clearance_and_return_to_neutral", matrix["hard_gates"])
        bathroom = self.contract["bathroom_readiness"]
        self.assertEqual(bathroom["current_status"], "NOT_IMPLEMENTED_NOT_TESTED")
        self.assertTrue(bathroom["geometry_ready_claim_requires_all_exact_hash_gates"])
        self.assertFalse(bathroom["fluid_waste_semen_sound_odor_health_or_memory_emission_allowed"])
        self.assertFalse(bathroom["geometry_ready_equals_urination_or_defecation_implemented"])

    def test_no_function_health_sensation_fertility_or_consent_claim_is_minted(self) -> None:
        truth = self.contract["truth_limits"]
        false_keys = (
            "geometry_proves_living_tissue_or_biological_function",
            "urination_implemented",
            "defecation_implemented",
            "continence_implemented",
            "erection_or_arousal_implemented",
            "ejaculation_implemented",
            "spermatogenesis_or_fertility_implemented",
            "hormone_or_endocrine_function_implemented",
            "sensation_or_subjective_experience_implemented",
            "hygiene_or_bathroom_use_implemented",
            "health_disease_or_diagnosis_implemented",
            "anatomy_or_body_response_is_consent",
            "anatomy_or_body_response_is_desire_or_preference",
            "private_reference_is_medical_diagnosis",
        )
        for key in false_keys:
            self.assertIs(truth[key], False, key)
        runtime = self.contract["future_runtime_truth_separation"]
        self.assertIn("consent", runtime["separate_state_domains"])
        self.assertIn("memory", runtime["separate_state_domains"])
        self.assertFalse(runtime["anatomy_or_physiology_can_auto_grant_consent"])
        self.assertFalse(runtime["runtime_activation_without_separate_acceptance"])

    def test_document_and_authoritative_sources_are_bound(self) -> None:
        self.assertIn("NO ROBERT BODY,\nMESH, RIG, PHYSIOLOGY, SENSATION, OR RUNTIME FUNCTION IS IMPLEMENTED", self.document)
        self.assertIn("PENDING_KIRA_OWNER_REVIEW", self.document)
        self.assertIn("two external outlets in this scope", self.document)
        self.assertIn(CONTRACT.relative_to(ROOT).as_posix(), self.document)
        for row in self.contract["source_registry"]:
            self.assertIn(row["url"], self.document)
            self.assertTrue(row["url"].startswith("https://www.ncbi.nlm.nih.gov/") or row["url"].startswith("https://www.niddk.nih.gov/"))


if __name__ == "__main__":
    unittest.main()
