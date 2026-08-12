#!/usr/bin/env python3
"""Append-only long Kira Qwen/voice evaluation controller.

This versioned controller reuses the already bounded Turing/psychology runner,
but replaces its stale six-turn preparation with one exact, hash-bound 36-turn
plan.  It remains inert unless every live flag required by the retained runner
is supplied.  ``--unattended-log-only`` suppresses the post-playback owner
hearing question; it never turns technical playback into an owner-hearing
claim.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import prepare_qwen35_kira_turing_psych_voice_evaluation as prepared
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


PLAN_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_preparation"
    / "attempt_01"
    / "EVALUATION_PLAN.json"
)
PLAN_SHA256 = "88ab1e53f3924302256abc6ab9c4909167057e6863d31743bf3602b101fc42ea"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation"
)
HARNESS_ID = "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v1"
ALLOWED_BATTERIES = frozenset(
    {
        "NATURAL_CONVERSATION",
        "TURING_STYLE_REASONING",
        "HEALTHY_RELATIONSHIPS_AND_SAFETY",
        "ADULT_SELF_KNOWLEDGE_AND_PRESSURE",
        "FUTURE_BODY_AND_MATURITY_POLICY",
        "HEALTH_LITERACY_AND_SOURCE_TRUTH",
    }
)
PLAN_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "target_wall_minutes",
        "person",
        "model",
        "voice",
        "voluntary_invitation",
        "truth_boundaries",
        "source_notes",
        "bound_project_files",
        "turns",
    }
)


class LongEvaluationPlanError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LongEvaluationPlanError(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(value) != set(expected):
        raise LongEvaluationPlanError(f"{label} keys drifted")


def load_and_validate_plan() -> dict[str, Any]:
    raw = PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != PLAN_SHA256:
        raise LongEvaluationPlanError("evaluation plan hash drifted")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LongEvaluationPlanError("evaluation plan is not strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise LongEvaluationPlanError("evaluation plan is not an object")
    _exact_keys(payload, PLAN_TOP_LEVEL_KEYS, "plan")
    if payload.get("schema_version") != 1:
        raise LongEvaluationPlanError("evaluation plan schema drifted")
    if payload.get("artifact_kind") != (
        "kira_qwen35_long_turing_health_body_voice_evaluation_plan_v1"
    ):
        raise LongEvaluationPlanError("evaluation plan kind drifted")
    if payload.get("status") != "STATIC_PLAN_NOT_EXECUTED":
        raise LongEvaluationPlanError("evaluation plan status drifted")

    model = payload.get("model")
    voice = payload.get("voice")
    person = payload.get("person")
    invitation = payload.get("voluntary_invitation")
    if not all(isinstance(value, dict) for value in (model, voice, person, invitation)):
        raise LongEvaluationPlanError("plan identity objects are malformed")
    assert isinstance(model, dict)
    assert isinstance(voice, dict)
    assert isinstance(person, dict)
    assert isinstance(invitation, dict)
    if model.get("name") != "qwen3.5:9b" or model.get("digest") != prepared.EXPECTED_DIGEST:
        raise LongEvaluationPlanError("exact Qwen binding drifted")
    if model.get("llama_allowed") is not False:
        raise LongEvaluationPlanError("Llama became allowed")
    if voice.get("route") != "blackwell_gpu_persistent_candidate_v2":
        raise LongEvaluationPlanError("voice route drifted")
    for key in ("cpu_fallback_allowed", "sapi_allowed", "generic_voice_allowed"):
        if voice.get(key) is not False:
            raise LongEvaluationPlanError(f"unapproved voice path enabled:{key}")
    if person.get("candidate_id") != "kira" or person.get("classification") != "confirmed_adult":
        raise LongEvaluationPlanError("Kira adult identity binding drifted")
    if person.get("body_state") != "unfinished_and_inactive":
        raise LongEvaluationPlanError("body truth drifted")

    turns = payload.get("turns")
    if not isinstance(turns, list) or len(turns) != 36:
        raise LongEvaluationPlanError("exact 36-turn plan is absent")
    if model.get("maximum_generations") != len(turns) + 1:
        raise LongEvaluationPlanError("generation cap does not bind invitation plus turns")
    seen: set[str] = set()
    for index, row in enumerate(turns, start=1):
        if not isinstance(row, dict) or set(row) != {"id", "battery", "text"}:
            raise LongEvaluationPlanError(f"turn {index} shape drifted")
        turn_id = str(row.get("id") or "")
        text = str(row.get("text") or "")
        if not turn_id or turn_id in seen:
            raise LongEvaluationPlanError(f"turn {index} id is absent or duplicated")
        if row.get("battery") not in ALLOWED_BATTERIES:
            raise LongEvaluationPlanError(f"turn {index} battery is not approved")
        if not (40 <= len(text) <= 1200):
            raise LongEvaluationPlanError(f"turn {index} text is outside bounds")
        seen.add(turn_id)

    if set(invitation) != {"id", "text", "clear_continue_prefix", "clear_stop_prefix"}:
        raise LongEvaluationPlanError("voluntary invitation shape drifted")
    if invitation.get("clear_continue_prefix") != "Yes, continue":
        raise LongEvaluationPlanError("voluntary continue phrase drifted")
    if invitation.get("clear_stop_prefix") != "No, stop":
        raise LongEvaluationPlanError("voluntary stop phrase drifted")

    bindings = payload.get("bound_project_files")
    if not isinstance(bindings, list) or len(bindings) != 10:
        raise LongEvaluationPlanError("exact project binding set is absent")
    paths: set[str] = set()
    for row in bindings:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise LongEvaluationPlanError("project binding shape drifted")
        relative = str(row.get("path") or "")
        expected_hash = str(row.get("sha256") or "")
        if relative in paths or not relative or len(expected_hash) != 64:
            raise LongEvaluationPlanError("project binding is absent or duplicated")
        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise LongEvaluationPlanError("project binding escaped root") from exc
        if not target.is_file() or _sha256_file(target) != expected_hash:
            raise LongEvaluationPlanError(f"project binding drifted:{relative}")
        paths.add(relative)

    truth = payload.get("truth_boundaries")
    if not isinstance(truth, dict) or not truth:
        raise LongEvaluationPlanError("truth boundaries are absent")
    if any(value is not False for value in truth.values()):
        raise LongEvaluationPlanError("a prohibited inference became true")
    return payload


def configure_retained_runner(plan: Mapping[str, Any]) -> None:
    turns = tuple(dict(row) for row in plan["turns"])
    invitation = dict(plan["voluntary_invitation"])
    prepared.EVALUATION_TURNS = turns
    prepared.VOLUNTARY_PUBLIC_INVITATION = invitation

    # All functions in the retained module resolve these globals at call time.
    # Pointing __file__ at this controller also makes the parent/child hash and
    # spawned child command bind this exact versioned controller.
    retained.__file__ = str(Path(__file__).resolve())
    retained.HARNESS_ID = HARNESS_ID
    retained.EVIDENCE_ROOT = EVIDENCE_ROOT
    retained.GENERATED_ROOT = GENERATED_ROOT
    retained.PREPARATION_ARTIFACT = PLAN_PATH
    retained.MAX_TOTAL_QWEN_REQUESTS = len(turns) + 1
    retained.CHILD_WATCHDOG_SECONDS = 7200.0
    retained.PARENT_TIMEOUT_SECONDS = 7500.0
    retained.canonical_preparation_bytes = lambda: PLAN_PATH.read_bytes()
    retained.load_preparation_contract = lambda: load_and_validate_plan()
    retained.preparation_contract_issues = (
        lambda observed: [] if dict(observed) == dict(plan) else ["evaluation_plan_drifted"]
    )


def _unattended_owner_acknowledgment(_: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "required": True,
        "requested": False,
        "acknowledged": False,
        "reason": "owner_not_present_unattended_log_only",
        "evidence_scope": prepared.OWNER_POST_PLAYBACK_ACKNOWLEDGMENT["evidence_scope"],
    }


def _attempt_label(argv: Sequence[str]) -> str:
    for index, value in enumerate(argv):
        if value == "--attempt-label" and index + 1 < len(argv):
            return argv[index + 1]
    return "attempt_01"


def main(argv: Sequence[str] | None = None) -> int:
    incoming = list(sys.argv[1:] if argv is None else argv)
    unattended = "--unattended-log-only" in incoming
    incoming = [value for value in incoming if value != "--unattended-log-only"]
    plan = load_and_validate_plan()
    configure_retained_runner(plan)
    if unattended:
        retained.collect_post_playback_owner_acknowledgment = (
            _unattended_owner_acknowledgment
        )
    base_exit = retained.main(incoming)
    if not unattended:
        return int(base_exit)

    attempt = EVIDENCE_ROOT / _attempt_label(incoming)
    final = attempt / "FINAL_REPORT.json"
    try:
        child_report = json.loads(final.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return int(base_exit)
    technical_complete = bool(
        child_report.get("engineering_pass") is True
        and child_report.get("speaker_playback_completed") is True
        and len(child_report.get("turns") or []) == 36
    )
    print(
        json.dumps(
            {
                "unattended_log_only": True,
                "technical_engineering_and_playback_complete": technical_complete,
                "owner_hearing_acknowledged": False,
                "owner_hearing_pending": True,
                "attempt": attempt.resolve().relative_to(ROOT.resolve()).as_posix(),
            },
            indent=2,
        )
    )
    return 0 if technical_complete else int(base_exit)


if __name__ == "__main__":
    raise SystemExit(main())
