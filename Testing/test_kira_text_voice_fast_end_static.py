from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "kira_world_shell_server.py"


def test_text_voice_end_skips_irrelevant_avatar_snapshot_wait() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    guard = "if (!state.text_voice_mode && state.active_has_body) {{"
    assert text.count(guard) >= 2
    assert "Text/voice launchers deliberately load no world or avatar." in text
    assert "made the owner's stop control appear" in text
    assert 'await api("/api/deactivate", {{}});' in text
    assert 'await api("/api/safe-close", {{ reason: "Robert clicked Close Safely" }});' in text


def test_end_control_keeps_primary_pointer_and_click_fallback() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert 'deactivateButton.addEventListener("pointerup", deactivateActiveCandidate)' in text
    assert 'deactivateButton.addEventListener("click", deactivateActiveCandidate)' in text
    assert "if (deactivationInFlight || !state.active_candidate) return;" in text
    assert "End conversation now" in text
