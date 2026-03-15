"""Publish mock MapTile messages with configurable payload size."""

from __future__ import annotations

import math

import rclpy
from ag_interfaces.msg import MapTile
from geometry_msgs.msg import Quaternion
from rclpy.node import Node

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import FRAME_MAP
from ag_network_tools.topic_names import UAV_MAP_TILE_TOPIC


class UavMockMapTilePub(Node):
    """Generate synthetic 2.5D map tiles for bandwidth and latency tests."""

    def __init__(self) -> None:
        super().__init__("uav_mock_map_tile_pub")

        self.declare_parameter("frequency_hz", 2.0)
        self.declare_parameter("tile_width", 64)
        self.declare_parameter("tile_height", 64)
        self.declare_parameter("resolution", 0.2)
        self.declare_parameter("payload_scale", 1.0)
        self.declare_parameter("origin_x", -5.0)
        self.declare_parameter("origin_y", -5.0)
        self.declare_parameter("origin_z", 0.0)

        self.frequency_hz = max(0.1, float(self.get_parameter("frequency_hz").value))
        self.tile_width = max(1, int(self.get_parameter("tile_width").value))
        self.tile_height = max(1, int(self.get_parameter("tile_height").value))
        self.resolution = max(0.01, float(self.get_parameter("resolution").value))
        self.payload_scale = max(0.25, float(self.get_parameter("payload_scale").value))
        self.origin_x = float(self.get_parameter("origin_x").value)
        self.origin_y = float(self.get_parameter("origin_y").value)
        self.origin_z = float(self.get_parameter("origin_z").value)

        self.publisher = self.create_publisher(
            MapTile,
            UAV_MAP_TILE_TOPIC,
            get_qos_profile_for_topic(UAV_MAP_TILE_TOPIC),
        )
        self.seq = 0
        self.phase = 0.0
        self.timer = self.create_timer(1.0 / self.frequency_hz, self.on_timer)

        actual_width, actual_height = self.get_effective_dimensions()
        estimated_payload_bytes = actual_width * actual_height * (4 + 1)
        self.get_logger().info(
            "Mock map tile publisher ready: "
            f"topic={UAV_MAP_TILE_TOPIC}, frequency={self.frequency_hz:.2f} Hz, "
            f"effective_tile={actual_width}x{actual_height}, estimated_payload~{estimated_payload_bytes} B"
        )

    def get_effective_dimensions(self) -> tuple[int, int]:
        """Scale the logical tile dimensions to make large-message tests easy."""
        width = max(1, int(round(self.tile_width * self.payload_scale)))
        height = max(1, int(round(self.tile_height * self.payload_scale)))
        return width, height

    def on_timer(self) -> None:
        """Publish one synthetic tile sample."""
        now = self.get_clock().now().to_msg()
        width, height = self.get_effective_dimensions()
        element_count = width * height

        elevation = []
        traversability = []
        for index in range(element_count):
            row = index // width
            col = index % width
            height_value = 0.5 * math.sin(0.07 * row + self.phase) + 0.25 * math.cos(0.11 * col)
            elevation.append(float(height_value))
            traversability.append(255 if abs(height_value) < 0.45 else 64)

        msg = MapTile()
        msg.header.stamp = now
        msg.header.frame_id = FRAME_MAP
        msg.resolution = float(self.resolution)
        msg.width = width
        msg.height = height
        msg.origin.position.x = self.origin_x
        msg.origin.position.y = self.origin_y
        msg.origin.position.z = self.origin_z
        msg.origin.orientation = Quaternion(w=1.0)
        msg.elevation = elevation
        msg.traversability = traversability
        msg.source_stamp = now
        msg.seq = self.seq
        self.publisher.publish(msg)

        self.phase += 0.15
        self.seq += 1


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = UavMockMapTilePub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
