"""Publish DelayProbe messages for end-to-end latency checks."""

from __future__ import annotations

import rclpy
from ag_interfaces.msg import DelayProbe
from rclpy.node import Node

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import DELAY_PROBE_TOPIC


class DelayProbePub(Node):
    """A lightweight latency probe publisher."""

    def __init__(self) -> None:
        super().__init__("delay_probe_pub")

        self.declare_parameter("frequency_hz", 2.0)
        self.declare_parameter("payload_bytes", 1024)

        self.frequency_hz = max(0.1, float(self.get_parameter("frequency_hz").value))
        self.payload_bytes = max(0, int(self.get_parameter("payload_bytes").value))
        self.publisher = self.create_publisher(
            DelayProbe,
            DELAY_PROBE_TOPIC,
            get_qos_profile_for_topic(DELAY_PROBE_TOPIC),
        )
        self.seq = 0
        self.timer = self.create_timer(1.0 / self.frequency_hz, self.on_timer)

        self.get_logger().info(
            f"Delay probe publisher ready: topic={DELAY_PROBE_TOPIC}, payload_bytes={self.payload_bytes}"
        )

    def on_timer(self) -> None:
        msg = DelayProbe()
        now = self.get_clock().now().to_msg()
        msg.header.stamp = now
        msg.header.frame_id = ""
        msg.seq = self.seq
        msg.source_stamp = now
        msg.payload_bytes = self.payload_bytes
        self.publisher.publish(msg)
        self.seq += 1


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = DelayProbePub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
