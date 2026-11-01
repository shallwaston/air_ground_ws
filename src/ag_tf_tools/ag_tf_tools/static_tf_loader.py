"""Load static transforms from YAML and publish them on /tf_static."""

from __future__ import annotations

import math
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster

from ag_network_tools.node_runner import run_node
from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import TF_STATIC_TOPIC
from ag_network_tools.transforms import quaternion_from_euler

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
        self.broadcaster = StaticTransformBroadcaster(
            self, qos=get_qos_profile_for_topic(TF_STATIC_TOPIC))
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
            parsed = yaml.safe_load(stream)
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict) or not isinstance(parsed.get('transforms', []), list):
            raise ValueError('Static TF config must contain a transforms list')

        transforms = []
        parents = {}
        now = self.get_clock().now().to_msg()
        for entry in parsed.get("transforms", []):
            if not isinstance(entry, dict):
                raise ValueError('Each static transform must be a mapping')
            parent, child = entry.get('parent'), entry.get('child')
            if (not isinstance(parent, str) or not isinstance(child, str)
                    or not parent or not child or parent == child
                    or parent.startswith('/') or child.startswith('/')):
                raise ValueError('TF frames must be nonempty, distinct names without leading slashes')
            if child in parents:
                raise ValueError(f'Duplicate static TF child: {child}')
            parents[child] = parent
            ancestor = parent
            while ancestor in parents:
                if ancestor == child:
                    raise ValueError(f'Static TF cycle involving {child}')
                ancestor = parents[ancestor]
            msg = TransformStamped()
            msg.header.stamp = now
            msg.header.frame_id = entry.get("parent", "")
            msg.child_frame_id = entry.get("child", "")
            translation = entry.get("translation", {})
            rotation = entry.get("rotation_rpy_rad", {})
            if not isinstance(translation, dict) or not isinstance(rotation, dict):
                raise ValueError('TF translation and rotation must be mappings')
            values = [float(translation.get(axis, 0.0)) for axis in ('x', 'y', 'z')]
            values += [float(rotation.get(axis, 0.0)) for axis in ('roll', 'pitch', 'yaw')]
            if not all(math.isfinite(value) for value in values):
                raise ValueError('TF coordinates must be finite')
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
    run_node(StaticTfLoader, args)
