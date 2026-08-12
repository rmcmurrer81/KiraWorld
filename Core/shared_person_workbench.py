"""Shared person workbenches and person-state-independent Studio policy."""
from __future__ import annotations

from pathlib import Path

PROTECTED_STANDALONE_STUDIO = (
    Path("VideoStudioDevelopment")
    / "chat_first_production"
    / "START_CHAT_FIRST_STUDIO.bat"
)


def standalone_video_studio_access(root: str | Path) -> dict[str, object]:
    """Authorize Studio without reading or changing any person/life-loop state."""

    project = Path(root)
    launcher = project / PROTECTED_STANDALONE_STUDIO
    if not launcher.is_file():
        return {
            "allowed": False,
            "reason": "protected_standalone_studio_launcher_missing",
            "person_state_inspected": False,
            "person_state_mutated": False,
            "lifecycle_action": "none",
        }
    return {
        "allowed": True,
        "mode": "standalone_owner_decision",
        "launcher": str(launcher),
        "person_id": None,
        "workbench": None,
        "person_state_inspected": False,
        "person_state_mutated": False,
        "lifecycle_action": "none",
        "publication_allowed": False,
        "automatic_publication": False,
        "automatic_person_studio_switching": False,
        "active_person_count_condition": False,
    }


def personal_workbench(root: str | Path, person_id: str) -> Path:
    project = Path(root)
    mapping = {
        "kira": project / "Data" / "core_ai_workbenches" / "kira",
        "lisa": project / "Data" / "core_ai_workbenches" / "lisa",
        "robert_mcmurrer_presence_ai": (
            project / "TemporaryAI" / "candidates" /
            "robert_mcmurrer_presence_ai" / "workbench"
        ),
    }
    if person_id not in mapping:
        raise PermissionError("No shared personal workbench is authorized for this person")
    return mapping[person_id]


def video_studio_access(root: str | Path, *, active_person: object = None,
                        requested_person: str = "",
                        active_people: object = None) -> dict[str, object]:
    """Compatibility wrapper for the superseded person-bound access call.

    All person inputs are deliberately ignored. Robert decides whether to open
    the protected standalone Studio, independently of person count or state.
    """

    result = standalone_video_studio_access(root)
    return {
        **result,
        "legacy_person_bound_access_superseded": True,
        "requested_person_ignored": str(requested_person or "").strip() or None,
        "active_person_input_ignored": active_person is not None,
        "active_people_input_ignored": active_people is not None,
        "person_context_attached": False,
    }
