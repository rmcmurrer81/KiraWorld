from __future__ import annotations

import collections
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static/"
    "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_CONTRACT.json"
)


class IntrinsicContractError(ValueError):
    """Raised when a sealed static input violates the intrinsic contract."""


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_edge(first: int, second: int) -> tuple[int, int]:
    if first == second:
        raise IntrinsicContractError("edge endpoints must differ")
    return (first, second) if first < second else (second, first)


def cycle_edges(cycle: Sequence[int]) -> set[tuple[int, int]]:
    if len(cycle) < 3 or len(set(cycle)) != len(cycle):
        raise IntrinsicContractError("cycle must have at least three unique vertices")
    return {
        canonical_edge(cycle[index], cycle[(index + 1) % len(cycle)])
        for index in range(len(cycle))
    }


def canonical_cycle(cycle: Sequence[int]) -> list[int]:
    values = list(cycle)
    if len(values) < 3 or len(set(values)) != len(values):
        raise IntrinsicContractError("cannot canonicalize an invalid cycle")
    minimum = min(values)
    start = values.index(minimum)
    forward = values[start:] + values[:start]
    reversed_values = list(reversed(values))
    reverse_start = reversed_values.index(minimum)
    reverse = reversed_values[reverse_start:] + reversed_values[:reverse_start]
    return min(forward, reverse)


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "kira.avatar.r24.intrinsic_curved_annulus_structured_retopology.v1":
        raise IntrinsicContractError("unexpected intrinsic contract schema")
    return value


def validate_immutable_bindings(
    contract: Mapping[str, object], *, verify_hashes: bool = True
) -> dict[str, Path]:
    bindings = contract.get("immutable_bindings")
    if not isinstance(bindings, dict) or not bindings:
        raise IntrinsicContractError("immutable bindings are missing")
    resolved: dict[str, Path] = {}
    for name, raw in bindings.items():
        if not isinstance(raw, dict):
            raise IntrinsicContractError(f"binding {name!r} is not an object")
        path = ROOT / str(raw.get("path", ""))
        if not path.is_file():
            raise IntrinsicContractError(f"binding {name!r} is not a file")
        if path.stat().st_size != int(raw.get("bytes", -1)):
            raise IntrinsicContractError(f"binding {name!r} byte count changed")
        if verify_hashes and sha256_file(path) != raw.get("sha256"):
            raise IntrinsicContractError(f"binding {name!r} hash changed")
        resolved[str(name)] = path
    return resolved


