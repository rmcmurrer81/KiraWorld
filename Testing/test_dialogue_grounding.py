import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import Core.dialogue_grounding as dialogue_grounding
from Core.dialogue_continuity import build_continuity_candidate
from Core.dialogue_grounding import load_approved_shared_continuity, load_dialogue_grounding


class DialogueGroundingTests(unittest.TestCase):
    @staticmethod
    def _canonical_sha(value) -> str:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _write_private_sidecar(self, root: Path, owner: str, secret: str, truth: str) -> None:
        speaker = owner.title()
        entry = {
            "turn": 1,
            "speaker": speaker,
            "private_mind": secret,
            "truth_flags": truth,
            "raw": f"raw-{owner}-must-not-load",
            "at": "now",
        }
        entry["private_mind_sha256"] = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        entry["truth_flags_sha256"] = hashlib.sha256(truth.encode("utf-8")).hexdigest()
        entry["raw_sha256"] = hashlib.sha256(entry["raw"].encode("utf-8")).hexdigest()
        entry["private_record_sha256"] = self._canonical_sha(entry)
        data = {
            "schema_version": 1,
            "dialogue_id": "prior",
            "owner_scope": owner,
            "other_dialogue_role_access_allowed": False,
            "tts_allowed": False,
            "public_export_allowed": False,
            "role_confidentiality_enforced": False,
            "storage_boundary": "logical_separation_only_same_os_user_can_read_file",
            "entries": [entry],
        }
        data["private_payload_sha256"] = self._canonical_sha(data["entries"])
        folder = root / "Data/dialogues/kira_robert_intro/private" / owner
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "prior.private.json").write_text(json.dumps(data), encoding="utf-8")

    def _root(self, temp: str) -> Path:
        root = Path(temp)
        (root / "Data/identity/robert_mcmurrer").mkdir(parents=True)
        (root / "Data/dialogues/kira_robert_intro/continuity").mkdir(parents=True)
        policy_dir = root / "Data/dialogues/kira_robert_intro/policies"
        policy_dir.mkdir(parents=True)
        checked_in_registry = (
            Path(__file__).resolve().parents[1]
            / "Data/dialogues/kira_robert_intro/policies/continuity_approval_registry.json"
        )
        (policy_dir / "continuity_approval_registry.json").write_bytes(
            checked_in_registry.read_bytes()
        )
        (root / "Data/memories_kira.json").write_text(
            json.dumps([
                {"owner": "kira", "status": "approved", "summary": "Kira-only memory.", "importance": {"score": 1}},
                {"owner": "kira", "status": "draft", "summary": "Unapproved memory."},
            ]),
            encoding="utf-8",
        )
        (root / "Data/identity/robert_mcmurrer/robert_source_memory_20260715.json").write_text(
            json.dumps({"canonical_identity": {"home": "Newark"}, "hard_false_memory_firewall": ["No invented school friends."]}),
            encoding="utf-8",
        )
        return root

    def test_role_private_sources_are_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            grounding = load_dialogue_grounding(self._root(temp))
            self.assertIn("Kira-only memory", grounding["role_text"]["Kira"])
            self.assertNotIn("Kira-only memory", grounding["role_text"]["Robert"])
            self.assertIn("Newark", grounding["role_text"]["Robert"])
            self.assertNotIn("Newark", grounding["role_text"]["Kira"])
            self.assertFalse(grounding["audit"]["cross_role_private_sharing"])

    def test_prior_private_belief_and_truth_tail_return_only_to_owning_role(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            self._write_private_sidecar(root, "kira", "Kira prior belief.", "Kira uncertain truth flag.")
            self._write_private_sidecar(root, "robert", "Robert prior belief.", "Robert boast flag.")
            grounding = load_dialogue_grounding(root)
            self.assertIn("Kira prior belief.", grounding["role_text"]["Kira"])
            self.assertIn("Kira uncertain truth flag.", grounding["role_text"]["Kira"])
            self.assertNotIn("Robert prior belief.", grounding["role_text"]["Kira"])
            self.assertIn("Robert prior belief.", grounding["role_text"]["Robert"])
            self.assertNotIn("Kira prior belief.", grounding["role_text"]["Robert"])
            self.assertNotIn("raw-kira-must-not-load", grounding["role_text"]["Kira"])
            self.assertFalse(
                grounding["audit"]["kira_private_dialogue_continuity"]["tts_allowed"]
            )

    def test_no_approved_continuity_means_no_false_recall(self):
        with tempfile.TemporaryDirectory() as temp:
            grounding = load_dialogue_grounding(self._root(temp))
            self.assertIn("Do not claim", grounding["shared_text"])

    def test_candidate_never_auto_promotes(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "session.json"
            source.write_text("{}", encoding="utf-8")
            candidate = build_continuity_candidate(
                {"dialogue_id": "x", "status": "complete", "target_reached": True, "transcript": []},
                source_path=source,
                source_context_contamination_count=0,
            )
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual("review_required_not_promoted", candidate["status"])

    def test_forged_or_private_marked_continuity_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            path = root / "Data/dialogues/kira_robert_intro/continuity/forged.approved.json"
            path.write_text(json.dumps({
                "status": "approved_shared_continuity",
                "public_summary": "Hello.\nPRIVATE MIND: secret",
            }), encoding="utf-8")
            text, audit = load_approved_shared_continuity(root)
            self.assertIn("No reviewed shared", text)
            self.assertEqual(0, audit["approved_count"])
            self.assertEqual(1, audit["rejected_count"])

    def test_title_case_private_summary_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            path = root / "Data/dialogues/kira_robert_intro/continuity/private.approved.json"
            summary = "Public sentence.\nConfidential Notes: do not share"
            path.write_text(json.dumps({
                "status": "approved_shared_continuity",
                "public_summary": summary,
                "public_summary_sha256": hashlib.sha256(summary.encode("utf-8")).hexdigest(),
            }), encoding="utf-8")
            text, audit = load_approved_shared_continuity(root)
            self.assertIn("No reviewed shared", text)
            self.assertEqual("empty_or_private_marker_in_summary", audit["rejected_records"][0]["reason"])

    def test_separate_approval_artifact_must_bind_source_summary_and_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            continuity_dir = root / "Data/dialogues/kira_robert_intro/continuity"
            source = root / "Data/dialogues/kira_robert_intro/source.json"
            source.write_text('{"transcript": []}', encoding="utf-8")
            source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            summary = "Kira and Robert discussed a public boundary."
            summary_sha = hashlib.sha256(summary.encode("utf-8")).hexdigest()
            record = continuity_dir / "valid.approved.json"
            approval = continuity_dir / "valid.approval.json"
            record.write_text(json.dumps({
                "status": "approved_shared_continuity",
                "public_summary": summary,
                "public_summary_sha256": summary_sha,
                "source_dialogue": str(source.relative_to(root)),
                "source_dialogue_sha256": source_sha,
                "approval_artifact": str(approval.relative_to(root)),
            }), encoding="utf-8")
            approval.write_text(json.dumps({
                "status": "approved",
                "reviewer_id": "robert_mcmurrer",
                "continuity_file_sha256": hashlib.sha256(record.read_bytes()).hexdigest(),
                "public_summary_sha256": summary_sha,
                "source_dialogue_sha256": source_sha,
            }), encoding="utf-8")
            text, audit = load_approved_shared_continuity(root)
            self.assertIn("No reviewed shared", text)
            self.assertEqual("approval_not_listed_in_owner_registry", audit["rejected_records"][0]["reason"])

            registry_path = root / dialogue_grounding.CONTINUITY_APPROVAL_REGISTRY_RELATIVE_PATH
            registry = {
                "schema_version": 1,
                "registry_type": "owner_controlled_dialogue_continuity_approval_registry",
                "owner_id": "robert_mcmurrer",
                "status": "active",
                "policy": {
                    "default": "deny",
                    "require_exact_approval_artifact_sha256": True,
                    "require_continuity_source_summary_bindings": True,
                },
                "entries": [{
                    "status": "approved",
                    "approval_artifact_sha256": hashlib.sha256(approval.read_bytes()).hexdigest(),
                    "continuity_file_sha256": hashlib.sha256(record.read_bytes()).hexdigest(),
                    "source_dialogue_sha256": source_sha,
                    "public_summary_sha256": summary_sha,
                }],
            }
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            registry_sha = hashlib.sha256(registry_path.read_bytes()).hexdigest()
            with patch.object(
                dialogue_grounding,
                "CONTINUITY_APPROVAL_REGISTRY_SHA256",
                registry_sha,
            ):
                text, audit = load_approved_shared_continuity(root)
            self.assertIn(summary, text)
            self.assertEqual(1, audit["approved_count"])

    def test_tampered_owner_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            registry = root / dialogue_grounding.CONTINUITY_APPROVAL_REGISTRY_RELATIVE_PATH
            registry.write_text("{}", encoding="utf-8")
            _, audit = load_approved_shared_continuity(root)
            self.assertFalse(audit["owner_approval_registry"]["valid"])
            self.assertIn(
                "registry_code_pinned_hash_mismatch",
                audit["owner_approval_registry"]["failures"],
            )

    def test_checked_in_public_continuity_is_owner_bound_and_not_first_meeting(self):
        project_root = Path(__file__).resolve().parents[1]
        text, audit = load_approved_shared_continuity(project_root)
        self.assertEqual(1, audit["approved_count"])
        self.assertTrue(audit["owner_approval_registry"]["valid"])
        self.assertIn("never a first meeting", text)
        self.assertIn("generated text conversations", text)
        self.assertNotIn("PRIVATE_MIND", text)
        self.assertNotIn("TRUTH_FLAGS", text)


if __name__ == "__main__":
    unittest.main()
