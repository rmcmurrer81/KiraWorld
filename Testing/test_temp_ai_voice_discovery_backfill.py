from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from Core.temp_ai_voice_discovery import (
    build_candidate_voice_discovery_request,
    validate_request,
)
from Core.temp_ai_voice_discovery_backfill import (
    AUTHORIZATION_STATUS,
    apply_voice_discovery_backfill,
    discover_profile_candidates,
    discovery_stage_boundary_proof,
    identity_and_source_blockers,
    plan_voice_discovery_backfill,
    validate_private_exact_voice_authorization,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def profile(candidate_id: str, *, category: str = "Fictional Character", version: str = "") -> dict:
    return {
        "candidate_id": candidate_id,
        "display_name": candidate_id.replace("_", " ").title(),
        "ui_category": category,
        "ai_type": "canon_reconstruction_temp_ai" if category == "Fictional Character" else "expert_temp_ai",
        "gender_preference": "Female",
        "knowledge_plan": {"version_or_life_point": version},
    }


def write_profile(root: Path, candidate_id: str, data: dict) -> Path:
    directory = root / candidate_id
    directory.mkdir(parents=True)
    (directory / "temporary_ai_profile.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    return directory


def valid_authorization() -> dict:
    return {
        "schema_version": 1,
        "authorization_id": "robert_private_exact_temp_ai_voice_authorization_20260716",
        "status": AUTHORIZATION_STATUS,
        "visibility": "project_private",
        "authorized_by": {"name": "Robert McMurrer", "project_owner": True},
        "future_scope": {
            "exact_voice_model_preparation_allowed_later": True,
            "private_candidate_voice_assignment_allowed_later": True,
            "public_release_allowed": False,
            "official_voice_claim_allowed": False,
        },
        "required_clip_conditions": {
            "human_confirmed_target_only": True,
            "character_id_confirmed": True,
            "variant_id_confirmed": True,
            "speaker_id_confirmed": True,
            "performer_id_confirmed_when_applicable": True,
            "mixed_or_overlapping_speakers_rejected": True,
            "source_and_artifact_hashes_bound": True,
        },
        "operations_now": {
            "download_media": False,
            "extract_audio": False,
            "clone_or_train_voice": False,
            "prepare_voice_model": False,
            "assign_voice": False,
            "activate_candidate": False,
            "publish_or_claim_official": False,
        },
        "stage_boundaries": {
            "metadata_discovery_remains_no_download": True,
            "private_local_intake_is_separate": True,
            "authorization_record_executes_no_operation": True,
        },
    }


class TempAiVoiceDiscoveryBackfillTests(unittest.TestCase):
    def test_profile_inventory_excludes_profileless_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_profile(root, "real_candidate", profile("real_candidate"))
            (root / "prompt_smoke").mkdir()
            candidates, excluded = discover_profile_candidates(root)
            self.assertEqual([item.name for item in candidates], ["real_candidate"])
            self.assertEqual(excluded, [{"candidate_id": "prompt_smoke", "reason": "no_temporary_ai_profile"}])

    def test_apply_creates_only_missing_and_preserves_existing_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing_dir = write_profile(
                root,
                "existing_candidate",
                profile("existing_candidate", version="selected continuity"),
            )
            missing_dir = write_profile(root, "missing_candidate", profile("missing_candidate"))
            existing = build_candidate_voice_discovery_request(
                profile("existing_candidate", version="selected continuity"), {}
            )
            existing_path = existing_dir / "voice_discovery_request.json"
            sentinel = json.dumps(existing, indent=3) + "\n"
            existing_path.write_text(sentinel, encoding="utf-8")

            result = apply_voice_discovery_backfill(root)

            self.assertEqual(existing_path.read_text(encoding="utf-8"), sentinel)
            created_path = missing_dir / "voice_discovery_request.json"
            self.assertTrue(created_path.is_file())
            created = json.loads(created_path.read_text(encoding="utf-8"))
            validate_request(created, expected_candidate_id="missing_candidate")
            self.assertTrue(discovery_stage_boundary_proof(created)["passed"])
            self.assertTrue(result["all_requests_stage_boundary_passed"])
            self.assertTrue(result["discovery_no_download_is_stage_scoped"])
            self.assertEqual(result["operations_performed"]["media_downloads"], 0)
            self.assertEqual(result["operations_performed"]["voice_models_prepared_or_trained"], 0)
            self.assertEqual(result["operations_performed"]["voices_assigned"], 0)

    def test_plan_reports_blank_version_performer_and_source(self) -> None:
        request = build_candidate_voice_discovery_request(profile("blank_fictional"), {})
        blockers = identity_and_source_blockers(request)
        self.assertIn("version_or_timepoint_blank", blockers)
        self.assertIn("fictional_variant_blank_or_unresolved", blockers)
        self.assertIn("performer_blank_or_unresolved", blockers)
        self.assertIn("human_confirmed_target_only_recording_source_missing", blockers)

    def test_authorization_is_future_private_and_executes_nothing(self) -> None:
        record = valid_authorization()
        self.assertEqual(validate_private_exact_voice_authorization(record), [])
        public = copy.deepcopy(record)
        public["future_scope"]["public_release_allowed"] = True
        self.assertIn(
            "future_scope_is_not_private_and_bounded",
            validate_private_exact_voice_authorization(public),
        )
        active = copy.deepcopy(record)
        active["operations_now"]["assign_voice"] = True
        self.assertIn(
            "operation_now_must_be_false:assign_voice",
            validate_private_exact_voice_authorization(active),
        )
        mixed = copy.deepcopy(record)
        mixed["required_clip_conditions"]["mixed_or_overlapping_speakers_rejected"] = False
        self.assertIn(
            "required_clip_condition_missing:mixed_or_overlapping_speakers_rejected",
            validate_private_exact_voice_authorization(mixed),
        )

    def test_current_repository_has_23_real_profiles_and_two_smoke_artifacts(self) -> None:
        root = PROJECT_ROOT / "TemporaryAI" / "candidates"
        candidates, excluded = discover_profile_candidates(root)
        self.assertEqual(len(candidates), 23)
        self.assertIn(
            "elsa_frozen_frozen_fever_frozen_ii_20260716",
            {item.name for item in candidates},
        )
        self.assertEqual(
            {item["candidate_id"] for item in excluded},
            {"emily_continuity_smoke", "ladybug_prompt_smoke"},
        )
        plan = plan_voice_discovery_backfill(root)
        self.assertEqual(plan["errors"], [])
        self.assertEqual(len(plan["rows"]), 23)
        self.assertTrue(all(row["stage_boundary"]["passed"] for row in plan["rows"]))

    def test_checked_in_authorization_record_validates(self) -> None:
        path = (
            PROJECT_ROOT
            / "Voice"
            / "authorizations"
            / "robert_private_exact_temp_ai_voice_authorization_20260716.json"
        )
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validate_private_exact_voice_authorization(record), [])


if __name__ == "__main__":
    unittest.main()
