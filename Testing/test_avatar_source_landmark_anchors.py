from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import Core.avatar_source_landmark_anchors as landmarks
from Core.avatar_anatomy_package import evaluate_avatar_anatomy_package_preflight
from Core.avatar_source_landmark_anchors import SourceLandmarkAnchorError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXACT_REQUEST = PROJECT_ROOT / (
    "Avatar/avatar_builder/anatomy_packages/"
    "kira_internal_pelvis_source_preflight_v1_20260820/PREFLIGHT_REQUEST.json"
)
EXACT_PELVIS = PROJECT_ROOT / (
    "Avatar/avatar_builder/asset_library/medical_reference/"
    "hra_female_pelvis_cc_by_4_v1_2/VH_F_Pelvis.glb"
)
CHECKED_IN_RECEIPT = PROJECT_ROOT / (
    "Avatar/avatar_builder/anatomy_packages/"
    "kira_internal_pelvis_source_preflight_v1_20260820/"
    "SOURCE_DERIVED_ORIENTATION_LANDMARK_RECEIPT.json"
)
CHECKED_IN_REPORT = EXACT_REQUEST.with_name("PREFLIGHT_REPORT.json")
PREFLIGHT_CLI = PROJECT_ROOT / "tools/evaluate_avatar_anatomy_package_preflight.py"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def cube(center: tuple[float, float, float], half: float = 0.01) -> list[tuple[float, float, float]]:
    return [
        tuple(center[axis] + delta[axis] for axis in range(3))
        for delta in itertools.product((-half, half), repeat=3)
    ]


def write_landmark_glb(
    path: Path,
    *,
    swapped_sides: bool = False,
    degenerate_sacrum: bool = False,
    reused_side_accessor: bool = False,
) -> None:
    mesh_names = [
        "VH_F_pubis_compact_bone_L",
        "VH_F_pubis_compact_bone_R",
        "VH_F_pubis_spongy_bone_L",
        "VH_F_pubis_spongy_bone_R",
        "VH_F_sacrum",
        "VH_F_ilium_compact_bone_L",
        "VH_F_ilium_compact_bone_R",
    ]
    left_x, right_x = (-0.2, 0.2) if swapped_sides else (0.2, -0.2)
    point_sets = [
        cube((0.03, 0.00, 0.25)),
        cube((-0.03, 0.00, 0.25)),
        cube((0.04, 0.01, 0.23)),
        cube((-0.04, 0.01, 0.23)),
        cube((0.00, 0.10, -0.25), 0.0 if degenerate_sacrum else 0.01),
        cube((left_x, 0.10, -0.05)),
        cube((right_x, 0.10, -0.05)),
    ]
    binary_parts: list[bytes] = []
    buffer_views: list[dict[str, int]] = []
    accessors: list[dict[str, object]] = []
    offset = 0
    for points in point_sets:
        packed = b"".join(struct.pack("<3f", *point) for point in points)
        binary_parts.append(packed)
        buffer_views.append(
            {"buffer": 0, "byteOffset": offset, "byteLength": len(packed)}
        )
        accessors.append(
            {
                "bufferView": len(buffer_views) - 1,
                "componentType": 5126,
                "count": len(points),
                "type": "VEC3",
                "min": [min(point[axis] for point in points) for axis in range(3)],
                "max": [max(point[axis] for point in points) for axis in range(3)],
            }
        )
        offset += len(packed)
    position_accessors = list(range(len(mesh_names)))
    if reused_side_accessor:
        position_accessors[-1] = position_accessors[-2]
    document = {
        "asset": {"version": "2.0", "generator": "hostile-landmark-fixture"},
        "buffers": [{"byteLength": offset}],
        "bufferViews": buffer_views,
        "accessors": accessors,
        "meshes": [
            {
                "name": name,
                "primitives": [
                    {"attributes": {"POSITION": position_accessors[index]}}
                ],
            }
            for index, name in enumerate(mesh_names)
        ],
        "nodes": [
            {"name": "VH_F_pubis", "children": [1, 2, 3, 4]},
            {"name": mesh_names[0], "mesh": 0},
            {"name": mesh_names[1], "mesh": 1},
            {"name": mesh_names[2], "mesh": 2},
            {"name": mesh_names[3], "mesh": 3},
            {"name": mesh_names[4], "mesh": 4},
            {"name": mesh_names[5], "mesh": 5},
            {"name": mesh_names[6], "mesh": 6},
        ],
        "scene": 0,
        "scenes": [{"nodes": [0, 5, 6, 7]}],
    }
    json_payload = canonical_bytes(document)
    json_payload += b" " * ((4 - len(json_payload) % 4) % 4)
    binary_payload = b"".join(binary_parts)
    total = 12 + 8 + len(json_payload) + 8 + len(binary_payload)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<II", len(json_payload), 0x4E4F534A)
        + json_payload
        + struct.pack("<II", len(binary_payload), 0x004E4942)
        + binary_payload
    )


