"""Static and pure-Python tests for the inactive adult-female surface method."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

from Core.avatar_adult_female_surface_authoring import (
    FEATURE_COMPONENTS,
    METHOD_ID,
    REQUIRED_RELATIONSHIPS,
    build_authoring_contract,
    frame_from_mapping,
    landmark_group_name,
    landmark_memberships,
    load_required_relationships,
    parameters_from_mapping,
    surface_displacement,
)


def valid_frame() -> dict[str, object]:
    return {
        "coordinate_space": "object_local",
        "origin": [0.0, -0.12, 0.78],
        "lateral_axis": [1.0, 0.0, 0.0],
        "longitudinal_axis": [0.0, 0.0, 1.0],
        "outward_axis": [0.0, -1.0, 0.0],
        "half_width_m": 0.06,
        "half_length_m": 0.14,
        "max_surface_offset_m": 0.04,
    }


class AdultFemaleSurfaceContractTests(unittest.TestCase):
    def test_relationships_exactly_match_qualification_policy(self) -> None:
        policy = json.loads(
            (
                PROJECT_ROOT
                / "Avatar/avatar_builder/policies/adult_foundation_qualification_v1.json"
            ).read_text(encoding="utf-8")
        )
        expected = tuple(policy["required_adult_female_relationships"])
        self.assertEqual(expected, REQUIRED_RELATIONSHIPS)
        self.assertEqual(expected, tuple(FEATURE_COMPONENTS))
        self.assertEqual(expected, load_required_relationships(PROJECT_ROOT))

    def test_contract_is_continuous_inactive_and_unqualified(self) -> None:
        frame = frame_from_mapping(valid_frame())
        parameters = parameters_from_mapping({})
        contract = build_authoring_contract(PROJECT_ROOT, frame, parameters)
        self.assertEqual(METHOD_ID, contract["method_id"])
        self.assertEqual(
            list(REQUIRED_RELATIONSHIPS),
            contract["relationships"],
        )
        self.assertTrue(contract["source_primary_surface_required"])
        self.assertEqual(1, contract["source_component_count_required"])
        self.assertEqual(1, contract["result_component_count_required"])
        self.assertEqual(0, contract["result_boundary_edges_required"])
        self.assertEqual(0, contract["result_nonmanifold_edges_required"])
        self.assertEqual(
            0,
            contract[
                "authored_region_nonadjacent_self_intersection_pairs_required"
            ],
        )
        self.assertFalse(
            contract["new_global_nonadjacent_self_intersection_pairs_allowed"]
        )
        self.assertEqual(
            0,
            contract[
                "qualification_global_nonadjacent_self_intersection_pairs_required"
            ],
        )
        self.assertFalse(contract["source_anatomy_geometry_copy_allowed"])
        self.assertFalse(contract["wrong_sex_helper_allowed"])
        self.assertFalse(contract["separate_anatomy_mesh_allowed"])
        self.assertFalse(contract["boolean_anatomy_union_allowed"])
        self.assertFalse(contract["painted_only_relationship_allowed"])
        self.assertFalse(contract["qualified_for_adult_foundation"])
        self.assertFalse(contract["runtime_activation_allowed"])
        self.assertFalse(contract["render_performed"])
        self.assertFalse(contract["export_performed"])

    def test_frame_rejects_nonorthogonal_or_unbounded_input(self) -> None:
        frame = valid_frame()
        frame["outward_axis"] = [0.1, -1.0, 0.0]
        with self.assertRaisesRegex(ValueError, "not orthogonal"):
            frame_from_mapping(frame)
        frame = valid_frame()
        frame["half_width_m"] = 0.5
        with self.assertRaisesRegex(ValueError, "half_width_m"):
            frame_from_mapping(frame)

    def test_unknown_parameters_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown authoring parameter"):
            parameters_from_mapping({"invented_override": True})
        with self.assertRaisesRegex(ValueError, "subdivision_cuts"):
            parameters_from_mapping({"subdivision_cuts": 0})
        with self.assertRaisesRegex(ValueError, "relief_scale_m"):
            parameters_from_mapping({"relief_scale_m": 0.02})

    def test_recess_and_relationship_order_are_deterministic(self) -> None:
        urethral = FEATURE_COMPONENTS[
            "urethral_opening_anterior_to_vaginal_opening"
        ][0]
        vaginal = FEATURE_COMPONENTS["vaginal_opening"][0]
        anal = FEATURE_COMPONENTS[
            "perineal_transition_to_anus_and_pelvic_floor"
        ][1]
        self.assertGreater(urethral["v"], vaginal["v"])
        self.assertGreater(vaginal["v"], anal["v"])
        for component in (urethral, vaginal, anal):
            displacement = surface_displacement(
                float(component["u"]),
                float(component["v"]),
                relief_scale_m=0.0032,
                taper_power=3,
            )
            self.assertLess(displacement, 0.0)

    def test_paired_landmarks_have_deterministic_sides(self) -> None:
        left = landmark_memberships(0.34, 0.02, threshold=0.32)
        right = landmark_memberships(-0.34, 0.02, threshold=0.32)
        self.assertIn("paired_labia_majora", left)
        self.assertIn("paired_labia_majora__left", left)
        self.assertNotIn("paired_labia_majora__right", left)
        self.assertIn("paired_labia_majora", right)
        self.assertIn("paired_labia_majora__right", right)
        self.assertNotIn("paired_labia_majora__left", right)

    def test_landmark_group_names_are_stable_and_blender_safe(self) -> None:
        memberships = list(REQUIRED_RELATIONSHIPS) + [
            "paired_labia_majora__left",
            "paired_labia_majora__right",
            "paired_labia_minora__left",
            "paired_labia_minora__right",
            "perineal_transition_to_anus_and_pelvic_floor__perineal_transition",
            "perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess",
        ]
        names = [landmark_group_name(value) for value in memberships]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(len(name.encode("utf-8")) <= 63 for name in names))

    def test_blender_sources_compile_but_have_no_render_or_export_path(self) -> None:
        adapter_path = (
            PROJECT_ROOT / "tools/blender_author_adult_female_external_surface.py"
        )
        wrapper_path = (
            PROJECT_ROOT
            / "tools/blender_build_makehuman_adult_female_foundation_inactive.py"
        )
        exact_path = PROJECT_ROOT / "tools/blender_exact_mesh_intersections.py"
        cleanup_path = (
            PROJECT_ROOT / "tools/blender_repair_bounded_self_intersections.py"
        )
        diagnostic_path = (
            PROJECT_ROOT
            / "tools/blender_diagnose_makehuman_adult_female_intersections.py"
        )
        artifact_auditor_path = (
            PROJECT_ROOT
            / "tools/blender_audit_inactive_adult_female_foundation.py"
        )
        for path in (
            adapter_path,
            wrapper_path,
            exact_path,
            cleanup_path,
            diagnostic_path,
            artifact_auditor_path,
        ):
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            lowered = source.lower()
            self.assertNotIn("bpy.ops.render", lowered)
            self.assertNotIn("export_scene", lowered)
            self.assertNotIn("adult_anatomy_reference", lowered)
            self.assertNotIn("private_owner_review", lowered)
        adapter_source = adapter_path.read_text(encoding="utf-8")
        self.assertNotIn("if __name__ ==", adapter_source)
        self.assertIn(
            "author_continuous_adult_female_surface",
            adapter_source,
        )
        wrapper_source = wrapper_path.read_text(encoding="utf-8")
        self.assertIn("--acknowledge-inactive-authoring", wrapper_source)
        self.assertIn('group == "body"', wrapper_source)
        self.assertNotIn('group in {"body", "helper-genital"}', wrapper_source)
        auditor_source = artifact_auditor_path.read_text(encoding="utf-8")
        self.assertNotIn("save_as_mainfile", auditor_source)
        self.assertIn("fresh_blender_process_read_only", auditor_source)
        self.assertIn("exact_artifact_sha256_verified", auditor_source)
        self.assertIn("mandatory_downstream_kira_candidate_gate", auditor_source)

    def test_makehuman_inactive_profile_is_generic_and_bounded(self) -> None:
        path = (
            PROJECT_ROOT
            / "Avatar/avatar_builder/tooling/"
            "makehuman_adult_female_foundation_inactive_authoring_v1.json"
        )
        profile = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(1, profile["schema_version"])
        self.assertEqual(
            "makehuman_hm08_female_macro_source",
            profile["foundation_id"],
        )
        self.assertIn("generic", profile["candidate_id"])
        frame_from_mapping(profile["frame"])
        parameters_from_mapping(profile["parameters"])
        serialized = json.dumps(profile).lower()
        self.assertNotIn("private_owner_review", serialized)
        self.assertNotIn("adult_anatomy_reference", serialized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
