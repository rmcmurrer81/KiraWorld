from __future__ import annotations

import collections
import hashlib
import json
import struct
import sys
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_strict_separation_envelope"
)
PROPOSAL = PACKAGE / "STRICT_SEPARATION_ENVELOPE_STATIC_PROPOSAL.md"
PARENT_BOUNDARY = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_boundary/"
    "LOCAL_TRANSITION_RETOPOLOGY_STATIC_PROPOSAL.md"
)
PARENT_BOUNDARY_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_boundary/CHECKPOINT.md"
)
PARENT_BOUNDARY_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_boundary/INDEPENDENT_STATIC_AUDIT.md"
)
PARENT_BOUNDARY_TEST = (
    ROOT / "Testing/test_kira_r24_local_transition_retopology_boundary_static.py"
)
PARENT_CONTRACT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_execution_contract/"
    "LOCAL_TRANSITION_CUT_EXECUTION_CONTRACT_STATIC_PROPOSAL.md"
)
PARENT_CONTRACT_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_execution_contract/CHECKPOINT.md"
)
PARENT_CONTRACT_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_execution_contract/"
    "INDEPENDENT_STATIC_AUDIT.md"
)
PARENT_CONTRACT_TEST = (
    ROOT / "Testing/test_kira_r24_local_transition_cut_contract_static.py"
)
REPAIR_DOMAIN = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_02/"
    "BLACKPROJECT_ATTEMPT02_REPAIR_DOMAIN.json"
)
SOURCE_GLB = ROOT / (
    "Avatar/avatar_builder/asset_library/base_body_reference/"
    "base_female_character_blackproject_cc_by_4.glb"
)
SOURCE_AUTHORITY = SOURCE_GLB.with_suffix(".AUTHORITY.json")


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


def parse_genitalia_source_topology(
    path: Path,
) -> tuple[bytes, dict[str, object], list[tuple[int, int, int]], int]:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("truncated GLB")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise ValueError("unexpected GLB header")

    offset = 12
    json_chunk: bytes | None = None
    bin_chunk: bytes | None = None
    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + chunk_length]
        if len(chunk) != chunk_length:
            raise ValueError("truncated GLB chunk")
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            json_chunk = chunk
        elif chunk_type == 0x004E4942:
            bin_chunk = chunk
    if offset != len(data) or json_chunk is None or bin_chunk is None:
        raise ValueError("missing GLB JSON or BIN chunk")

    document = json.loads(json_chunk)
    meshes = document["meshes"]
    matching = [
        mesh
        for mesh in meshes
        if mesh.get("name") == "Ariel_Mesh_Genitalia_0"
    ]
    if len(matching) != 1 or len(matching[0]["primitives"]) != 1:
        raise ValueError("source mesh identity is not unique")
    primitive = matching[0]["primitives"][0]
    if primitive.get("mode", 4) != 4:
        raise ValueError("source primitive is not triangles")

    def scalar_accessor(accessor_index: int) -> list[int]:
        accessor = document["accessors"][accessor_index]
        if accessor["type"] != "SCALAR":
            raise ValueError("index accessor is not scalar")
        component_type = accessor["componentType"]
        formats = {5121: "B", 5123: "H", 5125: "I"}
        if component_type not in formats:
            raise ValueError("unsupported index component type")
        fmt = formats[component_type]
        item_size = struct.calcsize("<" + fmt)
        view = document["bufferViews"][accessor["bufferView"]]
        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = view.get("byteStride", item_size)
        if stride < item_size:
            raise ValueError("invalid accessor stride")
        return [
            struct.unpack_from("<" + fmt, bin_chunk, start + index * stride)[0]
            for index in range(accessor["count"])
        ]

    indices = scalar_accessor(primitive["indices"])
    if len(indices) % 3:
        raise ValueError("triangle index count is not divisible by three")
    faces = [
        tuple(indices[offset : offset + 3])
        for offset in range(0, len(indices), 3)
    ]
    if any(len(set(face)) != 3 for face in faces):
        raise ValueError("degenerate source triangle")
    position_accessor = document["accessors"][primitive["attributes"]["POSITION"]]
    return data, document, faces, int(position_accessor["count"])


def edge_incidence(
    faces: list[tuple[int, int, int]], selected: set[int] | None = None
) -> dict[tuple[int, int], list[int]]:
    rows: dict[tuple[int, int], list[int]] = collections.defaultdict(list)
    face_indices = range(len(faces)) if selected is None else sorted(selected)
    for face_index in face_indices:
        first, second, third = faces[face_index]
        for edge in (
            canonical_edge(first, second),
            canonical_edge(second, third),
            canonical_edge(third, first),
        ):
            rows[edge].append(face_index)
    return rows


