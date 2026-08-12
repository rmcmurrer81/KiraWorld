#!/usr/bin/env python3
"""Pure-Python acceptance tests for R25 AFES extraction Attempt 02.

These tests never import bpy, launch Blender, create a pipe/process, or grant
execution/body-authoring authority.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest

from tools import kira_r25_afes_topology_core as attempt01_core
from tools import kira_r25_afes_topology_core_v2 as core
from tools import kira_r25_canonical_receipt as receipt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v2.json"
)
EXTRACTOR = ROOT / "tools/blender_extract_kira_r25_foundation_afes_transition_rings_v2.py"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_no_float(test: unittest.TestCase, value: object, location: str = "root") -> None:
    test.assertNotIsInstance(value, float, location)
    if isinstance(value, dict):
        for key, child in value.items():
            assert_no_float(test, child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_float(test, child, f"{location}[{index}]")


def toy_analysis() -> dict[str, object]:
    analysis = attempt01_core.analyze_afes_topology(
        vertex_count=7,
        edges=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)],
        faces=[(0, 1, 2), (2, 3, 4), (4, 5, 6)],
        memberships={"AFES_A": [2], "AFES_B": [2]},
        required_group_names=["AFES_A", "AFES_B"],
        transition_ring_count=2,
    )
    analysis["topology_structure"] = {
        "full_normalized_topology_sha256": analysis["whole_mesh"]["topology_sha256"],
        "connected_component_count": 1,
        "isolated_vertex_count": 0,
        "boundary_edge_count": 0,
        "nonmanifold_edge_count": 0,
        "loose_edge_count": 0,
        "face_boundary_edge_missing_from_mesh_count": 0,
        "duplicate_face_record_count": 0,
        "transition_ring_loose_edge_incidence_count": 0,
    }
    return analysis


def toy_compact() -> dict[str, object]:
    return core.compact_afes_analysis(
        toy_analysis(),
        {
            "unit": "nanometer",
            "integer_units_per_meter": 1_000_000_000,
            "rounding": core.ROUNDING_RULE,
            "minimum": [-1, -2, -3],
            "maximum": [1, 2, 3],
        },
    )


class FakeKernel32:
    def __init__(self, file_type: int) -> None:
        self.file_type = file_type
        self.calls = 0

    def GetFileType(self, handle: object) -> int:
        self.calls += 1
        self.last_handle = handle
        return self.file_type


class Attempt02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_attempt01_is_byte_for_byte_preserved(self) -> None:
        expected = {
            "config": (6989, "3f1f57d95a28287f024cd6806af9180c623d134b68249a547cb81475f8fe5fdc"),
            "topology_core": (10005, "972d5cdd5c9b9f511388607350b8c950e7b92df942e5d897eac98d08acfbfdce"),
            "extractor": (18513, "706a1035354bb133a8cc2a2c0dbeff414f6f1172bbedaaf7dafbf70e14c57bc2"),
            "tests": (7352, "6132c8fc82f60f924f81a4124358369ee2af6e51924e5b59aaa8d0b5f6588eb5"),
            "checkpoint": (4673, "5c96a9c5da3303733f431344223f64736a7148e2361d6d3e69d34cf31015b84a"),
        }
        self.assertEqual(self.config["attempt_01_preservation"], {
            key: self.config["attempt_01_preservation"][key] for key in expected
        })
        for key, (size, digest) in expected.items():
            row = self.config["attempt_01_preservation"][key]
            path = ROOT / row["path"]
            self.assertEqual((path.stat().st_size, file_sha256(path)), (size, digest))
            self.assertEqual((row["bytes"], row["sha256"]), (size, digest))

    def test_all_attempt02_code_and_receipt_bindings_are_exact(self) -> None:
        for label in (
            "canonical_receipt_helper", "attempt_02_topology_core", "attempt_02_extractor"
        ):
            row = self.config["bindings"][label]
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"])
            self.assertEqual(file_sha256(path), row["sha256"])
        self.assertEqual(
            Path(receipt.__file__).resolve(),
            (ROOT / self.config["bindings"]["canonical_receipt_helper"]["path"]).resolve(),
        )
        self.assertEqual(
            Path(core.__file__).resolve(),
            (ROOT / self.config["bindings"]["attempt_02_topology_core"]["path"]).resolve(),
        )

    def test_quantization_is_integer_signed64_and_half_even(self) -> None:
        self.assertEqual(core.meters_float_to_nanometers(0.0000000005), 0)
        self.assertEqual(core.meters_float_to_nanometers(0.0000000015), 2)
        self.assertEqual(core.meters_float_to_nanometers(-0.0000000005), 0)
        bounds = core.quantize_bounds_to_nanometers(
            {"minimum": [-0.053596877, -0.133306563, 0.679080844],
             "maximum": [0.053596877, -0.007144271, 0.898148775]}
        )
        self.assertEqual(
            bounds["minimum"], [-53596877, -133306563, 679080844]
        )
        self.assertEqual(bounds["maximum"], [53596877, -7144271, 898148775])
        assert_no_float(self, bounds)
        with self.assertRaises(core.CompactAfesEvidenceError):
            core.meters_float_to_nanometers(float("nan"))

    def test_topology_structure_proves_closed_single_component_and_exact_digest(self) -> None:
        edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
        result = core.analyze_foundation_topology_structure(
            vertex_count=4, edges=edges, faces=faces, transition_vertices=(0, 1)
        )
        self.assertEqual(result["connected_component_count"], 1)
        for key, value in result.items():
            if key != "full_normalized_topology_sha256" and key != "connected_component_count":
                self.assertEqual(value, 0, key)
        self.assertEqual(
            result["full_normalized_topology_sha256"],
            attempt01_core.canonical_json_sha256(
                {"vertex_count": 4, "edges": [list(edge) for edge in edges],
                 "faces": [list(face) for face in faces]}
            ),
        )

    def test_topology_structure_detects_boundary_loose_missing_and_duplicate(self) -> None:
        result = core.analyze_foundation_topology_structure(
            vertex_count=5,
            edges=[(0, 1), (1, 2), (0, 2), (3, 4)],
            faces=[(0, 1, 2), (2, 1, 0)],
            transition_vertices=(3,),
        )
        self.assertEqual(result["connected_component_count"], 2)
        self.assertEqual(result["duplicate_face_record_count"], 1)
        self.assertEqual(result["loose_edge_count"], 1)
        self.assertEqual(result["transition_ring_loose_edge_incidence_count"], 1)
        missing = core.analyze_foundation_topology_structure(
            vertex_count=3, edges=[(0, 1), (1, 2)], faces=[(0, 1, 2)]
        )
        self.assertEqual(missing["face_boundary_edge_missing_from_mesh_count"], 1)

    def test_compact_roundtrip_dedupes_and_verifies_ring_digests(self) -> None:
        compact = toy_compact()
        decoded = core.validate_compact_afes_analysis(compact)
        self.assertEqual(decoded["afes_union"], (2,))
        self.assertEqual(decoded["transition_rings"], ((1, 3), (0, 4)))
        group_refs = [
            compact["groups"][name]["vertex_indices"]["blob_ref"]
            for name in ("AFES_A", "AFES_B")
        ]
        self.assertEqual(group_refs[0], group_refs[1])
        self.assertLess(len(compact["binary_arrays"]), 10)
        def check_no_explicit_index_lists(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"vertex_indices", "incident_face_indices", "internal_face_indices"}:
                        self.assertIsInstance(child, dict)
                    check_no_explicit_index_lists(child)
            elif isinstance(value, list):
                for child in value:
                    check_no_explicit_index_lists(child)
        check_no_explicit_index_lists(compact)

    def test_binary_count_base64_raw_and_semantic_corruption_are_rejected(self) -> None:
        original = toy_compact()
        blob_ref = next(iter(original["binary_arrays"]))
        cases = []
        bad = copy.deepcopy(original)
        bad["binary_arrays"][blob_ref]["u32_count"] += 1
        cases.append(bad)
        bad = copy.deepcopy(original)
        raw = base64.b64decode(bad["binary_arrays"][blob_ref]["base64"])
        bad["binary_arrays"][blob_ref]["base64"] = base64.b64encode(raw + b"x").decode()
        cases.append(bad)
        bad = copy.deepcopy(original)
        bad["binary_arrays"][blob_ref]["raw_sha256"] = "0" * 64
        cases.append(bad)
        bad = copy.deepcopy(original)
        bad["transition_rings"]["rings"][0]["vertex_indices"]["semantic_sha256"] = "0" * 64
        cases.append(bad)
        for bad_case in cases:
            with self.assertRaises(core.CompactAfesEvidenceError):
                core.validate_compact_afes_analysis(bad_case)

    def test_canonical_receipt_roundtrip_is_float_free_and_bounded(self) -> None:
        payload = {"schema": "test.r25.attempt02", "analysis": toy_compact()}
        assert_no_float(self, payload)
        frame = receipt.encode_receipt_frame(payload)
        decoded = receipt.decode_receipt_frame(frame)
        self.assertEqual(decoded.payload, payload)
        self.assertLessEqual(len(decoded.canonical_payload), receipt.MAX_RECEIPT_PAYLOAD_BYTES)
        self.assertLessEqual(len(frame), receipt.MAX_RECEIPT_FRAME_BYTES)
        with self.assertRaises(receipt.ReceiptFrameError):
            receipt.encode_receipt_frame({"oversize": "x" * receipt.MAX_RECEIPT_PAYLOAD_BYTES})
        nested: object = "leaf"
        for _ in range(receipt.MAX_RECEIPT_DEPTH + 1):
            nested = {"n": nested}
        with self.assertRaises(receipt.ReceiptFrameError):
            receipt.encode_receipt_frame({"nested": nested})
        with self.assertRaises(receipt.ReceiptFrameError):
            receipt.encode_receipt_frame({"nodes": [0] * receipt.MAX_RECEIPT_NODES})

    def test_pipe_guard_accepts_only_file_type_pipe_before_any_write(self) -> None:
        allowed = FakeKernel32(core.FILE_TYPE_PIPE)
        self.assertEqual(
            core.require_win32_pipe_handle(123, kernel32=allowed, platform_name="nt"), 123
        )
        self.assertEqual(allowed.calls, 1)
        for rejected_type in (0, 1, 2, 0x8000):
            with self.assertRaises(core.CompactAfesEvidenceError):
                core.require_win32_pipe_handle(
                    123, kernel32=FakeKernel32(rejected_type), platform_name="nt"
                )
        with self.assertRaises(core.CompactAfesEvidenceError):
            core.require_win32_pipe_handle(123, kernel32=allowed, platform_name="posix")

    def test_extractor_has_no_path_result_or_blender_mutation_surface(self) -> None:
        source = EXTRACTOR.read_text(encoding="utf-8")
        for forbidden in (
            "bpy.ops", "--result-path", "write_text(", "write_bytes(",
            "bpy.data.libraries.write", "save_as_mainfile", "render.render", "export_scene"
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("canonical_receipt.encode_receipt_frame(payload)", source)
        self.assertIn("require_win32_pipe_handle(raw_handle)", source)
        self.assertLess(
            source.index("require_win32_pipe_handle(raw_handle)"),
            source.index("msvcrt.open_osfhandle(handle, flags)"),
        )
        self.assertIn("canonical_receipt_helper", source)
        self.assertIn("attempt_02_topology_core", source)
        self.assertIn("attempt_02_extractor", source)

    def test_config_is_float_free_fail_closed_and_requires_two_fresh_matches(self) -> None:
        assert_no_float(self, self.config)
        scope = self.config["scope"]
        self.assertTrue(scope["read_only"])
        for key in (
            "candidate_creation_allowed", "blend_edit_allowed", "blend_save_allowed",
            "render_allowed", "export_allowed", "runtime_activation_allowed",
            "path_output_allowed",
        ):
            self.assertFalse(scope[key])
        sealing = self.config["topology_sealing_contract"]
        self.assertIsNone(sealing["prior_sealed_expected_full_normalized_topology_sha256"])
        self.assertEqual(sealing["required_fresh_locked_matching_extractions"], 2)
        self.assertFalse(sealing["one_extraction_is_acceptance"])
        truth = self.config["truth_boundary"]
        self.assertFalse(truth["controller_or_pipe_creation_implemented"])
        self.assertFalse(truth["child_process_authentication_implemented"])
        self.assertFalse(truth["replay_protection_implemented"])
        self.assertFalse(truth["blender_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
