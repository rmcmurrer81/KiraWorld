from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_existing_mouth_authoring_limit_20260721"
)
EVIDENCE_PATH = PROOF_DIR / "topology_probe.json"
MANIFEST_PATH = PROOF_DIR / "manifest.json"
DIAGRAM_PATH = PROOF_DIR / "existing_single_mouth_topology_limit.png"
WORKSPACE_PATH = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1"
    / "kira_r7_authoring_workspace.blend"
)
SOURCE_R6_PATH = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
WORKER_PATH = PROJECT_ROOT / "tools/blender_probe_kira_r7_mouth_topology.py"
LAUNCHER_PATH = PROJECT_ROOT / "tools/inspect_kira_r7_existing_mouth_authoring_limit.py"
EXPECTED_PINNED_HASHES = {
    "workspace": "9d0f9dad39b2e0650419ccef48a7d524d5cd67e4429f1d23ee3398db396c0394",
    "source_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7ExistingMouthAuthoringLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_exact_existing_single_mouth_island_is_pinned(self) -> None:
        mouth = self.evidence["existing_mouth"]
        self.assertEqual(mouth["vertex_count"], 207)
        self.assertEqual(
            mouth["vertex_index_sha256"],
            "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b",
        )
        self.assertEqual(mouth["polygon_count"], 272)
        self.assertEqual(mouth["component_edge_count"], 478)
        self.assertEqual(mouth["euler_characteristic"], 1)
        self.assertEqual(mouth["face_vertex_count_histogram"], {"3": 272})

    def test_boundary_is_measured_but_not_semantically_inferred(self) -> None:
        mouth = self.evidence["existing_mouth"]
        self.assertEqual(mouth["boundary_edge_count"], 140)
        self.assertEqual(mouth["nonmanifold_edge_count"], 140)
        self.assertEqual(mouth["boundary_loop_count"], 1)
        self.assertEqual(mouth["boundary_vertex_degree_histogram"], {"2": 140})
        self.assertEqual(len(mouth["boundary_loops"]), 1)
        self.assertTrue(mouth["boundary_loops"][0]["closed"])
        self.assertEqual(mouth["boundary_loops"][0]["edge_count"], 140)
        self.assertEqual(mouth["boundary_loops"][0]["vertex_count"], 140)
        self.assertFalse(mouth["semantic_edge_map_present"])
        self.assertIsNone(mouth["central_oral_aperture_boundary_count"])
        self.assertIsNone(mouth["central_oral_aperture_present"])
        self.assertTrue(mouth["central_oral_aperture_truth"].startswith("unproven:"))

    def test_shape_keys_cannot_safely_invent_a_mouth_interior(self) -> None:
        mouth = self.evidence["existing_mouth"]
        self.assertTrue(mouth["shape_keys_preserve_topology"])
        self.assertFalse(mouth["interior_exposable_by_shape_keys_only"])
        self.assertFalse(mouth["non_destructive_real_mouth_authoring_feasible"])
        self.assertEqual(mouth["candidate_authoring_disposition"], "stopped_before_edit")
        self.assertIn("shortest-path selection would guess", mouth["exact_blocker"])

    def test_probe_left_pinned_inputs_byte_identical(self) -> None:
        verification = self.evidence["host_verification"]
        self.assertTrue(verification["all_pinned_inputs_byte_unchanged"])
        self.assertEqual(verification["pinned_hashes_before"], EXPECTED_PINNED_HASHES)
        self.assertEqual(verification["pinned_hashes_after"], EXPECTED_PINNED_HASHES)
        self.assertEqual(sha256_file(WORKSPACE_PATH), EXPECTED_PINNED_HASHES["workspace"])
        self.assertEqual(sha256_file(SOURCE_R6_PATH), EXPECTED_PINNED_HASHES["source_r6"])
        self.assertTrue(all(value is False for value in self.evidence["safety"].values()))

    def test_manifest_keeps_every_promotion_gate_closed(self) -> None:
        self.assertEqual(
            self.manifest["status"],
            "inactive_manual_semantic_selection_required",
        )
        result = self.manifest["result"]
        self.assertTrue(result["existing_single_mouth_preserved"])
        self.assertFalse(result["second_mouth_or_overlay_created"])
        self.assertFalse(result["mouth_interior_created"])
        self.assertFalse(result["viseme_or_jaw_controls_created"])
        self.assertTrue(result["deterministic_shortest_path_rejected"])
        self.assertEqual(
            result["required_manual_selection"],
            [
                "upper oral-fissure edge path",
                "lower oral-fissure edge path",
                "left and right commissure vertices",
                "outer attachment-rim edges",
                "open center/symmetry-seam edges and any duplicate center vertices",
            ],
        )
        self.assertTrue(all(value is False for value in self.manifest["gates"].values()))
        self.assertTrue(self.manifest["pinned_inputs_byte_unchanged"])

    def test_diagram_is_present_and_matches_manifest(self) -> None:
        self.assertTrue(DIAGRAM_PATH.is_file())
        self.assertGreater(DIAGRAM_PATH.stat().st_size, 0)
        self.assertEqual(
            sha256_file(DIAGRAM_PATH),
            self.manifest["artifacts"]["diagram_sha256"],
        )

    def test_probe_contains_no_save_export_or_runtime_mutation_call(self) -> None:
        worker = WORKER_PATH.read_text(encoding="utf-8")
        launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "bpy.ops.wm.save",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.export_scene",
            "bpy.ops.wm.open_mainfile",
        ):
            self.assertNotIn(forbidden, worker)
        for forbidden in (
            "bpy.ops.wm.save",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.export_scene",
            "bpy.ops.wm.open_mainfile",
        ):
            self.assertNotIn(forbidden, launcher)


if __name__ == "__main__":
    unittest.main()
