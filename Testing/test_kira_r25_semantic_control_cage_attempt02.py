from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock

from tools import kira_r25_semantic_control_cage_core_v2 as core


ROOT = Path(__file__).resolve().parents[1]


def alignment_fixture():
    coordinates = {
        "face": (0.0, 0.35, 3.0), "head": (0.0, 0.0, 3.3),
        "neck": (0.0, -0.05, 2.75), "torso": (0.0, -0.15, 2.0),
        "upper_arm.L": (1.0, 0.0, 2.4), "lower_arm.L": (2.0, 0.1, 2.3),
        "hand.L": (3.0, 0.25, 2.2), "upper_arm.R": (-1.0, 0.0, 2.4),
        "lower_arm.R": (-2.0, 0.1, 2.3), "hand.R": (-3.0, 0.25, 2.2),
        "thigh.L": (0.55, -0.05, 1.4), "shin.L": (0.55, 0.15, 0.65),
        "foot.L": (0.55, 0.6, 0.1), "thigh.R": (-0.55, -0.05, 1.4),
        "shin.R": (-0.55, 0.15, 0.65), "foot.R": (-0.55, 0.6, 0.1),
    }
    return [coordinates[region] for region in core.REGIONS], list(core.REGIONS)


def align(source, regions, target=None, **overrides):
    options = {
        "minimum_rank_ratio": 1e-5,
        "minimum_scale": 0.5,
        "maximum_scale": 2.0,
        "maximum_normalized_rms_residual": 0.02,
        "maximum_orthonormal_residual": 1e-8,
        "minimum_left_right_separation": 0.1,
    }
    options.update(overrides)
    return core.similarity_from_region_centroids(
        source, regions, target or source, regions, core.REGIONS, set(), set(), **options
    )


def torus_mesh(rows=6, columns=4):
    def vertex(row, column):
        return (row % rows) * columns + (column % columns)

    faces = []
    for row in range(rows):
        for column in range(columns):
            a = vertex(row, column)
            b = vertex(row + 1, column)
            c = vertex(row + 1, column + 1)
            d = vertex(row, column + 1)
            faces.extend(((a, b, c), (a, c, d)))
    edges = sorted({
        tuple(sorted((face[position], face[(position + 1) % 3])))
        for face in faces for position in range(3)
    })
    return rows * columns, edges, faces


class BlobTable:
    def __init__(self):
        self.records = {}

    def _blob(self, values):
        raw = b"".join(struct.pack(">I", value) for value in values)
        digest = hashlib.sha256(raw).hexdigest()
        reference = f"sha256:{digest}"
        self.records[reference] = {
            "codec": core.AFES_BLOB_CODEC, "endianness": "big",
            "u32_count": len(values), "raw_bytes": len(raw),
            "raw_sha256": digest, "base64": base64.b64encode(raw).decode("ascii"),
        }
        return reference

    def indices(self, values):
        values = tuple(sorted(set(values)))
        return {
            "blob_ref": self._blob(values), "semantic": core.AFES_INDEX_SEMANTIC,
            "item_count": len(values), "semantic_sha256": core.index_sha256(values),
        }

    def edges(self, values):
        values = tuple(sorted(set(tuple(sorted(value)) for value in values)))
        flat = tuple(component for value in values for component in value)
        return {
            "blob_ref": self._blob(flat), "semantic": core.AFES_EDGE_SEMANTIC,
            "item_count": len(values),
            "semantic_sha256": core.canonical_sha256([list(value) for value in values]),
        }


