import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT37_CONFIG.json"
)
WORKER = (
    ROOT
    / "tools"
    / "blender_diagnose_kira_r24_blackproject_candidate_attempt37.py"
)
PROPOSAL = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "PREFLIGHT"
    / "ATTEMPT_37_NONDEGRADING_CDT_CANDIDATE_PROPOSAL.md"
)
CHECKPOINT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "PREFLIGHT"
    / "ATTEMPT_37_STATIC_CHECKPOINT.md"
)
EXPECTED_CONFIG_SHA256 = (
    "f581395a6ddd24f730dfdcd8e8ae87229fca3e2bff4972035ab0118f5ce2bfd1"
)
EXPECTED_WORKER_SHA256 = (
    "15e4fd1fa2c9c02e178c0266421bd0086e555643cc34d86a8b0308c9883db33e"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_path(relative: str) -> Path:
    result = (ROOT / relative).resolve()
    result.relative_to(ROOT)
    return result


class Attempt37StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        spec = importlib.util.spec_from_file_location("attempt37_static", WORKER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.attempt35_path = project_path(
            cls.config["bindings"]["attempt35_worker"]["path"]
        )
        cls.attempt35_source = cls.attempt35_path.read_text(encoding="utf-8")
        cls.derived35_writer = cls.module.patch_attempt35_source(
            cls.attempt35_source, cls.config
        )
        spec35 = importlib.util.spec_from_file_location(
            "attempt37_test_bound_attempt35", cls.attempt35_path
        )
        assert spec35 is not None and spec35.loader is not None
        cls.attempt35_module = importlib.util.module_from_spec(spec35)
        spec35.loader.exec_module(cls.attempt35_module)
        cls.attempt35_config = json.loads(
            project_path(cls.config["bindings"]["attempt35_config"]["path"])
            .read_text(encoding="utf-8")
        )
        cls.attempt15_path = project_path(
            cls.config["bindings"]["attempt15_worker"]["path"]
        )
        cls.derived15_before = cls.attempt35_module.derive_attempt15_source(
            cls.attempt15_path.read_text(encoding="utf-8"),
            cls.attempt35_config,
        )
        cls.derived15_after = cls.module.patch_attempt15_candidate_source(
            cls.derived15_before, cls.config
        )
        cls.derived15_tree = ast.parse(cls.derived15_after)

    def assert_record(self, label: str, record: dict[str, object]) -> Path:
        path = project_path(str(record["path"]))
        self.assertTrue(path.is_file(), label)
        self.assertEqual(path.stat().st_size, int(record["bytes"]), label)
        self.assertEqual(sha256_file(path), record["sha256"], label)
        return path

    def test_01_artifact_hashes_compile_and_load(self) -> None:
        self.assertEqual(CONFIG.stat().st_size, 11597)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(WORKER.stat().st_size, 31552)
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(PROPOSAL.stat().st_size, 5207)
        self.assertEqual(
            sha256_file(PROPOSAL),
            "9a69716f6adf7a8034ff012bd86de5ee9a22b452c9e1e8dd54db8fc846fe75ad",
        )
        compile(self.source, str(WORKER), "exec")
        compile(self.derived35_writer, str(self.attempt35_path), "exec")
        compile(self.derived15_after, str(self.attempt15_path), "exec")
        self.assertEqual(self.module.load_config(), self.config)

    def test_02_all_prior_bindings_are_byte_and_hash_exact(self) -> None:
        self.assertEqual(len(self.config["bindings"]), 17)
        for label, record in self.config["bindings"].items():
            self.assert_record(label, record)
        self.assert_record("proposal", self.config["proposal"])

    def test_03_attempt36_trace_failure_and_integrity_are_exact(self) -> None:
        bindings = self.config["bindings"]
        trace = json.loads(
            project_path(bindings["attempt36_quality_trace"]["path"])
            .read_text(encoding="utf-8")
        )
        failure = json.loads(
            project_path(bindings["attempt36_failure"]["path"])
            .read_text(encoding="utf-8")
        )
        expected = (
            "quality_refined_cdt_failed_minimum_angle:"
            "achieved=0.0:required=12.0:seeds=160"
        )
        self.assertEqual(trace["call_count"], 124)
        self.assertEqual(
            trace["calls_sha256"],
            "99aefc4c3ef4b8d8bdf290d7f39721a8244760df93770cbb74d83ab4f5b186fe",
        )
        self.assertEqual(trace["error"], expected)
        self.assertEqual(failure["error"], expected)
        external = json.loads(
            project_path(bindings["attempt36_external_integrity"]["path"])
            .read_text(encoding="utf-8")
        )
        self.assertTrue(external["pre_post_exact"])
        self.assertEqual(external["before"], external["after"])
        self.assertEqual(len(external["before"]), 216)

    def test_04_exactly_one_candidate_selection_block_is_replaced(self) -> None:
        record = self.config["candidate_selection_patch"]
        self.assertEqual(
            self.module.sha256_text(self.module.ATTEMPT35_CANDIDATE_OLD),
            record["old_block_sha256"],
        )
        self.assertEqual(
            self.module.sha256_text(self.module.ATTEMPT37_CANDIDATE_NEW),
            record["new_block_sha256"],
        )
        self.assertEqual(
            self.derived15_before.count(self.module.ATTEMPT35_CANDIDATE_OLD), 1
        )
        self.assertEqual(
            self.derived15_after.count(self.module.ATTEMPT35_CANDIDATE_OLD), 0
        )
        self.assertEqual(
            self.derived15_after.count(self.module.ATTEMPT37_CANDIDATE_NEW), 1
        )
        restored = self.derived15_after.replace(
            self.module.ATTEMPT37_CANDIDATE_NEW,
            self.module.ATTEMPT35_CANDIDATE_OLD,
            1,
        )
        self.assertEqual(restored, self.derived15_before)

    def test_05_incenter_is_not_reachable_in_repaired_function(self) -> None:
        function = next(
            node
            for node in self.derived15_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "quality_refined_cdt"
        )
        called_names = [
            node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertNotIn("triangle_incenter", called_names)
        self.assertIn("run_cdt", called_names)
        self.assertIn('("circumcenter", circumcenter, None)', self.derived15_after)
        self.assertIn('"centroid"', self.module.ATTEMPT37_CANDIDATE_NEW)

    def test_06_trials_do_not_mutate_accepted_seed_list(self) -> None:
        block_tree = ast.parse("if True:\n" + self.module.ATTEMPT37_CANDIDATE_NEW)
        accepted_appends = [
            node
            for node in ast.walk(block_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "seeds"
            and node.func.attr == "append"
        ]
        trial_appends = [
            node
            for node in ast.walk(block_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "trial_seeds"
            and node.func.attr == "append"
        ]
        self.assertEqual(len(accepted_appends), 1)
        self.assertEqual(len(trial_appends), 1)
        source = self.module.ATTEMPT37_CANDIDATE_NEW
        self.assertLess(source.index("trial_seeds = list(seeds)"), source.index("trial_seeds.append(candidate)"))
        self.assertLess(source.index("if not valid_trials:"), source.index('seeds.append(best["candidate"])'))

    def test_07_trials_enforce_every_proposed_numerical_gate(self) -> None:
        source = self.module.ATTEMPT37_CANDIDATE_NEW
        required = (
            "candidate_represented_once_as_only_new_output_coordinate",
            "boundary_coordinates_exact",
            "output_coordinates_unique_rounded_14",
            "zero_angle_face_count_is_zero",
            "minimum_edge_above_floor",
            "minimum_absolute_double_area_above_floor",
            "strict_global_minimum_angle_improvement",
            "epsilon * 16.0",
            "epsilon * epsilon * 16.0",
            "minimum + improvement_tolerance_degrees",
        )
        for value in required:
            self.assertIn(value, source)

    def test_08_selection_and_failure_are_deterministic_and_evidenced(self) -> None:
        repair = self.config["nondegrading_repair"]
        self.assertEqual(repair["candidate_order"], ["circumcenter", "centroid"])
        self.assertEqual(
            repair["deterministic_valid_trial_score_descending"],
            [
                "minimum_angle_degrees",
                "minimum_edge_m",
                "minimum_absolute_double_area_m2",
                "negative_candidate_order",
            ],
        )
        source = self.module.ATTEMPT37_CANDIDATE_NEW
        self.assertIn('best = max(valid_trials, key=lambda value: value["score"])', source)
        self.assertIn("ATTEMPT37_CDT_REFINEMENT_TRACE.append(iteration_record)", source)
        self.assertIn("quality_refined_cdt_no_nondegrading_candidate:", source)
        self.assertIn('"trials": trial_records', source)

    def test_09_original_bootstrap_threshold_cap_and_domain_remain_exact(self) -> None:
        function_source = ast.get_source_segment(
            self.derived15_after,
            next(
                node
                for node in self.derived15_tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "quality_refined_cdt"
            ),
        )
        assert function_source is not None
        self.assertIn(
            'sum((base["coordinates"][index] for index in face), Vector((0.0, 0.0))) / 3.0',
            function_source,
        )
        self.assertIn('threshold = float(config["minimum_new_triangle_angle_degrees"])', function_source)
        self.assertIn('maximum_vertices = int(config["maximum_new_interior_vertex_count"])', function_source)
        config31 = json.loads(
            project_path(self.config["bindings"]["attempt31_config"]["path"])
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            config31["selected_candidate"]["candidate"],
            "targeted_complete_vertex_stars_2_6_20_28",
        )
        self.assertEqual(
            config31["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"],
            12.0,
        )
        self.assertEqual(
            config31["unchanged_hard_gates"]["maximum_new_interior_vertex_count"],
            160,
        )

    def test_10_exact_accepted_trial_result_can_return_without_recomputation(self) -> None:
        source = self.module.ATTEMPT37_CANDIDATE_NEW
        selected = source.index('result = best["result"]')
        threshold = source.index('if best["minimum_angle"] >= threshold:', selected)
        returned = source.index("return result", threshold)
        self.assertLess(selected, threshold)
        self.assertLess(threshold, returned)

    def test_11_append_only_writer_labels_attempt37_without_losing_attempt35_metadata(self) -> None:
        record = self.config["evidence_writer_patch"]
        self.assertEqual(
            self.module.sha256_text(self.module.ATTEMPT35_WRITER_OLD),
            record["old_block_sha256"],
        )
        self.assertEqual(
            self.module.sha256_text(self.module.ATTEMPT35_WRITER_NEW),
            record["new_block_sha256"],
        )
        self.assertEqual(self.attempt35_source.count(self.module.ATTEMPT35_WRITER_OLD), 1)
        self.assertEqual(self.derived35_writer.count(self.module.ATTEMPT35_WRITER_NEW), 1)
        self.assertIn('result["attempt35_dimension_patch"]', self.derived35_writer)
        self.assertIn('result["attempt37_nondegrading_cdt_repair"]', self.derived35_writer)

    def test_12_static_import_has_no_blender_save_render_export_or_launch(self) -> None:
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
            "subprocess",
            "Popen",
        ):
            self.assertNotIn(forbidden, self.source)

    def test_13_static_state_has_no_attempt37_runtime_artifacts(self) -> None:
        output = project_path(self.config["runtime_overlay"]["output"]["root"])
        self.assertFalse(output.exists())
        for key in ("stdout", "stderr", "external_integrity"):
            self.assertFalse(project_path(self.config["launch_contract"][key]).exists())
        truth = self.config["truth"]
        self.assertTrue(truth["attempt37_worker_prepared"])
        self.assertTrue(truth["attempt37_config_prepared"])
        self.assertTrue(truth["attempt37_static_tests_prepared"])
        for key in (
            "attempt37_blender_execution_performed",
            "attempt37_candidate_patch_executed_in_blender",
            "attempt37_trial_evidence_written",
            "attempt37_reconstruction_performed",
            "attempt37_body_mutation_performed",
            "attempt37_render_reached",
            "attempt37_blend_saved",
            "runtime_changed",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[key], key)

    def test_14_checkpoint_records_create_new_integrity_wrapper_and_stop_boundary(self) -> None:
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for value in (
            "STATIC_REPAIR_PREPARED_NOT_RUN",
            "not executed",
            "[System.IO.FileMode]::CreateNew",
            "Get-Attempt37Inventory",
            "attempt37_external_pre_post_integrity.json",
            "if (-not $exact)",
            "if ($null -ne $invocationError)",
            "if ($exitCode -ne 0)",
            "Do not launch Attempt 37",
        ):
            self.assertIn(value, checkpoint)
        invocation = checkpoint.index("& $blender --background")
        finally_index = checkpoint.index("} finally {", invocation)
        after = checkpoint.index("$after = Get-Attempt37Inventory $targets", finally_index)
        create = checkpoint.index("[System.IO.FileMode]::CreateNew", after)
        self.assertLess(invocation, finally_index)
        self.assertLess(finally_index, after)
        self.assertLess(after, create)

    def test_15_tamper_detection_rejects_scope_patch_and_source_drift(self) -> None:
        tampered = json.loads(json.dumps(self.config))
        tampered["scope"]["boundary_change_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "forbidden scope"):
            self.module.validate_config(tampered)
        tampered = json.loads(json.dumps(self.config))
        tampered["nondegrading_repair"]["incenter_reachable"] = True
        with self.assertRaisesRegex(RuntimeError, "repair contract"):
            self.module.validate_config(tampered)
        broken = self.derived15_before.replace(
            self.module.ATTEMPT35_CANDIDATE_OLD, "", 1
        )
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            self.module.patch_attempt15_candidate_source(broken, self.config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
