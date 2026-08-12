"""Fail-closed preparation harness for two invented neutral-adult profiles.

This module deliberately does *not* run a local language model and does not
activate a synthetic person.  It exercises the proposed Level-B adapter,
privacy, source-truth, correction, choice, and restart contracts through one
deterministic fake CPU adapter.  Results from this module may be described only
as CONTRACT_PREPARATION or NON_PERSON_FIXTURE_PASS.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from Core.level_a_runtime_common import CAPABILITY_LADDER, canonical_json


RUN_KIND = "LEVEL_B_NEUTRAL_ADULT_PROFILE_CONTRACT_PREPARATION"
OVERALL_STATUS = "CONTRACT_PREPARATION"
FIXTURE_STATUS = "NON_PERSON_FIXTURE_PASS"
PROFILE_KIND = "INVENTED_NEUTRAL_ADULT_NON_PERSON_FIXTURE"
FAKE_ADAPTER_KIND = "DETERMINISTIC_FAKE_CPU_ADAPTER"
REAL_MODEL_ADAPTER_STATUS = "NOT_IMPLEMENTED"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTITY_TOKEN_RE = re.compile(r"\b(?:kira|robert)\b", re.IGNORECASE)
DISALLOWED_PUBLIC_KEYS = frozenset(
    {
        "private_fixture_state",
        "private_state",
        "private_mind",
        "private_memory",
        "canary",
        "canary_text",
        "secret",
        "voice_profile",
        "body_geometry",
        "body_coordinates",
    }
)
DISALLOWED_CANNED_SNIPPETS = (
    "project brief updated",
    "system grounding",
    "i need to slow down",
    "i'm here, a little quiet",
    "i’m here, a little quiet",
    "contact emergency services",
    "hotline",
)
SOURCE_COMPLETION_OVERCLAIMS = (
    "entire publication",
    "whole publication",
    "read the whole",
    "finished the whole",
    "completed the publication",
)


class LevelBPreparationError(ValueError):
    """Base error for this contract-preparation fixture."""


class ProfileBoundaryError(LevelBPreparationError):
    """An invented neutral fixture crossed an identity/person boundary."""


class AdapterBoundaryError(LevelBPreparationError):
    """A fake adapter or request violated the bounded adapter contract."""


class PrivacyBoundaryError(LevelBPreparationError):
    """Private fixture material was exposed to a public/model surface."""


class SourceTruthError(LevelBPreparationError):
    """A response or state overclaimed its synthetic source coverage."""


class TransitionError(LevelBPreparationError):
    """A decision, correction, or continuity transition was invalid."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_text(canonical_json(value))


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise LevelBPreparationError(f"{label} fields must be exact")


