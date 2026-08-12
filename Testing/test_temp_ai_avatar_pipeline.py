from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core import temp_ai_avatar_pipeline as pipeline  # noqa: E402
from Core.avatar_asset_library import AvatarMaturityPolicyError  # noqa: E402


class TemporaryAIAvatarPipelineTests(unittest.TestCase):
    def test_named_desktop_folder_matches_exact_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Kara").mkdir()
            (root / "Marinette").mkdir()
            profile = {
                "candidate_id": "kara_zor_el_my_adventures_with_superman",
                "display_name": "Kara Zor-El",
                "role_title": "My Adventures with Superman Kara Zor-El",
            }
            matches = pipeline.matching_reference_folders(profile, root)
            self.assertEqual([item.name for item in matches], ["Kara"])

    def test_robert_avatar_base_folder_matches_robert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "robert avatar base").mkdir()
            (root / "3d models").mkdir()
            profile = {
                "candidate_id": "robert",
                "display_name": "Robert",
            }
            matches = pipeline.matching_reference_folders(profile, root)
            self.assertEqual([item.name for item in matches], ["robert avatar base"])

    def test_fictional_generation_job_locks_identity_and_all_forms(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = {
                "ai_type": "canon_reconstruction_temp_ai",
                "visual_identity": {
                    "forms": [{"id": "civilian"}, {"id": "hero"}],
                },
            }
            body_manifest = {"ready_pose_count": 6}
            with patch.object(pipeline, "AVATAR_ROOT", root):
                path = pipeline._write_generation_job(
                    "kara_smoke", profile, 12, body_manifest
                )
                result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(result["identity_mode"], "exact_version_likeness")
            self.assertEqual(result["requested_outputs"]["forms"], ["civilian", "hero"])
            self.assertFalse(result["backend_availability"]["skeleton_rigging"])

    def test_desktop_picture_intake_is_private_exact_subject_and_unapproved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "references"
            (source_root / "Kira").mkdir(parents=True)
            (source_root / "Kira" / "front.jpg").write_bytes(b"test-image-bytes")
            avatar_root = root / "Avatar" / "temp_ai"
            profile = {"candidate_id": "kira", "display_name": "Kira"}

            with patch.object(pipeline, "AVATAR_ROOT", avatar_root):
                manifest = pipeline.ingest_desktop_avatar_references(
                    "kira", profile, source_root
                )

            record = manifest["references"][0]
            self.assertEqual(record["media_type"], "image")
            self.assertEqual(record["subject_id"], "kira")
            self.assertEqual(record["privacy_scope"], "candidate_private_reference")
            self.assertTrue(record["artifact_hash_verified"])
            self.assertFalse(record["identity_evidence_approved"])
            self.assertEqual(record["status"], "copied_for_review")

    def test_generation_job_keeps_unreviewed_picture_count_out_of_staging_gate(self) -> None:
        contract = {
            "status": "blocked",
            "staging_allowed": False,
            "failures": ["no_approved_exact_subject_picture_identity_evidence"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.object(pipeline, "AVATAR_ROOT", root):
                path = pipeline._write_generation_job(
                    "kira",
                    {"candidate_id": "kira"},
                    12,
                    {"ready_pose_count": 0},
                    contract,
                )
                result = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "reference_review")
        self.assertEqual(
            result["picture_first_reconstruction_contract"]["status"], "blocked"
        )

    def test_kara_profile_has_maws_vessel_lock(self) -> None:
        profile_path = (
            PROJECT_ROOT
            / "TemporaryAI/candidates/kara_zor_el_my_adventures_with_superman_kara_zor_el_20260606_181026/temporary_ai_profile.json"
        )
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        lock = profile["adaptation_lock"]
        serialized = json.dumps(lock).lower()
        self.assertIn("vessel", serialized)
        self.assertIn("brainiac", serialized)
        self.assertIn("my adventures with superman", serialized)
        self.assertNotIn("cw supergirl", serialized)

    def test_prepare_rejects_persisted_maturity_incompatible_with_canonical_identity_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            avatar_root = Path(temp_dir) / "Avatar" / "temp_ai"
            profile = {
                "candidate_id": "kira",
                "display_name": "Kira",
                "age_review": {
                    "maturity_class_override": "non_adult_doll_safe",
                    "reason": "incompatible persisted fixture",
                },
            }
            with patch.object(pipeline, "AVATAR_ROOT", avatar_root):
                with self.assertRaisesRegex(
                    AvatarMaturityPolicyError,
                    "canonical_adult_identity_cannot_switch_to_doll_safe",
                ):
                    pipeline.prepare_candidate_avatar_pipeline(
                        "kira",
                        profile,
                        desktop_reference_root=Path(temp_dir) / "references",
                    )
            self.assertFalse((avatar_root / "kira").exists())


if __name__ == "__main__":
    unittest.main()
