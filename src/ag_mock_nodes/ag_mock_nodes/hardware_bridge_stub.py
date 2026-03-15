"""Stub placeholder for a future hardware bridge integration."""

from __future__ import annotations

import rclpy
from rclpy.node import Node


class HardwareBridgeStub(Node):
    """Log the expected contract for a future hardware bridge."""

    def __init__(self) -> None:
        super().__init__("hardware_bridge_stub")

        # TODO: Replace the sensor-input side of uav_mock_odom_tf_pub.py and uav_mock_map_tile_pub.py.
        # TODO: Connect this node to real sensors and actuators only after the real hardware interface is known.
        self.expected_subscriptions = [
            "<hardware_bridge/control_or_actuator_cmd_tbd>",
        ]
        self.expected_publications = [
            "<hardware_bridge/lidar_points_tbd>",
            "<hardware_bridge/imu_tbd>",
            "<hardware_bridge/wheel_odom_tbd>",
        ]

        self.create_timer(20.0, self.print_stub_summary)
        self.print_stub_summary()

    def print_stub_summary(self) -> None:
        self.get_logger().info("Hardware bridge stub mode active. No serial, CAN, USB, or vendor driver is running.")
        self.get_logger().info("Expected future subscriptions: " + ", ".join(self.expected_subscriptions))
        self.get_logger().info("Expected future publications: " + ", ".join(self.expected_publications))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = HardwareBridgeStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
