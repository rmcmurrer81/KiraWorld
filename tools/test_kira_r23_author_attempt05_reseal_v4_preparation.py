#!/usr/bin/env python3
"""Warning-fatal, no-Blender tests for R23 Attempt05 reseal-v4."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = ROOT / "tools/kira_r23_author_attempt05_reseal_v4_invocation.py"
SHIM_PATH = ROOT / "tools/blender_author_kira_r23_cc0_afes_attempt05_reseal_v4_wrapper.py"
PREP = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_reseal_v4_preparation"
)
CONFIG_PATH = PREP / "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_RESEAL_V4_CONFIG.json"
OVERLAY_PATH = PREP / "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_RESEAL_V4_REPAIR_OVERLAY.json"
MANIFEST_PATH = PREP / "PACKAGE_MANIFEST.json"
V3_PREP = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v3_preparation"
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def import_path(name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt05ResealV4PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.launcher = import_path("_r23_attempt05_v4_launcher_test", LAUNCHER_PATH)
        cls.shim = import_path("_r23_attempt05_v4_blender_shim_test", SHIM_PATH)
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
        cls.v3_config = json.loads(
            (V3_PREP / "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V3_CONFIG.json").read_text(
                encoding="utf-8"
            )
        )
        cls.v3_overlay = json.loads(
            (V3_PREP / "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V3_REPAIR_OVERLAY.json").read_text(
                encoding="utf-8"
            )
        )

    def _verify_preserved_section(self, label: str) -> None:
        section = next(
            row
            for row in self.config["preserved_append_only_evidence"]
            if row["label"] == label
        )
        directory = ROOT / section["directory"]
        self.assertEqual(
            sorted(path.name for path in directory.iterdir()),
            sorted(section["files"]),
        )
        for name, binding in section["files"].items():
            path = directory / name
            self.assertEqual(path.stat().st_size, binding["bytes"])
            self.assertEqual(digest(path), binding["sha256"])

    def test_01_consumed_v3_preparation_is_byte_exact(self) -> None:
        self._verify_preserved_section("reseal_v3_preparation_byte_for_byte")

    def test_02_consumed_v3_authorization_is_byte_exact(self) -> None:
        self._verify_preserved_section("consumed_v3_authorization_byte_for_byte")

    def test_03_consumed_v3_failure_journal_is_byte_exact(self) -> None:
        self._verify_preserved_section("consumed_v3_failure_journal_byte_for_byte")

    def test_04_v3_failure_review_is_byte_exact(self) -> None:
        self._verify_preserved_section("v3_failure_independent_review_byte_for_byte")

    def test_05_failure_diagnosis_is_exactly_nine_case_only_paths(self) -> None:
        pre = json.loads(
            (
                ROOT
                / "RecoverySprint/continuation_20260803/"
                "kira_r23_cc0_afes_author_attempt04_reseal_v3_execution/"
                "attempt_04/PRE_RUN.json"
            ).read_text(encoding="utf-8")
        )
        expected = self.config["failure_repair_contract"]["mismatched_labels"]
        actual: list[str] = []
        for label, binding in self.v3_config["bound_artifacts"].items():
            locked = pre["locked_input_records"][label]
            if binding["path"] != locked["path"]:
                self.assertEqual(binding["path"].casefold(), locked["path"].casefold())
                self.assertEqual(binding["bytes"], locked["bytes"])
                self.assertEqual(binding["sha256"], locked["sha256"])
                actual.append(label)
        self.assertEqual(actual, expected)

    @unittest.skipUnless(os.name == "nt", "Windows canonical locked paths")
    def test_06_every_config_binding_path_equals_locked_canonical_record(self) -> None:
        records = self.launcher._canonical_locked_bound_records(self.config)
        self.assertEqual(set(records), set(self.config["bound_artifacts"]))
        for label, binding in self.config["bound_artifacts"].items():
            self.assertEqual(binding["path"], records[label]["path"])
            self.assertEqual(binding["bytes"], records[label]["bytes"])
            self.assertEqual(binding["sha256"], records[label]["sha256"])

    def test_07_all_tool_bindings_use_canonical_lowercase_tools(self) -> None:
        for label, binding in self.config["bound_artifacts"].items():
            if binding["path"].casefold().startswith("tools/"):
                with self.subTest(label=label):
                    self.assertTrue(binding["path"].startswith("tools/"))
        for path in self.config["runtime_dependency_closure"]["project_local_modules"]:
            self.assertTrue(path.startswith("tools/"))

    @unittest.skipUnless(os.name == "nt", "Windows canonical locked paths")
    def test_08_uppercase_tools_regression_fails_before_execution(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["bound_artifacts"]["action_serializer_runtime"]["path"] = (
            "Tools/kira_r23_blender51_action_serializer.py"
        )
        with self.assertRaises(self.launcher.ResealV4Error):
            self.launcher._canonical_locked_bound_records(changed)

    def test_09_sealed_v3_engines_are_byte_exact(self) -> None:
        for label, expected_bytes, expected_hash in (
            (
                "reseal_v3_controller_engine",
                self.launcher.ENGINE_BYTES,
                self.launcher.ENGINE_SHA256,
            ),
            (
                "reseal_v3_wrapper_engine",
                self.shim.ENGINE_BYTES,
                self.shim.ENGINE_SHA256,
            ),
        ):
            binding = self.config["bound_artifacts"][label]
            path = ROOT / binding["path"]
            self.assertEqual(path.stat().st_size, expected_bytes)
            self.assertEqual(digest(path), expected_hash)

    def test_10_overlay_changes_only_identity_casing_and_attempt05_output(self) -> None:
        self.assertEqual(set(self.overlay), set(self.v3_overlay))
        self.assertEqual(
            self.overlay["nominal_source_baseline"],
            self.v3_overlay["nominal_source_baseline"],
        )
        self.assertEqual(
            self.overlay["nominal_corrected_final"],
            self.v3_overlay["nominal_corrected_final"],
        )
        self.assertEqual(
            self.overlay["clinical_semantics_contract"],
            self.v3_overlay["clinical_semantics_contract"],
        )
        repair_diff = {
            key
            for key in self.overlay["repair_contract"]
            if self.overlay["repair_contract"][key]
            != self.v3_overlay["repair_contract"][key]
        }
        self.assertEqual(repair_diff, {"effective_output", "effective_candidate"})
        for label, binding in self.overlay["bound_artifacts"].items():
            old = self.v3_overlay["bound_artifacts"][label]
            self.assertEqual(binding["bytes"], old["bytes"])
            self.assertEqual(binding["sha256"], old["sha256"])
            self.assertEqual(binding["path"].casefold(), old["path"].casefold())

    def test_11_overlay_and_output_contract_are_exact_attempt05(self) -> None:
        output = self.config["output_contract"]
        repair = self.overlay["repair_contract"]
        self.assertEqual(output["effective_directory"], repair["effective_output"])
        self.assertEqual(output["candidate_basename"], repair["effective_candidate"])
        self.assertTrue(output["effective_directory"].endswith("/attempt_05"))
        self.assertTrue(output["execution_directory"].endswith("/attempt_05"))
        self.assertNotIn("attempt_04", output["candidate_basename"])

    def test_12_overlay_artifacts_are_all_covered_by_outer_locked_set(self) -> None:
        outer = self.config["bound_artifacts"]
        by_path = {row["path"].casefold(): row for row in outer.values()}
        for label, binding in self.overlay["bound_artifacts"].items():
            with self.subTest(label=label):
                self.assertIn(binding["path"].casefold(), by_path)
                outer_binding = by_path[binding["path"].casefold()]
                self.assertEqual(binding["bytes"], outer_binding["bytes"])
                self.assertEqual(binding["sha256"], outer_binding["sha256"])

    def test_13_runtime_import_order_is_exact_and_fully_bound(self) -> None:
        closure = self.config["runtime_dependency_closure"]
        self.assertEqual(
            closure["project_local_modules"], closure["verified_source_import_order"]
        )
        bound = {row["path"] for row in self.config["bound_artifacts"].values()}
        self.assertTrue(set(closure["project_local_modules"]).issubset(bound))

    def test_14_command_uses_only_new_shim_and_sealed_author_tail(self) -> None:
        command = self.launcher.ENGINE.build_command(self.config)
        self.assertEqual(command.count("--python"), 1)
        self.assertNotIn("--python-expr", command)
        self.assertEqual(command.count("--"), 1)
        self.assertEqual(
            Path(command[8]).resolve(),
            (ROOT / self.config["bound_artifacts"]["reseal_v3_blender_wrapper"]["path"]).resolve(),
        )
        self.assertEqual(
            command[-3:],
            [
                "--config",
                self.config["handoff_contract"]["sealed_author_config_argument"],
                "--execute-authoring",
            ],
        )
        self.assertNotIn(
            self.config["handoff_contract"]["repair_overlay_config_argument"],
            command,
        )

    def test_15_direct_blender_shim_without_controller_lease_fails_closed(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(self.shim.BlenderResealV4ShimError):
                self.shim._read_locked_engine()

    def _shim_engine_without_real_lease(self) -> dict[str, object]:
        fake_bpy = types.ModuleType("bpy")
        fake_bpy.data = types.SimpleNamespace(filepath="")
        fake_bpy.app = types.SimpleNamespace(version_string="5.1-test")
        prior = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            source = (ROOT / self.config["bound_artifacts"]["reseal_v3_wrapper_engine"]["path"]).read_bytes()
            with mock.patch.object(self.shim, "_read_locked_engine", return_value=source):
                return self.shim._load_engine_namespace()
        finally:
            if prior is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = prior

    def test_16_shim_preserves_author_argv_and_accepts_only_attempt05_rebind(self) -> None:
        engine = self._shim_engine_without_real_lease()
        author = json.loads(
            (ROOT / self.config["handoff_contract"]["sealed_author_config_argument"]).read_text(
                encoding="utf-8"
            )
        )
        original = json.loads(
            (ROOT / self.config["bound_artifacts"]["original_repair_overlay"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        topology = types.SimpleNamespace(REPAIR_CONFIG=None)
        command = self.launcher.ENGINE.build_command(self.config)
        before = list(command)
        record = engine["apply_config_handoff"](
            topology, self.config, command, author, self.overlay, original
        )
        self.assertEqual(command, before)
        self.assertEqual(
            topology.REPAIR_CONFIG.as_posix(),
            self.config["handoff_contract"]["repair_overlay_config_argument"],
        )
        self.assertEqual(
            record["attempt05_output_rebind"]["only_repair_contract_fields_changed"],
            ["effective_candidate", "effective_output"],
        )

    def test_17_shim_rejects_any_third_repair_contract_change(self) -> None:
        engine = self._shim_engine_without_real_lease()
        author = json.loads(
            (ROOT / self.config["handoff_contract"]["sealed_author_config_argument"]).read_text(
                encoding="utf-8"
            )
        )
        original = json.loads(
            (ROOT / self.config["bound_artifacts"]["original_repair_overlay"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        changed = copy.deepcopy(self.overlay)
        changed["repair_contract"]["diagnosed_seam_chord_count"] = 23
        with self.assertRaises(engine["BlenderResealV3Error"]):
            engine["apply_config_handoff"](
                types.SimpleNamespace(REPAIR_CONFIG=None),
                self.config,
                self.launcher.ENGINE.build_command(self.config),
                author,
                changed,
                original,
            )

    def test_18_authorization_reviews_every_bound_input_and_package_binding(self) -> None:
        reviewed = set(self.config["authorization_contract"]["reviewed_binding_labels"])
        self.assertEqual(
            reviewed,
            set(self.config["bound_artifacts"]) | {"reseal_v3_config", "reseal_v3_manifest"},
        )

    def test_19_attempt05_state_is_absent_and_attempt04_output_was_not_created(self) -> None:
        self.assertEqual(
            self.launcher.ENGINE.authorization_presence(self.config),
            {"directory": False, "record": False, "manifest": False},
        )
        output = self.config["output_contract"]
        self.assertFalse((ROOT / output["effective_directory"]).exists())
        self.assertFalse((ROOT / output["execution_directory"]).exists())
        self.assertFalse(
            (
                ROOT
                / "RecoverySprint/continuation_20260803/"
                "kira_r23_cc0_afes_author/attempt_04"
            ).exists()
        )

    def test_20_preparation_verification_records_the_warning_fatal_path_gate(self) -> None:
        config, record = self.launcher.verify_preparation()
        self.assertEqual(config, self.config)
        self.assertTrue(
            record["canonical_path_gate"][
                "all_config_paths_exactly_equal_locked_controller_records"
            ]
        )
        self.assertEqual(
            set(record["canonical_path_gate"]["checked_labels"]),
            set(self.config["bound_artifacts"]),
        )

    def test_21_dry_launcher_never_calls_popen_or_creates_state(self) -> None:
        with mock.patch.object(self.launcher.ENGINE.subprocess, "Popen") as popen:
            result = self.launcher.main([])
        self.assertEqual(result, 0)
        popen.assert_not_called()
        output = self.config["output_contract"]
        self.assertFalse((ROOT / output["effective_directory"]).exists())
        self.assertFalse((ROOT / output["execution_directory"]).exists())

    def test_22_live_flag_without_new_authorization_fails_before_process(self) -> None:
        with mock.patch.object(self.launcher.ENGINE.subprocess, "Popen") as popen:
            with self.assertRaises(self.launcher.ENGINE.ResealV3Error):
                self.launcher.main(["--execute-attempt05-reseal-v4"])
        popen.assert_not_called()

    def test_23_package_manifest_is_exact_and_canonical(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["artifact_kind"],
            "KIRA_R23_AUTHOR_ATTEMPT05_RESEAL_V4_PREPARATION",
        )
        self.assertEqual(
            {row["path"] for row in manifest["artifacts"]},
            set(self.config["manifest_contract"]["required_artifact_paths"]),
        )
        for row in manifest["artifacts"]:
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"])
            self.assertEqual(digest(path), row["sha256"])
            self.assertEqual(
                self.launcher.ENGINE.relative(path),
                row["path"],
                f"noncanonical manifest path: {row['path']}",
            )

    def test_24_test_results_are_final_truth_and_no_blender_was_run(self) -> None:
        record = json.loads((PREP / "TEST_RESULTS.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "PASSED")
        self.assertEqual(record["tests_run"], 24)
        self.assertEqual(record["failures"], 0)
        self.assertEqual(record["errors"], 0)
        self.assertFalse(record["blender_invoked"])
        self.assertFalse(record["blend_mutated"])
        self.assertFalse(record["live_authorization_exists"])
        self.assertFalse(record["candidate_directory_exists"])
        self.assertFalse(record["execution_directory_exists"])


if __name__ == "__main__":
    unittest.main()
