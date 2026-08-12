from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path
from typing import Any, Callable

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v12 as v12
from Core import resident_media_voluntary_gate_v13 as v13
from Testing.test_resident_media_voluntary_gate_v12 import (
    PERSON,
    StaticExternalAuthorityV12,
    canonical,
    catalog,
    decode,
    item_for,
    sha,
)


ROOT = Path(__file__).resolve().parents[1]


def make_harness(
    *,
    accepted: v4.StimulusCatalog | None = None,
    authority: StaticExternalAuthorityV12 | None = None,
) -> tuple[v4.StimulusCatalog, StaticExternalAuthorityV12, Any]:
    accepted = accepted or catalog()
    authority = authority or StaticExternalAuthorityV12(accepted)
    ledger = v13._open_disconnected_static_contract_harness_v13(
        person_id=PERSON,
        external_authority=authority,
    )
    return accepted, authority, ledger


def consume(
    ledger: Any,
    accepted: v4.StimulusCatalog,
    ordinal: int,
    label: str,
    *,
    output_id: str | None = None,
    receipt_prefix: str | None = None,
) -> dict[str, Any]:
    session_id, value = item_for(
        accepted,
        ordinal=ordinal,
        label=label,
        output_id=output_id,
        receipt_prefix=receipt_prefix,
    )
    return ledger.validate_and_record_static_evidence(
        value,
        session_id=session_id,
        expected_manifest=accepted.manifest(ordinal),
        consumed_start_permit_sha256=sha(f"permit:{ordinal}"),
    )


def authority_state(authority: StaticExternalAuthorityV12) -> dict[str, Any]:
    return {
        "anchors": copy.deepcopy(authority._anchors),
        "issue_sequence": authority._issue_sequence,
        "verify_sequence": authority._verify_sequence,
        "prior_receipt_sha256": authority._prior_receipt_sha256,
        "consumed_receipt_ids": set(authority._consumed_receipt_ids),
        "issued_receipts": copy.deepcopy(authority._issued_receipts),
    }


