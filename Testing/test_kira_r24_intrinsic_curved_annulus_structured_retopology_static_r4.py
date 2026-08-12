from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
R19_BLEND = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
REJECTED_FIXTURE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r3_independent_rejection_audit/"
    "SYNTHETIC_PARSER_ACCEPTANCE_FIXTURE.blend"
)

from tools import kira_r24_blend_sdna_typed_static_r4 as typed
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r4 as r4


def _identity() -> list[list[float]]:
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def mesh_record(object_name: str, mesh_name: str, *, rig: bool = True) -> dict[str, object]:
    coordinates = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
    return {
        "object_name": object_name,
        "mesh_name": mesh_name,
        "parent_name": None,
        "matrix_world": _identity(),
        "modifiers": ([{"name": "Armature", "type": "ARMATURE", "object": "Rig"}] if rig else []),
        "materials": ["Skin"],
        "vertices": [
            {
                "index": index,
                "coordinate_local_m": coordinate,
                "normal_local": [0.0, 0.0, 1.0],
                "groups": [{"name": "Bone", "weight": 1.0}],
            }
            for index, coordinate in enumerate(coordinates)
        ],
        "edges": [
            {"index": 0, "vertices": [0, 1], "use_seam": False, "use_edge_sharp": False},
            {"index": 1, "vertices": [1, 2], "use_seam": False, "use_edge_sharp": False},
            {"index": 2, "vertices": [2, 3], "use_seam": False, "use_edge_sharp": False},
            {"index": 3, "vertices": [3, 0], "use_seam": False, "use_edge_sharp": False},
        ],
        "polygons": [
            {
                "index": 0,
                "vertices": [0, 1, 2, 3],
                "loop_indices": [0, 1, 2, 3],
                "material_index": 0,
                "use_smooth": True,
            }
        ],
        "loops": [{"index": index, "vertex_index": index} for index in range(4)],
        "uv_layers": [
            {
                "name": "UVMap",
                "active": True,
                "active_render": True,
                "data": [
                    {"loop_index": 0, "uv": [0.0, 0.0]},
                    {"loop_index": 1, "uv": [1.0, 0.0]},
                    {"loop_index": 2, "uv": [1.0, 1.0]},
                    {"loop_index": 3, "uv": [0.0, 1.0]},
                ],
            }
        ],
        "attributes": [],
        "shape_keys": [],
        "loop_triangles": [
            {"index": 0, "polygon_index": 0, "vertices": [0, 1, 2], "loops": [0, 1, 2], "material_index": 0},
            {"index": 1, "polygon_index": 0, "vertices": [0, 2, 3], "loops": [0, 2, 3], "material_index": 0},
        ],
    }


def two_region_body_record() -> dict[str, object]:
    row = mesh_record("Body", "BodyMesh")
    row["materials"] = ["Skin", "Torso"]
    row["edges"] = [
        {"index": 0, "vertices": [0, 1], "use_seam": False, "use_edge_sharp": False},
        {"index": 1, "vertices": [1, 2], "use_seam": False, "use_edge_sharp": False},
        {"index": 2, "vertices": [0, 2], "use_seam": False, "use_edge_sharp": False},
        {"index": 3, "vertices": [2, 3], "use_seam": False, "use_edge_sharp": False},
        {"index": 4, "vertices": [0, 3], "use_seam": False, "use_edge_sharp": False},
    ]
    row["polygons"] = [
        {"index": 0, "vertices": [0, 1, 2], "loop_indices": [0, 1, 2], "material_index": 0, "use_smooth": True},
        {"index": 1, "vertices": [0, 2, 3], "loop_indices": [3, 4, 5], "material_index": 1, "use_smooth": True},
    ]
    row["loops"] = [
        {"index": 0, "vertex_index": 0},
        {"index": 1, "vertex_index": 1},
        {"index": 2, "vertex_index": 2},
        {"index": 3, "vertex_index": 0},
        {"index": 4, "vertex_index": 2},
        {"index": 5, "vertex_index": 3},
    ]
    uv = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    row["uv_layers"][0]["data"] = [
        {"loop_index": index, "uv": value} for index, value in enumerate(uv)
    ]
    row["loop_triangles"] = [
        {"index": 0, "polygon_index": 0, "vertices": [0, 1, 2], "loops": [0, 1, 2], "material_index": 0},
        {"index": 1, "polygon_index": 1, "vertices": [0, 2, 3], "loops": [3, 4, 5], "material_index": 1},
    ]
    return row


def set_point_provenance(
    mesh: dict[str, object],
    source_faces: list[int],
    barycentrics: list[list[float]],
    displacements: list[list[float]],
) -> None:
    mesh["attributes"] = [
        {
            "name": "r24_source_face",
            "domain": "POINT",
            "data_type": "INT",
            "data": source_faces,
        },
        {
            "name": "r24_barycentric",
            "domain": "POINT",
            "data_type": "FLOAT_VECTOR",
            "data": barycentrics,
        },
        {
            "name": "r24_displacement_local_m",
            "domain": "POINT",
            "data_type": "FLOAT_VECTOR",
            "data": displacements,
        },
    ]


def bind_square_boundary_provenance(mesh: dict[str, object]) -> None:
    set_point_provenance(
        mesh,
        [0, 0, 0, 1],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0]],
        [[0.0, 0.0, 0.0] for _ in range(4)],
    )


