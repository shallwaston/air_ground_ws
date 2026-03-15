"""Generic heartbeat publisher used by launch files to report liveness."""

from __future__ import annotations

import rclpy
from ag_interfaces.msg import Heartbeat
from rclpy.node import Node

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import HEARTBEAT_TOPIC


class HeartbeatPub(Node):
    """Publish simple liveness messages for beginners and system monitors."""

    def __init__(self) -> None:
        super().__init__("heartbeat_pub")

        self.declare_parameter("frequency_hz", 1.0)
        self.declare_parameter("node_name", self.get_name())
        self.declare_parameter("role", "generic")
        self.declare_parameter("status", 1)
        self.declare_parameter("detail", "alive")

        self.frequency_hz = max(0.1, float(self.get_parameter("frequency_hz").value))
        self.reported_node_name = str(self.get_parameter("node_name").value)
        self.role = str(self.get_parameter("role").value)
        self.status = int(self.get_parameter("status").value)
        self.detail = str(self.get_parameter("detail").value)

        self.publisher = self.create_publisher(
            Heartbeat,
            HEARTBEAT_TOPIC,
            get_qos_profile_for_topic(HEARTBEAT_TOPIC),
        )
        self.sequence = 0
        self.timer = self.create_timer(1.0 / self.frequency_hz, self.on_timer)

        self.get_logger().info(
            f"Heartbeat publisher ready: topic={HEARTBEAT_TOPIC}, role={self.role}, node_name={self.reported_node_name}"
        )

    def on_timer(self) -> None:
        msg = Heartbeat()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ""
        msg.node_name = self.reported_node_name
        msg.role = self.role
        msg.status = self.status
        msg.detail = f"{self.detail}; seq={self.sequence}"
        self.publisher.publish(msg)
        self.sequence += 1


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = HeartbeatPub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
