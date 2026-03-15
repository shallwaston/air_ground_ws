"""Stub placeholder for a future EKF or localization alignment adapter."""

from __future__ import annotations

import rclpy
from rclpy.node import Node

from ag_network_tools.topic_names import FRAME_MAP
from ag_network_tools.topic_names import FRAME_UGV_ODOM
from ag_network_tools.topic_names import TF_TOPIC


class EkfAdapterStub(Node):
    """Log the expected contract for a future EKF adapter."""

    def __init__(self) -> None:
        super().__init__("ekf_adapter_stub")

        # TODO: Replace frame_alignment_stub.py with a real EKF or localization alignment adapter.
        # TODO: Connect this node to the real fused UGV localization sources later.
        self.expected_subscriptions = [
            "<hardware_bridge/wheel_odom_tbd>",
            "<hardware_bridge/imu_tbd>",
            "<localization/alignment_input_tbd>",
        ]
        self.expected_publications = [
            "<ekf/filtered_odom_tbd>",
            TF_TOPIC,
        ]

        self.create_timer(20.0, self.print_stub_summary)
        self.print_stub_summary()

    def print_stub_summary(self) -> None:
        self.get_logger().info("EKF adapter stub mode active. No real state estimation is running.")
        self.get_logger().info("Expected future subscriptions: " + ", ".join(self.expected_subscriptions))
        self.get_logger().info("Expected future publications: " + ", ".join(self.expected_publications))
        self.get_logger().info(f"Expected future TF contract: {FRAME_MAP} -> {FRAME_UGV_ODOM}")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = EkfAdapterStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
