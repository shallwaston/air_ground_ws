"""Receive mock map tiles and print beginner-friendly timing diagnostics."""

from __future__ import annotations

from collections import deque

import rclpy
from ag_interfaces.msg import MapTile
from rclpy.node import Node
from std_msgs.msg import String

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import DELAY_REPORT_TOPIC
from ag_network_tools.topic_names import HEARTBEAT_TOPIC
from ag_network_tools.topic_names import UAV_MAP_TILE_TOPIC


def stamp_to_ns(stamp) -> int:
    """Convert a ROS builtin time message to nanoseconds."""
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


class UgvMapTileSub(Node):
    """UGV-side receiver for mock map tiles."""

    def __init__(self) -> None:
        super().__init__("ugv_map_tile_sub")

        self.declare_parameter("log_every_n", 1)
        self.log_every_n = max(1, int(self.get_parameter("log_every_n").value))

        self.subscription = self.create_subscription(
            MapTile,
            UAV_MAP_TILE_TOPIC,
            self.on_tile,
            get_qos_profile_for_topic(UAV_MAP_TILE_TOPIC),
        )
        self.report_pub = self.create_publisher(
            String,
            DELAY_REPORT_TOPIC,
            get_qos_profile_for_topic(HEARTBEAT_TOPIC),
        )

        self.last_receive_ns = None
        self.last_seq = None
        self.delay_window_ms = deque(maxlen=20)
        self.message_count = 0

        self.get_logger().info(f"UGV map tile subscriber ready: topic={UAV_MAP_TILE_TOPIC}")

    def on_tile(self, msg: MapTile) -> None:
        now_ns = self.get_clock().now().nanoseconds
        source_ns = stamp_to_ns(msg.source_stamp)
        delay_ms = (now_ns - source_ns) / 1_000_000.0 if source_ns > 0 else -1.0
        receive_hz = 0.0
        if self.last_receive_ns is not None and now_ns > self.last_receive_ns:
            receive_hz = 1e9 / float(now_ns - self.last_receive_ns)

        self.delay_window_ms.append(delay_ms)
        self.message_count += 1
        loss_hint = ""
        if self.last_seq is not None and msg.seq != self.last_seq + 1:
            loss_hint = f" seq_jump={msg.seq - self.last_seq}"

        summary = (
            f"tile seq={msg.seq} size={msg.width}x{msg.height} "
            f"rx_hz={receive_hz:.2f} latency_ms={delay_ms:.2f}{loss_hint}"
        )

        if self.message_count % self.log_every_n == 0:
            self.get_logger().info(summary)

        report = String()
        report.data = summary
        self.report_pub.publish(report)

        self.last_receive_ns = now_ns
        self.last_seq = msg.seq


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = UgvMapTileSub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
