#!/usr/bin/env python3
"""Focused non-Blender tests for the prepared R23 read-only preflight."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.kira_r23_cc0_afes_preflight_core import (
    expand_face_rings,
    face_adjacency,
    shortest_path_union,
    topology_record,
)


WORKER = ROOT / "Tools" / "blender_preflight_kira_r23_cc0_afes_expanded_mask.py"
CORE = ROOT / "Tools" / "kira_r23_cc0_afes_preflight_core.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_preparation/"
    "KIRA_R23_CC0_AFES_EXPANDED_MASK_PREFLIGHT_CONFIG.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R23CC0AFESPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker_source = WORKER.read_text(encoding="utf-8")
        cls.core_source = CORE.read_text(encoding="utf-8")
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_python_sources_are_syntactically_valid(self) -> None:
        ast.parse(self.worker_source)
        ast.parse(self.core_source)

    def test_exact_input_hashes_and_sizes_are_current(self) -> None:
        for name, row in self.config["inputs"].items():
            with self.subTest(name=name):
                path = ROOT / row["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(sha256_file(path), row["sha256"])
                self.assertEqual(path.stat().st_size, row["bytes"])

    def test_config_is_preflight_only_and_append_only(self) -> None:
        self.assertEqual(
            self.config["schema"],
            "kira.avatar.r23_cc0_afes_expanded_mask_preflight.v1",
        )
        self.assertEqual(self.config["status"], "PREPARED_NOT_RUN_NO_CANDIDATE")
        scope = self.config["scope"]
        self.assertTrue(scope["read_only_preflight"])
        self.assertFalse(scope["authoring_allowed_by_this_config"])
        self.assertFalse(scope["blend_save_allowed"])
        self.assertFalse(scope["render_allowed"])
        self.assertFalse(scope["export_allowed"])
        output = ROOT / self.config["output"]["directory"]
        self.assertFalse(output.exists())
        self.assertTrue(self.config["output"]["append_only"])

    def test_r20_rule_is_preserved_and_narrowly_reconciled(self) -> None:
        rule = self.config["r20_rule_reconciliation"]
        self.assertTrue(rule["preserve_all_r20_files_byte_for_byte"])
        self.assertTrue(rule["not_retroactive"])
        self.assertFalse(rule["r20_result_reinterpreted"])
        self.assertEqual(
            rule["only_allowed_geometry_donor_id"],
            "generic_makehuman_adult_female_foundation_v1_20260801",
        )
        self.assertEqual(rule["license_required"], "CC0-1.0")
        self.assertFalse(rule["reference_only_or_unlicensed_geometry_copy_allowed"])
        self.assertFalse(rule["blackproject_patch_interior_copy_allowed"])

    def test_donor_and_r19_contracts_are_exact(self) -> None:
        donor = self.config["donor_contract"]
        self.assertEqual(donor["expected_vertices"], 14658)
        self.assertEqual(donor["expected_faces"], 15976)
        self.assertEqual(donor["expected_landmark_union_vertices"], 1169)
        self.assertEqual(donor["expected_landmark_incident_faces"], 2488)
        self.assertEqual(len(donor["required_landmark_groups"]), 16)
        r19 = self.config["r19_contract"]
        self.assertEqual(r19["expected_body_vertices"], 12612)
        self.assertEqual(r19["expected_body_faces"], 24936)
        self.assertEqual(r19["expected_old_patch_faces"], 376)
        self.assertEqual(r19["expected_old_patch_interface_vertices"], 34)

    def test_exactly_two_future_attempts_are_declared_but_not_authorized(self) -> None:
        attempts = self.config["bounded_future_attempts"]
        self.assertEqual([row["attempt"] for row in attempts], [1, 2])
        self.assertEqual(
            [row["id"] for row in attempts],
            [
                "R23_CC0_AFES_CORE_TRANSFER_A",
                "R23_CC0_AFES_CORE_TRANSFER_B_TARGETED_SCULPT",
            ],
        )
        self.assertTrue(
            all(row["authoring_authorized_by_this_preflight"] is False for row in attempts)
        )

    def test_worker_has_no_blend_write_render_export_or_candidate_path(self) -> None:
        forbidden = (
            r"bpy\.ops",
            r"save_as_mainfile",
            r"save_mainfile",
            r"write_still",
            r"export_scene",
            r"wm\.open_mainfile",
            r"subprocess",
            r"Avatar/private_owner_review",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.worker_source))
        self.assertIn("bpy.data.libraries.load", self.worker_source)
        self.assertIn('"candidate_created": False', self.worker_source)
        self.assertIn('"blend_written": False', self.worker_source)

    def test_worker_does_not_name_or_load_reference_only_asset_trees(self) -> None:
        forbidden = (
            "adult_anatomy_reference",
            "Avatar/Library/female",
            "female_anatomy_study_progress",
            "topless_sexy",
            "reference_mesh",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.worker_source)

    def test_one_disk_topology_fixture_passes(self) -> None:
        faces = [(0, 1, 2), (0, 2, 3)]
        record = topology_record(faces, {0, 1})
        self.assertTrue(record["is_one_disk"])
        self.assertEqual(record["component_count"], 1)
        self.assertEqual(record["boundary_cycle_count"], 1)
        self.assertEqual(record["euler_characteristic"], 1)

    def test_disconnected_fixture_fails_disk_gate(self) -> None:
        faces = [(0, 1, 2), (3, 4, 5)]
        record = topology_record(faces, {0, 1})
        self.assertFalse(record["is_one_disk"])
        self.assertEqual(record["component_count"], 2)

    def test_shortest_path_union_and_ring_expansion_are_bounded(self) -> None:
        faces = [
            (0, 1, 2),
            (2, 1, 3),
            (2, 3, 4),
            (4, 3, 5),
        ]
        adjacency = face_adjacency(faces)
        path, distances = shortest_path_union(
            adjacency, {0}, {3}, allowed={0, 1, 2, 3}
        )
        self.assertEqual(path, {0, 1, 2, 3})
        self.assertEqual(distances[3], 3)
        expanded = expand_face_rings({1}, adjacency, 1, allowed={0, 1, 2})
        self.assertEqual(expanded, {0, 1, 2})

    def test_functional_truth_is_not_overclaimed(self) -> None:
        truth = self.config["truth_boundary"]
        self.assertTrue(truth["external_connected_relationships_only"])
        self.assertFalse(
            truth[
                "bladder_urethral_canal_bowel_rectum_pelvic_floor_physiology_implemented"
            ]
        )
        self.assertFalse(
            truth["reproduction_pregnancy_delivery_or_hospital_physiology_implemented"]
        )


if __name__ == "__main__":
    unittest.main()