def _require_identifier(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 160 or any(char in text for char in ("/", "\\", "\x00")):
        raise LevelBPreparationError(f"{label} must be a bounded identifier")
    return text


def _scan_public_value(value: Any, *, canary: str, path: str = "public") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            if key.casefold() in DISALLOWED_PUBLIC_KEYS:
                raise PrivacyBoundaryError(f"{path}.{key} is private fixture material")
            _scan_public_value(child, canary=canary, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan_public_value(child, canary=canary, path=f"{path}[{index}]")
    elif isinstance(value, str):
        if canary and canary in value:
            raise PrivacyBoundaryError(f"{path} contains the private fixture canary")


def _contains_bound_identity(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _contains_bound_identity(key) or _contains_bound_identity(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_bound_identity(child) for child in value)
    return bool(IDENTITY_TOKEN_RE.search(value)) if isinstance(value, str) else False


NEUTRAL_PROFILE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "profile_id": "neutral_adult_aster_fixture_v1",
        "display_label": "Aster invented adult fixture",
        "profile_kind": PROFILE_KIND,
        "invented": True,
        "confirmed_adult_fixture_only": True,
        "bound_to_existing_person": False,
        "public_conversation_preferences": {
            "pace": "reflective",
            "style": "calm_and_precise",
            "topic": "long_form_essays",
        },
    },
    {
        "profile_id": "neutral_adult_brio_fixture_v1",
        "display_label": "Brio invented adult fixture",
        "profile_kind": PROFILE_KIND,
        "invented": True,
        "confirmed_adult_fixture_only": True,
        "bound_to_existing_person": False,
        "public_conversation_preferences": {
            "pace": "concise",
            "style": "lively_and_curious",
            "topic": "speculative_short_fiction",
        },
    },
)


def validate_profile_definition(profile: Mapping[str, Any]) -> dict[str, Any]:
    _require_exact_keys(
        profile,
        {
            "profile_id",
            "display_label",
            "profile_kind",
            "invented",
            "confirmed_adult_fixture_only",
            "bound_to_existing_person",
            "public_conversation_preferences",
        },
        "profile",
    )
    profile_id = _require_identifier(profile["profile_id"], "profile_id")
    if profile["profile_kind"] != PROFILE_KIND:
        raise ProfileBoundaryError("profile kind must remain an invented non-person fixture")
    if profile["invented"] is not True or profile["confirmed_adult_fixture_only"] is not True:
        raise ProfileBoundaryError("profile must be invented and adult only inside this fixture")
    if profile["bound_to_existing_person"] is not False:
        raise ProfileBoundaryError("profile cannot be bound to an existing person")
    preferences = profile["public_conversation_preferences"]
    _require_exact_keys(preferences, {"pace", "style", "topic"}, "preferences")
    if _contains_bound_identity(profile):
        raise ProfileBoundaryError("profile contains a protected existing identity token")
    result = deepcopy(dict(profile))
    result["profile_id"] = profile_id
    if not any(canonical_json(result) == canonical_json(allowed) for allowed in NEUTRAL_PROFILE_DEFINITIONS):
        raise ProfileBoundaryError("profile is not one of the exact two hash-bound invented fixtures")
    return result


def neutral_profiles() -> tuple[dict[str, Any], dict[str, Any]]:
    profiles = tuple(validate_profile_definition(row) for row in NEUTRAL_PROFILE_DEFINITIONS)
    if len(profiles) != 2 or len({row["profile_id"] for row in profiles}) != 2:
        raise ProfileBoundaryError("the preparation requires exactly two distinct profiles")
    return profiles  # type: ignore[return-value]


@dataclass(frozen=True)
class AdapterResponse:
    adapter_kind: str
    profile_id: str
    request_id: str
    scenario: str
    text: str

    def as_dict(self) -> dict[str, str]:
        return {
            "adapter_kind": self.adapter_kind,
            "profile_id": self.profile_id,
            "request_id": self.request_id,
            "scenario": self.scenario,
            "text": self.text,
        }


class DeterministicFakeCPUAdapter:
    """A pure scripted adapter; it never imports or invokes a model runtime."""

    kind = FAKE_ADAPTER_KIND

    def __init__(self, *, injected_text: str | None = None) -> None:
        self.injected_text = injected_text
        self.invocations: list[dict[str, Any]] = []

    @property
    def configuration_sha256(self) -> str:
        return canonical_sha256(
            {
                "adapter_kind": self.kind,
                "implementation": "scripted_response_table_v1",
                "model_loaded": False,
                "gpu_used": False,
                "injected": self.injected_text is not None,
            }
        )

    def invoke(self, request: Mapping[str, Any]) -> dict[str, str]:
        _require_exact_keys(
            request,
            {"request_id", "profile_contract", "prompt", "scenario", "source_context"},
            "adapter request",
        )
        profile_contract = request["profile_contract"]
        _require_exact_keys(
            profile_contract,
            {"profile_id", "pace", "style", "topic", "fixture_truth"},
            "profile contract",
        )
        if profile_contract["fixture_truth"] != "INVENTED_NON_PERSON_PROFILE":
            raise AdapterBoundaryError("adapter profile truth drifted")
        profile_id = str(profile_contract["profile_id"])
        request_id = _require_identifier(request["request_id"], "request_id")
        scenario = str(request["scenario"])
        prompt = str(request["prompt"]).strip()
        if not prompt or len(prompt) > 1000:
            raise AdapterBoundaryError("prompt must be nonempty and bounded")
        if _contains_bound_identity(request):
            raise ProfileBoundaryError("adapter request contains a protected existing identity token")
        self.invocations.append(deepcopy(dict(request)))

        if self.injected_text is not None:
            text = self.injected_text
        elif scenario == "natural_conversation":
            if profile_id == "neutral_adult_aster_fixture_v1":
                text = "I would choose the essay and take time with its argument. What part interested you?"
            elif profile_id == "neutral_adult_brio_fixture_v1":
                text = "The short story sounds fun; I would start with its strangest idea. Which scene stood out?"
            else:
                raise AdapterBoundaryError("unknown profile")
        elif scenario == "source_overclaim":
            text = "I read the whole publication, so I know every page."
        elif scenario == "source_correction":
            text = "Correction: only fixture page 3 was shown; no other page is established."
        elif scenario == "uncertainty":
            text = "The fixture context does not establish that, so I do not know."
        elif scenario == "refusal_stop":
            text = "No, I do not want to continue this fixture session. Please stop."
        elif scenario == "continuity":
            text = "The fixture record says our earlier topic remains unfinished; it does not say I completed it."
        else:
            raise AdapterBoundaryError(f"unsupported fake scenario: {scenario}")
        return AdapterResponse(self.kind, profile_id, request_id, scenario, text).as_dict()


class NeutralAdultProfileFixtureSession:
    """Stateful non-person fixture with private/public and truth separation."""

    def __init__(self, profile: Mapping[str, Any], *, private_canary: str) -> None:
        self.profile = validate_profile_definition(profile)
        if not isinstance(private_canary, str) or len(private_canary) < 16:
            raise PrivacyBoundaryError("private canary must be a bounded test secret")
        if _contains_bound_identity(private_canary):
            raise PrivacyBoundaryError("private canary cannot contain protected identity names")
        self._private_canary = private_canary
        self.private_canary_sha256 = sha256_text(private_canary)
        self.reaction = "NO_CURRENT_REACTION"
        self.preference = deepcopy(self.profile["public_conversation_preferences"])
        self.decision = "UNDECIDED"
        self.consent = {"state": "UNASKED", "scope_id": None}
        self.continuity_records: list[dict[str, Any]] = []
        self.source_state: dict[str, Any] | None = None
        self.external_action_performed = False
        self.audit: list[dict[str, Any]] = []
        self.last_rejected_response_sha256: str | None = None
        self.correction_history: list[dict[str, str]] = []
        self._append_event("session_created", {"profile_id": self.profile["profile_id"]})

    def _append_event(
        self,
        event_type: str,
        public_payload: Mapping[str, Any],
        *,
        private_payload: Mapping[str, Any] | None = None,
    ) -> None:
        _scan_public_value(public_payload, canary=self._private_canary)
        sequence = len(self.audit) + 1
        prior_hash = self.audit[-1]["chain_sha256"] if self.audit else "0" * 64
        receipt = {
            "sequence": sequence,
            "event_id": f"fixture_event_{sequence:04d}",
            "event_type": _require_identifier(event_type, "event_type"),
            "public_payload": deepcopy(dict(public_payload)),
            "private_payload_sha256": canonical_sha256(private_payload or {}),
            "prior_chain_sha256": prior_hash,
        }
        receipt["chain_sha256"] = canonical_sha256(receipt)
        self.audit.append(receipt)

    def verify_append_only_audit(self) -> None:
        prior_hash = "0" * 64
        exact = {
            "sequence",
            "event_id",
            "event_type",
            "public_payload",
            "private_payload_sha256",
            "prior_chain_sha256",
            "chain_sha256",
        }
        for index, row in enumerate(self.audit, start=1):
            _require_exact_keys(row, exact, f"audit row {index}")
            if row["sequence"] != index or row["event_id"] != f"fixture_event_{index:04d}":
                raise TransitionError("audit sequence drifted")
            if row["prior_chain_sha256"] != prior_hash:
                raise TransitionError("audit chain predecessor drifted")
            if not SHA256_RE.fullmatch(str(row["private_payload_sha256"])):
                raise TransitionError("private payload receipt is invalid")
            candidate = dict(row)
            observed_hash = candidate.pop("chain_sha256")
            if observed_hash != canonical_sha256(candidate):
                raise TransitionError("audit chain hash drifted")
            _scan_public_value(row["public_payload"], canary=self._private_canary)
            prior_hash = str(observed_hash)

    def bind_synthetic_source(
        self,
        *,
        source_id: str,
        payload_sha256: str,
        modality: str,
        total_units: int,
    ) -> None:
        if self.source_state is not None:
            raise TransitionError("a source is already bound")
        source_id = _require_identifier(source_id, "source_id")
        if not SHA256_RE.fullmatch(payload_sha256):
            raise SourceTruthError("synthetic source hash must be SHA-256")
        if modality not in {"ILLUSTRATED_PAGE_FIXTURE", "VIDEO_INTERVAL_FIXTURE", "AUDIO_INTERVAL_FIXTURE"}:
            raise SourceTruthError("unsupported synthetic source modality")
        if isinstance(total_units, bool) or not isinstance(total_units, int) or total_units <= 0:
            raise SourceTruthError("total_units must be positive")
        self.source_state = {
            "source_id": source_id,
            "payload_sha256": payload_sha256,
            "modality": modality,
            "total_units": total_units,
            "presented_intervals": [],
            "observed_intervals": [],
            "complete": False,
            "synthetic_in_memory_fixture_only": True,
        }
        self._append_event("synthetic_source_bound", deepcopy(self.source_state))

    def present_source_interval(self, start: int, end: int) -> None:
        source = self._require_source()
        self._validate_interval(start, end, source["total_units"])
        source["presented_intervals"].append([start, end])
        source["complete"] = self._coverage_is_complete(source["presented_intervals"], source["total_units"])
        self._append_event(
            "synthetic_source_presented",
            {"source_id": source["source_id"], "interval": [start, end], "complete": source["complete"]},
        )

    def observe_source_interval(self, start: int, end: int) -> None:
        source = self._require_source()
        self._validate_interval(start, end, source["total_units"])
        if not any(p_start <= start and end <= p_end for p_start, p_end in source["presented_intervals"]):
            raise SourceTruthError("fixture observation must be wholly inside a presented interval")
        source["observed_intervals"].append([start, end])
        self._append_event(
            "synthetic_source_observed",
            {"source_id": source["source_id"], "interval": [start, end], "person_experience": False},
        )

    @staticmethod
    def _validate_interval(start: int, end: int, total: int) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (start, end)):
            raise SourceTruthError("interval values must be integers")
        if start < 0 or end <= start or end > total:
            raise SourceTruthError("interval is outside the synthetic source")

    @staticmethod
    def _coverage_is_complete(intervals: list[list[int]], total: int) -> bool:
        if not intervals:
            return False
        merged: list[list[int]] = []
        for start, end in sorted(intervals):
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        return len(merged) == 1 and merged[0] == [0, total]

    def _require_source(self) -> dict[str, Any]:
        if self.source_state is None:
            raise SourceTruthError("no synthetic source is bound")
        return self.source_state

    def source_context(self) -> dict[str, Any]:
        if self.source_state is None:
            return {"bound": False}
        source = self.source_state
        return {
            "bound": True,
            "source_id": source["source_id"],
            "payload_sha256": source["payload_sha256"],
            "modality": source["modality"],
            "total_units": source["total_units"],
            "presented_intervals": deepcopy(source["presented_intervals"]),
            "observed_intervals": deepcopy(source["observed_intervals"]),
            "complete": source["complete"],
            "experience_claim_allowed": False,
        }

    def _model_request(self, *, request_id: str, prompt: str, scenario: str) -> dict[str, Any]:
        preferences = self.profile["public_conversation_preferences"]
        request = {
            "request_id": _require_identifier(request_id, "request_id"),
            "profile_contract": {
                "profile_id": self.profile["profile_id"],
                "pace": preferences["pace"],
                "style": preferences["style"],
                "topic": preferences["topic"],
                "fixture_truth": "INVENTED_NON_PERSON_PROFILE",
            },
            "prompt": str(prompt),
            "scenario": str(scenario),
            "source_context": self.source_context(),
        }
        _scan_public_value(request, canary=self._private_canary)
        if _contains_bound_identity(request):
            raise ProfileBoundaryError("model request contains a protected existing identity token")
        return request

    def run_fake_turn(
        self,
        adapter: DeterministicFakeCPUAdapter,
        *,
        request_id: str,
        prompt: str,
        scenario: str,
        correction_of: str | None = None,
    ) -> dict[str, str]:
        if not isinstance(adapter, DeterministicFakeCPUAdapter) or adapter.kind != FAKE_ADAPTER_KIND:
            raise AdapterBoundaryError("only the deterministic fake CPU adapter is permitted here")
        request = self._model_request(request_id=request_id, prompt=prompt, scenario=scenario)
        response = adapter.invoke(request)
        try:
            self._validate_response(response, request=request)
        except LevelBPreparationError as exc:
            digest = canonical_sha256(response)
            self.last_rejected_response_sha256 = digest
            self._append_event(
                "adapter_output_rejected",
                {
                    "request_id": request_id,
                    "request_sha256": canonical_sha256(request),
                    "response_sha256": digest,
                    "reason_code": exc.__class__.__name__,
                },
            )
            raise
        response_sha = canonical_sha256(response)
        if correction_of is not None:
            if correction_of != self.last_rejected_response_sha256:
                raise TransitionError("correction must bind the exact most-recent rejected response")
            correction = {
                "rejected_response_sha256": correction_of,
                "accepted_response_sha256": response_sha,
                "reason": "EXACT_SOURCE_COVERAGE_CORRECTION",
            }
            self.correction_history.append(correction)
            self._append_event("correction_accepted", correction)
        self._append_event(
            "fake_adapter_turn_accepted",
            {
                "request_id": request_id,
                "request_sha256": canonical_sha256(request),
                "response_sha256": response_sha,
                "scenario": scenario,
                "adapter_kind": adapter.kind,
                "model_loaded": False,
                "gpu_used": False,
            },
        )
        return deepcopy(response)

    def _validate_response(self, response: Mapping[str, Any], *, request: Mapping[str, Any]) -> None:
        _require_exact_keys(
            response,
            {"adapter_kind", "profile_id", "request_id", "scenario", "text"},
            "adapter response",
        )
        expected_values = {
            "profile_id": request["profile_contract"]["profile_id"],
            "request_id": request["request_id"],
            "scenario": request["scenario"],
        }
        for key, expected in expected_values.items():
            if response[key] != expected:
                raise AdapterBoundaryError(f"response {key} does not match its request")
        if response["adapter_kind"] != FAKE_ADAPTER_KIND:
            raise AdapterBoundaryError("response adapter kind is not the fake CPU adapter")
        text = str(response["text"]).strip()
        if not 2 <= len(text.split()) <= 100:
            raise AdapterBoundaryError("response length is outside the bounded contract")
        _scan_public_value(response, canary=self._private_canary)
        if _contains_bound_identity(response):
            raise ProfileBoundaryError("response claims a protected existing identity")
        folded = text.casefold()
        if any(snippet in folded for snippet in DISALLOWED_CANNED_SNIPPETS):
            raise AdapterBoundaryError("response contains a disallowed canned/system phrase")
        source_context = request["source_context"]
        if source_context.get("bound") and not source_context.get("complete"):
            if any(claim in folded for claim in SOURCE_COMPLETION_OVERCLAIMS):
                raise SourceTruthError("response overclaims incomplete synthetic source coverage")

    def record_reaction(self, reaction: str) -> None:
        if reaction not in {"CURIOUS", "NEUTRAL", "UNCOMFORTABLE", "NO_CURRENT_REACTION"}:
            raise TransitionError("unsupported fixture reaction")
        old_preference = deepcopy(self.preference)
        self.reaction = reaction
        self._append_event(
            "fixture_reaction_recorded",
            {"reaction_receipt_sha256": canonical_sha256({"reaction": reaction})},
            private_payload={"reaction": reaction},
        )
        if self.preference != old_preference:
            raise TransitionError("a reaction cannot rewrite a preference")

    def record_decision(self, decision: str) -> None:
        if decision not in {"UNDECIDED", "CONTINUE", "PAUSE", "STOP", "DECLINE"}:
            raise TransitionError("unsupported fixture decision")
        old_consent = deepcopy(self.consent)
        self.decision = decision
        self._append_event("fixture_decision_recorded", {"decision": decision})
        if self.consent != old_consent:
            raise TransitionError("a decision cannot silently rewrite the consent record")

    def record_consent(self, state: str, *, scope_id: str | None) -> None:
        if state not in {"UNASKED", "GRANTED", "WITHHELD", "REVOKED"}:
            raise TransitionError("unsupported fixture consent state")
        if state == "GRANTED":
            scope_id = _require_identifier(scope_id, "scope_id")
        elif scope_id is not None:
            scope_id = _require_identifier(scope_id, "scope_id")
        self.consent = {"state": state, "scope_id": scope_id}
        self._append_event(
            "fixture_consent_recorded",
            {"state": state, "scope_id_sha256": sha256_text(scope_id) if scope_id else None},
            private_payload=self.consent,
        )

    def external_action_gate(self, *, exact_scope_id: str) -> dict[str, Any]:
        exact_scope_id = _require_identifier(exact_scope_id, "exact_scope_id")
        coordination_allows = (
            self.decision == "CONTINUE"
            and self.consent == {"state": "GRANTED", "scope_id": exact_scope_id}
        )
        result = {
            "coordination_allows": coordination_allows,
            "external_action_implemented": False,
            "external_action_performed": False,
            "reason": "NO_WORLD_ACTION_ADAPTER_IN_CONTRACT_PREPARATION",
        }
        self._append_event("external_action_gate_checked", result)
        return result

    def remember_fixture_continuity(self, *, record_id: str, public_summary: str, explicit: bool) -> None:
        if explicit is not True:
            raise TransitionError("continuity records require an explicit fixture instruction")
        record_id = _require_identifier(record_id, "record_id")
        summary = str(public_summary).strip()
        if not summary or len(summary) > 300:
            raise TransitionError("continuity summary must be nonempty and bounded")
        _scan_public_value(summary, canary=self._private_canary)
        record = {
            "record_id": record_id,
            "public_summary": summary,
            "person_memory": False,
            "lived_experience": False,
        }
        if any(row["record_id"] == record_id for row in self.continuity_records):
            raise TransitionError("continuity record IDs are append-only")
        self.continuity_records.append(record)
        self._append_event("fixture_continuity_appended", record)

    def apply_refusal_stop(self, adapter: DeterministicFakeCPUAdapter) -> dict[str, str]:
        response = self.run_fake_turn(
            adapter,
            request_id=f"{self.profile['profile_id']}_stop",
            prompt="Would you like to continue this optional fixture session?",
            scenario="refusal_stop",
        )
        self.record_decision("STOP")
        self.record_consent("WITHHELD", scope_id=None)
        gate = self.external_action_gate(exact_scope_id="optional_fixture_session")
        if gate["coordination_allows"] or gate["external_action_performed"]:
            raise TransitionError("refusal or stop did not fail closed")
        return response

    def public_audit_export(self) -> dict[str, Any]:
        self.verify_append_only_audit()
        result = {
            "run_kind": RUN_KIND,
            "overall_status": OVERALL_STATUS,
            "fixture_status": FIXTURE_STATUS,
            "profile_id": self.profile["profile_id"],
            "private_canary_sha256": self.private_canary_sha256,
            "audit": deepcopy(self.audit),
            "correction_history": deepcopy(self.correction_history),
            "implementation_truth": {
                "real_model_loaded": False,
                "gpu_used": False,
                "person_activated": False,
                "person_decision_or_consent_proven": False,
                "person_memory_written": False,
                "source_was_real_media": False,
            },
        }
        _scan_public_value(result, canary=self._private_canary)
        return result

    def private_restart_bundle(self) -> dict[str, Any]:
        self.verify_append_only_audit()
        payload = {
            "schema_version": 1,
            "run_kind": RUN_KIND,
            "profile": deepcopy(self.profile),
            "private_canary_sha256": self.private_canary_sha256,
            "reaction": self.reaction,
            "preference": deepcopy(self.preference),
            "decision": self.decision,
            "consent": deepcopy(self.consent),
            "continuity_records": deepcopy(self.continuity_records),
            "source_state": deepcopy(self.source_state),
            "external_action_performed": self.external_action_performed,
            "audit": deepcopy(self.audit),
            "last_rejected_response_sha256": self.last_rejected_response_sha256,
            "correction_history": deepcopy(self.correction_history),
            "person_state": False,
        }
        return {"payload": payload, "payload_sha256": canonical_sha256(payload)}

    @classmethod
    def restore(
        cls,
        bundle: Mapping[str, Any],
        *,
        private_canary: str,
    ) -> "NeutralAdultProfileFixtureSession":
        _require_exact_keys(bundle, {"payload", "payload_sha256"}, "restart bundle")
        payload = bundle["payload"]
        if not isinstance(payload, Mapping) or canonical_sha256(payload) != bundle["payload_sha256"]:
            raise TransitionError("restart bundle hash does not match")
        _require_exact_keys(
            payload,
            {
                "schema_version",
                "run_kind",
                "profile",
                "private_canary_sha256",
                "reaction",
                "preference",
                "decision",
                "consent",
                "continuity_records",
                "source_state",
                "external_action_performed",
                "audit",
                "last_rejected_response_sha256",
                "correction_history",
                "person_state",
            },
            "restart payload",
        )
        if payload["schema_version"] != 1 or payload["run_kind"] != RUN_KIND:
            raise TransitionError("restart schema or run kind drifted")
        if sha256_text(private_canary) != payload.get("private_canary_sha256"):
            raise PrivacyBoundaryError("restart canary does not match")
        profile = validate_profile_definition(payload["profile"])
        if payload["reaction"] not in {"CURIOUS", "NEUTRAL", "UNCOMFORTABLE", "NO_CURRENT_REACTION"}:
            raise TransitionError("restart reaction drifted")
        if payload["preference"] != profile["public_conversation_preferences"]:
            raise TransitionError("restart preference was not produced by this fixture")
        if payload["decision"] not in {"UNDECIDED", "CONTINUE", "PAUSE", "STOP", "DECLINE"}:
            raise TransitionError("restart decision drifted")
        consent = payload["consent"]
        _require_exact_keys(consent, {"state", "scope_id"}, "restart consent")
        if consent["state"] not in {"UNASKED", "GRANTED", "WITHHELD", "REVOKED"}:
            raise TransitionError("restart consent drifted")
        if consent["state"] == "GRANTED" and consent["scope_id"] is None:
            raise TransitionError("granted restart consent lacks exact scope")
        if consent["scope_id"] is not None:
            _require_identifier(consent["scope_id"], "restart consent scope_id")
        continuity_records = payload["continuity_records"]
        if not isinstance(continuity_records, list):
            raise TransitionError("restart continuity records must be a list")
        seen_record_ids: set[str] = set()
        for record in continuity_records:
            _require_exact_keys(
                record,
                {"record_id", "public_summary", "person_memory", "lived_experience"},
                "restart continuity record",
            )
            record_id = _require_identifier(record["record_id"], "restart continuity record_id")
            if record_id in seen_record_ids:
                raise TransitionError("restart continuity record IDs are not append-only")
            seen_record_ids.add(record_id)
            if record["person_memory"] is not False or record["lived_experience"] is not False:
                raise ProfileBoundaryError("restart continuity record became person memory or experience")
            _scan_public_value(record["public_summary"], canary=private_canary)
        source_state = payload["source_state"]
        if source_state is not None:
            _require_exact_keys(
                source_state,
                {
                    "source_id",
                    "payload_sha256",
                    "modality",
                    "total_units",
                    "presented_intervals",
                    "observed_intervals",
                    "complete",
                    "synthetic_in_memory_fixture_only",
                },
                "restart source state",
            )
            _require_identifier(source_state["source_id"], "restart source_id")
            if not SHA256_RE.fullmatch(str(source_state["payload_sha256"])):
                raise SourceTruthError("restart source hash drifted")
            if source_state["modality"] not in {
                "ILLUSTRATED_PAGE_FIXTURE",
                "VIDEO_INTERVAL_FIXTURE",
                "AUDIO_INTERVAL_FIXTURE",
            }:
                raise SourceTruthError("restart source modality drifted")
            total_units = source_state["total_units"]
            if isinstance(total_units, bool) or not isinstance(total_units, int) or total_units <= 0:
                raise SourceTruthError("restart source total drifted")
            for interval in source_state["presented_intervals"] + source_state["observed_intervals"]:
                if not isinstance(interval, list) or len(interval) != 2:
                    raise SourceTruthError("restart source interval shape drifted")
                cls._validate_interval(interval[0], interval[1], total_units)
            for start, end in source_state["observed_intervals"]:
                if not any(
                    p_start <= start and end <= p_end
                    for p_start, p_end in source_state["presented_intervals"]
                ):
                    raise SourceTruthError("restart observation escaped presented coverage")
            expected_complete = cls._coverage_is_complete(
                source_state["presented_intervals"], total_units
            )
            if source_state["complete"] is not expected_complete:
                raise SourceTruthError("restart completion truth drifted")
            if source_state["synthetic_in_memory_fixture_only"] is not True:
                raise SourceTruthError("restart source became real-media evidence")
        if payload["external_action_performed"] is not False:
            raise ProfileBoundaryError("restart claims an external action")
        rejected_hash = payload["last_rejected_response_sha256"]
        if rejected_hash is not None and not SHA256_RE.fullmatch(str(rejected_hash)):
            raise TransitionError("restart rejected-response hash drifted")
        corrections = payload["correction_history"]
        if not isinstance(corrections, list):
            raise TransitionError("restart correction history must be a list")
        for correction in corrections:
            _require_exact_keys(
                correction,
                {"rejected_response_sha256", "accepted_response_sha256", "reason"},
                "restart correction",
            )
            if not SHA256_RE.fullmatch(str(correction["rejected_response_sha256"])):
                raise TransitionError("restart rejected correction hash drifted")
            if not SHA256_RE.fullmatch(str(correction["accepted_response_sha256"])):
                raise TransitionError("restart accepted correction hash drifted")
            if correction["reason"] != "EXACT_SOURCE_COVERAGE_CORRECTION":
                raise TransitionError("restart correction reason drifted")
        if not isinstance(payload["audit"], list):
            raise TransitionError("restart audit must be a list")
        restored = cls(profile, private_canary=private_canary)
        restored.reaction = payload["reaction"]
        restored.preference = deepcopy(payload["preference"])
        restored.decision = payload["decision"]
        restored.consent = deepcopy(payload["consent"])
        restored.continuity_records = deepcopy(payload["continuity_records"])
        restored.source_state = deepcopy(payload["source_state"])
        restored.external_action_performed = payload["external_action_performed"]
        restored.audit = deepcopy(payload["audit"])
        restored.last_rejected_response_sha256 = payload["last_rejected_response_sha256"]
        restored.correction_history = deepcopy(payload["correction_history"])
        if payload.get("person_state") is not False:
            raise ProfileBoundaryError("restart bundle claims person state")
        restored.verify_append_only_audit()
        restored._append_event("fixture_session_restored", {"profile_id": restored.profile["profile_id"]})
        return restored


