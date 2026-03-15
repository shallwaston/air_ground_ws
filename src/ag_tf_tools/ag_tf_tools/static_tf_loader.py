"""Load static transforms from YAML and publish them on /tf_static."""

from __future__ import annotations

import math
from pathlib import Path

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Quaternion
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster


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


def default_config_path() -> str:
    """Locate the packaged sample static transform YAML."""
    share_dir = Path(get_package_share_directory("ag_bringup"))
    return str(share_dir / "config" / "static_transforms.yaml")


class StaticTfLoader(Node):
    """Read a YAML file and broadcast each listed static transform."""

    def __init__(self) -> None:
        super().__init__("static_tf_loader")

        self.declare_parameter("config_path", default_config_path())
        self.config_path = str(self.get_parameter("config_path").value)
        self.broadcaster = StaticTransformBroadcaster(self)
        self.transforms = self.load_transforms(self.config_path)

        if self.transforms:
            self.broadcaster.sendTransform(self.transforms)
            self.get_logger().info(
                f"Published {len(self.transforms)} static transform(s) from {self.config_path}"
            )
        else:
            self.get_logger().warning(f"No static transforms were loaded from {self.config_path}")

    def load_transforms(self, config_path: str) -> list[TransformStamped]:
        path = Path(config_path)
        if not path.exists():
            self.get_logger().warning(f"Static TF config not found: {config_path}")
            return []

        with path.open("r", encoding="utf-8") as stream:
            parsed = yaml.safe_load(stream) or {}

        transforms = []
        now = self.get_clock().now().to_msg()
        for entry in parsed.get("transforms", []):
            msg = TransformStamped()
            msg.header.stamp = now
            msg.header.frame_id = entry.get("parent", "")
            msg.child_frame_id = entry.get("child", "")
            translation = entry.get("translation", {})
            rotation = entry.get("rotation_rpy_rad", {})
            msg.transform.translation.x = float(translation.get("x", 0.0))
            msg.transform.translation.y = float(translation.get("y", 0.0))
            msg.transform.translation.z = float(translation.get("z", 0.0))
            msg.transform.rotation = quaternion_from_euler(
                float(rotation.get("roll", 0.0)),
                float(rotation.get("pitch", 0.0)),
                float(rotation.get("yaw", 0.0)),
            )
            transforms.append(msg)

        return transforms


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = StaticTfLoader()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
