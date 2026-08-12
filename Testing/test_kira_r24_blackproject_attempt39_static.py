"""Static-only gates for the unexecuted Attempt 39 relocation proposal."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_candidate_attempt39.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT39_CONFIG.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module() -> object:
    name = "attempt39_static_test_module"
    spec = importlib.util.spec_from_file_location(name, WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 39 static worker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Attempt39StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_overlay(cls.config)
        cls.derived15 = cls.module.patch_attempt15_candidate_source(
            (
                cls.module._load_static_module(
                    "attempt39_test_bound_attempt35",
                    ROOT / cls.config["bindings"]["attempt35_worker"]["path"],
                ).derive_attempt15_source(
                    (ROOT / cls.config["bindings"]["attempt15_worker"]["path"]).read_text(encoding="utf-8"),
                    json.loads(
                        (ROOT / cls.config["bindings"]["attempt35_config"]["path"]).read_text(encoding="utf-8")
                    ),
                )
            ),
            cls.config,
            cls.verified["attempt38"],
            cls.verified["attempt37"],
        )

    def test_01_worker_and_config_are_exact_and_static(self) -> None:
        self.assertEqual(WORKER.stat().st_size, 40630)
        self.assertEqual(
            sha256(WORKER),
            "f6e980bcab814e57c93e200ba4a27e38fb885a08048a24522751c5c8b61417ab",
        )
        self.assertEqual(CONFIG.stat().st_size, 12044)
        self.assertEqual(
            sha256(CONFIG),
            "1c2a11a0f3a7ac3d90cc87a6d91d1d1968bb869f6f0e5fa120dcad4c458c4b87",
        )
        self.assertEqual(self.config["status"], "STATIC_REPAIR_PREPARED_NOT_RUN")

    def test_02_attempt38_failure_and_integrity_are_exactly_bound(self) -> None:
        self.assertEqual(
            self.verified["trials"]["error"],
            "quality_refined_cdt_no_nondegrading_candidate:current=2.635073748299402:iteration=0:seeds=38",
        )
        self.assertEqual(
            self.verified["trials"]["iterations"][0]["worst_face"],
            [77, 23, 24],
        )
        self.assertFalse(self.verified["failure"]["render_reached"])
        self.assertFalse(self.verified["failure"]["blend_saved"])

    def test_03_patch_is_one_exact_block_and_compiles(self) -> None:
        patch = self.config["candidate_selection_patch"]
        self.assertEqual(patch["exact_replacement_count"], 1)
        self.assertEqual(
            self.module.sha256_text(self.module.ATTEMPT39_CANDIDATE_NEW),
            patch["new_block_sha256"],
        )
        self.assertEqual(
            self.module.sha256_text(self.derived15),
            patch["derived_attempt15_source_sha256"],
        )
        compile(self.derived15, "attempt39_derived_attempt15.py", "exec")
        tree = ast.parse(self.derived15)
        functions = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "quality_refined_cdt"
        ]
        self.assertEqual(len(functions), 1)

    def test_04_initial_bootstrap_boundary_and_limits_remain_unchanged(self) -> None:
        source = self.derived15
        self.assertIn('base = run_cdt(boundary, [], epsilon)', source)
        self.assertIn('for face in base["faces"]', source)
        self.assertIn('for iteration in range(maximum_iterations + 1):', source)
        repair = self.config["guarded_seed_relocation"]
        self.assertEqual(repair["initial_bootstrap_centroid_count_unchanged"], 38)
        self.assertEqual(repair["cdt_epsilon_m_unchanged"], 1e-12)
        self.assertEqual(repair["maximum_seed_count_unchanged"], 160)
        self.assertEqual(repair["maximum_quality_refinement_iterations_unchanged"], 192)

    def test_05_relocation_requires_exact_geometric_identity(self) -> None:
        source = self.module.ATTEMPT39_CANDIDATE_NEW
        for required in (
            "worst_face_does_not_have_exactly_one_constrained_boundary_edge",
            "worst_face_does_not_have_exactly_one_nonboundary_vertex",
            "nonboundary_vertex_does_not_match_exactly_one_accepted_seed",
            "ordered_boundary_sources",
            "matching_seed_indices",
        ):
            self.assertIn(required, source)

    def test_06_trials_are_removal_and_deterministic_inward_offcenters(self) -> None:
        repair = self.config["guarded_seed_relocation"]
        self.assertEqual(
            repair["trial_order"],
            [
                "remove_seed_only",
                "relocate_offcenter_12.5_degrees",
                "relocate_offcenter_18_degrees",
                "relocate_offcenter_24_degrees",
            ],
        )
        source = self.module.ATTEMPT39_CANDIDATE_NEW
        self.assertIn("math.tan(math.radians(target_angle_degrees))", source)
        self.assertIn("midpoint + inward * height", source)
        self.assertIn("candidate_not_strictly_on_ccw_interior_side", source)

    def test_07_trials_do_not_mutate_accepted_seeds_before_selection(self) -> None:
        source = self.module.ATTEMPT39_CANDIDATE_NEW
        self.assertIn("trial_seeds = list(seeds)", source)
        self.assertIn("removed_seed = trial_seeds.pop(old_seed_index)", source)
        selection = source.index('best = max(valid_trials, key=lambda value: value["score"])')
        accepted_mutation = source.index('seeds = list(best["seeds"])')
        self.assertGreater(accepted_mutation, selection)
        self.assertTrue(self.config["guarded_seed_relocation"]["trial_mutates_accepted_seed_list"] is False)

    def test_08_every_numerical_and_coordinate_gate_is_fail_closed(self) -> None:
        source = self.module.ATTEMPT39_CANDIDATE_NEW
        for required in (
            "exact_one_seed_remove_or_relocation_coordinate_transition",
            "boundary_coordinates_exact",
            "output_coordinates_unique_rounded_14",
            "zero_angle_face_count_is_zero",
            "minimum_edge_above_floor",
            "minimum_absolute_double_area_above_floor",
            "epsilon * 16.0",
            "epsilon * epsilon * 16.0",
        ):
            self.assertIn(required, source)

    def test_09_quality_cannot_degrade_and_ties_require_count_progress(self) -> None:
        source = self.module.ATTEMPT39_CANDIDATE_NEW
        self.assertIn("trial_minimum_angle >= minimum", source)
        self.assertIn("trial_floor_face_count < current_floor_face_count", source)
        self.assertIn("strict_global_minimum_improvement", source)
        self.assertIn("tied_floor_face_count_reduction", source)
        self.assertIn("deterministic_quality_progress", source)
        self.assertTrue(
            self.config["guarded_seed_relocation"]["global_minimum_degradation_allowed"]
            is False
        )

    def test_10_final_12_degree_and_all_downstream_gates_remain_closed(self) -> None:
        repair = self.config["guarded_seed_relocation"]
        self.assertEqual(repair["minimum_angle_gate_degrees_unchanged"], 12.0)
        self.assertEqual(repair["minimum_world_area_gate_m2_unchanged"], 1e-10)
        contract = self.config["unchanged_geometry_and_quality_contract"]
        self.assertEqual(contract["selected_candidate"], "targeted_complete_vertex_stars_2_6_20_28")
        self.assertEqual(contract["selected_boundary_edge_count"], 40)
        self.assertGreater(contract["selected_minimum_boundary_angle_degrees"], 12.0)
        self.assertTrue(contract["intersection_seam_sanitation_preservation_and_area_gates_unchanged"])

    def test_11_no_blender_run_or_runtime_targets_exist(self) -> None:
        self.assertFalse(
            (ROOT / self.config["runtime_overlay"]["output"]["root"]).exists()
        )
        launch = self.config["launch_contract"]
        for key in ("stdout", "stderr", "external_integrity"):
            self.assertFalse((ROOT / launch[key]).exists(), key)
        self.assertFalse(launch["executed_during_static_preparation"])
        self.assertFalse(self.config["truth"]["attempt39_blender_execution_performed"])

    def test_12_no_save_render_activation_or_retry_is_permitted(self) -> None:
        scope = self.config["scope"]
        for key in (
            "render_allowed",
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "automatic_retry_allowed",
            "boundary_change_allowed",
            "quality_gate_reduction_allowed",
        ):
            self.assertFalse(scope[key], key)

    def test_13_offcenter_formula_has_the_requested_local_base_angles(self) -> None:
        first = (-0.0003287002327851951, -0.0012715889606624842)
        second = (-0.0003225125838071108, -0.002141158562153578)
        edge = (second[0] - first[0], second[1] - first[1])
        length = math.hypot(*edge)
        midpoint = ((first[0] + second[0]) / 2.0, (first[1] + second[1]) / 2.0)
        inward = (-edge[1] / length, edge[0] / length)
        for target in (12.5, 18.0, 24.0):
            height = length * 0.5 * math.tan(math.radians(target))
            candidate = (
                midpoint[0] + inward[0] * height,
                midpoint[1] + inward[1] * height,
            )
            left = (second[0] - first[0], second[1] - first[1])
            to_candidate = (candidate[0] - first[0], candidate[1] - first[1])
            self.assertGreater(left[0] * to_candidate[1] - left[1] * to_candidate[0], 0.0)
            dot = left[0] * to_candidate[0] + left[1] * to_candidate[1]
            cosine = dot / (math.hypot(*left) * math.hypot(*to_candidate))
            measured = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
            self.assertAlmostEqual(measured, target, places=10)


if __name__ == "__main__":
    unittest.main()
