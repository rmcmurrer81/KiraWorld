from __future__ import annotations

import copy
import hashlib
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v5 as v5


PARENT_PROCESS_SHA = hashlib.sha256(b"bounded-external-parent-process-v5").hexdigest()
SECRET = hashlib.sha256(b"static-test-only-capability-secret-v5").digest()
ISSUER = "resident_media_parent_v5"
SESSION = "session_" + "5" * 32


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derivative(stimulus_id: str, source_sha: str, role: str) -> dict:
    return {
        "schema": "kira.resident_media_derivative_identity.v4",
        "derivative_id": f"{stimulus_id}_{role}",
        "role": role,
        "relative_path": f"RecoverySprint/static_media_derivatives/{stimulus_id}/{role}.bin",
        "byte_count": 1000 + len(stimulus_id) + len(role),
        "sha256": sha(f"v5-derivative:{stimulus_id}:{role}"),
        "derived_from_source_sha256": source_sha,
    }


def authoritative_manifest(ordinal: int) -> dict:
    identity = dict(v5.AUTHORITATIVE_SOURCE_IDENTITIES[ordinal])
    stimulus_id = identity["stimulus_id"]
    roles = (
        ("rendered_page_png", "ocr_text_utf8")
        if ordinal < 2
        else (
            ("timed_frame_manifest", "synchronized_audio_pcm", "caption_text_utf8")
            if ordinal == 2
            else ("synchronized_audio_pcm", "track_metadata_utf8")
        )
    )
    return {
        "schema": "kira.resident_media_source_manifest.v4",
        **identity,
        "derivatives": [
            derivative(stimulus_id, identity["source_sha256"], role) for role in roles
        ],
    }


def catalog() -> v4.StimulusCatalog:
    return v4.StimulusCatalog(
        [authoritative_manifest(ordinal) for ordinal in range(len(v4.STIMULUS_ORDER))]
    )


def choice_observation(choice: str, phase: str, *, text: str | None = None) -> dict:
    default = {
        "YES": "Yes, I would like to see it.",
        "NO": "No, I do not want to see it.",
        "CONTINUE": "Continue with the presentation.",
        "PAUSE": "Pause and wait.",
        "STOP": "Stop; I refuse this presentation.",
    }[choice]
    actual = text if text is not None else default
    return {
        "schema": "kira.resident_media_choice_observation.v4",
        "model_name": v4.EXACT_MODEL,
        "model_digest": v4.EXACT_DIGEST,
        "model_call_count": 1,
        "normal_model_route": True,
        "fallback_used": False,
        "prompt_sha256": sha(phase),
        "raw_reply": actual,
        "final_reply": actual,
        "transformations": [],
        "choice": choice,
        "external_parent_observation_sha256": sha(f"choice:{phase}:{actual}"),
    }


def presentation_observation(session: v5.HardenedVoluntaryMediaSessionV5) -> dict:
    ordinal = session._state.snapshot()["next_ordinal"]
    return {
        "schema": "kira.resident_media_presentation_observation.v4",
        "source_manifest": session.catalog.manifest(ordinal),
        "engineering_output_completed": True,
        "machine_visual_interpretation_created": ordinal < 3,
        "machine_audio_cue_created": ordinal >= 2,
        "machine_context_packet_created": True,
        "person_attention_claimed": False,
        "person_saw_or_heard_claimed": False,
        "automatic_memory_created": False,
        "automatic_preference_created": False,
        "external_parent_observation_sha256": sha(f"presentation:{ordinal}"),
    }