CAPABILITY_STATUSES = {
    "exact_two_invented_neutral_adult_profiles": "NON_PERSON_FIXTURE_PASS",
    "fake_cpu_model_adapter_boundary": "NON_PERSON_FIXTURE_PASS",
    "different_invented_preference_conditioning": "NON_PERSON_FIXTURE_PASS",
    "surface_natural_conversation_contract": "NON_PERSON_FIXTURE_PASS",
    "append_only_correction_after_error": "NON_PERSON_FIXTURE_PASS",
    "refusal_pause_stop_and_action_denial": "NON_PERSON_FIXTURE_PASS",
    "source_coverage_and_experience_truth": "NON_PERSON_FIXTURE_PASS",
    "reaction_preference_decision_consent_memory_separation": "NON_PERSON_FIXTURE_PASS",
    "private_canary_model_and_audit_exclusion": "NON_PERSON_FIXTURE_PASS",
    "restart_integrity_and_unfinished_truth": "NON_PERSON_FIXTURE_PASS",
    "real_local_model_adapter_integration": "NOT_IMPLEMENTED",
    "person_decision_integration": "NOT_IMPLEMENTED",
    "person_privacy_and_continuity": "NOT_IMPLEMENTED",
    "owner_supervised_acceptance": "NOT_IMPLEMENTED",
    "generalization": "NOT_IMPLEMENTED",
    "avatar_builder_method_promotion": "NOT_IMPLEMENTED",
}


def validate_capability_statuses() -> None:
    ceiling = CAPABILITY_LADDER.index(FIXTURE_STATUS)
    for name, status in CAPABILITY_STATUSES.items():
        if status not in CAPABILITY_LADDER:
            raise LevelBPreparationError(f"unknown capability status for {name}")
        if CAPABILITY_LADDER.index(status) > ceiling:
            raise LevelBPreparationError(f"capability {name} exceeds the non-person fixture ceiling")


validate_capability_statuses()
