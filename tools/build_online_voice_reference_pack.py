"""CLI for online video voice-reference packs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.voice_online_reference import build_online_audio_pack, find_reference_by_url, link_saved_online_reference


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build a reviewable online voice-reference pack.")
    result.add_argument("--target-name", required=True)
    result.add_argument("--target-id", required=True)
    result.add_argument("--url", required=True)
    result.add_argument("--version", default="")
    result.add_argument("--script", default="")
    result.add_argument("--authorization-status", default="review_required")
    result.add_argument("--reference-dir", default="")
    result.add_argument("--link-only", action="store_true", help="Save captions/style/thumbnail without downloading audio.")
    return result


def main() -> int:
    args = parser().parse_args()
    saved = Path(args.reference_dir).resolve() if args.reference_dir else find_reference_by_url(args.url)
    try:
        if args.link_only:
            if not saved:
                raise FileNotFoundError("No saved TemporaryAI video reference matched this URL.")
            record = link_saved_online_reference(
                target_name=args.target_name,
                target_id=args.target_id,
                form_or_version=args.version,
                reference_dir=saved,
            )
        else:
            record = build_online_audio_pack(
                target_name=args.target_name,
                target_id=args.target_id,
                url=args.url,
                form_or_version=args.version,
                script_path=Path(args.script).resolve() if args.script else None,
                authorization_status=args.authorization_status,
                saved_reference_dir=saved,
            )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    summary = {
        "pack_id": record.get("pack_id"),
        "pack_dir": record.get("pack_dir"),
        "source_kind": record.get("source", {}).get("kind"),
        "candidate_clip_count": record.get("audio", {}).get("candidate_clip_count", 0),
        "model_ready": record.get("model_readiness", {}).get("eligible", False),
        "next": "Review target-only clips before any voice-model preparation.",
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
