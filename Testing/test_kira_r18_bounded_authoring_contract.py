"""Static fail-closed checks for the Blender-only Kira R18 worker."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_author_kira_r18_bounded_bald_candidate.py"
PLAN = (
    ROOT
    / "RecoverySprint/continuation_20260802/"
    "kira_r18_bounded_bald_authoring_preparation/AUTHORING_PLAN.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KiraR18BoundedAuthoringContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = WORKER.read_text(encoding="utf-8")
        self.plan = json.loads(PLAN.read_text(encoding="utf-8-sig"))

    def test_exact_frozen_source_and_plan_are_bound(self) -> None:
        self.assertEqual(
            self.plan["source"]["r17_blend_sha256"],
            "7f7a6519ee5902fb01b247add864a4f41f4be6e600ab917cc5195ca9ea21e493",
        )
        self.assertIn("R17_BLEND_SHA256", self.source)
        self.assertIn("validate_sources(PROJECT_ROOT)", self.source)
        self.assertIn(
            'PLAN_SHA256 = "0cda2366af4a0c440be805dcb1045dadfd5912335c2efe704fae25d4a05a1453"',
            self.source,
        )
        self.assertEqual(
            sha256(PLAN),
            "0cda2366af4a0c440be805dcb1045dadfd5912335c2efe704fae25d4a05a1453",
        )

    def test_worker_has_no_runtime_export_or_activation_operation(self) -> None:
        forbidden = (
            "bpy.ops.export",
            "bpy.ops.wm.save_as_mainfile(filepath=str(source)",
            "register_avatar",
            "activate_avatar",
            "publish_avatar",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)
        self.assertEqual(self.source.count("bpy.ops.wm.save_as_mainfile"), 1)

    def test_failure_evidence_cannot_modify_a_preexisting_attempt_or_package(self) -> None:
        self.assertIn("output_existed_before = requested_output.exists()", self.source)
        self.assertIn("and not output_existed_before", self.source)
        self.assertIn('f"attempt_{number:02d}"', self.source)
        self.assertIn("for number in (1, 2, 3, 4)", self.source)
        self.assertIn("output.name.startswith(DELIVERY_PREFIX)", self.source)

    def test_immutable_attribute_digest_handles_array_values_fail_closed(self) -> None:
        self.assertIn("values = tuple(value)", self.source)
        self.assertIn('return b"a" + struct.pack("<Q", len(values))', self.source)
        self.assertIn("unsupported mesh attribute value type", self.source)
        self.assertIn("unsupported mesh attribute data item", self.source)

    def test_blender_51_layered_actions_remain_in_immutable_digest(self) -> None:
        self.assertIn('action_row["storage"] = "layered"', self.source)
        self.assertIn("strip.channelbags", self.source)
        self.assertIn("channelbag.fcurves", self.source)
        self.assertNotIn("masks._action_digest()", self.source)

    def test_mechanical_attempts_do_not_consume_visual_repair_count(self) -> None:
        self.assertIn("append_only_execution_attempt", self.source)
        self.assertIn("bounded_surface_attempt", self.source)
        self.assertIn("PRESERVED_MECHANICAL_PRE_AUTHORING_FAILURES", self.source)
        self.assertIn("int(args.attempt_number) - 2", self.source)

    def test_local_surface_transfer_is_not_index_graft_or_global_nearest(self) -> None:
        self.assertIn(
            "restricted_named_anatomical_subchart_barycentric_transfer_v1",
            self.source,
        )
        self.assertIn('"direct_index_graft_used": False', self.source)
        self.assertIn('"global_nearest_neighbor_used": False', self.source)
        self.assertIn('"donor_vertex_indices_copied": False', self.source)
        self.assertIn("P1_BOUNDARY", self.source)
        self.assertIn('"collision_safe_backoff"', self.source)
        self.assertIn("remaining_new_pairs = iteration_pairs.difference", self.source)
        self.assertIn("did not reach zero new pairs", self.source)

    def test_full_review_and_truth_boundary_are_present(self) -> None:
        for label in (
            "brows_close",
            "diagnostic_medical_external_view",
            "toilet_seated_diagnostic_contact",
        ):
            self.assertIn(label, self.source)
        self.assertIn('for degrees in (30, 55, 80)', self.source)
        self.assertIn('f"{side_name}_knee_bend_{degrees}deg"', self.source)
        self.assertIn('f"bilateral_knee_bend_{degrees}deg"', self.source)
        self.assertIn('"bathroom_function_implemented_or_claimed": False', self.source)
        self.assertIn('"pregnancy_or_reproductive_function_implemented_or_claimed": False', self.source)
        self.assertIn('"runtime_exported": False', self.source)

    def test_all_exact_preflight_masks_are_named(self) -> None:
        for mask_name in ("P1", "S", "K_L", "K_R", "F1", "F2", "H_L", "H_R", "T_L", "T_R"):
            self.assertIn(f'"{mask_name}"', self.source)
        self.assertIn('"lower_lip_natural_volume": -0.08', self.source)
        self.assertIn('"lower_lip_weight_before": 0.20', self.source)
        self.assertIn('"lower_lip_weight_after": 0.12', self.source)


if __name__ == "__main__":
    unittest.main()
