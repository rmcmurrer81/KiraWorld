from __future__ import annotations

import copy
import hashlib
import inspect
import threading
import unittest
from pathlib import Path
from typing import Any

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v12 as v12
from Testing import test_resident_media_voluntary_gate_v9 as v9_authored
from Testing import test_resident_media_voluntary_gate_v11 as v11_authored
from Testing.test_resident_media_voluntary_gate_v5 import catalog


ROOT = Path(__file__).resolve().parents[1]
PERSON = "person_kira_primary"


def sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def canonical(value: dict[str, Any]) -> bytes:
    return v4.canonical_json_bytes(value)


def decode(value: bytes) -> dict[str, Any]:
    result = v4.strict_json_loads(value)
    assert isinstance(result, dict)
    assert canonical(result) == value
    return result


class StaticExternalAuthorityV12:
    """Stateful test double for the external-authority byte contract.

    This is intentionally not a production authority or OS trust root.  It is
    defined in the test module so V12 contains no issuer secret or test
    authority factory.
    """

    def __init__(self, accepted: v4.StimulusCatalog | None = None) -> None:
        selected = accepted or catalog()
        bindings = v12._catalog_bindings(selected)
        self.authority_instance_id = "external_authority_static_double_v12"
        self.authority_epoch_sha256 = sha("external-authority-v12-epoch")
        self._secret = hashlib.sha256(
            b"test-only-static-external-authority-v12"
        ).digest()
        owner_receipt_id = "owner_selection_receipt_static_v12"
        owner_receipt = {
            "schema": "kira.owner_selection_receipt.static_test.v12",
            "receipt_id": owner_receipt_id,
            "catalog_sha256": selected.sha256,
            "selection_revision": 1,
        }
        self.snapshot_record: dict[str, Any] = {
            "schema": "kira.resident_media.owner_selected_snapshot.v12",
            "status": "AUTHENTICATED_EXTERNAL_SELECTION_STATIC_CONTRACT_ONLY",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "snapshot_id": "owner_selected_snapshot_static_v12",
            "selection_revision": 1,
            "owner_selection_receipt_id": owner_receipt_id,
            "owner_selection_receipt_sha256": sha(
                canonical(owner_receipt).decode("utf-8")
            ),
            "authoritative_source_policy_sha256": (
                "ece0785cb5bb315ea63ccb16a1643b0c22dfc65ee7bf25f41b336afebd0dc127"
            ),
            **bindings,
            "owner_selected": True,
            "immutable_exact_bytes": True,
            "caller_catalog_input_accepted": False,
            "live_execution_allowed": False,
        }
        self._anchors: dict[str, dict[str, Any]] = {}
        self._issue_sequence = 0
        self._verify_sequence = 0
        self._prior_receipt_sha256 = sha("external-authority-receipt-genesis-v12")
        self._consumed_receipt_ids: set[str] = set()
        self._issued_receipts: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.replay_next_receipt: dict[str, Any] | None = None
        self.rewrite_readback_after_cas = False

    def describe_contract_v12(self) -> bytes:
        return canonical(
            {
                "schema": "kira.protected_external_media_authority.v12",
                "authority_interface_version": 12,
                "authority_instance_id": self.authority_instance_id,
                "authority_epoch_sha256": self.authority_epoch_sha256,
                "interface_mode": "STATIC_TEST_DOUBLE",
                "caller_catalog_input_accepted": False,
                "immutable_snapshot_bytes": True,
                "atomic_monotonic_cas": True,
                "exact_readback_receipts": True,
                "global_one_use_receipts": True,
                "python_process_is_trust_root": False,
                "production_connection_active": False,
            }
        )

    def _read_request(self, request_bytes: bytes, keys: set[str], schema: str) -> dict:
        request = decode(request_bytes)
        if set(request) != keys or request.get("schema") != schema:
            raise RuntimeError("request contract changed")
        if request.get("authority_instance_id") != self.authority_instance_id:
            raise RuntimeError("authority identity changed")
        if request.get("authority_epoch_sha256") != self.authority_epoch_sha256:
            raise RuntimeError("authority epoch changed")
        if request.get("live_execution_allowed") is not False:
            raise RuntimeError("live execution requested")
        return request

    def _receipt(self, purpose: str, context: dict[str, Any]) -> dict[str, Any]:
        if self.replay_next_receipt is not None:
            receipt = self.replay_next_receipt
            self.replay_next_receipt = None
            return copy.deepcopy(receipt)
        self._issue_sequence += 1
        context_sha = v12._record_sha(context)
        receipt_core = {
            "schema": "kira.protected_external_authority_receipt.v12",
            "receipt_id": f"external_receipt_{self._issue_sequence:08d}",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "purpose": purpose,
            "context_sha256": context_sha,
            "authority_sequence": self._issue_sequence,
            "prior_authority_receipt_sha256": self._prior_receipt_sha256,
        }
        authenticator = hashlib.sha256(
            self._secret + b"\x00" + canonical(receipt_core)
        ).hexdigest()
        receipt = dict(receipt_core)
        receipt["opaque_authenticator_sha256"] = authenticator
        receipt_sha = v12._record_sha(receipt)
        self._prior_receipt_sha256 = receipt_sha
        self._issued_receipts[receipt["receipt_id"]] = copy.deepcopy(receipt)
        return receipt

    def _response(self, core: dict[str, Any], purpose: str) -> bytes:
        response = copy.deepcopy(core)
        response["authority_receipt"] = self._receipt(purpose, core)
        return canonical(response)

    def read_owner_selected_snapshot_v12(self, request_bytes: bytes) -> bytes:
        self._read_request(
            request_bytes,
            {
                "schema",
                "authority_instance_id",
                "authority_epoch_sha256",
                "caller_catalog_supplied",
                "static_contract_only",
                "live_execution_allowed",
            },
            "kira.read_owner_selected_snapshot_request.v12",
        )
        core = {
            "schema": "kira.owner_selection_snapshot_read_response.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "snapshot": copy.deepcopy(self.snapshot_record),
            "snapshot_sha256": v12._record_sha(self.snapshot_record),
            "immutable_exact_bytes": True,
            "caller_catalog_input_accepted": False,
            "live_execution_allowed": False,
        }
        return self._response(core, "OWNER_SELECTION_SNAPSHOT_READ")

    def read_global_anchor_v12(self, request_bytes: bytes) -> bytes:
        request = self._read_request(
            request_bytes,
            {
                "schema",
                "authority_instance_id",
                "authority_epoch_sha256",
                "owner_selection_snapshot_sha256",
                "person_id",
                "static_contract_only",
                "live_execution_allowed",
            },
            "kira.read_global_anchor_request.v12",
        )
        person = request["person_id"]
        anchor = copy.deepcopy(self._anchors.get(person))
        core = {
            "schema": "kira.global_anchor_read_response.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "owner_selection_snapshot_sha256": request[
                "owner_selection_snapshot_sha256"
            ],
            "person_id": person,
            "anchor": anchor,
            "anchor_sha256": v12._record_sha(anchor) if anchor is not None else None,
            "exact_readback": True,
            "live_execution_allowed": False,
        }
        return self._response(core, "GLOBAL_ANCHOR_READBACK")

    def compare_and_swap_global_anchor_v12(self, request_bytes: bytes) -> bytes:
        request = self._read_request(
            request_bytes,
            {
                "schema",
                "authority_instance_id",
                "authority_epoch_sha256",
                "owner_selection_snapshot_sha256",
                "person_id",
                "expected_previous_anchor_sha256",
                "replacement_anchor",
                "replacement_anchor_sha256",
                "append_only_required",
                "static_contract_only",
                "live_execution_allowed",
            },
            "kira.compare_and_swap_global_anchor_request.v12",
        )
        person = request["person_id"]
        replacement = request["replacement_anchor"]
        if not isinstance(replacement, dict):
            raise RuntimeError("replacement is invalid")
        if request["replacement_anchor_sha256"] != v12._record_sha(replacement):
            raise RuntimeError("replacement digest changed")
        current = self._anchors.get(person)
        current_sha = v12._record_sha(current) if current is not None else None
        if request["expected_previous_anchor_sha256"] != current_sha:
            raise RuntimeError("protected global CAS mismatch")
        if current is None:
            if (
                replacement.get("revision") != 0
                or replacement.get("generation") != 0
                or replacement.get("presentation_records") != []
            ):
                raise RuntimeError("initial anchor is not exact")
        else:
            if (
                replacement.get("revision") != current["revision"] + 1
                or replacement.get("generation") != current["generation"] + 1
                or replacement.get("previous_anchor_sha256") != current_sha
                or replacement.get("presentation_records", [])[:-1]
                != current["presentation_records"]
                or len(replacement.get("presentation_records", []))
                != len(current["presentation_records"]) + 1
            ):
                raise RuntimeError("protected history is not append-only")
        self._anchors[person] = copy.deepcopy(replacement)
        core = {
            "schema": "kira.global_anchor_cas_response.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "owner_selection_snapshot_sha256": request[
                "owner_selection_snapshot_sha256"
            ],
            "person_id": person,
            "expected_previous_anchor_sha256": current_sha,
            "committed_anchor_sha256": v12._record_sha(replacement),
            "committed_revision": replacement["revision"],
            "committed_generation": replacement["generation"],
            "committed_chain_head_sha256": replacement["chain_head_sha256"],
            "atomic_compare_and_swap": True,
            "strictly_monotonic_revision": True,
            "global_receipt_one_use_enforced": True,
            "exact_post_commit_readback_required": True,
            "live_execution_allowed": False,
        }
        response = self._response(core, "GLOBAL_ANCHOR_COMPARE_AND_SWAP")
        if self.rewrite_readback_after_cas:
            self._anchors[person]["revision"] += 1
        return response

    def consume_and_verify_receipt_v12(
        self, receipt_bytes: bytes, expected_context_sha256: str
    ) -> bytes:
        receipt = decode(receipt_bytes)
        receipt_id = receipt["receipt_id"]
        expected = self._issued_receipts.get(receipt_id)
        if expected != receipt:
            raise RuntimeError("unknown or changed authority receipt")
        if receipt_id in self._consumed_receipt_ids:
            raise RuntimeError("authority receipt already consumed globally")
        if receipt["context_sha256"] != expected_context_sha256:
            raise RuntimeError("authority receipt context changed")
        core = copy.deepcopy(receipt)
        supplied_auth = core.pop("opaque_authenticator_sha256")
        expected_auth = hashlib.sha256(
            self._secret + b"\x00" + canonical(core)
        ).hexdigest()
        if supplied_auth != expected_auth:
            raise RuntimeError("authority receipt authenticator changed")
        self._consumed_receipt_ids.add(receipt_id)
        self._verify_sequence += 1
        return canonical(
            {
                "schema": "kira.protected_external_receipt_verification.v12",
                "authority_instance_id": self.authority_instance_id,
                "authority_epoch_sha256": self.authority_epoch_sha256,
                "receipt_id": receipt_id,
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                "purpose": receipt["purpose"],
                "context_sha256": expected_context_sha256,
                "verification_receipt_id": (
                    f"external_verification_{self._verify_sequence:08d}"
                ),
                "verification_sequence": self._verify_sequence,
                "accepted": True,
                "globally_one_use": True,
                "consumed": True,
                "verifier_boundary": "PROTECTED_EXTERNAL_AUTHORITY_INTERFACE",
            }
        )


