from __future__ import annotations

import ast
import hashlib
import math
import re
import unittest
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADAPTER = PROJECT_ROOT / "Tools/blender_avatar_natural_nail_delivery_v3.py"
CORE = PROJECT_ROOT / "Core/avatar_natural_nail_delivery_v3.py"
EXPECTED_UNCHANGED_CORE_SHA256 = (
    "8ce6cad33e519382043509f81fc1d465d354dac12ff427f33234cd12d52ce9ab"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _PureVector:
    def __init__(self, values: Sequence[float] = (0.0, 0.0, 0.0)) -> None:
        self.values = tuple(float(value) for value in values)

    def __add__(self, other: "_PureVector") -> "_PureVector":
        return _PureVector(
            first + second for first, second in zip(self.values, other.values)
        )

    def __radd__(self, other: object) -> "_PureVector":
        return self if other == 0 else self.__add__(other)  # type: ignore[arg-type]

    def __sub__(self, other: "_PureVector") -> "_PureVector":
        return _PureVector(
            first - second for first, second in zip(self.values, other.values)
        )

    def __truediv__(self, value: float) -> "_PureVector":
        return _PureVector(component / float(value) for component in self.values)

    def dot(self, other: "_PureVector") -> float:
        return sum(
            first * second for first, second in zip(self.values, other.values)
        )

    @property
    def length(self) -> float:
        return math.sqrt(sum(component * component for component in self.values))


class NaturalNailBlenderAdapterStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = ADAPTER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        locality_node = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_grid_locality_record"
        )
        namespace: dict[str, Any] = {
            "Any": Any,
            "Sequence": Sequence,
            "Vector": _PureVector,
        }
        exec(
            compile(
                ast.fix_missing_locations(
                    ast.Module(body=[locality_node], type_ignores=[])
                ),
                str(ADAPTER),
                "exec",
            ),
            namespace,
        )
        cls.locality = staticmethod(namespace["_grid_locality_record"])

    def test_component_contract_remains_unchanged(self) -> None:
        self.assertEqual(sha256_file(CORE), EXPECTED_UNCHANGED_CORE_SHA256)

    def test_fallback_is_bounded_and_uses_exact_loop_triangles(self) -> None:
        self.assertIn("LOCAL_SURFACE_FALLBACK_GRID_SIZE = 17", self.source)
        self.assertIn("LOCAL_SURFACE_MAXIMUM_QUERY_DISTANCE_M = 0.004", self.source)
        self.assertIn("nail.data.calc_loop_triangles()", self.source)
        self.assertIn("exact_auditor.classify_triangle_pair", self.source)
        self.assertIn('"raw_bvhtree_pairs_are_not_the_pass_gate": True', self.source)

    def test_fallback_is_after_unchanged_primary_failure_boundary(self) -> None:
        function = next(
            node
            for node in self.tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_projected_oval_nail_plate"
        )
        segment = ast.get_source_segment(self.source, function)
        self.assertIsNotNone(segment)
        assert segment is not None
        boundary = "if accepted is None:\n        (\n            accepted,"
        self.assertIn(boundary, segment)
        self.assertEqual(
            segment.count("_nearest_coherent_local_surface_fallback("),
            1,
        )
        self.assertLess(
            segment.index("for footprint_scale in FOOTPRINT_SCALE_CANDIDATES"),
            segment.index("_nearest_coherent_local_surface_fallback("),
        )

    def test_locality_winding_clearance_and_exact_gates_are_fail_closed(self) -> None:
        fallback_start = self.source.index(
            "def _nearest_coherent_local_surface_fallback("
        )
        attachment_start = self.source.index("def _attachment_report(")
        fallback = self.source[fallback_start:attachment_start]
        required = (
            "body_tree.find_nearest(",
            "LOCAL_SURFACE_MAXIMUM_QUERY_DISTANCE_M",
            'locality["locality_gate_passed"] is not True',
            'winding["all_top_surface_faces_outward"] is not True',
            "validate_clearance_measurement(",
            'exact["exact_genuine_penetration_pair_count"]',
            "MINIMUM_RETAINED_FOOTPRINT_SCALE",
            "MAXIMUM_NORMAL_LIFT_ITERATIONS + 1",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, fallback)
        self.assertLess(
            fallback.index('locality["locality_gate_passed"] is not True'),
            fallback.index("mesh = bpy.data.meshes.new(name)"),
        )
        self.assertLess(
            fallback.index('winding["all_top_surface_faces_outward"] is not True'),
            fallback.index("accepted_lift = -1"),
        )

    def test_locality_gate_accepts_coherent_grid_and_rejects_surface_hop(self) -> None:
        grid = 17
        coherent = [
            _PureVector((row * 0.006 / 16, column * 0.004 / 16, 0.0))
            for row in range(grid)
            for column in range(grid)
        ]
        kwargs = {
            "nominal_center": _PureVector((0.003, 0.002, 0.0)),
            "longitudinal": _PureVector((1.0, 0.0, 0.0)),
            "lateral": _PureVector((0.0, 1.0, 0.0)),
            "length_m": 0.006,
            "width_m": 0.004,
            "footprint_scale": 1.0,
            "grid": grid,
        }
        accepted = self.locality(points=coherent, **kwargs)
        self.assertIs(accepted["locality_gate_passed"], True)
        hopped = list(coherent)
        hopped[(grid // 2) * grid + grid // 2] = _PureVector(
            (0.003, 0.002, 0.010)
        )
        rejected = self.locality(points=hopped, **kwargs)
        self.assertIs(rejected["locality_gate_passed"], False)
        self.assertEqual(
            rejected["failure_reason"],
            "discontinuous_or_wrong_surface_grid_neighbor",
        )

    def test_body_and_rig_preservation_checks_remain(self) -> None:
        for token in (
            "body_signature_before = _mesh_signature(body)",
            "rig_signature_before = _rig_signature(armature)",
            "if body_signature_after != body_signature_before:",
            "if rig_signature_after != rig_signature_before:",
            "if len(body.modifiers) != body_modifier_count_before:",
        ):
            self.assertIn(token, self.source)

    def test_adapter_has_no_authoring_or_publication_operation(self) -> None:
        forbidden = (
            r"bpy\.ops\.wm\.save",
            r"bpy\.ops\.wm\.open",
            r"bpy\.ops\.render",
            r"save_as_mainfile",
            r"write_still",
            r"bpy\.ops\.export",
            r"subprocess",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.source))


if __name__ == "__main__":
    unittest.main()
