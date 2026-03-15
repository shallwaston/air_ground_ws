"""Check whether key TF frame relationships exist."""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer
from tf2_ros import TransformException
from tf2_ros import TransformListener

from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import FRAME_MAP
from ag_network_tools.topic_names import FRAME_UAV_BASE
from ag_network_tools.topic_names import FRAME_UGV_BASE
from ag_network_tools.topic_names import FRAME_UGV_ODOM
from ag_network_tools.topic_names import TF_STATIC_TOPIC
from ag_network_tools.topic_names import TF_TOPIC


class TfHealthcheck(Node):
    """Verify that the key frame chains required by the MVP are present."""

    def __init__(self) -> None:
        super().__init__("tf_healthcheck")

        self.declare_parameter("check_period_sec", 5.0)
        self.declare_parameter("one_shot", False)

        self.one_shot = bool(self.get_parameter("one_shot").value)
        check_period_sec = max(0.5, float(self.get_parameter("check_period_sec").value))

        self.buffer = Buffer()
        self.listener = TransformListener(
            self.buffer,
            self,
            qos=get_qos_profile_for_topic(TF_TOPIC),
            static_qos=get_qos_profile_for_topic(TF_STATIC_TOPIC),
        )
        self.required_pairs = [
            (FRAME_MAP, FRAME_UAV_BASE),
            (FRAME_MAP, FRAME_UGV_ODOM),
            (FRAME_UGV_ODOM, FRAME_UGV_BASE),
        ]
        self.create_timer(check_period_sec, self.run_check)

        self.get_logger().info("TF healthcheck ready.")

    def run_check(self) -> None:
        missing_pairs = []
        for target_frame, source_frame in self.required_pairs:
            try:
                self.buffer.lookup_transform(target_frame, source_frame, Time())
                self.get_logger().info(f"TF OK: {target_frame} <- {source_frame}")
            except TransformException as exc:
                self.get_logger().warning(f"TF missing: {target_frame} <- {source_frame} ({exc})")
                missing_pairs.append(f"{target_frame}<-{source_frame}")

        if not missing_pairs:
            self.get_logger().info("TF healthcheck passed for all key frame pairs.")

        if self.one_shot:
            self.get_logger().info("One-shot TF check complete, shutting down.")
            rclpy.shutdown()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TfHealthcheck()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
