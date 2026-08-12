from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest

from Core import kira_r20_attempt04_quality_diagnostic as diagnostic
from Core import kira_r20_curvilinear_pelvic_patch as r20


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "tools/blender_diagnose_kira_r20_attempt04_quality.py"
HELPER = PROJECT_ROOT / "Core/kira_r20_attempt04_quality_diagnostic.py"
SEALED_WORKER = PROJECT_ROOT / "tools/blender_author_kira_r20_pelvis_only.py"
SEALED_CORE = PROJECT_ROOT / "Core/kira_r20_curvilinear_pelvic_patch.py"
SEALED_CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json"
)
SEALED_TESTS = PROJECT_ROOT / "Testing/test_kira_r20_pelvis_only_authoring.py"
SEALED_MANIFEST = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/IMPLEMENTATION_MANIFEST.json"
)
PREPARED = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared"
)
CONFIG = PREPARED / "DIAGNOSTIC_CONFIG.json"
COMMAND = PREPARED / "RUN_DIAGNOSTIC_COMMAND.md"
MANIFEST = PREPARED / "IMPLEMENTATION_MANIFEST.json"
OUTPUT = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01"
)
ATTEMPT04 = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def call_chain(node: ast.AST) -> str:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def geometry_fixture() -> tuple[list[tuple[float, float, float]], ...]:
    seam = []
    exterior_1 = []
    exterior_2 = []
    normals = []
    for index in range(r20.SEAM_COUNT):
        fraction = index / r20.SEAM_COUNT
        fraction += 0.014 * math.sin(2.0 * math.pi * fraction)
        angle = 2.0 * math.pi * fraction
        radial_x = 0.051 * math.cos(angle)
        radial_z = 0.073 * math.sin(angle)
        surface_y = -0.010 + 0.0022 * math.cos(2.0 * angle)
        seam.append((radial_x, surface_y, 0.87 + radial_z))
        exterior_1.append((1.07 * radial_x, surface_y + 0.001, 0.87 + 1.07 * radial_z))
        exterior_2.append((1.14 * radial_x, surface_y + 0.002, 0.87 + 1.14 * radial_z))
        normals.append((0.0, -1.0, 0.0))
    canonical, order = r20.canonicalize_cycle(seam)
    return (
        list(canonical),
        [exterior_1[index] for index in order],
        [exterior_2[index] for index in order],
        [normals[index] for index in order],
    )


class PureDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        seam, first, second, normals = geometry_fixture()
        cls.seam_ids = list(range(1000, 1000 + r20.SEAM_COUNT))
        cls.positions = {}
        cls.details = {}
        for candidate in r20.CANDIDATES:
            positions, _evidence = r20.build_positions(
                seam, first, second, normals, candidate
            )
            faces = r20.build_quad_topology()
            cls.positions[candidate.candidate_id] = positions
            cls.details[candidate.candidate_id] = diagnostic.detailed_geometry_quality(
                positions,
                faces,
                cls.seam_ids,
                worst_n=32,
                maximum_quad_edge_ratio=3.0,
                coincidence_tolerance_m=1.0e-12,
            )

    def test_exact_face_category_and_vertex_mapping(self) -> None:
        faces = r20.build_quad_topology()
        cases = {
            0: "seam_to_collar_1",
            1: "collar_1_to_collar_2",
            68: "collar_2_to_core_3_to_1_leading",
            69: "collar_2_to_core_3_to_1_trailing",
            136: "core_grid",
            755: "core_grid",
        }
        for index, category in cases.items():
            record = diagnostic.face_topology_record(index, faces[index])
            self.assertEqual(record["category"], category)
            self.assertTrue(record["matches_fixed_topology_and_order"])
        seam = diagnostic.vertex_record(0, (1.0, 2.0, 3.0), self.seam_ids)
        self.assertEqual(seam["region"], "seam")
        self.assertEqual(seam["source_r19_vertex_id"], 1000)
        collar = diagnostic.vertex_record(34, (1.0, 2.0, 3.0), self.seam_ids)
        self.assertEqual(collar["region"], "collar_1")
        self.assertIsNone(collar["source_r19_vertex_id"])
        core = diagnostic.vertex_record(102, (1.0, 2.0, 3.0), self.seam_ids)
        self.assertEqual(core["region"], "core")
        self.assertTrue(core["core_perimeter"])

    def test_reverse_winding_is_not_topology_drift(self) -> None:
        faces = r20.build_quad_topology(reverse_winding=True)
        for index in (0, 68, 136, 755):
            record = diagnostic.face_topology_record(index, faces[index])
            self.assertEqual(record["winding"], "reverse")
            self.assertTrue(record["matches_fixed_topology_and_order"])

    def test_detailed_report_reproduces_aggregate_and_required_fields(self) -> None:
        for candidate in r20.CANDIDATES:
            positions = self.positions[candidate.candidate_id]
            details = self.details[candidate.candidate_id]
            aggregate = r20.geometry_quality(positions)
            self.assertEqual(details["face_count"], 756)
            self.assertEqual(details["worst_n"], 32)
            self.assertEqual(details["maximum_quad_edge_ratio"], aggregate["maximum_quad_edge_ratio"])
            self.assertEqual(details["minimum_face_area_m2"], aggregate["minimum_face_area_m2"])
            self.assertEqual(
                details["degenerate_face_count_at_1e_10_m2"],
                aggregate["degenerate_face_count_at_1e_10_m2"],
            )
            self.assertEqual(len(details["all_face_metrics"]), 756)
            self.assertEqual(len(details["worst_faces"]), 32)
            ratios = [record["quad_edge_ratio"] for record in details["worst_faces"]]
            self.assertEqual(ratios, sorted(ratios, reverse=True))
            worst = details["worst_faces"][0]
            self.assertEqual(worst["rank"], 1)
            self.assertEqual(len(worst["vertices"]), 4)
            self.assertEqual(len(worst["edges"]), 4)
            self.assertEqual(len(worst["triangle_areas_m2"]), 2)
            self.assertEqual(len(worst["diagonal_lengths_m"]), 2)
            self.assertIn("neighbor_face_topology_indices", worst)

    def test_coordinate_collapse_is_classified_without_threshold_change(self) -> None:
        candidate = r20.CANDIDATES[0]
        positions = list(self.positions[candidate.candidate_id])
        positions[r20.COLLAR_2_OFFSET] = positions[r20.CORE_OFFSET]
        details = diagnostic.detailed_geometry_quality(
            positions,
            r20.build_quad_topology(),
            self.seam_ids,
            worst_n=32,
            maximum_quad_edge_ratio=3.0,
            coincidence_tolerance_m=1.0e-12,
        )
        self.assertEqual(details["maximum_quad_edge_ratio_threshold_unchanged"], 3.0)
        self.assertTrue(details["exact_duplicate_coordinate_groups"])
        self.assertEqual(
            details["failure_localization"]["classification"],
            "COORDINATE_COINCIDENCE_OR_NEAR_COLLAPSE",
        )

    def test_candidate_comparison_is_exact_face_for_face(self) -> None:
        first_id, second_id = [candidate.candidate_id for candidate in r20.CANDIDATES]
        comparison = diagnostic.compare_candidate_quality(
            self.positions[first_id],
            self.details[first_id],
            self.positions[second_id],
            self.details[second_id],
            difference_count=32,
        )
        self.assertTrue(comparison["same_fixed_topology_connectivity"])
        self.assertEqual(len(comparison["largest_absolute_face_ratio_differences"]), 32)
        self.assertEqual(comparison["maximum_candidate_position_delta_by_region_m"]["seam"], 0.0)

    def test_nonexact_ratio_threshold_fails_closed(self) -> None:
        candidate = r20.CANDIDATES[0]
        with self.assertRaisesRegex(ValueError, "exactly 3.0"):
            diagnostic.detailed_geometry_quality(
                self.positions[candidate.candidate_id],
                r20.build_quad_topology(),
                self.seam_ids,
                worst_n=32,
                maximum_quad_edge_ratio=3.01,
                coincidence_tolerance_m=1.0e-12,
            )


class StaticDiagnosticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.calls = [node for node in ast.walk(cls.tree) if isinstance(node, ast.Call)]
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_sealed_attempt04_files_are_byte_exact(self) -> None:
        expected = {
            SEALED_CORE: "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d",
            SEALED_WORKER: "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a",
            SEALED_CONFIG: "5ab9d60a948d7cac4e08e71a0f9c3927af9f33004ef23f888cc60f21b2e9e7cc",
            SEALED_TESTS: "8e12b0573db0715ea339a163d705aa856142e3fbeee9f02e05e96fb3145bc71a",
            SEALED_MANIFEST: "eb585114d2096e9ef76c352a7d6f4c578d71fc960e96c3d69d857213598fa306",
        }
        for path, digest in expected.items():
            self.assertEqual(sha256_file(path), digest, path)

    def test_attempt04_failure_evidence_is_bound_exactly(self) -> None:
        records = {
            "author_attempt_04_summary": "66607972ca0678355b87b425678c952cc2b82fdd193894be7bb2666e5186c7af",
            "author_attempt_04_failure": "e0840aef480144a72221646ef4b67fcda1da5404429e4df46957239a6237f07e",
            "author_attempt_04_candidate_a_failure": "468b4a8366ce78231b24fada48771a14ca4e96bc8324aec26b2ccbadddcc2299",
            "author_attempt_04_candidate_b_failure": "a60b8b0ad47cbb87d453a34c845850d5e650b23005913c641cbc6cf1dd31fd28",
        }
        for key, digest in records.items():
            path = PROJECT_ROOT / self.config[key]
            self.assertEqual(sha256_file(path), digest, key)
            self.assertEqual(self.config[f"{key}_sha256"], digest)

    def test_script_uses_only_read_only_sealed_construction_calls(self) -> None:
        calls = {call_chain(node.func) for node in self.calls}
        self.assertIn("sealed_author._open_exact_blend", calls)
        self.assertIn("sealed_author.preflight_scene", calls)
        self.assertIn("patch_contract.build_positions", calls)
        self.assertIn("patch_contract.geometry_quality", calls)
        self.assertIn("quality_diagnostic.detailed_geometry_quality", calls)
        forbidden = {
            "sealed_author._prepare_candidate_fields",
            "sealed_author._apply_local_patch",
            "sealed_author.run_pose_suite",
            "sealed_author.run_verify_render_mode",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.render.render",
        }
        self.assertTrue(forbidden.isdisjoint(calls), forbidden.intersection(calls))
        imports = {
            alias.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertNotIn("bmesh", imports)

    def test_config_is_diagnostic_only_and_thresholds_are_unchanged(self) -> None:
        self.assertEqual(self.config["schema_version"], 1)
        self.assertEqual(self.config["status"], "PREPARED_NOT_EXECUTED")
        self.assertEqual(self.config["worst_face_count_per_candidate"], 32)
        self.assertEqual(self.config["maximum_quad_edge_ratio_threshold_unchanged"], 3.0)
        self.assertEqual(self.config["minimum_face_area_threshold_m2_unchanged"], 1.0e-10)
        self.assertTrue(self.config["contract"]["diagnostic_only"])
        for key in (
            "bmesh_import_or_call_forbidden_in_diagnostic",
            "prepare_candidate_fields_call_forbidden",
            "apply_local_patch_call_forbidden",
            "pose_suite_call_forbidden",
            "render_call_forbidden",
            "blend_save_forbidden",
            "threshold_loosening_forbidden",
            "topology_change_forbidden",
            "candidate_change_forbidden",
            "new_candidate_forbidden",
        ):
            self.assertTrue(self.config["contract"][key], key)

    def test_command_is_one_exact_diagnostic_invocation(self) -> None:
        value = COMMAND.read_text(encoding="utf-8")
        self.assertEqual(value.count("blender_diagnose_kira_r20_attempt04_quality.py"), 1)
        self.assertEqual(value.count("--acknowledge-private-inactive"), 1)
        self.assertNotIn("--mode author", value)
        self.assertNotIn("--mode verify-render", value)
        self.assertNotIn("--candidate-id", value)
        self.assertIn(sha256_file(SCRIPT), value)
        self.assertIn(sha256_file(CONFIG), value)

    def test_output_is_append_only_and_not_yet_run(self) -> None:
        self.assertTrue(ATTEMPT04.exists())
        self.assertFalse(OUTPUT.exists())

    def test_prepared_manifest_is_exact_and_complete(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        entries = manifest["files_excluding_this_manifest"]
        listed = set()
        for entry in entries:
            path = PROJECT_ROOT / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])
            self.assertEqual(path.stat().st_size, entry["size_bytes"], entry["path"])
            self.assertEqual(sha256_file(path), entry["sha256"], entry["path"])
            listed.add(path.resolve())
        prepared_files = {
            path.resolve()
            for path in PREPARED.iterdir()
            if path.is_file() and path.name != "IMPLEMENTATION_MANIFEST.json"
        }
        listed_prepared = {path for path in listed if path.parent == PREPARED.resolve()}
        self.assertEqual(listed_prepared, prepared_files)


if __name__ == "__main__":
    unittest.main()
