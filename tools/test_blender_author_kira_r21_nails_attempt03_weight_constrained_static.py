from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_author_kira_r21_nails_attempt03_weight_constrained.py"


class KiraR21NailAttempt03WorkerStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_worker_is_append_only_attempt03_and_preserves_prior_attempts(self) -> None:
        for token in (
            'CONFIG_SCHEMA = "kira.r21.nail_attempt03.run_config.v1"',
            'int(config.get("attempt", 0)) != 3',
            'config.get("status") != "PREPARED_NOT_RUN"',
            'if run_dir.exists() or owner_dir.exists() or output_blend.exists():',
            '"attempt": 3',
        ):
            self.assertIn(token, self.source)

    def test_exact_twenty_are_processed_independently(self) -> None:
        self.assertIn("inventory = expected_nail_inventory()", self.source)
        self.assertIn("for base_definition in inventory:", self.source)
        self.assertIn("except Exception as exc:", self.source)
        self.assertIn('"all_20_unique_nails": len(built) == 20', self.source)
        self.assertIn('"no_per_nail_failures": not failures', self.source)

    def test_partial_passes_are_cached_but_never_saved_as_a_candidate(self) -> None:
        for token in (
            'cache_path = run_dir / "PASSING_NAIL_COMPONENTS.json"',
            '"candidate_blend_saved": False',
            "if not all(full_gates.values()):",
            'failure_path = run_dir / "FAILURE_EVIDENCE.json"',
            '"FAILED_NO_CANDIDATE_BLEND_SAVED"',
        ):
            self.assertIn(token, self.source)
        failure_gate = self.source.index("if not all(full_gates.values()):")
        save = self.source.index("bpy.ops.wm.save_as_mainfile(")
        self.assertLess(failure_gate, save)

    def test_reuse_is_exact_hash_bound_and_revalidated(self) -> None:
        for token in (
            "validate_component_cache(",
            'if sha256_file(path) != str(row["sha256"]):',
            "projector.reconstruct_cached_nail_v1(",
            '"origin_source_non_nail_manifest_sha256"',
            '"origin_rig_rest_sha256"',
        ):
            self.assertIn(token, self.source)

    def test_protected_non_nails_and_rig_are_compared_before_save(self) -> None:
        for token in (
            "non_nail_before = legacy.non_nail_manifest()",
            "non_nail_after = legacy.non_nail_manifest()",
            '"body_mesh_unchanged"',
            '"body_modifier_stack_unchanged"',
            '"rig_rest_unchanged"',
            '"all_non_nail_objects_unchanged"',
            '"no_nail_to_nail_overlap"',
        ):
            self.assertIn(token, self.source)

    def test_worker_does_not_activate_assign_export_or_publish(self) -> None:
        for forbidden in (
            "bpy.ops.export",
            "runtime_registry",
            "activate_candidate",
            "publish_candidate",
            "upload",
        ):
            self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main()
