"""Capability check and explicit bounded-WAV consistency evidence CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_speaker_consistency import (  # noqa: E402
    BoundedWav,
    ConsistencyEvidenceError,
    WavLMSpeakerEmbedder,
    analyze_speaker_consistency,
    capability_report,
)


def _candidate(value: str) -> tuple[str, Path]:
    source_id, separator, path = value.partition("=")
    if not separator or not source_id.strip() or not path.strip():
        raise argparse.ArgumentTypeError("Use SOURCE_ID=PATH for each candidate.")
    return source_id.strip(), Path(path.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare bounded WAVs across recordings. Output is consistency evidence only; "
            "it never identifies, clones, assigns, or activates anyone."
        )
    )
    parser.add_argument("--capability", action="store_true", help="Check dependencies/cache only.")
    parser.add_argument("--anchor-wav", type=Path)
    parser.add_argument("--anchor-source-id", default="")
    parser.add_argument(
        "--owner-confirmed-anchor",
        action="store_true",
        help="Required attestation that the bounded anchor contains only the target speaker.",
    )
    parser.add_argument(
        "--candidate", action="append", type=_candidate, default=[], metavar="SOURCE_ID=PATH"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--presegmented", action="store_true", help="Treat each supplied WAV as one segment."
    )
    parser.add_argument("--model-id", default="microsoft/wavlm-base-plus-sv")
    parser.add_argument("--model-revision", default="main")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Explicitly permit a lazy Hugging Face model download if it is not cached.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.capability:
        print(json.dumps(capability_report(model_id=args.model_id, revision=args.model_revision), indent=2))
        return 0
    if not args.anchor_wav or not args.anchor_source_id or not args.candidate:
        build_parser().error(
            "analysis requires --anchor-wav, --anchor-source-id, and at least one --candidate"
        )

    backend = WavLMSpeakerEmbedder(
        model_id=args.model_id,
        revision=args.model_revision,
        cache_dir=args.cache_dir,
        allow_download=args.allow_model_download,
        device=args.device,
    )
    try:
        result = analyze_speaker_consistency(
            anchor=BoundedWav(
                path=args.anchor_wav,
                source_id=args.anchor_source_id,
                range_id="owner_confirmed_anchor",
                owner_confirmed_target_only=args.owner_confirmed_anchor,
            ),
            candidates=[
                BoundedWav(path=path, source_id=source_id, range_id=f"candidate_{number:04d}")
                for number, (source_id, path) in enumerate(args.candidate, 1)
            ],
            backend=backend,
            split_on_silence=not args.presegmented,
            output_path=args.output,
        )
    except ConsistencyEvidenceError as exc:
        print(
            json.dumps(
                {
                    "status": "failed_closed",
                    "error": str(exc),
                    "identity_proof": False,
                    "voice_assignment_performed": False,
                    "voice_clone_or_training_performed": False,
                    "activation_performed": False,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
