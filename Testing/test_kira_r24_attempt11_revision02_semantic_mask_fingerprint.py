from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from Core.kira_r24_semantic_mask_fingerprint import (
    MAX_ABSOLUTE_T_DELTA,
    compare_semantic_masks,
    semantic_mask_projection,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
)
REVISION01_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt10_revision01.py"
)
REVISION02_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt11_revision02.py"
)
SEMANTIC_HELPER = ROOT / "Core" / "kira_r24_semantic_mask_fingerprint.py"

BOUND_SHA256 = {
    SEMANTIC_HELPER: "c68d4121dcdce8ef28cbb04e48708984591569c70a9a70fb4c3565f66a4118e5",
    REVISION01_WORKER: "f36f08ee29652fccac3b626cc821f5d8cb6c36584a7441f129b67a65b051dfd9",
    EVIDENCE_ROOT
    / "attempt_09"
    / "PRE_MASK_DIAGNOSTIC.json": "0b881a0e16330c373f9b880f9257e5662d4129a52ce730201bcd5d9fcd93037b",
    EVIDENCE_ROOT
    / "attempt_09"
    / "PRE_CAP_DIAGNOSTIC.json": "790e3569b26329604636cbda44e820ecc6df4ac87a4fb9f6d79a9a253cc21dca",
    EVIDENCE_ROOT
    / "attempt_09"
    / "SOLVER_DIAGNOSTIC.json": "f23b84bc59b83a0cc5c619d58b361f7fdef988a34a1aa6c6c4e737149185c4a3",
    EVIDENCE_ROOT
    / "attempt_09"
    / "FAILURE.json": "5e98ca12e2d7123aa7b91acfec3f56955afa70a0801ccc93a50550dbe7963374",
    EVIDENCE_ROOT
    / "attempt_10"
    / "PRE_MASK_DIAGNOSTIC.json": "ddd040e808f38e16436148c5b82365aa6c441b32751a078578a4d897fd92fe9a",
    EVIDENCE_ROOT
    / "attempt_10"
    / "PRE_CAP_DIAGNOSTIC.json": "d7e77ed0dde9b08baba1d99cbdca8dc3ec39e2ded0d2f24092e78099c101536b",
    EVIDENCE_ROOT
    / "attempt_10"
    / "FAILURE.json": "ec66ea06c7b16545714b85725a136f427faf7859cf9e5cb14bf3daf4d82e7355",
}
EXPECTED_SEMANTIC_SHA256 = (
    "3b6f8c7fd085396deba9ce54c537d610cb1679f33b41724b1494f29a0c81f4c5"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R24Revision02SemanticMaskFingerprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.attempt09_masks = load_json(
            EVIDENCE_ROOT / "attempt_09" / "PRE_CAP_DIAGNOSTIC.json"
        )["masks"]
        cls.attempt10_masks = load_json(
            EVIDENCE_ROOT / "attempt_10" / "PRE_MASK_DIAGNOSTIC.json"
        )["masks"]

    def test_inherited_full_hash_drift_has_exact_semantic_fingerprint(self) -> None:
        self.assertNotEqual(
            self.attempt09_masks["canonical_sha256"],
            self.attempt10_masks["canonical_sha256"],
        )
        result = compare_semantic_masks(self.attempt09_masks, self.attempt10_masks)
        self.assertTrue(result["passed"], result["semantic_mismatches"][:3])
        self.assertEqual(
            result["reference_semantic_sha256"], EXPECTED_SEMANTIC_SHA256
        )
        self.assertEqual(
            result["observed_semantic_sha256"], EXPECTED_SEMANTIC_SHA256
        )
        self.assertTrue(result["checks"]["t_identity_sets_aligned_exactly"])
        self.assertTrue(result["checks"]["t_reference_identities_have_no_duplicates"])
        self.assertTrue(result["checks"]["t_observed_identities_have_no_duplicates"])
        self.assertTrue(result["checks"]["t_maximum_absolute_delta_within_gate"])
        self.assertLess(
            result["t_deltas"]["maximum_absolute_delta_t"], MAX_ABSOLUTE_T_DELTA
        )
        projection_text = json.dumps(semantic_mask_projection(self.attempt10_masks))
        self.assertNotIn('"t"', projection_text)
        self.assertNotIn("canonical_sha256", projection_text)

    def test_t_only_drift_within_bound_passes_but_meaningful_drift_fails(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        record = observed["vertex_masks"]["BOUNDARY_ZERO"]["records"][0]
        record["t"] += 1.0e-07
        result = compare_semantic_masks(self.attempt10_masks, observed)
        self.assertTrue(result["passed"])
        self.assertEqual(
            result["reference_semantic_sha256"],
            result["observed_semantic_sha256"],
        )
        self.assertEqual(
            result["t_deltas"]["acceptance_role"],
            "BOUNDED_STABILITY_GATE_FOR_RELIEF_INPUT",
        )
        self.assertEqual(result["t_deltas"]["changed_count"], 1)
        self.assertLess(result["t_deltas"]["maximum_absolute_delta_t"], MAX_ABSOLUTE_T_DELTA)

        meaningful = deepcopy(self.attempt10_masks)
        meaningful["vertex_masks"]["BOUNDARY_ZERO"]["records"][0]["t"] += 0.125
        rejected = compare_semantic_masks(self.attempt10_masks, meaningful)
        self.assertFalse(rejected["passed"])
        self.assertTrue(rejected["checks"]["semantic_projection_exact"])
        self.assertFalse(rejected["checks"]["t_maximum_absolute_delta_within_gate"])
        self.assertAlmostEqual(rejected["t_deltas"]["maximum_absolute_delta_t"], 0.125)

    def test_membership_drift_is_rejected(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        mask = observed["vertex_masks"]["CENTRAL_POSITIVE_RELIEF"]
        mask["records"].pop()
        mask["count"] -= 1
        result = compare_semantic_masks(self.attempt10_masks, observed)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["t_identity_sets_aligned_exactly"])
        self.assertTrue(
            any("CENTRAL_POSITIVE_RELIEF" in item["path"] for item in result["semantic_mismatches"])
        )

    def test_stable_u_drift_is_rejected_exactly(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        record = observed["vertex_masks"]["BOUNDARY_ZERO"]["records"][0]
        record["u"] += 1.0e-12
        result = compare_semantic_masks(self.attempt10_masks, observed)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any(item["path"].endswith(".u") for item in result["semantic_mismatches"])
        )

    def test_duplicate_t_identity_is_rejected(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        mask = observed["vertex_masks"]["BOUNDARY_ZERO"]
        mask["records"].append(deepcopy(mask["records"][0]))
        mask["count"] += 1
        result = compare_semantic_masks(self.attempt10_masks, observed)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["t_observed_identities_have_no_duplicates"])
        self.assertEqual(len(result["t_deltas"]["observed_duplicate_identities"]), 1)

    def test_unknown_top_level_field_fails_closed(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        observed["future_unreviewed_field"] = True
        with self.assertRaisesRegex(ValueError, r"masks fields must be exact.*unknown"):
            compare_semantic_masks(self.attempt10_masks, observed)

    def test_unknown_vertex_fields_fail_closed(self) -> None:
        cases = []
        unknown_mask = deepcopy(self.attempt10_masks)
        unknown_mask["vertex_masks"]["BOUNDARY_ZERO"]["future_field"] = True
        cases.append(unknown_mask)
        unknown_record = deepcopy(self.attempt10_masks)
        unknown_record["vertex_masks"]["BOUNDARY_ZERO"]["records"][0][
            "future_field"
        ] = True
        cases.append(unknown_record)
        for observed in cases:
            with self.subTest():
                with self.assertRaisesRegex(ValueError, r"fields must be exact.*unknown"):
                    compare_semantic_masks(self.attempt10_masks, observed)

    def test_unknown_edge_field_fails_closed(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        observed["edge_masks"]["SUPERIOR_JOIN_EDGES"]["future_field"] = True
        with self.assertRaisesRegex(ValueError, r"fields must be exact.*unknown"):
            compare_semantic_masks(self.attempt10_masks, observed)

    def test_unknown_binding_gate_and_overlap_fields_fail_closed(self) -> None:
        cases = []
        unknown_binding = deepcopy(self.attempt10_masks)
        unknown_binding["severe_subset_bindings"][0]["future_field"] = True
        cases.append(unknown_binding)
        unknown_gate = deepcopy(self.attempt10_masks)
        unknown_gate["severe_subset_gates"]["future_field"] = True
        cases.append(unknown_gate)
        unknown_overlap = deepcopy(self.attempt10_masks)
        unknown_overlap["observed_overlaps"][0]["future_field"] = True
        cases.append(unknown_overlap)
        for observed in cases:
            with self.subTest():
                with self.assertRaisesRegex(ValueError, r"fields must be exact.*unknown"):
                    compare_semantic_masks(self.attempt10_masks, observed)

    def test_worker_is_append_only_attempt_11_and_excludes_full_mask_gate(self) -> None:
        source = REVISION02_WORKER.read_text(encoding="utf-8")
        self.assertIn('EXPECTED_ATTEMPT_SLOT = "attempt_11"', source)
        self.assertIn("planned_output = next_append_only_output()", source)
        self.assertIn("planned_output.name != EXPECTED_ATTEMPT_SLOT", source)
        self.assertIn("ACTIVE_OUTPUT.name != EXPECTED_ATTEMPT_SLOT", source)
        self.assertIn("attempt11_revision02_pre_cap_fingerprint", source)
        self.assertIn("attempt11_revision02_solver_fingerprint", source)
        self.assertGreaterEqual(source.count("compare_semantic_masks("), 2)
        self.assertGreaterEqual(
            source.count("mask_semantic_and_t_stability_gate_passed"), 2
        )
        self.assertNotIn("mask_canonical_sha256_exact", source)
        self.assertNotIn("current_mask_canonical_sha256", source)
        self.assertNotIn("reference_mask_canonical_sha256", source)
        self.assertIn("SEMANTIC_HELPER_SHA256", source)
        self.assertIn(
            'SEMANTIC_HELPER_SHA256 = "c68d4121dcdce8ef28cbb04e48708984591569c70a9a70fb4c3565f66a4118e5"',
            source,
        )
        self.assertIn(
            '(SEMANTIC_HELPER, SEMANTIC_HELPER_SHA256, "semantic fingerprint helper")',
            source,
        )
        helper_guard = source.index(
            '(SEMANTIC_HELPER, SEMANTIC_HELPER_SHA256, "semantic fingerprint helper")'
        )
        self.assertLess(helper_guard, source.index("planned_output = next_append_only_output()"))
        self.assertLess(helper_guard, source.index("bpy.ops.wm.open_mainfile"))
        self.assertGreaterEqual(source.count('"semantic_fingerprint_helper": {'), 2)
        self.assertFalse((EVIDENCE_ROOT / "attempt_11").exists())

    def test_helper_revision01_and_attempt09_10_evidence_are_bound_exactly(self) -> None:
        for path, expected in BOUND_SHA256.items():
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), expected)


if __name__ == "__main__":
    unittest.main()
