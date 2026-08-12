from __future__ import annotations

import copy
import hashlib
import importlib
import pickle
import sys
import tracemalloc
import unittest
from dataclasses import fields, replace
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r25_whole_surface_fit_core_v4 as fit


def edge_count(faces):
    edges = set()
    for face in faces:
        for position, first in enumerate(face):
            second = face[(position + 1) % len(face)]
            edges.add(tuple(sorted((first, second))))
    return len(edges)


def solve_fixture(vertices, faces, regions, protected, anchors, *, limits=None, **changes):
    selected_limits = limits or fit.FitLimits()
    remaining_changes = dict(changes)
    if "expected_anchor_sha256" in remaining_changes:
        expected_anchor = remaining_changes.pop("expected_anchor_sha256")
    else:
        expected_anchor = fit.anchor_displacements_sha256(anchors, len(vertices))
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
        "expected_protected_sha256": fit.index_set_sha256(protected, len(vertices)),
        "expected_anchor_sha256": expected_anchor,
        "limits": selected_limits,
        "expected_limits_sha256": fit.fit_limits_sha256(selected_limits),
    }
    arguments.update(remaining_changes)
    return fit.solve_r25_whole_surface_fit(**arguments)


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


class WholeSurfaceFitCoreTests(unittest.TestCase):
    def test_protected_is_exact_zero_anchor_is_exact_and_topology_is_preserved(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.02, 0.01, 0.005)}
        result = solve_fixture(vertices, faces, regions, protected, anchors)
        self.assertEqual(result.displacement_field[8], (0.0, 0.0, 0.0))
        self.assertEqual(result.candidate_vertices[8], tuple(vertices[8]))
        self.assertEqual(result.displacement_field[0], anchors[0])
        self.assertEqual(result.evidence.protected_vertex_count, 1)
        self.assertEqual(result.evidence.anchor_count, 1)
        self.assertEqual(
            result.evidence.topology_sha256,
            result.evidence.topology_after_sha256,
        )
        self.assertEqual(result.evidence.converged, "YES")
        self.assertLessEqual(
            result.evidence.raw_equation_residual_inf_fixed_1e12,
            101,
        )

    def test_same_region_propagation_has_no_cross_region_component(self):
        columns, rows = 4, 2
        vertices, faces = grid_fixture(columns, rows)
        regions = []
        for _row in range(rows):
            regions.extend(("torso", "torso", "head", "head"))
        protected = [columns]
        anchors = {
            0: (0.03, 0.0, 0.0),
            3: (0.0, 0.04, 0.0),
        }
        result = solve_fixture(vertices, faces, regions, protected, anchors)
        for index, region in enumerate(regions):
            value = result.displacement_field[index]
            if region == "torso":
                self.assertEqual(value[1], 0.0)
                self.assertEqual(value[2], 0.0)
            else:
                self.assertEqual(value[0], 0.0)
                self.assertEqual(value[2], 0.0)

    def test_unknown_and_disconnected_semantic_regions_fail_closed(self):
        vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
        faces = [(0, 1, 2, 3)]
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "unknown_semantic_region"):
            solve_fixture(
                vertices,
                faces,
                ["torso", "torso", "torso", "unknown"],
                [3],
                {0: (0.0, 0.0, 0.0)},
            )
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "same_region_graph_disconnected"):
            solve_fixture(
                vertices,
                faces,
                ["torso", "head", "torso", "head"],
                [3],
                {0: (0.0, 0.0, 0.0), 1: (0.0, 0.0, 0.0)},
            )

    def test_protected_cut_that_leaves_unanchored_free_component_fails(self):
        vertices, faces = grid_fixture(5, 2)
        regions = ["torso"] * len(vertices)
        # Protect the full middle column.  Removing it splits the movable graph.
        protected = [2, 7]
        anchors = {0: (0.01, 0.0, 0.0)}
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "same_region_free_component_without_anchor"
        ):
            solve_fixture(vertices, faces, regions, protected, anchors)

    def test_anchor_preserving_line_search_rejects_flip_and_degenerate(self):
        baseline = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        raw = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, -2.0, 0.0)]
        accepted, candidate, denominator, rejections = fit._line_search_anchor_preserving(
            baseline_vertices=baseline,
            faces=[(0, 1, 2)],
            raw_displacements=raw,
            anchor_indices=[0],
            protected_indices=[1],
            limits=fit.FitLimits(
                maximum_displacement=3.0,
                minimum_area_ratio=0.20,
                maximum_area_ratio=5.0,
            ),
        )
        self.assertEqual(denominator, 4)
        self.assertEqual(accepted[0], raw[0])
        self.assertEqual(accepted[1], (0.0, 0.0, 0.0))
        self.assertEqual(accepted[2], (0.0, -0.5, 0.0))
        self.assertEqual(candidate[2], (0.0, 0.5, 0.0))
        self.assertIn("orientation_flip", rejections[0])
        self.assertIn("degenerate", rejections[1])

    def test_line_search_rejects_area_ratio_and_excessive_displacement(self):
        baseline = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        area_raw = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 9.0, 0.0)]
        accepted, _, denominator, rejections = fit._line_search_anchor_preserving(
            baseline_vertices=baseline,
            faces=[(0, 1, 2)],
            raw_displacements=area_raw,
            anchor_indices=[0],
            protected_indices=[1],
            limits=fit.FitLimits(
                maximum_displacement=100.0,
                minimum_area_ratio=0.10,
                maximum_area_ratio=2.0,
            ),
        )
        self.assertEqual(denominator, 16)
        self.assertTrue(all("area_ratio" in row for row in rejections))
        self.assertEqual(accepted[0], area_raw[0])

        displacement_raw = [
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 4.0),
        ]
        _, _, denominator, rejections = fit._line_search_anchor_preserving(
            baseline_vertices=baseline,
            faces=[(0, 1, 2)],
            raw_displacements=displacement_raw,
            anchor_indices=[0],
            protected_indices=[1],
            limits=fit.FitLimits(
                maximum_displacement=0.6,
                minimum_area_ratio=0.10,
                maximum_area_ratio=5.0,
            ),
        )
        self.assertEqual(denominator, 8)
        self.assertTrue(all("maximum_displacement" in row for row in rejections))

    def test_nonfinite_and_baseline_degenerate_are_rejected(self):
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "nonfinite"):
            fit._line_search_anchor_preserving(
                baseline_vertices=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
                faces=[(0, 1, 2)],
                raw_displacements=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (float("nan"), 0.0, 0.0)],
                anchor_indices=[0],
                protected_indices=[1],
                limits=fit.FitLimits(),
            )

    def test_empty_protected_set_and_constraint_aliases_fail_closed(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "protected_set_empty"):
            solve_fixture(
                vertices,
                faces,
                regions,
                [],
                {0: (0.01, 0.0, 0.0)},
            )
        baseline = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        raw = [(0.0, 0.0, 0.0)] * 3
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "duplicate"):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2)],
                raw_displacements=raw,
                anchor_indices=[0, 0],
                protected_indices=[1],
                limits=fit.FitLimits(),
            )
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "invalid"):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2)],
                raw_displacements=raw,
                anchor_indices=[True],
                protected_indices=[1],
                limits=fit.FitLimits(),
            )
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "baseline_triangle_degenerate"):
            fit._line_search_anchor_preserving(
                baseline_vertices=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
                faces=[(0, 1, 2)],
                raw_displacements=[(0.0, 0.0, 0.0)] * 3,
                anchor_indices=[0],
                protected_indices=[1],
                limits=fit.FitLimits(),
            )

    def test_solver_does_not_mutate_inputs(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: [0.02, 0.0, 0.0]}
        snapshots = copy.deepcopy((vertices, faces, regions, protected, anchors))
        solve_fixture(vertices, faces, regions, protected, anchors)
        self.assertEqual((vertices, faces, regions, protected, anchors), snapshots)

    def test_effectful_anchor_mapping_subclass_is_rejected_without_callback(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        benign = {0: (0.01, 0.0, 0.0)}

        class StatefulAnchors(dict):
            def __init__(self):
                super().__init__(benign)
                self.calls = 0

            def items(self):
                self.calls += 1
                if self.calls == 1:
                    return benign.items()
                return {0: (0.02, 0.0, 0.0)}.items()

        stateful = StatefulAnchors()
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "anchor_mapping_invalid"
        ):
            solve_fixture(
                vertices,
                faces,
                regions,
                protected,
                stateful,
                expected_anchor_sha256=fit.anchor_displacements_sha256(
                    benign, len(vertices)
                ),
            )
        self.assertEqual(stateful.calls, 0)

    def test_fit_limits_subclass_is_rejected_before_use(self):
        class UntrustedLimits(fit.FitLimits):
            pass

        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "limits_type_invalid"):
            fit.fit_limits_sha256(UntrustedLimits())

    def test_exact_scalar_subclasses_cannot_forge_bindings_or_regions(self):
        class EqualStr(str):
            def __eq__(self, _other):
                return True

            def __ne__(self, _other):
                return False

            __hash__ = str.__hash__

        class EqualInt(int):
            def __eq__(self, _other):
                return True

            def __ne__(self, _other):
                return False

            __hash__ = int.__hash__

        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.01, 0.0, 0.0)}
        changes = (
            {"qualification_id": EqualStr("EVIL_QUALIFICATION")},
            {"baseline_space": EqualStr("EVIL_BASELINE")},
            {"anchor_space": EqualStr("EVIL_ANCHOR")},
            {"expected_topology_sha256": EqualStr("evil")},
            {"expected_baseline_sha256": EqualStr("evil")},
            {"expected_regions_sha256": EqualStr("evil")},
            {"expected_protected_sha256": EqualStr("evil")},
            {"expected_anchor_sha256": EqualStr("evil")},
            {"expected_limits_sha256": EqualStr("evil")},
            {"expected_vertex_count": EqualInt(999)},
            {"expected_edge_count": EqualInt(999)},
            {"expected_face_count": EqualInt(999)},
            {"expected_connected_components": EqualInt(999)},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(
                fit.WholeSurfaceFitError
            ):
                solve_fixture(
                    vertices, faces, regions, protected, anchors, **change
                )
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "unknown_semantic_region"
        ):
            fit.regions_sha256([EqualStr("torso")])

    def test_effectful_numeric_subclasses_are_rejected_before_callbacks(self):
        holder = {"calls": 0}

        class MutatingFloat(float):
            def __float__(self):
                holder["calls"] += 1
                object.__setattr__(holder["limits"], "maximum_displacement", 100.0)
                return 0.25

        limits = fit.FitLimits(
            screen_weight=MutatingFloat(0.25),
            maximum_displacement=0.1,
        )
        holder["limits"] = limits
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "not_numeric"):
            fit.fit_limits_sha256(limits)
        self.assertEqual(holder["calls"], 0)
        self.assertEqual(limits.maximum_displacement, 0.1)

        class CallbackFloat(float):
            def __float__(self):
                holder["calls"] += 1
                return 0.0

        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "not_numeric"):
            fit.baseline_sha256([(CallbackFloat(0.0), 0.0, 0.0)])
        self.assertEqual(holder["calls"], 0)

    def test_expected_hashes_are_exact_lowercase_sha256(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.01, 0.0, 0.0)}
        valid = fit.topology_sha256(len(vertices), faces)
        for invalid in (valid.upper(), valid[:-1], "g" * 64):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(
                fit.WholeSurfaceFitError, "not_lowercase_sha256"
            ):
                solve_fixture(
                    vertices,
                    faces,
                    regions,
                    protected,
                    anchors,
                    expected_topology_sha256=invalid,
                )

    def test_canonical_json_rejects_effectful_container_and_scalar_subclasses(self):
        class EqualInt(int):
            pass

        class EffectfulDict(dict):
            pass

        with self.assertRaises(fit.WholeSurfaceFitError):
            fit.canonical_json_bytes({"value": EqualInt(1)})
        with self.assertRaises(fit.WholeSurfaceFitError):
            fit.canonical_json_bytes(EffectfulDict({"value": 1}))

    def test_canonical_result_rejects_direct_replace_and_registered_tampering(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.01, 0.0, 0.0)}
        valid = solve_fixture(vertices, faces, regions, protected, anchors)
        forged_evidence = replace(
            valid.evidence,
            topology_sha256="0" * 64,
            topology_after_sha256="1" * 64,
            candidate_vertex_sha256="2" * 64,
        )
        forged_candidate = tuple((999.0, 999.0, 999.0) for _ in vertices)
        self.assertNotIn(
            "topology_index_preserved", forged_evidence.payload()
        )
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "direct_construction_forbidden"
        ):
            fit.FitResult(
                valid.displacement_field,
                forged_candidate,
                forged_evidence,
            )
        with self.assertRaises(TypeError):
            replace(
                valid,
                candidate_vertices=forged_candidate,
                evidence=forged_evidence,
            )

        object.__setattr__(valid, "_candidate_vertices", forged_candidate)
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError,
            "fit_result_candidate_tampered",
        ):
            valid.canonical_payload()

        evidence_tampered = solve_fixture(
            vertices, faces, regions, protected, anchors
        )
        object.__setattr__(evidence_tampered, "_evidence", forged_evidence)
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "fit_result_evidence_tampered"
        ):
            evidence_tampered.canonical_payload()

    def test_no_module_constructor_or_caller_binding_registration_path_exists(self):
        forbidden_exact = {
            "_construct_fit_result",
            "_create_fit_result_api",
            "_ResultBindings",
            "_build_solver_result_boundary",
            "_compute_r25_whole_surface_state",
            "_boundary",
        }
        self.assertTrue(forbidden_exact.isdisjoint(vars(fit)))
        discoverable = {
            name
            for name in vars(fit)
            if any(
                word in name.lower()
                for word in ("issuer", "issuance", "register", "factory")
            )
        }
        self.assertEqual(discoverable, set())
        bare = object.__new__(fit.FitResult)
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "fit_result_not_solver_issued"
        ):
            bare.canonical_payload()

    def test_v3_private_constructor_forgery_is_closed_and_history_is_replayed(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.01, 0.0, 0.0)}
        result = solve_fixture(vertices, faces, regions, protected, anchors)
        payload = result.canonical_payload()
        self.assertEqual(
            payload["evidence"]["validated_claims"]["solver_history_replayed"],
            "YES",
        )
        forged = replace(
            result.evidence,
            final_update_inf_fixed_1e12=8_999_999_999_999_999_999,
        )
        object.__setattr__(result, "_evidence", forged)
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "fit_result_evidence_tampered"
        ):
            result.canonical_payload()

    def test_always_equal_visible_state_tampering_fails_before_equality_dispatch(self):
        class AlwaysEqual:
            def __eq__(self, _other):
                return True

            def __ne__(self, _other):
                return False

        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.02, 0.0, 0.0)}

        field_result = solve_fixture(vertices, faces, regions, protected, anchors)
        object.__setattr__(field_result, "_displacement_field", AlwaysEqual())
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "fit_result_displacement_shape_tampered"
        ):
            field_result.canonical_payload()

        candidate_result = solve_fixture(vertices, faces, regions, protected, anchors)
        candidate = list(candidate_result.candidate_vertices)
        candidate[0] = (AlwaysEqual(), 0.0, 0.0)
        object.__setattr__(candidate_result, "_candidate_vertices", tuple(candidate))
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "fit_result_candidate_scalar_tampered:0"
        ):
            candidate_result.canonical_payload()

        evidence_result = solve_fixture(vertices, faces, regions, protected, anchors)
        object.__setattr__(
            evidence_result.evidence,
            "final_update_inf_fixed_1e12",
            AlwaysEqual(),
        )
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError,
            "evidence_final_update_inf_fixed_1e12_invalid",
        ):
            evidence_result.canonical_payload()

    def test_every_serialized_evidence_field_is_replayed_not_trusted(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.015, 0.0, 0.0)}
        result = solve_fixture(vertices, faces, regions, protected, anchors)
        evidence = result.evidence

        for description in fields(fit.FitEvidence):
            name = description.name
            original = object.__getattribute__(evidence, name)
            if type(original) is int:
                tampered = original + 1
            elif type(original) is str:
                if len(original) == 64 and all(
                    character in "0123456789abcdef" for character in original
                ):
                    tampered = ("0" if original != "0" * 64 else "1") * 64
                else:
                    tampered = original + "__tampered"
            elif type(original) is tuple:
                tampered = original + ("tampered_replayed_claim",)
            else:
                self.fail(f"unexpected evidence primitive type for {name}")

            object.__setattr__(evidence, name, tampered)
            with self.subTest(evidence_field=name):
                with self.assertRaises(fit.WholeSurfaceFitError):
                    result.canonical_payload()
            object.__setattr__(evidence, name, original)

        self.assertEqual(
            result.canonical_payload()["evidence"]["validated_claims"][
                "solver_history_replayed"
            ],
            "YES",
        )

    def test_evidence_payload_and_class_method_monkeypatches_fail_closed(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.01, 0.0, 0.0)}
        original_payload = fit.FitEvidence.payload
        try:
            fit.FitEvidence.payload = lambda _self: {"attacker_controlled": "YES"}
            with self.assertRaisesRegex(
                fit.WholeSurfaceFitError, "evidence_class_changed:payload"
            ):
                solve_fixture(vertices, faces, regions, protected, anchors)
        finally:
            fit.FitEvidence.payload = original_payload

        result = solve_fixture(vertices, faces, regions, protected, anchors)
        try:
            fit.FitEvidence.payload = lambda _self: {"attacker_controlled": "YES"}
            with self.assertRaisesRegex(
                fit.WholeSurfaceFitError, "evidence_class_changed:payload"
            ):
                result.canonical_payload()
        finally:
            fit.FitEvidence.payload = original_payload
        self.assertNotIn("attacker_controlled", result.canonical_payload()["evidence"])

        with self.assertRaises(TypeError):
            fit.FitResult.canonical_payload = lambda _self: {
                "attacker_controlled": "YES"
            }

        original_result_method = fit.FitResult.__dict__["canonical_payload"]
        try:
            type.__setattr__(
                fit.FitResult,
                "canonical_payload",
                lambda _self: {"attacker_controlled": "YES"},
            )
            with self.assertRaisesRegex(
                fit.WholeSurfaceFitError,
                "result_class_changed:canonical_payload",
            ):
                result.canonical_payload()
        finally:
            type.__setattr__(
                fit.FitResult,
                "canonical_payload",
                original_result_method,
            )

        with mock.patch.object(fit.hashlib, "sha256", lambda _value=b"": None):
            with self.assertRaisesRegex(
                fit.WholeSurfaceFitError,
                "dependency_attribute_changed:hashlib.sha256",
            ):
                result.canonical_payload()

    def test_result_copy_deepcopy_and_pickle_attacks_fail_closed(self):
        vertices, faces = grid_fixture()
        result = solve_fixture(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            {0: (0.01, 0.0, 0.0)},
        )
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "copy_forbidden"):
            copy.copy(result)
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "deepcopy_forbidden"
        ):
            copy.deepcopy(result)
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "pickle_forbidden"):
            pickle.dumps(result)

    def test_private_line_search_rejects_empty_and_duplicate_boundaries(self):
        self.assertNotIn("line_search_anchor_preserving", fit.__all__)
        self.assertFalse(hasattr(fit, "line_search_anchor_preserving"))
        baseline = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        raw = [(0.0, 0.0, 0.0)] * 3
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "line_faces_empty"):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[],
                raw_displacements=raw,
                anchor_indices=[0],
                protected_indices=[1],
                limits=fit.FitLimits(),
            )
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "anchor_set_empty"):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2)],
                raw_displacements=raw,
                anchor_indices=[],
                protected_indices=[],
                limits=fit.FitLimits(),
            )
        with self.assertRaisesRegex(fit.WholeSurfaceFitError, "duplicate_face"):
            fit._line_search_anchor_preserving(
                baseline_vertices=baseline,
                faces=[(0, 1, 2), (2, 1, 0)],
                raw_displacements=raw,
                anchor_indices=[0],
                protected_indices=[1],
                limits=fit.FitLimits(),
            )

    def test_absolute_iteration_and_backtrack_ceilings_fail_closed(self):
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError, "max_iterations_above_absolute_ceiling"
        ):
            fit.fit_limits_sha256(
                fit.FitLimits(max_iterations=fit.MAX_JACOBI_ITERATIONS + 1)
            )
        with self.assertRaisesRegex(
            fit.WholeSurfaceFitError,
            "maximum_line_search_backtracks_above_absolute_ceiling",
        ):
            fit.fit_limits_sha256(
                fit.FitLimits(
                    maximum_line_search_backtracks=
                        fit.MAX_LINE_SEARCH_BACKTRACKS + 1
                )
            )

    def test_determinism_canonical_field_and_evidence_hashes(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.025, -0.01, 0.003)}
        first = solve_fixture(vertices, faces, regions, protected, anchors)
        second = solve_fixture(vertices, faces, regions, protected, anchors)
        self.assertEqual(first.displacement_field, second.displacement_field)
        self.assertEqual(first.candidate_vertices, second.candidate_vertices)
        self.assertEqual(first.evidence, second.evidence)
        self.assertEqual(first.canonical_sha256(), second.canonical_sha256())
        payload = first.canonical_payload()
        self.assertEqual(payload["schema"], "kira.r25.whole_surface_geometry_field.v4")
        self.assertEqual(payload["status"], "STATIC_GEOMETRY_FIELD_VALIDATED_NOT_A_BODY")
        self.assertEqual(
            hashlib.sha256(fit.canonical_json_bytes(payload)).hexdigest(),
            first.canonical_sha256(),
        )

    def test_backtracked_nonconverged_field_cannot_be_accepted(self):
        vertices, faces = grid_fixture()
        regions = ["torso"] * len(vertices)
        protected = [8]
        anchors = {0: (0.02, 0.0, 0.0)}
        forged_field = [(0.0, 0.0, 0.0) for _ in vertices]
        forged_field[0] = anchors[0]
        forged_field[4] = (0.10, 0.0, 0.0)
        forged_candidate = [
            tuple(vertices[index][axis] + forged_field[index][axis] for axis in range(3))
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
            fit.WholeSurfaceFitError,
            "module_integrity_changed:_line_search_anchor_preserving",
        ):
            solve_fixture(vertices, faces, regions, protected, anchors)

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
            with self.subTest(change=change), self.assertRaises(fit.WholeSurfaceFitError):
                solve_fixture(vertices, faces, regions, protected, anchors, **change)

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
        # Expected bindings are formed before memory measurement; the measured
        # region therefore covers the solver rather than fixture construction.
        bindings = {
            "expected_vertex_count": len(vertices),
            "expected_edge_count": edge_count(faces),
            "expected_face_count": len(faces),
            "expected_connected_components": 1,
            "expected_topology_sha256": fit.topology_sha256(len(vertices), faces),
            "expected_baseline_sha256": fit.baseline_sha256(vertices),
            "expected_regions_sha256": fit.regions_sha256(regions),
            "expected_protected_sha256": fit.index_set_sha256(protected, len(vertices)),
            "expected_anchor_sha256": fit.anchor_displacements_sha256(anchors, len(vertices)),
        }
        selected_limits = fit.FitLimits(max_iterations=2)
        bindings["expected_limits_sha256"] = fit.fit_limits_sha256(selected_limits)
        tracemalloc.start()
        try:
            result = fit.solve_r25_whole_surface_fit(
                qualification_id="kira_r25_qualified_continuous_foundation",
                baseline_space="globally_aligned_foundation",
                anchor_space="globally_aligned_foundation_displacement",
                baseline_vertices=vertices,
                faces=faces,
                vertex_regions=regions,
                protected_vertices=protected,
                anchor_displacements=anchors,
                limits=selected_limits,
                **bindings,
            )
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(result.evidence.vertex_count, 14_658)
        self.assertEqual(result.evidence.iteration_count, 1)
        self.assertLess(result.evidence.sparse_adjacency_slot_count, 8 * len(vertices))
        self.assertLess(result.evidence.sparse_storage_units_upper_bound, 40 * len(vertices))
        self.assertLess(peak, 96 * 1024 * 1024)

    def test_source_is_blender_free_and_has_no_dense_matrix_dependency(self):
        source = (ROOT / "tools/kira_r25_whole_surface_fit_core_v4.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("import bpy", source)
        self.assertNotIn("numpy", source.lower())
        self.assertNotIn("scipy", source.lower())
        self.assertNotIn("save_as_mainfile", source)
        self.assertNotIn("render.render", source)
        self.assertNotIn(".payload()", source)
        self.assertNotIn("_construct_fit_result", source)
        self.assertNotIn("_ResultBindings", source)
        self.assertIn("dense_matrix_constructed\": \"NO", source)

    def test_rejected_v1_v2_v3_and_audit_remain_byte_exact(self):
        expected = {
            "tools/kira_r25_whole_surface_fit_core_v1.py":
                "90034928e92c27edea8160ab4163193d7789047ff1114cc415072932a43e1e61",
            "Testing/test_kira_r25_whole_surface_fit_core_v1.py":
                "fe9a148b09ccc9e51622a076120d5626d996017533b7e7148dd723dcc25fbb2d",
            "tools/kira_r25_whole_surface_fit_core_v2.py":
                "aa03aae0f7699a1a26b526034f2783d6c1b666b635b1763175e1acc2e7e52548",
            "Testing/test_kira_r25_whole_surface_fit_core_v2.py":
                "1b9f4ecdabf3991031f916409be6730bdae50dac58d35d6602dbf9fa9427335b",
            "tools/kira_r25_whole_surface_fit_core_v3.py":
                "21f08df8c1a85dcaf25d194880ec6b8a66df820ccee287d50edc83e7d8bde94f",
            "Testing/test_kira_r25_whole_surface_fit_core_v3.py":
                "d9116450d77c56fad30e0fb1c61fd3be69c12e17ba360c3017de60845335bd0b",
            "RecoverySprint/continuation_20260809/kira_r25_whole_surface_fit_core_static_preparation/attempt_03/INDEPENDENT_AUDIT.md":
                "8b70d58e6ae11a068ffbf4797bbfbfca4938b5bb552c831698839b90173612db",
        }
        for relative, digest in expected.items():
            with self.subTest(relative=relative):
                self.assertEqual(
                    hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                    digest,
                )

    def test_z_reload_invalidates_prior_generation_results(self):
        vertices, faces = grid_fixture()
        old_result = solve_fixture(
            vertices,
            faces,
            ["torso"] * len(vertices),
            [8],
            {0: (0.01, 0.0, 0.0)},
        )
        old_result_type = type(old_result)
        importlib.reload(fit)
        self.assertIsNot(fit.FitResult, old_result_type)
        with self.assertRaisesRegex(Exception, "module_result_generation_changed"):
            old_result.canonical_payload()


if __name__ == "__main__":
    unittest.main()
