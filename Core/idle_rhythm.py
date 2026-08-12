"""
Fuzzy idle rhythm for chat runners.

Human waiting is uneven: sometimes someone waits at the conversation, sometimes
they get restless quickly, and sometimes they drift into something else later.
This module gives the lightweight chat runners that kind of explainable
variation without using a model call.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass
class IdleRhythm:
    min_seconds: int = field(default_factory=lambda: _env_int("KIRA_IDLE_MIN_SECONDS", 90))
    max_seconds: int = field(default_factory=lambda: _env_int("KIRA_IDLE_MAX_SECONDS", 480))
    quick_shift_chance: float = 0.2
    wait_longer_chance: float = 0.35
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        if self.min_seconds < 1:
            self.min_seconds = 1
        if self.max_seconds < self.min_seconds:
            self.max_seconds = self.min_seconds
        self._last_reason = "initial_wait"

    @property
    def last_reason(self) -> str:
        return self._last_reason

    def next_wait_seconds(self) -> int:
        roll = self.rng.random()
        span = self.max_seconds - self.min_seconds
        if span <= 0:
            self._last_reason = "fixed_by_configuration"
            return self.min_seconds

        if roll < self.quick_shift_chance:
            upper = self.min_seconds + max(1, span // 4)
            self._last_reason = "restless_quick_shift"
            return self.rng.randint(self.min_seconds, upper)
        if roll < self.quick_shift_chance + self.wait_longer_chance:
            lower = self.min_seconds + max(1, span // 2)
            self._last_reason = "settled_waiting_longer"
            return self.rng.randint(lower, self.max_seconds)

        lower = self.min_seconds + max(1, span // 4)
        upper = self.min_seconds + max(1, (span * 3) // 4)
        self._last_reason = "ordinary_idle_drift"
        return self.rng.randint(lower, upper)
