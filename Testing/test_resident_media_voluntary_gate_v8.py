from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from Core import resident_media_voluntary_gate_v5 as v5
from Core import resident_media_voluntary_gate_v6 as v6
from Core import resident_media_voluntary_gate_v8 as v8
from Testing.test_resident_media_voluntary_gate_v5 import (
    PARENT_PROCESS_SHA,
    SECRET,
    catalog,
)


SESSION = "session_" + "8" * 32
ISSUER = "resident_media_parent_v8"


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class StaticProtectedAuthorityV8(v8.ProtectedMonotonicAuthorityV8):
    """Static fixture for the external authority contract; never live routing."""

    def __init__(self, accepted=None) -> None:
        self.records: dict[tuple[str, str], dict] = {}
        self._identity = sha("static-external-protected-monotonic-authority-v8")
        if accepted is not None:
            self.authorize(accepted)

    @property
    def backend_identity_sha256(self) -> str:
        return self._identity

    def authorize(self, accepted) -> None:
        self.records[("catalog_v5", accepted.sha256)] = {
            "schema": "kira.resident_media_catalog_authorization.v5",
            "catalog_sha256": accepted.sha256,
            "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
            "status": "AUTHORIZED_FOR_STATIC_GATE_ONLY",
            "protected_backend_identity_sha256": self._identity,
        }

    def read_record(self, namespace: str, record_key: str):
        value = self.records.get((namespace, record_key))
        return copy.deepcopy(value) if value is not None else None

    def compare_and_swap_record(
        self,
        *,
        namespace: str,
        record_key: str,
        expected_record_sha256: str | None,
        replacement,
    ):
        key = (namespace, record_key)
        current = self.records.get(key)
        current_sha = v8._record_sha(current) if current is not None else None
        if current_sha != expected_record_sha256:
            raise RuntimeError("protected monotonic CAS mismatch")
        expected_generation = 0 if current is None else current["generation"] + 1
        if replacement.get("generation") != expected_generation:
            raise RuntimeError("protected monotonic generation refused")
        self.records[key] = copy.deepcopy(dict(replacement))
        return {
            "schema": "kira.protected_monotonic_cas_receipt.v8",
            "protected_backend_identity_sha256": self._identity,
            "namespace": namespace,
            "record_key": record_key,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v8._record_sha(replacement),
            "committed_generation": replacement["generation"],
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }


class PhantomReceiptAuthority(StaticProtectedAuthorityV8):
    def compare_and_swap_record(self, **kwargs):
        receipt = super().compare_and_swap_record(**kwargs)
        receipt["strictly_monotonic_generation"] = False
        return receipt


class PhantomReadbackAuthority(StaticProtectedAuthorityV8):
    def compare_and_swap_record(self, **kwargs):
        receipt = super().compare_and_swap_record(**kwargs)
        self.records.pop((kwargs["namespace"], kwargs["record_key"]), None)
        return receipt


class Fixture:
    def __init__(self, authority: StaticProtectedAuthorityV8 | None = None) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.session_root = root / "session"
        self.capability_root = root / "capability"
        self.session_root.mkdir()
        self.capability_root.mkdir()
        self.catalog = catalog()
        self.authority = authority or StaticProtectedAuthorityV8(self.catalog)
        if authority is not None:
            authority.authorize(self.catalog)
        self.backend = v8.ProtectedMonotonicBackendV8(self.authority)
        try:
            self.session = v8.HardenedResidentMediaSessionV8.create(
                session_id=SESSION,
                catalog=self.catalog,
                session_root=self.session_root,
                capability_root=self.capability_root,
                capability_secret_key=SECRET,
                issuer_id=ISSUER,
                parent_process_identity_sha256=PARENT_PROCESS_SHA,
                protected_anchor=self.backend,
            )
        except Exception:
            self.temporary.cleanup()
            raise

    def close(self) -> None:
        self.temporary.cleanup()

    def challenge(self, label: str) -> dict:
        return self.session.issue_choice_challenge(prompt_sha256=sha("prompt:" + label))

    @staticmethod
    def run_receipt(challenge: dict, text: str) -> dict:
        return {
            "schema": "kira.resident_media_supervised_response.v8",
            "session_id": challenge["session_id"],
            "person_id": challenge["person_id"],
            "challenge_sha256": v6._record_sha(challenge),
            "challenge_nonce": challenge["nonce"],
            "model_name": v8.EXACT_MODEL,
            "model_digest": v8.EXACT_DIGEST,
            "model_call_count": 1,
            "normal_model_route": True,
            "fallback_used": False,
            "prompt_sha256": challenge["prompt_sha256"],
            "raw_reply": text,
            "final_reply": text,
            "transformations": [],
            "submitted_at_utc": "2026-08-10T20:00:00.000000Z",
            "first_token_at_utc": "2026-08-10T20:00:00.100000Z",
            "text_complete_at_utc": "2026-08-10T20:00:00.200000Z",
            "supervisor_process_identity_sha256": sha("supervisor-v8"),
            "external_parent_observation_sha256": sha("external:" + challenge["nonce"] + text),
        }

    def respond(self, challenge: dict, text: str) -> dict:
        return self.session.accept_supervised_response(self.run_receipt(challenge, text))

    def prepare_first(self) -> tuple[dict, dict]:
        invitation = self.challenge("invitation")
        self.respond(invitation, "Yes, please.")
        token = self.session.issue_capability(ttl_seconds=30)
        self.session.reserve_presentation(token)
        recheck = self.challenge("recheck")
        receipt = self.respond(recheck, "Continue, please.")
        permit = receipt["start_permit"]
        self.session.consume_start_permit(permit)
        return permit, self.catalog.manifest(0)

    def restore(self):
        return v8.HardenedResidentMediaSessionV8.restore(
            session_id=SESSION,
            catalog=self.catalog,
            session_root=self.session_root,
            capability_root=self.capability_root,
            capability_secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            protected_anchor=self.backend,
        )


