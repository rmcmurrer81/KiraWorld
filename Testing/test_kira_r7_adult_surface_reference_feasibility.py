import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7"
    / "adult_reference_feasibility_20260721_v2"
)
EVIDENCE = RUN / "feasibility_evidence.json"
SUMMARY = RUN / "run_summary.json"
KIRA = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
REFERENCE = Path(r"C:\Users\robmc\Desktop\5\base_female_character.glb")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7AdultSurfaceReferenceFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    def test_sources_are_exact_and_unchanged(self) -> None:
        self.assertEqual(
            sha256(KIRA),
            "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
        )
        self.assertEqual(
            sha256(REFERENCE),
            "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df",
        )
        self.assertTrue(
            self.evidence["host_verification"]["all_sources_byte_unchanged"]
        )

    def test_reference_provenance_and_role_are_bounded(self) -> None:
        reference = self.evidence["sources"]["adult_reference"]
        self.assertEqual(
            reference["provenance"]["license"],
            "CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)",
        )
        self.assertIn("BlackProject", reference["provenance"]["author"])
        self.assertEqual(
            reference["permitted_role"],
            "proportion_and_construction_reference_only",
        )

    def test_structural_mismatch_blocks_automatic_transfer(self) -> None:
        self.assertEqual(self.evidence["kira"]["mesh_count"], 1)
        self.assertEqual(self.evidence["adult_reference"]["mesh_count"], 28)
        self.assertEqual(self.evidence["correspondence"]["kira_bone_count"], 79)
        self.assertEqual(
            self.evidence["correspondence"]["reference_bone_count"], 188
        )
        self.assertEqual(self.evidence["correspondence"]["common_bone_count"], 1)
        self.assertFalse(self.evidence["correspondence"]["exact_skeleton_match"])
        self.assertFalse(
            self.evidence["correspondence"]["reviewed_vertex_or_surface_map_present"]
        )
        self.assertFalse(
            self.evidence["gates"]["automatic_geometry_transfer_allowed"]
        )

    def test_no_candidate_or_live_change_was_made(self) -> None:
        safety = self.evidence["safety"]
        self.assertFalse(safety["geometry_transfer_applied"])
        self.assertFalse(safety["modifiers_added"])
        self.assertFalse(safety["shape_keys_added"])
        self.assertFalse(safety["weights_changed"])
        self.assertFalse(safety["materials_or_textures_copied"])
        self.assertFalse(safety["candidate_glb_exported"])
        self.assertFalse(safety["runtime_binding_touched"])
        self.assertFalse(safety["avatar_builder_binding_touched"])
        self.assertFalse(safety["home_world_touched"])
        self.assertFalse(list(RUN.glob("*.glb")))
        self.assertTrue((RUN / "kira_r7_adult_reference_feasibility.blend").is_file())

    def test_truth_status_does_not_claim_adult_completion(self) -> None:
        self.assertFalse(
            self.evidence["decision"]["genuinely_different_adult_surface_created"]
        )
        self.assertFalse(self.evidence["gates"]["complete_adult_anatomy_proven"])
        self.assertFalse(
            self.evidence["gates"]["stable_79_joint_deformation_proven"]
        )
        self.assertFalse(self.evidence["gates"]["candidate_export_allowed"])
        self.assertFalse(self.evidence["gates"]["runtime_activation_allowed"])
        self.assertFalse(self.evidence["gates"]["autobuild_allowed"])
        self.assertEqual(
            self.summary["status"],
            "inactive_reference_workspace_prepared_automatic_transfer_blocked",
        )


if __name__ == "__main__":
    unittest.main()
