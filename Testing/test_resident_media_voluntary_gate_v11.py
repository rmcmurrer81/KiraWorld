from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v11 as v11
from Testing import test_resident_media_voluntary_gate_v9 as authored
from Testing.test_resident_media_voluntary_gate_v5 import catalog


ROOT = Path(__file__).resolve().parents[1]
PERSON = "person_kira_primary"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def session(label: str) -> str:
    return "session_" + sha("resident-media-v11:" + label)[:32]


def make_ledger(*, accepted: v4.StimulusCatalog | None = None):
    accepted = accepted or catalog()
    authority = v11.issue_controller_owned_static_authority_v11(accepted)
    backend = v11.ProtectedMonotonicBackendV11(authority)
    ledger = v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
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
    value = authored.evidence(
        accepted.manifest(ordinal),
        ordinal=ordinal,
        output_id=output_id,
        receipt_prefix=receipt_prefix,
    )
    value["session_id"] = session_id
    return value


def consume(
    ledger: v11.ProtectedGlobalPresentationReceiptLedgerV11,
    accepted: v4.StimulusCatalog,
    *,
    ordinal: int,
    label: str,
) -> dict:
    sid = session(label)
    value = item_for(
        accepted,
        ordinal=ordinal,
        session_id=sid,
        output_id=f"v11_output_{label}",
        receipt_prefix=f"v11:{label}",
    )
    return ledger.validate_and_consume(
        value,
        session_id=sid,
        expected_manifest=accepted.manifest(ordinal),
        consumed_start_permit_sha256=sha(f"permit:{ordinal}"),
    )


