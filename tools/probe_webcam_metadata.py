"""
Probe or simulate webcam metadata and route it through perception.

Real capture requires optional `opencv-python` and an active permissioned
perception session. Raw frames are not stored.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from perception_gateway import PerceptionGateway  # noqa: E402
from webcam_metadata_adapter import analyze_frame_metadata, capture_webcam_metadata  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe webcam metadata.")
    parser.add_argument("session_id")
    parser.add_argument("--real", action="store_true", help="Attempt optional real webcam metadata capture.")
    parser.add_argument("--brightness", type=float, default=0.0)
    parser.add_argument("--motion", type=float, default=0.0)
    parser.add_argument("--person", type=float, default=0.0)
    parser.add_argument("--robert", type=float, default=0.0)
    parser.add_argument("--other-person", type=float, default=0.0)
    parser.add_argument("--phone-visible", type=float, default=0.0)
    parser.add_argument("--screen-visible", type=float, default=0.0)
    args = parser.parse_args()

    if args.real:
        metadata = capture_webcam_metadata()
        if not metadata.get("available"):
            print(json.dumps(metadata, indent=2, ensure_ascii=False))
            return
        brightness = float(metadata.get("brightness", 0.0))
    else:
        brightness = args.brightness

    cues = analyze_frame_metadata(
        brightness=brightness,
        motion_score=args.motion,
        person_probability=args.person,
        robert_face_probability=args.robert,
        other_person_probability=args.other_person,
        phone_visible_probability=args.phone_visible,
        screen_visible_probability=args.screen_visible,
    )
    event = PerceptionGateway().process_cues(args.session_id, cues)
    print(json.dumps({"cues": cues, "attention_event": event}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
