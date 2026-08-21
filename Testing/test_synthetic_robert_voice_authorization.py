from __future__ import annotations

import json
import unittest
from pathlib import Path

from Core.private_self_voice_authorization import validate_private_self_voice_authorization


ROOT = Path(__file__).resolve().parents[1]
AUTHORIZATION = ROOT / "Voice" / "authorizations" / "robert_self_voice_runtime_approval_20260717.json"
VOICE_PROFILE = ROOT / "Voice" / "profiles" / "temp_ai" / "robert_mcmurrer_voice_profile.json"
SYNTHETIC_ROBERT_RUNTIME_ID = "robert_mcmurrer_presence_ai"


class SyntheticRobertVoiceAuthorizationTests(unittest.TestCase):
    def test_persistent_runtime_binding_does_not_require_temporary_ai_profile(self) -> None:
        runtime_adapter = {
            "voice_and_behavior": {
                "voice_authorization": AUTHORIZATION.relative_to(ROOT).as_posix(),
                "voice_profile": VOICE_PROFILE.relative_to(ROOT).as_posix(),
            }
        }

        result = validate_private_self_voice_authorization(
            SYNTHETIC_ROBERT_RUNTIME_ID,
            runtime_adapter,
            project_root=ROOT,
        )

        self.assertTrue(result["allowed"], result["reasons"])
        self.assertEqual(result["scope"], "private_local_text_voice_chat_only")

    def test_metadata_keeps_synthetic_robert_separate_and_publication_bounded(self) -> None:
        authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8-sig"))
        profile = json.loads(VOICE_PROFILE.read_text(encoding="utf-8-sig"))
        combined = json.dumps({"authorization": authorization, "profile": profile})

        self.assertEqual(authorization["scope"]["person"], "synthetic_robert_variant")
        self.assertTrue(
            authorization["scope"]["biological_robert_and_synthetic_robert_remain_distinct"]
        )
        self.assertTrue(
            authorization["allowed"][
                "kira_world_repository_distribution_of_reviewed_reference_files"
            ]
        )
        self.assertTrue(
            authorization["not_authorized"]["unrestricted_public_voice_runtime"]
        )
        self.assertEqual(profile["target_type"], "synthetic_robert_persistent_runtime")
        self.assertNotIn("Codex", combined)
        self.assertNotIn("TemporaryAI/candidates/robert", combined)


if __name__ == "__main__":
    unittest.main()