def parse_genitalia_source_topology(
    path: Path,
) -> tuple[list[tuple[int, int, int]], int]:
    data = path.read_bytes()
    if len(data) < 20:
        raise IntrinsicContractError("truncated GLB")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise IntrinsicContractError("unexpected GLB header")

    offset = 12
    json_chunk: bytes | None = None
    bin_chunk: bytes | None = None
    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + chunk_length]
        if len(chunk) != chunk_length:
            raise IntrinsicContractError("truncated GLB chunk")
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            json_chunk = chunk
        elif chunk_type == 0x004E4942:
            bin_chunk = chunk
    if offset != len(data) or json_chunk is None or bin_chunk is None:
        raise IntrinsicContractError("missing GLB JSON or BIN chunk")

    document = json.loads(json_chunk)
    matching = [
        mesh
        for mesh in document["meshes"]
        if mesh.get("name") == "Ariel_Mesh_Genitalia_0"
    ]
    if len(matching) != 1 or len(matching[0]["primitives"]) != 1:
        raise IntrinsicContractError("source mesh identity is not unique")
    primitive = matching[0]["primitives"][0]
    if primitive.get("mode", 4) != 4:
        raise IntrinsicContractError("source primitive is not triangles")

    accessor = document["accessors"][primitive["indices"]]
    if accessor["type"] != "SCALAR":
        raise IntrinsicContractError("index accessor is not scalar")
    formats = {5121: "B", 5123: "H", 5125: "I"}
    component_type = accessor["componentType"]
    if component_type not in formats:
        raise IntrinsicContractError("unsupported index component type")
    fmt = formats[component_type]
    item_size = struct.calcsize("<" + fmt)
    view = document["bufferViews"][accessor["bufferView"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", item_size)
    if stride < item_size:
        raise IntrinsicContractError("invalid index stride")
    indices = [
        struct.unpack_from("<" + fmt, bin_chunk, start + index * stride)[0]
        for index in range(accessor["count"])
    ]
    if len(indices) % 3:
        raise IntrinsicContractError("triangle index count is not divisible by three")
    faces = [
        tuple(indices[index : index + 3])
        for index in range(0, len(indices), 3)
    ]
    if any(len(set(face)) != 3 for face in faces):
        raise IntrinsicContractError("degenerate source triangle")
    position_accessor = document["accessors"][primitive["attributes"]["POSITION"]]
    return faces, int(position_accessor["count"])


def edge_incidence(
    faces: Sequence[Sequence[int]], selected: Iterable[int] | None = None
) -> dict[tuple[int, int], list[int]]:
    rows: dict[tuple[int, int], list[int]] = collections.defaultdict(list)
    indices = range(len(faces)) if selected is None else sorted(set(selected))
    for face_index in indices:
        first, second, third = faces[face_index]
        for edge in (
            canonical_edge(first, second),
            canonical_edge(second, third),
            canonical_edge(third, first),
        ):
            rows[edge].append(face_index)
    return dict(rows)


def face_component_count(
    selected: set[int], incidence: Mapping[tuple[int, int], Sequence[int]]
) -> int:
    adjacency = {face_index: set() for face_index in selected}
    for incident in incidence.values():
        if len(incident) == 2:
            first, second = incident
            adjacency[first].add(second)
            adjacency[second].add(first)
    seen: set[int] = set()
    count = 0
    for start in sorted(selected):
        if start in seen:
            continue
        count += 1
        queue = collections.deque([start])
        seen.add(start)
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return count


def boundary_cycles(boundary: Iterable[tuple[int, int]]) -> list[list[int]]:
    edges = {canonical_edge(*edge) for edge in boundary}
    adjacency: dict[int, set[int]] = collections.defaultdict(set)
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise IntrinsicContractError("boundary is not a disjoint union of cycles")

    remaining = set(edges)
    cycles: list[list[int]] = []
    while remaining:
        start_edge = min(remaining)
        start = min(start_edge)
        first_neighbor = min(adjacency[start])
        cycle = [start]
        previous = start
        current = first_neighbor
        while current != start:
            if current in cycle:
                raise IntrinsicContractError("boundary revisited a non-start vertex")
            cycle.append(current)
            candidates = sorted(adjacency[current] - {previous})
            if len(candidates) != 1:
                raise IntrinsicContractError("boundary traversal is ambiguous")
            previous, current = current, candidates[0]
            if len(cycle) > len(edges):
                raise IntrinsicContractError("boundary traversal exceeded edge count")
        canonical = canonical_cycle(cycle)
        used = cycle_edges(canonical)
        if not used <= remaining:
            raise IntrinsicContractError("boundary cycles share an edge")
        remaining -= used
        cycles.append(canonical)
    return sorted(cycles)


def topology_summary(
    faces: Sequence[Sequence[int]], selected: set[int]
) -> dict[str, object]:
    incidence = edge_incidence(faces, selected)
    if any(len(rows) > 2 for rows in incidence.values()):
        raise IntrinsicContractError("selected topology is nonmanifold")
    vertices = sorted(
        {vertex for face_index in selected for vertex in faces[face_index]}
    )
    edges = sorted(incidence)
    boundary = sorted(edge for edge, rows in incidence.items() if len(rows) == 1)
    cycles = boundary_cycles(boundary)
    return {
        "face_count": len(selected),
        "vertices": vertices,
        "edges": edges,
        "boundary_edges": boundary,
        "boundary_cycles": cycles,
        "face_component_count": face_component_count(selected, incidence),
        "euler_characteristic": len(vertices) - len(edges) + len(selected),
    }


def _graph_component_count(adjacency: Mapping[object, set[object]]) -> int:
    seen: set[object] = set()
    count = 0
    for start in sorted(adjacency, key=repr):
        if start in seen:
            continue
        count += 1
        queue = collections.deque([start])
        seen.add(start)
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency[current], key=repr):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return count


def reconstruct_exact_domains(
    contract: Mapping[str, object], bindings: Mapping[str, Path]
) -> dict[str, object]:
    faces, vertex_count = parse_genitalia_source_topology(bindings["licensed_source_glb"])
    report = json.loads(bindings["repair_domain"].read_text(encoding="utf-8"))
    topology = contract["exact_topology"]
    domains = {int(row["face_ring_expansion"]): row for row in report["domains"]}
    d2 = set(domains[2]["face_indices"])
    d4 = set(domains[4]["face_indices"])
    additions = set(topology["estar_forced_addition_faces"])
    estar = d4 | additions
    collar = estar - d2
    outside = set(range(len(faces))) - estar

    d2_summary = topology_summary(faces, d2)
    collar_summary = topology_summary(faces, collar)
    estar_summary = topology_summary(faces, estar)
    inner_cycle = list(topology["d2_inner_cycle"])
    outer_cycle = list(topology["estar_outer_cycle"])

    checks = {
        "source_vertex_count": vertex_count == topology["source_vertex_count"],
        "source_face_count": len(faces) == topology["source_face_count"],
        "d2_face_count": len(d2) == topology["d2_face_count"],
        "d2_face_hash": compact_sha256(sorted(d2)) == topology["d2_face_sha256"],
        "d2_disk": d2_summary["face_component_count"] == 1
        and d2_summary["euler_characteristic"] == 1
        and d2_summary["boundary_cycles"] == [inner_cycle],
        "collar_face_count": len(collar) == topology["collar_face_count"],
        "collar_face_hash": compact_sha256(sorted(collar))
        == topology["collar_face_sha256"],
        "collar_annulus": collar_summary["face_component_count"] == 1
        and collar_summary["euler_characteristic"] == 0
        and collar_summary["boundary_cycles"] == sorted([inner_cycle, outer_cycle]),
        "collar_all_vertices_on_boundaries": len(collar_summary["vertices"])
        == len(inner_cycle) + len(outer_cycle)
        and set(collar_summary["vertices"]) == set(inner_cycle) | set(outer_cycle),
        "estar_face_count": len(estar) == topology["estar_face_count"],
        "estar_face_hash": compact_sha256(sorted(estar)) == topology["estar_face_sha256"],
        "estar_disk": estar_summary["face_component_count"] == 1
        and estar_summary["euler_characteristic"] == 1
        and estar_summary["boundary_cycles"] == [outer_cycle],
        "estar_vertex_partition": set(estar_summary["vertices"])
        == set(d2_summary["vertices"]) | set(outer_cycle)
        and not (set(d2_summary["vertices"]) & set(outer_cycle)),
        "collar_vertex_partition": set(collar_summary["vertices"])
        == set(inner_cycle) | set(outer_cycle)
        and not (set(inner_cycle) & set(outer_cycle)),
        "d2_is_exact_estar_interior": set(d2_summary["vertices"])
        == set(estar_summary["vertices"]) - set(outer_cycle),
        "outside_face_count": len(outside) == topology["outside_face_count"],
        "outside_face_hash": compact_sha256(sorted(outside))
        == topology["outside_face_sha256"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise IntrinsicContractError("exact domain reconstruction failed: " + ",".join(failed))

    full_incidence = edge_incidence(faces)
    exterior_adjacent: set[int] = set()
    for edge in estar_summary["boundary_edges"]:
        incident = full_incidence[edge]
        if len(incident) != 2:
            raise IntrinsicContractError("E* boundary lacks two complete source owners")
        inside = [face for face in incident if face in estar]
        exterior = [face for face in incident if face not in estar]
        if len(inside) != 1 or len(exterior) != 1:
            raise IntrinsicContractError("E* boundary does not separate exact exterior")
        exterior_adjacent.add(exterior[0])
    if len(exterior_adjacent) != topology["exterior_adjacent_face_count"]:
        raise IntrinsicContractError("exterior-adjacent face count changed")
    if compact_sha256(sorted(exterior_adjacent)) != topology["exterior_adjacent_face_sha256"]:
        raise IntrinsicContractError("exterior-adjacent face identity changed")

    seam = set(report["global_interface"]["boundary_vertex_indices"])
    expected_seam = set(contract["protection_gates"]["global_interface_vertex_indices"])
    if seam != expected_seam or set(estar_summary["vertices"]) & seam:
        raise IntrinsicContractError("E* and the immutable global interface are not disjoint")
    graph: dict[int, set[int]] = collections.defaultdict(set)
    for first, second in full_incidence:
        graph[first].add(second)
        graph[second].add(first)
    distances = {vertex: 0 for vertex in seam}
    queue = collections.deque(sorted(seam))
    while queue:
        current = queue.popleft()
        for neighbor in sorted(graph[current]):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    seam_rings = min(distances[vertex] for vertex in estar_summary["vertices"])
    if seam_rings < contract["protection_gates"]["minimum_global_interface_rings"]:
        raise IntrinsicContractError("E* approaches the immutable global interface")

    return {
        "faces": faces,
        "full_incidence": full_incidence,
        "d2": d2,
        "d4": d4,
        "estar": estar,
        "collar": collar,
        "outside": outside,
        "exterior_adjacent": exterior_adjacent,
        "d2_summary": d2_summary,
        "collar_summary": collar_summary,
        "estar_summary": estar_summary,
        "inner_cycle": inner_cycle,
        "outer_cycle": outer_cycle,
        "minimum_seam_rings": seam_rings,
    }


def _fraction(value: Sequence[int]) -> Fraction:
    if len(value) != 2:
        raise IntrinsicContractError("fraction must contain numerator and denominator")
    return Fraction(int(value[0]), int(value[1]))


def _validate_barycentric_record(
    record: Mapping[str, object],
    face_field: str,
    triangle_field: str,
    barycentric_field: str,
    faces: Sequence[Sequence[int]],
    t: Fraction,
) -> None:
    face_index = int(record[face_field])
    triangle = tuple(int(value) for value in record[triangle_field])
    source_triangle = tuple(int(value) for value in faces[face_index])
    same_stored_winding = triangle in (
        source_triangle,
        source_triangle[1:] + source_triangle[:1],
        source_triangle[2:] + source_triangle[:2],
    )
    if not same_stored_winding:
        raise IntrinsicContractError("stored triangle order changed")
    weights = [_fraction(value) for value in record[barycentric_field]]
    if len(weights) != 3 or sum(weights, Fraction(0)) != 1:
        raise IntrinsicContractError("barycentric weights do not sum exactly to one")
    edge = tuple(int(value) for value in record["edge"])
    expected = {edge[0]: Fraction(1) - t, edge[1]: t}
    for vertex, weight in zip(triangle, weights, strict=True):
        if weight != expected.get(vertex, Fraction(0)):
            raise IntrinsicContractError("barycentric weights do not bind the source edge")


def evaluate_intrinsic_candidate(
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
    domains: Mapping[str, object],
) -> dict[str, object]:
    failures: list[str] = []
    details: dict[str, object] = {}
    try:
        faces: Sequence[Sequence[int]] = domains["faces"]
        collar: set[int] = set(domains["collar"])
        inner = set(domains["inner_cycle"])
        outer = set(domains["outer_cycle"])
        collar_vertices = set(domains["collar_summary"]["vertices"])
        if inner & outer or inner | outer != collar_vertices:
            raise IntrinsicContractError("annular boundary label partition changed")
        labels = {vertex: 0 for vertex in inner}
        labels.update({vertex: 1 for vertex in outer})

        allowed_retired = set(contract["retired_planar_gates"])
        reported_failures = set(candidate.get("failure_names", []))
        unexpected = sorted(reported_failures - allowed_retired)
        if unexpected:
            failures.append("nonplanar_parent_failure:" + ",".join(unexpected))

        points: dict[tuple[int, ...], Mapping[str, object]] = {}
        level = _fraction(candidate["level"])
        if not 0 < level < 1:
            raise IntrinsicContractError("candidate level is not strictly interior")
        for raw in candidate["actual_point_records"]:
            key = tuple(int(value) for value in raw["key"])
            if key in points:
                raise IntrinsicContractError("candidate point key is duplicated")
            edge = tuple(int(value) for value in raw["edge"])
            if len(edge) != 2 or canonical_edge(*edge) != edge:
                raise IntrinsicContractError("candidate edge is not canonical")
            if edge[0] not in labels or edge[1] not in labels or labels[edge[0]] == labels[edge[1]]:
                raise IntrinsicContractError("candidate point is not on a mixed annular edge")
            t = _fraction(raw["t"])
            if not 0 < t < 1:
                raise IntrinsicContractError("candidate point is not open-edge")
            if Fraction(labels[edge[0]]) * (1 - t) + Fraction(labels[edge[1]]) * t != level:
                raise IntrinsicContractError("candidate point does not satisfy exact label equation")
            incident = sorted(
                face for face in domains["full_incidence"][edge] if face in collar
            )
            if len(incident) != 2 or incident != sorted(raw["incident_source_faces"]):
                raise IntrinsicContractError("candidate point lacks two exact collar owners")
            if {int(raw["owner_face"]), int(raw["other_face"])} != set(incident):
                raise IntrinsicContractError("candidate owner faces changed")
            _validate_barycentric_record(
                raw, "owner_face", "owner_triangle", "owner_barycentric", faces, t
            )
            _validate_barycentric_record(
                raw,
                "other_face",
                "other_triangle_stored_order",
                "other_barycentric",
                faces,
                t,
            )
            if raw.get("exact_label_residual") != [0, 1] or not raw.get(
                "exact_label_equation_verified"
            ):
                raise IntrinsicContractError("exact label provenance is not verified")
            points[key] = raw

        graph: dict[tuple[int, ...], set[tuple[int, ...]]] = {
            key: set() for key in points
        }
        segment_faces: list[int] = []
        for segment in candidate["segment_records"]:
            if segment.get("local_failures"):
                raise IntrinsicContractError("candidate segment reports a local failure")
            face_index = int(segment["source_face_index"])
            keys = [tuple(int(value) for value in row) for row in segment["point_keys"]]
            if face_index not in collar or len(keys) != 2 or keys[0] == keys[1]:
                raise IntrinsicContractError("candidate segment is not a valid collar chord")
            if any(key not in points for key in keys):
                raise IntrinsicContractError("candidate segment references an unknown point")
            face_vertices = set(faces[face_index])
            if any(not set(points[key]["edge"]) <= face_vertices for key in keys):
                raise IntrinsicContractError("candidate segment point is not owned by its face")
            graph[keys[0]].add(keys[1])
            graph[keys[1]].add(keys[0])
            segment_faces.append(face_index)

        mixed_faces = {
            face_index
            for face_index in collar
            if {labels[vertex] for vertex in faces[face_index]} == {0, 1}
        }
        if len(segment_faces) != len(set(segment_faces)) or set(segment_faces) != mixed_faces:
            raise IntrinsicContractError("candidate does not cut every and only mixed collar face once")
        if not graph or any(len(neighbors) != 2 for neighbors in graph.values()):
            raise IntrinsicContractError("candidate graph is not degree two")
        if _graph_component_count(graph) != 1:
            raise IntrinsicContractError("candidate graph is not one closed component")

        components = candidate.get("component_records", [])
        if len(components) != 1:
            raise IntrinsicContractError("candidate does not contain exactly one component record")
        component = components[0]
        ordered = [tuple(int(value) for value in row) for row in component["ordered_loop"]]
        if len(ordered) != len(points) or len(set(ordered)) != len(points) or set(ordered) != set(points):
            raise IntrinsicContractError("ordered loop does not cover every point exactly once")
        if any(ordered[(index + 1) % len(ordered)] not in graph[ordered[index]] for index in range(len(ordered))):
            raise IntrinsicContractError("ordered loop is not the segment graph cycle")
        if set(component["carrier_faces"]) != mixed_faces:
            raise IntrinsicContractError("carrier-face ledger changed")
        if set(component["split_collar_face_ledger"]) != mixed_faces:
            raise IntrinsicContractError("split-face ledger changed")
        if component["split_ledger_outside_collar"] or component[
            "exterior_adjacent_faces_crossed_or_split"
        ]:
            raise IntrinsicContractError("candidate touches protected exterior geometry")

        side_graphs: dict[int, dict[int, set[int]]] = {0: {}, 1: {}}
        for face_index in collar:
            face_labels = {labels[vertex] for vertex in faces[face_index]}
            for side in face_labels:
                side_graphs[side][face_index] = set()
        collar_incidence = edge_incidence(faces, collar)
        for edge, incident in collar_incidence.items():
            edge_labels = {labels[vertex] for vertex in edge}
            if len(incident) == 2:
                for side in edge_labels:
                    first, second = incident
                    if first in side_graphs[side] and second in side_graphs[side]:
                        side_graphs[side][first].add(second)
                        side_graphs[side][second].add(first)

        side_counts = {
            side: _graph_component_count(side_graphs[side]) for side in (0, 1)
        }
        if side_counts != {0: 1, 1: 1}:
            raise IntrinsicContractError("candidate does not divide the annulus into two connected sides")
        inner_edges = cycle_edges(domains["inner_cycle"])
        outer_edges = cycle_edges(domains["outer_cycle"])
        collar_boundary = {
            edge for edge, incident in collar_incidence.items() if len(incident) == 1
        }
        if collar_boundary != inner_edges | outer_edges:
            raise IntrinsicContractError("collar boundary identity changed")
        if any({labels[v] for v in edge} != {0} for edge in inner_edges):
            raise IntrinsicContractError("inner boundary label changed")
        if any({labels[v] for v in edge} != {1} for edge in outer_edges):
            raise IntrinsicContractError("outer boundary label changed")

        details = {
            "point_count": len(points),
            "segment_count": len(segment_faces),
            "mixed_carrier_face_count": len(mixed_faces),
            "intrinsic_loop_component_count": 1,
            "intrinsic_loop_every_degree": 2,
            "inner_side_component_count": side_counts[0],
            "outer_side_component_count": side_counts[1],
            "inner_side_touches_only_d2_boundary": True,
            "outer_side_touches_only_estar_boundary": True,
            "d2_plus_inner_side_is_one_disk": True,
            "projected_geometry_used": False,
            "world_planarity_used": False,
            "retired_planar_failures_observed": sorted(reported_failures & allowed_retired),
        }
    except Exception as exc:  # fail closed for malformed or drifted evidence
        failures.append(f"intrinsic_evaluation_error:{type(exc).__name__}:{exc}")

    return {
        "schema": "kira.avatar.r24.intrinsic_annulus_candidate_evaluation.v1",
        "level": candidate.get("level"),
        "intrinsic_eligible": not failures,
        "failure_names": failures,
        "details": details,
    }


def evaluate_runtime_family(
    contract: Mapping[str, object], domains: Mapping[str, object], bindings: Mapping[str, Path]
) -> dict[str, object]:
    runtime = json.loads(bindings["annular_runtime_result"].read_text(encoding="utf-8"))
    terminal = contract["terminal_parent_result"]
    solver = runtime.get("solver_summary", {})
    if runtime.get("status") != terminal["status"]:
        raise IntrinsicContractError("annular runtime status changed")
    if (
        solver.get("candidate_record_count") != terminal["candidate_record_count"]
        or solver.get("eligible_candidate_count") != terminal["eligible_candidate_count"]
        or solver.get("selected_eligible_candidate") is not terminal["selected_eligible_candidate"]
        or solver.get("finite_termination_reached") is not True
        or solver.get("mesh_mutation_used") is not False
    ):
        raise IntrinsicContractError("annular terminal solver truth changed")
    candidates = solver["candidate_records"]
    expected_failures = terminal["identical_candidate_failure_names"]
    if any(candidate.get("failure_names") != expected_failures for candidate in candidates):
        raise IntrinsicContractError("annular terminal failure distribution changed")
    evaluations = [
        evaluate_intrinsic_candidate(candidate, contract, domains) for candidate in candidates
    ]
    return {
        "schema": "kira.avatar.r24.intrinsic_annulus_family_evaluation.v1",
        "source_candidate_count": len(candidates),
        "intrinsic_eligible_count": sum(row["intrinsic_eligible"] for row in evaluations),
        "all_intrinsically_separating": all(row["intrinsic_eligible"] for row in evaluations),
        "evaluations": evaluations,
        "projected_geometry_used": False,
        "world_planarity_used": False,
    }


def evaluate_structured_retopology_evidence(
    evidence: Mapping[str, object] | None, contract: Mapping[str, object]
) -> dict[str, object]:
    """Fail-closed gate check for a future measured retopology evidence record.

    This does not inspect a mesh. A future mutation worker must compute every
    field from the candidate and bind its artifact hash. The static package
    deliberately supplies no such record, so the current result is ineligible.
    """

    failures: list[str] = []
    if not isinstance(evidence, Mapping):
        return {
            "schema": "kira.avatar.r24.structured_retopology_evidence_gate.v1",
            "eligible": False,
            "failure_names": ["measured_candidate_evidence_absent"],
        }
    required_sections = (
        "artifact",
        "topology",
        "scope",
        "provenance",
        "attributes",
        "rig",
        "geometry",
        "intersections",
        "global_interface",
        "truth",
    )
    for section in required_sections:
        if not isinstance(evidence.get(section), Mapping):
            failures.append(f"missing_section:{section}")
    if failures:
        return {
            "schema": "kira.avatar.r24.structured_retopology_evidence_gate.v1",
            "eligible": False,
            "failure_names": failures,
        }

    gates = contract["future_measured_candidate_gates"]
    topology = evidence["topology"]
    scope = evidence["scope"]
    provenance = evidence["provenance"]
    attributes = evidence["attributes"]
    rig = evidence["rig"]
    geometry = evidence["geometry"]
    intersections = evidence["intersections"]
    interface = evidence["global_interface"]
    truth = evidence["truth"]
    artifact = evidence["artifact"]

    artifact_path: Path | None = None
    artifact_file_exact = False
    try:
        raw_artifact_path = str(artifact.get("path", ""))
        artifact_path = (ROOT / raw_artifact_path).resolve()
        artifact_path.relative_to(ROOT.resolve())
        artifact_file_exact = (
            artifact.get("kind") == "measured_private_candidate_blend"
            and artifact_path.is_file()
            and artifact_path.suffix.lower() == ".blend"
            and artifact_path.stat().st_size == int(artifact.get("bytes", -1))
            and sha256_file(artifact_path) == artifact.get("sha256")
        )
    except (ValueError, OSError, TypeError):
        artifact_file_exact = False

    exact_checks = {
        "artifact_bound": artifact_file_exact,
        "one_disk": topology.get("component_count") == 1
        and topology.get("euler_characteristic") == 1
        and topology.get("boundary_cycle_count") == 1
        and topology.get("manifold") is True
        and topology.get("orientable") is True,
        "topology_parity": topology.get("outer_boundary_edge_count")
        == contract["structured_topology_parity"]["fixed_outer_boundary_edge_count"]
        and topology.get("outer_boundary_edge_split_count") == 0
        and isinstance(topology.get("odd_sided_face_count"), int)
        and topology.get("odd_sided_face_count", 0) > 0
        and topology.get("odd_sided_face_count", 0) % 2 == 1
        and isinstance(topology.get("ordered_stitch_schedule_sha256"), str)
        and len(topology.get("ordered_stitch_schedule_sha256", "")) == 64,
        "outer_cycle_exact": topology.get("outer_boundary_cycle")
        == contract["exact_topology"]["estar_outer_cycle"],
        "scope_exact": scope.get("consumed_source_face_count")
        == contract["exact_topology"]["estar_face_count"]
        and scope.get("consumed_source_face_sha256")
        == contract["exact_topology"]["estar_face_sha256"]
        and scope.get("consumed_d2_face_count")
        == contract["exact_topology"]["d2_face_count"]
        and scope.get("consumed_d2_face_sha256")
        == contract["exact_topology"]["d2_face_sha256"]
        and scope.get("consumed_collar_face_count")
        == contract["exact_topology"]["collar_face_count"]
        and scope.get("consumed_collar_face_sha256")
        == contract["exact_topology"]["collar_face_sha256"]
        and scope.get("collar_disposition_record_count")
        == contract["exact_topology"]["collar_face_count"]
        and scope.get("changed_face_count_outside_estar") == 0
        and scope.get("changed_exterior_adjacent_face_count") == 0,
        "provenance_complete": provenance.get("all_new_vertices_source_bound") is True
        and provenance.get("all_barycentric_weights_finite_normalized") is True
        and provenance.get("unbound_world_space_vertex_count") == 0,
        "attributes_preserved": attributes.get("changed_uv_record_count_outside_estar") == 0
        and attributes.get("changed_normal_record_count_outside_estar") == 0
        and attributes.get("material_index") == gates["preserve_material_index"]
        and attributes.get("changed_shape_key_record_count_outside_estar") == 0
        and attributes.get("estar_outer_point_edge_face_corner_exact") is True,
        "rig_preserved": rig.get("armature_identity_exact") is True
        and rig.get("changed_weight_record_count_outside_estar") == 0
        and rig.get("all_new_weights_interpolated_normalized") is True,
        "triangle_quality": geometry.get("minimum_triangle_angle_degrees", -1)
        >= gates["minimum_render_triangle_angle_degrees"]
        and geometry.get("minimum_triangle_area_m2", -1)
        >= gates["minimum_render_triangle_area_m2"]
        and geometry.get("new_interior_vertex_count", gates["maximum_new_interior_vertices"] + 1)
        <= gates["maximum_new_interior_vertices"]
        and geometry.get("degenerate_triangle_count") == 0,
        "intersection_gate": intersections.get("standalone_repaired_patch_pairs") == 0
        and intersections.get("post_graft_patch_related_pairs") == 0
        and intersections.get("new_noninherited_pairs") == 0
        and intersections.get("inherited_nonpatch_pairs")
        == gates["inherited_nonpatch_exact_pairs"],
        "global_interface_exact": interface.get("coordinate_delta_m")
        == gates["global_interface_coordinate_delta_m"]
        and interface.get("unique_weld_count") == gates["global_interface_unique_weld_count"]
        and interface.get("world_coordinate_sha256")
        == contract["protection_gates"]["global_interface_world_coordinate_sha256"],
        "private_inactive_truth": truth.get("private") is True
        and truth.get("inactive") is True
        and truth.get("unassigned") is True
        and truth.get("unpublished") is True
        and truth.get("owner_approval_claimed") is False,
    }
    failures.extend(sorted(name for name, passed in exact_checks.items() if not passed))
    return {
        "schema": "kira.avatar.r24.structured_retopology_evidence_gate.v1",
        "eligible": not failures,
        "failure_names": failures,
    }


def static_evaluation(path: Path = DEFAULT_CONTRACT) -> dict[str, object]:
    contract = load_contract(path)
    bindings = validate_immutable_bindings(contract)
    domains = reconstruct_exact_domains(contract, bindings)
    family = evaluate_runtime_family(contract, domains, bindings)
    future = evaluate_structured_retopology_evidence(None, contract)
    return {
        "schema": "kira.avatar.r24.intrinsic_curved_annulus_static_evaluation.v1",
        "status": "STATIC_INTRINSIC_TOPOLOGY_PASS_FUTURE_RETOPOLOGY_NOT_MEASURED",
        "domain": {
            "d2_face_count": len(domains["d2"]),
            "collar_face_count": len(domains["collar"]),
            "estar_face_count": len(domains["estar"]),
            "outside_face_count": len(domains["outside"]),
            "outer_cycle_count": len(domains["outer_cycle"]),
            "minimum_seam_rings": domains["minimum_seam_rings"],
        },
        "family": family,
        "future_measured_candidate": future,
        "blender_used": False,
        "mesh_mutated": False,
        "body_repair_claimed": False,
    }


def main() -> int:
    print(json.dumps(static_evaluation(), sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