def face_components(
    selected: set[int], incidence: dict[tuple[int, int], list[int]]
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


def canonical_boundary_cycle(boundary_edges: list[tuple[int, int]]) -> list[int]:
    adjacency: dict[int, set[int]] = collections.defaultdict(set)
    for first, second in boundary_edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("boundary is not a union of cycles")
    start = min(adjacency)
    previous: int | None = None
    current = start
    cycle = [start]
    while True:
        candidates = sorted(
            neighbor for neighbor in adjacency[current] if neighbor != previous
        )
        if not candidates:
            raise ValueError("boundary traversal stopped")
        next_vertex = candidates[0]
        if next_vertex == start:
            break
        if next_vertex in cycle:
            raise ValueError("boundary revisited a non-start vertex")
        cycle.append(next_vertex)
        previous, current = current, next_vertex
        if len(cycle) > len(boundary_edges):
            raise ValueError("boundary traversal exceeded edge count")
    if len(cycle) != len(boundary_edges):
        raise ValueError("boundary has more than one component")
    return cycle


def topology_summary(
    faces: list[tuple[int, int, int]], selected: set[int]
) -> dict[str, object]:
    vertices = sorted(
        {vertex for face_index in selected for vertex in faces[face_index]}
    )
    incidence = edge_incidence(faces, selected)
    edges = sorted(incidence)
    boundary = sorted(edge for edge, rows in incidence.items() if len(rows) == 1)
    if any(len(rows) > 2 for rows in incidence.values()):
        raise ValueError("selected topology is nonmanifold")
    cycle = canonical_boundary_cycle(boundary)
    return {
        "vertices": vertices,
        "edges": edges,
        "boundary": boundary,
        "cycle": cycle,
        "face_components": face_components(selected, incidence),
        "euler": len(vertices) - len(edges) + len(selected),
    }


class StrictSeparationEnvelopeStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPAIR_DOMAIN.read_text(encoding="utf-8"))
        cls.domains = {
            int(row["face_ring_expansion"]): row
            for row in cls.report["domains"]
        }
        cls.glb_bytes, cls.glb_document, cls.faces, cls.vertex_count = (
            parse_genitalia_source_topology(SOURCE_GLB)
        )
        cls.d2 = set(cls.domains[2]["face_indices"])
        cls.d4 = set(cls.domains[4]["face_indices"])
        cls.d2_vertices = {
            vertex for face_index in cls.d2 for vertex in cls.faces[face_index]
        }
        cls.full_incidence = edge_incidence(cls.faces)
        cls.vertex_faces: dict[int, set[int]] = collections.defaultdict(set)
        for face_index, face in enumerate(cls.faces):
            for vertex in face:
                cls.vertex_faces[vertex].add(face_index)
        cls.d4_summary = topology_summary(cls.faces, cls.d4)
        cls.overlap = sorted(
            cls.d2_vertices & set(cls.d4_summary["cycle"])
        )
        cls.required_additions = set().union(
            *(cls.vertex_faces[vertex] - cls.d4 for vertex in cls.overlap)
        )
        cls.envelope = cls.d4 | cls.required_additions
        cls.envelope_summary = topology_summary(cls.faces, cls.envelope)

    def test_01_parent_records_and_sealed_inputs_are_exact(self) -> None:
        expected = {
            PARENT_BOUNDARY: "64df882c44c23eb58f81bbcc94311269ac80f1444b27e144ec74e6c3cc18c3e7",
            PARENT_BOUNDARY_CHECKPOINT: "cfd791d16f97ef33a04e1c98ac6b32714805906506b8ff8dba88f108f1d9cbd7",
            PARENT_BOUNDARY_AUDIT: "75bdc7e3152aeffd4b8d17f9898b57c329e51c476c203b674547f297e07e2561",
            PARENT_BOUNDARY_TEST: "7f0c1d7bcb5b2dab501495c573b29e93bd3f694626e5595ba97278c05d79edf6",
            PARENT_CONTRACT: "a6665a0966e943c97ec6e8e55226c4b032e6b5721adc0b6f00dbe67d065d36c7",
            PARENT_CONTRACT_CHECKPOINT: "e37bc90c8d6e1d2e1c4b6c2479b8de94d618a31ef3cc0e61c247bbadd5e39237",
            PARENT_CONTRACT_AUDIT: "c5b7df3ef34500c2548f0849c4dc9d563168950f1d398afc899761cef56a3072",
            PARENT_CONTRACT_TEST: "0a1c4d1af5e75fec79bfeedce65202f355c031cf9f57b7f7dac63266f440ee72",
            REPAIR_DOMAIN: "c14e5f7324ae3e4279eb6408b52de7eaecb372fb9afa8caf191f875b411473a3",
            SOURCE_GLB: "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df",
            SOURCE_AUTHORITY: "d632a501edb2177aed7299aa257b61784685bdf2d9c88fa280370b640c4b508c",
        }
        for path, expected_hash in expected.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256_file(path), expected_hash)

    def test_02_proposal_is_static_bounded_and_fail_closed(self) -> None:
        text = PROPOSAL.read_text(encoding="utf-8")
        lower = text.lower()
        self.assertIn(
            "status: `static_strict_separation_envelope_bound_not_execution_authorized`",
            lower,
        )
        for token in (
            "unique minimum carrier envelope",
            "exactly nine necessary source triangles",
            "d2 is strictly interior",
            "1,275 of the 1,436 source faces lie outside e*",
            "not another source-star iteration",
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

    def test_03_source_topology_and_existing_domains_reproduce_exactly(self) -> None:
        self.assertEqual(len(self.glb_bytes), 129_862_196)
        self.assertEqual(self.vertex_count, 736)
        self.assertEqual(len(self.faces), 1436)
        self.assertEqual(
            compact_sha256([list(face) for face in self.faces]),
            "a0efc1d58800d7294b99a1c2eefbd5816fa47084561f189c6c98c9ea4a5f16bc",
        )
        self.assertEqual(
            compact_sha256(sorted(self.d2)),
            "aeb5ea5249c5e8883e5372e04b8844f6b4d449ccd36e72af8c0a213ec79d1426",
        )
        self.assertEqual(
            compact_sha256(sorted(self.d2_vertices)),
            "276358504d91cf2d0f16eda7180e181eada12ae8cb441e32904982f25e5127a2",
        )
        self.assertEqual(
            compact_sha256(sorted(self.d4)),
            "3fe5b3c84b731478cdfb8cec667f0cfc66651b086a4d5921a5c54f669d4f43b7",
        )
        self.assertEqual(
            compact_sha256([list(edge) for edge in self.d4_summary["boundary"]]),
            "ddc197b0b762b849170963bab5dcd5a5c0fe930323ce14f09fcbf2a42aa7349f",
        )
        self.assertEqual(self.overlap, [5, 90, 91, 508, 534])

    def test_04_nine_additions_are_individually_necessary_and_jointly_sufficient(self) -> None:
        expected_by_vertex = {
            5: [3],
            90: [368, 369, 1330],
            91: [372, 373, 1329],
            508: [826],
            534: [864],
        }
        actual_by_vertex = {
            vertex: sorted(self.vertex_faces[vertex] - self.d4)
            for vertex in self.overlap
        }
        self.assertEqual(actual_by_vertex, expected_by_vertex)
        self.assertEqual(
            sorted(self.required_additions),
            [3, 368, 369, 372, 373, 826, 864, 1329, 1330],
        )
        self.assertEqual(
            compact_sha256(sorted(self.required_additions)),
            "de93c898c67d4c7ef74adfbd9068b04af6746e3f8be33cc403bad0c8a58dd420",
        )
        complete_d2_incident_closure = set().union(
            *(self.vertex_faces[vertex] for vertex in self.d2_vertices)
        )
        self.assertEqual(complete_d2_incident_closure, self.envelope)
        self.assertTrue(
            all(self.vertex_faces[vertex] <= self.envelope for vertex in self.d2_vertices)
        )
        self.assertFalse(
            self.d2_vertices & set(self.envelope_summary["cycle"])
        )
        for omitted in sorted(self.required_additions):
            reduced = self.envelope - {omitted}
            boundary_vertices = set(topology_summary(self.faces, reduced)["cycle"])
            with self.subTest(omitted_face=omitted):
                self.assertTrue(self.d2_vertices & boundary_vertices)

    def test_05_minimum_envelope_is_one_disk_with_one_exact_boundary(self) -> None:
        summary = self.envelope_summary
        self.assertEqual(len(self.envelope), 161)
        self.assertEqual(len(summary["vertices"]), 102)
        self.assertEqual(len(summary["edges"]), 262)
        self.assertEqual(len(summary["boundary"]), 41)
        self.assertEqual(summary["face_components"], 1)
        self.assertEqual(summary["euler"], 1)
        self.assertEqual(len(summary["cycle"]), 41)
        self.assertEqual(
            compact_sha256(sorted(self.envelope)),
            "54eabc2570e5f74a2fd9a10c04654e4ac908e2780e546b40f5babaf8b104c68b",
        )
        self.assertEqual(
            compact_sha256(summary["vertices"]),
            "179bf99f8a85296261f48a5bdd2a3e0f7b30bb8a8c606cb74f93c3423e2a9e23",
        )
        self.assertEqual(
            compact_sha256([list(edge) for edge in summary["edges"]]),
            "44763d8e6fb737d18f15fcd3760423b4365a6c20998de607f6cb1da9c3fa0100",
        )
        self.assertEqual(
            compact_sha256([list(edge) for edge in summary["boundary"]]),
            "2c29f738004c3cc2b8af62ac73701ea062cb236f30900ff8ba67596a412fa870",
        )
        self.assertEqual(
            summary["cycle"],
            [
                0, 3, 6, 75, 76, 241, 246, 247, 714, 706, 518, 516,
                507, 503, 459, 489, 499, 498, 685, 686, 691, 575, 574,
                701, 702, 688, 536, 533, 528, 527, 513, 511, 510, 521,
                520, 705, 713, 249, 248, 240, 74,
            ],
        )
        self.assertEqual(
            compact_sha256(summary["cycle"]),
            "cbe518f5930c0f69466a95ef72b2845344c9605d55a7cdb5ef6107585a6acba5",
        )

    def test_06_collar_new_vertices_and_nonuniform_scope_are_exact(self) -> None:
        collar = sorted(self.envelope - self.d2)
        added_vertices = sorted(
            set(self.envelope_summary["vertices"])
            - set(self.d4_summary["vertices"])
        )
        self.assertEqual(len(collar), 73)
        self.assertEqual(
            compact_sha256(collar),
            "502cb9d83333c6b57d2fa1f99959455010627816f08226a42fedbf3a0ed27704",
        )
        self.assertEqual(added_vertices, [246, 247, 248, 249])
        self.assertEqual(
            compact_sha256(added_vertices),
            "6da7edb1d8c8b40647bf40d71d70b232d5cda66acbdb3b6f47a2e182a7850fd3",
        )
        d5 = set(self.domains[5]["face_indices"])
        d6 = set(self.domains[6]["face_indices"])
        self.assertFalse(self.envelope <= d5)
        self.assertEqual(sorted(self.envelope - d5), [368, 373])
        self.assertTrue(self.envelope <= d6)
        self.assertLess(len(self.envelope), len(d5))
        self.assertLess(len(self.envelope), len(d6))

    def test_07_exact_exterior_and_global_seam_remain_disjoint(self) -> None:
        outside = sorted(set(range(len(self.faces))) - self.envelope)
        self.assertEqual(len(outside), 1275)
        self.assertEqual(
            compact_sha256(outside),
            "8b3317f22790c880950a02bf7406c89c375e5ad0cdfbf9b2d5e53cc63d3f25a8",
        )
        seam = set(self.report["global_interface"]["boundary_vertex_indices"])
        envelope_vertices = set(self.envelope_summary["vertices"])
        self.assertFalse(envelope_vertices & seam)

        full_edges = edge_incidence(self.faces)
        graph: dict[int, set[int]] = collections.defaultdict(set)
        for first, second in full_edges:
            graph[first].add(second)
            graph[second].add(first)
        distance = {vertex: 0 for vertex in seam}
        queue = collections.deque(sorted(seam))
        while queue:
            current = queue.popleft()
            for neighbor in sorted(graph[current]):
                if neighbor not in distance:
                    distance[neighbor] = distance[current] + 1
                    queue.append(neighbor)
        self.assertEqual(min(distance[vertex] for vertex in envelope_vertices), 4)

        exterior_adjacent: set[int] = set()
        for edge in self.envelope_summary["boundary"]:
            incident = self.full_incidence[edge]
            self.assertEqual(len(incident), 2)
            inside = [face for face in incident if face in self.envelope]
            outside_rows = [face for face in incident if face not in self.envelope]
            self.assertEqual(len(inside), 1)
            self.assertEqual(len(outside_rows), 1)
            exterior_adjacent.update(outside_rows)
        self.assertEqual(len(exterior_adjacent), 41)
        self.assertEqual(
            compact_sha256(sorted(exterior_adjacent)),
            "80fc5609ac04b17d4fd1bc44a719bdfc7d5afd69816ab6d756dca8074c350b32",
        )

    def test_08_no_runtime_or_geometry_artifact_was_created(self) -> None:
        allowed = {
            "STRICT_SEPARATION_ENVELOPE_STATIC_PROPOSAL.md",
            "CHECKPOINT.md",
            "INDEPENDENT_STATIC_AUDIT.md",
        }
        actual = {path.name for path in PACKAGE.iterdir()}
        self.assertIn("STRICT_SEPARATION_ENVELOPE_STATIC_PROPOSAL.md", actual)
        self.assertTrue(actual <= allowed)
        self.assertTrue(all((PACKAGE / name).is_file() for name in actual))
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)


if __name__ == "__main__":
    unittest.main()
