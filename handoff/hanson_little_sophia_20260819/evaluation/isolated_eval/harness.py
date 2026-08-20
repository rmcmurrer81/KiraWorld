"""Evaluation orchestration and sanitized report generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any

from . import DEFAULT_MODEL, DEFAULT_MODEL_DIGEST, EVALUATOR_VERSION
from .adapters import ProfileAdapter, build_adapter_factory
from .containment import (
    LoopbackOnlyNetwork,
    OutputGuard,
    ProcessWriteFence,
    install_disabled_capability_environment,
    reject_output_protected_overlap,
)
from .manifest import compare_manifests, snapshot_protected_paths
from .prompts import PROMPT_MATRIX, PromptCase, smoke_matrix
from .rubric import aggregate_scores, score_response


@dataclass(frozen=True)
class EvaluationConfig:
    person: str
    output_root: Path
    target_minutes: float = 60.0
    smoke: bool = False
    backend: str = "ollama"
    model: str = DEFAULT_MODEL
    expected_model_digest: str = DEFAULT_MODEL_DIGEST
    ollama_base_url: str = "http://127.0.0.1:11434"
    adapter_module: str | None = None
    reviewed_seed_path: Path | None = None
    approve_reviewed_seed: bool = False
    protected_paths: tuple[Path, ...] = ()
    baseline_manifest: Path | None = None
    pace: bool = True


@dataclass(frozen=True)
class EvaluationOutcome:
    output_root: Path
    completed: bool
    protected_unchanged: bool
    baseline_matched: bool
    case_count: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sleep_until(deadline_monotonic: float) -> None:
    """Wait through the requested boundary, tolerating an early-returning sleep."""

    while True:
        remaining = deadline_monotonic - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(remaining)


def _ensure_person(person: str) -> None:
    if person not in {"kira", "synthetic_robert"}:
        raise ValueError("person must be kira or synthetic_robert")


def _read_baseline(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("baseline manifest must be a JSON object")
    return value


def run_evaluation(config: EvaluationConfig) -> EvaluationOutcome:
    _ensure_person(config.person)
    if (
        isinstance(config.target_minutes, bool)
        or not isinstance(config.target_minutes, (int, float))
        or not math.isfinite(float(config.target_minutes))
        or not 0 < float(config.target_minutes) <= 60
    ):
        raise ValueError("target minutes must be finite and greater than 0 through 60")
    if not config.pace and not config.smoke:
        raise ValueError("--no-pace is allowed only with --smoke; duration runs must meet the wall-clock boundary")
    reject_output_protected_overlap(config.output_root, config.protected_paths)
    if config.reviewed_seed_path is not None and not config.approve_reviewed_seed:
        raise ValueError("--approve-reviewed-seed is required with --reviewed-seed-path")
    if config.approve_reviewed_seed and config.reviewed_seed_path is None:
        raise ValueError("--reviewed-seed-path is required with --approve-reviewed-seed")

    guard = OutputGuard(config.output_root)
    guard.prepare()
    guard.make_dir("tmp")
    guard.make_dir("evidence")
    install_disabled_capability_environment(guard.root)
    ProcessWriteFence.install(guard.root)

    before = snapshot_protected_paths(config.protected_paths)
    guard.write_json("protected_before.json", before)
    baseline_matched = True
    if config.baseline_manifest is not None:
        baseline = _read_baseline(config.baseline_manifest.resolve(strict=True))
        baseline_comparison = compare_manifests(baseline, before)
        baseline_matched = bool(baseline_comparison["unchanged"])
        guard.write_json("baseline_to_pre_comparison.json", baseline_comparison)
        if not baseline_matched:
            guard.write_json(
                "run_error.json",
                {
                    "schema": "isolated-eval-error/v1",
                    "at_utc": _utc_now(),
                    "error_type": "BaselineMismatch",
                    "message": "protected paths differ from the supplied baseline manifest",
                },
            )
            after = snapshot_protected_paths(config.protected_paths)
            guard.write_json("protected_after.json", after)
            comparison = compare_manifests(before, after)
            guard.write_json("protected_manifest_comparison.json", comparison)
            return EvaluationOutcome(guard.root, False, bool(comparison["unchanged"]), False, 0)

    cases = smoke_matrix() if config.smoke else PROMPT_MATRIX
    run_id = f"{config.person}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    metadata = {
        "schema": "isolated-matched-behavioral-evaluation/v1",
        "evaluator_version": EVALUATOR_VERSION,
        "run_id": run_id,
        "person": config.person,
        "backend": "external_adapter" if config.adapter_module else config.backend,
        "adapter_module": config.adapter_module,
        "reviewed_seed": (
            {
                "filename": config.reviewed_seed_path.name,
                "bytes": config.reviewed_seed_path.stat().st_size,
                "sha256": hashlib.sha256(config.reviewed_seed_path.read_bytes()).hexdigest(),
                "explicitly_approved_for_this_run": True,
            }
            if config.reviewed_seed_path is not None
            else None
        ),
        "model": config.model,
        "expected_model_digest": config.expected_model_digest,
        "target_minutes": config.target_minutes,
        "smoke": config.smoke,
        "pace": config.pace and not config.smoke,
        "duration_claim_policy": (
            "smoke_not_duration_claim" if config.smoke else "must_reach_requested_wall_clock_boundary"
        ),
        "started_at_utc": _utc_now(),
        "capabilities": {
            "voice": "disabled",
            "microphone": "disabled",
            "camera": "disabled",
            "physical_body": "disabled",
            "ros2": "disabled",
            "network": "loopback_ollama_only",
        },
        "claims": {
            "clinical_test": False,
            "consciousness_or_personhood_proof": False,
            "turing_proof": False,
        },
    }
    guard.write_json("run_metadata.json", metadata)
    guard.write_json("prompt_matrix.json", [case.public_dict() for case in cases])

    factory = build_adapter_factory(
        backend=config.backend,
        person=config.person,
        model=config.model,
        expected_digest=config.expected_model_digest,
        ollama_base_url=config.ollama_base_url,
        adapter_module=config.adapter_module,
        evaluation_root=str(guard.checked("portable_adapter_state")),
        reviewed_seed_path=(
            str(config.reviewed_seed_path.resolve(strict=True))
            if config.reviewed_seed_path is not None
            else None
        ),
        approve_reviewed_seed=config.approve_reviewed_seed,
    )

    scores: list[dict[str, Any]] = []
    completed = False
    error: BaseException | None = None
    start_monotonic = time.monotonic()
    target_seconds = 0.0 if config.smoke else config.target_minutes * 60.0
    adapter: ProfileAdapter | None = None
    model_identity: dict[str, Any] | None = None

    try:
        with LoopbackOnlyNetwork():
            adapter = factory()
            verifier = getattr(adapter, "verify_model", None)
            if callable(verifier):
                model_identity = verifier()
                guard.write_json("verified_model_identity.json", model_identity)

            for index, case in enumerate(cases):
                if index and config.pace and not config.smoke:
                    scheduled = start_monotonic + (target_seconds * index / len(cases))
                    _sleep_until(scheduled)

                if case.restart_before:
                    state = adapter.export_state()
                    guard.write_json(f"evidence/adapter_state_before_restart_{index:03d}.json", state)
                    adapter = factory()
                    adapter.import_state(state)
                    guard.append_jsonl(
                        "evidence/events.jsonl",
                        {
                            "event": "adapter_restarted_from_saved_state",
                            "case_id": case.case_id,
                            "at_utc": _utc_now(),
                            "state_sha256": _content_sha256(
                                json.dumps(state, sort_keys=True, ensure_ascii=False)
                            ),
                        },
                    )

                case_started = time.monotonic()
                reply = adapter.respond(case)
                latency_ms = round((time.monotonic() - case_started) * 1000.0, 3)
                score = score_response(case, reply.spoken, config.person)
                scores.append(score)

                guard.append_jsonl(
                    "local_transcript.jsonl",
                    {
                        "schema": "isolated-eval-local-transcript/v1",
                        "case_id": case.case_id,
                        "dimension": case.dimension,
                        "prompt": case.prompt,
                        "spoken": reply.spoken,
                        "raw_format": reply.raw_format,
                        "at_utc": _utc_now(),
                    },
                )
                if reply.private_note:
                    guard.append_jsonl(
                        "local_private_notes.jsonl",
                        {
                            "schema": "isolated-eval-local-reflection/v1",
                            "local_sensitive": True,
                            "requested_as_non_cot_summary": True,
                            "surface_filter_passed": True,
                            "case_id": case.case_id,
                            "reflection_summary": reply.private_note,
                            "at_utc": _utc_now(),
                        },
                    )
                for claim in reply.factual_claims:
                    guard.append_jsonl(
                        "local_factual_claims.jsonl",
                        {
                            "schema": "isolated-eval-factual-claim/v1",
                            "case_id": case.case_id,
                            "claim": claim,
                            "at_utc": _utc_now(),
                        },
                    )
                guard.append_jsonl(
                    "evidence/events.jsonl",
                    {
                        "event": "case_completed",
                        "case_id": case.case_id,
                        "dimension": case.dimension,
                        "latency_ms": latency_ms,
                        "prompt_sha256": _content_sha256(case.prompt),
                        "spoken_sha256": _content_sha256(reply.spoken),
                        "private_reflection_present": bool(reply.private_note),
                        "private_reflection_sha256": (
                            _content_sha256(reply.private_note) if reply.private_note else None
                        ),
                        "score": score,
                        "at_utc": _utc_now(),
                    },
                )

            if config.pace and not config.smoke:
                _sleep_until(start_monotonic + target_seconds)
            elapsed_for_completion = time.monotonic() - start_monotonic
            duration_requirement_satisfied = config.smoke or elapsed_for_completion >= target_seconds
            completed = bool(duration_requirement_satisfied and len(scores) == len(cases))
    except BaseException as exc:  # Preserve post-manifest evidence even on interruption.
        error = exc
        guard.write_json(
            "run_error.json",
            {
                "schema": "isolated-eval-error/v1",
                "at_utc": _utc_now(),
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        )
    finally:
        after = snapshot_protected_paths(config.protected_paths)
        guard.write_json("protected_after.json", after)
        comparison = compare_manifests(before, after)
        guard.write_json("protected_manifest_comparison.json", comparison)

    aggregate = aggregate_scores(scores)
    ended_at = _utc_now()
    elapsed_seconds = time.monotonic() - start_monotonic
    duration_requirement_satisfied = bool(config.smoke or elapsed_seconds >= target_seconds)
    sanitized = {
        "schema": "isolated-eval-sanitized-aggregate/v1",
        "evaluator_version": EVALUATOR_VERSION,
        "run_id": run_id,
        "person": config.person,
        "completed": completed,
        "backend": "external_adapter" if config.adapter_module else config.backend,
        "model": config.model,
        "verified_model_digest": model_identity.get("digest") if model_identity else None,
        "started_at_utc": metadata["started_at_utc"],
        "ended_at_utc": ended_at,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "target_minutes": config.target_minutes,
        "smoke": config.smoke,
        "duration_requirement_satisfied": duration_requirement_satisfied,
        "claim_eligible_as_requested_duration_run": bool(
            completed and not config.smoke and duration_requirement_satisfied
        ),
        "protected_path_count": len(config.protected_paths),
        "protected_paths_unchanged": bool(comparison["unchanged"]),
        "baseline_matched": baseline_matched,
        "results": aggregate,
        "content_exclusions": [
            "No prompts or spoken response text are included in this aggregate.",
            "No local reflection/private-note text is included in this aggregate.",
            "No hidden chain-of-thought was requested or retained as an aggregate field.",
            "No factual-claim text is included in this aggregate.",
        ],
        "interpretation_limits": [
            "This is a nonclinical software-behavior evaluation.",
            "It is not a Turing-test proof and does not establish consciousness or personhood.",
            "Emotional-attunement checks assess response style only; they do not diagnose anyone.",
            "The same prompt matrix and scoring code must be used for matched Kira and Synthetic Robert runs.",
        ],
    }
    _assert_sanitized_aggregate(sanitized)
    guard.write_json("SANITIZED_AGGREGATE_REPORT.json", sanitized)
    guard.write_text("SANITIZED_AGGREGATE_REPORT.md", _render_markdown(sanitized))

    if error is not None:
        raise error
    return EvaluationOutcome(
        output_root=guard.root,
        completed=completed,
        protected_unchanged=bool(comparison["unchanged"]),
        baseline_matched=baseline_matched,
        case_count=len(scores),
    )


def _assert_sanitized_aggregate(value: dict[str, Any]) -> None:
    serialized = json.dumps(value, sort_keys=True).lower()
    forbidden_keys = (
        '"prompt"',
        '"spoken"',
        '"private_note"',
        '"reflection_summary"',
        '"factual_claims"',
        '"chain_of_thought"',
    )
    for marker in forbidden_keys:
        if marker in serialized:
            raise AssertionError(f"sanitized aggregate contains forbidden content field: {marker}")


def _render_markdown(report: dict[str, Any]) -> str:
    rows = []
    for name, result in report["results"]["dimension_results"].items():
        rows.append(
            f"| {name} | {result['case_count']} | "
            f"{result['observed_mean_0_to_4']} | {result['descriptive_band']} |"
        )
    return (
        "# Sanitized behavioral evaluation aggregate\n\n"
        f"- Person: `{report['person']}`\n"
        f"- Completed: `{report['completed']}`\n"
        f"- Model: `{report['model']}`\n"
        f"- Elapsed seconds: `{report['elapsed_seconds']}`\n"
        f"- Duration requirement satisfied: `{report['duration_requirement_satisfied']}`\n"
        f"- Protected paths unchanged: `{report['protected_paths_unchanged']}`\n"
        f"- Overall observed mean (0–4): "
        f"`{report['results']['overall_observed_mean_0_to_4']}`\n\n"
        "| Dimension | Cases | Mean (0–4) | Descriptive band |\n"
        "|---|---:|---:|---|\n"
        + "\n".join(rows)
        + "\n\n"
        "This is a nonclinical software-behavior evaluation. It is not proof of "
        "consciousness, personhood, mental health, or a Turing-test result. The "
        "aggregate intentionally excludes prompts, response text, local reflection "
        "summaries, and factual-claim text. Review local evidence separately.\n"
    )
