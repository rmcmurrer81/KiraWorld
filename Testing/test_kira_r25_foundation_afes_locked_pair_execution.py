from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tools import kira_r25_canonical_receipt as receipt
from tools import kira_r25_afes_topology_core_v2 as topology_core
from tools import run_kira_r25_foundation_afes_locked_pair as controller


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v1.json"
)
WRAPPER = ROOT / (
    "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v1.py"
)
CONTROLLER = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LockedPairExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_01_scope_authorizes_only_the_read_only_pair(self) -> None:
        self.assertEqual(
            self.contract["status"], "AUTHORIZED_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
        )
        scope = self.contract["scope"]
        self.assertTrue(scope["read_only_blender_diagnostic"])
        for key in (
            "blend_mutation_allowed",
            "blend_save_allowed",
            "render_allowed",
            "candidate_creation_allowed",
            "body_authoring_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "export_allowed",
            "publication_allowed",
        ):
            self.assertFalse(scope[key], key)
        self.assertEqual(self.contract["required_fresh_run_count"], 2)

    def test_02_all_project_bindings_and_blender_match_exact_bytes(self) -> None:
        for label, row in self.contract["bindings"].items():
            path = Path(row["path"])
            if not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), label)
            self.assertEqual(path.stat().st_size, row["bytes"], label)
            self.assertEqual(sha256(path), row["sha256"], label)
        self.assertEqual(
            Path(controller.__file__).resolve(),
            (ROOT / self.contract["bindings"]["parent_controller"]["path"]).resolve(),
        )
        self.assertEqual(receipt.MAX_RECEIPT_FRAME_BYTES, 1_048_628)
        self.assertEqual(
            self.contract["process_contract"]["maximum_frame_bytes"],
            receipt.MAX_RECEIPT_FRAME_BYTES,
        )

    def test_03_controller_locks_inputs_uses_least_handle_and_drains_concurrently(self) -> None:
        source = CONTROLLER.read_text(encoding="utf-8")
        for token in (
            "FILE_SHARE_READ",
            'startup.lpAttributeList = {"handle_list": [write_handle]}',
            "close_fds=True",
            "threading.Thread",
            "MAX_RECEIPT_FRAME_BYTES + 1",
            "process.communicate(timeout=",
            "process.terminate()",
            "WindowsExclusiveReceiptReservation.reserve",
            "for run_number in (1, 2)",
            "fresh_locked_inner_payloads_do_not_match",
            "bound_input_changed_during_locked_pair",
        ):
            self.assertIn(token, source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("bpy", source)

    def test_04_wrapper_has_nonce_binding_and_no_authoring_surface(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        for token in (
            "attempt02.extract_payload()",
            "--execution-contract-sha256",
            "--session-nonce",
            "--run-number",
            "write_receipt_frame_to_inherited_pipe",
        ):
            self.assertIn(token, source)
        for forbidden in (
            "bpy.ops",
            "save_as_mainfile",
            "render.render",
            "export_scene",
            "--result-path",
            "write_text(",
            "write_bytes(",
        ):
            self.assertNotIn(forbidden, source)

    def test_05_environment_is_restricted_and_candidate_root_is_fresh(self) -> None:
        environment = controller._restricted_environment()
        permitted = {
            "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERNAME", "USERPROFILE",
            "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "Path",
            "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE", "BLENDER_USER_CONFIG",
            "BLENDER_USER_SCRIPTS", "BLENDER_USER_DATAFILES",
        }
        self.assertLessEqual(set(environment), permitted)
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        output = ROOT / self.contract["append_only_output_root"]
        self.assertFalse(output.exists())

    def test_06_pair_summary_does_not_claim_body_acceptance(self) -> None:
        truth = self.contract["truth_boundary"]
        self.assertTrue(truth["pair_pass_would_only_satisfy_foundation_afes_plus_transition_vertex_set_audit"])
        self.assertTrue(truth["semantic_cage_still_required"])
        self.assertTrue(truth["positive_jacobian_and_intersection_fixtures_still_required"])
        self.assertTrue(truth["body_authoring_not_granted"])
        self.assertTrue(truth["candidate_not_created"])
        self.assertTrue(truth["owner_review_not_implied"])
        self.assertTrue(truth["runtime_authority_not_implied"])
        self.assertEqual(topology_core.FILE_TYPE_PIPE, 3)


if __name__ == "__main__":
    unittest.main()
