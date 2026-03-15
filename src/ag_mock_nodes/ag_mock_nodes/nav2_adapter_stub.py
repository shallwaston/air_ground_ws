"""Stub placeholder for a future Nav2 adapter integration."""

from __future__ import annotations

import rclpy
from rclpy.node import Node

from ag_network_tools.topic_names import UAV_MAP_TILE_TOPIC
from ag_network_tools.topic_names import UAV_TARGET_TOPIC


class Nav2AdapterStub(Node):
    """Log the expected contract for a future Nav2 bridge."""

    def __init__(self) -> None:
        super().__init__("nav2_adapter_stub")

        # TODO: Replace ugv_nav_sink_stub.py with a real Nav2 adapter.
        # TODO: Connect this node to Nav2 costmap, planning, and localization glue code later.
        self.expected_subscriptions = [
            UAV_MAP_TILE_TOPIC,
            UAV_TARGET_TOPIC,
            "<ekf/filtered_odom_tbd>",
        ]
        self.expected_publications = [
            "<nav2_adapter/costmap_input_tbd>",
            "<nav2_adapter/goal_or_path_tbd>",
        ]

        self.create_timer(20.0, self.print_stub_summary)
        self.print_stub_summary()

    def print_stub_summary(self) -> None:
        self.get_logger().info("Nav2 adapter stub mode active. No real navigation stack is running.")
        self.get_logger().info("Expected future subscriptions: " + ", ".join(self.expected_subscriptions))
        self.get_logger().info("Expected future publications: " + ", ".join(self.expected_publications))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = Nav2AdapterStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
