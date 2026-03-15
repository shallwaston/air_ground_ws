"""UGV/server-side bringup for Discovery Server based deployment."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import LogInfo
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
            ),
            DeclareLaunchArgument(
                "static_tf_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ag_bringup"), "config", "static_transforms.yaml"]
                ),
            ),
            LogInfo(msg="UGV/server bringup assumes RMW_IMPLEMENTATION=rmw_fastrtps_cpp is already exported."),
            LogInfo(msg="UGV/server bringup assumes ROS_DISCOVERY_SERVER=<server_ip>:11811 is already exported."),
            Node(package="ag_monitor", executable="qos_inspector", output="screen", parameters=[{"qos_config_path": qos_config}]),
            Node(package="ag_mock_nodes", executable="ugv_map_tile_sub", output="screen"),
            Node(package="ag_mock_nodes", executable="ugv_nav_sink_stub", output="screen"),
            Node(package="ag_mock_nodes", executable="arm_target_sink_stub", output="screen"),
            Node(
                package="ag_mock_nodes",
                executable="heartbeat_pub",
                name="heartbeat_server_stack",
                output="screen",
                parameters=[{"node_name": "ugv_server_stack"}, {"role": "server"}, {"detail": "server-side stack alive"}],
            ),
            Node(package="ag_monitor", executable="system_monitor", output="screen"),
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
