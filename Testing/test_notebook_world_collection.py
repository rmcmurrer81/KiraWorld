import copy
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_notebook_world_collection import validate_notebook_world_collection  # noqa: E402


def valid_collection() -> dict:
    return {
        "schema_version": 1,
        "collection_id": "education_notebook_collection",
        "collection_kind": "logical_notebook_collection",
        "title": "Education Notebook Collection",
        "status": "planned_request_only",
        "runtime_policy": {
            "load_mode": "sequential_members_only",
            "max_concurrent_notebook_worlds": 1,
            "co_load_members_allowed": False,
            "loads_home_world": False,
            "loads_resident_minds": False,
            "loads_voice": False,
            "loads_ollama": False,
            "memory_reconstruction_members_allowed": False,
            "hardware_profile": "Data/launch/hardware_capability_profile.json",
            "resource_gate_path": "Data/world_builds/notebook_collections/education_notebook_collection/resource_isolation_gate.json",
        },
        "protected_world_policy": {
            "merge_into_home_world_allowed": False,
            "strip_mall_mutation_allowed": False,
        },
        "members": [
            {
                "notebook_world_id": "college_campus_core_notebook_world",
                "member_type": "place_notebook_world",
                "status": "request_prepared",
                "prepared_request_path": "Data/world_builds/notebook_worlds/college_campus_core_notebook_world/request.json",
            },
            {
                "notebook_world_id": "college_campus_labs_notebook_world",
                "member_type": "place_notebook_world",
                "status": "queued_not_requested",
                "prepared_request_path": None,
            },
        ],
    }


def hardware_profile(ram_gb: int = 32) -> dict:
    return {"known_build": {"current_observed_ram": {"capacity_gb": ram_gb}}}


class NotebookWorldCollectionTests(unittest.TestCase):
    def test_sequential_collection_passes_at_32gb(self) -> None:
        self.assertEqual(validate_notebook_world_collection(valid_collection(), hardware_profile()), [])

    def test_co_load_policy_fails_at_32gb(self) -> None:
        data = copy.deepcopy(valid_collection())
        data["runtime_policy"]["co_load_members_allowed"] = True
        data["runtime_policy"]["max_concurrent_notebook_worlds"] = 2
        errors = validate_notebook_world_collection(data, hardware_profile())
        self.assertTrue(any("co_load_members_allowed" in error for error in errors))
        self.assertTrue(any("Below 64GB" in error for error in errors))

    def test_home_or_strip_mall_mutation_fails(self) -> None:
        data = copy.deepcopy(valid_collection())
        data["protected_world_policy"]["merge_into_home_world_allowed"] = True
        data["protected_world_policy"]["strip_mall_mutation_allowed"] = True
        errors = validate_notebook_world_collection(data, hardware_profile())
        self.assertTrue(any("merge_into_home_world_allowed" in error for error in errors))
        self.assertTrue(any("strip_mall_mutation_allowed" in error for error in errors))

    def test_memory_reconstruction_cannot_be_a_member(self) -> None:
        data = copy.deepcopy(valid_collection())
        data["members"][0]["member_type"] = "memory_reconstruction"
        errors = validate_notebook_world_collection(data, hardware_profile())
        self.assertTrue(any("memory reconstructions" in error for error in errors))

    def test_deployed_member_requires_pinned_manifest(self) -> None:
        data = copy.deepcopy(valid_collection())
        data["members"][0]["status"] = "deployed"
        errors = validate_notebook_world_collection(data, hardware_profile())
        self.assertTrue(any("pinned_deployment" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
