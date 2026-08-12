from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "Tools" / "blender_probe_kira_r21_oral_rig.py"
ATTEMPT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "kira_r21_exact_wav_lipsync_preparation"
    / "attempt_02_r19_baseline_probe_worker"
)
CONFIG = ATTEMPT / "PROBE_CONFIG.json"
EVIDENCE_PLAN = ATTEMPT / "READ_ONLY_PROBE_EVIDENCE_PLAN.md"
EXPECTED_SOURCE = (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
EXPECTED_SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
EXPECTED_RIG_SHA256 = "f956738cf0ed89badf7292f2ab78836f8bbafcb79f5e1c0993f3ceb01fddbb81"


def call_chain(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = call_chain(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


class ReadOnlyOralRigProbePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_exact_approved_r19_source_is_the_only_selected_blend(self) -> None:
        source = self.config["source_blend"]
        self.assertEqual(source["path"], EXPECTED_SOURCE)
        self.assertEqual(source["sha256"], EXPECTED_SOURCE_SHA256)
        self.assertEqual(source["size_bytes"], 90861425)
        self.assertTrue((ROOT / source["path"]).is_file())
        self.assertEqual((ROOT / source["path"]).stat().st_size, source["size_bytes"])
        policy = self.config["selection_policy"]
        self.assertTrue(policy["exact_approved_r19_baseline_only"])
        self.assertTrue(policy["owner_approved_face_at_rest_is_immutable"])
        self.assertFalse(policy["r21_pelvis_candidate_selected"])
        self.assertFalse(policy["movement_candidate_selected"])
        self.assertFalse(policy["runtime_or_body_activation_authorized"])

    def test_exact_rig_and_three_oral_components_are_hash_bound(self) -> None:
        self.assertEqual(self.config["rig"]["object_name"], "Kira_R19_BlackProject_Native_188_Rig")
        self.assertEqual(self.config["rig"]["bone_count"], 188)
        self.assertEqual(self.config["rig"]["rest_structure_sha256"], EXPECTED_RIG_SHA256)
        components = {item["mesh_data_name"]: item for item in self.config["oral_components"]}
        self.assertEqual(
            set(components),
            {"Ariel_Mesh_Lips_0", "Ariel_Mesh_Teeth_0", "Ariel_Mesh_Mouth_0"},
        )
        self.assertEqual(
            components["Ariel_Mesh_Lips_0"]["geometry_uv_sha256"],
            "31b110d3b894d92d34d1241d48bc9b56e7335871019620e1ee789e17e1a5a41c",
        )
        self.assertEqual(
            components["Ariel_Mesh_Teeth_0"]["geometry_uv_sha256"],
            "044e79fc4183e9ed518ac057ca0be5b3ea1c77a7acc2240dc25fa0dafe5c008f",
        )
        self.assertEqual(
            components["Ariel_Mesh_Mouth_0"]["geometry_uv_sha256"],
            "3d9a188fd1bc0f775bea741af439a13b2d657a76d54e4c703299ce4df51884b4",
        )
        for component in components.values():
            self.assertRegex(component["positive_weight_assignment_sha256"], r"^[0-9a-f]{64}$")

    def test_required_bones_regions_and_clearance_pairs_are_complete(self) -> None:
        bones = set(self.config["oral_bone_names"])
        for required in (
            "upperTeeth_092",
            "lowerJaw_093",
            "lowerTeeth_094",
            "tongue01_095",
            "tongue02_096",
            "tongue03_097",
            "tongue04_098",
            "lLipCorner_0104",
            "LipLowerMiddle_0107",
            "rLipCorner_0110",
            "LipUpperMiddle_0161",
        ):
            self.assertIn(required, bones)
        regions = self.config["semantic_regions"]
        self.assertEqual(
            set(regions), {"upper_lip", "lower_lip", "upper_teeth", "lower_teeth", "tongue"}
        )
        relations = {item["id"] for item in self.config["rest_relations"]}
        self.assertEqual(
            relations,
            {
                "bilabial_rest_gap",
                "fv_lower_lip_to_upper_incisor_candidate_clearance",
                "upper_to_lower_teeth_rest_clearance",
                "tongue_to_upper_teeth_rest_clearance",
                "tongue_to_lower_teeth_rest_clearance",
            },
        )

    def test_worker_has_the_required_measurement_surfaces(self) -> None:
        function_names = {
            node.name for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef)
        }
        for required in (
            "mesh_geometry_uv_signature",
            "positive_weight_signature",
            "rig_rest_signature",
            "oral_bone_axes",
            "mesh_weight_inventory",
            "semantic_region_points",
            "rest_clearance_inventory",
            "shape_key_inventory",
            "action_inventory",
            "relevant_driver_inventory",
            "source_state_digest",
            "run_probe",
        ):
            self.assertIn(required, function_names)
        self.assertIn("matrix_local", self.source)
        self.assertIn("world_space_unit_axes", self.source)
        self.assertIn("minimum_weighted-vertex-sample_distance_not_signed_surface_clearance", self.source)
        self.assertIn("all_required_bones_at_identity_pose_basis", self.source)

    def test_worker_contains_no_blender_authoring_save_or_render_call(self) -> None:
        calls = [
            call_chain(node.func)
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
        ]
        forbidden_fragments = (
            "bpy.ops",
            "save_as_mainfile",
            "save_mainfile",
            "render.render",
            "keyframe_insert",
            "driver_add",
            "driver_remove",
            "shape_key_add",
            "shape_key_remove",
            "vertex_groups.new",
            "actions.new",
            "objects.new",
            "meshes.new",
            "frame_set",
        )
        for chain in calls:
            self.assertFalse(
                any(fragment in chain for fragment in forbidden_fragments),
                f"forbidden mutating call found: {chain}",
            )
        assigned_attributes = {
            target.attr
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if isinstance(target, ast.Attribute)
        }
        self.assertTrue(
            assigned_attributes.isdisjoint(
                {
                    "co",
                    "value",
                    "matrix_basis",
                    "matrix_world",
                    "location",
                    "rotation_euler",
                    "rotation_quaternion",
                    "scale",
                    "frame_current",
                }
            )
        )
        self.assertNotIn("mkdir", calls)
        self.assertIn('output_path.open("x"', self.source)

    def test_source_invariants_are_measured_before_and_after(self) -> None:
        self.assertGreaterEqual(self.source.count("source_state_digest("), 3)
        self.assertGreaterEqual(self.source.count("sha256_file(source_path)"), 2)
        self.assertIn("source_unchanged", self.source)
        self.assertIn("bpy.data.is_dirty", self.source)
        self.assertIn("pose_or_mesh_perturbed", self.source)
        self.assertIn('"pose_or_mesh_perturbed": False', self.source)

    def test_reserved_action_names_are_traceable_and_not_authored(self) -> None:
        self.assertEqual(
            set(self.config["reserved_action_names"]),
            {
                "KW_R21_VISEME_AH_REVIEW",
                "KW_R21_VISEME_EE_REVIEW",
                "KW_R21_VISEME_O_REVIEW",
                "KW_R21_VISEME_FV_REVIEW",
                "KW_R21_VISEME_MBP_REVIEW",
                "KW_R21_LIPSYNC_ATTEMPT05_EXACT_WAV_60FPS",
            },
        )
        self.assertNotIn("bpy.data.actions.new", self.source)

    def test_probe_has_not_been_run_and_evidence_plan_is_explicit(self) -> None:
        self.assertEqual(self.config["mode"], "READ_ONLY_NO_SAVE_NO_RENDER")
        self.assertFalse((ATTEMPT / "PROBE_RESULT.json").exists())
        plan = EVIDENCE_PLAN.read_text(encoding="utf-8")
        for phrase in (
            "Do not run Blender",
            "exact approved R19 baseline",
            "No perturbation",
            "PROBE_RESULT.json",
            "vertex-sample clearance",
            "not authorization to author",
        ):
            self.assertIn(phrase, plan)


if __name__ == "__main__":
    unittest.main()
