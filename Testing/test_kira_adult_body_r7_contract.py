from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_adult_body_r7_contract"
    / "r7_build_contract.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraAdultBodyR7ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_is_inactive_and_does_not_claim_anatomy(self) -> None:
        self.assertEqual(self.contract["status"], "contract_only_no_model")
        truth = self.contract["truth_limits"]
        self.assertFalse(truth["complete_adult_anatomy_proven"])
        self.assertFalse(truth["stable_working_rig_proven"])
        self.assertFalse(truth["runtime_activation_allowed"])
        self.assertFalse(truth["multi_body_autobuild_allowed"])

    def test_rollback_hashes_match_exact_files(self) -> None:
        for record in self.contract["rollback_inputs"].values():
            path = PROJECT_ROOT / record["path"]
            self.assertTrue(path.is_file(), path)
            self.assertEqual(sha256_file(path), record["sha256"])

    def test_original_light_skin_tone_is_preserved(self) -> None:
        surface = self.contract["surface_and_material_contract"]
        tone = surface["base_skin_tone"]
        self.assertEqual(tone["template_id"], "caucasian_light_neutral_adult")
        self.assertEqual(tone["hex"].lower(), "#e6c0a9")
        self.assertEqual(tone["rgb"], [230, 192, 169])
        evidence = surface["current_r6_material_evidence"]
        self.assertEqual(evidence["material_count"], 1)
        self.assertFalse(evidence["semantic_body_region_masks_present"])
        self.assertFalse(evidence["reliable_localized_coloration_possible_now"])
        self.assertFalse(
            surface["localized_color_requirements"]["coloration_counts_as_topology_proof"]
        )

    def test_reference_intakes_are_pinned_and_not_auto_importable(self) -> None:
        evidence = self.contract["reference_evidence"]
        for key in ("folder_9_intake", "folder_91_intake"):
            record = evidence[key]
            self.assertFalse(record["automatic_import_allowed"])
            self.assertTrue((PROJECT_ROOT / record["manifest"]).is_file())
        beth = evidence["beth_exact_source"]
        self.assertTrue(beth["adaptation_allowed_with_attribution"])
        self.assertEqual(beth["rig"], "none")
        self.assertFalse(beth["direct_kira_body_use_allowed"])

    def test_contract_forbids_live_overwrite_and_guessed_uv_paint(self) -> None:
        prohibited = " ".join(self.contract["prohibited_actions"]).lower()
        self.assertIn("home world main.js", prohibited)
        self.assertIn("guessed uv", prohibited)
        self.assertIn("do not activate", prohibited)


if __name__ == "__main__":
    unittest.main()
