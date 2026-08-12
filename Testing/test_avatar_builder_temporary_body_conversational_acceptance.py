from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUNNER_PATH = ROOT / "Tools" / "run_avatar_builder_temporary_body_conversational_acceptance.py"
SPEC = importlib.util.spec_from_file_location(
    "run_avatar_builder_temporary_body_conversational_acceptance",
    RUNNER_PATH,
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import contract guard
    raise RuntimeError(f"Unable to load acceptance runner: {RUNNER_PATH}")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
run_acceptance = RUNNER.run_acceptance


class TemporaryBodyConversationalAcceptanceTests(unittest.TestCase):
    def test_complete_private_control_plane_acceptance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="avatar_builder_temp_acceptance_") as temp:
            output = Path(temp) / "attempt_01"
            result = run_acceptance(output)
            self.assertEqual(result["status"], "passed_control_plane_only")
            self.assertTrue((output / "ACCEPTANCE_RESULT.json").is_file())
            self.assertTrue((output / "CHECKPOINT.md").is_file())
            self.assertTrue((output / "MANIFEST.json").is_file())
            manifest = json.loads((output / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertGreater(manifest["file_count_excluding_manifest"], 10)

            cases = result["cases"]
            self.assertEqual(
                cases["temporary_owner_confirmed_adult_male"]["expected_body_lane"],
                "adult_male",
            )
            self.assertEqual(
                cases["temporary_owner_confirmed_adult_female"]["expected_body_lane"],
                "adult_female",
            )
            peter = cases["peter_deliberate_bad_class_then_owner_correction"]
            self.assertEqual(peter["wrong_body_sha256_before"], peter["wrong_body_sha256_after"])
            self.assertEqual(peter["first_route"]["body_lane"], "adult_male")
            self.assertEqual(
                peter["first_route"]["replacement_strategy"],
                "append_only_new_adult_body_build",
            )
            self.assertEqual(cases["marinette_non_adult_lane"]["maturity_remains"], "non_adult_doll_safe")
            self.assertEqual(
                cases["detachable_hair_component_isolation"]["component_hashes_before"],
                cases["detachable_hair_component_isolation"]["component_hashes_after"],
            )
            spa = cases["two_stage_spa_age_progression"]
            self.assertFalse(spa["stage_one_route"]["age_progression"]["stage_1"]["adult_anatomy_allowed"])
            self.assertTrue(spa["stage_two_contract"]["stage_2"]["adult_anatomy_allowed"])
            self.assertTrue(result["scope"]["body_geometry_generated"] is False)

    def test_existing_attempt_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="avatar_builder_temp_acceptance_immutable_") as temp:
            output = Path(temp) / "attempt_01"
            run_acceptance(output)
            with self.assertRaises(FileExistsError):
                run_acceptance(output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
