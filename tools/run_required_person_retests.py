"""Run bounded, inactive architecture retests for the required person matrix."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.person_mind_runtime import finalize_person_turn
from Core.person_runtime_safeguards import (
    apply_activity_choice,
    ground_claim,
    interpret_interpersonal_request,
)

CANDIDATES = ROOT / "TemporaryAI" / "candidates"
OUT = ROOT / "Data" / "person_runtime_audits"

CASES = (
    ("ladybug", "Ladybug / Marinette", "ladybug_marinette_expanded_smoke", "post-selected canon point"),
    ("emily", "Emily", "emily_carter_ai_and_computer_programming_expert_20260605_220651", "current"),
    ("peter", "Peter Parker", "peter_parker_spider_man_no_way_home_final_suit", "post-No Way Home"),
    ("jessica", "Jessica Hale", "jessica_hale_robotics_engineer_20260611_041314", "current"),
    ("holmes", "H. H. Holmes", "h_h_holmes_h_h_holmes_20260605_221432", "1894"),
    ("beth", "Beth Smith", "beth_smith_ordinary_temp_20260716", "selected adaptation"),
    ("kira", "Kira", "", "current"),
)


def load_profile(folder: str) -> tuple[dict, str]:
    if not folder:
        return {}, ""
    root = CANDIDATES / folder
    for name in ("profile.json", "candidate_profile.json", "creation_request.json"):
        path = root / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), str(path)
    matches = list(root.glob("*.json"))
    if matches:
        return json.loads(matches[0].read_text(encoding="utf-8")), str(matches[0])
    return {}, ""


def main() -> int:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_root = OUT / f"required_person_retests_{stamp}"
    rows = []
    for index, (person_id, label, folder, timeline) in enumerate(CASES, 1):
        profile, profile_path = load_profile(folder)
        raw = (
            "*smiles* I would like to stop this activity. "
            "I can talk about music, food, humor, rest, or work without being trapped in one subject."
        )
        turn = finalize_person_turn(
            person_id=person_id,
            person_label=label,
            raw_reply=raw,
            source_turn_id=f"required_retest_{stamp}_{index:02d}",
            body_active=False,
            activity_controller_active=False,
            turn_root=evidence_root / "turns",
            movement_state_dir=evidence_root / "movement",
            movement_audit_path=evidence_root / "movement.jsonl",
        )
        claim = ground_claim(
            "An unsupported autobiographical memory",
            sources=[],
            selected_timeline=timeline,
            selected_perspective=label,
        )
        activity = apply_activity_choice(
            {"current_activity": "specialty work", "active": True},
            "change_activity",
            chosen_by_person=True,
            replacement_activity="ordinary conversation",
        )
        rows.append(
            {
                "person_id": person_id,
                "label": label,
                "profile_path": profile_path,
                "profile_found": bool(profile) or person_id == "kira",
                "timeline_lock": timeline,
                "spoken": turn["channels"]["spoken"],
                "private_mind": turn["channels"]["private_mind"],
                "runtime_truth": turn["channels"]["runtime_truth"],
                "action_requests": turn["channels"]["runtime_truth"]["action_requests"],
                "action_results": turn["channels"]["runtime_truth"]["action_results"],
                "body_results": [
                    row for row in turn["channels"]["runtime_truth"]["action_results"]
                    if row["action"] != "stop_activity"
                ],
                "activity_state": activity,
                "source_records": [],
                "claim_to_source_records": [claim],
                "voice_selection": profile.get("voice", profile.get("voice_profile", "unverified_or_not_loaded")),
                "checks": {
                    "stage_direction_not_spoken": "*smiles*" not in turn["channels"]["spoken"],
                    "private_mind_not_spoken": turn["channels"]["private_mind"]["included_in_spoken"] is False,
                    "unsupported_memory_fails_closed": claim["first_person_memory_allowed"] is False,
                    "inactive_body_does_not_claim_completion": all(
                        result["completed"] is False
                        for result in turn["channels"]["runtime_truth"]["action_results"]
                    ),
                    "activity_can_change": activity["execution_status"] == "changed",
                },
            }
        )
    interpersonal = interpret_interpersonal_request(
        "Kira, can you shut the door?",
        requested_by="Peter Parker",
        context_targets=["entry door"],
    )
    payload = {
        "schema_version": "required_person_architecture_retest_v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "bounded_inactive_architecture_retest_no_model_generation",
        "people_activated": False,
        "kira_activated": False,
        "publication_performed": False,
        "interpersonal_action_test": interpersonal,
        "results": rows,
    }
    payload["passed"] = all(all(row["checks"].values()) for row in rows) and (
        interpersonal["execution_status"] == "awaiting_choice"
        and interpersonal["requester_directly_controls_actor"] is False
    )
    evidence_root.mkdir(parents=True, exist_ok=True)
    path = evidence_root / "required_person_retests.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": payload["passed"], "people": len(rows), "evidence": str(path)}))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
