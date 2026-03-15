"""Setuptools entrypoint for ag_tf_tools."""

from setuptools import find_packages, setup


package_name = "ag_tf_tools"


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
    description="TF helpers for the air-ground communication MVP.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "ekf_adapter_stub = ag_tf_tools.ekf_adapter_stub:main",
            "frame_alignment_stub = ag_tf_tools.frame_alignment_stub:main",
            "static_tf_loader = ag_tf_tools.static_tf_loader:main",
            "tf_healthcheck = ag_tf_tools.tf_healthcheck:main",
        ],
    },
)
