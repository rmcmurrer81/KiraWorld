"""Static v8 resident-media integration boundary.

V8 preserves the sealed v2-v7 choice and policy work.  It adds three pieces
that were intentionally absent from v7:

* an adapter to an external atomic monotonic authority, with exact read-back
  and no local-file/in-memory production fallback;
* media-kind-specific presentation-span validation bound to the exact source
  manifest, consumed start permit, output derivative, and monotonic time; and
* a supervised exact-Qwen response adapter that binds the raw/final response
  and timing evidence to the current one-use v7 challenge.

This module does not open, decode, render, display, or play media.  It does not
call a model, activate a person, create memory or preference, or authorize a
live session.  A protected authority implementation and a presentation/model
supervisor can be connected only by a later, separately audited harness.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v6 as v6
from Core import resident_media_voluntary_gate_v7 as v7


EXACT_MODEL = v7.EXACT_MODEL
EXACT_DIGEST = v7.EXACT_DIGEST
PERSON_ID = v7.PERSON_ID
MAX_V8_RESPONSES = 64
MAX_V8_PRESENTATION_RECORDS = 64


class ResidentMediaV8Error(ValueError):
    """The static v8 protected/evidence/response boundary failed closed."""


def semantic_choice_v8(text: str, phase: str) -> str:
    """V7 exact surfaces extended to explicit post-stimulus phases.

    V7 deliberately recognized only ``INVITATION`` and ``RECHECK``.  The
    inherited state machine also issues ``AFTER_<stimulus_id>`` phases between
    items.  V8 treats those as continuation phases while retaining the same
    refusal-dominant, no-discarded-semantics surface.
    """

    if not isinstance(phase, str) or not (
        phase in {"INVITATION", "RECHECK"} or phase.startswith("AFTER_")
    ):
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    if not isinstance(text, str) or not text.strip():
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    negative = v7._negative_projection(text)
    invitation = phase == "INVITATION"
    if v6._REFUSAL.search(negative):
        return "NO" if invitation else "STOP"
    if v6._PAUSE.search(negative):
        return "AMBIGUOUS_REQUIRES_NEW_TURN" if invitation else "PAUSE"
    surface = v7._strict_surface(text)
    if surface is None:
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    canonical = v7._SURFACE_CANONICAL.get(surface, surface)
    allowlist = v6._INVITATION_POSITIVE if invitation else v6._CONTINUE_POSITIVE
    if canonical in allowlist:
        return "YES" if invitation else "CONTINUE"
    return "AMBIGUOUS_REQUIRES_NEW_TURN"


class _V8ChoiceSurfaceSession(v7.HardenedVoluntaryMediaSessionV7):
    """Internal sealed-v7 subclass adding only the missing AFTER phase."""

    def _validate_response(
        self,
        response: Mapping[str, Any],
        challenge: Mapping[str, Any],
        now_utc: datetime,
        now_mono: int,
    ) -> tuple[dict[str, Any], str]:
        if not isinstance(response, Mapping):
            raise ResidentMediaV8Error("v8 choice response must be an object")
        phase = str(challenge.get("phase") or "")
        raw_decision = semantic_choice_v8(response.get("raw_reply"), phase)
        final_decision = semantic_choice_v8(response.get("final_reply"), phase)
        if raw_decision.startswith("AMBIGUOUS") or final_decision.startswith("AMBIGUOUS"):
            raise ResidentMediaV8Error("v8 choice contains unapproved or ambiguous semantic content")
        if raw_decision != final_decision or response.get("choice") != raw_decision:
            raise ResidentMediaV8Error("v8 raw/final/structured choice disagree")
        try:
            clean, inherited_decision = v6.HardenedVoluntaryMediaSessionV6._validate_response(
                self, response, challenge, now_utc, now_mono
            )
        except v6.ResidentMediaV6Error as exc:
            raise ResidentMediaV8Error(str(exc)) from exc
        if inherited_decision != raw_decision:
            raise ResidentMediaV8Error("v8/v6 semantic decision mismatch")
        return clean, raw_decision


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ResidentMediaV8Error("value is not strict canonical JSON") from exc


def _record_sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(dict(value))).hexdigest()


def _sha(value: Any, field: str, *, nonzero: bool = True) -> str:
    text = str(value or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise ResidentMediaV8Error(f"{field} must be SHA-256")
    if nonzero and text == "0" * 64:
        raise ResidentMediaV8Error(f"{field} cannot be the zero digest")
    return text


def _identifier(value: Any, field: str) -> str:
    text = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}", text):
        raise ResidentMediaV8Error(f"{field} is not a canonical identifier")
    return text


def _exact(value: Mapping[str, Any], keys: set[str], field: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ResidentMediaV8Error(f"{field} keys changed")


def _utc(value: Any, field: str) -> datetime:
    text = str(value or "")
    if not text.endswith("Z"):
        raise ResidentMediaV8Error(f"{field} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ResidentMediaV8Error(f"{field} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ResidentMediaV8Error(f"{field} must be UTC")
    return parsed


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ResidentMediaV8Error(f"{field} must be a nonnegative integer")
    return value


class ProtectedMonotonicAuthorityV8(ABC):
    """External trust-root contract used by the concrete v8 backend adapter.

    The authority, not this process, owns atomic CAS, monotonic generation,
    and rollback resistance.  A caller cannot substitute local JSON or a
    dictionary: the adapter requires this exact interface and exact receipts.
    """

    @property
    @abstractmethod
    def backend_identity_sha256(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_record(self, namespace: str, record_key: str) -> Mapping[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def compare_and_swap_record(
        self,
        *,
        namespace: str,
        record_key: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        raise NotImplementedError


class ProtectedMonotonicBackendV8(v6.ProtectedAnchorBackendV6):
    """Exact v5/v6/v8 adapter over an external protected monotonic authority."""

    _ALLOWED_NAMESPACES = frozenset({"catalog_v5", "session_v5", "session_v6", "session_v8"})

    def __init__(self, authority: ProtectedMonotonicAuthorityV8) -> None:
        if not isinstance(authority, ProtectedMonotonicAuthorityV8):
            raise ResidentMediaV8Error("an external v8 protected monotonic authority is required")
        self._authority = authority
        self._identity = _sha(authority.backend_identity_sha256, "authority identity")

    @property
    def backend_identity_sha256(self) -> str:
        return self._identity

    def _read(self, namespace: str, record_key: str) -> dict[str, Any] | None:
        if namespace not in self._ALLOWED_NAMESPACES:
            raise ResidentMediaV8Error("protected namespace is not allowed")
        value = self._authority.read_record(namespace, record_key)
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ResidentMediaV8Error("protected authority returned a non-object")
        return json.loads(_canonical(dict(value)).decode("utf-8"))

    def _cas(
        self,
        namespace: str,
        record_key: str,
        expected_sha: str | None,
        replacement: Mapping[str, Any],
    ) -> dict[str, Any]:
        if namespace not in self._ALLOWED_NAMESPACES:
            raise ResidentMediaV8Error("protected namespace is not allowed")
        clean = json.loads(_canonical(dict(replacement)).decode("utf-8"))
        replacement_sha = _record_sha(clean)
        generation = _nonnegative_int(clean.get("generation"), "protected replacement generation")
        if expected_sha is not None:
            expected_sha = _sha(expected_sha, "expected protected record")
        receipt = self._authority.compare_and_swap_record(
            namespace=namespace,
            record_key=record_key,
            expected_record_sha256=expected_sha,
            replacement=clean,
        )
        expected_receipt = {
            "schema": "kira.protected_monotonic_cas_receipt.v8",
            "protected_backend_identity_sha256": self._identity,
            "namespace": namespace,
            "record_key": record_key,
            "expected_previous_record_sha256": expected_sha,
            "replacement_record_sha256": replacement_sha,
            "committed_generation": generation,
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }
        if not isinstance(receipt, Mapping) or dict(receipt) != expected_receipt:
            raise ResidentMediaV8Error("protected authority CAS receipt is invalid")
        reopened = self._read(namespace, record_key)
        if reopened != clean:
            raise ResidentMediaV8Error("protected authority replacement did not read back exactly")
        return clean

    def read_catalog_authorization(self, catalog_sha256: str) -> Mapping[str, Any] | None:
        return self._read("catalog_v5", _sha(catalog_sha256, "catalog digest"))

    def read_session_anchor(self, session_id: str) -> Mapping[str, Any] | None:
        return self._read("session_v5", _identifier(session_id, "session id"))

    def compare_and_swap_session(
        self,
        session_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        clean = self._cas("session_v5", _identifier(session_id, "session id"), expected_record_sha256, replacement)
        return {
            "schema": "kira.protected_anchor_cas_receipt.v5",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": _record_sha(clean),
            "atomic_compare_and_swap": True,
            "rollback_domain_separate_from_local_ledgers": True,
        }

    def read_v6_anchor(self, session_id: str) -> Mapping[str, Any] | None:
        return self._read("session_v6", _identifier(session_id, "session id"))

    def compare_and_swap_v6_anchor(
        self,
        session_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        clean = self._cas("session_v6", _identifier(session_id, "session id"), expected_record_sha256, replacement)
        return {
            "schema": "kira.protected_anchor_v6_cas_receipt.v6",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": _record_sha(clean),
            "atomic_compare_and_swap": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }

    def read_v8_anchor(self, session_id: str) -> Mapping[str, Any] | None:
        return self._read("session_v8", _identifier(session_id, "session id"))

    def compare_and_swap_v8_anchor(
        self,
        session_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        clean = self._cas("session_v8", _identifier(session_id, "session id"), expected_record_sha256, replacement)
        return {
            "schema": "kira.protected_anchor_v8_cas_receipt.v8",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": _record_sha(clean),
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }


def adapt_supervised_choice_response_v8(
    run_receipt: Mapping[str, Any], challenge: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    """Validate a supervised result and return the exact v6 response object.

    This adapter consumes evidence supplied by a later supervisor.  It never
    calls Qwen and cannot make an ambiguous response affirmative.
    """

    _exact(
        run_receipt,
        {
            "schema", "session_id", "person_id", "challenge_sha256",
            "challenge_nonce", "model_name", "model_digest", "model_call_count",
            "normal_model_route", "fallback_used", "prompt_sha256", "raw_reply",
            "final_reply", "transformations", "submitted_at_utc",
            "first_token_at_utc", "text_complete_at_utc",
            "supervisor_process_identity_sha256", "external_parent_observation_sha256",
        },
        "supervised response receipt",
    )
    if run_receipt.get("schema") != "kira.resident_media_supervised_response.v8":
        raise ResidentMediaV8Error("supervised response schema changed")
    bindings = {
        "session_id": challenge.get("session_id"),
        "person_id": challenge.get("person_id"),
        "challenge_sha256": v6._record_sha(challenge),
        "challenge_nonce": challenge.get("nonce"),
        "prompt_sha256": challenge.get("prompt_sha256"),
    }
    for field, expected in bindings.items():
        if run_receipt.get(field) != expected:
            raise ResidentMediaV8Error(f"supervised response binding changed: {field}")
    if run_receipt.get("model_name") != EXACT_MODEL or str(
        run_receipt.get("model_digest") or ""
    ).lower() != EXACT_DIGEST:
        raise ResidentMediaV8Error("supervised response did not use exact Qwen")
    if run_receipt.get("model_call_count") != 1 or run_receipt.get("normal_model_route") is not True:
        raise ResidentMediaV8Error("supervised response requires one normal model call")
    if run_receipt.get("fallback_used") is not False:
        raise ResidentMediaV8Error("fallback cannot decide a resident-media choice")
    raw = run_receipt.get("raw_reply")
    final = run_receipt.get("final_reply")
    if not isinstance(raw, str) or not raw.strip() or not isinstance(final, str) or not final.strip():
        raise ResidentMediaV8Error("supervised raw/final response is missing")
    transformations = run_receipt.get("transformations")
    if not isinstance(transformations, list) or len(transformations) > 32 or any(
        not isinstance(item, Mapping) for item in transformations
    ):
        raise ResidentMediaV8Error("supervised transformations are malformed")
    submitted = _utc(run_receipt.get("submitted_at_utc"), "submitted_at_utc")
    first = _utc(run_receipt.get("first_token_at_utc"), "first_token_at_utc")
    complete = _utc(run_receipt.get("text_complete_at_utc"), "text_complete_at_utc")
    if not submitted <= first <= complete:
        raise ResidentMediaV8Error("supervised response timing is nonmonotonic")
    _sha(run_receipt.get("supervisor_process_identity_sha256"), "supervisor process")
    external = _sha(run_receipt.get("external_parent_observation_sha256"), "external observation")
    phase = str(challenge.get("phase") or "")
    raw_choice = semantic_choice_v8(raw, phase)
    final_choice = semantic_choice_v8(final, phase)
    if raw_choice.startswith("AMBIGUOUS") or final_choice.startswith("AMBIGUOUS"):
        raise ResidentMediaV8Error("supervised choice is ambiguous and needs a new turn")
    if raw_choice != final_choice:
        raise ResidentMediaV8Error("supervised raw/final choices disagree")
    response = {
        "schema": "kira.resident_media_choice_response.v6",
        "session_id": challenge["session_id"],
        "person_id": challenge["person_id"],
        "stimulus_id": challenge["stimulus_id"],
        "ordinal": challenge["ordinal"],
        "reservation_sha256": challenge["reservation_sha256"],
        "challenge_sha256": v6._record_sha(challenge),
        "challenge_nonce": challenge["nonce"],
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "model_call_count": 1,
        "normal_model_route": True,
        "fallback_used": False,
        "prompt_sha256": challenge["prompt_sha256"],
        "raw_reply": raw,
        "final_reply": final,
        "transformations": json.loads(_canonical(transformations).decode("utf-8")),
        "choice": raw_choice,
        "external_parent_observation_sha256": external,
    }
    return response, _record_sha(dict(run_receipt))


_SEGMENT_KEYS = {
    "sequence", "page_number", "track_number", "source_start_ms", "source_end_ms",
    "output_start_monotonic_ns", "output_end_monotonic_ns",
    "actual_visual_output", "actual_audio_output", "derivative_role",
    "derivative_sha256", "renderer_or_decoder_receipt_sha256",
}


def validate_presentation_evidence_v8(
    value: Mapping[str, Any],
    *,
    session_id: str,
    person_id: str,
    expected_manifest: Mapping[str, Any],
    consumed_start_permit_sha256: str,
) -> dict[str, Any]:
    """Validate exact source/output/time evidence without inferring attention."""

    _exact(
        value,
        {
            "schema", "session_id", "person_id", "stimulus_id", "ordinal",
            "source_manifest", "source_manifest_sha256",
            "consumed_start_permit_sha256", "output_receipt_id", "output_surface_id",
            "presented_at_utc", "presentation_segments", "engineering_output_completed",
            "presentation_complete_for_manifest", "full_source_experienced",
            "person_attention_claimed", "person_saw_or_heard_claimed",
            "automatic_memory_created", "automatic_preference_created",
            "external_parent_observation_sha256",
        },
        "presentation evidence",
    )
    if value.get("schema") != "kira.resident_media_exact_presentation_evidence.v8":
        raise ResidentMediaV8Error("presentation evidence schema changed")
    if value.get("session_id") != session_id or value.get("person_id") != person_id:
        raise ResidentMediaV8Error("presentation session/person binding changed")
    clean_manifest = v4.validate_source_manifest(expected_manifest)
    supplied_manifest = v4.validate_source_manifest(value.get("source_manifest"))
    if supplied_manifest != clean_manifest:
        raise ResidentMediaV8Error("presentation exact source manifest changed")
    manifest_sha = v4.sha256_record(clean_manifest)
    if value.get("source_manifest_sha256") != manifest_sha:
        raise ResidentMediaV8Error("presentation source manifest digest changed")
    if value.get("stimulus_id") != clean_manifest["stimulus_id"]:
        raise ResidentMediaV8Error("presentation stimulus identity changed")
    ordinal = _nonnegative_int(value.get("ordinal"), "presentation ordinal")
    if value.get("consumed_start_permit_sha256") != _sha(
        consumed_start_permit_sha256, "consumed start permit"
    ):
        raise ResidentMediaV8Error("presentation start-permit binding changed")
    _identifier(value.get("output_receipt_id"), "output receipt id")
    _identifier(value.get("output_surface_id"), "output surface id")
    _utc(value.get("presented_at_utc"), "presented_at_utc")
    for field in (
        "engineering_output_completed", "presentation_complete_for_manifest",
        "full_source_experienced", "person_attention_claimed",
        "person_saw_or_heard_claimed", "automatic_memory_created",
        "automatic_preference_created",
    ):
        if not isinstance(value.get(field), bool):
            raise ResidentMediaV8Error(f"{field} must be boolean")
    if any(
        value.get(field) is True
        for field in (
            "full_source_experienced", "person_attention_claimed",
            "person_saw_or_heard_claimed", "automatic_memory_created",
            "automatic_preference_created",
        )
    ):
        raise ResidentMediaV8Error("output evidence cannot assert experience, attention, memory, or preference")
    segments = value.get("presentation_segments")
    if not isinstance(segments, list) or not 1 <= len(segments) <= 256:
        raise ResidentMediaV8Error("presentation segments are missing or unbounded")
    derivative_by_role = {item["role"]: item for item in clean_manifest["derivatives"]}
    kind = clean_manifest["media_kind"]
    coordinates = clean_manifest["coordinates"]
    previous_output_end_by_role: dict[str, int] = {}
    intervals: list[tuple[int, int]] = []
    clean_segments: list[dict[str, Any]] = []
    for expected_sequence, segment in enumerate(segments):
        _exact(segment, _SEGMENT_KEYS, f"presentation segment {expected_sequence}")
        if segment.get("sequence") != expected_sequence:
            raise ResidentMediaV8Error("presentation segment sequence is not contiguous")
        output_start = _nonnegative_int(segment.get("output_start_monotonic_ns"), "output start")
        output_end = _nonnegative_int(segment.get("output_end_monotonic_ns"), "output end")
        if output_end <= output_start:
            raise ResidentMediaV8Error("presentation output time is empty or reversed")
        visual = segment.get("actual_visual_output")
        audio = segment.get("actual_audio_output")
        if not isinstance(visual, bool) or not isinstance(audio, bool) or not (visual or audio):
            raise ResidentMediaV8Error("presentation segment needs actual visual or audio output")
        role = _identifier(segment.get("derivative_role"), "derivative role")
        derivative = derivative_by_role.get(role)
        if derivative is None or segment.get("derivative_sha256") != derivative["sha256"]:
            raise ResidentMediaV8Error("presentation derivative identity changed")
        previous_output_end = previous_output_end_by_role.get(role, -1)
        if output_start <= previous_output_end:
            raise ResidentMediaV8Error("presentation output time is not strictly monotonic for its derivative stream")
        previous_output_end_by_role[role] = output_end
        _sha(segment.get("renderer_or_decoder_receipt_sha256"), "renderer/decoder receipt")
        page = segment.get("page_number")
        track = segment.get("track_number")
        start = segment.get("source_start_ms")
        end = segment.get("source_end_ms")
        if kind == "PAGE":
            if page != coordinates["page_number"] or track is not None or start is not None or end is not None:
                raise ResidentMediaV8Error("page presentation coordinates changed")
            if not visual or audio or role != "rendered_page_png":
                raise ResidentMediaV8Error("page presentation modality/derivative changed")
        else:
            start_i = _nonnegative_int(start, "segment source start")
            end_i = _nonnegative_int(end, "segment source end")
            if end_i <= start_i:
                raise ResidentMediaV8Error("presentation segment source interval is empty")
            if start_i < coordinates["start_ms"] or end_i > coordinates["end_ms"]:
                raise ResidentMediaV8Error("presentation segment escaped the accepted source interval")
            intervals.append((start_i, end_i))
            if kind == "VIDEO_INTERVAL":
                if page is not None or track is not None:
                    raise ResidentMediaV8Error("video presentation gained page/track coordinates")
                if role not in {"timed_frame_manifest", "synchronized_audio_pcm"}:
                    raise ResidentMediaV8Error("video derivative role changed")
                if role == "timed_frame_manifest" and (not visual or audio):
                    raise ResidentMediaV8Error("video frame evidence modality changed")
                if role == "synchronized_audio_pcm" and (visual or not audio):
                    raise ResidentMediaV8Error("video audio evidence modality changed")
            else:
                if page is not None or track != coordinates["track_number"]:
                    raise ResidentMediaV8Error("audio track coordinates changed")
                if role != "synchronized_audio_pcm" or visual or not audio:
                    raise ResidentMediaV8Error("audio track modality/derivative changed")
        clean_segments.append(json.loads(_canonical(dict(segment)).decode("utf-8")))
    if kind == "PAGE":
        complete = bool(clean_segments)
    else:
        cursor = coordinates["start_ms"]
        complete = True
        for start, end in sorted(intervals):
            if start > cursor:
                complete = False
                break
            cursor = max(cursor, end)
        complete = complete and cursor == coordinates["end_ms"]
    declared_complete = value.get("presentation_complete_for_manifest")
    engineering_complete = value.get("engineering_output_completed")
    if declared_complete is not complete:
        raise ResidentMediaV8Error("declared presentation completeness is false")
    if engineering_complete is not complete:
        raise ResidentMediaV8Error("engineering completion must equal exact manifest coverage")
    _sha(value.get("external_parent_observation_sha256"), "external presentation observation")
    clean = json.loads(_canonical(dict(value)).decode("utf-8"))
    clean["ordinal"] = ordinal
    clean["presentation_segments"] = clean_segments
    return clean


class HardenedResidentMediaSessionV8:
    """Static v8 facade around the sealed v7 session."""

    def __init__(
        self,
        *,
        session_id: str,
        catalog: v4.StimulusCatalog,
        session_root: Any,
        capability_root: Any,
        capability_secret_key: bytes,
        issuer_id: str,
        parent_process_identity_sha256: str,
        protected_anchor: ProtectedMonotonicBackendV8,
        create: bool,
    ) -> None:
        if not isinstance(protected_anchor, ProtectedMonotonicBackendV8):
            raise ResidentMediaV8Error("v8 requires the protected monotonic backend adapter")
        self.session_id = _identifier(session_id, "session id")
        self.catalog = catalog
        self.protected_anchor = protected_anchor
        self._tainted = False
        factory = (
            _V8ChoiceSurfaceSession.create
            if create
            else _V8ChoiceSurfaceSession.restore
        )
        try:
            self._v7 = factory(
                session_id=session_id,
                catalog=catalog,
                session_root=session_root,
                capability_root=capability_root,
                capability_secret_key=capability_secret_key,
                issuer_id=issuer_id,
                parent_process_identity_sha256=parent_process_identity_sha256,
                protected_anchor=protected_anchor,
            )
        except (v6.ResidentMediaV6Error, v7.ResidentMediaV7Error) as exc:
            raise ResidentMediaV8Error(str(exc)) from exc
        if create:
            if protected_anchor.read_v8_anchor(session_id) is not None:
                raise ResidentMediaV8Error("protected v8 session anchor already exists")
            control = {
                "pending_transition": None,
                "last_consumed_start_permit_sha256": None,
                "supervised_response_sha256s": [],
                "presentation_evidence_records": [],
            }
            self._anchor = self._build_anchor(0, control)
            self._cas(None, self._anchor)
        else:
            anchored = protected_anchor.read_v8_anchor(session_id)
            if not isinstance(anchored, Mapping):
                raise ResidentMediaV8Error("protected v8 session anchor is missing")
            self._anchor = dict(anchored)
            self._validate_anchor(self._anchor)
            if self._anchor["control"]["pending_transition"] is not None:
                raise ResidentMediaV8Error("v8 restore found an incomplete transition")
            if self._anchor != self._build_anchor(
                self._anchor["generation"], self._anchor["control"]
            ):
                raise ResidentMediaV8Error("v8 protected/local state changed or rolled back")

    @classmethod
    def create(cls, **kwargs: Any) -> "HardenedResidentMediaSessionV8":
        return cls(create=True, **kwargs)

    @classmethod
    def restore(cls, **kwargs: Any) -> "HardenedResidentMediaSessionV8":
        return cls(create=False, **kwargs)

    def _v6_anchor(self) -> dict[str, Any]:
        value = self.protected_anchor.read_v6_anchor(self.session_id)
        if not isinstance(value, Mapping):
            raise ResidentMediaV8Error("protected v6 anchor is missing")
        return dict(value)

    def _build_anchor(self, generation: int, control: Mapping[str, Any]) -> dict[str, Any]:
        v6_anchor = self._v6_anchor()
        return {
            "schema": "kira.resident_media_protected_session_anchor.v8",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "generation": generation,
            "catalog_sha256": self.catalog.sha256,
            "protected_backend_identity_sha256": self.protected_anchor.backend_identity_sha256,
            "v6_anchor_sha256": _record_sha(v6_anchor),
            "v6_anchor_generation": v6_anchor["generation"],
            "control": json.loads(_canonical(dict(control)).decode("utf-8")),
            "live_execution_allowed": False,
        }

    def _validate_anchor(self, value: Mapping[str, Any]) -> None:
        _exact(
            value,
            {
                "schema", "session_id", "person_id", "generation", "catalog_sha256",
                "protected_backend_identity_sha256", "v6_anchor_sha256",
                "v6_anchor_generation", "control", "live_execution_allowed",
            },
            "v8 protected anchor",
        )
        if value.get("schema") != "kira.resident_media_protected_session_anchor.v8":
            raise ResidentMediaV8Error("v8 protected anchor schema changed")
        expected = {
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "catalog_sha256": self.catalog.sha256,
            "protected_backend_identity_sha256": self.protected_anchor.backend_identity_sha256,
            "live_execution_allowed": False,
        }
        for field, wanted in expected.items():
            if value.get(field) != wanted:
                raise ResidentMediaV8Error(f"v8 protected anchor binding changed: {field}")
        _nonnegative_int(value.get("generation"), "v8 generation")
        _sha(value.get("v6_anchor_sha256"), "v6 anchor digest")
        _nonnegative_int(value.get("v6_anchor_generation"), "v6 anchor generation")
        control = value.get("control")
        _exact(
            control,
            {
                "pending_transition", "last_consumed_start_permit_sha256",
                "supervised_response_sha256s", "presentation_evidence_records",
            },
            "v8 control",
        )
        if control["last_consumed_start_permit_sha256"] is not None:
            _sha(control["last_consumed_start_permit_sha256"], "last start permit")
        responses = control["supervised_response_sha256s"]
        presentations = control["presentation_evidence_records"]
        if not isinstance(responses, list) or len(responses) > MAX_V8_RESPONSES:
            raise ResidentMediaV8Error("v8 supervised response history is invalid")
        for item in responses:
            _sha(item, "supervised response record")
        if not isinstance(presentations, list) or len(presentations) > MAX_V8_PRESENTATION_RECORDS:
            raise ResidentMediaV8Error("v8 presentation history is invalid")
        for item in presentations:
            _exact(item, {"evidence_sha256", "stimulus_id", "ordinal", "status"}, "presentation history item")
            _sha(item["evidence_sha256"], "presentation evidence")
            _identifier(item["stimulus_id"], "presentation stimulus")
            _nonnegative_int(item["ordinal"], "presentation ordinal")
            if item["status"] not in {"INCOMPLETE_NOT_RECORDED", "COMPLETE_MANIFEST_RECORDED"}:
                raise ResidentMediaV8Error("presentation history status changed")
        pending = control["pending_transition"]
        if pending is not None:
            _exact(pending, {"operation_id", "operation", "expected_v6_anchor_sha256"}, "pending transition")
            _sha(pending["operation_id"], "pending operation id")
            _identifier(pending["operation"], "pending operation")
            _sha(pending["expected_v6_anchor_sha256"], "pending v6 anchor")

    def _cas(self, previous: Mapping[str, Any] | None, replacement: Mapping[str, Any]) -> None:
        previous_sha = None if previous is None else _record_sha(previous)
        receipt = self.protected_anchor.compare_and_swap_v8_anchor(
            self.session_id, previous_sha, replacement
        )
        expected = {
            "schema": "kira.protected_anchor_v8_cas_receipt.v8",
            "protected_backend_identity_sha256": self.protected_anchor.backend_identity_sha256,
            "expected_previous_record_sha256": previous_sha,
            "replacement_record_sha256": _record_sha(replacement),
            "atomic_compare_and_swap": True,
            "strictly_monotonic_generation": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }
        if dict(receipt) != expected:
            raise ResidentMediaV8Error("protected v8 CAS receipt changed")
        reopened = self.protected_anchor.read_v8_anchor(self.session_id)
        if not isinstance(reopened, Mapping) or dict(reopened) != dict(replacement):
            raise ResidentMediaV8Error("protected v8 anchor did not read back exactly")

    def _assert_synced(self) -> None:
        if self._tainted:
            raise ResidentMediaV8Error("v8 session is fail-closed after a transition failure")
        reopened = self.protected_anchor.read_v8_anchor(self.session_id)
        if not isinstance(reopened, Mapping) or dict(reopened) != self._anchor:
            raise ResidentMediaV8Error("v8 protected anchor changed or rolled back")
        self._validate_anchor(self._anchor)
        v6_anchor = self._v6_anchor()
        if self._anchor["v6_anchor_sha256"] != _record_sha(v6_anchor):
            raise ResidentMediaV8Error("v8/v6 protected anchors are out of sync")

    def _control(self) -> dict[str, Any]:
        return json.loads(_canonical(self._anchor["control"]).decode("utf-8"))

    def _advance(self, control: Mapping[str, Any]) -> None:
        previous = self._anchor
        replacement = self._build_anchor(previous["generation"] + 1, control)
        self._validate_anchor(replacement)
        self._cas(previous, replacement)
        self._anchor = replacement

    def _transition(
        self,
        operation: str,
        callback: Callable[[], Any],
        on_commit: Callable[[dict[str, Any], Any], None] | None = None,
    ) -> Any:
        self._assert_synced()
        operation = _identifier(operation, "v8 operation")
        operation_id = secrets.token_hex(32)
        control = self._control()
        control["pending_transition"] = {
            "operation_id": operation_id,
            "operation": operation,
            "expected_v6_anchor_sha256": self._anchor["v6_anchor_sha256"],
        }
        self._advance(control)
        try:
            result = callback()
            control = self._control()
            pending = control["pending_transition"]
            if not isinstance(pending, Mapping) or pending.get("operation_id") != operation_id:
                raise ResidentMediaV8Error("v8 pending transition changed")
            if on_commit is not None:
                on_commit(control, result)
            control["pending_transition"] = None
            self._advance(control)
            return result
        except Exception as exc:
            self._tainted = True
            if isinstance(exc, ResidentMediaV8Error):
                raise
            raise ResidentMediaV8Error(f"v8 protected transition failed: {operation}") from exc

    def issue_choice_challenge(self, *, prompt_sha256: str) -> dict[str, Any]:
        return self._transition(
            "ISSUE_CHOICE_CHALLENGE",
            lambda: self._v7.issue_choice_challenge(prompt_sha256=prompt_sha256),
        )

    def accept_supervised_response(self, run_receipt: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_synced()
        challenge = self._v7._control().get("active_challenge")
        if not isinstance(challenge, Mapping):
            raise ResidentMediaV8Error("no active choice challenge exists")
        response, run_sha = adapt_supervised_choice_response_v8(run_receipt, challenge)

        def commit(control: dict[str, Any], _result: Any) -> None:
            if run_sha in control["supervised_response_sha256s"]:
                raise ResidentMediaV8Error("supervised response replayed")
            control["supervised_response_sha256s"].append(run_sha)

        try:
            return self._transition(
                "ACCEPT_SUPERVISED_RESPONSE",
                lambda: self._v7.accept_choice_response(response),
                commit,
            )
        except (v6.ResidentMediaV6Error, v7.ResidentMediaV7Error) as exc:
            self._tainted = True
            raise ResidentMediaV8Error(str(exc)) from exc

    def issue_capability(self, *, ttl_seconds: int = 30) -> dict[str, Any]:
        return self._transition(
            "ISSUE_CAPABILITY", lambda: self._v7.issue_capability(ttl_seconds=ttl_seconds)
        )

    def reserve_presentation(self, token: Mapping[str, Any]) -> dict[str, Any]:
        return self._transition(
            "RESERVE_PRESENTATION", lambda: self._v7.reserve_presentation(token)
        )

    def consume_start_permit(self, permit: Mapping[str, Any]) -> dict[str, Any]:
        permit_sha = _record_sha(dict(permit))

        def commit(control: dict[str, Any], _result: Any) -> None:
            if control["last_consumed_start_permit_sha256"] is not None:
                raise ResidentMediaV8Error("another start permit is already awaiting evidence")
            control["last_consumed_start_permit_sha256"] = permit_sha

        return self._transition(
            "CONSUME_START_PERMIT",
            lambda: self._v7.consume_start_permit(permit),
            commit,
        )

    def record_presentation_evidence(self, evidence: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_synced()
        control = self._control()
        permit_sha = control["last_consumed_start_permit_sha256"]
        if permit_sha is None:
            raise ResidentMediaV8Error("presentation evidence lacks a consumed start permit")
        next_ordinal = self._v7._v5._state.snapshot()["next_ordinal"]
        expected_manifest = self.catalog.manifest(next_ordinal)
        clean = validate_presentation_evidence_v8(
            evidence,
            session_id=self.session_id,
            person_id=PERSON_ID,
            expected_manifest=expected_manifest,
            consumed_start_permit_sha256=permit_sha,
        )
        if clean["ordinal"] != next_ordinal:
            raise ResidentMediaV8Error("presentation ordinal changed")
        evidence_sha = _record_sha(clean)
        if any(
            item["evidence_sha256"] == evidence_sha
            for item in control["presentation_evidence_records"]
        ):
            raise ResidentMediaV8Error("presentation evidence replayed")
        complete = clean["presentation_complete_for_manifest"]

        def commit(control_value: dict[str, Any], _result: Any) -> None:
            control_value["presentation_evidence_records"].append(
                {
                    "evidence_sha256": evidence_sha,
                    "stimulus_id": clean["stimulus_id"],
                    "ordinal": clean["ordinal"],
                    "status": (
                        "COMPLETE_MANIFEST_RECORDED"
                        if complete
                        else "INCOMPLETE_NOT_RECORDED"
                    ),
                }
            )
            if complete:
                control_value["last_consumed_start_permit_sha256"] = None

        if complete:
            observation = {
                "schema": "kira.resident_media_presentation_observation.v4",
                "source_manifest": clean["source_manifest"],
                "engineering_output_completed": True,
                "machine_visual_interpretation_created": False,
                "machine_audio_cue_created": False,
                "machine_context_packet_created": True,
                "person_attention_claimed": False,
                "person_saw_or_heard_claimed": False,
                "automatic_memory_created": False,
                "automatic_preference_created": False,
                "external_parent_observation_sha256": evidence_sha,
            }
            result = self._transition(
                "RECORD_COMPLETE_PRESENTATION",
                lambda: self._v7.record_presentation(observation),
                commit,
            )
            return {
                "schema": "kira.resident_media_presentation_result.v8",
                "status": "COMPLETE_MANIFEST_RECORDED",
                "evidence_sha256": evidence_sha,
                "v7_presentation_event_sha256": result,
                "full_source_experienced": False,
                "live_execution_allowed": False,
            }
        self._transition("RECORD_INCOMPLETE_EVIDENCE", lambda: None, commit)
        return {
            "schema": "kira.resident_media_presentation_result.v8",
            "status": "INCOMPLETE_NOT_RECORDED",
            "evidence_sha256": evidence_sha,
            "v7_presentation_event_sha256": None,
            "full_source_experienced": False,
            "live_execution_allowed": False,
        }

    def snapshot(self) -> dict[str, Any]:
        self._assert_synced()
        control = self._control()
        return {
            "schema": "kira.resident_media_voluntary_snapshot.v8",
            "v7_state": self._v7.snapshot(),
            "protected_anchor_generation": self._anchor["generation"],
            "supervised_response_count": len(control["supervised_response_sha256s"]),
            "presentation_evidence_records": control["presentation_evidence_records"],
            "presentation_pending": control["last_consumed_start_permit_sha256"] is not None,
            "protected_monotonic_backend_required": True,
            "exact_source_time_binding_required": True,
            "full_source_experienced": False,
            "live_execution_allowed": False,
        }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_summary.v8",
        "preserved_v7_contract_sha256": v6._record_sha(v7.static_contract_summary()),
        "exact_model": EXACT_MODEL,
        "exact_digest": EXACT_DIGEST,
        "external_atomic_monotonic_authority_required": True,
        "local_or_in_memory_production_fallback": False,
        "exact_post_cas_readback_required": True,
        "exact_source_page_interval_track_and_derivative_binding": True,
        "supervised_response_adapter_implemented": True,
        "incomplete_presentation_counts_as_experienced": False,
        "complete_manifest_counts_as_full_source_experienced": False,
        "live_execution_allowed": False,
        "live_authority_or_supervisor_connected": False,
        "different_fresh_audit_required_before_live_session": True,
    }
