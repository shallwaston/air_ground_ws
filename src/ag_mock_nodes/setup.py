"""Setuptools entrypoint for ag_mock_nodes."""

from setuptools import find_packages, setup


package_name = "ag_mock_nodes"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Codex",
    maintainer_email="dev@example.com",
    description="Mock publishers and sink stubs for the air-ground communication MVP.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "arm_target_adapter_stub = ag_mock_nodes.arm_target_adapter_stub:main",
            "arm_target_sink_stub = ag_mock_nodes.arm_target_sink_stub:main",
            "fastlio2_adapter_stub = ag_mock_nodes.fastlio2_adapter_stub:main",
            "heartbeat_pub = ag_mock_nodes.heartbeat_pub:main",
            "hardware_bridge_stub = ag_mock_nodes.hardware_bridge_stub:main",
            "map_2p5d_builder_stub = ag_mock_nodes.map_2p5d_builder_stub:main",
            "nav2_adapter_stub = ag_mock_nodes.nav2_adapter_stub:main",
            "uav_mock_map_tile_pub = ag_mock_nodes.uav_mock_map_tile_pub:main",
            "uav_mock_odom_tf_pub = ag_mock_nodes.uav_mock_odom_tf_pub:main",
            "uav_mock_target_pub = ag_mock_nodes.uav_mock_target_pub:main",
            "ugv_map_tile_sub = ag_mock_nodes.ugv_map_tile_sub:main",
            "ugv_nav_sink_stub = ag_mock_nodes.ugv_nav_sink_stub:main",
        ],
    },
)
