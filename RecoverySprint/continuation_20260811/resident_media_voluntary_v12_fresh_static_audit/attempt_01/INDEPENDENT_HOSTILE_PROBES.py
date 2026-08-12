from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v12 as v12
from Testing.test_resident_media_voluntary_gate_v12 import (
    PERSON,
    StaticExternalAuthorityV12,
    canonical,
    catalog,
    consume,
    decode,
    item_for,
    make_harness,
    sha,
)

V12_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "resident_media_voluntary_v12"
    / "attempt_01"
)
SEAL_PATH = V12_ROOT / "SEALED_MANIFEST.json"
SEAL_BYTES = 1411
SEAL_SHA256 = "7c6d2da7319e163dc0e2a1be0be1af06bbbfe89173f5a8b5f21e93e2a94e2a66"


def digest(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


class ResponseMutatingAuthority(StaticExternalAuthorityV12):
    def __init__(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(catalog())
        self._mutate = mutate

    def read_owner_selected_snapshot_v12(self, request_bytes: bytes) -> bytes:
        response = decode(super().read_owner_selected_snapshot_v12(request_bytes))
        self._mutate(response)
        return canonical(response)


class VerificationMutatingAuthority(StaticExternalAuthorityV12):
    def __init__(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(catalog())
        self._mutate = mutate

    def consume_and_verify_receipt_v12(
        self, receipt_bytes: bytes, expected_context_sha256: str
    ) -> bytes:
        verification = decode(
            super().consume_and_verify_receipt_v12(
                receipt_bytes, expected_context_sha256
            )
        )
        self._mutate(verification)
        return canonical(verification)


class ExplosiveProxy:
    def __getattribute__(self, name: str) -> Any:
        raise AssertionError(f"production opener inspected caller object:{name}")


class ResidentMediaV12FreshHostileAudit(unittest.TestCase):
    def test_01_exact_v12_seal_and_subject_closure(self) -> None:
        self.assertEqual(digest(SEAL_PATH), (SEAL_BYTES, SEAL_SHA256))
        seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            seal["status"],
            "SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        )
        self.assertEqual(len(seal["subjects"]), 4)
        for row in seal["subjects"]:
            self.assertEqual(
                digest(ROOT / row["path"]),
                (row["bytes"], row["sha256"]),
                row["path"],
            )
        predecessor = seal["predecessor_rejection_preserved"]
        self.assertEqual(
            digest(ROOT / predecessor["path"]),
            (predecessor["bytes"], predecessor["sha256"]),
        )
        self.assertEqual(seal["live_authorization"], "NONE")
        self.assertFalse(seal["production_pointer_changed"])

    def test_02_v10_v11_and_rejection_evidence_remain_exact(self) -> None:
        expected = {
            "Core/resident_media_voluntary_gate_v10.py": (
                21446,
                "ceaa12999e284cb575bd82a86ece1c88db4cf5000d2f65117d22a68205a791d8",
            ),
            "Testing/test_resident_media_voluntary_gate_v10.py": (
                12668,
                "dfe176526e057fd71989431c97324f74bdf66e3929598654f5ab78e9efeea497",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v10_fresh_static_audit/attempt_01/CHECKPOINT.md": (
                5749,
                "456cab5b46e105708a9ddd69823f715c6c0bc5e243573ddb0822059e2a2e3a19",
            ),
            "Core/resident_media_voluntary_gate_v11.py": (
                48475,
                "64e5edf62fce5002434a0af6165c1e58ab6d407a414d3750cd9cf66835fe1671",
            ),
            "Testing/test_resident_media_voluntary_gate_v11.py": (
                20165,
                "4e60c575021a7b0f9ce7dcff6e7a9a5ef20b757f0959f032131ae9e5276e859b",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v11/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V11.json": (
                2577,
                "5dc3c4f2a8044fa0e7cecf0c2588d018a0885dba046d517bea3ade90f33eda37",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v11/attempt_01/CHECKPOINT.md": (
                6284,
                "3bd339e6874b50ae61695d803fe99b137877dd33360a0286a8222c740c6fe016",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v11_review/attempt_01/CHECKPOINT.md": (
                3165,
                "bfe12c090c45e09b83fed2ad51f1258c1da882f2941f910e0d3f8033b26a0e1e",
            ),
            "RecoverySprint/continuation_20260811/resident_media_voluntary_v11_review/attempt_01/REVIEW_RESULT.json": (
                1615,
                "0b2d0e7a13cd1624f07fb01446f6e6f2c757add4e08cdf030f893e3c82c64443",
            ),
        }
        for relative, exact in expected.items():
            self.assertEqual(digest(ROOT / relative), exact, relative)

    def test_03_core_and_test_compile_from_exact_bytes_without_execution(self) -> None:
        for relative in (
            "Core/resident_media_voluntary_gate_v12.py",
            "Testing/test_resident_media_voluntary_gate_v12.py",
        ):
            path = ROOT / relative
            compile(path.read_bytes(), str(path), "exec")

    def test_04_public_opener_ignores_and_refuses_every_caller_authority_surface(self) -> None:
        opener = v12.open_production_resident_media_v12
        added = {
            "OWNER_SELECTED_CATALOG_SHA256_V12": sha("forged-catalog"),
            "OWNER_SELECTION_RECEIPT_SHA256_V12": sha("forged-selection"),
            "_CONTROLLER_ISSUER_TOKEN": object(),
            "_CONTROLLER_ISSUER_KEY": b"forged",
        }
        original_harness = v12._open_disconnected_static_contract_harness_v12
        for name, value in added.items():
            setattr(v12, name, value)
        v12._open_disconnected_static_contract_harness_v12 = lambda **kwargs: object()
        try:
            attempts = (
                ((), {}),
                ((ExplosiveProxy(),), {}),
                ((), {"catalog": ExplosiveProxy()}),
                ((), {"external_authority": ExplosiveProxy()}),
                ((), {"issuer_token": added["_CONTROLLER_ISSUER_TOKEN"]}),
                ((), {"catalog": catalog(), "authority": StaticExternalAuthorityV12()}),
            )
            for args, kwargs in attempts:
                with self.subTest(args=len(args), keys=tuple(kwargs)):
                    with self.assertRaisesRegex(
                        v12.ResidentMediaV12Error, "production.*disconnected"
                    ):
                        opener(*args, **kwargs)
        finally:
            v12._open_disconnected_static_contract_harness_v12 = original_harness
            for name in added:
                delattr(v12, name)
        self.assertEqual(
            v12.production_connection_status_v12()["status"],
            "DISCONNECTED_FAIL_CLOSED",
        )

    def test_05_private_harness_has_no_catalog_parameter_and_is_not_exported(self) -> None:
        accepted = catalog()
        authority = StaticExternalAuthorityV12(accepted)
        with self.assertRaises(TypeError):
            v12._open_disconnected_static_contract_harness_v12(
                person_id=PERSON,
                external_authority=authority,
                catalog=accepted,
            )
        self.assertNotIn("_open_disconnected_static_contract_harness_v12", v12.__all__)
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "interface is incomplete"):
            v12._open_disconnected_static_contract_harness_v12(
                person_id=PERSON, external_authority=object()
            )

    def test_06_external_objects_must_be_strict_canonical_exact_bytes(self) -> None:
        invalid = (
            b'{"a":1,"a":2}',
            b'{"b":2, "a":1}',
            b'{"a":NaN}',
            b'{"a":1}\n',
            bytearray(b'{"a":1}'),
            "{\"a\":1}",
        )
        for value in invalid:
            with self.subTest(value=repr(value)[:30]):
                with self.assertRaises(
                    (v12.ResidentMediaV12Error, v8.ResidentMediaV8Error)
                ):
                    v12._decode_canonical_object(value, "fresh hostile input")
        self.assertEqual(v12._decode_canonical_object(b'{"a":1}', "control"), {"a": 1})

    def test_07_receipt_purpose_context_sequence_and_digest_fields_fail_closed(self) -> None:
        mutations: dict[str, Callable[[dict[str, Any]], None]] = {
            "authority": lambda response: response["authority_receipt"].__setitem__(
                "authority_instance_id", "wrong_authority"
            ),
            "epoch": lambda response: response["authority_receipt"].__setitem__(
                "authority_epoch_sha256", sha("wrong-epoch")
            ),
            "receipt zero": lambda response: response["authority_receipt"].__setitem__(
                "receipt_id", "0"
            ),
            "purpose": lambda response: response["authority_receipt"].__setitem__(
                "purpose", "GLOBAL_ANCHOR_READBACK"
            ),
            "context": lambda response: response["authority_receipt"].__setitem__(
                "context_sha256", sha("wrong-context")
            ),
            "sequence bool": lambda response: response["authority_receipt"].__setitem__(
                "authority_sequence", True
            ),
            "prior zero": lambda response: response["authority_receipt"].__setitem__(
                "prior_authority_receipt_sha256", "0" * 64
            ),
            "authenticator zero": lambda response: response["authority_receipt"].__setitem__(
                "opaque_authenticator_sha256", "0" * 64
            ),
            "unknown response field": lambda response: response.__setitem__(
                "caller_unknown", True
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                with self.assertRaises(
                    (v12.ResidentMediaV12Error, v8.ResidentMediaV8Error)
                ):
                    v12._open_disconnected_static_contract_harness_v12(
                        person_id=PERSON,
                        external_authority=ResponseMutatingAuthority(mutate),
                    )

    def test_08_verification_response_identity_and_context_are_exact(self) -> None:
        mutations: dict[str, Callable[[dict[str, Any]], None]] = {
            "authority": lambda value: value.__setitem__(
                "authority_instance_id", "wrong_authority"
            ),
            "epoch": lambda value: value.__setitem__(
                "authority_epoch_sha256", sha("wrong-epoch")
            ),
            "receipt": lambda value: value.__setitem__("receipt_id", "wrong_receipt"),
            "receipt digest": lambda value: value.__setitem__(
                "receipt_sha256", sha("wrong-receipt")
            ),
            "purpose": lambda value: value.__setitem__(
                "purpose", "GLOBAL_ANCHOR_READBACK"
            ),
            "context": lambda value: value.__setitem__(
                "context_sha256", sha("wrong-context")
            ),
            "verification zero": lambda value: value.__setitem__(
                "verification_receipt_id", "0"
            ),
            "sequence bool": lambda value: value.__setitem__(
                "verification_sequence", True
            ),
            "not accepted": lambda value: value.__setitem__("accepted", False),
            "not consumed": lambda value: value.__setitem__("consumed", False),
            "wrong boundary": lambda value: value.__setitem__(
                "verifier_boundary", "PYTHON_PROCESS"
            ),
            "unknown": lambda value: value.__setitem__("caller_unknown", True),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                with self.assertRaises(
                    (v12.ResidentMediaV12Error, v8.ResidentMediaV8Error)
                ):
                    v12._open_disconnected_static_contract_harness_v12(
                        person_id=PERSON,
                        external_authority=VerificationMutatingAuthority(mutate),
                    )

    def test_09_snapshot_catalog_selection_source_time_and_derivatives_are_bound(self) -> None:
        accepted, authority, ledger = make_harness()
        original = copy.deepcopy(authority.snapshot_record)
        mutations: dict[str, Callable[[dict[str, Any]], None]] = {
            "snapshot": lambda value: value.__setitem__("snapshot_id", "changed_snapshot"),
            "selection receipt": lambda value: value.__setitem__(
                "owner_selection_receipt_sha256", sha("changed-selection")
            ),
            "source path": lambda value: value["catalog_record"]["manifests"][0].__setitem__(
                "source_relative_path", "changed/source.png"
            ),
            "source time": lambda value: value["source_time_identity_sha256s"].__setitem__(
                0, sha("changed-source-time")
            ),
            "derivative path": lambda value: value["catalog_record"]["manifests"][0][
                "derivatives"
            ][0].__setitem__("relative_path", "changed/derivative.png"),
            "derivative identity": lambda value: value[
                "derivative_identity_sha256s"
            ][0].__setitem__(0, sha("changed-derivative-identity")),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                authority.snapshot_record = copy.deepcopy(original)
                mutate(authority.snapshot_record)
                with self.assertRaises(v12.ResidentMediaV12Error):
                    ledger.snapshot()
        authority.snapshot_record = original
        self.assertEqual(ledger.snapshot()["catalog_sha256"], accepted.sha256)

    def test_10_authority_receipts_reject_local_and_cross_adapter_replay(self) -> None:
        accepted, authority, ledger = make_harness()
        ledger.snapshot()
        newest = max(
            authority._issued_receipts.values(),
            key=lambda row: row["authority_sequence"],
        )
        authority.replay_next_receipt = copy.deepcopy(newest)
        with self.assertRaises(v12.ResidentMediaV12Error):
            ledger.snapshot()

        snapshot_receipts = [
            row
            for row in authority._issued_receipts.values()
            if row["purpose"] == "OWNER_SELECTION_SNAPSHOT_READ"
        ]
        authority.replay_next_receipt = copy.deepcopy(
            max(snapshot_receipts, key=lambda row: row["authority_sequence"])
        )
        with self.assertRaises(v12.ResidentMediaV12Error):
            v12._open_disconnected_static_contract_harness_v12(
                person_id="person_lisa_secondary", external_authority=authority
            )

    def test_11_initial_append_stale_cas_rollback_and_readback_toc_tou(self) -> None:
        accepted, authority, first = make_harness()
        self.assertEqual(first.snapshot()["revision"], 0)
        stale = v12._open_disconnected_static_contract_harness_v12(
            person_id=PERSON, external_authority=authority
        )
        consume(first, accepted, 0, "fresh-audit-first")
        self.assertEqual(first.snapshot()["revision"], 1)
        with self.assertRaises(v12.ResidentMediaV12Error):
            consume(stale, accepted, 3, "fresh-audit-stale")
        old = copy.deepcopy(authority._anchors[PERSON])
        consume(first, accepted, 3, "fresh-audit-second")
        authority._anchors[PERSON] = old
        with self.assertRaises(v12.ResidentMediaV12Error):
            first.snapshot()

        drifting = StaticExternalAuthorityV12(catalog())
        drifting.rewrite_readback_after_cas = True
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "exact readback"):
            v12._open_disconnected_static_contract_harness_v12(
                person_id=PERSON, external_authority=drifting
            )

    def test_12_ambiguous_post_commit_failure_never_returns_acceptance(self) -> None:
        class CommitThenFail(StaticExternalAuthorityV12):
            def compare_and_swap_global_anchor_v12(self, request_bytes: bytes) -> bytes:
                super().compare_and_swap_global_anchor_v12(request_bytes)
                raise RuntimeError("ambiguous after commit")

        authority = CommitThenFail(catalog())
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "compare-and-swap failed"):
            v12._open_disconnected_static_contract_harness_v12(
                person_id=PERSON, external_authority=authority
            )
        self.assertIn(PERSON, authority._anchors)

    def test_13_exact_page_video_audio_caption_positive_controls(self) -> None:
        accepted, _authority, ledger = make_harness()
        expected = {
            0: {"rendered_page_png"},
            2: {"timed_frame_manifest", "synchronized_audio_pcm", "caption_text_utf8"},
            3: {"synchronized_audio_pcm"},
        }
        for ordinal in (0, 2, 3):
            clean = consume(ledger, accepted, ordinal, f"fresh-role-{ordinal}")
            self.assertEqual(set(clean["complete_by_required_role"]), expected[ordinal])
            self.assertTrue(all(clean["complete_by_required_role"].values()))
        self.assertEqual(ledger.snapshot()["revision"], 3)

    def test_14_blocker_honestly_declared_incomplete_video_is_recorded(self) -> None:
        accepted, _authority, ledger = make_harness()
        session_id, evidence = item_for(
            accepted, ordinal=2, label="fresh-honest-incomplete-video"
        )
        evidence["presentation_segments"] = [
            row
            for row in evidence["presentation_segments"]
            if row["derivative_role"] != "caption_text_utf8"
        ]
        evidence["presentation_complete_for_manifest"] = False
        evidence["engineering_output_completed"] = False
        clean = ledger.validate_and_record_static_evidence(
            evidence,
            session_id=session_id,
            expected_manifest=accepted.manifest(2),
            consumed_start_permit_sha256=sha("permit:2"),
        )
        self.assertFalse(clean["complete_by_required_role"]["caption_text_utf8"])
        self.assertFalse(clean["presentation_complete_for_manifest"])
        self.assertEqual(ledger.snapshot()["revision"], 1)

    def test_15_blocker_honestly_declared_incomplete_audio_is_recorded(self) -> None:
        accepted, _authority, ledger = make_harness()
        session_id, evidence = item_for(
            accepted, ordinal=3, label="fresh-honest-incomplete-audio"
        )
        evidence["presentation_segments"][0]["source_end_ms"] -= 1
        evidence["presentation_complete_for_manifest"] = False
        evidence["engineering_output_completed"] = False
        clean = ledger.validate_and_record_static_evidence(
            evidence,
            session_id=session_id,
            expected_manifest=accepted.manifest(3),
            consumed_start_permit_sha256=sha("permit:3"),
        )
        self.assertFalse(clean["complete_by_required_role"]["synchronized_audio_pcm"])
        self.assertEqual(ledger.snapshot()["revision"], 1)

    def test_16_blocker_bool_and_integer_snapshot_identifiers_are_accepted(self) -> None:
        authority = StaticExternalAuthorityV12(catalog())
        authority.snapshot_record["snapshot_id"] = True
        authority.snapshot_record["owner_selection_receipt_id"] = 1
        ledger = v12._open_disconnected_static_contract_harness_v12(
            person_id=PERSON, external_authority=authority
        )
        self.assertIs(ledger._snapshot["snapshot_id"], True)
        self.assertEqual(ledger._snapshot["owner_selection_receipt_id"], 1)
        self.assertEqual(ledger.snapshot()["revision"], 0)

    def test_17_blocker_bool_person_session_output_and_surface_are_accepted(self) -> None:
        accepted = catalog()
        authority = StaticExternalAuthorityV12(accepted)
        bool_person = v12._open_disconnected_static_contract_harness_v12(
            person_id=True, external_authority=authority
        )
        self.assertEqual(bool_person.snapshot()["person_id"], "True")

        accepted, _authority, ledger = make_harness()
        _old_session, evidence = item_for(
            accepted, ordinal=0, label="fresh-bool-identities"
        )
        evidence["session_id"] = "True"
        evidence["output_receipt_id"] = True
        evidence["output_surface_id"] = True
        clean = ledger.validate_and_record_static_evidence(
            evidence,
            session_id=True,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        self.assertEqual(clean["session_id"], "True")
        self.assertEqual(clean["output_receipt_id"], "True")
        self.assertIs(clean["output_surface_id"], True)
        self.assertEqual(ledger.snapshot()["revision"], 1)

    def test_18_blocker_numeric_64_digit_decoder_digest_is_accepted(self) -> None:
        accepted, _authority, ledger = make_harness()
        session_id, evidence = item_for(
            accepted, ordinal=0, label="fresh-numeric-decoder-digest"
        )
        numeric_digest = int("1" * 64)
        evidence["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ] = numeric_digest
        clean = ledger.validate_and_record_static_evidence(
            evidence,
            session_id=session_id,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        self.assertIsInstance(
            clean["presentation_segments"][0][
                "renderer_or_decoder_receipt_sha256"
            ],
            int,
        )
        self.assertEqual(
            clean["renderer_or_decoder_receipt_sha256s"], [str(numeric_digest)]
        )
        self.assertEqual(ledger.snapshot()["revision"], 1)

    def test_19_exact_normal_identity_substitution_and_global_replay_refuse(self) -> None:
        accepted, authority, ledger = make_harness()
        session_id, evidence = item_for(
            accepted,
            ordinal=0,
            label="fresh-exact-binding",
            output_id="fresh_global_output_receipt",
            receipt_prefix="fresh-global-decoder",
        )
        bad_session = copy.deepcopy(evidence)
        bad_session["session_id"] = "wrong_session"
        with self.assertRaises(v9.ResidentMediaV9Error):
            ledger.validate_and_record_static_evidence(
                bad_session,
                session_id=session_id,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        bad_person = copy.deepcopy(evidence)
        bad_person["person_id"] = "wrong_person"
        with self.assertRaises(v9.ResidentMediaV9Error):
            ledger.validate_and_record_static_evidence(
                bad_person,
                session_id=session_id,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        forged_manifest = copy.deepcopy(accepted.manifest(0))
        forged_manifest["source_byte_count"] += 1
        with self.assertRaises((v12.ResidentMediaV12Error, v4.ResidentMediaV4Error)):
            ledger.validate_and_record_static_evidence(
                evidence,
                session_id=session_id,
                expected_manifest=forged_manifest,
                consumed_start_permit_sha256=sha("permit:0"),
            )

        ledger.validate_and_record_static_evidence(
            evidence,
            session_id=session_id,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        reopened = v12._open_disconnected_static_contract_harness_v12(
            person_id=PERSON, external_authority=authority
        )
        replay_session, replay = item_for(
            accepted,
            ordinal=0,
            label="fresh-reopen-replay",
            output_id=evidence["output_receipt_id"],
            receipt_prefix="fresh-other-decoder",
        )
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "output receipt"):
            reopened.validate_and_record_static_evidence(
                replay,
                session_id=replay_session,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )

        decoder_session, decoder_replay = item_for(
            accepted,
            ordinal=0,
            label="fresh-reopen-decoder-replay",
            output_id="fresh_other_output_receipt",
            receipt_prefix="fresh-new-decoder",
        )
        decoder_replay["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ] = evidence["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ]
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "decoder receipt"):
            reopened.validate_and_record_static_evidence(
                decoder_replay,
                session_id=decoder_session,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )

    def test_20_truth_summary_and_static_import_surface_remain_disconnected(self) -> None:
        status = v12.production_connection_status_v12()
        summary = v12.static_contract_summary()
        self.assertEqual(status["status"], "DISCONNECTED_FAIL_CLOSED")
        self.assertFalse(status["live_execution_allowed"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["person_saw_or_heard_claimed"])
        self.assertFalse(summary["person_enjoyed_or_remembered_claimed"])
        names = set(vars(v12))
        for forbidden in (
            "_CONTROLLER_ISSUER_TOKEN",
            "_CONTROLLER_ISSUER_KEY",
            "OWNER_SELECTED_CATALOG_SHA256_V12",
            "OWNER_SELECTION_RECEIPT_SHA256_V12",
            "issue_controller_owned_static_authority_v12",
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
