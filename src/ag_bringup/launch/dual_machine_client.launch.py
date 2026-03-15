"""UAV/client-side bringup for Discovery Server based deployment."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import LogInfo
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    qos_config = LaunchConfiguration("qos_config")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "qos_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ag_bringup"), "config", "qos_profiles.yaml"]
                ),
            ),
            LogInfo(msg="UAV/client bringup assumes RMW_IMPLEMENTATION=rmw_fastrtps_cpp is already exported."),
            LogInfo(msg="UAV/client bringup assumes ROS_DISCOVERY_SERVER=<server_ip>:11811 is already exported."),
            Node(package="ag_monitor", executable="qos_inspector", output="screen", parameters=[{"qos_config_path": qos_config}]),
            Node(package="ag_mock_nodes", executable="uav_mock_odom_tf_pub", output="screen"),
            Node(package="ag_mock_nodes", executable="uav_mock_map_tile_pub", output="screen"),
            Node(package="ag_mock_nodes", executable="uav_mock_target_pub", output="screen"),
            Node(
                package="ag_mock_nodes",
                executable="heartbeat_pub",
                name="heartbeat_client_stack",
                output="screen",
                parameters=[{"node_name": "uav_client_stack"}, {"role": "client"}, {"detail": "uav-side mock stack alive"}],
            ),
            Node(package="ag_monitor", executable="delay_probe_pub", output="screen"),
        ]
    )