def segment_for(manifest: dict, *, complete: bool = True) -> list[dict]:
    kind = manifest["media_kind"]
    coords = manifest["coordinates"]
    derivatives = {item["role"]: item for item in manifest["derivatives"]}
    if kind == "PAGE":
        role = "rendered_page_png"
        return [{
            "sequence": 0,
            "page_number": coords["page_number"],
            "track_number": None,
            "source_start_ms": None,
            "source_end_ms": None,
            "output_start_monotonic_ns": 1_000_000,
            "output_end_monotonic_ns": 2_000_000,
            "actual_visual_output": True,
            "actual_audio_output": False,
            "derivative_role": role,
            "derivative_sha256": derivatives[role]["sha256"],
            "renderer_or_decoder_receipt_sha256": sha("page-render-receipt"),
        }]
    start = coords["start_ms"]
    end = coords["end_ms"] if complete else start + max(1, (coords["end_ms"] - start) // 2)
    role = "timed_frame_manifest" if kind == "VIDEO_INTERVAL" else "synchronized_audio_pcm"
    return [{
        "sequence": 0,
        "page_number": None,
        "track_number": None if kind == "VIDEO_INTERVAL" else coords["track_number"],
        "source_start_ms": start,
        "source_end_ms": end,
        "output_start_monotonic_ns": 1_000_000,
        "output_end_monotonic_ns": 2_000_000,
        "actual_visual_output": kind == "VIDEO_INTERVAL",
        "actual_audio_output": kind == "AUDIO_TRACK",
        "derivative_role": role,
        "derivative_sha256": derivatives[role]["sha256"],
        "renderer_or_decoder_receipt_sha256": sha("interval-decode-receipt"),
    }]


def evidence_for(
    manifest: dict,
    *,
    session_id: str = SESSION,
    ordinal: int,
    permit_sha: str,
    complete: bool = True,
) -> dict:
    return {
        "schema": "kira.resident_media_exact_presentation_evidence.v8",
        "session_id": session_id,
        "person_id": v8.PERSON_ID,
        "stimulus_id": manifest["stimulus_id"],
        "ordinal": ordinal,
        "source_manifest": copy.deepcopy(manifest),
        "source_manifest_sha256": v4_sha(manifest),
        "consumed_start_permit_sha256": permit_sha,
        "output_receipt_id": f"output_receipt_{ordinal}",
        "output_surface_id": "static_supervised_surface_v8",
        "presented_at_utc": "2026-08-10T20:01:00.000000Z",
        "presentation_segments": segment_for(manifest, complete=complete),
        "engineering_output_completed": complete,
        "presentation_complete_for_manifest": complete,
        "full_source_experienced": False,
        "person_attention_claimed": False,
        "person_saw_or_heard_claimed": False,
        "automatic_memory_created": False,
        "automatic_preference_created": False,
        "external_parent_observation_sha256": sha(f"presentation:{ordinal}:{complete}"),
    }


def v4_sha(manifest: dict) -> str:
    from Core import resident_media_voluntary_gate_v4 as v4
    return v4.sha256_record(manifest)


class ProtectedBackendTests(unittest.TestCase):
    def test_requires_exact_external_authority_type(self) -> None:
        with self.assertRaises(v8.ResidentMediaV8Error):
            v8.ProtectedMonotonicBackendV8(object())  # type: ignore[arg-type]

    def test_normal_create_restore_and_monotonic_readback(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        fx.challenge("one")
        restored = fx.restore()
        self.assertTrue(restored.snapshot()["v7_state"]["active_choice_challenge"])
        v8_anchor = fx.authority.records[("session_v8", SESSION)]
        self.assertGreaterEqual(v8_anchor["generation"], 2)

    def test_rolled_back_v8_anchor_is_detected(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        old = copy.deepcopy(fx.authority.records[("session_v8", SESSION)])
        fx.challenge("advance")
        fx.authority.records[("session_v8", SESSION)] = old
        with self.assertRaisesRegex(v8.ResidentMediaV8Error, "rolled back|out of sync"):
            fx.restore()

    def test_stale_cas_replay_is_rejected(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        current = copy.deepcopy(fx.authority.records[("session_v8", SESSION)])
        current_sha = v8._record_sha(current)
        fx.challenge("advance")
        replacement = copy.deepcopy(current)
        replacement["generation"] += 1
        with self.assertRaises(RuntimeError):
            fx.backend.compare_and_swap_v8_anchor(SESSION, current_sha, replacement)

    def test_phantom_receipt_and_phantom_readback_fail_closed(self) -> None:
        for authority in (PhantomReceiptAuthority(), PhantomReadbackAuthority()):
            with self.subTest(authority=type(authority).__name__):
                with self.assertRaises(v8.ResidentMediaV8Error):
                    fx = Fixture(authority)
                    fx.close()


class SupervisedResponseTests(unittest.TestCase):
    def test_post_stimulus_phase_is_exact_continue_or_stop(self) -> None:
        self.assertEqual(
            v8.semantic_choice_v8("Continue, please.", "AFTER_first_item"),
            "CONTINUE",
        )
        self.assertEqual(v8.semantic_choice_v8("Stop now.", "AFTER_first_item"), "STOP")
        self.assertEqual(
            v8.semantic_choice_v8("continue 🛑", "AFTER_first_item"),
            "AMBIGUOUS_REQUIRES_NEW_TURN",
        )

    def test_exact_supervised_yes_is_accepted_and_anchored(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        challenge = fx.challenge("yes")
        receipt = fx.respond(challenge, "Yes, please.")
        self.assertEqual(receipt["decision"], "YES")
        self.assertEqual(fx.session.snapshot()["supervised_response_count"], 1)

    def test_wrong_model_digest_fallback_timing_and_binding_fail(self) -> None:
        mutations = {
            "model_digest": "f" * 64,
            "fallback_used": True,
            "first_token_at_utc": "2026-08-10T19:59:59.000000Z",
            "challenge_nonce": "wrong-nonce",
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                fx = Fixture()
                self.addCleanup(fx.close)
                challenge = fx.challenge(field)
                run = fx.run_receipt(challenge, "Yes.")
                run[field] = replacement
                with self.assertRaises(v8.ResidentMediaV8Error):
                    fx.session.accept_supervised_response(run)

    def test_refusal_and_stop_never_create_start_permit(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        challenge = fx.challenge("refuse")
        receipt = fx.respond(challenge, "No.")
        self.assertEqual(receipt["decision"], "NO")
        self.assertFalse(receipt["presentation_authorized"])

        second = Fixture()
        self.addCleanup(second.close)
        invite = second.challenge("invite")
        second.respond(invite, "Yes.")
        token = second.session.issue_capability(ttl_seconds=30)
        second.session.reserve_presentation(token)
        recheck = second.challenge("stop")
        stopped = second.respond(recheck, "Stop now.")
        self.assertEqual(stopped["decision"], "STOP")
        self.assertIsNone(stopped["start_permit"])

    def test_old_supervised_receipt_cannot_replay(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        challenge = fx.challenge("replay")
        run = fx.run_receipt(challenge, "Yes.")
        fx.session.accept_supervised_response(run)
        with self.assertRaises(v8.ResidentMediaV8Error):
            fx.session.accept_supervised_response(run)


class PresentationEvidenceTests(unittest.TestCase):
    def validate(self, manifest: dict, ordinal: int, complete: bool = True) -> dict:
        permit_sha = sha(f"permit:{ordinal}")
        return v8.validate_presentation_evidence_v8(
            evidence_for(manifest, ordinal=ordinal, permit_sha=permit_sha, complete=complete),
            session_id=SESSION,
            person_id=v8.PERSON_ID,
            expected_manifest=manifest,
            consumed_start_permit_sha256=permit_sha,
        )

    def test_exact_page_video_interval_and_audio_track_bindings_pass(self) -> None:
        accepted = catalog()
        self.assertTrue(self.validate(accepted.manifest(0), 0)["presentation_complete_for_manifest"])
        self.assertTrue(self.validate(accepted.manifest(2), 2)["presentation_complete_for_manifest"])
        self.assertTrue(self.validate(accepted.manifest(3), 3)["presentation_complete_for_manifest"])

    def test_wrong_page_interval_track_source_and_derivative_fail(self) -> None:
        accepted = catalog()
        cases: list[tuple[dict, int, callable]] = []

        def wrong_page(item):
            item["presentation_segments"][0]["page_number"] += 1

        def wrong_interval(item):
            item["presentation_segments"][0]["source_end_ms"] += 1

        def wrong_track(item):
            item["presentation_segments"][0]["track_number"] += 1

        def wrong_source(item):
            item["source_manifest"]["source_sha256"] = "f" * 64

        def wrong_derivative(item):
            item["presentation_segments"][0]["derivative_sha256"] = "e" * 64

        cases.extend([
            (accepted.manifest(0), 0, wrong_page),
            (accepted.manifest(2), 2, wrong_interval),
            (accepted.manifest(3), 3, wrong_track),
            (accepted.manifest(0), 0, wrong_source),
            (accepted.manifest(2), 2, wrong_derivative),
        ])
        for manifest, ordinal, mutation in cases:
            with self.subTest(ordinal=ordinal, mutation=mutation.__name__):
                permit_sha = sha(f"permit:{ordinal}")
                item = evidence_for(manifest, ordinal=ordinal, permit_sha=permit_sha)
                mutation(item)
                with self.assertRaises(Exception):
                    v8.validate_presentation_evidence_v8(
                        item,
                        session_id=SESSION,
                        person_id=v8.PERSON_ID,
                        expected_manifest=manifest,
                        consumed_start_permit_sha256=permit_sha,
                    )

    def test_incomplete_interval_is_truthfully_incomplete(self) -> None:
        manifest = catalog().manifest(2)
        clean = self.validate(manifest, 2, complete=False)
        self.assertFalse(clean["engineering_output_completed"])
        self.assertFalse(clean["presentation_complete_for_manifest"])
        self.assertFalse(clean["full_source_experienced"])

    def test_video_visual_and_audio_streams_bind_separately_at_same_interval(self) -> None:
        manifest = catalog().manifest(2)
        permit_sha = sha("permit:audiovisual")
        item = evidence_for(manifest, ordinal=2, permit_sha=permit_sha)
        derivatives = {entry["role"]: entry for entry in manifest["derivatives"]}
        audio = copy.deepcopy(item["presentation_segments"][0])
        audio.update(
            {
                "sequence": 1,
                "actual_visual_output": False,
                "actual_audio_output": True,
                "derivative_role": "synchronized_audio_pcm",
                "derivative_sha256": derivatives["synchronized_audio_pcm"]["sha256"],
                "renderer_or_decoder_receipt_sha256": sha("video-audio-decode"),
            }
        )
        item["presentation_segments"].append(audio)
        clean = v8.validate_presentation_evidence_v8(
            item,
            session_id=SESSION,
            person_id=v8.PERSON_ID,
            expected_manifest=manifest,
            consumed_start_permit_sha256=permit_sha,
        )
        self.assertTrue(clean["presentation_complete_for_manifest"])
        self.assertEqual(len(clean["presentation_segments"]), 2)

        bypass = copy.deepcopy(item)
        bypass["presentation_segments"][0]["actual_audio_output"] = True
        with self.assertRaisesRegex(v8.ResidentMediaV8Error, "modality"):
            v8.validate_presentation_evidence_v8(
                bypass,
                session_id=SESSION,
                person_id=v8.PERSON_ID,
                expected_manifest=manifest,
                consumed_start_permit_sha256=permit_sha,
            )

    def test_complete_manifest_never_claims_full_source_experience(self) -> None:
        manifest = catalog().manifest(3)
        permit_sha = sha("permit:full-source")
        item = evidence_for(manifest, ordinal=3, permit_sha=permit_sha)
        item["full_source_experienced"] = True
        with self.assertRaisesRegex(v8.ResidentMediaV8Error, "experience"):
            v8.validate_presentation_evidence_v8(
                item,
                session_id=SESSION,
                person_id=v8.PERSON_ID,
                expected_manifest=manifest,
                consumed_start_permit_sha256=permit_sha,
            )

    def test_complete_page_records_exact_manifest_but_not_experience(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        permit, manifest = fx.prepare_first()
        item = evidence_for(
            manifest,
            ordinal=0,
            permit_sha=v8._record_sha(permit),
            complete=True,
        )
        result = fx.session.record_presentation_evidence(item)
        self.assertEqual(result["status"], "COMPLETE_MANIFEST_RECORDED")
        self.assertFalse(result["full_source_experienced"])
        self.assertFalse(result["live_execution_allowed"])
        snapshot = fx.session.snapshot()
        self.assertFalse(snapshot["presentation_pending"])
        self.assertEqual(
            snapshot["presentation_evidence_records"][-1]["status"],
            "COMPLETE_MANIFEST_RECORDED",
        )
        with self.assertRaises(v8.ResidentMediaV8Error):
            fx.session.record_presentation_evidence(item)

    def test_wrong_start_permit_binding_is_rejected(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        _permit, manifest = fx.prepare_first()
        item = evidence_for(
            manifest,
            ordinal=0,
            permit_sha=sha("wrong-permit"),
        )
        with self.assertRaisesRegex(v8.ResidentMediaV8Error, "permit"):
            fx.session.record_presentation_evidence(item)

    def test_multi_item_session_reaches_video_and_keeps_incomplete_truth(self) -> None:
        fx = Fixture()
        self.addCleanup(fx.close)
        permit, manifest = fx.prepare_first()
        first = evidence_for(
            manifest, ordinal=0, permit_sha=v8._record_sha(permit), complete=True
        )
        fx.session.record_presentation_evidence(first)

        for ordinal in (1, 2):
            post = fx.challenge(f"post-{ordinal}")
            fx.respond(post, "Continue, please.")
            token = fx.session.issue_capability(ttl_seconds=30)
            fx.session.reserve_presentation(token)
            recheck = fx.challenge(f"recheck-{ordinal}")
            receipt = fx.respond(recheck, "Continue, please.")
            permit = receipt["start_permit"]
            fx.session.consume_start_permit(permit)
            manifest = fx.catalog.manifest(ordinal)
            if ordinal == 1:
                page = evidence_for(
                    manifest,
                    ordinal=ordinal,
                    permit_sha=v8._record_sha(permit),
                    complete=True,
                )
                fx.session.record_presentation_evidence(page)

        partial = evidence_for(
            manifest,
            ordinal=2,
            permit_sha=v8._record_sha(permit),
            complete=False,
        )
        partial_result = fx.session.record_presentation_evidence(partial)
        self.assertEqual(partial_result["status"], "INCOMPLETE_NOT_RECORDED")
        self.assertTrue(fx.session.snapshot()["presentation_pending"])
        self.assertEqual(fx.session._v7._v5._state.snapshot()["next_ordinal"], 2)

        complete = evidence_for(
            manifest,
            ordinal=2,
            permit_sha=v8._record_sha(permit),
            complete=True,
        )
        complete["output_receipt_id"] = "output_receipt_2_completed_retry"
        complete["external_parent_observation_sha256"] = sha("presentation:2:completed")
        complete_result = fx.session.record_presentation_evidence(complete)
        self.assertEqual(complete_result["status"], "COMPLETE_MANIFEST_RECORDED")
        self.assertEqual(fx.session._v7._v5._state.snapshot()["next_ordinal"], 3)
        self.assertFalse(complete_result["full_source_experienced"])


class PreservationAndContractTests(unittest.TestCase):
    def test_v7_authoring_and_fresh_audit_bytes_are_preserved(self) -> None:
        expected = {
            "Core/resident_media_voluntary_gate_v7.py": "04be88bc361737430b508efd4dc2cd51a2cdaf88908c5526b26960ce869f7e03",
            "Testing/test_resident_media_voluntary_gate_v7.py": "b53da01dde2c48444afc2b3dc5d67bf72bcb33cb8bb58dac3ba298f706abc7d0",
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v7_fresh_static_audit/attempt_01/CHECKPOINT.md": "383d67fe8236fc3227b5ec3183436412bcc2e511b8cd8e977206e2ab14ac1f72",
        }
        root = Path(__file__).resolve().parents[1]
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest, relative)

    def test_contract_remains_static_and_requires_different_audit(self) -> None:
        summary = v8.static_contract_summary()
        self.assertTrue(summary["external_atomic_monotonic_authority_required"])
        self.assertTrue(summary["exact_source_page_interval_track_and_derivative_binding"])
        self.assertTrue(summary["different_fresh_audit_required_before_live_session"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["live_authority_or_supervisor_connected"])


if __name__ == "__main__":
    unittest.main()