def compact_afes_fixture():
    vertex_count, edges, faces = torus_mesh()
    adjacency = {index: set() for index in range(vertex_count)}
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    union = (0,)
    ring1 = tuple(sorted(adjacency[0] - {0}))
    ring2 = tuple(sorted({neighbor for current in ring1 for neighbor in adjacency[current]} - set(union) - set(ring1)))
    combined = tuple(sorted(set(ring1).union(ring2)))
    incident = tuple(i for i, face in enumerate(faces) if 0 in face)
    internal = ()
    connections = tuple(edge for edge in edges if (edge[0] == 0) != (edge[1] == 0))
    table = BlobTable()
    bounds = {
        "unit": "nanometer", "integer_units_per_meter": 1_000_000_000,
        "rounding": "decimal_from_shortest_roundtrip_float_then_half_even_to_integer",
        "minimum": [-10, -20, -30], "maximum": [10, 20, 30],
    }
    topology_digest = core.canonical_sha256({
        "vertex_count": vertex_count, "edges": [list(edge) for edge in edges],
        "faces": [list(face) for face in faces],
    })
    structure = {
        "full_normalized_topology_sha256": topology_digest,
        "connected_component_count": 1, "isolated_vertex_count": 0,
        "boundary_edge_count": 0, "nonmanifold_edge_count": 0,
        "loose_edge_count": 0, "face_boundary_edge_missing_from_mesh_count": 0,
        "duplicate_face_record_count": 0, "transition_ring_loose_edge_incidence_count": 0,
    }
    compact = {
        "whole_mesh": {
            "vertex_count": vertex_count, "edge_count": len(edges), "face_count": len(faces),
            "topology_sha256": topology_digest,
        },
        "topology_structure": structure,
        "groups": {"AFES_fixture": {"vertex_indices": table.indices(union)}},
        "afes_union": {
            "vertex_indices": table.indices(union),
            "incident_face_indices": table.indices(incident),
            "internal_face_indices": table.indices(internal),
            "primary_connection_edges": table.edges(connections),
        },
        "transition_rings": {
            "ring_count": 2,
            "rings": [
                {"ring_number": 1, "vertex_indices": table.indices(ring1)},
                {"ring_number": 2, "vertex_indices": table.indices(ring2)},
            ],
            "combined_vertex_indices": table.indices(combined),
            "disjoint_from_afes_union": True,
        },
        "bounds_object_nm": bounds,
        "binary_arrays": table.records,
    }
    verified_inputs = {
        "foundation_blend": {"path": "foundation.blend", "bytes": 10, "sha256": "a" * 64},
        "attempt_04_extractor": {"path": "extractor.py", "bytes": 20, "sha256": "b" * 64},
        "attempt_04_core": {"path": "core.py", "bytes": 30, "sha256": "c" * 64},
    }
    expected = {
        "pair_acceptance_frame_sha256": "3" * 64,
        "run_01_frame_sha256": "1" * 64, "run_02_frame_sha256": "2" * 64,
        "pair_schema": "pair.v4", "pair_status": "PAIR_ACCEPTED",
        "run_schema": "run.v4", "run_status": "PENDING_PAIR",
        "inner_schema": "inner.v4", "inner_status": "UNSEALED",
        "execution_contract_sha256": "4" * 64, "execution_contract_bytes": 100,
        "foundation_object": "Foundation", "foundation_mesh": "FoundationMesh",
        "exact_extraction_verified_inputs": deepcopy(verified_inputs),
        "foundation_vertex_count": vertex_count, "foundation_edge_count": len(edges),
        "foundation_face_count": len(faces), "foundation_topology_sha256": topology_digest,
        "required_afes_group_names": ["AFES_fixture"],
        "afes_union_count": len(union), "afes_union_sha256": core.index_sha256(union),
        "ring_1_count": len(ring1), "ring_1_sha256": core.index_sha256(ring1),
        "ring_2_count": len(ring2), "ring_2_sha256": core.index_sha256(ring2),
        "combined_ring_count": len(combined), "combined_ring_sha256": core.index_sha256(combined),
        "locked_vertex_count": len(set(union).union(combined)),
        "locked_vertex_sha256": core.index_sha256(set(union).union(combined)),
        "exact_topology_structure": structure,
        "exact_afes_bounds_object_nm": bounds,
    }
    inner = {
        "schema": "inner.v4", "status": "UNSEALED",
        "verified_inputs": verified_inputs, "foundation_object": "Foundation",
        "foundation_mesh": "FoundationMesh", "analysis": compact,
    }
    run1 = {
        "schema": "run.v4", "status": "PENDING_PAIR", "run_number": 1,
        "session_nonce": "5" * 64,
        "execution_contract": {"path": "contract.json", "bytes": 100, "sha256": "4" * 64},
        "inner_attempt02_payload": inner,
    }
    run2 = deepcopy(run1)
    run2["run_number"] = 2
    run2["session_nonce"] = "6" * 64
    inner_digest = core.canonical_sha256(inner)
    pair = {
        "schema": "pair.v4", "status": "PAIR_ACCEPTED",
        "execution_contract_sha256": "4" * 64,
        "bound_inputs_unchanged_under_locks": True,
        "runs": [
            {"run_number": 1, "session_nonce": "5" * 64, "frame_sha256": "1" * 64,
             "inner_payload_sha256": inner_digest, "topology_sha256": topology_digest},
            {"run_number": 2, "session_nonce": "6" * 64, "frame_sha256": "2" * 64,
             "inner_payload_sha256": inner_digest, "topology_sha256": topology_digest},
        ],
        "matching_inner_payload_sha256": inner_digest,
        "full_normalized_topology_sha256": topology_digest,
    }
    return compact, pair, (run1, run2), expected, edges, faces


