#!/usr/bin/env python3
"""Non-Blender checks for the bounded Robert R26 Attempt 09 preparation."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import verify_biological_robert_r26_attempt09_package as verifier


WORKER = ROOT / "Tools" / "blender_build_biological_robert_r26_bald_owner_review.py"
CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "biological_robert_r26_read_only_preparation"
    / "ROBERT_R26_BUILD_CONFIG.json"
)
RELEASE = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "ROBERT_R26_AFTER_KIRA_BLENDER_RELEASE.json"
)
CANDIDATE = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "dual_robert_20260729"
    / "biological_robert_r26_bald_owner_review"
)
ATTEMPT01_RESULT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "biological_robert_r26_bounded_run"
    / "attempt_09_preparation"
    / "nail_weight_constrained_finger5_probe"
    / "PROBE_RESULT.json"
)
ATTEMPT02_RESULT = ATTEMPT01_RESULT.parent / "attempt_02" / "PROBE_RESULT.json"
ALL20_RESULT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "biological_robert_r26_bounded_run"
    / "attempt_09_preparation"
    / "nail_all20_evaluated_footprint_probe"
    / "PROBE_RESULT.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nail_rows() -> list[dict[str, object]]:
    rows = []
    for nail_id in verifier.EXPECTED_NAIL_IDS:
        kind, digit, side = nail_id.split("_")
        prefix = "finger" if kind == "fingernail" else "toe"
        segment = "2" if kind == "toenail" and digit == "1" else "3"
        bone = f"{prefix}{digit}-{segment}.{side}"
        rows.append(
            {
                "nail_id": nail_id,
                "bone": bone,
                "declared_terminal_bone": bone,
                "automatic_bone_remap_performed": False,
                "footprint_binding": {"passed": True},
                "selection": {
                    "passed": True,
                    "every_sample_matches_declared_digit": True,
                    "every_sample_uses_one_connected_region": True,
                    "neighboring_or_occluding_first_hit_rejected_count": 0,
                },
                "final_evaluated_complete_shell_gate": {
                    "passed": True,
                    "exact_genuine_triangle_pair_count": 0,
                    "gates": {
                        "complete_shell_included": True,
                        "solidify_rim_included": True,
                        "zero_exact_genuine_penetrations": True,
                    },
                },
                "attachment": {
                    "bone": bone,
                    "parent_is_exact_armature": True,
                    "armature_modifier_targets_exact_rig": True,
                    "every_vertex_has_unit_terminal_bone_weight": True,
                },
            }
        )
    return rows


def nail_report() -> dict[str, object]:
    return {
        "method": "avatar_weight_constrained_evaluated_nail_projection_v1",
        "records": nail_rows(),
        "gates": {
            "exact_twenty_inventory_in_declared_order": True,
            "all_twenty_strict_declared_digit_footprints": True,
            "all_twenty_complete_evaluated_armature_solidify_shells": True,
            "all_twenty_zero_rest_shell_penetrations": True,
            "no_automatic_bone_remap": True,
            "all_twenty_exact_terminal_bone_attachments": True,
            "all_twenty_natural_material_and_oval_construction": True,
            "primary_body_mesh_unchanged": True,
            "official_rig_unchanged": True,
            "body_modifier_stack_unchanged": True,
        },
    }


class Attempt09PreparationTests(unittest.TestCase):
    def test_worker_is_syntactically_valid_and_uses_only_bounded_nail_rebind(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("WEIGHT_CONSTRAINED_NAIL_ADAPTER", source)
        self.assertIn("build_weight_constrained_nail_v1", source)
        self.assertIn("all_twenty_nails_strict_declared_digit_footprint", source)
        self.assertIn("all_twenty_nails_complete_evaluated_shell", source)
        self.assertIn("all_twenty_nails_exact_terminal_bone_attachment", source)
        self.assertIn("maximum_candidate_count", source)

    def test_config_is_single_private_bald_candidate_and_has_new_gates(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["schema"], "kira.avatar.biological_robert_r26_bald_owner_review_config.v3")
        self.assertEqual(config["output"]["maximum_candidate_count"], 1)
        self.assertTrue(config["scope"]["private"])
        self.assertTrue(config["scope"]["inactive"])
        self.assertTrue(config["scope"]["unassigned"])
        self.assertTrue(config["scope"]["unpublished"])
        self.assertFalse(config["scope"]["scalp_hair_allowed"])
        self.assertFalse(config["scope"]["runtime_export_allowed"])
        required = set(config["mandatory_exact_audits"])
        self.assertIn("all_twenty_nails_strict_declared_digit_footprint", required)
        self.assertIn("all_twenty_nails_complete_evaluated_shell", required)
        self.assertIn("all_twenty_nails_exact_terminal_bone_attachment", required)

    def test_every_configured_input_hash_and_size_is_exact(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        for name, row in config["inputs"].items():
            path = ROOT / row["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(sha256_file(path), row["sha256"], name)
            if "bytes" in row:
                self.assertEqual(path.stat().st_size, row["bytes"], name)

    def test_release_binds_current_worker_and_config(self) -> None:
        release = json.loads(RELEASE.read_text(encoding="utf-8"))
        implementation = release["implementation"]
        self.assertEqual(implementation["worker_sha256"], sha256_file(WORKER))
        self.assertEqual(implementation["config_sha256"], sha256_file(CONFIG))

    def test_prior_probe_results_are_preserved(self) -> None:
        expected = {
            ATTEMPT01_RESULT: "a9387c8b1616af32cd6dc87d62e2c7eaf577c67650d23243427f9bf5a109c53a",
            ATTEMPT02_RESULT: "1a02f1d58c5a222df150225c34b3294597f3d23b5f2852c604faadc457d50ec1",
            ALL20_RESULT: "6a9626d14481f2b90c42fc25a0c268031fbd8a5616ad54625e9a87af30d1a11a",
        }
        for path, digest in expected.items():
            self.assertEqual(sha256_file(path), digest)

    def test_preparation_has_not_created_candidate(self) -> None:
        self.assertFalse(CANDIDATE.exists())

    def test_verifier_accepts_exact_all20_nail_evidence(self) -> None:
        result = verifier.verify_nails(nail_report())
        self.assertEqual(result["record_count"], 20)
        self.assertTrue(result["strict_declared_digit_footprints_all_20"])
        self.assertTrue(result["complete_evaluated_shells_all_20"])

    def test_verifier_rejects_wrong_digit_footprint(self) -> None:
        report = nail_report()
        report["records"][7]["selection"]["every_sample_matches_declared_digit"] = False
        with self.assertRaises(verifier.Attempt09VerificationError):
            verifier.verify_nails(report)

    def test_verifier_rejects_incomplete_evaluated_shell(self) -> None:
        report = nail_report()
        report["records"][10]["final_evaluated_complete_shell_gate"]["passed"] = False
        with self.assertRaises(verifier.Attempt09VerificationError):
            verifier.verify_nails(report)

    def test_verifier_rejects_metadata_only_bone_match(self) -> None:
        report = nail_report()
        report["records"][4]["attachment"]["bone"] = "finger4-3.L"
        with self.assertRaises(verifier.Attempt09VerificationError):
            verifier.verify_nails(report)

    def test_nail_fixture_contains_only_finite_truth_values(self) -> None:
        for row in nail_rows():
            shell = row["final_evaluated_complete_shell_gate"]
            self.assertTrue(math.isfinite(float(shell["exact_genuine_triangle_pair_count"])))


if __name__ == "__main__":
    unittest.main()
