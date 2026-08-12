#!/usr/bin/env python3
"""Pure-Python verification for append-only R25 AFES Attempt 03."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest

from tools import kira_r25_afes_topology_core as attempt01_core
from tools import kira_r25_afes_topology_core_v2 as attempt02_core
from tools import kira_r25_afes_topology_core_v3 as core
from tools import kira_r25_canonical_receipt as receipt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v3.json"
)
CORE_SOURCE = ROOT / "tools/kira_r25_afes_topology_core_v3.py"
EXTRACTOR = ROOT / "tools/blender_extract_kira_r25_foundation_afes_transition_rings_v3.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_no_float(test: unittest.TestCase, value: object) -> None:
    test.assertNotIsInstance(value, float)
    if isinstance(value, dict):
        for child in value.values():
            assert_no_float(test, child)
    elif isinstance(value, list):
        for child in value:
            assert_no_float(test, child)


ATTEMPT01_SYMBOLS = (
    "AfesTopologyError", "analyze_afes_topology", "canonical_index_sha256",
    "canonical_json_sha256", "normalize_edges", "normalize_faces",
)


class Attempt03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def _verify_rows(self, rows: dict[str, object]) -> None:
        for label, row in rows.items():
            with self.subTest(label=label):
                path = ROOT / row["path"]
                self.assertEqual(path.stat().st_size, row["bytes"])
                self.assertEqual(sha256(path), row["sha256"])

    def test_01_attempt01_and_attempt02_are_byte_exact(self) -> None:
        self._verify_rows(self.config["attempt_01_preservation"])
        self._verify_rows(self.config["attempt_02_preservation"])
        baseline = self.config["attempt_02_baseline_config"]
        self.assertEqual(baseline, self.config["attempt_02_preservation"]["config"])
        baseline_json = json.loads((ROOT / baseline["path"]).read_text(encoding="utf-8"))
        self._verify_rows(baseline_json["bindings"])
        self._verify_rows(baseline_json["attempt_01_preservation"])

    def test_02_attempt01_core_is_an_exact_execution_binding(self) -> None:
        row = self.config["bindings"]["attempt_01_topology_core_execution_dependency"]
        self.assertEqual(row, self.config["attempt_01_preservation"]["topology_core"])
        self._verify_rows(self.config["bindings"])
        verified = core.require_exact_imported_python_module(
            attempt01_core,
            expected_module_name="tools.kira_r25_afes_topology_core",
            expected_path=ROOT / row["path"],
            expected_bytes=row["bytes"], expected_sha256=row["sha256"],
            required_symbols=ATTEMPT01_SYMBOLS,
        )
        self.assertIs(verified, attempt01_core)
        self.assertIs(core.attempt01_core, attempt01_core)

    def test_03_v3_core_imports_attempt01_as_module_not_copied_symbols(self) -> None:
        source = CORE_SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "from tools import kira_r25_afes_topology_core as attempt01_core", source
        )
        self.assertNotIn("from tools.kira_r25_afes_topology_core import", source)
        self.assertIn("attempt01_core.analyze_afes_topology(", source)
        self.assertIn("attempt01_core.canonical_json_sha256(value)", source)

    def test_04_fake_sys_modules_in_memory_attempt01_core_is_rejected(self) -> None:
        name = "tools.kira_r25_afes_topology_core"
        real = sys.modules[name]
        fake = ModuleType(name)
        for symbol_name in ATTEMPT01_SYMBOLS:
            if symbol_name == "AfesTopologyError":
                symbol = type("AfesTopologyError", (ValueError,), {})
            else:
                def symbol(*args: object, **kwargs: object) -> object:
                    return {}
            symbol.__module__ = name
            setattr(fake, symbol_name, symbol)
        sys.modules[name] = fake
        try:
            with self.assertRaises(core.ExactExecutionModuleError):
                core.require_exact_imported_python_module(
                    sys.modules[name], expected_module_name=name,
                    expected_path=Path(real.__file__),
                    expected_bytes=Path(real.__file__).stat().st_size,
                    expected_sha256=sha256(Path(real.__file__)),
                    required_symbols=ATTEMPT01_SYMBOLS,
                )
            # Even spoofing __file__ is insufficient: the in-memory module has
            # no file-backed import spec/loader and remains rejected.
            fake.__file__ = real.__file__
            with self.assertRaises(core.ExactExecutionModuleError):
                core.require_exact_imported_python_module(
                    sys.modules[name], expected_module_name=name,
                    expected_path=Path(real.__file__),
                    expected_bytes=Path(real.__file__).stat().st_size,
                    expected_sha256=sha256(Path(real.__file__)),
                    required_symbols=ATTEMPT01_SYMBOLS,
                )
        finally:
            sys.modules[name] = real
        self.assertIs(sys.modules[name], attempt01_core)

    def test_05_wrong_file_hash_is_rejected_before_analysis(self) -> None:
        path = Path(attempt01_core.__file__)
        with self.assertRaises(core.ExactExecutionModuleError):
            core.require_exact_imported_python_module(
                attempt01_core, expected_module_name=attempt01_core.__name__,
                expected_path=path, expected_bytes=path.stat().st_size,
                expected_sha256="0" * 64, required_symbols=ATTEMPT01_SYMBOLS,
            )

    def test_05b_exact_extractor_verifier_rejects_fake_sys_modules_dependency(self) -> None:
        extractor_name = (
            "tools.blender_extract_kira_r25_foundation_afes_transition_rings_v3"
        )
        original_bpy = sys.modules.get("bpy")
        original_extractor = sys.modules.get(extractor_name)
        original_attempt01 = sys.modules[attempt01_core.__name__]
        fake_bpy = ModuleType("bpy")
        fake_attempt01 = ModuleType(attempt01_core.__name__)
        spec = importlib.util.spec_from_file_location(extractor_name, EXTRACTOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        extractor = importlib.util.module_from_spec(spec)
        sys.modules["bpy"] = fake_bpy
        sys.modules[extractor_name] = extractor
        try:
            spec.loader.exec_module(extractor)
            sys.modules[attempt01_core.__name__] = fake_attempt01
            extractor.attempt01_core = fake_attempt01
            with self.assertRaises(extractor.R25AfesAttempt03Error):
                extractor._verify_execution_modules(self.config["bindings"])
        finally:
            sys.modules[attempt01_core.__name__] = original_attempt01
            if original_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = original_bpy
            if original_extractor is None:
                sys.modules.pop(extractor_name, None)
            else:
                sys.modules[extractor_name] = original_extractor

    def test_06_v3_analysis_matches_v2_hardening_exactly(self) -> None:
        kwargs = dict(
            vertex_count=7,
            edges=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)],
            faces=[(0, 1, 2), (2, 3, 4), (4, 5, 6)],
            memberships={"AFES_A": [2], "AFES_B": [2]},
            required_group_names=["AFES_A", "AFES_B"],
            transition_ring_count=2,
        )
        v2 = attempt02_core.analyze_afes_topology_v2(**kwargs)
        v3 = core.analyze_afes_topology_v3(**kwargs)
        self.assertEqual(v3, v2)
        v3["topology_structure"] = {
            "full_normalized_topology_sha256": v3["whole_mesh"]["topology_sha256"],
            "connected_component_count": 1, "isolated_vertex_count": 0,
            "boundary_edge_count": 0, "nonmanifold_edge_count": 0,
            "loose_edge_count": 0,
            "face_boundary_edge_missing_from_mesh_count": 0,
            "duplicate_face_record_count": 0,
            "transition_ring_loose_edge_incidence_count": 0,
        }
        compact = core.compact_afes_analysis(
            v3,
            {"unit": "nanometer", "integer_units_per_meter": 1_000_000_000,
             "rounding": core.ROUNDING_RULE, "minimum": [-1, -2, -3],
             "maximum": [1, 2, 3]},
        )
        self.assertEqual(
            core.validate_compact_afes_analysis(compact)["transition_rings"],
            ((1, 3), (0, 4)),
        )
        frame = receipt.encode_receipt_frame({"analysis": compact})
        self.assertEqual(receipt.decode_receipt_frame(frame).payload, {"analysis": compact})

    def test_07_extractor_verifies_module_file_before_analysis(self) -> None:
        source = EXTRACTOR.read_text(encoding="utf-8")
        self.assertIn(
            "from tools import kira_r25_afes_topology_core as attempt01_core", source
        )
        self.assertNotIn("from tools.kira_r25_afes_topology_core import", source)
        verify_call = source.index("_verify_execution_modules(execution)")
        analysis_call = source.index("topology_core.analyze_afes_topology_v3(")
        self.assertLess(verify_call, analysis_call)
        self.assertIn("Path(raw_file).resolve(strict=True) != expected_path", source)
        self.assertIn("topology_core.attempt01_core is not attempt01_core", source)
        for forbidden in (
            "bpy.ops", "--result-path", "write_text(", "write_bytes(",
            "save_as_mainfile", "render.render", "export_scene",
        ):
            self.assertNotIn(forbidden, source)

    def test_08_config_is_float_free_fail_closed_and_still_requires_two_runs(self) -> None:
        assert_no_float(self, self.config)
        contract = self.config["execution_module_contract"]
        self.assertTrue(contract["verification_must_precede_analysis"])
        self.assertTrue(contract["fake_or_in_memory_sys_modules_entry_must_fail"])
        self.assertEqual(tuple(contract["attempt_01_required_symbols"]), ATTEMPT01_SYMBOLS)
        sealing = self.config["topology_sealing_contract"]
        self.assertIsNone(sealing["prior_sealed_expected_full_normalized_topology_sha256"])
        self.assertEqual(sealing["required_fresh_locked_matching_extractions"], 2)
        self.assertFalse(sealing["one_extraction_is_acceptance"])
        truth = self.config["truth_boundary"]
        for key in (
            "controller_or_pipe_creation_implemented",
            "child_process_authentication_implemented", "replay_protection_implemented",
            "parent_binding_of_this_config_hash_implemented",
            "blender_execution_authorized", "body_authoring_authorized",
        ):
            self.assertFalse(truth[key])


if __name__ == "__main__":
    unittest.main()
