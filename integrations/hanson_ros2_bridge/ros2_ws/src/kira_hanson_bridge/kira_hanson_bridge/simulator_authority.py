from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.time import Time

from kira_intent_interfaces.msg import (
    ExecutionStatus,
    ExpressionIntent,
    GazeIntent,
    GestureIntent,
    SpeechIntent,
)

from .evidence import EvidenceChain, sanitize_payload
from .policy import SafetyPolicy, ValidationResult
from .request_guard import RequestGuard


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulatorAuthority(Node):
    """Policy authority for the proof of concept.

    Accepted intentions are logged as safe semantic requests. This node does
    not issue joint, motor, navigation, or hardware commands.
    """

    def __init__(self) -> None:
        super().__init__("kira_simulator_authority")

        package_share = Path(get_package_share_directory("kira_hanson_bridge"))
        default_policy = package_share / "config" / "safety_policy.yaml"

        policy_file = self.declare_parameter("policy_file", str(default_policy)).value
        evidence_file = self.declare_parameter(
            "evidence_file", "/tmp/kira_hanson_bridge_evidence_v2.jsonl"
        ).value
        topic_prefix = str(self.declare_parameter("topic_prefix", "kira").value).strip("/")
        if not topic_prefix:
            raise ValueError("topic_prefix must not be empty.")

        self.policy = SafetyPolicy.from_yaml(policy_file)
        self.evidence_file = Path(str(evidence_file))
        self.evidence = EvidenceChain(self.evidence_file)
        self.evidence_config = dict(self.policy.config.get("evidence", {}))
        self.request_guard = RequestGuard(
            int(self.policy.common.get("replay_cache_entries", 2048))
        )
        self.status_sequence = 0

        self.status_publisher = self.create_publisher(
            ExecutionStatus, f"{topic_prefix}/execution_status", 10
        )
        self.create_subscription(
            SpeechIntent, f"{topic_prefix}/intents/speech", self._on_speech, 10
        )
        self.create_subscription(
            GazeIntent, f"{topic_prefix}/intents/gaze", self._on_gaze, 10
        )
        self.create_subscription(
            ExpressionIntent, f"{topic_prefix}/intents/expression", self._on_expression, 10
        )
        self.create_subscription(
            GestureIntent, f"{topic_prefix}/intents/gesture", self._on_gesture, 10
        )

        self.get_logger().info(
            f"Bounded simulator authority ready. Policy={policy_file}; evidence={self.evidence_file}"
        )

    def _age_ms(self, stamp_msg: Any) -> int | None:
        stamp = Time.from_msg(stamp_msg)
        if stamp.nanoseconds <= 0:
            return None
        delta_ns = self.get_clock().now().nanoseconds - stamp.nanoseconds
        return int(delta_ns / 1_000_000)

    def _common(self, msg: Any) -> dict[str, Any]:
        return {
            "intent_id": msg.intent_id,
            "source_identity": msg.source_identity,
            "confidence": float(msg.confidence),
            "ttl_ms": int(msg.ttl_ms),
            "age_ms": self._age_ms(msg.header.stamp),
            "evidence_ref": msg.evidence_ref,
            "header_frame_id": msg.header.frame_id,
        }

    def _on_speech(self, msg: SpeechIntent) -> None:
        payload = {
            **self._common(msg),
            "text": msg.text,
            "voice": msg.voice,
            "max_duration_ms": int(msg.max_duration_ms),
        }
        self._decide("speech", msg.intent_id, payload)

    def _on_gaze(self, msg: GazeIntent) -> None:
        payload = {
            **self._common(msg),
            "target_frame": msg.target_frame,
            "target": {
                "x": float(msg.target.x),
                "y": float(msg.target.y),
                "z": float(msg.target.z),
            },
            "duration_ms": int(msg.duration_ms),
        }
        self._decide("gaze", msg.intent_id, payload)

    def _on_expression(self, msg: ExpressionIntent) -> None:
        payload = {
            **self._common(msg),
            "expression": msg.expression,
            "intensity": float(msg.intensity),
            "duration_ms": int(msg.duration_ms),
        }
        self._decide("expression", msg.intent_id, payload)

    def _on_gesture(self, msg: GestureIntent) -> None:
        payload = {
            **self._common(msg),
            "gesture": msg.gesture,
            "intensity": float(msg.intensity),
            "speed": float(msg.speed),
            "duration_ms": int(msg.duration_ms),
        }
        self._decide("gesture", msg.intent_id, payload)

    def _decide(self, category: str, intent_id: str, payload: dict[str, Any]) -> None:
        result = self.policy.validate(category, payload)
        request_digest = ""
        if result.accepted:
            replay = self.request_guard.assess(category, payload)
            request_digest = replay.request_digest
            if not replay.should_dispatch:
                result = ValidationResult.reject(replay.reason_code, replay.detail)

        status = ExecutionStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.intent_id = intent_id
        status.category = category
        status.accepted = result.accepted
        status.state = "POLICY_ACCEPTED" if result.accepted else "REJECTED"
        status.terminal = not result.accepted
        self.status_sequence += 1
        status.status_sequence = self.status_sequence
        status.reason_code = result.reason_code
        status.executor = "kira_simulator_authority"
        status.official_request_id = ""
        status.evidence_record_hash = ""

        if result.accepted:
            status.detail = (
                "Policy-admitted by bounded simulator authority. "
                "No low-level motor command was emitted by this proof of concept."
            )
        else:
            status.detail = result.detail

        try:
            evidence_record = {
                "recorded_at": utc_now(),
                "intent_id": intent_id,
                "category": category,
                "request_digest": request_digest,
                "payload": sanitize_payload(category, payload, self.evidence_config),
                "accepted": result.accepted,
                "reason_code": result.reason_code,
                "detail": status.detail,
                "executor": status.executor,
                "status_scope": "POLICY_ADMISSION_ONLY",
            }
            status.evidence_record_hash = self.evidence.append(evidence_record)
        except (OSError, OverflowError, TypeError, ValueError) as exc:
            if result.accepted:
                result = ValidationResult.reject(
                    "EVIDENCE_UNAVAILABLE",
                    "The authority withheld policy admission because evidence could not be persisted.",
                )
                status.accepted = False
                status.state = "REJECTED"
                status.terminal = True
                status.reason_code = result.reason_code
                status.detail = result.detail
            self.get_logger().error(f"Could not persist evidence before status publication: {exc}")

        if result.accepted:
            self.get_logger().info(f"ACCEPT {category} {intent_id}")
        else:
            self.get_logger().warning(
                f"REJECT {category} {intent_id}: {result.reason_code} — {result.detail}"
            )
        self.status_publisher.publish(status)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SimulatorAuthority()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
