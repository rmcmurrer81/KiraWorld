"""Pure/static tests for structured continuous adult-female surface v2."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

from Core.avatar_adult_female_surface_authoring import (
    frame_from_mapping,
    parameters_from_mapping,
)
from Core.avatar_adult_female_surface_authoring_v2 import (
    FEATURE_COMPONENTS,
    METHOD_ID,
    REQUIRED_RELATIONSHIPS,
    boundary_taper,
    build_authoring_contract,
    feature_sample_displacements,
    landmark_memberships,
    load_required_relationships,
    posterior_support_taper,
    posterior_surface_displacement,
    surface_displacement,
)


def frame_payload() -> dict[str, object]:
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


class AdultFemaleSurfaceV2Tests(unittest.TestCase):
    def test_policy_coverage_and_method_are_versioned(self) -> None:
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
        self.assertTrue(METHOD_ID.endswith("_v2"))

    def test_structured_samples_are_visibly_stronger_and_signed(self) -> None:
        values = feature_sample_displacements(0.0062, 2)
        for name in (
            "labia_majora_left",
            "labia_majora_right",
            "labia_minora_left",
            "labia_minora_right",
            "clitoral_hood",
            "clitoris",
            "fourchette",
        ):
            self.assertGreater(values[name], 0.0010, name)
        for name in ("urethral_opening", "vaginal_opening", "anal_recess"):
            self.assertLess(values[name], -0.0010, name)
        self.assertAlmostEqual(
            values["labia_majora_left"],
            values["labia_majora_right"],
            places=10,
        )

    def test_posterior_taper_does_not_suppress_anal_recess(self) -> None:
        self.assertGreater(boundary_taper(0.0, -0.70, 2), 0.90)
        self.assertEqual(0.0, boundary_taper(0.0, -1.0, 2))
        self.assertLess(
            posterior_surface_displacement(
                0.0,
                -0.36,
                relief_scale_m=0.0062,
                taper_power=2,
            ),
            -0.0010,
        )

    def test_posterior_support_taper_preserves_center_and_stops_outer_nudges(self) -> None:
        self.assertEqual(1.0, posterior_support_taper(0.0))
        self.assertEqual(1.0, posterior_support_taper(0.30))
        self.assertGreater(posterior_support_taper(0.34), 0.0)
        self.assertLess(posterior_support_taper(0.34), 1.0)
        self.assertEqual(0.0, posterior_support_taper(0.38))
        self.assertEqual(0.0, posterior_support_taper(-0.45))

    def test_pair_memberships_remain_deterministic(self) -> None:
        left = landmark_memberships(0.32, 0.01, threshold=0.20)
        right = landmark_memberships(-0.32, 0.01, threshold=0.20)
        self.assertIn("paired_labia_majora__left", left)
        self.assertNotIn("paired_labia_majora__right", left)
        self.assertIn("paired_labia_majora__right", right)
        self.assertNotIn("paired_labia_majora__left", right)

    def test_contract_stays_continuous_inactive_and_unqualified(self) -> None:
        frame = frame_from_mapping(frame_payload())
        parameters = parameters_from_mapping(
            {
                "subdivision_cuts": 3,
                "relief_scale_m": 0.0062,
                "boundary_taper_power": 2,
            }
        )
        contract = build_authoring_contract(PROJECT_ROOT, frame, parameters)
        self.assertEqual(METHOD_ID, contract["method_id"])
        self.assertEqual(
            "complete_required_external_relationships_no_internal_tract_claim",
            contract["scope"],
        )
        self.assertFalse(contract["separate_anatomy_mesh_allowed"])
        self.assertFalse(contract["boolean_anatomy_union_allowed"])
        self.assertFalse(contract["qualified_for_adult_foundation"])
        self.assertFalse(contract["runtime_activation_allowed"])
        self.assertTrue(contract["independent_visual_prominence_review_required"])

    def test_v1_sources_are_not_rewritten_by_v2(self) -> None:
        v1 = PROJECT_ROOT / "Core/avatar_adult_female_surface_authoring.py"
        adapter_v1 = PROJECT_ROOT / "tools/blender_author_adult_female_external_surface.py"
        adapter_v2 = PROJECT_ROOT / "tools/blender_author_adult_female_external_surface_v2.py"
        smoke_v2 = PROJECT_ROOT / "tools/blender_test_adult_female_surface_authoring_v2.py"
        real_probe_v2 = PROJECT_ROOT / "tools/blender_probe_profiled_adult_surface_v2.py"
        self.assertTrue(v1.is_file())
        self.assertTrue(adapter_v1.is_file())
        source = v1.read_text(encoding="utf-8")
        self.assertIn("generic_continuous_adult_female_external_surface_v1", source)
        self.assertNotIn("generic_continuous_adult_female_external_surface_v2", source)
        adapter_source = adapter_v2.read_text(encoding="utf-8")
        compile(adapter_source, str(adapter_v2), "exec")
        lowered = adapter_source.lower()
        self.assertNotIn("bpy.ops.render", lowered)
        self.assertNotIn("export_scene", lowered)
        self.assertNotIn("private_owner_review", lowered)
        self.assertNotIn("if __name__ ==", lowered)
        smoke_source = smoke_v2.read_text(encoding="utf-8")
        compile(smoke_source, str(smoke_v2), "exec")
        self.assertNotIn("bpy.ops.render", smoke_source.lower())
        self.assertNotIn("save_as_mainfile", smoke_source.lower())
        self.assertNotIn("export_scene", smoke_source.lower())
        probe_source = real_probe_v2.read_text(encoding="utf-8")
        compile(probe_source, str(real_probe_v2), "exec")
        self.assertNotIn("bpy.ops.render", probe_source.lower())
        self.assertNotIn("save_as_mainfile", probe_source.lower())
        self.assertNotIn("export_scene", probe_source.lower())
        self.assertIn("surface_probe_never_written", probe_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