def mapping_fixture():
    anchors = {"face": tuple(range(432))}
    source_regions = ["face"] * 432
    target_regions = ["face", "face", "face"]
    triangles = [core.Triangle(0, 0, (0, 1, 2))]
    records = [{
        "foundation_vertex_index": index, "foundation_region": "face", "target_region": "face",
        "r19_face_index": 0, "r19_triangle_index": 0,
        "r19_triangle_vertex_indices": [0, 1, 2],
        "barycentric_fixed_1e9": [1_000_000_000, 0, 0],
        "distance_micrometers": 1, "normal_dot_fixed_1e9": 500_000_000,
    } for index in range(432)]
    encoded, binary_digest, semantic_digest = core.encode_mapping_records(records)
    arguments = {
        "encoded": encoded, "declared_count": 432,
        "declared_record_bytes": core.MAPPING_RECORD.size,
        "declared_codec": core.MAPPING_CODEC,
        "declared_binary_sha256": binary_digest,
        "declared_mapping_sha256": semantic_digest,
        "expected_anchors": anchors, "source_regions": source_regions,
        "target_regions": target_regions, "target_triangles": triangles,
        "target_face_count": 1, "excluded_target_faces": set(),
        "maximum_distance_um": {"face": 10},
        "minimum_normal_dot_fixed": {"face": 0},
    }
    return records, arguments


class ExactSemanticTests(unittest.TestCase):
    def test_official_allowlist_is_complete_exact_139(self):
        self.assertEqual(len(core.OFFICIAL_MAKEHUMAN_GROUP_NAMES), 139)
        self.assertEqual(len(set(core.OFFICIAL_MAKEHUMAN_GROUP_NAMES)), 139)
        self.assertEqual(core.semantic_region_for_exact_group("upperarm01.L"), "upper_arm.L")

    def test_substring_spoofs_and_mixamo_aliases_fail(self):
        for value in ("not_a_left_hand_control", "fakejawdriver", "unrelated_leftarm_marker", "mixamorig:LeftArm"):
            with self.subTest(value=value), self.assertRaises(core.SemanticControlCageError):
                core.semantic_region_for_exact_group(value)

    def test_unknown_positive_assignment_fails_instead_of_being_ignored(self):
        with self.assertRaisesRegex(core.SemanticControlCageError, "nonofficial"):
            core.classify_weighted_vertices([[('head', 0.9), ('fakejawdriver', 0.1)]])

    def test_exact_weight_tie_fails(self):
        with self.assertRaisesRegex(core.SemanticControlCageError, "tie"):
            core.classify_weighted_vertices([[('head', 0.5), ('neck01', 0.5)]])


