"""Static verification for prepared, unexecuted R24 Attempt 35."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT35_CONFIG.json"
)
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_candidate_attempt35.py"
PROPOSAL = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_35_EXPLICIT_VECTOR_DIMENSION_PROPOSAL.md"
)
EXPECTED_CONFIG_SHA256 = "e92df1cc085b2a2d667a77923e76e379cd10c5d5315e31dc9287470872b5635f"
EXPECTED_WORKER_SHA256 = "82221025c21bc56f4410f687efcd2e88de3cfdf63d059b9ed8e1897e64d27199"
EXPECTED_PROPOSAL_SHA256 = "833df9f6035a5e3110687a1f13ff4b4fb9551baa4bcfbbd76a30fa248562c1fb"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    path.relative_to(ROOT)
    return path


def dimensionless_vector_sum_lines(source: str, functions: set[str]) -> list[int]:
    tree = ast.parse(source)
    result: list[int] = []
    for function in (
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ):
        if function.name not in functions:
            continue
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "sum"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Call)
                and isinstance(node.args[1].func, ast.Name)
                and node.args[1].func.id == "Vector"
                and not node.args[1].args
                and not node.args[1].keywords
            ):
                result.append(int(node.lineno))
    return sorted(result)


class Attempt35StaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.proposal = PROPOSAL.read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("attempt35_static", WORKER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.attempt15_path = project_path(
            cls.config["bindings"]["attempt15_worker"]["path"]
        )
        cls.r20_path = project_path(
            cls.config["bindings"]["r20_pelvis_helper"]["path"]
        )
        cls.attempt15_source = cls.attempt15_path.read_text(encoding="utf-8")
        cls.r20_source = cls.r20_path.read_text(encoding="utf-8")
        cls.derived15 = cls.module.derive_attempt15_source(
            cls.attempt15_source, cls.config
        )
        cls.derived20 = cls.module.derive_r20_source(cls.r20_source, cls.config)

    def assert_record(self, label: str, record: dict[str, object]) -> Path:
        path = project_path(str(record["path"]))
        self.assertTrue(path.is_file(), label)
        self.assertEqual(path.stat().st_size, int(record["bytes"]), label)
        self.assertEqual(sha256_file(path), record["sha256"], label)
        return path

    def test_01_artifact_hashes_and_compile(self) -> None:
        self.assertEqual(CONFIG.stat().st_size, 11648)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(WORKER.stat().st_size, 19186)
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(PROPOSAL.stat().st_size, 9930)
        self.assertEqual(sha256_file(PROPOSAL), EXPECTED_PROPOSAL_SHA256)
        compile(self.source, str(WORKER), "exec")
        compile(self.derived15, str(self.attempt15_path), "exec")
        compile(self.derived20, str(self.r20_path), "exec")

    def test_02_every_binding_and_proposal_is_exact(self) -> None:
        for label, record in self.config["bindings"].items():
            self.assert_record(label, record)
        self.assert_record("proposal", self.config["proposal"])

    def test_03_static_loader_overlay_and_full_derived_hashes_pass(self) -> None:
        loaded = self.module.load_config()
        self.assertEqual(loaded, self.config)
        verified = self.module.verify_overlay(loaded)
        self.assertEqual(len(verified["records"]), 17)
        self.assertEqual(
            verified["derived_attempt15_sha256"],
            "d4ea3a5bfc59ff67da8c846bcb149f5b2290fb98ce308135a7ef6da509118793",
        )
        self.assertEqual(
            verified["derived_r20_sha256"],
            "8ecd04cad5b8dd1ead519ef6795b0e07c046b5a6034935d6b21bd74f1c21b5ed",
        )

    def test_04_attempt34_append_failure_and_integrity_are_exact(self) -> None:
        bindings = self.config["bindings"]
        append = json.loads(
            project_path(bindings["attempt34_append_inventory"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            append["status"],
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_BEFORE_CLEANUP",
        )
        self.assertEqual(
            append["actual_appended_object_names_sha256"],
            "ef4ed395b5f7fc8c0a2d549a23c547d20d74cd45137e16cd68cc08482e08bb85",
        )
        failure = json.loads(
            project_path(bindings["attempt34_failure"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(failure["error_type"], "AttributeError")
        self.assertEqual(
            failure["error"],
            "Vector addition: vectors must have the same dimensions for this operation",
        )
        self.assertIn("line 557, in reconstruct_local_domain", failure["traceback"])
        self.assertIn("sum(samples, Vector())", failure["traceback"])
        self.assertFalse(failure["render_reached"])
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        external = json.loads(
            project_path(bindings["attempt34_external_integrity"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(external["blender_exit_code"], 1)
        self.assertIsNone(external["native_invocation_error"])
        self.assertTrue(external["pre_post_exact"])
        self.assertEqual(external["before"], external["after"])
        self.assertEqual(len(external["before"]), 192)

    def test_05_all_old_and_new_blocks_are_hash_bound_and_unique(self) -> None:
        replacements = self.config["dimension_patch"]["attempt15"]["replacements"]
        blocks = {
            "r21_provider_link": (
                self.module.ATTEMPT15_R21_IMPORT_OLD,
                self.module.ATTEMPT15_R21_IMPORT_NEW,
            ),
            "quality_refined_cdt_initial_face_centroids": (
                self.module.ATTEMPT15_CDT_SEED_OLD,
                self.module.ATTEMPT15_CDT_SEED_NEW,
            ),
            "quality_refined_cdt_candidate_centroid": (
                self.module.ATTEMPT15_CDT_CENTROID_OLD,
                self.module.ATTEMPT15_CDT_CENTROID_NEW,
            ),
            "reconstruct_local_domain_surrounding_normal": (
                self.module.ATTEMPT15_NORMAL_OLD,
                self.module.ATTEMPT15_NORMAL_NEW,
            ),
            "reconstruct_local_domain_boundary_uv": (
                self.module.ATTEMPT15_UV_OLD,
                self.module.ATTEMPT15_UV_NEW,
            ),
        }
        for label, (old, new) in blocks.items():
            record = replacements[label]
            self.assertEqual(self.module.sha256_text(old), record["old_block_sha256"])
            self.assertEqual(self.module.sha256_text(new), record["new_block_sha256"])
            self.assertEqual(self.attempt15_source.count(old), 1)
            self.assertEqual(self.derived15.count(old), 0)
            self.assertEqual(self.derived15.count(new), 1)
        r20 = self.config["dimension_patch"]["r20"]["replacement"]
        self.assertEqual(
            self.module.sha256_text(self.module.R20_NORMAL_RESTORE_OLD),
            r20["old_block_sha256"],
        )
        self.assertEqual(
            self.module.sha256_text(self.module.R20_NORMAL_RESTORE_NEW),
            r20["new_block_sha256"],
        )
        self.assertEqual(self.r20_source.count(self.module.R20_NORMAL_RESTORE_OLD), 1)
        self.assertEqual(self.derived20.count(self.module.R20_NORMAL_RESTORE_OLD), 0)
        self.assertEqual(self.derived20.count(self.module.R20_NORMAL_RESTORE_NEW), 1)

    def test_06_original_reachable_path_has_exactly_five_dimensionless_starts(self) -> None:
        attempt15_lines = dimensionless_vector_sum_lines(
            self.attempt15_source,
            {"quality_refined_cdt", "reconstruct_local_domain"},
        )
        r20_lines = dimensionless_vector_sum_lines(
            self.r20_source, {"_restore_exact_preserved_loop_normals"}
        )
        self.assertEqual(attempt15_lines, [279, 303, 513, 557])
        self.assertEqual(r20_lines, [2269])
        self.assertEqual(len(attempt15_lines) + len(r20_lines), 5)

    def test_07_derived_reachable_path_has_no_dimensionless_vector_start(self) -> None:
        self.assertEqual(
            dimensionless_vector_sum_lines(
                self.derived15,
                {"quality_refined_cdt", "reconstruct_local_domain"},
            ),
            [],
        )
        self.assertEqual(
            dimensionless_vector_sum_lines(
                self.derived20, {"_restore_exact_preserved_loop_normals"}
            ),
            [],
        )
        self.assertEqual(
            self.config["dimension_patch"]["reachable_dimensionless_accumulators_after"],
            0,
        )

    def test_08_explicit_dimensions_match_operand_domains(self) -> None:
        self.assertIn(
            'sum((base["coordinates"][index] for index in face), Vector((0.0, 0.0)))',
            self.derived15,
        )
        self.assertIn("sum(points, Vector((0.0, 0.0)))", self.derived15)
        self.assertIn(
            "surrounding_normals, Vector((0.0, 0.0, 0.0))", self.derived15
        )
        self.assertIn("sum(samples, Vector((0.0, 0.0)))", self.derived15)
        self.assertIn(
            "exterior_by_vertex[vertex_index], Vector((0.0, 0.0, 0.0))",
            self.derived20,
        )
        self.assertEqual(self.config["dimension_patch"]["dimensions"], {"2d": 3, "3d": 2})

    def test_09_reachability_is_bound_and_render_only_sites_are_excluded(self) -> None:
        attempt31 = project_path(
            self.config["bindings"]["attempt31_worker"]["path"]
        ).read_text(encoding="utf-8")
        for call in (
            "provider.reconstruct_local_domain(adult, reconstruction_config)",
            "provider.r21.r20._restore_exact_preserved_loop_normals(",
        ):
            self.assertIn(call, attempt31)
        self.assertIn("provider_quality(boundary, runtime)", attempt31)
        self.assertIn('"render_reached": False', attempt31)
        self.assertNotIn("provider.r21.render_review(", attempt31)
        reach = self.config["reachability"]
        self.assertFalse(reach["render_reachable"])
        self.assertEqual(reach["r21.render_review"], "EXCLUDED_NO_RENDER_GATE")

    def test_10_candidate_algorithm_and_hard_gates_remain_byte_bound(self) -> None:
        attempt34 = json.loads(
            project_path(self.config["bindings"]["attempt34_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        attempt31_record = attempt34["bindings"]["attempt31_config"]
        attempt31_path = self.assert_record("attempt31_config", attempt31_record)
        base = json.loads(attempt31_path.read_text(encoding="utf-8"))
        selected = base["selected_candidate"]
        self.assertEqual(selected["candidate"], "targeted_complete_vertex_stars_2_6_20_28")
        self.assertEqual(
            [
                selected["face_count"],
                selected["vertex_count"],
                selected["edge_count"],
                selected["interior_vertex_count"],
                selected["boundary_edge_count"],
            ],
            [104, 73, 176, 33, 40],
        )
        self.assertEqual(base["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(base["unchanged_hard_gates"]["minimum_new_triangle_world_area_m2"], 1e-10)
        self.assertFalse(self.config["dimension_patch"]["algorithm_change_allowed"])
        self.assertFalse(
            self.config["dimension_patch"]["operand_or_iteration_order_change_allowed"]
        )

    def test_11_static_import_is_blender_free_and_has_no_save_render_export_api(self) -> None:
        top_imports = []
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                top_imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.append(node.module)
        self.assertNotIn("bpy", top_imports)
        self.assertNotIn("bmesh", top_imports)
        for forbidden in (
            "save_as_mainfile",
            "save_mainfile",
            "write_homefile",
            "write_still",
            "bpy.ops.render",
            "export_scene",
            "export_mesh",
        ):
            self.assertNotIn(forbidden, self.source)

    def test_12_provider_linkage_evidence_relabel_and_module_restore_exist(self) -> None:
        for statement in (
            'sys.modules["blender_author_kira_r20_pelvis_only"] = r20_module',
            'load_module("attempt35_bound_r21", r21_path)',
            "r21_module.r20 is not r20_module",
            "provider.r21 is not r21_module or provider.r21.r20 is not r20_module",
            'result["attempt35_dimension_patch"]',
            'replace("attempt34", "attempt35")',
            "attempt34.load_derived_attempt31 = attempt35_load_derived_attempt31",
            "attempt34.load_derived_attempt31 = original_derived_loader",
            "attempt34.__file__ = original_attempt34_file",
            "sys.modules.pop(module_name, None)",
            "sys.modules[module_name] = prior",
        ):
            self.assertIn(statement, self.source)
        run = self.source.index("attempt34.run_blender(config_path, runtime_config)")
        finally_index = self.source.index("finally:", run)
        self.assertLess(run, finally_index)

    def test_13_wrapper_records_integrity_before_propagating_failure(self) -> None:
        source = self.proposal
        invocation = source.index("& $blender --background")
        finally_index = source.index("} finally {", invocation)
        after = source.index("$after = Get-Attempt35Inventory $targets", finally_index)
        create = source.index("[System.IO.FileMode]::CreateNew", after)
        self.assertLess(invocation, finally_index)
        self.assertLess(finally_index, after)
        self.assertLess(after, create)
        for text in (
            "if (-not $exact)",
            "if ($null -ne $invocationError)",
            "if ($exitCode -ne 0)",
        ):
            self.assertGreater(source.index(text, create), create)
        self.assertEqual(source.count("$ErrorActionPreference = 'Continue'"), 1)
        self.assertIn("$ErrorActionPreference = $savedPreference", source)

    def test_14_prepared_state_has_no_runtime_artifacts_and_no_overclaim(self) -> None:
        output = project_path(self.config["runtime_overlay"]["output"]["root"])
        self.assertFalse(output.exists())
        for key in ("stdout", "stderr", "external_integrity"):
            self.assertFalse(project_path(self.config["launch_contract"][key]).exists())
        truth = self.config["truth"]
        for key in (
            "attempt34_append_pass_bound",
            "attempt34_lifecycle_repair_advanced_bound",
            "attempt34_vector_dimension_failure_bound",
        ):
            self.assertTrue(truth[key], key)
        for key, value in truth.items():
            if not key.startswith("attempt34_"):
                self.assertFalse(value, key)

    def test_15_tamper_detection_rejects_scope_patch_source_and_failure_drift(self) -> None:
        tampered = json.loads(json.dumps(self.config))
        tampered["scope"]["repair_domain_change_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "forbidden scope"):
            self.module.validate_config(tampered)
        tampered = json.loads(json.dumps(self.config))
        tampered["dimension_patch"]["reachable_dimensionless_accumulators_after"] = 1
        with self.assertRaisesRegex(RuntimeError, "dimension patch contract"):
            self.module.validate_config(tampered)
        broken15 = self.attempt15_source.replace(self.module.ATTEMPT15_UV_OLD, "", 1)
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            self.module.derive_attempt15_source(broken15, self.config)
        doubled20 = self.r20_source + self.module.R20_NORMAL_RESTORE_OLD
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            self.module.derive_r20_source(doubled20, self.config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
