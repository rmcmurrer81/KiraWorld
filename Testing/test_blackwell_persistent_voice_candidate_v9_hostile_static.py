"""Hostile static-only tests for the append-only Blackwell v9 repair.

These tests run only v8's sealed synthetic static fixture through the exact
Windows venvlauncher topology.  They never import/run Ollama, Qwen, Torch,
CUDA, Chatterbox, audio synthesis/playback, a person, or Blender.
"""

from __future__ import annotations

import ast
import hashlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from Core.persistent_blackwell_voice_integration_v9 import (
    BlackwellV9Coordinator,
    LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE,
    PLAYBACK_AUTHORIZED,
    PRODUCTION_ROUTING_AUTHORIZED,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v9.candidate_contract import (
    CANONICAL_CONFIG_SHA256,
    CONFIG_PATH,
    PROJECT_ROOT,
    V9ContractError,
    load_canonical_config,
    sha256_file,
    verify_preserved_bytes,
    verify_seal_manifest,
    verify_topology_executables,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v9"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _exact_command(config: dict, nonce: str) -> tuple[str, ...]:
    return (
        config["process_topology"]["launcher"]["executable_path"],
        "-u",
        "-m",
        config["worker_module"],
        "--static-fixture",
        "--nonce",
        nonce,
    )


class V9ContractTests(unittest.TestCase):
    def test_config_is_exact_default_off_and_preserves_all_prior_bytes(self):
        config = load_canonical_config()
        self.assertEqual(sha256_file(CONFIG_PATH), CANONICAL_CONFIG_SHA256)
        self.assertFalse(config["production_routing_authorized"])
        self.assertFalse(config["live_execution_authorized_by_this_candidate"])
        self.assertFalse(config["playback_authorized_by_this_candidate"])
        self.assertFalse(config["current_production_route_changed"])
        self.assertEqual(config["live_attempt_number_allowed_after_fresh_audit"], 2)
        observed = verify_preserved_bytes(config)
        self.assertGreaterEqual(len(observed), 30)
        self.assertIn(
            "RecoverySprint/continuation_20260810/blackwell_v8_bounded_live_acceptance/attempt_01/FINAL_REPORT.json",
            observed,
        )

    def test_module_truth_and_production_factory_are_fail_closed(self):
        self.assertFalse(PRODUCTION_ROUTING_AUTHORIZED)
        self.assertFalse(LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE)
        self.assertFalse(PLAYBACK_AUTHORIZED)
        with self.assertRaisesRegex(V9ContractError, "not production"):
            BlackwellV9Coordinator.production_candidate()

    def test_v9_author_did_not_create_the_required_future_audit(self):
        config = load_canonical_config()
        audit = PROJECT_ROOT / config["fresh_audit_contract"]["required_relative_path"]
        self.assertFalse(audit.exists())
        with patch.dict(
            os.environ,
            {
                config["engineering_run_opt_in"]:
                config["engineering_run_opt_in_value"]
            },
            clear=False,
        ):
            with self.assertRaisesRegex(V9ContractError, "fresh different-agent"):
                BlackwellV9Coordinator.bounded_engineering_candidate(
                    nonce=_sha("v9-live-refusal"),
                    accepted_v9_audit_sha256="0" * 64,
                    accepted_v8_worker_audit_sha256=
                    config["v8_worker_audit_binding"]["sha256"],
                )

    def test_exact_launcher_and_base_python_file_identities_are_current(self):
        observed = verify_topology_executables(load_canonical_config())
        self.assertEqual(
            observed["launcher"]["executable_sha256"],
            "21bb438c0d4a6f1f164b9a646f6ee000340185e5871180aec06db8d3f07c0082",
        )
        self.assertEqual(
            observed["worker"]["executable_sha256"],
            "5f7b89a612c9b8af1d6456cdfcd1dbe5ca630849e79aebced9bee9a6694952ec",
        )
        self.assertNotEqual(
            observed["launcher"]["executable_file_index"],
            observed["worker"]["executable_file_index"],
        )

    def test_static_seal_rehashes_every_v9_file(self):
        config = load_canonical_config()
        seal = PROJECT_ROOT / config["fresh_audit_contract"]["required_seal_manifest_path"]
        result = verify_seal_manifest(config, seal)
        self.assertEqual(len(result["files"]), 7)


class V9TopologyTests(unittest.TestCase):
    def test_exact_static_topology_binds_two_handles_and_child_responses(self):
        coordinator = BlackwellV9Coordinator.static_fixture_candidate(
            nonce=_sha("v9-exact-topology")
        )
        cleanup = None
        try:
            started = coordinator.start()
            self.assertNotEqual(started["root_pid"], started["worker_pid"])
            self.assertEqual(started["worker_direct_parent_pid"], started["root_pid"])
            self.assertTrue(started["worker_child_job_proof"]["same_retained_job"])
            self.assertFalse(started["arbitrary_descendant_accepted"])
            self.assertEqual(
                started["launcher_process_identity"]["executable_file_index"],
                1407374884528005,
            )
            self.assertEqual(
                started["worker_process_identity"]["executable_file_index"],
                1970324837912590,
            )
            result = coordinator._invoke("fixture_echo", {"bound": "child"})
            self.assertEqual(result["worker_pid"], started["worker_pid"])
            self.assertEqual(result["root_pid"], started["root_pid"])
            self.assertEqual(result["value"], {"bound": "child"})
        finally:
            cleanup = coordinator.close()
        self.assertTrue(cleanup["root_exited"])
        self.assertTrue(cleanup["worker_child_exited"])
        self.assertTrue(cleanup["entire_bound_tree_exited"])
        self.assertTrue(cleanup["worker_child_handle_closed"])
        self.assertTrue(cleanup["job_handle_closed"])
        self.assertTrue(cleanup["root_standard_streams_closed"])
        self.assertTrue(cleanup["binding_accepted_before_cleanup"])

    def test_grandchild_protocol_owner_is_rejected_and_entire_job_exits(self):
        nonce = _sha("v9-hostile-grandchild")
        config = load_canonical_config()
        identities = verify_topology_executables(config)
        command = (
            identities["launcher"]["executable_path"],
            "-u",
            str(ROOT / "Testing/blackwell_v9_grandchild_redirector.py"),
            "--nonce",
            nonce,
        )
        coordinator = BlackwellV9Coordinator._static_fixture_for_hostile_test(
            nonce=nonce,
            command=command,
            expected_launcher_identity=identities["launcher"],
            expected_worker_identity=identities["worker"],
        )
        with self.assertRaisesRegex(Exception, "direct_parent_pid"):
            coordinator.start()
        rejection = coordinator.process.last_binding_rejection
        cleanup = coordinator.process.last_termination
        self.assertEqual(rejection["stage"], "root_child_identity")
        self.assertIn("direct_parent_pid", rejection["mismatch_fields"])
        self.assertFalse(rejection["arbitrary_descendant_accepted"])
        self.assertTrue(cleanup["root_exited"])
        self.assertTrue(cleanup["worker_child_exited"])
        self.assertTrue(cleanup["worker_child_handle_closed"])
        self.assertTrue(cleanup["entire_bound_tree_exited"])
        self.assertFalse(cleanup["binding_accepted_before_cleanup"])

    def test_changed_launcher_identity_is_rejected_before_resume(self):
        nonce = _sha("v9-hostile-launcher-identity")
        config = load_canonical_config()
        identities = verify_topology_executables(config)
        wrong_launcher = dict(identities["launcher"])
        wrong_launcher["executable_sha256"] = "0" * 64
        coordinator = BlackwellV9Coordinator._static_fixture_for_hostile_test(
            nonce=nonce,
            command=_exact_command(config, nonce),
            expected_launcher_identity=wrong_launcher,
            expected_worker_identity=identities["worker"],
        )
        with self.assertRaisesRegex(Exception, "launcher_executable_identity"):
            coordinator.start()
        rejection = coordinator.process.last_binding_rejection
        cleanup = coordinator.process.last_termination
        self.assertEqual(rejection["stage"], "launcher_identity")
        self.assertTrue(cleanup["root_exited"])
        self.assertIsNone(cleanup["worker_child_pid"])
        self.assertTrue(cleanup["entire_bound_tree_exited"])

    def test_changed_worker_identity_is_rejected_and_both_processes_exit(self):
        nonce = _sha("v9-hostile-worker-identity")
        config = load_canonical_config()
        identities = verify_topology_executables(config)
        wrong_worker = dict(identities["worker"])
        wrong_worker["executable_sha256"] = "f" * 64
        coordinator = BlackwellV9Coordinator._static_fixture_for_hostile_test(
            nonce=nonce,
            command=_exact_command(config, nonce),
            expected_launcher_identity=identities["launcher"],
            expected_worker_identity=wrong_worker,
        )
        with self.assertRaisesRegex(Exception, "worker_executable_identity"):
            coordinator.start()
        rejection = coordinator.process.last_binding_rejection
        cleanup = coordinator.process.last_termination
        self.assertEqual(rejection["stage"], "root_child_identity")
        self.assertTrue(cleanup["root_exited"])
        self.assertTrue(cleanup["worker_child_exited"])
        self.assertTrue(cleanup["worker_child_handle_closed"])
        self.assertTrue(cleanup["entire_bound_tree_exited"])


class V9StaticSourceTests(unittest.TestCase):
    def test_v9_python_parses_and_has_no_top_level_calls(self):
        paths = [
            ROOT / "Core/blackwell_v9_process_boundary.py",
            ROOT / "Core/persistent_blackwell_voice_integration_v9.py",
            ROOT / "Testing/blackwell_v9_grandchild_redirector.py",
            ROOT / "Testing/test_blackwell_persistent_voice_candidate_v9_hostile_static.py",
            PACKAGE / "candidate_contract.py",
        ]
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    self.fail(f"top-level call in {path}: {ast.dump(node.value)}")

    def test_import_is_inert_and_forbidden_live_stacks_remain_absent(self):
        module = "Core.persistent_blackwell_voice_integration_v9"
        before = {
            name: name in sys.modules
            for name in ("torch", "torchaudio", "chatterbox", "winsound", "bpy")
        }
        with patch("subprocess.Popen") as popen:
            __import__(module)
        popen.assert_not_called()
        for name, existed in before.items():
            if not existed:
                self.assertNotIn(name, sys.modules)

    def test_live_factory_is_source_ordered_after_v9_audit_and_capability(self):
        source = (
            ROOT / "Core/persistent_blackwell_voice_integration_v9.py"
        ).read_text(encoding="utf-8")
        audit = source.index("verify_fresh_audit_authorization(")
        capability = source.index("verify_per_run_live_capability(config)")
        live_environment = source.index("environment = _v8_live_environment")
        self.assertLess(audit, capability)
        self.assertLess(capability, live_environment)
        self.assertNotIn("import torch", source.casefold())
        self.assertNotIn("import chatterbox", source.casefold())


if __name__ == "__main__":
    unittest.main()
