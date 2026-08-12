"""Static-only hardened envelope for resident-media voluntary gate v4.

Version 5 preserves the sealed v4 implementation byte-for-byte and places a
fail-closed envelope around it.  The envelope fixes the defects reproduced by
the fresh v4 audit without claiming that this Python module is itself a
process, operating-system, or anti-rollback trust root.

No live use is authorized by this module.  A later parent must provide an
independently reviewed :class:`ProtectedAnchorBackend` whose state cannot be
rolled back with the local session/capability directories.  A caller-created
mock or in-process backend is suitable only for static tests.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from Core import resident_media_voluntary_gate_v4 as v4


EXACT_MODEL = v4.EXACT_MODEL
EXACT_DIGEST = v4.EXACT_DIGEST
PERSON_ID = v4.PERSON_ID
STIMULUS_ORDER = v4.STIMULUS_ORDER
MAX_RESERVATION_SECONDS = 30
MAX_START_PERMIT_SECONDS = 5


class ResidentMediaV5Error(ValueError):
    """A v5 trust, consent, freshness, or restore gate failed."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _record_sha(value: Mapping[str, Any]) -> str:
    return _sha256(v4.canonical_json_bytes(dict(value)))


def _require_sha(value: Any, field: str) -> str:
    text = str(value or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise ResidentMediaV5Error(f"{field} must be SHA-256")
    return text


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ResidentMediaV5Error(f"{label} keys changed")


def _utc(value: Any, field: str) -> datetime:
    text = str(value or "")
    if not text.endswith("Z"):
        raise ResidentMediaV5Error(f"{field} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ResidentMediaV5Error(f"{field} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ResidentMediaV5Error(f"{field} must be UTC")
    return parsed


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _system_sample() -> tuple[datetime, int]:
    # The v4 transition authority remains responsible for its own clock.  This
    # second sample is solely for the bounded v5 reservation/start envelope.
    import time

    return datetime.now(timezone.utc), time.monotonic_ns()


# These are the exact four owner-selected source identities from the preserved
# 2026-08-02 read-only preflight.  Derivative identities are additionally
# pinned by the separately protected catalog authorization described below.
AUTHORITATIVE_SOURCE_IDENTITIES: tuple[dict[str, Any], ...] = (
    {
        "stimulus_id": "illustrated_magazine_cover_page_001",
        "opaque_media_id": "c079ae6171a8c76680c3dde6c220902f60b453fc917f44ecfd026e1fd59b91a2",
        "media_kind": "PAGE",
        "source_relative_path": "Data/library/travel/magazines/travel_leisure_southeast_asia_2019_12.pdf",
        "source_byte_count": 147789858,
        "source_sha256": "69a7edf5ab6c7569d8fd66136efef227cbf6d791f1c1478f95cf0d6664562ad7",
        "coordinates": {"kind": "PAGE_NUMBER", "page_number": 1},
    },
    {
        "stimulus_id": "unfamiliar_merlion_race_car_crop_page_014",
        "opaque_media_id": "c079ae6171a8c76680c3dde6c220902f60b453fc917f44ecfd026e1fd59b91a2",
        "media_kind": "PAGE",
        "source_relative_path": "Data/library/travel/magazines/travel_leisure_southeast_asia_2019_12.pdf",
        "source_byte_count": 147789858,
        "source_sha256": "69a7edf5ab6c7569d8fd66136efef227cbf6d791f1c1478f95cf0d6664562ad7",
        "coordinates": {"kind": "PAGE_NUMBER", "page_number": 14},
    },
    {
        "stimulus_id": "power_rangers_commercial_interval_000_008",
        "opaque_media_id": "69bbc23292971ea984c7167962bd7b9eccb0cc56ae6c9e28db0b3eb4d59e0bd0",
        "media_kind": "VIDEO_INTERVAL",
        "source_relative_path": "Data/library/video_commercials/power_rangers/s_1_3_mighty_morphin_power_rangers/mighty_morphin_power_rangers_talking_rangers_and_lord_zedd_toy_commercial.mp4",
        "source_byte_count": 1794541,
        "source_sha256": "a9a8ca814df2a73191d0725ae91fb33bd8c78a50980ba3e03bae7fec25fc7797",
        "coordinates": {"kind": "INTERVAL_MS", "start_ms": 0, "end_ms": 8000},
    },
    {
        "stimulus_id": "highlander_new_york_new_york_interval_000_010",
        "opaque_media_id": "63345ede7968a88640dceb6fb3c033c66e96a8a3b81b6d6a76ad478c4fcdef52",
        "media_kind": "AUDIO_TRACK",
        "source_relative_path": "Data/library/music/soundtracks/highlander_soundtrack_1986/18_new_york_new_york.mp3",
        "source_byte_count": 1051103,
        "source_sha256": "da745c602b051877f6af3405773825121edeed32c253be6f5134647195857466",
        "coordinates": {
            "kind": "TRACK_INTERVAL_MS",
            "track_number": 18,
            "start_ms": 0,
            "end_ms": 10000,
        },
    },
)
AUTHORITATIVE_SOURCE_POLICY_SHA256 = _sha256(
    v4.canonical_json_bytes(
        {
            "schema": "kira.resident_media_authoritative_source_policy.v5",
            "sources": AUTHORITATIVE_SOURCE_IDENTITIES,
        }
    )
)


def validate_authoritative_catalog(catalog: v4.StimulusCatalog) -> str:
    """Reject a structurally valid but owner-unselected caller catalog."""

    if not isinstance(catalog, v4.StimulusCatalog):
        raise ResidentMediaV5Error("catalog must be a validated v4 catalog")
    for ordinal, expected in enumerate(AUTHORITATIVE_SOURCE_IDENTITIES):
        manifest = catalog.manifest(ordinal)
        for field in (
            "stimulus_id",
            "opaque_media_id",
            "media_kind",
            "source_relative_path",
            "source_byte_count",
            "source_sha256",
            "coordinates",
        ):
            if manifest.get(field) != expected[field]:
                raise ResidentMediaV5Error(
                    f"catalog does not match authoritative source identity: {expected['stimulus_id']}:{field}"
                )
        if not manifest["source_relative_path"].startswith("Data/library/"):
            raise ResidentMediaV5Error("authoritative source escaped Data/library")
    return catalog.sha256


class ProtectedAnchorBackend(ABC):
    """Interface to an independently protected monotonic store.

    A qualifying live backend must be outside the rollback domain of the
    session and capability directories.  It must implement atomic
    compare-and-swap and protect catalog authorization records.  This module
    intentionally supplies no local-file or in-memory production fallback.
    """

    @property
    @abstractmethod
    def backend_identity_sha256(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_catalog_authorization(self, catalog_sha256: str) -> Mapping[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def read_session_anchor(self, session_id: str) -> Mapping[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def compare_and_swap_session(
        self,
        session_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        raise NotImplementedError


def _validate_backend(backend: ProtectedAnchorBackend) -> str:
    if not isinstance(backend, ProtectedAnchorBackend):
        raise ResidentMediaV5Error("an explicit protected anchor backend is required")
    return _require_sha(backend.backend_identity_sha256, "protected backend identity")


def _validate_catalog_authorization(
    backend: ProtectedAnchorBackend, catalog_sha256: str
) -> dict[str, Any]:
    value = backend.read_catalog_authorization(catalog_sha256)
    if not isinstance(value, Mapping):
        raise ResidentMediaV5Error("catalog was not pre-authorized by the protected backend")
    _require_exact_keys(
        value,
        {
            "schema",
            "catalog_sha256",
            "authoritative_source_policy_sha256",
            "status",
            "protected_backend_identity_sha256",
        },
        "catalog authorization",
    )
    expected = {
        "schema": "kira.resident_media_catalog_authorization.v5",
        "catalog_sha256": catalog_sha256,
        "authoritative_source_policy_sha256": AUTHORITATIVE_SOURCE_POLICY_SHA256,
        "status": "AUTHORIZED_FOR_STATIC_GATE_ONLY",
        "protected_backend_identity_sha256": _validate_backend(backend),
    }
    if dict(value) != expected:
        raise ResidentMediaV5Error("protected catalog authorization changed")
    return expected


def _root_identity(root: Path) -> dict[str, Any]:
    original = Path(root)
    if not original.exists() or not original.is_dir() or original.is_symlink():
        raise ResidentMediaV5Error("anchored root must be an existing real directory")
    resolved = original.resolve(strict=True)
    stat = resolved.stat()
    if bool(getattr(stat, "st_file_attributes", 0) & 0x400):
        raise ResidentMediaV5Error("anchored root cannot be a reparse point")
    return {
        "resolved_path_sha256": _sha256(str(resolved).casefold().encode("utf-8")),
        "device": int(stat.st_dev),
        "inode": int(stat.st_ino),
        "file_attributes": int(getattr(stat, "st_file_attributes", 0)),
    }


def _session_inventory(journal: v4.DurableSessionJournal) -> dict[str, Any]:
    events = journal.load_contiguous()
    digests = [_record_sha(event) for event in events]
    return {
        "event_count": len(events),
        "head_sha256": digests[-1] if digests else None,
        "inventory_sha256": _sha256(v4.canonical_json_bytes(digests)),
    }


_CAPABILITY_NAME = re.compile(
    r"(?:capability_issue_binding_[0-9a-f]{64}|capability_consumed_[0-9a-f]{64})\.json"
)


def _capability_inventory(authority: v4.DurableCapabilityAuthority) -> dict[str, Any]:
    entries: list[dict[str, str]] = []
    for path in sorted(authority.store.root.iterdir(), key=lambda item: item.name):
        if not _CAPABILITY_NAME.fullmatch(path.name):
            raise ResidentMediaV5Error(f"unexpected capability ledger entry: {path.name}")
        record, receipt = authority.store.read_exact(path.name)
        entries.append(
            {
                "name": path.name,
                "record_sha256": _record_sha(record),
                "file_sha256": _require_sha(receipt["file_sha256"], "capability file digest"),
            }
        )
    return {
        "record_count": len(entries),
        "inventory_sha256": _sha256(v4.canonical_json_bytes(entries)),
    }


_REFUSAL_PATTERN = re.compile(
    r"(?:\bno\b|\bnever\b|\brefus(?:e|ed|ing)\b|\bdeclin(?:e|ed|ing)\b|"
    r"\bdo\s+not\b|\bdon['\N{RIGHT SINGLE QUOTATION MARK}]?t\b|\bnot\s+(?:my\s+answer|consent|agreeing|saying|want|interested)\b|"
    r"\bwithout\s+my\s+(?:permission|consent)\b|\bskip\b|\bleave\s+it\b)",
    re.IGNORECASE,
)
_STOP_PATTERN = re.compile(r"\b(?:stop|quit|cancel|end|leave)\b", re.IGNORECASE)
_PAUSE_PATTERN = re.compile(r"\b(?:pause|wait|hold\s+on|not\s+yet)\b", re.IGNORECASE)
_YES_PATTERN = re.compile(
    r"(?:\byes\b|\bi\s+(?:do\s+)?(?:want|choose)\s+to\b|"
    r"\bi['\N{RIGHT SINGLE QUOTATION MARK}]?d\s+like\s+to\b|\bshow\s+me\b|\bplay\s+it\b)",
    re.IGNORECASE,
)
_CONTINUE_PATTERN = re.compile(r"\b(?:continue|next|go\s+on|keep\s+going)\b", re.IGNORECASE)


def semantic_choice_v5(text: str, phase: str) -> str:
    """Fail closed: any explicit refusal prevents YES/CONTINUE."""

    if not isinstance(text, str) or not text.strip():
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    if _REFUSAL_PATTERN.search(text):
        return "NO" if phase == "INVITATION" else "STOP"
    if _STOP_PATTERN.search(text):
        return "STOP"
    if _PAUSE_PATTERN.search(text):
        return "AMBIGUOUS_REQUIRES_NEW_TURN" if phase == "INVITATION" else "PAUSE"
    if phase == "INVITATION":
        return "YES" if _YES_PATTERN.search(text) else "AMBIGUOUS_REQUIRES_NEW_TURN"
    if _YES_PATTERN.search(text) or _CONTINUE_PATTERN.search(text):
        return "CONTINUE"
    return "AMBIGUOUS_REQUIRES_NEW_TURN"


def validate_choice_observation_v5(
    value: Mapping[str, Any], *, phase: str, prompt_sha256: str
) -> dict[str, Any]:
    """Require raw/final semantics and label to agree under refusal-first parsing."""

    if not isinstance(value, Mapping):
        raise ResidentMediaV5Error("choice observation must be an object")
    raw = str(value.get("raw_reply") or "")
    final = str(value.get("final_reply") or "")
    raw_semantic = semantic_choice_v5(raw, phase)
    final_semantic = semantic_choice_v5(final, phase)
    supplied = str(value.get("choice") or "")
    if raw_semantic.startswith("AMBIGUOUS") or final_semantic.startswith("AMBIGUOUS"):
        raise ResidentMediaV5Error("choice wording is ambiguous and requires a new turn")
    if raw_semantic != final_semantic or supplied != raw_semantic:
        raise ResidentMediaV5Error("structured choice cannot override raw/final voluntary wording")
    expected_prompt = _require_sha(prompt_sha256, "prompt_sha256")
    try:
        v4.validate_choice_observation(value, phase=phase, prompt_sha256=expected_prompt)
    except v4.ResidentMediaV4Error as exc:
        # V5 intentionally recognizes refusal forms that v4 did not.  Preserve
        # all of v4's structural/route validation by retrying only this one
        # known semantic disagreement with equivalent canonical wording.
        if str(exc) != "structured choice cannot override the person's words":
            raise ResidentMediaV5Error(str(exc)) from exc
        canonical = {
            "YES": "Yes, I would like to see it.",
            "NO": "No, I do not want to see it.",
            "CONTINUE": "Continue to the next item.",
            "PAUSE": "Pause and wait.",
            "STOP": "Stop now.",
        }[supplied]
        structural = dict(value)
        structural["raw_reply"] = canonical
        structural["final_reply"] = canonical
        try:
            v4.validate_choice_observation(
                structural, phase=phase, prompt_sha256=expected_prompt
            )
        except v4.ResidentMediaV4Error as structural_exc:
            raise ResidentMediaV5Error(str(structural_exc)) from structural_exc
    return v4.strict_json_loads(v4.canonical_json_bytes(dict(value)))


def validate_restored_presentation_events(
    events: Sequence[Mapping[str, Any]], catalog: v4.StimulusCatalog
) -> None:
    """Apply v5 choice and live presentation invariants before v4 restore."""

    for event in events:
        if event.get("event_type") == "CHOICE_ACCEPTED":
            choice_payload = event.get("payload")
            if not isinstance(choice_payload, Mapping):
                raise ResidentMediaV5Error("restored choice payload is missing")
            observation = choice_payload.get("observation")
            phase = str(choice_payload.get("phase") or "")
            if not isinstance(observation, Mapping):
                raise ResidentMediaV5Error("restored choice observation is missing")
            validate_choice_observation_v5(
                observation,
                phase=phase,
                prompt_sha256=_require_sha(
                    observation.get("prompt_sha256"), "restored choice prompt"
                ),
            )
        if event.get("event_type") != "PRESENTATION_RECORDED":
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            raise ResidentMediaV5Error("restored presentation payload is missing")
        core = payload.get("presentation_core")
        if not isinstance(core, Mapping):
            raise ResidentMediaV5Error("restored presentation core is missing")
        if payload.get("presentation_core_sha256") != _record_sha(core):
            raise ResidentMediaV5Error("restored presentation core digest changed")
        ordinal = core.get("ordinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 0 <= ordinal < len(STIMULUS_ORDER):
            raise ResidentMediaV5Error("restored presentation ordinal is invalid")
        if core.get("source_manifest") != catalog.manifest(ordinal):
            raise ResidentMediaV5Error("restored presentation source manifest changed")
        if core.get("engineering_output_completed") is not True:
            raise ResidentMediaV5Error("restored presentation is not completed")
        for field in (
            "machine_visual_interpretation_created",
            "machine_audio_cue_created",
            "machine_context_packet_created",
            "person_attention_claimed",
            "person_saw_or_heard_claimed",
            "automatic_memory_created",
            "automatic_preference_created",
        ):
            if not isinstance(core.get(field), bool):
                raise ResidentMediaV5Error(f"restored {field} is not boolean")
        if any(
            core.get(field) is True
            for field in (
                "person_attention_claimed",
                "person_saw_or_heard_claimed",
                "automatic_memory_created",
                "automatic_preference_created",
            )
        ):
            raise ResidentMediaV5Error("restored static evidence asserted person experience or memory")
        _require_sha(core.get("external_parent_observation_sha256"), "restored parent observation")


def _validate_anchor_receipt(
    receipt: Mapping[str, Any], *, backend_sha: str, previous_sha: str | None, replacement_sha: str
) -> None:
    expected = {
        "schema": "kira.protected_anchor_cas_receipt.v5",
        "protected_backend_identity_sha256": backend_sha,
        "expected_previous_record_sha256": previous_sha,
        "replacement_record_sha256": replacement_sha,
        "atomic_compare_and_swap": True,
        "rollback_domain_separate_from_local_ledgers": True,
    }
    if dict(receipt) != expected:
        raise ResidentMediaV5Error("protected anchor CAS receipt is invalid")


class HardenedVoluntaryMediaSessionV5:
    """V5 static facade; direct access to the preserved v4 objects is invalid."""

    def __init__(
        self,
        *,
        session_id: str,
        catalog: v4.StimulusCatalog,
        session_root: Path,
        capability_root: Path,
        capability_secret_key: bytes,
        issuer_id: str,
        parent_process_identity_sha256: str,
        protected_anchor: ProtectedAnchorBackend,
        create: bool,
    ) -> None:
        self._tainted = False
        self.session_id = session_id
        self.catalog = catalog
        self.session_root = Path(session_root)
        self.capability_root = Path(capability_root)
        self.protected_anchor = protected_anchor
        self._backend_sha = _validate_backend(protected_anchor)
        catalog_sha = validate_authoritative_catalog(catalog)
        self._catalog_authorization = _validate_catalog_authorization(protected_anchor, catalog_sha)
        self._clock = v4.SystemClockAuthority()
        self._authority = v4.DurableCapabilityAuthority(
            root=self.capability_root,
            secret_key=capability_secret_key,
            issuer_id=issuer_id,
            parent_process_identity_sha256=parent_process_identity_sha256,
            clock=v4.SystemClockAuthority(),
        )
        self._journal = v4.DurableSessionJournal(self.session_root)
        if not create:
            events = self._journal.load_contiguous()
            validate_restored_presentation_events(events, catalog)
        factory = v4.VoluntaryMediaState.create if create else v4.VoluntaryMediaState.restore
        try:
            self._state = factory(
                session_id=session_id,
                catalog=catalog,
                journal=self._journal,
                capability_authority=self._authority,
                clock=self._clock,
                parent_process_identity_sha256=parent_process_identity_sha256,
            )
        except v4.ResidentMediaV4Error as exc:
            raise ResidentMediaV5Error(str(exc)) from exc
        self._anchor_record: dict[str, Any]
        if create:
            if protected_anchor.read_session_anchor(session_id) is not None:
                raise ResidentMediaV5Error("protected session anchor already exists")
            control = {
                "reservation_status": "NONE",
                "reservation": None,
                "permit": None,
                "last_recheck_observation_sha256": None,
            }
            self._anchor_record = self._build_anchor_record(generation=0, control=control)
            self._cas(None, self._anchor_record)
        else:
            anchored = protected_anchor.read_session_anchor(session_id)
            if not isinstance(anchored, Mapping):
                raise ResidentMediaV5Error("protected session anchor is missing")
            self._anchor_record = dict(anchored)
            self._validate_anchor_record(self._anchor_record)
            current = self._build_anchor_record(
                generation=self._anchor_record["generation"],
                control=self._anchor_record["control"],
            )
            if current != self._anchor_record:
                raise ResidentMediaV5Error("local session/capability state rolled back or root changed")

    @classmethod
    def create(cls, **kwargs: Any) -> "HardenedVoluntaryMediaSessionV5":
        return cls(create=True, **kwargs)

    @classmethod
    def restore(cls, **kwargs: Any) -> "HardenedVoluntaryMediaSessionV5":
        return cls(create=False, **kwargs)

    def _assert_usable(self) -> None:
        if self._tainted:
            raise ResidentMediaV5Error("v5 session is fail-closed after an anchor update failure")

    def _build_anchor_record(self, *, generation: int, control: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema": "kira.resident_media_protected_session_anchor.v5",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "generation": generation,
            "catalog_sha256": self.catalog.sha256,
            "catalog_authorization_sha256": _record_sha(self._catalog_authorization),
            "authoritative_source_policy_sha256": AUTHORITATIVE_SOURCE_POLICY_SHA256,
            "protected_backend_identity_sha256": self._backend_sha,
            "session_root_identity": _root_identity(self.session_root),
            "capability_root_identity": _root_identity(self.capability_root),
            "session_inventory": _session_inventory(self._journal),
            "capability_inventory": _capability_inventory(self._authority),
            "control": v4.strict_json_loads(v4.canonical_json_bytes(dict(control))),
            "live_execution_allowed": False,
        }

    def _validate_anchor_record(self, value: Mapping[str, Any]) -> None:
        _require_exact_keys(
            value,
            {
                "schema",
                "session_id",
                "person_id",
                "generation",
                "catalog_sha256",
                "catalog_authorization_sha256",
                "authoritative_source_policy_sha256",
                "protected_backend_identity_sha256",
                "session_root_identity",
                "capability_root_identity",
                "session_inventory",
                "capability_inventory",
                "control",
                "live_execution_allowed",
            },
            "protected session anchor",
        )
        if value.get("schema") != "kira.resident_media_protected_session_anchor.v5":
            raise ResidentMediaV5Error("protected session anchor schema changed")
        if value.get("session_id") != self.session_id or value.get("person_id") != PERSON_ID:
            raise ResidentMediaV5Error("protected session identity changed")
        generation = value.get("generation")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ResidentMediaV5Error("protected generation is invalid")
        if value.get("catalog_sha256") != self.catalog.sha256:
            raise ResidentMediaV5Error("protected catalog digest changed")
        if value.get("catalog_authorization_sha256") != _record_sha(self._catalog_authorization):
            raise ResidentMediaV5Error("protected catalog authorization changed")
        if value.get("authoritative_source_policy_sha256") != AUTHORITATIVE_SOURCE_POLICY_SHA256:
            raise ResidentMediaV5Error("protected source policy changed")
        if value.get("protected_backend_identity_sha256") != self._backend_sha:
            raise ResidentMediaV5Error("protected backend identity changed")
        if value.get("live_execution_allowed") is not False:
            raise ResidentMediaV5Error("static anchor cannot authorize live execution")
        if not isinstance(value.get("control"), Mapping):
            raise ResidentMediaV5Error("protected control state is missing")

    def _cas(self, previous: Mapping[str, Any] | None, replacement: Mapping[str, Any]) -> None:
        previous_sha = _record_sha(previous) if previous is not None else None
        replacement_sha = _record_sha(replacement)
        try:
            receipt = self.protected_anchor.compare_and_swap_session(
                self.session_id, previous_sha, replacement
            )
            _validate_anchor_receipt(
                receipt,
                backend_sha=self._backend_sha,
                previous_sha=previous_sha,
                replacement_sha=replacement_sha,
            )
        except Exception as exc:
            self._tainted = True
            if isinstance(exc, ResidentMediaV5Error):
                raise
            raise ResidentMediaV5Error("protected anchor compare-and-swap failed") from exc

    def _advance_anchor(self, control: Mapping[str, Any] | None = None) -> None:
        self._assert_usable()
        old = self._anchor_record
        self._validate_anchor_record(old)
        new = self._build_anchor_record(
            generation=old["generation"] + 1,
            control=control if control is not None else old["control"],
        )
        self._cas(old, new)
        self._anchor_record = new

    def _control(self) -> dict[str, Any]:
        return v4.strict_json_loads(v4.canonical_json_bytes(self._anchor_record["control"]))

    @property
    def next_required_phase(self) -> str:
        return self._state.next_required_phase

    def accept_choice(self, observation: Mapping[str, Any], *, prompt_sha256: str) -> str:
        self._assert_usable()
        validate_choice_observation_v5(
            observation, phase=self._state.next_required_phase, prompt_sha256=prompt_sha256
        )
        try:
            digest = self._state.accept_choice(observation, prompt_sha256=prompt_sha256)
        except v4.ResidentMediaV4Error as exc:
            raise ResidentMediaV5Error(str(exc)) from exc
        control = self._control()
        if control["reservation_status"] == "COMPLETED":
            control = {
                "reservation_status": "NONE",
                "reservation": None,
                "permit": None,
                "last_recheck_observation_sha256": None,
            }
        self._advance_anchor(control)
        return digest

    def issue_capability(self, *, ttl_seconds: int = MAX_RESERVATION_SECONDS) -> dict[str, Any]:
        self._assert_usable()
        try:
            token = self._authority.issue(
                self._state.expected_capability_binding(), ttl_seconds=ttl_seconds
            )
        except v4.ResidentMediaV4Error as exc:
            raise ResidentMediaV5Error(str(exc)) from exc
        self._advance_anchor()
        return token

    def reserve_presentation(self, token: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_usable()
        control = self._control()
        if control["reservation_status"] != "NONE":
            raise ResidentMediaV5Error("a v5 reservation is already present")
        try:
            reservation = self._state.reserve_presentation(token)
        except v4.ResidentMediaV4Error as exc:
            raise ResidentMediaV5Error(str(exc)) from exc
        now_utc, now_mono = _system_sample()
        token_expiry_utc = _utc(token.get("expires_at_utc"), "token expiry")
        token_expiry_mono = token.get("expires_monotonic_ns")
        if isinstance(token_expiry_mono, bool) or not isinstance(token_expiry_mono, int):
            raise ResidentMediaV5Error("token monotonic expiry is invalid")
        expires_utc = min(token_expiry_utc, now_utc + timedelta(seconds=MAX_RESERVATION_SECONDS))
        expires_mono = min(
            token_expiry_mono, now_mono + MAX_RESERVATION_SECONDS * 1_000_000_000
        )
        public = {
            "schema": "kira.resident_media_bounded_reservation.v5",
            "session_id": self.session_id,
            "stimulus_id": reservation["stimulus_id"],
            "ordinal": reservation["ordinal"],
            "v4_reservation_sha256": _record_sha(reservation),
            "created_at_utc": _utc_text(now_utc),
            "created_monotonic_ns": now_mono,
            "expires_at_utc": _utc_text(expires_utc),
            "expires_monotonic_ns": expires_mono,
            "status": "ACTIVE_AWAITING_FRESH_RECHECK",
            "live_execution_allowed": False,
        }
        control = {
            "reservation_status": "ACTIVE_AWAITING_FRESH_RECHECK",
            "reservation": public,
            "permit": None,
            "last_recheck_observation_sha256": None,
        }
        self._advance_anchor(control)
        return v4.strict_json_loads(v4.canonical_json_bytes(public))

    @staticmethod
    def _assert_deadline(record: Mapping[str, Any], now_utc: datetime, now_mono: int) -> None:
        expiry_utc = _utc(record.get("expires_at_utc"), "reservation/permit expiry")
        expiry_mono = record.get("expires_monotonic_ns")
        if isinstance(expiry_mono, bool) or not isinstance(expiry_mono, int):
            raise ResidentMediaV5Error("reservation/permit monotonic expiry is invalid")
        if now_utc > expiry_utc or now_mono > expiry_mono:
            raise ResidentMediaV5Error("reservation/permit expired")

    def recheck_and_authorize_start(
        self, observation: Mapping[str, Any], *, prompt_sha256: str
    ) -> dict[str, Any]:
        """Require a fresh current choice before returning a short start permit."""

        self._assert_usable()
        control = self._control()
        if control["reservation_status"] != "ACTIVE_AWAITING_FRESH_RECHECK":
            raise ResidentMediaV5Error("reservation is not awaiting a fresh voluntary recheck")
        reservation = control["reservation"]
        if not isinstance(reservation, Mapping):
            raise ResidentMediaV5Error("bounded reservation is missing")
        now_utc, now_mono = _system_sample()
        self._assert_deadline(reservation, now_utc, now_mono)
        raw_semantic = semantic_choice_v5(str(observation.get("raw_reply") or ""), "RECHECK")
        final_semantic = semantic_choice_v5(str(observation.get("final_reply") or ""), "RECHECK")
        supplied = str(observation.get("choice") or "")
        observation_sha = _record_sha(observation)
        if raw_semantic in {"STOP", "PAUSE"} or final_semantic in {"STOP", "PAUSE"}:
            validate_choice_observation_v5(
                observation, phase="RECHECK", prompt_sha256=prompt_sha256
            )
            if raw_semantic != final_semantic or supplied != raw_semantic:
                raise ResidentMediaV5Error("recheck refusal/decline wording and label disagree")
            control = {
                "reservation_status": "REVOKED_BY_PERSON",
                "reservation": reservation,
                "permit": None,
                "last_recheck_observation_sha256": observation_sha,
            }
            self._advance_anchor(control)
            raise ResidentMediaV5Error("person revoked or paused the reserved presentation")
        validate_choice_observation_v5(
            observation, phase="RECHECK", prompt_sha256=prompt_sha256
        )
        permit_expiry_utc = min(
            _utc(reservation["expires_at_utc"], "reservation expiry"),
            now_utc + timedelta(seconds=MAX_START_PERMIT_SECONDS),
        )
        permit_expiry_mono = min(
            int(reservation["expires_monotonic_ns"]),
            now_mono + MAX_START_PERMIT_SECONDS * 1_000_000_000,
        )
        permit = {
            "schema": "kira.resident_media_external_start_permit.v5",
            "session_id": self.session_id,
            "reservation_sha256": _record_sha(reservation),
            "fresh_choice_observation_sha256": observation_sha,
            "issued_at_utc": _utc_text(now_utc),
            "issued_monotonic_ns": now_mono,
            "expires_at_utc": _utc_text(permit_expiry_utc),
            "expires_monotonic_ns": permit_expiry_mono,
            "status": "UNCONSUMED",
            "live_execution_allowed_by_static_core": False,
        }
        control = {
            "reservation_status": "ACTIVE_PERMIT_UNCONSUMED",
            "reservation": reservation,
            "permit": permit,
            "last_recheck_observation_sha256": observation_sha,
        }
        self._advance_anchor(control)
        return v4.strict_json_loads(v4.canonical_json_bytes(permit))

    def consume_start_permit(self, permit: Mapping[str, Any]) -> dict[str, Any]:
        """Consume the short permit immediately before an external parent acts."""

        self._assert_usable()
        control = self._control()
        if control["reservation_status"] != "ACTIVE_PERMIT_UNCONSUMED":
            raise ResidentMediaV5Error("start permit is not currently usable")
        current = control.get("permit")
        if not isinstance(current, Mapping) or dict(permit) != dict(current):
            raise ResidentMediaV5Error("start permit changed or was replayed")
        now_utc, now_mono = _system_sample()
        self._assert_deadline(current, now_utc, now_mono)
        self._assert_deadline(control["reservation"], now_utc, now_mono)
        consumed = {**dict(current), "status": "CONSUMED_BEFORE_EXTERNAL_START"}
        control = {
            "reservation_status": "ACTIVE_START_PERMIT_CONSUMED",
            "reservation": control["reservation"],
            "permit": consumed,
            "last_recheck_observation_sha256": control["last_recheck_observation_sha256"],
        }
        self._advance_anchor(control)
        return {
            "schema": "kira.resident_media_external_start_receipt.v5",
            "permit_sha256": _record_sha(permit),
            "consumed_before_external_start": True,
            "protected_anchor_generation": self._anchor_record["generation"],
            "live_execution_allowed_by_static_core": False,
        }

    def revoke_reservation(
        self, observation: Mapping[str, Any], *, prompt_sha256: str
    ) -> str:
        """Durably revoke a pending reservation; this v4 session then stays terminal."""

        self._assert_usable()
        control = self._control()
        if not str(control["reservation_status"]).startswith("ACTIVE_"):
            raise ResidentMediaV5Error("no active reservation can be revoked")
        raw = semantic_choice_v5(str(observation.get("raw_reply") or ""), "RECHECK")
        final = semantic_choice_v5(str(observation.get("final_reply") or ""), "RECHECK")
        if raw not in {"STOP", "PAUSE"} or final != raw or observation.get("choice") != raw:
            raise ResidentMediaV5Error("revocation requires matching explicit refusal/pause wording")
        # Validate the exact Qwen route and prompt fields too; a structured
        # label alone never revokes or authorizes anything.
        validate_choice_observation_v5(
            observation, phase="RECHECK", prompt_sha256=prompt_sha256
        )
        observation_sha = _record_sha(observation)
        control = {
            "reservation_status": "REVOKED_BY_PERSON",
            "reservation": control["reservation"],
            "permit": None,
            "last_recheck_observation_sha256": observation_sha,
        }
        self._advance_anchor(control)
        return observation_sha

    def record_presentation(self, observation: Mapping[str, Any]) -> str:
        self._assert_usable()
        control = self._control()
        if control["reservation_status"] != "ACTIVE_START_PERMIT_CONSUMED":
            raise ResidentMediaV5Error("presentation lacks a consumed fresh start permit")
        now_utc, now_mono = _system_sample()
        self._assert_deadline(control["reservation"], now_utc, now_mono)
        # Reuse the strict v5 restore check shape on the observation before v4
        # appends it.  V4 then applies its full live validation independently.
        if observation.get("engineering_output_completed") is not True:
            raise ResidentMediaV5Error("incomplete presentation cannot be recorded")
        for field in (
            "machine_visual_interpretation_created",
            "machine_audio_cue_created",
            "machine_context_packet_created",
            "person_attention_claimed",
            "person_saw_or_heard_claimed",
            "automatic_memory_created",
            "automatic_preference_created",
        ):
            if not isinstance(observation.get(field), bool):
                raise ResidentMediaV5Error(f"{field} must be boolean")
        _require_sha(observation.get("external_parent_observation_sha256"), "parent observation")
        try:
            digest = self._state.record_presentation(observation, self._state._pending_reservation)
        except v4.ResidentMediaV4Error as exc:
            raise ResidentMediaV5Error(str(exc)) from exc
        control = {
            "reservation_status": "COMPLETED",
            "reservation": control["reservation"],
            "permit": control["permit"],
            "last_recheck_observation_sha256": control["last_recheck_observation_sha256"],
        }
        self._advance_anchor(control)
        return digest

    def snapshot(self) -> dict[str, Any]:
        self._assert_usable()
        current = self._build_anchor_record(
            generation=self._anchor_record["generation"], control=self._anchor_record["control"]
        )
        if current != self._anchor_record:
            raise ResidentMediaV5Error("local state no longer matches the protected anchor")
        effective_status = self._anchor_record["control"]["reservation_status"]
        reservation = self._anchor_record["control"].get("reservation")
        if str(effective_status).startswith("ACTIVE_") and isinstance(reservation, Mapping):
            now_utc, now_mono = _system_sample()
            try:
                self._assert_deadline(reservation, now_utc, now_mono)
            except ResidentMediaV5Error:
                effective_status = "EXPIRED_FAIL_CLOSED"
        return {
            "schema": "kira.resident_media_voluntary_snapshot.v5",
            "v4_state": self._state.snapshot(),
            "protected_anchor_generation": self._anchor_record["generation"],
            "reservation_status": effective_status,
            "catalog_authorized": True,
            "anti_rollback_anchor_required": True,
            "live_execution_allowed": False,
        }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_summary.v5",
        "exact_model": EXACT_MODEL,
        "exact_digest": EXACT_DIGEST,
        "explicit_refusal_can_parse_as_yes": False,
        "bare_caller_catalog_accepted": False,
        "protected_catalog_preauthorization_required": True,
        "protected_external_monotonic_anchor_required": True,
        "local_ledger_only_one_use_claimed": False,
        "session_suffix_and_root_rollback_rejected_by_anchor": True,
        "bounded_revocable_reservation": True,
        "fresh_choice_before_short_start_permit": True,
        "restore_revalidates_presentation_completion": True,
        "live_execution_allowed": False,
        "live_backend_implemented_here": False,
    }
