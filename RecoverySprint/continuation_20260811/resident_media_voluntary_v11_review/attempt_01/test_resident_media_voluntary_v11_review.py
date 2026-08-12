from __future__ import annotations

import copy
import unittest

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v11 as v11
from Testing.test_resident_media_voluntary_gate_v5 import catalog
from Testing import test_resident_media_voluntary_gate_v11 as authored


PERSON = "person_kira_primary"


class ResidentMediaV11FreshReviewTests(unittest.TestCase):
    def make_item(
        self,
        accepted: v4.StimulusCatalog,
        *,
        ordinal: int,
        label: str,
        output_id: str | None = None,
        receipt_prefix: str | None = None,
    ) -> tuple[str, dict]:
        sid = authored.session(label)
        return sid, authored.item_for(
            accepted,
            ordinal=ordinal,
            session_id=sid,
            output_id=output_id or f"review_output_{label}",
            receipt_prefix=receipt_prefix or f"review:{label}",
        )

    def consume(
        self,
        ledger: v11.ProtectedGlobalPresentationReceiptLedgerV11,
        accepted: v4.StimulusCatalog,
        *,
        ordinal: int,
        label: str,
        value: dict | None = None,
        session_id: str | None = None,
    ) -> dict:
        if value is None:
            session_id, value = self.make_item(
                accepted, ordinal=ordinal, label=label
            )
        assert session_id is not None
        return ledger.validate_and_consume(
            value,
            session_id=session_id,
            expected_manifest=accepted.manifest(ordinal),
            consumed_start_permit_sha256=authored.sha(f"permit:{ordinal}"),
        )

    def test_refusal_text_is_specific_for_representative_failures(self) -> None:
        accepted = catalog()
        authority = v11.issue_controller_owned_static_authority_v11(accepted)
        backend = v11.ProtectedMonotonicBackendV11(authority)
        with self.assertRaisesRegex(
            v11.ResidentMediaV11Error,
            r"^person id cannot be a zero sentinel$",
        ):
            v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
                person_id="0", catalog=accepted, protected_backend=backend
            )

        changed = copy.deepcopy(accepted.as_record()["manifests"])
        changed[0]["derivatives"][0]["byte_count"] += 1
        with self.assertRaisesRegex(
            v11.ResidentMediaV11Error,
            r"^catalog is not the exact owner-selected V11 catalog$",
        ):
            v11.issue_controller_owned_static_authority_v11(
                v4.StimulusCatalog(changed)
            )

        _accepted, _authority, _backend, ledger = authored.make_ledger()
        sid, evidence = self.make_item(
            accepted, ordinal=2, label="refusal-duplicate"
        )
        evidence["presentation_segments"][1][
            "renderer_or_decoder_receipt_sha256"
        ] = evidence["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ]
        with self.assertRaisesRegex(
            v9.ResidentMediaV9Error,
            r"^renderer/decoder receipt is reused within evidence$",
        ):
            self.consume(
                ledger,
                accepted,
                ordinal=2,
                label="refusal-duplicate",
                value=evidence,
                session_id=sid,
            )

    def test_required_video_audio_and_caption_roles_refuse_partial_coverage(self) -> None:
        for ordinal, roles in (
            (
                2,
                (
                    "timed_frame_manifest",
                    "synchronized_audio_pcm",
                    "caption_text_utf8",
                ),
            ),
            (3, ("synchronized_audio_pcm",)),
        ):
            for role in roles:
                with self.subTest(ordinal=ordinal, role=role):
                    accepted, _authority, _backend, ledger = authored.make_ledger()
                    label = f"partial-{ordinal}-{role}"
                    sid, evidence = self.make_item(
                        accepted, ordinal=ordinal, label=label
                    )
                    segment = next(
                        item
                        for item in evidence["presentation_segments"]
                        if item["derivative_role"] == role
                    )
                    segment["source_end_ms"] -= 1
                    with self.assertRaisesRegex(
                        v9.ResidentMediaV9Error,
                        r"^declared completeness differs from per-role coverage$",
                    ):
                        self.consume(
                            ledger,
                            accepted,
                            ordinal=ordinal,
                            label=label,
                            value=evidence,
                            session_id=sid,
                        )
                    self.assertEqual(ledger.snapshot()["revision"], 0)

    def test_duplicate_output_and_decoder_receipt_ids_refuse_without_commit(self) -> None:
        accepted, _authority, backend, first = authored.make_ledger()
        sid, original = self.make_item(
            accepted,
            ordinal=0,
            label="receipt-original",
            output_id="review_duplicate_output",
            receipt_prefix="review-duplicate-decoder",
        )
        self.consume(
            first,
            accepted,
            ordinal=0,
            label="receipt-original",
            value=original,
            session_id=sid,
        )
        restored = v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
            person_id=PERSON,
            catalog=accepted,
            protected_backend=backend,
        )

        sid2, duplicate_output = self.make_item(
            accepted,
            ordinal=0,
            label="receipt-output-replay",
            output_id=original["output_receipt_id"],
            receipt_prefix="review-new-decoder",
        )
        with self.assertRaisesRegex(
            v11.ResidentMediaV11Error,
            r"^output receipt was already consumed globally$",
        ):
            self.consume(
                restored,
                accepted,
                ordinal=0,
                label="receipt-output-replay",
                value=duplicate_output,
                session_id=sid2,
            )

        sid3, duplicate_decoder = self.make_item(
            accepted,
            ordinal=0,
            label="receipt-decoder-replay",
            output_id="review_fresh_output",
            receipt_prefix="review-another-decoder",
        )
        duplicate_decoder["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ] = original["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ]
        with self.assertRaisesRegex(
            v11.ResidentMediaV11Error,
            r"^renderer/decoder receipt was already consumed globally$",
        ):
            self.consume(
                restored,
                accepted,
                ordinal=0,
                label="receipt-decoder-replay",
                value=duplicate_decoder,
                session_id=sid3,
            )
        self.assertEqual(restored.snapshot()["revision"], 1)

    def test_empty_identity_evidence_and_segment_fields_refuse(self) -> None:
        accepted = catalog()
        authority = v11.issue_controller_owned_static_authority_v11(accepted)
        backend = v11.ProtectedMonotonicBackendV11(authority)
        with self.assertRaisesRegex(
            v8.ResidentMediaV8Error,
            r"^person id is not a canonical identifier$",
        ):
            v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
                person_id="", catalog=accepted, protected_backend=backend
            )

        _accepted, _authority, _backend, ledger = authored.make_ledger()
        base_sid, base = self.make_item(
            accepted, ordinal=0, label="empty-base"
        )
        cases: list[tuple[str, dict, str, str]] = []

        empty_session = copy.deepcopy(base)
        empty_session["session_id"] = ""
        cases.append(("session", empty_session, "", "canonical identifier"))

        empty_output = copy.deepcopy(base)
        empty_output["output_receipt_id"] = ""
        cases.append(("output", empty_output, base_sid, "canonical identifier"))

        empty_surface = copy.deepcopy(base)
        empty_surface["output_surface_id"] = ""
        cases.append(("surface", empty_surface, base_sid, "canonical identifier"))

        empty_receipt = copy.deepcopy(base)
        empty_receipt["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ] = ""
        cases.append(("decoder receipt", empty_receipt, base_sid, "must be SHA-256"))

        empty_segments = copy.deepcopy(base)
        empty_segments["presentation_segments"] = []
        cases.append(("segments", empty_segments, base_sid, "segments are missing"))

        for label, value, sid, refusal in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    (v8.ResidentMediaV8Error, v9.ResidentMediaV9Error), refusal
                ):
                    self.consume(
                        ledger,
                        accepted,
                        ordinal=0,
                        label=f"empty-{label}",
                        value=value,
                        session_id=sid,
                    )
        self.assertEqual(ledger.snapshot()["revision"], 0)

    def test_each_changed_catalog_data_category_refuses(self) -> None:
        accepted = catalog()

        def change_source_path(manifests: list[dict]) -> None:
            manifests[0]["source_relative_path"] += ".changed"

        def change_source_bytes(manifests: list[dict]) -> None:
            manifests[0]["source_byte_count"] += 1

        def change_source_digest(manifests: list[dict]) -> None:
            changed_digest = authored.sha("changed-source")
            manifests[0]["source_sha256"] = changed_digest
            for derivative in manifests[0]["derivatives"]:
                derivative["derived_from_source_sha256"] = changed_digest

        def change_source_coordinate(manifests: list[dict]) -> None:
            manifests[0]["coordinates"]["page_number"] += 1

        def change_derivative_path(manifests: list[dict]) -> None:
            manifests[0]["derivatives"][0]["relative_path"] += ".changed"

        def change_derivative_bytes(manifests: list[dict]) -> None:
            manifests[0]["derivatives"][0]["byte_count"] += 1

        def change_derivative_digest(manifests: list[dict]) -> None:
            manifests[0]["derivatives"][0]["sha256"] = authored.sha(
                "changed-derivative"
            )

        mutations = {
            "source path": change_source_path,
            "source bytes": change_source_bytes,
            "source digest": change_source_digest,
            "source coordinate": change_source_coordinate,
            "derivative path": change_derivative_path,
            "derivative bytes": change_derivative_bytes,
            "derivative digest": change_derivative_digest,
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                manifests = copy.deepcopy(accepted.as_record()["manifests"])
                mutate(manifests)
                changed = v4.StimulusCatalog(manifests)
                with self.assertRaisesRegex(
                    v11.ResidentMediaV11Error,
                    r"^catalog is not the exact owner-selected V11 catalog$",
                ):
                    v11.issue_controller_owned_static_authority_v11(changed)

    def test_journal_restore_is_consistent_before_and_after_append(self) -> None:
        accepted, authority, backend, ledger = authored.make_ledger()
        for ordinal, label in ((0, "restore-page"), (2, "restore-video"), (3, "restore-audio")):
            self.consume(ledger, accepted, ordinal=ordinal, label=label)
        before = ledger.snapshot()
        stored_before = copy.deepcopy(
            authority._records[("global_receipts_v11", PERSON)]
        )

        restored = v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
            person_id=PERSON,
            catalog=accepted,
            protected_backend=backend,
        )
        self.assertEqual(restored.snapshot(), before)
        self.assertEqual(
            authority._records[("global_receipts_v11", PERSON)], stored_before
        )
        self.assertEqual(before["revision"], 3)
        self.assertEqual(before["presentation_record_count"], 3)

        self.consume(restored, accepted, ordinal=0, label="restore-append")
        after = restored.snapshot()
        reopened_again = v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
            person_id=PERSON,
            catalog=accepted,
            protected_backend=backend,
        )
        self.assertEqual(reopened_again.snapshot(), after)
        self.assertEqual(after["revision"], 4)
        self.assertEqual(after["presentation_record_count"], 4)
        self.assertEqual(after["used_output_receipt_count"], 4)
        self.assertEqual(after["used_renderer_or_decoder_receipt_count"], 6)

    def test_changed_catalog_cannot_be_accepted_after_rebinding_final_constants(self) -> None:
        accepted = catalog()
        manifests = copy.deepcopy(accepted.as_record()["manifests"])
        manifests[0]["derivatives"][0]["relative_path"] += ".caller-selected"
        manifests[0]["derivatives"][0]["byte_count"] += 1
        manifests[0]["derivatives"][0]["sha256"] = authored.sha(
            "caller-selected-derivative"
        )
        changed = v4.StimulusCatalog(manifests)
        original_catalog_sha = v11.OWNER_SELECTED_CATALOG_SHA256_V11
        original_selection_receipt = v11.OWNER_SELECTION_RECEIPT_SHA256_V11
        try:
            v11.OWNER_SELECTED_CATALOG_SHA256_V11 = changed.sha256
            v11.OWNER_SELECTION_RECEIPT_SHA256_V11 = authored.hashlib.sha256(
                b"kira.resident_media.owner_selected_catalog.v11:"
                + changed.sha256.encode("ascii")
            ).hexdigest()
            with self.assertRaisesRegex(
                v11.ResidentMediaV11Error,
                r"catalog is not the exact owner-selected V11 catalog",
            ):
                v11.issue_controller_owned_static_authority_v11(changed)
        finally:
            v11.OWNER_SELECTED_CATALOG_SHA256_V11 = original_catalog_sha
            v11.OWNER_SELECTION_RECEIPT_SHA256_V11 = original_selection_receipt

    def test_caller_cannot_construct_capability_with_reserved_module_token(self) -> None:
        with self.assertRaisesRegex(
            v11.ResidentMediaV11Error, r"controller authority was not issued by V11"
        ):
            caller_constructed = v11.ControllerProtectedAuthorityCapabilityV11(
                v11._CONTROLLER_ISSUER_TOKEN,
                catalog(),
            )
            v11.ProtectedMonotonicBackendV11(caller_constructed)

    def test_caller_cannot_resign_rewritten_journal_and_floor(self) -> None:
        accepted, authority, backend, ledger = authored.make_ledger()
        self.consume(ledger, accepted, ordinal=0, label="forge-original")
        key = ("global_receipts_v11", PERSON)
        rewritten = copy.deepcopy(authority._records[key])
        record = rewritten["presentation_records"][0]
        forged_session = authored.session("forge-rewritten")
        record["session_id"] = forged_session
        record["presentation_evidence"]["session_id"] = forged_session
        record["presentation_evidence_sha256"] = v11._record_sha(
            record["presentation_evidence"]
        )
        record_core = {
            name: value
            for name, value in record.items()
            if name not in {"record_sha256", "controller_record_mac_sha256"}
        }
        record["record_sha256"] = v11._record_sha(record_core)
        record_mac_core = {
            name: value
            for name, value in record.items()
            if name != "controller_record_mac_sha256"
        }
        record["controller_record_mac_sha256"] = authority._mac(
            "presentation_record", record_mac_core
        )
        rewritten["chain_head_sha256"] = record["record_sha256"]
        anchor_core = {
            name: value
            for name, value in rewritten.items()
            if name != "controller_anchor_mac_sha256"
        }
        rewritten["controller_anchor_mac_sha256"] = authority._mac(
            "global_anchor", anchor_core
        )
        authority._records[key] = rewritten
        authority._monotonic_floor[key] = {
            "revision": rewritten["revision"],
            "generation": rewritten["generation"],
            "chain_head_sha256": rewritten["chain_head_sha256"],
            "signed_anchor_sha256": v11._record_sha(rewritten),
        }

        with self.assertRaises(v11.ResidentMediaV11Error):
            v11.ProtectedGlobalPresentationReceiptLedgerV11.open(
                person_id=PERSON,
                catalog=accepted,
                protected_backend=backend,
            )


if __name__ == "__main__":
    unittest.main()
