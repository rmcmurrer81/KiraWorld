from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.avatar_body_topology import inspect_glb_topology  # noqa: E402
from Core.avatar_multiview_owner_review import (  # noqa: E402
    _load_audited_base_catalog,
)
from Core.avatar_two_subject_autobuild_gate import (  # noqa: E402
    evaluate_two_subject_autobuild_gate,
)


PREFLIGHT = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/single_avatar_quality_attempt_20260717/source_preflight.json"
)
BASE = (
    ROOT
    / "Avatar/avatar_builder/asset_library/base_body_reference/womenfemale_body_base_rigged_3ec62ba8d7.glb"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class AvatarSingleCandidateQualityPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))

    def test_attempt_stops_without_fabricating_a_candidate_or_approval(self) -> None:
        self.assertEqual(
            self.preflight["result"],
            "blocked_before_generation_no_defensible_candidate_source_package",
        )
        for field in (
            "candidate_created",
            "candidate_called_perfect",
            "candidate_called_approved",
            "private_review_created",
            "live_body_replaced",
            "runtime_activation_allowed",
            "public_export_allowed",
            "auto_build_release_allowed",
        ):
            self.assertFalse(self.preflight[field], field)

    def test_selected_3ec_base_is_exact_and_structurally_ready_only(self) -> None:
        source = self.preflight["screened_sources"][0]
        self.assertEqual(source["sha256"], sha256(BASE))
        report = inspect_glb_topology(BASE, artifact_id="single_quality_base")

        self.assertTrue(report["valid_glb"])
        self.assertTrue(report["humanoid_rig_structurally_ready"])
        self.assertEqual(report["canonical_rig_evidence"]["missing_core_roles"], [])
        self.assertFalse(report["stable_working_rig_proven"])
        self.assertFalse(report["anatomical_completeness_proven"])
        self.assertEqual(report["topology_metrics"]["animation_count"], 0)

    def test_3ec_is_audited_new_surface_cage_not_a_copyable_avatar(self) -> None:
        public, options = _load_audited_base_catalog(
            ROOT, "confirmed_adult_topology"
        )
        base_id = "adult_female_body_base_rigged_3ec62ba8d7"

        self.assertEqual(public["status"], "ready")
        self.assertIn(base_id, options)
        option = options[base_id]
        self.assertFalse(option["copy_as_candidate_body_allowed"])
        self.assertTrue(
            option["structural_proof"]["humanoid_rig_structurally_ready"]
        )
        self.assertFalse(option["structural_proof"]["stable_working_rig_proven"])
        self.assertFalse(
            option["structural_proof"]["anatomical_completeness_proven"]
        )

    def test_beth_and_elsa_blockers_remain_exact_audit_bound(self) -> None:
        by_id = {
            item["source_id"]: item for item in self.preflight["screened_sources"]
        }
        beth = by_id["beth_smith_owner_supplied_reference"]
        elsa = by_id["elsa_frozen_adventures_owner_reference"]

        for source in (beth, elsa):
            binding = source["audit_binding"]
            path = ROOT / binding["path"]
            self.assertEqual(binding["sha256"], sha256(path))

        self.assertEqual(beth["objective_structure"]["skin_count"], 0)
        self.assertFalse(
            beth["objective_structure"]["humanoid_rig_structurally_ready"]
        )
        self.assertFalse(
            elsa["objective_structure"]["complete_body_under_outfit"]
        )

    def test_known_bad_eye_and_garment_methods_are_explicitly_rejected(self) -> None:
        rejected = set(self.preflight["generation_methods_rejected_for_this_attempt"])
        self.assertTrue(
            {
                "procedural_eye_caps",
                "threshold_cut_body_surface_clothing",
                "body_surface_shell_garments",
                "primitive_slab_or_box_garments",
                "primitive_box_shoes",
            }.issubset(rejected)
        )

    def test_authoritative_two_subject_gate_stays_locked_at_zero(self) -> None:
        result = evaluate_two_subject_autobuild_gate(ROOT)

        self.assertEqual(
            result["status"], "locked_awaiting_two_distinct_owner_approved_bodies"
        )
        self.assertEqual(result["qualified_body_count"], 0)
        self.assertFalse(result["batch_auto_authoring_allowed"])


if __name__ == "__main__":
    unittest.main()
