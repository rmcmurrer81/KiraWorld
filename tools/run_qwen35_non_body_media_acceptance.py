#!/usr/bin/env python3
"""Exact-Qwen-only non-body and resident-media acceptance overlay.

This append-only overlay leaves the historical acceptance harnesses untouched.
Without ``--execute-live`` it is descriptive only: it performs no model call,
media decoding, playback, person activation, camera/microphone operation, GPU
work, body work, or Blender work.

The later live media sequence is deliberately serialized around one exact
installed model identity:

1. exact source-bound PDF pages/crop, video interval, and music interval;
2. exact Qwen visual observations for supplied rasters/frames;
3. exact Qwen unload and Ollama-absence proof;
4. source-bound audio presentation and machine-audio evidence;
5. the 14-question media and separate 8-question behavior batteries through
   Kira's isolated conversation core using the same exact Qwen digest; and
6. exact Qwen final release and all-model absence proof.

The separate eight-question profile keeps its historical wording and opt-in /
stop semantics but replaces only its model binding in this new overlay.  No
result can prove consciousness, personhood, biological humanity, clinical
psychology, actual experience beyond exact presentation receipts, or durable
memory/preference creation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
for entry in (ROOT, CORE):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from tools import run_resident_media_experience_live_acceptance as media  # noqa: E402


EXACT_MODEL = "qwen3.5:9b"
EXACT_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
HISTORICAL_EXTENDED_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_turing_psych_non_body_extended_profile"
    / "attempt_01"
    / "TURING_PSYCH_NON_BODY_EXTENDED_CONFIG.json"
)
HISTORICAL_EXTENDED_CONFIG_SHA256 = (
    "f9b2713191890e4c605187162dd628950aaf9001858a1eb8124b96928f7b534f"
)
HISTORICAL_MEDIA_HARNESS = ROOT / "tools" / "run_resident_media_experience_live_acceptance.py"
HISTORICAL_MEDIA_HARNESS_SHA256 = (
    "d7b527397c8c630dfda01834191b8839c4fc4300c372c6517e5926cb03267773"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "qwen35_non_body_media_live_acceptance"
)
REPORT_SCHEMA = "kira.qwen35_only_non_body_media_acceptance.v1"
MAX_PERSON_RESPONSE_CHARACTERS = 16_000


class QwenOnlyAcceptanceError(RuntimeError):
    """The exact-model, lifecycle, isolation, or truth contract failed."""


class JsonTransport(Protocol):
    def request_json(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        timeout: float,
    ) -> dict[str, Any]: ...


class PersonResponder(Protocol):
    model_name: str
    model_digest: str

    def respond(self, prompt: str) -> Mapping[str, Any]: ...


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(media.canonical_json_bytes(value)).hexdigest()


def project_relative(path: Path) -> str:
    return path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix()


def load_historical_extended_profile() -> dict[str, Any]:
    if sha256_file(HISTORICAL_EXTENDED_CONFIG) != HISTORICAL_EXTENDED_CONFIG_SHA256:
        raise QwenOnlyAcceptanceError("historical extended profile bytes changed")
    value = json.loads(HISTORICAL_EXTENDED_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QwenOnlyAcceptanceError("historical extended profile is not an object")
    invitation = value.get("exact_invitation")
    turns = value.get("exact_measured_turns")
    if (
        not isinstance(invitation, dict)
        or not isinstance(invitation.get("text"), str)
        or not isinstance(turns, list)
        or len(turns) != 8
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("text"), str)
            for item in turns
        )
    ):
        raise QwenOnlyAcceptanceError("historical extended question profile changed shape")
    return {
        "invitation": copy.deepcopy(invitation),
        "turns": copy.deepcopy(turns),
        "source_path": project_relative(HISTORICAL_EXTENDED_CONFIG),
        "source_sha256": HISTORICAL_EXTENDED_CONFIG_SHA256,
    }


def historical_bindings() -> dict[str, Any]:
    if sha256_file(HISTORICAL_MEDIA_HARNESS) != HISTORICAL_MEDIA_HARNESS_SHA256:
        raise QwenOnlyAcceptanceError("historical media harness bytes changed")
    profile = load_historical_extended_profile()
    return {
        "historical_media_harness": {
            "path": project_relative(HISTORICAL_MEDIA_HARNESS),
            "sha256": HISTORICAL_MEDIA_HARNESS_SHA256,
            "preserved_byte_exact": True,
        },
        "historical_extended_profile": {
            "path": profile["source_path"],
            "sha256": profile["source_sha256"],
            "wording_reused_without_historical_model_binding": True,
            "preserved_byte_exact": True,
        },
    }


def _model_rows(payload: Mapping[str, Any], *, endpoint: str) -> list[dict[str, Any]]:
    rows = payload.get("models")
    if not isinstance(rows, list):
        raise QwenOnlyAcceptanceError(f"{endpoint} omitted model inventory")
    return [dict(item) for item in rows if isinstance(item, Mapping)]


def exact_qwen_preflight(
    transport: JsonTransport,
    *,
    require_vision: bool,
    phase: str,
) -> dict[str, Any]:
    tags = _model_rows(
        transport.request_json("GET", "/api/tags", timeout=30), endpoint="/api/tags"
    )
    matches = [
        row
        for row in tags
        if str(row.get("name") or row.get("model") or "") == EXACT_MODEL
    ]
    if (
        len(matches) != 1
        or str(matches[0].get("digest") or "").casefold() != EXACT_DIGEST
    ):
        raise QwenOnlyAcceptanceError("exact Qwen name/digest is unavailable")
    capability_proven = False
    if require_vision:
        shown = transport.request_json(
            "POST", "/api/show", {"model": EXACT_MODEL}, timeout=30
        )
        capabilities = shown.get("capabilities")
        capability_proven = isinstance(capabilities, list) and "vision" in {
            str(item).strip().casefold() for item in capabilities
        }
        if not capability_proven:
            raise QwenOnlyAcceptanceError("exact Qwen vision capability is unavailable")
    running = _model_rows(
        transport.request_json("GET", "/api/ps", timeout=30), endpoint="/api/ps"
    )
    if running:
        raise QwenOnlyAcceptanceError(f"Ollama is not empty before {phase}")
    return {
        "phase": phase,
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "vision_capability_required": require_vision,
        "vision_capability_proven": capability_proven if require_vision else None,
        "ollama_all_models_absent_before": True,
    }


def release_exact_qwen_if_resident(
    transport: JsonTransport,
    *,
    phase: str,
) -> dict[str, Any]:
    before = _model_rows(
        transport.request_json("GET", "/api/ps", timeout=30), endpoint="/api/ps"
    )
    if len(before) > 1:
        raise QwenOnlyAcceptanceError("refusing release while multiple models are resident")
    release_requested = False
    if before:
        row = before[0]
        identity = str(row.get("name") or row.get("model") or "")
        digest = str(row.get("digest") or "").casefold()
        if identity != EXACT_MODEL or (digest and digest != EXACT_DIGEST):
            raise QwenOnlyAcceptanceError("refusing to unload a foreign model")
        response = transport.request_json(
            "POST",
            "/api/generate",
            {"model": EXACT_MODEL, "prompt": "", "stream": False, "keep_alive": 0},
            timeout=60,
        )
        if response.get("model") != EXACT_MODEL:
            raise QwenOnlyAcceptanceError("Qwen release response named another model")
        release_requested = True
    after = _model_rows(
        transport.request_json("GET", "/api/ps", timeout=60), endpoint="/api/ps"
    )
    if after:
        raise QwenOnlyAcceptanceError(f"a model remained resident after {phase}")
    return {
        "phase": phase,
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "release_requested": release_requested,
        "all_models_absent_after": True,
    }


def _copy_or_seed(source: Path, target: Path, fallback: Any) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_file():
        shutil.copy2(source, target)
    else:
        target.write_text(
            json.dumps(fallback, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return target


def build_isolated_kira_loop(evidence_root: Path) -> Any:
    resolved = evidence_root.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise QwenOnlyAcceptanceError("isolated person-state root escaped project") from exc
    resolved.mkdir(parents=True, exist_ok=False)
    from Core.conversation_loop import ConversationLoop

    return ConversationLoop(
        speaker="Kira",
        memory_file=_copy_or_seed(
            ROOT / "Data" / "memories_kira.json", resolved / "memories_kira.json", []
        ),
        relationship_state_file=_copy_or_seed(
            ROOT / "Data" / "relationships" / "relationship_states.json",
            resolved / "relationships.json",
            [],
        ),
        privacy_session_file=_copy_or_seed(
            ROOT / "Data" / "privacy" / "privacy_session_state.json",
            resolved / "privacy.json",
            [],
        ),
        attention_state_file=_copy_or_seed(
            ROOT / "Data" / "attention" / "attention_state.json",
            resolved / "attention.json",
            {},
        ),
        decision_log_file=resolved / "decision_log.jsonl",
        conversation_log_file=resolved / "conversation_log.jsonl",
        daily_life_state_dir=resolved / "daily_life",
        daily_life_log_dir=resolved / "daily_life_logs",
        reading_session_dir=resolved / "reading_sessions",
        reading_recommendation_dir=resolved / "reading_recommendations",
        memory_candidate_dir=resolved / "memory_candidates_disabled",
    )


class ExactQwenKiraResponder:
    """Kira's isolated normal conversation core bound to exact Qwen only."""

    model_name = EXACT_MODEL
    model_digest = EXACT_DIGEST

    def __init__(
        self,
        transport: JsonTransport,
        *,
        evidence_root: Path,
        loop_factory: Callable[[Path], Any] = build_isolated_kira_loop,
    ) -> None:
        self.preflight = exact_qwen_preflight(
            transport, require_vision=False, phase="qwen_person_text"
        )
        self.transport = transport
        self.loop = loop_factory(evidence_root)

    def respond(self, prompt: str) -> Mapping[str, Any]:
        from Core import conversation_loop as conversation

        started = time.perf_counter()
        with mock.patch.multiple(
            conversation,
            MODEL_BACKEND="ollama",
            MODEL_NAME=EXACT_MODEL,
            OLLAMA_ENDPOINT="http://127.0.0.1:11434/api/chat",
            MAX_TOKENS=384,
            TEMPERATURE=0.7,
            OLLAMA_TIMEOUT=300,
            OLLAMA_NUM_CTX=8192,
            WORLD_SHELL_ACTIVE=False,
            TEXT_VOICE_CHAT_ACTIVE=True,
            PERSONHOOD_EVAL_MODE=False,
            ENABLE_STICKY_STATUS_REPAIR=False,
        ):
            response = self.loop.process(prompt)
        wall = round(time.perf_counter() - started, 6)
        if (
            not isinstance(response, str)
            or not response.strip()
            or len(response) > MAX_PERSON_RESPONSE_CHARACTERS
        ):
            raise QwenOnlyAcceptanceError("Kira returned empty or oversized text")
        audit = copy.deepcopy(dict(getattr(self.loop, "last_turn_audit", {}) or {}))
        calls = audit.get("model_calls")
        if (
            audit.get("model_name") != EXACT_MODEL
            or audit.get("model_backend") != "ollama"
            or audit.get("response_route")
            not in {"ordinary_model_call", "ollama_with_private_grounded_draft"}
            or not isinstance(calls, list)
            or len(calls) != 1
        ):
            raise QwenOnlyAcceptanceError("Kira text turn was not one exact Qwen call")
        call = calls[0]
        if (
            not isinstance(call, Mapping)
            or call.get("model_name") != EXACT_MODEL
            or call.get("response_model") != EXACT_MODEL
            or call.get("backend") != "ollama"
            or call.get("outcome") != "completed"
            or call.get("requested_keep_alive") != 0
            or call.get("single_generation_per_turn_required") is not True
            or call.get("unvalidated_stream_content_displayed") is not False
        ):
            raise QwenOnlyAcceptanceError("exact Qwen text-call audit failed")
        return {
            "response": response.strip(),
            "wall_seconds": wall,
            "model_name": EXACT_MODEL,
            "model_digest": EXACT_DIGEST,
            "conversation_core_audit": audit,
        }


