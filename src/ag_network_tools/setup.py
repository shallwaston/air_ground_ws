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
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Codex",
    maintainer_email="dev@example.com",
    description="Shared topic names and QoS helpers for the air-ground MVP.",
    license="Apache-2.0",
    tests_require=["pytest"],
)
