"""Stub placeholder for a future arm target adapter integration."""

from __future__ import annotations

import rclpy
from rclpy.node import Node

from ag_network_tools.topic_names import UAV_TARGET_TOPIC


class ArmTargetAdapterStub(Node):
    """Log the expected contract for a future arm target adapter."""

    def __init__(self) -> None:
        super().__init__("arm_target_adapter_stub")

        # TODO: Replace arm_target_sink_stub.py with a real arm target adapter.
        # TODO: Connect this node to the real arm planning and grasp execution stack later.
        self.expected_subscriptions = [
            UAV_TARGET_TOPIC,
        ]
        self.expected_publications = [
            "<arm_target_adapter/command_tbd>",
            "<arm_target_adapter/status_tbd>",
        ]

        self.create_timer(20.0, self.print_stub_summary)
        self.print_stub_summary()

    def print_stub_summary(self) -> None:
        self.get_logger().info("Arm target adapter stub mode active. No real arm control is running.")
        self.get_logger().info("Expected future subscriptions: " + ", ".join(self.expected_subscriptions))
        self.get_logger().info("Expected future publications: " + ", ".join(self.expected_publications))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ArmTargetAdapterStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
