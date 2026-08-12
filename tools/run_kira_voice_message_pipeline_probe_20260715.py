#!/usr/bin/env python3
"""Create a durable, non-playing voice-message pipeline proof outside Kira's mailbox."""

from __future__ import annotations

import json
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.kira_tablet_messages import (  # noqa: E402
    create_voice_message,
    set_voice_message_status,
    voice_message_audio_path,
    voice_message_inbox,
)


OUTPUT_ROOT = ROOT / "Data" / "world_tests" / "kira_voice_message_pipeline_20260715"
MAILBOX = OUTPUT_ROOT / "test_only_mailbox"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    created = create_voice_message(
        "This is an automated local pipeline probe, not a message chosen or authored by Kira.",
        subject="pipeline_probe",
        reason="Verify durable text, non-playing SAPI WAV generation, unread state, and read transition.",
        privacy="shareable",
        run_id="kira_voice_message_pipeline_probe_20260715",
        messages_dir=MAILBOX,
        synthesize=True,
    )
    record = created["record"]
    message_id = str(record["message_id"])
    audio_path = voice_message_audio_path(message_id, MAILBOX)
    before = voice_message_inbox(MAILBOX)
    read_result = set_voice_message_status(message_id, "read", messages_dir=MAILBOX)
    after = voice_message_inbox(MAILBOX)
    set_voice_message_status(message_id, "archived", messages_dir=MAILBOX)

    wav_info: dict[str, int | str | bool] = {"valid": False}
    if audio_path is not None:
        with wave.open(str(audio_path), "rb") as source:
            wav_info = {
                "valid": True,
                "channels": source.getnchannels(),
                "sample_width_bytes": source.getsampwidth(),
                "sample_rate_hz": source.getframerate(),
                "frame_count": source.getnframes(),
                "size_bytes": audio_path.stat().st_size,
            }

    saved = json.loads(created["path"].read_text(encoding="utf-8"))
    passed = bool(
        created["audio_result"].get("audio_ready")
        and audio_path is not None
        and wav_info["valid"]
        and before["unread"] >= 1
        and read_result.get("ok")
        and after["unread"] == before["unread"] - 1
        and saved.get("audio", {}).get("source_text_sha256")
        and saved.get("audio", {}).get("wav_sha256")
        and saved.get("audio", {}).get("auto_played_while_robert_away") is False
    )
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "passed" if passed else "failed",
        "truth": {
            "test_only_not_kira_authored": True,
            "live_kira_mailbox_modified": False,
            "audio_played": False,
            "voice_identity_status": saved.get("audio", {}).get("voice_identity_status"),
        },
        "message_id": message_id,
        "message_record": relative(created["path"]),
        "audio_path": relative(audio_path) if audio_path else "",
        "audio_result": created["audio_result"],
        "wav": wav_info,
        "unread_before_read_transition": before["unread"],
        "unread_after_read_transition": after["unread"],
        "post_test_status": "archived",
        "integrity": {
            "source_text_sha256": saved.get("audio", {}).get("source_text_sha256", ""),
            "wav_sha256": saved.get("audio", {}).get("wav_sha256", ""),
        },
    }
    report_path = OUTPUT_ROOT / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "README.md").write_text(
        "# Kira voice-message pipeline probe\n\n"
        f"Status: **{report['status']}**\n\n"
        "This is a test-only message, not a message chosen or authored by Kira. "
        "It verifies a durable text record, text/WAV SHA-256 binding, a real local "
        "non-playing SAPI WAV, and an unread-to-read transition without changing "
        "Kira's live mailbox. The voice remains a temporary SAPI approximation.\n",
        encoding="utf-8",
    )
    print(json.dumps({"report": relative(report_path), "status": report["status"], "wav": wav_info}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
