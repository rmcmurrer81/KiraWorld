from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from .support import generic_voice, source_voice
from kira_local_voice.errors import ConflictError, ValidationError
from kira_local_voice.models import AuditionStatus
from kira_local_voice.registry import VoiceRegistry
from kira_local_voice.voice_design import (
    BRIEF_SCHEMA,
    AgeBand,
    AssignmentMode,
    AuditionApproval,
    AvatarSourceAttestation,
    BodyPresence,
    EraContext,
    Gender,
    IdentityKind,
    SubjectVoiceSelection,
    VoiceDesignBrief,
    VoiceDesignEngine,
    VoiceDesignStore,
    safe_builtin_catalog,
)


def brief(
    subject_id: str = "sarah-bennett",
    display_name: str = "Sarah Bennett",
    *,
    gender: Gender = Gender.FEMALE,
    age_band: AgeBand = AgeBand.ADULT,
    body_presence: BodyPresence = BodyPresence.BALANCED,
    role: str = "Entertainment expert",
    traits: tuple[str, ...] = ("warm", "clear", "practical"),
    language: str = "en-US",
    era: EraContext = EraContext.CONTEMPORARY,
    identity_kind: IdentityKind = IdentityKind.ORIGINAL,
    mode: AssignmentMode = AssignmentMode.ASSIGN_IF_MISSING,
    existing_voice_id: str | None = None,
    candidate_count: int = 3,
    source_attestation: AvatarSourceAttestation | None = None,
) -> VoiceDesignBrief:
    return VoiceDesignBrief(
        subject_id=subject_id,
        display_name=display_name,
        gender=gender,
        age_band=age_band,
        body_presence=body_presence,
        role=role,
        personality_traits=traits,
        language=language,
        era=era,
        identity_kind=identity_kind,
        assignment_mode=mode,
        source_attestation=source_attestation or AvatarSourceAttestation(
            candidate_id=subject_id,
            storage_id=f"{subject_id}-storage",
            profile_sha256=hashlib.sha256(f"profile:{subject_id}".encode()).hexdigest(),
            request_sha256=hashlib.sha256(f"request:{subject_id}".encode()).hexdigest(),
            registry_sha256="3" * 64,
        ),
        existing_voice_id=existing_voice_id,
        candidate_count=candidate_count,
    )


def approval_for(candidate: dict, *, at: str = "2026-08-25T01:00:00-04:00") -> AuditionApproval:
    return AuditionApproval(
        candidate_id=candidate["candidate_id"],
        listener="Product owner",
        auditioned_at=at,
        sample_sha256="a" * 64,
        heard_full_sample=True,
        clarity=5,
        naturalness=4,
        character_fit=5,
        provenance_reviewed=True,
        distinctness_checked=True,
        distinctness_report_sha256="b" * 64,
        shared_spec_sha256=candidate["shared_spec_sha256"],
        notes="Auditioned through the complete comparison script.",
    )


class VoiceDesignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = VoiceRegistry(self.root / "voices")
        self.store = VoiceDesignStore(self.root / "design")
        self.engine = VoiceDesignEngine(self.store, self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def register(self, voice_id: str):
        return self.registry.register(replace(generic_voice(voice_id), display_name=f"Existing {voice_id}"))

    def test_strict_input_schema_round_trip_and_unknown_field_rejection(self):
        payload = brief().to_dict()
        self.assertEqual(payload["schema"], BRIEF_SCHEMA)
        self.assertEqual(VoiceDesignBrief.from_dict(payload).to_dict(), payload)
        payload["silent_override"] = True
        with self.assertRaises(ValidationError):
            VoiceDesignBrief.from_dict(payload)

    def test_source_attestation_preserves_exact_registry_alias_and_rejects_contradiction(self):
        source = AvatarSourceAttestation(
            candidate_id="sarah-bennett", storage_id="sarah-bennett-storage",
            profile_sha256="4" * 64, request_sha256="5" * 64, registry_sha256="6" * 64,
            registry_alias="TemporaryAI/generated_experts/enterainment_pr_expert",
        )
        first = self.engine.create_bundle(brief(source_attestation=source))
        self.assertEqual(
            first["brief"]["source_attestation"]["registry_alias"],
            "TemporaryAI/generated_experts/enterainment_pr_expert",
        )
        with self.assertRaisesRegex(ValidationError, "contradictory"):
            self.engine.create_bundle(brief(gender=Gender.MALE, source_attestation=source))

    def test_brief_requires_explicit_supported_gender_and_bounded_traits(self):
        payload = brief().to_dict()
        payload["gender"] = "unspecified"
        with self.assertRaises(ValidationError):
            VoiceDesignBrief.from_dict(payload)
        payload = brief().to_dict()
        payload["personality_traits"] = ["warm"] * 13
        with self.assertRaises(ValidationError):
            VoiceDesignBrief.from_dict(payload)

    def test_candidates_are_deterministic_and_use_profile_dimensions(self):
        first = self.engine.create_bundle(brief())
        with tempfile.TemporaryDirectory() as other_raw:
            other_root = Path(other_raw)
            second = VoiceDesignEngine(
                VoiceDesignStore(other_root / "design"), VoiceRegistry(other_root / "voices")
            ).create_bundle(brief())
        self.assertEqual(first["bundle_id"], second["bundle_id"])
        self.assertEqual(
            [item["candidate_id"] for item in first["candidates"]],
            [item["candidate_id"] for item in second["candidates"]],
        )
        self.assertEqual([item["catalog_id"] for item in first["candidates"]],
                         [item["catalog_id"] for item in second["candidates"]])
        self.assertEqual(first["candidates"][0]["catalog_id"], "bella-clear")
        self.assertIn("age:adult", first["candidates"][0]["fit_reasons"])
        self.assertIn("body:balanced", first["candidates"][0]["fit_reasons"])
        self.assertIn("era:contemporary", first["candidates"][0]["fit_reasons"])

    def test_gender_never_crosses_the_safe_base_route(self):
        female = self.engine.create_bundle(brief())
        male = self.engine.create_bundle(brief(
            subject_id="ryan-hale", display_name="Ryan Hale", gender=Gender.MALE,
        ))
        self.assertTrue(all(
            item["gender"] == "female"
            and item["backend_voice_id"] in {"af_heart", "af_bella", "af_nicole", "af_aoede", "af_kore", "af_sarah"}
            for item in female["candidates"]
        ))
        self.assertTrue(all(
            item["gender"] == "male" and item["backend_voice_id"] in {"am_fenrir", "am_michael", "am_puck"}
            for item in male["candidates"]
        ))
        self.assertTrue(all(item["technical_status"] == "technical_pass_human_review_required"
                            for item in female["candidates"] + male["candidates"]))
        self.assertTrue(all(len(item["source_attestation"]["source_attestation_sha256"]) == 64
                            for item in female["candidates"] + male["candidates"]))

    def test_technical_catalog_is_exact_and_still_requires_human_review(self):
        catalog = safe_builtin_catalog()
        self.assertEqual(
            {item.backend_voice_id for item in catalog},
            {"af_heart", "af_bella", "af_nicole", "af_aoede", "af_kore", "af_sarah",
             "am_fenrir", "am_michael", "am_puck"},
        )
        for item in catalog:
            attestation = item.source_attestation()
            self.assertEqual(attestation["model_revision"], "f3ff3571791e39611d31c381e3a41a3af07b4987")
            self.assertEqual(attestation["technical_status"], "technical_pass_human_review_required")
            self.assertEqual(len(attestation["source_attestation_sha256"]), 64)

    def test_bounded_expert_batch_creates_audition_bundles_without_binding(self):
        briefs = [
            brief("sarah-bennett", "Sarah Bennett", role="Entertainment expert"),
            brief("laura-mitchell", "Laura Mitchell", role="Attorney"),
            brief("jessica-hale", "Jessica Hale", role="Robotics engineer"),
            brief("emily-carter", "Emily Carter", role="Programming expert"),
            brief("ryan-hale", "Ryan Hale", gender=Gender.MALE, role="Quantum mechanics expert"),
        ]
        bundles = self.engine.create_batch(briefs)
        self.assertEqual(len(bundles), 5)
        self.assertTrue(all(item["status"] == "awaiting_audio_and_human_audition" for item in bundles))
        self.assertTrue(all(len(item["candidates"]) == 3 for item in bundles))
        self.assertTrue(all(self.engine.current_binding(item.subject_id) is None for item in briefs))

    def test_batch_preflight_rejects_duplicate_subject_before_writing(self):
        with self.assertRaisesRegex(ValidationError, "repeat a subject_id"):
            self.engine.create_batch([brief(), brief()])
        self.assertEqual(self.store.list_bundles(), [])

    def test_unsupported_language_is_truthfully_rejected(self):
        with self.assertRaisesRegex(ValidationError, "too few candidates"):
            self.engine.create_bundle(brief(language="fr-FR"))

    def test_keep_existing_preserves_peter_and_marinette_without_candidates(self):
        self.register("peter-current")
        peter = self.engine.create_bundle(brief(
            subject_id="peter_parker", display_name="Peter Parker", gender=Gender.MALE,
            identity_kind=IdentityKind.FICTIONAL, mode=AssignmentMode.KEEP_EXISTING,
            existing_voice_id="peter-current",
        ))
        self.assertEqual(peter["status"], "existing_voice_preserved")
        self.assertEqual(peter["candidates"], [])
        with self.assertRaisesRegex(ValidationError, "locked"):
            self.engine.create_bundle(replace(
                brief(subject_id="marinette", display_name="Ladybug", identity_kind=IdentityKind.FICTIONAL),
                assignment_mode=AssignmentMode.ASSIGN_IF_MISSING,
            ))

    def test_source_recording_existing_voice_can_be_preserved_when_provenance_is_complete(self):
        self.registry.register(replace(source_voice("c" * 64), voice_id="licensed-peter"))
        bundle = self.engine.create_bundle(brief(
            subject_id="peter_parker", display_name="Peter Parker", gender=Gender.MALE,
            identity_kind=IdentityKind.FICTIONAL, mode=AssignmentMode.KEEP_EXISTING,
            existing_voice_id="licensed-peter",
        ))
        self.assertTrue(bundle["existing_voice"]["provenance_permits_reuse"])

    def test_deactivated_or_expired_existing_voice_cannot_be_reused(self):
        self.register("stopped")
        self.registry.deactivate("stopped", authority="owner", reason="retired")
        with self.assertRaisesRegex(ValidationError, "deactivated"):
            self.engine.create_bundle(brief(
                mode=AssignmentMode.REPLACE_EXISTING, existing_voice_id="stopped",
            ))
        expired = replace(
            generic_voice("expired"),
            consent=replace(
                generic_voice().consent,
                recorded_at="1999-01-01T00:00:00Z", expires_at="2000-01-01T00:00:00Z",
            ),
        )
        self.registry.register(expired)
        with self.assertRaisesRegex(ValidationError, "expired"):
            self.engine.create_bundle(brief(
                mode=AssignmentMode.REPLACE_EXISTING, existing_voice_id="expired",
            ))

    def test_historical_holmes_is_never_presented_as_authentic(self):
        self.register("holmes-estimate")
        bundle = self.engine.create_bundle(brief(
            subject_id="h_h_holmes", display_name="H. H. Holmes", gender=Gender.MALE,
            age_band=AgeBand.ADULT, body_presence=BodyPresence.GROUNDED,
            role="Historical figure", traits=("formal", "measured", "clear"),
            era=EraContext.HISTORICAL, identity_kind=IdentityKind.HISTORICAL,
            mode=AssignmentMode.REPLACE_EXISTING, existing_voice_id="holmes-estimate",
        ))
        self.assertIn("Speculative historical reconstruction", bundle["disclosure"])
        self.assertTrue(all("not an authentic recording" in item["disclosure"] for item in bundle["candidates"]))

    def test_holmes_rejects_nonhistorical_identity_context(self):
        with self.assertRaisesRegex(ValidationError, "historical reconstruction"):
            self.engine.create_bundle(brief(
                subject_id="h_h_holmes", display_name="H. H. Holmes", gender=Gender.MALE,
                identity_kind=IdentityKind.FICTIONAL,
            ))

    def test_audition_requires_provenance_distinctness_and_exact_shared_spec(self):
        bundle = self.engine.create_bundle(brief())
        candidate = bundle["candidates"][0]
        good = approval_for(candidate)
        with self.assertRaisesRegex(ValidationError, "provenance review"):
            self.engine.approve_bundle(bundle["bundle_id"], replace(good, provenance_reviewed=False), authority="owner")
        with self.assertRaisesRegex(ValidationError, "distinctness check"):
            self.engine.approve_bundle(bundle["bundle_id"], replace(good, distinctness_checked=False), authority="owner")
        with self.assertRaisesRegex(ValidationError, "shared candidate"):
            self.engine.approve_bundle(
                bundle["bundle_id"], replace(good, shared_spec_sha256="f" * 64), authority="owner"
            )

    def test_generated_expert_binds_only_after_all_audition_gates(self):
        bundle = self.engine.create_bundle(brief())
        candidate = bundle["candidates"][0]
        event = self.engine.approve_bundle(bundle["bundle_id"], approval_for(candidate), authority="owner")
        self.assertEqual(event["action"], "activate_auditioned_candidate")
        self.assertEqual(event["active_target"]["candidate_id"], candidate["candidate_id"])
        self.assertEqual(event["active_target"]["shared_spec_sha256"], candidate["shared_spec_sha256"])
        self.assertEqual(event["active_target"]["runtime_resolution_status"], "requires_exact_runtime_resolver")
        self.assertIsNone(event["rollback_target"])
        self.assertEqual(self.engine.current_binding("sarah-bennett")["event_id"], event["event_id"])

    def test_replacement_binding_preserves_append_only_rollback_target(self):
        self.register("original-route")
        bundle = self.engine.create_bundle(brief(
            mode=AssignmentMode.REPLACE_EXISTING, existing_voice_id="original-route",
        ))
        event = self.engine.approve_bundle(
            bundle["bundle_id"], approval_for(bundle["candidates"][0]), authority="owner"
        )
        self.assertEqual(event["rollback_target"]["voice_id"], "original-route")
        rollback = self.engine.rollback(
            "sarah-bennett", authority="owner", reason="Prefer the previous approved route",
            effective_at="2026-08-25T01:30:00-04:00",
        )
        self.assertEqual(rollback["active_target"]["voice_id"], "original-route")
        self.assertEqual(rollback["parent_event_id"], event["event_id"])

    def test_kira_owner_audition_only_makes_candidate_eligible(self):
        self.register("kira-current")
        bundle = self.engine.create_bundle(brief(
            subject_id="kira", display_name="Kira", role="World guide",
            traits=("warm", "observant", "practical"), identity_kind=IdentityKind.ORIGINAL,
            mode=AssignmentMode.REPLACE_EXISTING, existing_voice_id="kira-current",
        ))
        candidate = bundle["candidates"][0]
        decision = self.engine.approve_bundle(bundle["bundle_id"], approval_for(candidate), authority="owner")
        self.assertEqual(decision["decision"], "eligible_pending_subject_selection")
        self.assertIsNone(self.engine.current_binding("kira"))

    def test_kira_selects_eligible_candidate_and_keeps_current_route_for_rollback(self):
        self.register("kira-current")
        bundle = self.engine.create_bundle(brief(
            subject_id="kira", display_name="Kira", role="World guide",
            traits=("warm", "observant", "practical"),
            mode=AssignmentMode.REPLACE_EXISTING, existing_voice_id="kira-current",
        ))
        candidate = bundle["candidates"][0]
        self.engine.approve_bundle(bundle["bundle_id"], approval_for(candidate), authority="owner")
        event = self.engine.select_eligible_candidate(
            bundle["bundle_id"],
            SubjectVoiceSelection(
                candidate_id=candidate["candidate_id"], selector_subject_id="kira",
                selected_at="2026-08-25T01:20:00-04:00", comparison_complete=True,
                selection_receipt_sha256="d" * 64,
            ),
            authority="Kira voice selection gate",
        )
        self.assertEqual(event["action"], "activate_subject_selected_candidate")
        self.assertEqual(event["rollback_target"]["voice_id"], "kira-current")

    def test_lisa_can_select_a_new_voice_but_owner_cannot_select_for_her(self):
        bundle = self.engine.create_bundle(brief(
            subject_id="lisa", display_name="Lisa", role="World resident",
            traits=("expressive", "direct", "warm"),
        ))
        candidate = bundle["candidates"][0]
        self.engine.approve_bundle(bundle["bundle_id"], approval_for(candidate), authority="owner")
        with self.assertRaisesRegex(ValidationError, "must match"):
            self.engine.select_eligible_candidate(
                bundle["bundle_id"],
                SubjectVoiceSelection(
                    candidate_id=candidate["candidate_id"], selector_subject_id="owner",
                    selected_at="2026-08-25T01:20:00-04:00", comparison_complete=True,
                    selection_receipt_sha256="d" * 64,
                ), authority="owner",
            )
        event = self.engine.select_eligible_candidate(
            bundle["bundle_id"],
            SubjectVoiceSelection(
                candidate_id=candidate["candidate_id"], selector_subject_id="lisa",
                selected_at="2026-08-25T01:21:00-04:00", comparison_complete=True,
                selection_receipt_sha256="e" * 64,
            ), authority="Lisa voice selection gate",
        )
        self.assertIsNone(event["rollback_target"])

    def test_duplicate_approval_is_refused_instead_of_creating_a_binding_fork(self):
        bundle = self.engine.create_bundle(brief())
        candidate = bundle["candidates"][0]
        self.engine.approve_bundle(bundle["bundle_id"], approval_for(candidate), authority="owner")
        with self.assertRaises(ConflictError):
            self.engine.approve_bundle(bundle["bundle_id"], approval_for(candidate), authority="owner")

    def test_immutable_bundle_detects_tampering(self):
        bundle = self.engine.create_bundle(brief())
        path = self.store.bundle_root / f"{bundle['bundle_id']}.json"
        envelope = json.loads(path.read_text(encoding="utf-8"))
        envelope["payload"]["status"] = "silently-approved"
        path.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "tamper"):
            self.store.get_bundle(bundle["bundle_id"])

    def test_rehashed_bundle_cannot_route_outside_deterministic_catalog_plan(self):
        bundle = self.engine.create_bundle(brief())
        candidate = bundle["candidates"][0]
        path = self.store.bundle_root / f"{bundle['bundle_id']}.json"
        envelope = json.loads(path.read_text(encoding="utf-8"))
        envelope["payload"]["candidates"][0]["backend_voice_id"] = "am_puck"
        canonical = json.dumps(
            envelope["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        envelope["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
        path.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "deterministic safe catalog"):
            self.engine.approve_bundle(bundle["bundle_id"], approval_for(candidate), authority="owner")

    def test_binding_history_refuses_a_second_root(self):
        bundle = self.engine.create_bundle(brief())
        event = self.engine.approve_bundle(
            bundle["bundle_id"], approval_for(bundle["candidates"][0]), authority="owner"
        )
        fork = dict(event)
        fork["event_id"] = "sarah-bennett--be-ffffffffffffffffffffffff"
        self.store.put_binding(fork)
        with self.assertRaisesRegex(ValidationError, "forked or ambiguous"):
            self.engine.current_binding("sarah-bennett")


if __name__ == "__main__":
    unittest.main()
