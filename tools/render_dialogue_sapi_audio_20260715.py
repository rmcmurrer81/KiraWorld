"""Render a saved dialogue transcript to a single Windows SAPI WAV draft.

This is a listening draft, not final voice cloning. It uses installed Windows
voices so Robert can review long text without eye strain while reviewed neural
voice references are still being prepared.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.dialogue_privacy import DialoguePrivacyError, prepare_dialogue_speech_turns
from Core.artifact_binding import (
    bind_artifact_hashes,
    canonical_json_sha256,
    sha256_file,
)


def _clean_for_speech(text: str, max_chars: int) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"[*_#>~]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if max_chars > 0 and len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "."
    return cleaned


def _load_turns(path: Path, last_turns: int, max_chars: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    prepared, audit = prepare_dialogue_speech_turns(data, last_turns=last_turns, max_chars=max_chars)
    turns: list[dict[str, str]] = []
    for item in prepared:
        text = _clean_for_speech(str(item["text"]), max_chars=0)
        if text:
            turns.append({"speaker": str(item["speaker"]), "text": text})
    return turns, audit


def _write_powershell_renderer(path: Path) -> None:
    path.write_text(
        r"""
param(
  [Parameter(Mandatory=$true)][string]$PayloadPath,
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [Parameter(Mandatory=$true)][string]$KiraVoice,
  [Parameter(Mandatory=$true)][string]$RobertVoice
)

Add-Type -AssemblyName System.Speech
$items = Get-Content -LiteralPath $PayloadPath -Raw -Encoding UTF8 | ConvertFrom-Json
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SetOutputToWaveFile($OutputPath)

foreach ($item in $items) {
  $name = [string]$item.speaker
  $voice = $RobertVoice
  $rate = 0
  $volume = 95
  if ($name -eq "Kira") {
    $voice = $KiraVoice
    $rate = -1
    $volume = 92
  }
  $speaker.SelectVoice($voice)
  $speaker.Rate = $rate
  $speaker.Volume = $volume
  $speaker.Speak($name + ".")
  $speaker.Speak([string]$item.text)
  $speaker.Speak(" ")
}

$speaker.SetOutputToNull()
$speaker.Dispose()
""".strip()
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render dialogue JSON to a SAPI WAV listening draft.")
    parser.add_argument("dialogue_json", type=Path)
    parser.add_argument("--last-turns", type=int, default=0, help="Render only the last N turns. 0 means all.")
    parser.add_argument("--max-chars-per-turn", type=int, default=900)
    parser.add_argument("--kira-voice", default="Microsoft Zira Desktop")
    parser.add_argument("--robert-voice", default="Microsoft David Desktop")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "Data" / "dialogues" / "kira_robert_intro" / "audio")
    args = parser.parse_args()

    dialogue_path = args.dialogue_json
    if not dialogue_path.is_absolute():
        dialogue_path = PROJECT_ROOT / dialogue_path
    if not dialogue_path.exists():
        print(f"Missing dialogue JSON: {dialogue_path}", file=sys.stderr)
        return 2

    try:
        turns, privacy_audit = _load_turns(
            dialogue_path,
            last_turns=args.last_turns,
            max_chars=args.max_chars_per_turn,
        )
    except DialoguePrivacyError as exc:
        print(f"Privacy gate blocked TTS: {exc}", file=sys.stderr)
        return 3
    if not turns:
        print("No spoken turns found.", file=sys.stderr)
        return 3

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = dialogue_path.stem
    suffix = "full" if args.last_turns <= 0 else f"last_{args.last_turns}_turns"
    output_wav = output_dir / f"{stem}_{suffix}_sapi_listening_draft.wav"
    payload_path = output_dir / f"{stem}_{suffix}_sapi_payload.json"
    ps1_path = output_dir / "render_sapi_dialogue.ps1"
    manifest_path = output_dir / f"{stem}_{suffix}_sapi_listening_draft_manifest.json"

    payload_path.write_text(json.dumps(turns, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_powershell_renderer(ps1_path)

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps1_path),
            "-PayloadPath",
            str(payload_path),
            "-OutputPath",
            str(output_wav),
            "-KiraVoice",
            args.kira_voice,
            "-RobertVoice",
            args.robert_voice,
        ],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=900,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stderr.strip(), file=sys.stderr)
        return completed.returncode or 1

    source_sha256 = sha256_file(dialogue_path)
    payload_sha256 = sha256_file(payload_path)
    wav_sha256 = sha256_file(output_wav)
    voice_configuration_sha256 = canonical_json_sha256(
        {"kira_voice": args.kira_voice, "robert_voice": args.robert_voice}
    )
    artifact_binding = bind_artifact_hashes(
        {
            "source_dialogue": source_sha256,
            "speech_payload_file": payload_sha256,
            "spoken_payload": privacy_audit["spoken_payload_sha256"],
            "voice_configuration": voice_configuration_sha256,
            "output_wav": wav_sha256,
        },
        metadata={
            "voice_mode": "windows_sapi_listening_draft",
            "turn_count": len(turns),
            "last_turns": args.last_turns,
            "max_chars_per_turn": args.max_chars_per_turn,
        },
    )
    manifest: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dialogue_json": str(dialogue_path.relative_to(PROJECT_ROOT)),
        "source_dialogue_sha256": source_sha256,
        "audio_path": str(output_wav.relative_to(PROJECT_ROOT)),
        "payload_path": str(payload_path.relative_to(PROJECT_ROOT)),
        "payload_sha256": payload_sha256,
        "turn_count": len(turns),
        "last_turns": args.last_turns,
        "max_chars_per_turn": args.max_chars_per_turn,
        "voice_mode": "windows_sapi_listening_draft",
        "kira_voice": args.kira_voice,
        "robert_voice": args.robert_voice,
        "not_final_voice_clone": True,
        "privacy_audit": privacy_audit,
        "private_channels_spoken": False,
        "wav_sha256": wav_sha256,
        "voice_configuration_sha256": voice_configuration_sha256,
        "artifact_binding": artifact_binding,
        "note": (
            "Robert's reviewed approved_reference.wav is not ready yet. "
            "This file is for easier listening only and should be replaced by "
            "a final Kira/Robert voice render later."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