class AlignmentTests(unittest.TestCase):
    def test_full_rank_identity_alignment_passes(self):
        vertices, regions = alignment_fixture()
        result = align(vertices, regions)
        self.assertAlmostEqual(result.similarity.scale, 1.0)
        self.assertGreater(result.source_rank_ratio, 1e-5)
        self.assertAlmostEqual(result.rotation_determinant, 1.0)

    def test_collinear_cloud_fails_full_rank_gate(self):
        original, regions = alignment_fixture()
        vertices = [(x, 0.0, 0.0) for x, _, _ in original]
        with self.assertRaisesRegex(core.SemanticControlCageError, "full_rank"):
            align(vertices, regions, minimum_left_right_separation=0.0001)

    def test_reflection_with_preserved_x_side_order_fails(self):
        vertices, regions = alignment_fixture()
        reflected = [(x, -y, z) for x, y, z in vertices]
        with self.assertRaisesRegex(core.SemanticControlCageError, "reflection"):
            align(vertices, regions, reflected)

    def test_physical_left_right_swap_fails(self):
        vertices, regions = alignment_fixture()
        swapped = [(-x, y, z) for x, y, z in vertices]
        with self.assertRaisesRegex(core.SemanticControlCageError, "physical_left_right"):
            align(vertices, regions, swapped)

    def test_implausible_scale_fails(self):
        vertices, regions = alignment_fixture()
        scaled = [(x * 3, y * 3, z * 3) for x, y, z in vertices]
        with self.assertRaisesRegex(core.SemanticControlCageError, "scale"):
            align(vertices, regions, scaled)

    def test_large_normalized_residual_fails(self):
        vertices, regions = alignment_fixture()
        target = list(vertices)
        target[0] = (target[0][0], target[0][1] + 2.0, target[0][2])
        with self.assertRaisesRegex(core.SemanticControlCageError, "residual"):
            align(vertices, regions, target)


class CoverageTests(unittest.TestCase):
    def _chain(self, count=434):
        vertices = [(index * 0.001, 0.0, 0.0) for index in range(count)]
        faces = [(index, index + 1, index + 2) for index in range(count - 2)]
        return vertices, faces, ["face"] * count

    def test_432_anchor_control_cage_covers_every_permissible_vertex(self):
        vertices, faces, regions = self._chain()
        result = core.select_control_anchors_with_coverage(
            vertices, faces, regions, set(), {"face": 432}, {"face": 5000}, ("face",)
        )
        self.assertEqual(len(result.anchors["face"]), 432)
        self.assertEqual(result.rows[0]["covered_vertex_count"], 434)
        self.assertEqual(result.rows[0]["same_region_connected_component_count"], 1)

    def test_disconnected_or_loose_same_region_vertex_fails(self):
        vertices, faces, regions = self._chain()
        faces = [face for face in faces if 433 not in face]
        with self.assertRaisesRegex(core.SemanticControlCageError, "component_not_single"):
            core.select_control_anchors_with_coverage(
                vertices, faces, regions, set(), {"face": 432}, {"face": 5000}, ("face",)
            )

    def test_geodesic_radius_over_limit_fails(self):
        vertices, faces, regions = self._chain()
        with self.assertRaisesRegex(core.SemanticControlCageError, "geodesic_radius"):
            core.select_control_anchors_with_coverage(
                vertices, faces, regions, set(), {"face": 432}, {"face": 1}, ("face",)
            )


