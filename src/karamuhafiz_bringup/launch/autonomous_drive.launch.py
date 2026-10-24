#!/usr/bin/env python3
"""Simulasyon + lokalizasyon + Nav2 + gorev baslatici (otonom suruş).

localization.launch.py'yi (ki o da sim + manuel surus altyapisini) dahil
eder, uzerine Nav2 yigini ve waypoint_mission_node'u ekler.

Teknik kisit (sartname): "Otonom gorev sirasinda klavye, joystick veya
manuel komut kullanilamaz." Bu launch dosyasi global_keyboard_teleop_node'u
BASLATMAZ - yalnizca Nav2'nin kendi uretecegi komutlar
/ackermann_steering_controller/reference_unstamped'e ulasir (manual_drive_node
devre disi birakilmadiysa onunla CAKISABILIR - bkz. Hafta 3 Gun 3 raporu,
twist_mux ile cozulecek).

NOT: Bu dosya simulasyonda CANLI TEST EDILMEDI (bkz. Hafta 3 raporlari).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    bringup_share = get_package_share_directory("karamuhafiz_bringup")

    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, "launch", "localization.launch.py")
        )
    )

    nav2_params = os.path.join(bringup_share, "config", "nav2_params.yaml")
    mission_yaml = os.path.join(bringup_share, "config", "mission_waypoints.yaml")

    nav2_nodes = [
        Node(
            package="nav2_controller", executable="controller_server",
            name="controller_server", output="screen",
            parameters=[nav2_params],
            # Nav2'nin ham hiz komutu once velocity_smoother'dan gecsin
            # (ani hizlanma/yavaslama sinirlanir - egim/dar bolge guvenligi),
            # ardindan Ackermann controller'a ulassin.
            remappings=[("cmd_vel", "cmd_vel_nav2_raw")],
        ),
        Node(
            package="nav2_planner", executable="planner_server",
            name="planner_server", output="screen",
            parameters=[nav2_params],
        ),
        Node(
            package="nav2_behaviors", executable="behavior_server",
            name="behavior_server", output="screen",
            parameters=[nav2_params],
        ),
        Node(
            package="nav2_bt_navigator", executable="bt_navigator",
            name="bt_navigator", output="screen",
            parameters=[nav2_params],
        ),
        Node(
            package="nav2_waypoint_follower", executable="waypoint_follower",
            name="waypoint_follower", output="screen",
            parameters=[nav2_params],
        ),
        Node(
            package="nav2_velocity_smoother", executable="velocity_smoother",
            name="velocity_smoother", output="screen",
            parameters=[nav2_params],
            remappings=[
                ("cmd_vel", "cmd_vel_nav2_raw"),
                ("cmd_vel_smoothed", "/ackermann_steering_controller/reference_unstamped"),
            ],
        ),
        Node(
            package="nav2_lifecycle_manager", executable="lifecycle_manager",
            name="lifecycle_manager_navigation", output="screen",
            parameters=[
                nav2_params,
                {"node_names": [
                    "controller_server", "planner_server", "behavior_server",
                    "bt_navigator", "waypoint_follower", "velocity_smoother",
                ]},
            ],
        ),
    ]

    waypoint_mission_node = Node(
        package="karamuhafiz_control",
        executable="waypoint_mission_node",
        output="screen",
        parameters=[mission_yaml],
    )

    return LaunchDescription([
        localization,
        *nav2_nodes,
        waypoint_mission_node,
    ])
