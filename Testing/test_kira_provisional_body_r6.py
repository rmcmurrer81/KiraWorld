from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_provisional_body_r6"
)
SOURCE = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "base_body_reference"
    / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
)
LIVE = ROOT / "Avatar" / "models" / "temp_ai" / "kira" / "avatar.glb"
ENROLLED_SHA = "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def latest_passing_run() -> tuple[Path, dict[str, object]]:
    for run_dir in sorted(RUN_ROOT.glob("r6_*"), reverse=True):
        summary_path = run_dir / "run_summary.json"
        if not summary_path.is_file():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("adult_external_form_materially_advanced") is True:
            return run_dir, summary
    raise AssertionError("no passing private R6 run summary exists")


class KiraProvisionalBodyR6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir, cls.summary = latest_passing_run()
        cls.candidate = cls.run_dir / "kira_provisional_body_r6.glb"
        cls.manifest = json.loads(
            (cls.run_dir / "kira_provisional_body_r6_manifest.json").read_text(encoding="utf-8")
        )
        cls.compatibility = json.loads(
            (cls.run_dir / "exact_candidate_compatibility_audit.json").read_text(encoding="utf-8")
        )

    def test_live_and_enrolled_source_are_unchanged(self) -> None:
        self.assertEqual(sha256_file(SOURCE), ENROLLED_SHA)
        self.assertEqual(sha256_file(LIVE), ENROLLED_SHA)
        self.assertTrue(self.summary["source_unchanged"])
        self.assertTrue(self.summary["live_model_unchanged"])

    def test_exact_candidate_is_private_inactive_and_hash_bound(self) -> None:
        self.assertTrue(self.candidate.is_file())
        candidate_sha = sha256_file(self.candidate)
        self.assertEqual(candidate_sha, self.summary["candidate_sha256"])
        self.assertEqual(candidate_sha, self.manifest["exact_hash_guards"]["candidate_sha256"])
        self.assertNotEqual(candidate_sha, ENROLLED_SHA)
        self.assertEqual(self.manifest["status"], "private_inactive_reversible_review_candidate")
        self.assertFalse(self.manifest["privacy_and_activation"]["runtime_activation_allowed"])
        self.assertFalse(self.manifest["privacy_and_activation"]["owner_approved"])
        self.assertFalse(self.manifest["autobuild_gate"]["passed"])

    def test_body_form_advanced_but_anatomy_is_not_overclaimed(self) -> None:
        form = self.manifest["adult_external_form"]
        regions = form["region_vertex_visits"]
        self.assertGreater(regions["adult_breast_surface_left"], 0)
        self.assertGreater(regions["adult_breast_surface_right"], 0)
        self.assertGreater(regions["adult_external_pelvic_surface"], 0)
        self.assertTrue(form["doll_safe_external_body_limitation"]["undifferentiated_surface_reduced"])
        self.assertFalse(form["doll_safe_external_body_limitation"]["removal_or_completeness_proven"])
        self.assertFalse(form["anatomical_completeness_claimed"])
        self.assertFalse(self.compatibility["gates"]["anatomical_completeness_proven"])

    def test_exact_rig_topology_head_and_mouth_are_preserved(self) -> None:
        structural = self.compatibility["structural_preservation"]
        deformation = self.compatibility["deformation_regions"]
        self.assertTrue(structural["topology_preserved_after_fresh_import"])
        self.assertTrue(structural["vertex_group_names_and_order_preserved"])
        self.assertTrue(structural["bone_names_and_order_preserved"])
        self.assertEqual(structural["bone_count"], 79)
        self.assertTrue(structural["bone_rest_matrices_preserved_within_2e_5"])
        self.assertTrue(deformation["protected_head"]["exact_within_tolerance"])
        self.assertEqual(deformation["protected_head"]["moved_vertex_count_over_tolerance"], 0)
        self.assertTrue(deformation["protected_existing_mouth_surface"]["exact_within_tolerance"])
        self.assertEqual(
            deformation["protected_existing_mouth_surface"]["moved_vertex_count_over_tolerance"],
            0,
        )
        self.assertFalse(self.manifest["existing_mouth_contract"]["second_mouth_mesh_created"])

    def test_eye_and_lip_sync_are_structurally_supported_not_runtime_proven(self) -> None:
        eye = self.compatibility["staged_eye_rig_compatibility"]
        mouth = self.compatibility["existing_mouth_lip_sync_compatibility"]
        self.assertTrue(eye["structural_reuse_supported"])
        self.assertFalse(eye["assembled_fit_on_exact_candidate_proven"])
        self.assertFalse(eye["runtime_eye_behavior_proven"])
        self.assertTrue(mouth["structural_compatibility_supported"])
        self.assertFalse(mouth["runtime_lip_sync_playback_on_exact_candidate_proven"])
        self.assertFalse(self.compatibility["gates"]["runtime_activation_allowed"])

    def test_references_remain_study_only_and_renders_remain_covered(self) -> None:
        study = self.manifest["adult_anatomy_study_evidence"]
        self.assertFalse(study["reference_geometry_imported_or_copied"])
        self.assertEqual(len(study["selected_references"]), 4)
        self.assertTrue(all(not item["geometry_imported_or_copied"] for item in study["selected_references"]))
        self.assertFalse(self.manifest["privacy_and_activation"]["retained_uncovered_or_intimate_renders"])
        contact = self.manifest["covered_contact_sheet"]
        self.assertFalse(contact["contains_uncovered_or_intimate_view"])
        self.assertEqual(sha256_file(Path(contact["path"])), contact["sha256"])


if __name__ == "__main__":
    unittest.main()
