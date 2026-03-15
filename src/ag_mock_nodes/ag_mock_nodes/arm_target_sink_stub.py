"""Minimal placeholder for a future arm target adapter."""

from __future__ import annotations

import rclpy
from ag_interfaces.msg import TargetInfo
from rclpy.node import Node

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import UAV_TARGET_TOPIC


class ArmTargetSinkStub(Node):
    """A tiny subscriber that confirms target messages reach the arm side."""

    def __init__(self) -> None:
        super().__init__("arm_target_sink_stub")

        self.create_subscription(
            TargetInfo,
            UAV_TARGET_TOPIC,
            self.on_target,
            get_qos_profile_for_topic(UAV_TARGET_TOPIC),
        )
        self.get_logger().info("Arm target sink stub ready. Replace this node with a real arm adapter later.")

    def on_target(self, msg: TargetInfo) -> None:
        self.get_logger().info(
            f"收到抓取目标: id={msg.target_id}, x={msg.pose.position.x:.2f}, "
            f"y={msg.pose.position.y:.2f}, confidence={msg.confidence:.2f}"
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ArmTargetSinkStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
