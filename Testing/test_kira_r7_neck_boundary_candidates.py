from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_neck_boundary_owner_review_20260721"
)
EVIDENCE_PATH = OUTPUT_DIR / "evidence.json"
MANIFEST_PATH = OUTPUT_DIR / "inactive_owner_review_manifest.json"
WORKER_PATH = PROJECT_ROOT / "tools/blender_inspect_kira_r7_neck_boundary_candidates.py"
LAUNCHER_PATH = PROJECT_ROOT / "tools/inspect_kira_r7_neck_boundary_candidates.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7NeckBoundaryCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_pinned_inputs_are_byte_unchanged(self) -> None:
        verification = self.evidence["host_verification"]
        self.assertTrue(verification["all_pinned_inputs_byte_unchanged"])
        self.assertEqual(
            verification["pinned_hashes_before"],
            verification["pinned_hashes_after"],
        )
        for record in self.evidence["sources"].values():
            self.assertEqual(sha256_file(Path(record["path"])), record["sha256"])

    def test_exact_working_mesh_and_shared_half_shells_are_pinned(self) -> None:
        body = self.evidence["working_body"]
        self.assertEqual(body["object"], "Object_85")
        self.assertEqual(body["mesh"], "Cuerpo__0")
        self.assertEqual(body["vertex_count"], 57745)
        self.assertEqual(body["edge_count"], 165776)
        self.assertEqual(body["polygon_count"], 108080)
        self.assertEqual(body["connected_component_count"], 49)
        support = self.evidence["support_analysis"]
        self.assertEqual(
            support["shared_head_neck_spine2_components"],
            ["component_002", "component_003"],
        )

    def test_only_closed_boundaries_are_disqualified_half_shell_perimeters(self) -> None:
        boundary = self.evidence["shared_component_open_boundary_analysis"]
        self.assertEqual(boundary["boundary_edge_count"], 1472)
        self.assertEqual(boundary["connected_boundary_part_count"], 2)
        self.assertEqual(boundary["closed_boundary_cycle_count"], 2)
        self.assertEqual(boundary["defensible_neck_boundary_count"], 0)
        expected_edges = {
            "73998b97a1204977fc646d640b5a748d4f06138052c2b0710c18a9298a173ca3",
            "5176dba974db2c931d8e14d9f4f3f096bfc21ce33624e89332889b46706d7dd8",
        }
        self.assertEqual(
            {record["edge_index_pair_sha256"] for record in boundary["parts"]},
            expected_edges,
        )
        for record in boundary["parts"]:
            self.assertEqual(record["vertex_count"], 736)
            self.assertEqual(record["edge_count"], 736)
            self.assertTrue(record["topologically_closed_cycle"])
            self.assertFalse(record["defensible_neck_boundary"])
            self.assertEqual(
                record["classification"],
                "whole_mirrored_half_shell_perimeter_not_neck_ring",
            )
            self.assertGreater(record["local_bounds"]["size"][2], 1.5)

    def test_lower_neck_search_contains_no_closed_cycle(self) -> None:
        slab = self.evidence["lower_neck_existing_edge_cycle_search"]
        self.assertEqual(slab["local_z_slab"], [5.9, 6.25])
        self.assertEqual(slab["maximum_edge_endpoint_delta_z"], 0.004)
        self.assertEqual(slab["candidate_edge_count"], 612)
        self.assertEqual(slab["connected_part_count"], 141)
        self.assertEqual(slab["topologically_closed_cycle_count"], 0)
        self.assertEqual(
            slab["candidate_edge_index_pair_sha256"],
            "a7128d094079b7a174ab53764c492942f46665501b409f7bd5a95765c458f1d3",
        )
        self.assertFalse(any(part["topologically_closed_cycle"] for part in slab["parts"]))

    def test_no_misleading_paired_trace_was_retained(self) -> None:
        trace = self.evidence["paired_open_review_traces"]
        self.assertEqual(trace["status"], "not_emitted_no_simple_defensible_path")
        self.assertEqual(trace["trace_count"], 0)
        self.assertEqual(
            self.evidence["conclusion"]["defensible_existing_closed_neck_ring_count"],
            0,
        )
        self.assertFalse(
            self.evidence["manual_blender_selection_required"]["automatic_selection_allowed"]
        )

    def test_fixed_multiview_files_match_recorded_hashes(self) -> None:
        views = self.evidence["fixed_multiview_renders"]
        self.assertEqual(set(views), {"front", "left", "back", "right"})
        for name, record in views.items():
            path = Path(record["path"])
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.stat().st_size, record["size_bytes"], name)
            self.assertEqual(sha256_file(path), record["sha256"], name)
            self.assertEqual(record["orthographic_scale"], 0.379999995)

    def test_manifest_is_inactive_and_every_gate_is_closed(self) -> None:
        self.assertEqual(
            self.manifest["status"],
            "inactive_owner_review_required_no_defensible_existing_neck_ring",
        )
        self.assertEqual(
            self.manifest["decision"]["defensible_existing_closed_neck_ring_count"],
            0,
        )
        self.assertTrue(self.manifest["decision"]["manual_blender_selection_required"])
        self.assertTrue(all(value is False for value in self.evidence["gates"].values()))
        self.assertTrue(all(value is False for value in self.evidence["safety"].values()))
        self.assertTrue(all(value is False for value in self.manifest["gates"].values()))
        self.assertTrue(all(value is False for value in self.manifest["safety"].values()))

    def test_inspection_scripts_cannot_save_export_bind_or_activate(self) -> None:
        combined = "\n".join(
            (
                WORKER_PATH.read_text(encoding="utf-8"),
                LAUNCHER_PATH.read_text(encoding="utf-8"),
            )
        )
        for forbidden in (
            "bpy.ops.wm.save",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.export_scene",
            "bpy.ops.wm.open_mainfile",
            "runtime_binding",
            "avatar_builder_binding",
            "activate_ai",
        ):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
