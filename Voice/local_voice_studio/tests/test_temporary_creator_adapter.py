from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from .support import generic_voice
from kira_local_voice.errors import ValidationError
from kira_local_voice.registry import VoiceRegistry
from kira_local_voice.temporary_creator_adapter import (
    GENERATED_EXPERT_CANDIDATES,
    TemporaryCreatorVoiceAdapter,
)
from kira_local_voice.voice_design import (
    AuditionApproval,
    LanguageProvenance,
    VoiceDesignEngine,
    VoiceDesignStore,
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


class AdapterFixture:
    def __init__(self, root: Path, *, locale: str | None = None, gender: str = "Female", storage: str = "expert-one"):
        self.root = root
        self.canonical = "expert-one"
        self.storage = storage
        self.subject = "expert-one-subject"
        self.registry_path = root / "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json"
        self.profile_path = root / "TemporaryAI/candidates" / storage / "temporary_ai_profile.json"
        self.request_path = self.profile_path.parent / "voice_discovery_request.json"
        self.preflight_path = root / "Core/avatar_profile_preflight.py"
        record = {
            "canonical_candidate_id": self.canonical,
            "profile_directory": storage,
            "aliases": [storage, "expert-alias"],
            "subject_id": self.subject,
            "identity_class": "generated_expert",
            "variant_kind": "generated_person",
            "version_policy": {"required": False},
            "maturity_policy": {"lane": "adult"},
            "adult_variant_policy": {"separate_variant_required": False},
        }
        write_json(self.registry_path, {"schema_version": 1, "candidates": [record]})
        profile = {
            "candidate_id": self.canonical,
            "display_name": "Expert One",
            "role_title": "Robotics expert",
            "gender_preference": gender,
            "knowledge_plan": {"gender_preference": gender},
            "avatar_identity_selection": {"maturity_lane": "adult", "body_authored": False},
            "personality_notes": "This prose is deliberately not parsed as curated tags.",
        }
        if locale is not None:
            profile["locale"] = locale
        write_json(self.profile_path, profile)
        write_json(self.request_path, {"candidate_id": self.canonical, "status": "not_run"})
        self.preflight_path.parent.mkdir(parents=True, exist_ok=True)
        self.preflight_path.write_text("def evaluate_avatar_profile_preflight(*args, **kwargs):\n    return {}\n", encoding="utf-8")

    def evaluator(self, project_root: Path, requested_candidate_id: str) -> dict:
        registry_sha = hashlib.sha256(self.registry_path.read_bytes()).hexdigest()
        profile_sha = hashlib.sha256(self.profile_path.read_bytes()).hexdigest()
        return {
            "registry_binding_verified": True,
            "canonical_candidate_id": self.canonical,
            "registry": {"sha256": registry_sha},
            "canonical_profile": {"path": self.profile_path.relative_to(self.root).as_posix(), "sha256": profile_sha},
            "identity": {
                "subject_id": self.subject,
                "identity_class": "generated_expert",
                "selected_version": "",
            },
            "maturity": {"lane": "adult"},
            "failures": [],
            "authoring_allowed": True,
        }


def approval(candidate: dict) -> AuditionApproval:
    return AuditionApproval(
        candidate_id=candidate["candidate_id"],
        listener="Human listener",
        auditioned_at="2026-08-25T12:00:00Z",
        sample_sha256="a" * 64,
        heard_full_sample=True,
        clarity=5,
        naturalness=4,
        character_fit=4,
        provenance_reviewed=True,
        distinctness_checked=True,
        distinctness_report_sha256="b" * 64,
        shared_spec_sha256=candidate["shared_spec_sha256"],
    )


class TemporaryCreatorAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_locale_and_gender_create_source_attested_generic_brief(self):
        fixture = AdapterFixture(self.root, locale="en-US")
        adapter = TemporaryCreatorVoiceAdapter(self.root, preflight_evaluator=fixture.evaluator)
        result = adapter.adapt("expert-one")
        self.assertEqual(result["status"], "ready_for_design")
        self.assertEqual(result["binding_status"], "source_fields_complete")
        brief = result["brief"]
        self.assertEqual(brief["gender"], "female")
        self.assertEqual(brief["language"], "en-US")
        self.assertEqual(brief["language_provenance"], "explicit_source")
        self.assertEqual(brief["age_band"], "adult")
        self.assertEqual(brief["body_presence"], "not_authored")
        self.assertEqual(brief["personality_traits"], [])
        self.assertIn("body_not_authored_zero_affinity", result["fit_limitations"])
        self.assertIn("personality_tags_not_authored_zero_affinity", result["fit_limitations"])
        self.assertEqual(brief["source_attestation"]["profile_sha256"], result["source_hashes"]["profile_sha256"])
        self.assertEqual(len(result["source_hashes"]["preflight_sha256"]), 64)

    def test_missing_locale_needs_review_and_is_never_inferred_from_prose(self):
        fixture = AdapterFixture(self.root)
        adapter = TemporaryCreatorVoiceAdapter(self.root, preflight_evaluator=fixture.evaluator)
        result = adapter.adapt("expert-one")
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["missing_required_fields"], ["locale"])
        self.assertIsNone(result["brief"])

    def test_application_default_makes_nonbinding_audition_but_cannot_be_approved(self):
        fixture = AdapterFixture(self.root)
        adapter = TemporaryCreatorVoiceAdapter(self.root, preflight_evaluator=fixture.evaluator)
        result = adapter.adapt("expert-one", audition_locale="en-US")
        self.assertEqual(result["status"], "ready_for_nonbinding_audition")
        self.assertEqual(result["binding_status"], "needs_review")
        self.assertEqual(result["missing_required_fields"], ["locale"])
        self.assertEqual(result["brief"]["language_provenance"], "application_audition_default")

        registry = VoiceRegistry(self.root / "voice-data/voices")
        engine = VoiceDesignEngine(VoiceDesignStore(self.root / "voice-data/design"), registry)
        bundle = engine.create_bundle(result["brief"])
        self.assertIn("locale_confirmation_required_before_binding", bundle["profile_fit_limitations"])
        with self.assertRaisesRegex(ValidationError, "confirmed"):
            engine.approve_bundle(bundle["bundle_id"], approval(bundle["candidates"][0]), authority="Owner")
        self.assertIsNone(engine.current_binding(self.subject if hasattr(self, "subject") else fixture.subject))

    def test_exact_registry_alias_preserves_storage_typo_without_path_guessing(self):
        fixture = AdapterFixture(self.root, locale="en-US", storage="expert-enterainment-agent")
        adapter = TemporaryCreatorVoiceAdapter(self.root, preflight_evaluator=fixture.evaluator)
        result = adapter.adapt("expert-enterainment-agent")
        self.assertEqual(result["status"], "ready_for_design")
        self.assertEqual(result["canonical_candidate_id"], "expert-one")
        self.assertEqual(result["storage_id"], "expert-enterainment-agent")
        self.assertEqual(result["brief"]["source_attestation"]["registry_alias"], "expert-enterainment-agent")
        with self.assertRaisesRegex(ValidationError, "exact registry"):
            adapter.adapt("expert-entertainment-agent")

    def test_contradictory_gender_is_refused(self):
        fixture = AdapterFixture(self.root, locale="en-US")
        profile = json.loads(fixture.profile_path.read_text(encoding="utf-8"))
        profile["knowledge_plan"]["gender_preference"] = "Male"
        write_json(fixture.profile_path, profile)
        adapter = TemporaryCreatorVoiceAdapter(self.root, preflight_evaluator=fixture.evaluator)
        result = adapter.adapt("expert-one")
        self.assertEqual(result["status"], "needs_review")
        self.assertIn("contradictory_explicit_gender_fields", result["conflicts"])

    def test_duplicate_json_keys_and_preflight_mutation_fail_closed(self):
        fixture = AdapterFixture(self.root, locale="en-US")
        fixture.profile_path.write_text('{"candidate_id":"expert-one","candidate_id":"other"}', encoding="utf-8")
        adapter = TemporaryCreatorVoiceAdapter(self.root, preflight_evaluator=fixture.evaluator)
        with self.assertRaisesRegex(ValidationError, "duplicate JSON key"):
            adapter.adapt("expert-one")

        # Rebuild a clean fixture because sources are intentionally append-free.
        other = self.root / "other"
        clean = AdapterFixture(other, locale="en-US")
        clean_adapter = TemporaryCreatorVoiceAdapter(other, preflight_evaluator=clean.evaluator)
        clean.preflight_path.write_text("# changed trust boundary\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "preflight changed"):
            clean_adapter.adapt("expert-one")

    def test_live_registry_coverage_preserves_existing_and_prepares_nonbinding_experts(self):
        project_root = Path(__file__).resolve().parents[3]
        adapter = TemporaryCreatorVoiceAdapter(project_root)
        report = adapter.live_coverage()
        saved_report = json.loads(
            (Path(__file__).resolve().parents[1] / "evidence/live_temporary_creator_voice_coverage.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report, saved_report)
        expectations = json.loads(
            (Path(__file__).parent / "fixtures/live_voice_coverage_expectations.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            {item["candidate_id"]: item["status"] for item in report["generated_experts"]},
            expectations["generated_experts"],
        )
        self.assertTrue(all(
            item["binding_status"] == expectations["generated_expert_binding_status"]
            and item["missing_required_fields"] == expectations["generated_expert_missing_required_fields"]
            for item in report["generated_experts"]
        ))
        preserved = {item["candidate_id"]: item for item in report["preserved_existing_voices"]}
        self.assertEqual(
            {candidate_id: item["status"] for candidate_id, item in preserved.items()},
            expectations["preserved_existing"],
        )
        self.assertEqual(report["summary"]["ready_for_nonbinding_audition_count"], 5)


if __name__ == "__main__":
    unittest.main()
