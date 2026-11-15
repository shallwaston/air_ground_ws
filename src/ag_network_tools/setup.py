"""Setuptools entrypoint for ag_network_tools."""

from setuptools import find_packages, setup


package_name = "ag_network_tools"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        # Fixed executable data avoids setuptools easy-install's ambient
        # pkg_resources bootstrap, retaining -IS from the interpreter birth.
        (f"lib/{package_name}", ["ag_network_tools/_strict_launcher_generated/ag_strict_isolated"]),
    ],
    package_data={package_name: ["strict_assets/*", "_strict_asset_pin.py", "_m6_mvp_policy.json"]},
    install_requires=["setuptools"],
    zip_safe=False,
    maintainer="Codex",
    maintainer_email="dev@example.com",
    description="Shared topic names and QoS helpers for the air-ground MVP.",
    license="Apache-2.0",
    tests_require=["pytest"],
)
