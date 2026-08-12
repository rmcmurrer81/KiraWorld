from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_existing_mouth_semantic_review_20260721"
)
EVIDENCE_PATH = PROOF_DIR / "semantic_review_evidence.json"
MANIFEST_PATH = PROOF_DIR / "manifest.json"
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
WORKER_PATH = PROJECT_ROOT / "tools/blender_review_kira_r7_mouth_semantics.py"
LAUNCHER_PATH = PROJECT_ROOT / "tools/review_kira_r7_existing_mouth_semantics.py"

EXPECTED_PINNED_HASHES = {
    "workspace": "9d0f9dad39b2e0650419ccef48a7d524d5cd67e4429f1d23ee3398db396c0394",
    "source_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
}
EXPECTED_COMPONENT_HASH = (
    "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_edge(edge: list[int]) -> tuple[int, int]:
    return tuple(sorted(edge))


class KiraR7ExistingMouthSemanticReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_exact_existing_component_remains_pinned(self) -> None:
        mouth = self.evidence["existing_mouth"]
        self.assertEqual(mouth["vertex_count"], 207)
        self.assertEqual(mouth["vertex_index_sha256"], EXPECTED_COMPONENT_HASH)
        self.assertEqual(mouth["boundary_edge_count"], 140)
        self.assertEqual(len(mouth["ordered_boundary"]), 141)
        self.assertEqual(mouth["ordered_boundary"][0], mouth["ordered_boundary"][-1])

    def test_candidate_partition_is_complete_but_explicitly_rejected(self) -> None:
        partition = self.evidence["candidate_boundary_partition"]
        role_keys = (
            "upper_oral_fissure_edges",
            "lower_oral_fissure_edges",
            "commissure_edges",
            "outer_attachment_rim_edges",
            "open_upper_center_seam_edges",
        )
        expected_counts = (35, 31, 2, 68, 4)
        role_edges = [partition[key] for key in role_keys]
        self.assertEqual(tuple(map(len, role_edges)), expected_counts)

        flattened = [canonical_edge(edge) for group in role_edges for edge in group]
        self.assertEqual(len(flattened), 140)
        self.assertEqual(len(set(flattened)), 140)

        ordered = self.evidence["existing_mouth"]["ordered_boundary"]
        boundary_edges = {
            canonical_edge([first, second])
            for first, second in zip(ordered, ordered[1:])
        }
        self.assertEqual(set(flattened), boundary_edges)
        self.assertTrue(partition["boundary_partition_complete"])
        self.assertEqual(partition["boundary_partition_unique_edge_count"], 140)
        self.assertEqual(
            partition["semantic_status"], "rejected_not_visually_defensible"
        )

    def test_candidate_commissures_and_duplicate_center_pairs_are_exact(self) -> None:
        partition = self.evidence["candidate_boundary_partition"]
        self.assertEqual(partition["right_commissure_vertices"], [7307, 7308])
        self.assertEqual(partition["left_commissure_vertices"], [7759, 7765])
        duplicate_pairs = partition["duplicate_upper_center_vertex_pairs"]
        self.assertEqual(
            [entry["vertices"] for entry in duplicate_pairs],
            [[7256, 7708], [7257, 7711], [7260, 7716]],
        )
        self.assertTrue(
            all(entry["local_distance_m"] == 0.0 for entry in duplicate_pairs)
        )

    def test_front_visibility_disproves_visible_exterior_lip_identity(self) -> None:
        probe = self.evidence["front_visibility_probe"]
        expected = {
            "lower_oral_fissure": (32, 23, 9),
            "upper_oral_fissure": (37, 37, 0),
            "commissures": (4, 4, 0),
            "outer_attachment_rim": (69, 69, 0),
            "open_upper_center_seam": (6, 6, 0),
        }
        for role, (total, occluded, visible) in expected.items():
            measured = probe["by_semantic_role"][role]
            self.assertEqual(measured["vertex_count"], total)
            self.assertEqual(measured["front_occluded_vertex_count"], occluded)
            self.assertEqual(measured["front_visible_vertex_count"], visible)

        self.assertEqual(
            len(probe["unique_nearest_occluding_source_polygon_indices"]), 181
        )
        self.assertEqual(
            len(probe["unique_nearest_occluding_source_vertex_indices"]), 245
        )
        self.assertEqual(
            probe["unique_nearest_occluding_source_vertex_index_sha256"],
            "b351422d30c446d7c1db16ae43965ab3f9bbefeca957903c68c65bdd215e3f45",
        )

    def test_verdict_blocks_cavity_viseme_and_promotion(self) -> None:
        verdict = self.evidence["verdict"]
        self.assertFalse(verdict["defensible_existing_mouth_semantic_map_proven"])
        self.assertFalse(verdict["isolated_cavity_or_viseme_prototype_allowed"])
        self.assertFalse(
            verdict["exact_207_component_confirmed_as_visible_exterior_lips"]
        )
        self.assertIn("hide the 207-vertex backing patch", verdict["smallest_remaining_manual_ambiguity"])
        self.assertEqual(
            self.manifest["status"],
            "inactive_semantic_map_rejected_component_identity_unproven",
        )
        self.assertTrue(all(value is False for value in self.manifest["gates"].values()))

    def test_inactive_review_left_all_guarded_inputs_byte_identical(self) -> None:
        verification = self.evidence["host_verification"]
        self.assertTrue(verification["all_guarded_inputs_byte_unchanged"])
        self.assertEqual(verification["pinned_hashes_before"], EXPECTED_PINNED_HASHES)
        self.assertEqual(verification["pinned_hashes_after"], EXPECTED_PINNED_HASHES)
        self.assertEqual(
            verification["runtime_state_sha256_before"],
            verification["runtime_state_sha256_after"],
        )
        self.assertEqual(sha256_file(WORKSPACE_PATH), EXPECTED_PINNED_HASHES["workspace"])
        self.assertEqual(sha256_file(SOURCE_R6_PATH), EXPECTED_PINNED_HASHES["source_r6"])
        self.assertTrue(all(value is False for value in self.evidence["safety"].values()))

    def test_evidence_and_fixed_renders_match_manifest(self) -> None:
        artifacts = self.manifest["artifacts"]
        self.assertEqual(sha256_file(EVIDENCE_PATH), artifacts["evidence_sha256"])
        render_names = {
            "front_face": "front_face_semantic_overlay.png",
            "front_mouth": "front_mouth_semantic_overlay.png",
            "left_profile": "left_profile_semantic_overlay.png",
            "right_profile": "right_profile_semantic_overlay.png",
            "oblique": "oblique_semantic_overlay.png",
        }
        for key, filename in render_names.items():
            path = PROOF_DIR / "fixed_renders" / filename
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)
            self.assertEqual(
                sha256_file(path), artifacts["fixed_render_sha256"][key]
            )

    def test_tools_contain_no_blend_save_or_model_export_call(self) -> None:
        for path in (WORKER_PATH, LAUNCHER_PATH):
            source = path.read_text(encoding="utf-8")
            for forbidden in (
                "bpy.ops.wm.save",
                "bpy.ops.wm.save_as_mainfile",
                "bpy.ops.export_scene",
                "bpy.ops.wm.open_mainfile",
            ):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
