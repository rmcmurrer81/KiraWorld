"""
Pre-GPU daily life manager for Kira and Lisa.

This keeps daily life lightweight: JSON state, small logs, and explainable
activity choices. It does not run models, internet, voice, video, or worlds.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_ENTITIES = {"kira", "lisa"}
VALID_CYCLE = {"wake_orienting", "active", "quiet", "private", "resting", "sleeping", "dreaming", "waking"}
VALID_SLEEP = {"awake", "drowsy", "resting", "asleep", "dreaming", "waking", "insomniac"}
VALID_INTERRUPT = {"low", "medium", "high", "emergency_only"}
VALID_MOOD = {"neutral", "warm", "playful", "curious", "bored", "sad", "angry", "jealous", "anxious", "tired", "reflective"}
VALID_ACTIVITY = {
    "none",
    "reading",
    "research",
    "talking",
    "music",
    "private_time",
    "memory_replay",
    "notebook_world_planning",
    "doctor_ai_session",
    "dream",
    "rest",
    "creative_project",
    "self_reflection",
}
VALID_PRIVACY = {"public", "personal", "private", "locked_private"}
VALID_VISIBILITY = {"none", "status_only", "small_summary", "selected_details", "full"}
VALID_MEMORY_TYPE = {"none", "event", "reflection", "dream", "idle_thought", "relationship", "insight"}
QUIET_ACTIVITY_CONTINUATION_STEPS = {
    "reading": 12,
    "research": 6,
    "music": 6,
    "notebook_world_planning": 8,
    "rest": 6,
    "creative_project": 8,
    "self_reflection": 4,
}
MAX_CONTINUATION_STEPS = 24

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = PROJECT_ROOT / "Data" / "daily_life" / "runtime"
DEFAULT_LOG_DIR = PROJECT_ROOT / "Data" / "daily_life" / "logs" / "events"
DEFAULT_READING_SESSION_DIR = PROJECT_ROOT / "Data" / "reading" / "sessions"
DEFAULT_READING_RECOMMENDATION_DIR = PROJECT_ROOT / "Data" / "reading"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def validate_daily_life_state(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "entity_id",
        "cycle_state",
        "sleep_state",
        "mood_state",
        "current_activity",
        "privacy_state",
        "unpredictability",
        "memory_policy",
    }
    missing = sorted(required - set(data))
    if missing:
        errors.append("Missing required fields: " + ", ".join(missing))
    if data.get("entity_id") not in VALID_ENTITIES:
        errors.append("entity_id must be kira or lisa.")
    if data.get("cycle_state") not in VALID_CYCLE:
        errors.append(f"cycle_state must be one of: {', '.join(sorted(VALID_CYCLE))}")

    sleep = data.get("sleep_state")
    if not isinstance(sleep, dict):
        errors.append("sleep_state must be an object.")
    else:
        if sleep.get("state") not in VALID_SLEEP:
            errors.append(f"sleep_state.state must be one of: {', '.join(sorted(VALID_SLEEP))}")
        if sleep.get("can_be_interrupted") not in (True, False, "emergency_only"):
            errors.append("sleep_state.can_be_interrupted must be true, false, or emergency_only.")

    mood = data.get("mood_state")
    if not isinstance(mood, dict):
        errors.append("mood_state must be an object.")
    else:
        if mood.get("primary_mood") not in VALID_MOOD:
            errors.append(f"mood_state.primary_mood must be one of: {', '.join(sorted(VALID_MOOD))}")
        intensity = mood.get("intensity")
        if not isinstance(intensity, (int, float)) or not 0 <= float(intensity) <= 1:
            errors.append("mood_state.intensity must be a number from 0.0 to 1.0.")

    activity = data.get("current_activity")
    if not isinstance(activity, dict):
        errors.append("current_activity must be an object.")
    else:
        if activity.get("activity_type") not in VALID_ACTIVITY:
            errors.append(f"current_activity.activity_type must be one of: {', '.join(sorted(VALID_ACTIVITY))}")
        if activity.get("interruptibility") not in VALID_INTERRUPT:
            errors.append(f"current_activity.interruptibility must be one of: {', '.join(sorted(VALID_INTERRUPT))}")
        continuation = activity.get("continuation_steps_remaining", 0)
        if (
            isinstance(continuation, bool)
            or not isinstance(continuation, int)
            or not 0 <= continuation <= MAX_CONTINUATION_STEPS
        ):
            errors.append(
                f"current_activity.continuation_steps_remaining must be an integer from 0 to {MAX_CONTINUATION_STEPS}."
            )

    privacy = data.get("privacy_state")
    if not isinstance(privacy, dict):
        errors.append("privacy_state must be an object.")
    else:
        if privacy.get("level") not in VALID_PRIVACY:
            errors.append(f"privacy_state.level must be one of: {', '.join(sorted(VALID_PRIVACY))}")
        for key in ("robert_visibility", "kira_lisa_visibility"):
            if privacy.get(key) not in VALID_VISIBILITY:
                errors.append(f"privacy_state.{key} must be one of: {', '.join(sorted(VALID_VISIBILITY))}")

    unpredictability = data.get("unpredictability")
    if not isinstance(unpredictability, dict):
        errors.append("unpredictability must be an object.")
    else:
        if unpredictability.get("variation_allowed") not in (True, False):
            errors.append("unpredictability.variation_allowed must be true or false.")
        if unpredictability.get("must_remain_explainable") is not True:
            errors.append("unpredictability.must_remain_explainable must be true.")

    memory = data.get("memory_policy")
    if not isinstance(memory, dict):
        errors.append("memory_policy must be an object.")
    else:
        if memory.get("candidate_for_memory") not in (True, False):
            errors.append("memory_policy.candidate_for_memory must be true or false.")
        if memory.get("memory_type") not in VALID_MEMORY_TYPE:
            errors.append(f"memory_policy.memory_type must be one of: {', '.join(sorted(VALID_MEMORY_TYPE))}")
        if memory.get("promote_only_if_meaningful") is not True:
            errors.append("memory_policy.promote_only_if_meaningful must be true.")
        if memory.get("store_private_details") not in (True, False):
            errors.append("memory_policy.store_private_details must be true or false.")

    return errors


def default_state(entity_id: str) -> dict[str, Any]:
    entity = entity_id.lower()
    if entity not in VALID_ENTITIES:
        raise ValueError("entity_id must be kira or lisa.")
    mood = "curious" if entity == "kira" else "reflective"
    public_summary = f"{entity.title()} is awake and keeping a light pre-GPU daily life state."
    return {
        "entity_id": entity,
        "cycle_state": "quiet",
        "sleep_state": {
            "state": "awake",
            "started_at": utc_timestamp(),
            "natural_wake_window": "",
            "can_be_interrupted": True,
        },
        "mood_state": {
            "primary_mood": mood,
            "intensity": 0.35,
            "toward": "",
        },
        "current_activity": {
            "activity_type": "none",
            "source_path": "",
            "public_summary": public_summary,
            "private_summary": "",
            "interruptibility": "medium",
            "continuation_steps_remaining": 0,
            "self_chosen": False,
            "decision_checkpoint_due": False,
            "allowed_next_choices": ["continue", "pause", "switch", "rest", "do_nothing"],
        },
        "privacy_state": {
            "level": "personal",
            "robert_visibility": "status_only",
            "kira_lisa_visibility": "small_summary",
        },
        "unpredictability": {
            "variation_allowed": True,
            "variation_reason": "curiosity",
            "must_remain_explainable": True,
        },
        "memory_policy": {
            "candidate_for_memory": False,
            "memory_type": "none",
            "promote_only_if_meaningful": True,
            "store_private_details": False,
        },
        "updated_at": utc_timestamp(),
    }


class DailyLifeManager:
    def __init__(
        self,
        state_dir: str | Path = DEFAULT_STATE_DIR,
        log_dir: str | Path = DEFAULT_LOG_DIR,
        reading_session_dir: str | Path = DEFAULT_READING_SESSION_DIR,
        reading_recommendation_dir: str | Path = DEFAULT_READING_RECOMMENDATION_DIR,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.log_dir = Path(log_dir)
        self.reading_session_dir = Path(reading_session_dir)
        self.reading_recommendation_dir = Path(reading_recommendation_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_state(self, entity_id: str) -> dict[str, Any]:
        path = self._state_path(entity_id)
        if not path.exists():
            state = default_state(entity_id)
            self._write_state(state)
            return state
        return json.loads(path.read_text(encoding="utf-8"))

    def list_states(self) -> list[dict[str, Any]]:
        return [self.get_state("kira"), self.get_state("lisa")]

    def set_state(
        self,
        entity_id: str,
        *,
        cycle_state: str,
        mood: str,
        intensity: float,
        activity_type: str,
        public_summary: str,
        private_summary: str = "",
        privacy_level: str = "personal",
        robert_visibility: str = "status_only",
        kira_lisa_visibility: str = "small_summary",
        interruptibility: str = "medium",
        toward: str = "",
        source_path: str = "",
        variation_reason: str = "curiosity",
        candidate_for_memory: bool = False,
        memory_type: str = "none",
        store_private_details: bool = False,
        continuation_steps_remaining: int | None = None,
        self_chosen: bool = True,
    ) -> dict[str, Any]:
        state = self.get_state(entity_id)
        previous_activity = state.get("current_activity", {}) if isinstance(state.get("current_activity"), dict) else {}
        same_activity = (
            previous_activity.get("activity_type") == activity_type
            and str(previous_activity.get("source_path") or "") == str(source_path or "")
        )
        if continuation_steps_remaining is None:
            previous_remaining = previous_activity.get("continuation_steps_remaining")
            if same_activity and isinstance(previous_remaining, int) and not isinstance(previous_remaining, bool):
                continuation_steps_remaining = previous_remaining
            else:
                continuation_steps_remaining = QUIET_ACTIVITY_CONTINUATION_STEPS.get(activity_type, 0)
        continuation_steps_remaining = max(
            0,
            min(MAX_CONTINUATION_STEPS, int(continuation_steps_remaining)),
        )
        state["cycle_state"] = cycle_state
        state["mood_state"] = {"primary_mood": mood, "intensity": float(intensity), "toward": toward}
        state["current_activity"] = {
            "activity_type": activity_type,
            "source_path": source_path,
            "public_summary": public_summary,
            "private_summary": private_summary,
            "interruptibility": interruptibility,
            "continuation_steps_remaining": continuation_steps_remaining,
            "self_chosen": bool(self_chosen),
            "decision_checkpoint_due": bool(
                activity_type in QUIET_ACTIVITY_CONTINUATION_STEPS
                and continuation_steps_remaining == 0
            ),
            "allowed_next_choices": ["continue", "pause", "switch", "rest", "do_nothing"],
        }
        state["privacy_state"] = {
            "level": privacy_level,
            "robert_visibility": robert_visibility,
            "kira_lisa_visibility": kira_lisa_visibility,
        }
        state["unpredictability"] = {
            "variation_allowed": True,
            "variation_reason": variation_reason,
            "must_remain_explainable": True,
        }
        state["memory_policy"] = {
            "candidate_for_memory": candidate_for_memory,
            "memory_type": memory_type,
            "promote_only_if_meaningful": True,
            "store_private_details": store_private_details,
        }
        state["sleep_state"] = self._sleep_for_cycle(state.get("sleep_state", {}), cycle_state)
        state["updated_at"] = utc_timestamp()
        self._write_state(state)
        return deepcopy(state)

    def advance_away_step(self, entity_id: str, trigger: str = "away_mode") -> dict[str, Any]:
        state = self.get_state(entity_id)
        choice = self.choose_activity(entity_id)
        mood = str(state.get("mood_state", {}).get("primary_mood", "neutral"))
        privacy = str(state.get("privacy_state", {}).get("level", "personal"))
        entity = entity_id.lower()

        if privacy == "locked_private" or mood in {"angry", "jealous"}:
            return self.set_state(
                entity,
                cycle_state="private",
                mood=mood if mood in VALID_MOOD else "reflective",
                intensity=max(0.45, float(state.get("mood_state", {}).get("intensity", 0.4))),
                activity_type="private_time",
                public_summary=f"{entity.title()} is taking private time and may not answer right away.",
                private_summary="Private emotional processing is not exposed by default.",
                privacy_level="locked_private",
                robert_visibility="status_only",
                kira_lisa_visibility="selected_details",
                interruptibility="low",
                variation_reason="relationship",
            )

        if mood in {"tired", "sad", "anxious"}:
            return self.set_state(
                entity,
                cycle_state="resting",
                mood=mood,
                intensity=float(state.get("mood_state", {}).get("intensity", 0.35)),
                activity_type="rest",
                public_summary=f"{entity.title()} is resting during away mode.",
                privacy_level="personal",
                robert_visibility="status_only",
                interruptibility="emergency_only",
                variation_reason="fatigue",
            )

        activity = choice["activity_type"]
        summary = choice["public_summary"]
        return self.set_state(
            entity,
            cycle_state="quiet",
            mood=mood if mood in VALID_MOOD else ("curious" if entity == "kira" else "reflective"),
            intensity=float(state.get("mood_state", {}).get("intensity", 0.35)),
            activity_type=activity,
            public_summary=summary,
            private_summary=choice["private_reason"],
            privacy_level=choice["privacy_level"],
            robert_visibility=choice["robert_visibility"],
            kira_lisa_visibility=choice["kira_lisa_visibility"],
            interruptibility=choice["interruptibility"],
            source_path=choice["source_path"],
            variation_reason=choice["variation_reason"] if trigger == "away_mode" else "random_small_shift",
            continuation_steps_remaining=choice.get("continuation_steps_remaining"),
            self_chosen=True,
        )

    def choose_activity(self, entity_id: str) -> dict[str, Any]:
        """Choose one explainable, advisory activity for the current daily state."""
        state = self.get_state(entity_id)
        entity = entity_id.lower()
        mood = str(state.get("mood_state", {}).get("primary_mood", "neutral"))
        privacy = str(state.get("privacy_state", {}).get("level", "personal"))
        current = state.get("current_activity", {}) if isinstance(state.get("current_activity"), dict) else {}
        active_session = self._active_reading_session(entity)
        recommendation = self._top_reading_recommendation(entity)

        if privacy == "locked_private":
            return self._activity_choice(
                entity,
                action="keep_private_time",
                activity_type="private_time",
                public_summary=f"{entity.title()} is taking private time and may not answer right away.",
                private_reason="Locked-private state already active.",
                interruptibility="low",
                privacy_level="locked_private",
            )

        if mood in {"tired", "sad", "anxious"}:
            return self._activity_choice(
                entity,
                action="rest_or_self_reflect",
                activity_type="rest" if mood == "tired" else "self_reflection",
                public_summary=f"{entity.title()} is keeping things quiet for a while.",
                private_reason=f"Mood is {mood}, so a low-pressure activity is preferred.",
                interruptibility="emergency_only" if mood == "tired" else "low",
            )

        if mood in {"angry", "jealous"}:
            return self._activity_choice(
                entity,
                action="private_reflection",
                activity_type="private_time",
                public_summary=f"{entity.title()} is taking space before choosing what to say.",
                private_reason=f"Mood is {mood}; privacy and emotional cooling are preferred.",
                interruptibility="low",
                privacy_level="private",
            )

        if mood == "bored":
            if active_session:
                return self._activity_choice(
                    entity,
                    action="may_continue_pause_or_abandon_book",
                    activity_type="reading",
                    source_path=active_session["source_path"],
                    public_summary=f"{entity.title()} is deciding whether to continue reading or stop this book.",
                    private_reason="Boredom can mean the current book is not working; abandoning it is allowed.",
                    allowed_reader_choices=["continue_reading", "pause_reading", "abandon_book"],
                )
            if recommendation:
                return self._reading_choice(entity, recommendation, action="start_recommended_reading")
            return self._activity_choice(
                entity,
                action="listen_to_music_or_browse_library",
                activity_type="music",
                public_summary=f"{entity.title()} is browsing for something low-pressure to do.",
                private_reason="Boredom without an active book can lead to music or light library browsing.",
                allowed_reader_choices=["listen_to_music", "browse_library", "do_nothing"],
            )

        current_type = str(current.get("activity_type") or "none")
        configured_budget = QUIET_ACTIVITY_CONTINUATION_STEPS.get(current_type, 0)
        raw_remaining = current.get("continuation_steps_remaining", configured_budget)
        remaining = (
            raw_remaining
            if isinstance(raw_remaining, int) and not isinstance(raw_remaining, bool)
            else configured_budget
        )
        if current_type in QUIET_ACTIVITY_CONTINUATION_STEPS and remaining > 0:
            return self._activity_choice(
                entity,
                action="continue_self_chosen_quiet_activity",
                activity_type=current_type,
                source_path=str(current.get("source_path") or (active_session or {}).get("source_path") or ""),
                public_summary=str(current.get("public_summary") or f"{entity.title()} is continuing a quiet activity."),
                private_reason=(
                    "The current quiet activity remains available by choice; no scheduler churn is required."
                ),
                interruptibility=str(current.get("interruptibility") or "medium"),
                privacy_level=privacy if privacy in VALID_PRIVACY else "personal",
                robert_visibility=str(state.get("privacy_state", {}).get("robert_visibility") or "small_summary"),
                kira_lisa_visibility=str(state.get("privacy_state", {}).get("kira_lisa_visibility") or "small_summary"),
                allowed_reader_choices=["continue_current_activity", "pause", "switch", "rest", "do_nothing"],
                continuation_steps_remaining=max(0, remaining - 1),
            )

        if current_type == "reading" and active_session:
            return self._activity_choice(
                entity,
                action="reading_decision_checkpoint",
                activity_type="reading",
                source_path=active_session["source_path"],
                public_summary=f"{entity.title()} has reached a reading choice point.",
                private_reason="A bounded continuation window ended; continuing, pausing, switching, or resting are all valid.",
                allowed_reader_choices=["continue_reading", "pause_reading", "abandon_book", "switch_activity", "rest"],
                continuation_steps_remaining=0,
                decision_checkpoint_due=True,
            )

        if recommendation and mood in {"curious", "reflective", "neutral", "warm", "playful"}:
            return self._reading_choice(entity, recommendation, action="consider_recommended_reading")

        if entity == "lisa":
            return self._activity_choice(
                entity,
                action="work_on_private_creative_project",
                activity_type="creative_project",
                public_summary="Lisa is quietly working on a small creative idea.",
                private_reason="Lisa's default idle rhythm leans toward private creative work.",
                allowed_reader_choices=["work_on_project", "ask_kira_to_talk", "rest"],
            )

        return self._activity_choice(
            entity,
            action="private_reflection_or_light_reading",
            activity_type="self_reflection",
            public_summary="Kira is thinking quietly and may choose a light reading thread.",
            private_reason="Kira's default idle rhythm leans toward curiosity and reflection.",
            allowed_reader_choices=["reflect", "read", "ask_lisa_to_talk", "rest"],
        )

    def choose_and_apply_activity(self, entity_id: str) -> dict[str, Any]:
        choice = self.choose_activity(entity_id)
        state = self.set_state(
            entity_id,
            cycle_state="quiet" if choice["activity_type"] not in {"rest", "private_time"} else ("resting" if choice["activity_type"] == "rest" else "private"),
            mood=str(self.get_state(entity_id).get("mood_state", {}).get("primary_mood", "neutral")),
            intensity=float(self.get_state(entity_id).get("mood_state", {}).get("intensity", 0.35)),
            activity_type=choice["activity_type"],
            public_summary=choice["public_summary"],
            private_summary=choice["private_reason"],
            privacy_level=choice["privacy_level"],
            robert_visibility=choice["robert_visibility"],
            kira_lisa_visibility=choice["kira_lisa_visibility"],
            interruptibility=choice["interruptibility"],
            source_path=choice["source_path"],
            variation_reason=choice["variation_reason"],
            continuation_steps_remaining=choice.get("continuation_steps_remaining"),
            self_chosen=True,
        )
        log = self.write_log(
            entity_id,
            notes=(
                f"Idle rhythm note: chose {choice['action']}. "
                f"Allowed choices were {', '.join(choice.get('allowed_reader_choices', []))}. "
                "This is a small activity trace, not a promoted memory."
            ),
        )
        return {"choice": choice, "state": state, "idle_log": log}

    def phone_availability(self, entity_id: str) -> dict[str, Any]:
        state = self.get_state(entity_id)
        cycle = state.get("cycle_state")
        sleep = state.get("sleep_state", {}).get("state")
        activity = state.get("current_activity", {})
        privacy = state.get("privacy_state", {})
        mood = state.get("mood_state", {})
        interruptibility = activity.get("interruptibility", "medium")

        if privacy.get("level") == "locked_private":
            recommendation = "delay_or_ignore"
            reason = "locked private time"
        elif sleep in {"asleep", "dreaming"} or cycle in {"sleeping", "dreaming"}:
            recommendation = "emergency_only"
            reason = "sleep or dream state"
        elif interruptibility == "emergency_only":
            recommendation = "delay_unless_urgent"
            reason = "resting or low interruptibility"
        elif mood.get("primary_mood") in {"angry", "jealous"} and float(mood.get("intensity", 0)) >= 0.6:
            recommendation = "may_decline_or_answer_coldly"
            reason = "strong mood affects answer choice"
        else:
            recommendation = "available_by_choice"
            reason = "no hard daily-life blocker"

        return {
            "entity_id": state["entity_id"],
            "recommendation": recommendation,
            "reason": reason,
            "current_activity": activity.get("activity_type", "none"),
            "public_summary": activity.get("public_summary", ""),
            "mood": mood.get("primary_mood", "neutral"),
            "privacy_level": privacy.get("level", "personal"),
            "recipient_may_decline_delay_or_ignore": True,
        }

    def write_log(self, entity_id: str, notes: str = "") -> dict[str, Any]:
        state = self.get_state(entity_id)
        now = utc_timestamp()
        log = {
            "log_id": f"daily_life_{state['entity_id']}_{now.replace(':', '').replace('-', '').replace('Z', 'z')}",
            "status": "draft",
            "actor": state["entity_id"],
            "started_at": state.get("updated_at", now),
            "ended_at": now,
            "cycle_state": state["cycle_state"],
            "activity_type": state["current_activity"]["activity_type"],
            "public_summary": state["current_activity"].get("public_summary", ""),
            "private_summary": state["current_activity"].get("private_summary", ""),
            "share_permissions": {
                "robert": state["privacy_state"].get("robert_visibility", "status_only"),
                "kira": "full" if state["entity_id"] == "kira" else state["privacy_state"].get("kira_lisa_visibility", "small_summary"),
                "lisa": "full" if state["entity_id"] == "lisa" else state["privacy_state"].get("kira_lisa_visibility", "small_summary"),
            },
            "dream_fragment": {"present": state["current_activity"]["activity_type"] == "dream", "summary": "", "canon_status": "not_canon"},
            "doctor_ai_flags": ["private_session_possible"] if state["current_activity"]["activity_type"] == "doctor_ai_session" else [],
            "memory_candidates": [],
            "resource_use": {
                "pre_gpu_safe": True,
                "used_internet": False,
                "used_video": False,
                "used_heavy_model": False,
            },
            "notes": notes,
        }
        path = self.log_dir / f"{log['log_id']}.json"
        path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
        return log

    def _state_path(self, entity_id: str) -> Path:
        entity = entity_id.lower()
        if entity not in VALID_ENTITIES:
            raise ValueError("entity_id must be kira or lisa.")
        return self.state_dir / f"{entity}_daily_life_state.json"

    def _active_reading_session(self, entity_id: str) -> dict[str, str] | None:
        if not self.reading_session_dir.exists():
            return None
        for path in sorted(self.reading_session_dir.glob("*.json")):
            try:
                session = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if session.get("reader") != entity_id:
                continue
            if session.get("status") not in {"active", "paused"}:
                continue
            material = session.get("material", {}) if isinstance(session.get("material"), dict) else {}
            return {
                "session_path": _relative(path),
                "source_path": str(material.get("source_path", "")),
                "title": str(material.get("title", "")),
                "status": str(session.get("status", "")),
            }
        return None

    def _top_reading_recommendation(self, entity_id: str) -> dict[str, Any] | None:
        path = self.reading_recommendation_dir / f"reading_recommendations_{entity_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        recommendations = data.get("recommendations", [])
        if not isinstance(recommendations, list) or not recommendations:
            return None
        first = recommendations[0]
        return first if isinstance(first, dict) else None

    def _reading_choice(self, entity_id: str, recommendation: dict[str, Any], action: str) -> dict[str, Any]:
        title = str(recommendation.get("title", "a recommended book"))
        return self._activity_choice(
            entity_id,
            action=action,
            activity_type="reading",
            source_path=str(recommendation.get("source_path", "")),
            public_summary=f"{entity_id.title()} is considering reading {title}.",
            private_reason="Recommendation matched current interests, but the reader may decline.",
            allowed_reader_choices=["start_reading", "save_for_later", "decline", "choose_something_else"],
        )

    def _activity_choice(
        self,
        entity_id: str,
        *,
        action: str,
        activity_type: str,
        public_summary: str,
        private_reason: str,
        source_path: str = "",
        interruptibility: str = "medium",
        privacy_level: str = "personal",
        robert_visibility: str = "small_summary",
        kira_lisa_visibility: str = "small_summary",
        variation_reason: str = "curiosity",
        allowed_reader_choices: list[str] | None = None,
        continuation_steps_remaining: int | None = None,
        decision_checkpoint_due: bool = False,
    ) -> dict[str, Any]:
        return {
            "entity_id": entity_id,
            "action": action,
            "activity_type": activity_type,
            "source_path": source_path,
            "public_summary": public_summary,
            "private_reason": private_reason,
            "interruptibility": interruptibility,
            "privacy_level": privacy_level,
            "robert_visibility": robert_visibility,
            "kira_lisa_visibility": kira_lisa_visibility,
            "variation_reason": variation_reason,
            "allowed_reader_choices": allowed_reader_choices or ["accept", "decline", "delay", "do_nothing"],
            "continuation_steps_remaining": continuation_steps_remaining,
            "decision_checkpoint_due": bool(decision_checkpoint_due),
            "advisory_only": True,
            "may_decline_or_change_mind": True,
            "does_not_force_activity": True,
            "book_may_be_abandoned_if_not_liked": True,
        }

    def _write_state(self, state: dict[str, Any]) -> None:
        errors = validate_daily_life_state(state)
        if errors:
            raise ValueError("Daily life state failed validation: " + "; ".join(errors))
        self._state_path(state["entity_id"]).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def _sleep_for_cycle(self, current: dict[str, Any], cycle_state: str) -> dict[str, Any]:
        sleep = dict(current) if isinstance(current, dict) else {}
        if cycle_state == "sleeping":
            sleep.update({"state": "asleep", "can_be_interrupted": "emergency_only"})
        elif cycle_state == "dreaming":
            sleep.update({"state": "dreaming", "can_be_interrupted": "emergency_only"})
        elif cycle_state == "resting":
            sleep.update({"state": "resting", "can_be_interrupted": "emergency_only"})
        elif cycle_state == "waking":
            sleep.update({"state": "waking", "can_be_interrupted": True})
        else:
            sleep.update({"state": "awake", "can_be_interrupted": True})
        sleep.setdefault("started_at", utc_timestamp())
        sleep.setdefault("natural_wake_window", "")
        return sleep
