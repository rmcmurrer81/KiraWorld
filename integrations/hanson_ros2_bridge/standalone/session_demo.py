from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "kira_hanson_bridge"
sys.path.insert(0, str(PACKAGE_ROOT))

from kira_hanson_bridge.evidence import EvidenceChain  # noqa: E402
from kira_hanson_bridge.lifecycle import EmbodimentSession  # noqa: E402
from kira_hanson_bridge.policy import SafetyPolicy  # noqa: E402


class DemoClock:
    def __init__(self, initial_ms: int = 1_000_000):
        self.value = initial_ms

    def __call__(self) -> int:
        return self.value

    def advance(self, milliseconds: int) -> None:
        self.value += milliseconds


def main() -> int:
    policy_path = (
        PROJECT_ROOT
        / "ros2_ws"
        / "src"
        / "kira_hanson_bridge"
        / "config"
        / "safety_policy.yaml"
    )
    sequence_path = Path(__file__).with_name("sample_sequence.json")
    evidence_path = Path(__file__).with_name("session_evidence.jsonl")
    if evidence_path.exists():
        evidence_path.unlink()

    policy = SafetyPolicy.from_yaml(policy_path)
    evidence = EvidenceChain(evidence_path)
    sequence = json.loads(sequence_path.read_text(encoding="utf-8"))
    clock = DemoClock()
    session = EmbodimentSession(
        session_id="demo-session-001",
        body_id="little-sophia-simulator",
        source_identity="kira",
        capabilities=("speech", "gaze", "expression", "gesture"),
        session_ttl_ms=60_000,
        heartbeat_timeout_ms=5_000,
        now_ms=clock,
    )

    completed = 0
    rejected = 0
    status_sequence = 0
    evidence_epoch = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    for sequence_number, item in enumerate(sequence, start=1):
        payload = dict(item)
        category = payload.pop("category")
        intent_id = str(payload["intent_id"])
        request = session.request_intent(
            intent_id=intent_id,
            sequence=sequence_number,
            capability=category,
            payload=payload,
        )
        if not request.created:
            raise RuntimeError(f"Demo request was not created: {request.reason_code}")

        decision = policy.validate(category, payload)
        if decision.accepted:
            session.accept(intent_id, detail="Accepted by the bounded policy reference.")
            clock.advance(20)
            session.start(intent_id, detail="Started by the deterministic mock executor.")
            clock.advance(50)
            final = session.complete(
                intent_id,
                detail="Completed by the deterministic mock executor; no robot hardware was used.",
            )
            completed += 1
        else:
            final = session.reject(
                intent_id,
                reason_code=decision.reason_code,
                detail=decision.detail,
            )
            rejected += 1

        for event_index, event in enumerate(final.events):
            status_sequence += 1
            recorded_at = evidence_epoch + timedelta(
                milliseconds=event.at_ms - session.opened_at_ms
            )
            evidence.append(
                {
                    "protocol_version": "0.2-proposal",
                    "session_id": session.session_id,
                    "body_id": session.body_id,
                    "intent_id": intent_id,
                    "intent_sequence": sequence_number,
                    "status_sequence": status_sequence,
                    "category": category,
                    "state": event.state.value,
                    "terminal": final.terminal and event_index == len(final.events) - 1,
                    "reason_code": event.reason_code,
                    "detail": event.detail,
                    "recorded_at_utc": recorded_at.isoformat().replace("+00:00", "Z"),
                    "decision_scope": event.decision_scope,
                    "executor": "deterministic_mock_simulator",
                }
            )

        print(
            f"{final.state.value:9} {category:10} {intent_id}: "
            f"{final.events[-1].reason_code}"
        )
        clock.advance(100)
        if not session.heartbeat():
            raise RuntimeError("Demo session lost its heartbeat unexpectedly.")

    valid, record_count, final_hash = EvidenceChain.verify(evidence_path)
    print(f"\nSummary: completed={completed}, rejected={rejected}")
    print(f"Evidence records: {record_count}")
    print(f"Evidence chain valid: {valid}")
    print(f"Evidence final SHA-256: {final_hash}")
    print(f"Evidence: {evidence_path}")
    return 0 if completed == 4 and rejected == 1 and valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
