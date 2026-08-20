from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import datetime
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .backends import (
    ALLOWED_SOURCES,
    ALLOWED_UNCERTAINTY,
    BackendResult,
    ConversationBackend,
    DeterministicStubBackend,
    SAFE_REFLECTION,
)
from .embodiment import ALLOWED_CAPABILITIES, EMBODIMENT_BOUNDARY, SAFE_ENDPOINT, EmbodimentManager
from .life_loops import LifeLoopManager
from .paths import LocalSandbox, default_data_root
from .profiles import PublicProfile, load_profile
from .records import (
    AppendOnlyJSONL,
    StorageCorruption,
    canonical_json,
    exclusive_file_lock,
    stable_event_id,
    utc_now,
)
from .state import AppraisalState, BOUNDARY_NOTICE, appraise_ephemeral_input
from .strict_json import load_path_strict


TURN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
PUBLIC_TEST_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]{1,31}-[A-Z0-9]{1,31}\b")
SELF_INTRODUCTION = re.compile(
    r"\b(?i:my name is)\s+"
    r"(?P<name>[A-Z][A-Za-z'’-]{0,31}(?:\s+[A-Z][A-Za-z'’-]{0,31}){0,2})"
    r"(?=\s*(?:[,!.?]|$|\band\b|\bfrom\b|\bwith\b))"
)
MEMORY_QUERY_TERM = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]{2,}")
MEMORY_QUERY_STOPWORDS = frozenset(
    {
        "about",
        "and",
        "after",
        "again",
        "answer",
        "back",
        "could",
        "details",
        "did",
        "from",
        "have",
        "into",
        "job",
        "know",
        "like",
        "liked",
        "looking",
        "memory",
        "part",
        "remember",
        "remembered",
        "remembering",
        "tell",
        "that",
        "the",
        "their",
        "there",
        "these",
        "they",
        "this",
        "thinking",
        "time",
        "what",
        "when",
        "where",
        "which",
        "with",
        "would",
        "work",
        "worked",
        "working",
        "your",
        "you",
        "was",
        "were",
    }
)


def _memory_terms(text: str) -> set[str]:
    """Return exact lexical terms; never count short substrings inside words."""

    return {
        match.group(0).casefold()
        for match in MEMORY_QUERY_TERM.finditer(text)
        if match.group(0).casefold() not in MEMORY_QUERY_STOPWORDS
    }


def _normalized_memory_surface(text: str) -> str:
    return " ".join(
        match.group(0).casefold()
        for match in re.finditer(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)
    )


def _reviewed_contract_matches(item: Any, query_text: str) -> list[str]:
    if not isinstance(item, dict):
        return []
    normalized_query = f" {_normalized_memory_surface(query_text)} "
    matches: list[str] = []
    contracts = item.get("required_response_concepts", [])
    for contract in contracts if isinstance(contracts, list) else []:
        if not isinstance(contract, dict):
            continue
        triggers = contract.get("when_query_contains_any", [])
        for trigger in triggers if isinstance(triggers, list) else []:
            if not isinstance(trigger, str):
                continue
            normalized_trigger = _normalized_memory_surface(trigger)
            if normalized_trigger and f" {normalized_trigger} " in normalized_query:
                matches.append(trigger)
    return matches


def _reviewed_searchable_text(item: Any) -> str:
    """Index answer-bearing fields, never prohibitions or contract metadata."""

    if not isinstance(item, dict):
        return ""
    values: list[str] = []
    for key in ("summary", "text", "reflection", "claim", "content"):
        value = item.get(key)
        if isinstance(value, str):
            values.append(value)
    facts = item.get("facts", [])
    if isinstance(facts, list):
        values.extend(value for value in facts if isinstance(value, str))
    identity = item.get("identity")
    if item.get("kind") == "identity_and_continuity_boundary" and isinstance(identity, dict):
        for key in ("display_name", "variant_kind"):
            value = identity.get(key)
            if isinstance(value, str):
                values.append(value)
    return " ".join(values)


def _query_requests_self_introduced_identity(text: str) -> bool:
    normalized = f" {_normalized_memory_surface(text)} "
    phrases = (
        " who am i ",
        " what is my name ",
        " remember my name ",
        " remember who i am ",
        " do you remember me ",
        " who did i say i am ",
        " who did i tell you i am ",
        " what role did i tell you ",
    )
    return any(phrase in normalized for phrase in phrases)
REFLECTION_DISCLOSURE = (
    "Short deterministic runtime-derived functional appraisal note. Model-authored reflection text is "
    "discarded; this channel is not chain-of-thought, hidden reasoning, a private mental state, a clinical "
    "record, or evidence of consciousness."
)
FACT_DISCLOSURE = (
    "Structured model claim with declared provenance and uncertainty; not automatically a verified truth."
)
REVIEWED_NOTE_DISCLOSURE = (
    "Exact operator-supplied reviewed continuity note. The reviewer label is not authenticated; the note is "
    "append-only and may point to an older same-profile fact but is not automatic truth or deletion."
)
INPUT_RETENTION_NOTICE = (
    "full_raw_user_utterance_not_persisted; an explicit 'my name is' label may be retained "
    "separately as an unverified acquaintance record"
)
BRANCH_BOUNDARY = (
    "Separate installations share only the explicitly imported checkpoint. New life loops remain "
    "branch-local unless selected records are reviewed, exported, and imported."
)
APPRAISAL_KEYS = frozenset({"valence", "arousal", "engagement", "confidence"})
TRANSACTION_KEYS = frozenset(
    {
        "schema_version",
        "event_id",
        "timestamp",
        "profile_id",
        "branch_id",
        "turn_id",
        "loop_id",
        "input_retention",
        "speech",
        "reflection",
        "factual_claims",
        "functional_state_before",
        "functional_state_after",
        "backend",
        "model",
        "model_digest",
        "model_digest_kind",
        "fallback_reason",
        "embodiment_intentions",
    }
)
MATERIALIZATION_KEYS = frozenset(
    {
        "schema_version",
        "event_id",
        "timestamp",
        "profile_id",
        "branch_id",
        "turn_id",
        "transaction_event_id",
        "recovered_after_restart",
        "embodiment_plan_present_in_transaction",
    }
)
MODEL_DIGEST_KINDS = frozenset(
    {"unavailable", "not_applicable_stub", "ollama_reported_manifest_sha256"}
)