class PelvicLandmarkAnchorTests(unittest.TestCase):
    def synthetic_source(self, **options: bool) -> tuple[Path, mock._patch, mock._patch]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / landmarks.SOURCE_FILE
        write_landmark_glb(path, **options)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        bytes_patch = mock.patch.object(landmarks, "SOURCE_BYTES", path.stat().st_size)
        sha_patch = mock.patch.object(landmarks, "SOURCE_SHA256", digest)
        bytes_patch.start()
        sha_patch.start()
        self.addCleanup(bytes_patch.stop)
        self.addCleanup(sha_patch.stop)
        return path, bytes_patch, sha_patch

    def arguments(self, path: Path) -> dict[str, object]:
        return {
            "expected_source_file": landmarks.SOURCE_FILE,
            "expected_bytes": path.stat().st_size,
            "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_units": "meters",
            "source_axes": copy.deepcopy(landmarks.SOURCE_AXES),
            "target_units": "meters",
            "target_axes": copy.deepcopy(landmarks.TARGET_AXES),
            "normalization_transform": list(landmarks.NORMALIZATION_TRANSFORM),
        }

    def test_exact_receipt_is_deterministic_and_binary_source_bound(self) -> None:
        path = self.synthetic_source()[0]
        arguments = self.arguments(path)
        first = landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)
        second = landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)

        self.assertEqual(first, second)
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        self.assertEqual(len(first["landmarks"]), 4)
        self.assertTrue(first["algorithm"]["uses_binary_position_values"])
        self.assertFalse(first["truth_limits"]["counts_as_anatomy_components"])
        self.assertFalse(first["truth_limits"]["internal_anatomy_complete"])
        self.assertFalse(first["truth_limits"]["whole_body_complete"])
        for item in first["landmarks"]:
            self.assertEqual(item["source_file_sha256"], arguments["expected_sha256"])
            self.assertFalse(item["counts_as_anatomy_component"])
            self.assertFalse(item["tissue_or_organ_claim"])
            self.assertFalse(item["authored"])

    def test_wrong_source_hash_and_node_fail_closed(self) -> None:
        path = self.synthetic_source()[0]
        arguments = self.arguments(path)
        arguments["expected_sha256"] = "0" * 64
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "SHA-256 mismatch"):
            landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)

        arguments = self.arguments(path)
        arguments["expected_source_file"] = "other.glb"
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "file binding mismatch"):
            landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)

        bad_specs = copy.deepcopy(landmarks.LANDMARK_SPECS)
        bad_specs[0]["source_node"] = "VH_F_not_a_real_pubis"
        with mock.patch.object(landmarks, "LANDMARK_SPECS", tuple(bad_specs)):
            with self.assertRaisesRegex(SourceLandmarkAnchorError, "source node is missing"):
                landmarks.derive_pelvic_landmark_anchor_receipt(
                    path,
                    **self.arguments(path),
                )

    def test_wrong_units_axes_and_transform_fail_closed(self) -> None:
        path = self.synthetic_source()[0]
        arguments = self.arguments(path)
        arguments["source_units"] = "millimeters"
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "source units/axes mismatch"):
            landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)

        arguments = self.arguments(path)
        arguments["source_axes"] = {"up": "+Z", "forward": "+Y", "handedness": "right"}
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "source units/axes mismatch"):
            landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)

        arguments = self.arguments(path)
        arguments["normalization_transform"] = [1.0] * 16
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "transform mismatch"):
            landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)

    def test_degenerate_bounds_and_swapped_sides_fail_closed(self) -> None:
        path = self.synthetic_source(degenerate_sacrum=True)[0]
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "bounds are degenerate"):
            landmarks.derive_pelvic_landmark_anchor_receipt(
                path,
                **self.arguments(path),
            )

        path = self.synthetic_source(swapped_sides=True)[0]
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "left/right.*swapped"):
            landmarks.derive_pelvic_landmark_anchor_receipt(
                path,
                **self.arguments(path),
            )

    def test_reused_geometry_and_component_spoof_fail_closed(self) -> None:
        path = self.synthetic_source(reused_side_accessor=True)[0]
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "cannot reuse POSITION geometry"):
            landmarks.derive_pelvic_landmark_anchor_receipt(
                path,
                **self.arguments(path),
            )

        path = self.synthetic_source()[0]
        arguments = self.arguments(path)
        receipt = landmarks.derive_pelvic_landmark_anchor_receipt(path, **arguments)
        spoofed = copy.deepcopy(receipt)
        spoofed["truth_limits"]["counts_as_anatomy_components"] = True
        spoofed["landmarks"][0]["counts_as_anatomy_component"] = True
        with self.assertRaisesRegex(SourceLandmarkAnchorError, "differs from exact re-derivation"):
            landmarks.validate_pelvic_landmark_anchor_receipt(
                spoofed,
                path,
                **arguments,
            )

    def test_checked_in_preflight_integrates_without_weakening_truth_gates(self) -> None:
        request = json.loads(EXACT_REQUEST.read_text(encoding="utf-8"))
        source_before = hashlib.sha256(EXACT_PELVIS.read_bytes()).hexdigest()
        report = evaluate_avatar_anatomy_package_preflight(PROJECT_ROOT, request)
        source_after = hashlib.sha256(EXACT_PELVIS.read_bytes()).hexdigest()

        receipt = report["source_derived_orientation_landmarks"]
        self.assertEqual(receipt["status"], landmarks.RECEIPT_STATUS)
        self.assertEqual(len(receipt["landmarks"]), 4)
        self.assertEqual(report["mapped_structure_count"], 13)
        self.assertEqual(len(report["components"]), 13)
        self.assertEqual(len(report["missing_required_structures"]), 15)
        for still_missing in (
            "pubic_landmark_empty",
            "sacral_landmark_empty",
            "pelvic_side_anchor_left",
            "pelvic_side_anchor_right",
            "vaginal_canal",
            "female_urethra_shell",
        ):
            self.assertIn(still_missing, report["missing_required_structures"])
        self.assertNotIn("missing_source_anchor:pubic_reference", report["blockers"])
        self.assertIn("missing_source_anchor:anal_opening", report["blockers"])
        self.assertFalse(report["truth"]["internal_anatomy_complete"])
        self.assertFalse(report["scope"]["whole_body_complete"])
        self.assertFalse(report["build_performed"])
        self.assertFalse(report["blender_invoked"])
        self.assertEqual(source_before, source_after)

        checked_in = json.loads(CHECKED_IN_RECEIPT.read_text(encoding="utf-8"))
        exact_arguments = {
            "expected_source_file": landmarks.SOURCE_FILE,
            "expected_bytes": landmarks.SOURCE_BYTES,
            "expected_sha256": landmarks.SOURCE_SHA256,
            "source_units": "meters",
            "source_axes": landmarks.SOURCE_AXES,
            "target_units": "meters",
            "target_axes": landmarks.TARGET_AXES,
            "normalization_transform": landmarks.NORMALIZATION_TRANSFORM,
        }
        validated = landmarks.validate_pelvic_landmark_anchor_receipt(
            checked_in,
            EXACT_PELVIS,
            **exact_arguments,
        )
        self.assertEqual(checked_in, validated)
        self.assertEqual(receipt, checked_in)
        self.assertEqual(
            report,
            json.loads(CHECKED_IN_REPORT.read_text(encoding="utf-8")),
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-W",
                "error",
                str(PREFLIGHT_CLI),
                "--project-root",
                str(PROJECT_ROOT),
                "--request",
                EXACT_REQUEST.relative_to(PROJECT_ROOT).as_posix(),
                "--compact",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(completed.stdout, CHECKED_IN_REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