class ResidentMediaV11Tests(unittest.TestCase):
    def test_controller_authorized_page_video_audio_commit_with_exact_roles(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        expected_roles = {
            0: {"rendered_page_png"},
            2: {"timed_frame_manifest", "synchronized_audio_pcm", "caption_text_utf8"},
            3: {"synchronized_audio_pcm"},
        }
        for ordinal in (0, 2, 3):
            clean = consume(ledger, accepted, ordinal=ordinal, label=f"positive-{ordinal}")
            self.assertTrue(clean["presentation_complete_for_manifest"])
            self.assertEqual(set(clean["complete_by_required_role"]), expected_roles[ordinal])
            self.assertTrue(all(clean["complete_by_required_role"].values()))
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot["revision"], 3)
        self.assertEqual(snapshot["presentation_record_count"], 3)
        self.assertTrue(snapshot["controller_owned_authority"])
        self.assertTrue(snapshot["complete_authenticated_history"])
        self.assertFalse(snapshot["live_execution_allowed"])

    def test_authorization_authenticates_full_catalog_derivatives_and_source_time(self) -> None:
        accepted, authority, backend, _ledger = make_ledger()
        authorization = backend.read_catalog_authorization(accepted.sha256)
        self.assertIsNotNone(authorization)
        assert authorization is not None
        self.assertEqual(authorization["catalog_record"], accepted.as_record())
        self.assertEqual(len(authorization["manifest_sha256s"]), 4)
        self.assertEqual(len(authorization["source_time_identity_sha256s"]), 4)
        self.assertEqual(len(authorization["derivative_set_sha256s"]), 4)
        self.assertEqual(
            [len(value) for value in authorization["derivative_identity_sha256s"]],
            [2, 2, 3, 2],
        )
        authority._authorization["derivative_set_sha256s"][0] = sha("forged-set")
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "authorization"):
            backend.read_catalog_authorization(accepted.sha256)

    def test_v10_phantom_authority_and_equality_proxy_are_rejected(self) -> None:
        phantom = authored.StaticAuthority()
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "controller-owned"):
            v11.ProtectedMonotonicBackendV11(phantom)  # type: ignore[arg-type]

        class EqualityProxy:
            def __eq__(self, _other: object) -> bool:
                return True

            backend_identity_sha256 = sha("pretend-controller")
            controller_capability_id = sha("pretend-capability")

        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "controller-owned"):
            v11.ProtectedMonotonicBackendV11(EqualityProxy())  # type: ignore[arg-type]

    def test_controller_capability_cannot_be_subclassed_or_caller_constructed(self) -> None:
        with self.assertRaisesRegex(TypeError, "cannot be subclassed"):
            class Phantom(v11.ControllerProtectedAuthorityCapabilityV11):
                pass

        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "not issued"):
            v11.ControllerProtectedAuthorityCapabilityV11(object(), catalog())

    def test_v10_owner_unselected_derivative_catalog_is_rejected(self) -> None:
        accepted = catalog()
        manifests = copy.deepcopy(accepted.as_record()["manifests"])
        derivative = manifests[0]["derivatives"][0]
        derivative["relative_path"] = "RecoverySprint/forged/owner_unselected.bin"
        derivative["byte_count"] += 1
        derivative["sha256"] = sha("owner-unselected-derivative")
        forged = v4.StimulusCatalog(manifests)
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "owner-selected"):
            v11.issue_controller_owned_static_authority_v11(forged)

    def test_post_issue_caller_and_frozen_catalog_mutation_fail_closed(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        exact_manifest = accepted.manifest(0)
        accepted._manifests[0]["derivatives"][0]["sha256"] = sha("caller-mutated")
        self.assertEqual(ledger.snapshot()["catalog_sha256"], v11.OWNER_SELECTED_CATALOG_SHA256_V11)
        ledger._catalog_record["manifests"][0]["derivatives"][0]["sha256"] = sha(
            "frozen-mutated"
        )
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "catalog"):
            ledger.snapshot()
        self.assertNotEqual(exact_manifest, accepted.manifest(0))

    def test_complete_canonical_evidence_is_retained_and_bound(self) -> None:
        accepted, authority, _backend, ledger = make_ledger()
        clean = consume(ledger, accepted, ordinal=2, label="complete-history")
        stored = authority._records[("global_receipts_v11", PERSON)]
        record = stored["presentation_records"][0]
        self.assertEqual(record["presentation_evidence"], clean)
        self.assertEqual(record["presentation_evidence_sha256"], v11._record_sha(clean))
        self.assertEqual(record["record_revision"], 1)
        self.assertEqual(record["previous_record_sha256"], v11.GENESIS_RECORD_SHA256_V11)
        self.assertRegex(record["controller_record_mac_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(stored["controller_anchor_mac_sha256"], r"^[0-9a-f]{64}$")

    def test_each_v10_history_rewrite_is_rejected_across_reopen(self) -> None:
        accepted, authority, backend, ledger = make_ledger()
        consume(ledger, accepted, ordinal=0, label="rewrite-source")
        key = ("global_receipts_v11", PERSON)
        original = copy.deepcopy(authority._records[key])
        mutations = {
            "presentation evidence digest": lambda value: value["presentation_records"][0].__setitem__(
                "presentation_evidence_sha256", sha("rewritten-evidence")
            ),
            "consumed permit": lambda value: value["presentation_records"][0].__setitem__(
                "consumed_start_permit_sha256", sha("rewritten-permit")
            ),
            "session id": lambda value: value["presentation_records"][0].__setitem__(
                "session_id", session("rewritten-session")
            ),
            "complete evidence": lambda value: value["presentation_records"][0][
                "presentation_evidence"
            ].__setitem__("presented_at_utc", "2026-08-11T00:00:00.000000Z"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                authority._records[key] = copy.deepcopy(original)
                mutate(authority._records[key])
                with self.assertRaisesRegex(v11.ResidentMediaV11Error, "MAC"):
                    v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
                        person_id=PERSON,
                        catalog=accepted,
                        protected_backend=backend,
                    )
        authority._records[key] = original
        self.assertEqual(ledger.snapshot()["revision"], 1)

    def test_record_chain_splice_and_reorder_are_rejected(self) -> None:
        accepted, authority, backend, ledger = make_ledger()
        consume(ledger, accepted, ordinal=0, label="chain-a")
        consume(ledger, accepted, ordinal=3, label="chain-b")
        key = ("global_receipts_v11", PERSON)
        original = copy.deepcopy(authority._records[key])
        for label, records in (
            ("splice", [copy.deepcopy(original["presentation_records"][1])]),
            ("reorder", list(reversed(copy.deepcopy(original["presentation_records"])))),
        ):
            with self.subTest(label=label):
                authority._records[key] = copy.deepcopy(original)
                authority._records[key]["presentation_records"] = records
                with self.assertRaises(v11.ResidentMediaV11Error):
                    v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
                        person_id=PERSON, catalog=accepted, protected_backend=backend
                    )
        authority._records[key] = original

    def test_signed_old_anchor_rollback_is_rejected_across_reopen(self) -> None:
        accepted, authority, backend, ledger = make_ledger()
        consume(ledger, accepted, ordinal=0, label="rollback-a")
        key = ("global_receipts_v11", PERSON)
        signed_revision_one = copy.deepcopy(authority._records[key])
        consume(ledger, accepted, ordinal=3, label="rollback-b")
        authority._records[key] = signed_revision_one
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "rollback"):
            v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
                person_id=PERSON, catalog=accepted, protected_backend=backend
            )

    def test_direct_cas_cannot_obtain_signature_for_history_rewrite(self) -> None:
        accepted, authority, backend, ledger = make_ledger()
        consume(ledger, accepted, ordinal=0, label="direct-cas")
        current = copy.deepcopy(authority._records[("global_receipts_v11", PERSON)])
        replacement = copy.deepcopy(current)
        replacement.pop("controller_anchor_mac_sha256")
        replacement["revision"] += 1
        replacement["generation"] += 1
        replacement["previous_anchor_sha256"] = v11._record_sha(current)
        replacement["presentation_records"][0]["session_id"] = session("direct-rewrite")
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "append-only"):
            backend.compare_and_swap_global_receipt_anchor(
                PERSON, v11._record_sha(current), replacement
            )
        self.assertEqual(ledger.snapshot()["revision"], 1)

    def test_global_output_and_decoder_receipts_are_one_use_across_sessions(self) -> None:
        accepted, _authority, backend, first = make_ledger()
        sid_a = session("replay-a")
        original = item_for(
            accepted,
            ordinal=0,
            session_id=sid_a,
            output_id="v11_global_output",
            receipt_prefix="v11-global-decoder",
        )
        first.validate_and_consume(
            original,
            session_id=sid_a,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        second = v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
            person_id=PERSON, catalog=accepted, protected_backend=backend
        )
        replay = copy.deepcopy(original)
        replay["session_id"] = session("replay-b")
        replay["external_parent_observation_sha256"] = sha("new-wrapper")
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "output receipt"):
            second.validate_and_consume(
                replay,
                session_id=replay["session_id"],
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        replay["output_receipt_id"] = "v11_new_output_same_decoder"
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "decoder receipt"):
            second.validate_and_consume(
                replay,
                session_id=replay["session_id"],
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )

    def test_stale_concurrent_ledger_cannot_overwrite_new_head(self) -> None:
        accepted, authority, backend, first = make_ledger()
        stale = v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
            person_id=PERSON, catalog=accepted, protected_backend=backend
        )
        consume(first, accepted, ordinal=0, label="concurrent-first")
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "changed"):
            consume(stale, accepted, ordinal=3, label="concurrent-stale")
        self.assertEqual(
            authority._records[("global_receipts_v11", PERSON)]["revision"], 1
        )

    def test_zero_person_session_output_receipt_and_digest_sentinels_reject(self) -> None:
        accepted = catalog()
        authority = v11.issue_controller_owned_static_authority_v11(accepted)
        backend = v11.ProtectedMonotonicBackendV11(authority)
        with self.assertRaisesRegex(v11.ResidentMediaV11Error, "zero sentinel"):
            v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
                person_id="0", catalog=accepted, protected_backend=backend
            )

        _accepted, _authority, _backend, ledger = make_ledger()
        base = item_for(
            accepted,
            ordinal=0,
            session_id=session("zero-base"),
            output_id="v11_zero_base_output",
            receipt_prefix="v11-zero-base",
        )
        cases: list[tuple[str, dict, str, str]] = []
        zero_session = copy.deepcopy(base)
        zero_session["session_id"] = "0"
        cases.append(("session", zero_session, "0", sha("permit:0")))
        zero_output = copy.deepcopy(base)
        zero_output["output_receipt_id"] = "0"
        cases.append(("output", zero_output, zero_output["session_id"], sha("permit:0")))
        zero_surface = copy.deepcopy(base)
        zero_surface["output_surface_id"] = "00000000-0000-0000-0000-000000000000"
        cases.append(("surface", zero_surface, zero_surface["session_id"], sha("permit:0")))
        zero_decoder = copy.deepcopy(base)
        zero_decoder["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ] = "0" * 64
        cases.append(("decoder", zero_decoder, zero_decoder["session_id"], sha("permit:0")))
        zero_permit = copy.deepcopy(base)
        zero_permit["consumed_start_permit_sha256"] = "0" * 64
        cases.append(("permit", zero_permit, zero_permit["session_id"], "0" * 64))
        for label, value, sid, permit in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    (v11.ResidentMediaV11Error, v8.ResidentMediaV8Error), "zero"
                ):
                    ledger.validate_and_consume(
                        value,
                        session_id=sid,
                        expected_manifest=accepted.manifest(0),
                        consumed_start_permit_sha256=permit,
                    )
        self.assertEqual(ledger.snapshot()["revision"], 0)

    def test_unknown_fields_role_gaps_and_disjoint_captions_remain_rejected(self) -> None:
        accepted, _authority, _backend, ledger = make_ledger()
        manifest = accepted.manifest(2)
        sid = session("hostile-video")
        value = item_for(
            accepted,
            ordinal=2,
            session_id=sid,
            output_id="v11_hostile_video",
            receipt_prefix="v11-hostile-video",
        )
        value["unknown"] = True
        with self.assertRaises(v8.ResidentMediaV8Error):
            ledger.validate_and_consume(
                value,
                session_id=sid,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:2"),
            )
        disjoint = item_for(
            accepted,
            ordinal=2,
            session_id=sid,
            output_id="v11_disjoint_caption",
            receipt_prefix="v11-disjoint-caption",
        )
        caption = next(
            item
            for item in disjoint["presentation_segments"]
            if item["derivative_role"] == "caption_text_utf8"
        )
        caption["source_end_ms"] = 4000
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "completeness"):
            ledger.validate_and_consume(
                disjoint,
                session_id=sid,
                expected_manifest=manifest,
                consumed_start_permit_sha256=sha("permit:2"),
            )
        self.assertEqual(ledger.snapshot()["revision"], 0)

    def test_static_summary_is_disconnected_and_truthful(self) -> None:
        summary = v11.static_contract_summary()
        self.assertEqual(
            summary["status"],
            "DISCONNECTED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        )
        self.assertTrue(summary["exact_controller_issued_capability_required"])
        self.assertTrue(summary["complete_canonical_presentation_evidence_retained"])
        self.assertTrue(summary["controller_maced_record_chain"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["person_saw_or_heard_claimed"])
        self.assertFalse(summary["person_enjoyed_or_remembered_claimed"])

    def test_v10_seal_and_rejection_audit_are_preserved_exactly(self) -> None:
        expected = {
            "Core/resident_media_voluntary_gate_v10.py": (
                21446,
                "ceaa12999e284cb575bd82a86ece1c88db4cf5000d2f65117d22a68205a791d8",
            ),
            "Testing/test_resident_media_voluntary_gate_v10.py": (
                12668,
                "dfe176526e057fd71989431c97324f74bdf66e3929598654f5ab78e9efeea497",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v10/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V10.json": (
                1969,
                "aec3f775747ebec9e0fa562bb681dadd2266cc7283a2457fe93c2a7d570f2ecc",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v10/attempt_01/CHECKPOINT.md": (
                3203,
                "6dec0a0a68063bc8f8d10ce1c9978adb79a1ab467e9eda6b3e6eff41b2423c4a",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v10_fresh_static_audit/attempt_01/CHECKPOINT.md": (
                5749,
                "456cab5b46e105708a9ddd69823f715c6c0bc5e243573ddb0822059e2a2e3a19",
            ),
        }
        for relative, (size, digest) in expected.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest, relative)


if __name__ == "__main__":
    unittest.main()
