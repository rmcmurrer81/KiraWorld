"""Append-only static revision 02 of the R24 attempt_01 diagnostic.

This module deliberately layers two narrow corrections over the preserved
Attempt 01 worker: one shared protected-tree inventory implementation and an
actual opposite-triangle barycentric reconstruction.  It remains read-only,
no-save, no-render, one-shot, and unauthorised until a fresh independent audit.
"""

from __future__ import annotations

from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Sequence


sys.dont_write_bytecode = True
THIS_FILE = Path(__file__).resolve()
TOOLS = THIS_FILE.parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from r24_local_transition_canonical_inventory import (  # noqa: E402
    canonical_inventory,
    sha256_file as canonical_sha256_file,
)


BASE_WORKER = TOOLS / "blender_diagnose_kira_r24_local_transition_geometric_attempt01.py"
_SPEC = importlib.util.spec_from_file_location("r24_attempt01_preserved_worker", BASE_WORKER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load preserved Attempt 01 worker")
_BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)

for _name in dir(_BASE):
    if not _name.startswith("__"):
        globals().setdefault(_name, getattr(_BASE, _name))

DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_geometric_diagnostic_attempt_01_revision_02_static/"
    "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_REVISION02_CONFIG.json"
)
_BASE_LOAD_CONFIG = _BASE.load_config
_BASE_VALIDATE_CONFIG = _BASE.validate_config
_BASE_VERIFY_IMMUTABLE = _BASE.verify_immutable_bindings
_BASE_EVALUATE_LEVEL = _BASE.evaluate_level
_BASE_RUN = _BASE.run


def _project_file(binding: dict[str, object]) -> Path:
    path = (ROOT / str(binding["path"])).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(f"revision binding escapes project: {binding['path']}") from exc
    return path


def _verify_revision_binding(name: str, binding: dict[str, object]) -> Path:
    path = _project_file(binding)
    if not path.is_file():
        raise RuntimeError(f"revision binding absent: {name}")
    if path.stat().st_size != int(binding["bytes"]):
        raise RuntimeError(f"revision binding byte count drifted: {name}")
    if canonical_sha256_file(path) != binding["sha256"]:
        raise RuntimeError(f"revision binding hash drifted: {name}")
    return path


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    revision = json.loads(path.read_text(encoding="utf-8"))
    if revision.get("schema") != (
        "kira.avatar.r24.local_transition_geometric_diagnostic."
        "attempt01.static_revision.v1"
    ):
        raise RuntimeError("revision-02 overlay schema drifted")
    for name in ("base_config", "base_worker", "attempt01_blocking_audit", "canonical_inventory_implementation"):
        _verify_revision_binding(name, revision[name])
    config = _BASE_LOAD_CONFIG(_project_file(revision["base_config"]))
    config["static_revision"] = int(revision["static_revision"])
    config["revision_status"] = revision["status"]
    config["revision_bindings"] = {
        name: revision[name]
        for name in ("base_config", "base_worker", "attempt01_blocking_audit", "canonical_inventory_implementation")
    }
    config["revision_corrections"] = revision["corrections"]
    config["launch_contract"]["worker"] = revision["replacement_worker"]
    config["launch_contract"]["wrapper"] = revision["replacement_wrapper"]
    if config["output_contract"]["root"] != revision["runtime_output_root"]:
        raise RuntimeError("revision attempted to redirect append-only output")
    if config["output_contract"]["runtime_cache_root"] != revision["runtime_cache_root"]:
        raise RuntimeError("revision attempted to redirect controlled cache")
    return config


def validate_config(config: dict[str, object]) -> None:
    _BASE_VALIDATE_CONFIG(config)
    if config.get("static_revision") != 2:
        raise RuntimeError("static revision identity drifted")
    corrections = config.get("revision_corrections", {})
    if not all(corrections.values()):
        raise RuntimeError("one or more revision-02 correction gates were disabled")


def verify_protected_inventories(config: dict[str, object]) -> list[dict[str, object]]:
    records = []
    for expected in config["protected_inventories"]:
        actual = canonical_inventory(ROOT, expected["root"])
        if actual != expected:
            raise RuntimeError(f"protected package inventory drifted: {expected['root']}")
        records.append(actual)
    return records


def verify_immutable_bindings(config: dict[str, object]) -> dict[str, object]:
    records = _BASE_VERIFY_IMMUTABLE(config)
    for name, binding in config["revision_bindings"].items():
        _verify_revision_binding(name, binding)
    verify_protected_inventories(config)
    return records


def exact_edge_barycentric_weights(
    triangle: Sequence[int], first: int, second: int, t: Fraction
) -> tuple[Fraction, Fraction, Fraction]:
    """Return exact weights in *triangle's actual vertex order*."""
    if len(triangle) != 3 or len(set(triangle)) != 3:
        raise ValueError("opposite source triangle is not a nondegenerate triangle")
    if first not in triangle or second not in triangle or first == second:
        raise ValueError("source edge is not contained by the opposite triangle")
    if not Fraction(0) < t < Fraction(1):
        raise ValueError("edge interpolation parameter is not strictly interior")
    by_vertex = {first: Fraction(1) - t, second: t}
    weights = tuple(by_vertex.get(vertex, Fraction(0)) for vertex in triangle)
    if (
        sum(weights, Fraction(0)) != Fraction(1)
        or any(weight < 0 or weight > 1 for weight in weights)
        or sum(weight == 0 for weight in weights) != 1
    ):
        raise ValueError("opposite-triangle exact barycentric proof failed")
    return weights


