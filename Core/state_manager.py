"""
state_manager.py
Kira Project — Phase 1 Core File

Controls state transitions and coordinates which systems are allowed to run.
The State Manager does not replace personality, memory, or emotion.
It decides which systems are active, when, and at what intensity.

Source documents:
  - STATE_MANAGER_v1.pdf
  - STATE_OBJECT_SCHEMA_TEMPLATE_v1.pdf
  - USER-AWAY_MODE_v1.pdf
  - SESSION_ZERO_OVERRIDES_v1.md

Primary states (Phase 1):
  active_conversation  — user present, conversation ongoing
  quiet_presence       — user present, no active conversation
  idle_thought         — user absent or inactive, calm system
  sleep_dream          — extended idle, low load, dream mode eligible
  user_away            — user explicitly absent

Per SESSION_ZERO_OVERRIDES: State System must exist before Conversation Loop.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Optional


# Minimum inactive minutes before transitioning out of quiet_presence
IDLE_THRESHOLD_MINUTES = 10

# Minimum inactive minutes before dream mode is eligible
DREAM_THRESHOLD_MINUTES = 30


@dataclass
class SystemState:
    """
    Core runtime state object.
    Serializable — must be writable to state.json for persistence.
    """
    mode: str = "active_conversation"
    user_present: bool = True
    conversation_active: bool = False
    inactive_minutes: int = 0
    emotional_intensity: float = 0.0
    active_entity: str = "kira"           # which character is primary
    resource_load: str = "low"            # low | medium | high
    dream_eligible: bool = False
    last_insight_given: bool = False      # cooldown flag for Insight Trigger


class StateManager:
    """
    Central state controller for the Kira system.

    Usage:
        sm = StateManager()
        sm.update_presence(user_present=True)
        sm.update_conversation(active=True)
        mode = sm.determine_mode()
    """

    def __init__(self) -> None:
        self.state = SystemState()

    # ------------------------------------------------------------------
    # Update methods
    # ------------------------------------------------------------------

    def update_presence(self, user_present: bool) -> None:
        self.state.user_present = user_present
        if not user_present:
            self.state.conversation_active = False

    def update_conversation(self, active: bool) -> None:
        self.state.conversation_active = active
        if active:
            self.state.inactive_minutes = 0
            self.state.last_insight_given = False

    def update_inactive_minutes(self, minutes: int) -> None:
        self.state.inactive_minutes = max(0, minutes)
        self.state.dream_eligible = (
            self.state.inactive_minutes >= DREAM_THRESHOLD_MINUTES
        )

    def update_emotion_intensity(self, intensity: float) -> None:
        self.state.emotional_intensity = max(0.0, min(1.0, intensity))

    def update_resource_load(self, load: str) -> None:
        """load: 'low' | 'medium' | 'high'"""
        if load in ("low", "medium", "high"):
            self.state.resource_load = load

    def set_active_entity(self, entity: str) -> None:
        """Switch primary active character: 'kira' or 'lisa'"""
        self.state.active_entity = entity.lower()

    def mark_insight_given(self) -> None:
        """Called by insight_engine after surfacing an insight."""
        self.state.last_insight_given = True

    # ------------------------------------------------------------------
    # Mode determination
    # ------------------------------------------------------------------

    def determine_mode(self) -> str:
        """
        Evaluates current state and returns the correct system mode.
        This is the central routing decision for all other systems.

        Mode priority order:
          1. active_conversation (highest priority)
          2. quiet_presence (user present, no active chat)
          3. sleep_dream (extended idle, low resources)
          4. idle_thought (inactive but not long enough for dream)
          5. user_away (user absent)
        """
        if self.state.conversation_active and self.state.user_present:
            self.state.mode = "active_conversation"

        elif self.state.user_present and not self.state.conversation_active:
            self.state.mode = "quiet_presence"

        elif not self.state.user_present and self.state.dream_eligible:
            if self.state.resource_load == "low":
                self.state.mode = "sleep_dream"
            else:
                # Resource load too high for dream — fall back to idle
                self.state.mode = "idle_thought"

        elif not self.state.user_present and (
            self.state.inactive_minutes >= IDLE_THRESHOLD_MINUTES
        ):
            self.state.mode = "idle_thought"

        elif not self.state.user_present:
            self.state.mode = "user_away"

        else:
            self.state.mode = "quiet_presence"

        return self.state.mode

    # ------------------------------------------------------------------
    # System permission gates
    # ------------------------------------------------------------------

    def is_allowed(self, system_name: str) -> bool:
        """
        Returns True if the named system is permitted to run in the current mode.
        Augment Code should call this before activating any subsystem.

        Per STATE_MANAGER_v1.pdf allowed/blocked rules per mode.
        Post-GPU systems always return False until unlocked externally.
        """
        mode = self.state.mode

        # Post-GPU systems — always blocked in Phase 1
        POST_GPU_SYSTEMS = {
            "avatar_builder",
            "world_builder",
            "movement_embodiment",
            "advanced_perception",
        }
        if system_name in POST_GPU_SYSTEMS:
            return False

        rules: Dict[str, Dict[str, bool]] = {
            "active_conversation": {
                "conversation_loop": True,
                "memory_manager": True,
                "emotion_system": True,
                "relationship_system": True,
                "insight_trigger": True,   # limited
                "idle_thought": False,
                "dream_system": False,
                "state_manager": True,
            },
            "quiet_presence": {
                "conversation_loop": False,
                "memory_manager": True,    # light association
                "emotion_system": True,
                "relationship_system": False,
                "insight_trigger": False,
                "idle_thought": True,      # light only
                "dream_system": False,
                "state_manager": True,
            },
            "idle_thought": {
                "conversation_loop": False,
                "memory_manager": True,
                "emotion_system": True,
                "relationship_system": False,
                "insight_trigger": False,
                "idle_thought": True,
                "dream_system": False,
                "state_manager": True,
            },
            "sleep_dream": {
                "conversation_loop": False,
                "memory_manager": True,
                "emotion_system": True,
                "relationship_system": False,
                "insight_trigger": False,
                "idle_thought": False,
                "dream_system": True,
                "state_manager": True,
            },
            "user_away": {
                "conversation_loop": False,
                "memory_manager": True,
                "emotion_system": True,
                "relationship_system": False,
                "insight_trigger": False,
                "idle_thought": True,
                "dream_system": self.state.dream_eligible,
                "state_manager": True,
            },
        }

        mode_rules = rules.get(mode, {})
        return mode_rules.get(system_name, False)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, object]:
        return asdict(self.state)

    def get_mode(self) -> str:
        return self.state.mode
