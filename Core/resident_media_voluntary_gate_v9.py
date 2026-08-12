"""Append-only resident-media v9 presentation-evidence repair.

V8 was rejected because it combined coverage across derivative roles and
because a caller could replay an output/decoder receipt after changing only a
wrapper digest.  This static successor validates every required role
independently and consumes receipt identities through an external protected
monotonic CAS authority before returning an accepted record.

It does not open media, call a model, control a person, or promote v9 into the
live resident-media session.  A later audited adapter is still required.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v8 as v8


class ResidentMediaV9Error(v8.ResidentMediaV8Error):
    """Raised when v9 evidence or protected receipt state is not exact."""


MAX_SEGMENTS = 256
MAX_RECORDS = 512
MAX_RECEIPTS = 2048

_EVIDENCE_KEYS = {
    "schema", "session_id", "person_id", "stimulus_id", "ordinal",
    "source_manifest", "source_manifest_sha256",
    "consumed_start_permit_sha256", "output_receipt_id", "output_surface_id",
    "presented_at_utc", "presentation_segments", "engineering_output_completed",
    "presentation_complete_for_manifest", "full_source_experienced",
    "person_attention_claimed", "person_saw_or_heard_claimed",
    "automatic_memory_created", "automatic_preference_created",
    "external_parent_observation_sha256",
}

_SEGMENT_KEYS = {
    "sequence", "page_number", "track_number", "source_start_ms",
    "source_end_ms", "output_start_monotonic_ns", "output_end_monotonic_ns",
    "actual_visual_output", "actual_audio_output", "actual_text_output",
    "derivative_role", "derivative_sha256",
    "renderer_or_decoder_receipt_sha256",
}


def _canonical_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(v8._canonical(dict(value)).decode("utf-8"))


def _required_roles(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    roles = {item["role"] for item in manifest["derivatives"]}
    kind = manifest["media_kind"]
    if kind == "PAGE":
        required = ("rendered_page_png",)
    elif kind == "AUDIO_TRACK":
        required = ("synchronized_audio_pcm",)
    elif kind == "VIDEO_INTERVAL":
        required_list = ["timed_frame_manifest", "synchronized_audio_pcm"]
        if "caption_text_utf8" in roles:
            required_list.append("caption_text_utf8")
        required = tuple(required_list)
    else:
        raise ResidentMediaV9Error("presentation media kind is unsupported")
    missing = [role for role in required if role not in roles]
    if missing:
        raise ResidentMediaV9Error("presentation manifest lacks a required derivative role")
    return required


def _role_complete(
    intervals: list[tuple[int, int]], *, start_ms: int, end_ms: int
) -> bool:
    if not intervals:
        return False
    cursor = start_ms
    for start, end in sorted(intervals):
        if start > cursor:
            return False
        cursor = max(cursor, end)
    return cursor == end_ms


def validate_presentation_evidence_v9(
    value: Mapping[str, Any],
    *,
    session_id: str,
    person_id: str,
    expected_manifest: Mapping[str, Any],
    consumed_start_permit_sha256: str,
) -> dict[str, Any]:
    """Validate source/output truth with independent required-role coverage."""

    v8._exact(value, _EVIDENCE_KEYS, "v9 presentation evidence")
    if value.get("schema") != "kira.resident_media_exact_presentation_evidence.v9":
        raise ResidentMediaV9Error("presentation evidence schema changed")
    session_id = v8._identifier(session_id, "session id")
    person_id = v8._identifier(person_id, "person id")
    if value.get("session_id") != session_id or value.get("person_id") != person_id:
        raise ResidentMediaV9Error("presentation session/person binding changed")

    manifest = v4.validate_source_manifest(expected_manifest)
    supplied = v4.validate_source_manifest(value.get("source_manifest"))
    if supplied != manifest:
        raise ResidentMediaV9Error("presentation exact source manifest changed")
    manifest_sha = v4.sha256_record(manifest)
    if value.get("source_manifest_sha256") != manifest_sha:
        raise ResidentMediaV9Error("presentation source manifest digest changed")
    if value.get("stimulus_id") != manifest["stimulus_id"]:
        raise ResidentMediaV9Error("presentation stimulus identity changed")
    ordinal = v8._nonnegative_int(value.get("ordinal"), "presentation ordinal")
    permit_sha = v8._sha(consumed_start_permit_sha256, "consumed start permit")
    if value.get("consumed_start_permit_sha256") != permit_sha:
        raise ResidentMediaV9Error("presentation start-permit binding changed")
    output_receipt_id = v8._identifier(value.get("output_receipt_id"), "output receipt id")
    v8._identifier(value.get("output_surface_id"), "output surface id")
    v8._utc(value.get("presented_at_utc"), "presented_at_utc")
    v8._sha(value.get("external_parent_observation_sha256"), "external observation")

    boolean_fields = (
        "engineering_output_completed", "presentation_complete_for_manifest",
        "full_source_experienced", "person_attention_claimed",
        "person_saw_or_heard_claimed", "automatic_memory_created",
        "automatic_preference_created",
    )
    for field in boolean_fields:
        if not isinstance(value.get(field), bool):
            raise ResidentMediaV9Error(f"{field} must be boolean")
    if any(value[field] for field in boolean_fields[2:]):
        raise ResidentMediaV9Error(
            "engineering evidence cannot claim experience, attention, memory, or preference"
        )

    segments = value.get("presentation_segments")
    if not isinstance(segments, list) or not 1 <= len(segments) <= MAX_SEGMENTS:
        raise ResidentMediaV9Error("presentation segments are missing or unbounded")
    derivatives = {item["role"]: item for item in manifest["derivatives"]}
    required_roles = _required_roles(manifest)
    kind = manifest["media_kind"]
    coordinates = manifest["coordinates"]
    prior_output_end: dict[str, int] = {}
    intervals_by_role: dict[str, list[tuple[int, int]]] = {
        role: [] for role in required_roles
    }
    renderer_receipts: list[str] = []
    clean_segments: list[dict[str, Any]] = []

    for expected_sequence, segment in enumerate(segments):
        v8._exact(segment, _SEGMENT_KEYS, f"v9 presentation segment {expected_sequence}")
        if segment.get("sequence") != expected_sequence:
            raise ResidentMediaV9Error("presentation segment sequence is not contiguous")
        output_start = v8._nonnegative_int(
            segment.get("output_start_monotonic_ns"), "output start"
        )
        output_end = v8._nonnegative_int(
            segment.get("output_end_monotonic_ns"), "output end"
        )
        if output_end <= output_start:
            raise ResidentMediaV9Error("presentation output time is empty or reversed")
        visual = segment.get("actual_visual_output")
        audio = segment.get("actual_audio_output")
        text = segment.get("actual_text_output")
        if any(not isinstance(flag, bool) for flag in (visual, audio, text)):
            raise ResidentMediaV9Error("presentation modalities must be boolean")
        if not (visual or audio or text):
            raise ResidentMediaV9Error("presentation segment has no actual output")
        role = v8._identifier(segment.get("derivative_role"), "derivative role")
        derivative = derivatives.get(role)
        if derivative is None or segment.get("derivative_sha256") != derivative["sha256"]:
            raise ResidentMediaV9Error("presentation derivative identity changed")
        if role not in required_roles:
            raise ResidentMediaV9Error("presentation used a non-required derivative role")
        if output_start <= prior_output_end.get(role, -1):
            raise ResidentMediaV9Error("presentation output time is not monotonic per role")
        prior_output_end[role] = output_end
        receipt = v8._sha(
            segment.get("renderer_or_decoder_receipt_sha256"),
            "renderer/decoder receipt",
        )
        if receipt in renderer_receipts:
            raise ResidentMediaV9Error("renderer/decoder receipt is reused within evidence")
        renderer_receipts.append(receipt)

        page = segment.get("page_number")
        track = segment.get("track_number")
        start = segment.get("source_start_ms")
        end = segment.get("source_end_ms")
        if kind == "PAGE":
            if (
                page != coordinates["page_number"]
                or track is not None
                or start is not None
                or end is not None
                or role != "rendered_page_png"
                or not visual
                or audio
                or text
            ):
                raise ResidentMediaV9Error("page coordinates, role, or modality changed")
        else:
            start_i = v8._nonnegative_int(start, "segment source start")
            end_i = v8._nonnegative_int(end, "segment source end")
            if (
                end_i <= start_i
                or start_i < coordinates["start_ms"]
                or end_i > coordinates["end_ms"]
            ):
                raise ResidentMediaV9Error("presentation segment escaped its source interval")
            if kind == "VIDEO_INTERVAL":
                if page is not None or track is not None:
                    raise ResidentMediaV9Error("video presentation gained page/track coordinates")
                expected_modalities = {
                    "timed_frame_manifest": (True, False, False),
                    "synchronized_audio_pcm": (False, True, False),
                    "caption_text_utf8": (True, False, True),
                }
                if (visual, audio, text) != expected_modalities[role]:
                    raise ResidentMediaV9Error("video role modality changed")
            else:
                if (
                    page is not None
                    or track != coordinates["track_number"]
                    or role != "synchronized_audio_pcm"
                    or (visual, audio, text) != (False, True, False)
                ):
                    raise ResidentMediaV9Error("audio track coordinates, role, or modality changed")
            intervals_by_role[role].append((start_i, end_i))
        clean_segments.append(_canonical_copy(segment))

    if kind == "PAGE":
        complete_by_role = {"rendered_page_png": bool(clean_segments)}
    else:
        complete_by_role = {
            role: _role_complete(
                intervals_by_role[role],
                start_ms=coordinates["start_ms"],
                end_ms=coordinates["end_ms"],
            )
            for role in required_roles
        }
    complete = all(complete_by_role.values())
    if value.get("presentation_complete_for_manifest") is not complete:
        raise ResidentMediaV9Error("declared completeness differs from per-role coverage")
    if value.get("engineering_output_completed") is not complete:
        raise ResidentMediaV9Error("engineering completion differs from per-role coverage")

    clean = _canonical_copy(value)
    clean["ordinal"] = ordinal
    clean["presentation_segments"] = clean_segments
    clean["required_roles"] = list(required_roles)
    clean["complete_by_required_role"] = complete_by_role
    clean["output_receipt_id"] = output_receipt_id
    clean["renderer_or_decoder_receipt_sha256s"] = renderer_receipts
    clean["evidence_sha256"] = v8._record_sha(clean)
    return clean


class ProtectedMonotonicBackendV9(v8.ProtectedMonotonicBackendV8):
    """V8 backend plus one protected v9 receipt-ledger namespace."""

    _ALLOWED_NAMESPACES = frozenset(
        set(v8.ProtectedMonotonicBackendV8._ALLOWED_NAMESPACES) | {"session_v9"}
    )

    def read_v9_anchor(self, session_id: str) -> Mapping[str, Any] | None:
        return self._read("session_v9", v8._identifier(session_id, "session id"))

    def compare_and_swap_v9_anchor(
        self,
        session_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        clean = self._cas(
            "session_v9",
            v8._identifier(session_id, "session id"),
            expected_record_sha256,
            replacement,
        )
        return {
            "schema": "kira.protected_anchor_v9_cas_receipt.v9",
            "protected_backend_identity_sha256": self.backend_identity_sha256,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v8._record_sha(clean),
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }


class ProtectedPresentationReceiptLedgerV9:
    """Consume exact output and decoder receipts before accepting evidence."""

    def __init__(
        self,
        *,
        session_id: str,
        person_id: str,
        catalog: v4.StimulusCatalog,
        protected_backend: ProtectedMonotonicBackendV9,
        create: bool,
    ) -> None:
        if not isinstance(protected_backend, ProtectedMonotonicBackendV9):
            raise ResidentMediaV9Error("v9 requires its protected monotonic backend")
        self.session_id = v8._identifier(session_id, "session id")
        self.person_id = v8._identifier(person_id, "person id")
        if not isinstance(catalog, v4.StimulusCatalog):
            raise ResidentMediaV9Error("v9 requires the exact accepted stimulus catalog")
        self.catalog = catalog
        self.catalog_sha256 = v8._sha(catalog.sha256, "catalog digest")
        self.backend = protected_backend
        if create:
            if self.backend.read_v9_anchor(self.session_id) is not None:
                raise ResidentMediaV9Error("protected v9 receipt ledger already exists")
            self._anchor = self._build_anchor(0, [], [], [])
            self._cas(None, self._anchor)
        else:
            value = self.backend.read_v9_anchor(self.session_id)
            if not isinstance(value, Mapping):
                raise ResidentMediaV9Error("protected v9 receipt ledger is missing")
            self._anchor = dict(value)
            self._validate_anchor(self._anchor)

    @classmethod
    def create(cls, **kwargs: Any) -> "ProtectedPresentationReceiptLedgerV9":
        return cls(create=True, **kwargs)

    @classmethod
    def restore(cls, **kwargs: Any) -> "ProtectedPresentationReceiptLedgerV9":
        return cls(create=False, **kwargs)

    def _build_anchor(
        self,
        generation: int,
        output_ids: list[str],
        decoder_receipts: list[str],
        records: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema": "kira.resident_media_protected_receipt_ledger.v9",
            "session_id": self.session_id,
            "person_id": self.person_id,
            "catalog_sha256": self.catalog_sha256,
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "generation": generation,
            "used_output_receipt_ids": list(output_ids),
            "used_renderer_or_decoder_receipt_sha256s": list(decoder_receipts),
            "presentation_records": [deepcopy(dict(item)) for item in records],
            "live_execution_allowed": False,
        }

    def _validate_anchor(self, value: Mapping[str, Any]) -> None:
        v8._exact(
            value,
            {
                "schema", "session_id", "person_id", "catalog_sha256",
                "protected_backend_identity_sha256", "generation",
                "used_output_receipt_ids",
                "used_renderer_or_decoder_receipt_sha256s",
                "presentation_records", "live_execution_allowed",
            },
            "v9 protected receipt ledger",
        )
        expected = {
            "schema": "kira.resident_media_protected_receipt_ledger.v9",
            "session_id": self.session_id,
            "person_id": self.person_id,
            "catalog_sha256": self.catalog_sha256,
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "live_execution_allowed": False,
        }
        if any(value.get(field) != wanted for field, wanted in expected.items()):
            raise ResidentMediaV9Error("v9 protected receipt-ledger binding changed")
        v8._nonnegative_int(value.get("generation"), "v9 generation")
        output_ids = value.get("used_output_receipt_ids")
        decoder_receipts = value.get("used_renderer_or_decoder_receipt_sha256s")
        records = value.get("presentation_records")
        if not isinstance(output_ids, list) or len(output_ids) > MAX_RECEIPTS:
            raise ResidentMediaV9Error("v9 output-receipt ledger is invalid")
        if len(set(output_ids)) != len(output_ids):
            raise ResidentMediaV9Error("v9 output-receipt ledger contains replay")
        for item in output_ids:
            v8._identifier(item, "used output receipt id")
        if not isinstance(decoder_receipts, list) or len(decoder_receipts) > MAX_RECEIPTS:
            raise ResidentMediaV9Error("v9 decoder-receipt ledger is invalid")
        if len(set(decoder_receipts)) != len(decoder_receipts):
            raise ResidentMediaV9Error("v9 decoder-receipt ledger contains replay")
        for item in decoder_receipts:
            v8._sha(item, "used renderer/decoder receipt")
        if not isinstance(records, list) or len(records) > MAX_RECORDS:
            raise ResidentMediaV9Error("v9 presentation-record ledger is invalid")
        for item in records:
            v8._exact(
                item,
                {
                    "evidence_sha256", "stimulus_id", "ordinal",
                    "consumed_start_permit_sha256", "output_receipt_id",
                    "renderer_or_decoder_receipt_sha256s",
                    "presentation_complete_for_manifest",
                },
                "v9 presentation receipt record",
            )
            v8._sha(item["evidence_sha256"], "record evidence digest")
            v8._identifier(item["stimulus_id"], "record stimulus id")
            v8._nonnegative_int(item["ordinal"], "record ordinal")
            v8._sha(item["consumed_start_permit_sha256"], "record start permit")
            v8._identifier(item["output_receipt_id"], "record output receipt")
            if not isinstance(item["presentation_complete_for_manifest"], bool):
                raise ResidentMediaV9Error("record completeness must be boolean")
            if not isinstance(item["renderer_or_decoder_receipt_sha256s"], list):
                raise ResidentMediaV9Error("record decoder receipts must be a list")
            for receipt in item["renderer_or_decoder_receipt_sha256s"]:
                v8._sha(receipt, "record renderer/decoder receipt")

    def _cas(self, previous: Mapping[str, Any] | None, replacement: Mapping[str, Any]) -> None:
        previous_sha = None if previous is None else v8._record_sha(previous)
        receipt = self.backend.compare_and_swap_v9_anchor(
            self.session_id, previous_sha, replacement
        )
        expected = {
            "schema": "kira.protected_anchor_v9_cas_receipt.v9",
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "expected_previous_record_sha256": previous_sha,
            "replacement_record_sha256": v8._record_sha(replacement),
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }
        if dict(receipt) != expected:
            raise ResidentMediaV9Error("protected v9 CAS receipt changed")
        reopened = self.backend.read_v9_anchor(self.session_id)
        if not isinstance(reopened, Mapping) or dict(reopened) != dict(replacement):
            raise ResidentMediaV9Error("protected v9 receipt ledger did not read back exactly")

    def _assert_synced(self) -> None:
        reopened = self.backend.read_v9_anchor(self.session_id)
        if not isinstance(reopened, Mapping) or dict(reopened) != self._anchor:
            raise ResidentMediaV9Error("protected v9 receipt ledger changed or rolled back")
        self._validate_anchor(self._anchor)

    def validate_and_consume(
        self,
        value: Mapping[str, Any],
        *,
        expected_manifest: Mapping[str, Any],
        consumed_start_permit_sha256: str,
    ) -> dict[str, Any]:
        self._assert_synced()
        clean = validate_presentation_evidence_v9(
            value,
            session_id=self.session_id,
            person_id=self.person_id,
            expected_manifest=expected_manifest,
            consumed_start_permit_sha256=consumed_start_permit_sha256,
        )
        try:
            catalog_manifest = self.catalog.manifest(clean["ordinal"])
        except Exception as exc:
            raise ResidentMediaV9Error("presentation ordinal is not in the accepted catalog") from exc
        if v4.validate_source_manifest(catalog_manifest) != v4.validate_source_manifest(
            expected_manifest
        ):
            raise ResidentMediaV9Error("expected manifest is not the exact catalog ordinal")
        output_ids = list(self._anchor["used_output_receipt_ids"])
        decoder_receipts = list(
            self._anchor["used_renderer_or_decoder_receipt_sha256s"]
        )
        if clean["output_receipt_id"] in output_ids:
            raise ResidentMediaV9Error("output receipt identity was already consumed")
        if any(
            receipt in decoder_receipts
            for receipt in clean["renderer_or_decoder_receipt_sha256s"]
        ):
            raise ResidentMediaV9Error("renderer/decoder receipt identity was already consumed")
        output_ids.append(clean["output_receipt_id"])
        decoder_receipts.extend(clean["renderer_or_decoder_receipt_sha256s"])
        records = list(self._anchor["presentation_records"])
        records.append(
            {
                "evidence_sha256": clean["evidence_sha256"],
                "stimulus_id": clean["stimulus_id"],
                "ordinal": clean["ordinal"],
                "consumed_start_permit_sha256": clean["consumed_start_permit_sha256"],
                "output_receipt_id": clean["output_receipt_id"],
                "renderer_or_decoder_receipt_sha256s": clean[
                    "renderer_or_decoder_receipt_sha256s"
                ],
                "presentation_complete_for_manifest": clean[
                    "presentation_complete_for_manifest"
                ],
            }
        )
        replacement = self._build_anchor(
            self._anchor["generation"] + 1,
            output_ids,
            decoder_receipts,
            records,
        )
        self._validate_anchor(replacement)
        self._cas(self._anchor, replacement)
        self._anchor = replacement
        return deepcopy(clean)

    def snapshot(self) -> dict[str, Any]:
        self._assert_synced()
        return {
            "schema": "kira.resident_media_receipt_ledger_snapshot.v9",
            "session_id": self.session_id,
            "person_id": self.person_id,
            "generation": self._anchor["generation"],
            "used_output_receipt_count": len(self._anchor["used_output_receipt_ids"]),
            "used_renderer_or_decoder_receipt_count": len(
                self._anchor["used_renderer_or_decoder_receipt_sha256s"]
            ),
            "presentation_record_count": len(self._anchor["presentation_records"]),
            "protected_monotonic_backend_required": True,
            "live_execution_allowed": False,
        }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_static_contract.v9",
        "required_role_coverage_is_independent": True,
        "caption_coverage_required_when_manifest_contains_captions": True,
        "output_receipt_identity_one_use": True,
        "renderer_decoder_receipt_identity_one_use": True,
        "wrapper_digest_change_cannot_rearm_receipts": True,
        "protected_monotonic_cas_and_readback_required": True,
        "full_source_experienced": False,
        "live_execution_allowed": False,
        "live_media_adapter_connected": False,
        "fresh_independent_audit_required": True,
    }
