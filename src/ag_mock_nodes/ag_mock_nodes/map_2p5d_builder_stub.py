"""Stub placeholder for a future 2.5D map builder integration."""

from __future__ import annotations

import rclpy
from rclpy.node import Node

from ag_network_tools.topic_names import UAV_MAP_TILE_TOPIC
from ag_network_tools.topic_names import UAV_ODOM_TOPIC


class Map2p5dBuilderStub(Node):
    """Log the expected contract for a future 2.5D map builder."""

    def __init__(self) -> None:
        super().__init__("map_2p5d_builder_stub")

        # TODO: Replace uav_mock_map_tile_pub.py with a real 2.5D map builder adapter.
        # TODO: Connect this node to the real mapping stack once field sensor topics are ready.
        self.expected_subscriptions = [
            UAV_ODOM_TOPIC,
            "<hardware_bridge/lidar_points_tbd>",
        ]
        self.expected_publications = [
            UAV_MAP_TILE_TOPIC,
        ]

        self.create_timer(20.0, self.print_stub_summary)
        self.print_stub_summary()

    def print_stub_summary(self) -> None:
        self.get_logger().info("2.5D map builder stub mode active. No real map generation is running.")
        self.get_logger().info("Expected future subscriptions: " + ", ".join(self.expected_subscriptions))
        self.get_logger().info("Expected future publications: " + ", ".join(self.expected_publications))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = Map2p5dBuilderStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
