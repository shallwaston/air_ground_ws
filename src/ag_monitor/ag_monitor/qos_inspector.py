"""Read the QoS YAML mapping and print the chosen policy for each topic."""

from __future__ import annotations

import rclpy
from rclpy.node import Node

from ag_network_tools.qos_profiles import describe_qos_for_topic
from ag_network_tools.qos_profiles import get_all_topic_configs


class QosInspector(Node):
    """Print the configured QoS strategies at startup."""

    def __init__(self) -> None:
        super().__init__("qos_inspector")

        self.declare_parameter("qos_config_path", "")
        self.declare_parameter("repeat_period_sec", 0.0)

        self.qos_config_path = str(self.get_parameter("qos_config_path").value)
        repeat_period_sec = float(self.get_parameter("repeat_period_sec").value)

        self.print_qos_summary()
        if repeat_period_sec > 0.0:
            self.create_timer(repeat_period_sec, self.print_qos_summary)

    def print_qos_summary(self) -> None:
        topic_configs = get_all_topic_configs(self.qos_config_path or None)
        self.get_logger().info("Configured QoS profiles:")
        for topic_name in sorted(topic_configs.keys()):
            self.get_logger().info("  " + describe_qos_for_topic(topic_name, self.qos_config_path or None))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = QosInspector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
