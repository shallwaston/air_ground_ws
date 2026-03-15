"""Launch a heavier payload setup for QoS and transport stress tests."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    qos_config = LaunchConfiguration("qos_config")
    frequency_hz = LaunchConfiguration("frequency_hz")
    tile_width = LaunchConfiguration("tile_width")
    tile_height = LaunchConfiguration("tile_height")
    payload_scale = LaunchConfiguration("payload_scale")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "qos_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ag_bringup"), "config", "qos_profiles.yaml"]
                ),
            ),
            DeclareLaunchArgument("frequency_hz", default_value="5.0"),
            DeclareLaunchArgument("tile_width", default_value="128"),
            DeclareLaunchArgument("tile_height", default_value="128"),
            DeclareLaunchArgument("payload_scale", default_value="2.0"),
            Node(package="ag_monitor", executable="qos_inspector", output="screen", parameters=[{"qos_config_path": qos_config}]),
            Node(
                package="ag_mock_nodes",
                executable="uav_mock_map_tile_pub",
                output="screen",
                parameters=[
                    {"frequency_hz": ParameterValue(frequency_hz, value_type=float)},
                    {"tile_width": ParameterValue(tile_width, value_type=int)},
                    {"tile_height": ParameterValue(tile_height, value_type=int)},
                    {"payload_scale": ParameterValue(payload_scale, value_type=float)},
                ],
            ),
            Node(package="ag_mock_nodes", executable="ugv_map_tile_sub", output="screen"),
            Node(
                package="ag_monitor",
                executable="delay_probe_pub",
                output="screen",
                parameters=[{"frequency_hz": ParameterValue(frequency_hz, value_type=float)}],
            ),
            Node(package="ag_monitor", executable="delay_probe_sub", output="screen"),
            Node(package="ag_monitor", executable="system_monitor", output="screen"),
            Node(package="ag_monitor", executable="topic_watchdog", output="screen"),
        ]
    )
