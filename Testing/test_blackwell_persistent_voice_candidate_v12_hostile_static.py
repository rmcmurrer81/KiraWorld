"""Hostile static tests for canonical Blackwell V12."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import math
import os
import pickle
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12"
CONFIG = PACKAGE / "candidate_config.json"
SEAL = PACKAGE / "STATIC_SEAL_MANIFEST.json"
ROUTING = ROOT / "Voice/sidecars/kira_approved_voice_routing.json"


def token(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class BlackwellV12HostileStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.candidate_contract"
        )
        cls.canonical = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.canonical_typed_memory_binding"
        )
        cls.worker = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.worker_entry"
        )
        cls.integration = importlib.import_module(
            "Core.persistent_blackwell_voice_integration_v12"
        )
        cls.heavy_before = {
            name: name in sys.modules for name in ("torch", "ollama", "chatterbox", "bpy")
        }

    def binding(self, *, installed: bool = False):
        value = self.canonical.create_canonical_typed_memory_binding()
        if installed:
            self.canonical.install_exact_typed_memory_probe(value)
        return value

    def test_01_config_is_exact_default_off_and_preserves_v11_rejection(self):
        config = self.contract.load_canonical_config()
        self.assertFalse(config["production_routing_authorized"])
        self.assertFalse(config["live_execution_authorized_by_this_candidate"])
        self.assertFalse(config["playback_authorized_by_this_candidate"])
        self.assertFalse(config["current_production_route_changed"])
        self.assertFalse(config["worker_integration_live_validated"])
        self.assertFalse(config["future_live_attempt_authorized"])
        self.assertEqual(len(self.contract.verify_preserved_bytes(config)), 28)
        rejection = self.contract.verify_v11_rejection(config)
        self.assertEqual(rejection["decision"], "REJECT")
        self.assertEqual(
            rejection["blocking_finding_ids"],
            ["BLOCK_V11_EXACT_ADAPTER_MODULE_OBJECT_NOT_BOUND"],
        )

    def test_02_config_schema_types_duplicates_and_nonfinite_fail_closed(self):
        config = self.contract.load_canonical_config()
        mutations = []
        changed = copy.deepcopy(config)
        changed["schema_version"] = True
        mutations.append(changed)
        changed = copy.deepcopy(config)
        changed["integration_contract"]["exact_executed_module_object_bound"] = 1
        mutations.append(changed)
        changed = copy.deepcopy(config)
        changed["static_test_contract"]["unknown"] = False
        mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(self.contract.V12ContractError):
                self.contract._validate_config(changed)
        with self.assertRaises(self.contract.V12ContractError):
            self.contract._strict_json(b'{"a":1,"a":2}')
        with self.assertRaises(self.contract.V12ContractError):
            self.contract._strict_json(b'{"x":NaN}')

    def test_03_v10_audit_is_static_only_and_v12_future_audit_is_absent(self):
        config = self.contract.load_canonical_config()
        v10 = self.contract.verify_v10_static_audit(config)
        self.assertIs(v10["static_only"], True)
        self.assertIs(v10["live_authorized"], False)
        audit = ROOT / config["future_fresh_audit_contract"]["required_relative_path"]
        self.assertFalse(audit.exists())
        with self.assertRaises(self.contract.V12ContractError):
            self.contract.verify_future_fresh_audit_authorization(
                config, expected_audit_sha256="0" * 64
            )

    def test_04_parent_and_worker_live_paths_refuse_before_prepare_or_process(self):
        self.assertFalse(self.integration.PRODUCTION_ROUTING_AUTHORIZED)
        self.assertFalse(self.integration.LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE)
        self.assertFalse(self.integration.PLAYBACK_AUTHORIZED)
        with self.assertRaises(self.contract.V12ContractError):
            self.integration.BlackwellV12Coordinator.production_candidate()
        with patch.object(
            self.integration.BlackwellV12Coordinator,
            "_v9_process",
            side_effect=AssertionError("no live process construction"),
        ):
            with self.assertRaises(self.contract.V12ContractError):
                self.integration.BlackwellV12Coordinator.bounded_engineering_candidate()
        original = list(sys.argv)
        try:
            sys.argv = ["worker_entry.py", "--live", "--nonce", token("v12-live")]
            with patch.object(
                self.worker,
                "prepare_future_harness_memory_binding",
                side_effect=AssertionError("prepare remains unreachable"),
            ):
                self.assertEqual(self.worker.main(), 96)
        finally:
            sys.argv = original

    def test_05_worker_mode_and_audit_argument_parser_is_fail_closed(self):
        digest = token("v12-audit")
        delegated, observed = self.worker._extract_v12_audit_and_strip(
            ["--live", "--accepted-v12-audit-sha256", digest]
        )
        self.assertEqual(observed, digest)
        self.assertNotIn("--accepted-v12-audit-sha256", delegated)
        with self.assertRaises(self.contract.V12ContractError):
            self.worker._extract_v12_audit_and_strip(
                ["--live", "--accepted-v12-audit-sha256", "bad"]
            )
        original = list(sys.argv)
        try:
            sys.argv = ["worker_entry.py"]
            self.assertEqual(self.worker.main(), 94)
        finally:
            sys.argv = original

    def test_06_binding_is_opaque_uncopyable_and_not_normal_import_state(self):
        value = self.binding()
        self.assertNotIn(self.canonical.V8_ADAPTER_NAME, sys.modules)
        self.assertNotIn(self.canonical.V10_MEMORY_NAME, sys.modules)
        self.assertNotIn(self.canonical.PRIVATE_ADAPTER_NAME, sys.modules)
        self.assertNotIn(self.canonical.PRIVATE_MEMORY_NAME, sys.modules)
        with self.assertRaises(TypeError):
            copy.copy(value)
        with self.assertRaises(TypeError):
            copy.deepcopy(value)
        with self.assertRaises(TypeError):
            pickle.dumps(value)
        with self.assertRaises(TypeError):
            self.canonical.CanonicalTypedMemoryBinding()

    def test_07_v11_forged_namespace_and_proxy_are_rejected(self):
        def _windows_memory_mib():
            return None

        forged = types.SimpleNamespace(
            __file__=str(self.canonical.V8_ADAPTER_PATH),
            _windows_memory_mib=_windows_memory_mib,
        )
        for operation in (
            self.canonical.install_exact_typed_memory_probe,
            self.canonical.revalidate_exact_typed_memory_probe,
            self.canonical.read_exact_typed_memory_mib,
        ):
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                operation(forged)

    def test_08_preexisting_sys_modules_adapter_poison_is_rejected(self):
        name = self.canonical.V8_ADAPTER_NAME
        sentinel = object()
        previous = sys.modules.get(name, sentinel)
        try:
            fake = types.ModuleType(name)
            fake.__file__ = str(self.canonical.V8_ADAPTER_PATH)
            sys.modules[name] = fake
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "pre-existing module"
            ):
                self.binding()
        finally:
            if previous is sentinel:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous

    def test_09_preexisting_package_adapter_poison_is_rejected(self):
        package = importlib.import_module(self.canonical.V8_ADAPTER_PARENT)
        sentinel = object()
        previous = getattr(package, "live_adapter", sentinel)
        try:
            package.live_adapter = types.SimpleNamespace(
                __file__=str(self.canonical.V8_ADAPTER_PATH)
            )
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "package attribute"
            ):
                self.binding()
        finally:
            if previous is sentinel:
                delattr(package, "live_adapter")
            else:
                package.live_adapter = previous

    def test_10_preexisting_v10_module_or_package_poison_is_rejected(self):
        name = self.canonical.V10_MEMORY_NAME
        parent = importlib.import_module(self.canonical.V10_MEMORY_PARENT)
        sentinel = object()
        previous_module = sys.modules.get(name, sentinel)
        previous_attribute = getattr(parent, "blackwell_v10_windows_memory", sentinel)
        try:
            sys.modules[name] = types.ModuleType(name)
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                self.binding()
            sys.modules.pop(name, None)
            parent.blackwell_v10_windows_memory = object()
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                self.binding()
        finally:
            if previous_module is sentinel:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous_module
            if previous_attribute is sentinel:
                try:
                    delattr(parent, "blackwell_v10_windows_memory")
                except AttributeError:
                    pass
            else:
                parent.blackwell_v10_windows_memory = previous_attribute

    def test_11_install_binds_exact_private_objects_and_readback(self):
        value = self.binding()
        evidence = self.canonical.install_exact_typed_memory_probe(value)
        self.assertTrue(evidence["installed"])
        self.assertFalse(evidence["quarantined"])
        self.assertFalse(evidence["live_backend_constructed"])
        self.assertEqual(evidence["revision"], 1)
        self.assertIs(
            value._adapter_module._windows_memory_mib, value._memory_probe
        )
        self.assertIs(value._adapter_original.__globals__, value._adapter_module.__dict__)
        self.assertIs(value._memory_probe.__globals__, value._memory_module.__dict__)
        self.assertEqual(
            self.canonical.revalidate_exact_typed_memory_probe(value)["binding_sha256"],
            evidence["binding_sha256"],
        )

    def test_12_swapped_original_code_is_rejected_and_restorable(self):
        value = self.binding()
        function = value._adapter_original
        original = function.__code__
        try:
            function.__code__ = (lambda: (0.0, 0.0, 0.0, 0.0)).__code__
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "code object identity"
            ):
                value.revalidate()
        finally:
            function.__code__ = original
        value.revalidate()

    def test_13_swapped_defaults_and_annotations_are_rejected(self):
        value = self.binding()
        function = value._adapter_original
        defaults = function.__defaults__
        annotations = function.__annotations__
        try:
            function.__defaults__ = ()
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                value.revalidate()
            function.__defaults__ = defaults
            function.__annotations__ = dict(annotations)
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                value.revalidate()
        finally:
            function.__defaults__ = defaults
            function.__annotations__ = annotations
        value.revalidate()

    def test_14_swapped_referenced_global_is_rejected(self):
        value = self.binding()
        module = value._adapter_module
        original = module.__dict__["ctypes"]
        try:
            module.__dict__["ctypes"] = object()
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "global changed"
            ):
                value.revalidate()
        finally:
            module.__dict__["ctypes"] = original
        value.revalidate()

    def test_15_callable_proxy_and_changed_closure_are_rejected(self):
        value = self.binding()
        module = value._adapter_module
        original = module.__dict__["_windows_memory_mib"]

        class Proxy:
            def __call__(self):
                return (1.0, 1.0, 1.0, 1.0)

        try:
            module.__dict__["_windows_memory_mib"] = Proxy()
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                value.revalidate()
        finally:
            module.__dict__["_windows_memory_mib"] = original

        test_module = types.ModuleType("closure_probe")
        exec(
            "def make_closure():\n"
            "    captured = ['first']\n"
            "    def closure_function():\n"
            "        return captured[0]\n"
            "    return closure_function, captured\n",
            test_module.__dict__,
        )
        closure_function, captured = test_module.make_closure()
        seal = self.canonical._FunctionSeal(
            closure_function, test_module, label="closure hostile probe"
        )
        captured[0] = "changed"
        with self.assertRaisesRegex(
            self.canonical.V12CanonicalBindingError, "closure contents"
        ):
            seal.verify(label="closure hostile probe")

    def test_16_module_spec_loader_path_and_global_schema_swaps_reject(self):
        value = self.binding()
        module = value._adapter_module
        original_origin = value._adapter_spec.origin
        original_loader = module.__loader__
        try:
            value._adapter_spec.origin = "forged"
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                value.revalidate()
            value._adapter_spec.origin = original_origin
            module.__loader__ = object()
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                value.revalidate()
            module.__loader__ = original_loader
            module.__dict__["forged_global"] = True
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                value.revalidate()
        finally:
            value._adapter_spec.origin = original_origin
            module.__loader__ = original_loader
            module.__dict__.pop("forged_global", None)
        value.revalidate()

    def test_17_poison_added_after_install_is_rejected_at_next_authority_use(self):
        value = self.binding(installed=True)
        name = self.canonical.V8_ADAPTER_NAME
        try:
            sys.modules[name] = types.ModuleType(name)
            with self.assertRaises(self.canonical.V12CanonicalBindingError):
                self.canonical.read_exact_typed_memory_mib(value)
        finally:
            sys.modules.pop(name, None)
        value.revalidate()

    def test_18_stored_installer_or_probe_swap_is_rejected_before_call(self):
        value = self.binding()
        original_installer = value._memory_installer
        try:
            value._memory_installer = lambda _module: {"installed": True}
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "stored v10 installer"
            ):
                value.install()
        finally:
            value._memory_installer = original_installer
        value.install()
        original_probe = value._memory_probe
        try:
            value._memory_probe = lambda: (1.0, 1.0, 1.0, 1.0)
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "stored v10 probe"
            ):
                value.memory_values()
        finally:
            value._memory_probe = original_probe
        value.revalidate()

    def test_19_post_install_source_toctou_rolls_back_exactly(self):
        value = self.binding()
        original_verify = self.canonical._verify_source
        calls = {"count": 0}

        def fail_once(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 3:
                raise self.canonical.V12CanonicalBindingError(
                    "forced post-install source TOCTOU"
                )
            return original_verify(*args, **kwargs)

        with patch.object(self.canonical, "_verify_source", side_effect=fail_once):
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "forced post-install"
            ):
                value.install()
        self.assertFalse(value._installed)
        self.assertEqual(value._revision, 0)
        self.assertIs(value._adapter_module._windows_memory_mib, value._adapter_original)
        value.revalidate()

    def test_20_post_telemetry_source_toctou_returns_no_values(self):
        value = self.binding(installed=True)
        original_verify = self.canonical._verify_source
        calls = {"count": 0}

        def fail_once(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 3:
                raise self.canonical.V12CanonicalBindingError(
                    "forced post-telemetry source TOCTOU"
                )
            return original_verify(*args, **kwargs)

        with patch.object(self.canonical, "_verify_source", side_effect=fail_once):
            with self.assertRaisesRegex(
                self.canonical.V12CanonicalBindingError, "forced post-telemetry"
            ):
                value.memory_values()
        value.revalidate()

    def test_21_integrated_prepare_uses_canonical_binding_and_exact_readback(self):
        with patch.object(
            self.contract,
            "verify_future_fresh_audit_authorization",
            return_value={"static_only": True, "live_authorized": False},
        ), patch.object(
            self.contract, "verify_outer_preparation_opt_in", return_value=None
        ):
            binding, evidence = self.worker.prepare_future_harness_memory_binding(
                token("future-v12-audit")
            )
        self.assertTrue(evidence["installed"])
        self.assertFalse(evidence["live_backend_constructed"])
        self.assertEqual(binding.revalidate()["binding_sha256"], evidence["binding_sha256"])
        self.assertNotIn(self.canonical.V8_ADAPTER_NAME, sys.modules)
        self.assertNotIn(self.canonical.V10_MEMORY_NAME, sys.modules)

    def test_22_integrated_prepare_rejects_v11_sysmodules_poison_variant(self):
        name = self.canonical.V8_ADAPTER_NAME
        fake = types.ModuleType(name)
        fake.__file__ = str(self.canonical.V8_ADAPTER_PATH)
        try:
            sys.modules[name] = fake
            with patch.object(
                self.contract,
                "verify_future_fresh_audit_authorization",
                return_value={"static_only": True, "live_authorized": False},
            ), patch.object(
                self.contract, "verify_outer_preparation_opt_in", return_value=None
            ):
                with self.assertRaisesRegex(
                    self.canonical.V12CanonicalBindingError, "pre-existing module"
                ):
                    self.worker.prepare_future_harness_memory_binding(
                        token("poisoned-v12-audit")
                    )
        finally:
            sys.modules.pop(name, None)

    def test_22b_integrated_prepare_rechecks_dependencies_after_install(self):
        original = self.contract.verify_preserved_bytes
        calls = {"count": 0}

        def fail_post_prepare(config):
            calls["count"] += 1
            if calls["count"] == 2:
                raise self.contract.V12ContractError(
                    "forced post-prepare dependency TOCTOU"
                )
            return original(config)

        with patch.object(
            self.contract,
            "verify_future_fresh_audit_authorization",
            return_value={"static_only": True, "live_authorized": False},
        ), patch.object(
            self.contract, "verify_outer_preparation_opt_in", return_value=None
        ), patch.object(
            self.contract,
            "verify_preserved_bytes",
            side_effect=fail_post_prepare,
        ):
            with self.assertRaisesRegex(
                self.contract.V12ContractError, "post-prepare dependency TOCTOU"
            ):
                self.worker.prepare_future_harness_memory_binding(
                    token("future-v12-audit-post-prepare-toctou")
                )
        self.assertEqual(calls["count"], 2)

    def test_23_real_memory_values_are_strict_finite_typed(self):
        value = self.binding(installed=True)
        values = self.canonical.read_exact_typed_memory_mib(value)
        self.assertEqual(len(values), 4)
        self.assertTrue(all(type(item) is float for item in values))
        self.assertTrue(all(math.isfinite(item) and item >= 0 for item in values))
        self.assertGreater(values[0], 0)
        self.assertGreater(values[2], 0)
        self.assertLessEqual(values[1], values[2])

    def test_24_static_topology_identity_and_cleanup_are_exact(self):
        coordinator = self.integration.BlackwellV12Coordinator.static_fixture_candidate(
            nonce=token("v12-static-topology")
        )
        try:
            started = coordinator.start()
            self.assertNotEqual(started["root_pid"], started["worker_pid"])
            self.assertEqual(started["worker_direct_parent_pid"], started["root_pid"])
            self.assertTrue(started["worker_child_job_proof"]["same_retained_job"])
            echoed = coordinator._invoke("fixture_echo", {"v12": "static"})
            self.assertEqual(echoed["value"], {"v12": "static"})
            self.assertEqual(
                echoed["process_identity_digest"],
                started["worker_process_identity_digest"],
            )
        finally:
            cleanup = coordinator.close()
        self.assertTrue(cleanup["entire_bound_tree_exited"])
        self.assertTrue(cleanup["worker_child_handle_closed"])
        self.assertTrue(cleanup["job_handle_closed"])
        self.assertTrue(cleanup["root_standard_streams_closed"])
        self.assertEqual(cleanup["errors"], [])

    def test_25_seal_and_production_route_are_exact(self):
        config = self.contract.load_canonical_config()
        seal = self.contract.verify_seal_manifest(config, SEAL)
        self.assertEqual(len(seal["files"]), 7)
        self.assertFalse(seal["live_execution_authorized"])
        self.assertFalse(seal["playback_authorized"])
        self.assertEqual(
            self.contract.sha256_file(ROUTING),
            config["preserved_boundaries"]["Voice/sidecars/kira_approved_voice_routing.json"],
        )

    def test_26_sources_parse_and_no_heavy_module_was_loaded(self):
        for path in (
            ROOT / "Core/persistent_blackwell_voice_integration_v12.py",
            PACKAGE / "candidate_contract.py",
            PACKAGE / "canonical_typed_memory_binding.py",
            PACKAGE / "worker_entry.py",
            Path(__file__),
        ):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, was_loaded in self.heavy_before.items():
            self.assertEqual(was_loaded, name in sys.modules, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
