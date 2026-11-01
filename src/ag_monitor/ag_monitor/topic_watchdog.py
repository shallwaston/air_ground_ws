"""Inspect whether configured topics exist and have publishers/subscribers."""

from __future__ import annotations

from rclpy.node import Node

from ag_network_tools.node_runner import run_node
from ag_network_tools.topic_names import KEY_TOPICS


class TopicWatchdog(Node):
    """Print topic discovery information in a beginner-friendly format."""

    def __init__(self) -> None:
        super().__init__("topic_watchdog")

        self.declare_parameter("topics", KEY_TOPICS)
        self.declare_parameter("check_period_sec", 5.0)

        self.topics = list(self.get_parameter("topics").value)
        check_period_sec = max(0.5, float(self.get_parameter("check_period_sec").value))
        self.create_timer(check_period_sec, self.print_topic_state)

        self.get_logger().info("Topic watchdog ready. It will report missing publishers/subscribers.")

    def print_topic_state(self) -> None:
        discovered = dict(self.get_topic_names_and_types())
        for topic_name in self.topics:
            topic_types = discovered.get(topic_name, [])
            publisher_count = self.count_publishers(topic_name)
            subscriber_count = self.count_subscribers(topic_name)

            if not topic_types:
                self.get_logger().warning(f"{topic_name}: topic not discovered yet")
                continue

            if publisher_count == 0 or subscriber_count == 0:
                self.get_logger().warning(
                    f"{topic_name}: types={topic_types} publishers={publisher_count} subscribers={subscriber_count}"
                )
            else:
                self.get_logger().info(
                    f"{topic_name}: types={topic_types} publishers={publisher_count} subscribers={subscriber_count}"
                )


def main(args: list[str] | None = None) -> None:
    run_node(TopicWatchdog, args)
