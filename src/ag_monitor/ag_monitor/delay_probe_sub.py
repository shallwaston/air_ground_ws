"""Subscribe to DelayProbe and print rolling latency statistics."""

from __future__ import annotations

from collections import deque

import rclpy
from ag_interfaces.msg import DelayProbe
from rclpy.node import Node
from std_msgs.msg import String

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import DELAY_PROBE_TOPIC
from ag_network_tools.topic_names import DELAY_REPORT_TOPIC
from ag_network_tools.topic_names import HEARTBEAT_TOPIC


def stamp_to_ns(stamp) -> int:
    """Convert a builtin time message to nanoseconds."""
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


class DelayProbeSub(Node):
    """A readable subscriber for measuring end-to-end message latency."""

    def __init__(self) -> None:
        super().__init__("delay_probe_sub")

        self.declare_parameter("recent_window", 10)
        self.recent_window = max(1, int(self.get_parameter("recent_window").value))
        self.latencies_ms = deque(maxlen=self.recent_window)

        self.create_subscription(
            DelayProbe,
            DELAY_PROBE_TOPIC,
            self.on_probe,
            get_qos_profile_for_topic(DELAY_PROBE_TOPIC),
        )
        self.report_pub = self.create_publisher(
            String,
            DELAY_REPORT_TOPIC,
            get_qos_profile_for_topic(HEARTBEAT_TOPIC),
        )

        self.get_logger().info(f"Delay probe subscriber ready: topic={DELAY_PROBE_TOPIC}")

    def on_probe(self, msg: DelayProbe) -> None:
        now_ns = self.get_clock().now().nanoseconds
        latency_ms = (now_ns - stamp_to_ns(msg.source_stamp)) / 1_000_000.0
        self.latencies_ms.append(latency_ms)

        mean_ms = sum(self.latencies_ms) / len(self.latencies_ms)
        max_ms = max(self.latencies_ms)
        recent_text = ", ".join(f"{value:.2f}" for value in self.latencies_ms)
        summary = (
            f"probe seq={msg.seq} payload_bytes={msg.payload_bytes} "
            f"latency_ms={latency_ms:.2f} mean_ms={mean_ms:.2f} max_ms={max_ms:.2f} recent=[{recent_text}]"
        )

        self.get_logger().info(summary)
        report = String()
        report.data = summary
        self.report_pub.publish(report)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = DelayProbeSub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
