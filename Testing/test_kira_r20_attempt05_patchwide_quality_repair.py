from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import struct
import unittest

from Core import kira_r20_curvilinear_pelvic_patch as sealed
from Core import kira_r20_attempt05_patchwide_quality_repair as repair


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_04_quality_diagnostic_01/QUALITY_DIAGNOSTIC_EVIDENCE.json"
)
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json"
)
PURE_MODULE = ROOT / "Core/kira_r20_attempt05_patchwide_quality_repair.py"
BOOTSTRAP = ROOT / "tools/blender_author_kira_r20_pelvis_only_attempt05.py"
ATTEMPT05_OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_05"
)

EXPECTED = {
    "r20_candidate_a_balanced_organic": {
        "positions_sha256": "3a163ffb9ad6dcb4c50e5900267b6ef1254d2e93439766a5bda6d8fa7bbcf548",
        "feature_sha256": "b9bc934349a8328111fda74034ba7208bfc4969ddbad7d179230eed283b049d9",
        "sweeps": 1832,
        "maximum_ratio": 2.8111308538532214,
        "maximum_landmark_centroid_drift_m": 0.00039383633064582414,
        "float32_maximum_ratio": 2.811129471077544,
    },
    "r20_candidate_b_soft_natural": {
        "positions_sha256": "00c3fd137ba45eb9e9b081c88acb9afe3e4f2611dbe46a9212c79efe93a60f27",
        "feature_sha256": "f91b36305627ac14c17b43f7cad9c80a7cbd6e9bc489a736c928258f7adbaeec",
        "sweeps": 1760,
        "maximum_ratio": 2.877648372542592,
        "maximum_landmark_centroid_drift_m": 0.00026102876083624547,
        "float32_maximum_ratio": 2.8776474663917315,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


class Attempt05PatchwideQualityRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
        cls.inputs = cls.diagnostic["construction_inputs"]
        cls.results = {}
        for candidate in sealed.CANDIDATES:
            positions, evidence = repair.build_positions(
                cls.inputs["seam_project_m"],
                cls.inputs["first_exterior_ring_project_m"],
                cls.inputs["second_exterior_ring_project_m"],
                cls.inputs["seam_normals_project"],
                candidate,
            )
            original, _original_evidence = repair._SEALED_BUILD_POSITIONS(
                cls.inputs["seam_project_m"],
                cls.inputs["first_exterior_ring_project_m"],
                cls.inputs["second_exterior_ring_project_m"],
                cls.inputs["seam_normals_project"],
                candidate,
            )
            cls.results[candidate.candidate_id] = (positions, evidence, original)

    def test_01_sealed_callable_and_authorities_remain_exact(self) -> None:
        self.assertIs(repair._SEALED_BUILD_POSITIONS, sealed.build_positions)
        expected = {
            "Core/kira_r20_curvilinear_pelvic_patch.py": "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d",
            "tools/blender_author_kira_r20_pelvis_only.py": "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a",
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json": "5ab9d60a948d7cac4e08e71a0f9c3927af9f33004ef23f888cc60f21b2e9e7cc",
            "Testing/test_kira_r20_pelvis_only_authoring.py": "8e12b0573db0715ea339a163d705aa856142e3fbeee9f02e05e96fb3145bc71a",
        }
        for relative, digest in expected.items():
            self.assertEqual(sha256_file(ROOT / relative), digest, relative)

    def test_02_attempt04_and_diagnostic_evidence_are_append_only_exact(self) -> None:
        expected = {
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04/AUTHORING_SUMMARY.json": "66607972ca0678355b87b425678c952cc2b82fdd193894be7bb2666e5186c7af",
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04/AUTHOR_FAILURE.json": "e0840aef480144a72221646ef4b67fcda1da5404429e4df46957239a6237f07e",
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04/r20_candidate_a_balanced_organic/FAILURE_EVIDENCE.json": "468b4a8366ce78231b24fada48771a14ca4e96bc8324aec26b2ccbadddcc2299",
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04/r20_candidate_b_soft_natural/FAILURE_EVIDENCE.json": "a60b8b0ad47cbb87d453a34c845850d5e650b23005913c641cbc6cf1dd31fd28",
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01/QUALITY_DIAGNOSTIC_EVIDENCE.json": "3d44a5ac098e647a33e77740663ff88fa983f78d79ccf67e5f74866a29092950",
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01/CHECKPOINT.md": "9de4862ddff56ceabba8922152a2223708af088cd29f1285ff0e291cea26a1e4",
            "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01/PACKAGE_MANIFEST.json": "b583473840385c52887dec11fd5043bb8bc7074cc0e1fef398707f1b69ec0aca",
        }
        for relative, digest in expected.items():
            self.assertEqual(sha256_file(ROOT / relative), digest, relative)

    def test_03_attempt05_output_is_absent_before_authoring(self) -> None:
        self.assertFalse(ATTEMPT05_OUTPUT.exists())

    def test_04_exact_seam_topology_counts_and_candidate_ids_are_preserved(self) -> None:
        self.assertEqual(
            sealed.topology_contract()["connectivity_sha256"],
            "761981c7b14b769fb1d750deef946ab95019821c2280383d7e1c5cf15c47b749",
        )
        self.assertEqual(sealed.NEW_VERTEX_COUNT, 740)
        self.assertEqual(sealed.REPLACEMENT_FACE_COUNT, 756)
        self.assertEqual(set(self.results), set(EXPECTED))
        for positions, evidence, _original in self.results.values():
            self.assertEqual(tuple(positions[:34]), tuple(map(tuple, self.inputs["seam_project_m"])))
            self.assertEqual(len(positions), 774)
            self.assertFalse(evidence["topology_changed"])
            self.assertFalse(evidence["candidate_parameters_changed"])
            self.assertFalse(evidence["acceptance_threshold_changed"])

    def test_05_pinned_deterministic_outputs_and_feature_fields(self) -> None:
        for candidate_id, (positions, evidence, _original) in self.results.items():
            expected = EXPECTED[candidate_id]
            record = evidence["patchwide_quality_repair"]
            self.assertEqual(record["output_positions_sha256"], expected["positions_sha256"])
            self.assertEqual(record["feature_scalar_field_sha256"], expected["feature_sha256"])
            self.assertEqual(record["sweeps_used"], expected["sweeps"])
            self.assertEqual(record["output_positions_sha256"], repair._canonical_sha256(positions))
            self.assertFalse(record["feature_scalar_values_or_station_order_changed"])

    def test_06_double_precision_quality_orientation_and_area_pass(self) -> None:
        for candidate_id, (_positions, evidence, _original) in self.results.items():
            metrics = evidence["patchwide_quality_repair"]["post_repair_strict_metrics"]
            self.assertAlmostEqual(
                metrics["maximum_quad_edge_ratio"], EXPECTED[candidate_id]["maximum_ratio"], places=14
            )
            self.assertLessEqual(metrics["maximum_quad_edge_ratio"], 2.90)
            self.assertEqual(metrics["edge_ratio_violation_count_at_3"], 0)
            self.assertGreater(metrics["minimum_face_area_m2"], 1.0e-10)
            self.assertEqual(metrics["degenerate_face_count_at_1e_10_m2"], 0)
            self.assertEqual(metrics["triangle_1_nonpositive_signed_count"], 0)
            self.assertEqual(metrics["triangle_2_nonpositive_signed_count"], 0)
            self.assertEqual(metrics["mutual_triangle_negative_dot_count"], 0)
            self.assertEqual(metrics["exact_duplicate_position_count"], 0)
            self.assertEqual(len(metrics["all_756_edge_ratios"]), 756)
            self.assertEqual(len(metrics["all_756_face_areas_m2"]), 756)

    def test_07_caps_normal_component_and_landmark_drift_pass(self) -> None:
        for candidate_id, (_positions, evidence, _original) in self.results.items():
            record = evidence["patchwide_quality_repair"]
            self.assertLessEqual(record["maximum_absolute_frozen_normal_drift_m"], 1.0e-12)
            self.assertLessEqual(
                record["landmark_centroid_drift"]["maximum_drift_m"],
                record["landmark_centroid_drift_limit_m"],
            )
            self.assertAlmostEqual(
                record["landmark_centroid_drift"]["maximum_drift_m"],
                EXPECTED[candidate_id]["maximum_landmark_centroid_drift_m"],
                places=14,
            )
            self.assertEqual(len(record["all_774_displacement_records"]), 774)
            for displacement in record["all_774_displacement_records"]:
                self.assertLessEqual(
                    displacement["magnitude_m"], displacement["cap_m"] + 1.0e-12
                )

    def test_08_float32_local_world_roundtrip_preserves_margin(self) -> None:
        matrix = json.loads(CONFIG.read_text(encoding="utf-8"))[
            "attempt_04_coordinate_space_contract"
        ]["body_matrix_world"]
        inverse, _normal_matrix, _affine = sealed.positive_affine_transform_matrices(matrix)
        faces = tuple(sealed.build_quad_topology(reverse_winding=False))
        for candidate_id, (positions, _evidence, original) in self.results.items():
            generated_local = sealed.transform_affine_points(inverse, positions[34:])
            stored_local = tuple(tuple(float32(value) for value in row) for row in generated_local)
            returned_world = sealed.transform_affine_points(matrix, stored_local)
            roundtrip = tuple(positions[:34]) + returned_world
            reference_faces, _reference_vertices = repair._reference_frames(original, faces)
            metrics = repair._strict_metrics(roundtrip, faces, reference_faces)
            self.assertAlmostEqual(
                metrics["maximum_quad_edge_ratio"],
                EXPECTED[candidate_id]["float32_maximum_ratio"],
                places=12,
            )
            self.assertLessEqual(metrics["maximum_quad_edge_ratio"], 2.95)
            self.assertEqual(metrics["edge_ratio_violation_count_at_3"], 0)
            self.assertEqual(metrics["triangle_1_nonpositive_signed_count"], 0)
            self.assertEqual(metrics["triangle_2_nonpositive_signed_count"], 0)
            self.assertEqual(metrics["mutual_triangle_negative_dot_count"], 0)
            self.assertGreater(metrics["minimum_face_area_m2"], 1.0e-10)

    def test_09_pure_module_has_no_blender_or_heavy_solver_dependency(self) -> None:
        tree = ast.parse(PURE_MODULE.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue({"bpy", "bmesh", "numpy", "torch", "scipy"}.isdisjoint(imported))
        text = PURE_MODULE.read_text(encoding="utf-8")
        for token in ("bpy.ops", "bmesh.new", "save_as_mainfile", "export_scene"):
            self.assertNotIn(token, text)

    def test_10_bootstrap_is_narrow_and_reversible(self) -> None:
        tree = ast.parse(BOOTSTRAP.read_text(encoding="utf-8"))
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("_ORIGINAL_VALIDATE_CONFIG(config_path, args)", text)
        self.assertIn("sealed_worker.patch_contract.build_positions = repair.build_positions", text)
        self.assertIn("sealed_worker.patch_contract.build_positions = _ORIGINAL_BUILD_POSITIONS", text)
        self.assertIn("paths[\"author_output\"] = target", text)
        self.assertIn("attempt_05", text)
        self.assertIn("args.mode == \"preflight\"", text)
        for token in ("bpy.ops", "bmesh.new", "save_as_mainfile", "export_scene", "unlink("):
            self.assertNotIn(token, text)
        self.assertGreater(len(tuple(ast.walk(tree))), 0)

    def test_11_truthful_external_surface_scope(self) -> None:
        for _positions, evidence, _original in self.results.values():
            self.assertTrue(evidence["external_surface_only"])
            self.assertFalse(evidence["internal_physiology_claimed"])
            record = evidence["patchwide_quality_repair"]
            self.assertFalse(record["bmesh_called"])
            self.assertFalse(record["mesh_edited"])
            self.assertFalse(record["blend_saved"])


if __name__ == "__main__":
    unittest.main()

