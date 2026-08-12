import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import create_world_notebook_request as generator  # noqa: E402
from validate_notebook_world_request import validate_notebook_world_request  # noqa: E402


class WorldNotebookRequestGeneratorTests(unittest.TestCase):
    def test_louvre_seed_creates_valid_paris_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_root = generator.DEFAULT_WORLD_ROOT
            original_index = generator.DEFAULT_INDEX_PATH
            try:
                generator.DEFAULT_WORLD_ROOT = Path(temp_dir) / "worlds"
                generator.DEFAULT_INDEX_PATH = Path(temp_dir) / "index.json"
                seed = generator.infer_seed("Louvre Courtyard", city="Paris")
                paths = generator.create_files(seed, "robert", "test", "private_only", "request_mode", "draft")
                data = json.loads(paths["request"].read_text(encoding="utf-8"))
                self.assertEqual(validate_notebook_world_request(data), [])
                self.assertEqual(data["schema_version"], 2)
                self.assertEqual(data["world_plan"]["notebook_world_id"], "paris_notebook_world")
                self.assertFalse(data["isolation_policy"]["home_world_mutation_allowed"])
                self.assertTrue(paths["quality_gate"].exists())
                self.assertTrue(paths["resource_isolation_gate"].exists())
                placement = json.loads(paths["placement"].read_text(encoding="utf-8"))
                self.assertEqual(placement["real_world_coordinates"]["latitude"], 48.8606)
            finally:
                generator.DEFAULT_WORLD_ROOT = original_root
                generator.DEFAULT_INDEX_PATH = original_index

    def test_generator_rejects_non_draft_promotion(self) -> None:
        seed = generator.infer_seed("College Campus")
        with self.assertRaisesRegex(ValueError, "draft-only"):
            generator.create_files(seed, "robert", "test", "private_only", "request_mode", "active")

    def test_draft_anchor_is_not_used_as_coordinate_origin(self) -> None:
        seed = generator.infer_seed("Louvre Courtyard", city="Paris")
        index = {
            "schema_version": 1,
            "notebook_worlds": {
                "paris_notebook_world": {
                    "anchors": [
                        {
                            "request_id": "notebook_world_unapproved_anchor_001",
                            "status": "draft",
                            "placement_approved": False,
                            "real_world_coordinates": {"latitude": 48.86, "longitude": 2.33},
                        }
                    ]
                }
            },
        }
        placement = generator.placement_for(seed, index)
        self.assertEqual(placement["placement_status"], "coordinates_known_no_approved_anchor")
        self.assertEqual(placement["unapproved_candidate_anchors_ignored"], 1)

    def test_college_seed_uses_sequential_collection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_root = generator.DEFAULT_WORLD_ROOT
            original_index = generator.DEFAULT_INDEX_PATH
            try:
                generator.DEFAULT_WORLD_ROOT = Path(temp_dir) / "worlds"
                generator.DEFAULT_INDEX_PATH = Path(temp_dir) / "index.json"
                seed = generator.infer_seed("College Campus")
                paths = generator.create_files(seed, "robert", "test", "private_only", "request_mode", "draft")
                data = json.loads(paths["request"].read_text(encoding="utf-8"))
                self.assertEqual(data["world_plan"]["collection_id"], "education_notebook_collection")
                self.assertEqual(data["isolation_policy"]["runtime_load_policy"], "one_notebook_world_at_a_time")
                self.assertFalse(data["isolation_policy"]["co_load_with_other_notebook_worlds"])
            finally:
                generator.DEFAULT_WORLD_ROOT = original_root
                generator.DEFAULT_INDEX_PATH = original_index

    def test_v2_validator_rejects_home_mutation_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_root = generator.DEFAULT_WORLD_ROOT
            original_index = generator.DEFAULT_INDEX_PATH
            try:
                generator.DEFAULT_WORLD_ROOT = Path(temp_dir) / "worlds"
                generator.DEFAULT_INDEX_PATH = Path(temp_dir) / "index.json"
                seed = generator.infer_seed("College Campus")
                paths = generator.create_files(seed, "robert", "test", "private_only", "request_mode", "draft")
                data = json.loads(paths["request"].read_text(encoding="utf-8"))
                data["isolation_policy"]["home_world_mutation_allowed"] = True
                errors = validate_notebook_world_request(data)
                self.assertTrue(any("home_world_mutation_allowed" in error for error in errors))
            finally:
                generator.DEFAULT_WORLD_ROOT = original_root
                generator.DEFAULT_INDEX_PATH = original_index

    def test_malformed_index_is_rejected_before_request_folder_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_root = generator.DEFAULT_WORLD_ROOT
            original_index = generator.DEFAULT_INDEX_PATH
            try:
                generator.DEFAULT_WORLD_ROOT = Path(temp_dir) / "worlds"
                generator.DEFAULT_INDEX_PATH = Path(temp_dir) / "index.json"
                generator.write_json(
                    generator.DEFAULT_INDEX_PATH,
                    {"schema_version": 1, "notebook_worlds": {"Unsafe World Id": {"anchors": []}}},
                )
                seed = generator.infer_seed("College Campus")
                with self.assertRaisesRegex(ValueError, "invalid world id"):
                    generator.create_files(seed, "robert", "test", "private_only", "request_mode", "draft")
                self.assertFalse(generator.DEFAULT_WORLD_ROOT.exists())
            finally:
                generator.DEFAULT_WORLD_ROOT = original_root
                generator.DEFAULT_INDEX_PATH = original_index

    def test_brown_derby_seed_adds_historic_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_root = generator.DEFAULT_WORLD_ROOT
            original_index = generator.DEFAULT_INDEX_PATH
            try:
                generator.DEFAULT_WORLD_ROOT = Path(temp_dir) / "worlds"
                generator.DEFAULT_INDEX_PATH = Path(temp_dir) / "index.json"
                seed = generator.infer_seed("The Brown Derby", city="Los Angeles")
                paths = generator.create_files(seed, "robert", "test", "private_only", "request_mode", "draft")
                data = json.loads(paths["request"].read_text(encoding="utf-8"))
                self.assertEqual(validate_notebook_world_request(data), [])
                self.assertEqual(data["subject"]["category"], "real_historic_place")
                self.assertEqual(data["subject"]["era"], "1930s")
                source_tasks = json.loads(paths["source_tasks"].read_text(encoding="utf-8"))
                task_ids = {task["task_id"] for task in source_tasks["tasks"]}
                self.assertIn("historic_variant_check", task_ids)
            finally:
                generator.DEFAULT_WORLD_ROOT = original_root
                generator.DEFAULT_INDEX_PATH = original_index

    def test_generic_explicit_seed_overrides_do_not_require_hardcoded_place_logic(self) -> None:
        seed = generator.infer_seed("Synthetic People Filming Backlot", category="original_idea")
        returned = generator.apply_seed_overrides(
            seed,
            notebook_world_id="synthetic_people_filming_backlot_notebook_world",
            notebook_title="Synthetic People Filming Backlot Notebook World",
            region="Production Notebook Worlds",
            country="Virtual",
            starting_area="two-room soundstage and unfinished facade",
            initial_scope="two_room_filming_prototype",
        )
        self.assertIs(returned, seed)
        self.assertEqual(seed.notebook_world_id, "synthetic_people_filming_backlot_notebook_world")
        self.assertEqual(seed.starting_area, "two-room soundstage and unfinished facade")
        self.assertEqual(seed.initial_scope, "two_room_filming_prototype")


if __name__ == "__main__":
    unittest.main()
