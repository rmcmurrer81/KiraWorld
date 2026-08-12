import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from Core.kira_runtime_body_selection import (
    DEFAULT_SELECTION_PATH,
    evaluate_kira_runtime_body_selection,
    resolve_kira_runtime_body_path,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "Avatar/models/temp_ai/kira/avatar.glb"
R6 = ROOT / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb"
PRE_TRIAL = ROOT / "Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/kira_runtime_body_selection.pre_trial.json"
BROWSER_EVIDENCE = ROOT / "Data/world_tests/kira_r6_exact_browser_sandbox_20260718/20260718T222144Z/evidence.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class KiraRuntimeBodySelectionTests(unittest.TestCase):
    def test_real_selection_loads_exact_r6_as_reversible_review_trial(self):
        original_before = sha256(LIVE)
        result = evaluate_kira_runtime_body_selection(ROOT)
        selected = resolve_kira_runtime_body_path(ROOT)
        self.assertTrue(result["selection_valid"], result["selection_failures"])
        self.assertEqual(result["decision"], "reversible_r6_owner_review_trial_selected")
        self.assertTrue(result["candidate_runtime_allowed"])
        self.assertTrue(result["reversible_owner_review_trial"])
        self.assertEqual(selected, R6.resolve())
        self.assertEqual(result["selected_model_sha256"], sha256(R6))
        self.assertTrue(result["original_live_asset_file_unchanged"])
        self.assertEqual(sha256(LIVE), original_before)

    def test_trial_keeps_all_unproven_claims_and_clothing_separate(self):
        result = evaluate_kira_runtime_body_selection(ROOT)
        self.assertFalse(result["full_adult_anatomy_proven"])
        self.assertFalse(result["stable_working_rig_proven"])
        self.assertFalse(result["eye_visual_fit_approved"])
        self.assertFalse(result["permanent_candidate_allowed"])
        self.assertFalse(result["kira_accepted_exact_candidate"])
        self.assertTrue(result["technical_runtime_compatibility_passed"])
        self.assertTrue(result["clothing_is_separate_not_baked"])
        self.assertEqual(result["runtime_blockers"], [])
        self.assertIn(
            "exact_evidence_does_not_approve_a_complete_runtime_avatar",
            result["permanent_promotion_blockers"],
        )

    def test_exact_pre_trial_schema_one_selection_still_rolls_back(self):
        result = evaluate_kira_runtime_body_selection(ROOT, PRE_TRIAL)
        selected = resolve_kira_runtime_body_path(ROOT, PRE_TRIAL)
        self.assertTrue(result["selection_valid"], result["selection_failures"])
        self.assertFalse(result["candidate_runtime_allowed"])
        self.assertEqual(result["decision"], "retain_current_runtime_body")
        self.assertEqual(selected, LIVE.resolve())
        self.assertEqual(result["selected_model_sha256"], sha256(LIVE))

    def test_permanent_mode_cannot_reuse_trial_authorization(self):
        data = json.loads((ROOT / DEFAULT_SELECTION_PATH).read_text(encoding="utf-8"))
        data["selection_mode"] = "permanent"
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            temp_path = Path(temp_dir) / "selection.json"
            temp_path.write_text(json.dumps(data), encoding="utf-8")
            result = evaluate_kira_runtime_body_selection(ROOT, temp_path)
        self.assertFalse(result["candidate_runtime_allowed"])
        self.assertFalse(result["permanent_candidate_allowed"])
        self.assertEqual(Path(result["selected_model_path"]), LIVE.resolve())

    def test_missing_required_browser_check_fails_trial_closed(self):
        selection = json.loads((ROOT / DEFAULT_SELECTION_PATH).read_text(encoding="utf-8"))
        evidence = json.loads(BROWSER_EVIDENCE.read_text(encoding="utf-8"))
        evidence["checks"]["no_runtime_errors"] = False
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            temp_dir_path = Path(temp_dir)
            evidence_path = temp_dir_path / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            selection["evidence"]["runtime_browser_evidence"] = {
                "path": evidence_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(evidence_path),
            }
            selection_path = temp_dir_path / "selection.json"
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            result = evaluate_kira_runtime_body_selection(ROOT, selection_path)
        self.assertFalse(result["candidate_runtime_allowed"])
        self.assertEqual(Path(result["selected_model_path"]), LIVE.resolve())
        self.assertIn("trial_browser_check_not_proven:no_runtime_errors", result["runtime_blockers"])

    def test_tampered_candidate_binding_fails_closed(self):
        data = json.loads((ROOT / DEFAULT_SELECTION_PATH).read_text(encoding="utf-8"))
        modified = copy.deepcopy(data)
        modified["review_candidate"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            temp_path = Path(temp_dir) / "selection.json"
            temp_path.write_text(json.dumps(modified), encoding="utf-8")
            result = evaluate_kira_runtime_body_selection(ROOT, temp_path)
        self.assertFalse(result["selection_valid"])
        self.assertFalse(result["candidate_runtime_allowed"])
        self.assertIn("review_candidate_sha256_mismatch", result["selection_failures"])


if __name__ == "__main__":
    unittest.main()