def make_harness(
    *, accepted: v4.StimulusCatalog | None = None, authority: StaticExternalAuthorityV12 | None = None
) -> tuple[v4.StimulusCatalog, StaticExternalAuthorityV12, Any]:
    accepted = accepted or catalog()
    authority = authority or StaticExternalAuthorityV12(accepted)
    ledger = v12._open_disconnected_static_contract_harness_v12(
        person_id=PERSON, external_authority=authority
    )
    return accepted, authority, ledger


def item_for(
    accepted: v4.StimulusCatalog,
    *,
    ordinal: int,
    label: str,
    output_id: str | None = None,
    receipt_prefix: str | None = None,
) -> tuple[str, dict[str, Any]]:
    sid = v11_authored.session(f"v12-{label}")
    value = v11_authored.item_for(
        accepted,
        ordinal=ordinal,
        session_id=sid,
        output_id=output_id or f"v12_output_{label}",
        receipt_prefix=receipt_prefix or f"v12:{label}",
    )
    return sid, value


def consume(ledger: Any, accepted: v4.StimulusCatalog, ordinal: int, label: str) -> dict:
    sid, value = item_for(accepted, ordinal=ordinal, label=label)
    return ledger.validate_and_record_static_evidence(
        value,
        session_id=sid,
        expected_manifest=accepted.manifest(ordinal),
        consumed_start_permit_sha256=sha(f"permit:{ordinal}"),
    )


