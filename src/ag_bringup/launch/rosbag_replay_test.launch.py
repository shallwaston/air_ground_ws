"""Bring up sink nodes and optionally replay a rosbag for validation."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import ExecuteProcess
from launch.actions import LogInfo
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    bag_path = LaunchConfiguration("bag_path")
    auto_play = LaunchConfiguration("auto_play")
    qos_config = LaunchConfiguration("qos_config")
    static_tf_config = LaunchConfiguration("static_tf_config")

    return LaunchDescription(
        [
            DeclareLaunchArgument("bag_path", default_value="", description="Path to a rosbag to replay."),
            DeclareLaunchArgument("auto_play", default_value="false", description="If true, run ros2 bag play automatically."),
            DeclareLaunchArgument(
                "qos_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ag_bringup"), "config", "qos_profiles.yaml"]
                ),
            ),
            DeclareLaunchArgument(
                "static_tf_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ag_bringup"), "config", "static_transforms.yaml"]
                ),
            ),
            LogInfo(
                condition=UnlessCondition(auto_play),
                msg="auto_play is false. Start replay manually with: ros2 bag play <bag_path>",
            ),
            ExecuteProcess(
                condition=IfCondition(auto_play),
                cmd=["ros2", "bag", "play", bag_path, "--clock"],
                output="screen",
            ),
            Node(package="ag_monitor", executable="qos_inspector", output="screen", parameters=[{"qos_config_path": qos_config}]),
            Node(package="ag_mock_nodes", executable="ugv_map_tile_sub", output="screen"),
            Node(package="ag_mock_nodes", executable="ugv_nav_sink_stub", output="screen"),
            Node(package="ag_mock_nodes", executable="arm_target_sink_stub", output="screen"),
            Node(package="ag_monitor", executable="system_monitor", output="screen"),
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
