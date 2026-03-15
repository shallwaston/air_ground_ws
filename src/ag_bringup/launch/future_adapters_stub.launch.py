"""Launch all future adapter stubs without requiring any real hardware."""

from launch import LaunchDescription
from launch.actions import LogInfo
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            LogInfo(msg="Starting future adapter stubs only. No real hardware or real algorithms are required."),
            Node(package="ag_mock_nodes", executable="fastlio2_adapter_stub", output="screen"),
            Node(package="ag_mock_nodes", executable="map_2p5d_builder_stub", output="screen"),
            Node(package="ag_tf_tools", executable="ekf_adapter_stub", output="screen"),
            Node(package="ag_mock_nodes", executable="nav2_adapter_stub", output="screen"),
            Node(package="ag_mock_nodes", executable="arm_target_adapter_stub", output="screen"),
            Node(package="ag_mock_nodes", executable="hardware_bridge_stub", output="screen"),
        ]
    )
