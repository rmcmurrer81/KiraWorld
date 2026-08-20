"""Command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import DEFAULT_MODEL, DEFAULT_MODEL_DIGEST
from .harness import EvaluationConfig, run_evaluation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an isolated matched, nonclinical behavioral evaluation."
    )
    parser.add_argument("--person", required=True, choices=("kira", "synthetic_robert"))
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--target-minutes", type=float, default=60.0)
    parser.add_argument("--smoke", action="store_true", help="run a fast unpaced subset")
    parser.add_argument("--backend", choices=("ollama", "stub"), default="ollama")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--expected-model-digest", default=DEFAULT_MODEL_DIGEST)
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--adapter-module",
        help="audited module exposing create_evaluation_adapter(...); overrides backend adapter",
    )
    parser.add_argument(
        "--reviewed-seed-path",
        type=Path,
        help="identity-bound reviewed continuity seed copied into the isolated adapter state",
    )
    parser.add_argument(
        "--approve-reviewed-seed",
        action="store_true",
        help="explicitly approve importing the exact reviewed seed for this isolated run",
    )
    parser.add_argument(
        "--protected-path",
        action="append",
        default=[],
        type=Path,
        help="read-only file or directory to hash before and after; repeat as needed",
    )
    parser.add_argument(
        "--baseline-manifest",
        type=Path,
        help="optional earlier protected manifest that must match the pre-run snapshot",
    )
    parser.add_argument(
        "--no-pace",
        action="store_true",
        help="unpaced execution is permitted only with --smoke; duration runs always meet the boundary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = EvaluationConfig(
        person=args.person,
        output_root=args.output_root,
        target_minutes=args.target_minutes,
        smoke=args.smoke,
        backend=args.backend,
        model=args.model,
        expected_model_digest=args.expected_model_digest,
        ollama_base_url=args.ollama_base_url,
        adapter_module=args.adapter_module,
        reviewed_seed_path=args.reviewed_seed_path,
        approve_reviewed_seed=args.approve_reviewed_seed,
        protected_paths=tuple(args.protected_path),
        baseline_manifest=args.baseline_manifest,
        pace=not args.no_pace,
    )
    try:
        outcome = run_evaluation(config)
    except BaseException as exc:
        print(f"EVALUATION_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if not outcome.baseline_matched:
        print(f"BASELINE_MISMATCH output={outcome.output_root}", file=sys.stderr)
        return 4
    if not outcome.protected_unchanged:
        print(f"PROTECTED_PATH_CHANGED output={outcome.output_root}", file=sys.stderr)
        return 3
    print(
        f"EVALUATION_COMPLETE person={args.person} cases={outcome.case_count} "
        f"output={outcome.output_root}"
    )
    return 0
