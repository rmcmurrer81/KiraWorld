from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_semantic_control_cage_diagnostic_v4.json"
ADAPTER = ROOT / "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4.py"
WRAPPER = ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v4.py"
CONTROLLER = ROOT / "tools/run_kira_r25_semantic_control_cage_v4.py"
ATTEMPT03_CONFIG = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_semantic_control_cage_diagnostic_v3.json"
ATTEMPT03_WRAPPER = ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v3.py"
ATTEMPT03_TEST = ROOT / "Testing/test_kira_r25_semantic_control_cage_attempt03.py"
ATTEMPT03_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/attempt_03/CHECKPOINT.md"
)
ATTEMPT03_AUDIT = ATTEMPT03_CHECKPOINT.with_name("INDEPENDENT_AUDIT.md")


def digest(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SemanticControlCageAttempt04StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.adapter = load_module("_test_semantic_v4_adapter", ADAPTER)
        cls.controller = load_module("_test_semantic_v4_controller", CONTROLLER)
        cls.wrapper_source = WRAPPER.read_text(encoding="utf-8")
        cls.controller_source = CONTROLLER.read_text(encoding="utf-8")
        cls.adapter_source = ADAPTER.read_text(encoding="utf-8")

    def test_01_identity_is_static_unsealed_and_execution_forbidden(self) -> None:
        self.assertEqual(self.config["schema"], "kira.avatar.r25.semantic_control_cage_diagnostic.v4")
        self.assertEqual(self.config["attempt_id"], "attempt_04_static_unsealed")
        self.assertEqual(
            self.config["status"],
            "STATIC_PREPARATION_ONLY_V3R3_EVIDENCE_NOT_SEALED_EXECUTION_FORBIDDEN",
        )
        self.assertFalse(self.config["scope"]["blender_execution_authorized"])
        self.assertTrue(self.config["scope"]["read_only_diagnostic"])

    def test_02_exact_sixteen_placeholders_are_preserved(self) -> None:
        expected = [
            "FINAL_INDEPENDENT_AFES_ATTEMPT_AUDIT_PATH_BYTES_SHA256_AND_PASS_STATUS",
            "FINAL_INDEPENDENTLY_ACCEPTED_LOCKED_PAIR_EXECUTION_CONTRACT_PATH_BYTES_SHA256",
            "FINAL_PAIR_ACCEPTANCE_FRAME_SHA256", "FINAL_RUN_01_FRAME_SHA256",
            "FINAL_RUN_02_FRAME_SHA256", "FINAL_PAIR_RUN_INNER_SCHEMAS_AND_STATUSES",
            "FINAL_EXACT_EXTRACTION_VERIFIED_INPUT_ROWS",
            "FINAL_FOUNDATION_FULL_NORMALIZED_TOPOLOGY_SHA256",
            "FINAL_AFES_UNION_COUNT_AND_SHA256", "FINAL_RING_1_COUNT_AND_SHA256",
            "FINAL_RING_2_COUNT_AND_SHA256", "FINAL_COMBINED_RING_COUNT_AND_SHA256",
            "FINAL_LOCKED_UNION_COUNT_AND_SHA256", "FINAL_EXACT_TOPOLOGY_STRUCTURE",
            "FINAL_EXACT_AFES_BOUNDS_OBJECT_NANOMETERS",
            "FINAL_TWO_DISTINCT_FRESH_SESSION_NONCES_AND_MATCHING_INNER_DECISION",
        ]
        self.assertEqual(self.config["afes_v3r3_pair_binding"]["required_final_placeholders"], expected)
        self.assertEqual(len(set(expected)), 16)

    def test_03_every_final_v3r3_evidence_slot_is_null(self) -> None:
        pair = self.config["afes_v3r3_pair_binding"]
        for key in (
            "final_locked_pair_execution_contract_binding",
            "final_locked_pair_independent_audit_binding",
            "final_locked_pair_native_manifest_binding",
            "final_locked_pair_execution_outcome_binding",
            "final_run_01_receipt_binding", "final_run_02_receipt_binding",
            "expected_pair_and_analysis",
        ):
            self.assertIsNone(pair[key], key)

    def test_04_adapter_and_contract_exact_expected_fields_match(self) -> None:
        declared = set(self.config["afes_v3r3_pair_binding"]["expected_pair_and_analysis_exact_fields"])
        self.assertEqual(declared, self.adapter.EXPECTED_KEYS)

    def test_05_attempt03_acceptance_lineage_is_exact(self) -> None:
        expected = {
            ATTEMPT03_CONFIG: (12845, "42a96cb62ede275a247d1bcae836a0bfe800f2ec02449b697f8709ffd56efd45"),
            ATTEMPT03_WRAPPER: (35374, "4d3fab98efc822950078aa905e2290aad5b6021659e8a036c774325e6cc29379"),
            ATTEMPT03_TEST: (39958, "384c0545a2ce066dd74b212fbebe3e9a6fe29f010eec2d9bd70aba65a40ca1ce"),
            ATTEMPT03_CHECKPOINT: (8912, "8e9730103bc58badfdf08a6c04e872d6555c7217e924330edc1bcbfaa6ccfa86"),
            ATTEMPT03_AUDIT: (8279, "9e762318cc6aa3da99de3460947ade84086e27d0be0a9370de52f77c2c7768e5"),
        }
        for path, row in expected.items():
            self.assertEqual(digest(path), row)

    def test_06_every_present_binding_rehashes_exactly(self) -> None:
        for label, row in self.config["bindings"].items():
            path = ROOT / row["path"]
            self.assertEqual(digest(path), (row["bytes"], row["sha256"]), label)

    def test_07_current_preparation_paths_are_unique_and_absent(self) -> None:
        paths = self.config["append_only_execution_paths"]
        values = [paths["independent_audit"], paths["outcome_receipt"], paths["evidence_root"]]
        self.assertEqual(len(values), len(set(values)))
        for value in values:
            self.assertFalse((ROOT / value).exists(), value)
        self.assertTrue(all("attempt_04" in value for value in values))

    def test_08_direct_controller_refuses_without_mutation(self) -> None:
        audit = ROOT / self.controller.STATIC_AUDIT_RELATIVE_PATH
        outcome = ROOT / self.controller.OUTCOME_RELATIVE_PATH
        output = ROOT / self.controller.OUTPUT_RELATIVE_ROOT
        before = tuple(path.exists() for path in (audit, outcome, output))
        completed = subprocess.run(
            [sys.executable, str(CONTROLLER)], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn(b"static preparation only", completed.stdout)
        self.assertEqual(tuple(path.exists() for path in (audit, outcome, output)), before)

    def test_09_plan_builder_fails_on_static_status_before_audit_lookup(self) -> None:
        sha = digest(CONFIG)[1]
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4PlanError,
            "static_v4_preparation_is_not_execution_authority",
        ):
            self.controller.build_sealed_execution_plan(sha, "0" * 64)

    def test_10_controller_contains_no_launcher_or_write_primitive(self) -> None:
        tree = ast.parse(self.controller_source)
        imported = {
            alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("subprocess", imported)
        self.assertNotIn("ctypes", imported)
        self.assertNotIn("bpy", imported)
        for token in ("Popen(", "run(", "write_bytes(", "write_text(", "mkdir(", "unlink("):
            self.assertNotIn(token, self.controller_source)

    def test_11_wrapper_has_only_pipe_handles_and_no_path_result_argument(self) -> None:
        self.assertIn('parser.add_argument("--lock-handle"', self.wrapper_source)
        self.assertIn('parser.add_argument("--result-handle"', self.wrapper_source)
        for token in (
            "--output", "--result-path", "bpy.ops", "save_as_mainfile", ".render(",
            "export_scene", "write_bytes(", "write_text(",
        ):
            self.assertNotIn(token, self.wrapper_source)

    def test_12_wrapper_refuses_static_config_before_runtime_or_blend_load(self) -> None:
        fake_bpy = type(sys)("bpy")
        previous = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            wrapper = load_module("_test_semantic_v4_wrapper", WRAPPER)
            with self.assertRaisesRegex(
                wrapper.R25SemanticControlCageV4Error,
                "v4_static_preparation_is_not_execution_authority",
            ):
                wrapper._read_config(digest(CONFIG)[1])
        finally:
            if previous is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = previous

    def test_13_unsealed_expected_object_fails_closed(self) -> None:
        unresolved = {key: "FINAL_PENDING" for key in self.adapter.EXPECTED_KEYS}
        with self.assertRaisesRegex(
            self.adapter.SemanticCageAfesV3R3Error,
            "still_unsealed",
        ):
            self.adapter.require_sealed_expected(unresolved)

    def test_14_alias_or_extra_expected_field_fails_closed(self) -> None:
        unresolved = {key: "FINAL_PENDING" for key in self.adapter.EXPECTED_KEYS}
        unresolved["pair_frame_sha256"] = unresolved.pop("pair_acceptance_frame_sha256")
        with self.assertRaisesRegex(
            self.adapter.SemanticCageAfesV3R3Error,
            "shape_drift",
        ):
            self.adapter.require_sealed_expected(unresolved)

    def test_15_v3r3_input_and_v4_output_schemas_are_literal_and_exact(self) -> None:
        schemas = self.config["afes_v3r3_pair_binding"]["known_source_schema_constants_not_result_claims"]
        self.assertEqual(schemas["pair_schema"], "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v3r3")
        self.assertEqual(schemas["run_schema"], "kira.avatar.r25.foundation_afes_locked_extraction_run.v3r3")
        self.assertEqual(schemas["inner_schema"], "kira.avatar.r25.foundation_afes_transition_diagnostic.v5")
        self.assertEqual(schemas["semantic_output_schema"], "kira.r25.semantic_control_cage_diagnostic.v4")
        self.assertIn(schemas["semantic_output_schema"], self.wrapper_source)
        self.assertIn("pair acceptance", self.config["scope"]["input_transport"].replace("_", " "))

    def test_16_no_result_or_audit_hash_is_invented(self) -> None:
        pair = self.config["afes_v3r3_pair_binding"]
        serialized = json.dumps(pair, sort_keys=True)
        self.assertNotIn("kira_r25_foundation_afes_locked_pair_execution_v3r3.json\", \"bytes", serialized)
        self.assertEqual(serialized.count("null"), 7)
        self.assertTrue(self.config["truth_boundary"]["v3r3_source_shape_is_known_but_no_result_hash_is_claimed"])


if __name__ == "__main__":
    unittest.main()
