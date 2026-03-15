"""Publish a configurable map -> ugv/odom placeholder transform."""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import Quaternion
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import FRAME_MAP
from ag_network_tools.topic_names import FRAME_UGV_ODOM
from ag_network_tools.topic_names import TF_TOPIC


def quaternion_from_euler(roll: float, pitch: float, yaw: float) -> Quaternion:
    """Convert Euler angles to a ROS quaternion."""
    qx = math.sin(roll / 2.0) * math.cos(pitch / 2.0) * math.cos(yaw / 2.0) - math.cos(roll / 2.0) * math.sin(
        pitch / 2.0
    ) * math.sin(yaw / 2.0)
    qy = math.cos(roll / 2.0) * math.sin(pitch / 2.0) * math.cos(yaw / 2.0) + math.sin(roll / 2.0) * math.cos(
        pitch / 2.0
    ) * math.sin(yaw / 2.0)
    qz = math.cos(roll / 2.0) * math.cos(pitch / 2.0) * math.sin(yaw / 2.0) - math.sin(roll / 2.0) * math.sin(
        pitch / 2.0
    ) * math.cos(yaw / 2.0)
    qw = math.cos(roll / 2.0) * math.cos(pitch / 2.0) * math.cos(yaw / 2.0) + math.sin(roll / 2.0) * math.sin(
        pitch / 2.0
    ) * math.sin(yaw / 2.0)

    return Quaternion(x=qx, y=qy, z=qz, w=qw)


class FrameAlignmentStub(Node):
    """Placeholder for future map alignment, re-localization, or EKF fusion."""

    def __init__(self) -> None:
        super().__init__("frame_alignment_stub")

        self.declare_parameter("frequency_hz", 10.0)
        self.declare_parameter("x", 0.0)
        self.declare_parameter("y", 0.0)
        self.declare_parameter("z", 0.0)
        self.declare_parameter("roll", 0.0)
        self.declare_parameter("pitch", 0.0)
        self.declare_parameter("yaw", 0.0)

        self.frequency_hz = max(0.1, float(self.get_parameter("frequency_hz").value))
        self.translation = {
            "x": float(self.get_parameter("x").value),
            "y": float(self.get_parameter("y").value),
            "z": float(self.get_parameter("z").value),
        }
        self.rotation = {
            "roll": float(self.get_parameter("roll").value),
            "pitch": float(self.get_parameter("pitch").value),
            "yaw": float(self.get_parameter("yaw").value),
        }

        self.broadcaster = TransformBroadcaster(self, qos=get_qos_profile_for_topic(TF_TOPIC))
        self.create_timer(1.0 / self.frequency_hz, self.on_timer)

        self.get_logger().info(
            "Frame alignment stub ready. Replace this with a future EKF or localization alignment module."
        )

    def on_timer(self) -> None:
        msg = TransformStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = FRAME_MAP
        msg.child_frame_id = FRAME_UGV_ODOM
        msg.transform.translation.x = self.translation["x"]
        msg.transform.translation.y = self.translation["y"]
        msg.transform.translation.z = self.translation["z"]
        msg.transform.rotation = quaternion_from_euler(
            self.rotation["roll"],
            self.rotation["pitch"],
            self.rotation["yaw"],
        )
        self.broadcaster.sendTransform(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = FrameAlignmentStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
