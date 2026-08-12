"""Validate one generated WAV and write a non-playing privacy disposition."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.dialogue_audio_review import review_dialogue_wav


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_json", type=Path)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source_path = _resolve(args.source_json)
    wav_path = _resolve(args.wav)
    manifest_path = _resolve(args.manifest) if args.manifest else None
    source_data = json.loads(source_path.read_text(encoding="utf-8-sig"))
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if manifest_path and manifest_path.exists()
        else None
    )
    report = review_dialogue_wav(
        source_path=source_path,
        source_data=source_data,
        wav_path=wav_path,
        manifest=manifest,
    )
    report["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    report["manifest_path"] = str(manifest_path) if manifest_path else None

    output = _resolve(args.output) if args.output else wav_path.with_name(
        wav_path.stem + "_privacy_disposition.json"
    )
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "status": report["status"]}, indent=2))
    return 0 if report["status"] == "manifest_bound_listening_copy_not_acoustically_verified" else 4


if __name__ == "__main__":
    raise SystemExit(main())
