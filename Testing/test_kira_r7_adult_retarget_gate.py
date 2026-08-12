from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = (
    ROOT
    / "Data"
    / "avatar_builder_workspace_tests"
    / "kira_r7_adult_retarget_gate_20260721"
)
EVIDENCE_PATH = EVIDENCE_DIR / "evidence.json"
MANIFEST_PATH = EVIDENCE_DIR / "manifest.json"

EXPECTED_KIRA_SHA256 = (
    "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77"
)
EXPECTED_REFERENCE_SHA256 = (
    "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
)
EXPECTED_STATUS = (
    "blocked_retarget_rest_shape_collapsed_and_no_identity_neck_seam_no_candidate"
)
EXPECTED_RENDERS = {
    "uniform_fit_reference_front.png",
    "uniform_fit_reference_side.png",
    "retarget_rest_same_scale_comparison.png",
    "retarget_rest_front.png",
    "retarget_rest_side.png",
    "retarget_upper_limb.png",
    "retarget_hip_knee.png",
    "retarget_spine.png",
}


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7AdultRetargetGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = load_json(EVIDENCE_PATH)
        cls.manifest = load_json(MANIFEST_PATH)

    def test_pinned_inputs_remain_byte_identical(self) -> None:
        sources = self.evidence["sources"]
        host = self.evidence["host_verification"]

        self.assertEqual(sources["kira_r6"]["sha256"], EXPECTED_KIRA_SHA256)
        self.assertEqual(
            sources["adult_reference"]["sha256"], EXPECTED_REFERENCE_SHA256
        )
        self.assertEqual(
            sha256_file(Path(sources["kira_r6"]["path"])), EXPECTED_KIRA_SHA256
        )
        self.assertEqual(
            sha256_file(Path(sources["adult_reference"]["path"])),
            EXPECTED_REFERENCE_SHA256,
        )
        self.assertEqual(host["pinned_hashes_before"], host["pinned_hashes_after"])
        self.assertIs(host["all_pinned_inputs_byte_unchanged"], True)

    def test_static_body_selection_is_fragmented_and_identity_meshes_are_excluded(
        self,
    ) -> None:
        topology = self.evidence["static_topology_inspection"]
        selected = {item["mesh"] for item in topology["included_body_meshes"]}

        self.assertEqual(
            selected,
            {
                "Ariel_Mesh_Torso_0",
                "Ariel_Mesh_Arms_0",
                "Ariel_Mesh_Legs_0",
                "Ariel_Mesh_Fingernails_0",
                "Ariel_Mesh_Toenails_0",
                "Ariel_Mesh_Genitalia_0",
            },
        )
        self.assertEqual(topology["included_mesh_count"], 6)
        self.assertEqual(topology["included_vertex_total"], 13216)
        self.assertEqual(topology["included_polygon_total"], 23908)
        self.assertIs(topology["cohesive_single_surface"], False)
        self.assertGreaterEqual(len(topology["identity_bearing_meshes_excluded"]), 20)
        self.assertIs(self.evidence["retarget_trial"]["identity_meshes_copied"], False)
        self.assertIs(
            self.evidence["retarget_trial"]["source_materials_or_textures_copied"],
            False,
        )

    def test_reference_torso_does_not_supply_a_defensible_identity_boundary(
        self,
    ) -> None:
        records = {
            item["source_mesh"]: item
            for item in self.evidence["retarget_trial"]["major_body_mapping_records"]
        }
        torso_unmapped = set(
            records["Ariel_Mesh_Torso_0"]["unmapped_positive_source_groups"]
        )

        for group in (
            "BelowJaw_0115",
            "lowerJaw_093",
            "lEar_0167",
            "rEar_0168",
            "lJawClench_0116",
            "rJawClench_0117",
        ):
            self.assertIn(group, torso_unmapped)
        self.assertEqual(
            self.evidence["neck_boundary_blocker"][
                "defensible_existing_closed_neck_ring_count"
            ],
            0,
        )
        self.assertEqual(
            self.evidence["neck_boundary_blocker"]["lower_neck_closed_cycles"], 0
        )

    def test_automatic_mapping_reaches_vertices_but_destroys_rest_shape(self) -> None:
        summary = self.evidence["retarget_trial"]["summary"]
        decision = self.evidence["decision"]

        self.assertEqual(summary["vertex_count"], 13216)
        self.assertEqual(summary["mapped_vertex_count"], 13216)
        self.assertEqual(summary["mapped_vertex_fraction"], 1.0)
        self.assertGreater(summary["mapped_weight_mass_fraction"], 0.99)
        self.assertLess(summary["mapped_weight_mass_fraction"], 1.0)
        self.assertGreater(
            self.evidence["retarget_trial"]["maximum_joint_head_correction_m"],
            0.68,
        )
        self.assertIs(summary["rest_shape_gate_passed"], False)
        self.assertEqual(
            set(summary["rest_shape_collapse_detected_on_meshes"]),
            {
                "Ariel_Mesh_Arms_0",
                "Ariel_Mesh_Genitalia_0",
                "Ariel_Mesh_Legs_0",
                "Ariel_Mesh_Torso_0",
            },
        )
        self.assertEqual(
            set(summary["severe_rest_displacement_detected_on_meshes"]),
            {
                "Ariel_Mesh_Arms_0",
                "Ariel_Mesh_Fingernails_0",
                "Ariel_Mesh_Genitalia_0",
                "Ariel_Mesh_Legs_0",
                "Ariel_Mesh_Toenails_0",
                "Ariel_Mesh_Torso_0",
            },
        )
        self.assertEqual(decision["status"], EXPECTED_STATUS)
        self.assertIs(decision["valid_avatar_candidate_authored"], False)
        self.assertIs(decision["candidate_glb_created"], False)

    def test_pose_response_does_not_unlock_stability_gate(self) -> None:
        poses = self.evidence["deformation_evidence"]
        for pose_name in ("upper_limb", "hip_knee", "spine"):
            self.assertIs(poses[pose_name]["metrics"]["all_coordinates_finite"], True)

        self.assertGreater(
            poses["upper_limb"]["metrics"]["region_centroid_displacement_m"][
                "left_forearm_hand"
            ],
            0.20,
        )
        self.assertGreater(
            poses["hip_knee"]["metrics"]["region_centroid_displacement_m"][
                "left_lower_leg_foot"
            ],
            0.18,
        )
        self.assertGreater(
            poses["spine"]["metrics"]["region_centroid_displacement_m"][
                "upper_torso"
            ],
            0.005,
        )
        self.assertIs(
            self.evidence["gates"]["stable_79_joint_deformation_proven"], False
        )

    def test_no_candidate_or_live_binding_was_created(self) -> None:
        gates = self.evidence["gates"]
        safety = self.evidence["safety"]

        self.assertTrue(all(value is False for value in gates.values()))
        self.assertTrue(all(value is False for value in safety.values()))
        self.assertFalse(list(EVIDENCE_DIR.glob("*.glb")))
        self.assertTrue((EVIDENCE_DIR / "inactive_retarget_diagnostic.blend").is_file())
        self.assertEqual(self.manifest["status"], EXPECTED_STATUS)
        self.assertIs(self.manifest["candidate_glb_created"], False)
        self.assertIs(self.manifest["avatar_builder_binding_allowed"], False)
        self.assertIs(self.manifest["runtime_activation_allowed"], False)

    def test_fixed_review_renders_are_present_and_hashed(self) -> None:
        artifacts = self.evidence["host_verification"]["artifacts"]

        self.assertTrue(EXPECTED_RENDERS.issubset(artifacts))
        for name in EXPECTED_RENDERS:
            path = EVIDENCE_DIR / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 100_000, name)
            self.assertEqual(sha256_file(path), artifacts[name]["sha256"], name)


if __name__ == "__main__":
    unittest.main()
