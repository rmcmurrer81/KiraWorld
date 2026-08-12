from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_adult_body_r7"
    / "workspace_v1"
)
CONTRACT_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_adult_body_r7_contract"
    / "r7_build_contract.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7AuthoringWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(CONTRACT_PATH)
        cls.manifest = load_json(WORKSPACE_DIR / "workspace_manifest.json")
        cls.audit = load_json(WORKSPACE_DIR / "workspace_audit.json")
        cls.registry = load_json(WORKSPACE_DIR / "semantic_mask_registry.json")
        cls.summary = load_json(WORKSPACE_DIR / "run_summary.json")

    def test_workspace_is_isolated_inactive_and_not_a_candidate(self) -> None:
        self.assertEqual(
            self.manifest["status"],
            "inactive_unmodified_workspace_waiting_for_manual_semantic_selection",
        )
        self.assertEqual(
            self.summary["status"],
            "prepared_inactive_workspace_waiting_for_manual_semantic_selection",
        )
        self.assertFalse(self.manifest["outputs"]["candidate_glb_created"])
        self.assertFalse(self.manifest["outputs"]["runtime_binding_changed"])
        self.assertFalse(self.manifest["outputs"]["avatar_builder_binding_changed"])
        self.assertFalse(self.manifest["outputs"]["home_world_changed"])
        self.assertFalse(self.summary["workspace"]["candidate_model_exported"])
        self.assertFalse(self.summary["workspace"]["runtime_binding_changed"])
        self.assertFalse(list(WORKSPACE_DIR.glob("*.glb")))
        self.assertFalse(list(WORKSPACE_DIR.glob("*.gltf")))

    def test_pinned_r6_source_was_hash_verified_and_remained_unchanged(self) -> None:
        r6 = self.contract["rollback_inputs"]["current_r6"]
        source_path = PROJECT_ROOT / r6["path"]
        expected = r6["sha256"]
        self.assertEqual(sha256_file(source_path), expected)
        self.assertEqual(self.manifest["source_sha256"], expected)
        self.assertEqual(self.audit["source_sha256"], expected)
        self.assertEqual(self.summary["source_r6"]["sha256_before"], expected)
        self.assertEqual(self.summary["source_r6"]["sha256_after"], expected)
        self.assertTrue(self.summary["source_r6"]["unchanged"])

    def test_workspace_file_matches_recorded_hash(self) -> None:
        workspace_path = PROJECT_ROOT / self.manifest["workspace"]["path"]
        self.assertTrue(workspace_path.is_file(), workspace_path)
        self.assertEqual(
            sha256_file(workspace_path), self.manifest["workspace"]["sha256"]
        )
        self.assertEqual(
            self.summary["workspace"]["sha256"],
            self.manifest["workspace"]["sha256"],
        )

    def test_independent_blender_reopen_audit_is_byte_identical(self) -> None:
        original = WORKSPACE_DIR / "workspace_audit.json"
        recheck = WORKSPACE_DIR / "workspace_audit_recheck.json"
        self.assertTrue(recheck.is_file(), recheck)
        self.assertEqual(sha256_file(original), sha256_file(recheck))
        self.assertEqual(
            sha256_file(original),
            self.summary["audit"]["sha256"],
        )

    def test_exact_body_head_mouth_rig_and_weights_are_preserved(self) -> None:
        integrity = self.audit["workspace_integrity"]
        self.assertTrue(integrity["prepared_baseline_exact"])
        self.assertTrue(all(integrity["working_body_preservation"].values()))
        self.assertTrue(all(integrity["protected_full_surface_baseline"].values()))
        self.assertEqual(integrity["source_bone_count"], 79)
        self.assertLessEqual(integrity["maximum_positive_skin_influences"], 4)
        self.assertTrue(
            integrity["existing_head_and_single_mouth_preserved_by_exact_whole_surface"]
        )
        self.assertFalse(integrity["second_mouth_created"])

        preserved = self.manifest["exact_preservation"]
        for key in (
            "whole_surface_position_hash_preserved",
            "shape_key_coordinates_and_values_preserved",
            "face_index_topology_preserved",
            "uv_preserved",
            "skin_vertex_group_names_and_order_preserved",
            "skin_weight_assignments_preserved",
            "bone_names_order_parents_and_rest_matrices_preserved",
            "existing_single_mouth_preserved_as_part_of_exact_whole_surface",
        ):
            self.assertTrue(preserved[key], key)
        self.assertEqual(preserved["bone_count"], 79)
        self.assertLessEqual(preserved["maximum_positive_influences"], 4)
        self.assertFalse(preserved["second_mouth_created"])

    def test_semantic_masks_are_empty_review_scaffolds_not_guessed_regions(self) -> None:
        expected = {
            "r7_mask_protected_head_existing_mouth",
            "r7_mask_authorable_body_below_protected_boundary",
            "r7_mask_mammary_areola_left",
            "r7_mask_mammary_areola_right",
            "r7_mask_external_genital_surface",
        }
        infrastructure = self.audit["semantic_mask_infrastructure"]
        self.assertTrue(infrastructure["scaffold_structure_valid"])
        self.assertFalse(infrastructure["automated_body_region_selection_used"])
        self.assertTrue(infrastructure["all_masks_empty"])
        self.assertEqual(set(infrastructure["masks"]), expected)
        for record in infrastructure["masks"].values():
            self.assertTrue(record["present"])
            self.assertEqual(record["domain"], "POINT")
            self.assertEqual(record["data_type"], "FLOAT")
            self.assertEqual(record["nonzero_vertex_count"], 0)
            self.assertEqual(record["fractional_value_count"], 0)

        registry_masks = {
            record["attribute"]: record for record in self.registry["masks"]
        }
        self.assertEqual(set(registry_masks), expected)
        for record in registry_masks.values():
            self.assertEqual(record["initial_nonzero_vertex_count"], 0)
            self.assertTrue(record["human_review_required"])
            self.assertEqual(
                record["selection_state"],
                "empty_unreviewed_no_automated_region_guess",
            )
        self.assertFalse(self.registry["storage"]["skin_vertex_groups_changed"])
        self.assertFalse(self.registry["storage"]["skin_weights_changed"])

    def test_all_authoring_promotion_and_autobuild_gates_remain_closed(self) -> None:
        partition = self.audit["semantic_mask_infrastructure"]["protection_partition"]
        self.assertFalse(partition["protected_nonempty"])
        self.assertFalse(partition["authorable_nonempty"])
        self.assertFalse(partition["complete_vertex_domain_partition"])
        self.assertTrue(all(value is False for value in self.audit["gates"].values()))
        self.assertTrue(all(value is False for value in self.manifest["gates"].values()))

    def test_next_operation_requires_reviewed_manual_selection_and_exact_complement(self) -> None:
        operation = self.audit["next_required_operation"]
        self.assertEqual(
            operation["operation_id"],
            "manual_reviewed_protected_boundary_selection",
        )
        self.assertFalse(operation["automatic_selection_allowed"])
        instructions = " ".join(operation["instructions"]).lower()
        self.assertIn("head", instructions)
        self.assertIn("mouth", instructions)
        self.assertIn("exact remaining vertex-domain complement", instructions)
        self.assertIn("attestation", instructions)


if __name__ == "__main__":
    unittest.main()
