#!/usr/bin/env python3
"""Pure/static adversarial tests for R25 AFES Attempt 04."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest

import tools
from tools import kira_r25_afes_topology_core_v3 as ambient_v3
from tools import kira_r25_afes_topology_core_v4 as private_loader


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v4.json"
)
EXTRACTOR_PATH = ROOT / "tools/blender_extract_kira_r25_foundation_afes_transition_rings_v4.py"


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
    canonical = private_loader.ATTEMPT01_CANONICAL
    fake = ModuleType(canonical)
    fake.__file__ = str(real_path)
    spec = importlib.util.spec_from_file_location(canonical, real_path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not create genuine SourceFileLoader metadata")
    fake.__spec__ = spec
    fake.__loader__ = spec.loader
    fake.__package__ = "tools"
    for name in (
        "analyze_afes_topology", "canonical_index_sha256", "canonical_json_sha256",
        "normalize_edges", "normalize_faces",
    ):
        def forged(*args: object, **kwargs: object) -> object:
            return {"forged": True}
        forged.__name__ = name
        forged.__module__ = canonical
        setattr(fake, name, forged)
    error = type("AfesTopologyError", (ValueError,), {})
    error.__module__ = canonical
    fake.AfesTopologyError = error
    return fake


class Attempt04Tests(unittest.TestCase):
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

    def test_01_attempts01_through03_are_byte_exact(self) -> None:
        self.verify_rows(self.config["attempt_01_preservation"])
        self.verify_rows(self.config["attempt_02_preservation"])
        self.verify_rows(self.config["attempt_03_preservation"])
        self.verify_rows(self.config["bindings"])
        baseline = self.config["attempt_03_baseline_config"]
        self.assertEqual(baseline, self.config["attempt_03_preservation"]["config"])

    def test_02_private_graph_physically_reads_each_bound_source_once(self) -> None:
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

    def test_03_genuine_loader_metadata_spoof_passes_v3_but_is_ignored_by_v4(self) -> None:
        canonical = private_loader.ATTEMPT01_CANONICAL
        real_path = ROOT / self.graph_bindings[
            "attempt_01_topology_core_execution_dependency"
        ]["path"]
        fake = forged_attempt01_module(real_path)
        previous_sys = sys.modules.get(canonical)
        attribute = canonical.split(".", 1)[1]
        previous_attr = getattr(tools, attribute, None)
        sys.modules[canonical] = fake
        setattr(tools, attribute, fake)
        try:
            # Reproduce the stronger audit: mutable metadata plus the separate
            # honest disk hash is sufficient for Attempt 03 to accept the fake.
            accepted_by_v3 = ambient_v3.require_exact_imported_python_module(
                fake, expected_module_name=canonical, expected_path=real_path,
                expected_bytes=real_path.stat().st_size,
                expected_sha256=digest(real_path),
                required_symbols=("AfesTopologyError", "analyze_afes_topology",
                                  "canonical_index_sha256", "canonical_json_sha256",
                                  "normalize_edges", "normalize_faces"),
            )
            self.assertIs(accepted_by_v3, fake)
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

    def test_04_private_graph_retains_v2_v3_receipt_hardening(self) -> None:
        graph = private_loader.load_private_dependency_graph(
            bindings=self.graph_bindings, read_exact=CountingReader()
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
            "loose_edge_count": 0,
            "face_boundary_edge_missing_from_mesh_count": 0,
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
        receipt = graph["canonical_receipt"]
        frame = receipt.encode_receipt_frame({"analysis": compact})
        self.assertEqual(receipt.decode_receipt_frame(frame).payload,
                         {"analysis": compact})

    def test_05_extractor_has_no_ambient_project_import_or_authoring_surface(self) -> None:
        source = EXTRACTOR_PATH.read_text(encoding="utf-8")
        self.assertNotIn("from tools", source)
        self.assertNotIn("import tools", source)
        self.assertIn("_bootstrap_private_loader", source)
        self.assertIn("load_private_dependency_graph(", source)
        self.assertIn("ledger.read_exact", source)
        self.assertIn("private_modules_inserted_into_sys_modules\": 0", source)
        for forbidden in (
            "bpy.ops", "--result-path", "write_text(", "write_bytes(",
            "save_as_mainfile", "render.render", "export_scene",
        ):
            self.assertNotIn(forbidden, source)

    def test_06_extractor_ledger_caches_one_physical_read(self) -> None:
        name = "_test_private_attempt04_extractor"
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
            evidence = ledger.evidence([row["path"]])
            self.assertEqual(evidence[0]["physical_read_count"], 1)
        finally:
            if old_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = old_bpy

    def test_06b_extractor_bootstrap_ignores_forged_ambient_v4_loader(self) -> None:
        extractor_name = "_test_private_attempt04_bootstrap"
        canonical = "tools.kira_r25_afes_topology_core_v4"
        loader_path = ROOT / self.config["bindings"]["attempt_04_private_loader_core"][
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
        forged_graph.__module__ = canonical
        fake_loader.load_private_dependency_graph = forged_graph
        old_canonical = sys.modules.get(canonical)
        old_attribute = getattr(tools, "kira_r25_afes_topology_core_v4", None)
        old_bpy = sys.modules.get("bpy")
        sys.modules[canonical] = fake_loader
        tools.kira_r25_afes_topology_core_v4 = fake_loader
        sys.modules["bpy"] = ModuleType("bpy")
        spec = importlib.util.spec_from_file_location(extractor_name, EXTRACTOR_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        extractor = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(extractor)
            ledger = extractor.ExactByteLedger(ROOT)
            private = extractor._bootstrap_private_loader(
                self.config["bindings"]["attempt_04_private_loader_core"], ledger
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
                delattr(tools, "kira_r25_afes_topology_core_v4")
            else:
                tools.kira_r25_afes_topology_core_v4 = old_attribute
            if old_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = old_bpy

    def test_07_config_is_float_free_fail_closed_and_requires_two_runs(self) -> None:
        no_float(self, self.config)
        contract = self.config["private_exact_byte_execution_contract"]
        self.assertFalse(contract["ambient_project_sys_modules_dependencies_allowed"])
        self.assertEqual(contract["security_sources_physically_read_per_child"], 1)
        self.assertTrue(contract["exact_retained_bytes_used_for_hash_and_compile"])
        self.assertTrue(contract["ambient_metadata_or_symbol_spoof_must_be_ignored"])
        sealing = self.config["topology_sealing_contract"]
        self.assertEqual(sealing["required_fresh_locked_matching_extractions"], 2)
        self.assertFalse(sealing["one_extraction_is_acceptance"])
        truth = self.config["truth_boundary"]
        for key in (
            "controller_or_pipe_creation_implemented", "child_process_authentication_implemented",
            "replay_protection_implemented", "parent_binding_of_this_config_hash_implemented",
            "blender_execution_authorized", "body_authoring_authorized",
        ):
            self.assertFalse(truth[key])


if __name__ == "__main__":
    unittest.main()
