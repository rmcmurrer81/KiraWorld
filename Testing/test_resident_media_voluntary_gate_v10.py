from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v5 as v5
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v10 as v10
from Testing import test_resident_media_voluntary_gate_v9 as authored
from Testing.test_resident_media_voluntary_gate_v5 import catalog


ROOT = Path(__file__).resolve().parents[1]
PERSON = "person_kira_primary"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def session(label: str) -> str:
    return "session_" + sha("resident-media-v10:" + label)[:32]


def authorize_catalog(authority: authored.StaticAuthority, accepted: v4.StimulusCatalog) -> None:
    authority.records[("catalog_v5", accepted.sha256)] = {
        "schema": "kira.resident_media_catalog_authorization.v5",
        "catalog_sha256": accepted.sha256,
        "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
        "status": "AUTHORIZED_FOR_STATIC_GATE_ONLY",
        "protected_backend_identity_sha256": authority.backend_identity_sha256,
    }


def make_ledger(
    *,
    accepted: v4.StimulusCatalog | None = None,
    authority: authored.StaticAuthority | None = None,
    authorize: bool = True,
):
    accepted = accepted or catalog()
    authority = authority or authored.StaticAuthority()
    if authorize:
        authorize_catalog(authority, accepted)
    backend = v10.ProtectedMonotonicBackendV10(authority)
    ledger = v10.ProtectedGlobalPresentationReceiptLedgerV10.open(
        person_id=PERSON,
        catalog=accepted,
        protected_backend=backend,
    )
    return accepted, authority, backend, ledger


def item_for(
    accepted: v4.StimulusCatalog,
    *,
    ordinal: int,
    session_id: str,
    output_id: str,
    receipt_prefix: str,
) -> dict:
    manifest = accepted.manifest(ordinal)
    value = authored.evidence(
        manifest,
        ordinal=ordinal,
        output_id=output_id,
        receipt_prefix=receipt_prefix,
    )
    value["session_id"] = session_id
    return value


def forged_catalog_from(accepted: v4.StimulusCatalog) -> v4.StimulusCatalog:
    manifests = copy.deepcopy(accepted.as_record()["manifests"])
    forged = manifests[0]
    source_sha = sha("v10-owner-unselected-source")
    forged["opaque_media_id"] = sha("v10-owner-unselected-media")
    forged["source_relative_path"] = "Data/library/unauthorized/v10_forged.pdf"
    forged["source_byte_count"] = 4321
    forged["source_sha256"] = source_sha
    for index, derivative in enumerate(forged["derivatives"]):
        derivative["relative_path"] = (
            f"Data/runtime/unauthorized/v10_forged_{index}.png"
        )
        derivative["byte_count"] = 200 + index
        derivative["sha256"] = sha(f"v10-forged-derivative:{index}")
        derivative["derived_from_source_sha256"] = source_sha
    return v4.StimulusCatalog(manifests)


