from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    package_share = Path(get_package_share_directory("kira_hanson_bridge"))
    default_policy_file = str(package_share / "config" / "safety_policy.yaml")
    namespace = LaunchConfiguration("namespace")
    policy_file = LaunchConfiguration("policy_file")
    evidence_file = LaunchConfiguration("evidence_file")
    topic_prefix = LaunchConfiguration("topic_prefix")
    source_identity = LaunchConfiguration("source_identity")

    arguments = [
        DeclareLaunchArgument("namespace", default_value="little_sophia_sim"),
        DeclareLaunchArgument("policy_file", default_value=default_policy_file),
        DeclareLaunchArgument(
            "evidence_file", default_value="/tmp/kira_hanson_bridge_evidence_v2.jsonl"
        ),
        DeclareLaunchArgument("topic_prefix", default_value="kira"),
        DeclareLaunchArgument("source_identity", default_value="kira"),
    ]

    authority = Node(
        package="kira_hanson_bridge",
        executable="simulator_authority",
        name="kira_simulator_authority",
        namespace=namespace,
        output="screen",
        parameters=[
            {
                "policy_file": policy_file,
                "evidence_file": evidence_file,
                "topic_prefix": topic_prefix,
            }
        ],
    )

    monitor = Node(
        package="kira_hanson_bridge",
        executable="status_monitor",
        name="kira_execution_status_monitor",
        namespace=namespace,
        output="screen",
        parameters=[{"topic_prefix": topic_prefix}],
    )

    demo = TimerAction(
        period=1.5,
        actions=[
            Node(
                package="kira_hanson_bridge",
                executable="demo_intent_source",
                name="kira_demo_intent_source",
                namespace=namespace,
                output="screen",
                parameters=[
                    {
                        "topic_prefix": topic_prefix,
                        "source_identity": source_identity,
                    }
                ],
            )
        ],
    )

    return LaunchDescription([*arguments, authority, monitor, demo])
