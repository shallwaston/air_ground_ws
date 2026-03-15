"""Publish mock UAV odometry and TF for single-machine and distributed tests."""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import Quaternion
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import FRAME_MAP
from ag_network_tools.topic_names import FRAME_UAV_BASE
from ag_network_tools.topic_names import TF_TOPIC
from ag_network_tools.topic_names import UAV_ODOM_TOPIC


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


class UavMockOdomTfPub(Node):
    """A simple circular-motion UAV publisher for MVP bringup."""

    def __init__(self) -> None:
        super().__init__("uav_mock_odom_tf_pub")

        self.declare_parameter("frequency_hz", 30.0)
        self.declare_parameter("radius_m", 8.0)
        self.declare_parameter("speed_mps", 2.0)
        self.declare_parameter("altitude_m", 2.5)
        self.declare_parameter("vertical_wave_m", 0.5)

        self.frequency_hz = max(1.0, float(self.get_parameter("frequency_hz").value))
        self.radius_m = max(0.1, float(self.get_parameter("radius_m").value))
        self.speed_mps = max(0.1, float(self.get_parameter("speed_mps").value))
        self.altitude_m = float(self.get_parameter("altitude_m").value)
        self.vertical_wave_m = max(0.0, float(self.get_parameter("vertical_wave_m").value))

        self.odom_pub = self.create_publisher(
            Odometry,
            UAV_ODOM_TOPIC,
            get_qos_profile_for_topic(UAV_ODOM_TOPIC),
        )
        self.tf_broadcaster = TransformBroadcaster(self, qos=get_qos_profile_for_topic(TF_TOPIC))

        self.start_time_sec = self.get_clock().now().nanoseconds / 1e9
        self.timer = self.create_timer(1.0 / self.frequency_hz, self.on_timer)

        self.get_logger().info(
            "Mock UAV odom/TF publisher ready: "
            f"topic={UAV_ODOM_TOPIC}, frequency={self.frequency_hz:.1f} Hz, radius={self.radius_m:.1f} m"
        )

    def on_timer(self) -> None:
        """Publish one mock UAV pose sample and matching TF transform."""
        now = self.get_clock().now()
        t = now.nanoseconds / 1e9 - self.start_time_sec
        omega = self.speed_mps / self.radius_m

        x = self.radius_m * math.cos(omega * t)
        y = self.radius_m * math.sin(omega * t)
        z = self.altitude_m + self.vertical_wave_m * math.sin(0.5 * omega * t)
        yaw = omega * t + math.pi / 2.0
        orientation = quaternion_from_euler(0.0, 0.0, yaw)

        odom_msg = Odometry()
        odom_msg.header.stamp = now.to_msg()
        odom_msg.header.frame_id = FRAME_MAP
        odom_msg.child_frame_id = FRAME_UAV_BASE
        odom_msg.pose.pose.position.x = x
        odom_msg.pose.pose.position.y = y
        odom_msg.pose.pose.position.z = z
        odom_msg.pose.pose.orientation = orientation
        odom_msg.twist.twist.linear.x = -self.speed_mps * math.sin(omega * t)
        odom_msg.twist.twist.linear.y = self.speed_mps * math.cos(omega * t)
        odom_msg.twist.twist.linear.z = 0.25 * self.vertical_wave_m * math.cos(0.5 * omega * t)
        odom_msg.twist.twist.angular.z = omega
        self.odom_pub.publish(odom_msg)

        tf_msg = TransformStamped()
        tf_msg.header.stamp = odom_msg.header.stamp
        tf_msg.header.frame_id = FRAME_MAP
        tf_msg.child_frame_id = FRAME_UAV_BASE
        tf_msg.transform.translation.x = x
        tf_msg.transform.translation.y = y
        tf_msg.transform.translation.z = z
        tf_msg.transform.rotation = orientation
        self.tf_broadcaster.sendTransform(tf_msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = UavMockOdomTfPub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
