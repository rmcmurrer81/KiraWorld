from __future__ import annotations

import hashlib
import json
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_execution_contract"
)
CONTRACT = PACKAGE / "LOCAL_TRANSITION_CUT_EXECUTION_CONTRACT_STATIC_PROPOSAL.md"
PARENT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_boundary/"
    "LOCAL_TRANSITION_RETOPOLOGY_STATIC_PROPOSAL.md"
)
PARENT_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_boundary/CHECKPOINT.md"
)
PARENT_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_boundary/INDEPENDENT_STATIC_AUDIT.md"
)
PARENT_TEST = ROOT / "Testing/test_kira_r24_local_transition_retopology_boundary_static.py"
REPAIR_DOMAIN = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_02/"
    "BLACKPROJECT_ATTEMPT02_REPAIR_DOMAIN.json"
)
ATTEMPT47 = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "ATTEMPT47_RUNTIME_WRAPPER_LOG_PREFLIGHT_CONFLICT_CHECKPOINT.md"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def compact_sha256(value: object) -> str:
    return hashlib.sha256(compact_json(value)).hexdigest()


def canonical_edge(first: int, second: int) -> tuple[int, int]:
    if first == second:
        raise ValueError("edge endpoints must differ")
    return (first, second) if first < second else (second, first)


def canonical_triangle(loop: tuple[int, int, int]) -> tuple[int, int, int]:
    if len(set(loop)) != 3:
        raise ValueError("triangle vertices must be distinct")
    rotations = (
        loop,
        (loop[1], loop[2], loop[0]),
        (loop[2], loop[0], loop[1]),
    )
    return min(rotations)


