"""Pure/static tests for the inactive profiled adult candidate builder.

These tests intentionally do not import bpy, invoke Blender, render, save, or
create a candidate directory.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import LANDMARK_GROUP_PREFIX
import Core.avatar_profiled_adult_candidate_contract as contract_module
from Core.avatar_profiled_adult_candidate_contract import (
    BUILDER_CONFIG_PATH,
    LIVE_KIRA_STATE_FILES,
    OWNER_REVIEW_VIEW_LABELS,
    QUALIFIED_FOUNDATION_AUTHORING_CONFIG,
    QUALIFIED_FOUNDATION_AUTHORING_CONFIG_SHA256,
    REQUIRED_FOUNDATION_ID,
    _private_output_path,
    capture_live_kira_state_hashes,
    evaluate_profiled_candidate_preflight,
    scaled_adult_surface_settings,
    validate_profiled_candidate_builder_config,
    verify_live_kira_state_unchanged,
)


COMPONENTS_PATH = PROJECT_ROOT / "tools/blender_profiled_adult_candidate_components.py"
BUILDER_PATH = PROJECT_ROOT / "tools/blender_build_profiled_kira_adult_candidate.py"
PROFILE_PATH = PROJECT_ROOT / (
    "Avatar/avatar_builder/style_profiles/"
    "natural_athletic_warm_asymmetric_waves_v1.json"
)
CONFIG_PATH = PROJECT_ROOT / BUILDER_CONFIG_PATH
STATIC_OUTPUT = Path(
    "Avatar/private_owner_review/kira_profiled_adult_candidate_static_contract_20260801"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _call_order(tree: ast.AST, function_name: str) -> list[str]:
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    calls: list[str] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Name):
            calls.append(target.id)
        elif isinstance(target, ast.Attribute):
            calls.append(target.attr)
    # ast.walk is breadth-first rather than execution order; line ordering is
    # the relevant static invariant for these direct build calls.
    direct = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and hasattr(node, "lineno")
    ]
    direct.sort(key=lambda node: (node.lineno, node.col_offset))
    result: list[str] = []
    for node in direct:
        if isinstance(node.func, ast.Name):
            result.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            result.append(node.func.attr)
    return result


class ProfiledAdultCandidateContractTests(unittest.TestCase):
    def test_exact_configuration_and_live_preflight_are_read_only(self) -> None:
        self.assertFalse((PROJECT_ROOT / STATIC_OUTPUT).exists())
        config = validate_profiled_candidate_builder_config(PROJECT_ROOT)
        self.assertTrue(config["valid"], config["blockers"])
        self.assertEqual(config["status"], "VALIDATED_BUILDER_CONFIG")
        report = evaluate_profiled_candidate_preflight(PROJECT_ROOT, STATIC_OUTPUT)
        self.assertFalse((PROJECT_ROOT / STATIC_OUTPUT).exists())
        self.assertFalse(report["build_performed"])
        self.assertFalse(report["blender_scene_mutated"])
        self.assertFalse(report["candidate_saved"])
        self.assertEqual(report["required_foundation_id"], REQUIRED_FOUNDATION_ID)
        if report["ready"]:
            self.assertEqual(report["status"], "READY_FOR_EXPLICIT_INACTIVE_BUILD")
            self.assertTrue(report["foundation"]["qualified_for_adult_foundation"])
            self.assertTrue(report["style_profile"]["valid"])
        else:
            self.assertEqual(report["status"], "BLOCKED_BEFORE_BLENDER_MUTATION")
            self.assertTrue(report["blockers"])

    def test_configuration_binds_exact_source_profile_and_policy(self) -> None:
        config = _json(CONFIG_PATH)
        profile = _json(PROFILE_PATH)
        self.assertEqual(config["required_qualified_foundation_id"], REQUIRED_FOUNDATION_ID)
        self.assertEqual(config["style_profile"]["sha256"], _sha256(PROFILE_PATH))
        self.assertEqual(config["style_profile"]["required_target_count"], 12)
        self.assertEqual(config["style_profile"]["required_target_height_m"], 1.651)
        self.assertEqual(len(profile["shape_targets"]), 12)
        self.assertEqual(profile["material_profile"]["skin"]["base_srgb_hex"], "#C7A08E")
        self.assertEqual(profile["eye_profile"]["iris_color_family"], "brown")
        source = config["makehuman_source_set"]
        self.assertEqual(source["base_body"]["face_group"], "body")
        self.assertEqual(len(source["female_macros"]), 2)
        self.assertFalse(source["male_helper_groups_allowed"])
        self.assertFalse(source["copied_anatomy_geometry_allowed"])
        rig = config["official_rig"]
        self.assertEqual(rig["maximum_influences"], 4)
        self.assertTrue(rig["normalize_every_vertex"])
        self.assertTrue(rig["fallback_root_for_unweighted"])
        output = config["output_policy"]
        self.assertTrue(output["direct_new_child_only"])
        self.assertFalse(output["overwrite_allowed"])
        self.assertTrue(output["inactive"])
        self.assertFalse(output["assigned"])
        self.assertFalse(output["clothing_included"])
        self.assertFalse(output["publication_allowed"])
        self.assertFalse(output["runtime_activation_allowed"])
        self.assertEqual(config["protected_live_kira_state"], [p.as_posix() for p in LIVE_KIRA_STATE_FILES])
        self.assertEqual(config["owner_review_view_labels"], list(OWNER_REVIEW_VIEW_LABELS))
        self.assertEqual(config["hair_provider_interface"]["callable_name"], "build_dynamic_hair")

    def test_adult_authoring_frame_and_metrics_scale_with_height(self) -> None:
        config = _json(CONFIG_PATH)
        authoring = config["adult_surface_authoring"]
        frame, parameters = scaled_adult_surface_settings(authoring, 1.651)
        ratio = 1.651 / 1.7
        for actual, baseline in zip(frame["origin"], authoring["frame"]["origin"]):
            self.assertAlmostEqual(actual, baseline * ratio, places=12)
        for name in ("half_width_m", "half_length_m", "max_surface_offset_m"):
            self.assertAlmostEqual(frame[name], authoring["frame"][name] * ratio, places=12)
        self.assertAlmostEqual(
            parameters["relief_scale_m"],
            authoring["parameters"]["relief_scale_m"] * ratio,
            places=12,
        )
        self.assertAlmostEqual(
            parameters["degeneracy_area_m2"],
            authoring["parameters"]["degeneracy_area_m2"] * ratio * ratio,
            places=18,
        )

    def test_adult_authoring_is_exactly_bound_to_qualified_neutral_config(self) -> None:
        config = _json(CONFIG_PATH)
        authoring = config["adult_surface_authoring"]
        neutral_path = PROJECT_ROOT / QUALIFIED_FOUNDATION_AUTHORING_CONFIG
        neutral = _json(neutral_path)
        binding = authoring["qualified_neutral_config"]
        self.assertEqual(binding["path"], QUALIFIED_FOUNDATION_AUTHORING_CONFIG.as_posix())
        self.assertEqual(binding["sha256"], QUALIFIED_FOUNDATION_AUTHORING_CONFIG_SHA256)
        self.assertEqual(binding["sha256"], _sha256(neutral_path))
        self.assertEqual(authoring["baseline_height_m"], neutral["target_height_m"])
        self.assertEqual(authoring["frame"], neutral["frame"])
        self.assertEqual(authoring["parameters"], neutral["parameters"])

    def test_any_authoring_drift_from_qualified_neutral_config_fails_closed(self) -> None:
        original_read_json = contract_module._read_json

        def drifted_read(path: Path) -> dict:
            payload = original_read_json(path)
            if Path(path).resolve() == CONFIG_PATH.resolve():
                payload = copy.deepcopy(payload)
                payload["adult_surface_authoring"]["parameters"]["relief_scale_m"] += 0.0001
            return payload

        with patch.object(contract_module, "_read_json", side_effect=drifted_read):
            report = validate_profiled_candidate_builder_config(PROJECT_ROOT)
        self.assertFalse(report["valid"])
        self.assertIn(
            "adult_surface_parameters_not_exact_qualified_config",
            report["blockers"],
        )

    def test_output_policy_refuses_unsafe_or_existing_paths_without_writes(self) -> None:
        blockers: list[str] = []
        self.assertIsNone(_private_output_path(PROJECT_ROOT, Path("../escape"), blockers))
        self.assertIn("output_directory_unsafe", blockers)
        blockers = []
        wrong = Path("Avatar/private_owner_review/nongated_candidate_20260801")
        self.assertIsNone(_private_output_path(PROJECT_ROOT, wrong, blockers))
        self.assertIn("output_directory_name_invalid", blockers)
        blockers = []
        with patch.object(Path, "exists", return_value=True):
            resolved = _private_output_path(PROJECT_ROOT, STATIC_OUTPUT, blockers)
        self.assertIsNotNone(resolved)
        self.assertIn("output_directory_already_exists_refuse_overwrite", blockers)
        self.assertFalse((PROJECT_ROOT / STATIC_OUTPUT).exists())

    def test_exact_three_live_files_hash_and_detect_drift_in_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for index, relative in enumerate(LIVE_KIRA_STATE_FILES):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"fixture-{index}".encode("ascii"))
            before = capture_live_kira_state_hashes(root)
            self.assertEqual(list(before), [path.as_posix() for path in LIVE_KIRA_STATE_FILES])
            unchanged = verify_live_kira_state_unchanged(root, before)
            self.assertTrue(unchanged["passed"], unchanged["blockers"])
            (root / LIVE_KIRA_STATE_FILES[1]).write_bytes(b"drift")
            changed = verify_live_kira_state_unchanged(root, before)
            self.assertFalse(changed["passed"])
            self.assertIn(
                f"live_state_changed:{LIVE_KIRA_STATE_FILES[1].as_posix()}",
                changed["blockers"],
            )


class ProfiledAdultCandidateStaticBlenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.component_source = COMPONENTS_PATH.read_text(encoding="utf-8")
        cls.builder_source = BUILDER_PATH.read_text(encoding="utf-8")
        cls.component_tree = ast.parse(cls.component_source)
        cls.builder_tree = ast.parse(cls.builder_source)

    def test_blender_modules_parse_and_do_not_import_prior_body_geometry(self) -> None:
        for tree in (self.component_tree, self.builder_tree):
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = str(node.module or "").lower()
                    self.assertNotIn("temporary_functional_body", module)
                    self.assertNotIn("blackproject", module)
                    self.assertNotIn("robert", module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.lower()
                        self.assertNotIn("temporary_functional_body", module)
                        self.assertNotIn("blackproject", module)
        prohibited_fixed_indices = {4370, 4372, 6335, 12932, 6392, 12989, 6393, 12990, 6394, 12991, 6395, 12992}
        numeric_constants = {
            node.value
            for tree in (self.component_tree, self.builder_tree)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
        }
        self.assertFalse(prohibited_fixed_indices.intersection(numeric_constants))

    def test_no_blender_build_or_candidate_is_invoked_at_module_scope(self) -> None:
        for tree in (self.component_tree, self.builder_tree):
            for node in tree.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    self.fail(f"top-level Blender call at line {node.lineno}")
        guarded_main = [
            node
            for node in self.builder_tree.body
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and any(
                isinstance(value, ast.Constant) and value.value == "__main__"
                for value in ast.walk(node.test)
            )
        ]
        self.assertEqual(len(guarded_main), 1)

    def test_build_preflight_precedes_every_scene_mutation_and_order_is_bounded(self) -> None:
        order = _call_order(self.builder_tree, "build")
        required = [
            "evaluate_profiled_candidate_preflight",
            "_capture_build_hash_snapshot",
            "_assert_background_factory_startup_safe_scene",
            "_clear_scene_after_preflight",
            "prepare_profiled_body_source",
            "build_official_rig_and_normalized_weights",
            "repair_bounded_self_intersections",
            "author_continuous_adult_female_surface",
            "add_natural_helper_eyes",
            "add_natural_nails",
            "solve_bilateral_knee_axes_and_actions",
            "invoke_hash_bound_hair_provider",
            "verify_live_kira_state_unchanged",
        ]
        positions = [order.index(name) for name in required]
        self.assertEqual(positions, sorted(positions), order)
        self.assertLess(order.index("evaluate_profiled_candidate_preflight"), order.index("_clear_scene_after_preflight"))
        self.assertLess(
            order.index("_assert_background_factory_startup_safe_scene"),
            order.index("_clear_scene_after_preflight"),
        )
        self.assertLess(order.index("verify_live_kira_state_unchanged"), order.index("mkdir"))

    def test_component_contract_contains_material_eye_nail_knee_and_hair_gates(self) -> None:
        source = self.component_source
        for token in (
            "IEC_61966_2_1_srgb_piecewise_to_scene_linear",
            "#C7A08E",
            "ShaderNodeTexNoise",
            'coordinates.outputs["Generated"]',
            "Kira_Natural_Iris_Variation",
            '"natural_iris_procedural_variation": True',
            "HELPER_EYE_FIT_SCALE = 0.855",
            "HELPER_EYE_POSTERIOR_INSET_M = 0.0022",
            "limbal_ring_present",
            "transparent_cornea_cap_present",
            "visual_black_band_absence_proven",
            "visual_black_band_review_required",
            "fingernail_count",
            "toenail_count",
            "surface_fit_measured",
            "floating_or_intersection_absence_proven",
            'f"upperleg02.{side}"',
            'f"lowerleg01.{side}"',
            'f"lowerleg02.{side}"',
            "posterior > 0.015",
            "skeleton_kinematic_objective_pass",
            "knee_mesh_deformation_quality_proven",
            "build_dynamic_hair",
            "HAIRLESS_ENGINEERING_CANDIDATE_PROVIDER_NOT_SUPPLIED",
            "measured_strand_count",
            "requested_controls_per_strand",
            "minimum_actual_controls_per_strand",
            "maximum_actual_controls_per_strand",
            "adaptive_tube_clearance_proof",
            "all_bilinear_grid_tube_clearance_passed",
            "adaptive_shared_topology_verified",
            "returned_objects_and_data_new_in_scene",
            "candidate builder accepts no provider-asserted World runtime proof",
        ):
            self.assertIn(token, source)
        self.assertNotIn('"black_band_present": False', source)
        self.assertNotIn("slight_surface_overlap_no_floating_free_edge", source)
        self.assertEqual(LANDMARK_GROUP_PREFIX, "AFES_LANDMARK__")

    def test_r15_non_anatomy_repairs_are_measured_and_fail_closed(self) -> None:
        component = self.component_source
        builder = self.builder_source
        for token in (
            "SKIN_SUBSURFACE_SCALE_M = 0.00125",
            '"Subsurface Scale"',
            "Kira_Subtle_Skin_Micro_Bump",
            "single_continuous_nonoverlapping_optical_disc",
            "pupil_iris_coplanar_overlap_face_count",
            "Kira_Iris_Radial_Angle",
            "minimum_unsigned_body_surface_clearance_m",
            "body_surface_triangle_overlap_count",
            "body_raycast_conformal_oriented_nail_plates_v3",
            "toe_plate_orientation_derived_from_surface_projection",
            "surface_fit_measured\": True",
            "floating_or_intersection_absence_proven\": True",
            "modifier.use_deform_preserve_volume = True",
            "KNEE_DEFORMATION_GATE_ANGLES_DEGREES = (30, 55, 80)",
            "_evaluated_body_points",
            "evaluated_mesh_deformation_passed",
            '"knee_mesh_deformation_quality_proven": all(',
            "apply_relaxed_hand_pose",
        ):
            self.assertIn(token, component)
        for token in (
            "bounded_neutral_warm_skin_review_rig_v2",
            'scene.view_settings.view_transform = "AgX"',
            'scene.view_settings.exposure = -0.65',
            '"legacy_overbright_1050_650_900_w_rig_used": False',
            'body=body',
            "solve_bilateral_knee_axes_and_actions(armature, body)",
            'knee_report.get("knee_mesh_deformation_quality_proven") is not True',
            'label == "eyes_close"',
            "apply_relaxed_hand_pose",
        ):
            self.assertIn(token, builder)
        self.assertNotIn('f"{candidate_id}_pupil_{side}"', component)
        self.assertNotIn('f"{candidate_id}_limbal_ring_{side}"', component)
        self.assertNotIn('"surface_fit_measured": False', component)

    def test_r15_eye_optical_fit_is_bounded_and_uses_an_anterior_dome(self) -> None:
        component = self.component_source
        for token in (
            "EYE_OPTICAL_FIT_SCALE_PER_ITERATION = 0.98",
            "EYE_OPTICAL_FIT_MAX_ITERATIONS = 8",
            "EYE_OPTICAL_MINIMUM_CUMULATIVE_SCALE = 0.85",
            "EYE_CORNEA_RIM_FORWARD_OFFSET_M = 0.00034",
            "EYE_CORNEA_DOME_DEPTH_M = 0.00040",
            "def _shallow_cornea_dome(",
            "transparent_open_anterior_cornea_dome",
            "full_socket_crossing_cornea_sphere_used",
            "def _adapt_eye_component_to_socket(",
            "initial_body_surface_triangle_overlap_count",
            "final_body_surface_triangle_overlap_count",
            "minimum_allowed_cumulative_xz_fit_scale",
            "bounded_socket_fit_passed",
            "iris_fit = _adapt_eye_component_to_socket(body_tree, iris)",
            "cornea_fit = _adapt_eye_component_to_socket(body_tree, cornea)",
        ):
            self.assertIn(token, component)
        eye_function = next(
            node
            for node in self.component_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "add_natural_helper_eyes"
        )
        eye_source = ast.get_source_segment(component, eye_function)
        self.assertIsNotNone(eye_source)
        self.assertNotIn("cornea = _uv_sphere(", eye_source)

    def test_r15_nail_fit_is_generic_bilateral_bounded_and_fail_closed(self) -> None:
        component = self.component_source
        for token in (
            "NAIL_PROJECTION_GRID_SIZE = 9",
            "NAIL_PROJECTION_CENTER_FRACTION_CANDIDATES = (0.52, 0.58, 0.64, 0.70, 0.76, 0.82)",
            "NAIL_FOOTPRINT_SCALE_CANDIDATES = (1.0, 0.95, 0.90, 0.85)",
            "NAIL_MINIMUM_FOOTPRINT_SCALE = 0.85",
            "NAIL_MINIMUM_OUTWARD_NORMAL_ALIGNMENT = 0.12",
            "NAIL_ADAPTIVE_NORMAL_LIFT_STEP_M = 0.000025",
            "NAIL_ADAPTIVE_NORMAL_LIFT_MAX_ITERATIONS = 10",
            "initial_body_surface_triangle_overlap_count",
            "final_body_surface_triangle_overlap_count",
            "projection_center_fraction_from_terminal",
            "retained_footprint_scale",
            "additional_normal_lift_m",
            "bounded_adaptive_conformal_fit_passed",
            "all_bounded_adaptive_conformal_fits_passed",
            "bounded conformal nail fit failed",
        ):
            self.assertIn(token, component)
        nail_function = next(
            node
            for node in self.component_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_projected_nail_plate"
        )
        nail_source = ast.get_source_segment(component, nail_function)
        self.assertIsNotNone(nail_source)
        self.assertNotIn("grid = 5", nail_source)
        self.assertNotIn("finger1-3.L", nail_source)
        self.assertNotIn("finger1-3.R", nail_source)

    def test_r15_structured_adult_detail_is_versioned_and_requalified(self) -> None:
        config = json.loads(
            (
                PROJECT_ROOT
                / "Avatar/avatar_builder/tooling/profiled_adult_candidate_builder_v1.json"
            ).read_text(encoding="utf-8")
        )
        detail = config["adult_surface_authoring"]["structured_detail_refinement"]
        self.assertEqual(
            "generic_continuous_adult_female_external_surface_v2",
            detail["method_id"],
        )
        self.assertEqual(0.0032, detail["baseline_relief_scale_m"])
        self.assertEqual(2, detail["boundary_taper_power"])
        posterior_frame = detail["posterior_frame"]
        self.assertEqual([0.0, 0.005, 0.775], posterior_frame["origin"])
        self.assertEqual([0.0, -0.8, 0.6], posterior_frame["longitudinal_axis"])
        self.assertEqual([0.0, -0.6, -0.8], posterior_frame["outward_axis"])
        self.assertTrue(detail["continuous_primary_surface_only"])
        self.assertTrue(detail["no_internal_tract_claim"])
        self.assertTrue(
            detail[
                "independent_topology_relationship_visual_requalification_required"
            ]
        )
        for token in (
            "refine_existing_continuous_adult_female_surface_v2",
            "new_global_nonadjacent_self_intersection_pairs",
            "structured_detail_refinement",
            "adult_relationship_surface_detail_method",
        ):
            self.assertIn(token, self.builder_source)

    def test_hash_scene_and_private_glb_truth_gates_are_explicit(self) -> None:
        for token in (
            "_capture_build_hash_snapshot",
            "_verify_build_hash_snapshot",
            "point-of-use exact binding failed",
            "bpy.app.background",
            "bpy.data.filepath",
            "use --factory-startup",
            "untouched factory-startup scene fingerprint",
            "UNVALIDATED_PENDING_FRESH_IMPORT",
            '"fresh_import_validation_performed": False',
            '"hair_curve_and_morph_runtime_survival_proven": False',
            "export_extras=True",
            '"pose_space_pelvic_patch_deformation_audit_status": "NOT_PERFORMED"',
        ):
            self.assertIn(token, self.builder_source)

    def test_cli_requires_private_ack_and_keeps_optional_outputs_explicit(self) -> None:
        for token in (
            "--output-dir",
            "--acknowledge-inactive-private-candidate",
            "--render-owner-review",
            "--export-private-glb",
            "--hair-provider-path",
            "--hair-provider-sha256",
            "--hairless-engineering-candidate",
        ):
            self.assertIn(token, self.builder_source)
        for invariant in (
            '"inactive": True',
            '"assigned": False',
            '"clothing_included": False',
            '"publication_allowed": False',
            '"runtime_activation_allowed": False',
            '"live_kira_state_mutated": False',
        ):
            self.assertIn(invariant, self.builder_source)

    def test_exact_owner_views_include_three_protected_relationship_views(self) -> None:
        self.assertEqual(len(OWNER_REVIEW_VIEW_LABELS), 17)
        protected = [
            label for label in OWNER_REVIEW_VIEW_LABELS
            if label.startswith("protected_adult_relationship_")
        ]
        self.assertEqual(
            protected,
            [
                "protected_adult_relationship_front",
                "protected_adult_relationship_side",
                "protected_adult_relationship_three_quarter",
            ],
        )
        for token in (
            "hair_dry_front",
            "hair_dry_rear",
            "hair_wind_left_front",
            "hair_wind_right_front",
            "hair_wet_front",
            "hair_wet_rear",
            "hair_wet_wind_left_front",
            "hair_wet_wind_right_front",
            '"world_runtime_hair_response_proven": False',
            'for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")',
        ):
            self.assertIn(token, self.builder_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
