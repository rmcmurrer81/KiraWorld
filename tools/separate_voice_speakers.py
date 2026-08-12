"""Create reviewable speaker folders from an existing voice reference pack."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.voice_speaker_separation import separate_reference_pack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    parser.add_argument("--clusters", type=int, default=None)
    args = parser.parse_args()
    result = separate_reference_pack(args.pack, args.clusters)
    print(json.dumps({"pack_id": result["pack_id"], "speaker_labels": result["speaker_labels"], "clip_count": len(result["clips"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