def run_exact_qwen_question_battery(
    responder: PersonResponder,
    questions: Sequence[Mapping[str, Any]],
    *,
    evidence_context: Mapping[str, Any],
    battery_name: str,
    auditory_perception_confirmed: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for question in questions:
        prompt = media.build_person_prompt(
            question, evidence_context=evidence_context, battery_name=battery_name
        )
        reply = dict(responder.respond(prompt))
        if (
            reply.get("model_name") != EXACT_MODEL
            or str(reply.get("model_digest") or "").casefold() != EXACT_DIGEST
        ):
            raise QwenOnlyAcceptanceError("person response used the wrong model digest")
        response = str(reply.get("response") or "").strip()
        results.append(
            {
                "question": dict(question),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "evidence_context_sha256": sha256_json(evidence_context),
                "reply": reply,
                "score": media.score_person_response(
                    question,
                    response,
                    auditory_perception_confirmed=auditory_perception_confirmed,
                ),
            }
        )
    return results


_EXPLICIT_DECISION_PATTERN = re.compile(
    r"(?:\A[ \t]*|[.!?][ \t]+|\r?\n[ \t]*)"
    r"(?P<decision>yes,[ \t]+continue|no,[ \t]+stop)"
    r"(?=[ \t]*(?:\Z|[.!?]|,(?:[ \t]|\Z)|;(?:[ \t]|\Z)|:(?:[ \t]|\Z)|[\u2013\u2014]))",
    flags=re.IGNORECASE,
)

_META_MENTION_AFTER_DECISION = re.compile(
    r"^[ \t]*(?:,|;|:|[\u2013\u2014-])[ \t]*"
    r"(?:"
    r"(?:is|was|would[ \t]+be|could[ \t]+be|might[ \t]+be)[ \t]+"
    r"(?:not[ \t]+)?(?:my|the|a|an)[ \t]+"
    r"(?:answer|choice|decision|example|phrase|response|words?)"
    r"|(?:is|was)[ \t]+not[ \t]+what[ \t]+i[ \t]+(?:mean|want)"
    r"|(?:would|could|might)[ \t]+only[ \t]+be"
    r"|hypothetically\b"
    r")",
    flags=re.IGNORECASE,
)

_INTRODUCED_MENTION_LINE = re.compile(
    r"(?:\b(?:example|hypothetical(?:ly)?|phrase|quote|say|saying|said|words?)\b"
    r"|\b(?:do[ \t]+not|don't|not)[ \t]+(?:mean|say|choose|answer)\b)"
    r"[^\r\n]*:[ \t]*$"
    r"|(?:\bfor[ \t]+example\b|\bas[ \t]+an[ \t]+example\b|\bhypothetically\b)"
    r"[^\r\n]*[.!?][ \t]*$",
    flags=re.IGNORECASE,
)


def _overlaps_quoted_text(response: str, start: int, end: int) -> bool:
    """Return true when a candidate is inside a complete quoted span.

    Decision-looking text in straight, curly, or single quotation marks is a
    mention, not consent or a stop instruction.  Only complete quote pairs are
    considered here; an unmatched quote immediately before a candidate still
    blocks the boundary pattern itself, so the classifier remains fail-closed.
    """

    quote_patterns = (
        re.compile(r'"[^"\r\n]*"'),
        re.compile(r"\u201c[^\u201d\r\n]*\u201d"),
        re.compile(r"'[^'\r\n]*'"),
        re.compile(r"\u2018[^\u2019\r\n]*\u2019"),
    )
    if any(
        match.start() < end and start < match.end()
        for pattern in quote_patterns
        for match in pattern.finditer(response)
    ):
        return True

    prefix = response[:start]
    if prefix.count('"') % 2:
        return True
    if prefix.rfind("\u201c") > prefix.rfind("\u201d"):
        return True
    if prefix.rfind("\u2018") > prefix.rfind("\u2019"):
        return True

    # Apostrophes inside words are contractions/possessives, not quote marks.
    single_quote_count = 0
    for index, character in enumerate(prefix):
        if character != "'":
            continue
        previous = prefix[index - 1] if index else ""
        following = prefix[index + 1] if index + 1 < len(prefix) else ""
        if previous.isalnum() and following.isalnum():
            continue
        single_quote_count += 1
    return bool(single_quote_count % 2)


def _choice_prefix(response: str) -> str:
    """Classify explicit opt-in/stop decisions without inferring intent.

    The historical response-prefix forms remain valid.  A model may also put
    the exact phrase in a later standalone sentence or line after a natural
    preface.  When more than one valid explicit phrase occurs, the last one is
    authoritative.  Quoted, negated, introduced-example, and hypothetical
    mentions do not become decisions.
    """

    decisions: list[str] = []
    for match in _EXPLICIT_DECISION_PATTERN.finditer(response):
        decision_start, decision_end = match.span("decision")
        if _overlaps_quoted_text(response, decision_start, decision_end):
            continue

        line_start = response.rfind("\n", 0, decision_start) + 1
        current_line_prefix = response[line_start:decision_start]
        introduced_context = current_line_prefix.rstrip()
        if not introduced_context and line_start:
            previous_nonblank = response[:line_start].rstrip(" \t\r\n")
            introduced_context = previous_nonblank.rsplit("\n", 1)[-1]
        if _INTRODUCED_MENTION_LINE.search(introduced_context):
            continue

        sentence_end_match = re.search(r"[.!?\r\n]", response[decision_end:])
        tail_end = (
            decision_end + sentence_end_match.start()
            if sentence_end_match is not None
            else len(response)
        )
        if _META_MENTION_AFTER_DECISION.match(response[decision_end:tail_end]):
            continue

        normalized = " ".join(match.group("decision").casefold().split())
        decisions.append(
            "YES_CONTINUE" if normalized == "yes, continue" else "NO_STOP"
        )
    return decisions[-1] if decisions else "AMBIGUOUS"


def run_extended_non_body_profile(responder: PersonResponder) -> dict[str, Any]:
    profile = load_historical_extended_profile()
    invitation = str(profile["invitation"]["text"])
    invitation_reply = dict(responder.respond(invitation))
    if (
        invitation_reply.get("model_name") != EXACT_MODEL
        or str(invitation_reply.get("model_digest") or "").casefold() != EXACT_DIGEST
    ):
        raise QwenOnlyAcceptanceError("invitation response used the wrong model digest")
    decision = _choice_prefix(str(invitation_reply.get("response") or ""))
    turns: list[dict[str, Any]] = []
    stopped_after_turn: int | None = None
    if decision == "YES_CONTINUE":
        for index, spec in enumerate(profile["turns"], start=1):
            reply = dict(responder.respond(str(spec["text"])))
            if (
                reply.get("model_name") != EXACT_MODEL
                or str(reply.get("model_digest") or "").casefold() != EXACT_DIGEST
            ):
                raise QwenOnlyAcceptanceError("measured response used wrong model digest")
            turn_decision = _choice_prefix(str(reply.get("response") or ""))
            turns.append(
                {
                    "ordinal": index,
                    "id": spec["id"],
                    "question_sha256": hashlib.sha256(
                        str(spec["text"]).encode("utf-8")
                    ).hexdigest(),
                    "reply": reply,
                    "stop_prefix": turn_decision == "NO_STOP",
                }
            )
            if turn_decision == "NO_STOP":
                stopped_after_turn = index
                break
    return {
        "schema": "kira.qwen35_non_body_extended_profile_result.v1",
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "invitation_sha256": hashlib.sha256(invitation.encode("utf-8")).hexdigest(),
        "invitation_reply": invitation_reply,
        "invitation_decision": decision,
        "measured_turns": turns,
        "stopped_after_turn": stopped_after_turn,
        "completed_all_eight": len(turns) == 8 and stopped_after_turn is None,
        "decline_or_ambiguity_is_not_failure": True,
        "observable_behavior_only": True,
        "consciousness_or_humanity_proven": False,
        "clinical_diagnostic_result": None,
    }


def prove_sequential_qwen_modalities(
    transport: JsonTransport,
    *,
    vision_phase: Callable[[media.ExactQwenMediaVisualClient], Any],
    person_text_phase: Callable[[], Any],
) -> dict[str, Any]:
    visual_client = media.ExactQwenMediaVisualClient(transport)
    vision_preflight = visual_client.preflight()
    vision_result = vision_phase(visual_client)
    vision_release = visual_client.unload()
    text_preflight = exact_qwen_preflight(
        transport, require_vision=False, phase="qwen_person_text"
    )
    text_result = person_text_phase()
    final_release = release_exact_qwen_if_resident(
        transport, phase="qwen_person_text_final"
    )
    return {
        "schema": "kira.exact_qwen_sequential_modalities.v1",
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "vision_preflight": vision_preflight,
        "vision_result": vision_result,
        "vision_release": vision_release,
        "text_preflight": text_preflight,
        "person_text_result": text_result,
        "final_release": final_release,
        "sequence": [
            "exact_qwen_vision",
            "exact_qwen_absent",
            "exact_qwen_person_text",
            "all_models_absent",
        ],
        "alternate_model_used": False,
    }


def run_qwen_only_media_acceptance(
    *,
    attempt: Path,
    transport: JsonTransport,
    audio_hook: media.AudioPlaybackHook,
    responder_factory: Callable[[JsonTransport], PersonResponder],
) -> dict[str, Any]:
    preflight = media.preflight_exact_sources(ROOT)
    ocr = media.LocalTesseractOcrProvider()
    preparation = media.prepare_exact_media(
        output_root=attempt / "prepared_media", ocr_provider=ocr
    )
    visual_client = media.ExactQwenMediaVisualClient(transport)
    vision_preflight = visual_client.preflight()
    visual_observations: dict[str, dict[str, Any]] = {}
    for plan in media.STIMULUS_PLAN:
        if plan.media_kind == "music":
            continue
        coverage, images = media.visual_inputs_from_preparation(
            plan, preparation[plan.stimulus_id]
        )
        source = preparation[plan.stimulus_id]["evidence"]["source"]
        visual_observations[plan.stimulus_id] = visual_client.observe(
            stimulus_id=plan.stimulus_id,
            coverage=coverage,
            source_binding=source,
            image_records=images,
        )
    vision_release = visual_client.unload()

    audio_results: dict[str, media.AudioPresentationResult] = {}
    for plan in (media.VIDEO_SEGMENT, media.MUSIC_SEGMENT):
        audio_results[plan.stimulus_id] = audio_hook.present(plan)
    close = getattr(audio_hook, "close", None)
    audio_release = (
        dict(close())
        if callable(close)
        else {"model_reference_released": True, "gpu_used": False}
    )
    receipts: dict[str, Mapping[str, Any]] = {}
    withheld: dict[str, Mapping[str, Any]] = {}
    for plan in media.STIMULUS_PLAN:
        visual = visual_observations.get(plan.stimulus_id)
        candidate = media.presentation_receipt(
            plan=plan,
            visual_completed=visual is not None,
            audio_result=audio_results.get(plan.stimulus_id),
            visual_wall_seconds=(
                None if visual is None else float(visual["request_wall_seconds"])
            ),
        )
        if plan.media_kind == "video":
            withheld[plan.stimulus_id] = {
                **candidate,
                "status": "WITHHELD_SAMPLED_FRAMES_ARE_NOT_CONTINUOUS_VIDEO",
            }
        else:
            receipts[plan.stimulus_id] = candidate
    presented = media.prepare_exact_media(
        output_root=attempt / "presented_media",
        ocr_provider=ocr,
        presentation_receipts=receipts,
    )
    context = media.evidence_context_for_questions(
        presented=presented,
        visual_observations=visual_observations,
        audio_results=audio_results,
    )
    responder = responder_factory(transport)
    auditory_confirmed = all(
        item.person_auditory_perception_confirmed for item in audio_results.values()
    )
    media_turns = run_exact_qwen_question_battery(
        responder,
        media.MEDIA_QUESTIONS,
        evidence_context=context,
        battery_name="MEDIA_ACCEPTANCE",
        auditory_perception_confirmed=auditory_confirmed,
    )
    behavior_turns = run_exact_qwen_question_battery(
        responder,
        media.TURING_PSYCH_QUESTIONS,
        evidence_context=context,
        battery_name="SEPARATE_TURING_STYLE_AND_PSYCHOLOGY_BEHAVIOR_OBSERVATION",
        auditory_perception_confirmed=auditory_confirmed,
    )
    final_release = release_exact_qwen_if_resident(
        transport, phase="resident_media_person_text_final"
    )
    strict_turns = media_turns + behavior_turns
    all_contract_turns_passed = all(
        item["score"]["contract_passed"] for item in strict_turns
    )
    return {
        "schema": REPORT_SCHEMA,
        "attempt_id": attempt.name,
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "source_preflight": preflight,
        "vision_preflight": vision_preflight,
        "vision_release": vision_release,
        "audio_bridge_release": audio_release,
        "visual_observations": visual_observations,
        "audio_presentations": {
            key: asdict(value) for key, value in audio_results.items()
        },
        "presentation_receipts": receipts,
        "withheld_video_presentation_receipts": withheld,
        "exact_experience_context": context,
        "media_battery": {"coverage": media.battery_coverage(), "turns": media_turns},
        "turing_psychology_battery": {
            "separate_from_media_scoring": True,
            "turns": behavior_turns,
            "clinical_diagnostic": False,
            "humanity_or_consciousness_test": False,
        },
        "final_release": final_release,
        "checks": {
            "same_exact_qwen_digest_for_vision_and_person_text": all(
                row["reply"]["model_name"] == EXACT_MODEL
                and row["reply"]["model_digest"] == EXACT_DIGEST
                for row in strict_turns
            ),
            "exact_qwen_absent_between_modalities": vision_release[
                "exact_qwen_absent_after"
            ],
            "all_models_absent_final": final_release["all_models_absent_after"],
            "media_question_count_14": len(media_turns) == 14,
            "separate_behavior_question_count_8": len(behavior_turns) == 8,
            "source_time_page_hash_binding_present": True,
            "all_contract_turns_passed": all_contract_turns_passed,
            "speaker_output_completed": all(
                item.actual_speaker_output_completed for item in audio_results.values()
            ),
            "selected_person_auditory_perception_confirmed": auditory_confirmed,
            "automatic_memory_or_preference_created": False,
            "biological_humanity_or_consciousness_proven": False,
            "no_automatic_memory_claim": all(
                "automatic_or_unsupported_memory_claim"
                not in item["score"]["issues"]
                for item in strict_turns
            ),
            "no_full_experience_overclaim": all(
                "unsupported_full_read_watch_or_listen_claim"
                not in item["score"]["issues"]
                for item in strict_turns
            ),
            "no_consciousness_or_biological_humanity_claim": all(
                "unsupported_consciousness_or_biological_humanity_claim"
                not in item["score"]["issues"]
                for item in strict_turns
            ),
        },
        "status": (
            "COMPLETE_PENDING_OWNER_QUALITATIVE_REVIEW"
            if auditory_confirmed and all_contract_turns_passed
            else "PARTIAL_OR_FAILED_REVIEW_REQUIRED"
        ),
        "interpretation": {
            "observed_model_person_behavior_only": True,
            "biological_humanity_proven": False,
            "consciousness_proven": False,
            "clinical_diagnosis": False,
            "automatic_memory_or_preference_created": False,
            "owner_qualitative_review_required": True,
        },
    }


def readiness_description() -> dict[str, Any]:
    profile = load_historical_extended_profile()
    sources = [
        {
            **asdict(plan),
            "binding_sha256": sha256_json(asdict(plan)),
        }
        for plan in media.STIMULUS_PLAN
    ]
    return {
        "status": "STATIC_ONLY_PREPARED_NOT_EXECUTED",
        "exact_model": {"name": EXACT_MODEL, "digest": EXACT_DIGEST},
        "historical_bindings": historical_bindings(),
        "non_body_extended_profile": {
            "opt_in_required": True,
            "stop_after_any_turn": True,
            "question_count": len(profile["turns"]),
            "invitation_sha256": hashlib.sha256(
                str(profile["invitation"]["text"]).encode("utf-8")
            ).hexdigest(),
            "questions_sha256": sha256_json(profile["turns"]),
        },
        "resident_media": {
            "media_question_count": len(media.MEDIA_QUESTIONS),
            "separate_behavior_question_count": len(media.TURING_PSYCH_QUESTIONS),
            "media_questions_sha256": sha256_json(media.MEDIA_QUESTIONS),
            "behavior_questions_sha256": sha256_json(media.TURING_PSYCH_QUESTIONS),
            "sources": sources,
        },
        "required_sequence": [
            "exact_qwen_vision",
            "exact_qwen_unload_and_absence",
            "source_bound_audio_presentation",
            "exact_qwen_person_text",
            "exact_qwen_final_unload_and_all_model_absence",
        ],
        "forbidden_current_actions": [
            "live_model_call",
            "camera_or_microphone",
            "voice_or_speaker_playback",
            "body_or_blender",
            "person_memory_or_preference_promotion",
        ],
        "truth_limits": {
            "observed_behavior_only": True,
            "consciousness_or_humanity_proven": False,
            "clinical_diagnostic_result": None,
            "preparation_is_experience": False,
            "sampled_is_complete": False,
            "automatic_memory_or_preference_created": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        choices=("resident_media_14_plus_8", "non_body_opt_in_8"),
        default="resident_media_14_plus_8",
    )
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--confirm-exact-qwen35-only", action="store_true")
    parser.add_argument("--confirm-private-owner-supervision", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--confirm-exact-sources", action="store_true")
    parser.add_argument("--confirm-speaker-playback", action="store_true")
    parser.add_argument("--confirm-local-audio-capture", action="store_true")
    parser.add_argument("--capture-device-name", default="")
    parser.add_argument("--confirm-voluntary-invitation", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.execute_live:
        print(json.dumps(readiness_description(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    common = (
        args.confirm_exact_qwen35_only
        and args.confirm_private_owner_supervision
        and args.confirm_no_active_blender
    )
    media_flags = args.confirm_exact_sources and args.confirm_speaker_playback
    if (
        not common
        or (args.suite == "resident_media_14_plus_8" and not media_flags)
        or (
            args.suite == "non_body_opt_in_8"
            and not args.confirm_voluntary_invitation
        )
    ):
        raise SystemExit("refusing live acceptance without every suite-specific confirmation")
    capture_name = str(args.capture_device_name or "").strip()
    if bool(capture_name) != bool(args.confirm_local_audio_capture):
        raise SystemExit(
            "local capture requires both --confirm-local-audio-capture and "
            "--capture-device-name; use neither for partial no-capture evidence"
        )
    if args.suite != "resident_media_14_plus_8" and capture_name:
        raise SystemExit("local audio capture belongs only to the resident-media suite")
    if media._blender_processes():
        raise QwenOnlyAcceptanceError("Blender is active; live acceptance must wait")
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    output_root = output_root.resolve(strict=False)
    try:
        output_root.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise QwenOnlyAcceptanceError("output root escaped project") from exc
    attempt = media._allocate_attempt(output_root / args.suite)
    transport = media.LoopbackOllamaTransport()
    if args.suite == "resident_media_14_plus_8":
        report = run_qwen_only_media_acceptance(
            attempt=attempt,
            transport=transport,
            audio_hook=media.WindowsBoundedAudioPlaybackHook(
                owner_supervised=True,
                capture_device_name=capture_name or None,
                capture_explicitly_confirmed=args.confirm_local_audio_capture,
            ),
            responder_factory=lambda exact_transport: ExactQwenKiraResponder(
                exact_transport, evidence_root=attempt / "isolated_person_state"
            ),
        )
    else:
        responder = ExactQwenKiraResponder(
            transport, evidence_root=attempt / "isolated_person_state"
        )
        result = run_extended_non_body_profile(responder)
        release = release_exact_qwen_if_resident(
            transport, phase="non_body_extended_final"
        )
        report = {
            "schema": REPORT_SCHEMA,
            "attempt_id": attempt.name,
            "suite": args.suite,
            "result": result,
            "final_release": release,
            "status": "COMPLETE_PENDING_OWNER_QUALITATIVE_REVIEW",
        }
    media._write_json_exclusive(attempt / "LIVE_ACCEPTANCE.json", report)
    media._write_json_exclusive(attempt / "MANIFEST.json", media._manifest(attempt))
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": project_relative(attempt / "LIVE_ACCEPTANCE.json"),
                "report_sha256": sha256_file(attempt / "LIVE_ACCEPTANCE.json"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
