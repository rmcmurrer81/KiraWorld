"""Candidate-owned, non-executing movement-intent records.

Temporary people may write a short stage direction such as ``*smirks*`` in
their own generated reply.  This module separates that voluntary expression
from the words sent to speech and records it for a future body.  It deliberately
has no motor/runtime dependency: recording an intent never moves a live body
and never claims that a movement physically happened.

Only candidate-generated reply text belongs in this API.  User text is not an
input and therefore cannot be translated into a motor command here.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import threading
import uuid
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = PROJECT_ROOT / "Avatar" / "state" / "movement_intents"
DEFAULT_AUDIT_PATH = PROJECT_ROOT / "Data" / "runtime" / "candidate_movement_intents.jsonl"

SCHEMA_VERSION = 1
_WRITE_LOCK = threading.RLock()
_SINGLE_ASTERISK_STAGE = re.compile(r"(?<!\*)\*([^*\r\n]{1,180})\*(?!\*)")
_QUOTED_KIRA_SPEECH_WITH_NARRATION = re.compile(
    r"^\s*[\"\u201c](?P<spoken>[\s\S]+)[\"\u201d]\s*"
    r"(?P<narration>,?\s*(?:Kira|[Ss]he|[Hh]e|[Tt]hey|I)\s+"
    r"(?:said|says|asked|asks|replied|replies|answered|answers|murmured|murmurs|"
    r"whispered|whispers|remarked|remarks)\b[\s\S]*)$",
)


# Ordered from more specific to more general so, for example, ``raises an
# eyebrow`` is not reduced to an unspecific arm/hand raise.
_ACTION_SPECS: tuple[dict[str, object], ...] = (
    {
        "action": "pause_activity",
        "category": "activity_control",
        "pattern": re.compile(r"\b(?:pause|pauses|paused|pausing)\b", re.I),
        "capabilities": ["activity_controller"],
    },
    {
        "action": "stop_activity",
        "category": "activity_control",
        "pattern": re.compile(r"\b(?:stop|stops|stopped|stopping)\b", re.I),
        "capabilities": ["activity_controller"],
    },
    {
        "action": "change_activity",
        "category": "activity_control",
        "pattern": re.compile(r"\b(?:change|switch)(?:s|ed|ing)?\b[^,;]{0,32}\bactivit(?:y|ies)\b", re.I),
        "capabilities": ["activity_controller"],
    },
    {
        "action": "raise_eyebrow",
        "category": "face",
        "pattern": re.compile(r"\b(?:raise|raises|raised|raising|arch|arches|arched|arching)\b[^,;]{0,28}\beyebrows?\b", re.I),
        "capabilities": ["facial_rig", "left_right_eyebrow_controls"],
    },
    {
        "action": "lean_forward",
        "category": "posture",
        "pattern": re.compile(r"\b(?:lean|leans|leaned|leaning)\b[^,;]{0,24}\bforward\b", re.I),
        "capabilities": ["spine_rig", "balance_controller"],
    },
    {
        "action": "lean_back",
        "category": "posture",
        "pattern": re.compile(r"\b(?:lean|leans|leaned|leaning)\b[^,;]{0,24}\bback(?:ward|wards)?\b", re.I),
        "capabilities": ["spine_rig", "balance_controller"],
    },
    {
        "action": "smirk",
        "category": "face",
        "pattern": re.compile(r"\bsmirk(?:s|ed|ing)?\b", re.I),
        "capabilities": ["facial_rig", "mouth_corner_controls"],
    },
    {
        "action": "smile",
        "category": "face",
        "pattern": re.compile(r"\bsmil(?:e|es|ed|ing)\b", re.I),
        "capabilities": ["facial_rig", "mouth_corner_controls"],
    },
    {
        "action": "grin",
        "category": "face",
        "pattern": re.compile(r"\bgrin(?:s|ned|ning)?\b", re.I),
        "capabilities": ["facial_rig", "mouth_controls"],
    },
    {
        "action": "frown",
        "category": "face",
        "pattern": re.compile(r"\bfrown(?:s|ed|ing)?\b", re.I),
        "capabilities": ["facial_rig", "brow_and_mouth_controls"],
    },
    {
        "action": "wink",
        "category": "eyes",
        "pattern": re.compile(r"\bwink(?:s|ed|ing)?\b", re.I),
        "capabilities": ["eyelid_rig", "independent_eye_controls"],
    },
    {
        "action": "blink",
        "category": "eyes",
        "pattern": re.compile(r"\bblink(?:s|ed|ing)?\b", re.I),
        "capabilities": ["eyelid_rig"],
    },
    {
        "action": "nod",
        "category": "head",
        "pattern": re.compile(r"\bnod(?:s|ded|ding)?\b", re.I),
        "capabilities": ["neck_rig"],
    },
    {
        "action": "shake_head",
        "category": "head",
        "pattern": re.compile(r"\b(?:shake|shakes|shook|shaking)\b[^,;]{0,24}\b(?:my|her|his|their|the)?\s*head\b", re.I),
        "capabilities": ["neck_rig"],
    },
    {
        "action": "tilt_head",
        "category": "head",
        "pattern": re.compile(r"\b(?:tilt|tilts|tilted|tilting)\b[^,;]{0,24}\b(?:my|her|his|their|the)?\s*head\b", re.I),
        "capabilities": ["neck_rig"],
    },
    {
        "action": "look_or_glance",
        "category": "gaze",
        "pattern": re.compile(r"\b(?:look|looks|looked|looking|glance|glances|glanced|glancing)\b", re.I),
        "capabilities": ["eye_aim_rig", "neck_rig"],
    },
    {
        "action": "shrug",
        "category": "upper_body",
        "pattern": re.compile(r"\bshrug(?:s|ged|ging)?\b", re.I),
        "capabilities": ["clavicle_rig", "shoulder_rig"],
    },
    {
        "action": "shift_weight",
        "category": "posture",
        "pattern": re.compile(r"\b(?:shift|shifts|shifted|shifting)\b[^,;]{0,32}\bweight\b", re.I),
        "capabilities": ["full_body_rig", "balance_controller", "foot_plant"],
    },
    {
        "action": "cross_arms",
        "category": "arms",
        "pattern": re.compile(r"\b(?:cross|crosses|crossed|crossing|fold|folds|folded|folding)\b[^,;]{0,24}\barms?\b", re.I),
        "capabilities": ["arm_rig", "hand_rig", "self_collision_avoidance"],
    },
    {
        "action": "wave",
        "category": "arms",
        "pattern": re.compile(r"\bwave(?:s|d|ing)?\b", re.I),
        "capabilities": ["arm_rig", "wrist_rig", "hand_rig"],
    },
    {
        "action": "raise_hand",
        "category": "arms",
        "pattern": re.compile(r"\b(?:raise|raises|raised|raising|lift|lifts|lifted|lifting)\b[^,;]{0,28}\b(?:hand|arm)\b", re.I),
        "capabilities": ["arm_rig", "shoulder_rig", "hand_rig"],
    },
    {
        "action": "point",
        "category": "hands",
        "pattern": re.compile(r"\bpoint(?:s|ed|ing)?\b", re.I),
        "capabilities": ["arm_rig", "hand_rig", "finger_rig"],
    },
    {
        "action": "reach",
        "category": "hands",
        "pattern": re.compile(r"\breach(?:es|ed|ing)?\b", re.I),
        "capabilities": ["arm_rig", "hand_ik", "grasp_planner"],
    },
    {
        "action": "touch",
        "category": "hands",
        "pattern": re.compile(r"\btouch(?:es|ed|ing)?\b", re.I),
        "capabilities": ["arm_rig", "hand_ik", "contact_sensing"],
    },
    {
        "action": "clasp_hands",
        "category": "hands",
        "pattern": re.compile(r"\bclasp(?:s|ed|ing)?\b", re.I),
        "capabilities": ["arm_rig", "hand_rig", "finger_rig"],
    },
    {
        "action": "rub_or_tap",
        "category": "hands",
        "pattern": re.compile(r"\b(?:rub|rubs|rubbed|rubbing|tap|taps|tapped|tapping)\b", re.I),
        "capabilities": ["arm_rig", "hand_rig", "contact_sensing"],
    },
    {
        "action": "wiggle_fingers_or_toes",
        "category": "digits",
        "pattern": re.compile(r"\b(?:wiggle|wiggles|wiggled|wiggling|wriggle|wriggles|wriggled|wriggling)\b[^,;]{0,30}\b(?:fingers?|toes?)\b", re.I),
        "capabilities": ["finger_or_toe_rig", "independent_digit_controls"],
    },
    {
        "action": "sigh_or_breathe",
        "category": "breathing",
        "pattern": re.compile(r"\b(?:sigh|sighs|sighed|sighing|inhale|inhales|inhaled|inhaling|exhale|exhales|exhaled|exhaling|breathe|breathes|breathed|breathing)\b", re.I),
        "capabilities": ["breathing_controller", "chest_rig"],
    },
    {
        "action": "sit",
        "category": "locomotion",
        "pattern": re.compile(r"\b(?:sit|sits|sat|sitting)\b", re.I),
        "capabilities": ["full_body_rig", "seat_alignment", "collision_queries"],
    },
    {
        "action": "lie_down",
        "category": "locomotion",
        "pattern": re.compile(r"\b(?:lie|lies|lay|laid|lying|laying)\b", re.I),
        "capabilities": ["full_body_rig", "surface_alignment", "collision_queries"],
    },
    {
        "action": "stand",
        "category": "locomotion",
        "pattern": re.compile(r"\b(?:stand|stands|stood|standing)\b", re.I),
        "capabilities": ["full_body_rig", "balance_controller", "foot_plant"],
    },
    {
        "action": "walk_or_step",
        "category": "locomotion",
        "pattern": re.compile(r"\b(?:walk|walks|walked|walking|step|steps|stepped|stepping)\b", re.I),
        "capabilities": ["locomotion_controller", "navigation", "foot_plant"],
    },
    {
        "action": "open_or_close_door",
        "category": "world_interaction",
        "pattern": re.compile(r"\b(?:open|opens|opened|opening|close|closes|closed|closing)\b[^,;]{0,28}\bdoor\b", re.I),
        "capabilities": ["world_interaction", "door_controller", "hand_ik"],
    },
    {
        "action": "pick_up_or_put_down",
        "category": "object_interaction",
        "pattern": re.compile(r"\b(?:pick(?:s|ed|ing)?\s+up|put(?:s|ting)?\s+down)\b", re.I),
        "capabilities": ["world_interaction", "hand_ik", "grasp_planner"],
    },
)

_MODIFIER_WORDS = {
    "slight",
    "slightly",
    "slow",
    "slowly",
    "quick",
    "quickly",
    "soft",
    "softly",
    "gentle",
    "gently",
    "subtle",
    "subtly",
    "playful",
    "playfully",
    "brief",
    "briefly",
    "forward",
    "back",
    "left",
    "right",
}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_candidate_id(value: str) -> str:
    safe = re.sub(r"[^a-z0-9._-]+", "_", str(value or "").strip().lower()).strip("._-")
    return safe[:120] or "unknown_candidate"


def _normalize_spoken_text(value: str) -> str:
    text = re.sub(r"[ \t]+", " ", str(value or ""))
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def _actions_for_stage(stage: str) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for spec in _ACTION_SPECS:
        pattern = spec["pattern"]
        if isinstance(pattern, re.Pattern) and pattern.search(stage):
            matches.append(
                {
                    "action": str(spec["action"]),
                    "category": str(spec["category"]),
                    "required_capabilities": list(spec["capabilities"]),
                }
            )
    return matches


def _split_quoted_kira_speech_from_narration(raw: str) -> tuple[str, str]:
    """Separate a narrow model-written dialogue/narration envelope.

    Kira occasionally returns prose such as ``"I'm ready," Kira said,
    smiling. She stood and walked ...``.  Only the quoted words are speech.
    This deliberately does *not* strip ordinary quotations, quoted material
    attributed to Robert/another named person, or unquoted prose.  The caller
    still treats any recognized movements as candidate-owned, non-executing
    future-body intents.
    """

    match = _QUOTED_KIRA_SPEECH_WITH_NARRATION.fullmatch(str(raw or ""))
    if not match:
        return raw, ""
    spoken = str(match.group("spoken") or "").strip()
    narration = str(match.group("narration") or "").lstrip(" ,\t\r\n")
    # Dialogue punctuation commonly puts a comma before the closing quote
    # solely because an attribution follows.  Once that attribution is kept
    # out of speech, end the public sentence cleanly without changing words.
    if spoken.endswith(","):
        spoken = spoken[:-1].rstrip() + "."
    return spoken, narration


def extract_candidate_owned_movement_intents(candidate_reply: str) -> dict[str, object]:
    """Separate voluntary stage movement from the reply's spoken words.

    The function intentionally accepts exactly one text channel: the
    candidate-generated reply.  It cannot interpret a user's request as a
    movement.  Unrecognized asterisk text is preserved so ordinary Markdown
    emphasis is not silently deleted.
    """

    raw = str(candidate_reply or "")
    public_raw, narrative_stage = _split_quoted_kira_speech_from_narration(raw)
    intents: list[dict[str, object]] = []
    output: list[str] = []
    cursor = 0
    recognized_stage_count = 0
    stage_matches = list(_SINGLE_ASTERISK_STAGE.finditer(public_raw))
    for stage_index, match in enumerate(stage_matches):
        output.append(public_raw[cursor : match.start()])
        stage = _normalize_spoken_text(match.group(1))
        actions = _actions_for_stage(stage)
        if actions:
            recognized_stage_count += 1
            modifiers = sorted(
                {
                    token.lower()
                    for token in re.findall(r"[A-Za-z]+", stage)
                    if token.lower() in _MODIFIER_WORDS
                }
            )
            for action_index, action in enumerate(actions):
                intents.append(
                    {
                        **action,
                        "stage_index": stage_index,
                        "action_index": action_index,
                        "raw_stage_direction": stage,
                        "modifiers": modifiers,
                    }
                )
            # A movement direction belongs to the future-body lane, not speech.
            output.append(" ")
        else:
            output.append(match.group(0))
        cursor = match.end()
    output.append(public_raw[cursor:])
    recognized_narration_count = 0
    if narrative_stage:
        narrative_actions = _actions_for_stage(narrative_stage)
        if narrative_actions:
            recognized_stage_count += 1
            recognized_narration_count = 1
            modifiers = sorted(
                {
                    token.lower()
                    for token in re.findall(r"[A-Za-z]+", narrative_stage)
                    if token.lower() in _MODIFIER_WORDS
                }
            )
            for action_index, action in enumerate(narrative_actions):
                intents.append(
                    {
                        **action,
                        "stage_index": len(stage_matches),
                        "action_index": action_index,
                        "raw_stage_direction": _normalize_spoken_text(narrative_stage),
                        "modifiers": modifiers,
                        "source_style": "third_person_narration_after_quoted_kira_speech",
                    }
                )
    # First-person future intentions are legitimate action requests, but the
    # words remain public speech.  Past/present completion claims are not
    # dispatched: runtime truth may never be rewritten from dialogue alone.
    intention_pattern = re.compile(
        r"\b(?:I\s+(?:want|would\s+like|need|choose|intend|am\s+going)\s+to|let(?:'s|\s+us))\s+"
        r"(?P<action>pause|stop|smile|sit|stand|walk|reach|wave|open|close|pick|put|change)\b"
        r"(?P<context>[^.!?]{0,80})",
        re.I,
    )
    for intention_index, match in enumerate(intention_pattern.finditer(public_raw)):
        phrase = _normalize_spoken_text(match.group(0))
        actions = _actions_for_stage(phrase)
        for action_index, action in enumerate(actions):
            intents.append(
                {
                    **action,
                    "stage_index": len(stage_matches) + recognized_narration_count + intention_index,
                    "action_index": action_index,
                    "raw_stage_direction": phrase,
                    "modifiers": [],
                    "source_style": "first_person_future_intention",
                }
            )
    return {
        "spoken_text": _normalize_spoken_text("".join(output)),
        "movement_intents": intents,
        "recognized_stage_count": recognized_stage_count,
        "recognized_narration_count": recognized_narration_count,
    }


def movement_intent_state_path(candidate_id: str, state_dir: Path | None = None) -> Path:
    return (state_dir or DEFAULT_STATE_DIR) / f"{_safe_candidate_id(candidate_id)}.json"


def _read_json(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _atomic_write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _append_jsonl(path: Path, records: Iterable[dict[str, object]]) -> None:
    rows = list(records)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def record_candidate_owned_movement_intents(
    candidate_id: str,
    candidate_label: str,
    parsed_intents: Iterable[dict[str, object]],
    *,
    source_turn_id: str,
    source_at: str | None = None,
    state_dir: Path | None = None,
    audit_path: Path | None = None,
) -> dict[str, object]:
    """Persist candidate-owned intentions without dispatching any movement."""

    safe_id = _safe_candidate_id(candidate_id)
    turn_id = str(source_turn_id or "").strip()
    if not turn_id:
        raise ValueError("source_turn_id is required so retries can be deduplicated")
    recorded_at = str(source_at or _now_iso())
    path = movement_intent_state_path(safe_id, state_dir)
    candidates = [dict(item) for item in parsed_intents if isinstance(item, dict)]
    new_records: list[dict[str, object]] = []

    with _WRITE_LOCK:
        current = _read_json(path, {})
        if not isinstance(current, dict):
            current = {}
        records = current.get("records")
        if not isinstance(records, list):
            records = []
        existing_fingerprints = {
            str(item.get("dedupe_fingerprint") or "")
            for item in records
            if isinstance(item, dict)
        }
        for parsed in candidates:
            fingerprint_source = "|".join(
                [
                    safe_id,
                    turn_id,
                    str(parsed.get("stage_index", "")),
                    str(parsed.get("action_index", "")),
                    str(parsed.get("action", "")),
                    str(parsed.get("raw_stage_direction", "")),
                ]
            )
            fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
            if fingerprint in existing_fingerprints:
                continue
            record = {
                "schema_version": SCHEMA_VERSION,
                "record_id": f"movement_intent_{uuid.uuid4().hex}",
                "recorded_at": recorded_at,
                "candidate_id": safe_id,
                "candidate_label": str(candidate_label or candidate_id).strip(),
                "action": str(parsed.get("action") or "").strip(),
                "category": str(parsed.get("category") or "").strip(),
                "raw_stage_direction": str(parsed.get("raw_stage_direction") or "").strip(),
                "modifiers": list(parsed.get("modifiers") or []),
                "required_capabilities": list(parsed.get("required_capabilities") or []),
                "source": {
                    "kind": (
                        "candidate_generated_third_person_narration"
                        if parsed.get("source_style")
                        == "third_person_narration_after_quoted_kira_speech"
                        else "candidate_generated_first_person_intention"
                        if parsed.get("source_style") == "first_person_future_intention"
                        else "candidate_generated_stage_direction"
                    ),
                    "style": str(parsed.get("source_style") or "single_asterisk_stage_direction"),
                    "turn_id": turn_id,
                    "stage_index": int(parsed.get("stage_index") or 0),
                    "action_index": int(parsed.get("action_index") or 0),
                },
                "ownership": {
                    "authored_by_candidate": True,
                    "candidate_voluntary_expression": True,
                    "user_message_parsed_as_motor_command": False,
                },
                "execution": {
                    "status": "recorded_for_future_body",
                    "dispatched_to_live_body": False,
                    "physical_completion_claimed": False,
                    "requires_candidate_choice_at_execution": True,
                },
                "dedupe_fingerprint": fingerprint,
            }
            records.append(record)
            new_records.append(record)
            existing_fingerprints.add(fingerprint)

        if new_records:
            payload = {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": safe_id,
                "candidate_label": str(candidate_label or candidate_id).strip(),
                "created_at": str(current.get("created_at") or recorded_at),
                "updated_at": recorded_at,
                "policy": {
                    "candidate_owned": True,
                    "future_body_only": True,
                    "user_text_is_not_a_motor_command": True,
                    "physical_completion_is_not_claimed": True,
                },
                "records": records,
            }
            _atomic_write_json(path, payload)
            audit = audit_path if audit_path is not None else DEFAULT_AUDIT_PATH
            _append_jsonl(
                audit,
                [
                    {
                        "at": recorded_at,
                        "event": "candidate_owned_movement_intent_recorded",
                        "candidate_id": safe_id,
                        "candidate_label": str(candidate_label or candidate_id).strip(),
                        "record_id": item["record_id"],
                        "action": item["action"],
                        "source_turn_id": turn_id,
                        "dispatched_to_live_body": False,
                        "physical_completion_claimed": False,
                    }
                    for item in new_records
                ],
            )

    return {
        "candidate_id": safe_id,
        "state_path": str(path),
        "recorded": new_records,
        "recorded_count": len(new_records),
        "deduplicated_count": max(0, len(candidates) - len(new_records)),
    }


def prepare_and_record_candidate_reply(
    candidate_id: str,
    candidate_label: str,
    candidate_reply: str,
    *,
    source_turn_id: str,
    source_at: str | None = None,
    state_dir: Path | None = None,
    audit_path: Path | None = None,
) -> dict[str, object]:
    """Prepare speech/UI text and persist any voluntary future-body intents."""

    parsed = extract_candidate_owned_movement_intents(candidate_reply)
    persisted = record_candidate_owned_movement_intents(
        candidate_id,
        candidate_label,
        parsed["movement_intents"],
        source_turn_id=source_turn_id,
        source_at=source_at,
        state_dir=state_dir,
        audit_path=audit_path,
    )
    return {**parsed, **persisted}
