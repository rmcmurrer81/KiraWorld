from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest

from tools import kira_r25_canonical_receipt as receipt
from tools.kira_r25_semantic_cage_correspondence_core import (
    FIXED_SCALE,
    REGIONS,
    SemanticCageError,
    Triangle,
    build_correspondence_receipt,
    canonical_bytes,
    decode_mapping_records,
    semantic_region_for_group,
    select_geodesic_anchors,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_semantic_cage_correspondence_diagnostic_v1.json"
CORE = ROOT / "tools/kira_r25_semantic_cage_correspondence_core.py"
WRAPPER = ROOT / "tools/blender_diagnose_kira_r25_semantic_cage_correspondence.py"


def transformed(point: tuple[float, float, float]) -> tuple[float, float, float]:
    angle = math.radians(17.0)
    cosine, sine, scale = math.cos(angle), math.sin(angle), 1.15
    x = scale * (cosine * point[0] - sine * point[1]) + 0.12
    y = scale * (sine * point[0] + cosine * point[1]) - 0.08
    z = scale * point[2] + 0.04
    return (x, y, z)


def fixture() -> dict[str, object]:
    source_vertices: list[tuple[float, float, float]] = []
    source_normals: list[tuple[float, float, float]] = []
    source_faces: list[list[int]] = []
    source_regions: list[str] = []
    target_vertices: list[tuple[float, float, float]] = []
    target_regions: list[str] = []
    target_triangles: list[Triangle] = []
    for region_index, region in enumerate(REGIONS):
        center_x = (region_index % 4) * 0.2
        center_y = (region_index // 4) * 0.23
        center_z = (region_index % 3) * 0.07
        base = len(source_vertices)
        local = [
            (center_x - 0.02, center_y - 0.02, center_z),
            (center_x + 0.02, center_y - 0.02, center_z),
            (center_x + 0.02, center_y + 0.02, center_z),
            (center_x - 0.02, center_y + 0.02, center_z),
        ]
        source_vertices.extend(local)
        source_normals.extend([(0.0, 0.0, 1.0)] * 4)
        source_regions.extend([region] * 4)
        source_faces.extend([[base, base + 1, base + 2], [base, base + 2, base + 3]])
        target_base = len(target_vertices)
        target_vertices.extend(transformed(value) for value in local)
        target_regions.extend([region] * 4)
        face_base = region_index * 2
        target_triangles.extend(
            [
                Triangle(face_base, 0, (target_base, target_base + 1, target_base + 2)),
                Triangle(face_base + 1, 0, (target_base, target_base + 2, target_base + 3)),
            ]
        )
    return {
        "source_vertices": source_vertices,
        "source_normals": source_normals,
        "source_faces": source_faces,
        "source_regions": source_regions,
        "target_vertices": target_vertices,
        "target_regions": target_regions,
        "target_triangles": target_triangles,
    }


def build(**overrides: object) -> dict[str, object]:
    values = fixture()
    values.update(overrides)
    anchors = {region: 1 for region in REGIONS}
    maximum_distance = int(values.get("maximum_distance_um", 100))
    maximums = {region: maximum_distance for region in REGIONS}
    dots = {region: 900_000_000 for region in REGIONS}
    return build_correspondence_receipt(
        source_vertices=values["source_vertices"],
        source_normals=values["source_normals"],
        source_faces=values["source_faces"],
        source_regions=values["source_regions"],
        target_vertices=values["target_vertices"],
        target_regions=values["target_regions"],
        target_triangles=values["target_triangles"],
        excluded_target_faces=set(values.get("excluded_target_faces", set())),
        locked_source_vertices=set(values.get("locked_source_vertices", set())),
        lock_summary={"locked_vertex_count": len(set(values.get("locked_source_vertices", set())))},
        anchors_per_region=anchors,
        max_distance_um=maximums,
        min_normal_dot_fixed=dots,
        bindings={"fixture": "exact"},
    )


class R25SemanticCagePreparationTests(unittest.TestCase):
    def test_01_semantic_group_mapping_keeps_left_and_right_separate(self) -> None:
        expected = {
            "upperarm01.L": "upper_arm.L",
            "mixamorig:RightArm_014": "upper_arm.R",
            "lowerarm02.L": "lower_arm.L",
            "mixamorig:RightForeArm_015": "lower_arm.R",
            "finger1-1.L": "hand.L",
            "mixamorig:RightHand_016": "hand.R",
            "upperleg01.L": "thigh.L",
            "mixamorig:RightUpLeg_060": "thigh.R",
            "lowerleg01.L": "shin.L",
            "mixamorig:RightLeg_061": "shin.R",
            "foot.L": "foot.L",
            "mixamorig:RightFoot_062": "foot.R",
            "jaw": "face",
            "head": "head",
            "neck01": "neck",
            "spine03": "torso",
        }
        self.assertEqual({name: semantic_region_for_group(name) for name in expected}, expected)
        self.assertIsNone(semantic_region_for_group("unrecognized_helper"))
        self.assertIsNone(semantic_region_for_group("upperarm"))

    def test_02_receipt_is_deterministic_compact_and_round_trips(self) -> None:
        first, second = build(), build()
        self.assertEqual(first, second)
        self.assertLess(len(canonical_bytes(first)), receipt.MAX_RECEIPT_PAYLOAD_BYTES)
        framed = receipt.encode_receipt_frame(first)
        self.assertEqual(receipt.decode_receipt_frame(framed).payload, first)
        decoded = decode_mapping_records(first["mapping_records_base64"], first["mapping_count"])
        self.assertEqual(len(decoded), len(REGIONS))
        self.assertEqual(first["mapping_binary_sha256"], hashlib.sha256(
            __import__("base64").b64decode(first["mapping_records_base64"])
        ).hexdigest())

    def test_03_r20_mask_faces_are_excluded_and_barycentrics_are_exact(self) -> None:
        output = build(excluded_target_faces={0}, maximum_distance_um=1_000_000)
        records = decode_mapping_records(output["mapping_records_base64"], output["mapping_count"])
        self.assertNotIn(0, {row["r19_face_index"] for row in records})
        for row in records:
            barycentric = row["barycentric_fixed_1e9"]
            self.assertEqual(sum(barycentric), FIXED_SCALE)
            self.assertTrue(all(0 <= value <= FIXED_SCALE for value in barycentric))
            self.assertEqual(row["foundation_region"], row["target_region"])

    def test_04_normal_incompatibility_fails_instead_of_using_nearest_surface(self) -> None:
        values = fixture()
        reversed_triangles = [
            Triangle(item.face_index, item.triangle_index, (item.vertex_indices[0], item.vertex_indices[2], item.vertex_indices[1]))
            for item in values["target_triangles"]
        ]
        with self.assertRaisesRegex(SemanticCageError, "normal_compatible_target_unavailable"):
            build(target_triangles=reversed_triangles)

    def test_05_distance_gate_rejects_a_geometrically_remote_region(self) -> None:
        values = fixture()
        shifted = list(values["target_vertices"])
        for index in range(4):
            shifted[index] = (shifted[index][0], shifted[index][1], shifted[index][2] + 0.2)
        with self.assertRaisesRegex(SemanticCageError, "target_distance_gate_failed"):
            build(target_vertices=shifted)

    def test_06_missing_region_fails_without_coordinate_fallback(self) -> None:
        values = fixture()
        target_regions = list(values["target_regions"])
        target_regions[:4] = ["head"] * 4
        with self.assertRaisesRegex(SemanticCageError, "required_region_mapping_unavailable:face"):
            build(target_regions=target_regions)

    def test_07_afes_lock_vertices_cannot_be_selected_as_anchors(self) -> None:
        values = fixture()
        face_vertices = [index for index, region in enumerate(values["source_regions"]) if region == "face"]
        selected = select_geodesic_anchors(
            values["source_vertices"],
            values["source_faces"],
            values["source_regions"],
            {face_vertices[0]},
            {"face": 2},
        )
        self.assertNotIn(face_vertices[0], selected["face"])
        with self.assertRaisesRegex(SemanticCageError, "minimum_anchor_coverage_unavailable"):
            select_geodesic_anchors(
                values["source_vertices"],
                values["source_faces"],
                values["source_regions"],
                set(face_vertices),
                {"face": 1},
            )

    def test_08_static_config_binds_exact_inputs_and_existing_receipt_limits(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["alignment_and_anchor_contract"]["total_required_anchor_count"], 432)
        self.assertEqual(config["bindings"]["r20_exact_rejected_target_region"]["selected_faces"], 376)
        self.assertEqual(config["bindings"]["qualified_foundation_blend"]["vertices"], 14658)
        self.assertEqual(config["bindings"]["foundation_afes_extraction_contract"]["afes_union_vertices"], 1169)
        transport = config["bindings"]["canonical_receipt_primitive"]
        self.assertEqual(transport["maximum_payload_bytes"], receipt.MAX_RECEIPT_PAYLOAD_BYTES)
        self.assertEqual(transport["maximum_depth"], receipt.MAX_RECEIPT_DEPTH)
        self.assertEqual(transport["maximum_nodes"], receipt.MAX_RECEIPT_NODES)
        for row in config["bindings"].values():
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["sha256"])

    def test_09_blender_wrapper_is_inert_handle_only_and_has_no_authoring_calls(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("--lock-handle", source)
        self.assertIn("--result-handle", source)
        self.assertIn("encode_receipt_frame", source)
        self.assertIn("decode_receipt_frame", source)
        self.assertNotIn("--result-path", source)
        self.assertNotIn("bpy.ops", source)
        self.assertNotIn("save_as_mainfile", source)
        self.assertNotIn("render.render", source)
        self.assertNotIn("export_scene", source)


if __name__ == "__main__":
    unittest.main()
