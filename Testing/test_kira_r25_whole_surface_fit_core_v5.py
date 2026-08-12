from __future__ import annotations

import base64
import copy
import hashlib
import importlib
import inspect
import pickle
import struct
import sys
import tracemalloc
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r25_whole_surface_fit_core_v5 as fit


def edge_count(faces):
    edges = set()
    for face in faces:
        for position, first in enumerate(face):
            second = face[(position + 1) % len(face)]
            edges.add(tuple(sorted((first, second))))
    return len(edges)


def grid_fixture(columns=3, rows=3):
    vertices = [
        (float(column), float(row), 0.0)
        for row in range(rows)
        for column in range(columns)
    ]
    faces = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            a = row * columns + column
            b = a + 1
            c = a + columns
            d = c + 1
            faces.extend(((a, b, d), (a, d, c)))
    return vertices, faces


def limit_arguments(**changes):
    values = {
        "screen_weight": fit.DEFAULT_SCREEN_WEIGHT,
        "jacobi_relaxation": fit.DEFAULT_JACOBI_RELAXATION,
        "convergence_tolerance": fit.DEFAULT_CONVERGENCE_TOLERANCE,
        "max_iterations": fit.DEFAULT_MAX_ITERATIONS,
        "maximum_displacement": fit.DEFAULT_MAXIMUM_DISPLACEMENT,
        "minimum_triangle_area": fit.DEFAULT_MINIMUM_TRIANGLE_AREA,
        "minimum_area_ratio": fit.DEFAULT_MINIMUM_AREA_RATIO,
        "maximum_area_ratio": fit.DEFAULT_MAXIMUM_AREA_RATIO,
        "minimum_orientation_cosine": fit.DEFAULT_MINIMUM_ORIENTATION_COSINE,
        "maximum_line_search_backtracks": (
            fit.DEFAULT_MAXIMUM_LINE_SEARCH_BACKTRACKS
        ),
    }
    values.update(changes)
    return values


def limit_tuple(**changes):
    return fit._normalize_limits(**limit_arguments(**changes))


def fixture_arguments(
    vertices,
    faces,
    regions,
    protected,
    anchors,
    *,
    limits=None,
    **changes,
):
    selected_limits = limit_arguments(**(limits or {}))
    arguments = {
        "qualification_id": "kira_r25_qualified_continuous_foundation",
        "baseline_space": "globally_aligned_foundation",
        "anchor_space": "globally_aligned_foundation_displacement",
        "baseline_vertices": vertices,
        "faces": faces,
        "vertex_regions": regions,
        "protected_vertices": protected,
        "anchor_displacements": anchors,
        "expected_vertex_count": len(vertices),
        "expected_edge_count": edge_count(faces),
        "expected_face_count": len(faces),
        "expected_connected_components": 1,
        "expected_topology_sha256": fit.topology_sha256(len(vertices), faces),
        "expected_baseline_sha256": fit.baseline_sha256(vertices),
        "expected_regions_sha256": fit.regions_sha256(regions),
        "expected_protected_sha256": fit.index_set_sha256(
            protected, len(vertices)
        ),
        "expected_anchor_sha256": fit.anchor_displacements_sha256(
            anchors, len(vertices)
        ),
        "expected_limits_sha256": fit.fit_limits_sha256(**selected_limits),
        **selected_limits,
    }
    arguments.update(changes)
    return arguments


def compute_fixture(
    vertices,
    faces,
    regions,
    protected,
    anchors,
    *,
    limits=None,
    **changes,
):
    return fit.compute_r25_whole_surface_math(
        **fixture_arguments(
            vertices,
            faces,
            regions,
            protected,
            anchors,
            limits=limits,
            **changes,
        )
    )


def decode_rows(encoded, header):
    raw = base64.b64decode(encoded, validate=True)
    if not raw.startswith(header):
        raise AssertionError("unexpected row codec header")
    offset = len(header)
    count = struct.unpack_from("<I", raw, offset)[0]
    offset += 4
    expected_length = offset + count * 24
    if len(raw) != expected_length:
        raise AssertionError("unexpected encoded row length")
    return tuple(
        struct.unpack_from("<ddd", raw, offset + index * 24)
        for index in range(count)
    )


