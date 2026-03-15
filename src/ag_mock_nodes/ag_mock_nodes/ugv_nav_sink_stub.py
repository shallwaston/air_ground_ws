"""Receive upstream data and act as a placeholder for a future Nav2 adapter."""

from __future__ import annotations

import rclpy
from ag_interfaces.msg import MapTile
from ag_interfaces.msg import TargetInfo
from rclpy.node import Node

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import UAV_MAP_TILE_TOPIC
from ag_network_tools.topic_names import UAV_TARGET_TOPIC


class UgvNavSinkStub(Node):
    """A minimal sink that confirms the UGV side is receiving useful inputs."""

    def __init__(self) -> None:
        super().__init__("ugv_nav_sink_stub")

        self.latest_tile_seq = None
        self.latest_target_id = "none"

        self.create_subscription(
            MapTile,
            UAV_MAP_TILE_TOPIC,
            self.on_tile,
            get_qos_profile_for_topic(UAV_MAP_TILE_TOPIC),
        )
        self.create_subscription(
            TargetInfo,
            UAV_TARGET_TOPIC,
            self.on_target,
            get_qos_profile_for_topic(UAV_TARGET_TOPIC),
        )
        self.create_timer(5.0, self.print_summary)

        self.get_logger().info("UGV Nav sink stub ready. Replace this node with a future Nav2 adapter.")

    def on_tile(self, msg: MapTile) -> None:
        self.latest_tile_seq = msg.seq
        self.get_logger().info(f"Nav sink stub received map tile seq={msg.seq} ({msg.width}x{msg.height}).")

    def on_target(self, msg: TargetInfo) -> None:
        self.latest_target_id = msg.target_id
        self.get_logger().info(
            f"Nav sink stub received target {msg.target_id} with confidence={msg.confidence:.2f}."
        )

    def print_summary(self) -> None:
        tile_text = "none yet" if self.latest_tile_seq is None else str(self.latest_tile_seq)
        self.get_logger().info(
            f"Nav sink stub summary: latest_tile_seq={tile_text}, latest_target_id={self.latest_target_id}"
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = UgvNavSinkStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
