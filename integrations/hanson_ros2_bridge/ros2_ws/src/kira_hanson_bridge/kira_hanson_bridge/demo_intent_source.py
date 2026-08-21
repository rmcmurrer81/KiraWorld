from __future__ import annotations

from collections.abc import Callable
import re
import uuid

import rclpy
from rclpy.node import Node

from kira_intent_interfaces.msg import (
    ExpressionIntent,
    GazeIntent,
    GestureIntent,
    SpeechIntent,
)


class DemoIntentSource(Node):
    SAFE_SOURCE_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

    def __init__(self) -> None:
        super().__init__("kira_demo_intent_source")
        topic_prefix = str(self.declare_parameter("topic_prefix", "kira").value).strip("/")
        if not topic_prefix:
            raise ValueError("topic_prefix must not be empty.")
        self.source_identity = str(
            self.declare_parameter("source_identity", "kira").value
        )
        if not self.SAFE_SOURCE_IDENTITY.fullmatch(self.source_identity):
            raise ValueError("source_identity must be one bounded ASCII identifier.")
        self.speech_pub = self.create_publisher(SpeechIntent, f"{topic_prefix}/intents/speech", 10)
        self.gaze_pub = self.create_publisher(GazeIntent, f"{topic_prefix}/intents/gaze", 10)
        self.expression_pub = self.create_publisher(
            ExpressionIntent, f"{topic_prefix}/intents/expression", 10
        )
        self.gesture_pub = self.create_publisher(
            GestureIntent, f"{topic_prefix}/intents/gesture", 10
        )

        self.steps: list[Callable[[], None]] = [
            self.publish_speech,
            self.publish_gaze,
            self.publish_expression,
            self.publish_wave,
            self.publish_rejected_gesture,
        ]
        self.index = 0
        self.timer = self.create_timer(1.0, self._tick)
        self.get_logger().info("Demo sequence armed.")

    def _base(self, msg: object, evidence_ref: str) -> None:
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "world"
        msg.intent_id = str(uuid.uuid4())
        msg.source_identity = self.source_identity
        msg.confidence = 0.95
        msg.ttl_ms = 5000
        msg.evidence_ref = evidence_ref

    def _tick(self) -> None:
        if self.index >= len(self.steps):
            self.timer.cancel()
            self.get_logger().info(
                "Demo sequence complete. The final gesture should be rejected."
            )
            return
        self.steps[self.index]()
        self.index += 1

    def publish_speech(self) -> None:
        msg = SpeechIntent()
        self._base(msg, "demo:conversation:welcome")
        if self.source_identity == "kira":
            msg.text = "Hello. I am Kira. This is a bounded simulator-first intention test."
        else:
            msg.text = (
                "Hello. This is a bounded simulator-first intention test; "
                "no running person session is attached."
            )
        msg.voice = "default"
        msg.max_duration_ms = 10000
        self.speech_pub.publish(msg)
        self.get_logger().info("Published bounded speech intention.")

    def publish_gaze(self) -> None:
        msg = GazeIntent()
        self._base(msg, "demo:target:visitor")
        msg.target_frame = "world"
        msg.target.x = 0.6
        msg.target.y = 0.0
        msg.target.z = 1.4
        msg.duration_ms = 2500
        self.gaze_pub.publish(msg)
        self.get_logger().info("Published bounded gaze intention.")

    def publish_expression(self) -> None:
        msg = ExpressionIntent()
        self._base(msg, "demo:affect:attentive")
        msg.expression = "attentive"
        msg.intensity = 0.65
        msg.duration_ms = 3000
        self.expression_pub.publish(msg)
        self.get_logger().info("Published bounded expression intention.")

    def publish_wave(self) -> None:
        msg = GestureIntent()
        self._base(msg, "demo:social:wave")
        msg.gesture = "wave"
        msg.intensity = 0.5
        msg.speed = 0.4
        msg.duration_ms = 2500
        self.gesture_pub.publish(msg)
        self.get_logger().info("Published bounded wave intention.")

    def publish_rejected_gesture(self) -> None:
        msg = GestureIntent()
        self._base(msg, "demo:negative-test:unsupported-motion")
        msg.gesture = "unbounded_spin"
        msg.intensity = 1.0
        msg.speed = 1.0
        msg.duration_ms = 8000
        self.gesture_pub.publish(msg)
        self.get_logger().info("Published intentionally unsupported gesture.")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = DemoIntentSource()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
