"""Setuptools entrypoint for ag_monitor."""

from setuptools import find_packages, setup


package_name = "ag_monitor"


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
    description="Monitoring and diagnostics nodes for the air-ground communication MVP.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "delay_probe_pub = ag_monitor.delay_probe_pub:main",
            "delay_probe_sub = ag_monitor.delay_probe_sub:main",
            "qos_inspector = ag_monitor.qos_inspector:main",
            "system_monitor = ag_monitor.system_monitor:main",
            "topic_watchdog = ag_monitor.topic_watchdog:main",
        ],
    },
)
