#!/usr/bin/env python3
"""Rank every bounded clip in a voice pack against one confirmed anchor."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_speaker_consistency import (  # noqa: E402
    BoundedWav,
    ConsistencyEvidenceError,
    WavLMSpeakerEmbedder,
    analyze_speaker_consistency,
)


def _project_file(value: str, *, field: str) -> Path:
    path = Path(value)
    resolved = (PROJECT_ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must stay inside the Kira project.") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise FileNotFoundError(f"{field} is not a regular file: {resolved}")
    return resolved


def load_pack_candidates(manifest_path: Path) -> tuple[dict[str, Any], list[BoundedWav]]:
    manifest_path = _project_file(str(manifest_path), field="pack manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Pack manifest must be a JSON object.")
    pack_id = str(manifest.get("pack_id") or "").strip()
    clips = manifest.get("audio", {}).get("clips", [])
    if not pack_id or not isinstance(clips, list) or not clips:
        raise ValueError("Pack manifest needs a pack_id and non-empty audio.clips list.")
    if len(clips) > 500:
        raise ValueError("Pack comparison is bounded to at most 500 clips.")
    source_hash = str(manifest.get("source", {}).get("sha256") or "")
    candidates: list[BoundedWav] = []
    for number, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            raise ValueError(f"Clip {number} is not a JSON object.")
        clip_id = str(clip.get("clip_id") or f"clip_{number:04d}").strip()
        path = _project_file(str(clip.get("path") or ""), field=f"{clip_id} path")
        candidates.append(
            BoundedWav(
                path=path,
                source_id=f"{pack_id}::{clip_id}",
                range_id=clip_id,
                source_start_seconds=clip.get("start_seconds"),
                source_end_seconds=clip.get("end_seconds"),
                source_media_sha256=source_hash,
            )
        )
    return manifest, candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare all bounded WAV clips in one pack to a confirmed target-only anchor. "
            "Scores are same-speaker consistency evidence, not identity approval."
        )
    )
    parser.add_argument("--anchor-wav", type=Path, required=True)
    parser.add_argument("--anchor-source-id", required=True)
    parser.add_argument("--owner-confirmed-anchor", action="store_true")
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-id", default="microsoft/wavlm-base-plus-sv")
    parser.add_argument("--model-revision", default="main")
    parser.add_argument("--device", default="cpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.owner_confirmed_anchor:
        build_parser().error("--owner-confirmed-anchor is required")
    try:
        manifest, candidates = load_pack_candidates(args.pack_manifest)
        result = analyze_speaker_consistency(
            anchor=BoundedWav(
                path=_project_file(str(args.anchor_wav), field="anchor WAV"),
                source_id=args.anchor_source_id,
                range_id="owner_confirmed_anchor",
                owner_confirmed_target_only=True,
            ),
            candidates=candidates,
            backend=WavLMSpeakerEmbedder(
                model_id=args.model_id,
                revision=args.model_revision,
                device=args.device,
            ),
            output_path=args.output,
        )
    except (ConsistencyEvidenceError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed_closed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    computed = [
        item for item in result["candidates"]
        if item.get("consistency_evidence", {}).get("status") == "computed"
    ]
    ranked = sorted(
        computed,
        key=lambda item: item["consistency_evidence"]["median_cosine_similarity"],
        reverse=True,
    )
    summary = {
        "status": "pack_ranked_same_speaker_consistency_not_identity_proof",
        "pack_id": manifest["pack_id"],
        "candidate_count": len(candidates),
        "computed_count": len(computed),
        "rejected_before_embedding": len(candidates) - len(computed),
        "supported_count": sum(
            item["consistency_evidence"]["decision"]
            == "speaker_consistency_supported_not_identity_proof"
            for item in computed
        ),
        "top_candidates": [
            {
                "clip_id": item["range_id"],
                "start_seconds": item.get("source_start_seconds"),
                "end_seconds": item.get("source_end_seconds"),
                "median_cosine_similarity": item["consistency_evidence"]["median_cosine_similarity"],
                "decision": item["consistency_evidence"]["decision"],
            }
            for item in ranked[:12]
        ],
        "output": str(args.output.resolve()),
        "music_or_score_screening_performed": False,
        "clean_spoken_source_approved": False,
        "requires_separate_transcript_audiovisual_and_contamination_gate": True,
        "identity_approved": False,
        "voice_assigned": False,
        "candidate_activated": False,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
