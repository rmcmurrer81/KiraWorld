from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_face_authoring_boundary_20260721/evidence.json"
)
WORKER_PATH = PROJECT_ROOT / "tools/blender_inspect_kira_r7_face_authoring_boundary.py"
LAUNCHER_PATH = PROJECT_ROOT / "tools/inspect_kira_r7_face_authoring_boundary.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7FaceAuthoringBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_inspection_is_pinned_to_unchanged_inactive_inputs(self) -> None:
        verification = self.evidence["host_verification"]
        self.assertTrue(verification["all_pinned_inputs_byte_unchanged"])
        self.assertEqual(
            verification["pinned_hashes_before"],
            verification["pinned_hashes_after"],
        )
        for name, record in self.evidence["sources"].items():
            self.assertEqual(sha256_file(Path(record["path"])), record["sha256"], name)

    def test_exact_r6_has_one_deterministic_207_vertex_lip_island_candidate(self) -> None:
        mouth = self.evidence["existing_single_mouth_surface"]
        self.assertEqual(mouth["runtime_cross_reference_vertex_count"], 207)
        self.assertEqual(mouth["matching_connected_component_count"], 1)
        self.assertTrue(mouth["deterministic_on_exact_pinned_r6"])
        candidate = mouth["unique_topology_island_candidate"]
        self.assertEqual(candidate["vertex_count"], 207)
        self.assertEqual(
            candidate["vertex_index_sha256"],
            "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b",
        )
        self.assertFalse(mouth["second_mouth_created"])

    def test_connectivity_cannot_supply_a_semantic_head_neck_cut(self) -> None:
        boundary = self.evidence["head_neck_boundary"]
        self.assertTrue(boundary["head_neck_torso_welded_in_same_component"])
        self.assertTrue(boundary["components_with_head_neck_and_upper_torso_support"])
        self.assertFalse(boundary["closed_neck_boundary_loop_semantically_labeled"])
        self.assertFalse(boundary["automatic_boundary_selection_proven"])
        for group in (
            "mixamorig:Head_06",
            "mixamorig:Neck_05",
            "mixamorig:Spine2_04",
        ):
            self.assertGreater(boundary["support_groups"][group]["vertex_count"], 0)

    def test_workspace_has_no_reviewed_face_animation_controls(self) -> None:
        face = self.evidence["face_animation_capability"]
        self.assertEqual(face["facial_shape_keys"], [])
        self.assertEqual(face["facial_bones"], [])
        self.assertFalse(face["reviewed_viseme_or_jaw_control_present"])
        self.assertFalse(face["real_lip_sync_ready"])

    def test_eye_rig_is_separate_and_socket_lid_fit_is_not_proven(self) -> None:
        eyes = self.evidence["eye_fit_capability"]
        self.assertTrue(eyes["staged_eye_rig_exists_as_separate_pinned_asset"])
        self.assertFalse(eyes["eye_rig_appended_to_workspace"])
        self.assertFalse(eyes["eyelid_socket_vertex_masks_present"])
        self.assertFalse(eyes["exact_eye_fit_proven"])

    def test_masks_remain_empty_and_every_promotion_gate_stays_closed(self) -> None:
        semantic = self.evidence["current_semantic_masks"]
        self.assertTrue(semantic["all_empty"])
        for record in semantic["masks"].values():
            self.assertTrue(record["present"])
            self.assertEqual(record["nonzero_vertex_count"], 0)
        self.assertTrue(all(value is False for value in self.evidence["gates"].values()))
        self.assertFalse(self.evidence["next_manual_operation"]["automatic_selection_allowed"])

    def test_worker_contains_no_blend_save_or_model_export_call(self) -> None:
        worker = WORKER_PATH.read_text(encoding="utf-8")
        launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "bpy.ops.wm.save",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.export_scene",
            "bpy.ops.wm.open_mainfile",
        ):
            self.assertNotIn(forbidden, worker)
            self.assertNotIn(forbidden, launcher)
        safety = self.evidence["safety"]
        self.assertTrue(all(value is False for value in safety.values()))


if __name__ == "__main__":
    unittest.main()