class ResidentMediaV10Tests(unittest.TestCase):
    def test_authorized_catalog_and_per_role_evidence_commit_globally(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        for ordinal in (0, 2, 3):
            sid = session(f"positive-{ordinal}")
            value = item_for(
                accepted,
                ordinal=ordinal,
                session_id=sid,
                output_id=f"v10_output_{ordinal}",
                receipt_prefix=f"v10-positive:{ordinal}",
            )
            clean = ledger.validate_and_consume(
                value,
                session_id=sid,
                expected_manifest=accepted.manifest(ordinal),
                consumed_start_permit_sha256=sha(f"permit:{ordinal}"),
            )
            self.assertTrue(clean["presentation_complete_for_manifest"])
            self.assertTrue(all(clean["complete_by_required_role"].values()))
        state = ledger.snapshot()
        self.assertEqual(state["used_output_receipt_count"], 3)
        self.assertEqual(state["presentation_record_count"], 3)
        self.assertTrue(state["global_across_sessions"])
        self.assertTrue(state["catalog_authorized_by_protected_backend"])
        self.assertFalse(state["live_execution_allowed"])

    def test_cross_session_output_and_decoder_replay_is_rejected(self) -> None:
        accepted, authority, backend, first = make_ledger()
        sid_a = session("cross-a")
        original = item_for(
            accepted,
            ordinal=0,
            session_id=sid_a,
            output_id="globally_replayed_output",
            receipt_prefix="globally-replayed-decoder",
        )
        first.validate_and_consume(
            original,
            session_id=sid_a,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )

        second = v10.ProtectedGlobalPresentationReceiptLedgerV10.open(
            person_id=PERSON,
            catalog=accepted,
            protected_backend=backend,
        )
        sid_b = session("cross-b")
        replay = copy.deepcopy(original)
        replay["session_id"] = sid_b
        replay["external_parent_observation_sha256"] = sha("changed-wrapper")
        with self.assertRaisesRegex(v10.ResidentMediaV10Error, "globally"):
            second.validate_and_consume(
                replay,
                session_id=sid_b,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(
            authority.records[("global_receipts_v10", PERSON)]["generation"], 1
        )

    def test_missing_protected_catalog_authorization_is_rejected(self) -> None:
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "pre-authorized"):
            make_ledger(authorize=False)

    def test_owner_unselected_catalog_is_rejected_even_if_caller_authorizes_digest(self) -> None:
        forged = forged_catalog_from(catalog())
        authority = authored.StaticAuthority()
        authorize_catalog(authority, forged)
        with self.assertRaisesRegex(v5.ResidentMediaV5Error, "authoritative source"):
            make_ledger(accepted=forged, authority=authority, authorize=False)

    def test_post_anchor_caller_catalog_mutation_cannot_change_source(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        original_manifest = accepted.manifest(0)
        internal = accepted._manifests[0]
        internal["source_relative_path"] = (
            "Data/library/unauthorized/post_anchor_mutated_source.pdf"
        )
        internal["source_sha256"] = sha("mutated-source")
        mutated_manifest = accepted.manifest(0)
        sid = session("caller-mutation")
        mutated = authored.evidence(
            mutated_manifest,
            ordinal=0,
            output_id="mutated_catalog_output",
            receipt_prefix="mutated-catalog",
        )
        mutated["session_id"] = sid
        with self.assertRaisesRegex(
            (v9.ResidentMediaV9Error, v10.ResidentMediaV10Error),
            "manifest|authoritative",
        ):
            ledger.validate_and_consume(
                mutated,
                session_id=sid,
                expected_manifest=mutated_manifest,
                consumed_start_permit_sha256=sha("permit:0"),
            )

        # The ledger retained only its exact authorized canonical snapshot.
        clean_original = authored.evidence(
            original_manifest,
            ordinal=0,
            output_id="original_snapshot_output",
            receipt_prefix="original-snapshot",
        )
        clean_original["session_id"] = sid
        accepted_clean = ledger.validate_and_consume(
            clean_original,
            session_id=sid,
            expected_manifest=original_manifest,
            consumed_start_permit_sha256=sha("permit:0"),
        )
        self.assertEqual(
            accepted_clean["source_manifest"]["source_relative_path"],
            original_manifest["source_relative_path"],
        )

    def test_mutating_frozen_internal_catalog_record_fails_closed(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        ledger._catalog_record["manifests"][0]["source_sha256"] = sha("tampered")
        with self.assertRaisesRegex(v10.ResidentMediaV10Error, "catalog"):
            ledger.snapshot()

    def test_global_anchor_rollback_or_removal_is_detected(self) -> None:
        _accepted, authority, _backend, ledger = make_ledger()
        authority.records.pop(("global_receipts_v10", PERSON))
        with self.assertRaisesRegex(v10.ResidentMediaV10Error, "rolled back"):
            ledger.snapshot()

    def test_reopened_anchor_requires_receipt_lists_to_match_exact_history(self) -> None:
        accepted, authority, _backend, ledger = make_ledger()
        sid = session("history-consistency")
        value = item_for(
            accepted,
            ordinal=0,
            session_id=sid,
            output_id="v10_history_output",
            receipt_prefix="v10-history",
        )
        ledger.validate_and_consume(
            value,
            session_id=sid,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        stored = authority.records[("global_receipts_v10", PERSON)]
        stored["presentation_records"] = []
        with self.assertRaisesRegex(v10.ResidentMediaV10Error, "history"):
            v10.ProtectedGlobalPresentationReceiptLedgerV10.open(
                person_id=PERSON,
                catalog=accepted,
                protected_backend=v10.ProtectedMonotonicBackendV10(authority),
            )

    def test_v9_role_gap_and_caption_rejections_remain_exact(self) -> None:
        accepted, *_ = make_ledger()
        manifest = accepted.manifest(2)
        coords = manifest["coordinates"]
        frames_only = authored.evidence(
            manifest,
            ordinal=2,
            output_id="v10_frames_only",
            receipt_prefix="v10-frames-only",
            role_spans={
                "timed_frame_manifest": (coords["start_ms"], coords["end_ms"])
            },
        )
        sid = session("frames-only")
        frames_only["session_id"] = sid
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "per-role coverage"):
            v9.validate_presentation_evidence_v9(
                frames_only,
                session_id=sid,
                person_id=PERSON,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:2"),
            )

    def test_static_summary_is_disconnected_and_truthful(self) -> None:
        summary = v10.static_contract_summary()
        self.assertEqual(
            summary["status"], "DISCONNECTED_STATIC_CANDIDATE_PENDING_FRESH_AUDIT"
        )
        self.assertTrue(summary["exact_v5_owner_selected_catalog_required"])
        self.assertTrue(summary["global_cross_session_output_receipt_one_use"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["person_saw_or_heard_claimed"])
        self.assertFalse(summary["person_enjoyed_or_remembered_claimed"])

    def test_v9_and_rejection_evidence_are_preserved(self) -> None:
        expected = {
            "Core/resident_media_voluntary_gate_v9.py": (
                24763,
                "eaf4b46cb37cc9b76bbe45b76407c6be569c7078a72854c5243ea08fdea8934e",
            ),
            "Testing/test_resident_media_voluntary_gate_v9.py": (
                14685,
                "9bb510b707b66194a7a31c676a09d087b675879d322c14c37fe4e39dffc97066",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v9/attempt_01/CHECKPOINT.md": (
                3235,
                "feb85185d90efcbefab509dd3e85958441787a32e6591e734e8d437945439614",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v9_fresh_static_audit/attempt_01/CHECKPOINT.md": (
                11245,
                "5a280dcd480bc987c6a36ca35c309467d46e1aae9603010a224c6688341ea72c",
            ),
        }
        for relative, (size, digest) in expected.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), digest, relative
            )


if __name__ == "__main__":
    unittest.main()
