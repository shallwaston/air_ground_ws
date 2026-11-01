"""System summary node that watches heartbeats and critical topics."""

from __future__ import annotations

from typing import Dict
from time import monotonic_ns

from ag_interfaces.msg import DelayProbe
from ag_interfaces.msg import Heartbeat
from ag_interfaces.msg import MapTile
from ag_interfaces.msg import TargetInfo
from nav_msgs.msg import Odometry
from rclpy.context import Context
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from std_msgs.msg import String

from ag_monitor.health_logic import age_seconds, expired_heartbeat_names
from ag_network_tools.node_runner import run_node
from ag_network_tools.qos_profiles import get_qos_profile_for_topic
from ag_network_tools.topic_names import DELAY_PROBE_TOPIC
from ag_network_tools.topic_names import DELAY_REPORT_TOPIC
from ag_network_tools.topic_names import HEARTBEAT_TOPIC
from ag_network_tools.topic_names import UAV_MAP_TILE_TOPIC
from ag_network_tools.topic_names import UAV_ODOM_TOPIC
from ag_network_tools.topic_names import UAV_TARGET_TOPIC


class SystemMonitor(Node):
    """Print a readable summary of overall MVP health."""

    def __init__(self, *, context: Context | None = None) -> None:
        super().__init__("system_monitor", context=context)

        self.declare_parameter("timeout_sec", 5.0)
        self.declare_parameter("summary_period_sec", 2.0)

        self.timeout_sec = max(0.5, float(self.get_parameter("timeout_sec").value))
        summary_period_sec = max(0.5, float(self.get_parameter("summary_period_sec").value))

        self.last_seen_ns: Dict[str, int] = {}
        self.heartbeats: Dict[str, str] = {}
        self.heartbeat_last_seen_ns: Dict[str, int] = {}
        self.latest_delay_report = "no delay report yet"

        self.create_subscription(
            Heartbeat,
            HEARTBEAT_TOPIC,
            self.on_heartbeat,
            get_qos_profile_for_topic(HEARTBEAT_TOPIC),
        )
        self.create_subscription(
            Odometry,
            UAV_ODOM_TOPIC,
            lambda msg: self.mark_seen(UAV_ODOM_TOPIC),
            get_qos_profile_for_topic(UAV_ODOM_TOPIC),
        )
        self.create_subscription(
            MapTile,
            UAV_MAP_TILE_TOPIC,
            lambda msg: self.mark_seen(UAV_MAP_TILE_TOPIC),
            get_qos_profile_for_topic(UAV_MAP_TILE_TOPIC),
        )
        self.create_subscription(
            TargetInfo,
            UAV_TARGET_TOPIC,
            lambda msg: self.mark_seen(UAV_TARGET_TOPIC),
            get_qos_profile_for_topic(UAV_TARGET_TOPIC),
        )
        self.create_subscription(
            DelayProbe,
            DELAY_PROBE_TOPIC,
            lambda msg: self.mark_seen(DELAY_PROBE_TOPIC),
            get_qos_profile_for_topic(DELAY_PROBE_TOPIC),
        )
        self.create_subscription(
            String,
            DELAY_REPORT_TOPIC,
            self.on_delay_report,
            get_qos_profile_for_topic(DELAY_REPORT_TOPIC),
        )
        # Arrival liveness must continue to run while /clock is paused or reset.
        self.summary_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.summary_timer = self.create_timer(
            summary_period_sec, self.print_summary, clock=self.summary_clock)

        self.get_logger().info("System monitor ready. It will warn when key topics go quiet.")

    def mark_seen(self, topic_name: str) -> None:
        self.last_seen_ns[topic_name] = monotonic_ns()

    def on_heartbeat(self, msg: Heartbeat) -> None:
        now_ns = monotonic_ns()
        self.last_seen_ns[HEARTBEAT_TOPIC] = now_ns
        self.heartbeats[msg.node_name] = f"role={msg.role}, status={msg.status}, detail={msg.detail}"
        self.heartbeat_last_seen_ns[msg.node_name] = now_ns

    def on_delay_report(self, msg: String) -> None:
        self.latest_delay_report = msg.data

    def print_summary(self) -> None:
        now_ns = monotonic_ns()
        expired = expired_heartbeat_names(self.heartbeat_last_seen_ns, now_ns, self.timeout_sec)
        for node_name in expired:
            self.heartbeat_last_seen_ns.pop(node_name)
            self.heartbeats.pop(node_name, None)
        if expired:
            self.get_logger().warning('Heartbeat timeout: ' + ', '.join(sorted(expired)))
        watched_topics = [HEARTBEAT_TOPIC, UAV_ODOM_TOPIC, UAV_MAP_TILE_TOPIC, UAV_TARGET_TOPIC, DELAY_PROBE_TOPIC]
        parts = []
        warning_topics = []

        for topic_name in watched_topics:
            last_ns = self.last_seen_ns.get(topic_name)
            if last_ns is None:
                parts.append(f"{topic_name}=missing")
                warning_topics.append(topic_name)
                continue

            age_sec = age_seconds(last_ns, now_ns)
            parts.append(f"{topic_name}={age_sec:.2f}s")
            if age_sec > self.timeout_sec:
                warning_topics.append(topic_name)

        self.get_logger().info(
            "System summary | "
            + " | ".join(parts)
            + f" | heartbeats={len(self.heartbeats)} | latest_delay_report={self.latest_delay_report}"
        )

        if warning_topics:
            self.get_logger().warning(
                "Topic timeout or missing data detected: " + ", ".join(sorted(set(warning_topics)))
            )


def main(args: list[str] | None = None) -> None:
    run_node(SystemMonitor, args)
