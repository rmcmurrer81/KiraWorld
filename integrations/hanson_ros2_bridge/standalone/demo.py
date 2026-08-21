from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "kira_hanson_bridge"
sys.path.insert(0, str(PACKAGE_ROOT))

from kira_hanson_bridge.evidence import EvidenceChain, sanitize_payload  # noqa: E402
from kira_hanson_bridge.policy import SafetyPolicy, ValidationResult  # noqa: E402
from kira_hanson_bridge.request_guard import RequestGuard  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    default_policy_path = (
        PROJECT_ROOT
        / "ros2_ws"
        / "src"
        / "kira_hanson_bridge"
        / "config"
        / "safety_policy.yaml"
    )
    parser = argparse.ArgumentParser(
        description="Run the bounded policy demo for one exact mock source identity."
    )
    parser.add_argument("--source-identity", default="kira")
    parser.add_argument("--policy-file", type=Path, default=default_policy_path)
    args = parser.parse_args(argv)
    sequence_path = Path(__file__).with_name("sample_sequence.json")
    evidence_path = Path(__file__).with_name("evidence.jsonl")

    policy = SafetyPolicy.from_yaml(args.policy_file)
    if policy.common.get("allowed_source_identities") != [args.source_identity]:
        raise ValueError(
            "Demo policy must allow exactly the selected source identity."
        )
    request_guard = RequestGuard(int(policy.common.get("replay_cache_entries", 2048)))
    sequence = json.loads(sequence_path.read_text(encoding="utf-8"))

    if evidence_path.exists():
        evidence_path.unlink()
    evidence = EvidenceChain(evidence_path)

    accepted = 0
    rejected = 0

    for item in sequence:
        payload = dict(item)
        category = payload.pop("category")
        payload["source_identity"] = args.source_identity
        if category == "speech" and args.source_identity != "kira":
            payload["text"] = (
                "Hello. This is a bounded simulator-first intention test; "
                "no running person session is attached."
            )
        result = policy.validate(category, payload)
        request_digest = ""
        if result.accepted:
            replay = request_guard.assess(category, payload)
            request_digest = replay.request_digest
            if not replay.should_dispatch:
                result = ValidationResult.reject(replay.reason_code, replay.detail)
        record = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "intent_id": payload["intent_id"],
            "category": category,
            "accepted": result.accepted,
            "reason_code": result.reason_code,
            "detail": result.detail,
            "request_digest": request_digest,
            "payload": sanitize_payload(category, payload, policy.config.get("evidence", {})),
            "executor": "standalone_simulator_authority",
            "status_scope": "POLICY_ADMISSION_ONLY",
        }
        evidence.append(record)

        label = "ACCEPT" if result.accepted else "REJECT"
        print(
            f"{label:6} {category:10} {payload['intent_id']}: "
            f"{result.reason_code} — {result.detail}"
        )
        accepted += int(result.accepted)
        rejected += int(not result.accepted)

    print(f"\nSelected source identity: {args.source_identity}")
    print(f"Summary: accepted={accepted}, rejected={rejected}")
    valid, record_count, final_hash = EvidenceChain.verify(evidence_path)
    print(f"Evidence records: {record_count}")
    print(f"Evidence chain valid: {valid}")
    print(f"Evidence final SHA-256: {final_hash}")
    print(f"Evidence: {evidence_path}")
    return 0 if accepted == 4 and rejected == 1 and valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