def displaced_feature_fixture() -> tuple[
    dict[str, object],
    list[list[float]],
    list[list[int]],
    list[list[float]],
    list[list[dict[str, object]]],
]:
    source_positions = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    source_faces = [[0, 1, 2]]
    source_uvs = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
    source_weights = [
        [{"bone_name": "BoneA", "weight": 1.0}],
        [{"bone_name": "BoneB", "weight": 1.0}],
        [{"bone_name": "BoneC", "weight": 1.0}],
    ]
    coordinates = source_positions + [[0.3, 0.3, 0.004]]
    groups = [
        [{"name": "BoneA", "weight": 1.0}],
        [{"name": "BoneB", "weight": 1.0}],
        [{"name": "BoneC", "weight": 1.0}],
        [
            {"name": "BoneA", "weight": 0.4},
            {"name": "BoneB", "weight": 0.3},
            {"name": "BoneC", "weight": 0.3},
        ],
    ]
    polygon_vertices = [[0, 1, 3], [1, 2, 3], [2, 0, 3]]
    mesh: dict[str, object] = {
        "object_name": "Patch",
        "mesh_name": "PatchMesh",
        "matrix_world": _identity(),
        "materials": ["Skin"],
        "vertices": [
            {
                "index": index,
                "coordinate_local_m": coordinate,
                "normal_local": [0.0, 0.0, 1.0],
                "groups": groups[index],
            }
            for index, coordinate in enumerate(coordinates)
        ],
        "polygons": [
            {
                "index": index,
                "vertices": values,
                "loop_indices": [3 * index + offset for offset in range(3)],
                "material_index": 0,
                "use_smooth": True,
            }
            for index, values in enumerate(polygon_vertices)
        ],
        "loops": [
            {"index": 3 * polygon + corner, "vertex_index": vertex}
            for polygon, values in enumerate(polygon_vertices)
            for corner, vertex in enumerate(values)
        ],
        "uv_layers": [
            {
                "name": "UVMap",
                "active": True,
                "active_render": True,
                "data": [
                    {
                        "loop_index": 3 * polygon + corner,
                        "uv": ([0.3, 0.3] if vertex == 3 else source_uvs[vertex]),
                    }
                    for polygon, values in enumerate(polygon_vertices)
                    for corner, vertex in enumerate(values)
                ],
            }
        ],
        "attributes": [],
    }
    set_point_provenance(
        mesh,
        [0, 0, 0, 0],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.4, 0.3, 0.3]],
        [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.004]],
    )
    return mesh, source_positions, source_faces, source_uvs, source_weights


def intersection_pair(first: int, second: int, *, distance: float = 1.0) -> dict[str, object]:
    return {
        "face_indices": [first, second],
        "shared_vertex_count": 0,
        "shared_edge_count": 0,
        "topology_edge_hops": 4,
        "face_centers": [[float(first), 0.0, 0.0], [float(second), 0.0, 0.0]],
        "center_distance_m": distance,
        "combined_bounds": {"min": [0.0, 0.0, 0.0], "max": [2.0, 1.0, 1.0]},
        "body_region": "pelvis",
        "overlap_character": "genuine_penetration",
        "genuine_positive_area_or_segment_penetration": True,
        "triangle_pair_classifications": [
            {
                "classification": "noncoplanar_crossing_segment",
                "genuine_penetration": True,
                "intersection_segment_length_m": 0.25,
                "triangle_indices": [first, second],
            }
        ],
    }


def contract_fixture() -> dict[str, object]:
    return {
        "artifact_semantic_identity": {
            "body_object_name": "Body",
            "patch_object_name": "Patch",
            "required_material_name": "Skin",
            "required_objects": {
                "Body": {"type": "MESH", "data_name": "BodyMesh"},
                "Patch": {"type": "MESH", "data_name": "PatchMesh"},
                "Rig": {"type": "ARMATURE", "data_name": "Armature"},
            },
            "armature_modified_mesh_objects": ["Body", "Patch"],
        },
        "rig_and_action_requirements": {
            "required_armature_name": "Rig",
            "required_action_names": ["Act"],
        },
        "intersection_and_interface_requirements": {
            "global_interface_vertex_indices": [0, 1],
            "global_interface_vertex_count": 0,
        },
    }


def snapshot_fixture() -> dict[str, object]:
    body = mesh_record("Body", "BodyMesh")
    patch = mesh_record("Patch", "PatchMesh")
    rig = {
        "object_name": "Rig",
        "armature_name": "Armature",
        "parent_name": None,
        "matrix_world": _identity(),
        "bones": [
            {
                "name": "Bone",
                "parent": None,
                "head_local": [0.0, 0.0, 0.0],
                "tail_local": [0.0, 0.0, 1.0],
                "matrix_local": _identity(),
                "use_deform": True,
            }
        ],
    }
    state = {
        "objects": [
            {"name": "Body", "type": "MESH", "data_name": "BodyMesh", "parent_name": None},
            {"name": "Patch", "type": "MESH", "data_name": "PatchMesh", "parent_name": None},
            {"name": "Rig", "type": "ARMATURE", "data_name": "Armature", "parent_name": None},
        ],
        "mesh_objects": [body, patch],
        "armature_objects": [rig],
        "materials": [{"name": "Skin", "use_nodes": False, "surface_render_method": "", "nodes": [], "links": []}],
        "actions": [{"name": "Act", "frame_range": [1.0, 2.0], "use_fake_user": False, "storage": "legacy", "fcurves": []}],
        "intersection_reports": {},
        "scenes": [],
    }
    return {"state": state}


def dna_payload() -> bytes:
    names = ["name[66]", "id", "decoy[66]"]
    types = ["char", "ID", "Object", "Mesh", "bArmature", "bAction", "Material"]
    lengths = [1, 66, 66, 66, 66, 66, 66]
    structures = [
        (1, [(0, 0)]),
        (2, [(1, 1)]),
        (3, [(1, 1)]),
        (4, [(1, 1)]),
        (5, [(1, 1)]),
        (6, [(1, 1)]),
    ]
    payload = bytearray(b"SDNANAME" + struct.pack("<I", len(names)))
    payload.extend(b"".join(value.encode() + b"\x00" for value in names))
    while len(payload) % 4:
        payload.append(0)
    payload.extend(b"TYPE" + struct.pack("<I", len(types)))
    payload.extend(b"".join(value.encode() + b"\x00" for value in types))
    while len(payload) % 4:
        payload.append(0)
    payload.extend(b"TLEN")
    payload.extend(struct.pack("<" + "H" * len(lengths), *lengths))
    while len(payload) % 4:
        payload.append(0)
    payload.extend(b"STRC" + struct.pack("<I", len(structures)))
    for type_index, fields in structures:
        payload.extend(struct.pack("<HH", type_index, len(fields)))
        for field_type, field_name in fields:
            payload.extend(struct.pack("<HH", field_type, field_name))
    return bytes(payload)


