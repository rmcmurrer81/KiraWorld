"""Hardware-aware capacity policy for Kira World group conversations.

The policy is intentionally pure.  It never starts a model, activates a
person, creates a body, or writes runtime state.  Callers must still perform
the normal per-person activation checks and keep each person's state keyed by
their exact candidate id.
"""

from __future__ import annotations

import ctypes
import math
import os
from dataclasses import asdict, dataclass
from typing import Mapping


DEFAULT_MAX_ACTIVE_SESSIONS = 1
DEFAULT_RAM_GB_PER_SESSION = 32.0
HARD_MAX_ACTIVE_SESSIONS = 8
GROUP_OPT_IN_ENV = "KIRA_WORLD_GROUP_SESSIONS"
MAX_ACTIVE_SESSIONS_ENV = "KIRA_WORLD_MAX_ACTIVE_SESSIONS"
RAM_GB_PER_SESSION_ENV = "KIRA_WORLD_RAM_GB_PER_ACTIVE_SESSION"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True)
class WorldShellSessionPolicy:
    """Resolved, fail-closed capacity for one shell process."""

    group_opt_in: bool
    requested_max_active_sessions: int
    hardware_max_active_sessions: int
    effective_max_active_sessions: int
    detected_ram_gb: float | None
    ram_gb_per_active_session: float
    hard_max_active_sessions: int
    capacity_source: str
    reason: str

    @property
    def group_sessions_enabled(self) -> bool:
        return self.group_opt_in and self.effective_max_active_sessions > 1

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["group_sessions_enabled"] = self.group_sessions_enabled
        result["default_max_active_sessions"] = DEFAULT_MAX_ACTIVE_SESSIONS
        result["activation_performed"] = False
        return result


def _physical_ram_bytes() -> int | None:
    """Return installed physical RAM without introducing a psutil dependency."""

    if os.name == "nt":
        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except (AttributeError, OSError):
            return None
        return None

    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        page_count = int(os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    total = page_size * page_count
    return total if total > 0 else None


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> tuple[int, bool]:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default, False
    if parsed < minimum or parsed > maximum:
        return default, False
    return parsed, True


def _bounded_float(
    value: object,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> tuple[float, bool]:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return default, False
    if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
        return default, False
    return parsed, True


def resolve_world_shell_session_policy(
    environ: Mapping[str, str] | None = None,
    *,
    total_ram_bytes: int | None = None,
) -> WorldShellSessionPolicy:
    """Resolve the group-session limit, defaulting to exactly one.

    RAM alone never enables group mode.  The operator must set both
    ``KIRA_WORLD_GROUP_SESSIONS=1`` and a requested maximum greater than one.
    Invalid or unavailable inputs fail closed to one active session.
    """

    env = os.environ if environ is None else environ
    group_opt_in = str(env.get(GROUP_OPT_IN_ENV, "")).strip().lower() in _TRUE_VALUES
    requested, requested_valid = _bounded_int(
        env.get(MAX_ACTIVE_SESSIONS_ENV, str(DEFAULT_MAX_ACTIVE_SESSIONS)),
        default=DEFAULT_MAX_ACTIVE_SESSIONS,
        minimum=DEFAULT_MAX_ACTIVE_SESSIONS,
        maximum=HARD_MAX_ACTIVE_SESSIONS,
    )
    per_session_ram, ram_budget_valid = _bounded_float(
        env.get(RAM_GB_PER_SESSION_ENV, str(DEFAULT_RAM_GB_PER_SESSION)),
        default=DEFAULT_RAM_GB_PER_SESSION,
        minimum=8.0,
        maximum=128.0,
    )

    measured_bytes = _physical_ram_bytes() if total_ram_bytes is None else total_ram_bytes
    if isinstance(measured_bytes, bool) or not isinstance(measured_bytes, int) or measured_bytes <= 0:
        detected_ram_gb = None
        hardware_max = DEFAULT_MAX_ACTIVE_SESSIONS
        capacity_source = "ram_unavailable_fail_closed"
    else:
        detected_ram_gb = round(measured_bytes / (1024**3), 2)
        hardware_max = max(
            DEFAULT_MAX_ACTIVE_SESSIONS,
            min(HARD_MAX_ACTIVE_SESSIONS, int(detected_ram_gb // per_session_ram)),
        )
        capacity_source = "installed_physical_ram"

    if not group_opt_in:
        effective = DEFAULT_MAX_ACTIVE_SESSIONS
        reason = "group_sessions_require_explicit_opt_in"
    elif not requested_valid or not ram_budget_valid:
        effective = DEFAULT_MAX_ACTIVE_SESSIONS
        reason = "invalid_capacity_configuration_fail_closed"
    elif requested <= DEFAULT_MAX_ACTIVE_SESSIONS:
        effective = DEFAULT_MAX_ACTIVE_SESSIONS
        reason = "requested_single_session"
    elif detected_ram_gb is None:
        effective = DEFAULT_MAX_ACTIVE_SESSIONS
        reason = "physical_ram_unavailable_fail_closed"
    else:
        effective = min(requested, hardware_max, HARD_MAX_ACTIVE_SESSIONS)
        reason = (
            "group_session_capacity_enabled"
            if effective > DEFAULT_MAX_ACTIVE_SESSIONS
            else "hardware_capacity_allows_only_one_session"
        )

    return WorldShellSessionPolicy(
        group_opt_in=group_opt_in,
        requested_max_active_sessions=requested,
        hardware_max_active_sessions=hardware_max,
        effective_max_active_sessions=effective,
        detected_ram_gb=detected_ram_gb,
        ram_gb_per_active_session=per_session_ram,
        hard_max_active_sessions=HARD_MAX_ACTIVE_SESSIONS,
        capacity_source=capacity_source,
        reason=reason,
    )


__all__ = [
    "DEFAULT_MAX_ACTIVE_SESSIONS",
    "DEFAULT_RAM_GB_PER_SESSION",
    "GROUP_OPT_IN_ENV",
    "HARD_MAX_ACTIVE_SESSIONS",
    "MAX_ACTIVE_SESSIONS_ENV",
    "RAM_GB_PER_SESSION_ENV",
    "WorldShellSessionPolicy",
    "resolve_world_shell_session_policy",
]
