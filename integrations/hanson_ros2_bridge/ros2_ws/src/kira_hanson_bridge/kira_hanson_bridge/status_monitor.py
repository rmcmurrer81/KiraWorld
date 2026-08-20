from __future__ import annotations

import json

import rclpy
from rclpy.node import Node

from kira_intent_interfaces.msg import ExecutionStatus


class StatusMonitor(Node):
    def __init__(self) -> None:
        super().__init__("kira_execution_status_monitor")
        topic_prefix = str(self.declare_parameter("topic_prefix", "kira").value).strip("/")
        if not topic_prefix:
            raise ValueError("topic_prefix must not be empty.")
        self.create_subscription(
            ExecutionStatus, f"{topic_prefix}/execution_status", self._on_status, 10
        )
        self.get_logger().info("Listening for execution status.")

    def _on_status(self, msg: ExecutionStatus) -> None:
        record = {
            "intent_id": msg.intent_id,
            "category": msg.category,
            "accepted": bool(msg.accepted),
            "state": msg.state,
            "terminal": bool(msg.terminal),
            "status_sequence": int(msg.status_sequence),
            "reason_code": msg.reason_code,
            "detail": msg.detail,
            "executor": msg.executor,
            "official_request_id": msg.official_request_id,
            "evidence_record_hash": msg.evidence_record_hash,
        }
        self.get_logger().info(json.dumps(record, sort_keys=True))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = StatusMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
