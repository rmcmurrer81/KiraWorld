"""Append-only resident-media v10 protected catalog/global-receipt repair.

V9 proved per-required-role page/video/audio/caption coverage, but its fresh
audit rejected the authority boundary: receipt identities were one-use only
inside one session, a caller-created catalog was trusted, the protected v5
catalog authorization was never read, and a catalog could be mutated after
the v9 anchor was created.

V10 is still a disconnected static candidate.  It reuses v9's exact evidence
validator only after rebuilding an immutable snapshot of the exact v5
owner-selected catalog and revalidating its protected authorization.  Output
and renderer/decoder receipt identities are consumed in one protected global
person ledger, so changing session identifiers cannot rearm them.  Nothing in
this module opens media, calls a model, presents output, or records a person's
reaction, preference, attention, experience, or memory.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v5 as v5
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9


MAX_GLOBAL_RECEIPTS = 4096
MAX_GLOBAL_RECORDS = 1024


class ResidentMediaV10Error(v9.ResidentMediaV9Error):
    """Raised when protected catalog or global receipt truth is not exact."""


def _canonical_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return v4.strict_json_loads(v4.canonical_json_bytes(dict(value)))


def _freeze_authorized_catalog(
    catalog: v4.StimulusCatalog,
    backend: "ProtectedMonotonicBackendV10",
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    if not isinstance(catalog, v4.StimulusCatalog):
        raise ResidentMediaV10Error("catalog must be a validated v4 catalog")
    record = catalog.as_record()
    if set(record) != {"schema", "manifests"}:
        raise ResidentMediaV10Error("catalog record shape changed")
    if record.get("schema") != "kira.resident_media_source_catalog.v4":
        raise ResidentMediaV10Error("catalog schema changed")
    manifests = record.get("manifests")
    if not isinstance(manifests, list):
        raise ResidentMediaV10Error("catalog manifests are missing")

    # Reconstruct from canonical bytes rather than retaining a caller-owned
    # StimulusCatalog object.  All later evidence is checked against another
    # reconstruction from these frozen bytes.
    snapshot = v4.StimulusCatalog(manifests)
    catalog_sha = v5.validate_authoritative_catalog(snapshot)
    if snapshot.as_record() != record or snapshot.sha256 != catalog_sha:
        raise ResidentMediaV10Error("catalog canonical reconstruction changed")
    if catalog.sha256 != catalog_sha:
        raise ResidentMediaV10Error("caller catalog digest changed")
    authorization = v5._validate_catalog_authorization(backend, catalog_sha)
    return _canonical_copy(record), catalog_sha, _canonical_copy(authorization)


class ProtectedMonotonicBackendV10(v9.ProtectedMonotonicBackendV9):
    """V9 backend plus one cross-session protected receipt namespace."""

    _ALLOWED_NAMESPACES = frozenset(
        set(v9.ProtectedMonotonicBackendV9._ALLOWED_NAMESPACES)
        | {"global_receipts_v10"}
    )

    def read_global_receipt_anchor(self, person_id: str) -> Mapping[str, Any] | None:
        return self._read("global_receipts_v10", v8._identifier(person_id, "person id"))

    def compare_and_swap_global_receipt_anchor(
        self,
        person_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        person_id = v8._identifier(person_id, "person id")
        clean = self._cas(
            "global_receipts_v10",
            person_id,
            expected_record_sha256,
            replacement,
        )
        return {
            "schema": "kira.protected_global_receipt_cas.v10",
            "protected_backend_identity_sha256": self.backend_identity_sha256,
            "person_id": person_id,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v8._record_sha(clean),
            "committed_generation": clean["generation"],
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_sessions": True,
            "exact_post_commit_readback_required": True,
        }


class ProtectedGlobalPresentationReceiptLedgerV10:
    """Validate catalog-bound evidence and consume receipts across sessions."""

    def __init__(
        self,
        *,
        person_id: str,
        catalog: v4.StimulusCatalog,
        protected_backend: ProtectedMonotonicBackendV10,
    ) -> None:
        if not isinstance(protected_backend, ProtectedMonotonicBackendV10):
            raise ResidentMediaV10Error("an explicit v10 protected backend is required")
        self.person_id = v8._identifier(person_id, "person id")
        self.backend = protected_backend
        self._lock = threading.RLock()
        (
            self._catalog_record,
            self._catalog_sha256,
            self._catalog_authorization,
        ) = _freeze_authorized_catalog(catalog, protected_backend)
        self._catalog_authorization_sha256 = v8._record_sha(
            self._catalog_authorization
        )

        existing = self.backend.read_global_receipt_anchor(self.person_id)
        if existing is None:
            self._anchor = self._build_anchor(
                generation=0,
                output_ids=[],
                decoder_receipts=[],
                records=[],
            )
            self._cas(None, self._anchor)
        else:
            self._anchor = _canonical_copy(existing)
            self._validate_anchor(self._anchor)

    @classmethod
    def open(cls, **kwargs: Any) -> "ProtectedGlobalPresentationReceiptLedgerV10":
        return cls(**kwargs)

    def _fresh_catalog_snapshot(self) -> v4.StimulusCatalog:
        # Reparse the frozen canonical record on every call.  Mutating a
        # caller-owned catalog, or even this instance's decoded record, cannot
        # silently retain the original digest.
        record = _canonical_copy(self._catalog_record)
        try:
            snapshot = v4.StimulusCatalog(record["manifests"])
        except (TypeError, ValueError, v4.ResidentMediaV4Error) as exc:
            raise ResidentMediaV10Error("frozen catalog record changed") from exc
        if snapshot.as_record() != record:
            raise ResidentMediaV10Error("frozen catalog record changed")
        if snapshot.sha256 != self._catalog_sha256:
            raise ResidentMediaV10Error("frozen catalog digest changed")
        if v5.validate_authoritative_catalog(snapshot) != self._catalog_sha256:
            raise ResidentMediaV10Error("authoritative catalog identity changed")
        authorization = v5._validate_catalog_authorization(
            self.backend, self._catalog_sha256
        )
        if authorization != self._catalog_authorization:
            raise ResidentMediaV10Error("protected catalog authorization changed")
        return snapshot

    def _build_anchor(
        self,
        *,
        generation: int,
        output_ids: list[str],
        decoder_receipts: list[str],
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema": "kira.resident_media_global_receipt_ledger.v10",
            "person_id": self.person_id,
            "generation": generation,
            "catalog_sha256": self._catalog_sha256,
            "catalog_authorization_sha256": self._catalog_authorization_sha256,
            "authoritative_source_policy_sha256": (
                v5.AUTHORITATIVE_SOURCE_POLICY_SHA256
            ),
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "used_output_receipt_ids": list(output_ids),
            "used_renderer_or_decoder_receipt_sha256s": list(decoder_receipts),
            "presentation_records": [_canonical_copy(item) for item in records],
            "global_across_sessions": True,
            "live_execution_allowed": False,
        }

    def _validate_anchor(self, value: Mapping[str, Any]) -> None:
        expected_keys = {
            "schema",
            "person_id",
            "generation",
            "catalog_sha256",
            "catalog_authorization_sha256",
            "authoritative_source_policy_sha256",
            "protected_backend_identity_sha256",
            "used_output_receipt_ids",
            "used_renderer_or_decoder_receipt_sha256s",
            "presentation_records",
            "global_across_sessions",
            "live_execution_allowed",
        }
        if set(value) != expected_keys:
            raise ResidentMediaV10Error("global receipt anchor shape changed")
        expected_fixed = {
            "schema": "kira.resident_media_global_receipt_ledger.v10",
            "person_id": self.person_id,
            "catalog_sha256": self._catalog_sha256,
            "catalog_authorization_sha256": self._catalog_authorization_sha256,
            "authoritative_source_policy_sha256": (
                v5.AUTHORITATIVE_SOURCE_POLICY_SHA256
            ),
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "global_across_sessions": True,
            "live_execution_allowed": False,
        }
        for key, expected in expected_fixed.items():
            if value.get(key) != expected:
                raise ResidentMediaV10Error(f"global receipt anchor binding changed:{key}")
        generation = value.get("generation")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ResidentMediaV10Error("global receipt generation is invalid")

        output_ids = value.get("used_output_receipt_ids")
        decoder_receipts = value.get("used_renderer_or_decoder_receipt_sha256s")
        records = value.get("presentation_records")
        if not isinstance(output_ids, list) or len(output_ids) > MAX_GLOBAL_RECEIPTS:
            raise ResidentMediaV10Error("global output-receipt list is invalid")
        if len(set(output_ids)) != len(output_ids):
            raise ResidentMediaV10Error("global output receipt replay is present")
        for item in output_ids:
            v8._identifier(item, "global output receipt id")
        if (
            not isinstance(decoder_receipts, list)
            or len(decoder_receipts) > MAX_GLOBAL_RECEIPTS
        ):
            raise ResidentMediaV10Error("global decoder-receipt list is invalid")
        if len(set(decoder_receipts)) != len(decoder_receipts):
            raise ResidentMediaV10Error("global decoder receipt replay is present")
        for item in decoder_receipts:
            v8._sha(item, "global renderer/decoder receipt")
        if not isinstance(records, list) or len(records) > MAX_GLOBAL_RECORDS:
            raise ResidentMediaV10Error("global presentation-record list is invalid")
        try:
            catalog = v4.StimulusCatalog(
                _canonical_copy(self._catalog_record)["manifests"]
            )
        except (KeyError, TypeError, ValueError, v4.ResidentMediaV4Error) as exc:
            raise ResidentMediaV10Error("frozen catalog record changed") from exc
        derived_output_ids: list[str] = []
        derived_decoder_receipts: list[str] = []
        for record in records:
            if not isinstance(record, Mapping) or set(record) != {
                "session_id",
                "stimulus_id",
                "ordinal",
                "source_manifest_sha256",
                "consumed_start_permit_sha256",
                "output_receipt_id",
                "renderer_or_decoder_receipt_sha256s",
                "presentation_evidence_sha256",
            }:
                raise ResidentMediaV10Error("global presentation record is invalid")
            v8._identifier(record["session_id"], "record session id")
            v8._identifier(record["stimulus_id"], "record stimulus id")
            ordinal = record["ordinal"]
            if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
                raise ResidentMediaV10Error("record ordinal is invalid")
            try:
                manifest = catalog.manifest(ordinal)
            except v4.ResidentMediaV4Error as exc:
                raise ResidentMediaV10Error("record ordinal escaped catalog") from exc
            if (
                record["stimulus_id"] != manifest["stimulus_id"]
                or record["source_manifest_sha256"]
                != catalog.manifest_sha256(ordinal)
            ):
                raise ResidentMediaV10Error("record source binding changed")
            v8._sha(record["source_manifest_sha256"], "record manifest")
            v8._sha(record["consumed_start_permit_sha256"], "record permit")
            v8._identifier(record["output_receipt_id"], "record output receipt")
            if not isinstance(record["renderer_or_decoder_receipt_sha256s"], list):
                raise ResidentMediaV10Error("record decoder receipts are invalid")
            for receipt in record["renderer_or_decoder_receipt_sha256s"]:
                v8._sha(receipt, "record renderer/decoder receipt")
            v8._sha(record["presentation_evidence_sha256"], "record evidence")
            derived_output_ids.append(record["output_receipt_id"])
            derived_decoder_receipts.extend(
                record["renderer_or_decoder_receipt_sha256s"]
            )
        if generation != len(records):
            raise ResidentMediaV10Error("global receipt generation/history changed")
        if output_ids != derived_output_ids:
            raise ResidentMediaV10Error("global output receipt history changed")
        if decoder_receipts != derived_decoder_receipts:
            raise ResidentMediaV10Error("global decoder receipt history changed")

    def _cas(
        self,
        previous: Mapping[str, Any] | None,
        replacement: Mapping[str, Any],
    ) -> None:
        previous_sha = v8._record_sha(previous) if previous is not None else None
        receipt = self.backend.compare_and_swap_global_receipt_anchor(
            self.person_id, previous_sha, replacement
        )
        expected = {
            "schema": "kira.protected_global_receipt_cas.v10",
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "person_id": self.person_id,
            "expected_previous_record_sha256": previous_sha,
            "replacement_record_sha256": v8._record_sha(replacement),
            "committed_generation": replacement["generation"],
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_sessions": True,
            "exact_post_commit_readback_required": True,
        }
        if dict(receipt) != expected:
            raise ResidentMediaV10Error("protected global receipt CAS changed")
        reopened = self.backend.read_global_receipt_anchor(self.person_id)
        if not isinstance(reopened, Mapping) or dict(reopened) != dict(replacement):
            raise ResidentMediaV10Error("protected global receipt anchor did not read back")

    def _assert_synced(self) -> None:
        reopened = self.backend.read_global_receipt_anchor(self.person_id)
        if not isinstance(reopened, Mapping) or dict(reopened) != self._anchor:
            raise ResidentMediaV10Error("global receipt anchor changed or rolled back")
        self._validate_anchor(self._anchor)

    def validate_and_consume(
        self,
        value: Mapping[str, Any],
        *,
        session_id: str,
        expected_manifest: Mapping[str, Any],
        consumed_start_permit_sha256: str,
    ) -> dict[str, Any]:
        with self._lock:
            self._assert_synced()
            catalog = self._fresh_catalog_snapshot()
            session_id = v8._identifier(session_id, "session id")
            if not isinstance(value, Mapping) or value.get("session_id") != session_id:
                raise ResidentMediaV10Error("presentation session binding changed")
            ordinal = value.get("ordinal")
            if isinstance(ordinal, bool) or not isinstance(ordinal, int):
                raise ResidentMediaV10Error("presentation ordinal is invalid")
            authoritative_manifest = catalog.manifest(ordinal)
            if _canonical_copy(expected_manifest) != authoritative_manifest:
                raise ResidentMediaV10Error("caller expected manifest is not authoritative")

            clean = v9.validate_presentation_evidence_v9(
                value,
                session_id=session_id,
                person_id=self.person_id,
                expected_manifest=authoritative_manifest,
                consumed_start_permit_sha256=consumed_start_permit_sha256,
            )
            output_ids = list(self._anchor["used_output_receipt_ids"])
            decoder_receipts = list(
                self._anchor["used_renderer_or_decoder_receipt_sha256s"]
            )
            if clean["output_receipt_id"] in output_ids:
                raise ResidentMediaV10Error(
                    "output receipt identity was already consumed globally"
                )
            if any(
                receipt in decoder_receipts
                for receipt in clean["renderer_or_decoder_receipt_sha256s"]
            ):
                raise ResidentMediaV10Error(
                    "renderer/decoder receipt identity was already consumed globally"
                )
            if (
                len(output_ids) + 1 > MAX_GLOBAL_RECEIPTS
                or len(decoder_receipts)
                + len(clean["renderer_or_decoder_receipt_sha256s"])
                > MAX_GLOBAL_RECEIPTS
            ):
                raise ResidentMediaV10Error("global receipt ledger capacity exceeded")
            records = list(self._anchor["presentation_records"])
            if len(records) + 1 > MAX_GLOBAL_RECORDS:
                raise ResidentMediaV10Error("global presentation ledger capacity exceeded")

            output_ids.append(clean["output_receipt_id"])
            decoder_receipts.extend(clean["renderer_or_decoder_receipt_sha256s"])
            records.append(
                {
                    "session_id": session_id,
                    "stimulus_id": clean["stimulus_id"],
                    "ordinal": clean["ordinal"],
                    "source_manifest_sha256": clean["source_manifest_sha256"],
                    "consumed_start_permit_sha256": clean[
                        "consumed_start_permit_sha256"
                    ],
                    "output_receipt_id": clean["output_receipt_id"],
                    "renderer_or_decoder_receipt_sha256s": clean[
                        "renderer_or_decoder_receipt_sha256s"
                    ],
                    "presentation_evidence_sha256": v8._record_sha(clean),
                }
            )
            replacement = self._build_anchor(
                generation=self._anchor["generation"] + 1,
                output_ids=output_ids,
                decoder_receipts=decoder_receipts,
                records=records,
            )
            self._validate_anchor(replacement)
            self._cas(self._anchor, replacement)
            self._anchor = replacement
            return clean

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._assert_synced()
            self._fresh_catalog_snapshot()
            return {
                "schema": "kira.resident_media_global_receipt_snapshot.v10",
                "person_id": self.person_id,
                "generation": self._anchor["generation"],
                "catalog_sha256": self._catalog_sha256,
                "used_output_receipt_count": len(
                    self._anchor["used_output_receipt_ids"]
                ),
                "used_renderer_or_decoder_receipt_count": len(
                    self._anchor["used_renderer_or_decoder_receipt_sha256s"]
                ),
                "presentation_record_count": len(
                    self._anchor["presentation_records"]
                ),
                "global_across_sessions": True,
                "catalog_authorized_by_protected_backend": True,
                "live_execution_allowed": False,
            }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_static_summary.v10",
        "status": "DISCONNECTED_STATIC_CANDIDATE_PENDING_FRESH_AUDIT",
        "v9_per_required_role_validation_reused": True,
        "exact_v5_owner_selected_catalog_required": True,
        "protected_catalog_authorization_read_each_consume": True,
        "caller_catalog_retained": False,
        "global_cross_session_output_receipt_one_use": True,
        "global_cross_session_decoder_receipt_one_use": True,
        "live_execution_allowed": False,
        "person_saw_or_heard_claimed": False,
        "person_enjoyed_or_remembered_claimed": False,
    }


__all__ = [
    "ProtectedGlobalPresentationReceiptLedgerV10",
    "ProtectedMonotonicBackendV10",
    "ResidentMediaV10Error",
    "static_contract_summary",
]
