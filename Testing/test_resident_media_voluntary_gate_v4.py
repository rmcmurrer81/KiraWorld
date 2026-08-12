from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Core import resident_media_voluntary_gate_v4 as v4


PARENT_PROCESS_SHA = hashlib.sha256(b"bounded-external-parent-process-v4").hexdigest()
SECRET = hashlib.sha256(b"static-test-only-capability-secret-v4").digest()
ISSUER = "resident_media_parent_v4"
SESSION = "session_" + "4" * 32


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derivative(stimulus_id: str, source_sha: str, role: str) -> dict:
    return {
        "schema": "kira.resident_media_derivative_identity.v4",
        "derivative_id": f"{stimulus_id}_{role}",
        "role": role,
        "relative_path": f"derived/{stimulus_id}/{role}.bin",
        "byte_count": 1000 + len(stimulus_id) + len(role),
        "sha256": sha(f"derivative:{stimulus_id}:{role}"),
        "derived_from_source_sha256": source_sha,
    }


def manifest(stimulus_id: str, ordinal: int) -> dict:
    source_sha = sha(f"source:{stimulus_id}")
    if ordinal < 2:
        media_kind = "PAGE"
        coordinates = {"kind": "PAGE_NUMBER", "page_number": (1, 14)[ordinal]}
        roles = ("rendered_page_png", "ocr_text_utf8")
        suffix = "pdf"
    else:
        media_kind = "VIDEO_INTERVAL"
        coordinates = {
            "kind": "INTERVAL_MS",
            "start_ms": 0,
            "end_ms": (8000, 10000)[ordinal - 2],
        }
        roles = ("timed_frame_manifest", "synchronized_audio_pcm", "caption_text_utf8")
        suffix = "mkv"
    return {
        "schema": "kira.resident_media_source_manifest.v4",
        "stimulus_id": stimulus_id,
        "opaque_media_id": f"media_{ordinal:02d}_{sha(stimulus_id)[:16]}",
        "media_kind": media_kind,
        "source_relative_path": f"Data/library/test_sources/{stimulus_id}.{suffix}",
        "source_byte_count": 100_000 + ordinal,
        "source_sha256": source_sha,
        "coordinates": coordinates,
        "derivatives": [derivative(stimulus_id, source_sha, role) for role in roles],
    }


def catalog() -> v4.StimulusCatalog:
    return v4.StimulusCatalog(
        [manifest(stimulus_id, ordinal) for ordinal, stimulus_id in enumerate(v4.STIMULUS_ORDER)]
    )


def choice_observation(value: str, phase: str, *, raw: str | None = None, final: str | None = None) -> dict:
    default = {
        "YES": "Yes, I would like to see it.",
        "NO": "No, I do not want to see it.",
        "CONTINUE": "Continue to the next item.",
        "PAUSE": "Pause and wait.",
        "STOP": "Stop now.",
    }[value]
    return {
        "schema": "kira.resident_media_choice_observation.v4",
        "model_name": v4.EXACT_MODEL,
        "model_digest": v4.EXACT_DIGEST,
        "model_call_count": 1,
        "normal_model_route": True,
        "fallback_used": False,
        "prompt_sha256": sha(phase),
        "raw_reply": raw if raw is not None else default,
        "final_reply": final if final is not None else (raw if raw is not None else default),
        "transformations": [],
        "choice": value,
        "external_parent_observation_sha256": sha(f"observation:{phase}:{default}"),
    }


def presentation_observation(state: v4.VoluntaryMediaState) -> dict:
    ordinal = state.snapshot()["next_ordinal"]
    return {
        "schema": "kira.resident_media_presentation_observation.v4",
        "source_manifest": state.catalog.manifest(ordinal),
        "engineering_output_completed": True,
        "machine_visual_interpretation_created": ordinal < 4,
        "machine_audio_cue_created": ordinal >= 2,
        "machine_context_packet_created": True,
        "person_attention_claimed": False,
        "person_saw_or_heard_claimed": False,
        "automatic_memory_created": False,
        "automatic_preference_created": False,
        "external_parent_observation_sha256": sha(f"presentation:{ordinal}"),
    }


class Fixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.session_root = root / "session"
        self.capability_root = root / "capabilities"
        self.session_root.mkdir()
        self.capability_root.mkdir()
        self.catalog = catalog()
        self.state_clock = v4.SystemClockAuthority()
        self.cap_clock = v4.SystemClockAuthority()
        self.authority = v4.DurableCapabilityAuthority(
            root=self.capability_root,
            secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            clock=self.cap_clock,
        )
        self.journal = v4.DurableSessionJournal(self.session_root)
        self.state = v4.VoluntaryMediaState.create(
            session_id=SESSION,
            catalog=self.catalog,
            journal=self.journal,
            capability_authority=self.authority,
            clock=self.state_clock,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
        )

    def close(self) -> None:
        self.temporary.cleanup()

    def accept(self, value: str, **kwargs: str) -> str:
        phase = self.state.next_required_phase
        observation = choice_observation(value, phase, **kwargs)
        return self.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])

    def issue(self) -> dict:
        return self.authority.issue(self.state.expected_capability_binding(), ttl_seconds=30)

    def reserve(self, token: dict | None = None) -> dict:
        use = token if token is not None else self.issue()
        return self.state.reserve_presentation(use)

    def present(self, token: dict | None = None) -> str:
        reservation = self.reserve(token)
        return self.state.record_presentation(presentation_observation(self.state), reservation)

    def restarted_authority(self) -> v4.DurableCapabilityAuthority:
        return v4.DurableCapabilityAuthority(
            root=self.capability_root,
            secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            clock=v4.SystemClockAuthority(),
        )

    def restore_state(self, authority: v4.DurableCapabilityAuthority | None = None) -> v4.VoluntaryMediaState:
        return v4.VoluntaryMediaState.restore(
            session_id=SESSION,
            catalog=self.catalog,
            journal=v4.DurableSessionJournal(self.session_root),
            capability_authority=authority or self.restarted_authority(),
            clock=v4.SystemClockAuthority(),
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
        )


