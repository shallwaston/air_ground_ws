"""Stub placeholder for a future FAST-LIO2 adapter integration."""

from __future__ import annotations

import rclpy
from rclpy.node import Node

from ag_network_tools.topic_names import TF_TOPIC
from ag_network_tools.topic_names import UAV_ODOM_TOPIC


class Fastlio2AdapterStub(Node):
    """Log the expected contract for a future FAST-LIO2 adapter."""

    def __init__(self) -> None:
        super().__init__("fastlio2_adapter_stub")

        # TODO: Replace uav_mock_odom_tf_pub.py with a real FAST-LIO2 adapter.
        # TODO: Connect this node to the real FAST-LIO2 output pipeline on target hardware.
        self.expected_subscriptions = [
            "<hardware_bridge/lidar_points_tbd>",
            "<hardware_bridge/imu_tbd>",
        ]
        self.expected_publications = [
            UAV_ODOM_TOPIC,
            TF_TOPIC,
        ]

        self.create_timer(20.0, self.print_stub_summary)
        self.print_stub_summary()

    def print_stub_summary(self) -> None:
        self.get_logger().info("FAST-LIO2 adapter stub mode active. No real localization logic is running.")
        self.get_logger().info("Expected future subscriptions: " + ", ".join(self.expected_subscriptions))
        self.get_logger().info("Expected future publications: " + ", ".join(self.expected_publications))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = Fastlio2AdapterStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