def mini_blend(
    *,
    wrong_sdna: bool = False,
    wrong_length: bool = False,
    wrong_count: bool = False,
    wrong_field_name: bool = False,
    wrong_pointer: str | None = None,
) -> bytes:
    blocks = []
    names = {"OB": "Body", "ME": "Mesh", "AR": "Armature", "AC": "Act", "MA": "Skin"}
    indices = {"OB": 1, "ME": 2, "AR": 3, "AC": 4, "MA": 5}
    old_address = 0x1000
    for code in ("OB", "ME", "AR", "AC", "MA"):
        semantic = (code + names[code]).encode()
        if code == "OB" and wrong_field_name:
            payload = b"\x00" * 66 + semantic.ljust(66, b"\x00")
            # Change Object's TLEN/field layout only for this fixture by using
            # a caller string in an untyped tail. The block must fail length.
        else:
            payload = semantic.ljust(66, b"\x00")
        sdna = indices[code]
        if code == "OB" and wrong_sdna:
            sdna = indices["ME"]
        count = 2 if code == "OB" and wrong_count else 1
        if count == 2:
            payload *= 2
        if code == "OB" and wrong_length:
            payload = payload[:-1]
        pointer = old_address
        if code == "OB" and wrong_pointer == "null":
            pointer = 0
        if code == "ME" and wrong_pointer == "duplicate":
            pointer = 0x1000
        blocks.append(struct.pack("<4sIQII", code.encode().ljust(4, b"\x00"), len(payload), pointer, sdna, count) + payload)
        old_address += 0x1000
    dna = dna_payload()
    blocks.append(struct.pack("<4sIQII", b"DNA1", len(dna), old_address, 0, 1) + dna)
    blocks.append(struct.pack("<4sIQII", b"ENDB", 0, 0, 0, 0))
    return b"BLENDER-v401" + b"".join(blocks)


