"""Run a Kira/Robert text meeting, then render a real-voice listening WAV.

This is intentionally unattended: Robert can start it, leave it alone, and
come back to a transcript plus a Chatterbox audio file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.dialogue_privacy import build_spoken_only_export
from tools.prepare_dialogue_speech_export_20260715 import _immutable_json_artifact
DIALOGUE_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_robert_intro"


def gain_label(value: float) -> str:
    rounded = int(value) if float(value).is_integer() else value
    text = str(rounded).replace("-", "minus").replace(".", "p")
    return f"{text}db"


def newest_dialogue_json(start_time: float) -> Path | None:
    candidates = []
    for path in DIALOGUE_DIR.glob("kira_robert_*.json"):
        if path.stat().st_mtime >= start_time:
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def run_checked(command: list[str]) -> None:
    print(" ".join(command))
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run weekly Kira/Robert meeting and render audio afterward.")
    parser.add_argument("--duration-minutes", type=float, default=60.0)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--max-turns", type=int, default=0, help="Safety cap; 0 follows the duration target without a turn cap.")
    parser.add_argument("--turn-delay-seconds", type=float, default=15.0)
    parser.add_argument("--chunk-chars", type=int, default=180)
    parser.add_argument("--chunk-max-attempts", type=int, default=2)
    parser.add_argument("--min-seconds-per-word", type=float, default=0.18)
    parser.add_argument("--robert-gain-db", type=float, default=-9.0)
    parser.add_argument("--robert-proximity-cut-hz", type=float, default=95.0)
    parser.add_argument("--robert-proximity-cut-mix", type=float, default=0.30)
    parser.add_argument("--kira-gain-db", type=float, default=0.0)
    parser.add_argument("--skip-audio", action="store_true")
    args = parser.parse_args()

    start_time = time.time() - 1
    run_checked(
        [
            sys.executable,
            "tools/run_kira_robert_intro_dialogue_20260714.py",
            "--meeting-kind",
            "weekly",
            "--duration-minutes",
            str(args.duration_minutes),
            "--model",
            args.model,
            "--max-turns",
            str(args.max_turns),
            "--turn-delay-seconds",
            str(args.turn_delay_seconds),
        ]
    )

    dialogue_json = newest_dialogue_json(start_time)
    if dialogue_json is None:
        print("No new Kira/Robert dialogue JSON was found.", file=sys.stderr)
        return 2
    print(f"Dialogue complete: {dialogue_json}")

    dialogue_data = json.loads(dialogue_json.read_text(encoding="utf-8-sig"))
    if dialogue_data.get("status") != "complete" or not dialogue_data.get("target_reached"):
        print("Dialogue did not reach its requested duration; audio render is blocked.", file=sys.stderr)
        return 3

    speech_export = build_spoken_only_export(dialogue_data, source_path=dialogue_json)
    speech_export_dir = DIALOGUE_DIR / "speech_exports"
    speech_export_dir.mkdir(parents=True, exist_ok=True)
    speech_export_path, speech_export_sha256 = _immutable_json_artifact(
        speech_export_dir,
        artifact_stem=f"{dialogue_json.stem}_spoken_only_privacy_checked",
        value=speech_export,
    )
    print(f"Privacy-safe immutable speech export: {speech_export_path} ({speech_export_sha256})")

    if args.skip_audio:
        return 0

    run_checked(
        [
            sys.executable,
            "tools/render_dialogue_chatterbox_audio_20260715.py",
            str(speech_export_path),
            "--output-label",
            f"weekly_no_names_robert_{gain_label(args.robert_gain_db)}",
            "--chunk-chars",
            str(args.chunk_chars),
            "--chunk-max-attempts",
            str(args.chunk_max_attempts),
            "--min-seconds-per-word",
            str(args.min_seconds_per_word),
            "--max-chars-per-turn",
            "0",
            "--robert-gain-db",
            str(args.robert_gain_db),
            "--robert-proximity-cut-hz",
            str(args.robert_proximity_cut_hz),
            "--robert-proximity-cut-mix",
            str(args.robert_proximity_cut_mix),
            "--kira-gain-db",
            str(args.kira_gain_db),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
