"""Hostile static tests for the default-off Blackwell v11 integration."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v11"
CONFIG_PATH = PACKAGE / "candidate_config.json"
SEAL_PATH = PACKAGE / "STATIC_SEAL_MANIFEST.json"
ROUTING_PATH = ROOT / "Voice/sidecars/kira_approved_voice_routing.json"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class BlackwellV11ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v11.candidate_contract"
        )
        cls.worker = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v11.worker_entry"
        )
        cls.integration = importlib.import_module(
            "Core.persistent_blackwell_voice_integration_v11"
        )

    def test_01_config_is_exact_default_off(self):
        config = self.contract.load_canonical_config()
        self.assertFalse(config["production_routing_authorized"])
        self.assertFalse(config["live_execution_authorized_by_this_candidate"])
        self.assertFalse(config["playback_authorized_by_this_candidate"])
        self.assertFalse(config["current_production_route_changed"])
        self.assertTrue(config["worker_integration_implemented"])
        self.assertFalse(config["worker_integration_live_validated"])
        self.assertFalse(config["future_live_attempt_authorized"])

    def test_02_exact_fourteen_predecessor_boundaries_match(self):
        observed = self.contract.verify_preserved_bytes(
            self.contract.load_canonical_config()
        )
        self.assertEqual(len(observed), 14)
        self.assertEqual(
            observed["Voice/sidecars/kira_approved_voice_routing.json"],
            "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81",
        )

    def test_03_v10_static_audit_is_parsed_and_bound(self):
        value = self.contract.verify_v10_static_audit(
            self.contract.load_canonical_config()
        )
        self.assertEqual(
            value["verdict"],
            "ACCEPT_V10_STATIC_MEMORY_REPAIR_FOR_FUTURE_HARNESS_AUTHORING_ONLY",
        )
        self.assertFalse(value["live_authorized"])

    def test_04_future_v11_audit_is_absent_and_fails_closed(self):
        config = self.contract.load_canonical_config()
        path = ROOT / config["future_fresh_audit_contract"]["required_relative_path"]
        self.assertFalse(path.exists())
        with self.assertRaisesRegex(
            self.contract.V11ContractError, "fresh different-agent v11 audit"
        ):
            self.contract.verify_future_fresh_audit_authorization(
                config, expected_audit_sha256="0" * 64
            )

    def test_05_production_factory_is_fail_closed(self):
        self.assertFalse(self.integration.PRODUCTION_ROUTING_AUTHORIZED)
        self.assertFalse(self.integration.LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE)
        self.assertFalse(self.integration.PLAYBACK_AUTHORIZED)
        with self.assertRaisesRegex(self.contract.V11ContractError, "not production"):
            self.integration.BlackwellV11Coordinator.production_candidate()

    def test_06_live_factory_refuses_before_process_creation(self):
        config = self.contract.load_canonical_config()
        with patch.dict(
            os.environ,
            {config["engineering_run_opt_in"]: config["engineering_run_opt_in_value"]},
            clear=False,
        ):
            with self.assertRaisesRegex(
                self.contract.V11ContractError, "does not authorize a live run"
            ):
                self.integration.BlackwellV11Coordinator.bounded_engineering_candidate(
                    nonce=_sha("v11-refuse-live"),
                    accepted_v11_audit_sha256="0" * 64,
                    accepted_v10_audit_sha256=config["v10_static_audit_binding"]["sha256"],
                    accepted_v9_audit_sha256="0" * 64,
                    accepted_v8_worker_audit_sha256="0" * 64,
                )

    def test_07_v11_argument_is_stripped_before_v8_parser(self):
        audit = _sha("v11-audit")
        delegated, observed = self.worker._extract_v11_audit_and_strip(
            [
                "--live", "--nonce", _sha("nonce"),
                "--accepted-audit-sha256", _sha("v8-audit"),
                "--accepted-v11-audit-sha256", audit,
            ]
        )
        self.assertEqual(observed, audit)
        self.assertNotIn("--accepted-v11-audit-sha256", delegated)
        self.assertIn("--accepted-audit-sha256", delegated)

    def test_08_duplicate_or_malformed_v11_audit_argument_rejects(self):
        with self.assertRaises(self.contract.V11ContractError):
            self.worker._extract_v11_audit_and_strip(
                ["--live", "--accepted-v11-audit-sha256", "bad"]
            )
        digest = _sha("duplicate")
        with self.assertRaises(self.contract.V11ContractError):
            self.worker._extract_v11_audit_and_strip(
                [
                    "--live", "--accepted-v11-audit-sha256", digest,
                    "--accepted-v11-audit-sha256", digest,
                ]
            )

    def test_09_exact_v8_adapter_receives_typed_probe_and_test_restores_it(self):
        from Core import blackwell_v10_windows_memory as memory
        from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8 import (
            live_adapter,
        )

        original = live_adapter._windows_memory_mib
        try:
            with patch.object(
                self.contract,
                "verify_future_fresh_audit_authorization",
                return_value={"static_only": True, "live_authorized": False},
            ), patch.object(
                self.contract, "verify_per_run_live_capability", return_value=None
            ):
                evidence = self.worker.prepare_live_memory_integration(_sha("audit"))
            self.assertTrue(evidence["installed"])
            self.assertIs(live_adapter._windows_memory_mib, memory.windows_memory_mib)
        finally:
            live_adapter._windows_memory_mib = original
        self.assertIs(live_adapter._windows_memory_mib, original)

    def test_10_worker_import_is_inert_and_live_imports_are_branch_local(self):
        source = (PACKAGE / "worker_entry.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        top_imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                top_imports.append(node.module or "")
        self.assertFalse(any("live_adapter" in value for value in top_imports))
        self.assertNotIn("import torch", source)
        self.assertNotIn("import ollama", source)
        self.assertNotIn("import bpy", source)

    def test_11_current_main_refuses_live_before_v8_worker_delegation(self):
        source = (PACKAGE / "worker_entry.py").read_text(encoding="utf-8")
        main_start = source.index("def main()")
        main_source = source[main_start:]
        self.assertLess(
            main_source.index("return 93"),
            main_source.index("worker_entry as v8_worker_entry"),
        )

    def test_11b_current_worker_command_refuses_live_before_prepare(self):
        original = list(sys.argv)
        try:
            sys.argv = [
                "worker_entry.py", "--live", "--nonce", _sha("live-refusal")
            ]
            with patch.object(
                self.worker,
                "prepare_live_memory_integration",
                side_effect=AssertionError("live prepare must remain unreachable"),
            ):
                self.assertEqual(self.worker.main(), 93)
        finally:
            sys.argv = original

    def test_12_static_fixture_uses_exact_v9_topology_without_live_adapter(self):
        before = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.live_adapter" in sys.modules
        coordinator = self.integration.BlackwellV11Coordinator.static_fixture_candidate(
            nonce=_sha("v11-static-topology")
        )
        try:
            started = coordinator.start()
            self.assertNotEqual(started["root_pid"], started["worker_pid"])
            self.assertEqual(started["worker_direct_parent_pid"], started["root_pid"])
            echoed = coordinator._invoke("fixture_echo", {"v11": "static"})
            self.assertEqual(echoed["value"], {"v11": "static"})
        finally:
            cleanup = coordinator.close()
        self.assertTrue(cleanup["entire_bound_tree_exited"])
        self.assertTrue(cleanup["worker_child_handle_closed"])
        self.assertEqual(
            before,
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.live_adapter"
            in sys.modules,
        )

    def test_13_seal_rehashes_exact_v11_files(self):
        config = self.contract.load_canonical_config()
        seal = self.contract.verify_seal_manifest(config, SEAL_PATH)
        self.assertEqual(len(seal["files"]), 6)
        self.assertFalse(seal["live_execution_authorized"])
        self.assertFalse(seal["playback_authorized"])

    def test_14_production_route_is_exact_and_unchanged(self):
        config = self.contract.load_canonical_config()
        self.assertEqual(
            self.contract.sha256_file(ROUTING_PATH),
            config["preserved_boundaries"][
                "Voice/sidecars/kira_approved_voice_routing.json"
            ],
        )

    def test_15_closed_config_rejects_unknown_or_bool_numeric_schema(self):
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        value["unknown"] = True
        with self.assertRaises(self.contract.V11ContractError):
            self.contract._validate_config(value)
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        value["schema_version"] = True
        with self.assertRaises(self.contract.V11ContractError):
            self.contract._validate_config(value)

    def test_16_all_v11_sources_parse(self):
        for path in (
            ROOT / "Core/persistent_blackwell_voice_integration_v11.py",
            PACKAGE / "candidate_contract.py",
            PACKAGE / "worker_entry.py",
            Path(__file__),
        ):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