class DescriptorMutatingAuthority(StaticExternalAuthorityV12):
    def __init__(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(catalog())
        self._descriptor_mutate = mutate

    def describe_contract_v12(self) -> bytes:
        value = decode(super().describe_contract_v12())
        self._descriptor_mutate(value)
        return canonical(value)


class SnapshotResponseMutatingAuthority(StaticExternalAuthorityV12):
    def __init__(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(catalog())
        self._response_mutate = mutate

    def read_owner_selected_snapshot_v12(self, request_bytes: bytes) -> bytes:
        value = decode(super().read_owner_selected_snapshot_v12(request_bytes))
        self._response_mutate(value)
        return canonical(value)


class VerificationMutatingAuthority(StaticExternalAuthorityV12):
    def __init__(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(catalog())
        self._verification_mutate = mutate

    def consume_and_verify_receipt_v12(
        self,
        receipt_bytes: bytes,
        expected_context_sha256: str,
    ) -> bytes:
        value = decode(
            super().consume_and_verify_receipt_v12(
                receipt_bytes,
                expected_context_sha256,
            )
        )
        self._verification_mutate(value)
        return canonical(value)


class ExplosiveProxy:
    def __getattribute__(self, name: str) -> Any:
        raise AssertionError(f"production opener inspected caller object:{name}")


class ResidentMediaV13Tests(unittest.TestCase):
    def test_01_public_production_opener_remains_unconditionally_disconnected(self) -> None:
        explosive = ExplosiveProxy()
        for args, kwargs in (
            ((), {}),
            ((explosive,), {}),
            ((), {"catalog": explosive}),
            ((), {"external_authority": explosive}),
            ((), {"issuer_token": explosive}),
        ):
            with self.subTest(args=len(args), kwargs=tuple(kwargs)):
                with self.assertRaisesRegex(
                    v13.ResidentMediaV13Error,
                    "production.*disconnected",
                ):
                    v13.open_production_resident_media_v13(*args, **kwargs)
        status = v13.production_connection_status_v13()
        self.assertEqual(status["status"], "DISCONNECTED_FAIL_CLOSED")
        self.assertFalse(status["production_opener_accepts_caller_authority"])
        self.assertFalse(status["production_opener_accepts_caller_catalog"])
        self.assertFalse(status["live_execution_allowed"])

    def test_02_private_harness_accepts_no_catalog_and_is_not_exported(self) -> None:
        accepted = catalog()
        authority = StaticExternalAuthorityV12(accepted)
        with self.assertRaises(TypeError):
            v13._open_disconnected_static_contract_harness_v13(
                person_id=PERSON,
                external_authority=authority,
                catalog=accepted,
            )
        self.assertNotIn(
            "_open_disconnected_static_contract_harness_v13",
            v13.__all__,
        )

    def test_03_complete_page_video_caption_and_audio_roles_commit(self) -> None:
        accepted, _authority, ledger = make_harness()
        expected = {
            0: {"rendered_page_png"},
            2: {
                "timed_frame_manifest",
                "synchronized_audio_pcm",
                "caption_text_utf8",
            },
            3: {"synchronized_audio_pcm"},
        }
        for ordinal in (0, 2, 3):
            clean = consume(ledger, accepted, ordinal, f"v13-complete-{ordinal}")
            self.assertEqual(set(clean["required_roles"]), expected[ordinal])
            self.assertEqual(set(clean["complete_by_required_role"]), expected[ordinal])
            self.assertTrue(clean["engineering_output_completed"])
            self.assertTrue(clean["presentation_complete_for_manifest"])
            self.assertTrue(all(clean["complete_by_required_role"].values()))
        self.assertEqual(ledger.snapshot()["revision"], 3)

    def test_04_incomplete_video_caption_refuses_without_any_external_change(self) -> None:
        accepted, authority, ledger = make_harness()
        session_id, value = item_for(
            accepted,
            ordinal=2,
            label="v13-incomplete-caption",
        )
        value["presentation_segments"] = [
            row
            for row in value["presentation_segments"]
            if row["derivative_role"] != "caption_text_utf8"
        ]
        value["engineering_output_completed"] = False
        value["presentation_complete_for_manifest"] = False
        before = authority_state(authority)
        with self.assertRaisesRegex(v13.ResidentMediaV13Error, "incomplete"):
            ledger.validate_and_record_static_evidence(
                value,
                session_id=session_id,
                expected_manifest=accepted.manifest(2),
                consumed_start_permit_sha256=sha("permit:2"),
            )
        self.assertEqual(authority_state(authority), before)
        anchor = authority._anchors[PERSON]
        self.assertEqual(anchor["revision"], 0)
        self.assertEqual(anchor["used_output_receipt_ids"], [])
        self.assertEqual(anchor["used_renderer_or_decoder_receipt_sha256s"], [])
        self.assertEqual(anchor["presentation_records"], [])

    def test_05_incomplete_audio_gap_refuses_without_any_external_change(self) -> None:
        accepted, authority, ledger = make_harness()
        session_id, value = item_for(
            accepted,
            ordinal=3,
            label="v13-incomplete-audio",
        )
        value["presentation_segments"][0]["source_end_ms"] -= 1
        value["engineering_output_completed"] = False
        value["presentation_complete_for_manifest"] = False
        before = authority_state(authority)
        with self.assertRaisesRegex(v13.ResidentMediaV13Error, "incomplete"):
            ledger.validate_and_record_static_evidence(
                value,
                session_id=session_id,
                expected_manifest=accepted.manifest(3),
                consumed_start_permit_sha256=sha("permit:3"),
            )
        self.assertEqual(authority_state(authority), before)
        self.assertEqual(authority._anchors[PERSON]["revision"], 0)

    def test_06_snapshot_and_nested_catalog_identifiers_require_exact_strings(self) -> None:
        mutations: dict[str, Callable[[dict[str, Any]], None]] = {
            "snapshot bool": lambda value: value.__setitem__("snapshot_id", True),
            "selection int": lambda value: value.__setitem__(
                "owner_selection_receipt_id", 1
            ),
            "nested derivative bool": lambda value: value["catalog_record"][
                "manifests"
            ][0]["derivatives"][0].__setitem__("derivative_id", True),
            "nested role int": lambda value: value["catalog_record"]["manifests"][
                0
            ]["derivatives"][0].__setitem__("role", 1),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                authority = StaticExternalAuthorityV12(catalog())
                mutate(authority.snapshot_record)
                with self.assertRaises(v13.ResidentMediaV13Error):
                    v13._open_disconnected_static_contract_harness_v13(
                        person_id=PERSON,
                        external_authority=authority,
                    )

    def test_07_descriptor_receipt_and_verification_types_fail_closed(self) -> None:
        authorities = (
            DescriptorMutatingAuthority(
                lambda value: value.__setitem__("authority_instance_id", True)
            ),
            SnapshotResponseMutatingAuthority(
                lambda value: value["authority_receipt"].__setitem__(
                    "receipt_id", True
                )
            ),
            VerificationMutatingAuthority(
                lambda value: value.__setitem__("verification_receipt_id", 1)
            ),
        )
        for authority in authorities:
            with self.subTest(authority=type(authority).__name__):
                with self.assertRaises(v13.ResidentMediaV13Error):
                    v13._open_disconnected_static_contract_harness_v13(
                        person_id=PERSON,
                        external_authority=authority,
                    )

    def test_08_person_session_output_surface_and_manifest_types_refuse_precommit(self) -> None:
        with self.assertRaisesRegex(v13.ResidentMediaV13Error, "person.*string"):
            v13._open_disconnected_static_contract_harness_v13(
                person_id=True,
                external_authority=StaticExternalAuthorityV12(catalog()),
            )

        accepted, authority, ledger = make_harness()
        cases: list[tuple[str, Callable[[dict[str, Any]], None], Any]] = [
            ("session", lambda value: value.__setitem__("session_id", "True"), True),
            (
                "output receipt",
                lambda value: value.__setitem__("output_receipt_id", True),
                None,
            ),
            (
                "output surface",
                lambda value: value.__setitem__("output_surface_id", True),
                None,
            ),
            (
                "stimulus",
                lambda value: value.__setitem__("stimulus_id", True),
                None,
            ),
            (
                "segment role",
                lambda value: value["presentation_segments"][0].__setitem__(
                    "derivative_role", True
                ),
                None,
            ),
        ]
        for label, mutate, session_override in cases:
            with self.subTest(label=label):
                session_id, value = item_for(
                    accepted,
                    ordinal=0,
                    label=f"v13-type-{label.replace(' ', '-')}",
                )
                mutate(value)
                before = authority_state(authority)
                with self.assertRaises(v13.ResidentMediaV13Error):
                    ledger.validate_and_record_static_evidence(
                        value,
                        session_id=(
                            session_override
                            if session_override is not None
                            else session_id
                        ),
                        expected_manifest=accepted.manifest(0),
                        consumed_start_permit_sha256=sha("permit:0"),
                    )
                self.assertEqual(authority_state(authority), before)

        session_id, value = item_for(
            accepted,
            ordinal=0,
            label="v13-nested-manifest-type",
        )
        forged_manifest = copy.deepcopy(accepted.manifest(0))
        forged_manifest["derivatives"][0]["derivative_id"] = True
        before = authority_state(authority)
        with self.assertRaises(v13.ResidentMediaV13Error):
            ledger.validate_and_record_static_evidence(
                value,
                session_id=session_id,
                expected_manifest=forged_manifest,
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(authority_state(authority), before)

    def test_09_sha256_values_require_exact_lowercase_string_types(self) -> None:
        accepted, authority, ledger = make_harness()
        numeric_digest = int("1" * 64)
        cases: list[tuple[str, Callable[[dict[str, Any]], None], Any]] = [
            (
                "numeric decoder",
                lambda value: value["presentation_segments"][0].__setitem__(
                    "renderer_or_decoder_receipt_sha256", numeric_digest
                ),
                sha("permit:0"),
            ),
            (
                "numeric-only decoder string",
                lambda value: value["presentation_segments"][0].__setitem__(
                    "renderer_or_decoder_receipt_sha256", "1" * 64
                ),
                sha("permit:0"),
            ),
            (
                "uppercase decoder",
                lambda value: value["presentation_segments"][0].__setitem__(
                    "renderer_or_decoder_receipt_sha256",
                    sha("uppercase-decoder").upper(),
                ),
                sha("permit:0"),
            ),
            (
                "numeric permit",
                lambda value: None,
                numeric_digest,
            ),
        ]
        for label, mutate, permit in cases:
            with self.subTest(label=label):
                session_id, value = item_for(
                    accepted,
                    ordinal=0,
                    label=f"v13-sha-{label.replace(' ', '-')}",
                )
                mutate(value)
                before = authority_state(authority)
                with self.assertRaises(v13.ResidentMediaV13Error):
                    ledger.validate_and_record_static_evidence(
                        value,
                        session_id=session_id,
                        expected_manifest=accepted.manifest(0),
                        consumed_start_permit_sha256=permit,
                    )
                self.assertEqual(authority_state(authority), before)

    def test_10_nested_snapshot_and_anchor_sha_types_fail_closed(self) -> None:
        numeric_digest = int("1" * 64)
        for label, mutate in (
            (
                "snapshot catalog sha",
                lambda value: value.__setitem__("catalog_sha256", numeric_digest),
            ),
            (
                "nested derivative sha",
                lambda value: value["catalog_record"]["manifests"][0][
                    "derivatives"
                ][0].__setitem__("sha256", numeric_digest),
            ),
        ):
            with self.subTest(label=label):
                authority = StaticExternalAuthorityV12(catalog())
                mutate(authority.snapshot_record)
                with self.assertRaises(v13.ResidentMediaV13Error):
                    v13._open_disconnected_static_contract_harness_v13(
                        person_id=PERSON,
                        external_authority=authority,
                    )

        accepted, authority, ledger = make_harness()
        consume(ledger, accepted, 0, "v13-anchor-type-source")
        authority._anchors[PERSON]["presentation_records"][0][
            "output_receipt_id"
        ] = True
        with self.assertRaises(v13.ResidentMediaV13Error):
            v13._open_disconnected_static_contract_harness_v13(
                person_id=PERSON,
                external_authority=authority,
            )

    def test_11_output_and_decoder_receipts_remain_global_across_reopen(self) -> None:
        accepted, authority, first = make_harness()
        session_id, original = item_for(
            accepted,
            ordinal=0,
            label="v13-global-original",
            output_id="v13_global_output_receipt",
            receipt_prefix="v13-global-decoder",
        )
        first.validate_and_record_static_evidence(
            original,
            session_id=session_id,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        reopened = v13._open_disconnected_static_contract_harness_v13(
            person_id=PERSON,
            external_authority=authority,
        )
        replay_session, replay_output = item_for(
            accepted,
            ordinal=0,
            label="v13-global-output-replay",
            output_id=original["output_receipt_id"],
            receipt_prefix="v13-fresh-decoder",
        )
        with self.assertRaisesRegex(v13.ResidentMediaV13Error, "output receipt"):
            reopened.validate_and_record_static_evidence(
                replay_output,
                session_id=replay_session,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        decoder_session, replay_decoder = item_for(
            accepted,
            ordinal=0,
            label="v13-global-decoder-replay",
            output_id="v13_fresh_output_receipt",
            receipt_prefix="v13-another-decoder",
        )
        replay_decoder["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ] = original["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ]
        with self.assertRaisesRegex(v13.ResidentMediaV13Error, "decoder receipt"):
            reopened.validate_and_record_static_evidence(
                replay_decoder,
                session_id=decoder_session,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(reopened.snapshot()["revision"], 1)

    def test_12_stale_anchor_and_snapshot_mutation_still_fail_closed(self) -> None:
        accepted, authority, first = make_harness()
        stale = v13._open_disconnected_static_contract_harness_v13(
            person_id=PERSON,
            external_authority=authority,
        )
        consume(first, accepted, 0, "v13-stale-first")
        with self.assertRaisesRegex(v13.ResidentMediaV13Error, "changed or rolled back"):
            consume(stale, accepted, 3, "v13-stale-second")

        original = copy.deepcopy(authority.snapshot_record)
        authority.snapshot_record["snapshot_id"] = "changed_snapshot_v13"
        with self.assertRaises(v13.ResidentMediaV13Error):
            first.snapshot()
        authority.snapshot_record = original

    def test_13_scalar_walker_closes_all_nested_identifier_and_digest_locations(self) -> None:
        valid_sha = sha("v13-valid-walker")
        v13._require_exact_string_types(
            {
                "schema": "kira.example.v13",
                "person_id": "person_kira_primary",
                "nested": {
                    "output_receipt_id": "output_v13",
                    "source_sha256": valid_sha,
                    "renderer_or_decoder_receipt_sha256s": [valid_sha],
                },
            },
            "walker control",
        )
        invalid = (
            {"person_id": True},
            {"nested": {"session_id": 1}},
            {"source_sha256": int("1" * 64)},
            {"source_sha256": valid_sha.upper()},
            {"renderer_or_decoder_receipt_sha256": "1" * 64},
            {"used_output_receipt_ids": ["valid", True]},
            {"derivative_identity_sha256s": [[valid_sha, 1]]},
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(v13.ResidentMediaV13Error):
                    v13._require_exact_string_types(value, "walker hostile")

    def test_14_v12_seal_and_rejection_package_remain_exact(self) -> None:
        expected = {
            "Core/resident_media_voluntary_gate_v12.py": (
                50849,
                "2cc9e588affde3c0dd1e127baef31fd2183cc2d188d61afdf2899df06bd6bf5c",
            ),
            "Testing/test_resident_media_voluntary_gate_v12.py": (
                32717,
                "9e9441564eaf6415b19c100b678430f425b0b29003a003b2954af093693291b8",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/STATIC_TEST_RESULTS.md": (
                2127,
                "e3d87c7e09384582145d69d955f3b9f5c525264b02344aca22b02fb4bfec5542",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V12.json": (
                3600,
                "362a9a833d324ab53b8eebf90cc4a05308fde2ff3e70fbd989c6ec8ad14f81f8",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/SEALED_MANIFEST.json": (
                1411,
                "7c6d2da7319e163dc0e2a1be0be1af06bbbfe89173f5a8b5f21e93e2a94e2a66",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12_fresh_static_audit/attempt_01/CHECKPOINT.md": (
                6289,
                "cdafe2169a6580b2586366bc2c6e0774f5f802f30ee76be0573d4dd89b54eb30",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12_fresh_static_audit/attempt_01/AUDIT_DECISION.json": (
                4546,
                "26c26d2d119e802e7333f6088ec610987a51a096c7b31beb894c094ccdbbb239",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12_fresh_static_audit/attempt_01/HASH_VERIFICATION.md": (
                1730,
                "536b662d9a883c336df4304413623ff3b3b405e8901210128f4a74642bec554b",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12_fresh_static_audit/attempt_01/TEST_RESULTS.md": (
                3224,
                "21e1b5b1bafc07f73657f5f9d078f36a37d60778537649d8db9f89dd5c2c1c34",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v12_fresh_static_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py": (
                27281,
                "9bf904044295ca1aa796f17f891f4f58cd73a50cee16df6bddeabf9804c9306a",
            ),
        }
        for relative, (size, digest) in expected.items():
            path = ROOT / relative
            with self.subTest(path=relative):
                data = path.read_bytes()
                self.assertEqual(len(data), size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)

    def test_15_summary_and_import_surface_are_static_only(self) -> None:
        summary = v13.static_contract_summary()
        self.assertEqual(
            summary["status"],
            "SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        )
        self.assertTrue(summary["v12_rejection_preserved"])
        self.assertTrue(summary["external_authority_contract_retained"])
        self.assertTrue(summary["consent_privacy_and_choice_predecessor_gates_retained"])
        self.assertTrue(summary["identifier_and_sha256_exact_string_types_required"])
        self.assertTrue(summary["numeric_only_decoder_sha256_refused"])
        self.assertTrue(summary["all_authoritative_required_roles_complete_before_commit"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["person_saw_or_heard_claimed"])
        self.assertFalse(summary["person_enjoyed_learned_or_remembered_claimed"])
        names = set(vars(v13))
        for forbidden in (
            "_CONTROLLER_ISSUER_TOKEN",
            "_CONTROLLER_ISSUER_KEY",
            "OWNER_SELECTED_CATALOG_SHA256_V13",
            "OWNER_SELECTION_RECEIPT_SHA256_V13",
            "issue_controller_owned_static_authority_v13",
        ):
            self.assertNotIn(forbidden, names)
        heavy = {
            name
            for name in sys.modules
            if name == "torch"
            or name.startswith("torch.")
            or name == "ollama"
            or name.startswith("ollama.")
            or name == "chatterbox"
            or name.startswith("chatterbox.")
            or name == "bpy"
        }
        self.assertEqual(heavy, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
