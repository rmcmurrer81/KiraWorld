"""Read-only analysis tests for the preserved Attempt 38 CDT stall."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_38"
)

EXPECTED = {
    "ATTEMPT_STARTED.json": (8071, "65f06e871f180b046bc23e7ff7f84d6da6457d8ffde099368275fe05a2da232e"),
    "APPEND_INVENTORY.json": (7549, "c091e20109bc085ce55a3279193646c9b26295ac23c957173ffb1354e222cdb0"),
    "CDT_NONDEGRADING_TRIALS.json": (6271, "082e7b59e924698a477e0f77dceece5e3d3bad7c2b739bcfb33d5e9fd4ab49c7"),
    "FAILURE.json": (9320, "22768220b896eb76743800ef2465bc8422e92a74f3cdb877414acaadb96e4561"),
}

EXTERNAL = {
    "RecoverySprint/continuation_20260808/attempt38_blender_stdout.log": (
        566,
        "3da02953cdc851aede9784cb6736be6e9b19dc053cd8e755d799c1a2160074bb",
    ),
    "RecoverySprint/continuation_20260808/attempt38_blender_stderr.log": (
        6502,
        "273915fb61761f805aa54176c69da74f964085e267ca9a61f89d0da00222397b",
    ),
    "RecoverySprint/continuation_20260808/attempt38_external_pre_post_integrity.json": (
        163608,
        "747c4f97f45ed176f0ef0919abd9cd03e192848b22a8f9017cc8d31f71ad6f16",
    ),
    "RecoverySprint/continuation_20260808/ATTEMPT38_RUNTIME_CDT_STALL_FAILURE_CHECKPOINT.md": (
        6237,
        "a8b11a2b0e6ecb2ad56dc818d5c8df9d19318dc4b627d17f55ad446d8f6226b4",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def angle_degrees(center: tuple[float, float], first: tuple[float, float], second: tuple[float, float]) -> float:
    left = (first[0] - center[0], first[1] - center[1])
    right = (second[0] - center[0], second[1] - center[1])
    cosine = (left[0] * right[0] + left[1] * right[1]) / (
        math.hypot(*left) * math.hypot(*right)
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


class Attempt38RuntimeAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.trials = json.loads((RUNTIME / "CDT_NONDEGRADING_TRIALS.json").read_text(encoding="utf-8"))
        cls.failure = json.loads((RUNTIME / "FAILURE.json").read_text(encoding="utf-8"))
        cls.integrity = json.loads(
            (ROOT / "RecoverySprint/continuation_20260808/attempt38_external_pre_post_integrity.json").read_text(encoding="utf-8")
        )

    def test_01_all_attempt38_evidence_is_byte_bound(self) -> None:
        for name, (size, digest) in EXPECTED.items():
            path = RUNTIME / name
            self.assertEqual(path.stat().st_size, size, name)
            self.assertEqual(sha256(path), digest, name)
        for relative, (size, digest) in EXTERNAL.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(sha256(path), digest, relative)

    def test_02_failure_is_iteration_zero_policy_stall(self) -> None:
        expected = "quality_refined_cdt_no_nondegrading_candidate:current=2.635073748299402:iteration=0:seeds=38"
        self.assertEqual(self.trials["error"], expected)
        self.assertEqual(self.failure["error"], expected)
        self.assertEqual(self.trials["iteration_count"], 1)
        self.assertEqual(self.trials["iterations"][0]["iteration"], 0)
        self.assertEqual(self.trials["iterations"][0]["worst_face"], [77, 23, 24])

    def test_03_circumcenter_is_safe_but_stagnant(self) -> None:
        trial = self.trials["iterations"][0]["trials"][0]
        self.assertEqual(trial["candidate_kind"], "circumcenter")
        self.assertEqual(trial["minimum_angle_degrees"], 2.635073748299402)
        self.assertEqual(trial["rejection_reasons"], ["strict_global_minimum_angle_improvement"])
        passed_except_progress = dict(trial["checks"])
        self.assertFalse(passed_except_progress.pop("strict_global_minimum_angle_improvement"))
        self.assertTrue(all(passed_except_progress.values()))

    def test_04_centroid_is_safe_but_degrading(self) -> None:
        trial = self.trials["iterations"][0]["trials"][1]
        self.assertEqual(trial["candidate_kind"], "centroid")
        self.assertAlmostEqual(trial["minimum_angle_degrees"], 0.9799868976552613)
        self.assertLess(
            trial["minimum_angle_degrees"],
            self.trials["iterations"][0]["current_minimum_angle_degrees"],
        )
        self.assertEqual(trial["rejection_reasons"], ["strict_global_minimum_angle_improvement"])

    def test_05_worst_face_is_near_flat_boundary_seed_triangle(self) -> None:
        # Exact coordinates come from the independently preserved Attempt 36
        # trace for the same 38-seed CDT state used by Attempt 38.
        points = (
            (-0.000302500237012282, -0.0016266348538920283),
            (-0.0003287002327851951, -0.0012715889606624842),
            (-0.0003225125838071108, -0.002141158562153578),
        )
        angles = sorted(
            angle_degrees(points[index], points[(index + 1) % 3], points[(index + 2) % 3])
            for index in range(3)
        )
        self.assertLess(angles[0], 2.636)
        self.assertLess(angles[1], 3.813)
        self.assertGreater(angles[2], 173.55)
        self.assertEqual(
            self.trials["iterations"][0]["worst_face"][1:], [23, 24]
        )  # consecutive fixed boundary sources

    def test_06_failure_precedes_mutation_save_render_and_runtime(self) -> None:
        self.assertFalse(self.failure["render_reached"])
        self.assertFalse(self.failure["blend_saved"])
        self.assertFalse(self.failure["runtime_changed"])
        inventory = json.loads((RUNTIME / "APPEND_INVENTORY.json").read_text(encoding="utf-8"))
        self.assertFalse(inventory["geometry_mutation_reached"])
        self.assertFalse(inventory["reconstruction_reached"] if "reconstruction_reached" in inventory else False)
        self.assertFalse((RUNTIME / "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json").exists())

    def test_07_external_integrity_is_exact_240_of_240(self) -> None:
        self.assertEqual(self.integrity["blender_exit_code"], 1)
        self.assertIsNone(self.integrity["native_invocation_error"])
        self.assertTrue(self.integrity["pre_post_exact"])
        self.assertEqual(len(self.integrity["before"]), 240)
        self.assertEqual(self.integrity["before"], self.integrity["after"])

    def test_08_attempt38_is_not_a_body_quality_pass(self) -> None:
        self.assertEqual(self.failure["status"], "NO_SAVE_ATTEMPT38_FAILURE_PRESERVED")
        self.assertNotEqual(self.trials["status"], "PASS")
        self.assertFalse(self.failure.get("body_repair_proven", False))


if __name__ == "__main__":
    unittest.main()