def payload_strings(value):
    if type(value) is str:
        yield value
    elif type(value) is list:
        for item in value:
            yield from payload_strings(item)
    elif type(value) is dict:
        for key, item in value.items():
            yield key
            yield from payload_strings(item)


class WholeSurfaceMathCoreTests(unittest.TestCase):
    def test_stateless_payload_is_explicitly_non_authoritative(self):
        vertices, faces = grid_fixture()
        payload = compute_fixture(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            {0: (0.02, 0.01, 0.005)},
        )
        self.assertEqual(payload["status"], fit.STATIC_MATH_STATUS)
        self.assertEqual(payload["check_scope"], fit.NONAUTHORITATIVE_CHECK)
        self.assertEqual(payload["schema"], "kira.r25.whole_surface_math.v5")
        lowered = tuple(value.lower() for value in payload_strings(payload))
        self.assertNotIn("yes", lowered)
        self.assertFalse(any("accepted" in value for value in lowered))
        self.assertFalse(any("body authority" in value for value in lowered))

    def test_protected_zero_anchor_exact_and_topology_preserved(self):
        vertices, faces = grid_fixture()
        anchors = {0: (0.02, 0.01, 0.005)}
        payload = compute_fixture(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            anchors,
        )
        field = decode_rows(
            payload["displacement_field"]["base64"],
            fit.VECTOR_FIELD_HEADER,
        )
        candidate = decode_rows(
            payload["candidate_vertices"]["base64"],
            fit.CANDIDATE_HEADER,
        )
        evidence = payload["evidence"]
        self.assertEqual(field[8], (0.0, 0.0, 0.0))
        self.assertEqual(candidate[8], tuple(vertices[8]))
        self.assertEqual(field[0], anchors[0])
        self.assertEqual(evidence["protected_vertex_count"], 1)
        self.assertEqual(evidence["anchor_count"], 1)
        self.assertEqual(
            evidence["topology_sha256"], evidence["topology_after_sha256"]
        )
        self.assertEqual(evidence["iteration_state"], "CONVERGED")
        self.assertLessEqual(
            evidence["raw_equation_residual_inf_fixed_1e12"], 101
        )

    def test_same_region_propagation_has_no_cross_region_component(self):
        columns, rows = 4, 2
        vertices, faces = grid_fixture(columns, rows)
        regions = []
        for _row in range(rows):
            regions.extend(("torso", "torso", "head", "head"))
        payload = compute_fixture(
            vertices,
            faces,
            regions,
            [columns],
            {0: (0.03, 0.0, 0.0), 3: (0.0, 0.04, 0.0)},
        )
        field = decode_rows(
            payload["displacement_field"]["base64"],
            fit.VECTOR_FIELD_HEADER,
        )
        for index, region in enumerate(regions):
            if region == "torso":
                self.assertEqual(field[index][1:], (0.0, 0.0))
            else:
                self.assertEqual(field[index][0], 0.0)
                self.assertEqual(field[index][2], 0.0)

    def test_unknown_and_disconnected_semantic_regions_fail_closed(self):
        vertices = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
        ]
        faces = [(0, 1, 2, 3)]
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "unknown_semantic_region"
        ):
            compute_fixture(
                vertices,
                faces,
                ["torso", "torso", "torso", "unknown"],
                [3],
                {0: (0.0, 0.0, 0.0)},
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "same_region_graph_disconnected"
        ):
            compute_fixture(
                vertices,
                faces,
                ["torso", "head", "torso", "head"],
                [3],
                {0: (0.0, 0.0, 0.0), 1: (0.0, 0.0, 0.0)},
            )

    def test_protected_cut_leaving_unanchored_component_fails(self):
        vertices, faces = grid_fixture(5, 2)
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError,
            "same_region_free_component_without_anchor",
        ):
            compute_fixture(
                vertices,
                faces,
                ["torso"] * len(vertices),
                [2, 7],
                {0: (0.01, 0.0, 0.0)},
            )

    def test_anchor_preserving_line_search_rejects_flip_and_degenerate(self):
        baseline = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ]
        raw = [
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, -2.0, 0.0),
        ]
        field, candidate, denominator, rejections = (
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2)],
                raw_displacements=raw,
                anchor_indices=[0],
                protected_indices=[1],
                limits=limit_tuple(
                    maximum_displacement=3.0,
                    minimum_area_ratio=0.20,
                    maximum_area_ratio=5.0,
                ),
            )
        )
        self.assertEqual(denominator, 4)
        self.assertEqual(field[0], raw[0])
        self.assertEqual(field[1], (0.0, 0.0, 0.0))
        self.assertEqual(field[2], (0.0, -0.5, 0.0))
        self.assertEqual(candidate[2], (0.0, 0.5, 0.0))
        self.assertIn("orientation_flip", rejections[0])
        self.assertIn("degenerate", rejections[1])

    def test_line_search_rejects_area_ratio_and_displacement(self):
        baseline = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ]
        area_raw = [
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 9.0, 0.0),
        ]
        field, _candidate, denominator, rejections = (
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2)],
                raw_displacements=area_raw,
                anchor_indices=[0],
                protected_indices=[1],
                limits=limit_tuple(
                    maximum_displacement=20.0,
                    maximum_area_ratio=3.0,
                ),
            )
        )
        self.assertGreater(denominator, 1)
        self.assertEqual(field[0], area_raw[0])
        self.assertTrue(any("area_ratio" in item for item in rejections))

        displacement_raw = [
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (4.0, 0.0, 0.0),
        ]
        _field, _candidate, denominator, rejections = (
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2)],
                raw_displacements=displacement_raw,
                anchor_indices=[0],
                protected_indices=[1],
                limits=limit_tuple(maximum_displacement=1.0),
            )
        )
        self.assertGreater(denominator, 1)
        self.assertTrue(
            any("maximum_displacement_exceeded" in item for item in rejections)
        )

    def test_private_line_search_rejects_empty_duplicate_boundaries(self):
        baseline = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ]
        raw = [(0.0, 0.0, 0.0)] * 3
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "line_faces_empty"
        ):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[],
                raw_displacements=raw,
                anchor_indices=[0],
                protected_indices=[1],
                limits=limit_tuple(),
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "anchor_set_empty"
        ):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2)],
                raw_displacements=raw,
                anchor_indices=[],
                protected_indices=[1],
                limits=limit_tuple(),
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "duplicate_face"
        ):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2), (2, 1, 0)],
                raw_displacements=raw,
                anchor_indices=[0],
                protected_indices=[1],
                limits=limit_tuple(),
            )

    def test_nonfinite_and_degenerate_baseline_fail_closed(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "nonfinite"
        ):
            altered = list(vertices)
            altered[1] = (float("nan"), 0.0, 0.0)
            compute_fixture(
                altered, faces, regions, [8], {0: (0.0, 0.0, 0.0)}
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "baseline_triangle_degenerate"
        ):
            compute_fixture(
                [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
                [(0, 1, 2)],
                ["torso"] * 3,
                [2],
                {0: (0.0, 0.0, 0.0)},
            )

    def test_absolute_iteration_and_backtrack_ceilings(self):
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "max_iterations_above_absolute_ceiling"
        ):
            fit.fit_limits_sha256(
                max_iterations=fit.MAX_JACOBI_ITERATIONS + 1
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError,
            "maximum_line_search_backtracks_above_absolute_ceiling",
        ):
            fit.fit_limits_sha256(
                maximum_line_search_backtracks=(
                    fit.MAX_LINE_SEARCH_BACKTRACKS + 1
                )
            )

    def test_determinism_and_canonical_hashes(self):
        vertices, faces = grid_fixture()
        arguments = fixture_arguments(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            {0: (0.025, -0.01, 0.003)},
        )
        first = fit.compute_r25_whole_surface_math(**arguments)
        second = fit.compute_r25_whole_surface_math(**arguments)
        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(fit.canonical_json_bytes(first)).hexdigest(),
            hashlib.sha256(fit.canonical_json_bytes(second)).hexdigest(),
        )
        self.assertEqual(
            fit.replay_r25_whole_surface_math(
                claimed_payload=first, **arguments
            ),
            fit.NONAUTHORITATIVE_CHECK,
        )

    def test_backtracked_nonconverged_field_is_rejected_mathematically(self):
        vertices, faces = grid_fixture()
        anchors = {0: (0.02, 0.0, 0.0)}
        forged_field = [(0.0, 0.0, 0.0) for _ in vertices]
        forged_field[0] = anchors[0]
        forged_field[4] = (0.10, 0.0, 0.0)
        forged_candidate = [
            tuple(
                vertices[index][axis] + forged_field[index][axis]
                for axis in range(3)
            )
            for index in range(len(vertices))
        ]
        with mock.patch.object(
            fit,
            "_line_search_anchor_preserving",
            return_value=(
                tuple(forged_field),
                tuple(forged_candidate),
                2,
                ("scale_1_over_1:fixture_rejection",),
            ),
        ), self.assertRaisesRegex(
            fit.WholeSurfaceMathError,
            "post_line_search_screened_harmonic_residual_exceeded",
        ):
            compute_fixture(
                vertices,
                faces,
                ["torso"] * len(vertices),
                [8],
                anchors,
            )

    def test_every_external_binding_is_fail_closed(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.01, 0.0, 0.0)}
        changes = (
            {"expected_topology_sha256": "0" * 64},
            {"expected_baseline_sha256": "0" * 64},
            {"expected_regions_sha256": "0" * 64},
            {"expected_protected_sha256": "0" * 64},
            {"expected_anchor_sha256": "0" * 64},
            {"expected_limits_sha256": "0" * 64},
            {"expected_edge_count": 999},
            {"qualification_id": "caller_self_qualified"},
            {"baseline_space": "local"},
            {"anchor_space": "other"},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(
                fit.WholeSurfaceMathError
            ):
                compute_fixture(
                    vertices,
                    faces,
                    regions,
                    protected,
                    anchors,
                    **change,
                )

    def test_effectful_numeric_and_mapping_subclasses_are_rejected(self):
        callbacks = []

        class EffectfulFloat(float):
            def __float__(self):
                callbacks.append("float")
                return super().__float__()

        class EffectfulDict(dict):
            def items(self):
                callbacks.append("items")
                return super().items()

        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "screen_weight_not_numeric"
        ):
            fit.fit_limits_sha256(screen_weight=EffectfulFloat(0.25))
        self.assertEqual(callbacks, [])

        hostile_limits = list(limit_tuple())
        hostile_limits[0] = EffectfulFloat(0.25)
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "screen_weight_not_numeric"
        ):
            fit._line_search_anchor_preserving(
                baseline_vertices=[
                    (0.0, 0.0, 0.0),
                    (1.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0),
                ],
                faces=[(0, 1, 2)],
                raw_displacements=[(0.0, 0.0, 0.0)] * 3,
                anchor_indices=[0],
                protected_indices=[1],
                limits=tuple(hostile_limits),
            )
        self.assertEqual(callbacks, [])

        vertices, faces = grid_fixture()
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "anchor_mapping_invalid"
        ):
            compute_fixture(
                vertices,
                faces,
                ["torso"] * len(vertices),
                [8],
                EffectfulDict({0: (0.01, 0.0, 0.0)}),
            )
        self.assertEqual(callbacks, [])

    def test_canonical_json_rejects_effectful_and_noncanonical_values(self):
        class EqualInt(int):
            pass

        class EffectfulDict(dict):
            pass

        with self.assertRaises(fit.WholeSurfaceMathError):
            fit.canonical_json_bytes({"value": EqualInt(1)})
        with self.assertRaises(fit.WholeSurfaceMathError):
            fit.canonical_json_bytes(EffectfulDict({"value": 1}))
        with self.assertRaises(fit.WholeSurfaceMathError):
            fit.canonical_json_bytes({"value": 1.0})

    def test_empty_protected_anchor_overlap_and_aliases_fail_closed(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "protected_set_empty"
        ):
            compute_fixture(
                vertices,
                faces,
                regions,
                [],
                {0: (0.01, 0.0, 0.0)},
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "anchor_inside"
        ):
            compute_fixture(
                vertices,
                faces,
                regions,
                [0, 8],
                {0: (0.01, 0.0, 0.0)},
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "duplicate_or_out_of_range"
        ):
            compute_fixture(
                vertices,
                faces,
                regions,
                [8, 8],
                {0: (0.01, 0.0, 0.0)},
            )

    def test_exact_scalar_subclasses_cannot_forge_bindings(self):
        class EqualString(str):
            def __eq__(self, _other):
                return True

        class EqualInt(int):
            def __eq__(self, _other):
                return True

        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.01, 0.0, 0.0)}
        with self.assertRaises(fit.WholeSurfaceMathError):
            compute_fixture(
                vertices,
                faces,
                regions,
                protected,
                anchors,
                qualification_id=EqualString(
                    "kira_r25_qualified_continuous_foundation"
                ),
            )
        with self.assertRaises(fit.WholeSurfaceMathError):
            compute_fixture(
                vertices,
                faces,
                regions,
                protected,
                anchors,
                expected_vertex_count=EqualInt(len(vertices)),
            )

    def test_inputs_are_not_mutated(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: [0.01, 0.0, 0.0]}
        before = copy.deepcopy((vertices, faces, regions, protected, anchors))
        compute_fixture(vertices, faces, regions, protected, anchors)
        self.assertEqual(
            (vertices, faces, regions, protected, anchors), before
        )

    def test_every_evidence_field_tamper_replay_mismatches(self):
        vertices, faces = grid_fixture()
        arguments = fixture_arguments(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            {0: (0.015, 0.0, 0.0)},
        )
        payload = fit.compute_r25_whole_surface_math(**arguments)
        for name, original in payload["evidence"].items():
            altered = copy.deepcopy(payload)
            if type(original) is int:
                altered["evidence"][name] = original + 1
            elif type(original) is str:
                altered["evidence"][name] = original + "__tampered"
            elif type(original) is list:
                altered["evidence"][name] = original + ["tampered"]
            else:
                self.fail(f"unexpected evidence type for {name}")
            with self.subTest(field=name), self.assertRaisesRegex(
                fit.WholeSurfaceMathError, "replay_mismatch"
            ):
                fit.replay_r25_whole_surface_math(
                    claimed_payload=altered, **arguments
                )

    def test_public_callables_expose_no_live_closure_or_issuance_state(self):
        public_functions = {
            name: getattr(fit, name)
            for name in fit.__all__
            if inspect.isfunction(getattr(fit, name))
        }
        self.assertTrue(public_functions)
        for name, function in public_functions.items():
            with self.subTest(public_callable=name):
                self.assertIsNone(function.__closure__)

        forbidden_name_parts = (
            "registry",
            "weakref",
            "issuance",
            "issuer",
            "registration",
            "authority_token",
        )
        exposed = {
            name
            for name in vars(fit)
            if any(part in name.lower() for part in forbidden_name_parts)
        }
        self.assertEqual(exposed, set())
        mutable_baselines = {
            name
            for name, value in vars(fit).items()
            if not name.startswith("__")
            and name.isupper()
            and type(value) in (dict, list, set)
        }
        self.assertEqual(mutable_baselines, set())

    def test_v4_closure_and_toctou_attacks_can_never_create_authority(self):
        vertices, faces = grid_fixture()
        arguments = fixture_arguments(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            {0: (0.01, 0.0, 0.0)},
        )
        self.assertIsNone(fit.compute_r25_whole_surface_math.__closure__)
        self.assertIsNone(fit.replay_r25_whole_surface_math.__closure__)

        with mock.patch.object(
            fit, "_fixed_1e12", lambda _value, _label: 777_777_777_777
        ):
            altered_math = fit.compute_r25_whole_surface_math(**arguments)
        self.assertEqual(altered_math["status"], fit.STATIC_MATH_STATUS)
        self.assertEqual(altered_math["check_scope"], fit.NONAUTHORITATIVE_CHECK)
        altered_strings = tuple(
            value.lower() for value in payload_strings(altered_math)
        )
        self.assertFalse(any("accepted" in value for value in altered_strings))
        self.assertNotIn("yes", altered_strings)

        with mock.patch.object(fit, "STATIC_MATH_STATUS", "ACCEPTED"), \
             mock.patch.object(fit, "NONAUTHORITATIVE_CHECK", "YES"):
            literal_bound = fit.compute_r25_whole_surface_math(**arguments)
            self.assertEqual(
                literal_bound["status"],
                "STATIC_MATH_CORE_ONLY_REQUIRES_EXACT_BYTE_ISOLATED_WORKER_CONTROLLER",
            )
            self.assertEqual(
                literal_bound["check_scope"],
                "NONAUTHORITATIVE_IN_PROCESS_MATH_CHECK",
            )
            self.assertEqual(
                fit.replay_r25_whole_surface_math(
                    claimed_payload=literal_bound, **arguments
                ),
                "NONAUTHORITATIVE_IN_PROCESS_MATH_CHECK",
            )

        fabricated = {
            "schema": "caller.fabricated",
            "status": "ACCEPTED",
            "evidence": {"solver_history_replayed": "YES"},
        }
        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "replay_mismatch"
        ):
            fit.replay_r25_whole_surface_math(
                claimed_payload=fabricated, **arguments
            )
        with mock.patch.object(
            fit,
            "compute_r25_whole_surface_math",
            return_value=fabricated,
        ):
            self.assertEqual(
                fit.replay_r25_whole_surface_math(
                    claimed_payload=fabricated, **arguments
                ),
                fit.NONAUTHORITATIVE_CHECK,
            )

        callbacks = []

        class EffectfulClaim(dict):
            def items(self):
                callbacks.append("items")
                fit._fixed_1e12 = lambda _value, _label: 424_242_424_242
                return super().items()

        with self.assertRaisesRegex(
            fit.WholeSurfaceMathError, "claimed_payload_not_plain_dict"
        ):
            fit.replay_r25_whole_surface_math(
                claimed_payload=EffectfulClaim(fabricated), **arguments
            )
        self.assertEqual(callbacks, [])

    def test_copy_pickle_and_reload_preserve_only_non_authoritative_data(self):
        vertices, faces = grid_fixture()
        arguments = fixture_arguments(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            {0: (0.01, 0.0, 0.0)},
        )
        payload = fit.compute_r25_whole_surface_math(**arguments)
        copies = (copy.copy(payload), copy.deepcopy(payload), pickle.loads(pickle.dumps(payload)))
        for copied in copies:
            self.assertEqual(copied, payload)
            self.assertEqual(copied["status"], fit.STATIC_MATH_STATUS)
            self.assertEqual(
                fit.replay_r25_whole_surface_math(
                    claimed_payload=copied, **arguments
                ),
                fit.NONAUTHORITATIVE_CHECK,
            )
        reloaded = importlib.reload(fit)
        self.assertEqual(
            reloaded.replay_r25_whole_surface_math(
                claimed_payload=payload, **arguments
            ),
            reloaded.NONAUTHORITATIVE_CHECK,
        )

    def test_14658_vertex_sparse_memory_is_bounded(self):
        columns = 7_329
        vertices = []
        for column in range(columns):
            x = float(column) * 0.001
            vertices.extend(((x, 0.0, 0.0), (x, 1.0, 0.0)))
        faces = []
        for column in range(columns - 1):
            a = 2 * column
            b = a + 1
            c = a + 2
            d = a + 3
            faces.extend(((a, c, d), (a, d, b)))
        self.assertEqual(len(vertices), 14_658)
        regions = ["torso"] * len(vertices)
        protected = [len(vertices) - 1]
        anchors = {0: (0.0, 0.0, 0.0)}
        limits = {"max_iterations": 2}
        arguments = fixture_arguments(
            vertices,
            faces,
            regions,
            protected,
            anchors,
            limits=limits,
        )
        tracemalloc.start()
        try:
            payload = fit.compute_r25_whole_surface_math(**arguments)
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        evidence = payload["evidence"]
        self.assertEqual(evidence["vertex_count"], 14_658)
        self.assertEqual(evidence["iteration_count"], 1)
        self.assertLess(
            evidence["sparse_adjacency_slot_count"], 8 * len(vertices)
        )
        self.assertLess(
            evidence["sparse_storage_units_upper_bound"], 40 * len(vertices)
        )
        self.assertLess(peak, 96 * 1024 * 1024)

    def test_source_is_pure_blender_free_and_has_no_authority_api(self):
        source = (
            ROOT / "tools/kira_r25_whole_surface_fit_core_v5.py"
        ).read_text(encoding="utf-8")
        lowered = source.lower()
        self.assertNotIn("import bpy", source)
        self.assertNotIn("numpy", lowered)
        self.assertNotIn("scipy", lowered)
        self.assertNotIn("save_as_mainfile", source)
        self.assertNotIn("render.render", source)
        self.assertNotIn("import weakref", source)
        self.assertNotIn("registry", lowered)
        self.assertNotIn("fitresult", lowered)
        self.assertNotIn("fitevidence", lowered)
        self.assertNotIn("validated_claims", lowered)
        self.assertNotIn("solver_history_replayed", lowered)
        self.assertIn(fit.STATIC_MATH_STATUS, source)
        self.assertIn(fit.NONAUTHORITATIVE_CHECK, source)

    def test_rejected_v1_through_v4_and_both_audits_remain_byte_exact(self):
        expected = {
            "tools/kira_r25_whole_surface_fit_core_v1.py": (
                36_740,
                "90034928e92c27edea8160ab4163193d7789047ff1114cc415072932a43e1e61",
            ),
            "Testing/test_kira_r25_whole_surface_fit_core_v1.py": (
                15_778,
                "fe9a148b09ccc9e51622a076120d5626d996017533b7e7148dd723dcc25fbb2d",
            ),
            "tools/kira_r25_whole_surface_fit_core_v2.py": (
                39_062,
                "aa03aae0f7699a1a26b526034f2783d6c1b666b635b1763175e1acc2e7e52548",
            ),
            "Testing/test_kira_r25_whole_surface_fit_core_v2.py": (
                19_050,
                "1b9f4ecdabf3991031f916409be6730bdae50dac58d35d6602dbf9fa9427335b",
            ),
            "tools/kira_r25_whole_surface_fit_core_v3.py": (
                57_348,
                "21f08df8c1a85dcaf25d194880ec6b8a66df820ccee287d50edc83e7d8bde94f",
            ),
            "Testing/test_kira_r25_whole_surface_fit_core_v3.py": (
                27_473,
                "d9116450d77c56fad30e0fb1c61fd3be69c12e17ba360c3017de60845335bd0b",
            ),
            "RecoverySprint/continuation_20260809/kira_r25_whole_surface_fit_core_static_preparation/attempt_03/INDEPENDENT_AUDIT.md": (
                10_167,
                "8b70d58e6ae11a068ffbf4797bbfbfca4938b5bb552c831698839b90173612db",
            ),
            "tools/kira_r25_whole_surface_fit_core_v4.py": (
                65_380,
                "230e643f8c94a0fd9cd2b855080255edb5690c4c16766f7ca783fa7c8f0e2d07",
            ),
            "Testing/test_kira_r25_whole_surface_fit_core_v4.py": (
                36_515,
                "313fe6026ddc85f3d098f511c599032f556c74ad62b297a5ff097573b30c74f3",
            ),
            "RecoverySprint/continuation_20260809/kira_r25_whole_surface_fit_core_static_preparation/attempt_04/INDEPENDENT_AUDIT.md": (
                12_734,
                "2461a22d88fe9b54978b476a1083198b8ae8b6397cf39cf34d80a3ad6c4c31a3",
            ),
        }
        for relative, (expected_bytes, expected_hash) in expected.items():
            path = ROOT / relative
            with self.subTest(path=relative):
                data = path.read_bytes()
                self.assertEqual(len(data), expected_bytes)
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)


if __name__ == "__main__":
    unittest.main()