def ratio(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def canonical_point_record(
    edge: tuple[int, int],
    tau: Fraction,
    phi: dict[int, Fraction],
    incident_faces: dict[tuple[int, int], tuple[int, ...]],
    collar_faces: set[int],
    face_loops: dict[int, tuple[int, int, int]],
) -> dict[str, object]:
    a, b = canonical_edge(*edge)
    incidence = tuple(sorted(incident_faces[(a, b)]))
    if len(incidence) != 2 or not set(incidence) <= collar_faces:
        raise ValueError("crossed edge is not owned by exactly two collar faces")
    if (phi[a] < tau) == (phi[b] < tau):
        raise ValueError("edge does not strictly cross the level")
    t = (tau - phi[a]) / (phi[b] - phi[a])
    if not Fraction(0) < t < Fraction(1):
        raise ValueError("cut point is not strictly inside the source edge")
    owner = min(incidence)
    vertices = canonical_triangle(face_loops[owner])
    if a not in vertices or b not in vertices:
        raise ValueError("owner triangle does not contain canonical edge")
    by_vertex = {a: 1 - t, b: t}
    weights = [by_vertex.get(vertex, Fraction(0)) for vertex in vertices]
    if sum(weights, Fraction(0)) != Fraction(1):
        raise ValueError("barycentric weights are not exactly normalized")
    return {
        "edge": [a, b],
        "owner_face": owner,
        "owner_triangle_vertices": list(vertices),
        "t": ratio(t),
        "barycentric": [ratio(weight) for weight in weights],
    }


def validate_crossed_edge_ledger(
    crossed_edges: set[tuple[int, int]],
    incident_faces: dict[tuple[int, int], tuple[int, ...]],
    collar_faces: set[int],
) -> set[int]:
    split_faces: set[int] = set()
    for edge in sorted(crossed_edges):
        incidence = tuple(sorted(incident_faces[canonical_edge(*edge)]))
        if len(incidence) != 2 or not set(incidence) <= collar_faces:
            raise ValueError("D4-exterior, D2, boundary, or nonmanifold edge")
        split_faces.update(incidence)
    if not split_faces <= collar_faces:
        raise ValueError("split ledger escaped the collar")
    return split_faces


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.fsum(a[index] * b[index] for index in range(3))


def norm(a: tuple[float, float, float]) -> float:
    return math.sqrt(dot(a, a))


def scale(a: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(component * factor for component in a)  # type: ignore[return-value]


def subtract(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(a[index] - b[index] for index in range(3))  # type: ignore[return-value]


def cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def matvec(
    matrix: tuple[tuple[float, float, float], ...],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(dot(row, vector) for row in matrix)  # type: ignore[return-value]


def determinant(matrix: tuple[tuple[float, float, float], ...]) -> float:
    return (
        matrix[0][0]
        * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1]
        * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2]
        * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )


def chart_frame(
    matrix: tuple[tuple[float, float, float], ...]
) -> tuple[tuple[float, float, float], ...]:
    if not all(math.isfinite(value) for row in matrix for value in row):
        raise ValueError("nonfinite matrix")
    if abs(determinant(matrix)) < 1e-15:
        raise ValueError("degenerate matrix")
    u0 = matvec(matrix, (1.0, 0.0, 0.0))
    n0 = matvec(matrix, (0.0, 0.0, -1.0))
    if norm(u0) < 1e-12:
        raise ValueError("degenerate U axis")
    u = scale(u0, 1.0 / norm(u0))
    rejected = subtract(n0, scale(u, dot(n0, u)))
    if norm(rejected) < 1e-12:
        raise ValueError("degenerate normal")
    n = scale(rejected, 1.0 / norm(rejected))
    v0 = cross(n, u)
    if norm(v0) < 1e-12:
        raise ValueError("degenerate V axis")
    v = scale(v0, 1.0 / norm(v0))
    return u, v, n


class LocalTransitionCutExecutionContractStaticTests(unittest.TestCase):
    def test_01_parent_records_are_byte_exact(self) -> None:
        expected = {
            PARENT: "64df882c44c23eb58f81bbcc94311269ac80f1444b27e144ec74e6c3cc18c3e7",
            PARENT_CHECKPOINT: "cfd791d16f97ef33a04e1c98ac6b32714805906506b8ff8dba88f108f1d9cbd7",
            PARENT_AUDIT: "75bdc7e3152aeffd4b8d17f9898b57c329e51c476c203b674547f297e07e2561",
            PARENT_TEST: "7f0c1d7bcb5b2dab501495c573b29e93bd3f694626e5595ba97278c05d79edf6",
            ATTEMPT47: "8e6c2eb624e5fa3d155d8f649a31f860470785ddb7d71b6634063d80ec3b1458",
            REPAIR_DOMAIN: "c14e5f7324ae3e4279eb6408b52de7eaecb372fb9afa8caf191f875b411473a3",
        }
        for path, expected_hash in expected.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256_file(path), expected_hash)

    def test_02_contract_is_static_fail_closed_and_complete(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        lower = text.lower()
        self.assertIn(
            "status: `static_execution_contract_complete_preflight_blocked_not_authorized`",
            lower,
        )
        for token in (
            "exactly 192 candidate records",
            "canonical owner face",
            "exact rational arithmetic",
            "no candidate-specific pca",
            "d2_d4_boundary_vertex_overlap",
            "no d4-exterior adjacent face is split",
            "fails before mutation",
        ):
            self.assertIn(token, lower)
        for forbidden in (
            "attempt_48",
            "bpy.",
            "open_mainfile",
            "save_as_mainfile",
            "blender.exe",
        ):
            self.assertNotIn(forbidden, lower)

    def test_03_actual_domain_exposes_exact_preflight_blocker(self) -> None:
        report = json.loads(REPAIR_DOMAIN.read_text(encoding="utf-8"))
        domains = {row["face_ring_expansion"]: row for row in report["domains"]}
        d2 = domains[2]
        d4 = domains[4]
        d2_vertices = set(d2["vertex_indices"])
        d4_boundary_vertices = {
            vertex for edge in d4["boundary_edges"] for vertex in edge
        }
        overlap = sorted(d2_vertices & d4_boundary_vertices)
        self.assertEqual(overlap, [5, 90, 91, 508, 534])
        self.assertEqual(
            compact_sha256(overlap),
            "53fe925030e94c6ad47eb7a7b0fce17093e16b576e026858136dbc4a3c9d087e",
        )
        d2_boundary_edges = {canonical_edge(*edge) for edge in d2["boundary_edges"]}
        d4_boundary_edges = {canonical_edge(*edge) for edge in d4["boundary_edges"]}
        self.assertEqual(d2_boundary_edges & d4_boundary_edges, set())
        self.assertTrue(set(overlap) <= set(d2["boundary_cycle_vertex_indices"][0]))
        self.assertTrue(set(overlap) <= set(d4["boundary_cycle_vertex_indices"][0]))

    def test_04_finite_rational_level_family_is_exact(self) -> None:
        levels = [Fraction(k, 193) for k in range(1, 193)]
        self.assertEqual(len(levels), 192)
        self.assertEqual(len(set(levels)), 192)
        self.assertEqual(levels[0], Fraction(1, 193))
        self.assertEqual(levels[-1], Fraction(192, 193))
        self.assertTrue(all(Fraction(0) < level < Fraction(1) for level in levels))
        self.assertTrue(all(level.denominator == 193 for level in levels))

    def test_05_canonical_owner_and_exact_barycentric_serialization(self) -> None:
        record = canonical_point_record(
            edge=(7, 2),
            tau=Fraction(1, 2),
            phi={2: Fraction(1, 4), 7: Fraction(3, 4)},
            incident_faces={(2, 7): (12, 11)},
            collar_faces={11, 12},
            face_loops={11: (7, 5, 2), 12: (7, 2, 9)},
        )
        expected = {
            "edge": [2, 7],
            "owner_face": 11,
            "owner_triangle_vertices": [2, 7, 5],
            "t": [1, 2],
            "barycentric": [[1, 2], [1, 2], [0, 1]],
        }
        self.assertEqual(record, expected)
        self.assertEqual(
            compact_json(record),
            b'{"barycentric":[[1,2],[1,2],[0,1]],"edge":[2,7],"owner_face":11,"owner_triangle_vertices":[2,7,5],"t":[1,2]}',
        )
        self.assertEqual(
            compact_sha256(record),
            "37a29886cf26cd32c14c4d660c06bdf86d2120a4d72bb2ccd5bc6982d050faea",
        )

    def test_06_cyclic_triangle_canonicalization_preserves_winding(self) -> None:
        self.assertEqual(canonical_triangle((7, 5, 2)), (2, 7, 5))
        self.assertEqual(canonical_triangle((7, 2, 5)), (2, 5, 7))
        self.assertNotEqual(
            canonical_triangle((7, 5, 2)), canonical_triangle((7, 2, 5))
        )

    def test_07_exterior_or_d2_adjacent_crossed_edge_fails_closed(self) -> None:
        collar = {11, 12, 13}
        incident = {
            (2, 7): (11, 12),
            (7, 9): (12, 13),
            (4, 5): (13, 99),
            (1, 2): (7, 11),
        }
        self.assertEqual(
            validate_crossed_edge_ledger({(2, 7), (7, 9)}, incident, collar),
            {11, 12, 13},
        )
        with self.assertRaisesRegex(ValueError, "D4-exterior"):
            validate_crossed_edge_ledger({(4, 5)}, incident, collar)
        with self.assertRaisesRegex(ValueError, "D4-exterior"):
            validate_crossed_edge_ledger({(1, 2)}, incident, collar)

    def test_08_body_frame_is_fixed_and_degeneracy_fails_closed(self) -> None:
        matrix = (
            (0.009523809887468815, 0.0, 0.0),
            (0.0, 0.00952381081879139, -1.6055943241610748e-09),
            (0.0, 1.6055943241610748e-09, 0.00952381081879139),
        )
        u, v, n = chart_frame(matrix)
        self.assertAlmostEqual(u[0], 1.0, places=15)
        self.assertAlmostEqual(u[1], 0.0, places=15)
        self.assertAlmostEqual(u[2], 0.0, places=15)
        self.assertGreater(n[2] * -1.0, 0.999999999)
        self.assertLess(abs(dot(u, v)), 1e-12)
        self.assertLess(abs(dot(u, n)), 1e-12)
        self.assertLess(abs(dot(v, n)), 1e-12)
        recorded_d2_normal = (
            -0.06707893400904828,
            -0.18044577914607934,
            -0.9812949288570557,
        )
        self.assertGreaterEqual(dot(n, recorded_d2_normal), 0.95)
        with self.assertRaisesRegex(ValueError, "degenerate matrix"):
            chart_frame(((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)))

    def test_09_domain_hashes_seed_containment_and_seam_distance_remain_exact(self) -> None:
        report = json.loads(REPAIR_DOMAIN.read_text(encoding="utf-8"))
        domains = {row["face_ring_expansion"]: row for row in report["domains"]}
        d2_faces = set(domains[2]["face_indices"])
        d4_faces = set(domains[4]["face_indices"])
        collar = sorted(d4_faces - d2_faces)
        self.assertEqual(len(collar), 64)
        self.assertEqual(
            compact_sha256(collar),
            "0fab4f296d7b234044e0651a8c10a08cabf7c784510c0a720085e2e21c1dd25b",
        )
        self.assertEqual(
            compact_sha256(domains[4]["boundary_edges"]),
            "ddc197b0b762b849170963bab5dcd5a5c0fe930323ce14f09fcbf2a42aa7349f",
        )
        self.assertTrue(set(report["exact_collision"]["seed_face_indices"]) <= d2_faces)
        self.assertFalse(domains[4]["touches_global_34_vertex_seam"])
        self.assertGreaterEqual(domains[4]["minimum_vertex_ring_distance_from_global_seam"], 4)

    def test_10_no_runtime_package_or_blender_was_created(self) -> None:
        allowed_static_records = {
            "LOCAL_TRANSITION_CUT_EXECUTION_CONTRACT_STATIC_PROPOSAL.md",
            "INDEPENDENT_STATIC_AUDIT.md",
            "CHECKPOINT.md",
        }
        actual = {path.name for path in PACKAGE.iterdir()}
        self.assertIn("LOCAL_TRANSITION_CUT_EXECUTION_CONTRACT_STATIC_PROPOSAL.md", actual)
        self.assertTrue(actual <= allowed_static_records)
        self.assertTrue(all((PACKAGE / name).is_file() for name in actual))
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)
        attempt47_text = ATTEMPT47.read_text(encoding="utf-8")
        self.assertIn("Attempt 47 is closed and must never be retried", attempt47_text)
        self.assertIn("No source Blend was opened", attempt47_text)


if __name__ == "__main__":
    unittest.main()
