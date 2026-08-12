#!/usr/bin/env python3
"""Pure/static adversarial tests for R25 AFES Attempt 05."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest

import tools
from tools import kira_r25_afes_topology_core_v5 as private_loader


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v5.json"
)
EXTRACTOR_PATH = ROOT / "tools/blender_extract_kira_r25_foundation_afes_transition_rings_v5.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_float(test: unittest.TestCase, value: object) -> None:
    test.assertNotIsInstance(value, float)
    if isinstance(value, dict):
        for child in value.values():
            no_float(test, child)
    elif isinstance(value, list):
        for child in value:
            no_float(test, child)


class CountingReader:
    def __init__(self) -> None:
        self.counts: dict[Path, int] = {}

    def __call__(self, binding: dict[str, object]) -> tuple[Path, bytes]:
        path = (ROOT / str(binding["path"])).resolve(strict=True)
        self.counts[path] = self.counts.get(path, 0) + 1
        value = path.read_bytes()
        if len(value) != binding["bytes"] or hashlib.sha256(value).hexdigest() != binding[
            "sha256"
        ]:
            raise AssertionError("test binding drifted")
        return path, value


def forged_attempt01_module(real_path: Path) -> ModuleType:
    """Build the strongest prior mutable-metadata/project-module spoof."""

    canonical = private_loader.ATTEMPT01_CANONICAL
    fake = ModuleType(canonical)
    fake.__file__ = str(real_path)
    spec = importlib.util.spec_from_file_location(canonical, real_path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not create genuine SourceFileLoader metadata")
    fake.__spec__ = spec
    fake.__loader__ = spec.loader
    fake.__package__ = "tools"
    for symbol_name in (
        "analyze_afes_topology", "canonical_index_sha256",
        "canonical_json_sha256", "normalize_edges", "normalize_faces",
    ):
        def forged(*args: object, **kwargs: object) -> object:
            return {"forged": True}
        forged.__name__ = symbol_name
        forged.__module__ = canonical
        setattr(fake, symbol_name, forged)
    error = type("AfesTopologyError", (ValueError,), {})
    error.__module__ = canonical
    fake.AfesTopologyError = error
    return fake


class Attempt05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.graph_bindings = {
            key: cls.config["bindings"][key] for key in (
                "attempt_01_topology_core_execution_dependency",
                "attempt_02_hardening_core_execution_dependency",
                "attempt_03_hardening_core_execution_dependency",
                "canonical_receipt_helper",
            )
        }

    def verify_rows(self, rows: dict[str, object]) -> None:
        for label, row in rows.items():
            with self.subTest(label=label):
                path = ROOT / row["path"]
                self.assertEqual(path.stat().st_size, row["bytes"])
                self.assertEqual(digest(path), row["sha256"])

    def test_01_attempts01_through04_are_byte_exact(self) -> None:
        for attempt in range(1, 5):
            self.verify_rows(self.config[f"attempt_{attempt:02d}_preservation"])
        self.verify_rows(self.config["bindings"])
        baseline = self.config["attempt_04_baseline_config"]
        self.assertEqual(baseline, self.config["attempt_04_preservation"]["config"])

    def test_02_hostile_ambient_dataclass_is_never_consumed(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        ambient_dataclass = dataclasses.dataclass
        receipt_name = private_loader.RECEIPT_RUNTIME_NAME
        shim_name = private_loader.DATACLASS_SHIM_RUNTIME_NAME
        old_receipt = sys.modules.get(receipt_name)
        old_shim = sys.modules.get(shim_name)
        forged_receipt = ModuleType(receipt_name)
        forged_shim = ModuleType(shim_name)

        def hostile_dataclass(*args: object, **kwargs: object) -> object:
            calls.append((args, kwargs))
            raise AssertionError("ambient dataclasses.dataclass was consumed")

        dataclasses.dataclass = hostile_dataclass
        sys.modules[receipt_name] = forged_receipt
        sys.modules[shim_name] = forged_shim
        try:
            graph = private_loader.load_private_dependency_graph(
                bindings=self.graph_bindings, read_exact=CountingReader()
            )
            self.assertEqual(calls, [])
            receipt = graph["canonical_receipt"]
            shim = graph["private_dataclass_shim"]
            self.assertIsNot(receipt, forged_receipt)
            self.assertIsNot(shim, forged_shim)
            self.assertIsNot(receipt, dataclasses)
            self.assertIsNot(shim, dataclasses)
            self.assertIs(receipt.dataclass, shim.dataclass)
            self.assertIsNot(receipt.dataclass, hostile_dataclass)
            self.assertEqual(receipt.__name__, receipt_name)
            self.assertEqual(receipt.DecodedReceipt.__module__, receipt_name)
            self.assertEqual(shim.__name__, shim_name)
            self.assertFalse(any(receipt is module for module in sys.modules.values()))
            self.assertFalse(any(shim is module for module in sys.modules.values()))
            frame = receipt.encode_receipt_frame({"hostile_ambient_ignored": True})
            decoded = receipt.decode_receipt_frame(frame)
            self.assertEqual(decoded.payload, {"hostile_ambient_ignored": True})
        finally:
            dataclasses.dataclass = ambient_dataclass
            if old_receipt is None:
                sys.modules.pop(receipt_name, None)
            else:
                sys.modules[receipt_name] = old_receipt
            if old_shim is None:
                sys.modules.pop(shim_name, None)
            else:
                sys.modules[shim_name] = old_shim

    def test_03_private_declarative_record_is_narrow_frozen_and_private(self) -> None:
        graph = private_loader.load_private_dependency_graph(
            bindings=self.graph_bindings, read_exact=CountingReader()
        )
        receipt = graph["canonical_receipt"]
        shim = graph["private_dataclass_shim"]
        frame = receipt.encode_receipt_frame({"x": 1})
        first = receipt.decode_receipt_frame(frame)
        second = receipt.decode_receipt_frame(frame)
        self.assertEqual(first, second)
        direct = receipt.DecodedReceipt(
            payload=first.payload,
            canonical_payload=first.canonical_payload,
            payload_sha256=first.payload_sha256,
            frame_sha256=first.frame_sha256,
        )
        self.assertEqual(first, direct)
        self.assertNotEqual(first, object())
        self.assertEqual(
            receipt.DecodedReceipt.__private_frozen_record_fields__,
            ("payload", "canonical_payload", "payload_sha256", "frame_sha256"),
        )
        self.assertEqual(
            receipt.DecodedReceipt.__private_dataclass_shim__,
            private_loader.DATACLASS_SHIM_RUNTIME_NAME,
        )
        for method_name in (
            "__init__", "__repr__", "__eq__", "__hash__", "__setattr__", "__delattr__"
        ):
            self.assertEqual(
                getattr(receipt.DecodedReceipt, method_name).__module__,
                private_loader.RECEIPT_RUNTIME_NAME,
            )
        with self.assertRaises(private_loader.PrivateFrozenInstanceError):
            first.payload = {"changed": True}
        with self.assertRaises(private_loader.PrivateFrozenInstanceError):
            del first.payload
        with self.assertRaises(TypeError):
            receipt.DecodedReceipt(payload={})
        with self.assertRaises(private_loader.PrivateDataclassContractError):
            shim.dataclass()
        with self.assertRaises(private_loader.PrivateDataclassContractError):
            shim.dataclass(frozen=False)
        with self.assertRaises(private_loader.PrivateDataclassContractError):
            shim.dataclass(frozen=True, slots=True)
        second_decorator = shim.dataclass(frozen=True)
        with self.assertRaises(private_loader.PrivateDataclassContractError):
            second_decorator(type("DecodedReceipt", (), {}))
        self.assertFalse(
            any(receipt.DecodedReceipt is value for value in vars(dataclasses).values())
        )

    def test_04_private_graph_retains_all_prior_hardening(self) -> None:
        reader = CountingReader()
        graph = private_loader.load_private_dependency_graph(
            bindings=self.graph_bindings, read_exact=reader
        )
        self.assertEqual(len(reader.counts), 4)
        self.assertEqual(set(reader.counts.values()), {1})
        for module in graph.values():
            self.assertFalse(any(module is value for value in sys.modules.values()))
        self.assertIs(graph["attempt03_core"].attempt01_core, graph["attempt01_core"])
        self.assertIs(graph["attempt03_core"].attempt02_core, graph["attempt02_core"])
        self.assertIs(
            graph["attempt02_core"].analyze_afes_topology,
            graph["attempt01_core"].analyze_afes_topology,
        )
        v3 = graph["attempt03_core"]
        analysis = v3.analyze_afes_topology_v3(
            vertex_count=7,
            edges=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)],
            faces=[(0, 1, 2), (2, 3, 4), (4, 5, 6)],
            memberships={"AFES_A": [2], "AFES_B": [2]},
            required_group_names=["AFES_A", "AFES_B"], transition_ring_count=2,
        )
        analysis["topology_structure"] = {
            "full_normalized_topology_sha256": analysis["whole_mesh"]["topology_sha256"],
            "connected_component_count": 1, "isolated_vertex_count": 0,
            "boundary_edge_count": 0, "nonmanifold_edge_count": 0,
            "loose_edge_count": 0, "face_boundary_edge_missing_from_mesh_count": 0,
            "duplicate_face_record_count": 0,
            "transition_ring_loose_edge_incidence_count": 0,
        }
        compact = v3.compact_afes_analysis(
            analysis,
            {"unit": "nanometer", "integer_units_per_meter": 1_000_000_000,
             "rounding": v3.ROUNDING_RULE, "minimum": [-1, -2, -3],
             "maximum": [1, 2, 3]},
        )
        self.assertEqual(
            v3.validate_compact_afes_analysis(compact)["transition_rings"],
            ((1, 3), (0, 4)),
        )

    def test_05_v5_loader_has_no_ambient_dataclasses_import_statement(self) -> None:
        tree = ast.parse((ROOT / self.config["bindings"][
            "attempt_05_private_loader_core"
        ]["path"]).read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        self.assertNotIn("dataclasses", imports)
        shim_functions = [
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_make_private_dataclass_shim"
        ]
        self.assertEqual(len(shim_functions), 1)
        shim_tree = shim_functions[0]
        self.assertFalse(
            any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(shim_tree))
        )
        self.assertFalse(
            any(isinstance(node, ast.Name) and node.id == "sys" for node in ast.walk(shim_tree))
        )

    def test_06_extractor_has_no_authoring_or_ambient_project_import_surface(self) -> None:
        source = EXTRACTOR_PATH.read_text(encoding="utf-8")
        self.assertNotIn("from tools", source)
        self.assertNotIn("import tools", source)
        self.assertIn("_bootstrap_private_loader", source)
        self.assertIn("load_private_dependency_graph(", source)
        self.assertIn("ambient_dataclasses_decorator_consumed\": 0", source)
        self.assertIn("private_receipt_runtime", source)
        self.assertIn("--result-handle", source)
        self.assertIn("require_win32_pipe_handle", source)
        self.assertNotIn("--result-path", source)
        for forbidden in (
            "bpy.ops", "--result-path", "write_text(", "write_bytes(",
            "save_as_mainfile", "render.render", "export_scene",
        ):
            self.assertNotIn(forbidden, source)

    def test_07_extractor_ledger_caches_one_physical_read(self) -> None:
        name = "_test_private_attempt05_extractor"
        fake_bpy = ModuleType("bpy")
        old_bpy = sys.modules.get("bpy")
        spec = importlib.util.spec_from_file_location(name, EXTRACTOR_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules["bpy"] = fake_bpy
        try:
            spec.loader.exec_module(module)
            ledger = module.ExactByteLedger(ROOT)
            row = self.config["bindings"]["attempt_01_topology_core_execution_dependency"]
            first = ledger.read_exact(row)
            second = ledger.read_exact(row)
            self.assertIs(first[1], second[1])
            self.assertEqual(ledger.evidence([row["path"]])[0]["physical_read_count"], 1)
        finally:
            if old_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = old_bpy

    def test_08b_strong_project_module_spoof_is_ignored_by_v5_graph(self) -> None:
        canonical = private_loader.ATTEMPT01_CANONICAL
        real_path = ROOT / self.graph_bindings[
            "attempt_01_topology_core_execution_dependency"
        ]["path"]
        fake = forged_attempt01_module(real_path)
        attribute = canonical.split(".", 1)[1]
        previous_sys = sys.modules.get(canonical)
        previous_attr = getattr(tools, attribute, None)
        sys.modules[canonical] = fake
        setattr(tools, attribute, fake)
        try:
            reader = CountingReader()
            graph = private_loader.load_private_dependency_graph(
                bindings=self.graph_bindings, read_exact=reader
            )
            self.assertIsNot(graph["attempt01_core"], fake)
            self.assertIs(
                graph["attempt03_core"].attempt01_core, graph["attempt01_core"]
            )
            self.assertIsNot(
                graph["attempt02_core"].analyze_afes_topology,
                fake.analyze_afes_topology,
            )
            self.assertEqual(set(reader.counts.values()), {1})
        finally:
            if previous_sys is None:
                sys.modules.pop(canonical, None)
            else:
                sys.modules[canonical] = previous_sys
            if previous_attr is None:
                delattr(tools, attribute)
            else:
                setattr(tools, attribute, previous_attr)

    def test_08_extractor_bootstrap_ignores_forged_ambient_v5_loader(self) -> None:
        extractor_name = "_test_private_attempt05_bootstrap"
        canonical = "tools.kira_r25_afes_topology_core_v5"
        loader_path = ROOT / self.config["bindings"]["attempt_05_private_loader_core"][
            "path"
        ]
        fake_loader = ModuleType(canonical)
        fake_loader.__file__ = str(loader_path)
        fake_spec = importlib.util.spec_from_file_location(canonical, loader_path)
        self.assertIsNotNone(fake_spec)
        self.assertIsNotNone(fake_spec.loader)
        fake_loader.__spec__ = fake_spec
        fake_loader.__loader__ = fake_spec.loader

        def forged_graph(*args: object, **kwargs: object) -> dict[str, object]:
            return {"forged": True}

        fake_loader.load_private_dependency_graph = forged_graph
        old_canonical = sys.modules.get(canonical)
        old_attribute = getattr(tools, "kira_r25_afes_topology_core_v5", None)
        old_bpy = sys.modules.get("bpy")
        sys.modules[canonical] = fake_loader
        tools.kira_r25_afes_topology_core_v5 = fake_loader
        sys.modules["bpy"] = ModuleType("bpy")
        spec = importlib.util.spec_from_file_location(extractor_name, EXTRACTOR_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        extractor = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(extractor)
            ledger = extractor.ExactByteLedger(ROOT)
            private = extractor._bootstrap_private_loader(
                self.config["bindings"]["attempt_05_private_loader_core"], ledger
            )
            self.assertIsNot(private, fake_loader)
            self.assertFalse(any(private is value for value in sys.modules.values()))
            self.assertEqual(
                Path(private.load_private_dependency_graph.__code__.co_filename).resolve(),
                loader_path.resolve(),
            )
        finally:
            if old_canonical is None:
                sys.modules.pop(canonical, None)
            else:
                sys.modules[canonical] = old_canonical
            if old_attribute is None:
                delattr(tools, "kira_r25_afes_topology_core_v5")
            else:
                tools.kira_r25_afes_topology_core_v5 = old_attribute
            if old_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = old_bpy

    def test_09_config_is_float_free_fail_closed_and_requires_fresh_audit(self) -> None:
        no_float(self, self.config)
        contract = self.config["private_exact_byte_execution_contract"]
        self.assertFalse(contract["ambient_dataclasses_import_allowed"])
        self.assertFalse(contract["ambient_dataclasses_decorator_consumption_allowed"])
        self.assertFalse(contract["ambient_dataclasses_alias_allowed"])
        self.assertFalse(contract["ambient_sys_modules_receipt_or_record_lookup_allowed"])
        self.assertTrue(contract["private_record_decorator_single_use"])
        sealing = self.config["topology_sealing_contract"]
        self.assertEqual(sealing["required_fresh_locked_matching_extractions"], 2)
        self.assertFalse(sealing["one_extraction_is_acceptance"])
        truth = self.config["truth_boundary"]
        self.assertTrue(truth["attempt_05_fresh_independent_audit_required"])
        self.assertTrue(truth["attempt_05_self_authorization_forbidden"])
        for key in (
            "controller_or_pipe_creation_implemented", "child_process_authentication_implemented",
            "replay_protection_implemented", "parent_binding_of_this_config_hash_implemented",
            "blender_execution_authorized", "body_authoring_authorized",
        ):
            self.assertFalse(truth[key])


if __name__ == "__main__":
    unittest.main()