class MappingValidationTests(unittest.TestCase):
    def test_exact_432_mapping_round_trip_passes(self):
        _, arguments = mapping_fixture()
        rows = core.decode_and_validate_mapping_records(**arguments)
        self.assertEqual(len(rows), 432)

    def _mutate_record(self, arguments, position, field_index, value):
        raw = bytearray(base64.b64decode(arguments["encoded"]))
        offset = position * core.MAPPING_RECORD.size
        values = list(core.MAPPING_RECORD.unpack_from(raw, offset))
        values[field_index] = value
        core.MAPPING_RECORD.pack_into(raw, offset, *values)
        changed = dict(arguments)
        changed["encoded"] = base64.b64encode(raw).decode("ascii")
        changed["declared_binary_sha256"] = hashlib.sha256(raw).hexdigest()
        return changed

    def test_duplicate_source_record_fails(self):
        _, arguments = mapping_fixture()
        changed = self._mutate_record(arguments, 1, 0, 0)
        with self.assertRaisesRegex(core.SemanticControlCageError, "duplicate"):
            core.decode_and_validate_mapping_records(**changed)

    def test_out_of_range_or_wrong_sum_barycentric_fails(self):
        _, arguments = mapping_fixture()
        changed = self._mutate_record(arguments, 0, 7, 1_000_000_001)
        with self.assertRaisesRegex(core.SemanticControlCageError, "barycentric"):
            core.decode_and_validate_mapping_records(**changed)

    def test_triangle_vertex_alias_or_mismatch_fails(self):
        _, arguments = mapping_fixture()
        changed = self._mutate_record(arguments, 0, 4, 2)
        with self.assertRaisesRegex(core.SemanticControlCageError, "triangle_identity"):
            core.decode_and_validate_mapping_records(**changed)

    def test_excluded_face_fails(self):
        _, arguments = mapping_fixture()
        arguments["excluded_target_faces"] = {0}
        with self.assertRaisesRegex(core.SemanticControlCageError, "excluded"):
            core.decode_and_validate_mapping_records(**arguments)

    def test_binary_and_semantic_digests_are_independent_gates(self):
        _, arguments = mapping_fixture()
        changed = dict(arguments)
        changed["declared_binary_sha256"] = "0" * 64
        with self.assertRaisesRegex(core.SemanticControlCageError, "binary_digest"):
            core.decode_and_validate_mapping_records(**changed)
        changed = dict(arguments)
        changed["declared_mapping_sha256"] = "0" * 64
        with self.assertRaisesRegex(core.SemanticControlCageError, "semantic_digest"):
            core.decode_and_validate_mapping_records(**changed)

    def test_noncanonical_base64_and_wrong_count_fail(self):
        _, arguments = mapping_fixture()
        changed = dict(arguments)
        changed["encoded"] += "\n"
        with self.assertRaisesRegex(core.SemanticControlCageError, "base64"):
            core.decode_and_validate_mapping_records(**changed)
        changed = dict(arguments)
        changed["declared_count"] = 431
        with self.assertRaisesRegex(core.SemanticControlCageError, "432"):
            core.decode_and_validate_mapping_records(**changed)

    def test_negative_index_and_record_alias_key_fail_before_pack(self):
        records, _ = mapping_fixture()
        changed = deepcopy(records)
        changed[0]["r19_triangle_index"] = -1
        with self.assertRaisesRegex(core.SemanticControlCageError, "below_minimum"):
            core.encode_mapping_records(changed)
        changed = deepcopy(records)
        changed[0]["face_index"] = changed[0]["r19_face_index"]
        with self.assertRaisesRegex(core.SemanticControlCageError, "keys_drifted"):
            core.encode_mapping_records(changed)


