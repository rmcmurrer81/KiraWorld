from __future__ import annotations

import inspect
import unittest
from pathlib import Path

from tools import kira_spa_resource_smoke as smoke
from tools import serve_legal_day_spa_notebook_world as spa_server


evaluate_placement_decision = smoke.evaluate_placement_decision


def hardware(capacity: int, blocked: list[str] | None = None) -> dict:
    return {
        "known_build": {"current_observed_ram": {"capacity_gb": capacity}},
        "current_planned_stage": "current",
        "capability_stages": [{"stage_id": "current", "blocked_work": blocked or []}],
    }


def gate(**overrides) -> dict:
    value = {
        "status": "approved",
        "runtime_kira_route_test": "passed",
        "visual_realism_review": "passed",
        "robert_approval": "granted",
    }
    value.update(overrides)
    return value


class KiraSpaResourcePolicyTests(unittest.TestCase):
    def test_smoke_uses_same_code_pinned_registration_and_scoped_handler(self) -> None:
        smoke_build, spa_folder, gate_path, gate_data = smoke.resolve_pinned_spa_inputs()
        launcher_build = spa_server.verify_pinned_build()
        self.assertEqual(smoke_build.manifest_sha256, launcher_build.manifest_sha256)
        self.assertEqual(smoke_build.registration_sha256, launcher_build.registration_sha256)
        self.assertEqual(spa_folder, (smoke.ROOT / launcher_build.entrypoint_relative_path).parent)
        self.assertEqual(gate_path, launcher_build.role_paths["preview_approval_gate"][0])
        self.assertIsInstance(gate_data, dict)
        self.assertEqual(
            Path(inspect.getsourcefile(smoke.bind_pinned_spa_server) or "").resolve(),
            Path(inspect.getsourcefile(spa_server.bind_server) or "").resolve(),
        )
        source = inspect.getsource(smoke)
        self.assertNotIn('"http.server"', source)
        self.assertNotIn("LATEST_SPA", source)

    def test_current_32gb_stage_keeps_spa_separate_and_former_mall_reversible(self) -> None:
        result = evaluate_placement_decision(
            hardware(32, ["3d_home_runtime_as_lived_world"]),
            gate(),
            "passed_bounded_combined_smoke",
            15.0,
        )
        self.assertEqual(result["choice"], "separate_notebook_world")
        self.assertFalse(result["home_world_mutation_allowed"])
        self.assertFalse(result["strip_mall_deletion_allowed"])
        self.assertEqual(result["strip_mall_runtime_visibility"], "empty_lot_default_owner_choice")
        self.assertTrue(result["strip_mall_source_preserved"])
        self.assertEqual(result["strip_mall_restore_switch"], "?stripMall=1")
        self.assertFalse(result["spa_placed_on_former_strip_mall_site"])
        self.assertTrue(any("32GB" in reason for reason in result["reasons"]))
        self.assertTrue(any("several-hour" in reason for reason in result["reasons"]))

    def test_failed_spa_gates_block_home_world_even_if_short_smoke_passes(self) -> None:
        result = evaluate_placement_decision(
            hardware(64),
            gate(status="not_approved", runtime_kira_route_test="not_run", visual_realism_review="failed"),
            "passed_bounded_combined_smoke",
            20.0,
        )
        self.assertFalse(result["home_world_mutation_allowed"])
        self.assertTrue(any("not approved" in reason for reason in result["reasons"]))
        self.assertTrue(any("route test" in reason for reason in result["reasons"]))

    def test_low_available_memory_is_reported(self) -> None:
        result = evaluate_placement_decision(hardware(64), gate(), "passed_bounded_combined_smoke", 7.75)
        self.assertTrue(any("8GB" in reason for reason in result["reasons"]))

    def test_short_smoke_failure_is_reported(self) -> None:
        result = evaluate_placement_decision(hardware(64), gate(), "failed_bounded_combined_smoke", 18.0)
        self.assertTrue(any("did not fully pass" in reason for reason in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