def _is_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 40 or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value
    ):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def _is_bounded_plain_text(value: Any, maximum: int, *, allow_empty: bool = False) -> bool:
    return bool(
        isinstance(value, str)
        and (allow_empty or value.strip())
        and len(value) <= maximum
        and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value)
    )


@dataclass(frozen=True)
class RuntimeResponse:
    turn_id: str
    loop_id: str
    speech: str
    reflection: str
    factual_claims: tuple[dict[str, str], ...]
    functional_state: AppraisalState
    backend: str
    model: str
    model_digest: str | None
    model_digest_kind: str
    fallback_reason: str | None
    embodiment_intentions: tuple[dict[str, Any], ...]
    branch_id: str


class ConversationRuntime:
    """Durable local runtime with privacy-minimal persistence and idempotent turns."""

    def __init__(
        self,
        profile_id: str,
        *,
        data_root: str | Path | None = None,
        backend: ConversationBackend | None = None,
    ):
        self.profile: PublicProfile = load_profile(profile_id)
        self.sandbox = LocalSandbox(data_root or default_data_root())
        person = self.sandbox.person_dir(profile_id)
        self._mutation_lock_path = person / ".profile-mutation.lock"
        with exclusive_file_lock(self._mutation_lock_path):
            self.branch_id = self._load_or_create_branch_identity(person)
        self.transactions = AppendOnlyJSONL(person / "turn_transactions.jsonl")
        self.spoken = AppendOnlyJSONL(person / "spoken.jsonl")
        self.reflections = AppendOnlyJSONL(person / "reflections.jsonl")
        self.facts = AppendOnlyJSONL(person / "factual_claims.jsonl")
        self.state_events = AppendOnlyJSONL(person / "appraisal_state.jsonl")
        self.voice_events = AppendOnlyJSONL(person / "voice_events.jsonl")
        self.reviewed_imports = AppendOnlyJSONL(person / "reviewed_imports.jsonl")
        self.acquaintances = AppendOnlyJSONL(person / "acquaintances.jsonl")
        self.materializations = AppendOnlyJSONL(person / "turn_materializations.jsonl")
        self.backend = backend or DeterministicStubBackend()
        self.life_loops = LifeLoopManager(self.sandbox, profile_id, self.branch_id)
        self.embodiment = EmbodimentManager(self.sandbox, self.branch_id)
        with self.mutation_guard():
            self._recover_committed_transactions()

    @property
    def profile_id(self) -> str:
        return self.profile.profile_id

    def begin_life_loop(self) -> str:
        with self.mutation_guard():
            return self.life_loops.start().loop_id

    def mutation_guard(self):
        """Serialize one profile/data-root mutation across threads and processes."""

        return exclusive_file_lock(self._mutation_lock_path)

    def _load_or_create_branch_identity(self, person: Path) -> str:
        path = person / "branch_identity.json"
        if not path.exists():
            document = {
                "schema_version": 1,
                "profile_id": self.profile.profile_id,
                "branch_id": uuid.uuid4().hex,
                "created_at": utc_now(),
                "origin": "new_local_installation_from_shared_reviewed_handoff",
                "boundary": BRANCH_BOUNDARY,
            }
            temporary = person / f".branch_identity.{uuid.uuid4().hex}.tmp"
            try:
                with temporary.open("x", encoding="utf-8", newline="\n") as handle:
                    json.dump(document, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        try:
            loaded = load_path_strict(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("local branch identity is missing or corrupt") from exc
        required = {"schema_version", "profile_id", "branch_id", "created_at", "origin", "boundary"}
        if (
            not isinstance(loaded, dict)
            or set(loaded) != required
            or loaded.get("schema_version") != 1
            or loaded.get("profile_id") != self.profile.profile_id
            or not re.fullmatch(r"[0-9a-f]{32}", str(loaded.get("branch_id", "")))
            or not _is_utc_timestamp(loaded.get("created_at"))
            or loaded.get("origin") != "new_local_installation_from_shared_reviewed_handoff"
            or loaded.get("boundary") != BRANCH_BOUNDARY
        ):
            raise ValueError("local branch identity schema or profile binding is invalid")
        return str(loaded["branch_id"])

    def close_life_loop(self, reason: str = "completed") -> dict[str, Any]:
        with self.mutation_guard():
            return self.life_loops.close(
                spoken=self.spoken,
                facts=self.facts,
                state_events=self.state_events,
                reason=reason,
            )

    def functional_state(self) -> AppraisalState:
        return AppraisalState.replay(self.state_events.records())

    def continuity_view(self, query_text: str | None = None) -> dict[str, Any]:
        all_spoken_records = self.spoken.records()
        all_fact_records = self.facts.records()
        prior_spoken = [
            {"event_id": record["event_id"], "text": str(record["text"])[:800]}
            for record in all_spoken_records[-3:]
        ]
        # This small, non-prunable surface-history lane exists only for the
        # public answer style/duplication guard. It never contains user input.
        quality_recent_spoken = [
            {"event_id": record["event_id"], "text": str(record["text"])[:260]}
            for record in all_spoken_records[-4:]
        ]
        prior_facts = [
            {
                "event_id": record["event_id"],
                "claim": str(record["claim"])[:600],
                "source": record["source"],
                "uncertainty": record["uncertainty"],
                "status": record.get("status", "model_claim_not_verified_truth"),
                "supersedes_event_ids": list(record.get("supersedes_event_ids", [])),
            }
            for record in all_fact_records[-6:]
        ]
        all_reviewed_records = self.reviewed_imports.records()
        all_acquaintance_records = self.acquaintances.records()
        # Keep one projected label per normalized name, ordered by the most
        # recent introduction event. The append-only encounter history remains
        # intact, while a returning person becomes the latest active label.
        projected_acquaintance_records_reversed: list[dict[str, Any]] = []
        projected_names: set[str] = set()
        for record in reversed(all_acquaintance_records):
            normalized_name = str(record.get("introduced_name", "")).casefold().strip()
            if not normalized_name or normalized_name in projected_names:
                continue
            projected_names.add(normalized_name)
            projected_acquaintance_records_reversed.append(record)
        projected_acquaintance_records = list(reversed(projected_acquaintance_records_reversed))
        identity_records = [
            record
            for record in all_reviewed_records
            if isinstance(record.get("item"), dict)
            and record["item"].get("kind") == "identity_and_continuity_boundary"
        ]
        nonidentity_records = [record for record in all_reviewed_records if record not in identity_records]
        reviewed_items: list[dict[str, Any]] = []
        relevant_reviewed_items: list[dict[str, Any]] = []
        relevant_prior_spoken: list[dict[str, Any]] = []
        relevant_prior_facts: list[dict[str, Any]] = []
        query_requests_person_identity = bool(
            query_text and _query_requests_self_introduced_identity(query_text)
        )
        if query_text:
            terms = _memory_terms(query_text)
            latest_introduced_name = ""
            if query_requests_person_identity and projected_acquaintance_records:
                latest_introduced_name = str(
                    projected_acquaintance_records[-1].get("introduced_name", "")
                )
                terms.update(
                    _memory_terms(latest_introduced_name)
                )
            ranked: list[tuple[int, int, int, int, dict[str, Any]]] = []
            for position, record in enumerate(all_reviewed_records):
                searchable = _reviewed_searchable_text(record["item"])
                searchable_terms = _memory_terms(searchable)
                matched = sorted(terms & searchable_terms)
                contract_matches = _reviewed_contract_matches(record["item"], query_text)
                item_kind = record["item"].get("kind") if isinstance(record["item"], dict) else None
                memory_kind = (
                    record["item"].get("memory_kind") if isinstance(record["item"], dict) else None
                )
                normalized_name = _normalized_memory_surface(latest_introduced_name)
                relationship_name_match = bool(
                    query_requests_person_identity
                    and normalized_name
                    and (item_kind == "review_relationship_context" or memory_kind == "review_relationship_context")
                    and f" {normalized_name} " in f" {_normalized_memory_surface(searchable)} "
                )
                if matched or contract_matches:
                    ranked.append(
                        (
                            2 if relationship_name_match else int(bool(contract_matches)),
                            len(matched),
                            sum(len(term) for term in matched),
                            position,
                            {
                                "event_id": record["event_id"],
                                "item": record["item"],
                                "source_digest": record["source_digest"],
                                "matched_reviewed_terms": matched,
                                "matched_response_contract_triggers": contract_matches,
                            },
                        )
                    )
            ranked.sort(key=lambda item: item[:4], reverse=True)
            if ranked:
                best_score = ranked[0][:3]
                relevant_reviewed_items = [
                    item[4] for item in ranked if item[:3] == best_score
                ][:2]

            ranked_spoken: list[tuple[int, int, dict[str, Any]]] = []
            for position, record in enumerate(all_spoken_records):
                searchable = str(record.get("text", "")).lower()
                matched = sorted(terms & _memory_terms(searchable))
                if matched:
                    ranked_spoken.append(
                        (
                            len(matched),
                            position,
                            {
                                "event_id": record["event_id"],
                                "text": str(record["text"])[:800],
                                "matched_conversation_terms": matched,
                            },
                        )
                    )
            ranked_spoken.sort(key=lambda item: (item[0], item[1]), reverse=True)
            recent_spoken_ids = {item["event_id"] for item in prior_spoken}
            relevant_prior_spoken = [
                item[2] for item in ranked_spoken if item[2]["event_id"] not in recent_spoken_ids
            ][:2]

            ranked_facts: list[tuple[int, int, dict[str, Any]]] = []
            for position, record in enumerate(all_fact_records):
                searchable = str(record.get("claim", "")).lower()
                matched = sorted(terms & _memory_terms(searchable))
                if matched:
                    ranked_facts.append(
                        (
                            len(matched),
                            position,
                            {
                                "event_id": record["event_id"],
                                "claim": str(record["claim"])[:600],
                                "source": record["source"],
                                "uncertainty": record["uncertainty"],
                                "status": record.get("status", "model_claim_not_verified_truth"),
                                "reviewed_by": record.get("reviewed_by"),
                                "supersedes_event_ids": list(record.get("supersedes_event_ids", [])),
                                "matched_conversation_terms": matched,
                            },
                        )
                    )
            ranked_facts.sort(key=lambda item: (item[0], item[1]), reverse=True)
            recent_fact_ids = {item["event_id"] for item in prior_facts}
            relevant_prior_facts = [
                item[2] for item in ranked_facts if item[2]["event_id"] not in recent_fact_ids
            ][:2]

        relevant_reviewed_ids = {item["event_id"] for item in relevant_reviewed_items}
        # When a query has a relevant reviewed item, adding unrelated recent
        # reviewed records buries the answer and wastes the small local-model
        # context. Retain the identity boundary plus relevant items only.
        fallback_count = 0 if relevant_reviewed_items else 3
        fallback_records = (
            [
                record
                for record in nonidentity_records
                if record["event_id"] not in relevant_reviewed_ids
            ][-fallback_count:]
            if fallback_count
            else []
        )
        retained_reviewed_records = ([identity_records[-1]] if identity_records else []) + fallback_records
        reviewed_items = [
            {
                "event_id": record["event_id"],
                "item": record["item"],
                "source_digest": record["source_digest"],
            }
            for record in retained_reviewed_records
        ]

        # Keep reviewed continuity comfortably below the 4096-token model
        # context. Relevant items are never duplicated in the fallback list.
        # Remove generic fallback first, then secondary relevance. A single
        # unusually large item is projected to its bounded factual core.
        def reviewed_payload_chars() -> int:
            return len(
                json.dumps(
                    {"fallback": reviewed_items, "relevant": relevant_reviewed_items},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

        reviewed_context_limit = 5800
        while reviewed_payload_chars() > reviewed_context_limit and len(reviewed_items) > int(bool(identity_records)):
            reviewed_items.pop()
        while reviewed_payload_chars() > reviewed_context_limit and len(relevant_reviewed_items) > 1:
            relevant_reviewed_items.pop()
        if reviewed_payload_chars() > reviewed_context_limit and relevant_reviewed_items:
            original_item = relevant_reviewed_items[0]["item"]
            if isinstance(original_item, dict):
                bounded_item = {
                    key: original_item[key]
                    for key in ("kind", "memory_id", "memory_kind", "summary", "source_class")
                    if key in original_item
                }
                facts = original_item.get("facts", [])
                forbidden = original_item.get("forbidden_inferences", [])
                if isinstance(facts, list):
                    query_fact_terms = _memory_terms(query_text or "")
                    ranked_facts = sorted(
                        enumerate(facts),
                        key=lambda entry: (
                            len(query_fact_terms & _memory_terms(str(entry[1]))),
                            sum(
                                len(term)
                                for term in query_fact_terms & _memory_terms(str(entry[1]))
                            ),
                            -entry[0],
                        ),
                        reverse=True,
                    )
                    bounded_item["facts"] = [str(item)[:700] for _, item in ranked_facts[:8]]
                if isinstance(forbidden, list):
                    bounded_item["forbidden_inferences"] = [str(item)[:500] for item in forbidden[:3]]
                forbidden_surface = original_item.get("forbidden_surface_phrases", [])
                if isinstance(forbidden_surface, list):
                    bounded_item["forbidden_surface_phrases"] = [
                        str(item)[:160] for item in forbidden_surface[:8]
                    ]
                response_concepts = original_item.get("required_response_concepts", [])
                if isinstance(response_concepts, list):
                    normalized_query = f" {_normalized_memory_surface(query_text or '')} "
                    matching_concepts = []
                    for contract in response_concepts:
                        triggers = contract.get("when_query_contains_any", []) if isinstance(contract, dict) else []
                        if not isinstance(triggers, list):
                            continue
                        if any(
                            isinstance(trigger, str)
                            and f" {_normalized_memory_surface(trigger)} " in normalized_query
                            for trigger in triggers
                        ):
                            matching_concepts.append(contract)
                    if matching_concepts:
                        bounded_item["required_response_concepts"] = matching_concepts[:2]
                relevant_reviewed_items[0] = {
                    **relevant_reviewed_items[0],
                    "item": bounded_item,
                    "projection": "bounded_relevant_factual_core",
                }
                while (
                    reviewed_payload_chars() > reviewed_context_limit
                    and len(bounded_item.get("facts", [])) > 3
                ):
                    bounded_item["facts"].pop()
        public_test_tokens: list[str] = []
        for record in prior_spoken:
            for token in PUBLIC_TEST_TOKEN.findall(str(record["text"])):
                if token not in public_test_tokens:
                    public_test_tokens.append(token)
        result = {
            "branch_id": self.branch_id,
            "prior_spoken": prior_spoken,
            "quality_recent_spoken": quality_recent_spoken,
            "prior_factual_claims": prior_facts,
            "query_relevant_prior_spoken": relevant_prior_spoken,
            "query_relevant_prior_factual_claims": relevant_prior_facts,
            "explicitly_reviewed_imports": reviewed_items,
            "query_relevant_reviewed_imports": relevant_reviewed_items,
            "self_introduced_people": [
                {
                    "event_id": record["event_id"],
                    "introduced_name": record["introduced_name"],
                    "status": record["status"],
                    "biometric_identity_verified": False,
                }
                for record in projected_acquaintance_records[-8:]
            ],
            "query_requests_self_introduced_identity": query_requests_person_identity,
            "public_test_tokens_from_prior_assistant_speech": public_test_tokens[-8:],
            "full_raw_user_utterance_persisted": False,
            "explicit_self_introduced_name_label_may_be_retained": True,
            "explicit_reviewed_note_text_may_be_retained_when_confirmed": True,
            "continuity_payload_chars": 0,
            "continuity_payload_limit_chars": 8000,
        }

        # Enforce a conservative budget over the complete continuity object,
        # not only reviewed records. Keep query-relevant reviewed memory and
        # the identity boundary; discard lower-priority recent history first.
        def continuity_payload_chars() -> int:
            return len(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

        trimming_order = (
            ("prior_spoken", 0),
            ("prior_factual_claims", 0),
            ("query_relevant_prior_spoken", -1),
            ("query_relevant_prior_factual_claims", -1),
            ("self_introduced_people", 0),
            ("quality_recent_spoken", 0),
        )
        for key, pop_index in trimming_order:
            values = result[key]
            minimum = (
                1
                if key == "self_introduced_people" and query_requests_person_identity
                else 2
                if key == "quality_recent_spoken"
                else 0
            )
            while continuity_payload_chars() > 7900 and len(values) > minimum:
                values.pop(pop_index)
        if continuity_payload_chars() > 8000:
            raise ValueError("bounded continuity projection exceeds the local model context budget")
        result["continuity_payload_chars"] = continuity_payload_chars()
        # Recompute once with the real digit count now present in the object.
        result["continuity_payload_chars"] = continuity_payload_chars()
        if result["continuity_payload_chars"] > 8000:
            raise ValueError("bounded continuity projection exceeds the local model context budget")
        return result

    def _record_explicit_self_introduction(self, user_text: str, loop_id: str, turn_id: str) -> None:
        match = SELF_INTRODUCTION.search(user_text)
        if match is None:
            return
        introduced_name = " ".join(match.group("name").split())
        normalized_name = introduced_name.casefold()
        self.acquaintances.append_once(
            {
                "schema_version": 1,
                "event_id": stable_event_id(
                    "self-introduction", self.profile_id, normalized_name, turn_id
                ),
                "timestamp": utc_now(),
                "profile_id": self.profile_id,
                "branch_id": self.branch_id,
                "loop_id": loop_id,
                "turn_id": turn_id,
                "introduced_name": introduced_name,
                "source": "explicit_self_introduction_in_conversation",
                "status": "self_introduced_label_unverified",
                "full_raw_utterance_persisted": False,
                "introduced_name_derived_from_user_input": True,
                "biometric_identity_verified": False,
                "identity_authentication": False,
                "boundary": (
                    "This stores only the explicitly introduced name label. It is not face/voice recognition, "
                    "identity authentication, consent to unrelated data collection, or proof that two speakers "
                    "using the same name are the same person. Corrections must remain auditable."
                ),
            }
        )

    def remember_reviewed_note(
        self,
        text: str,
        *,
        reviewed_by: str,
        confirmed_reviewed: bool,
        supersedes_event_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Append one explicitly reviewed local continuity fact.

        This is an operator-visible memory action, not automatic truth promotion.
        It retains the supplied note text and therefore requires an explicit
        confirmation distinct from ordinary ephemeral conversation.
        """
        if not confirmed_reviewed:
            raise ValueError("explicit reviewed-memory confirmation is required")
        if not isinstance(text, str) or not text.strip() or len(text) > 1200 or "\x00" in text:
            raise ValueError("reviewed note must be 1 to 1200 safe characters")
        if not isinstance(reviewed_by, str) or not reviewed_by.strip() or len(reviewed_by) > 120:
            raise ValueError("reviewer label must be 1 to 120 characters")
        clean_text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
        clean_reviewer = " ".join(reviewed_by.replace("\r", " ").replace("\n", " ").split())
        supersedes = tuple(dict.fromkeys(supersedes_event_ids))
        if len(supersedes) > 32 or any(not TURN_ID.fullmatch(event_id) for event_id in supersedes):
            raise ValueError("superseded event IDs must be valid bounded identifiers")
        with self.mutation_guard():
            existing_fact_ids = {record["event_id"] for record in self.facts.records()}
            missing_superseded = [event_id for event_id in supersedes if event_id not in existing_fact_ids]
            if missing_superseded:
                raise ValueError("every superseded event ID must resolve in this profile's fact ledger")
            event_id = stable_event_id(
                "reviewed-local-note",
                self.profile_id,
                clean_reviewer,
                clean_text,
                "\x1e".join(supersedes),
            )
            loop = self.life_loops.current() or self.life_loops.start()
            record = {
                "schema_version": 1,
                "event_id": event_id,
                "timestamp": utc_now(),
                "profile_id": self.profile_id,
                "branch_id": self.branch_id,
                "turn_id": f"reviewed-note:{event_id[:24]}",
                "loop_id": loop.loop_id,
                "channel": "factual_claim",
                "claim": clean_text,
                "source": "reviewed_continuity",
                "uncertainty": "medium",
                "status": "explicitly_reviewed_local_continuity_note",
                "reviewed_by": clean_reviewer,
                "reviewer_label_status": "operator_supplied_unverified_label",
                "supersedes_event_ids": list(supersedes),
                "input_retention": "explicit_reviewed_note_text_retained",
                "disclosure": REVIEWED_NOTE_DISCLOSURE,
            }
            created = self.facts.append_once(record)
            persisted = self.facts.find(event_id)
            if persisted is None:
                raise StorageCorruption("reviewed note append did not produce a readable ledger record")
            return {**persisted, "created": created}

    def interact(self, user_text: str, *, turn_id: str | None = None) -> RuntimeResponse:
        if not isinstance(user_text, str) or not user_text.strip():
            raise ValueError("user text must be non-empty")
        if len(user_text) > 8000 or "\x00" in user_text:
            raise ValueError("user text exceeds the safe ephemeral input limit")
        selected_turn = turn_id or uuid.uuid4().hex
        if not TURN_ID.fullmatch(selected_turn):
            raise ValueError("invalid turn identifier")
        with self.mutation_guard():
            return self._interact_locked(user_text, selected_turn)

    def _interact_locked(self, user_text: str, selected_turn: str) -> RuntimeResponse:
        transaction_id = stable_event_id("turn", self.profile_id, selected_turn)
        transaction = self.transactions.find(transaction_id)
        if transaction is None:
            loop = self.life_loops.current() or self.life_loops.start()
            self._record_explicit_self_introduction(user_text, loop.loop_id, selected_turn)
            before = self.functional_state()
            after = appraise_ephemeral_input(user_text, before)
            continuity = self.continuity_view(user_text)
            result = self.backend.respond(
                self.profile,
                user_text,
                continuity,
                after.as_record(),
            )
            # A restart check may ask for a short token that already appears in
            # persisted *public assistant speech*. This deterministic retrieval
            # never stores/relabels raw user input or private/model reasoning.
            if "test token" in user_text.lower():
                tokens = continuity["public_test_tokens_from_prior_assistant_speech"]
                if tokens and tokens[-1].lower() not in result.speech.lower():
                    result = replace(
                        result,
                        speech=f"The most recent public test token in restart continuity is {tokens[-1]}.",
                        fallback_reason=(
                            (result.fallback_reason + "; " if result.fallback_reason else "")
                            + "deterministic_public_assistant_token_retrieval"
                        ),
                    )
            transaction = self._transaction_record(selected_turn, loop.loop_id, result, before, after)
            if not self.transactions.append_once(transaction):
                persisted = self.transactions.find(transaction_id)
                if persisted is None:
                    raise StorageCorruption("turn transaction lost an append race without a persisted winner")
                transaction = persisted
        self._materialize(transaction)
        return self._response_from_transaction(transaction)

    def _transaction_record(
        self,
        turn_id: str,
        loop_id: str,
        result: BackendResult,
        before: AppraisalState,
        after: AppraisalState,
    ) -> dict[str, Any]:
        planned_intentions = self.embodiment.plan_intentions(
            self.profile_id,
            turn_id,
            result.speech,
            after,
        )
        return {
            "schema_version": 1,
            "event_id": stable_event_id("turn", self.profile_id, turn_id),
            "timestamp": utc_now(),
            "profile_id": self.profile_id,
            "branch_id": self.branch_id,
            "turn_id": turn_id,
            "loop_id": loop_id,
            "input_retention": INPUT_RETENTION_NOTICE,
            "speech": result.speech,
            "reflection": result.reflection,
            "factual_claims": list(result.factual_claims),
            "functional_state_before": before.as_record(),
            "functional_state_after": after.as_record(),
            "backend": result.backend,
            "model": result.model,
            "model_digest": result.model_digest,
            "model_digest_kind": result.model_digest_kind,
            "fallback_reason": result.fallback_reason,
            "embodiment_intentions": list(planned_intentions),
        }

    @staticmethod
    def _validate_appraisal_record(value: Any) -> None:
        ranges = {
            "valence": (-1.0, 1.0),
            "arousal": (0.0, 1.0),
            "engagement": (0.0, 1.0),
            "confidence": (0.0, 1.0),
        }
        if not isinstance(value, dict) or set(value) != APPRAISAL_KEYS:
            raise StorageCorruption("committed turn appraisal state schema is invalid")
        for key, (minimum, maximum) in ranges.items():
            number = value.get(key)
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(float(number))
                or not minimum <= float(number) <= maximum
            ):
                raise StorageCorruption("committed turn appraisal state value is invalid")

    def _validate_committed_transaction(self, transaction: dict[str, Any]) -> None:
        if not isinstance(transaction, dict) or set(transaction) != TRANSACTION_KEYS:
            raise StorageCorruption("committed turn transaction schema is invalid")
        turn_id = transaction.get("turn_id")
        loop_id = transaction.get("loop_id")
        model_digest = transaction.get("model_digest")
        model_digest_kind = transaction.get("model_digest_kind")
        fallback_reason = transaction.get("fallback_reason")
        if (
            transaction.get("schema_version") != 1
            or transaction.get("profile_id") != self.profile_id
            or transaction.get("branch_id") != self.branch_id
            or not isinstance(turn_id, str)
            or not TURN_ID.fullmatch(turn_id)
            or transaction.get("event_id") != stable_event_id("turn", self.profile_id, turn_id)
            or not isinstance(loop_id, str)
            or not TURN_ID.fullmatch(loop_id)
            or not _is_utc_timestamp(transaction.get("timestamp"))
            or transaction.get("input_retention") != INPUT_RETENTION_NOTICE
            or not _is_bounded_plain_text(transaction.get("speech"), 4000)
            or transaction.get("reflection") != SAFE_REFLECTION
            or not isinstance(transaction.get("factual_claims"), list)
            or len(transaction["factual_claims"]) > 12
            or not _is_bounded_plain_text(transaction.get("backend"), 120)
            or not _is_bounded_plain_text(transaction.get("model"), 240)
            or model_digest_kind not in MODEL_DIGEST_KINDS
            or (
                model_digest_kind == "ollama_reported_manifest_sha256"
                and (not isinstance(model_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", model_digest))
            )
            or (model_digest_kind != "ollama_reported_manifest_sha256" and model_digest is not None)
            or (
                fallback_reason is not None
                and not _is_bounded_plain_text(fallback_reason, 1000)
            )
        ):
            raise StorageCorruption("committed turn transaction is corrupt or cross-profile")
        self._validate_appraisal_record(transaction.get("functional_state_before"))
        self._validate_appraisal_record(transaction.get("functional_state_after"))
        for claim in transaction["factual_claims"]:
            if (
                not isinstance(claim, dict)
                or set(claim) != {"claim", "source", "uncertainty", "status"}
                or not isinstance(claim.get("claim"), str)
                or not isinstance(claim.get("source"), str)
                or not isinstance(claim.get("uncertainty"), str)
                or not claim["claim"].strip()
                or len(claim["claim"]) > 600
                or claim["source"] not in ALLOWED_SOURCES
                or claim["uncertainty"] not in ALLOWED_UNCERTAINTY
                or claim.get("status") != "model_claim_not_verified_truth"
            ):
                raise StorageCorruption("committed turn factual claim is invalid")
        planned_intentions = transaction["embodiment_intentions"]
        if not isinstance(planned_intentions, list) or len(planned_intentions) > len(ALLOWED_CAPABILITIES):
            raise StorageCorruption("committed embodiment intention list is invalid")
        seen_kinds: set[str] = set()
        for intention in planned_intentions:
            if not isinstance(intention, dict):
                raise StorageCorruption("committed embodiment intention is invalid")
            expected_keys = {
                "schema_version",
                "event_id",
                "timestamp",
                "session_id",
                "profile_id",
                "branch_id",
                "endpoint_id",
                "turn_id",
                "kind",
                "payload",
                "execution_status",
                "boundary",
            }
            session_id = intention.get("session_id")
            kind = intention.get("kind")
            if (
                set(intention) != expected_keys
                or intention.get("schema_version") != 1
                or intention.get("profile_id") != self.profile_id
                or intention.get("branch_id") != self.branch_id
                or intention.get("turn_id") != turn_id
                or not _is_utc_timestamp(intention.get("timestamp"))
                or not isinstance(session_id, str)
                or not TURN_ID.fullmatch(session_id)
                or kind not in ALLOWED_CAPABILITIES
                or kind in seen_kinds
                or not isinstance(intention.get("endpoint_id"), str)
                or not SAFE_ENDPOINT.fullmatch(intention["endpoint_id"])
                or intention.get("event_id")
                != stable_event_id("intention", session_id, turn_id, str(kind))
                or intention.get("execution_status") != "not_executed_high_level_intention_only"
                or intention.get("boundary") != EMBODIMENT_BOUNDARY
                or not isinstance(intention.get("payload"), dict)
            ):
                raise StorageCorruption("committed embodiment intention is invalid")
            try:
                EmbodimentManager._validate_intention(str(kind), intention["payload"])
            except Exception as exc:
                raise StorageCorruption("committed embodiment intention payload is invalid") from exc
            if any(
                not isinstance(value, str)
                or not value.strip()
                or len(value) > (1000 if kind == "speech" else 128)
                for value in intention["payload"].values()
            ):
                raise StorageCorruption("committed embodiment intention payload text is invalid")
            seen_kinds.add(str(kind))

    def _expected_materialized_channels(
        self, transaction: dict[str, Any]
    ) -> tuple[tuple[AppendOnlyJSONL, list[dict[str, Any]]], ...]:
        turn_id = str(transaction["turn_id"])
        common = {
            "schema_version": 1,
            "timestamp": transaction["timestamp"],
            "profile_id": self.profile_id,
            "branch_id": self.branch_id,
            "turn_id": turn_id,
            "loop_id": transaction["loop_id"],
            "backend": transaction["backend"],
            "model": transaction["model"],
            "model_digest": transaction["model_digest"],
            "model_digest_kind": transaction["model_digest_kind"],
        }
        spoken = [
            {
                **common,
                "event_id": stable_event_id("spoken", self.profile_id, turn_id),
                "channel": "spoken",
                "text": transaction["speech"],
            }
        ]
        reflections = [
            {
                **common,
                "event_id": stable_event_id("reflection", self.profile_id, turn_id),
                "channel": "non_spoken_reflection",
                "reflection": transaction["reflection"],
                "disclosure": REFLECTION_DISCLOSURE,
            }
        ]
        facts: list[dict[str, Any]] = []
        for index, claim in enumerate(transaction["factual_claims"]):
            facts.append(
                {
                    **common,
                    "event_id": stable_event_id("fact", self.profile_id, turn_id, str(index)),
                    "channel": "factual_claim",
                    "claim_index": index,
                    **claim,
                    "disclosure": FACT_DISCLOSURE,
                }
            )
        states = [
            {
                **common,
                "event_id": stable_event_id("state", self.profile_id, turn_id),
                "channel": "functional_appraisal_state",
                "before": transaction["functional_state_before"],
                "after": transaction["functional_state_after"],
                "boundary": BOUNDARY_NOTICE,
            }
        ]
        intentions = [dict(intention) for intention in transaction["embodiment_intentions"]]
        return (
            (self.spoken, spoken),
            (self.reflections, reflections),
            (self.facts, facts),
            (self.state_events, states),
            (self.embodiment.intentions, intentions),
        )

    def _validate_materialization_marker(
        self, marker: dict[str, Any], transaction: dict[str, Any]
    ) -> None:
        transaction_event_id = str(transaction["event_id"])
        turn_id = str(transaction["turn_id"])
        if (
            not isinstance(marker, dict)
            or set(marker) != MATERIALIZATION_KEYS
            or marker.get("schema_version") != 1
            or marker.get("event_id")
            != stable_event_id("turn-materialized", self.profile_id, transaction_event_id)
            or not _is_utc_timestamp(marker.get("timestamp"))
            or marker.get("profile_id") != self.profile_id
            or marker.get("branch_id") != self.branch_id
            or marker.get("turn_id") != turn_id
            or marker.get("transaction_event_id") != transaction_event_id
            or not isinstance(marker.get("recovered_after_restart"), bool)
            or marker.get("embodiment_plan_present_in_transaction") is not True
        ):
            raise StorageCorruption("turn materialization marker is corrupt or cross-profile")

    def _verify_materialized_channels(self, transaction: dict[str, Any]) -> None:
        turn_id = str(transaction["turn_id"])
        for channel, expected_records in self._expected_materialized_channels(transaction):
            expected = {record["event_id"]: record for record in expected_records}
            actual_records = [
                record
                for record in channel.records()
                if record.get("profile_id") == self.profile_id and record.get("turn_id") == turn_id
            ]
            actual = {record["event_id"]: record for record in actual_records}
            if set(actual) != set(expected) or any(
                canonical_json(actual[event_id]) != canonical_json(record)
                for event_id, record in expected.items()
            ):
                raise StorageCorruption(
                    f"materialized channel does not exactly match committed turn: {channel.path.name}"
                )

    def _verify_no_unexpected_materialized_records(self, transaction: dict[str, Any]) -> None:
        """Allow a crash-partial exact prefix, but reject conflicts/extras before replay writes."""

        turn_id = str(transaction["turn_id"])
        for channel, expected_records in self._expected_materialized_channels(transaction):
            expected = {record["event_id"]: record for record in expected_records}
            actual_records = [
                record
                for record in channel.records()
                if record.get("profile_id") == self.profile_id and record.get("turn_id") == turn_id
            ]
            for record in actual_records:
                event_id = record["event_id"]
                if event_id not in expected or canonical_json(record) != canonical_json(expected[event_id]):
                    raise StorageCorruption(
                        f"unexpected or conflicting partial materialization: {channel.path.name}"
                    )

    def _recover_committed_transactions(self) -> None:
        transactions = self.transactions.records()
        transaction_by_id: dict[str, dict[str, Any]] = {}
        for transaction in transactions:
            self._validate_committed_transaction(transaction)
            transaction_by_id[str(transaction["event_id"])] = transaction
        markers: dict[str, dict[str, Any]] = {}
        for marker in self.materializations.records():
            transaction = transaction_by_id.get(str(marker.get("transaction_event_id", "")))
            if transaction is None:
                raise StorageCorruption("turn materialization marker references no committed transaction")
            self._validate_materialization_marker(marker, transaction)
            markers[str(transaction["event_id"])] = marker
        for transaction in transactions:
            transaction_event_id = str(transaction["event_id"])
            if transaction_event_id in markers:
                self._verify_materialized_channels(transaction)
            else:
                self._materialize(transaction, recovery=True)

    def _materialize(self, transaction: dict[str, Any], *, recovery: bool = False) -> None:
        self._validate_committed_transaction(transaction)
        transaction_event_id = str(transaction["event_id"])
        marker_event_id = stable_event_id("turn-materialized", self.profile_id, transaction_event_id)
        existing_marker = self.materializations.find(marker_event_id)
        if existing_marker is not None:
            self._validate_materialization_marker(existing_marker, transaction)
            self._verify_materialized_channels(transaction)
            return
        self._verify_no_unexpected_materialized_records(transaction)
        for channel, records in self._expected_materialized_channels(transaction):
            for record in records:
                channel.append_exact_or_verify(record)
        self._verify_materialized_channels(transaction)
        marker = {
            "schema_version": 1,
            "event_id": marker_event_id,
            "timestamp": utc_now(),
            "profile_id": self.profile_id,
            "branch_id": self.branch_id,
            "turn_id": str(transaction["turn_id"]),
            "transaction_event_id": transaction_event_id,
            "recovered_after_restart": recovery,
            "embodiment_plan_present_in_transaction": True,
        }
        self.materializations.append_exact_or_verify(marker)

    def _response_from_transaction(self, transaction: dict[str, Any]) -> RuntimeResponse:
        intentions = tuple(
            record
            for record in self.embodiment.intentions.records()
            if record.get("profile_id") == self.profile_id
            and record.get("turn_id") == transaction["turn_id"]
        )
        return RuntimeResponse(
            turn_id=str(transaction["turn_id"]),
            loop_id=str(transaction["loop_id"]),
            speech=str(transaction["speech"]),
            reflection=str(transaction["reflection"]),
            factual_claims=tuple(transaction["factual_claims"]),
            functional_state=AppraisalState.from_mapping(transaction["functional_state_after"]),
            backend=str(transaction["backend"]),
            model=str(transaction["model"]),
            model_digest=transaction.get("model_digest"),
            model_digest_kind=str(transaction.get("model_digest_kind", "unavailable")),
            fallback_reason=transaction.get("fallback_reason"),
            embodiment_intentions=intentions,
            branch_id=str(transaction.get("branch_id", self.branch_id)),
        )

    def channel(self, channel: str) -> AppendOnlyJSONL:
        mapping = {
            "spoken": self.spoken,
            "reflection": self.reflections,
            "facts": self.facts,
            "state": self.state_events,
            "loops": self.life_loops.events,
            "consolidations": self.life_loops.consolidations,
            "imports": self.reviewed_imports,
            "voice": self.voice_events,
            "people": self.acquaintances,
        }
        try:
            return mapping[channel]
        except KeyError as exc:
            raise ValueError(f"unknown channel: {channel}") from exc
