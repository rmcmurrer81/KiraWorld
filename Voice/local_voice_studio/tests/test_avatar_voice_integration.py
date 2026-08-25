from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from . import support as _support  # adds the local src tree to sys.path
from kira_local_voice.avatar_voice_integration import (
    AvatarTemporaryCreatorVoiceIntegration,
    HISTORICAL_DISCLOSURE,
)
from kira_local_voice.errors import ValidationError
from kira_local_voice.temporary_creator_adapter import TemporaryCreatorVoiceAdapter
from kira_local_voice.voice_design import VoiceDesignBrief


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


class IntegrationFixture:
    candidate_id = "expert-one"
    subject_id = "expert-one-subject"

    def __init__(self, root: Path, *, locale: str | None = None):
        self.root = root
        self.registry_path = root / "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json"
        self.profile_path = root / f"TemporaryAI/candidates/{self.candidate_id}/temporary_ai_profile.json"
        self.request_path = self.profile_path.parent / "voice_discovery_request.json"
        self.creation_path = self.profile_path.parent / "creation_request.json"
        self.preflight_path = root / "Core/avatar_profile_preflight.py"
        (root / "Voice/profiles/temp_ai").mkdir(parents=True, exist_ok=True)
        write_json(
            self.registry_path,
            {
                "schema_version": 1,
                "candidates": [
                    {
                        "canonical_candidate_id": self.candidate_id,
                        "subject_id": self.subject_id,
                        "identity_class": "generated_expert",
                        "inventory_scope": "current_temporary_ai_profile",
                        "aliases": ["expert-one-alias"],
                        "version_policy": {"required": False},
                        "maturity_policy": {"lane": "adult"},
                        "adult_variant_policy": {"separate_variant_required": False},
                    }
                ],
            },
        )
        profile = {
            "candidate_id": self.candidate_id,
            "display_name": "Expert One",
            "role_title": "Robotics expert",
            "gender_preference": "Female",
            "knowledge_plan": {"gender_preference": "Female"},
            "avatar_identity_selection": {"maturity_lane": "adult", "body_authored": False},
        }
        if locale is not None:
            profile["locale"] = locale
        write_json(self.profile_path, profile)
        write_json(
            self.request_path,
            {
                "candidate_id": self.candidate_id,
                "status": "metadata_discovery_request_not_run",
                "policy": {"activation_allowed": False},
            },
        )
        write_json(
            self.creation_path,
            {
                "candidate_id": self.candidate_id,
                "status": "draft_pending_review",
                "voice_plan": {"status": "metadata_discovery_not_run"},
            },
        )
        write_json(
            self.profile_path.parent / "activation_plan.json",
            {"candidate_id": self.candidate_id, "status": "pending_review"},
        )
        self.preflight_path.parent.mkdir(parents=True, exist_ok=True)
        self.preflight_path.write_text(
            "def evaluate_avatar_profile_preflight(*args, **kwargs):\n    return {}\n",
            encoding="utf-8",
        )

    def evaluator(self, project_root: Path, requested_candidate_id: str) -> dict:
        return {
            "registry_binding_verified": True,
            "canonical_candidate_id": self.candidate_id,
            "registry": {"sha256": hashlib.sha256(self.registry_path.read_bytes()).hexdigest()},
            "canonical_profile": {
                "path": self.profile_path.relative_to(self.root).as_posix(),
                "sha256": hashlib.sha256(self.profile_path.read_bytes()).hexdigest(),
            },
            "identity": {
                "subject_id": self.subject_id,
                "identity_class": "generated_expert",
                "selected_version": "",
            },
            "maturity": {"lane": "adult"},
            "failures": [],
            "authoring_allowed": True,
        }

    def integration(self) -> AvatarTemporaryCreatorVoiceIntegration:
        adapter = TemporaryCreatorVoiceAdapter(self.root, preflight_evaluator=self.evaluator)
        return AvatarTemporaryCreatorVoiceIntegration(self.root, adapter=adapter)


class AvatarVoiceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_voice_creates_only_source_attested_nonbinding_brief(self):
        fixture = IntegrationFixture(self.root)
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (fixture.profile_path, fixture.request_path, fixture.creation_path)
        }
        plan = fixture.integration().build_plan(audition_locale="en-US")
        self.assertEqual(plan["summary"]["registered_candidate_count"], 1)
        self.assertEqual(plan["summary"]["nonbinding_audition_brief_count"], 1)
        item = plan["candidates"][0]
        self.assertEqual(item["action"], "prepare_nonbinding_audition_brief")
        brief = VoiceDesignBrief.from_dict(item["audition_brief"])
        self.assertEqual(brief.gender.value, "female")
        self.assertEqual(brief.language_provenance.value, "application_audition_default")
        self.assertEqual(
            item["creator_source_attestation"]["voice_discovery_request_sha256"],
            brief.source_attestation.request_sha256,
        )
        self.assertTrue(item["review_gates"]["human_audition_required"])
        self.assertTrue(item["review_gates"]["source_locale_confirmation_required_before_binding"])
        self.assertFalse(item["review_gates"]["owner_approval_can_activate"])
        self.assertFalse(item["temporary_ai_activation_allowed"])
        self.assertFalse(plan["integration_boundary"]["source_profiles_modified"])
        self.assertEqual(
            before,
            {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before},
        )

    def test_exact_existing_voice_profile_is_preserved_without_audition(self):
        fixture = IntegrationFixture(self.root, locale="en-US")
        write_json(
            self.root / "Voice/profiles/temp_ai/expert_one_voice_profile.json",
            {
                "candidate_id": fixture.candidate_id,
                "voice_id": "expert_one_existing_voice_v1",
                "status": {"readiness_label": "reviewed_existing_voice"},
            },
        )
        plan = fixture.integration().build_plan()
        item = plan["candidates"][0]
        self.assertEqual(item["action"], "preserve_existing_voice_profile")
        self.assertEqual(item["existing_voice"]["voice_id"], "expert_one_existing_voice_v1")
        self.assertIsNone(item["audition_brief"])
        self.assertEqual(plan["summary"]["nonbinding_audition_brief_count"], 0)

    def test_static_creator_no_voice_authority_fails_closed(self):
        fixture = IntegrationFixture(self.root)
        creation = json.loads(fixture.creation_path.read_text(encoding="utf-8"))
        creation["voice_plan"]["status"] = "STATIC_QUALITY_V2_NO_VOICE_WORK_AUTHORIZED"
        write_json(fixture.creation_path, creation)
        with self.assertRaisesRegex(ValidationError, "forbids voice audition work"):
            fixture.integration().build_plan()

    def test_stale_kira_route_profile_digest_fails_closed(self):
        registry_path = self.root / "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json"
        write_json(
            registry_path,
            {
                "schema_version": 1,
                "candidates": [
                    {
                        "canonical_candidate_id": "kira",
                        "subject_id": "kira",
                        "identity_class": "original_person",
                        "inventory_scope": "current_temporary_ai_profile",
                        "aliases": [],
                    }
                ],
            },
        )
        preflight = self.root / "Core/avatar_profile_preflight.py"
        preflight.parent.mkdir(parents=True, exist_ok=True)
        preflight.write_text("def evaluate_avatar_profile_preflight(*args, **kwargs):\n    return {}\n", encoding="utf-8")
        profile_path = self.root / "Voice/profiles/temp_ai/kira_voice_profile.json"
        write_json(
            profile_path,
            {
                "voice_id": "kira_current_voice_v1",
                "status": {"readiness_label": "current"},
            },
        )
        write_json(
            self.root / "Voice/sidecars/kira_approved_voice_routing.json",
            {
                "approved_profile": "Voice/profiles/temp_ai/kira_voice_profile.json",
                "approved_profile_sha256": "0" * 64,
                "policy": {
                    "preferred_route": "gpu",
                    "automatic_fallback_routes": ["sealed_cpu"],
                    "generic_voice_fallback_allowed": False,
                    "sapi_fallback_allowed": False,
                    "unsealed_in_process_fallback_allowed": False,
                },
            },
        )
        adapter = TemporaryCreatorVoiceAdapter(
            self.root,
            preflight_evaluator=lambda *args, **kwargs: {},
        )
        with self.assertRaisesRegex(ValidationError, "digest is stale"):
            AvatarTemporaryCreatorVoiceIntegration(self.root, adapter=adapter).build_plan()

    def test_live_plan_preserves_routes_and_reports_exact_gaps(self):
        project_root = Path(__file__).resolve().parents[3]
        plan = AvatarTemporaryCreatorVoiceIntegration(project_root).build_plan()
        saved = json.loads(
            (Path(__file__).resolve().parents[1] / "evidence/avatar_temporary_creator_voice_integration.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(plan, saved)
        self.assertEqual(
            plan["summary"],
            {
                "registered_candidate_count": 22,
                "source_profile_present_count": 9,
                "preserved_voice_or_route_count": 5,
                "nonbinding_audition_brief_count": 6,
                "needs_review_count": 11,
                "binding_ready_count": 0,
                "activation_allowed_count": 0,
            },
        )
        by_id = {item["canonical_candidate_id"]: item for item in plan["candidates"]}
        self.assertEqual(by_id["kira"]["action"], "preserve_current_kira_route")
        self.assertTrue(by_id["kira"]["review_gates"]["subject_comparative_selection_required"])
        self.assertEqual(
            by_id["peter_parker_spider_man_no_way_home_final_suit"]["action"],
            "preserve_existing_voice_profile",
        )
        self.assertEqual(
            by_id["ladybug_marinette_expanded_smoke"]["action"],
            "preserve_existing_voice_profile",
        )
        holmes = by_id["h_h_holmes_h_h_holmes_20260605_221432"]
        self.assertEqual(holmes["required_disclosure"], HISTORICAL_DISCLOSURE)
        self.assertEqual(holmes["existing_voice"]["voice_status"], "estimated_reconstruction_only")
        audition_items = [item for item in plan["candidates"] if item["audition_brief"] is not None]
        self.assertEqual(len(audition_items), 6)
        self.assertTrue(all(
            VoiceDesignBrief.from_dict(item["audition_brief"]).language_provenance.value
            == "application_audition_default"
            for item in audition_items
        ))
        self.assertTrue(all(not item["temporary_ai_activation_allowed"] for item in plan["candidates"]))


if __name__ == "__main__":
    unittest.main()