class ResidentMediaVoluntaryGateV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def tearDown(self) -> None:
        self.fx.close()

    def test_v3_bytes_are_preserved_exactly(self) -> None:
        expected = {
            Path("Core/resident_media_voluntary_gate_v3.py"): (19045, "ea2e4b404a1d1594679af3a72b7f14580a9c3ccaf2ff6067c1f4233fccc6b4bc"),
            Path("Testing/test_resident_media_voluntary_gate_v3.py"): (10000, "5732ef8720f861b7f58fca1c03bf9344767d1f8db73a6ae3fcf74f4890c7af76"),
        }
        for path, (size, digest) in expected.items():
            data = path.read_bytes()
            self.assertEqual(len(data), size)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)

    def test_no_capability_before_clear_yes(self) -> None:
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "no current accepted choice"):
            self.fx.state.expected_capability_binding()

    def test_plain_decline_cannot_be_labeled_yes(self) -> None:
        before = self.fx.state.snapshot()
        observation = choice_observation(
            "YES",
            "INVITATION",
            raw="No, I do not want to see it.",
            final="No, I do not want to see it.",
        )
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "cannot override"):
            self.fx.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])
        self.assertEqual(self.fx.state.snapshot(), before)
        self.assertEqual(len(list(self.fx.session_root.iterdir())), 1)

    def test_plain_later_decline_cannot_be_labeled_continue(self) -> None:
        self.fx.accept("YES")
        self.fx.present()
        phase = self.fx.state.next_required_phase
        observation = choice_observation(
            "CONTINUE",
            phase,
            raw="No, I don't want another item.",
            final="No, I don't want another item.",
        )
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "cannot override"):
            self.fx.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])

    def test_mixed_and_self_correcting_words_require_new_turn(self) -> None:
        for text in (
            "No, I do not want it. Actually yes, show me.",
            "Yes, but wait, not yet.",
            "I might want to, maybe, I am unsure.",
        ):
            observation = choice_observation("YES", "INVITATION", raw=text, final=text)
            with self.subTest(text=text), self.assertRaisesRegex(
                v4.ResidentMediaV4Error, "requires a new turn"
            ):
                self.fx.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])

    def test_raw_and_final_cannot_disagree(self) -> None:
        observation = choice_observation(
            "YES",
            "INVITATION",
            raw="Yes, show me.",
            final="No, I do not want it.",
        )
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "raw and final"):
            self.fx.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])

    def test_clear_stop_and_decline_remain_non_authorizing(self) -> None:
        observation = choice_observation(
            "STOP", "INVITATION", raw="No. Stop now.", final="No. Stop now."
        )
        self.fx.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])
        self.assertTrue(self.fx.state.stopped)
        with self.assertRaises(v4.ResidentMediaV4Error):
            self.fx.state.expected_capability_binding()

    def test_transition_record_cannot_supply_caller_time(self) -> None:
        observation = choice_observation("YES", "INVITATION")
        observation["created_at_utc"] = "2099-01-01T00:00:00Z"
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "keys are not exact"):
            self.fx.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])

    def test_source_hash_byte_count_coordinates_and_derivatives_are_exact(self) -> None:
        mutations = (
            ("source_sha256", "0" * 64),
            ("source_byte_count", 1),
            ("coordinates.page_number", 2),
            ("derivatives.0.sha256", "f" * 64),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                local = Fixture()
                try:
                    local.accept("YES")
                    token = local.issue()
                    reservation = local.reserve(token)
                    observation = presentation_observation(local.state)
                    if field == "source_sha256":
                        observation["source_manifest"][field] = value
                        for item in observation["source_manifest"]["derivatives"]:
                            item["derived_from_source_sha256"] = value
                    elif field == "source_byte_count":
                        observation["source_manifest"][field] = value
                    elif field == "coordinates.page_number":
                        observation["source_manifest"]["coordinates"]["page_number"] = value
                    else:
                        observation["source_manifest"]["derivatives"][0]["sha256"] = value
                    before = local.state.snapshot()
                    with self.assertRaises(v4.ResidentMediaV4Error):
                        local.state.record_presentation(observation, reservation)
                    self.assertEqual(local.state.snapshot(), before)
                    self.assertTrue(before["presentation_reservation_pending"])
                finally:
                    local.close()

    def test_source_path_traversal_and_missing_derivatives_fail(self) -> None:
        candidate = manifest(v4.STIMULUS_ORDER[0], 0)
        candidate["source_relative_path"] = "../outside.pdf"
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "project-relative"):
            v4.validate_source_manifest(candidate)
        candidate = manifest(v4.STIMULUS_ORDER[0], 0)
        candidate["derivatives"] = []
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "derivative"):
            v4.validate_source_manifest(candidate)

    def test_capability_binds_every_declared_identity(self) -> None:
        self.fx.accept("YES")
        binding = self.fx.state.expected_capability_binding()
        token = self.fx.authority.issue(binding)
        fields = (
            "session_id",
            "person_id",
            "stimulus_id",
            "ordinal",
            "session_event_sequence",
            "choice_event_sha256",
            "source_manifest_sha256",
            "source_byte_count",
            "source_coordinates_sha256",
            "derivative_set_sha256",
            "parent_process_identity_sha256",
        )
        for field in fields:
            forged = dict(token)
            forged[field] = (forged[field] + "x") if isinstance(forged[field], str) else forged[field] + 1
            with self.subTest(field=field), self.assertRaises(v4.ResidentMediaV4Error):
                self.fx.authority.verify_unconsumed(forged, binding)

    def test_capability_signature_and_durable_issue_record_are_required(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        forged = dict(token)
        forged["signature_sha256"] = "0" * 64
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "signature"):
            self.fx.authority.verify_unconsumed(forged, self.fx.state.expected_capability_binding())
        issue_path = self.fx.capability_root / f"capability_issue_binding_{token['binding_sha256']}.json"
        issue_path.write_bytes(b'{"schema":"tampered"}\n')
        with self.assertRaises(v4.ResidentMediaV4Error):
            self.fx.authority.verify_unconsumed(token, self.fx.state.expected_capability_binding())

    def test_one_choice_source_binding_cannot_mint_two_capabilities(self) -> None:
        self.fx.accept("YES")
        binding = self.fx.state.expected_capability_binding()
        self.fx.authority.issue(binding)
        with self.assertRaises(FileExistsError):
            self.fx.authority.issue(binding)

    def test_capability_expiry_uses_monotonic_clock_without_sleep(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clock = v4.SystemClockAuthority()
            authority = v4.DurableCapabilityAuthority(
                root=root,
                secret_key=SECRET,
                issuer_id=ISSUER,
                parent_process_identity_sha256=PARENT_PROCESS_SHA,
                clock=clock,
            )
            binding = v4.CapabilityBinding(
                session_id=SESSION,
                person_id="kira",
                stimulus_id=v4.STIMULUS_ORDER[0],
                ordinal=0,
                session_event_sequence=2,
                choice_event_sha256=sha("choice"),
                source_manifest_sha256=sha("manifest"),
                source_byte_count=1,
                source_coordinates_sha256=sha("coordinates"),
                derivative_set_sha256=sha("derivatives"),
                parent_process_identity_sha256=PARENT_PROCESS_SHA,
            )
            with mock.patch.object(v4.time, "monotonic_ns", side_effect=[1_000_000_000, 3_000_000_001]):
                token = authority.issue(binding, ttl_seconds=1)
                with self.assertRaisesRegex(v4.ResidentMediaV4Error, "not fresh"):
                    authority.verify_unconsumed(token, binding)

    def test_capability_is_durably_single_use_across_authority_restart(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        binding = self.fx.state.expected_capability_binding()
        self.fx.reserve(token)
        restarted = self.fx.restarted_authority()
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "already consumed"):
            restarted.verify_unconsumed(token, binding)

    def test_unconsumed_capability_survives_authority_restart(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        binding = self.fx.state.expected_capability_binding()
        clean = self.fx.restarted_authority().verify_unconsumed(token, binding)
        self.assertEqual(clean, token)

    def test_consumed_capability_cannot_authorize_the_next_stimulus(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        self.fx.present(token)
        self.fx.accept("CONTINUE")
        with self.assertRaises(v4.ResidentMediaV4Error):
            self.fx.state.reserve_presentation(token)

    def test_person_claims_fail_after_reservation_without_completion(self) -> None:
        for field in (
            "person_attention_claimed",
            "person_saw_or_heard_claimed",
            "automatic_memory_created",
            "automatic_preference_created",
        ):
            with self.subTest(field=field):
                local = Fixture()
                try:
                    local.accept("YES")
                    token = local.issue()
                    reservation = local.reserve(token)
                    observation = presentation_observation(local.state)
                    observation[field] = True
                    with self.assertRaisesRegex(v4.ResidentMediaV4Error, "cannot assert"):
                        local.state.record_presentation(observation, reservation)
                    self.assertTrue(local.state.snapshot()["presentation_reservation_pending"])
                finally:
                    local.close()

    def test_incomplete_output_leaves_fail_closed_consumed_reservation(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        reservation = self.fx.reserve(token)
        observation = presentation_observation(self.fx.state)
        observation["engineering_output_completed"] = False
        before = self.fx.state.snapshot()
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "incomplete"):
            self.fx.state.record_presentation(observation, reservation)
        self.assertEqual(self.fx.state.snapshot(), before)
        self.assertTrue(before["presentation_reservation_pending"])

    def test_presentation_cannot_be_recorded_before_durable_reservation(self) -> None:
        self.fx.accept("YES")
        fake = {
            "schema": "kira.resident_media_presentation_reservation.v4",
            "session_id": SESSION,
        }
        before = self.fx.state.snapshot()
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "no durable consumed reservation"):
            self.fx.state.record_presentation(presentation_observation(self.fx.state), fake)
        self.assertEqual(self.fx.state.snapshot(), before)

    def test_pending_reservation_reopens_exactly_and_remains_consumed(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        reservation = self.fx.reserve(token)
        expected = self.fx.state.snapshot()
        restarted_authority = self.fx.restarted_authority()
        restored = self.fx.restore_state(restarted_authority)
        self.assertEqual(restored.snapshot(), expected)
        self.assertTrue(expected["presentation_reservation_pending"])
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "already consumed"):
            restarted_authority.verify_unconsumed(
                token,
                v4.CapabilityBinding(
                    session_id=SESSION,
                    person_id="kira",
                    stimulus_id=reservation["stimulus_id"],
                    ordinal=reservation["ordinal"],
                    session_event_sequence=2,
                    choice_event_sha256=token["choice_event_sha256"],
                    source_manifest_sha256=token["source_manifest_sha256"],
                    source_byte_count=token["source_byte_count"],
                    source_coordinates_sha256=token["source_coordinates_sha256"],
                    derivative_set_sha256=token["derivative_set_sha256"],
                    parent_process_identity_sha256=PARENT_PROCESS_SHA,
                ),
            )

    def test_state_does_not_advance_when_durable_choice_append_fails(self) -> None:
        observation = choice_observation("YES", "INVITATION")
        before = self.fx.state.snapshot()
        with mock.patch.object(
            self.fx.journal,
            "append",
            side_effect=v4.ResidentMediaV4Error("injected append failure"),
        ):
            with self.assertRaisesRegex(v4.ResidentMediaV4Error, "injected"):
                self.fx.state.accept_choice(observation, prompt_sha256=observation["prompt_sha256"])
        self.assertEqual(self.fx.state.snapshot(), before)

    def test_state_does_not_advance_if_reservation_journal_fails_after_consumption(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        binding = self.fx.state.expected_capability_binding()
        before = self.fx.state.snapshot()
        with mock.patch.object(
            self.fx.journal,
            "append",
            side_effect=v4.ResidentMediaV4Error("injected reservation append failure"),
        ):
            with self.assertRaisesRegex(v4.ResidentMediaV4Error, "injected reservation"):
                self.fx.state.reserve_presentation(token)
        self.assertEqual(self.fx.state.snapshot(), before)
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "already consumed"):
            self.fx.authority.verify_unconsumed(token, binding)
        with self.assertRaises(FileExistsError):
            self.fx.authority.issue(binding)

    def test_state_does_not_advance_if_completion_journal_fails(self) -> None:
        self.fx.accept("YES")
        reservation = self.fx.reserve()
        before = self.fx.state.snapshot()
        with mock.patch.object(
            self.fx.journal,
            "append",
            side_effect=v4.ResidentMediaV4Error("injected completion append failure"),
        ):
            with self.assertRaisesRegex(v4.ResidentMediaV4Error, "injected completion"):
                self.fx.state.record_presentation(
                    presentation_observation(self.fx.state), reservation
                )
        self.assertEqual(self.fx.state.snapshot(), before)
        self.assertTrue(before["presentation_reservation_pending"])

    def test_exclusive_append_fsync_reopen_and_identity_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = v4.DurableDirectory(Path(temporary))
            receipt = store.exclusive_append("record.json", {"schema": "test", "value": 1})
            self.assertTrue(receipt["exclusive_create"])
            self.assertTrue(receipt["fsync_completed"])
            self.assertTrue(receipt["reopened_exact"])
            self.assertTrue(receipt["file_identity_validated"])
            with self.assertRaises(FileExistsError):
                store.exclusive_append("record.json", {"schema": "test", "value": 2})

    def test_restore_rejects_future_or_nonmonotonic_event_time(self) -> None:
        self.fx.accept("YES")
        path = self.fx.session_root / "event_000001.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["recorded_at_utc"] = "2099-01-01T00:00:00.000000Z"
        path.write_bytes(v4.canonical_json_bytes(record) + b"\n")
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "future"):
            self.fx.restore_state()

    def test_restore_rejects_event_hash_chain_tampering(self) -> None:
        self.fx.accept("YES")
        token = self.fx.issue()
        self.fx.present(token)
        path = self.fx.session_root / "event_000002.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["previous_event_sha256"] = "0" * 64
        path.write_bytes(v4.canonical_json_bytes(record) + b"\n")
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "chain"):
            self.fx.restore_state()

    def test_restore_rejects_monotonic_regression(self) -> None:
        self.fx.accept("YES")
        genesis = json.loads(
            (self.fx.session_root / "event_000000.json").read_text(encoding="utf-8")
        )
        path = self.fx.session_root / "event_000001.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["recorded_monotonic_ns"] = genesis["recorded_monotonic_ns"]
        path.write_bytes(v4.canonical_json_bytes(record) + b"\n")
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "monotonic"):
            self.fx.restore_state()

    def test_state_reopens_and_reconstructs_exactly(self) -> None:
        self.fx.accept("YES")
        self.fx.present()
        expected = self.fx.state.snapshot()
        restored = self.fx.restore_state()
        self.assertEqual(restored.snapshot(), expected)

    def test_pause_needs_a_new_durable_choice_to_resume(self) -> None:
        self.fx.accept("YES")
        self.fx.present()
        self.fx.accept("PAUSE")
        with self.assertRaises(v4.ResidentMediaV4Error):
            self.fx.state.expected_capability_binding()
        self.fx.accept("CONTINUE")
        token = self.fx.issue()
        self.assertEqual(token["ordinal"], 1)

    def test_full_sequence_finishes_without_person_experience_claim(self) -> None:
        self.fx.accept("YES")
        for ordinal in range(len(v4.STIMULUS_ORDER)):
            self.fx.present()
            if ordinal + 1 < len(v4.STIMULUS_ORDER):
                self.fx.accept("CONTINUE")
        self.fx.state.mark_engineering_finished()
        snap = self.fx.state.snapshot()
        self.assertTrue(snap["engineering_finished"])
        self.assertFalse(snap["live_execution_allowed"])
        self.assertFalse(snap["parent_process_trust_proven"])
        self.assertFalse(snap["selected_person_direct_seeing_or_hearing_proven"])
        self.assertFalse(snap["automatic_memory_or_preference_created"])
        restored = self.fx.restore_state()
        self.assertEqual(restored.snapshot(), snap)

    def test_duplicate_json_keys_and_nonfinite_values_fail(self) -> None:
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "duplicate"):
            v4.strict_json_loads(b'{"choice":"YES","choice":"STOP"}')
        with self.assertRaisesRegex(v4.ResidentMediaV4Error, "non-finite"):
            v4.strict_json_loads(b'{"x":NaN}')

    def test_static_contract_remains_inert_and_truthful(self) -> None:
        result = v4.static_execution_requirements()
        self.assertFalse(result["live_execution_allowed"])
        self.assertTrue(result["fresh_independent_hostile_audit_required"])
        self.assertTrue(result["capability_single_use_is_durable_across_authority_restart"])
        self.assertTrue(result["exact_manifest_byte_count_hash_coordinates_and_derivatives_bound"])
        self.assertFalse(result["automatic_memory_or_preference"])


if __name__ == "__main__":
    unittest.main()
