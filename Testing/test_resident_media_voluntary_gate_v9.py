from __future__ import annotations

import copy
import hashlib
import unittest

from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9
from Testing.test_resident_media_voluntary_gate_v5 import catalog


SESSION = "session_" + "9" * 32
PERSON = "person_kira_primary"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StaticAuthority(v8.ProtectedMonotonicAuthorityV8):
    def __init__(self) -> None:
        self.records: dict[tuple[str, str], dict] = {}
        self._identity = sha("resident-media-v9-static-protected-authority")

    @property
    def backend_identity_sha256(self) -> str:
        return self._identity

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
        generation = 0 if current is None else current["generation"] + 1
        if replacement.get("generation") != generation:
            raise RuntimeError("protected monotonic generation mismatch")
        self.records[key] = copy.deepcopy(dict(replacement))
        return {
            "schema": "kira.protected_monotonic_cas_receipt.v8",
            "protected_backend_identity_sha256": self._identity,
            "namespace": namespace,
            "record_key": record_key,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v8._record_sha(replacement),
            "committed_generation": generation,
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }


def make_ledger():
    accepted = catalog()
    authority = StaticAuthority()
    backend = v9.ProtectedMonotonicBackendV9(authority)
    ledger = v9.ProtectedPresentationReceiptLedgerV9.create(
        session_id=SESSION,
        person_id=PERSON,
        catalog=accepted,
        protected_backend=backend,
    )
    return accepted, authority, backend, ledger


def _segment(
    manifest: dict,
    *,
    sequence: int,
    role: str,
    start_ms: int | None,
    end_ms: int | None,
    receipt_label: str,
) -> dict:
    derivatives = {item["role"]: item for item in manifest["derivatives"]}
    modality = {
        "rendered_page_png": (True, False, False),
        "timed_frame_manifest": (True, False, False),
        "synchronized_audio_pcm": (False, True, False),
        "caption_text_utf8": (True, False, True),
    }[role]
    return {
        "sequence": sequence,
        "page_number": (
            manifest["coordinates"]["page_number"]
            if manifest["media_kind"] == "PAGE"
            else None
        ),
        "track_number": (
            manifest["coordinates"]["track_number"]
            if manifest["media_kind"] == "AUDIO_TRACK"
            else None
        ),
        "source_start_ms": start_ms,
        "source_end_ms": end_ms,
        "output_start_monotonic_ns": 1000 + sequence * 1000,
        "output_end_monotonic_ns": 1500 + sequence * 1000,
        "actual_visual_output": modality[0],
        "actual_audio_output": modality[1],
        "actual_text_output": modality[2],
        "derivative_role": role,
        "derivative_sha256": derivatives[role]["sha256"],
        "renderer_or_decoder_receipt_sha256": sha(receipt_label),
    }


def evidence(
    manifest: dict,
    *,
    ordinal: int,
    output_id: str,
    receipt_prefix: str,
    role_spans: dict[str, tuple[int, int] | None] | None = None,
    declared_complete: bool = True,
) -> dict:
    kind = manifest["media_kind"]
    coords = manifest["coordinates"]
    if role_spans is None:
        if kind == "PAGE":
            role_spans = {"rendered_page_png": None}
        elif kind == "AUDIO_TRACK":
            role_spans = {
                "synchronized_audio_pcm": (coords["start_ms"], coords["end_ms"])
            }
        else:
            role_spans = {
                "timed_frame_manifest": (coords["start_ms"], coords["end_ms"]),
                "synchronized_audio_pcm": (coords["start_ms"], coords["end_ms"]),
                "caption_text_utf8": (coords["start_ms"], coords["end_ms"]),
            }
    segments = []
    for sequence, (role, span) in enumerate(role_spans.items()):
        start, end = (None, None) if span is None else span
        segments.append(
            _segment(
                manifest,
                sequence=sequence,
                role=role,
                start_ms=start,
                end_ms=end,
                receipt_label=f"{receipt_prefix}:{role}:{sequence}",
            )
        )
    return {
        "schema": "kira.resident_media_exact_presentation_evidence.v9",
        "session_id": SESSION,
        "person_id": PERSON,
        "stimulus_id": manifest["stimulus_id"],
        "ordinal": ordinal,
        "source_manifest": copy.deepcopy(manifest),
        "source_manifest_sha256": v8.v4.sha256_record(manifest),
        "consumed_start_permit_sha256": sha(f"permit:{ordinal}"),
        "output_receipt_id": output_id,
        "output_surface_id": "surface_static_v9",
        "presented_at_utc": "2026-08-10T21:00:00.000000Z",
        "presentation_segments": segments,
        "engineering_output_completed": declared_complete,
        "presentation_complete_for_manifest": declared_complete,
        "full_source_experienced": False,
        "person_attention_claimed": False,
        "person_saw_or_heard_claimed": False,
        "automatic_memory_created": False,
        "automatic_preference_created": False,
        "external_parent_observation_sha256": sha(
            f"observation:{output_id}:{receipt_prefix}"
        ),
    }


