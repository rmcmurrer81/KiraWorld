"""Write fixed, candidate-confined local voice-source review artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_local_voice_source_review import (  # noqa: E402
    build_clean_range_review_queue,
    build_local_voice_source_review_manifest,
)
from Core.temp_ai_voice_discovery import load_or_create_request, resolve_candidate_dir  # noqa: E402


def _write_fixed(path: Path, payload: dict) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing to overwrite symlink output: {path}")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit user-authorized Data/library voice leads without extraction, playback, voice generation, or activation."
    )
    parser.add_argument("--candidate-id", required=True)
    args = parser.parse_args()
    request_path, request = load_or_create_request(args.candidate_id)
    candidate_dir = resolve_candidate_dir(args.candidate_id)
    manifest = build_local_voice_source_review_manifest(request)
    queue = build_clean_range_review_queue(manifest)
    manifest_path = candidate_dir / "local_voice_source_evidence_manifest.json"
    queue_path = candidate_dir / "clean_range_review_queue.json"
    _write_fixed(manifest_path, manifest)
    _write_fixed(queue_path, queue)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "candidate_id": args.candidate_id,
                "request": str(request_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "source_count": len(manifest["sources"]),
                "highest_ranked_source_id": manifest["selection"]["highest_ranked_source_id"],
                "evidence_manifest": str(manifest_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "clean_range_review_queue": str(queue_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "audio_played": False,
                "audio_extracted": False,
                "voice_generated_or_assigned": False,
                "candidate_activated": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

