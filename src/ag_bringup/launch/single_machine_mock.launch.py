"""Single-machine loopback bringup for the air-ground communication MVP."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    qos_config = LaunchConfiguration("qos_config")
    static_tf_config = LaunchConfiguration("static_tf_config")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "qos_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ag_bringup"), "config", "qos_profiles.yaml"]
                ),
                description="QoS YAML config used by qos_inspector and helper nodes.",
            ),
            DeclareLaunchArgument(
                "static_tf_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ag_bringup"), "config", "static_transforms.yaml"]
                ),
                description="Static transform YAML for placeholder extrinsics.",
            ),
            Node(package="ag_monitor", executable="qos_inspector", output="screen", parameters=[{"qos_config_path": qos_config}]),
            Node(package="ag_mock_nodes", executable="uav_mock_odom_tf_pub", output="screen"),
            Node(package="ag_mock_nodes", executable="uav_mock_map_tile_pub", output="screen"),
            Node(package="ag_mock_nodes", executable="uav_mock_target_pub", output="screen"),
            Node(package="ag_mock_nodes", executable="ugv_map_tile_sub", output="screen"),
            Node(package="ag_mock_nodes", executable="ugv_nav_sink_stub", output="screen"),
            Node(package="ag_mock_nodes", executable="arm_target_sink_stub", output="screen"),
            Node(
                package="ag_mock_nodes",
                executable="heartbeat_pub",
                name="heartbeat_uav_stack",
                output="screen",
                parameters=[{"node_name": "uav_mock_stack"}, {"role": "uav"}, {"detail": "mock publishers alive"}],
            ),
            Node(
                package="ag_mock_nodes",
                executable="heartbeat_pub",
                name="heartbeat_ugv_stack",
                output="screen",
                parameters=[{"node_name": "ugv_mock_stack"}, {"role": "ugv"}, {"detail": "mock sinks alive"}],
            ),
            Node(package="ag_monitor", executable="system_monitor", output="screen"),
            Node(package="ag_monitor", executable="delay_probe_pub", output="screen"),
            Node(package="ag_monitor", executable="delay_probe_sub", output="screen"),
            Node(package="ag_monitor", executable="topic_watchdog", output="screen"),
            Node(package="ag_tf_tools", executable="frame_alignment_stub", output="screen"),
            Node(
                package="ag_tf_tools",
                executable="static_tf_loader",
                output="screen",
                parameters=[{"config_path": static_tf_config}],
            ),
            Node(package="ag_tf_tools", executable="tf_healthcheck", output="screen"),
        ]
    )
