"""Setuptools entrypoint for ag_system_tests."""

from setuptools import find_packages, setup


package_name = "ag_system_tests"


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
    description="System smoke tests for the air-ground communication MVP.",
    license="Apache-2.0",
    tests_require=["pytest"],
)
