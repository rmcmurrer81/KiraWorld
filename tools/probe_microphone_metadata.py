"""
Probe or simulate microphone metadata and route it through perception.

Real capture requires optional `sounddevice` and an active permissioned
perception session. Raw audio is not stored.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from microphone_metadata_adapter import analyze_audio_metadata, capture_microphone_metadata  # noqa: E402
from perception_gateway import PerceptionGateway  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe microphone metadata.")
    parser.add_argument("session_id")
    parser.add_argument("--real", action="store_true", help="Attempt optional real mic level capture.")
    parser.add_argument("--rms", type=float, default=0.0)
    parser.add_argument("--peak", type=float, default=0.0)
    parser.add_argument("--speech", type=float, default=0.0)
    parser.add_argument("--music", type=float, default=0.0)
    parser.add_argument("--adult-private", type=float, default=0.0)
    parser.add_argument("--robert", type=float, default=0.0)
    parser.add_argument("--visitor", type=float, default=0.0)
    parser.add_argument("--phone", type=float, default=0.0)
    parser.add_argument("--tv", type=float, default=0.0)
    parser.add_argument("--addressed-ai", type=float, default=0.0)
    args = parser.parse_args()

    if args.real:
        metadata = capture_microphone_metadata()
        if not metadata.get("available"):
            print(json.dumps(metadata, indent=2, ensure_ascii=False))
            return
        rms = float(metadata.get("rms_level", 0.0))
        peak = float(metadata.get("peak_level", 0.0))
    else:
        rms = args.rms
        peak = args.peak

    cues = analyze_audio_metadata(
        rms_level=rms,
        peak_level=peak,
        speech_probability=args.speech,
        music_probability=args.music,
        adult_private_probability=args.adult_private,
        robert_voice_probability=args.robert,
        visitor_voice_probability=args.visitor,
        phone_audio_probability=args.phone,
        tv_audio_probability=args.tv,
        addressed_ai_probability=args.addressed_ai,
    )
    event = PerceptionGateway().process_cues(args.session_id, cues)
    print(json.dumps({"cues": cues, "attention_event": event}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
