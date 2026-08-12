#!/usr/bin/env python3
"""Focused non-Blender tests for the R25 AFES extraction preparation."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "body_systems"
    / "kira_r25_foundation_afes_read_only_extraction_v1.json"
)
CORE = ROOT / "tools" / "kira_r25_afes_topology_core.py"
EXTRACTOR = ROOT / "tools" / "blender_extract_kira_r25_foundation_afes_transition_rings.py"


from tools.kira_r25_afes_topology_core import (  # noqa: E402
    AfesTopologyError,
    analyze_afes_topology,
    geodesic_vertex_rings,
    normalize_memberships,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R25AfesReadOnlyExtractionPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.edges = [(index, index + 1) for index in range(8)]
        cls.faces = [
            (0, 1, 2),
            (2, 3, 4),
            (3, 4, 5),
            (4, 5, 6),
            (6, 7, 8),
        ]

    def _analysis(self, *, reverse_edges: bool = False) -> dict[str, object]:
        edges = list(reversed(self.edges)) if reverse_edges else self.edges
        return analyze_afes_topology(
            vertex_count=9,
            edges=edges,
            faces=self.faces,
            memberships={"g_b": [5, 4], "g_a": [4, 3]},
            required_group_names=["g_a", "g_b"],
            transition_ring_count=2,
        )

    def test_01_union_groups_faces_connections_and_rings_are_exact(self) -> None:
        analysis = self._analysis()
        self.assertEqual(analysis["groups"]["g_a"]["vertex_indices"], [3, 4])
        self.assertEqual(analysis["groups"]["g_b"]["vertex_indices"], [4, 5])
        union = analysis["afes_union"]
        self.assertEqual(union["vertex_indices"], [3, 4, 5])
        self.assertEqual(
            union["vertex_index_sha256"],
            "251e3c94506e86df03eedb498e73490db6ee18a5218e27977f64c8399006937a",
        )
        self.assertEqual(union["incident_face_indices"], [1, 2, 3])
        self.assertEqual(union["internal_face_indices"], [2])
        self.assertEqual(union["connection_edges"], [[2, 3], [5, 6]])
        self.assertEqual(
            union["connection_edge_sha256"],
            "aea674fb7c94eb7be80e4762becf78b75b2a6c62e3568dba0f8d801151e47537",
        )
        rings = analysis["transition_rings"]
        self.assertEqual(rings["rings"][0]["vertex_indices"], [2, 6])
        self.assertEqual(rings["rings"][1]["vertex_indices"], [1, 7])
        self.assertEqual(rings["combined_vertex_indices"], [1, 2, 6, 7])
        self.assertTrue(rings["disjoint_from_afes_union"])

    def test_02_input_order_does_not_change_the_diagnostic(self) -> None:
        self.assertEqual(self._analysis(), self._analysis(reverse_edges=True))

    def test_03_group_membership_is_fail_closed(self) -> None:
        with self.assertRaisesRegex(AfesTopologyError, "group-key mismatch"):
            normalize_memberships(4, {"expected": [1], "extra": [2]}, ["expected"])
        with self.assertRaisesRegex(AfesTopologyError, "repeats a vertex"):
            normalize_memberships(4, {"expected": [1, 1]}, ["expected"])
        with self.assertRaisesRegex(AfesTopologyError, "must be an integer"):
            normalize_memberships(4, {"expected": [True]}, ["expected"])

    def test_04_two_nonempty_geodesic_rings_are_mandatory(self) -> None:
        self.assertEqual(
            geodesic_vertex_rings(9, self.edges, [3, 4, 5], ring_count=2),
            ((2, 6), (1, 7)),
        )
        with self.assertRaisesRegex(AfesTopologyError, "at least two"):
            geodesic_vertex_rings(9, self.edges, [3, 4, 5], ring_count=1)
        with self.assertRaisesRegex(AfesTopologyError, "ring 1 is empty"):
            geodesic_vertex_rings(3, [(0, 1), (1, 2)], [0, 1, 2], ring_count=2)

    def test_05_config_binds_exact_foundation_and_all_sixteen_groups(self) -> None:
        self.assertEqual(
            self.config["status"], "STATIC_PREPARATION_ONLY_EXECUTION_NOT_AUTHORIZED"
        )
        scope = self.config["scope"]
        self.assertTrue(scope["read_only"])
        for key in (
            "candidate_creation_allowed",
            "blend_edit_allowed",
            "blend_save_allowed",
            "render_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "path_output_allowed",
        ):
            self.assertFalse(scope[key])
        foundation = self.config["bindings"]["foundation_blend"]
        self.assertEqual(foundation["bytes"], 789620)
        self.assertEqual(
            foundation["sha256"],
            "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f",
        )
        groups = self.config["foundation_contract"]["required_groups"]
        self.assertEqual(len(groups), 16)
        self.assertEqual(groups["AFES_LANDMARK__urethral_opening"]["vertex_count"], 13)
        self.assertEqual(groups["AFES_LANDMARK__vaginal_opening"]["vertex_count"], 299)
        self.assertEqual(
            self.config["foundation_contract"]["afes_union"]["vertex_index_sha256"],
            "e176a908e76fbca6f7bf2b843e3745fe9bc51cf4c46add2fa6dcd384fd413195",
        )

    def test_06_every_bound_source_still_matches_hash_and_size(self) -> None:
        for label, row in self.config["bindings"].items():
            path = ROOT / row["path"]
            self.assertTrue(path.is_file(), label)
            self.assertEqual(path.stat().st_size, row["bytes"], label)
            self.assertEqual(_sha256(path), row["sha256"], label)

    def test_07_extractor_has_no_operator_or_path_output_surface(self) -> None:
        source = EXTRACTOR.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertNotIn("bpy" + ".ops", source)
        self.assertNotIn("--output", source)
        self.assertNotIn("write_text(", source)
        self.assertNotIn("write_bytes(", source)
        self.assertNotIn("os.fsync", source)
        arguments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ]
        literal_args = {
            node.args[0].value
            for node in arguments
            if node.args and isinstance(node.args[0], ast.Constant)
        }
        self.assertEqual(literal_args, {"--result-handle"})
        self.assertIn("write_payload_to_inherited_binary_handle", source)
        self.assertIn("while total < len(view)", source)
        self.assertIn("bpy.data.is_dirty", source)

    def test_08_extractor_is_sealed_to_the_exact_config(self) -> None:
        source = EXTRACTOR.read_text(encoding="utf-8")
        self.assertIn(f'CONFIG_BYTES = {CONFIG.stat().st_size}', source)
        self.assertIn(f'CONFIG_SHA256 = "{_sha256(CONFIG)}"', source)
        self.assertIn("R23 and R25 foundation bindings differ", source)
        self.assertIn("sealed R23 subgroup results drifted", source)
        self.assertIn("AFES subgroup count or digest drifted", source)


if __name__ == "__main__":
    unittest.main()
