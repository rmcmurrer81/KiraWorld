from __future__ import annotations

import ast
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "Tools" / "diagnose_persistent_blackwell_load_phases.py"
SPEC = importlib.util.spec_from_file_location("persistent_blackwell_load_phase_diagnostic", TOOL)
assert SPEC is not None and SPEC.loader is not None
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


class PersistentBlackwellLoadPhaseDiagnosticTests(unittest.TestCase):
    def test_preserved_attempt_candidate_and_production_files_match(self) -> None:
        evidence = diagnostic.bound_integrity()
        self.assertTrue(evidence["passed"])
        self.assertEqual(set(evidence["files"]), set(diagnostic.EXPECTED_SHA256))
        self.assertTrue(all(row["matches"] for row in evidence["files"].values()))

    def test_describe_is_inactive_and_performs_no_execution(self) -> None:
        value = diagnostic.describe()
        self.assertEqual(value["status"], "prepared_inactive_not_executed")
        self.assertEqual(value["candidate_status"], "inactive_private_candidate_not_production")
        self.assertFalse(value["model_or_gpu_execution_performed_by_describe"])
        self.assertFalse(value["synthesis_performed"])
        self.assertFalse(value["playback_performed"])
        self.assertTrue(value["production_route_unchanged"])
        self.assertEqual(value["automatic_fallback"], "sealed_cpu_chatterbox_only")

    def test_current_exact_cache_snapshot_is_complete_without_weight_hash_sweep(self) -> None:
        value = diagnostic.static_cache_inventory()
        self.assertEqual(value["revision"], "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18")
        self.assertTrue(value["all_required_files_present"])
        self.assertEqual([row["filename"] for row in value["files"]], list(diagnostic.MODEL_FILENAMES))
        self.assertTrue(all(row["sha256_intentionally_not_computed"] for row in value["files"]))
        self.assertGreater(sum(int(row["bytes"]) for row in value["files"]), 3_000_000_000)

    def test_every_required_phase_is_named_in_source(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        for phase in diagnostic.DIAGNOSTIC_PHASES:
            self.assertIn(phase, source)
        self.assertIn("heartbeat", source)
        self.assertIn("timed_out_phase", source)

    def test_no_top_level_model_audio_or_gpu_import(self) -> None:
        tree = ast.parse(TOOL.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(str(node.module or "").split(".")[0])
        self.assertTrue(
            {
                "torch",
                "torchaudio",
                "transformers",
                "numpy",
                "soundfile",
                "librosa",
                "perth",
                "chatterbox",
            }.isdisjoint(imported)
        )

    def test_diagnostic_never_calls_generate_or_playback(self) -> None:
        tree = ast.parse(TOOL.read_text(encoding="utf-8"))
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("generate", called_attributes)
        self.assertNotIn("play", called_attributes)
        self.assertNotIn("playsound", called_attributes)

    def test_phase_timeout_prefers_explicit_outer_bound(self) -> None:
        self.assertEqual(diagnostic.phase_timeout("from_pretrained.total"), 900.0)
        self.assertEqual(diagnostic.phase_timeout("from_pretrained.t3.load_file"), 300.0)
        self.assertEqual(diagnostic.phase_timeout("cache.resolve.conds.pt"), 60.0)
        self.assertEqual(diagnostic.phase_timeout("unlisted"), 300.0)

    def test_attempt_allocation_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "attempt_01").mkdir()
            first = diagnostic.allocate_attempt_directory(root)
            second = diagnostic.allocate_attempt_directory(root)
            self.assertEqual(first.name, "attempt_02")
            self.assertEqual(second.name, "attempt_03")
            self.assertTrue((root / "attempt_01").is_dir())

    def test_event_emitter_records_bounded_phase_evidence(self) -> None:
        stream = io.StringIO()
        emitter = diagnostic.EventEmitter(stream)
        with emitter.phase("unit.phase", purpose="no_heavy_execution"):
            pass
        rows = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual([row["message_type"] for row in rows], ["phase_start", "phase_end"])
        self.assertEqual(rows[0]["phase"], "unit.phase")
        self.assertEqual(rows[1]["status"], "passed")

    def test_execute_requires_explicit_no_blender_confirmation(self) -> None:
        with patch.object(sys, "argv", [str(TOOL), "--execute-diagnostic"]):
            with self.assertRaises(SystemExit) as caught:
                diagnostic.main()
        self.assertEqual(caught.exception.code, 2)

    def test_full_load_is_diagnostic_only_and_instrumented_from_local(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn('implementation="sealed_from_pretrained_with_hash_bound_instrumented_from_local"', source)
        self.assertIn("ChatterboxTTS.__dict__[\"from_local\"]", source)
        self.assertIn("local_files_only", source)
        self.assertIn("full_model_loaded_then_released", source)
        self.assertIn("production_routing_changed", source)


if __name__ == "__main__":
    unittest.main()