class R4StaticGateTests(unittest.TestCase):
    def test_01_r3_rejection_audit_and_fixture_are_exactly_bound(self) -> None:
        contract = r4.load_sealed_contract()
        self.assertEqual(
            r4.sha256_file(REJECTED_FIXTURE),
            "22ad510d481525f190664ff1d1d9521168125452dac22709e44b08cac0e81fef",
        )
        self.assertGreaterEqual(len(contract["parent_bindings"]), 10)
        context = r4.r3.exact_context()
        all_pairs, outside_pairs = r4._source_patch_diagnostic_records(
            contract, set(context["domains"]["outside"])
        )
        self.assertEqual(len(all_pairs), 259)
        self.assertEqual(len(outside_pairs), 214)
        self.assertEqual(r4.validate_inherited_outside_quality_record(context, contract), set())

    def test_02_r4_contract_and_all_implementation_files_are_sealed(self) -> None:
        contract = r4.load_sealed_contract()
        self.assertEqual(
            r4.canonical_sha256(r4._semantic_projection(contract)),
            r4.SEALED_CONTRACT_SEMANTIC_SHA256,
        )
        for record in contract["authorized_implementation"].values():
            if isinstance(record, dict) and set(record) >= {"path", "bytes", "sha256"}:
                r4.validate_exact_file(ROOT, record)

    def test_03_real_r19_blend_uses_typed_sdna_and_typed_id_names(self) -> None:
        summary = typed.parse_typed_blend(R19_BLEND)
        self.assertEqual(summary["header"], "BLENDER17-01v0501")
        for code, expected_type in typed.CODE_TO_STRUCTURE.items():
            self.assertTrue(summary["semantic_ids"][code])
            self.assertTrue(all(row["sdna_type"] == expected_type for row in summary["semantic_ids"][code]))
        self.assertIn("Ariel_Mesh", typed.semantic_names(summary, "OB"))

    def test_04_preserved_r3_synthetic_acceptance_fixture_fails_typed_gate(self) -> None:
        with self.assertRaises(typed.TypedBlendError):
            typed.parse_typed_blend(REJECTED_FIXTURE)

    def test_05_semantic_string_in_wrong_field_cannot_authorize(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r24_r4_wrong_field_") as raw:
            path = Path(raw) / "candidate.blend"
            path.write_bytes(mini_blend(wrong_field_name=True))
            with self.assertRaises(typed.TypedBlendError):
                typed.parse_typed_blend(path)

    def test_06_wrong_sdna_index_length_and_count_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r24_r4_typed_attacks_") as raw:
            root = Path(raw)
            for name, payload in (
                ("wrong_sdna.blend", mini_blend(wrong_sdna=True)),
                ("wrong_length.blend", mini_blend(wrong_length=True)),
                ("wrong_count.blend", mini_blend(wrong_count=True)),
            ):
                path = root / name
                path.write_bytes(payload)
                with self.subTest(name=name), self.assertRaises(typed.TypedBlendError):
                    typed.parse_typed_blend(path)

    def test_07_valid_minimal_typed_fixture_uses_id_field_not_regex(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r24_r4_typed_valid_") as raw:
            path = Path(raw) / "candidate.blend"
            path.write_bytes(mini_blend())
            summary = typed.parse_typed_blend(path)
            self.assertEqual(typed.semantic_names(summary, "OB"), {"Body"})
            self.assertNotIn("re", typed.__dict__)

    def test_08_caller_evidence_json_has_no_acceptance_path(self) -> None:
        result = r4.evaluate_measured_candidate_evidence(
            {"eligible": True, "topology": "claimed", "intersections": []}
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["failure_names"], ["caller_evidence_not_an_acceptance_input"])

    def test_09_extraction_envelope_binds_nonce_candidate_extractor_and_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r24_r4_envelope_") as raw:
            candidate = Path(raw) / "candidate.blend"
            candidate.write_bytes(b"x")
            state = {
                "objects": [],
                "mesh_objects": [],
                "armature_objects": [],
                "materials": [],
                "actions": [],
                "intersection_reports": {},
                "scenes": [],
            }
            snapshot = {
                "schema": "kira.avatar.r24.read_only_blender_extraction.v4",
                "nonce": "nonce",
                "candidate": {"path": str(candidate.resolve()), "bytes": 1, "sha256": hashlib.sha256(b"x").hexdigest()},
                "extractor": {"path": str(r4.EXTRACTOR.resolve()), "bytes": r4.EXTRACTOR.stat().st_size, "sha256": r4.sha256_file(r4.EXTRACTOR)},
                "intersection_helper": {
                    "path": str(r4.INTERSECTION_HELPER.resolve()),
                    "bytes": r4.INTERSECTION_HELPER.stat().st_size,
                    "sha256": r4.sha256_file(r4.INTERSECTION_HELPER),
                },
                "blender": {"version": "5.1.0", "background": True, "loaded_filepath": str(candidate.resolve())},
                "state": state,
                "truth": {
                    "read_only_extraction": True,
                    "blend_saved": False,
                    "candidate_mutated": False,
                    "in_memory_pose_evaluation_only": True,
                },
                "state_sha256": r4.canonical_sha256(state),
            }
            failures = r4.validate_extraction_envelope(
                snapshot,
                nonce="nonce",
                candidate=candidate,
                candidate_sha256=hashlib.sha256(b"x").hexdigest(),
                extractor_sha256=r4.sha256_file(r4.EXTRACTOR),
                intersection_helper_sha256=r4.sha256_file(r4.INTERSECTION_HELPER),
            )
            self.assertEqual(failures, set())
            snapshot["nonce"] = "forged"
            self.assertIn(
                "extraction:nonce",
                r4.validate_extraction_envelope(
                    snapshot,
                    nonce="nonce",
                    candidate=candidate,
                    candidate_sha256=hashlib.sha256(b"x").hexdigest(),
                    extractor_sha256=r4.sha256_file(r4.EXTRACTOR),
                    intersection_helper_sha256=r4.sha256_file(r4.INTERSECTION_HELPER),
                ),
            )
            snapshot["nonce"] = "nonce"
            snapshot["candidate"]["sha256"] = "0" * 64
            self.assertIn(
                "extraction:candidate_binding",
                r4.validate_extraction_envelope(
                    snapshot,
                    nonce="nonce",
                    candidate=candidate,
                    candidate_sha256=hashlib.sha256(b"x").hexdigest(),
                    extractor_sha256=r4.sha256_file(r4.EXTRACTOR),
                    intersection_helper_sha256=r4.sha256_file(r4.INTERSECTION_HELPER),
                ),
            )
            snapshot["candidate"]["sha256"] = hashlib.sha256(b"x").hexdigest()
            snapshot["intersection_helper"]["sha256"] = "0" * 64
            self.assertIn(
                "extraction:intersection_helper_binding",
                r4.validate_extraction_envelope(
                    snapshot,
                    nonce="nonce",
                    candidate=candidate,
                    candidate_sha256=hashlib.sha256(b"x").hexdigest(),
                    extractor_sha256=r4.sha256_file(r4.EXTRACTOR),
                    intersection_helper_sha256=r4.sha256_file(r4.INTERSECTION_HELPER),
                ),
            )
            snapshot["intersection_helper"]["sha256"] = r4.sha256_file(r4.INTERSECTION_HELPER)
            del snapshot["state"]["mesh_objects"]
            snapshot["state_sha256"] = r4.canonical_sha256(snapshot["state"])
            self.assertIn(
                "extraction:complete_state",
                r4.validate_extraction_envelope(
                    snapshot,
                    nonce="nonce",
                    candidate=candidate,
                    candidate_sha256=hashlib.sha256(b"x").hexdigest(),
                    extractor_sha256=r4.sha256_file(r4.EXTRACTOR),
                    intersection_helper_sha256=r4.sha256_file(r4.INTERSECTION_HELPER),
                ),
            )

    def test_10_disconnected_object_mesh_or_armature_link_is_rejected(self) -> None:
        snapshot = snapshot_fixture()
        contract = contract_fixture()
        self.assertEqual(r4.validate_object_links(snapshot, contract), set())
        snapshot["state"]["objects"][1]["data_name"] = "OtherMesh"
        snapshot["state"]["mesh_objects"][1]["modifiers"] = []
        failures = r4.validate_object_links(snapshot, contract)
        self.assertIn("object_link:Patch", failures)
        self.assertIn("object_link:Patch:armature_modifier", failures)

    def test_11_topology_is_derived_from_extracted_vertices_and_polygons(self) -> None:
        patch = mesh_record("Patch", "PatchMesh")
        boundary = {0: [0.0, 0.0, 0.0], 1: [1.0, 0.0, 0.0], 2: [1.0, 1.0, 0.0], 3: [0.0, 1.0, 0.0]}
        failures, mapping = r4.validate_patch_topology(patch, boundary, [0, 1, 2, 3], 0, "Skin")
        self.assertEqual(failures, set())
        self.assertEqual(mapping, {0: 0, 1: 1, 2: 2, 3: 3})
        patch["polygons"][0]["vertices"] = [0, 1, 2]
        failures, _ = r4.validate_patch_topology(patch, boundary, [0, 1, 2, 3], 0, "Skin")
        self.assertIn("topology:exact_unsplit_source_boundary", failures)

    def test_12_uvs_are_extracted_per_loop_and_source_derived(self) -> None:
        patch = mesh_record("Patch", "PatchMesh")
        bind_square_boundary_provenance(patch)
        source_positions = [row["coordinate_local_m"] for row in patch["vertices"]]
        source_faces = [[0, 1, 2], [0, 2, 3]]
        source_uvs = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
        source_weights = [[{"bone_name": "Bone", "weight": 1.0}] for _ in range(4)]
        failures = r4.validate_patch_uv_and_weights(
            patch, source_positions, source_faces, source_uvs, source_weights, {0, 1}, {0: 0, 1: 1, 2: 2, 3: 3}
        )
        self.assertEqual(failures, set())
        patch["uv_layers"][0]["data"][0]["uv"] = [0.25, 0.25]
        self.assertIn(
            "uv:source_derived_corner_values",
            r4.validate_patch_uv_and_weights(
                patch, source_positions, source_faces, source_uvs, source_weights, {0, 1}, {0: 0, 1: 1, 2: 2, 3: 3}
            ),
        )

    def test_13_weights_are_extracted_and_source_derived(self) -> None:
        patch = mesh_record("Patch", "PatchMesh")
        bind_square_boundary_provenance(patch)
        positions = [row["coordinate_local_m"] for row in patch["vertices"]]
        weights = [[{"bone_name": "Bone", "weight": 1.0}] for _ in range(4)]
        patch["vertices"][2]["groups"] = [{"name": "Fake", "weight": 1.0}]
        failures = r4.validate_patch_uv_and_weights(
            patch, positions, [[0, 1, 2], [0, 2, 3]], [[0, 0], [1, 0], [1, 1], [0, 1]], weights, {0, 1}, {0: 0, 1: 1, 2: 2, 3: 3}
        )
        self.assertIn("weights:source_derived_native_groups", failures)

    def test_14_rig_actions_and_material_are_compared_to_extracted_source(self) -> None:
        source = snapshot_fixture()
        candidate = copy.deepcopy(source)
        contract = contract_fixture()
        self.assertEqual(r4.validate_preserved_rig_actions_material(source, candidate, contract), set())
        candidate["state"]["armature_objects"][0]["bones"][0]["tail_local"][2] = 2.0
        candidate["state"]["actions"][0]["frame_range"] = [1.0, 3.0]
        candidate["state"]["materials"][0]["use_nodes"] = True
        failures = r4.validate_preserved_rig_actions_material(source, candidate, contract)
        self.assertIn("rig:source_exact_armature_state", failures)
        self.assertIn("actions:Act:source_exact", failures)
        self.assertIn("material:source_exact_graph", failures)
        source = snapshot_fixture()
        source["state"]["materials"][0].update(
            {
                "use_nodes": True,
                "nodes": [
                    {
                        "name": "Principled BSDF",
                        "type": "ShaderNodeBsdfPrincipled",
                        "label": "",
                        "inputs": [["Roughness", 0.45]],
                    }
                ],
                "links": [],
            }
        )
        candidate = copy.deepcopy(source)
        candidate["state"]["materials"][0]["nodes"][0]["inputs"][0][1] = 0.9
        self.assertIn(
            "material:source_exact_graph",
            r4.validate_preserved_rig_actions_material(source, candidate, contract),
        )

    def test_15_interface_and_outside_body_state_are_extracted_not_claimed(self) -> None:
        source = snapshot_fixture()
        candidate = copy.deepcopy(source)
        contract = contract_fixture()
        source["state"]["mesh_objects"][0] = two_region_body_record()
        candidate["state"]["mesh_objects"][0] = copy.deepcopy(source["state"]["mesh_objects"][0])
        contract["intersection_and_interface_requirements"]["global_interface_vertex_count"] = 2
        self.assertEqual(r4.validate_interface_and_protected_body(source, candidate, contract, {0}), set())
        candidate["state"]["mesh_objects"][0]["vertices"][0]["coordinate_local_m"][0] = 0.1
        failures = r4.validate_interface_and_protected_body(source, candidate, contract, {0})
        self.assertIn("interface:exact_extracted_vertex_state", failures)
        self.assertIn("protected_body:outside_face_topology_material", failures)

    def test_16_render_quality_comes_from_blender_loop_triangles_and_coordinates(self) -> None:
        patch = mesh_record("Patch", "PatchMesh")
        self.assertEqual(r4.validate_render_triangulation(patch, 1e-10, 12.0), set())
        patch["vertices"][2]["coordinate_local_m"] = [2.0, 0.0, 0.0]
        failures = r4.validate_render_triangulation(patch, 1e-10, 12.0)
        self.assertIn("render:minimum_triangle_area", failures)
        self.assertIn("render:minimum_triangle_angle", failures)

    def test_17_intersections_are_recomputed_from_extracted_triangle_geometry(self) -> None:
        first = [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 2.0, 0.0]]
        second = [[1.0, 0.5, -1.0], [1.0, 0.5, 1.0], [1.5, 1.0, 0.0]]
        self.assertTrue(r4.triangles_properly_intersect(first, second))
        mesh = {
            "vertices": [
                {"index": index, "coordinate_local_m": point, "groups": []}
                for index, point in enumerate(first + second)
            ],
            "polygons": [],
            "loop_triangles": [
                {"vertices": [0, 1, 2]},
                {"vertices": [3, 4, 5]},
            ],
        }
        self.assertEqual(r4.derived_self_intersections(mesh), [[0, 1]])

    def test_18_candidate_evidence_hash_or_snapshot_claim_cannot_mask_geometry(self) -> None:
        # There is intentionally no evidence-hash parameter in any geometry
        # validator. Altering raw extracted coordinates changes the result.
        patch = mesh_record("Patch", "PatchMesh")
        patch["claimed_render_pass"] = True
        patch["claimed_topology_sha256"] = "f" * 64
        patch["vertices"][2]["coordinate_local_m"] = [2.0, 0.0, 0.0]
        self.assertTrue(r4.validate_render_triangulation(patch, 1e-10, 12.0))

    def test_19_standalone_complete_patch_must_equal_actual_body_graft(self) -> None:
        source = snapshot_fixture()
        candidate = copy.deepcopy(source)
        contract = contract_fixture()
        self.assertEqual(r4.validate_actual_graft(source, candidate, contract), set())
        candidate["state"]["mesh_objects"][0]["vertices"][2]["coordinate_local_m"] = [1.2, 1.0, 0.0]
        failures = r4.validate_actual_graft(source, candidate, contract)
        self.assertIn("graft:standalone_patch_equals_body_residual", failures)
        candidate = copy.deepcopy(source)
        candidate["state"]["mesh_objects"][1]["matrix_world"][0][3] = 0.25
        self.assertIn(
            "graft:patch_body_world_transform_exact",
            r4.validate_actual_graft(source, candidate, contract),
        )

    def test_20_package_inventory_is_exact_and_audit_aware(self) -> None:
        expected = {
            "CHECKPOINT.md",
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R4_CONTRACT.json",
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R4_PROPOSAL.md",
            "PACKAGE_MANIFEST.json",
            "STATIC_TEST_RESULTS.json",
        }
        with tempfile.TemporaryDirectory(prefix="r24_r4_inventory_") as raw:
            root = Path(raw)
            for name in expected:
                (root / name).write_bytes(b"")
            self.assertEqual(r4.package_inventory_status(root)["state"], "PRE_AUDIT_EXACT")
            (root / "INDEPENDENT_STATIC_AUDIT.md").write_bytes(b"")
            self.assertEqual(r4.package_inventory_status(root)["state"], "POST_AUDIT_EXACT")
            (root / "extra").write_bytes(b"")
            self.assertEqual(r4.package_inventory_status(root)["state"], "INVALID")

    def test_21_static_package_grants_no_blender_or_body_authority(self) -> None:
        result = r4.static_evaluation()
        self.assertEqual(result["preserved_synthetic_fixture"], "REJECTED_TYPED_SDNA")
        self.assertFalse(result["future_candidate"]["eligible"])
        self.assertFalse(result["blender_used"])
        self.assertFalse(result["mesh_mutated"])
        self.assertFalse(result["candidate_created"])
        self.assertFalse(result["execution_authority_granted"])
        self.assertTrue(result["fresh_independent_static_audit_required"])

    def test_22_null_and_duplicate_semantic_old_address_pointers_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r24_r4_pointer_attacks_") as raw:
            root = Path(raw)
            for name, mode in (("null.blend", "null"), ("duplicate.blend", "duplicate")):
                path = root / name
                path.write_bytes(mini_blend(wrong_pointer=mode))
                with self.subTest(mode=mode), self.assertRaises(typed.TypedBlendError):
                    typed.parse_typed_blend(path)

    def test_23_candidate_adds_exactly_one_unlinked_patch_and_nothing_else(self) -> None:
        source = snapshot_fixture()
        source["state"]["objects"] = [row for row in source["state"]["objects"] if row["name"] != "Patch"]
        source["state"]["mesh_objects"] = [
            row for row in source["state"]["mesh_objects"] if row["object_name"] != "Patch"
        ]
        source["state"]["scenes"] = [{"name": "Scene", "object_names": ["Body", "Rig"], "camera": None}]
        candidate = copy.deepcopy(source)
        candidate["state"]["objects"].append(
            {"name": "Patch", "type": "MESH", "data_name": "PatchMesh", "parent_name": None}
        )
        candidate["state"]["mesh_objects"].append(mesh_record("Patch", "PatchMesh"))
        contract = contract_fixture()
        self.assertEqual(r4.validate_protected_object_inventory(source, candidate, contract), set())
        self.assertEqual(r4.validate_complete_protected_scene(source, candidate, contract), set())
        self.assertEqual(r4.validate_object_links(candidate, contract), set())
        candidate["state"]["objects"].append(
            {"name": "Extra", "type": "EMPTY", "data_name": None, "parent_name": None}
        )
        self.assertIn(
            "object_inventory:exact_name_set",
            r4.validate_protected_object_inventory(source, candidate, contract),
        )
        candidate["state"]["objects"].pop()
        candidate["state"]["scenes"][0]["object_names"].append("Patch")
        self.assertIn(
            "object_inventory:scene_links_source_exact_patch_unlinked",
            r4.validate_protected_object_inventory(source, candidate, contract),
        )

    def test_24_sealed_runtime_path_size_and_hash_fail_closed_without_launch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r24_r4_runtime_") as raw:
            root = Path(raw)
            exact = root / "blender.exe"
            other = root / "other.exe"
            exact.write_bytes(b"sealed")
            other.write_bytes(b"other")
            contract = {
                "authorized_runtime": {
                    "blender_executable": {
                        "path": str(exact.resolve()),
                        "bytes": exact.stat().st_size,
                        "sha256": r4.sha256_file(exact),
                    },
                    "required_version": "5.1.0",
                }
            }
            self.assertEqual(r4.validate_blender_runtime(exact, contract), exact.resolve())
            with self.assertRaises(r4.R4ExtractionError):
                r4.validate_blender_runtime(other, contract)
            exact.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                r4.validate_blender_runtime(exact, contract)

    def test_25_required_direct_action_and_material_block_hashes_are_artifact_derived(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r24_r4_direct_hash_") as raw:
            path = Path(raw) / "candidate.blend"
            path.write_bytes(mini_blend())
            summary = typed.parse_typed_blend(path)
            hashes = {
                "AC": {
                    row["name"]: row["direct_block_sha256"]
                    for row in summary["semantic_ids"]["AC"]
                }
            }
            normalized_material_hashes = {
                row["name"]: row["id_user_count_normalized_block_sha256"]
                for row in summary["semantic_ids"]["MA"]
            }
            contract = {
                "artifact_semantic_identity": {
                    "required_typed_id_names": {
                        "OB": ["Body"], "ME": ["Mesh"], "AR": ["Armature"], "AC": ["Act"], "MA": ["Skin"]
                    },
                    "required_direct_block_hashes": hashes,
                    "required_id_user_count_normalized_block_hashes": {
                        "MA": normalized_material_hashes,
                    },
                }
            }
            self.assertEqual(r4._typed_identity_failures(summary, contract), set())
            summary["semantic_ids"]["AC"][0]["direct_block_sha256"] = "0" * 64
            self.assertIn("typed_sdna:required_AC_direct_hash", r4._typed_identity_failures(summary, contract))
            summary = typed.parse_typed_blend(path)
            summary["semantic_ids"]["MA"][0]["id_user_count_normalized_block_sha256"] = "0" * 64
            self.assertIn(
                "typed_sdna:required_MA_id_us_normalized_hash",
                r4._typed_identity_failures(summary, contract),
            )

    def test_26_complete_patch_preserves_licensed_outside_and_derives_only_repaired_estar(self) -> None:
        patch = two_region_body_record()
        patch["object_name"] = "Patch"
        patch["mesh_name"] = "PatchMesh"
        patch["materials"] = ["Skin"]
        for polygon in patch["polygons"]:
            polygon["material_index"] = 0
        patch["vertices"][3]["coordinate_local_m"] = [0.0, 1.0, 0.1]
        source_mesh = {
            "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
            "normals": [[0.0, 0.0, 1.0]] * 4,
            "texcoords": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            "joints": [[0]] * 4,
            "weights": [[1.0]] * 4,
            "faces": [[0, 1, 2], [0, 2, 3]],
        }
        context = {
            "source_mesh": source_mesh,
            "bone_names": ["Bone"],
            "domains": {"outside": {0}, "estar": {1}},
        }
        contract = contract_fixture()
        contract["exact_topology"] = {"outside_face_count": 1}
        failures, repaired = r4.derive_repaired_estar_patch(patch, context, contract)
        self.assertEqual(failures, set())
        self.assertIsNotNone(repaired)
        self.assertEqual(len(repaired["polygons"]), 1)
        patch["vertices"][1]["coordinate_local_m"] = [1.1, 0.0, 0.0]
        failures, _ = r4.derive_repaired_estar_patch(patch, context, contract)
        self.assertIn("scope:all_1275_licensed_faces_outside_estar_exact", failures)

    def test_27_displaced_feature_uses_sealed_candidate_owned_origin_and_displacement(self) -> None:
        patch, positions, faces, uvs, weights = displaced_feature_fixture()

        def evaluate(value: dict[str, object]) -> set[str]:
            return r4.validate_patch_uv_and_weights(
                value,
                positions,
                faces,
                uvs,
                weights,
                {0},
                {0: 0, 1: 1, 2: 2},
                0.012,
            )

        self.assertEqual(evaluate(patch), set())

        wrong_face = copy.deepcopy(patch)
        wrong_face["attributes"][0]["data"][3] = 1
        self.assertIn("attributes:eligible_source_face", evaluate(wrong_face))

        wrong_barycentric = copy.deepcopy(patch)
        wrong_barycentric["attributes"][1]["data"][3] = [0.4, 0.3, 0.4]
        self.assertIn("attributes:normalized_barycentric_origin", evaluate(wrong_barycentric))

        substituted_displacement = copy.deepcopy(patch)
        substituted_displacement["attributes"][2]["data"][3] = [0.0, 0.0, 0.005]
        self.assertIn(
            "attributes:displacement_coordinate_binding",
            evaluate(substituted_displacement),
        )

        unbounded_displacement = copy.deepcopy(patch)
        unbounded_displacement["attributes"][2]["data"][3] = [0.0, 0.0, 0.013]
        unbounded_displacement["vertices"][3]["coordinate_local_m"] = [0.3, 0.3, 0.013]
        self.assertIn(
            "attributes:maximum_world_displacement",
            evaluate(unbounded_displacement),
        )

        moved_boundary = copy.deepcopy(patch)
        moved_boundary["attributes"][2]["data"][0] = [0.0, 0.0, 0.001]
        moved_boundary["vertices"][0]["coordinate_local_m"] = [0.0, 0.0, 0.001]
        self.assertIn("attributes:boundary_zero_displacement", evaluate(moved_boundary))

        source_scaled = copy.deepcopy(patch)
        scale = 0.00952381
        source_scaled["matrix_world"] = [
            [scale, 0.0, 0.0, 0.0],
            [0.0, scale, 0.0, 0.0],
            [0.0, 0.0, scale, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        source_scaled["attributes"][2]["data"][3] = [0.0, 0.0, 0.525]
        source_scaled["vertices"][3]["coordinate_local_m"] = [0.3, 0.3, 0.525]
        self.assertEqual(evaluate(source_scaled), set())

        source_scaled_too_far = copy.deepcopy(source_scaled)
        source_scaled_too_far["attributes"][2]["data"][3] = [0.0, 0.0, 1.27]
        source_scaled_too_far["vertices"][3]["coordinate_local_m"] = [0.3, 0.3, 1.27]
        self.assertIn(
            "attributes:maximum_world_displacement",
            evaluate(source_scaled_too_far),
        )

    def test_28_inherited_outside_sliver_is_exact_but_only_replacement_is_quality_gated(self) -> None:
        complete = two_region_body_record()
        complete["object_name"] = "Patch"
        complete["mesh_name"] = "PatchMesh"
        complete["materials"] = ["Skin"]
        for polygon in complete["polygons"]:
            polygon["material_index"] = 0
        for triangle in complete["loop_triangles"]:
            triangle["material_index"] = 0
        source_positions = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.01, 0.0001, 0.0],
            [0.0, 0.02, 0.0],
        ]
        candidate_positions = copy.deepcopy(source_positions)
        candidate_positions[3] = [0.0, 0.01, 0.004]
        for index, coordinate in enumerate(candidate_positions):
            complete["vertices"][index]["coordinate_local_m"] = coordinate
        source_uvs = [[0.0, 0.0], [1.0, 0.0], [0.01, 0.0001], [0.0, 0.02]]
        loop_vertices = [0, 1, 2, 0, 2, 3]
        for row, vertex in zip(complete["uv_layers"][0]["data"], loop_vertices, strict=True):
            row["uv"] = copy.deepcopy(source_uvs[vertex])
        context = {
            "source_mesh": {
                "positions": source_positions,
                "normals": [[0.0, 0.0, 1.0]] * 4,
                "texcoords": source_uvs,
                "joints": [[0]] * 4,
                "weights": [[1.0]] * 4,
                "faces": [[0, 1, 2], [0, 2, 3]],
            },
            "bone_names": ["Bone"],
            "domains": {"outside": {0}, "estar": {1}},
        }
        contract = contract_fixture()
        contract["exact_topology"] = {"outside_face_count": 1}
        failures, replacement = r4.derive_repaired_estar_patch(complete, context, contract)
        self.assertEqual(failures, set())
        self.assertIsNotNone(replacement)
        self.assertEqual(r4.validate_extracted_triangulation_identity(complete), set())
        self.assertEqual(r4.validate_render_triangulation(replacement, 1e-10, 12.0), set())

        replacement_sliver = copy.deepcopy(replacement)
        replacement_sliver["vertices"][1]["coordinate_local_m"] = [1.0, 0.0, 0.0]
        replacement_sliver["vertices"][2]["coordinate_local_m"] = [2.0, 0.001, 0.0]
        self.assertIn(
            "render:minimum_triangle_angle",
            r4.validate_render_triangulation(replacement_sliver, 1e-10, 12.0),
        )

        replacement_zero_area = copy.deepcopy(replacement)
        replacement_zero_area["vertices"][1]["coordinate_local_m"] = [1.0, 0.0, 0.0]
        replacement_zero_area["vertices"][2]["coordinate_local_m"] = [2.0, 0.0, 0.0]
        self.assertIn(
            "render:minimum_triangle_area",
            r4.validate_render_triangulation(replacement_zero_area, 1e-10, 12.0),
        )

        outside_drift = copy.deepcopy(complete)
        outside_drift["vertices"][1]["coordinate_local_m"] = [1.1, 0.0, 0.0]
        failures, _ = r4.derive_repaired_estar_patch(outside_drift, context, contract)
        self.assertIn("scope:all_1275_licensed_faces_outside_estar_exact", failures)

    def test_29_neutral_patch_preserves_exact_inherited_outside_pairs_only(self) -> None:
        inherited = intersection_pair(0, 1)
        removable_cross = intersection_pair(1, 2, distance=1.25)
        expected_all = r4._stable_patch_pair_records([inherited, removable_cross])
        expected_outside = r4._stable_patch_pair_records([inherited])
        self.assertIsNotNone(expected_all)
        self.assertIsNotNone(expected_outside)
        source = {
            "scope": "source_body_patch_material_region",
            "extracted_object_name": "Body",
            "exact_genuine_penetration_pair_count": 2,
            "pairs": [inherited, removable_cross],
        }
        candidate = {
            "scope": "complete_private_patch_object",
            "extracted_object_name": "Patch",
            "exact_genuine_penetration_pair_count": 1,
            "pairs": [copy.deepcopy(inherited)],
        }

        def validate(value: dict[str, object]) -> set[str]:
            return r4.validate_neutral_patch_pair_partition(
                source,
                value,
                {0, 1},
                expected_all,
                expected_outside,
                source_object_name="Body",
                candidate_object_name="Patch",
            )

        self.assertEqual(validate(candidate), set())
        missing = copy.deepcopy(candidate)
        missing["pairs"] = []
        missing["exact_genuine_penetration_pair_count"] = 0
        self.assertIn("intersections:exact_214_inherited_outside_pairs", validate(missing))
        changed = copy.deepcopy(candidate)
        changed["pairs"][0]["center_distance_m"] = 1.5
        self.assertIn("intersections:exact_214_inherited_outside_pairs", validate(changed))
        additional = copy.deepcopy(candidate)
        additional["pairs"].append(copy.deepcopy(inherited))
        additional["exact_genuine_penetration_pair_count"] = 2
        self.assertIn("intersections:exact_214_inherited_outside_pairs", validate(additional))
        cross = copy.deepcopy(candidate)
        cross["pairs"].append(copy.deepcopy(removable_cross))
        cross["exact_genuine_penetration_pair_count"] = 2
        self.assertIn("intersections:replacement_or_cross_boundary_neutral_pair", validate(cross))

    def test_30_material_direct_hash_normalizes_only_typed_id_user_count(self) -> None:
        schema = typed.SDNASchema(
            names=("name[66]", "us", "id"),
            types=("char", "short", "ID", "Material"),
            type_lengths=(1, 2, 68, 68),
            structures=(
                typed.SDNAStruct(2, (typed.SDNAField(0, 0), typed.SDNAField(1, 1))),
                typed.SDNAStruct(3, (typed.SDNAField(2, 2),)),
            ),
        )

        def block(users: int, *, tamper: bool = False) -> typed.BlendBlock:
            payload = bytearray(68)
            payload[:8] = b"MAMat\x00\x00\x00"
            struct.pack_into("<h", payload, 66, users)
            if tamper:
                payload[20] = 1
            return typed.BlendBlock("MA", 68, 1, 1, 1, bytes(payload))

        first = block(1)
        second = block(2)
        self.assertNotEqual(
            hashlib.sha256(first.payload).hexdigest(),
            hashlib.sha256(second.payload).hexdigest(),
        )
        self.assertEqual(
            typed.id_user_count_normalized_block_sha256(schema, first, 8),
            typed.id_user_count_normalized_block_sha256(schema, second, 8),
        )
        self.assertNotEqual(
            typed.id_user_count_normalized_block_sha256(schema, first, 8),
            typed.id_user_count_normalized_block_sha256(schema, block(2, tamper=True), 8),
        )


if __name__ == "__main__":
    unittest.main()
