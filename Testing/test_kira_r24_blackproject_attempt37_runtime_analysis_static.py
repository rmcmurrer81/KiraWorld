import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "RecoverySprint" / "continuation_20260808"
PREFLIGHT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "PREFLIGHT"
)
ATTEMPT_ROOT = PREFLIGHT.parent / "attempt_37"
STDOUT = RUNTIME / "attempt37_blender_stdout.log"
STDERR = RUNTIME / "attempt37_blender_stderr.log"
INTEGRITY = RUNTIME / "attempt37_external_pre_post_integrity.json"
WORKER = ROOT / "tools" / "blender_diagnose_kira_r24_blackproject_candidate_attempt37.py"
CHECKPOINT = PREFLIGHT / "ATTEMPT_37_STATIC_CHECKPOINT.md"
PROPOSAL = PREFLIGHT / "ATTEMPT_38_LAUNCH_TARGET_OWNERSHIP_PROPOSAL.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Attempt37RuntimeAnalysisStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stdout = STDOUT.read_text(encoding="utf-8", errors="replace")
        stderr_bytes = STDERR.read_bytes()
        cls.stderr = stderr_bytes.decode(
            "utf-16" if stderr_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8",
            errors="replace",
        )
        cls.integrity = json.loads(INTEGRITY.read_text(encoding="utf-8"))
        cls.worker = WORKER.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        cls.proposal = PROPOSAL.read_text(encoding="utf-8")

    def test_01_runtime_files_are_exactly_bound(self) -> None:
        self.assertEqual(
            sha256(STDOUT),
            "d1ca02209155e832b2cc2e7660813078125d9dc820eb5d57c9bcb2d17bbe87ce",
        )
        self.assertEqual(
            sha256(STDERR),
            "91172000b1e0e463fcd14e24e8fb5da57611a0daf2f81bca49fa8e2644caf389",
        )
        self.assertEqual(
            sha256(INTEGRITY),
            "175f250e5459f1884e111497cd073aab4c7b31880490a8dae7286102d5c1df4c",
        )

    def test_02_exact_failure_is_launcher_worker_ownership_conflict(self) -> None:
        expected = "Attempt 37 runtime target already exists: stdout"
        self.assertIn(expected, self.stderr)
        self.assertIn("validate_config(config)", self.stderr)
        self.assertNotIn("quality_refined_cdt_failed", self.stderr)
        self.assertNotIn("CDT_NONDEGRADING_TRIALS", self.stderr)

    def test_03_wrapper_precreates_logs_before_worker_validation(self) -> None:
        create_logs = self.checkpoint.index("foreach ($log in @($stdout, $stderr))")
        create_new = self.checkpoint.index("[System.IO.FileMode]::CreateNew", create_logs)
        invocation = self.checkpoint.index("& $blender --background", create_new)
        self.assertLess(create_logs, create_new)
        self.assertLess(create_new, invocation)
        worker_absence = re.search(
            r'for key in \("stdout", "stderr", "external_integrity"\):\s*'
            r'if project_path\(str\(launch\[key\]\), must_exist=False\)\.exists\(\):',
            self.worker,
        )
        self.assertIsNotNone(worker_absence)

    def test_04_candidate_patch_and_evidence_writer_were_not_reached(self) -> None:
        self.assertFalse(ATTEMPT_ROOT.exists())
        for name in (
            "ATTEMPT_STARTED.json",
            "APPEND_INVENTORY.json",
            "CDT_NONDEGRADING_TRIALS.json",
            "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
            "FAILURE.json",
        ):
            self.assertFalse((ATTEMPT_ROOT / name).exists(), name)
        self.assertNotIn("verify_overlay(config)", self.stderr)
        self.assertNotIn("quality_refined_cdt", self.stderr)

    def test_05_external_integrity_is_exact_despite_exit_one(self) -> None:
        self.assertEqual(
            self.integrity["schema"],
            "kira.avatar.r24.attempt37.external_pre_post_integrity.v1",
        )
        self.assertEqual(self.integrity["blender_exit_code"], 1)
        self.assertIsNone(self.integrity["native_invocation_error"])
        self.assertTrue(self.integrity["pre_post_exact"])
        self.assertEqual(len(self.integrity["before"]), 230)
        self.assertEqual(len(self.integrity["after"]), 230)
        self.assertEqual(self.integrity["before"], self.integrity["after"])

    def test_06_result_is_not_a_cdt_or_body_result(self) -> None:
        self.assertNotIn("body repair proven", self.stdout.lower())
        self.assertNotIn("candidate accepted", self.stdout.lower())
        self.assertFalse(ATTEMPT_ROOT.exists())

    def test_07_next_proposal_changes_only_launch_target_ownership(self) -> None:
        proposal_flat = " ".join(self.proposal.split())
        required = (
            "static proposal only",
            "worker stopped during config validation",
            "passed nor failed; it is untested",
            "wrapper remains the sole owner of external stdout, stderr, and",
            "worker must not require wrapper-owned stdout",
            "exact Attempt 37 geometry/candidate implementation forward unchanged",
            "No runtime attempt is authorized by this proposal.",
        )
        for value in required:
            self.assertIn(value, proposal_flat)

    def test_08_next_proposal_preserves_hard_boundaries(self) -> None:
        for value in (
            "exact 12-degree minimum-angle gate",
            "160-interior-vertex cap",
            "40-vertex constrained boundary",
            "no-render, no-save, no-export",
            "no automatic retry",
            "No lowering of a quality gate",
        ):
            self.assertIn(value, self.proposal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