class AfesPairValidationTests(unittest.TestCase):
    def validate(self, pair=None, runs=None, expected=None, edges=None, faces=None):
        _, default_pair, default_runs, default_expected, default_edges, default_faces = compact_afes_fixture()
        return core.validate_afes_pair_bundle(
            pair_payload=pair or default_pair, pair_frame_sha256="3" * 64,
            run_payloads=runs or default_runs, run_frame_sha256s=("1" * 64, "2" * 64),
            source_edges=edges or default_edges, source_faces=faces or default_faces,
            expected=expected or default_expected,
        )

    def test_exact_pair_union_rings_topology_and_dependencies_pass(self):
        locked, summary = self.validate()
        self.assertEqual(len(locked), summary["locked_vertex_count"])
        self.assertEqual(summary["fresh_session_nonces_distinct"], "YES")

    def test_pair_status_and_pair_frame_are_exact(self):
        _, pair, runs, expected, edges, faces = compact_afes_fixture()
        pair["status"] = "PENDING"
        with self.assertRaisesRegex(core.SemanticControlCageError, "decision"):
            self.validate(pair, runs, expected, edges, faces)
        with self.assertRaisesRegex(core.SemanticControlCageError, "pair_frame"):
            core.validate_afes_pair_bundle(
                pair_payload=pair, pair_frame_sha256="9" * 64, run_payloads=runs,
                run_frame_sha256s=("1" * 64, "2" * 64), source_edges=edges,
                source_faces=faces, expected=expected,
            )

    def test_fresh_nonces_must_be_distinct(self):
        _, pair, runs, expected, edges, faces = compact_afes_fixture()
        runs[1]["session_nonce"] = runs[0]["session_nonce"]
        pair["runs"][1]["session_nonce"] = runs[0]["session_nonce"]
        with self.assertRaisesRegex(core.SemanticControlCageError, "not_distinct"):
            self.validate(pair, runs, expected, edges, faces)

    def test_two_inner_payloads_must_match(self):
        _, pair, runs, expected, edges, faces = compact_afes_fixture()
        runs[1]["inner_attempt02_payload"]["extra"] = "drift"
        with self.assertRaises(core.SemanticControlCageError):
            self.validate(pair, runs, expected, edges, faces)

    def test_exact_extraction_dependencies_must_match(self):
        _, pair, runs, expected, edges, faces = compact_afes_fixture()
        runs[0]["inner_attempt02_payload"]["verified_inputs"]["attempt_04_core"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(core.SemanticControlCageError, "dependencies"):
            self.validate(pair, runs, expected, edges, faces)

    def test_ring_digest_or_topological_order_drift_fails(self):
        _, pair, runs, expected, edges, faces = compact_afes_fixture()
        expected["ring_1_sha256"] = "0" * 64
        with self.assertRaisesRegex(core.SemanticControlCageError, "ring_1"):
            self.validate(pair, runs, expected, edges, faces)
        _, pair, runs, expected, edges, faces = compact_afes_fixture()
        ring_rows = runs[0]["inner_attempt02_payload"]["analysis"]["transition_rings"]["rings"]
        ring_rows[0]["ring_number"] = 2
        with self.assertRaisesRegex(core.SemanticControlCageError, "ring_order"):
            self.validate(pair, runs, expected, edges, faces)

    def test_foundation_topology_digest_and_structure_are_recomputed(self):
        _, pair, runs, expected, edges, faces = compact_afes_fixture()
        bad_edges = list(edges)
        bad_edges.pop()
        with self.assertRaises(core.SemanticControlCageError):
            self.validate(pair, runs, expected, bad_edges, faces)

    def test_compact_blob_digest_and_unreferenced_alias_fail(self):
        compact, pair, runs, expected, edges, faces = compact_afes_fixture()
        blob = next(iter(compact["binary_arrays"].values()))
        blob["base64"] = blob["base64"][:-4] + "AAAA"
        with self.assertRaises(core.SemanticControlCageError):
            self.validate(pair, runs, expected, edges, faces)


class StaticScopeTests(unittest.TestCase):
    def test_attempt01_artifacts_remain_exact(self):
        expected = {
            "Avatar/avatar_builder/body_systems/kira_r25_semantic_cage_correspondence_diagnostic_v1.json": "b0d4cfd289cd9063547a17575f77f251b5566c683b9e421ee5529bc8c5a7c74c",
            "tools/kira_r25_semantic_cage_correspondence_core.py": "89e40d87c4ccc27dd9bdef5c3a1d4ca5b9c20b80097b9326a5f58031a99f8881",
            "tools/blender_diagnose_kira_r25_semantic_cage_correspondence.py": "fe074b5d339146e20574bd6b906c2005392bd978e4a2c07e17ad3b9eef8a1d98",
            "Testing/test_kira_r25_semantic_cage_correspondence_preparation.py": "336089291e899f1c9ef50b1f47ae48606d5299cf4e85b179f0869b67f98fe8e1",
            "RecoverySprint/continuation_20260809/kira_r25_semantic_cage_correspondence_static_preparation/CHECKPOINT.md": "a5daab75cb1592a871d8f36295f2790d2606ff743ff7b25c640ddddd89970411",
        }
        for relative, digest in expected.items():
            with self.subTest(relative=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)

    def test_attempt02_config_is_pending_unsealed_and_exactly_self_bound(self):
        config_path = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_semantic_control_cage_diagnostic_v2.json"
        config_bytes = config_path.read_bytes()
        config = json.loads(config_bytes.decode("utf-8"))
        self.assertEqual(
            config["status"],
            "STATIC_PREPARATION_ONLY_BLENDER_EXECUTION_NOT_AUTHORIZED",
        )
        afes = config["afes_pair_binding"]
        self.assertEqual(
            afes["seal_status"],
            "PENDING_UNSEALED_FINAL_INDEPENDENT_AUDIT_AND_FRESH_PAIR_EXECUTION",
        )
        self.assertIsNone(afes["expected_pair_and_analysis"])
        self.assertIn("pending_attempt_04_author_artifacts_not_yet_accepted", afes)
        self.assertNotIn("read_only_extraction_v2", config_bytes.decode("utf-8"))
        anchors = config["control_cage_contract"]["anchors_per_region"]
        self.assertEqual(sum(anchors.values()), 432)
        self.assertEqual(config["control_cage_contract"]["total_control_anchor_count"], 432)
        for binding_name in ("pure_control_cage_core", "execution_wrapper"):
            row = config["bindings"][binding_name]
            payload = (ROOT / row["path"]).read_bytes()
            with self.subTest(binding=binding_name):
                self.assertEqual(len(payload), row["bytes"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])

    @classmethod
    def _load_wrapper(cls):
        path = ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v2.py"
        name = "_test_r25_semantic_control_cage_wrapper_v2"
        sys.modules.pop(name, None)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        prior_bpy = sys.modules.get("bpy")
        sys.modules["bpy"] = types.ModuleType("bpy")
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            if prior_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = prior_bpy
        return module

    def test_wrapper_requires_FILE_TYPE_PIPE_for_both_handles(self):
        wrapper = self._load_wrapper()

        class GetFileType:
            argtypes = None
            restype = None

            def __init__(self, value):
                self.value = value

            def __call__(self, _handle):
                return self.value

        class Kernel:
            def __init__(self, value):
                self.GetFileType = GetFileType(value)

        with mock.patch.object(wrapper.ctypes, "WinDLL", return_value=Kernel(3)):
            wrapper._require_pipe(123, "lock_input")
            wrapper._require_pipe(456, "result_output")
        with mock.patch.object(wrapper.ctypes, "WinDLL", return_value=Kernel(1)):
            with self.assertRaisesRegex(wrapper.R25SemanticControlCageV2Error, "FILE_TYPE_PIPE"):
                wrapper._require_pipe(123, "lock_input")

    def test_fresh_exact_loader_rejects_metadata_spoofed_sys_modules(self):
        wrapper = self._load_wrapper()
        source = b"def exact_symbol():\n    return 'REAL_EXACT_BYTES'\n"
        digest = hashlib.sha256(source).hexdigest()
        private_name = f"_kira_r25_exact_fixture_{digest}"
        with tempfile.NamedTemporaryFile(
            dir=ROOT / "Testing", suffix=".py", delete=False
        ) as stream:
            stream.write(source)
            path = Path(stream.name)
        relative = path.relative_to(ROOT).as_posix()
        row = {"path": relative, "bytes": len(source), "sha256": digest}
        fake = types.ModuleType(private_name)
        fake.__file__ = str(path)
        fake.__spec__ = importlib.util.spec_from_file_location(private_name, path)
        fake.exact_symbol = lambda: "FAKE"
        sys.modules[private_name] = fake
        try:
            with self.assertRaisesRegex(wrapper.R25SemanticControlCageV2Error, "namespace_already_present"):
                wrapper._load_fresh_exact_module("fixture", row, ("exact_symbol",))
        finally:
            sys.modules.pop(private_name, None)
        try:
            loaded = wrapper._load_fresh_exact_module("fixture", row, ("exact_symbol",))
            self.assertEqual(loaded.exact_symbol(), "REAL_EXACT_BYTES")
            self.assertIsNot(loaded, fake)
        finally:
            sys.modules.pop(private_name, None)
            path.unlink(missing_ok=True)

    def test_wrapper_is_config_bound_and_has_no_path_result_or_authoring_calls(self):
        source = (ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v2.py").read_text(encoding="utf-8")
        self.assertIn("execution_wrapper_self_binding_mismatch", source)
        self.assertIn("--config-sha256", source)
        self.assertIn("_load_fresh_exact_module", source)
        self.assertIn("GetFileType", source)
        self.assertNotIn("bpy.ops", source)
        for forbidden in (
            "save_as_mainfile", "save_mainfile", "render.render", "export_scene",
            "wm.save", "write_text(", "write_bytes(", "open(\"w",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_wrapper_reads_exactly_pair_and_two_fresh_run_frames(self):
        source = (ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v2.py").read_text(encoding="utf-8")
        self.assertIn("MAX_INPUT_FRAMES = 3", source)
        self.assertIn("input_pipe_contains_more_than_three_frames", source)
        self.assertIn("pair_payload=pair_payload", source)


if __name__ == "__main__":
    unittest.main()
