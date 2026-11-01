"""Shared Euler-to-quaternion conversion without changing frame conventions."""

import math

from geometry_msgs.msg import Quaternion


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

