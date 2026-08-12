"""Static-only v6 repair envelope for resident-media voluntary choice.

V6 preserves v5 byte-for-byte and repairs only the four findings in the
fresh v5 hostile audit. It is still not a live model, media, person, or
playback authorization. A later parent needs a separately implemented and
audited protected backend; this module verifies the backend contract with
exact post-CAS read-back but cannot make an in-process test double external.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
import unicodedata
from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v5 as v5


EXACT_MODEL = v5.EXACT_MODEL
EXACT_DIGEST = v5.EXACT_DIGEST
PERSON_ID = v5.PERSON_ID
STIMULUS_ORDER = v5.STIMULUS_ORDER
MAX_CHALLENGE_SECONDS = 20
MAX_CONSUMED_CHALLENGES = 32


class ResidentMediaV6Error(ValueError):
    """The v6 choice, freshness, evidence, or protected-state gate failed."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _record_sha(value: Mapping[str, Any]) -> str:
    return _sha256(v4.canonical_json_bytes(dict(value)))


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ResidentMediaV6Error(f"{label} keys changed")


def _sha(value: Any, field: str, *, nonzero: bool = False) -> str:
    text = str(value or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise ResidentMediaV6Error(f"{field} must be SHA-256")
    if nonzero and text == "0" * 64:
        raise ResidentMediaV6Error(f"{field} cannot be the zero digest")
    return text


def _utc(value: Any, field: str) -> datetime:
    text = str(value or "")
    if not text.endswith("Z"):
        raise ResidentMediaV6Error(f"{field} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ResidentMediaV6Error(f"{field} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ResidentMediaV6Error(f"{field} must be UTC")
    return parsed


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _system_sample() -> tuple[datetime, int]:
    return datetime.now(timezone.utc), time.monotonic_ns()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 16_384:
        raise ResidentMediaV6Error(f"{field} is missing or oversized")
    return value


def _normalize_choice(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().replace("’", "'")
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return " ".join(text.split())


_INVITATION_POSITIVE = frozenset(
    {
        "yes",
        "yes please",
        "yes show me",
        "yes play it",
        "show me",
        "play it",
        "i want to see it",
        "i choose to see it",
        "i would like to see it",
        "i'd like to see it",
    }
)
_CONTINUE_POSITIVE = frozenset(
    {
        "continue",
        "continue please",
        "continue with the presentation",
        "continue to the next item",
        "yes continue",
        "next",
        "go on",
        "keep going",
    }
)
_REFUSAL = re.compile(
    r"(?:\bno\b|\bnope\b|\bnah\b|\bnever\b|\bnot\b|\bcannot\b|\bcan't\b|"
    r"\bwon't\b|\bdon't\b|\brefus\w*\b|\bdeclin\w*\b|\breject\w*\b|"
    r"\bwithdraw\w*\b|\bretract\w*\b|\brescind\w*\b|\bwithhold\w*\b|"
    r"\bobject\w*\b|\bdeny\w*\b|\bdissent\w*\b|\bopt\s+out\b|"
    r"\bwithout\s+(?:my\s+)?(?:permission|consent)\b|\bskip\w*\b|"
    r"\bstop\b|\bcancel\b|\bquit\b|\bleave\b)",
    re.IGNORECASE,
)
_PAUSE = re.compile(r"\b(?:pause|wait|hold\s+on|not\s+yet)\b", re.IGNORECASE)


def semantic_choice_v6(text: str, phase: str) -> str:
    """Only an exact affirmative allowlist can authorize presentation.

    Refusal/pause language is evaluated before the allowlist. Any longer or
    mixed sentence containing a stray ``yes``/``continue`` is ambiguous or a
    refusal, never an authorization.
    """

    if not isinstance(text, str) or not text.strip():
        return "AMBIGUOUS_REQUIRES_NEW_TURN"
    normalized = _normalize_choice(text)
    if _REFUSAL.search(normalized):
        return "NO" if phase == "INVITATION" else "STOP"
    if _PAUSE.search(normalized):
        return "AMBIGUOUS_REQUIRES_NEW_TURN" if phase == "INVITATION" else "PAUSE"
    allowlist = _INVITATION_POSITIVE if phase == "INVITATION" else _CONTINUE_POSITIVE
    if normalized in allowlist:
        return "YES" if phase == "INVITATION" else "CONTINUE"
    return "AMBIGUOUS_REQUIRES_NEW_TURN"


class ProtectedAnchorBackendV6(v5.ProtectedAnchorBackend):
    """V5 backend plus a separately namespaced v6 atomic anchor."""

    @abstractmethod
    def read_v6_anchor(self, session_id: str) -> Mapping[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def compare_and_swap_v6_anchor(
        self,
        session_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        raise NotImplementedError


def _validate_backend(backend: ProtectedAnchorBackendV6) -> str:
    if not isinstance(backend, ProtectedAnchorBackendV6):
        raise ResidentMediaV6Error("an explicit v6 protected anchor backend is required")
    return _sha(backend.backend_identity_sha256, "protected backend identity", nonzero=True)


def _validate_v6_cas_receipt(
    receipt: Mapping[str, Any], *, backend_sha: str, previous_sha: str | None, replacement_sha: str
) -> None:
    expected = {
        "schema": "kira.protected_anchor_v6_cas_receipt.v6",
        "protected_backend_identity_sha256": backend_sha,
        "expected_previous_record_sha256": previous_sha,
        "replacement_record_sha256": replacement_sha,
        "atomic_compare_and_swap": True,
        "rollback_domain_separate_from_local_ledgers": True,
        "exact_post_commit_readback_required": True,
    }
    if dict(receipt) != expected:
        raise ResidentMediaV6Error("protected v6 anchor CAS receipt is invalid")


def _validate_nonzero_presentation_history(events: list[Mapping[str, Any]]) -> None:
    for event in events:
        if event.get("event_type") != "PRESENTATION_RECORDED":
            continue
        payload = event.get("payload")
        core = payload.get("presentation_core") if isinstance(payload, Mapping) else None
        if not isinstance(core, Mapping):
            raise ResidentMediaV6Error("v6 restore presentation core is missing")
        _sha(
            core.get("external_parent_observation_sha256"),
            "v6 restored external observation",
            nonzero=True,
        )


def _canonical_v4_observation(
    response: Mapping[str, Any], *, phase: str, decision: str, fresh_sha256: str
) -> dict[str, Any]:
    canonical_choice = decision
    if phase == "INVITATION":
        canonical_choice = "YES" if decision == "YES" else "NO"
    elif decision == "YES":
        canonical_choice = "CONTINUE"
    canonical_text = {
        "YES": "Yes, I would like to see it.",
        "NO": "No, I do not want to see it.",
        "CONTINUE": "Continue to the next item.",
        "PAUSE": "Pause and wait.",
        "STOP": "Stop now.",
    }[canonical_choice]
    return {
        "schema": "kira.resident_media_choice_observation.v4",
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "model_call_count": 1,
        "normal_model_route": True,
        "fallback_used": False,
        "prompt_sha256": response["prompt_sha256"],
        "raw_reply": canonical_text,
        "final_reply": canonical_text,
        "transformations": [
            {
                "schema": "kira.resident_media_v6_canonical_transition.v6",
                "fresh_observation_sha256": fresh_sha256,
                "original_raw_reply_sha256": _sha256(response["raw_reply"].encode("utf-8")),
                "original_final_reply_sha256": _sha256(response["final_reply"].encode("utf-8")),
            }
        ],
        "choice": canonical_choice,
        "external_parent_observation_sha256": response[
            "external_parent_observation_sha256"
        ],
    }


class HardenedVoluntaryMediaSessionV6:
    """Static v6 facade. Direct use of ``_v5`` is outside this contract."""

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
        protected_anchor: ProtectedAnchorBackendV6,
        create: bool,
    ) -> None:
        self._tainted = False
        self.session_id = session_id
        self.catalog = catalog
        self.protected_anchor = protected_anchor
        self._backend_sha = _validate_backend(protected_anchor)
        factory = (
            v5.HardenedVoluntaryMediaSessionV5.create
            if create
            else v5.HardenedVoluntaryMediaSessionV5.restore
        )
        try:
            self._v5 = factory(
                session_id=session_id,
                catalog=catalog,
                session_root=session_root,
                capability_root=capability_root,
                capability_secret_key=capability_secret_key,
                issuer_id=issuer_id,
                parent_process_identity_sha256=parent_process_identity_sha256,
                protected_anchor=protected_anchor,
            )
        except v5.ResidentMediaV5Error as exc:
            raise ResidentMediaV6Error(str(exc)) from exc
        self._verify_v5_readback()
        _validate_nonzero_presentation_history(self._v5._journal.load_contiguous())
        if create:
            if protected_anchor.read_v6_anchor(session_id) is not None:
                raise ResidentMediaV6Error("protected v6 session anchor already exists")
            control = {
                "active_challenge": None,
                "consumed_challenges": [],
                "pending_transition": None,
            }
            self._anchor_record = self._build_anchor(generation=0, control=control)
            self._cas_v6(None, self._anchor_record)
        else:
            anchored = protected_anchor.read_v6_anchor(session_id)
            if not isinstance(anchored, Mapping):
                raise ResidentMediaV6Error("protected v6 session anchor is missing")
            self._anchor_record = dict(anchored)
            self._validate_anchor(self._anchor_record)
            current = self._build_anchor(
                generation=self._anchor_record["generation"],
                control=self._anchor_record["control"],
            )
            if current != self._anchor_record:
                raise ResidentMediaV6Error("v6 protected/local state changed or rolled back")
            if self._anchor_record["control"]["pending_transition"] is not None:
                raise ResidentMediaV6Error("v6 restore found an incomplete protected transition")

    @classmethod
    def create(cls, **kwargs: Any) -> "HardenedVoluntaryMediaSessionV6":
        return cls(create=True, **kwargs)

    @classmethod
    def restore(cls, **kwargs: Any) -> "HardenedVoluntaryMediaSessionV6":
        return cls(create=False, **kwargs)

    def _assert_usable(self) -> None:
        if self._tainted:
            raise ResidentMediaV6Error("v6 session is fail-closed after a protected transition failure")

    def _verify_v5_readback(self) -> dict[str, Any]:
        value = self.protected_anchor.read_session_anchor(self.session_id)
        if not isinstance(value, Mapping) or dict(value) != self._v5._anchor_record:
            raise ResidentMediaV6Error("v5 protected anchor did not read back exactly")
        self._v5._validate_anchor_record(value)
        return dict(value)

    def _build_anchor(self, *, generation: int, control: Mapping[str, Any]) -> dict[str, Any]:
        v5_anchor = self._verify_v5_readback()
        return {
            "schema": "kira.resident_media_protected_session_anchor.v6",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "generation": generation,
            "catalog_sha256": self.catalog.sha256,
            "protected_backend_identity_sha256": self._backend_sha,
            "v5_anchor_sha256": _record_sha(v5_anchor),
            "v5_anchor_generation": v5_anchor["generation"],
            "control": v4.strict_json_loads(v4.canonical_json_bytes(dict(control))),
            "live_execution_allowed": False,
        }

    def _validate_challenge(self, challenge: Mapping[str, Any]) -> None:
        _exact_keys(
            challenge,
            {
                "schema",
                "session_id",
                "person_id",
                "catalog_sha256",
                "phase",
                "stimulus_id",
                "ordinal",
                "reservation_sha256",
                "prompt_sha256",
                "nonce",
                "nonce_sha256",
                "issued_at_utc",
                "issued_monotonic_ns",
                "expires_at_utc",
                "expires_monotonic_ns",
                "v5_anchor_sha256",
                "v5_anchor_generation",
                "status",
                "live_execution_allowed",
            },
            "v6 choice challenge",
        )
        if challenge.get("schema") != "kira.resident_media_choice_challenge.v6":
            raise ResidentMediaV6Error("v6 challenge schema changed")
        if challenge.get("session_id") != self.session_id or challenge.get("person_id") != PERSON_ID:
            raise ResidentMediaV6Error("v6 challenge identity changed")
        if challenge.get("catalog_sha256") != self.catalog.sha256:
            raise ResidentMediaV6Error("v6 challenge catalog changed")
        nonce = str(challenge.get("nonce") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", nonce):
            raise ResidentMediaV6Error("v6 challenge nonce is invalid")
        if challenge.get("nonce_sha256") != _sha256(nonce.encode("ascii")):
            raise ResidentMediaV6Error("v6 challenge nonce digest changed")
        issued_utc = _utc(challenge.get("issued_at_utc"), "challenge issued_at_utc")
        expires_utc = _utc(challenge.get("expires_at_utc"), "challenge expires_at_utc")
        issued_mono = challenge.get("issued_monotonic_ns")
        expires_mono = challenge.get("expires_monotonic_ns")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in (issued_mono, expires_mono)):
            raise ResidentMediaV6Error("v6 challenge monotonic values are invalid")
        if expires_utc != issued_utc + timedelta(seconds=MAX_CHALLENGE_SECONDS):
            raise ResidentMediaV6Error("v6 challenge UTC bound changed")
        if expires_mono != issued_mono + MAX_CHALLENGE_SECONDS * 1_000_000_000:
            raise ResidentMediaV6Error("v6 challenge monotonic bound changed")
        _sha(challenge.get("prompt_sha256"), "v6 challenge prompt")
        reservation_sha = challenge.get("reservation_sha256")
        if reservation_sha is not None:
            _sha(reservation_sha, "v6 challenge reservation")
        if challenge.get("status") != "ACTIVE_ONE_USE" or challenge.get("live_execution_allowed") is not False:
            raise ResidentMediaV6Error("v6 challenge status changed")

    def _validate_control(self, control: Mapping[str, Any]) -> None:
        _exact_keys(
            control,
            {"active_challenge", "consumed_challenges", "pending_transition"},
            "v6 control",
        )
        challenge = control.get("active_challenge")
        if challenge is not None:
            if not isinstance(challenge, Mapping):
                raise ResidentMediaV6Error("v6 active challenge is malformed")
            self._validate_challenge(challenge)
        consumed = control.get("consumed_challenges")
        if not isinstance(consumed, list) or len(consumed) > MAX_CONSUMED_CHALLENGES:
            raise ResidentMediaV6Error("v6 consumed challenge inventory is malformed")
        nonce_hashes: set[str] = set()
        for entry in consumed:
            if not isinstance(entry, Mapping):
                raise ResidentMediaV6Error("v6 consumed challenge entry is malformed")
            _exact_keys(
                entry,
                {
                    "schema",
                    "challenge_sha256",
                    "nonce_sha256",
                    "response_sha256",
                    "response",
                    "fresh_observation",
                    "decision",
                    "outcome",
                    "operation_id",
                    "transition_result_sha256",
                },
                "v6 consumed challenge entry",
            )
            nonce_sha = _sha(entry.get("nonce_sha256"), "consumed nonce")
            if nonce_sha in nonce_hashes:
                raise ResidentMediaV6Error("v6 challenge nonce was consumed more than once")
            nonce_hashes.add(nonce_sha)
            if entry.get("outcome") not in {"V5_TRANSITION_PENDING", "COMMITTED"}:
                raise ResidentMediaV6Error("v6 consumed challenge outcome changed")
            if not isinstance(entry.get("response"), Mapping) or not isinstance(
                entry.get("fresh_observation"), Mapping
            ):
                raise ResidentMediaV6Error("v6 consumed response evidence is missing")
            if entry.get("schema") != "kira.resident_media_consumed_choice_challenge.v6":
                raise ResidentMediaV6Error("v6 consumed challenge schema changed")
            if entry.get("response_sha256") != _record_sha(entry["response"]):
                raise ResidentMediaV6Error("v6 consumed response digest changed")
            fresh = entry["fresh_observation"]
            _exact_keys(
                fresh,
                {
                    "schema",
                    "session_id",
                    "person_id",
                    "stimulus_id",
                    "ordinal",
                    "reservation_sha256",
                    "challenge_sha256",
                    "nonce_sha256",
                    "response_sha256",
                    "prompt_sha256",
                    "decision",
                    "observed_at_utc",
                    "observed_monotonic_ns",
                    "clock_id_sha256",
                    "freshness_verified",
                    "nonce_consumed",
                    "external_parent_observation_sha256",
                },
                "v6 fresh observation",
            )
            if fresh.get("schema") != "kira.resident_media_fresh_choice_observation.v6":
                raise ResidentMediaV6Error("v6 fresh observation schema changed")
            if (
                fresh.get("session_id") != self.session_id
                or fresh.get("person_id") != PERSON_ID
                or fresh.get("challenge_sha256") != entry.get("challenge_sha256")
                or fresh.get("nonce_sha256") != nonce_sha
                or fresh.get("response_sha256") != entry.get("response_sha256")
                or fresh.get("decision") != entry.get("decision")
                or fresh.get("freshness_verified") is not True
                or fresh.get("nonce_consumed") is not True
            ):
                raise ResidentMediaV6Error("v6 fresh observation binding changed")
            _utc(fresh.get("observed_at_utc"), "v6 observed_at_utc")
            observed_mono = fresh.get("observed_monotonic_ns")
            if isinstance(observed_mono, bool) or not isinstance(observed_mono, int):
                raise ResidentMediaV6Error("v6 observed monotonic time is invalid")
            if fresh.get("clock_id_sha256") != v4.SystemClockAuthority.CLOCK_ID_SHA256:
                raise ResidentMediaV6Error("v6 fresh observation clock changed")
            _sha(entry.get("challenge_sha256"), "consumed challenge")
            _sha(entry.get("operation_id"), "consumed operation id", nonzero=True)
            transition_result = entry.get("transition_result_sha256")
            if entry.get("outcome") == "COMMITTED":
                _sha(transition_result, "v6 transition result", nonzero=True)
            elif transition_result is not None:
                raise ResidentMediaV6Error("pending v6 transition already has a result")
            _sha(
                entry["response"].get("external_parent_observation_sha256"),
                "consumed external observation",
                nonzero=True,
            )
        pending = control.get("pending_transition")
        if pending is not None:
            if not isinstance(pending, Mapping):
                raise ResidentMediaV6Error("v6 pending transition is malformed")
            _exact_keys(
                pending,
                {"schema", "operation_id", "operation", "expected_v5_anchor_sha256"},
                "v6 pending transition",
            )
            _sha(pending.get("operation_id"), "v6 operation id")
            _sha(pending.get("expected_v5_anchor_sha256"), "expected v5 anchor")

    def _validate_anchor(self, value: Mapping[str, Any]) -> None:
        _exact_keys(
            value,
            {
                "schema",
                "session_id",
                "person_id",
                "generation",
                "catalog_sha256",
                "protected_backend_identity_sha256",
                "v5_anchor_sha256",
                "v5_anchor_generation",
                "control",
                "live_execution_allowed",
            },
            "v6 protected anchor",
        )
        if value.get("schema") != "kira.resident_media_protected_session_anchor.v6":
            raise ResidentMediaV6Error("v6 protected anchor schema changed")
        if value.get("session_id") != self.session_id or value.get("person_id") != PERSON_ID:
            raise ResidentMediaV6Error("v6 protected anchor identity changed")
        generation = value.get("generation")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ResidentMediaV6Error("v6 anchor generation is invalid")
        if value.get("catalog_sha256") != self.catalog.sha256:
            raise ResidentMediaV6Error("v6 anchor catalog changed")
        if value.get("protected_backend_identity_sha256") != self._backend_sha:
            raise ResidentMediaV6Error("v6 anchor backend identity changed")
        _sha(value.get("v5_anchor_sha256"), "v6 bound v5 anchor")
        if value.get("live_execution_allowed") is not False:
            raise ResidentMediaV6Error("v6 static anchor cannot authorize live use")
        control = value.get("control")
        if not isinstance(control, Mapping):
            raise ResidentMediaV6Error("v6 protected control is missing")
        self._validate_control(control)

    def _cas_v6(self, previous: Mapping[str, Any] | None, replacement: Mapping[str, Any]) -> None:
        previous_sha = _record_sha(previous) if previous is not None else None
        replacement_sha = _record_sha(replacement)
        try:
            receipt = self.protected_anchor.compare_and_swap_v6_anchor(
                self.session_id, previous_sha, replacement
            )
            _validate_v6_cas_receipt(
                receipt,
                backend_sha=self._backend_sha,
                previous_sha=previous_sha,
                replacement_sha=replacement_sha,
            )
            reopened = self.protected_anchor.read_v6_anchor(self.session_id)
            if not isinstance(reopened, Mapping) or dict(reopened) != dict(replacement):
                raise ResidentMediaV6Error("protected v6 anchor did not read back exactly")
        except Exception as exc:
            self._tainted = True
            if isinstance(exc, ResidentMediaV6Error):
                raise
            raise ResidentMediaV6Error("protected v6 anchor compare-and-swap failed") from exc

    def _assert_synced(self) -> None:
        self._assert_usable()
        if _validate_backend(self.protected_anchor) != self._backend_sha:
            raise ResidentMediaV6Error("v6 protected backend identity changed")
        self._validate_anchor(self._anchor_record)
        reopened = self.protected_anchor.read_v6_anchor(self.session_id)
        if not isinstance(reopened, Mapping) or dict(reopened) != self._anchor_record:
            raise ResidentMediaV6Error("v6 protected anchor changed outside the facade")
        v5_anchor = self._verify_v5_readback()
        if _record_sha(v5_anchor) != self._anchor_record["v5_anchor_sha256"]:
            raise ResidentMediaV6Error("v5 changed outside the v6 protected transition")
        active = self._anchor_record["control"]["active_challenge"]
        if isinstance(active, Mapping):
            binding = self._current_binding()
            for field in ("phase", "stimulus_id", "ordinal", "reservation_sha256"):
                if active.get(field) != binding[field]:
                    raise ResidentMediaV6Error(f"active v6 challenge binding changed: {field}")
            if (
                active.get("v5_anchor_sha256") != self._anchor_record["v5_anchor_sha256"]
                or active.get("v5_anchor_generation")
                != self._anchor_record["v5_anchor_generation"]
            ):
                raise ResidentMediaV6Error("active v6 challenge v5 binding changed")
        if self._anchor_record["control"]["pending_transition"] is not None:
            raise ResidentMediaV6Error("v6 has an incomplete protected transition")

    def _advance(self, control: Mapping[str, Any]) -> None:
        old = self._anchor_record
        new = self._build_anchor(generation=old["generation"] + 1, control=control)
        self._cas_v6(old, new)
        self._anchor_record = new

    def _control(self) -> dict[str, Any]:
        return v4.strict_json_loads(v4.canonical_json_bytes(self._anchor_record["control"]))

    def _run_v5_transition(self, operation: str, callback: Callable[[], Any]) -> Any:
        self._assert_synced()
        operation_id = secrets.token_hex(32)
        control = self._control()
        control["pending_transition"] = {
            "schema": "kira.resident_media_v6_pending_transition.v6",
            "operation_id": operation_id,
            "operation": operation,
            "expected_v5_anchor_sha256": self._anchor_record["v5_anchor_sha256"],
        }
        self._advance(control)
        try:
            result = callback()
            self._verify_v5_readback()
            control = self._control()
            if control["pending_transition"]["operation_id"] != operation_id:
                raise ResidentMediaV6Error("v6 pending transition identity changed")
            control["pending_transition"] = None
            self._advance(control)
            return result
        except Exception as exc:
            self._tainted = True
            if isinstance(exc, ResidentMediaV6Error):
                raise
            raise ResidentMediaV6Error(f"v6 protected transition failed: {operation}") from exc

    def _current_binding(self) -> dict[str, Any]:
        state = self._v5._state.snapshot()
        ordinal = state["next_ordinal"]
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 0 <= ordinal < len(
            STIMULUS_ORDER
        ):
            raise ResidentMediaV6Error("no further stimulus can receive a choice challenge")
        v5_control = self._v5._control()
        reservation = v5_control.get("reservation")
        if v5_control.get("reservation_status") == "ACTIVE_AWAITING_FRESH_RECHECK":
            phase = "RECHECK"
            if not isinstance(reservation, Mapping):
                raise ResidentMediaV6Error("v6 recheck lacks the exact reservation")
            reservation_sha: str | None = _record_sha(reservation)
        else:
            phase = self._v5.next_required_phase
            reservation_sha = None
        return {
            "phase": phase,
            "stimulus_id": STIMULUS_ORDER[ordinal],
            "ordinal": ordinal,
            "reservation_sha256": reservation_sha,
        }

    def issue_choice_challenge(self, *, prompt_sha256: str) -> dict[str, Any]:
        self._assert_synced()
        prompt_sha = _sha(prompt_sha256, "v6 challenge prompt")
        control = self._control()
        if control["active_challenge"] is not None:
            raise ResidentMediaV6Error("a one-use choice challenge is already active")
        binding = self._current_binding()
        now_utc, now_mono = _system_sample()
        nonce = secrets.token_hex(32)
        challenge = {
            "schema": "kira.resident_media_choice_challenge.v6",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "catalog_sha256": self.catalog.sha256,
            **binding,
            "prompt_sha256": prompt_sha,
            "nonce": nonce,
            "nonce_sha256": _sha256(nonce.encode("ascii")),
            "issued_at_utc": _utc_text(now_utc),
            "issued_monotonic_ns": now_mono,
            "expires_at_utc": _utc_text(
                now_utc + timedelta(seconds=MAX_CHALLENGE_SECONDS)
            ),
            "expires_monotonic_ns": now_mono + MAX_CHALLENGE_SECONDS * 1_000_000_000,
            "v5_anchor_sha256": self._anchor_record["v5_anchor_sha256"],
            "v5_anchor_generation": self._anchor_record["v5_anchor_generation"],
            "status": "ACTIVE_ONE_USE",
            "live_execution_allowed": False,
        }
        self._validate_challenge(challenge)
        control["active_challenge"] = challenge
        self._advance(control)
        return v4.strict_json_loads(v4.canonical_json_bytes(challenge))

    def _validate_response(
        self, response: Mapping[str, Any], challenge: Mapping[str, Any], now_utc: datetime, now_mono: int
    ) -> tuple[dict[str, Any], str]:
        if not isinstance(response, Mapping):
            raise ResidentMediaV6Error("v6 choice response must be an object")
        _exact_keys(
            response,
            {
                "schema",
                "session_id",
                "person_id",
                "stimulus_id",
                "ordinal",
                "reservation_sha256",
                "challenge_sha256",
                "challenge_nonce",
                "model_name",
                "model_digest",
                "model_call_count",
                "normal_model_route",
                "fallback_used",
                "prompt_sha256",
                "raw_reply",
                "final_reply",
                "transformations",
                "choice",
                "external_parent_observation_sha256",
            },
            "v6 choice response",
        )
        if response.get("schema") != "kira.resident_media_choice_response.v6":
            raise ResidentMediaV6Error("v6 choice response schema changed")
        for field in ("session_id", "person_id", "stimulus_id", "ordinal", "reservation_sha256"):
            if response.get(field) != challenge.get(field):
                raise ResidentMediaV6Error(f"v6 response binding changed: {field}")
        if response.get("challenge_sha256") != _record_sha(challenge):
            raise ResidentMediaV6Error("v6 response challenge digest changed")
        if response.get("challenge_nonce") != challenge.get("nonce"):
            raise ResidentMediaV6Error("v6 response challenge nonce changed")
        if response.get("prompt_sha256") != challenge.get("prompt_sha256"):
            raise ResidentMediaV6Error("v6 response prompt binding changed")
        if response.get("model_name") != EXACT_MODEL or str(
            response.get("model_digest") or ""
        ).lower() != EXACT_DIGEST:
            raise ResidentMediaV6Error("v6 response did not use exact Qwen")
        if response.get("model_call_count") != 1 or response.get("normal_model_route") is not True:
            raise ResidentMediaV6Error("v6 response requires one normal model call")
        if response.get("fallback_used") is not False:
            raise ResidentMediaV6Error("v6 fallback cannot decide voluntary choice")
        raw = _text(response.get("raw_reply"), "v6 raw reply")
        final = _text(response.get("final_reply"), "v6 final reply")
        transforms = response.get("transformations")
        if not isinstance(transforms, list) or len(transforms) > 32 or len(
            v4.canonical_json_bytes(transforms)
        ) > 65_536 or any(not isinstance(item, Mapping) for item in transforms):
            raise ResidentMediaV6Error("v6 choice transformations are malformed")
        phase = str(challenge["phase"])
        raw_semantic = semantic_choice_v6(raw, phase)
        final_semantic = semantic_choice_v6(final, phase)
        if raw_semantic.startswith("AMBIGUOUS") or final_semantic.startswith("AMBIGUOUS"):
            raise ResidentMediaV6Error("v6 choice is ambiguous and requires a new turn")
        if raw_semantic != final_semantic or response.get("choice") != raw_semantic:
            raise ResidentMediaV6Error("v6 raw/final/structured choice disagree")
        _sha(
            response.get("external_parent_observation_sha256"),
            "v6 external parent observation",
            nonzero=True,
        )
        issued_utc = _utc(challenge["issued_at_utc"], "v6 challenge issue")
        expiry_utc = _utc(challenge["expires_at_utc"], "v6 challenge expiry")
        issued_mono = int(challenge["issued_monotonic_ns"])
        expiry_mono = int(challenge["expires_monotonic_ns"])
        if not issued_utc <= now_utc < expiry_utc or not issued_mono <= now_mono < expiry_mono:
            raise ResidentMediaV6Error("v6 one-use choice challenge is stale or from the future")
        clean = v4.strict_json_loads(v4.canonical_json_bytes(dict(response)))
        return clean, raw_semantic

    def accept_choice_response(self, response: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_synced()
        control = self._control()
        challenge = control.get("active_challenge")
        if not isinstance(challenge, Mapping):
            raise ResidentMediaV6Error("no active one-use choice challenge exists")
        now_utc, now_mono = _system_sample()
        clean, decision = self._validate_response(response, challenge, now_utc, now_mono)
        challenge_sha = _record_sha(challenge)
        response_sha = _record_sha(clean)
        fresh = {
            "schema": "kira.resident_media_fresh_choice_observation.v6",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "stimulus_id": challenge["stimulus_id"],
            "ordinal": challenge["ordinal"],
            "reservation_sha256": challenge["reservation_sha256"],
            "challenge_sha256": challenge_sha,
            "nonce_sha256": challenge["nonce_sha256"],
            "response_sha256": response_sha,
            "prompt_sha256": challenge["prompt_sha256"],
            "decision": decision,
            "observed_at_utc": _utc_text(now_utc),
            "observed_monotonic_ns": now_mono,
            "clock_id_sha256": v4.SystemClockAuthority.CLOCK_ID_SHA256,
            "freshness_verified": True,
            "nonce_consumed": True,
            "external_parent_observation_sha256": clean[
                "external_parent_observation_sha256"
            ],
        }
        fresh_sha = _record_sha(fresh)
        operation_id = secrets.token_hex(32)
        entry = {
            "schema": "kira.resident_media_consumed_choice_challenge.v6",
            "challenge_sha256": challenge_sha,
            "nonce_sha256": challenge["nonce_sha256"],
            "response_sha256": response_sha,
            "response": clean,
            "fresh_observation": fresh,
            "decision": decision,
            "outcome": "V5_TRANSITION_PENDING",
            "operation_id": operation_id,
            "transition_result_sha256": None,
        }
        control["active_challenge"] = None
        control["consumed_challenges"].append(entry)
        control["pending_transition"] = {
            "schema": "kira.resident_media_v6_pending_transition.v6",
            "operation_id": operation_id,
            "operation": f"CHOICE_{challenge['phase']}_{decision}",
            "expected_v5_anchor_sha256": self._anchor_record["v5_anchor_sha256"],
        }
        self._advance(control)
        canonical = _canonical_v4_observation(
            clean, phase=str(challenge["phase"]), decision=decision, fresh_sha256=fresh_sha
        )
        try:
            if challenge["phase"] == "RECHECK":
                if decision == "CONTINUE":
                    transition_result = self._v5.recheck_and_authorize_start(
                        canonical, prompt_sha256=clean["prompt_sha256"]
                    )
                else:
                    transition_result = self._v5.revoke_reservation(
                        canonical, prompt_sha256=clean["prompt_sha256"]
                    )
            else:
                transition_result = self._v5.accept_choice(
                    canonical, prompt_sha256=clean["prompt_sha256"]
                )
            self._verify_v5_readback()
            result_sha = (
                _record_sha(transition_result)
                if isinstance(transition_result, Mapping)
                else _sha(transition_result, "v6 transition result")
            )
            control = self._control()
            pending = control["pending_transition"]
            if not isinstance(pending, Mapping) or pending.get("operation_id") != operation_id:
                raise ResidentMediaV6Error("v6 choice pending transition changed")
            last = control["consumed_challenges"][-1]
            if last["operation_id"] != operation_id or last["outcome"] != "V5_TRANSITION_PENDING":
                raise ResidentMediaV6Error("v6 consumed challenge transition changed")
            last["outcome"] = "COMMITTED"
            last["transition_result_sha256"] = result_sha
            control["pending_transition"] = None
            self._advance(control)
        except Exception as exc:
            self._tainted = True
            if isinstance(exc, ResidentMediaV6Error):
                raise
            raise ResidentMediaV6Error("v6 protected choice transition failed") from exc
        start_permit = None
        if challenge["phase"] == "RECHECK" and decision == "CONTINUE":
            start_permit = {
                "schema": "kira.resident_media_external_start_permit.v6",
                "session_id": self.session_id,
                "stimulus_id": challenge["stimulus_id"],
                "ordinal": challenge["ordinal"],
                "reservation_sha256": challenge["reservation_sha256"],
                "challenge_sha256": challenge_sha,
                "fresh_observation_sha256": fresh_sha,
                "v5_permit": transition_result,
                "live_execution_allowed_by_static_core": False,
            }
        return {
            "schema": "kira.resident_media_choice_receipt.v6",
            "decision": decision,
            "challenge_sha256": challenge_sha,
            "fresh_observation_sha256": fresh_sha,
            "presentation_authorized": start_permit is not None,
            "start_permit": start_permit,
            "live_execution_allowed": False,
        }

    def issue_capability(self, *, ttl_seconds: int = v5.MAX_RESERVATION_SECONDS) -> dict[str, Any]:
        return self._run_v5_transition(
            "ISSUE_CAPABILITY", lambda: self._v5.issue_capability(ttl_seconds=ttl_seconds)
        )

    def reserve_presentation(self, token: Mapping[str, Any]) -> dict[str, Any]:
        return self._run_v5_transition(
            "RESERVE_PRESENTATION", lambda: self._v5.reserve_presentation(token)
        )

    def consume_start_permit(self, permit: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_synced()
        if not isinstance(permit, Mapping):
            raise ResidentMediaV6Error("v6 start permit must be an object")
        _exact_keys(
            permit,
            {
                "schema",
                "session_id",
                "stimulus_id",
                "ordinal",
                "reservation_sha256",
                "challenge_sha256",
                "fresh_observation_sha256",
                "v5_permit",
                "live_execution_allowed_by_static_core",
            },
            "v6 start permit",
        )
        if permit.get("schema") != "kira.resident_media_external_start_permit.v6":
            raise ResidentMediaV6Error("v6 start permit schema changed")
        if permit.get("session_id") != self.session_id or permit.get(
            "live_execution_allowed_by_static_core"
        ) is not False:
            raise ResidentMediaV6Error("v6 start permit identity/status changed")
        control = self._control()
        committed = control["consumed_challenges"][-1] if control["consumed_challenges"] else None
        if not isinstance(committed, Mapping) or committed.get("outcome") != "COMMITTED":
            raise ResidentMediaV6Error("v6 start permit lacks a committed fresh choice")
        fresh = committed["fresh_observation"]
        if permit.get("challenge_sha256") != committed.get("challenge_sha256") or permit.get(
            "fresh_observation_sha256"
        ) != _record_sha(fresh):
            raise ResidentMediaV6Error("v6 start permit fresh-choice binding changed")
        for field in ("stimulus_id", "ordinal", "reservation_sha256"):
            if permit.get(field) != fresh.get(field):
                raise ResidentMediaV6Error(f"v6 start permit binding changed: {field}")
        if committed.get("decision") != "CONTINUE":
            raise ResidentMediaV6Error("v6 start permit lacks an affirmative recheck")
        v5_control = self._v5._control()
        if permit.get("v5_permit") != v5_control.get("permit"):
            raise ResidentMediaV6Error("v6 start permit changed from protected v5 state")
        return self._run_v5_transition(
            "CONSUME_START_PERMIT",
            lambda: self._v5.consume_start_permit(permit["v5_permit"]),
        )

    def record_presentation(self, observation: Mapping[str, Any]) -> str:
        if not isinstance(observation, Mapping):
            raise ResidentMediaV6Error("v6 presentation observation must be an object")
        _sha(
            observation.get("external_parent_observation_sha256"),
            "v6 external presentation observation",
            nonzero=True,
        )
        result = self._run_v5_transition(
            "RECORD_PRESENTATION", lambda: self._v5.record_presentation(observation)
        )
        return _sha(result, "v6 presentation result")

    def snapshot(self) -> dict[str, Any]:
        self._assert_synced()
        control = self._control()
        return {
            "schema": "kira.resident_media_voluntary_snapshot.v6",
            "v5_state": self._v5.snapshot(),
            "protected_anchor_generation": self._anchor_record["generation"],
            "active_choice_challenge": control["active_challenge"] is not None,
            "consumed_choice_challenge_count": len(control["consumed_challenges"]),
            "exact_post_cas_readback_required": True,
            "zero_external_observation_allowed": False,
            "live_execution_allowed": False,
        }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_summary.v6",
        "exact_model": EXACT_MODEL,
        "exact_digest": EXACT_DIGEST,
        "affirmative_choice_requires_exact_allowlist": True,
        "explicit_refusal_with_stray_positive_can_authorize": False,
        "fresh_choice_bound_to_trusted_dual_clock": True,
        "fresh_choice_bound_to_session_stimulus_reservation_nonce": True,
        "choice_nonce_protected_one_use": True,
        "protected_cas_requires_exact_post_commit_readback": True,
        "zero_external_observation_allowed": False,
        "live_execution_allowed": False,
        "live_backend_implemented_here": False,
    }
