import sys
import unittest
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_memory_reconstruction_world import validate_world  # noqa: E402


class MemoryReconstructionWorldValidatorTests(unittest.TestCase):
    def test_minimal_valid_world_passes(self) -> None:
        data = {
            "reconstruction_id": "memworld_001",
            "source_memory_id": "mem_001",
            "title": "Memory World",
            "world_type": "memory_reconstruction",
            "status": "draft",
            "phase_support": {"pre_gpu_recall": True, "post_gpu_world": False},
            "owners": ["kira"],
            "participants_in_memory": ["kira"],
            "privacy": {
                "level": "private",
                "consent_required_from": ["kira"],
            },
            "pre_gpu_recall": {},
            "post_gpu_world": {},
            "confirmed_zones": [{"zone_id": "known", "description": "Known detail."}],
            "inferred_zones": [],
            "unknown_zones": ["Exact dialogue."],
            "sealed_private_zones": [],
            "perspectives": {"kira": {}},
            "forbidden_inferences": ["Do not invent exact dialogue."],
        }

        self.assertEqual(validate_world(data), [])

    def test_private_shared_requires_consent(self) -> None:
        data = {
            "reconstruction_id": "memworld_002",
            "source_memory_id": "mem_002",
            "title": "Shared Memory World",
            "world_type": "memory_reconstruction",
            "status": "draft",
            "phase_support": {"pre_gpu_recall": True, "post_gpu_world": False},
            "owners": ["kira", "lisa"],
            "participants_in_memory": ["kira", "lisa"],
            "privacy": {"level": "private_shared"},
            "pre_gpu_recall": {},
            "post_gpu_world": {},
            "confirmed_zones": [{"zone_id": "known", "description": "Known detail."}],
            "inferred_zones": [],
            "unknown_zones": [],
            "sealed_private_zones": [],
            "perspectives": {"kira": {}, "lisa": {}},
            "forbidden_inferences": ["Do not invent exact dialogue."],
        }

        errors = validate_world(data)
        self.assertTrue(any("consent_required_from" in error for error in errors))

    def test_sealed_private_zone_requires_controls(self) -> None:
        data = {
            "reconstruction_id": "memworld_003",
            "source_memory_id": "mem_003",
            "title": "Private Zone",
            "world_type": "memory_reconstruction",
            "status": "draft",
            "phase_support": {"pre_gpu_recall": True, "post_gpu_world": False},
            "owners": ["kira", "lisa"],
            "participants_in_memory": ["kira", "lisa"],
            "privacy": {
                "level": "private_shared",
                "consent_required_from": ["kira", "lisa"],
            },
            "pre_gpu_recall": {},
            "post_gpu_world": {},
            "confirmed_zones": [{"zone_id": "known", "description": "Known detail."}],
            "inferred_zones": [],
            "unknown_zones": [],
            "sealed_private_zones": [{"zone_id": "locked"}],
            "perspectives": {"kira": {}, "lisa": {}},
            "forbidden_inferences": ["Do not expose private details."],
        }

        errors = validate_world(data)
        self.assertTrue(any("sealed_private_zones[0]" in error for error in errors))

    def test_ordinary_family_reconstruction_worlds_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "memory_reconstruction_worlds" / "kira_owen_tv_argument_001.draft.json",
            PROJECT_ROOT / "Data" / "memory_reconstruction_worlds" / "kira_grounded_late_001.draft.json",
            PROJECT_ROOT / "Data" / "memory_reconstruction_worlds" / "lisa_melanie_shared_space_argument_001.draft.json",
            PROJECT_ROOT / "Data" / "memory_reconstruction_worlds" / "lisa_grounded_late_001.draft.json",
        ]

        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_world(data), [])
                self.assertIn("Do not invent exact dialogue.", data["forbidden_inferences"])


if __name__ == "__main__":
    unittest.main()
