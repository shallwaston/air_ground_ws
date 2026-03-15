"""Publish a low-rate mock target stream for perception-to-ground testing."""

from __future__ import annotations

import math

import rclpy
from ag_interfaces.msg import TargetInfo
from geometry_msgs.msg import Quaternion
from rclpy.node import Node

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import FRAME_MAP
from ag_network_tools.topic_names import UAV_TARGET_TOPIC


class UavMockTargetPub(Node):
    """Generate simple moving targets for downstream sink stubs."""

    def __init__(self) -> None:
        super().__init__("uav_mock_target_pub")

        self.declare_parameter("frequency_hz", 1.0)
        self.declare_parameter("radius_m", 3.0)
        self.declare_parameter("height_m", 0.8)

        self.frequency_hz = max(0.1, float(self.get_parameter("frequency_hz").value))
        self.radius_m = max(0.1, float(self.get_parameter("radius_m").value))
        self.height_m = float(self.get_parameter("height_m").value)

        self.publisher = self.create_publisher(
            TargetInfo,
            UAV_TARGET_TOPIC,
            get_qos_profile_for_topic(UAV_TARGET_TOPIC),
        )
        self.seq = 0
        self.start_time_sec = self.get_clock().now().nanoseconds / 1e9
        self.timer = self.create_timer(1.0 / self.frequency_hz, self.on_timer)

        self.get_logger().info(
            f"Mock target publisher ready: topic={UAV_TARGET_TOPIC}, frequency={self.frequency_hz:.2f} Hz"
        )

    def on_timer(self) -> None:
        now = self.get_clock().now().to_msg()
        t = self.get_clock().now().nanoseconds / 1e9 - self.start_time_sec

        msg = TargetInfo()
        msg.header.stamp = now
        msg.header.frame_id = FRAME_MAP
        msg.target_id = f"mock_target_{self.seq % 4}"
        msg.pose.position.x = self.radius_m * math.cos(0.25 * t)
        msg.pose.position.y = self.radius_m * math.sin(0.25 * t)
        msg.pose.position.z = self.height_m
        msg.pose.orientation = Quaternion(w=1.0)
        msg.confidence = float(0.85 + 0.1 * math.sin(0.3 * t))
        self.publisher.publish(msg)
        self.seq += 1


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = UavMockTargetPub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
