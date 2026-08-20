from glob import glob
from setuptools import find_packages, setup

package_name = "kira_hanson_bridge"

setup(
    name=package_name,
    version="0.2.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools", "PyYAML>=6.0"],
    python_requires=">=3.10",
    zip_safe=True,
    maintainer="Robert McMurrer",
    maintainer_email="rmcmurrer@kiralabs.org",
    description="Bounded simulator-first ROS 2 intention bridge for Kira World.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "simulator_authority = kira_hanson_bridge.simulator_authority:main",
            "demo_intent_source = kira_hanson_bridge.demo_intent_source:main",
            "status_monitor = kira_hanson_bridge.status_monitor:main",
        ],
    },
)
