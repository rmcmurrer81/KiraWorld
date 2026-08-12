from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "Avatar/avatar_builder/body_systems/kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1.json"
DOC = ROOT / "System/Docs/KIRA_CONFIRMED_ADULT_INTERNAL_PELVIC_ANATOMY_MODULE_CONTRACT_20260809.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KiraConfirmedAdultInternalPelvicAnatomyModuleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.document = DOC.read_text(encoding="utf-8")

    def test_design_only_and_non_mutating(self) -> None:
        self.assertEqual(
            self.contract["status"],
            "SOURCE_BACKED_DESIGN_CONTRACT_ONLY_NOT_IMPLEMENTED_NOT_RUNTIME_AUTHORITY",
        )
        scope = self.contract["scope"]
        for key in (
            "external_body_mesh_mutation_authorized",
            "approved_face_mutation_authorized",
            "approved_skin_mutation_authorized",
            "carrier_rig_mutation_authorized",
            "blender_execution_authorized",
            "runtime_activation_authorized",
            "explicit_behavior_scene_authorized",
            "physiology_simulation_implemented",
        ):
            self.assertIs(scope[key], False, key)

    def test_r19_inventory_is_exact_and_r24_is_not_silently_selected(self) -> None:
        r19 = self.contract["carrier_inventory_read_only"]["r19_candidate"]
        path = ROOT / r19["path"]
        self.assertTrue(path.is_file())
        self.assertEqual(path.stat().st_size, r19["bytes"])
        self.assertEqual(digest(path), r19["sha256"])
        r24 = self.contract["carrier_inventory_read_only"]["r24_candidate"]
        self.assertEqual(r24["status"], "NO_ACCEPTED_R24_CARRIER_INVENTORIED_BY_THIS_CONTRACT")
        self.assertEqual(r24["may_be_selected_only_after"], ["exact_manifest_hash", "separate_owner_review_acceptance"])

    def test_adult_privacy_boundary_fails_closed(self) -> None:
        privacy = self.contract["maturity_and_privacy"]
        self.assertEqual(privacy["maturity_status_required"], "confirmed_adult")
        self.assertEqual(privacy["non_adult_or_unresolved_body_representation"], "doll_safe_non_anatomical")
        self.assertTrue(privacy["private_review_lease_required"])
        for key in ("review_lease_is_consent_or_activity_authority", "public_export_allowed", "general_gallery_allowed", "runtime_instantiation_allowed"):
            self.assertIs(privacy[key], False, key)

    def test_anatomical_routes_and_outlets_are_distinct(self) -> None:
        bindings = self.contract["external_outlet_bindings"]
        self.assertEqual(len(bindings), 3)
        self.assertEqual({row["route"] for row in bindings}, {"urinary", "reproductive", "bowel"})
        self.assertEqual(len({row["anchor"] for row in bindings}), 3)
        self.assertTrue(all(row["exclusive"] for row in bindings))
        spatial = self.contract["spatial_relationships"]
        self.assertEqual(spatial["sagittal_order_anterior_to_posterior"], ["bladder_and_female_urethra", "vaginal_canal_cervix_uterus", "rectum_and_anal_canal"])
        self.assertFalse(spatial["compartment_merging_allowed"])
        self.assertFalse(spatial["shared_lumen_allowed"])
        self.assertFalse(spatial["shared_external_endpoint_allowed"])

    def test_carrier_write_protection_and_pose_review_are_mandatory(self) -> None:
        interface = self.contract["attachment_interface"]
        self.assertTrue(interface["source_carrier_hash_must_match_before_and_after"])
        self.assertEqual(interface["carrier_dependency_mode"], "READ_ONLY_TRANSFORM_FOLLOWING_ONLY")
        self.assertEqual(
            set(interface["forbidden_carrier_writes"]),
            {"vertices", "uvs", "materials", "armature_bones", "constraints", "shape_keys", "drivers", "actions", "vertex_groups"},
        )
        matrix = self.contract["acceptance_matrix"]
        self.assertEqual(len(matrix["required_poses"]), 7)
        self.assertIn("seated_contact", matrix["required_poses"])
        self.assertIn("supine", matrix["required_poses"])
        self.assertIn("three_distinct_exclusive_outlet_bindings", matrix["hard_gates"])

    def test_no_biological_function_or_consent_claim_is_minted(self) -> None:
        truth = self.contract["truth_limits"]
        for key in (
            "geometry_proves_biological_function",
            "urination_implemented",
            "defecation_implemented",
            "menstrual_cycle_implemented",
            "pregnancy_implemented",
            "sensation_implemented",
            "health_or_diagnosis_implemented",
            "anatomy_or_body_response_is_consent",
            "anatomy_or_body_response_is_desire_or_preference",
        ):
            self.assertIs(truth[key], False, key)

    def test_document_and_sources_are_present(self) -> None:
        self.assertIn("NO MESH, RIG, RUNTIME, OR\nPHYSIOLOGY IMPLEMENTED", self.document)
        for row in self.contract["source_registry"]:
            self.assertIn(row["url"], self.document)
            self.assertTrue(row["url"].startswith("https://"))
        self.assertIn(CONTRACT.relative_to(ROOT).as_posix(), self.document)


if __name__ == "__main__":
    unittest.main()
