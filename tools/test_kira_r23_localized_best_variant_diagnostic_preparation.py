#!/usr/bin/env python3
"""Static tests for the exact no-save R23 best-variant diagnostic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_localized_best_variant_diagnostic_preparation/"
    "KIRA_R23_LOCALIZED_BEST_VARIANT_DIAGNOSTIC_CONFIG.json"
)


class LocalizedBestVariantDiagnosticPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_all_bindings_are_exact(self):
        for label, row in self.config["bindings"].items():
            with self.subTest(label=label):
                path = ROOT / row["path"]
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.stat().st_size, row["bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["sha256"])

    def test_exact_attempt08_best_variant_is_bound(self):
        self.assertEqual(self.config["variant"]["id"], "o0.50_d0.00_c0.0000")

    def test_worker_has_no_save_render_or_export_operator(self):
        source = (ROOT / self.config["bindings"]["worker"]["path"]).read_text(encoding="utf-8")
        for marker in (
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.wm.save_mainfile",
            "bpy.ops.render.render",
            "bpy.ops.export_scene",
        ):
            self.assertNotIn(marker, source)

    def test_restrictions_are_fail_closed(self):
        self.assertTrue(all(self.config["restrictions"].values()))


if __name__ == "__main__":
    unittest.main()