class ResidentMediaV9Tests(unittest.TestCase):
    def test_page_video_and_audio_require_exact_roles_and_consume_receipts(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        expected_receipts = 0
        for ordinal in (0, 2, 3):
            manifest = accepted.manifest(ordinal)
            item = evidence(
                manifest,
                ordinal=ordinal,
                output_id=f"output_v9_{ordinal}",
                receipt_prefix=f"complete:{ordinal}",
            )
            clean = ledger.validate_and_consume(
                item,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha(f"permit:{ordinal}"),
            )
            self.assertTrue(clean["presentation_complete_for_manifest"])
            self.assertTrue(all(clean["complete_by_required_role"].values()))
            expected_receipts += len(item["presentation_segments"])
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot["used_output_receipt_count"], 3)
        self.assertEqual(
            snapshot["used_renderer_or_decoder_receipt_count"], expected_receipts
        )
        self.assertFalse(snapshot["live_execution_allowed"])

    def test_full_frames_without_audio_or_captions_cannot_be_complete(self) -> None:
        accepted, *_ = make_ledger()
        manifest = accepted.manifest(2)
        coords = manifest["coordinates"]
        item = evidence(
            manifest,
            ordinal=2,
            output_id="frames_only",
            receipt_prefix="frames-only",
            role_spans={
                "timed_frame_manifest": (coords["start_ms"], coords["end_ms"])
            },
            declared_complete=True,
        )
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "per-role coverage"):
            v9.validate_presentation_evidence_v9(
                item,
                session_id=SESSION,
                person_id=PERSON,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:2"),
            )

    def test_disjoint_cross_role_halves_cannot_combine_into_completion(self) -> None:
        accepted, *_ = make_ledger()
        manifest = accepted.manifest(2)
        start = manifest["coordinates"]["start_ms"]
        end = manifest["coordinates"]["end_ms"]
        middle = (start + end) // 2
        item = evidence(
            manifest,
            ordinal=2,
            output_id="disjoint_roles",
            receipt_prefix="disjoint",
            role_spans={
                "timed_frame_manifest": (start, middle),
                "synchronized_audio_pcm": (middle, end),
                "caption_text_utf8": (start, end),
            },
            declared_complete=True,
        )
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "per-role coverage"):
            v9.validate_presentation_evidence_v9(
                item,
                session_id=SESSION,
                person_id=PERSON,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:2"),
            )

    def test_truthful_incomplete_record_is_accepted_but_not_called_experience(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        manifest = accepted.manifest(2)
        coords = manifest["coordinates"]
        item = evidence(
            manifest,
            ordinal=2,
            output_id="truthful_incomplete",
            receipt_prefix="incomplete",
            role_spans={
                "timed_frame_manifest": (coords["start_ms"], coords["end_ms"]),
                "synchronized_audio_pcm": (coords["start_ms"], coords["end_ms"]),
            },
            declared_complete=False,
        )
        clean = ledger.validate_and_consume(
            item,
            expected_manifest=manifest,
            consumed_start_permit_sha256=sha("permit:2"),
        )
        self.assertFalse(clean["presentation_complete_for_manifest"])
        self.assertFalse(clean["full_source_experienced"])

    def test_output_receipt_replay_fails_even_when_wrapper_digest_changes(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        manifest = accepted.manifest(0)
        first = evidence(
            manifest,
            ordinal=0,
            output_id="one_use_output",
            receipt_prefix="first",
        )
        ledger.validate_and_consume(
            first,
            expected_manifest=manifest,
            consumed_start_permit_sha256=sha("permit:0"),
        )
        replay = evidence(
            manifest,
            ordinal=0,
            output_id="one_use_output",
            receipt_prefix="different-receipts",
        )
        replay["external_parent_observation_sha256"] = sha("changed-wrapper-only")
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "output receipt"):
            ledger.validate_and_consume(
                replay,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:0"),
            )

    def test_decoder_receipt_replay_fails_with_new_output_and_wrapper(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        manifest = accepted.manifest(0)
        first = evidence(
            manifest,
            ordinal=0,
            output_id="first_output",
            receipt_prefix="same-decoder",
        )
        ledger.validate_and_consume(
            first,
            expected_manifest=manifest,
            consumed_start_permit_sha256=sha("permit:0"),
        )
        replay = copy.deepcopy(first)
        replay["output_receipt_id"] = "second_output"
        replay["external_parent_observation_sha256"] = sha("second-wrapper")
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "decoder receipt"):
            ledger.validate_and_consume(
                replay,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:0"),
            )

    def test_duplicate_decoder_receipt_inside_one_record_fails(self) -> None:
        accepted, *_ = make_ledger()
        manifest = accepted.manifest(2)
        item = evidence(
            manifest,
            ordinal=2,
            output_id="duplicate_internal",
            receipt_prefix="unique-initially",
        )
        item["presentation_segments"][1]["renderer_or_decoder_receipt_sha256"] = (
            item["presentation_segments"][0]["renderer_or_decoder_receipt_sha256"]
        )
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "reused within evidence"):
            v9.validate_presentation_evidence_v9(
                item,
                session_id=SESSION,
                person_id=PERSON,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:2"),
            )

    def test_wrong_catalog_ordinal_fails_before_receipt_consumption(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        manifest = accepted.manifest(0)
        item = evidence(
            manifest,
            ordinal=1,
            output_id="wrong_ordinal",
            receipt_prefix="wrong-ordinal",
        )
        item["consumed_start_permit_sha256"] = sha("permit:1")
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "catalog ordinal"):
            ledger.validate_and_consume(
                item,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:1"),
            )
        self.assertEqual(ledger.snapshot()["used_output_receipt_count"], 0)

    def test_protected_rollback_fails_closed(self) -> None:
        _accepted, authority, _backend, ledger = make_ledger()
        authority.records.pop(("session_v9", SESSION))
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "changed or rolled back"):
            ledger.snapshot()

    def test_static_contract_stays_disconnected(self) -> None:
        truth = v9.static_contract_summary()
        self.assertTrue(truth["required_role_coverage_is_independent"])
        self.assertTrue(truth["output_receipt_identity_one_use"])
        self.assertFalse(truth["live_execution_allowed"])
        self.assertFalse(truth["live_media_adapter_connected"])


if __name__ == "__main__":
    unittest.main()
