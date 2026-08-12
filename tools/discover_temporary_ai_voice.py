"""Create or refresh a metadata-only TemporaryAI voice discovery index."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_voice_discovery import (  # noqa: E402
    INDEX_FILENAME,
    load_or_create_request,
    project_relative,
    run_voice_discovery,
    validate_request,
    write_json,
)


RESERVED_CANDIDATE_FILENAMES = frozenset(
    {
        "activation_plan.json",
        "creation_request.json",
        "expanded_source_gather.json",
        "online_research_summary.json",
        "reliable_source_pack.json",
        "source_research_queue.json",
        "temporary_ai_profile.json",
        "voice_discovery_request.json",
    }
)
VOICE_INDEX_FILENAME_RE = re.compile(
    r"^voice_discovery_index(?:_[a-z0-9][a-z0-9_-]{0,80})?\.json$",
    re.IGNORECASE,
)


def resolve_safe_output_path(request_path: Path, output_name: str) -> Path:
    """Return a candidate-local voice-index path without following symlinks."""

    output_fragment = Path(output_name.strip())
    if (
        output_fragment.is_absolute()
        or len(output_fragment.parts) != 1
        or output_fragment.name in {"", ".", ".."}
    ):
        raise ValueError("--output must be one filename inside the candidate folder.")
    normalized_name = output_fragment.name.casefold()
    if normalized_name in RESERVED_CANDIDATE_FILENAMES:
        raise ValueError(f"--output cannot overwrite reserved candidate file: {output_fragment.name}")
    if not VOICE_INDEX_FILENAME_RE.fullmatch(output_fragment.name):
        raise ValueError(
            "--output must be voice_discovery_index.json or a versioned "
            "voice_discovery_index_<label>.json filename."
        )
    output_path = request_path.parent / output_fragment.name
    if output_path.is_symlink():
        raise ValueError("--output cannot be a symlink.")
    if output_path.exists() and not output_path.is_file():
        raise ValueError("--output must be a regular file path.")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Index candidate recordings and synthetic voice-model metadata for one "
            "TemporaryAI. This command never downloads media/model weights, extracts "
            "audio, clones a voice, generates speech, or activates the candidate."
        )
    )
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument(
        "--metadata-search",
        action="store_true",
        help="Query metadata providers. Media, audio, captions, thumbnails, datasets, and model weights remain excluded.",
    )
    parser.add_argument(
        "--request-only",
        action="store_true",
        help="Create/validate voice_discovery_request.json without running discovery.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional candidate-folder output filename. Absolute paths and parent traversal are rejected.",
    )
    args = parser.parse_args()

    try:
        request_path, request = load_or_create_request(args.candidate_id)
        validate_request(request, expected_candidate_id=args.candidate_id)
        if args.request_only:
            print(
                json.dumps(
                    {
                        "status": "request_ready_not_run",
                        "candidate_id": args.candidate_id,
                        "request": project_relative(request_path),
                        "media_downloaded": False,
                        "voice_generated": False,
                    },
                    indent=2,
                )
            )
            return 0

        output_name = args.output.strip() or INDEX_FILENAME
        output_path = resolve_safe_output_path(request_path, output_name)
        result = run_voice_discovery(request, metadata_search=args.metadata_search)
        write_json(output_path, result)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "candidate_id": result["candidate_id"],
                    "request": project_relative(request_path),
                    "output": project_relative(output_path),
                    "recording_candidates": len(result["recording_candidates"]),
                    "synthetic_model_candidates": len(result["synthetic_model_candidates"]),
                    "recommended_lane": result["selection"]["recommended_lane"],
                    "provider_errors": result["provider_errors"],
                    "media_downloaded": False,
                    "model_downloaded": False,
                    "voice_generated": False,
                    "candidate_activated": False,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(f"VOICE DISCOVERY BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