def reconstruct_triangle_point(
    triangle: Sequence[int],
    weights: Sequence[Fraction],
    coordinates: Sequence[Sequence[float]],
) -> tuple[float, float, float]:
    if len(triangle) != 3 or len(weights) != 3:
        raise ValueError("triangle reconstruction requires three vertices and weights")
    return tuple(
        math.fsum(float(weight) * float(coordinates[vertex][axis]) for vertex, weight in zip(triangle, weights))
        for axis in range(3)
    )


def verify_opposite_triangle_reconstructions(
    k: int,
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    full_incidence: dict[tuple[int, int], list[int]],
    collar: set[int],
    phi: dict[int, Fraction],
    config: dict[str, object],
) -> dict[str, object]:
    tau = Fraction(k, config["candidate_generator"]["tau_denominator"])
    tolerance = float(config["chart"]["barycentric_reconstruction_maximum_delta_m"])
    seen: set[tuple[int, int, int, int]] = set()
    maximum_owner_delta = 0.0
    maximum_other_delta = 0.0
    for face_index in sorted(collar):
        for first, second in triangle_edges(faces[face_index]):
            if not ((phi[first] < tau < phi[second]) or (phi[second] < tau < phi[first])):
                continue
            incident = sorted(full_incidence.get((first, second), []))
            if len(incident) != 2 or not set(incident) <= collar:
                raise ValueError("crossed edge lacks exactly two complete collar triangles")
            t = (tau - phi[first]) / (phi[second] - phi[first])
            key = (first, second, t.numerator, t.denominator)
            if key in seen:
                continue
            seen.add(key)
            owner_face = min(incident)
            other_face = incident[0] if incident[1] == owner_face else incident[1]
            owner_triangle = canonical_triangle(faces[owner_face])
            other_triangle = tuple(int(vertex) for vertex in faces[other_face])
            owner_bary = exact_edge_barycentric_weights(owner_triangle, first, second, t)
            other_bary = exact_edge_barycentric_weights(other_triangle, first, second, t)
            direct = vector_add(
                vector_scale(coordinates[first], float(Fraction(1) - t)),
                vector_scale(coordinates[second], float(t)),
            )
            owner_reconstruction = reconstruct_triangle_point(owner_triangle, owner_bary, coordinates)
            other_reconstruction = reconstruct_triangle_point(other_triangle, other_bary, coordinates)
            owner_delta = distance(direct, owner_reconstruction)
            other_delta = distance(direct, other_reconstruction)
            maximum_owner_delta = max(maximum_owner_delta, owner_delta)
            maximum_other_delta = max(maximum_other_delta, other_delta)
            if owner_delta > tolerance or other_delta > tolerance:
                raise ValueError("independent source-triangle reconstruction exceeded tolerance")
    return {
        "schema": "kira.avatar.r24.opposite_triangle_barycentric_proof.v1",
        "point_count": len(seen),
        "owner_triangle_maximum_direct_delta_m": maximum_owner_delta,
        "opposite_triangle_maximum_direct_delta_m": maximum_other_delta,
        "maximum_allowed_delta_m": tolerance,
        "actual_opposite_triangle_vertex_order_used": True,
        "exact_sum_range_and_one_zero_asserted": True,
        "direct_edge_interpolation_independently_compared": True,
    }


def evaluate_level(
    k,
    faces,
    coordinates,
    full_incidence,
    collar,
    d2_vertices,
    boundary_vertices,
    seed_faces,
    phi,
    frame,
    config,
    d2_boundary,
    envelope_adjacency,
):
    proof = verify_opposite_triangle_reconstructions(
        k, faces, coordinates, full_incidence, collar, phi, config
    )
    record = _BASE_EVALUATE_LEVEL(
        k,
        faces,
        coordinates,
        full_incidence,
        collar,
        d2_vertices,
        boundary_vertices,
        seed_faces,
        phi,
        frame,
        config,
        d2_boundary,
        envelope_adjacency,
    )
    record["opposite_triangle_barycentric_proof"] = proof
    return record


def run(config_path: Path) -> dict[str, object]:
    return _BASE_RUN(config_path)


# Patch only the preserved worker's global call sites used by its run/main.
_BASE.DEFAULT_CONFIG = DEFAULT_CONFIG
_BASE.__file__ = str(THIS_FILE)
_BASE.load_config = load_config
_BASE.validate_config = validate_config
_BASE.verify_immutable_bindings = verify_immutable_bindings
_BASE.evaluate_level = evaluate_level
_BASE.run = run


def main() -> None:
    _BASE.main()


if __name__ == "__main__":
    main()
