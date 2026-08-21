"""Focused non-Blender tests for the inactive MakeHuman carrier boundary."""

from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_makehuman_rigged_carrier as carrier


CONFIG_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "tooling"
    / "makehuman_adult_female_rigged_carrier_v1.json"
)
BUILDER_PATH = (
    PROJECT_ROOT
    / "tools"
    / "blender_build_makehuman_adult_female_rigged_carrier_inactive.py"
)
AUDITOR_PATH = (
    PROJECT_ROOT
    / "tools"
    / "blender_audit_makehuman_adult_female_rigged_carrier.py"
)


class RiggedCarrierPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = carrier.read_json(CONFIG_PATH, "test config")

    def test_01_exact_real_inputs_are_ready_without_execution_authority(self) -> None:
        report = carrier.prepare_preflight(PROJECT_ROOT, CONFIG_PATH)
        self.assertEqual(
            report["status"],
            "PREFLIGHT_READY_AWAITING_EXACT_ONE_RUN_AUTHORIZATION",
        )
        self.assertTrue(report["source"]["unchanged"])
        self.assertTrue(report["outputs_absent"])
        self.assertIsNone(report["blender_executable"])
        self.assertFalse(report["one_run_authorization"]["present"])
        self.assertEqual(report["input_snapshot_root_before"], report["input_snapshot_root_after"])
        source_definition = report["source_definition"]
        self.assertEqual(source_definition["bone_count"], 163)
        self.assertEqual(source_definition["weight_group_count"], 139)
        self.assertEqual(source_definition["weighted_groups_missing_bones"], [])
        self.assertEqual(
            source_definition["resolved_skeleton_geometry"]["bone_geometry_count"],
            163,
        )
        self.assertEqual(
            [record["changed_vertex_count"] for record in report["macro_targets"]],
            [0, 19150],
        )
        self.assertEqual(
            report["required_blender_flags"],
            ["--background", "--factory-startup", "--disable-autoexec"],
        )
        for command in (report["build_command"], report["audit_command"]):
            self.assertEqual(command[1:4], report["required_blender_flags"])
            self.assertIn("--authorization", command)
        self.assertEqual(
            report["preflight_report_receipt_sha256"],
            carrier.canonical_sha256(
                {
                    key: value
                    for key, value in report.items()
                    if key != "preflight_report_receipt_sha256"
                }
            ),
        )
        binding_receipt, code_bindings = carrier.preflight_binding_receipt(
            PROJECT_ROOT,
            CONFIG_PATH,
        )
        self.assertEqual(report["preflight_receipt_sha256"], binding_receipt)
        self.assertEqual(report["bound_code"], code_bindings)
        self.assertTrue(report["source"]["decompressed_container_verified"])

    def test_02_exact_rig_and_weights_bindings_match_disk(self) -> None:
        for name in ("definition", "weights"):
            binding = self.config["skeleton"][name]
            path = carrier.project_path(
                PROJECT_ROOT,
                binding["path"],
                name,
                must_exist=True,
            )
            self.assertEqual(carrier.native_filesystem_path(path).stat().st_size, binding["bytes"])
            self.assertEqual(carrier.sha256_file(path), binding["sha256"])
        self.assertEqual(
            self.config["skeleton"]["definition"]["sha256"],
            "5acfcaff5f0f46f88bc2a2935c18b65f7ba4f10c99a6628e97d08d2ef7bb9ba0",
        )
        self.assertEqual(
            self.config["skeleton"]["weights"]["sha256"],
            "ae2d830adb5ee890c90e071bde6efaa2b9c1f2937b49770f7b5264041637b071",
        )

    def test_03_pose_bones_and_separate_module_boundaries_are_exact(self) -> None:
        definition_path = carrier.project_path(
            PROJECT_ROOT,
            self.config["skeleton"]["definition"]["path"],
            "definition",
            must_exist=True,
        )
        skeleton = carrier.read_json(definition_path, "skeleton")
        pose_bones = {
            bone
            for pose in self.config["pose_audit"]["poses"]
            for bone in pose["rotations_degrees_xyz"]
        }
        self.assertLessEqual(pose_bones, set(skeleton["bones"]))
        separation = self.config["separation"]
        self.assertTrue(separation["bald"])
        for key in (
            "contains_hair",
            "contains_clothing",
            "contains_internal_anatomy",
            "contains_identity_styling",
            "contains_actions",
            "runtime_activation_allowed",
            "public_export_allowed",
        ):
            self.assertFalse(separation[key])
        self.assertEqual(
            separation["carrier_dependency_mode_for_future_modules"],
            "READ_ONLY_TRANSFORM_FOLLOWING_ONLY",
        )
        self.assertFalse(self.config["authority"]["anatomy_authoring_authorized"])

    def test_04_config_mutations_fail_closed(self) -> None:
        mutations = {
            "hair": lambda value: value["separation"].__setitem__("contains_hair", True),
            "clothing": lambda value: value["separation"].__setitem__("contains_clothing", True),
            "internals": lambda value: value["separation"].__setitem__("contains_internal_anatomy", True),
            "identity": lambda value: value["separation"].__setitem__("contains_identity_styling", True),
            "runtime": lambda value: value["separation"].__setitem__("runtime_activation_allowed", True),
            "public": lambda value: value["separation"].__setitem__("public_export_allowed", True),
            "owner": lambda value: value["authority"].__setitem__("owner_approved", True),
            "blender": lambda value: value["authority"].__setitem__("blender_execution_authorized", True),
            "pose": lambda value: value["pose_audit"]["poses"][1]["rotations_degrees_xyz"]["upperleg01.L"].__setitem__(0, 181.0),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = deepcopy(self.config)
                mutate(candidate)
                with self.assertRaises(carrier.RiggedCarrierError):
                    carrier._validate_config_shape(candidate)
        escaped = deepcopy(self.config)
        escaped["output"]["candidate_blend"] = "../outside.blend"
        with self.assertRaises(carrier.RiggedCarrierError):
            carrier._output_paths(PROJECT_ROOT, escaped["output"])

    def test_05_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw_directory:
            path = Path(raw_directory) / "duplicate.json"
            path.write_text('{"status":"first","status":"second"}\n', encoding="utf-8")
            with self.assertRaisesRegex(carrier.RiggedCarrierError, "duplicate JSON key"):
                carrier.read_json(path, "duplicate fixture")

    def test_06_authorization_requires_exact_false_safety_permissions(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw_directory:
            directory = Path(raw_directory)
            relative_directory = directory.relative_to(PROJECT_ROOT).as_posix()
            config = deepcopy(self.config)
            config["output"] = {
                "allowed_root": relative_directory,
                "candidate_blend": f"{relative_directory}/candidate.blend",
                "build_report": f"{relative_directory}/build.json",
                "audit_report": f"{relative_directory}/audit.json",
                "one_run_authorization": f"{relative_directory}/authorization.json",
            }
            config_path = directory / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            authorization = {
                "schema": carrier.ONE_RUN_AUTHORIZATION_SCHEMA,
                "status": carrier.ONE_RUN_AUTHORIZATION_STATUS,
                "one_run_id": "unit-test-only",
                "issued_at_utc": "2026-08-20T12:00:00Z",
                "config_sha256": carrier.sha256_file(config_path),
                "source_sha256": config["source"]["sha256"],
                "candidate_blend_path": config["output"]["candidate_blend"],
                "build_report_path": config["output"]["build_report"],
                "audit_report_path": config["output"]["audit_report"],
                "blender_executable_sha256": carrier.sha256_file(Path(sys.executable)),
                "preflight_receipt_sha256": carrier.preflight_binding_receipt(
                    PROJECT_ROOT,
                    config_path,
                )[0],
                "controller_sha256": carrier.sha256_file(
                    PROJECT_ROOT / carrier.CONTROLLER_RELATIVE_PATH
                ),
                "builder_sha256": carrier.sha256_file(
                    PROJECT_ROOT / carrier.BUILDER_RELATIVE_PATH
                ),
                "auditor_sha256": carrier.sha256_file(
                    PROJECT_ROOT / carrier.AUDITOR_RELATIVE_PATH
                ),
                "intersection_auditor_sha256": carrier.sha256_file(
                    PROJECT_ROOT / carrier.INTERSECTION_AUDITOR_RELATIVE_PATH
                ),
                "build_allowed": True,
                "audit_allowed": True,
                "background_required": True,
                "factory_startup_required": True,
                "autoexec_disabled_required": True,
                "overwrite_allowed": False,
                "source_mutation_allowed": False,
                "hair_allowed": False,
                "clothing_allowed": False,
                "internal_anatomy_allowed": False,
                "identity_styling_allowed": False,
                "runtime_activation_allowed": False,
                "public_export_allowed": False,
            }
            authorization_path = directory / "authorization.json"
            authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
            accepted = carrier.validate_one_run_authorization(
                PROJECT_ROOT,
                config_path,
                authorization_path,
                Path(sys.executable),
                operation="build",
            )
            self.assertEqual(accepted["one_run_id"], "unit-test-only")
            for key in (
                "overwrite_allowed",
                "source_mutation_allowed",
                "hair_allowed",
                "clothing_allowed",
                "internal_anatomy_allowed",
                "identity_styling_allowed",
                "runtime_activation_allowed",
                "public_export_allowed",
            ):
                with self.subTest(key=key):
                    rejected = dict(authorization)
                    rejected[key] = True
                    authorization_path.write_text(json.dumps(rejected), encoding="utf-8")
                    with self.assertRaises(carrier.RiggedCarrierError):
                        carrier.validate_one_run_authorization(
                            PROJECT_ROOT,
                            config_path,
                            authorization_path,
                            Path(sys.executable),
                            operation="build",
                        )
            alternate_path = directory / "alternate_authorization.json"
            alternate_path.write_text(json.dumps(authorization), encoding="utf-8")
            with self.assertRaisesRegex(carrier.RiggedCarrierError, "path differs"):
                carrier.validate_one_run_authorization(
                    PROJECT_ROOT,
                    config_path,
                    alternate_path,
                    Path(sys.executable),
                    operation="audit",
                )
            changed_code = dict(authorization)
            changed_code["builder_sha256"] = "0" * 64
            authorization_path.write_text(json.dumps(changed_code), encoding="utf-8")
            with self.assertRaisesRegex(carrier.RiggedCarrierError, "builder_sha256"):
                carrier.validate_one_run_authorization(
                    PROJECT_ROOT,
                    config_path,
                    authorization_path,
                    Path(sys.executable),
                    operation="build",
                )

    def test_07_runtime_preflight_does_not_require_python_314_zstd(self) -> None:
        original_import = __import__

        def guarded_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "compression" or name.startswith("compression."):
                raise AssertionError("runtime preflight attempted Python 3.14 zstd import")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=guarded_import):
            report = carrier.prepare_preflight(
                PROJECT_ROOT,
                CONFIG_PATH,
                verify_decompressed_container=False,
            )
        self.assertFalse(report["source"]["decompressed_container_verified"])
        self.assertEqual(
            report["status"],
            "PREFLIGHT_READY_AWAITING_EXACT_ONE_RUN_AUTHORIZATION",
        )

    def test_08_no_replace_promotion_is_behavioral_and_atomic_at_destination(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw_directory:
            directory = Path(raw_directory)
            private = directory / "private"
            private.mkdir()
            staging = private / "candidate.staging.blend"
            destination = directory / "candidate.blend"
            payload = b"private-candidate-fixture"
            staging.write_bytes(payload)
            receipt = carrier.promote_file_no_replace(staging, destination)
            self.assertFalse(staging.exists())
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(receipt["sha256"], carrier.sha256_file(destination))
            self.assertEqual(destination.stat().st_nlink, 1)

            competing_stage = private / "competing.staging.blend"
            competing_stage.write_bytes(b"must-not-win")
            with self.assertRaisesRegex(carrier.RiggedCarrierError, "replacement"):
                carrier.promote_file_no_replace(competing_stage, destination)
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(competing_stage.read_bytes(), b"must-not-win")

    def test_09_pose_gate_rejects_zero_response_and_global_collapse(self) -> None:
        thresholds = self.config["pose_audit"]
        passing = {
            "exact_intersection_pairs": 0,
            "pelvic_minimum_edge_ratio": 1.0,
            "pelvic_maximum_edge_ratio": 1.0,
            "pelvic_minimum_triangle_area_ratio": 1.0,
            "global_minimum_edge_ratio": 1.0,
            "global_maximum_edge_ratio": 1.0,
            "global_minimum_triangle_area_ratio": 1.0,
            "global_maximum_triangle_area_ratio": 1.0,
            "orientation_reversal_triangle_count": 0,
            "signed_volume_ratio": 1.0,
            "rotation_application_passed": True,
            "requested_rotation_count": 2,
            "moved_vertex_count": 100,
            "maximum_displacement_m": 0.05,
            "rotated_bone_group_response_passed": True,
        }
        self.assertTrue(
            carrier.evaluate_pose_gate("left_knee_flexion", passing, thresholds)[
                "passed"
            ]
        )
        zero_response = dict(passing)
        zero_response.update(
            moved_vertex_count=0,
            maximum_displacement_m=0.0,
            rotated_bone_group_response_passed=False,
        )
        zero_gate = carrier.evaluate_pose_gate(
            "left_knee_flexion", zero_response, thresholds
        )
        self.assertFalse(zero_gate["movement"])
        self.assertFalse(zero_gate["passed"])
        collapse = dict(passing)
        collapse["global_minimum_triangle_area_ratio"] = 0.0
        collapse_gate = carrier.evaluate_pose_gate(
            "left_knee_flexion", collapse, thresholds
        )
        self.assertFalse(collapse_gate["global_deformation"])
        self.assertFalse(collapse_gate["passed"])
        reversal = dict(passing)
        reversal["orientation_reversal_triangle_count"] = 1
        self.assertFalse(
            carrier.evaluate_pose_gate(
                "left_knee_flexion", reversal, thresholds
            )["passed"]
        )


class RiggedCarrierWorkerStaticTests(unittest.TestCase):
    def test_10_workers_parse_and_preserve_the_exact_cli_boundary(self) -> None:
        for path in (BUILDER_PATH, AUDITOR_PATH):
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path))
            self.assertIn("validate_one_run_authorization", source)
            self.assertIn("REQUIRED_BLENDER_FLAGS", source)
            self.assertIn("sys.argv[:separator]", source)
            self.assertIn("use_scripts=False", source)
            self.assertNotIn("subprocess", source)
            self.assertNotIn("socket", source)
            self.assertNotIn("requests", source)

    def test_11_auditor_has_no_save_render_or_export_operation(self) -> None:
        source = AUDITOR_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        operation_names = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("open_mainfile", operation_names)
        self.assertNotIn("save_as_mainfile", operation_names)
        self.assertNotIn("render", operation_names)
        self.assertFalse(any(name.startswith("export") for name in operation_names))

    def test_12_builder_only_saves_the_fresh_candidate_and_never_exports(self) -> None:
        source = BUILDER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        operation_names = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        self.assertEqual(operation_names.count("open_mainfile"), 1)
        self.assertEqual(operation_names.count("save_as_mainfile"), 1)
        self.assertNotIn("render", operation_names)
        self.assertFalse(any(name.startswith("export") for name in operation_names))
        self.assertIn("promote_file_no_replace", source)
        self.assertLess(source.index("if _path_exists(candidate_path)"), source.index("save_as_mainfile"))
        self.assertLess(source.index("source_sha_before"), source.index("open_mainfile"))
        self.assertGreater(source.index("source_sha_after"), source.index("save_as_mainfile"))


if __name__ == "__main__":
    unittest.main()
