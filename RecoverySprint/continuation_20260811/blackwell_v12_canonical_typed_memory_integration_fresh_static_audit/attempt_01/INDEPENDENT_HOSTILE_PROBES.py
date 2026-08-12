from __future__ import annotations

import hashlib
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12 import (
    candidate_contract as contract,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12 import (
    canonical_typed_memory_binding as canonical,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12 import (
    worker_entry as worker,
)
from Core import persistent_blackwell_voice_integration_v12 as integration


CANONICAL_NAME = (
    "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12."
    "canonical_typed_memory_binding"
)
CANONICAL_PARENT = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12"
ROUTING = ROOT / "Voice/sidecars/kira_approved_voice_routing.json"
ROUTING_SHA256 = "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class IndependentV12HostileProbes(unittest.TestCase):
    def binding(self, *, installed: bool = False):
        value = canonical.create_canonical_typed_memory_binding()
        if installed:
            canonical.install_exact_typed_memory_probe(value)
        return value

    def test_01_seal_checkpoint_subjects_and_28_predecessors_are_exact(self):
        config = contract.load_canonical_config()
        self.assertEqual(len(contract.verify_preserved_bytes(config)), 28)
        manifest = contract.verify_seal_manifest(
            config,
            ROOT / config["future_fresh_audit_contract"]["required_seal_manifest_path"],
        )
        self.assertEqual(len(manifest["files"]), 7)
        self.assertEqual(
            digest(
                ROOT
                / "RecoverySprint/continuation_20260811/"
                "blackwell_v12_canonical_typed_memory_integration_static_preparation/"
                "attempt_01/CHECKPOINT.md"
            ),
            "c9725313ac1730e3e6346211dd94b09c5ea0dbf46f7ec8bf3f530b4b93033d54",
        )

    def test_02_default_off_live_refusal_and_production_route_are_exact(self):
        self.assertIs(integration.PRODUCTION_ROUTING_AUTHORIZED, False)
        self.assertIs(integration.LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE, False)
        self.assertIs(integration.PLAYBACK_AUTHORIZED, False)
        with self.assertRaises(contract.V12ContractError):
            integration.BlackwellV12Coordinator.production_candidate()
        with self.assertRaises(contract.V12ContractError):
            integration.BlackwellV12Coordinator.bounded_engineering_candidate()
        self.assertEqual(digest(ROUTING), ROUTING_SHA256)

    def test_03_forged_adapter_file_and_callable_names_are_rejected(self):
        def _windows_memory_mib():
            return (1.0, 1.0, 1.0, 1.0)

        forged = types.SimpleNamespace(
            __file__=str(canonical.V8_ADAPTER_PATH),
            __name__=canonical.PRIVATE_ADAPTER_NAME,
            _windows_memory_mib=_windows_memory_mib,
        )
        for operation in (
            canonical.install_exact_typed_memory_probe,
            canonical.revalidate_exact_typed_memory_probe,
            canonical.read_exact_typed_memory_mib,
        ):
            with self.assertRaises(canonical.V12CanonicalBindingError):
                operation(forged)

    def test_04_exact_module_subclass_and_function_proxy_are_rejected(self):
        class ModuleSubclass(types.ModuleType):
            pass

        class FunctionProxy:
            __name__ = "_windows_memory_mib"
            __qualname__ = "_windows_memory_mib"
            __module__ = canonical.PRIVATE_ADAPTER_NAME

            def __call__(self):
                return (1.0, 1.0, 1.0, 1.0)

        value = self.binding()
        original_module = value._adapter_module
        original_callable = original_module.__dict__["_windows_memory_mib"]
        try:
            value._adapter_module = ModuleSubclass(canonical.PRIVATE_ADAPTER_NAME)
            with self.assertRaises(canonical.V12CanonicalBindingError):
                value.revalidate()
            value._adapter_module = original_module
            original_module.__dict__["_windows_memory_mib"] = FunctionProxy()
            with self.assertRaises(canonical.V12CanonicalBindingError):
                value.revalidate()
        finally:
            value._adapter_module = original_module
            original_module.__dict__["_windows_memory_mib"] = original_callable
        value.revalidate()

    def test_05_v8_and_v10_sysmodules_and_package_poisoning_are_rejected(self):
        cases = (
            (canonical.V8_ADAPTER_NAME, canonical.V8_ADAPTER_PARENT, "live_adapter"),
            (
                canonical.V10_MEMORY_NAME,
                canonical.V10_MEMORY_PARENT,
                "blackwell_v10_windows_memory",
            ),
        )
        missing = object()
        for name, parent_name, attribute in cases:
            parent = importlib.import_module(parent_name)
            old_module = sys.modules.get(name, missing)
            old_attribute = getattr(parent, attribute, missing)
            try:
                sys.modules[name] = types.ModuleType(name)
                with self.assertRaises(canonical.V12CanonicalBindingError):
                    self.binding()
                sys.modules.pop(name, None)
                setattr(parent, attribute, object())
                with self.assertRaises(canonical.V12CanonicalBindingError):
                    self.binding()
            finally:
                if old_module is missing:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = old_module
                if old_attribute is missing:
                    try:
                        delattr(parent, attribute)
                    except AttributeError:
                        pass
                else:
                    setattr(parent, attribute, old_attribute)

    def test_06_altered_code_defaults_globals_and_closure_are_rejected(self):
        value = self.binding()
        function = value._memory_probe
        old_code = function.__code__
        old_defaults = function.__defaults__
        referenced_name, referenced_value = value._memory_probe_seal.referenced_globals[0]
        try:
            function.__code__ = (lambda: (1.0, 1.0, 1.0, 1.0)).__code__
            with self.assertRaises(canonical.V12CanonicalBindingError):
                value.revalidate()
            function.__code__ = old_code
            function.__defaults__ = ()
            with self.assertRaises(canonical.V12CanonicalBindingError):
                value.revalidate()
            function.__defaults__ = old_defaults
            function.__globals__[referenced_name] = object()
            with self.assertRaises(canonical.V12CanonicalBindingError):
                value.revalidate()
        finally:
            function.__code__ = old_code
            function.__defaults__ = old_defaults
            function.__globals__[referenced_name] = referenced_value
        value.revalidate()

        probe_module = types.ModuleType("independent_closure_probe")
        exec(
            "def maker():\n"
            "    captured = ['sealed']\n"
            "    def probe():\n"
            "        return captured[0]\n"
            "    return probe, captured\n",
            probe_module.__dict__,
        )
        probe, captured = probe_module.maker()
        seal = canonical._FunctionSeal(probe, probe_module, label="independent closure")
        captured[0] = "changed"
        with self.assertRaises(canonical.V12CanonicalBindingError):
            seal.verify(label="independent closure")

    def test_07_typed_helper_requires_exact_binding_and_exact_probe_identity(self):
        value = self.binding(installed=True)
        self.assertIs(value._adapter_module._windows_memory_mib, value._memory_probe)
        self.assertIs(value._memory_probe, value._memory_probe_seal.function)
        self.assertIs(value._memory_probe.__globals__, value._memory_module.__dict__)
        with self.assertRaises(canonical.V12CanonicalBindingError):
            canonical.install_exact_typed_memory_probe(types.SimpleNamespace(_seal=value._seal))

    def test_08_toctou_before_install_fails_closed(self):
        value = self.binding()
        with patch.object(
            canonical,
            "_verify_source",
            side_effect=canonical.V12CanonicalBindingError("before install TOCTOU"),
        ):
            with self.assertRaisesRegex(
                canonical.V12CanonicalBindingError, "before install TOCTOU"
            ):
                value.install()
        value.revalidate()

    def test_09_toctou_after_install_rolls_back_before_return(self):
        value = self.binding()
        original = canonical._verify_source
        calls = {"count": 0}

        def fail_post_install(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 3:
                raise canonical.V12CanonicalBindingError("after install TOCTOU")
            return original(*args, **kwargs)

        with patch.object(canonical, "_verify_source", side_effect=fail_post_install):
            with self.assertRaisesRegex(
                canonical.V12CanonicalBindingError, "after install TOCTOU"
            ):
                value.install()
        self.assertIs(value._installed, False)
        self.assertIs(value._adapter_module._windows_memory_mib, value._adapter_original)
        value.revalidate()

    def test_10_toctou_after_prepare_dependency_check_returns_no_binding(self):
        original = contract.verify_preserved_bytes
        calls = {"count": 0}

        def fail_second(config):
            calls["count"] += 1
            if calls["count"] == 2:
                raise contract.V12ContractError("after prepare TOCTOU")
            return original(config)

        with patch.object(
            contract,
            "verify_future_fresh_audit_authorization",
            return_value={"static_only": True, "live_authorized": False},
        ), patch.object(
            contract, "verify_outer_preparation_opt_in", return_value=None
        ), patch.object(contract, "verify_preserved_bytes", side_effect=fail_second):
            with self.assertRaisesRegex(contract.V12ContractError, "after prepare TOCTOU"):
                worker.prepare_future_harness_memory_binding(token("audit-toctou"))

    def test_11_canonical_module_replacement_after_binding_must_fail_closed(self):
        value = self.binding(installed=True)
        parent = importlib.import_module(CANONICAL_PARENT)
        old_module = sys.modules[CANONICAL_NAME]
        old_attribute = parent.canonical_typed_memory_binding
        fake = types.ModuleType(CANONICAL_NAME)
        try:
            sys.modules[CANONICAL_NAME] = fake
            parent.canonical_typed_memory_binding = fake
            with self.assertRaises(canonical.V12CanonicalBindingError):
                value.revalidate()
        finally:
            sys.modules[CANONICAL_NAME] = old_module
            parent.canonical_typed_memory_binding = old_attribute
        value.revalidate()

    def test_12_integrated_prepare_must_reject_replaced_canonical_module(self):
        parent = importlib.import_module(CANONICAL_PARENT)
        old_module = sys.modules[CANONICAL_NAME]
        old_attribute = parent.canonical_typed_memory_binding
        fake = types.ModuleType(CANONICAL_NAME)
        forged_binding = object()
        readback = {
            "schema": "forged",
            "binding_sha256": "f" * 64,
            "revision": 1,
            "installed": True,
            "quarantined": False,
        }
        evidence = dict(readback)
        evidence["installer_evidence"] = {"forged": True}
        fake.create_canonical_typed_memory_binding = lambda: forged_binding
        fake.install_exact_typed_memory_probe = lambda binding: dict(evidence)
        fake.revalidate_exact_typed_memory_probe = lambda binding: dict(readback)
        try:
            sys.modules[CANONICAL_NAME] = fake
            parent.canonical_typed_memory_binding = fake
            with patch.object(
                contract,
                "verify_future_fresh_audit_authorization",
                return_value={"static_only": True, "live_authorized": False},
            ), patch.object(
                contract, "verify_outer_preparation_opt_in", return_value=None
            ):
                with self.assertRaises((contract.V12ContractError, canonical.V12CanonicalBindingError)):
                    worker.prepare_future_harness_memory_binding(token("canonical-poison"))
        finally:
            sys.modules[CANONICAL_NAME] = old_module
            parent.canonical_typed_memory_binding = old_attribute

    def test_13_canonical_validator_global_replacement_must_not_bypass_poison(self):
        value = self.binding(installed=True)
        old_clean = canonical._ensure_import_slots_clean
        name = canonical.V8_ADAPTER_NAME
        try:
            canonical._ensure_import_slots_clean = lambda: None
            sys.modules[name] = types.ModuleType(name)
            with self.assertRaises(canonical.V12CanonicalBindingError):
                value.revalidate()
        finally:
            sys.modules.pop(name, None)
            canonical._ensure_import_slots_clean = old_clean
        value.revalidate()

    def test_14_future_authorization_and_candidate_live_outputs_are_absent(self):
        config = contract.load_canonical_config()
        authorization = ROOT / config["future_fresh_audit_contract"]["required_relative_path"]
        self.assertFalse(authorization.exists())
        for path in (
            ROOT / "Voice/generated/chatterbox_blackwell_persistent_candidate_v12",
            ROOT / "RecoverySprint/continuation_20260811/blackwell_v12_live_attempt",
        ):
            self.assertFalse(path.exists())

    def test_15_no_heavy_or_body_media_modules_loaded_by_probes(self):
        for name in ("ollama", "torch", "chatterbox", "bpy"):
            self.assertNotIn(name, sys.modules)


if __name__ == "__main__":
    unittest.main(verbosity=2)
