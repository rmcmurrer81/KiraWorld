"""
Simulate a mic/webcam cue packet through the pre-GPU perception gateway.

This does not open real devices.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from perception_gateway import PerceptionGateway  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a perception event.")
    parser.add_argument("session_id")
    parser.add_argument("--phone", action="store_true")
    parser.add_argument("--tv", action="store_true")
    parser.add_argument("--visitor", action="store_true")
    parser.add_argument("--robert", action="store_true")
    parser.add_argument("--addressed-ai", action="store_true")
    parser.add_argument("--music", action="store_true")
    parser.add_argument("--adult-private", action="store_true")
    parser.add_argument("--confidence", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--relationship-stage", default="friendship")
    parser.add_argument("--unspoken-feeling", action="store_true")
    args = parser.parse_args()

    cues = {
        "phone_audio_detected": args.phone,
        "living_room_tv_detected": args.tv,
        "visitor_voice_detected": args.visitor,
        "robert_voice_match": args.robert,
        "addressed_ai": args.addressed_ai,
        "music_detected": args.music,
        "adult_private_audio_detected": args.adult_private,
        "dialogue_detected": args.tv,
        "confidence_hint": args.confidence,
    }
    gateway = PerceptionGateway()
    event = gateway.process_cues(
        args.session_id,
        cues,
        relationship_stage=args.relationship_stage,
        unspoken_feeling_possible=args.unspoken_feeling,
    )
    print(json.dumps(event, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