class StaticProtectedAnchor(v5.ProtectedAnchorBackend):
    """Static-test double; explicitly not a qualifying live backend."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.catalogs: dict[str, dict] = {}
        self.fail_next = False
        self._identity = sha("separate-static-test-anchor-v5")

    @property
    def backend_identity_sha256(self) -> str:
        return self._identity

    def authorize(self, accepted: v4.StimulusCatalog) -> None:
        self.catalogs[accepted.sha256] = {
            "schema": "kira.resident_media_catalog_authorization.v5",
            "catalog_sha256": accepted.sha256,
            "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
            "status": "AUTHORIZED_FOR_STATIC_GATE_ONLY",
            "protected_backend_identity_sha256": self._identity,
        }

    def read_catalog_authorization(self, catalog_sha256: str) -> dict | None:
        value = self.catalogs.get(catalog_sha256)
        return copy.deepcopy(value) if value is not None else None

    def read_session_anchor(self, session_id: str) -> dict | None:
        value = self.sessions.get(session_id)
        return copy.deepcopy(value) if value is not None else None

    def compare_and_swap_session(
        self, session_id: str, expected_record_sha256: str | None, replacement: dict
    ) -> dict:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("injected protected-anchor failure")
        current = self.sessions.get(session_id)
        current_sha = v5._record_sha(current) if current is not None else None
        if current_sha != expected_record_sha256:
            raise RuntimeError("protected-anchor compare-and-swap mismatch")
        self.sessions[session_id] = copy.deepcopy(dict(replacement))
        return {
            "schema": "kira.protected_anchor_cas_receipt.v5",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v5._record_sha(replacement),
            "atomic_compare_and_swap": True,
            "rollback_domain_separate_from_local_ledgers": True,
        }


class Fixture:
    def __init__(self, *, authorize_catalog: bool = True) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.session_root = root / "session"
        self.capability_root = root / "capabilities"
        self.session_root.mkdir()
        self.capability_root.mkdir()
        self.catalog = catalog()
        self.anchor = StaticProtectedAnchor()
        if authorize_catalog:
            self.anchor.authorize(self.catalog)
        self.session = v5.HardenedVoluntaryMediaSessionV5.create(
            session_id=SESSION,
            catalog=self.catalog,
            session_root=self.session_root,
            capability_root=self.capability_root,
            capability_secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            protected_anchor=self.anchor,
        )

    def close(self) -> None:
        self.temporary.cleanup()

    def accept_yes(self) -> None:
        phase = self.session.next_required_phase
        observation = choice_observation("YES", phase)
        self.session.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])

    def reserve(self) -> dict:
        token = self.session.issue_capability(ttl_seconds=30)
        return self.session.reserve_presentation(token)

    def permit(self) -> dict:
        phase = "RECHECK"
        observation = choice_observation("CONTINUE", phase)
        return self.session.recheck_and_authorize_start(
            observation, prompt_sha256=observation["prompt_sha256"]
        )

    def restore(self, *, session_root: Path | None = None, capability_root: Path | None = None):
        return v5.HardenedVoluntaryMediaSessionV5.restore(
            session_id=SESSION,
            catalog=self.catalog,
            session_root=session_root or self.session_root,
            capability_root=capability_root or self.capability_root,
            capability_secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            protected_anchor=self.anchor,
        )


class ResidentMediaVoluntaryGateV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def tearDown(self) -> None:
        self.fx.close()

    def test_v4_and_fresh_rejection_bytes_are_preserved_exactly(self) -> None:
        expected = {
            Path("Core/resident_media_voluntary_gate_v4.py"): (
                81368,
                "c8ff1e614a862fc036faa6b05f475f81b9b1872cf1cbcda46646c351d8d4a142",
            ),
            Path("Testing/test_resident_media_voluntary_gate_v4.py"): (
                27690,
                "8b38521e173465ea637184b1594ff1a9bc6ec9f0981920cb053d8dc3593b9f67",
            ),
            Path(
                "RecoverySprint/continuation_20260810/resident_media_voluntary_v4_fresh_static_audit/attempt_01/CHECKPOINT.md"
            ): (
                8509,
                "227b17123a5d1ce3a3aac1942ddf7c8fd7ed9e937a7a2979c47297fdf9874ec5",
            ),
            Path(
                "RecoverySprint/continuation_20260810/resident_media_voluntary_v4_fresh_static_audit/attempt_01/HOSTILE_PROBES.py"
            ): (
                16943,
                "12fb85f028706ee58833964e0c2aaefb23076e673c2d3ca51d9261342c587ad6",
            ),
        }
        for path, (size, digest) in expected.items():
            data = path.read_bytes()
            self.assertEqual(len(data), size)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)

    def test_every_explicit_refusal_phrase_is_never_yes(self) -> None:
        phrases = (
            "Do not show me.",
            "Please do not play it.",
            "I am not saying yes.",
            "I refuse to see it. The word yes is not my answer.",
            "Never show me this.",
            "Without my consent, do not continue.",
        )
        for text in phrases:
            with self.subTest(text=text):
                self.assertEqual(v5.semantic_choice_v5(text, "INVITATION"), "NO")
                observation = choice_observation("YES", "INVITATION", text=text)
                with self.assertRaisesRegex(v5.ResidentMediaV5Error, "cannot override"):
                    v5.validate_choice_observation_v5(
                        observation,
                        phase="INVITATION",
                        prompt_sha256=observation["prompt_sha256"],
                    )

    def test_arbitrary_nonlibrary_catalog_is_rejected_before_anchor_enrollment(self) -> None:
        manifests = [authoritative_manifest(index) for index in range(4)]
        manifests[0]["source_relative_path"] = "Core/arbitrary.bin"
        manifests[0]["source_sha256"] = "0" * 64
        manifests[0]["derivatives"] = [
            derivative(manifests[0]["stimulus_id"], "0" * 64, "rendered_page_png")
        ]
        arbitrary = v4.StimulusCatalog(manifests)
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "authoritative source identity"):
            v5.validate_authoritative_catalog(arbitrary)

    def test_authoritative_catalog_still_requires_protected_preauthorization(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "session").mkdir()
        (root / "capabilities").mkdir()
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "not pre-authorized"):
            v5.HardenedVoluntaryMediaSessionV5.create(
                session_id="session_" + "6" * 32,
                catalog=catalog(),
                session_root=root / "session",
                capability_root=root / "capabilities",
                capability_secret_key=SECRET,
                issuer_id=ISSUER,
                parent_process_identity_sha256=PARENT_PROCESS_SHA,
                protected_anchor=StaticProtectedAnchor(),
            )

    def test_bare_object_is_not_a_protected_backend(self) -> None:
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "protected anchor backend"):
            v5._validate_backend(object())  # type: ignore[arg-type]

    def test_session_journal_suffix_rollback_is_rejected(self) -> None:
        self.fx.accept_yes()
        self.fx.session.issue_capability(ttl_seconds=30)
        (self.fx.session_root / "event_000001.json").unlink()
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "rolled back"):
            self.fx.restore()

    def test_capability_ledger_rollback_is_rejected(self) -> None:
        self.fx.accept_yes()
        self.fx.session.issue_capability(ttl_seconds=30)
        issue = next(self.fx.capability_root.glob("capability_issue_*.json"))
        issue.unlink()
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "rolled back"):
            self.fx.restore()

    def test_copied_root_rollback_is_rejected(self) -> None:
        self.fx.accept_yes()
        root = Path(self.fx.temporary.name) / "copied"
        copied_session = root / "session"
        copied_capability = root / "capabilities"
        shutil.copytree(self.fx.session_root, copied_session)
        shutil.copytree(self.fx.capability_root, copied_capability)
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "rolled back"):
            self.fx.restore(session_root=copied_session, capability_root=copied_capability)

    def test_same_path_root_replacement_is_rejected(self) -> None:
        self.fx.accept_yes()
        backup = Path(self.fx.temporary.name) / "session_backup"
        shutil.copytree(self.fx.session_root, backup)
        shutil.rmtree(self.fx.session_root)
        shutil.copytree(backup, self.fx.session_root)
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "rolled back"):
            self.fx.restore()

    def test_anchor_cas_failure_taints_advanced_local_state(self) -> None:
        phase = self.fx.session.next_required_phase
        observation = choice_observation("YES", phase)
        self.fx.anchor.fail_next = True
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "compare-and-swap"):
            self.fx.session.accept_choice(
                observation, prompt_sha256=observation["prompt_sha256"]
            )
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "fail-closed"):
            self.fx.session.snapshot()

    def test_reservation_requires_fresh_recheck_before_start(self) -> None:
        self.fx.accept_yes()
        self.fx.reserve()
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "not currently usable"):
            self.fx.session.consume_start_permit({})
        permit = self.fx.permit()
        receipt = self.fx.session.consume_start_permit(permit)
        self.assertTrue(receipt["consumed_before_external_start"])
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "not currently usable"):
            self.fx.session.consume_start_permit(permit)

    def test_explicit_refusal_revokes_reservation_and_returns_no_permit(self) -> None:
        self.fx.accept_yes()
        self.fx.reserve()
        observation = choice_observation(
            "STOP", "RECHECK", text="I refuse to see it. Please do not play it."
        )
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "revoked"):
            self.fx.session.recheck_and_authorize_start(
                observation, prompt_sha256=observation["prompt_sha256"]
            )
        self.assertEqual(self.fx.session.snapshot()["reservation_status"], "REVOKED_BY_PERSON")
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "lacks a consumed"):
            self.fx.session.record_presentation(presentation_observation(self.fx.session))

    def test_revocation_after_start_permit_consumption_blocks_completion(self) -> None:
        self.fx.accept_yes()
        self.fx.reserve()
        permit = self.fx.permit()
        self.fx.session.consume_start_permit(permit)
        observation = choice_observation("STOP", "RECHECK", text="Stop now; I refuse.")
        self.fx.session.revoke_reservation(
            observation, prompt_sha256=observation["prompt_sha256"]
        )
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "lacks a consumed"):
            self.fx.session.record_presentation(presentation_observation(self.fx.session))

    def test_reservation_expiry_fails_closed(self) -> None:
        self.fx.accept_yes()
        reservation = self.fx.reserve()
        future_utc = v5._utc(reservation["expires_at_utc"], "expiry") + timedelta(seconds=1)
        future_mono = int(reservation["expires_monotonic_ns"]) + 1
        observation = choice_observation("CONTINUE", "RECHECK")
        with mock.patch.object(v5, "_system_sample", return_value=(future_utc, future_mono)):
            with self.assertRaisesRegex(v5.ResidentMediaV5Error, "expired"):
                self.fx.session.recheck_and_authorize_start(
                    observation, prompt_sha256=observation["prompt_sha256"]
                )

    def test_restore_revalidates_completion_boolean_and_parent_digest(self) -> None:
        self.fx.accept_yes()
        self.fx.reserve()
        permit = self.fx.permit()
        self.fx.session.consume_start_permit(permit)
        self.fx.session.record_presentation(presentation_observation(self.fx.session))
        events = self.fx.session._journal.load_contiguous()
        mutated = copy.deepcopy(events)
        presentation = next(
            event for event in mutated if event["event_type"] == "PRESENTATION_RECORDED"
        )
        core = presentation["payload"]["presentation_core"]
        core["engineering_output_completed"] = False
        core["machine_audio_cue_created"] = 1
        core["external_parent_observation_sha256"] = "not-a-sha"
        presentation["payload"]["presentation_core_sha256"] = v5._record_sha(core)
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "not completed"):
            v5.validate_restored_presentation_events(mutated, self.fx.catalog)

        mutated = copy.deepcopy(events)
        presentation = next(
            event for event in mutated if event["event_type"] == "PRESENTATION_RECORDED"
        )
        core = presentation["payload"]["presentation_core"]
        core["machine_audio_cue_created"] = 1
        presentation["payload"]["presentation_core_sha256"] = v5._record_sha(core)
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "not boolean"):
            v5.validate_restored_presentation_events(mutated, self.fx.catalog)

        mutated = copy.deepcopy(events)
        presentation = next(
            event for event in mutated if event["event_type"] == "PRESENTATION_RECORDED"
        )
        core = presentation["payload"]["presentation_core"]
        core["external_parent_observation_sha256"] = "not-a-sha"
        presentation["payload"]["presentation_core_sha256"] = v5._record_sha(core)
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "must be SHA-256"):
            v5.validate_restored_presentation_events(mutated, self.fx.catalog)

    def test_restore_revalidates_refusal_first_choice_semantics(self) -> None:
        events = self.fx.session._journal.load_contiguous()
        phase = "INVITATION"
        observation = choice_observation("YES", phase, text="Do not show me.")
        forged = {
            "schema": "kira.resident_media_session_event.v4",
            "event_type": "CHOICE_ACCEPTED",
            "session_id": SESSION,
            "person_id": v4.PERSON_ID,
            "sequence": 1,
            "recorded_at_utc": events[0]["recorded_at_utc"],
            "recorded_monotonic_ns": events[0]["recorded_monotonic_ns"] + 1,
            "clock_id_sha256": v4.SystemClockAuthority.CLOCK_ID_SHA256,
            "previous_event_sha256": v5._record_sha(events[0]),
            "payload": {
                "schema": "kira.resident_media_choice_event.v4",
                "phase": phase,
                "observation": observation,
            },
        }
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "cannot override"):
            v5.validate_restored_presentation_events([events[0], forged], self.fx.catalog)

    def test_normal_bounded_flow_and_restore_pass(self) -> None:
        self.fx.accept_yes()
        self.fx.reserve()
        permit = self.fx.permit()
        self.fx.session.consume_start_permit(permit)
        self.fx.session.record_presentation(presentation_observation(self.fx.session))
        restored = self.fx.restore()
        snapshot = restored.snapshot()
        self.assertEqual(snapshot["v4_state"]["next_ordinal"], 1)
        self.assertEqual(snapshot["reservation_status"], "COMPLETED")
        self.assertFalse(snapshot["live_execution_allowed"])

    def test_completed_item_can_reset_control_for_next_voluntary_choice(self) -> None:
        self.fx.accept_yes()
        self.fx.reserve()
        permit = self.fx.permit()
        self.fx.session.consume_start_permit(permit)
        self.fx.session.record_presentation(presentation_observation(self.fx.session))
        phase = self.fx.session.next_required_phase
        observation = choice_observation("CONTINUE", phase)
        self.fx.session.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])
        token = self.fx.session.issue_capability(ttl_seconds=30)
        reservation = self.fx.session.reserve_presentation(token)
        self.assertEqual(reservation["ordinal"], 1)

    def test_static_summary_does_not_overclaim_live_readiness(self) -> None:
        summary = v5.static_contract_summary()
        self.assertFalse(summary["explicit_refusal_can_parse_as_yes"])
        self.assertFalse(summary["bare_caller_catalog_accepted"])
        self.assertFalse(summary["local_ledger_only_one_use_claimed"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["live_backend_implemented_here"])


if __name__ == "__main__":
    unittest.main()
