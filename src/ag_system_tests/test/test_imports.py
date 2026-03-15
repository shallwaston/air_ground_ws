"""Basic import smoke tests for the air-ground MVP workspace."""

import importlib


def test_import_core_modules() -> None:
    module_names = [
        "ag_mock_nodes.arm_target_adapter_stub",
        "ag_network_tools.qos_profiles",
        "ag_network_tools.topic_names",
        "ag_mock_nodes.fastlio2_adapter_stub",
        "ag_mock_nodes.hardware_bridge_stub",
        "ag_mock_nodes.map_2p5d_builder_stub",
        "ag_mock_nodes.nav2_adapter_stub",
        "ag_mock_nodes.uav_mock_map_tile_pub",
        "ag_mock_nodes.uav_mock_odom_tf_pub",
        "ag_mock_nodes.uav_mock_target_pub",
        "ag_mock_nodes.ugv_map_tile_sub",
        "ag_monitor.delay_probe_pub",
        "ag_monitor.delay_probe_sub",
        "ag_monitor.system_monitor",
        "ag_tf_tools.ekf_adapter_stub",
        "ag_tf_tools.frame_alignment_stub",
        "ag_tf_tools.static_tf_loader",
        "ag_tf_tools.tf_healthcheck",
    ]

    for module_name in module_names:
        assert importlib.import_module(module_name) is not None