class ResidentMediaV12Tests(unittest.TestCase):
    def test_public_production_opener_is_unconditionally_disconnected(self) -> None:
        accepted = catalog()
        authority = StaticExternalAuthorityV12(accepted)
        attempts = (
            {},
            {"catalog": accepted},
            {"external_authority": authority},
            {"catalog": accepted, "external_authority": authority},
            {"issuer_token": object()},
        )
        for kwargs in attempts:
            with self.subTest(kwargs=tuple(kwargs)):
                with self.assertRaisesRegex(
                    v12.ResidentMediaV12Error, "production.*disconnected"
                ):
                    v12.open_production_resident_media_v12(**kwargs)
        status = v12.production_connection_status_v12()
        self.assertEqual(status["status"], "DISCONNECTED_FAIL_CLOSED")
        self.assertFalse(status["protected_external_authority_implementation_present"])
        self.assertFalse(status["production_opener_accepts_caller_authority"])
        self.assertFalse(status["production_opener_accepts_caller_catalog"])
        self.assertFalse(status["live_execution_allowed"])

    def test_no_module_issuer_secret_factory_or_trusted_catalog_global(self) -> None:
        names = set(vars(v12))
        self.assertNotIn("_CONTROLLER_ISSUER_TOKEN", names)
        self.assertNotIn("_CONTROLLER_ISSUER_KEY", names)
        self.assertNotIn("OWNER_SELECTED_CATALOG_SHA256_V12", names)
        self.assertNotIn("OWNER_SELECTION_RECEIPT_SHA256_V12", names)
        self.assertNotIn("issue_controller_owned_static_authority_v12", names)
        self.assertNotIn("_open_disconnected_static_contract_harness_v12", v12.__all__)
        self.assertNotIn("from typing import Any, Final", inspect.getsource(v12))

    def test_same_process_rebinding_and_v11_token_cannot_open_production(self) -> None:
        accepted = catalog()
        altered = copy.deepcopy(accepted.as_record()["manifests"])
        altered[0]["derivatives"][0]["relative_path"] += ".caller"
        forged = v4.StimulusCatalog(altered)
        v12.OWNER_SELECTED_CATALOG_SHA256_V12 = forged.sha256
        v12.OWNER_SELECTION_RECEIPT_SHA256_V12 = sha("caller-rebound")
        v12._CONTROLLER_ISSUER_TOKEN = object()
        try:
            for kwargs in (
                {"catalog": forged},
                {"issuer_token": v12._CONTROLLER_ISSUER_TOKEN},
            ):
                with self.assertRaises(v12.ResidentMediaV12Error):
                    v12.open_production_resident_media_v12(**kwargs)
        finally:
            del v12.OWNER_SELECTED_CATALOG_SHA256_V12
            del v12.OWNER_SELECTION_RECEIPT_SHA256_V12
            del v12._CONTROLLER_ISSUER_TOKEN

    def test_static_harness_accepts_no_caller_catalog_and_binds_authority_snapshot(self) -> None:
        accepted = catalog()
        authority = StaticExternalAuthorityV12(accepted)
        with self.assertRaises(TypeError):
            v12._open_disconnected_static_contract_harness_v12(
                person_id=PERSON,
                external_authority=authority,
                catalog=accepted,
            )
        _accepted, _authority, ledger = make_harness(
            accepted=accepted, authority=authority
        )
        first = ledger.snapshot()
        self.assertEqual(first["catalog_sha256"], accepted.sha256)
        self.assertFalse(first["live_execution_allowed"])
        self.assertFalse(first["python_process_is_trust_root"])
        accepted._manifests[0]["derivatives"][0]["sha256"] = sha("caller-mutation")
        self.assertEqual(ledger.snapshot()["catalog_sha256"], first["catalog_sha256"])

    def test_exact_page_video_audio_roles_and_incomplete_refusal(self) -> None:
        accepted, _authority, ledger = make_harness()
        expected_roles = {
            0: {"rendered_page_png"},
            2: {
                "timed_frame_manifest",
                "synchronized_audio_pcm",
                "caption_text_utf8",
            },
            3: {"synchronized_audio_pcm"},
        }
        for ordinal in (0, 2, 3):
            clean = consume(ledger, accepted, ordinal, f"roles-{ordinal}")
            self.assertEqual(set(clean["complete_by_required_role"]), expected_roles[ordinal])
            self.assertTrue(all(clean["complete_by_required_role"].values()))
        before = ledger.snapshot()["revision"]
        sid, partial = item_for(accepted, ordinal=2, label="partial-caption")
        caption = next(
            segment
            for segment in partial["presentation_segments"]
            if segment["derivative_role"] == "caption_text_utf8"
        )
        caption["source_end_ms"] -= 1
        with self.assertRaisesRegex(v9.ResidentMediaV9Error, "completeness"):
            ledger.validate_and_record_static_evidence(
                partial,
                session_id=sid,
                expected_manifest=accepted.manifest(2),
                consumed_start_permit_sha256=sha("permit:2"),
            )
        self.assertEqual(ledger.snapshot()["revision"], before)

    def test_external_snapshot_source_time_and_each_derivative_are_exact(self) -> None:
        accepted, authority, ledger = make_harness()
        original = copy.deepcopy(authority.snapshot_record)
        def change_catalog_path(value: dict[str, Any]) -> None:
            manifest = value["catalog_record"]["manifests"][0]
            manifest["source_relative_path"] += ".changed"

        def change_source_bytes(value: dict[str, Any]) -> None:
            value["catalog_record"]["manifests"][0]["source_byte_count"] += 1

        def change_source_digest(value: dict[str, Any]) -> None:
            value["catalog_record"]["manifests"][0]["source_sha256"] = sha(
                "changed-source-digest"
            )

        def change_source_coordinate(value: dict[str, Any]) -> None:
            value["catalog_record"]["manifests"][0]["coordinates"][
                "page_number"
            ] += 1

        def change_derivative_path(value: dict[str, Any]) -> None:
            value["catalog_record"]["manifests"][0]["derivatives"][0][
                "relative_path"
            ] += ".changed"

        def change_derivative_bytes(value: dict[str, Any]) -> None:
            value["catalog_record"]["manifests"][0]["derivatives"][0][
                "byte_count"
            ] += 1

        def change_derivative_digest(value: dict[str, Any]) -> None:
            value["catalog_record"]["manifests"][0]["derivatives"][0][
                "sha256"
            ] = sha("changed-derivative-digest")

        mutations = {
            "catalog path": change_catalog_path,
            "source bytes": change_source_bytes,
            "source digest": change_source_digest,
            "source coordinate": change_source_coordinate,
            "derivative path": change_derivative_path,
            "derivative bytes": change_derivative_bytes,
            "derivative digest": change_derivative_digest,
            "source-time": lambda value: value["source_time_identity_sha256s"].__setitem__(
                0, sha("changed-source-time")
            ),
            "derivative set": lambda value: value["derivative_set_sha256s"].__setitem__(
                0, sha("changed-derivative-set")
            ),
            "derivative identity": lambda value: value[
                "derivative_identity_sha256s"
            ][0].__setitem__(0, sha("changed-derivative-identity")),
            "selection receipt": lambda value: value.__setitem__(
                "owner_selection_receipt_sha256", sha("changed-selection")
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                authority.snapshot_record = copy.deepcopy(original)
                mutate(authority.snapshot_record)
                with self.assertRaises(v12.ResidentMediaV12Error):
                    ledger.snapshot()
        authority.snapshot_record = original
        self.assertEqual(ledger.snapshot()["catalog_sha256"], accepted.sha256)

    def test_external_authority_receipt_replay_is_globally_rejected(self) -> None:
        accepted, authority, ledger = make_harness()
        self.assertEqual(ledger.snapshot()["revision"], 0)
        last_id = max(
            authority._issued_receipts,
            key=lambda item: authority._issued_receipts[item]["authority_sequence"],
        )
        authority.replay_next_receipt = copy.deepcopy(
            authority._issued_receipts[last_id]
        )
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "receipt replayed"):
            ledger.snapshot()

    def test_external_receipt_replay_rejects_across_fresh_adapter(self) -> None:
        accepted, authority, ledger = make_harness()
        self.assertEqual(ledger.snapshot()["revision"], 0)
        snapshot_receipts = [
            receipt
            for receipt in authority._issued_receipts.values()
            if receipt["purpose"] == "OWNER_SELECTION_SNAPSHOT_READ"
        ]
        replay = max(snapshot_receipts, key=lambda item: item["authority_sequence"])
        authority.replay_next_receipt = copy.deepcopy(replay)
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "verification failed"):
            v12._open_disconnected_static_contract_harness_v12(
                person_id="person_lisa_secondary", external_authority=authority
            )

    def test_output_and_decoder_receipts_are_global_across_sessions_and_reopen(self) -> None:
        accepted, authority, first = make_harness()
        sid, original = item_for(
            accepted,
            ordinal=0,
            label="global-original",
            output_id="v12_global_output",
            receipt_prefix="v12-global-decoder",
        )
        first.validate_and_record_static_evidence(
            original,
            session_id=sid,
            expected_manifest=accepted.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        second = v12._open_disconnected_static_contract_harness_v12(
            person_id=PERSON, external_authority=authority
        )
        sid2, replay_output = item_for(
            accepted,
            ordinal=0,
            label="global-output-replay",
            output_id=original["output_receipt_id"],
            receipt_prefix="v12-new-decoder",
        )
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "output receipt"):
            second.validate_and_record_static_evidence(
                replay_output,
                session_id=sid2,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        sid3, replay_decoder = item_for(
            accepted,
            ordinal=0,
            label="global-decoder-replay",
            output_id="v12_fresh_output",
            receipt_prefix="v12-fresh-decoder",
        )
        replay_decoder["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ] = original["presentation_segments"][0][
            "renderer_or_decoder_receipt_sha256"
        ]
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "decoder receipt"):
            second.validate_and_record_static_evidence(
                replay_decoder,
                session_id=sid3,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(second.snapshot()["revision"], 1)

    def test_stale_concurrent_anchor_and_signed_old_rollback_fail(self) -> None:
        accepted, authority, first = make_harness()
        stale = v12._open_disconnected_static_contract_harness_v12(
            person_id=PERSON, external_authority=authority
        )
        consume(first, accepted, 0, "concurrent-first")
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "changed or rolled back"):
            consume(stale, accepted, 3, "concurrent-stale")
        revision_one = copy.deepcopy(authority._anchors[PERSON])
        consume(first, accepted, 3, "rollback-second")
        authority._anchors[PERSON] = revision_one
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "changed or rolled back"):
            first.snapshot()

    def test_cas_readback_toc_tou_and_unknown_fields_fail_closed(self) -> None:
        accepted = catalog()
        authority = StaticExternalAuthorityV12(accepted)
        authority.rewrite_readback_after_cas = True
        with self.assertRaisesRegex(v12.ResidentMediaV12Error, "exact readback"):
            v12._open_disconnected_static_contract_harness_v12(
                person_id=PERSON, external_authority=authority
            )

        accepted, _authority, ledger = make_harness()
        sid, evidence = item_for(accepted, ordinal=0, label="unknown-field")
        evidence["caller_unknown"] = True
        with self.assertRaises(v8.ResidentMediaV8Error):
            ledger.validate_and_record_static_evidence(
                evidence,
                session_id=sid,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(ledger.snapshot()["revision"], 0)

    def test_zero_unicode_and_bool_integer_bypasses_fail_closed(self) -> None:
        accepted = catalog()
        authority = StaticExternalAuthorityV12(accepted)
        for person in ("0", "00000000-0000-0000-0000-000000000000", "null"):
            with self.subTest(person=person):
                with self.assertRaises(v12.ResidentMediaV12Error):
                    v12._open_disconnected_static_contract_harness_v12(
                        person_id=person, external_authority=authority
                    )
        _accepted, authority, ledger = make_harness()
        original = authority.snapshot_record["selection_revision"]
        authority.snapshot_record["selection_revision"] = True
        with self.assertRaises(v12.ResidentMediaV12Error):
            ledger.snapshot()
        authority.snapshot_record["selection_revision"] = original
        self.assertEqual(ledger.snapshot()["revision"], 0)

    def test_summary_is_truthful_static_only(self) -> None:
        summary = v12.static_contract_summary()
        self.assertEqual(
            summary["status"],
            "DISCONNECTED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        )
        self.assertTrue(summary["module_resident_issuer_token_removed"])
        self.assertFalse(summary["rebindable_final_catalog_globals_trusted"])
        self.assertFalse(summary["caller_catalog_accepted"])
        self.assertFalse(summary["static_test_double_is_production_authority"])
        self.assertFalse(summary["python_process_is_trust_root"])
        self.assertTrue(summary["public_production_opener_disconnected"])
        self.assertFalse(summary["live_execution_allowed"])

    def test_v10_v11_and_rejection_evidence_are_preserved_exactly(self) -> None:
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
        for relative, (size, digest) in expected.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest, relative)


if __name__ == "__main__":
    unittest.main()
