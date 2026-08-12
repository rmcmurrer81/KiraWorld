#!/usr/bin/env python3
"""Static/dry tests for the bounded R23 Author Attempt04 repair package."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_REPAIR_CONFIG.json"
)
WRAPPER = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt04_wrapper.py"
CONTROLLER = ROOT / "Tools/kira_r23_author_attempt04_invocation.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Attempt04PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.wrapper_text = WRAPPER.read_text(encoding="utf-8")
        cls.wrapper_tree = ast.parse(cls.wrapper_text)
        cls.controller_text = CONTROLLER.read_text(encoding="utf-8")

    def test_schema_scope_and_outputs_are_append_only(self) -> None:
        self.assertEqual(
            self.config["schema"], "kira.avatar.r23_author_attempt04_repair.v1"
        )
        self.assertEqual(
            self.config["status"], "PREPARED_NOT_RUN_EXPLICIT_EXECUTION_REQUIRED"
        )
        scope = self.config["scope"]
        self.assertFalse(scope["sealed_r19_source_changed"])
        self.assertFalse(scope["sealed_author_worker_changed"])
        self.assertFalse(scope["attempts_01_through_03_changed"])
        self.assertFalse(scope["blender_run_authorized_by_preparation"])
        repair = self.config["repair_contract"]
        self.assertEqual(repair["diagnosed_seam_chord_count"], 22)
        self.assertFalse(repair["preknown_stable_original_id_hash_available"])
        self.assertNotIn("diagnosed_seam_chord_stable_id_sha256", repair)
        self.assertEqual(
            repair["diagnosed_post_reindex_loose_row_sha256"],
            "82cac224cbd45a6e5501a8b336ec1af741ed8d98a02b3b3929d5cd479d1c0cce",
        )
        self.assertTrue(repair["global_weld_allowed"] is False)
        self.assertTrue(repair["global_boundary_deletion_allowed"] is False)
        self.assertFalse((ROOT / repair["effective_output"]).exists())
        self.assertFalse(
            (ROOT / self.config["future_execution"]["directory"]).exists()
        )

    def test_every_bound_artifact_and_preserved_directory_is_exact(self) -> None:
        for label, binding in self.config["bound_artifacts"].items():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), label)
            self.assertEqual(path.stat().st_size, binding["bytes"], label)
            self.assertEqual(sha256(path), binding["sha256"], label)
        for section in self.config["preserved_append_only_evidence"]:
            root = ROOT / section["directory"]
            self.assertEqual(
                sorted(path.name for path in root.iterdir() if path.is_file()),
                sorted(section["files"]),
                section["label"],
            )
            for name, binding in section["files"].items():
                path = root / name
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(sha256(path), binding["sha256"])

    def test_no_face_edges_import_shadow_regression(self) -> None:
        aliases = {
            alias.asname or alias.name
            for node in ast.walk(self.wrapper_tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
            if alias.name == "face_edges"
        }
        self.assertEqual(aliases, {"topology_face_edges"})
        assigned_names = {
            target.id
            for node in ast.walk(self.wrapper_tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
            for target in (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
            )
            if isinstance(target, ast.Name)
        }
        self.assertNotIn("face_edges", assigned_names)
        self.assertIn("topology_face_edges(faces[face_index])", self.wrapper_text)

    def test_wrapper_binds_only_bounded_runtime_hooks(self) -> None:
        required = [
            "sealed_worker.preflight_base.edge_face_map = edge_face_map",
            "sealed_worker.output_paths = attempt04_output_paths",
            "sealed_worker.exact_donor_disk = attempt04_exact_donor_disk",
            "sealed_worker.bmesh_frozen_snapshot = attempt04_bmesh_frozen_snapshot",
            "sealed_worker.apply_patch = attempt04_apply_patch",
            "sealed_worker.topology_gate = attempt04_topology_gate",
        ]
        for text in required:
            self.assertIn(text, self.wrapper_text)
        self.assertIn("context != \"FACES_ONLY\"", self.wrapper_text)
        self.assertIn("context=\"EDGES\"", self.wrapper_text)
        self.assertIn(
            '"postdelete_seam_orphan_set_exact": actual_chords == expected_chords',
            self.wrapper_text,
        )
        self.assertIn(
            '"none_were_loose_in_source": not actual_chords.intersection(',
            self.wrapper_text,
        )
        self.assertIn(
            '"none_were_boundary_in_source": not actual_chords.intersection(',
            self.wrapper_text,
        )
        self.assertNotIn("remove_doubles", self.wrapper_text)
        self.assertNotIn("weld_verts", self.wrapper_text)
        self.assertNotIn("save_as_mainfile", self.wrapper_text)
        self.assertNotIn("bpy.ops.render", self.wrapper_text)

    def test_source_preserving_topology_and_euler_gates_are_explicit(self) -> None:
        required = [
            '"stable_source_boundary_exact": stable_boundary == source_boundary',
            '"zero_new_boundary": not new_boundary',
            '"zero_greater_than_two_face_edges": len(overused) == 0',
            '"zero_loose_mesh_edges": len(loose) == 0',
            '"zero_duplicate_mesh_edges": not duplicate_mesh_edges',
            "expected_face_edges = expected_vertices + expected_faces - expected_face_euler",
            "expected_mesh_edges = expected_vertices + expected_faces - expected_mesh_euler",
            '"closed_whole_body_assumed": False',
        ]
        for text in required:
            self.assertIn(text, self.wrapper_text)
        source = self.config["nominal_source_baseline"]
        final = self.config["nominal_corrected_final"]
        self.assertEqual(source["vertices"] - source["mesh_edges"] + source["faces"], -21)
        self.assertEqual(final["vertices"] - final["mesh_edges"] + final["faces"], -21)
        self.assertEqual(final["mesh_edges"], 41551)
        self.assertEqual(final["boundary_edges"], 330)
        self.assertEqual(final["boundary_cycles"], 23)

    def test_clinical_semantics_are_placeholders_not_function_claims(self) -> None:
        clinical = self.config["clinical_semantics_contract"]
        self.assertTrue(clinical["metadata_only_no_geometry_creation"])
        self.assertEqual(len(clinical["exact_region_placeholders_when_deterministically_extractable"]), 5)
        self.assertEqual(len(clinical["must_remain_unextractable_without_fabrication"]), 2)
        for marker in (
            "NOT_WHOLE_CLITORIS_NOT_RIM_PROOF",
            "NOT_MEATUS_RIM_PATENCY_OR_ROUTE_PROOF",
            "NOT_INTROITUS_RIM_PATENCY_OR_ROUTE_PROOF",
            "NOT_ANUS_ANAL_VERGE_RIM_PATENCY_OR_ROUTE_PROOF",
            "NOT_DETERMINISTICALLY_EXTRACTABLE_FROM_SEALED_DONOR_NO_SET_FABRICATED",
            "NOT_DETERMINISTICALLY_EXTRACTABLE_FROM_BROAD_PERINEAL_PATH_NO_SET_FABRICATED",
            '"internal_canals_or_typed_routes_created": False',
            '"bathroom_function_proven": False',
        ):
            self.assertIn(marker, self.wrapper_text)

    def test_controller_is_dry_by_default_and_command_is_exact(self) -> None:
        self.assertIn('parser.add_argument("--execute-attempt04", action="store_true")', self.controller_text)
        self.assertIn("DRY_ATTEMPT04_REPAIR_ONLY_BLENDER_NOT_RUN", self.controller_text)
        self.assertIn('"--background"', self.controller_text)
        self.assertIn('"--factory-startup"', self.controller_text)
        self.assertIn('"--disable-autoexec"', self.controller_text)
        from tools import kira_r23_author_attempt04_invocation as controller

        command = controller.build_command(self.config)
        self.assertLess(command.index("--python-exit-code"), command.index("--python"))
        self.assertEqual(command[command.index("--python-exit-code") + 1], "7")
        self.assertFalse(Path(command[command.index("--config") + 1]).is_absolute())
        self.assertEqual(command[-1], "--execute-authoring")
        output = io.StringIO()
        with mock.patch.object(controller.base, "blender_process_count", return_value=0):
            with redirect_stdout(output):
                self.assertEqual(controller.main([]), 0)
        dry = json.loads(output.getvalue())
        self.assertEqual(dry["status"], "DRY_ATTEMPT04_REPAIR_ONLY_BLENDER_NOT_RUN")
        self.assertFalse(dry["blender_started"])
        self.assertEqual(dry["blender_process_count_observed"], 0)


if __name__ == "__main__":
    unittest.main()
