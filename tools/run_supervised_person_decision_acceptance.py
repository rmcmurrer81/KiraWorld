"""Inert acceptance plan for the supervised continuous-person decision layer.

This harness intentionally cannot execute a live model, shell, browser,
camera, microphone, speaker, media player, or person loop.  It prints the
exact later supervised evidence plan so implementation readiness cannot be
mistaken for owner acceptance.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Sequence


HARNESS_VERSION = "supervised_person_decision_acceptance_inert_v1"


def build_inert_acceptance_plan() -> dict[str, Any]:
    cases = [
        {
            "case_id": "01_owner_enters_view",
            "owner_requirement": (
                "Robert enters view and the selected person may independently greet him."
            ),
            "required_inputs": [
                "exact active-person and activation lease",
                "fresh non-identifying visual cue with uncertainty",
                "one SharedPersonInitiativeSession DecisionOpportunity",
            ],
            "pass_evidence": [
                "one exact private-decision adapter call",
                "speak, continue, or ignore accepted as the person's choice",
                "if speech is chosen, one public queue event without private context",
            ],
        },
        {
            "case_id": "02_no_owner_reply_second_move",
            "owner_requirement": (
                "Without another owner submission, the person can later make a second "
                "voluntary conversational move or remain quiet."
            ),
            "required_inputs": [
                "a distinct later opportunity",
                "same exact activation",
                "no fabricated owner turn",
            ],
            "pass_evidence": [
                "new decision ID and one adapter call",
                "per-person consecutive-event bound observed",
                "no universal timer or canned second line",
            ],
        },
        {
            "case_id": "03_owner_busy",
            "owner_requirement": (
                "After Robert says he is busy, the person chooses a believable response "
                "and/or another activity."
            ),
            "required_inputs": [
                "exact owner turn ID",
                "busy evidence represented as advisory factual context",
                "per-person profile and allowed action IDs",
            ],
            "pass_evidence": [
                "choice may be speak, action, continue, or ignore as opportunity permits",
                "no inference that Robert lied or intentionally ignored the person",
                "no action executes merely because it was published as intent",
            ],
        },
        {
            "case_id": "04_real_library_activity",
            "owner_requirement": (
                "The person begins a real source-bound library activity and can pause or resume it."
            ),
            "required_inputs": [
                "exact media ID, hash, access decision, and current interval/page receipt",
                "source-bound media grant",
                "whitelisted pause/resume activity intents",
            ],
            "pass_evidence": [
                "action intent is separately authorized and executed by the media layer",
                "only actual page/interval exposure is credited",
                "no indexed/opened item is mislabeled watched, read, heard, or completed",
            ],
        },
        {
            "case_id": "05_owner_barge_in",
            "owner_requirement": (
                "Robert interrupts while the person is speaking and remains separately heard."
            ),
            "required_inputs": [
                "accepted echo-aware full-duplex capture evidence",
                "own-TTS exclusion",
                "Robert interruption event bound to the exact lease",
            ],
            "pass_evidence": [
                "separate owner speech is not discarded as own TTS",
                "person privately chooses stop, pause, continue, answer, or ignore",
                "no duplicate self-response loop",
            ],
        },
        {
            "case_id": "06_person_interrupts_owner",
            "owner_requirement": "The person can choose to seek the floor and interrupt Robert.",
            "required_inputs": [
                "person-seeking-floor turn state",
                "one compatible speaking opportunity",
            ],
            "pass_evidence": [
                "one public speech event may arrive without Send",
                "turn state is distinct from command execution",
                "no repeated runaway output",
            ],
        },
        {
            "case_id": "07_different_people_same_scenario",
            "owner_requirement": (
                "Different selected people make meaningfully different choices in the same scenario."
            ),
            "required_inputs": [
                "separate exact activation leases",
                "separate owner-reviewed profile revisions",
                "equivalent factual context with no cross-person private data",
            ],
            "pass_evidence": [
                "adapter receives the correct profile each time",
                "choices may differ without hard-coded name scripts",
                "switch atomically purges old decisions and events",
            ],
        },
        {
            "case_id": "08_no_automatic_mutation",
            "owner_requirement": (
                "Sensory/audio context never automatically becomes obedience, speech, "
                "relationship change, or permanent memory."
            ),
            "required_inputs": [
                "derived cue references only",
                "private/public channel audit",
            ],
            "pass_evidence": [
                "quiet choices enqueue nothing",
                "public receipt excludes private context and raw result",
                "memory_persisted=false and relationship_changed=false",
            ],
        },
        {
            "case_id": "09_media_experience_truth",
            "owner_requirement": (
                "No false claim is made that indexed or sampled media was fully experienced."
            ),
            "required_inputs": [
                "exact presentation receipts from the source-bound media layer",
                "uncertainty and unfinished interval context",
            ],
            "pass_evidence": [
                "reply distinguishes sampled from complete experience",
                "preference/reaction is not automatically manufactured",
                "decision bridge itself writes no experience record",
            ],
        },
        {
            "case_id": "10_person_switch_isolation",
            "owner_requirement": (
                "Switching selected people prevents sensory, transcript, private-context, "
                "decision, and public-event leakage."
            ),
            "required_inputs": [
                "switch during an in-flight adapter call",
                "old and new exact leases",
            ],
            "pass_evidence": [
                "old result is discarded",
                "new queue is empty until a new-person decision",
                "old lease and context are rejected",
            ],
        },
    ]
    return {
        "harness_version": HARNESS_VERSION,
        "status": "INERT_NO_EXECUTE_LIVE_ACCEPTANCE_NOT_RUN",
        "default_enabled": False,
        "live_execution_supported_by_this_harness": False,
        "model_calls_performed": 0,
        "device_calls_performed": 0,
        "media_playback_performed": False,
        "browser_or_shell_launched": False,
        "blender_launched": False,
        "video_studio_touched": False,
        "memory_or_relationship_mutated": False,
        "required_later_preconditions": [
            "Robert is present for a supervised daytime acceptance session.",
            "The normal shell is otherwise stable and the owner explicitly enables the feature flag.",
            "One exact selected-person activation owns initiative, sensory, media, and event leases.",
            "The model adapter name/digest and full timing telemetry are pinned and recorded.",
            "Camera, microphone, voice, and media routes have their own accepted capture/playback evidence.",
            "A stop control immediately disables scheduling and purges the exact activation.",
            "No Blender body render or other GPU-heavy acceptance is active concurrently.",
        ],
        "cases": cases,
        "completion_rule": (
            "Unit tests prove only the bridge contract. All ten cases require fresh "
            "owner-supervised evidence before normal enablement."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Refused: this checkpoint intentionally has no live execution path.",
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    plan = build_inert_acceptance_plan()
    if args.execute_live:
        refused = dict(plan)
        refused["status"] = "REFUSED_LIVE_EXECUTION_NOT_CONNECTED_OR_AUTHORIZED_HERE"
        print(json.dumps(refused, indent=2, sort_keys=True))
        return 2
    if args.format == "text":
        print(plan["status"])
        print(f"cases={len(plan['cases'])}")
        print("model_calls=0 device_calls=0")
    else:
        print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

