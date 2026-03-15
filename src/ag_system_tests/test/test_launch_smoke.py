"""Launch smoke tests for the air-ground MVP workspace."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from launch import LaunchDescription
from launch import LaunchService
from launch.actions import Shutdown
from launch.actions import TimerAction
from launch_ros.actions import Node


def workspace_root() -> Path:
    """Return the workspace root from the source tree layout."""
    return Path(__file__).resolve().parents[3]


def configure_launch_logging_env() -> None:
    """Point launch logging to a writable directory for sandboxed test runs."""
    ros_home = Path("/tmp/air_ground_ws_test_ros_home")
    ros_log_dir = ros_home / "log"
    ros_log_dir.mkdir(parents=True, exist_ok=True)
    os.environ["ROS_HOME"] = str(ros_home)
    os.environ["ROS_LOG_DIR"] = str(ros_log_dir)


def load_launch_module(launch_file: Path):
    """Import a launch file module from disk."""
    spec = importlib.util.spec_from_file_location("launch_under_test", launch_file)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_single_machine_launch_description_loads() -> None:
    configure_launch_logging_env()
    launch_file = workspace_root() / "src" / "ag_bringup" / "launch" / "single_machine_mock.launch.py"
    module = load_launch_module(launch_file)
    launch_description = module.generate_launch_description()

    assert isinstance(launch_description, LaunchDescription)
    assert len(launch_description.entities) > 0


def test_future_adapter_launch_description_loads() -> None:
    configure_launch_logging_env()
    launch_file = workspace_root() / "src" / "ag_bringup" / "launch" / "future_adapters_stub.launch.py"
    module = load_launch_module(launch_file)
    launch_description = module.generate_launch_description()

    assert isinstance(launch_description, LaunchDescription)
    assert len(launch_description.entities) > 0


def test_heartbeat_launch_smoke() -> None:
    configure_launch_logging_env()
    launch_service = LaunchService()
    launch_description = LaunchDescription(
        [
            Node(
                package="ag_mock_nodes",
                executable="heartbeat_pub",
                name="heartbeat_pub_smoke_test",
                output="screen",
                parameters=[
                    {"node_name": "heartbeat_pub_smoke_test"},
                    {"role": "test"},
                    {"detail": "launch smoke"},
                ],
            ),
            TimerAction(period=2.0, actions=[Shutdown(reason="smoke test complete")]),
        ]
    )
    launch_service.include_launch_description(launch_description)

    assert launch_service.run() == 0
