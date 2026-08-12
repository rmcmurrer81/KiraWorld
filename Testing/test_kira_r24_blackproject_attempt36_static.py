"""Static verification for prepared, unexecuted R24 Attempt 36."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT36_CONFIG.json"
)
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_candidate_attempt36.py"
PROPOSAL = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_36_CDT_QUALITY_TRACE_PROPOSAL.md"
)
EXPECTED_CONFIG_SHA256 = "4cafcc80ad746975bbb66ffe2ba3b58c2264d9ddbe8e1ccb5b9433c03a327cc1"
EXPECTED_WORKER_SHA256 = "774d71909fda3621b22c214bb67c3c27bd3196a283bef83db7f198799ba9c957"
EXPECTED_PROPOSAL_SHA256 = "7160c9c8c7218b26ee48bf28056d0157aab1638d998d532730ecff7a2a0c6bb0"


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


class V:
    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def __getitem__(self, index: int) -> float:
        return (self.x, self.y)[index]

    def __add__(self, other: "V") -> "V":
        return V(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "V") -> "V":
        return V(self.x - other.x, self.y - other.y)

    def __mul__(self, value: float) -> "V":
        return V(self.x * value, self.y * value)

    __rmul__ = __mul__

    def __truediv__(self, value: float) -> "V":
        return V(self.x / value, self.y / value)

    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y)


class FakeProvider:
    @staticmethod
    def orient2d(first: V, second: V, third: V) -> float:
        return (second.x - first.x) * (third.y - first.y) - (
            second.y - first.y
        ) * (third.x - first.x)

    @staticmethod
    def triangle_angles(points: list[V]) -> list[float]:
        values = []
        for index in range(3):
            first = points[(index + 1) % 3] - points[index]
            second = points[(index + 2) % 3] - points[index]
            cosine = (first.x * second.x + first.y * second.y) / (
                first.length * second.length
            )
            values.append(math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))
        return values

    @staticmethod
    def triangle_incenter(points: list[V]) -> V:
        first, second, third = points
        weights = ((second - third).length, (first - third).length, (first - second).length)
        total = sum(weights)
        return (first * weights[0] + second * weights[1] + third * weights[2]) / total


class Attempt36StaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.proposal = PROPOSAL.read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("attempt36_static", WORKER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.attempt35_path = project_path(
            cls.config["bindings"]["attempt35_worker"]["path"]
        )
        cls.attempt35_source = cls.attempt35_path.read_text(encoding="utf-8")
        cls.derived35 = cls.module.patch_attempt35_source(
            cls.attempt35_source, cls.config
        )

    def assert_record(self, label: str, record: dict[str, object]) -> Path:
        path = project_path(str(record["path"]))
        self.assertTrue(path.is_file(), label)
        self.assertEqual(path.stat().st_size, int(record["bytes"]), label)
        self.assertEqual(sha256_file(path), record["sha256"], label)
        return path

    def test_01_artifact_hashes_and_compile(self) -> None:
        self.assertEqual(CONFIG.stat().st_size, 8671)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(WORKER.stat().st_size, 22712)
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(PROPOSAL.stat().st_size, 10121)
        self.assertEqual(sha256_file(PROPOSAL), EXPECTED_PROPOSAL_SHA256)
        compile(self.source, str(WORKER), "exec")
        compile(self.derived35, str(self.attempt35_path), "exec")

    def test_02_every_binding_and_proposal_is_exact(self) -> None:
        for label, record in self.config["bindings"].items():
            self.assert_record(label, record)
        self.assert_record("proposal", self.config["proposal"])

    def test_03_static_loader_overlay_and_derived_hash_pass(self) -> None:
        loaded = self.module.load_config()
        self.assertEqual(loaded, self.config)
        verified = self.module.verify_overlay(loaded)
        self.assertEqual(len(verified["records"]), 14)
        self.assertEqual(
            verified["derived_attempt35_sha256"],
            "5a3dade4c9f9acedd7227e51fd547d558422567ccf180bacf97a6e623b34e44c",
        )

    def test_04_attempt35_failure_and_external_integrity_are_exact(self) -> None:
        bindings = self.config["bindings"]
        failure = json.loads(
            project_path(bindings["attempt35_failure"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(failure["error_type"], "RuntimeError")
        self.assertEqual(
            failure["error"],
            "quality_refined_cdt_failed_minimum_angle:achieved=0.0:required=12.0:seeds=160",
        )
        self.assertIn("line 330, in quality_refined_cdt", failure["traceback"])
        self.assertFalse(failure["render_reached"])
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        external = json.loads(
            project_path(bindings["attempt35_external_integrity"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(external["blender_exit_code"], 1)
        self.assertIsNone(external["native_invocation_error"])
        self.assertTrue(external["pre_post_exact"])
        self.assertEqual(external["before"], external["after"])
        self.assertEqual(len(external["before"]), 204)

    def test_05_evidence_writer_blocks_are_exact_unique_and_hash_bound(self) -> None:
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
        self.assertEqual(self.derived35.count(self.module.ATTEMPT35_WRITER_OLD), 0)
        self.assertEqual(self.derived35.count(self.module.ATTEMPT35_WRITER_NEW), 1)
        self.assertIn('result["attempt36_quality_instrumentation"]', self.derived35)
        self.assertIn('result["attempt_id"] = "attempt_36"', self.derived35)

    def test_06_trace_wrapper_calls_original_once_and_returns_same_result(self) -> None:
        run = next(
            node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "traced_run_cdt"
        )
        original_calls = [
            node
            for node in ast.walk(run)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "original_run_cdt"
        ]
        self.assertEqual(len(original_calls), 1)
        returns = [node for node in ast.walk(run) if isinstance(node, ast.Return)]
        self.assertEqual(len(returns), 1)
        self.assertIsInstance(returns[0].value, ast.Name)
        self.assertEqual(returns[0].value.id, "result")
        self.assertIn("result = original_run_cdt(boundary, seeds, epsilon)", self.source)

    def test_07_instrumentation_has_no_input_or_result_mutation(self) -> None:
        instrument = self.config["quality_instrumentation"]
        self.assertEqual(instrument["original_call_count_per_wrapper_call"], 1)
        self.assertTrue(instrument["return_exact_original_result"])
        self.assertFalse(instrument["mutate_inputs_or_result"])
        self.assertFalse(instrument["change_quality_decisions"])
        self.assertTrue(instrument["measurement_error_must_not_change_pipeline_outcome"])
        run = next(
            node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "traced_run_cdt"
        )
        mutating_methods = {"append", "extend", "insert", "pop", "remove", "clear", "update", "sort", "reverse"}
        forbidden_calls = [
            node
            for node in ast.walk(run)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"boundary", "seeds", "result"}
            and node.func.attr in mutating_methods
        ]
        self.assertEqual(forbidden_calls, [])
        self.assertNotIn("provider.quality_refined_cdt =", self.source)
        self.assertIn("except Exception as measurement_error:", self.source)
        self.assertIn(
            '"exact_original_result_returned_despite_measurement_error": True',
            self.source,
        )

    def test_08_pure_measurement_smoke_is_deterministic_and_nonmutating(self) -> None:
        boundary = [V(0.0, 0.0), V(1.0, 0.0), V(0.0, 1.0)]
        seeds: list[V] = []
        result = {
            "coordinates": list(boundary),
            "faces": [[0, 1, 2]],
            "maximum_boundary_delta_2d_m": 0.0,
        }
        before = json.dumps(
            {
                "boundary": [(value.x, value.y) for value in boundary],
                "seeds": [],
                "faces": result["faces"],
            },
            sort_keys=True,
        )
        first = self.module.measure_cdt_call(
            FakeProvider, boundary, seeds, 1e-10, result, None, 0
        )
        second = self.module.measure_cdt_call(
            FakeProvider, boundary, seeds, 1e-10, result, None, 0
        )
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["minimum_triangle_angle_degrees"], 45.0)
        self.assertEqual(first["zero_angle_face_count"], 0)
        self.assertEqual(first["output_face_count"], 1)
        after = json.dumps(
            {
                "boundary": [(value.x, value.y) for value in boundary],
                "seeds": [],
                "faces": result["faces"],
            },
            sort_keys=True,
        )
        self.assertEqual(before, after)

    def test_09_trace_fields_cover_the_exact_evidence_gap(self) -> None:
        fields = set(self.config["quality_instrumentation"]["recorded_fields"])
        for required in (
            "new_seed_coordinates_and_prior_worst_candidate_classification",
            "seed_duplicate_groups_rounded_14",
            "output_duplicate_coordinate_groups_rounded_14",
            "minimum_triangle_angle_degrees",
            "minimum_edge_length_m",
            "minimum_absolute_double_area_m2",
            "zero_angle_face_count_and_sha256",
            "first_16_exact_zero_angle_faces",
            "exact_worst_face_and_candidate_coordinates",
        ):
            self.assertIn(required, fields)
        self.assertIn('state["calls_sha256"]', self.source)
        self.assertIn('state["final_call"]', self.source)
        self.assertIn("_write_trace_once(trace_path, state)", self.source)

    def test_10_candidate_domain_seed_cap_and_hard_gates_remain_exact(self) -> None:
        attempt35 = json.loads(
            project_path(self.config["bindings"]["attempt35_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        attempt34_record = attempt35["bindings"]["attempt34_config"]
        attempt34 = json.loads(
            self.assert_record("attempt34_config", attempt34_record).read_text(
                encoding="utf-8"
            )
        )
        attempt31_record = attempt34["bindings"]["attempt31_config"]
        attempt31 = json.loads(
            self.assert_record("attempt31_config", attempt31_record).read_text(
                encoding="utf-8"
            )
        )
        selected = attempt31["selected_candidate"]
        self.assertEqual(selected["candidate"], "targeted_complete_vertex_stars_2_6_20_28")
        self.assertEqual(
            [selected["face_count"], selected["vertex_count"], selected["edge_count"], selected["interior_vertex_count"], selected["boundary_edge_count"]],
            [104, 73, 176, 33, 40],
        )
        hard = attempt31["unchanged_hard_gates"]
        self.assertEqual(hard["maximum_new_interior_vertex_count"], 160)
        self.assertEqual(hard["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(hard["minimum_new_triangle_world_area_m2"], 1e-10)

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

    def test_12_wrapper_records_integrity_before_propagating_failure(self) -> None:
        source = self.proposal
        invocation = source.index("& $blender --background")
        finally_index = source.index("} finally {", invocation)
        after = source.index("$after = Get-Attempt36Inventory $targets", finally_index)
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

    def test_13_prepared_state_has_no_runtime_artifacts_and_no_overclaim(self) -> None:
        output = project_path(self.config["runtime_overlay"]["output"]["root"])
        self.assertFalse(output.exists())
        for key in ("stdout", "stderr", "external_integrity"):
            self.assertFalse(project_path(self.config["launch_contract"][key]).exists())
        truth = self.config["truth"]
        self.assertTrue(truth["attempt35_pipeline_bound"])
        self.assertTrue(truth["attempt35_quality_failure_bound"])
        for key, value in truth.items():
            if not key.startswith("attempt35_"):
                self.assertFalse(value, key)

    def test_14_tamper_detection_rejects_scope_instrumentation_and_source_drift(self) -> None:
        tampered = json.loads(json.dumps(self.config))
        tampered["scope"]["quality_gate_reduction_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "forbidden scope"):
            self.module.validate_config(tampered)
        tampered = json.loads(json.dumps(self.config))
        tampered["quality_instrumentation"]["original_call_count_per_wrapper_call"] = 2
        with self.assertRaisesRegex(RuntimeError, "instrumentation contract"):
            self.module.validate_config(tampered)
        broken = self.attempt35_source.replace(self.module.ATTEMPT35_WRITER_OLD, "", 1)
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            self.module.patch_attempt35_source(broken, self.config)
        doubled = self.attempt35_source + self.module.ATTEMPT35_WRITER_OLD
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            self.module.patch_attempt35_source(doubled, self.config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
